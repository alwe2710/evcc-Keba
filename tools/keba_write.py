#!/usr/bin/env python3
"""Single, guarded write to a KEBA KeContact P30 via Modbus TCP (test tool).

Exactly ONE write per invocation (function 0x06), no loops. Afterwards it
waits --settle seconds and reads back the relevant registers.

Write registers (source: KEBA P30 Modbus TCP Programmers Guide V1.04, ch. 4,
both verified on this box 2026-10-27). The guide recommends > 5 s between
writes.
    5004  set charging current  [mA], 6000..63000, valid until reboot
    5014  enable/disable station  0 = disable, 1 = enable

Usage:
    python3 keba_write.py <ip> enable 0|1
    python3 keba_write.py <ip> current <A>      # 6 .. min(16, HW limit)
"""

import argparse
import sys
import time

from keba_dump import CABLE_STATE, CHARGING_STATE, Client, ModbusError

ABS_MAX_A = 16  # site fuse limit, never exceeded regardless of arguments
MIN_A = 6


def readback(c):
    st, cable, maxma = c.read_u32(1000), c.read_u32(1004), c.read_u32(1100)
    print(f"  1000 charging_state       = {st} ({CHARGING_STATE.get(st, '?')})")
    print(f"  1004 cable_state          = {cable} ({CABLE_STATE.get(cable, '?')})")
    print(f"  1100 max_charging_current = {maxma} mA")
    print(f"  1020 active_power         = {c.read_u32(1020) / 1000:g} W")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("host")
    p.add_argument("cmd", choices=["enable", "current"])
    p.add_argument("value", type=float)
    p.add_argument("--port", type=int, default=502)
    p.add_argument("--unit", type=int, default=255)
    p.add_argument("--settle", type=float, default=5.0, help="wait before read-back in s (default 5)")
    a = p.parse_args()

    c = Client(a.host, a.port, a.unit, 3.0)
    try:
        if a.cmd == "enable":
            if a.value not in (0, 1):
                sys.exit("enable: value must be 0 or 1")
            addr, raw = 5014, int(a.value)
        else:
            hw_ma = c.read_u32(1110)
            limit_a = min(ABS_MAX_A, hw_ma / 1000)
            if not MIN_A <= a.value <= limit_a:
                sys.exit(f"current: {a.value:g} A outside {MIN_A}..{limit_a:g} A, nothing written")
            addr, raw = 5004, int(round(a.value * 1000))

        print("before:")
        readback(c)
        print(f"WRITE register {addr} := {raw}")
        c.write_single(addr, raw)
        print(f"write acknowledged, waiting {a.settle:g} s ...")
        time.sleep(a.settle)
        print("after:")
        readback(c)
    except (ModbusError, OSError) as e:
        sys.exit(f"FAILED: {e}")
    finally:
        c.close()


if __name__ == "__main__":
    main()
