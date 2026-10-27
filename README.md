# KEBA KeContact P30 als evcc `custom` Charger

Eigene evcc-Konfiguration (`type: custom`, offizielle Plugins `modbus`/`js`)
für eine KEBA KeContact P30 per Modbus TCP.

**Lizenz-Abgrenzung:** Kein Code aus evccs sponsorpflichtigem KEBA-Treiber
(`charger/keba*.go`, KEBA-Templates) wurde gelesen, kopiert oder nachgebaut.
Der Sponsor-Check wird nicht verändert. Einzige Protokollquellen: KEBAs
öffentlicher *KeContact P30 Modbus TCP Programmers Guide* (V1.04) und eigene Messungen.

## Status

| Runde | Inhalt | Stand |
|---|---|---|
| 0 | Erreichbarkeit, Lese-Dump | erledigt (2026-10-26) |
| 1 | Read-Attribute (status, enabled, power, energy) | erledigt (2026-10-27) |
| 2 | enable / maxcurrent | erledigt (2026-10-27); Failsafe bewusst nicht genutzt |
| 3 | Loadpoint, PV-Modus | `config/keba-ui.yaml` für die Web-UI, Test offen |

## Diagnosetool

`tools/keba_dump.py` – nur lesend (Modbus-Funktion 0x03), nur Python-Standardbibliothek.

```sh
python3 tools/keba_dump.py <ip>                       # einmaliger Dump
python3 tools/keba_dump.py <ip> --watch 5 --count 12  # 1 min Verlauf
python3 tools/keba_dump.py <ip> --json > dump.json
```

Schreibtest (genau ein Schreibzugriff pro Aufruf, danach Rücklesen):

```sh
python3 tools/keba_write.py <ip> enable 0|1
python3 tools/keba_write.py <ip> current <A>   # 6 .. min(16, Reg. 1110)
```

## Register-Map (Lesen)

Quelle „Doku“ = *KeContact P30 Modbus TCP Programmers Guide V1.04* (© KEBA 2022),
Kapitel/Seite angegeben. „Messung“ = an meiner Box (KC-P30 c-series, Kabel,
Firmware 3.10.80) bestätigt.

Protokoll laut Doku Kap. 2 (S. 9): Unit-ID muss 255 sein, nur FC3 (Lesen) und
FC6 (Schreiben), pro Anfrage höchstens 2 Wörter (jedes Leseregister ist UINT32),
empfohlener Abstand > 0,5 s zwischen Lesezugriffen und > 5 s zwischen
Schreibzugriffen. Modbus TCP wird über DIP-Schalter DSW1.3 = ON aktiviert und
darf nicht zusammen mit der UDP-Schnittstelle genutzt werden (Kap. 1.4, S. 7;
c-series ab Firmware 3.10.16).

| Adresse | Inhalt | Einheit / Kodierung | Doku | Messung |
|---|---|---|---|---|
| 1000 | Ladestatus | 0 Start-up, 1 nicht bereit (kein Fahrzeug / durch Autorisierung gesperrt), 2 bereit, 3 lädt, 4 Fehler, 5 unterbrochen (suspended/gesperrt oder Übertemperatur) | 3.1, S. 10 | 1, 3, 5 gesehen; 5 = nach 5014 := 0 |
| 1004 | Kabelstatus | 0 kein Kabel, 1 an Box, 3 an Box verriegelt, 5 Box+Fahrzeug, 7 Box+Fahrzeug verriegelt | 3.2, S. 10 | 3, 7 gesehen |
| 1006 | Fehlercode | 0 = kein Fehler, sonst hexadezimal lesen (z. B. 0x40000 = Gruppe 4) | 3.3, S. 11 | nur 0 gesehen |
| 1008/1010/1012 | Strom L1/L2/L3 | mA | 3.4–3.6, S. 11 | ✓ |
| 1014 | Seriennummer | dezimal | 3.7, S. 12 | 20784954 |
| 1016 | Produkttyp | 6 Dezimalziffern: Typ, Kabel/Steckdose, Strom, Serie, Zähler, RFID | 3.8, S. 12–13 | 314110 = Kabel, 32 A, c-series, Standardzähler, ohne RFID |
| 1018 | Firmware | Bytes hex: Major.Minor.Patch | 3.9, S. 13 | 0x030A5000 = 3.10.80 |
| 1020 | Wirkleistung | mW | 3.10, S. 13 | ✓ |
| 1036 | Gesamtzählerstand | **Doku: Wh. Messung: 0,1 Wh** | 3.11, S. 13–14 | 0,1 Wh, siehe unten |
| 1040/1042/1044 | Spannung L1/L2/L3 | V | 3.12–3.14, S. 14 | ✓ (0 ohne Ladung) |
| 1046 | Leistungsfaktor | 0,1 % | 3.15, S. 14 | ✓ (0 ohne Ladung) |
| 1100 | aktueller max. Ladestrom | mA | 3.16, S. 15 | ✓, 0 wenn gesperrt oder kein Fahrzeug |
| 1110 | max. von der Hardware unterstützter Strom | mA, Minimum aus DIP, Kabelcodierung, Temperatur | 3.17, S. 15 | 16000 |
| 1500 | RFID-Karte | erste 4 Byte UID, hex | 3.18, S. 15 | 0 |
| 1502 | Energie aktuelle Session | **Doku: Wh. Messung: 0,1 Wh** | 3.19, S. 16 | 0,1 Wh |
| 1550 | Phasenumschaltung Quelle | Enum, wie 5050 | 3.20, S. 16 | 0 |
| 1552 | Phasenumschaltung Zustand | 1 oder 3 Phasen | 3.21, S. 16 | 0 |
| 1600 | aktiver Failsafe-Strom | mA | 3.22.1, S. 16 | 0 |
| 1602 | aktiver Failsafe-Timeout | s | 3.22.2, S. 17 | 0 |

