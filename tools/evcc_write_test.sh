#!/bin/sh
# Runde 2: evcc-Setter gegen die Box testen, mit Rücklesen nach jedem Schritt.
# Fester Ablauf aus 4 Schreibzugriffen, keine Schleife; vor jedem Schritt
# wird mit Enter bestätigt, Ctrl-C bricht ab.
set -e
IP=${1:-192.168.178.151}
CFG=${CFG:-config/round2-write.yaml}
DB=${DB:-/tmp/evcc-keba-test.db}
cd "$(dirname "$0")/.."

readback() {
  sleep 15
  python3 tools/keba_dump.py "$IP" | sed -n '3,5p;12p;18p'
}

step() {
  printf '\n=== %s  (Enter = ausführen, Ctrl-C = abbrechen) ' "$1"
  read _
  evcc charger -c "$CFG" --database "$DB" $2 2>&1 | grep -v 'INFO' || true
  readback
}

echo "Ausgangszustand:"
python3 tools/keba_dump.py "$IP" | sed -n '3,5p;12p;18p'
step "1: evcc --disable (erwartet 1000=5, 1100=0, 0 W)" --disable
step "2: evcc --enable (erwartet 1000=3, 1100=6000)" --enable
step "3: evcc --current 8 (erwartet 1100=8000, ~3,7 kW)" "--current 8"
step "4: evcc --current 6 (erwartet 1100=6000, ~2,75 kW)" "--current 6"
