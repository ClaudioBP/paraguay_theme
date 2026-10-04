# paraguay_theme

[![Licencia: GPL v3](https://img.shields.io/badge/Licencia-GPLv3-blue.svg)](LICENSE)
[![Plymouth: >= 0.9.5](https://img.shields.io/badge/Plymouth->=0.9.5-informational.svg)](https://www.freedesktop.org/wiki/Software/Plymouth/)

[Read in English](README.en.md) | **Español**

Tema para [Plymouth](https://www.freedesktop.org/wiki/Software/Plymouth/) (la pantalla de arranque de Linux): una bandera paraguaya construida mediante una matriz de puntos luminosos, que ondea con relieve e iluminación dinámica sobre fondo negro durante el arranque y apagado del sistema.

![Vista previa: fotogramas capturados del Plymouth real](docs/vista-previa.gif)

---

## Características

- **Diseño geométrico fiel:** 1245 puntos en grilla de 24 × 44 para las franjas tricolor (rojo `#D52B1E`, blanco `#E8E8E8`, azul `#0038A8`; proporción 11:20 oficial) y sub-grilla fina de 17 × 17 para el escudo del anverso según el Decreto N.º 11.400/2013.
- **Onda fluida con relieve:** Bucle continuo de 3 segundos con pliegues diagonales y sombreado tridimensional (los puntos aumentan de escala y brillo en las crestas).
- **Soporte completo de diálogos del sistema:**
  - Desbloqueo de disco cifrado (con ranuras interactivas de puntos y texto de aviso).
  - Preguntas y confirmaciones del sistema.
  - Mensajes de arranque y apagado.
  - Barra de progreso para actualizaciones del sistema sin conexión (*offline updates*).
- **Adaptable y multi-monitor:** Ajuste dinámico de escala desde 800 × 600 hasta 4K / HiDPI (escala 2) y soporte para configuraciones con varias pantallas.
- **Rendimiento optimizado:** Agrupamiento de puntos en tramos con atlas de sprites pre-renderizados y sprite cobertor que minimiza el consumo de CPU.

---

## Requisitos

- Sistema operativo Linux (probado en Ubuntu 24.04 LTS y 26.04).
- **Plymouth 0.9.5** (2020) o posterior con el plugin `script` (incluido en `plymouth` en Debian/Ubuntu/Arch; `plymouth-plugin-script` en Fedora/openSUSE).
- Para textos de avisos y diálogos: plugin de etiquetas (`plymouth-label` en Debian/Ubuntu; `plymouth-plugin-label` en Fedora/openSUSE).
- En Debian y Ubuntu: paquete `fontconfig` (requerido por el hook de initramfs de Plymouth al usar temas gráficos).

---

## Instalación

En el equipo Linux de destino:

```bash
git clone -c core.autocrlf=false https://github.com/<usuario>/paraguay_theme.git
cd paraguay_theme

# 1. Simulación previa (muestra las acciones sin realizar cambios en el sistema)
./instalar.sh --simular

# 2. Instalación real (copia paraguay/, selecciona el tema y regenera el initramfs)
sudo ./instalar.sh
```

El instalador registra el tema previo del equipo para permitir una restauración limpia y segura. Si la regeneración del initramfs falla, revierte automáticamente los cambios.

### Desinstalación

Para restaurar el tema previo de Plymouth y desinstalar `paraguay`:

```bash
sudo ./desinstalar.sh
```

### Verificación post-instalación

En distribuciones basadas en Debian o Ubuntu, puedes verificar que todos los archivos, enlaces del sistema y componentes en el initramfs quedaron correctamente configurados:

```bash
sudo scripts/verificar_instalacion.sh
```

---

## Probar sin reiniciar el equipo

Es posible previsualizar el tema interactivo en una consola libre (`tty8`) mediante SSH o terminal sin reiniciar:

```bash
sudo sh -c 'plymouthd --debug --debug-file=/tmp/plymouth.log --tty=/dev/tty8 --kernel-command-line="splash plymouth.splash=paraguay"; plymouth show-splash; sleep 8; plymouth quit'
```

Para probar también el diálogo de contraseña antes de salir:

```bash
sudo sh -c 'plymouthd --debug --tty=/dev/tty8; plymouth show-splash; plymouth ask-for-password --prompt="Prueba de clave" >/dev/null; sleep 3; plymouth quit'
```

---

## Desarrollo y banco de pruebas

El repositorio incluye herramientas completas para modificar el tema y validarlo de extremo a extremo sin necesidad de root:

```bash
# 1. Regenerar atlas de imágenes y el bloque de datos del script
python scripts/generar_tema.py

# 2. Validar el tema contra una instancia real aislada de Plymouth
python scripts/validar_tema.py --rapida

# 3. Medir el costo de CPU y consumo de recursos
python scripts/medir_tema.py
```

### Banco de pruebas aislado

Para ejecutar `plymouthd` en un entorno aislado con namespaces y Xvfb (sin privilegios de root ni afectar el escritorio):

```bash
# Desde Linux o dentro de WSL:
scripts/banco_plymouth.sh preparar

# Desde Windows (PowerShell con WSL):
wsl -- bash scripts/banco_plymouth.sh preparar
```

Consulta [docs/manuales/banco-de-pruebas.md](docs/manuales/banco-de-pruebas.md) para más detalles.

---

## Estructura del repositorio

```text
paraguay/        Archivos instalables del tema: .plymouth, .script y atlas de sprites PNG
instalar.sh      Instalador idempotente con respaldo y rollback automático
desinstalar.sh   Restaura el tema anterior del sistema
scripts/         Generadores de assets, suite de pruebas y scripts de diagnóstico
docs/
  arquitectura/  Documentación de arquitectura y optimizaciones del script
  investigacion/ Especificación legal de la bandera y referencia del lenguaje Plymouth
  manuales/      Guía de uso del banco de pruebas sin root
assets/          Manifiesto y procedencia de insumos
```

---

## Puntos de entrada a la documentación

- **Arquitectura del tema:** [docs/arquitectura/tema.md](docs/arquitectura/tema.md).
- **Referencia del lenguaje de script de Plymouth:** [docs/investigacion/plymouth-script-referencia.md](docs/investigacion/plymouth-script-referencia.md).
- **Marco normativo y proporciones de la bandera:** [docs/investigacion/bandera-paraguay.md](docs/investigacion/bandera-paraguay.md).
- **Mediciones y comparativa de rendimiento:** [docs/investigacion/plymouth-script-mediciones.md](docs/investigacion/plymouth-script-mediciones.md).

---

## Licencia

Este proyecto está publicado bajo la licencia **GNU General Public License v3.0** (GPL-3.0). Consulta el archivo [LICENSE](LICENSE) para más detalles.