### Abweichungen Doku ↔ Messung

- **1036/1502 Energie-Einheit:** Die Doku sagt Wh. Gemessen ist 0,1 Wh:
  Beim Laden mit 2,76 kW stiegen beide Register um 107 bzw. 114 Einheiten
  in < 19 s. Das sind höchstens 14,6 Wh, mit Einheit Wh wären es 107 Wh
  (≈ 20 kW). Die letzte Session zeigte 152031 → 15,2 kWh statt 152 kWh.
  Gesamtzählerstand mit Display noch abgleichen.
- **1018 Beispiel:** Das Beispiel der Doku (50990336 = 0x030A0D00 = „3.10.14“)
  enthält einen Rechenfehler, 0x0D ist 13. Die Dekodierung im Tool folgt der
  Byte-Regel, nicht dem Beispiel.
- **Failsafe-Tabellen (S. 20–21):** Bei 5018 und 5020 steht in der Tabelle
  „5016“. Laut Überschriften: 5016 Strom, 5018 Timeout, 5020 Persist.

### Messbefunde (Runde 0, 2026-10-26, Firmware-Rohwert 0x030A5000)

- Leistung 1020 in mW bestätigt: 2764,86 W ≈ Σ U·I·cos φ
  (232 V·5,939 A + 233 V·5,996 A)·0,993 ≈ 2756 W.
- 1036 und 1502 in 0,1 Wh bestätigt: beide steigen beim Laden konsistent
  (+107 bzw. +114 Einheiten ≈ 11 Wh in < 19 s bei 2,76 kW).
- Spannungen und Leistungsfaktor lesen 0, solange nicht geladen wird.
- 1502 behält den Wert der letzten Session bis zum nächsten Ladebeginn.
- 1100 las 0 vor der Freigabe und 6000 danach (Hypothese H1: 0 = gesperrt).
- 1110 = 16000 mA: Hardware-Limit 16 A.
- 1550/1552 = 0: keine Phasenumschaltung konfiguriert.
- 1600/1602 = 0: Failsafe inaktiv (Klärung in Runde 2).
- Fahrzeug lädt zweiphasig (L3 ≈ 0,001 A).
- 1018 = 0x030A5000 → Firmware 3.10.80 (Kodierung laut Doku 3.9).
- 1016 = 314110 → KC-P30, Kabel, 32 A, c-series, Standardzähler, ohne RFID.

## Register-Map (Schreiben)

FC6 (Write Single Register), Wert UINT16, Doku Kap. 4 (S. 18–21).

| Adresse | Inhalt | Wert | Doku | Messung |
|---|---|---|---|---|
| 5004 | Ladestrom setzen | 6000–63000 mA, gilt bis zum Neustart | 4.1, S. 18 | ✓ 6 → 8 → 6 A |
| 5010 | Energielimit Session | 10 Wh | 4.2, S. 18 | nicht genutzt |
| 5012 | Stecker entriegeln | 0, nur im suspended-Zustand | 4.3, S. 18–19 | nicht genutzt |
| 5014 | Box freigeben/sperren | 0 sperren (laufende Ladung stoppt), 1 freigeben | 4.4, S. 19 | ✓ |
| 5050 | Quelle Phasenumschaltung (Kontakt X2) | 0 keine, 1 OCPP, 2 REST, 3 Modbus, 4 UDP | 4.5, S. 19 | nicht genutzt (keine S10) |
| 5052 | Phasenumschaltung auslösen | 0 = 1 Phase, 1 = 3 Phasen | 4.6, S. 19–20 | nicht genutzt |
| 5016 | Failsafe-Strom | 0 = Laden stoppen, 6000–32000 mA | 4.7.1, S. 20 | offen |
| 5018 | Failsafe-Timeout | 0 = Failsafe aus, 10–600 s | 4.7.2, S. 20 | offen |
| 5020 | Failsafe speichern | 1 = aktuelle Einstellung dauerhaft | 4.7.3, S. 20–21 | offen |

