# Banco de pruebas de Plymouth (`scripts/banco_plymouth.sh`)

Ejecuta el **Plymouth real** (`plymouthd` + plugin de splash `script` + renderer
`x11`) dentro de WSL o de un Linux, **sin root y sin tocar el sistema**, dibujando
en un Xvfb privado. Captura fotogramas PNG y métricas (CPU, memoria, tasa de
animación, errores del `.script`) para validar el tema y medir cuánto cuesta.

No abre ventanas en el escritorio, no usa `DISPLAY=:0`, WSLg ni Wayland del
usuario, y no captura su pantalla: lo único que se graba es un framebuffer
virtual que solo existe dentro del aislamiento. La validación es programática
(códigos de salida, `metricas.json`, análisis de píxeles por script).

## Uso rápido

Desde **Windows (PowerShell)**:

```powershell
wsl -- bash /mnt/d/repos/paraguay_theme/scripts/banco_plymouth.sh preparar
wsl -- bash /mnt/d/repos/paraguay_theme/scripts/banco_plymouth.sh probar /mnt/d/repos/paraguay_theme/<dir_tema> --segundos 8
wsl -- bash /mnt/d/repos/paraguay_theme/scripts/banco_plymouth.sh video /mnt/d/repos/paraguay_theme/output/temporales/banco/<carpeta>
wsl -- bash /mnt/d/repos/paraguay_theme/scripts/banco_plymouth.sh autoprueba
```

Desde Git Bash hay que anteponer `MSYS_NO_PATHCONV=1` (si no, convierte `/mnt/d`
en una ruta de Windows). Para órdenes con `$variables`, comillas o tuberías,
escribir un `.sh` con LF y ejecutarlo con `wsl -- bash /mnt/d/.../archivo.sh`:
`wsl -- bash -c '...'` pasa antes por otro shell que expande los `$`.

Desde **Linux nativo o dentro de WSL** (en la raíz del repositorio):

```bash
scripts/banco_plymouth.sh preparar                       # una vez (descarga ~2,8 MB)
scripts/banco_plymouth.sh probar tema/paraguay --segundos 10 --tamano 1920x1080 --fps 60
scripts/banco_plymouth.sh probar stock:script --segundos 5   # tema de ejemplo de plymouth
scripts/banco_plymouth.sh video output/temporales/banco/paraguay-AAAAMMDD-HHMMSS-PID
scripts/banco_plymouth.sh --help
```

`<dir_tema>` es un directorio con `<nombre>.plymouth`, `<nombre>.script` y las
imágenes. El `.plymouth` debe declarar las rutas de instalación reales
(`ImageDir=/usr/share/plymouth/themes/<nombre>` y `ScriptFile=` debajo de ella);
si no, `probar` se niega (o las reescribe solo en la copia de prueba con
`--ajustar-rutas`).

## Subcomandos

| Subcomando | Qué hace |
|---|---|
| `preparar [--forzar]` | Descarga con `apt-get download` (sin root) y extrae con `dpkg-deb -x` lo que falte en el sistema. Idempotente: con la caché completa no descarga nada. |
| `probar <dir_tema\|stock:NOMBRE> [opciones]` | Corre el tema aislado, captura y escribe métricas. |
| `video <DIR> [--ancho W] [--fps F] [--formato gif\|mp4\|ambos]` | Arma `DIR/animacion.gif` y/o `DIR/animacion.mp4` desde `DIR/frames`, a la velocidad real de la captura. |
| `estado` | Indica si la caché está preparada y con qué versiones. |
| `autoprueba [--salida DIR]` | Verifica el propio banco (4 comprobaciones, ver más abajo). |
| `limpiar --si` | Borra la caché completa (se niega si hay una prueba en curso). |

Opciones de `probar`:

