# Xbox BLE diagnostic app

`xbox-ble.ax` is a developer diagnostic for the Linux BLE backend used by the
TC002. It connects directly through `import ble`, independently of the normal
Gamepad module. It does not register a player. Script changes do not require
another firmware update. The `technicTiming` option requires the backend in
this branch.

## Run one test

1. Remove old BLE test scripts, especially scripts that delete bonds in `init()`.
   Loading a disabled app still calls `init()` and `setup()`.
2. Let active pairing finish and remove saved gamepads under **System → Gamepad**.
   Both player states must be `unpaired`. Do not press **Pair** during this test.
3. Create a script app, paste [xbox-ble.ax](xbox-ble.ax), save it and enable the app.
4. Open the app settings and enter the controller address from your own log.
   Leave **Test einmal starten** off while saving the initial settings.
5. Open the clock log in a second browser tab. Turn on the controller and put it
   in pairing mode, then enable **Test einmal starten** and save the app settings.
6. Wait for `XBD: Abonnement angefragt`, press A/B and move the sticks. The app
   shows the notification count as `N=`.
7. Keep the log open until `XBD: ENDE` and `XBD: ERGEBNIS`. Save the `XBD:` and
   intervening `ble:` lines outside the checkout. Remove the diagnostic app when
   finished, before testing **System → Gamepad → Pair** again.

A start request resets itself before validation. Without a request the app
stays in `idle`, including after a clock reboot. Enabling an app adds it to the
rotation but does not restart a finished test. For another run, reopen the
settings, enable **Test einmal starten** and save. Saving unchanged settings
is a no-op. Each run scans for at most 30 seconds, bounds connection/setup time
and releases its own resources on completion or failure.

## Settings

The German labels match the diagnostic app's settings.

| Setting | Default | Effect |
|---|---|---|
| Test einmal starten | Off | Requests one run when saved, then resets itself to off. |
| Controller-Adresse | Empty | Connects only to this address; the address type comes from scanning. |
| Testablauf | `notify` | `notify`: subscribe to Input Report 1. `read_first`: read a report before subscribing, then take up to five more samples. `all_reports`: subscribe to all HID Report instances that support notifications or indications. |
| MTU-Austausch | Off | Off uses ATT MTU 23 without a local exchange request. On requests the normal exchange. |
| Technic-Timing anfordern | On | Requests a 50 ms interval, zero peripheral latency and a 600 ms supervision timeout. |
| Pause vor dem Abonnieren | 0 ms | Waits after optional setup operations; range 0–10000 ms. |
| Beobachtungsdauer | 60 s | Observes for 20–180 seconds from the subscription request. |
| Geräteinformationen lesen | On | Reads available manufacturer, model, firmware and software fields. Logs bounded hex, excluding serial numbers. |
| HID-Report-Map vorher lesen | Off | Reads `1812` / `2a4b` before input setup and logs only the length. A missing, empty or failed map read ends the test. |
| HID-Ruhezustand verlassen | Off | Sends one `01` (Exit Suspend) Write Command to `1812` / `2a4c` after the optional map read, before input setup. Requires property `x`. |
| Controller-Kopplung einmal löschen | Off | Deletes only the selected controller's saved bond before scanning, then resets itself to off. |

For a comparison, change one option at a time and use a new radio connection.
Power-cycle the controller and put it in pairing mode before starting again.
Disabling a timing or MTU request does not undo settings on a shared connection.

The report-map option compares the initialization step in
[Pybricks' Xbox client](https://github.com/pybricks/pybricks-micropython/blob/e6f705cb275dd7df9c5c7a9f23a927485c180eec/pybricks/iodevices/pb_type_iodevices_xbox_controller.c).
The normal AWTRIX gamepad client already reads this map. The Exit Suspend option
compares the HID Control Point command implemented by
[BlueZ](https://github.com/bluez/bluez/blob/master/src/shared/hog.c).
Neither option is an established requirement for every Xbox controller.
A successful Write Command callback confirms only local sending, not peer
acknowledgement or a change in the controller's state.

## Read the results

- `APP START v1.4` confirms an explicit start request reached `setup()`.
  It appears even if validation or the active-gamepad guard ends the run.
- `Abonnement angefragt` confirms a subscription request, not its completion.
  Check the backend's `notifications ... enabled` line as well.
- `NOTIFY` counts actual notifications or indications. Only the first five
  generate individual lines, with their length and no input bytes.
- `READ` counts explicit read results and reports baseline, changed or unchanged.
  A read is never counted as a notification. A static readable snapshot does
  not prove that the controller cannot detect inputs.
- `ERGEBNIS` summarizes notification, read and changed-sample counts.
  `reads=0` is expected in `notify` and `all_reports`.
- `0 subscriber(s)` before the app subscribes means an early input arrived
  without a registered script callback. Later `NOTIFY` lines establish delivery.

`ble.read` selects the first readable `2a4d` instance. Berry does not provide a
handle or Report Reference filter for this operation, so it is not guaranteed
to select Report 1 on every device. In `all_reports`, callbacks do not identify
the source handle. A notification proves that at least one selected instance
is sending values. The app does not decode buttons or the report map.

The script uses the same BLE hub as the normal gamepad client. Its subscriptions
set `readInitial: false`, so they do not request the hub's diagnostic readback,
sampling or CCCD Write Command retry. Adapter-wide security and privacy policy
remain in effect. See [TC002 Bluetooth configuration](../../../docs/developers/tc002/bluetooth.md)
for those policies, HCI diagnostics and the remaining scan limitation.

## Troubleshooting

**No new log lines:** check for a script loading or syntax error, remove log
filters, and verify that a start request was saved. **Clear log** clears the
browser view only. Reloading retrieves the clock's retained lines again. The
clock retains 34 lines, so open the log before starting and keep it visible.

**Authentication failed / Permission denied:** a stale bond is one possible
cause. End normal gamepad pairing, power-cycle the controller, enter pairing
mode, enable **Controller-Kopplung einmal löschen** together with the start
request, then save. The log says whether a bond existed and was deleted. This
does not erase the controller's own stored keys or guarantee successful pairing.
The backend's bond count counts LTK records, not necessarily distinct devices.

**Controller blinks again after a test:** the diagnostic intentionally ends and
releases its subscription and connection. Test persistent gameplay through the
normal Gamepad module after removing the diagnostic app.

## Local verification

```sh
python3 tools/tc002/diagnostics/test_xbox_ble.py
```

Requires Python 3 and `cc`. The test compiles the vendored Berry interpreter in
a temporary directory and runs the app with simulated BLE callbacks. It covers
the modes, explicit-start gate, optional setup operations, errors, timeouts,
late callbacks, targeted bond removal and cleanup. It does not exercise the
TC002 scheduler or a physical Bluetooth controller. CI runs this test in the
Linux job.
