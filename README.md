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
| 0 | Erreichbarkeit, Lese-Dump | erledigt (2026-10-26) |
| 1 | Read-Attribute (status, enabled, power, energy) | `config/round1-read.yaml`, Test offen |
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
| 1000 | Ladestatus | 0 Start-up, 1 nicht bereit, 2 bereit, 3 lädt, 4 Fehler, 5 Autorisierung abgelehnt | Messung 2026-10-26 (nur 1, 3 gesehen) |
| 1004 | Kabelstatus | 0 kein Kabel, 1 Kabel an Box, 3 an Box verriegelt, 5 Box+Fahrzeug, 7 Box+Fahrzeug verriegelt | Messung 2026-10-26 (nur 3, 7 gesehen) |
| 1006 | Fehlercode | 0 = kein Fehler | Messung 2026-10-26 (nur 0 gesehen) |
| 1008/1010/1012 | Strom L1/L2/L3 | mA | Messung 2026-10-26 |
| 1014 | Seriennummer | dezimal | Doku |
| 1016 | Produkttyp | dezimal, Kodierung offen | Doku |
| 1018 | Firmware | Kodierung offen (roh + hex ausgeben) | Doku |
| 1020 | Wirkleistung | mW | Messung 2026-10-26 |
| 1036 | Gesamtzählerstand | 0,1 Wh | Messung 2026-10-26 |
| 1040/1042/1044 | Spannung L1/L2/L3 | V | Messung 2026-10-26 |
| 1046 | Leistungsfaktor | 0,1 % | Messung 2026-10-26 |
| 1100 | aktueller max. Ladestrom | mA | Doku |
| 1110 | max. unterstützter Strom (HW/DIP) | mA | Messung 2026-10-26 |
| 1500 | RFID-Karte | hex | Doku |
| 1502 | Energie aktuelle Session | 0,1 Wh | Messung 2026-10-26 |
| 1550 | Phasenumschaltung Quelle | Enum | Doku |
| 1552 | Phasenumschaltung Zustand | Enum | Doku |
| 1600 | Failsafe-Strom | mA | Doku |
| 1602 | Failsafe-Timeout | s | Doku |

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
- 1018 als Bytes gelesen 03.0A.50.00 → vermutlich Firmware 3.10.80
  (unbestätigt, mit Web-UI/Display vergleichen).
- 1016 = 314110: Kodierung unklar, nicht benötigt.