| Opción | Por defecto | Descripción |
|---|---|---|
| `--segundos N` | 8 | Segundos de splash (máx. 600). |
| `--tamano WxH` | 1920x1080 | Resolución de la pantalla virtual. |
| `--fps F` | 30 | Fotogramas por segundo de la captura (máx. 120). |
| `--salida DIR` | `output/temporales/banco/<nombre>-<marca>/` | Directorio de resultados. |
| `--modo M` | boot | `boot`, `shutdown`, `reboot`, `updates`, `system-upgrade`, `firmware-upgrade`, `system-reset`. |
| `--evento T:ACCION[:ARG]` | — | Repetible. Dispara una orden `plymouth ...` a los T segundos del splash (ver tabla). |
| `--min-distintos N` | 0 | Falla (código 14) si hay menos de N fotogramas distintos del anterior. |
| `--plugin-esperado P` | script | Plugin de splash exigido. |
| `--escala N` | — | Fuerza la escala HiDPI (`PLYMOUTH_FORCE_SCALE`). |
| `--cmdline "..."` | `quiet splash plymouth.ignore-serial-consoles` | Línea de comandos del kernel falsa. |
| `--ajustar-rutas` | — | Reescribe `ImageDir`/`ScriptFile` en la copia de prueba. |
| `--sin-frames` | — | No extrae los PNG (solo métricas; más rápido). |
| `--conservar-captura` | — | Deja `DIR/captura.mkv` (video sin pérdida de la captura). |

Acciones de `--evento` (ejercitan los callbacks del tema):

| Acción | Orden que ejecuta | Callback del script |
|---|---|---|
| `mensaje:TEXTO` | `plymouth display-message --text=TEXTO` | `SetDisplayMessageFunction` (verificado) |
| `ocultar-mensaje:TEXTO` | `plymouth hide-message --text=TEXTO` | `SetHideMessageFunction` (**no se disparó**, ver nota) |
| `clave:PROMPT` | `plymouth ask-for-password --prompt=PROMPT` (queda esperando, sin bloquear) | `SetDisplayPasswordFunction` (verificado) |
| `pregunta:PROMPT` | `plymouth ask-question --prompt=PROMPT` (ídem) | `SetDisplayQuestionFunction` (verificado) |
| `progreso:NN` | `plymouth system-update --progress=NN` | `SetSystemUpdateFunction` (verificado) |
| `estado:TEXTO` | `plymouth update --status=TEXTO` | `SetUpdateStatusFunction` (verificado) |
| `raiz-montada` | `plymouth update-root-fs --new-root-dir=/` | `SetRootMountedFunction` (verificado) |
| `modo:M` | `plymouth change-mode --M` (`boot-up`, `shutdown`, `updates`...) | — |
| `pausar` / `reanudar` | `pause-progress` / `unpause-progress` | — |
| `ocultar` / `mostrar` | `hide-splash` / `show-splash` | — |
| `desactivar` / `reactivar` | `deactivate` / `reactivate` | — |
| `raiz-rw`, `recargar` | `update-root-fs --read-write`, `reload` | — |
| `crudo:ARGS` | `plymouth ARGS` (separados por espacios) | — |

Ejemplo: `--evento 2:mensaje:"Verificando discos" --evento 4:clave:"Clave" --evento 6:progreso:42`.

Los eventos se disparan en su segundo absoluto (desvío medido: 5–15 ms) y
`metricas.json` anota cuánto tardó cada orden. «Verificado» significa que un
tema de prueba dibujó una marca distinta en cada callback y se comprobó por
píxeles en los PNG. Notas:

- Con plymouth 24.004.60-1ubuntu7.2 el callback de `SetHideMessageFunction` **no
  se ejecutó** al enviar `hide-message` (el demonio registra `hiding message`,
  pero la función del script no corre). No se determinó la causa; conviene que
  el tema no dependa de ese callback.
- Mientras hay una clave pendiente, una `pregunta` posterior queda en cola y no
  se muestra (no hay forma de responder la clave: el banco no simula teclado).

## Resultados

En el directorio de salida:

- `metricas.json` — resumen legible por máquina (tabla siguiente).
- `frames/f_NNNNN.png` — fotogramas capturados, numerados desde 1.
- `logs/plymouth-debug.log` — registro de depuración de `plymouthd` (ahí salen los
  `Parser error` / `Execution error` del script).
- `logs/fotogramas.csv` — una fila por fotograma: `n`, `pts_s`, `cambio` (1 si
  difiere del anterior), `fraccion_no_negra`, caja de los píxeles no negros
  (`bbox_x0..y1`), `filas_cambiadas` y su rango vertical (`cambio_y0`, `cambio_y1`).
