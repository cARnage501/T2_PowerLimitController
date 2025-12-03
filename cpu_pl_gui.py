#!/usr/bin/env python3
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# ---------- low-level helpers ----------

def run_rdmsr(msr):
    out = subprocess.check_output(["sudo", "rdmsr", msr], text=True).strip()
    return int(out, 16)

def run_wrmsr(msr, value_int):
    subprocess.check_call(["sudo", "wrmsr", msr, hex(value_int)])

def decode_power_time_units():
    """
    MSR 0x606 (RAPL_POWER_UNIT):
    bits 3:0  -> power units  (1 / 2^N W)
    bits 7:4  -> time units   (1 / 2^M s)
    """
    val = run_rdmsr("0x606")
    power_bits = val & 0xF
    time_bits  = (val >> 4) & 0xF

    power_unit = 1.0 / (2 ** power_bits)
    time_unit  = 1.0 / (2 ** time_bits)  # on your chip, this is 1 s
    return power_unit, time_unit

def decode_pls():
    """
    Read MSR 0x610, return (pl1_W, pl2_W, tau_seconds, raw_val)
    Tau is taken from PL1 struct, but we don't modify it in this GUI.
    """
    power_unit, time_unit = decode_power_time_units()
    val = run_rdmsr("0x610")

    lower = val & 0xFFFFFFFF      # PL1 struct
    upper = (val >> 32) & 0xFFFFFFFF  # PL2 struct

    # limit fields (bits 0-14)
    pl1_raw = lower & 0x7FFF
    pl2_raw = upper & 0x7FFF

    # Tau for PL1: bits 17-23 (Intel spec uses this field,
    # we treat it as exponent for simplicity: tau = time_unit * 2^raw)
    tau_raw = (lower >> 17) & 0x7F
    tau_seconds = time_unit * (2 ** tau_raw)

    pl1_w = pl1_raw * power_unit
    pl2_w = pl2_raw * power_unit

    return pl1_w, pl2_w, tau_seconds, val

def encode_pls(pl1_w, pl2_w, preserve_tau_from_val):
    """
    Given desired PL1/PL2 in watts and an existing 0x610 value,
    return new 0x610 int with:
      - PL1 limit updated
      - PL2 limit updated
      - Tau and flags preserved
    """
    power_unit, _ = decode_power_time_units()
    old = preserve_tau_from_val

    lower_old = old & 0xFFFFFFFF
    upper_old = (old >> 32) & 0xFFFFFFFF

    # Encode watts -> raw steps
    pl1_raw = int(round(pl1_w / power_unit))
    pl2_raw = int(round(pl2_w / power_unit))

    # mask out limit bits (0-14), keep the rest
    lower_new = (lower_old & ~0x7FFF) | (pl1_raw & 0x7FFF)
    upper_new = (upper_old & ~0x7FFF) | (pl2_raw & 0x7FFF)

    return (upper_new << 32) | lower_new

# ---------- profiles (in watts) ----------

PROFILES = [
    ("Eco",   12.0, 20.0),
    ("Chill", 20.0, 28.0),
    ("Sport", 23.0, 32.0),
    ("Full",  27.5, 40.0),
    ("Stupid",30.0, 45.0),
]

# ---------- GUI ----------

class PLGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPU PL Control")
        self.resizable(False, False)

        self.current_label = tk.Label(self, text="", font=("monospace", 12))
        self.current_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")

        # Table headers
        hdr_frame = tk.Frame(self)
        hdr_frame.grid(row=1, column=0, columnspan=4, padx=10, sticky="w")

        tk.Label(hdr_frame, text="Profile", width=10, anchor="w").grid(row=0, column=0)
        tk.Label(hdr_frame, text="PL1 (W)", width=10, anchor="e").grid(row=0, column=1)
        tk.Label(hdr_frame, text="PL2 (W)", width=10, anchor="e").grid(row=0, column=2)
        tk.Label(hdr_frame, text="Tau (s)", width=10, anchor="e").grid(row=0, column=3)

        self.profile_var = tk.StringVar(value="Chill")

        self.rows_frame = tk.Frame(self)
        self.rows_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=(0,10), sticky="w")

        for i, (name, pl1, pl2) in enumerate(PROFILES):
            rb = tk.Radiobutton(self.rows_frame, text=name, variable=self.profile_var,
                                value=name, anchor="w")
            rb.grid(row=i, column=0, sticky="w")

            tk.Label(self.rows_frame, text=f"{pl1:4.1f}", width=10, anchor="e").grid(row=i, column=1)
            tk.Label(self.rows_frame, text=f"{pl2:4.1f}", width=10, anchor="e").grid(row=i, column=2)
            # Tau column: we just show "current" because we preserve tau
            tk.Label(self.rows_frame, text="current", width=10, anchor="e").grid(row=i, column=3)

        self.apply_btn = tk.Button(self, text="Apply", command=self.apply_profile)
        self.apply_btn.grid(row=3, column=3, padx=10, pady=(0,10), sticky="e")

        self.refresh_btn = tk.Button(self, text="Refresh", command=self.update_current_label)
        self.refresh_btn.grid(row=3, column=2, padx=10, pady=(0,10), sticky="e")

        self.update_current_label()

    def update_current_label(self):
        try:
            pl1, pl2, tau, _ = decode_pls()
            self.current_label.config(
                text=f"Current →  PL1: {pl1:4.1f} W   PL2: {pl2:4.1f} W   Tau: {tau:5.1f} s"
            )
        except Exception as e:
            messagebox.showerror("Error reading PLs", str(e))

    def apply_profile(self):
        name = self.profile_var.get()
        prof = next((p for p in PROFILES if p[0] == name), None)
        if not prof:
            return
        _, pl1, pl2 = prof
        try:
            _, _, _, old_val = decode_pls()
            new_val = encode_pls(pl1, pl2, old_val)
            run_wrmsr("0x610", new_val)
            self.update_current_label()
        except Exception as e:
            messagebox.showerror("Error applying profile", str(e))

if __name__ == "__main__":
    app = PLGui()
    app.mainloop()
