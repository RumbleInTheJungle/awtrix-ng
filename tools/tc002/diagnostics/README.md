# Xbox BLE-Diagnose per Berry

`xbox-ble.ax` ist eine Entwickler-Diagnose für den Branch `fix/xbox-1914` ab
Commit `25bef86`. Sie läuft auf dem bereits installierten Testbuild. Dafür ist
kein neues Firmware-Update nötig. Die App verbindet den Controller direkt über
`import ble`, um den GATT-Ablauf unabhängig vom Gamepad-Modul zu untersuchen.
Sie macht den Controller dabei nicht als Spieler in AWTRIX verfügbar.

## Erster Versuch

1. Alte BLE-Testskripte entfernen, insbesondere das Bond-Löschscript `test`.
   Deaktivieren reicht dafür nicht: `init()` und `setup()` laufen auch beim
   Laden einer deaktivierten App. Einen noch laufenden Pairing-Versuch unter
   **System → Gamepad** auslaufen lassen. Gespeicherte Gamepads für diesen
   isolierten Test dort über **Forget** entfernen. Die Diagnose startet nur,
   wenn beide Spielerzustände `unpaired` sind. **Pair** während des Tests nicht
   anklicken.
2. Den Controller ausschalten, um eine vorhandene Funkverbindung zu beenden.
3. Unter **Scripts** eine App `xbox-diagnose` anlegen. Den vollständigen Inhalt
   von [xbox-ble.ax](xbox-ble.ax) einfügen und speichern.
4. Die App aktivieren. In den App-Einstellungen die Bluetooth-Adresse des
   Controllers aus dem Log eintragen. Die restlichen Einstellungen zunächst
   auf den Vorgaben lassen. **Test einmal starten** bleibt vorerst aus.
   Einstellungen speichern. Die App wartet in `idle` ohne BLE-Aktivität.
5. Den Controller einschalten und in den Pairing-Modus mit schnellem Blinken
   setzen. **Test einmal starten** einschalten und die App-Einstellungen
   speichern. Die Option setzt sich vor dem Versuch selbst wieder auf aus.
   Der Scan wartet höchstens 30 Sekunden. Das Log in einem zweiten Browser-Tab
   bereits vor dem Start öffnen und während des Versuchs geöffnet lassen.
6. Ab der Meldung `XBD: Abonnement angefragt` wiederholt A/B drücken und die
   Sticks bewegen. Die Uhr zeigt unter `N=` die Zahl eingegangener Werte.
7. Nach etwa 60 Sekunden Beobachtung endet der Lauf und gibt seine Verbindung
   frei. Das Log von `XBD: START` bis `XBD: ERGEBNIS` einschließlich der
   dazwischenliegenden `ble:`-Zeilen sichern. Bei einem vorzeitigen Abbruch
   steht der Grund hinter `XBD: ENDE`.

Das alte Bond-Löschscript muss für diese Versuche nicht ausgeführt werden.
Diese Diagnose löscht in der Vorgabe keine Bonds und startet keine automatische
Wiederholung. Ein Aus- und Einschalten der Uhr ist normalerweise nicht nötig.

### Keine neuen Script-Logs

Aktivieren nimmt die App in die Rotation auf, startet aber keinen neuen Test.
Ab Version 1.2 löst **Test einmal starten → Ein → Speichern** einen Lauf aus.
Falls die Einstellungen noch den eingeschalteten Schalter anzeigen, den Dialog
schließen und erneut öffnen. Dann lässt sich die nächste Änderung speichern.
Ein Speichern ohne geänderte Einstellung löst keinen Neustart aus.

Ein angeforderter Lauf meldet zuerst `XBD: APP START v1.4`, auch wenn eine
Einstellung fehlt oder das Gamepad-Modul den Test blockiert. Ohne Startauftrag
bleibt die App still, auch beim Booten. Im Log nach `XBD:` suchen und einen
eventuell gesetzten Filter entfernen. Fehlt die Startmeldung trotz Startauftrag,
den Script-Status im Editor auf einen Lade-/Syntaxfehler prüfen.

**Log löschen** leert nur die Browseransicht. Beim Neuladen erscheinen die auf
der Uhr gespeicherten Zeilen wieder. Die Uhr hält nur die letzten 34 Zeilen vor.
Deshalb kann der Anfang eines Versuchs beim nachträglichen Öffnen fehlen.
Die Diagnose fasst die Dienstliste in einer Zeile zusammen, um Platz zu sparen.
Während eines Versuchs das Log geöffnet lassen und die Seite nicht neu laden.

### Authentifizierung schlägt fehl

Bei wiederholtem `authentication failed` / `Permission denied` ist eine nicht mehr
passende gespeicherte Kopplung ein möglicher Grund. Version 1.1 bietet dafür
**Controller-Kopplung einmal löschen**. Zuerst laufendes Gamepad-Pairing beenden
und gespeicherte Gamepads entfernen. Den Controller aus-/einschalten und in den
Pairing-Modus setzen, dann die Option und **Test einmal starten** aktivieren und
die Einstellungen speichern.
Die App löscht nur den Bond der eingetragenen Adresse vor ihrem Scan. Sie setzt
die Option selbst wieder auf aus; andere Geräte bleiben erhalten. Das Log zeigt,
ob ein Bond vorhanden war und entfernt wurde. Ein Fehler beendet den Versuch.
Die Einstellung löscht nichts im Controller selbst und garantiert keine erfolgreiche
Kopplung. Die Firmware zählt in `N bonds` gespeicherte LTK-Einträge, nicht zwingend
unterschiedliche Geräte.