- `logs/muestras.csv` — cada 0,5 s: ticks de CPU y RSS de `plymouthd`, ticks de Xvfb.
- `logs/eventos.tsv` — inicio, fin, segundo pedido, código y orden de cada evento.
- `logs/montajes.log`, `xvfb.log`, `ffmpeg-*.log`, `plymouthd.stderr`,
  `tema-probado.plymouth`.

Campos principales de `metricas.json`:

| Campo | Significado |
|---|---|
| `veredicto`, `codigo_salida`, `problemas` | `OK`/`FALLA`, el código devuelto y la lista de motivos. |
| `avisos`, `imagenes_faltantes` | Advertencias que no cambian el veredicto: `Image("x.png")` literales cuyo archivo no está en el tema (Plymouth no da error, solo no dibuja) y archivos con CRLF. |
| `resolucion` | Tamaño de la pantalla que plymouth dijo usar (`adding WxH pixel display`). |
| `renderer`, `plugin_splash` | Renderer y plugin **realmente usados**, leídos del registro de depuración. |
| `fotogramas_capturados` | Fotogramas grabados (incluye ~0,5 s previos al splash, en negro). |
| `fotogramas_distintos` | Cuántos difieren del anterior (comparación exacta de píxeles). |
| `fotogramas_unicos`, `fotogramas_no_negros`, `primer_fotograma_no_negro` | Conteos auxiliares. |
| `tasa_animacion_fps` | Fotogramas distintos por segundo desde el primer cambio hasta el final. |
| `fps_captura`, `fps_captura_efectivo` | Ritmo pedido y ritmo real de la captura. |
| `animado` | `true` si hubo al menos 2 cambios (1 solo es la aparición del splash). |
| `bbox_no_negro_union`, `fraccion_no_negra_media` | Zona de pantalla que llegó a encenderse. |
| `cpu_plymouthd_pct` | % de **un núcleo** que usó `plymouthd` con el splash visible (`utime+stime` de `/proc/PID/stat` sobre el tiempo de pared). También separado en usuario/sistema. |
| `cpu_xvfb_pct` | Ídem para Xvfb (costo de presentación, ajeno al tema). |
| `rss_max_plymouthd_kb` | Pico de memoria residente (`VmHWM`). `rss_antes_del_splash_kb` permite restar la base. |
| `tiempo_show_splash_s`, `cpu_arranque_y_carga_s` | Cuánto tardó `plymouth show-splash` (parseo + primera ejecución del script) y CPU consumida hasta ahí. |
| `errores_script` | Lista con `tipo` (`parseo`/`ejecucion`), `mensaje`, `archivo`, `linea`, `columna`, `veces`. |
| `eventos` | Segundo pedido, segundo real, duración y código de cada evento. |
| `plymouthd` | `arranco`, `vivo_al_final`, `termino_limpio`, códigos de `show-splash` y `quit`. |

Códigos de salida de `probar`:

| Código | Significado |
|---|---|
| 0 | OK. |
| 1 | Error inesperado. |
| 2 | Argumentos incorrectos (incluye rutas del `.plymouth` mal declaradas). |
| 3 | Caché sin preparar, requisito faltante o fallo de infraestructura. |
| 10 | `plymouthd` no arrancó, murió o dejó de responder (p. ej. bucle infinito en el script). |
| 11 | No se usó el plugin esperado (`script`) con el renderer gráfico `x11`. |
| 12 | Errores en el `.script`: de parseo o de ejecución. |
| 13 | No hubo fotogramas o salieron todos negros. |
| 14 | Menos fotogramas distintos que `--min-distintos`. |

### Cómo leer las métricas

- **`tasa_animacion_fps` es una cota inferior.** Está limitada por `--fps` y por
  el renderer x11, que agrupa actualizaciones (ver «Diferencias»). Para estimar
  el ritmo real del script conviene capturar a 60 fps y medir el desplazamiento:
  con un sprite que avanza 4 px por refresco se midieron 192 px/s, es decir
  ~48 refrescos/s (el plugin `script` refresca a 50 Hz nominales), aunque solo
  ~38 fotogramas/s salieron distintos.
