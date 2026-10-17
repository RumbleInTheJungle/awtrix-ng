"""Run the diagnostic app in the vendored Berry VM with simulated BLE callbacks.

Requires a C compiler; creates its interpreter and fixtures in a temporary directory.
This checks the script state machine, not Bluetooth hardware or the host scheduler.
"""
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
APP = Path(__file__).with_name("xbox-ble.ax")

RUNNER = r'''
#include <stdio.h>
#include <stdlib.h>
#include "berry.h"
void *awtrix_script_heap_alloc(size_t n) { return malloc(n); }
void *awtrix_script_heap_realloc(void *p, size_t n) { return realloc(p, n); }
void awtrix_script_heap_free(void *p) { free(p); }
int main(int argc, char **argv) {
  if (argc != 2) return 2;
  FILE *f = fopen(argv[1], "rb");
  if (!f) return 2;
  fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
  char *s = malloc(n + 1);
  if (!s || fread(s, 1, n, f) != (size_t)n) return 2;
  fclose(f); s[n] = 0;
  bvm *vm = be_vm_new();
  int result = be_loadbuffer(vm, argv[1], s, n);
  if (!result) result = be_pcall(vm, 0);
  if (result) be_dumpexcept(vm);
  be_vm_delete(vm); free(s); return result;
}
'''

