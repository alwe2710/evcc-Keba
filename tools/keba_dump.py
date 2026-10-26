#!/usr/bin/env python3
"""Read-only register dump for a KEBA KeContact P30 via Modbus TCP.

Sends ONLY function code 0x03 (Read Holding Registers). It never writes.
No dependencies beyond the Python 3 standard library.

Register map source: KEBA "KeContact P30 Modbus TCP Programmers Guide"
(public document). Every entry is marked "doc" until confirmed by a
measurement on the real box; see README.md for the verification status.

Usage:
    python3 keba_dump.py 192.168.x.x
    python3 keba_dump.py 192.168.x.x --watch 5 --count 12
    python3 keba_dump.py 192.168.x.x --json > dump.json
"""

import argparse
import json
import socket
import struct
import sys
import time

# Charging state (reg 1000) and cable state (reg 1004) per Programmers Guide.
CHARGING_STATE = {
    0: "start-up",
    1: "not ready for charging (e.g. disabled / waiting)",
    2: "ready for charging, waiting for EV",
    3: "charging",
    4: "error",
    5: "authorization rejected",
}
CABLE_STATE = {
    0: "no cable plugged",
    1: "cable plugged in station",
    3: "cable locked in station",
    5: "cable plugged in station and vehicle",
    7: "cable plugged and locked in station and vehicle",
}


def enum(table):
    return lambda v: table.get(v, "UNKNOWN value")


def scale(factor, unit):
    return lambda v: f"{v * factor:g} {unit}"


def hexval(v):
    return f"0x{v:08X}"


# (address, name, interpretation). All registers are 2 x 16 bit, uint32 big endian
# (assumption from the guide, to be verified).
REGISTERS = [
    (1000, "charging_state", enum(CHARGING_STATE)),
    (1004, "cable_state", enum(CABLE_STATE)),
    (1006, "error_code", lambda v: "no error" if v == 0 else f"error {v}"),
    (1008, "current_l1", scale(0.001, "A")),  # mA
    (1010, "current_l2", scale(0.001, "A")),
    (1012, "current_l3", scale(0.001, "A")),
    (1014, "serial_number", str),
    (1016, "product_type", str),
    (1018, "firmware_version", hexval),
    (1020, "active_power", scale(0.001, "W")),  # mW
    (1036, "total_energy", scale(0.0001, "kWh")),  # 0.1 Wh
    (1040, "voltage_l1", scale(1, "V")),
    (1042, "voltage_l2", scale(1, "V")),
    (1044, "voltage_l3", scale(1, "V")),
    (1046, "power_factor", scale(0.1, "%")),  # 0.1 %
    (1100, "max_charging_current", scale(0.001, "A")),  # mA
    (1110, "max_supported_current", scale(0.001, "A")),  # mA, HW limit (DIP)
    (1500, "rfid_card", hexval),
    (1502, "session_energy", scale(0.0001, "kWh")),  # 0.1 Wh
    (1550, "phase_switch_source", str),
    (1552, "phase_switch_state", str),
    (1600, "failsafe_current", scale(0.001, "A")),  # mA
    (1602, "failsafe_timeout", scale(1, "s")),
]


class ModbusError(Exception):
    pass


class Client:
    def __init__(self, host, port, unit, timeout):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.unit = unit
        self.tid = 0

    def _recv(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ModbusError("connection closed by peer")
            buf += chunk
        return buf

    def read_holding(self, addr, count):
        self.tid = (self.tid + 1) & 0xFFFF
        pdu = struct.pack(">BHH", 0x03, addr, count)
        self.sock.sendall(struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit) + pdu)
        tid, _, length, _ = struct.unpack(">HHHB", self._recv(7))
        body = self._recv(length - 1)
        if tid != self.tid:
            raise ModbusError(f"transaction id mismatch ({tid} != {self.tid})")
        if body[0] & 0x80:
            raise ModbusError(f"exception code {body[1]}")
        return body[2:2 + body[1]]

    def close(self):
        self.sock.close()


def dump(client, delay):
    rows = []
    for addr, name, interp in REGISTERS:
        row = {"addr": addr, "name": name}
        try:
            raw = client.read_holding(addr, 2)
            regs = struct.unpack(">HH", raw)
            value = struct.unpack(">I", raw)[0]
            row.update(regs=list(regs), raw=value, value=interp(value))
        except (ModbusError, OSError) as e:
            row["error"] = str(e)
        rows.append(row)
        time.sleep(delay)
    return rows


def print_table(rows):
    print(time.strftime("--- %Y-%m-%d %H:%M:%S ---"))
    print(f"{'addr':>5}  {'name':<22} {'regs (hi, lo)':<16} {'raw u32':>12}  interpreted")
    for r in rows:
        if "error" in r:
            print(f"{r['addr']:>5}  {r['name']:<22} READ FAILED: {r['error']}")
        else:
            regs = f"{r['regs'][0]}, {r['regs'][1]}"
            print(f"{r['addr']:>5}  {r['name']:<22} {regs:<16} {r['raw']:>12}  {r['value']}")
    sys.stdout.flush()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("host")
    p.add_argument("--port", type=int, default=502)
    p.add_argument("--unit", type=int, default=255)
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--delay", type=float, default=0.1,
                   help="pause between single register reads in s (default 0.1)")
    p.add_argument("--watch", type=float, metavar="SEC",
                   help="repeat the dump every SEC seconds (min 2)")
    p.add_argument("--count", type=int, default=10,
                   help="number of dumps in --watch mode (default 10, hard max 720)")
    p.add_argument("--json", action="store_true", help="print JSON instead of a table")
    a = p.parse_args()

    runs = 1
    if a.watch is not None:
        a.watch = max(a.watch, 2.0)
        runs = max(1, min(a.count, 720))

    client = Client(a.host, a.port, a.unit, a.timeout)
    try:
        for i in range(runs):
            rows = dump(client, a.delay)
            if a.json:
                print(json.dumps({"time": time.time(), "registers": rows}))
            else:
                print_table(rows)
            if i < runs - 1:
                time.sleep(a.watch)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


if __name__ == "__main__":
    main()