- **CPU y memoria sirven para comparar versiones del tema entre sí**, no como
  valor absoluto del arranque real. Piso medido con un tema trivial (un sprite):
  ~6–7 % de un núcleo y ~27–40 MB de RSS (incluye GTK). Lo que suba de ahí es
  costo del tema.
- Las mediciones tienen ruido si la máquina está ocupada (en WSL la primera
  ejecución tras un rato inactivo arranca con la caché de disco fría). Ante la
  duda, repetir y comparar.

## Cómo está armado

```
banco_plymouth.sh probar
 ├─ copia el tema a <cache>/ejecuciones/<id>/capa/usr/share/plymouth/themes/<nombre>/
 │  y escribe capa/etc/plymouth/plymouthd.conf (Theme=<nombre>, ShowDelay=0)
 ├─ timeout → unshare --user --map-root-user --mount --net --ipc --pid --fork
 │            --mount-proc --kill-child → env -i → setsid → banco_plymouth.sh __interno
 │    ├─ overlays de solo lectura: capa de la ejecución + <cache>/root + sistema real
 │    │    sobre /usr (o sus subdirectorios), /etc y /var
 │    ├─ tmpfs privados en /tmp, /run, /var/lib/plymouth y /mnt/wslg
 │    ├─ Xvfb :99 -screen 0 WxHx24 -nolisten tcp -extension GLX
 │    ├─ plymouthd --no-daemon --debug --debug-file=... --mode=M --kernel-command-line="..."
 │    ├─ ffmpeg -f x11grab → captura.mkv sin pérdida (libx264rgb -qp 0)
 │    ├─ plymouth show-splash → eventos → espera N s → medidas de /proc → plymouth quit
 │    └─ medidas.env
 ├─ ffmpeg: captura.mkv → frames/f_%05d.png
 └─ python3 (solo biblioteca estándar): registros + captura → metricas.json y código de salida
```

- **Paquetes sin root.** `preparar` pregunta a `apt-get -s install` qué falta para
  `plymouth plymouth-x11 plymouth-themes plymouth-label xvfb x11-xkb-utils`, lo baja
  con `apt-get download` y lo extrae en `~/.cache/paraguay-theme-rig/rig/root`
  (cambiable con `BANCO_PLYMOUTH_CACHE`). En el WSL de este equipo fueron 18
  paquetes (2,8 MB; 11 MB extraídos); GTK3 ya estaba instalado. Versión probada:
  plymouth 24.004.60-1ubuntu7.2 (Ubuntu 24.04).
- **Rutas compiladas.** `plymouthd` busca en `/usr/share/plymouth`,
  `/usr/lib/x86_64-linux-gnu/plymouth`, `/etc/plymouth`, `/run/plymouth` y
  `/var/lib/plymouth`. Esas rutas solo existen dentro del namespace de montaje,
  mediante overlays cuya capa inferior es el sistema real. Nada se escribe fuera
  de la caché y del directorio de salida.
- **Montajes heredados.** El kernel rechaza usar como capa inferior un directorio
  que contiene montajes heredados (`overlayfs: failed to clone lowerpath`). En WSL
  `/usr` los tiene (`/usr/lib/wsl/...`), así que el banco desciende y superpone
  `/usr/bin`, `/usr/sbin`, `/usr/share`, `/usr/libexec`, `/usr/lib/x86_64-linux-gnu`...
  Lo decidido queda en `logs/montajes.log`.
- **uid 0 solo adentro.** El cliente `plymouth` y el demonio comparten el
  namespace de usuario, así que la comprobación de credenciales del socket ve uid 0.
- **Concurrencia.** El socket de `plymouthd` (`@/org/freedesktop/plymouthd`) y el
  de X11 son abstractos y pertenecen al namespace de red: cada ejecución tiene el
  suyo, además de `/tmp` y directorio de ejecución propios. Todas pueden usar `:99`.
- **Sin huérfanos.** El namespace de PID con `--kill-child` hace que el kernel
  mate todo si muere `unshare`; el script lo mata en su trampa de salida, y
  `timeout` limita la duración total aunque el script reciba SIGKILL. Los
  directorios de ejecuciones muertas se barren en la siguiente prueba.
