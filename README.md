# KEBA KeContact P30 als evcc `custom` Charger

Eigene evcc-Konfiguration (`type: custom`, offizielle Plugins `modbus`/`js`)
für eine KEBA KeContact P30 per Modbus TCP.

**Lizenz-Abgrenzung:** Kein Code aus evccs sponsorpflichtigem KEBA-Treiber
(`charger/keba*.go`, KEBA-Templates) wurde gelesen, kopiert oder nachgebaut.
Der Sponsor-Check wird nicht verändert. Einzige Protokollquellen: KEBAs
öffentlicher *KeContact P30 Modbus TCP Programmers Guide* und eigene Messungen.

## Status

| Runde | Inhalt | Stand |
|---|---|---|
| 0 | Erreichbarkeit, Lese-Dump | Script fertig, Messung an der Box offen |
| 1 | Read-Attribute (status, enabled, power, energy) | offen |
| 2 | enable / maxcurrent | offen |
| 3 | Loadpoint, PV-Modus | offen |

## Diagnosetool

`tools/keba_dump.py` – nur lesend (Modbus-Funktion 0x03), nur Python-Standardbibliothek.

```sh
python3 tools/keba_dump.py <ip>                       # einmaliger Dump
python3 tools/keba_dump.py <ip> --watch 5 --count 12  # 1 min Verlauf
python3 tools/keba_dump.py <ip> --json > dump.json
```

## Register-Map (Lesen)

Alle Register: Holding Register (FC 0x03), je 2 × 16 bit, uint32 big endian,
Unit-ID 255. **Quelle-Spalte:** `Doku` = laut Programmers Guide, noch nicht
gemessen; `Messung` = an meiner Box bestätigt (mit Datum).

| Adresse | Inhalt | Einheit / Kodierung | Quelle |
|---|---|---|---|
| 1000 | Ladestatus | 0 Start-up, 1 nicht bereit, 2 bereit, 3 lädt, 4 Fehler, 5 Autorisierung abgelehnt | Doku |
| 1004 | Kabelstatus | 0 kein Kabel, 1 Kabel an Box, 3 an Box verriegelt, 5 Box+Fahrzeug, 7 Box+Fahrzeug verriegelt | Doku |
| 1006 | Fehlercode | 0 = kein Fehler | Doku |
| 1008/1010/1012 | Strom L1/L2/L3 | mA | Doku |
| 1014 | Seriennummer | dezimal | Doku |
| 1016 | Produkttyp | dezimal, Kodierung offen | Doku |
| 1018 | Firmware | Kodierung offen (roh + hex ausgeben) | Doku |
| 1020 | Wirkleistung | mW | Doku |
| 1036 | Gesamtzählerstand | 0,1 Wh | Doku |
| 1040/1042/1044 | Spannung L1/L2/L3 | V | Doku |
| 1046 | Leistungsfaktor | 0,1 % | Doku |
| 1100 | aktueller max. Ladestrom | mA | Doku |
| 1110 | max. unterstützter Strom (HW/DIP) | mA | Doku |
| 1500 | RFID-Karte | hex | Doku |
| 1502 | Energie aktuelle Session | 0,1 Wh | Doku |
| 1550 | Phasenumschaltung Quelle | Enum | Doku |
| 1552 | Phasenumschaltung Zustand | Enum | Doku |
| 1600 | Failsafe-Strom | mA | Doku |
| 1602 | Failsafe-Timeout | s | Doku |

Offene Punkte, die per Messung zu klären sind: Skalierung 1036/1502
(0,1 Wh?), Kodierung 1016/1018, Verfügbarkeit 1550+ je nach Firmware.