Failsafe laut Doku 4.7: Aktiv wird er erst, wenn ein Timeout geschrieben wird.
Den Strom allein zu setzen genügt nicht. Ohne 5020 := 1 gilt die Einstellung
nur bis zum Neustart. Er greift, wenn innerhalb des Timeouts „kein Modbus-TCP-
Befehl“ kam. Ob Lesezugriffe als Befehl zählen, sagt die Doku nicht, das muss
gemessen werden.

### Runde 1 Messung (evcc charger, 2026-10-26)

| Situation | status | enabled | power | currents |
|---|---|---|---|---|
| angesteckt, lädt nicht | B | false | 0 W | 0/0/0 |
| lädt (6 A) | C | true | 2763 W | 5,96/5,98/0 |
| lädt (16 A, von openWB gesetzt) | C | true | 7324 W | 15,8/15,9/0 |
| abgesteckt | A | false | 0 W | 0/0/0 |

`enabled` (H1, 1100 > 0) ist noch nicht belegt: 1100 fällt auch beim Abstecken
auf 0, könnte also „kein Ladevorgang“ statt „gesperrt“ bedeuten.

### Runde 2, Schreibtest ohne Auto (2026-10-26)

5004 := 6000, 5014 := 0, 5014 := 1 wurden jeweils ohne Modbus-Exception
quittiert (Echo korrekt). Ohne Fahrzeug zeigt sich keine Wirkung:
1000 bleibt 1, 1100 bleibt 0. Aussagekräftig erst mit Fahrzeug.

### Runde 2, Schreibtest mit Auto (2026-10-26)

- Nach dem Anstecken: 1000 = 5 (laut Doku „unterbrochen / suspended“), 1100 = 0;
  evcc-Status B.
- `current 6` und `enable 0` in diesem Zustand: keine sichtbare Änderung.
- `enable 1`: Ladung startet, 1000 = 3, 1100 = 6000, 2753 W.
- `current 8`: 1100 = 8000, 3676 W (≈ 2 × 230 V × 8 A) – 5004 in mA bestätigt.
- Offen: Sperre (5014 := 0) während einer laufenden Ladung; ob 1100 dann auf 0 fällt (H1).

### Runde 2, Sperren während der Ladung (2026-10-27)

- `enable 0` beim Laden: 1000 = 5, 1100 = 0, 0 W. `enable 1`: 1000 = 3,
  1100 = 6000, 2742 W. **H1 bestätigt:** `enabled` = 1100 > 0.
- Ab-/Anstecken bei freigegebener Box: 1000 = 1, 1100 = 6000, Ladung startet
  von selbst. Die Freigabe übersteht also das Abstecken; der frühere Zustand 5
  nach dem Anstecken kam vermutlich von openWB.
- Bekannte Einschränkung: ohne Fahrzeug liest 1100 = 0, `enabled` daher false.

### Runde 2, evcc-Setter (`config/round2-write.yaml`, 2026-10-27)

| evcc-Befehl | 1000 | Leistung |
|---|---|---|
| Ausgangszustand | 3 | 2737 W |
| `--disable` | 5 | 0 W |
| `--enable` | 3 | 2733 W |
| `--current 8` | 3 | 3652 W |
| `--current 6` | 3 | 2735 W |

Bekannte Einschränkungen:
- `maxcurrent`-Setter braucht im js-`out` `type: float` (otto liefert float64;
  `type: int` führt zu einem evcc-Panic).
- Failsafe (1600/1602) ist an der Box inaktiv. Fällt evcc aus, bleibt der
  zuletzt gesetzte Strom aktiv.
- evcc liest pro Zyklus 8 Register direkt hintereinander. Die Doku empfiehlt
  > 0,5 s zwischen Lesezugriffen, und das modbus-Plugin hat keine Option
  für eine Pause pro Anfrage. In allen Tests lief das fehlerfrei.
- Beim Start einer Ladung schreibt evcc `maxcurrent` und `enable` evtl. kurz
  hintereinander. Die Doku empfiehlt > 5 s, in den Tests gab es keine Probleme.

## Umgebung

- evcc 0.318.1, Linux-Paket (systemd), Konfiguration über die Web-UI
  (keine `/etc/evcc.yaml`, Datenbank `/var/lib/evcc/evcc.db`)
- openWB-Steuerung deaktiviert (2026-10-27)
- Failsafe: bewusst nicht aktiviert (Entscheidung 2026-10-27). Fällt evcc aus,
  lädt die Box mit dem zuletzt gesetzten Strom weiter (max. 16 A, Register 1110).
