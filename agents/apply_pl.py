#!/usr/bin/env python3
"""
Apply a safe power-limit preset for Intel T2 MacBook Pros on Linux.

Lite preset used here:
    PL1 = 20 W
    PL2 = 28 W
Tau (time window) is left unchanged.

Requires:
    msr-tools (rdmsr, wrmsr)
    msr kernel module loaded (modprobe msr)
"""

import subprocess

MSR_RAPL_POWER_UNIT = 0x606
MSR_PKG_POWER_LIMIT = 0x610


def rdmsr(msr: int) -> int:
    """Read 64-bit MSR value with rdmsr -0 <msr>."""
    out = subprocess.check_output(["rdmsr", "-0", hex(msr)], text=True)
    return int(out.strip(), 16)


def wrmsr(msr: int, value: int) -> None:
    """Write 64-bit MSR value with wrmsr -0 <msr> <value>."""
    subprocess.check_call(["wrmsr", "-0", hex(msr), hex(value)])


def decode_units():
    """
    Decode RAPL power/time units from MSR_RAPL_POWER_UNIT (0x606).

    power_unit = 1 / 2^pu  (Watts)
    time_unit  = 1 / 2^tu  (Seconds)
    """
    units = rdmsr(MSR_RAPL_POWER_UNIT)
    pu = units & 0x0F
    tu = (units >> 16) & 0x0F
    power_unit = 1.0 / (1 << pu)
    time_unit = 1.0 / (1 << tu)
    return power_unit, time_unit


def encode_power_field(raw: int, watts: float, power_unit: float) -> int:
    """
    Patch the 15-bit power field in a PKG_POWER_LIMIT dword.

    Keeps all non-power bits (enable, clamp, lock, etc.) intact.
    """
    raw_power = int(watts / power_unit)
    # clear bits 0–14, then OR in new value
    raw &= ~0x7FFF
    raw |= (raw_power & 0x7FFF)
    return raw


def apply_chill_profile():
    """
    Apply the 'Chill' profile:

        PL1 = 20 W
        PL2 = 28 W

    Tau stays whatever the firmware / previous config set.
    """
    power_unit, _time_unit = decode_units()

    # Read current package power limit MSR
    pkg = rdmsr(MSR_PKG_POWER_LIMIT)

    # Split into low/high dwords
    lo = pkg & 0xFFFFFFFF
    hi = (pkg >> 32) & 0xFFFFFFFF

    # Apply new power limits, preserve all other bits
    lo = encode_power_field(lo, 20.0, power_unit)  # PL1
    hi = encode_power_field(hi, 28.0, power_unit)  # PL2

    new_pkg = (hi << 32) | lo
    wrmsr(MSR_PKG_POWER_LIMIT, new_pkg)

    print("T2 PL preset applied: Chill (PL1=20 W, PL2=28 W)")


def main():
    apply_chill_profile()


if __name__ == "__main__":
    main()
