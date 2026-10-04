# scripts/ — paraguay_theme

Reusable automation scripts for generating, validating, benchmarking, and maintaining the `paraguay` Plymouth theme.

**English** | [Leer en español](README.md)

## Script Catalog

### `banco_plymouth.sh`

- **Purpose:** Rootless test rig executing real `plymouthd` with the `script` plugin and `x11` renderer inside isolated user namespaces with a private Xvfb display. Captures PNG frames and performance metrics to validate themes and profile CPU usage.
- **Manual:** [docs/manuales/banco-de-pruebas.md](../docs/manuales/banco-de-pruebas.md).
- **Environment:** Debian/Ubuntu Linux (bash) or Windows via WSL.
- **Basic Usage:**
  ```bash
  scripts/banco_plymouth.sh preparar
  scripts/banco_plymouth.sh probar paraguay --segundos 8
  ```

---

### `generar_tema.py`

- **Purpose:** Generates PNG sprite atlases (`paraguay/p*.png`, `e*.png`, `d*.png`) and updates the generated data block in `paraguay/paraguay.script` from mathematical parameters and legal flag definitions.
- **Environment:** Python 3.9+ with Pillow.
- **Basic Usage:**
  ```bash
  python scripts/generar_tema.py
  python scripts/generar_tema.py --comprobar
  ```

---

### `validar_tema.py`

- **Purpose:** Fully automated end-to-end theme validation: static code/API syntax checks and dynamic behavioral tests against real Plymouth instances analyzing captured frames (stripes, coat of arms, wave loop, password prompt dialog, progress bar).
- **Environment:** Python 3.9+ with Pillow and prepared test rig.
- **Basic Usage:**
  ```bash
  python scripts/validar_tema.py --rapida
  python scripts/validar_tema.py --sin-banco
  ```

---

### `verificar_instalacion.sh`

- **Purpose:** Verifies on the target installation system that all theme files match repository checksums, that the theme is actively registered in system alternatives, and that the initramfs contains required plugins and config.
- **Environment:** Debian/Ubuntu Linux (bash). Requires root.
- **Basic Usage:**
  ```bash
  sudo scripts/verificar_instalacion.sh
  ```

---

### `probar_instalador.sh`

- **Purpose:** Tests `instalar.sh` and `desinstalar.sh` in a non-root simulated sandbox, verifying installer idempotence, backup preservation, and clean rollback.
- **Environment:** Linux or WSL (bash).
- **Basic Usage:**
  ```bash
  scripts/probar_instalador.sh
  ```

---

### `medir_tema.py`

- **Purpose:** Accurately benchmarks CPU consumption, distinct frames per second, and memory usage across different segment sizes and refresh rates.
- **Environment:** Python 3.9+.
- **Basic Usage:**
  ```bash
  python scripts/medir_tema.py t4_30 --repeticiones 3
  ```

---

### `hacer_vista_previa.py`

- **Purpose:** Creates `docs/vista-previa.gif` by capturing animation loop frames from a live Plymouth test run.
- **Environment:** Python 3.9+.
- **Basic Usage:**
  ```bash
  python scripts/hacer_vista_previa.py --reusar --ancho 480
  ```

---

### `render_mapa_puntos.py`

- **Purpose:** Validates the coat of arms dot matrix (dimensions, symmetry, centering, legends) and renders preview images.
- **Environment:** Python 3.8+ (standard library for validation, Pillow for image rendering).
- **Basic Usage:**
  ```bash
  python scripts/render_mapa_puntos.py --validar
  ```

---

### `probar_validacion.py`

- **Purpose:** Mutation testing suite for the validation framework: injects deliberate faults into temporary copies (swapped colors, corrupted atlases, missing dialogs) to ensure the test suite correctly rejects them.
- **Environment:** Python 3.9+.
- **Basic Usage:**
  ```bash
  python scripts/probar_validacion.py --lista
  ```