FAKES = r'''
import json
var h = {'now': 0, 'logs': [], 'stops': [], 'disconnects': [], 'pad': 'unpaired', 'reject': ''}
def now_ms() return h['now'] end
def log(s) h['logs'].push(s) end
def clear() end
def text(a,b,c,d) end
var store = module('store')
store.get = def (key) return cfg.find(key) end
store.set = def (key, value) cfg[key] = value end
var gamepad = module('gamepad')
gamepad.state = def (player) return h['pad'] end
var ble = module('ble')
ble.bonds = def () return h.find('bonds', []) end
ble.forget = def (address)
  h['forgotten'] = address
  return h['reject'] != 'forget'
end
ble.scan = def (cb, opts)
  if h['reject'] == 'scan' return nil end
  h['scan'] = cb
  return 1
end
ble.stop = def (id) h['stops'].push(id) return true end
ble.connect = def (addr, cb, opts)
  h['connect'] = cb
  h['options'] = opts
  return h['reject'] == 'connect' ? nil : 2
end
ble.disconnect = def (id) h['disconnects'].push(id) return true end
ble.on_disconnect = def (id, cb) h['disconnect'] = cb end
ble.services = def (id)
  if h.find('missing_map', false) return [] end
  return [{'uuid':'1812', 'chars':[{'uuid':'2a4d','props':'rn'}, {'uuid':'2a4b','props':'r'}]},
          {'uuid':'180a', 'chars':[{'uuid':'2a26','props':'r'}]}]
end
ble.read = def (id, svc, chr, cb)
  h['read'] = cb
  h['read_chr'] = chr
  return h['reject'] == 'read' ? nil : 3
end
ble.subscribe = def (id, svc, chr, cb, opts)
  h['notify'] = cb
  h['sub_options'] = opts
  return h['reject'] == 'subscribe' ? nil : 4
end
def found()
  h['scan']({'addr': '02:00:00:00:00:01', 'random': true, 'rssi': -40}, nil)
end
def linked()
  found()
  h['connect'](2, nil)
end
'''


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="awtrix-berry-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        runner = cls.work / "runner.c"
        runner.write_text(RUNNER)
        berry = ROOT / "lib/berry"
        cls.binary = cls.work / "berry-test"
        cmd = ["cc", "-O1", "-Wno-comment", *("-I" + str(berry / p) for p in (".", "src", "generate")),
               str(runner), *map(str, sorted((berry / "src").glob("*.c"))),
               *map(str, sorted((berry / "default").glob("*.c"))), "-lm", "-o", str(cls.binary)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        cls.defaults = {}
        for line in APP.read_text().splitlines():
            if not line.startswith("# @config "):
                continue
            parts = shlex.split(line)
            value = next(p.split("=", 1)[1] for p in parts if p.startswith("default="))
            cls.defaults[parts[2]] = (value == "true" if parts[3] == "bool" else
                                    int(value) if parts[3] == "number" else value)

    def run_case(self, checks, **settings):
        config = {**self.defaults, "address": "02:00:00:00:00:01", "info": False,
                  "start_once": True, **settings}
        source = APP.read_text().replace("import ble\n", "").replace("import gamepad\n", "")
        source = source.replace("return XboxBleDiagnostic()", "var app = XboxBleDiagnostic()")
        fixture = self.work / "case.be"
        fixture.write_text("import json\nvar cfg = json.load(" + json.dumps(json.dumps(config)) + ")\n" +
                           FAKES + source + "\n" + checks)
        result = subprocess.run([str(self.binary), str(fixture)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_modes_and_cleanup(self):
        for mode in ("notify", "read_first", "all_reports"):
            with self.subTest(mode=mode):
                self.run_case(r'''
app.setup()
linked()
assert(h['options']['secure'] && h['options']['random'])
assert(!h['options']['exchangeMtu'] && h['options']['technicTiming'])
app.loop()
if cfg['mode'] == 'read_first'
  assert(app.state == 'read' && !h.contains('notify'))
  h['read'](bytes('0102'), nil)
end
assert(app.state == 'listen')
assert(h['sub_options'].contains('desc') == (cfg['mode'] != 'all_reports'))
assert(!h['sub_options']['readInitial'])
h['notify'](bytes('0102'), nil)
assert(app.notifications == 1)
if cfg['mode'] == 'read_first'
  for i : 1..5
    h['now'] += 3000
    app.loop()
    h['read'](bytes('0304'), nil)
  end
  assert(app.samples == 6 && app.changed == 1 && app.next_read == 0)
end
h['now'] = app.deadline
app.loop()
assert(app.state == 'done' && h['disconnects'] == [2])
assert(h['stops'] == [1,4])
h['notify'](bytes('0304'), nil)
assert(app.notifications == 1)
app.draw()
''', mode=mode)

    def test_device_information_and_delay(self):
        self.run_case(r'''
app.setup()
linked()
assert(app.state == 'info' && h['read_chr'] == '2a26')
h['read'](bytes('352e3233'), nil)
assert(app.state == 'pause')
app.loop()
assert(!h.contains('notify'))
h['now'] = 1000
app.loop()
assert(app.state == 'listen')
assert(h['options']['exchangeMtu'] && !h['options']['technicTiming'])
''', info=True, delay=1000, mtu=True, timing=False)

    def test_timeouts_and_active_manager(self):
        self.run_case("h['pad'] = 'pairing'\napp.setup()\nassert(app.state == 'done' && !h.contains('scan'))")
        self.run_case("app.setup()\nh['now'] = 30000\napp.loop()\nassert(app.state == 'done' && h['stops'] == [1])")
        self.run_case("app.setup()\nfound()\nh['now'] = 45000\napp.loop()\nh['connect'](2,nil)\nassert(app.state == 'done' && !h.contains('notify'))")
        self.run_case("app.setup()\nlinked()\napp.loop()\nh['pad'] = 'connecting'\napp.loop()\nassert(app.state == 'done' && h['disconnects'] == [2])")

    def test_errors(self):
        for op in ("scan", "connect", "read", "subscribe"):
            with self.subTest(op=op):
                self.run_case("h['reject'] = '" + op + "'\napp.setup()\n" +
                              ("found()\n" if op == "connect" else "linked()\napp.loop()\n" if op in ("read", "subscribe") else "") +
                              "assert(app.state == 'done')", mode="read_first" if op == "read" else "notify")
        self.run_case("app.setup()\nlinked()\napp.loop()\nh['notify'](nil,'test failure')\nassert(app.state == 'done')")
        self.run_case("app.setup()\nlinked()\nh['disconnect']('peer closed')\nassert(app.state == 'done')")
        self.run_case("app.setup()\nlinked()\napp.loop()\nh['read'](nil,'no answer')\nassert(app.state == 'listen' && app.next_read == 0)", mode="read_first")

    def test_forget_is_explicit_targeted_and_once(self):
        self.run_case("h['bonds'] = [cfg['address']]\napp.setup()\nassert(!h.contains('forgotten'))")
        self.run_case(r'''
h['bonds'] = ['02:00:00:00:00:02', cfg['address']]
app.setup()
assert(h['forgotten'] == cfg['address'] && !cfg['forget_once'])
assert(app.state == 'scan')
app.finish('test complete')
h.remove('forgotten')
var again = XboxBleDiagnostic()
again.setup()
assert(!h.contains('forgotten'))
''', forget_once=True)
        self.run_case("app.setup()\nassert(!h.contains('forgotten') && !cfg['forget_once'] && app.state == 'scan')", forget_once=True)
        self.run_case("h['pad'] = 'pairing'\napp.setup()\nassert(!h.contains('forgotten') && cfg['forget_once'])", forget_once=True)
        self.run_case("h['bonds'] = [cfg['address']]\nh['reject'] = 'forget'\napp.setup()\nassert(app.state == 'done' && !h.contains('scan'))", forget_once=True)

    def test_failure_cleanup_and_start_marker(self):
        self.run_case("app.setup()\nassert(h['logs'][0] == 'XBD: APP START v1.3' && !cfg['start_once'])", address="")
        self.run_case("app.setup()\nfound()\nh['connect'](nil,'Permission denied')\nassert(app.state == 'done' && h['disconnects'] == [])")
        self.run_case("app.setup()\nlinked()\napp.loop()\nh['disconnect']('peer closed')\nassert(app.state == 'done' && h['disconnects'] == [] && h['stops'] == [1])")

    def test_explicit_start_and_reload(self):
        self.assertFalse(self.defaults['start_once'])
        self.run_case(r'''
h['pad'] = 'pairing'
app.setup()
app.loop()
assert(app.state == 'idle' && h['logs'] == [] && !h.contains('scan'))
assert(!h.contains('forgotten') && cfg['forget_once'])
''', start_once=False, forget_once=True)
        self.run_case(r'''
app.setup()
assert(app.state == 'scan' && !cfg['start_once'])
app.finish('test complete')
h.remove('scan')
var rebooted = XboxBleDiagnostic()
rebooted.setup()
rebooted.loop()
assert(rebooted.state == 'idle' && !h.contains('scan'))
cfg['start_once'] = true
var restarted = XboxBleDiagnostic()
restarted.setup()
assert(restarted.state == 'scan' && !cfg['start_once'])
''')

    def test_compact_service_log(self):
        self.run_case(r'''
app.setup()
linked()
assert(size(h['logs']) == 7)
assert(h['logs'][6] == 'XBD: Dienste=2 HID-Reports=1')
''')

    def test_report_map_before_input_and_subscription(self):
        self.assertFalse(self.defaults['report_map'])
        for mode in ('notify', 'read_first', 'all_reports'):
            with self.subTest(mode=mode):
                self.run_case(r'''
app.setup()
linked()
assert(app.state == 'map' && h['read_chr'] == '2a4b' && !h.contains('notify'))
app.loop()
assert(app.state == 'map')
h['read'](bytes('05010905'), nil)
assert(app.state == 'pause' && app.samples == 0)
app.loop()
if cfg['mode'] == 'read_first'
  assert(app.state == 'read' && h['read_chr'] == '2a4d')
  h['read'](bytes('0102'), nil)
end
assert(app.state == 'listen' && h.contains('notify'))
''', report_map=True, mode=mode)
        self.run_case("app.setup()\nlinked()\nassert(!h.contains('read'))")

    def test_report_map_failures_and_late_reply(self):
        for setup, action in (
            ("h['missing_map'] = true", ""),
            ("h['reject'] = 'read'", ""),
            ("", "h['read'](nil, 'read denied')"),
            ("", "h['read'](bytes(), nil)"),
            ("", "h['now'] = app.deadline\napp.loop()\nh['read'](bytes('0501'),nil)"),
            ("", "h['disconnect']('peer closed')\nh['read'](bytes('0501'),nil)"),
        ):
            with self.subTest(setup=setup, action=action):
                self.run_case(setup + "\napp.setup()\nlinked()\n" + action +
                              "\nassert(app.state == 'done' && !h.contains('notify'))", report_map=True)


if __name__ == "__main__":
    unittest.main()
