# scripts/ — paraguay_theme

Scripts reutilizables de generación, validación, medición y soporte para el tema `paraguay`.

[Read in English](README.en.md) | **Español**

## Catálogo de scripts

### `banco_plymouth.sh`

- **Propósito:** Banco de pruebas que ejecuta el Plymouth real (`plymouthd` + plugin `script` + renderer `x11`) sin root, aislado en namespaces y dibujando en un Xvfb privado; captura fotogramas PNG y métricas para validar el tema y medir su costo.
- **Manual:** [docs/manuales/banco-de-pruebas.md](../docs/manuales/banco-de-pruebas.md).
- **Sistema:** Linux Debian/Ubuntu (bash) o Windows vía WSL.
- **Uso básico:**
  ```bash
  scripts/banco_plymouth.sh preparar
  scripts/banco_plymouth.sh probar paraguay --segundos 8
  ```

---

### `generar_tema.py`

- **Propósito:** Genera los atlas de sprites PNG (`paraguay/p*.png`, `e*.png`, `d*.png`) y actualiza el bloque «DATOS GENERADOS» de `paraguay/paraguay.script` a partir de las constantes de diseño y la especificación de la bandera.
- **Sistema:** Python 3.9+ con Pillow.
- **Uso básico:**
  ```bash
  python scripts/generar_tema.py
  python scripts/generar_tema.py --comprobar
  ```

---

### `validar_tema.py`

- **Propósito:** Validación automatizada de extremo a extremo sin intervención visual: comprobaciones estáticas de sintaxis/API del script y pruebas dinámicas contra el Plymouth real analizando fotogramas (franjas, escudo, onda, diálogo de clave, barra de progreso).
- **Sistema:** Python 3.9+ con Pillow y banco de pruebas preparado.
- **Uso básico:**
  ```bash
  python scripts/validar_tema.py --rapida
  python scripts/validar_tema.py --sin-banco
  ```

---

### `verificar_instalacion.sh`

- **Propósito:** Verifica en el equipo donde se instaló el tema que todos los archivos coincidan con el repositorio, que el tema esté activo en las alternativas del sistema y que el initramfs contenga los binarios y dependencias requeridas.
- **Sistema:** Linux Debian/Ubuntu (bash). Requiere root.
- **Uso básico:**
  ```bash
  sudo scripts/verificar_instalacion.sh
  ```

---

### `probar_instalador.sh`

- **Propósito:** Ejercita `instalar.sh` y `desinstalar.sh` en un arenero simulado sin root, verificando la idempotencia, respaldos y desinstalación limpia.
- **Sistema:** Linux o WSL (bash).
- **Uso básico:**
  ```bash
  scripts/probar_instalador.sh
  ```

---

### `medir_tema.py`

- **Propósito:** Mide con precisión en el banco de pruebas el consumo de CPU, fotogramas por segundo y memoria para diferentes configuraciones y tamaños de tramo de sprite.
- **Sistema:** Python 3.9+.
- **Uso básico:**
  ```bash
  python scripts/medir_tema.py t4_30 --repeticiones 3
  ```

---

### `hacer_vista_previa.py`

- **Propósito:** Genera `docs/vista-previa.gif` capturando los fotogramas del bucle de animación ejecutado en el Plymouth real.
- **Sistema:** Python 3.9+.
- **Uso básico:**
  ```bash
  python scripts/hacer_vista_previa.py --reusar --ancho 480
  ```

---

### `render_mapa_puntos.py`

- **Propósito:** Valida la matriz de puntos del escudo (dimensiones, simetría, centrado y leyenda) y genera vistas previas intermedias.
- **Sistema:** Python 3.8+ (biblioteca estándar para validar, Pillow para renderizar).
- **Uso básico:**
  ```bash
  python scripts/render_mapa_puntos.py --validar
  ```

---

### `probar_validacion.py`

- **Propósito:** Pruebas de mutación de la suite de validación: introduce defectos deliberados (franjas invertidas, atlas corrupto, etc.) y confirma que la validación los detecte y rechace.
- **Sistema:** Python 3.9+.
- **Uso básico:**
  ```bash
  python scripts/probar_validacion.py --lista
  ```