- **Bloqueos.** `probar` toma un bloqueo compartido de la caché; `preparar` y
  `limpiar`, exclusivo.
- **Splash en vez de «details».** `/proc/cmdline` de WSL no tiene `splash` y su
  consola es serie (`hvc0`); por eso se falsea la línea del kernel con
  `quiet splash plymouth.ignore-serial-consoles`. Con `DISPLAY` definido,
  `plymouthd` ignora udev y elige el renderer x11, que crea una ventana GTK del
  tamaño del monitor (el del Xvfb).
- **Sin terminal.** `setsid` deja al demonio sin terminal de control: no puede
  tocar la terminal desde la que se lanzó la prueba.

## Qué difiere de un arranque real

| Aspecto | En el banco | En el arranque real |
|---|---|---|
| Renderer | `x11` (ventana GTK3 sobre Xvfb). | `drm` (KMS) o `frame-buffer`. |
| Presentación | GTK repinta cuando se bombea su bucle (cada 20 ms) y agrupa actualizaciones: algunos fotogramas consecutivos salen repetidos y otros saltan dos pasos. | Cada vaciado va directo al framebuffer. |
| Costo medido | Script + composición de sprites + GTK/cairo/X. | Script + composición + copia al framebuffer. La composición es el mismo código. |
| Dónde corre | Sistema ya arrancado, discos y cachés disponibles. | Initramfs y arranque temprano: CPU fría, sin caché de disco. |
| Archivos del tema | Copia completa del directorio. | Solo lo que el hook de initramfs incluya; hay que regenerar el initramfs. |
| Texto y fuentes | `label-pango.so` con todas las fuentes del sistema. La primera etiqueta tarda ~0,3–0,6 s (carga de pango/fontconfig). | En el initramfs suele haber una sola fuente y el plugin de etiquetas puede faltar: el texto puede verse distinto o no verse. |
| Progreso de arranque | No hay `boot-duration` previo ni systemd enviando estados: el progreso avanza solo por tiempo, salvo `--evento estado:...`. | Usa la duración del arranque anterior y los estados de systemd. |
| Pantallas | Una sola, del tamaño pedido, 24 bits, escala 1 (o `--escala`). | Resolución nativa, posible HiDPI y varias pantallas. |
| Teclado | No se pueden simular teclas: una clave pedida queda en pantalla hasta el final; no se prueba Escape. | Teclado real. |
| Consola | Sin VT ni tty: no hay pantalla de texto ni paso a «details». | Consola virtual real. |
| Salida | `plymouth quit` llega después de cerrar la captura: la transición final no se graba. | El splash cede al gestor de sesión. |
| Versión | La del paquete de Ubuntu de la caché (24.004.60). | La de la distribución destino. |

Conclusión práctica: el banco valida **sintaxis, lógica, composición de píxeles
y costo relativo** del tema. La fluidez exacta, el texto dentro del initramfs y
el comportamiento con varias pantallas hay que confirmarlos en un equipo real.

## Comportamientos de Plymouth verificados con el banco

Importan para escribir el tema:

- **Un error de sintaxis no detiene a Plymouth.** El plugin imprime
  `Parser error "<archivo>" L:n C:n : ...` y sigue adelante con lo que haya
  podido parsear; el resultado suele ser una pantalla negra. El banco lo
  convierte en código 12.
- **Los errores de ejecución solo se ven en el registro de depuración**
  (`Execution error ... Cannot negate non number objects`), repetidos en cada
  refresco. También dan código 12.
- **Sin ningún sprite no se pinta ni el fondo.** `script_lib_sprite_draw_area`
  retorna si la lista de sprites está vacía: un tema que solo llama a
  `Window.SetBackgroundTopColor` deja la pantalla negra (código 13).
- **Un `while` infinito cuelga a `plymouthd`** al 100 % de CPU; `show-splash` y
  `quit` dejan de responder (código 10; la prueba tarda ~1 min en rendirse).
- **Una imagen inexistente no da error.** `Image("no-existe.png")` devuelve un
  objeto vacío y el sprite no se dibuja; el veredicto sigue en OK. El banco solo
  puede avisar (`avisos`) cuando el nombre aparece literal en el script.
