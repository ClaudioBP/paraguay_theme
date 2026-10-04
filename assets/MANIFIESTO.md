# MANIFIESTO de assets — paraguay_theme

Registro de todo recurso externo relevante. Sirve para reproducibilidad,
auditoría de licencias y actualización controlada.

## Recursos versionados en `assets/`

Ninguno. El tema no incluye imágenes, fuentes ni datos de terceros: todos los
PNG de `paraguay/` los dibuja `scripts/generar_tema.py`.

## Recursos externos que se usan sin versionarlos

Se descargan a la caché del banco de pruebas (`~/.cache/paraguay-theme-rig/`,
fuera del repositorio) y no forman parte del tema que se instala.

| Nombre | Origen / URL | Fecha descarga | Versión | Licencia | Propósito | Actualizar cuando | Tamaño |
|--------|--------------|----------------|---------|----------|-----------|-------------------|--------|
| Paquetes de Plymouth y Xvfb para el banco (18 `.deb`) | Repositorios apt configurados en el equipo (`archive.ubuntu.com`), con `apt-get download` desde `scripts/banco_plymouth.sh preparar` | 2026-10-03 | plymouth 24.004.60-1ubuntu7.2 (Ubuntu 24.04) | GPL-2.0-or-later (Plymouth), MIT/X11 (Xvfb) | Ejecutar el Plymouth real sin instalarlo | Cambie la versión de Plymouth del equipo destino | 2,8 MB |
| Código fuente de Plymouth | `https://gitlab.freedesktop.org/plymouth/plymouth.git`, etiqueta `24.004.60` (commit `d6e6366d`) | 2026-10-03 | 24.004.60 | GPL-2.0-or-later | Base de `docs/investigacion/plymouth-script-referencia.md` | Se quiera contrastar otra versión | — |
| Decreto N.º 11.400/2013 (PDF escaneado) | Copia en Wayback Machine citada en `docs/investigacion/bandera-paraguay.md` | 2026-10-03 | 15-07-2013 | Documento público | Norma de la bandera y del escudo | Se promulgue una nueva ley de símbolos | — |

Los mapas de puntos del escudo y la paleta son obra de este proyecto; están en
el bloque JSON de `docs/investigacion/bandera-paraguay.md`.
