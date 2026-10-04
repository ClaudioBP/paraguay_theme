# paraguay_theme

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Plymouth: >= 0.9.5](https://img.shields.io/badge/Plymouth->=0.9.5-informational.svg)](https://www.freedesktop.org/wiki/Software/Plymouth/)

**English** | [Leer en español](README.md)

A theme for [Plymouth](https://www.freedesktop.org/wiki/Software/Plymouth/) (the Linux boot splash screen): an animated Paraguayan flag rendered as a luminous dot matrix waving with 3D depth and dynamic lighting against a solid black background during boot and shutdown.

![Preview: Captured frames from live Plymouth engine](docs/vista-previa.gif)

---

## Features

- **Accurate Geometric Design:** 1,245 points across a 24 × 44 grid representing the tricolor bands (red `#D52B1E`, white `#E8E8E8`, blue `#0038A8`; official 11:20 ratio), and a fine 17 × 17 sub-grid depicting the obverse national coat of arms in accordance with Paraguay Presidential Decree No. 11,400/2013.
- **Fluid Wave Motion with Depth:** 3-second continuous loop featuring diagonal wave folds, perspective relief, and dynamic specular shading (dots expand in scale and brighten across wave peaks).
- **Comprehensive System Dialogs:**
  - Encrypted disk password prompt (with animated dot slots and text display).
  - Interactive system prompts and questions.
  - Informational boot and shutdown status messages.
  - Progress bar for offline operating system updates.
- **Multi-Monitor and HiDPI Support:** Dynamic auto-scaling from 800 × 600 up to 4K / HiDPI (scale 2), maintaining visual fidelity across multi-display setups.
- **Optimized CPU Footprint:** Dots grouped into vertical segments using pre-rendered sprite atlases with a single covering sprite to minimize screen redraw damage area.

---

## Prerequisites

- Linux operating system (tested on Ubuntu 24.04 LTS and 26.04).
- **Plymouth 0.9.5** (2020) or newer with the `script` plugin (shipped within `plymouth` on Debian, Ubuntu, and Arch; `plymouth-plugin-script` on Fedora and openSUSE).
- Text/labels support: Plymouth label plugin (`plymouth-label` on Debian/Ubuntu; `plymouth-plugin-label` on Fedora/openSUSE).
- On Debian/Ubuntu: `fontconfig` package (required by Plymouth's initramfs hooks when graphic themes are active).

---

## Installation

On your target Linux machine:

```bash
git clone -c core.autocrlf=false https://github.com/<user>/paraguay_theme.git
cd paraguay_theme

# 1. Dry run / simulation (shows what actions would be taken without modifying the system)
./instalar.sh --simular

# 2. Live installation (copies theme files, configures default theme, and rebuilds initramfs)
sudo ./instalar.sh
```

The installer records your previous theme configuration to enable safe rollbacks. If the initramfs generation fails, it automatically reverts all changes.

### Uninstallation

To restore the previous Plymouth theme and remove `paraguay`:

```bash
sudo ./desinstalar.sh
```

### Post-Installation Verification

On Debian and Ubuntu-based systems, you can verify that all installed files, system symlinks, and initramfs contents are properly configured:

```bash
sudo scripts/verificar_instalacion.sh
```

---

## Testing Without Rebooting

You can preview the live theme on a free virtual console (`tty8`) over SSH or local terminal without rebooting:

```bash
sudo sh -c 'plymouthd --debug --debug-file=/tmp/plymouth.log --tty=/dev/tty8 --kernel-command-line="splash plymouth.splash=paraguay"; plymouth show-splash; sleep 8; plymouth quit'
```

To also test the password prompt dialog before exiting:

```bash
sudo sh -c 'plymouthd --debug --tty=/dev/tty8; plymouth show-splash; plymouth ask-for-password --prompt="Password Test" >/dev/null; sleep 3; plymouth quit'
```

---

## Development and Test Rig

This repository includes a full development toolkit allowing you to modify and validate the theme end-to-end without requiring root access:

```bash
# 1. Regenerate sprite atlases and the script data block
python scripts/generar_tema.py

# 2. Validate the theme against an isolated, live Plymouth daemon
python scripts/validar_tema.py --rapida

# 3. Benchmark CPU utilization and performance
python scripts/medir_tema.py
```

### Isolated Plymouth Test Rig

To run the real `plymouthd` daemon inside an unprivileged user namespace with Xvfb (without root or GUI desktop interaction):

```bash
# From native Linux or inside WSL:
scripts/banco_plymouth.sh preparar

# From Windows (PowerShell with WSL):
wsl -- bash scripts/banco_plymouth.sh preparar
```

For detailed documentation, see [docs/manuales/banco-de-pruebas.md](docs/manuales/banco-de-pruebas.md).

---

## Repository Structure

```text
paraguay/        Installable theme assets: .plymouth, .script, and sprite PNG atlases
instalar.sh      Idempotent installer script with backup and auto-rollback
desinstalar.sh   Restores previous system theme
scripts/         Asset generators, verification scripts, and isolated test harness
docs/
  arquitectura/  Technical architecture and script optimization notes
  investigacion/ Legal flag specifications and Plymouth scripting reference
  manuales/      Guide for using the rootless Plymouth test rig
assets/          Manifest and provenance of external references
```

---

## Documentation Entry Points

- **Theme Architecture:** [docs/arquitectura/tema.md](docs/arquitectura/tema.md).
- **Plymouth Script Reference Manual:** [docs/investigacion/plymouth-script-referencia.md](docs/investigacion/plymouth-script-referencia.md).
- **Paraguayan Flag Specifications:** [docs/investigacion/bandera-paraguay.md](docs/investigacion/bandera-paraguay.md).
- **Performance Benchmarks and Measurements:** [docs/investigacion/plymouth-script-mediciones.md](docs/investigacion/plymouth-script-mediciones.md).

---

## License

This project is licensed under the **GNU General Public License v3.0** (GPL-3.0). See the [LICENSE](LICENSE) file for the full text.