## Einstellungen

| Einstellung | Wirkung |
|---|---|
| Test einmal starten | Startet beim Speichern genau einen Lauf. Setzt sich vor der Prüfung der Einstellungen wieder auf aus. |
| Controller-Adresse | Verbindet ausschließlich diese Adresse; der Adresstyp kommt aus dem Scan. |
| `notify` | Abonniert die HID-Report-Characteristics mit Report Reference `0101` (Input Report 1). Liest keine Eingabeproben. |
| `read_first` | Liest zunächst einen Input Report, abonniert anschließend Report 1 und liest bis zu fünf weitere Proben im Abstand von drei Sekunden. |
| `all_reports` | Abonniert alle benachrichtigungsfähigen HID-Report-Characteristics (`1812` / `2a4d`) ohne Report-Reference-Filter. Liest keine Eingabeproben. |
| MTU-Austausch | Aus: ATT MTU 23 ohne lokale MTU-Anfrage. Ein: normaler MTU-Austausch. |
| Technic-Timing anfordern | Ein: fordert 50 ms Intervall, Latenz 0 und 600 ms Timeout an. Aus: stellt keine Timing-Anfrage. |
| Pause vor dem Abonnieren | Wartet nach den optionalen Geräteinformationen, bevor der jeweilige Testablauf beginnt. |
| Beobachtungsdauer | 20–180 Sekunden ab der Abonnement-Anfrage; Vorgabe 60 Sekunden. |
| Geräteinformationen lesen | Listet zusätzlich verfügbare Hersteller-, Modell-, Firmware- und Softwarewerte auf. Die Werte erscheinen als Hex, damit beliebige Zeichen das Log nicht verfälschen. |
| HID-Report-Map vorher lesen | Optional: liest `1812` / `2a4b` nach den Geräteinformationen, vor der Pause und vor Eingabeproben oder Abonnement. Protokolliert nur die Länge. Fehler oder ein leeres Ergebnis beenden den Versuch. Vorgabe aus. |
| HID-Ruhezustand verlassen | Optional: sendet einmal `01` (Exit Suspend) an `1812` / `2a4c`, nach der optionalen Report-Map und vor der Pause. Erfordert die Eigenschaft `x`. Vorgabe aus. |
| Controller-Kopplung einmal löschen | Optionaler gezielter Neustart der Kopplung; setzt sich vor dem Löschversuch wieder auf aus. |

Vor jedem weiteren Versuch den Controller aus- und wieder einschalten, in den
Pairing-Modus versetzen und **Test einmal starten** einschalten und speichern.
Das erzwingt eine neue
Funkverbindung. Eine ausgeschaltete Timing-Option setzt bereits ausgehandelte
Werte auf einer noch bestehenden Verbindung nicht zurück. Bereits vorhandene
GATT-Clients können außerdem ihre MTU und ihr Timing behalten.

Zuerst `notify` testen. Danach jeweils nur den Testablauf zu `read_first` oder
`all_reports` ändern. MTU, Timing, Geräteinformationen und Pause dabei zunächst
gleich lassen. Weitere Varianten gezielt nach Auswertung des Logs auswählen.

### Report-Map mit Pybricks vergleichen