- **Un `.plymouth` con finales CRLF no carga el plugin:** Plymouth cae a
  `details`. El banco avisa y devuelve código 11.
- **Refresco real:** ~48–50 llamadas por segundo a la función de
  `Plymouth.SetRefreshFunction`.

## Autoprueba

`banco_plymouth.sh autoprueba` crea dos temas mínimos en su carpeta de salida y
comprueba, imprimiendo una línea `AUTOPRUEBA PASA|FALLA` por punto:

- a) el tema `script` de stock corre con renderer x11 y hay fotogramas distintos;
- b) un tema mínimo mueve un sprite de 40×40: se decodifican los PNG y se mide
  la caja del sprite en cada fotograma (tamaño, fila y cambio de `x`);
- c) un `.script` con error de sintaxis termina con código 12 e informa
  archivo, línea y columna;
- d) dos ejecuciones simultáneas, con temas y resoluciones distintas, terminan
  bien, se solapan en el tiempo y cada una ve solo lo suyo.

Devuelve 0 solo si pasan las cuatro.

## Resolución de problemas

| Síntoma | Causa y salida |
|---|---|
| `la cache no esta preparada` (código 3) | Ejecutar `preparar`. |
| `la simulacion de apt-get fallo` / falla la descarga | Índices de apt desactualizados o sin red. Actualizarlos (`sudo apt-get update`) es decisión del usuario: el banco nunca usa sudo. |
| `este sistema no permite el aislamiento sin root` | Faltan user namespaces u overlayfs sin privilegios (kernel < 5.11). En Ubuntu 24.04 **nativo**, AppArmor los restringe por defecto (`kernel.apparmor_restrict_unprivileged_userns=1`); levantarlo requiere root y queda a criterio del usuario (caso no probado aquí). En WSL2 no ocurre. |
| Código 13, todo negro | Tema sin sprites, imágenes que no cargan (`ImageDir` mal, nombre de archivo equivocado: `Image()` falla en silencio) u opacidad 0. Mirar `logs/fotogramas.csv` y `logs/plymouth-debug.log`. |
| Código 12 | Leer `errores_script` en `metricas.json`: la línea y columna indican dónde se detuvo el parser. |
| Código 11 | `ModuleName` distinto de `script`, `.plymouth` con CRLF o `--cmdline` sin `splash`. `plugin_splash` dice qué se usó. |
| Código 10 | Script colgado (bucle sin fin) o `plymouthd` caído. Ver `logs/plymouthd.stderr`. |
| `fps_captura_efectivo` menor que el pedido | Máquina saturada; bajar `--fps` o `--tamano`, o repetir. |
| Tiempos de arranque muy variables | Caché de disco fría en WSL. Repetir la prueba. |
| Rutas `/mnt/d/...` rotas desde Git Bash | Usar PowerShell o `MSYS_NO_PATHCONV=1`. |
| Quedó basura tras un corte | Los directorios de `~/.cache/paraguay-theme-rig/rig/ejecuciones/` se barren en la siguiente prueba; `limpiar --si` borra toda la caché. |

Dos tropiezos ya resueltos dentro del script, por si reaparecen en otro entorno:

- **GLX en WSL.** Con GLX activo, Xvfb demoraba 15–18 s la primera conexión de
  GTK (carga de controladores gráficos de WSL). Xvfb se lanza con
  `-extension GLX` y `LIBGL_ALWAYS_SOFTWARE=1`.
- **Marcas de tiempo de la captura.** Con la base de tiempo por defecto, ffmpeg
  fusionaba marcas de fotogramas tomados en ráfaga; se fija `-enc_time_base 1:1000`.

## Limitaciones conocidas

- Solo Debian/Ubuntu (usa `apt-get download` y `dpkg-deb`). Probado únicamente en
  WSL2 con Ubuntu 24.04; **no se probó en Linux nativo**.
- Solo arquitectura del sistema anfitrión (x86-64 aquí).
- No simula teclado ni varias pantallas.
- `/usr/lib/xorg/protocol.txt` no puede proveerse en WSL (no hay dónde montarlo);
  solo afecta a los nombres de protocolo en mensajes de error de X.
