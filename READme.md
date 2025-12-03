# **T2 Power Limit Controller — Lite Edition**

*A simple, safe RAPL editor + GUI for Intel T2 MacBook Pros on Linux.*

This project gives T2 MacBooks (2018–2020) a **turbo-friendly power profile** on Linux by adjusting Intel RAPL (Running Average Power Limit) values — **without touching firmware, SMC, kernel patches, or persistent system files.**

The Lite Edition focuses on:

* Simple presets
* Safe MSR writes
* Reversible behavior
* Zero permanent modifications
* Eliminating the infamous **400–800 MHz “battery potato mode”** dips and restoring full turbo, even unplugged

The goal:
**Make your Intel T2 MacBook behave like a normal laptop again.**

---

## **What This Actually Fixes**

T2 MacBooks enforce extremely low battery power limits:

* **PL1:** ~5–7W
* **PL2:** ~12–15W

When Linux boots, the system inherits these restrictive defaults.
Result:

* CPU randomly collapses to **400–800 MHz**
* Turbo barely engages
* Heavy tasks stall unless on AC

By raising PL1/PL2 within safe ranges (still below macOS defaults), you get:

* 3.0–3.8 GHz real-world turbo
* Much faster responsiveness
* No firmware changes
* No risk of SMC lockouts

Short dips to 400–800 MHz **may still occur** due to C-state transitions — but the CPU **recovers instantly**, which is the entire objective of this Lite Edition.

---

# **Features**

### **Preset Profiles (GUI)**

The GUI provides safe, conservative presets:

| Profile | PL1 (W) | PL2 (W) | Tau     |
| ------- | ------- | ------- | ------- |
| Eco     | 12      | 20      | current |
| Chill   | 20      | 28      | current |
| Sport   | 23      | 32      | current |
| Full    | 27.5    | 40      | current |
| Stupid  | 30      | 45      | current |

These write directly into **PKG_POWER_LIMIT (MSR 0x610)** while preserving:

* enable flags
* clamp bits
* lock bits
* reserved fields

Only the **power limit values** change.

---

# **Supported Hardware**

* 2018–2020 MacBook Pro (Intel + T2 Chip)
* i5 / i7 / i9 CPUs
* Linux kernels with T2 patches (Ubuntu T2, Mint T2, Fedora T2)

---

# **Dependencies**

### Install MSR tools:

Debian/Mint/Ubuntu:

```bash
sudo apt install msr-tools
```

Fedora:

```bash
sudo dnf install msr-tools
```

### Enable MSR module:

```bash
sudo modprobe msr
```

---

# **Running the GUI**

The repo contains:

* `cpu_pl_gui.py` — main GUI
* `agents/apply_pl.py` — optional auto-apply script

Run the GUI manually:

```bash
python3 cpu_pl_gui.py
```

---

# **Auto-Apply a Preset at Boot (Optional)**

### 1. Make sure the agent is executable

```bash
chmod +x agents/apply_pl.py
```

### 2. Create a systemd service

```bash
sudo nano /etc/systemd/system/t2pl.service
```

Paste this exactly:

```ini
[Unit]
Description=Apply T2 Power Limits
After=multi-user.target

[Service]
ExecStart=/usr/bin/python3 /PATH/TO/REPO/agents/apply_pl.py
Type=oneshot

[Install]
WantedBy=multi-user.target
```

Save → Exit.

### 3. Enable the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable t2pl.service
```

On reboot, your chosen preset will apply automatically.

---

# **Behavior You Should Expect**

### ✔ Longer sustained turbo

3.0–3.8 GHz under load, even on battery

### ✔ Instant recovery from 400–800 MHz dips

These are still triggered by deep C-states, but the CPU snaps back to full speed within milliseconds.

### ✔ No firmware changes

Everything resets automatically if:

* you reboot without auto-apply
* you disable the service
* you remove the tool

### ✔ No thermal override

This tool **does not** disable thermal throttling. Your fans/SMC still protect the system.

---

# **What You Should NOT Expect**

* No permanent PL2 override at hardware level
* No SMC power gate removal
* No thermal throttle bypass
* No macOS-level PL2 behavior
* No persistence unless you explicitly enable systemd auto-apply

The Lite Edition is intentionally safe and non-intrusive.

---

# **Disclaimer**

This project writes directly to Intel MSRs.
Presets included here are known safe for T2 machines.
Modifying them beyond recommended values is **your responsibility**.