Der [Pybricks-Xbox-Verbindungsablauf](https://github.com/pybricks/pybricks-micropython/blob/e6f705cb275dd7df9c5c7a9f23a927485c180eec/pybricks/iodevices/pb_type_iodevices_xbox_controller.c)
liest die HID-Report-Map vor dem Abonnieren. Der Kommentar beschreibt das Lesen
als möglicherweise nötig, um den Controller nach dem Koppeln zu aktivieren.
Die Report-Map beschreibt das Format der Eingaben. Sie enthält keine aktuellen
Tastenwerte. Der AWTRIX-Gamepad-Code liest sie bereits. Ein fehlendes Lesen
erklärt deshalb nicht automatisch die bisherigen Fehler im Gamepad-Modul.

Für den Vergleich innerhalb des Berry-Scripts **HID-Report-Map vorher lesen**
einschalten und die übrigen Einstellungen des Vergleichslaufs beibehalten.
Wurde im Vergleichslauf die Kopplung gelöscht, auch hier die Option einmal
aktivieren. Erwartet wird `HID-Report-Map: ... Bytes` vor dem ersten `READ`
oder der Abonnement-Anfrage. Die App dekodiert die Map nicht.
Das ist ein einzelner Vergleichsschritt, keine vollständige Nachbildung des
Pybricks-Treibers. Insbesondere bleibt die bisherige CCCD-Schreibweise bestehen.

### HID-Control-Point vergleichen

**HID-Ruhezustand verlassen** sendet einen einzelnen Write Command mit dem
Wert `01`. [BlueZ verwendet diesen Befehl zum Verlassen des HID-Ruhezustands](https://github.com/bluez/bluez/blob/master/src/shared/hog.c)
in `bt_hog_set_control_point(hog, false)`. Das ist kein Beleg, dass der
Xbox-Controller in unseren Versuchen im Ruhezustand ist oder dass BlueZ den
Befehl bei jeder Verbindung sendet. Das fortgesetzte Blinken allein beweist
diesen Zustand ebenfalls nicht.

Für einen Vergleich nur diese Option zusätzlich einschalten. Bei Erfolg des
lokalen Sendepfads erscheint `Exit Suspend 01 lokal gesendet; ohne Peer-Bestaetigung`.
Ein Write Command hat keine ATT-Antwort. Diese Meldung bestätigt deshalb weder
die Annahme durch den Controller noch einen Zustandswechsel. Entscheidend sind
weiterhin echte Benachrichtigungen und das beobachtete Blinkverhalten.
Fehlt die Characteristic mit der Eigenschaft `x`, scheitert das Senden oder
bleibt der Callback aus, endet der Versuch. Die App sendet keinen Suspend-Befehl.

### Bisherige Hardware-Ergebnisse

Die Versuche vom 17. Oktober 2026 mit Modell 1914 und Controller-Firmware
`5.9.2709.0` ergaben in den folgenden Varianten keine Benachrichtigungen:

| Ablauf | MTU-Austausch | Technic-Timing | Report-Map | Leseproben |
|---|---|---|---|---|
| `notify` | aus | ein | aus | keine |
| `read_first` | aus | ein | aus | sechs unverändert |
| `read_first` | aus | aus | aus | sechs unverändert |
| `read_first` | ein | aus | aus | sechs unverändert |
| `read_first` | ein | aus | ein, 283 Bytes | sechs unverändert |

Mit MTU-Austausch blieb die ausgehandelte MTU bei 23. Auch der HCI-Monitor
zählte keine Benachrichtigungen. Im letzten Lauf blinkte der Controller laut
Beobachtung während des gesamten Tests. Die Verschlüsselung und GATT-Zugriffe
funktionierten. Einzelne andere Versuche scheiterten bereits bei der
Authentifizierung. Diese Ergebnisse legen die Ursache noch nicht fest.

## Was das Ergebnis aussagt

- `START` protokolliert die gewählten Einstellungen. `Abonnement angefragt`
  bestätigt noch keine erfolgreiche Deskriptor-Konfiguration. Dafür die
  `ble: ... notifications ... enabled`-Zeile beachten.
- `NOTIFY` zählt gelieferte Benachrichtigungen bzw. Indikationen. Nur die ersten
  fünf Werte erzeugen Einzelmeldungen, jeweils mit Länge und ohne Eingabebytes.
  `ERGEBNIS notifications=...` enthält die Gesamtzahl des Laufs.
- `READ` zählt gelesene Proben und unterscheidet Baseline, unverändert und
  geändert. Eine gelesene Probe wird niemals als Benachrichtigung gezählt.
- Bei mehreren lesbaren `2a4d`-Characteristics wählt `ble.read` die erste
  lesbare Instanz. Berry erlaubt hier keine Auswahl per Handle oder Report
  Reference. Der erste gelesene Report muss deshalb nicht zwingend Report 1 sein.
- Bei `all_reports` enthält der Callback keinen Ursprungshandle. Ein Empfang
  beweist daher zunächst nur, dass mindestens eine der abonnierten Instanzen
  Werte liefert.
- Die App liest die Report-Map nur mit der entsprechenden Option und dekodiert
  keine Tasten. Sie nutzt denselben
  BLE-Hub wie das Gamepad-Modul, aber eine eigene Abfolge. Die internen
  `readInitial`-Diagnoseproben und der automatische CCCD-Write-Command-Versuch
  bleiben für ihre Abonnements aus. So können wir zuerst das normale Abonnieren
  allein prüfen.
- Die bestehende Adapter-Konfiguration, insbesondere Legacy Pairing, bleibt
  bestehen. HCI-Kommandos, AIC-Energiespareinstellungen und beliebige Deskriptoren
  können mit dieser App nicht geändert werden.

Wenn die Diagnose beendet ist, die App entfernen. Danach kann wieder über
**System → Gamepad → Pair** getestet werden.

## Lokale Prüfung

```sh
python3 tools/tc002/diagnostics/test_xbox_ble.py
```

Benötigt Python 3 und `cc`. Der Test baut den vorhandenen Berry-Interpreter in
einem temporären Verzeichnis und führt die App mit simulierten BLE-Callbacks
aus. Geprüft werden die drei Abläufe, Geräteinformationen, Optionen, Wartezeit,
Zeitlimits, Ablehnungen, Trennungen, späte Callbacks, der ausdrückliche Start,
das stille Laden ohne Startauftrag, die optionale Report-Map und Exit Suspend
mit Fehler- und Timeout-Pfaden und die Sperre bei aktivem
Gamepad-Modul. Das ersetzt keinen Test mit der Uhr und dem Controller.
