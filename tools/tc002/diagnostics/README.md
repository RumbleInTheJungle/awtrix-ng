# Xbox BLE-Diagnose per Berry

`xbox-ble.ax` ist eine Entwickler-Diagnose für den Branch `fix/xbox-1914` ab
Commit `25bef86`. Sie läuft auf dem bereits installierten Testbuild. Dafür ist
kein neues Firmware-Update nötig. Die App verbindet den Controller direkt über
`import ble`, um den GATT-Ablauf unabhängig vom Gamepad-Modul zu untersuchen.
Sie macht den Controller dabei nicht als Spieler in AWTRIX verfügbar.

## Erster Versuch

1. Alte BLE-Testskripte entfernen. Einen noch laufenden Pairing-Versuch unter
   **System → Gamepad** auslaufen lassen. Gespeicherte Gamepads für diesen
   isolierten Test dort über **Forget** entfernen. Die Diagnose startet nur,
   wenn beide Spielerzustände `unpaired` sind. **Pair** während des Tests nicht
   anklicken.
2. Den Controller ausschalten, um eine vorhandene Funkverbindung zu beenden.
3. Unter **Scripts** eine App `xbox-diagnose` anlegen. Den vollständigen Inhalt
   von [xbox-ble.ax](xbox-ble.ax) einfügen und speichern.
4. In den App-Einstellungen die Bluetooth-Adresse des Controllers aus dem Log
   eintragen. Die restlichen Einstellungen zunächst auf den Vorgaben lassen.
   Bei leerer Adresse startet die App keinen Scan.
5. Den Controller einschalten und in den Pairing-Modus mit schnellem Blinken
   setzen. Die App-Einstellungen speichern bzw. die App neu starten. Ein Lauf
   beginnt beim Start der App; der Scan wartet höchstens 30 Sekunden.
6. Ab der Meldung `XBD: Abonnement angefragt` wiederholt A/B drücken und die
   Sticks bewegen. Die Uhr zeigt unter `N=` die Zahl eingegangener Werte.
7. Nach etwa 60 Sekunden Beobachtung endet der Lauf und gibt seine Verbindung
   frei. Das Log von `XBD: START` bis `XBD: ERGEBNIS` einschließlich der
   dazwischenliegenden `ble:`-Zeilen sichern. Bei einem vorzeitigen Abbruch
   steht der Grund hinter `XBD: ENDE`.

Das alte Bond-Löschscript muss für diese Versuche nicht ausgeführt werden.
Diese Diagnose löscht selbst keine Bonds und startet keine automatische
Wiederholung. Ein Aus- und Einschalten der Uhr ist normalerweise nicht nötig.

## Einstellungen

| Einstellung | Wirkung |
|---|---|
| Controller-Adresse | Verbindet ausschließlich diese Adresse; der Adresstyp kommt aus dem Scan. |
| `notify` | Abonniert die HID-Report-Characteristics mit Report Reference `0101` (Input Report 1). Liest keine Eingabeproben. |
| `read_first` | Liest zunächst einen Input Report, abonniert anschließend Report 1 und liest bis zu fünf weitere Proben im Abstand von drei Sekunden. |
| `all_reports` | Abonniert alle benachrichtigungsfähigen HID-Report-Characteristics (`1812` / `2a4d`) ohne Report-Reference-Filter. Liest keine Eingabeproben. |
| MTU-Austausch | Aus: ATT MTU 23 ohne lokale MTU-Anfrage. Ein: normaler MTU-Austausch. |
| Technic-Timing anfordern | Ein: fordert 50 ms Intervall, Latenz 0 und 600 ms Timeout an. Aus: stellt keine Timing-Anfrage. |
| Pause vor dem Abonnieren | Wartet nach den optionalen Geräteinformationen, bevor der jeweilige Testablauf beginnt. |
| Beobachtungsdauer | 20–180 Sekunden ab der Abonnement-Anfrage; Vorgabe 60 Sekunden. |
| Geräteinformationen lesen | Listet zusätzlich verfügbare Hersteller-, Modell-, Firmware- und Softwarewerte auf. Die Werte erscheinen als Hex, damit beliebige Zeichen das Log nicht verfälschen. |

Vor jedem weiteren Versuch den Controller aus- und wieder einschalten, in den
Pairing-Modus versetzen und die App neu starten. Das erzwingt eine neue
Funkverbindung. Eine ausgeschaltete Timing-Option setzt bereits ausgehandelte
Werte auf einer noch bestehenden Verbindung nicht zurück. Bereits vorhandene
GATT-Clients können außerdem ihre MTU und ihr Timing behalten.

Zuerst `notify` testen. Danach jeweils nur den Testablauf zu `read_first` oder
`all_reports` ändern. MTU, Timing, Geräteinformationen und Pause dabei zunächst
gleich lassen. Weitere Varianten gezielt nach Auswertung des Logs auswählen.

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
- Die App liest keine Report Map und dekodiert keine Tasten. Sie nutzt denselben
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
Zeitlimits, Ablehnungen, Trennungen, späte Callbacks und die Sperre bei aktivem
Gamepad-Modul. Das ersetzt keinen Test mit der Uhr und dem Controller.
