#!/usr/bin/env bash
# banco_plymouth.sh - Banco de pruebas del Plymouth REAL, sin root y sin tocar el sistema.
#
# Ejecuta plymouthd + plugin de splash "script" + renderer x11 dentro de un juego
# privado de namespaces (usuario, montaje, red, IPC y PID), dibujando en un Xvfb
# privado. Captura fotogramas PNG y métricas (CPU, memoria, tasa de animación,
# errores del .script) para validar un tema y medir cuánto cuesta.
#
# Manual completo: docs/manuales/banco-de-pruebas.md
#
# Nota: los mensajes en tiempo de ejecución van sin tildes a propósito, para que
# no se rompan al capturarlos desde consolas de Windows con otra codificación.

set -u
set -o pipefail
export LC_ALL=C.UTF-8 LANG=C.UTF-8

readonly VERSION_BANCO="1.0"
RUTA_SCRIPT="$(readlink -f -- "${BASH_SOURCE[0]}")"
readonly RUTA_SCRIPT
DIR_REPO="$(dirname -- "$(dirname -- "$RUTA_SCRIPT")")"
readonly DIR_REPO
CACHE="${BANCO_PLYMOUTH_CACHE:-$HOME/.cache/paraguay-theme-rig/rig}"

# Paquetes que se descargan (con sus dependencias faltantes) y se extraen en la cache.
readonly PAQUETES_BASE=(plymouth plymouth-x11 plymouth-themes plymouth-label xvfb x11-xkb-utils)
readonly PANTALLA=":99"
readonly CMDLINE_POR_DEFECTO="quiet splash plymouth.ignore-serial-consoles"
readonly MODOS_VALIDOS="boot shutdown reboot updates system-upgrade firmware-upgrade system-reset"

# Códigos de salida
readonly SAL_OK=0          # todo bien
readonly SAL_ERROR=1       # error inesperado
readonly SAL_USO=2         # argumentos incorrectos
readonly SAL_ENTORNO=3     # cache sin preparar, requisitos faltantes o fallo de infraestructura
readonly SAL_DEMONIO=10    # plymouthd no arranco, murio o dejo de responder
readonly SAL_PLUGIN=11     # no se uso el plugin esperado (script) con renderer grafico (x11)
readonly SAL_SCRIPT=12     # el .script tiene errores (de parseo o de ejecucion)
readonly SAL_NEGRO=13      # no hubo fotogramas o salieron todos negros
readonly SAL_ANIMACION=14  # menos fotogramas distintos que --min-distintos

info()  { printf 'banco_plymouth: %s\n' "$*"; }
aviso() { printf 'banco_plymouth: aviso: %s\n' "$*" >&2; }
error() { printf 'banco_plymouth: error: %s\n' "$*" >&2; }
morir() { error "$1"; exit "${2:-$SAL_ERROR}"; }

ayuda() {
    cat <<'EOF'
banco_plymouth.sh - banco de pruebas del Plymouth real (plymouthd + plugin "script" +
renderer x11) aislado en namespaces sin root y dibujando en un Xvfb privado.

USO
  banco_plymouth.sh preparar [--forzar]
  banco_plymouth.sh probar <dir_tema|stock:NOMBRE> [opciones]
  banco_plymouth.sh video <DIR> [--ancho W] [--fps F] [--formato gif|mp4|ambos]
  banco_plymouth.sh estado
  banco_plymouth.sh autoprueba [--salida DIR]
  banco_plymouth.sh limpiar --si
  banco_plymouth.sh --help

SUBCOMANDOS
  preparar    Descarga con "apt-get download" (no requiere root) plymouth, sus plugins,
              Xvfb y las dependencias que falten, y los extrae con dpkg en la cache
              (~/.cache/paraguay-theme-rig/rig, o $BANCO_PLYMOUTH_CACHE). Idempotente:
              si la cache ya esta completa no descarga nada. --forzar la rehace.

  probar      Ejecuta el tema dentro del aislamiento, muestra el splash, captura
              fotogramas y escribe metricas. <dir_tema> es un directorio con
              <nombre>.plymouth + <nombre>.script + imagenes (puede estar en /mnt/d/...).
              "stock:script" prueba el tema de ejemplo que trae plymouth-themes.
      --segundos N        segundos de splash a capturar (por defecto 8; max 600)
      --tamano WxH        resolucion de la pantalla virtual (por defecto 1920x1080)
      --fps F             fotogramas por segundo de la captura (por defecto 30; max 120)
      --salida DIR        directorio de resultados
                          (por defecto <repo>/output/temporales/banco/<nombre>-<marca>/)
      --modo M            boot | shutdown | reboot | updates | system-upgrade |
                          firmware-upgrade | system-reset (por defecto boot)
      --evento T:ACCION[:ARG]   (repetible) dispara una accion a los T segundos de
                          haber mostrado el splash. Acciones:
                            mensaje:TEXTO          plymouth display-message --text=TEXTO
                            ocultar-mensaje:TEXTO  plymouth hide-message --text=TEXTO
                            clave:PROMPT           plymouth ask-for-password (sin bloquear)
                            pregunta:PROMPT        plymouth ask-question (sin bloquear)
                            progreso:NN            plymouth system-update --progress=NN
                            estado:TEXTO           plymouth update --status=TEXTO
                            modo:M                 plymouth change-mode --M (boot-up,
                                                   shutdown, reboot, updates, ...)
                            pausar | reanudar      pause-progress / unpause-progress
                            ocultar | mostrar      hide-splash / show-splash
                            desactivar | reactivar deactivate / reactivate
                            raiz-montada           update-root-fs --new-root-dir=/
                            raiz-rw                update-root-fs --read-write
                            recargar               reload
                            crudo:ARGS             plymouth ARGS (separados por espacios)
      --min-distintos N   falla (codigo 14) si hay menos de N fotogramas distintos
                          del anterior (por defecto 0: no se exige animacion)
      --plugin-esperado P plugin de splash exigido (por defecto script)
      --escala N          fuerza la escala HiDPI de plymouth (PLYMOUTH_FORCE_SCALE)
      --cmdline "..."     linea de comandos del kernel falsa para plymouthd
                          (por defecto "quiet splash plymouth.ignore-serial-consoles")
      --ajustar-rutas     reescribe ImageDir/ScriptFile en la copia de prueba si no
                          apuntan a /usr/share/plymouth/themes/<nombre>
      --sin-frames        no extrae los PNG (solo metricas)
      --conservar-captura deja DIR/captura.mkv (video sin perdida de la captura)

  video       Arma DIR/animacion.gif y/o DIR/animacion.mp4 a partir de DIR/frames.
      --ancho W           ancho de salida en pixeles (por defecto 640; 0 = original)
      --fps F             fps de salida (por defecto 25)
      --formato X         gif | mp4 | ambos (por defecto ambos)

  estado      Muestra si la cache esta preparada y con que versiones.

  autoprueba  Verifica el propio banco: (a) tema "script" de stock animado, (b) tema
              minimo cuyo sprite se mueve (analisis de pixeles), (c) .script con error
              de sintaxis => codigo != 0, (d) dos ejecuciones concurrentes aisladas.

  limpiar     Borra la cache completa. Exige --si. No borra resultados de pruebas.

RESULTADOS DE "probar" (en DIR)
  metricas.json          resolucion, renderer, plugin_splash, fotogramas_capturados,
                         fotogramas_distintos, cpu_plymouthd_pct, rss_max_plymouthd_kb,
                         errores_script, veredicto, codigo_salida y mas detalle
  frames/f_NNNNN.png     fotogramas capturados (numerados desde 1)
  logs/                  plymouth-debug.log, fotogramas.csv, muestras.csv, eventos.tsv...

CODIGOS DE SALIDA
   0  OK                        10  plymouthd no arranco / murio / no responde
   1  error inesperado          11  no se uso el plugin esperado con renderer x11
   2  argumentos incorrectos    12  errores en el .script (parseo o ejecucion)
   3  entorno o cache no listos 13  sin fotogramas o todos negros
                                14  animacion insuficiente (--min-distintos)

EJEMPLOS
  # Desde Windows (PowerShell):
  wsl -- bash /mnt/d/repos/paraguay_theme/scripts/banco_plymouth.sh preparar
  wsl -- bash /mnt/d/repos/paraguay_theme/scripts/banco_plymouth.sh probar stock:script --segundos 5
  # Desde Linux / dentro de WSL:
  scripts/banco_plymouth.sh probar tema/paraguay --segundos 10 --tamano 1920x1080 --fps 60 \
      --evento 3:mensaje:"Verificando discos" --evento 5:clave:"Clave"
  scripts/banco_plymouth.sh video output/temporales/banco/paraguay-20260101-120000-123
EOF
}

# ---------------------------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------------------------

exigir_comandos() {
    local faltan=() c
    for c in "$@"; do
        command -v "$c" >/dev/null 2>&1 || faltan+=("$c")
    done
    if [ "${#faltan[@]}" -gt 0 ]; then
        error "faltan comandos en este sistema: ${faltan[*]}"
        return 1
    fi
}

validar_ruta_cache() {
    case "$CACHE" in
        /*) ;;
        *) morir "la ruta de la cache debe ser absoluta: $CACHE" "$SAL_USO" ;;
    esac
    case "$CACHE" in
        *[:,\\\ ]*|*$'\n'*|*$'\t'*)
            morir "la ruta de la cache no puede tener ':', ',', '\\' ni espacios: $CACHE" "$SAL_USO" ;;
    esac
    case "$CACHE/" in
        /tmp/*|/run/*|/proc/*|/sys/*|/dev/*|/usr/*|/etc/*|/var/lib/plymouth/*)
            morir "la cache no puede vivir bajo /tmp, /run, /usr ni /etc (quedan tapados dentro del aislamiento): $CACHE" "$SAL_USO" ;;
    esac
}

# Bloqueo de la cache en el descriptor 9: compartido para "probar", exclusivo para
# "preparar" y "limpiar". Los procesos aislados lo heredan, asi la cache no puede
# borrarse mientras quede alguno vivo.
abrir_bloqueo() {
    mkdir -p "$CACHE" || morir "no se pudo crear la cache: $CACHE" "$SAL_ENTORNO"
    exec 9>>"$CACHE/.bloqueo" || morir "no se pudo abrir el bloqueo de la cache" "$SAL_ENTORNO"
}

cache_preparada() {
    [ -f "$CACHE/preparado.ok" ] && [ -d "$CACHE/root" ]
}

# Comprueba que el sistema deja crear los namespaces y montar overlay/tmpfs sin root.
sonda_aislamiento() {
    local d="$CACHE/.sonda.$$" salida
    mkdir -p "$d/a" "$d/b" "$d/m"
    salida=$(unshare --user --map-root-user --mount --net --ipc --pid --fork --mount-proc --kill-child \
        sh -c 'mount -t overlay overlay -o "lowerdir=$1/a:$1/b" "$1/m" && mount -t tmpfs tmpfs "$1/m" && echo SONDA_OK' sh "$d" 2>&1)
    rm -rf -- "$d"
    case "$salida" in
        *SONDA_OK*) return 0 ;;
    esac
    error "este sistema no permite el aislamiento sin root (user namespaces + overlayfs)."
    error "detalle: ${salida:-sin salida}"
    error "en Ubuntu 24.04 nativo suele deberse a kernel.apparmor_restrict_unprivileged_userns=1 (ver el manual)."
    return 1
}

# Lanza "$RUTA_SCRIPT __interno <accion> <dir>" dentro de los namespaces privados.
#   $1 = limite de tiempo total en segundos, $2 = accion, $3 = directorio de ejecucion.
# - user+mount: overlays y tmpfs que solo existen ahi dentro.
# - net: aisla los sockets abstractos (plymouthd y X11) entre ejecuciones concurrentes.
# - pid + --kill-child: si muere "unshare", el kernel mata todo lo de adentro.
# - setsid: sin terminal de control, para que plymouthd no toque la terminal del usuario.
# - env -i: entorno limpio (ni DISPLAY ni WAYLAND_DISPLAY del usuario llegan adentro).
PID_AISLADO=""
lanzar_aislado() {
    local limite="$1" accion="$2" dir="$3"
    timeout --kill-after=5 "$limite" \
        unshare --user --map-root-user --mount --net --ipc --pid --fork --mount-proc --kill-child \
        env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/nonexistent LC_ALL=C.UTF-8 LANG=C.UTF-8 \
        setsid bash "$RUTA_SCRIPT" __interno "$accion" "$dir" </dev/null &
    PID_AISLADO=$!
    wait "$PID_AISLADO"
    local rc=$?
    PID_AISLADO=""
    return "$rc"
}

DIR_EJEC=""
limpieza_salida() {
    local rc=$?
    trap - EXIT INT TERM HUP
    if [ -n "$PID_AISLADO" ] && kill -0 "$PID_AISLADO" 2>/dev/null; then
        # "timeout" lidera su propio grupo de procesos, que incluye a "unshare". Al matar
        # el grupo, el kernel mata (--kill-child + namespace de PID) todo lo de adentro.
        # (unshare bloquea SIGTERM mientras espera, por eso se usa SIGKILL.)
        kill -KILL -- "-$PID_AISLADO" 2>/dev/null || kill -TERM "$PID_AISLADO" 2>/dev/null
        wait "$PID_AISLADO" 2>/dev/null
    fi
    if [ -n "$DIR_EJEC" ] && [ -d "$DIR_EJEC" ]; then
        local i=0
        while [ "$i" -lt 10 ]; do
            rm -rf -- "$DIR_EJEC" 2>/dev/null
            [ -d "$DIR_EJEC" ] || break
            sleep 0.2
            i=$((i + 1))
        done
    fi
    exit "$rc"
}

instalar_trampas() {
    trap limpieza_salida EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM HUP
}

# Crea el directorio privado de esta ejecucion dentro de la cache (ext4, apto para
# overlay) y de paso barre los que hayan quedado de ejecuciones muertas. El archivo
# ".vivo" queda bloqueado (descriptor 8) mientras viva la ejecucion o algun proceso suyo.
crear_dir_ejecucion() {
    mkdir -p "$CACHE/ejecuciones" || morir "no se pudo crear $CACHE/ejecuciones" "$SAL_ENTORNO"
    exec 7>>"$CACHE/ejecuciones/.crear"
    flock -x 7
    local d
    for d in "$CACHE"/ejecuciones/*/; do
        [ -d "$d" ] || continue
        if ( exec 6>>"${d}.vivo" && flock -n 6 ) 2>/dev/null; then
            rm -rf -- "$d"
        fi
    done
    DIR_EJEC=$(mktemp -d "$CACHE/ejecuciones/XXXXXXXX") || morir "no se pudo crear el directorio de ejecucion" "$SAL_ENTORNO"
    exec 8>>"$DIR_EJEC/.vivo"
    flock -n 8 || morir "no se pudo bloquear el directorio de ejecucion" "$SAL_ENTORNO"
    flock -u 7
    exec 7>&-
}

escribir_config() {
    # $1 = archivo; resto = nombres de variables a volcar
    local archivo="$1" v
    shift
    : > "$archivo"
    for v in "$@"; do
        printf '%s=%q\n' "$v" "${!v}" >> "$archivo"
    done
}

# ---------------------------------------------------------------------------
# preparar
# ---------------------------------------------------------------------------

# Imprime "paquete=version" de todo lo que apt instalaria (es decir, lo que falta).
calcular_paquetes() {
    local sim
    if ! sim=$(LC_ALL=C apt-get -s install --no-install-recommends "${PAQUETES_BASE[@]}" 2>&1); then
        error "la simulacion de apt-get fallo (indices desactualizados o paquetes inexistentes?):"
        printf '%s\n' "$sim" | tail -n 15 >&2
        return 1
    fi
    printf '%s\n' "$sim" | sed -n 's/^Inst \([^ ]*\) \(\[[^]]*\] \)\{0,1\}(\([^ ]*\) .*/\1=\3/p' | sort
}

verificar_cache() {
    # Corre la verificacion dentro del aislamiento (ahi se ven los archivos de la cache).
    local d rc
    d=$(mktemp -d "$CACHE/.verificar.XXXXXX") || return 1
    mkdir -p "$d/capa" "$d/logs"
    escribir_config "$d/config.sh" CACHE
    lanzar_aislado 120 verificar "$d"
    rc=$?
    rm -rf -- "$d"
    return "$rc"
}

cmd_preparar() {
    local forzar=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --forzar) forzar=1; shift ;;
            -h|--help) ayuda; exit 0 ;;
            *) morir "opcion desconocida para preparar: $1" "$SAL_USO" ;;
        esac
    done
    validar_ruta_cache
    exigir_comandos unshare flock setsid timeout apt-get dpkg-deb ffmpeg ffprobe python3 awk sed find getconf \
        || exit "$SAL_ENTORNO"
    abrir_bloqueo
    if ! flock -n -x 9; then
        info "hay pruebas en curso; esperando el bloqueo exclusivo de la cache..."
        flock -x -w 900 9 || morir "no se pudo tomar el bloqueo de la cache" "$SAL_ENTORNO"
    fi
    instalar_trampas
    sonda_aislamiento || exit "$SAL_ENTORNO"

    local lista
    lista=$(calcular_paquetes) || exit "$SAL_ENTORNO"

    if [ "$forzar" = 0 ] && cache_preparada && [ "$(cat "$CACHE/paquetes.txt" 2>/dev/null)" = "$lista" ]; then
        if verificar_cache > "$CACHE/verificacion.log" 2>&1; then
            info "la cache ya estaba preparada: $CACHE"
            sed 's/^/banco_plymouth:   /' "$CACHE/verificacion.log"
            return 0
        fi
        aviso "la cache existe pero no pasa la verificacion; se rehace"
    fi

    rm -f "$CACHE/preparado.ok"
    rm -rf -- "$CACHE/root.tmp"
    mkdir -p "$CACHE/debs" "$CACHE/root.tmp" || morir "no se pudo escribir en la cache" "$SAL_ENTORNO"
    : > "$CACHE/.banco-plymouth-cache"

    local -a paquetes=()
    local p
    while IFS= read -r p; do
        [ -n "$p" ] && paquetes+=("$p")
    done <<< "$lista"

    if [ "${#paquetes[@]}" -gt 0 ]; then
        info "descargando ${#paquetes[@]} paquetes con apt-get download (sin root) en $CACHE/debs"
        if ! ( cd "$CACHE/debs" && apt-get download "${paquetes[@]}" ) > "$CACHE/descarga.log" 2>&1; then
            error "fallo la descarga (ver $CACHE/descarga.log):"
            tail -n 15 "$CACHE/descarga.log" >&2
            exit "$SAL_ENTORNO"
        fi
        local deb id extraidos=0
        for deb in "$CACHE"/debs/*.deb; do
            [ -f "$deb" ] || continue
            id="$(dpkg-deb -f "$deb" Package)=$(dpkg-deb -f "$deb" Version)"
            if grep -qxF -- "$id" <<< "$lista"; then
                dpkg-deb -x "$deb" "$CACHE/root.tmp" || morir "no se pudo extraer $deb" "$SAL_ENTORNO"
                extraidos=$((extraidos + 1))
            fi
        done
        if [ "$extraidos" -ne "${#paquetes[@]}" ]; then
            morir "se esperaban ${#paquetes[@]} paquetes y se extrajeron $extraidos (ver $CACHE/descarga.log)" "$SAL_ENTORNO"
        fi
        info "extraidos $extraidos paquetes"
    else
        info "el sistema ya tiene instalado todo lo necesario; no se descarga nada"
    fi

    # Paquetes sin "usrmerge": se llevan /bin, /sbin y /lib* a /usr para montar solo /usr.
    local d
    for d in bin sbin lib lib32 lib64 libx32; do
        if [ -d "$CACHE/root.tmp/$d" ] && [ ! -L "$CACHE/root.tmp/$d" ]; then
            mkdir -p "$CACHE/root.tmp/usr/$d"
            cp -a "$CACHE/root.tmp/$d/." "$CACHE/root.tmp/usr/$d/" && rm -rf -- "$CACHE/root.tmp/$d"
        fi
    done
    mkdir -p "$CACHE/root.tmp/usr" "$CACHE/root.tmp/etc" "$CACHE/root.tmp/var"

    rm -rf -- "$CACHE/root"
    mv "$CACHE/root.tmp" "$CACHE/root" || morir "no se pudo dejar la raiz extraida en su lugar" "$SAL_ENTORNO"
    printf '%s\n' "$lista" > "$CACHE/paquetes.txt"

    if ! verificar_cache > "$CACHE/verificacion.log" 2>&1; then
        error "la verificacion dentro del aislamiento fallo:"
        cat "$CACHE/verificacion.log" >&2
        exit "$SAL_ENTORNO"
    fi
    date -u +%Y-%m-%dT%H:%M:%SZ > "$CACHE/preparado.ok"
    info "cache preparada en $CACHE ($(du -sh "$CACHE" 2>/dev/null | cut -f1))"
    sed 's/^/banco_plymouth:   /' "$CACHE/verificacion.log"
}

cmd_estado() {
    validar_ruta_cache
    info "version del banco: $VERSION_BANCO"
    info "cache: $CACHE"
    if cache_preparada; then
        info "estado: preparada el $(cat "$CACHE/preparado.ok")"
        info "paquetes extraidos:"
        sed 's/^/banco_plymouth:   /' "$CACHE/paquetes.txt"
        [ -f "$CACHE/verificacion.log" ] && sed 's/^/banco_plymouth:   /' "$CACHE/verificacion.log"
        info "temas de stock: $(find "$CACHE/root/usr/share/plymouth/themes" -mindepth 1 -maxdepth 1 -type d -printf '%f ' 2>/dev/null)"
        return 0
    fi
    info "estado: SIN PREPARAR (ejecute: $(basename "$RUTA_SCRIPT") preparar)"
    return "$SAL_ENTORNO"
}

cmd_limpiar() {
    local si=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --si) si=1; shift ;;
            -h|--help) ayuda; exit 0 ;;
            *) morir "opcion desconocida para limpiar: $1" "$SAL_USO" ;;
        esac
    done
    validar_ruta_cache
    [ "$si" = 1 ] || morir "limpiar borra por completo $CACHE; repita con --si para confirmar" "$SAL_USO"
    if [ ! -d "$CACHE" ]; then
        info "no hay cache que limpiar ($CACHE)"
        return 0
    fi
    [ -f "$CACHE/.banco-plymouth-cache" ] || [ -z "$(ls -A "$CACHE" 2>/dev/null | grep -v '^\.bloqueo$')" ] \
        || morir "$CACHE no parece una cache de este banco (falta .banco-plymouth-cache); no se borra" "$SAL_ERROR"
    abrir_bloqueo
    flock -n -x 9 || morir "hay pruebas o una preparacion en curso; no se limpia" "$SAL_ERROR"
    rm -rf -- "$CACHE" || morir "no se pudo borrar $CACHE" "$SAL_ERROR"
    info "cache borrada: $CACHE"
}

# ---------------------------------------------------------------------------
# probar (lado de afuera)
# ---------------------------------------------------------------------------

EVENTOS=()
agregar_evento() {
    local spec="$1" t resto accion arg=""
    t="${spec%%:*}"
    resto="${spec#*:}"
    [ "$resto" != "$spec" ] || morir "evento mal formado (se espera T:ACCION[:ARG]): $spec" "$SAL_USO"
    accion="${resto%%:*}"
    if [ "$accion" != "$resto" ]; then
        arg="${resto#*:}"
    fi
    [[ "$t" =~ ^[0-9]+([.][0-9]+)?$ ]] || morir "el tiempo del evento debe ser un numero de segundos: $spec" "$SAL_USO"
    case "$accion" in
        mensaje|ocultar-mensaje|clave|pregunta|progreso|estado|modo|crudo)
            [ -n "$arg" ] || morir "el evento '$accion' necesita un argumento: $spec" "$SAL_USO" ;;
        pausar|reanudar|ocultar|mostrar|desactivar|reactivar|raiz-montada|raiz-rw|recargar) ;;
        *) morir "accion de evento desconocida: '$accion' (ver --help)" "$SAL_USO" ;;
    esac
    case "$arg" in
        *$'\t'*|*$'\n'*) morir "el argumento del evento no puede tener tabuladores ni saltos de linea" "$SAL_USO" ;;
    esac
    EVENTOS+=("$t"$'\t'"$accion"$'\t'"$arg")
}

# Lee una clave de un archivo .plymouth (formato INI simple).
clave_ini() {
    sed -n "s/^[[:space:]]*$2[[:space:]]*=[[:space:]]*//p" "$1" | head -n 1 | tr -d '\r' | sed 's/[[:space:]]*$//'
}

normalizar_ruta() {
    printf '%s' "$1" | sed 's|//*|/|g; s|/$||'
}

cmd_probar() {
    local tema_arg="" SEGUNDOS=8 TAMANO=1920x1080 FPS=30 SALIDA="" MODO=boot MIN_DISTINTOS=0
    local PLUGIN_ESPERADO=script ESCALA="" CMDLINE="$CMDLINE_POR_DEFECTO" ajustar_rutas=0 sin_frames=0 conservar=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --*=*) set -- "${1%%=*}" "${1#*=}" "${@:2}"; continue ;;
            -h|--help) ayuda; exit 0 ;;
            --ajustar-rutas) ajustar_rutas=1; shift; continue ;;
            --sin-frames) sin_frames=1; shift; continue ;;
            --conservar-captura) conservar=1; shift; continue ;;
            --segundos|--tamano|--fps|--salida|--modo|--evento|--min-distintos|--plugin-esperado|--escala|--cmdline)
                [ $# -ge 2 ] || morir "falta el valor de $1" "$SAL_USO" ;;
            --*) morir "opcion desconocida para probar: $1" "$SAL_USO" ;;
            *)
                [ -z "$tema_arg" ] || morir "sobra un argumento: $1" "$SAL_USO"
                tema_arg="$1"; shift; continue ;;
        esac
        case "$1" in
            --segundos) SEGUNDOS="$2" ;;
            --tamano) TAMANO="$2" ;;
            --fps) FPS="$2" ;;
            --salida) SALIDA="$2" ;;
            --modo) MODO="$2" ;;
            --evento) agregar_evento "$2" ;;
            --min-distintos) MIN_DISTINTOS="$2" ;;
            --plugin-esperado) PLUGIN_ESPERADO="$2" ;;
            --escala) ESCALA="$2" ;;
            --cmdline) CMDLINE="$2" ;;
        esac
        shift 2
    done

    [ -n "$tema_arg" ] || morir "falta <dir_tema> (ver --help)" "$SAL_USO"
    [[ "$SEGUNDOS" =~ ^[0-9]+([.][0-9]+)?$ ]] || morir "--segundos debe ser un numero: $SEGUNDOS" "$SAL_USO"
    awk -v s="$SEGUNDOS" 'BEGIN { exit (s > 0 && s <= 600) ? 0 : 1 }' || morir "--segundos debe estar entre 0 y 600" "$SAL_USO"
    [[ "$TAMANO" =~ ^([0-9]+)x([0-9]+)$ ]] || morir "--tamano debe tener la forma WxH: $TAMANO" "$SAL_USO"
    local ANCHO="${BASH_REMATCH[1]}" ALTO="${BASH_REMATCH[2]}"
    { [ "$ANCHO" -ge 64 ] && [ "$ANCHO" -le 7680 ] && [ "$ALTO" -ge 64 ] && [ "$ALTO" -le 4320 ]; } \
        || morir "--tamano fuera de rango (64x64 a 7680x4320): $TAMANO" "$SAL_USO"
    { [[ "$FPS" =~ ^[0-9]+$ ]] && [ "$FPS" -ge 1 ] && [ "$FPS" -le 120 ]; } || morir "--fps debe ser un entero entre 1 y 120" "$SAL_USO"
    [[ "$MIN_DISTINTOS" =~ ^[0-9]+$ ]] || morir "--min-distintos debe ser un entero" "$SAL_USO"
    [[ "$PLUGIN_ESPERADO" =~ ^[A-Za-z0-9_-]+$ ]] || morir "--plugin-esperado invalido" "$SAL_USO"
    [ -z "$ESCALA" ] || [[ "$ESCALA" =~ ^[1-4]$ ]] || morir "--escala debe ser un entero de 1 a 4" "$SAL_USO"
    case " $MODOS_VALIDOS " in
        *" $MODO "*) ;;
        *) morir "--modo invalido: $MODO (validos: $MODOS_VALIDOS)" "$SAL_USO" ;;
    esac
    case "$CMDLINE" in
        *$'\n'*) morir "--cmdline no puede tener saltos de linea" "$SAL_USO" ;;
    esac

    validar_ruta_cache
    exigir_comandos unshare flock setsid timeout ffmpeg ffprobe python3 awk sed find getconf || exit "$SAL_ENTORNO"
    cache_preparada || morir "la cache no esta preparada; ejecute primero: $(basename "$RUTA_SCRIPT") preparar" "$SAL_ENTORNO"

    # --- tema bajo prueba
    local DIR_TEMA ORIGEN_TEMA
    case "$tema_arg" in
        stock:*)
            DIR_TEMA="$CACHE/root/usr/share/plymouth/themes/${tema_arg#stock:}"
            ORIGEN_TEMA="$tema_arg"
            [ -d "$DIR_TEMA" ] || morir "no existe el tema de stock '${tema_arg#stock:}' en la cache" "$SAL_USO" ;;
        *)
            [ -d "$tema_arg" ] || morir "no existe el directorio del tema: $tema_arg" "$SAL_USO"
            DIR_TEMA="$(readlink -f -- "$tema_arg")"
            ORIGEN_TEMA="$DIR_TEMA" ;;
    esac
    local -a defs=()
    local f
    for f in "$DIR_TEMA"/*.plymouth; do
        [ -f "$f" ] && defs+=("$f")
    done
    [ "${#defs[@]}" -gt 0 ] || morir "no hay ningun archivo .plymouth en $DIR_TEMA" "$SAL_USO"
    local DEF="${defs[0]}"
    if [ "${#defs[@]}" -gt 1 ]; then
        DEF="$DIR_TEMA/$(basename "$DIR_TEMA").plymouth"
        [ -f "$DEF" ] || morir "hay varios .plymouth en $DIR_TEMA y ninguno se llama como el directorio" "$SAL_USO"
    fi
    local TEMA
    TEMA="$(basename "$DEF" .plymouth)"
    [[ "$TEMA" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || morir "nombre de tema no admitido: '$TEMA'" "$SAL_USO"
    local MODULO IMAGEDIR SCRIPTFILE DESTINO="/usr/share/plymouth/themes/$TEMA"
    MODULO="$(clave_ini "$DEF" ModuleName)"
    IMAGEDIR="$(normalizar_ruta "$(clave_ini "$DEF" ImageDir)")"
    SCRIPTFILE="$(normalizar_ruta "$(clave_ini "$DEF" ScriptFile)")"
    [ -n "$MODULO" ] || morir "$DEF no declara ModuleName" "$SAL_USO"
    local tam_mb
    tam_mb=$(du -sm -- "$DIR_TEMA" 2>/dev/null | cut -f1)
    [ "${tam_mb:-0}" -le 512 ] || morir "el directorio del tema pesa ${tam_mb} MB; no parece un tema" "$SAL_USO"

    if [ "$MODULO" = script ]; then
        local rutas_mal=0
        [ "$IMAGEDIR" = "$DESTINO" ] || rutas_mal=1
        case "$SCRIPTFILE" in
            "$DESTINO"/*) ;;
            *) rutas_mal=1 ;;
        esac
        if [ "$rutas_mal" = 1 ] && [ "$ajustar_rutas" = 0 ]; then
            error "$(basename "$DEF") debe apuntar a donde se instala el tema:"
            error "  ImageDir=$DESTINO            (ahora: '${IMAGEDIR}')"
            error "  ScriptFile=$DESTINO/$TEMA.script  (ahora: '${SCRIPTFILE}')"
            error "corrija el .plymouth o use --ajustar-rutas para reescribirlo solo en la copia de prueba."
            exit "$SAL_USO"
        fi
    fi

    # --- salida
    if [ -z "$SALIDA" ]; then
        SALIDA="$DIR_REPO/output/temporales/banco/$TEMA-$(date +%Y%m%d-%H%M%S)-$$"
    fi
    mkdir -p "$SALIDA/frames" "$SALIDA/logs" || morir "no se pudo crear el directorio de salida: $SALIDA" "$SAL_ERROR"
    SALIDA="$(readlink -f -- "$SALIDA")"
    # Restos de una prueba anterior en el mismo directorio (solo lo que escribe el banco).
    find "$SALIDA/frames" -maxdepth 1 -type f -name 'f_*.png' -delete 2>/dev/null
    find "$SALIDA/logs" -maxdepth 1 -type f \( -name '*.log' -o -name '*.csv' -o -name '*.tsv' \
        -o -name 'plymouthd.std*' -o -name 'tema-probado.plymouth' \) -delete 2>/dev/null
    rm -f "$SALIDA/metricas.json" "$SALIDA/captura.mkv"

    # --- codec sin perdida para la captura intermedia
    local CODEC_CAPTURA codecs
    codecs=$(ffmpeg -hide_banner -encoders 2>/dev/null)
    if grep -q ' libx264rgb ' <<< "$codecs"; then
        CODEC_CAPTURA="libx264rgb -preset ultrafast -qp 0"
    elif grep -q ' ffv1 ' <<< "$codecs"; then
        CODEC_CAPTURA="ffv1"
    else
        CODEC_CAPTURA="huffyuv"
    fi
    ffmpeg -hide_banner -devices 2>/dev/null | grep -q x11grab || morir "este ffmpeg no trae el dispositivo x11grab" "$SAL_ENTORNO"

    abrir_bloqueo
    flock -s -w 900 9 || morir "no se pudo tomar el bloqueo de la cache (preparar/limpiar en curso?)" "$SAL_ENTORNO"
    cache_preparada || morir "la cache dejo de estar preparada; ejecute preparar" "$SAL_ENTORNO"
    instalar_trampas
    crear_dir_ejecucion

    # --- capa propia de esta ejecucion: el tema instalado y plymouthd.conf
    local capa="$DIR_EJEC/capa"
    mkdir -p "$capa/usr/share/plymouth/themes/$TEMA" "$capa/etc/plymouth" "$capa/var" "$DIR_EJEC/logs"
    cp -rL -- "$DIR_TEMA/." "$capa/usr/share/plymouth/themes/$TEMA/" || morir "no se pudo copiar el tema" "$SAL_ERROR"
    chmod -R u+rwX,go+rX "$capa/usr/share/plymouth/themes/$TEMA" 2>/dev/null
    local def_copia="$capa/usr/share/plymouth/themes/$TEMA/$TEMA.plymouth"
    # Los finales de linea CRLF no se corrigen (romperian el tema instalado de verdad):
    # se anotan y el analisis los informa como aviso.
    local con_crlf
    con_crlf=$(grep -l $'\r' "$capa/usr/share/plymouth/themes/$TEMA"/*.plymouth "$capa/usr/share/plymouth/themes/$TEMA"/*.script 2>/dev/null | sed 's|.*/||' | tr '\n' ' ')
    if [ "$MODULO" = script ] && [ "$ajustar_rutas" = 1 ]; then
        sed -i -e "s|^[[:space:]]*ImageDir[[:space:]]*=.*|ImageDir=$DESTINO|" \
               -e "s|^[[:space:]]*ScriptFile[[:space:]]*=.*|ScriptFile=$DESTINO/$TEMA.script|" "$def_copia"
        SCRIPTFILE="$DESTINO/$TEMA.script"
        aviso "ImageDir/ScriptFile reescritos en la copia de prueba (--ajustar-rutas)"
    fi
    if [ "$MODULO" = script ] && [ ! -f "$capa$SCRIPTFILE" ]; then
        morir "no existe el script declarado en ScriptFile: $SCRIPTFILE" "$SAL_USO"
    fi
    cat > "$capa/etc/plymouth/plymouthd.conf" <<EOF
[Daemon]
Theme=$TEMA
ShowDelay=0
DeviceTimeout=1
EOF
    if [ "${#EVENTOS[@]}" -gt 0 ]; then
        printf '%s\n' "${EVENTOS[@]}" | sort -t$'\t' -k1,1n -s > "$DIR_EJEC/eventos.tsv"
    else
        : > "$DIR_EJEC/eventos.tsv"
    fi
    escribir_config "$DIR_EJEC/config.sh" CACHE TEMA ANCHO ALTO FPS SEGUNDOS MODO CMDLINE ESCALA CODEC_CAPTURA
    {
        printf 'tema=%s\n' "$TEMA"
        printf 'origen=%s\n' "$ORIGEN_TEMA"
        printf 'modulo_declarado=%s\n' "$MODULO"
        printf 'ancho=%s\nalto=%s\nfps=%s\nsegundos=%s\nmodo=%s\n' "$ANCHO" "$ALTO" "$FPS" "$SEGUNDOS" "$MODO"
        printf 'cmdline=%s\n' "$CMDLINE"
        printf 'escala=%s\n' "$ESCALA"
        printf 'min_distintos=%s\n' "$MIN_DISTINTOS"
        printf 'plugin_esperado=%s\n' "$PLUGIN_ESPERADO"
        printf 'codec_captura=%s\n' "$CODEC_CAPTURA"
        printf 'version_banco=%s\n' "$VERSION_BANCO"
        printf 'paquete_plymouth=%s\n' "$(sed -n 's/^plymouth=//p' "$CACHE/paquetes.txt" 2>/dev/null)"
        printf 'scriptfile=%s\n' "$([ "$MODULO" = script ] && printf '%s' "$SCRIPTFILE")"
        printf 'archivos_crlf=%s\n' "$con_crlf"
    } > "$DIR_EJEC/parametros.env"

    info "tema '$TEMA' ($ORIGEN_TEMA), modo $MODO, ${ANCHO}x${ALTO}, ${SEGUNDOS} s, captura a $FPS fps"

    # --- ejecucion aislada
    local limite rc_interno
    limite=$(awk -v s="$SEGUNDOS" 'BEGIN { printf "%d", s + 180 }')
    lanzar_aislado "$limite" probar "$DIR_EJEC"
    rc_interno=$?

    cp -f "$DIR_EJEC"/logs/* "$SALIDA/logs/" 2>/dev/null
    cp -f "$def_copia" "$SALIDA/logs/tema-probado.plymouth" 2>/dev/null

    # --- fotogramas PNG a partir de la captura sin perdida
    if [ "$sin_frames" = 0 ] && [ -s "$DIR_EJEC/captura.mkv" ]; then
        ffmpeg -nostdin -hide_banner -loglevel error -i "$DIR_EJEC/captura.mkv" -fps_mode passthrough \
            -enc_time_base 1:1000 "$SALIDA/frames/f_%05d.png" > "$SALIDA/logs/ffmpeg-frames.log" 2>&1 \
            || aviso "ffmpeg no pudo extraer todos los PNG (ver logs/ffmpeg-frames.log)"
    fi

    # --- analisis y metricas
    local rc
    BANCO_RC_INTERNO="$rc_interno" analizar "$DIR_EJEC" "$SALIDA"
    rc=$?
    if [ "$conservar" = 1 ] && [ -s "$DIR_EJEC/captura.mkv" ]; then
        cp -f "$DIR_EJEC/captura.mkv" "$SALIDA/captura.mkv"
    fi
    info "salida: $SALIDA"
    exit "$rc"
}

# Analiza la captura y los registros, escribe metricas.json y devuelve el codigo final.
analizar() {
    python3 - "$1" "$2" <<'PYEOF'
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time

dir_ejec, dir_salida = sys.argv[1], sys.argv[2]
SAL_OK, SAL_ENTORNO, SAL_DEMONIO, SAL_PLUGIN, SAL_SCRIPT, SAL_NEGRO, SAL_ANIMACION = 0, 3, 10, 11, 12, 13, 14


def leer_kv(ruta):
    datos = {}
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            for linea in f:
                linea = linea.rstrip("\n")
                if "=" in linea:
                    k, v = linea.split("=", 1)
                    datos[k] = v
    except OSError:
        pass
    return datos


def leer_texto(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def num(d, clave, tipo=float):
    try:
        return tipo(d[clave])
    except (KeyError, ValueError):
        return None


med = leer_kv(os.path.join(dir_ejec, "medidas.env"))
par = leer_kv(os.path.join(dir_ejec, "parametros.env"))
ancho, alto = int(par["ancho"]), int(par["alto"])
fps, segundos = float(par["fps"]), float(par["segundos"])
rc_interno = int(os.environ.get("BANCO_RC_INTERNO", "0") or 0)
problemas = []  # pares (codigo, texto), en orden de gravedad


def problema(codigo, texto):
    problemas.append((codigo, texto))


# ---- registros de plymouthd -------------------------------------------------
debug = leer_texto(os.path.join(dir_salida, "logs", "plymouth-debug.log"))
stderr = leer_texto(os.path.join(dir_salida, "logs", "plymouthd.stderr"))
renderers = re.findall(r"opened renderer plugin \S*/renderers/([\w-]+)\.so", debug)
# Las trazas llevan el archivo fuente que las emite (recortado a un ancho fijo); cualquier
# traza salida de src/plugins/splash/<nombre>/ delata al plugin que esta trabajando.
plugins = re.findall(r"src/plugins/splash/([\w-]+)/", debug)
pantallas = re.findall(r"adding (\d+)x(\d+) pixel display", debug)
renderer = renderers[-1] if renderers else None
plugin = plugins[-1] if plugins else None
resolucion = "%sx%s" % pantallas[-1] if pantallas else None

errores = {}
patron_pos = re.compile(r'"([^"]*)" L:(\d+) C:(\d+) : (.*)')
for linea in (debug + "\n" + stderr).splitlines():
    l = linea.strip()
    if l.startswith("Parser error"):
        tipo = "parseo"
    elif "Execution error" in l:
        tipo = "ejecucion"
        l = l[l.index("Execution error"):]
    else:
        continue
    if l in errores:
        errores[l]["veces"] += 1
        continue
    e = {"tipo": tipo, "mensaje": l, "veces": 1}
    m = patron_pos.search(l)
    if m:
        e.update(archivo=m.group(1), linea=int(m.group(2)), columna=int(m.group(3)), detalle=m.group(4))
    errores[l] = e
errores_script = list(errores.values())[:100]

# ---- revision estatica barata del tema (solo avisa) ------------------------------
# Image("archivo") con un archivo inexistente NO da error en Plymouth: el sprite
# simplemente no se dibuja. Se buscan los nombres literales y se comprueba que existan.
avisos = []
imagenes_faltantes = []
if par.get("scriptfile"):
    copia_tema = os.path.join(dir_ejec, "capa", "usr", "share", "plymouth", "themes", par.get("tema", ""))
    fuente = leer_texto(os.path.join(dir_ejec, "capa") + par["scriptfile"])
    for nombre in sorted(set(re.findall(r'\bImage\s*\(\s*"([^"]+)"\s*\)', fuente))):
        if "://" in nombre:
            continue  # p. ej. "special://logo", que resuelve el propio Plymouth
        if not os.path.isfile(os.path.join(copia_tema, nombre)):
            imagenes_faltantes.append(nombre)
    if imagenes_faltantes:
        avisos.append("el script cita imagenes que no estan en el tema (Plymouth no avisa, solo no las dibuja): "
                      + ", ".join(imagenes_faltantes))
if par.get("archivos_crlf", "").strip():
    avisos.append("archivos con finales de linea CRLF (deben ser LF): " + par["archivos_crlf"].strip())


# ---- fotogramas ---------------------------------------------------------------
def analizar_captura(captura, ruta_csv):
    r = {
        "capturados": 0, "distintos": 0, "unicos": 0, "no_negros": 0,
        "primer_no_negro": None, "primer_cambio": None, "duracion_s": 0.0,
        "bbox_union": None, "fraccion_no_negra_media": 0.0, "pts": [],
    }
    if not os.path.isfile(captura) or os.path.getsize(captura) == 0:
        return r
    pts = []
    try:
        salida = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "packet=pts_time", "-of", "csv=p=0", captura],
            capture_output=True, text=True, timeout=300).stdout
        for campo in salida.split():
            campo = campo.split(",")[0]
            try:
                pts.append(float(campo))
            except ValueError:
                pass
        pts.sort()
    except (OSError, subprocess.SubprocessError):
        pts = []
    tam, fila = ancho * alto * 3, ancho * 3
    fila_negra = bytes(fila)
    registro = open(os.path.join(dir_salida, "logs", "ffmpeg-analisis.log"), "w")
    proc = subprocess.Popen(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", captura, "-fps_mode", "passthrough",
         "-enc_time_base", "1:1000", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE, stderr=registro)
    previo = None
    unicos = set()
    suma_frac = 0.0
    union = None
    n = 0
    with open(ruta_csv, "w", newline="") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(["n", "pts_s", "cambio", "fraccion_no_negra", "bbox_x0", "bbox_y0", "bbox_x1",
                    "bbox_y1", "filas_cambiadas", "cambio_y0", "cambio_y1"])
        while True:
            buf = proc.stdout.read(tam)
            if len(buf) < tam:
                break
            n += 1
            t = pts[n - 1] - pts[0] if len(pts) >= n else (n - 1) / fps
            cambio = previo is not None and buf != previo
            ceros = buf.count(0)
            frac = 1.0 - ceros / tam
            suma_frac += frac
            unicos.add(hashlib.blake2b(buf, digest_size=8).digest())
            bbox = ("", "", "", "")
            if ceros != tam:
                r["no_negros"] += 1
                if r["primer_no_negro"] is None:
                    r["primer_no_negro"] = n
                y0 = 0
                while buf[y0 * fila:(y0 + 1) * fila] == fila_negra:
                    y0 += 1
                y1 = alto - 1
                while buf[y1 * fila:(y1 + 1) * fila] == fila_negra:
                    y1 -= 1
                x0, x1 = ancho, -1
                for y in range(y0, y1 + 1):
                    tramo = buf[y * fila:(y + 1) * fila]
                    if tramo == fila_negra:
                        continue
                    a = (fila - len(tramo.lstrip(b"\0"))) // 3
                    b = (len(tramo.rstrip(b"\0")) - 1) // 3
                    if a < x0:
                        x0 = a
                    if b > x1:
                        x1 = b
                    if x0 == 0 and x1 == ancho - 1:
                        break
                bbox = (x0, y0, x1, y1)
                if union is None:
                    union = list(bbox)
                else:
                    union = [min(union[0], x0), min(union[1], y0), max(union[2], x1), max(union[3], y1)]
            filas_cambiadas, cy0, cy1 = 0, "", ""
            if cambio:
                r["distintos"] += 1
                if r["primer_cambio"] is None:
                    r["primer_cambio"] = n
                for y in range(alto):
                    a = y * fila
                    if buf[a:a + fila] != previo[a:a + fila]:
                        filas_cambiadas += 1
                        if cy0 == "":
                            cy0 = y
                        cy1 = y
            w.writerow([n, "%.4f" % t, int(cambio), "%.6f" % frac, *bbox, filas_cambiadas, cy0, cy1])
            previo = buf
    proc.stdout.close()
    proc.wait()
    registro.close()
    r["capturados"] = n
    r["unicos"] = len(unicos)
    r["bbox_union"] = union
    r["fraccion_no_negra_media"] = suma_frac / n if n else 0.0
    if n:
        r["duracion_s"] = (pts[n - 1] - pts[0] if len(pts) >= n else (n - 1) / fps) + 1.0 / fps
    r["pts"] = [p - pts[0] for p in pts[:n]] if len(pts) >= n else [i / fps for i in range(n)]
    return r


t_ini = time.time()
fot = analizar_captura(os.path.join(dir_ejec, "captura.mkv"), os.path.join(dir_salida, "logs", "fotogramas.csv"))
t_analisis = time.time() - t_ini

tasa_animacion = None
if fot["primer_cambio"] is not None and fot["capturados"] > fot["primer_cambio"]:
    pts = fot["pts"]
    lapso = pts[-1] - pts[fot["primer_cambio"] - 2] if fot["primer_cambio"] >= 2 else pts[-1]
    if lapso > 0:
        tasa_animacion = round(fot["distintos"] / lapso, 2)

# ---- CPU y memoria -----------------------------------------------------------
tck = num(med, "clk_tck") or 100.0


def pct(prefijo):
    t0, t1 = num(med, "t_cpu_0"), num(med, "t_cpu_1")
    u0, s0 = num(med, prefijo + "_utime_0"), num(med, prefijo + "_stime_0")
    u1, s1 = num(med, prefijo + "_utime_1"), num(med, prefijo + "_stime_1")
    if None in (t0, t1, u0, s0, u1, s1) or t1 <= t0:
        return None, None, None
    dt = t1 - t0
    return (round(100.0 * (u1 + s1 - u0 - s0) / tck / dt, 2),
            round(100.0 * (u1 - u0) / tck / dt, 2),
            round(100.0 * (s1 - s0) / tck / dt, 2))


cpu_ply, cpu_ply_usr, cpu_ply_sis = pct("ply")
cpu_xvfb, _, _ = pct("xvfb")


def resta(a, b):
    x, y = num(med, a), num(med, b)
    return round(x - y, 3) if x is not None and y is not None else None


ticks_arranque = num(med, "ply_ticks_tras_show")
eventos = []
for linea in leer_texto(os.path.join(dir_salida, "logs", "eventos.tsv")).splitlines():
    campos = linea.split("\t")
    if len(campos) >= 5:
        t_show = num(med, "t_show_fin")
        try:
            t_real = round(float(campos[0]) - t_show, 3) if t_show else None
            duracion = round(float(campos[1]) - float(campos[0]), 3)
        except ValueError:
            t_real = duracion = None
        eventos.append({"t_pedido_s": float(campos[2]), "t_real_s": t_real, "duracion_s": duracion,
                        "rc": campos[3], "orden": campos[4]})

# ---- veredicto -----------------------------------------------------------------
arranco = med.get("arranco") == "1"
vivo = med.get("vivo_al_final") == "1"
if rc_interno not in (0,) and "arranco" not in med:
    problema(SAL_ENTORNO, "fallo la infraestructura del aislamiento (codigo %d; ver logs/banco-interno.log)" % rc_interno)
elif not arranco:
    problema(SAL_DEMONIO, "plymouthd no arranco o no respondio al ping (ver logs/plymouthd.stderr y plymouth-debug.log)")
else:
    if med.get("show_rc") not in ("0", None):
        problema(SAL_DEMONIO, "'plymouth show-splash' fallo o no respondio (rc=%s)" % med.get("show_rc"))
    if not vivo:
        problema(SAL_DEMONIO, "plymouthd murio durante la prueba (codigo %s)" % med.get("codigo_salida_plymouthd"))
    elif med.get("termino_limpio") == "0":
        problema(SAL_DEMONIO, "plymouthd no respondio a 'plymouth quit' y hubo que matarlo (script colgado?)")
    if not debug.strip():
        problema(SAL_DEMONIO, "plymouthd no llego a escribir su registro de depuracion (colgado o muerto antes de tiempo)")
    else:
        if renderer != "x11":
            problema(SAL_PLUGIN, "no se uso el renderer grafico x11 (usado: %s)" % renderer)
        if plugin != par.get("plugin_esperado"):
            problema(SAL_PLUGIN, "no se uso el plugin de splash '%s' (usado: %s)" % (par.get("plugin_esperado"), plugin))
    if errores_script:
        for e in errores_script[:10]:
            problema(SAL_SCRIPT, "error de %s en el script: %s" % (e["tipo"], e["mensaje"]))
    if fot["capturados"] == 0:
        problema(SAL_NEGRO, "no se capturo ningun fotograma (ver logs/ffmpeg-captura.log)")
    elif fot["no_negros"] == 0:
        problema(SAL_NEGRO, "los %d fotogramas capturados son completamente negros" % fot["capturados"])
    min_dist = int(par.get("min_distintos") or 0)
    if fot["capturados"] and fot["distintos"] < min_dist:
        problema(SAL_ANIMACION, "solo %d fotogramas distintos del anterior (se exigian %d)" % (fot["distintos"], min_dist))

codigo = problemas[0][0] if problemas else SAL_OK
veredicto = "OK" if codigo == SAL_OK else "FALLA"

metricas = {
    "banco_version": par.get("version_banco"),
    "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "veredicto": veredicto,
    "codigo_salida": codigo,
    "problemas": [p[1] for p in problemas],
    "avisos": avisos,
    "imagenes_faltantes": imagenes_faltantes,
    "tema": par.get("tema"),
    "origen_tema": par.get("origen"),
    "modulo_declarado": par.get("modulo_declarado"),
    "modo": par.get("modo"),
    "resolucion_solicitada": "%dx%d" % (ancho, alto),
    "resolucion": resolucion,
    "renderer": renderer,
    "plugin_splash": plugin,
    "plymouth_paquete": par.get("paquete_plymouth") or None,
    "segundos_splash": segundos,
    "fps_captura": fps,
    "fotogramas_capturados": fot["capturados"],
    "fotogramas_distintos": fot["distintos"],
    "fotogramas_unicos": fot["unicos"],
    "fotogramas_no_negros": fot["no_negros"],
    "primer_fotograma_no_negro": fot["primer_no_negro"],
    "primer_fotograma_con_cambio": fot["primer_cambio"],
    "duracion_captura_s": round(fot["duracion_s"], 3),
    "fps_captura_efectivo": round(fot["capturados"] / fot["duracion_s"], 2) if fot["duracion_s"] else None,
    "tasa_animacion_fps": tasa_animacion,
    # un solo cambio es apenas la aparicion del splash sobre la pantalla negra
    "animado": fot["distintos"] >= 2,
    "bbox_no_negro_union": fot["bbox_union"],
    "fraccion_no_negra_media": round(fot["fraccion_no_negra_media"], 6),
    "cpu_plymouthd_pct": cpu_ply,
    "cpu_plymouthd_usuario_pct": cpu_ply_usr,
    "cpu_plymouthd_sistema_pct": cpu_ply_sis,
    "cpu_xvfb_pct": cpu_xvfb,
    "ventana_cpu_s": resta("t_cpu_1", "t_cpu_0"),
    "cpu_arranque_y_carga_s": round(ticks_arranque / tck, 3) if ticks_arranque is not None else None,
    "rss_max_plymouthd_kb": num(med, "ply_rss_max_kb", int),
    "rss_final_plymouthd_kb": num(med, "ply_rss_final_kb", int),
    "rss_antes_del_splash_kb": num(med, "ply_rss_antes_show_kb", int),
    "tiempo_arranque_demonio_s": resta("t_demonio_listo", "t_demonio_inicio"),
    "tiempo_show_splash_s": resta("t_show_fin", "t_show_inicio"),
    "inicio_splash_epoca": num(med, "t_show_fin"),
    "fin_splash_epoca": num(med, "t_cpu_1"),
    "errores_script": errores_script,
    "eventos": eventos,
    "plymouthd": {
        "arranco": arranco,
        "vivo_al_final": vivo,
        "termino_limpio": med.get("termino_limpio") == "1",
        "codigo_salida": num(med, "codigo_salida_plymouthd", int),
        "show_splash_rc": num(med, "show_rc", int),
        "quit_rc": num(med, "quit_rc", int),
    },
    "cmdline": par.get("cmdline"),
    "escala_forzada": par.get("escala") or None,
    "codec_captura": par.get("codec_captura"),
    "segundos_de_analisis": round(t_analisis, 2),
}
with open(os.path.join(dir_salida, "metricas.json"), "w", encoding="utf-8") as f:
    json.dump(metricas, f, ensure_ascii=False, indent=2)
    f.write("\n")


def mostrar(valor, sufijo=""):
    return "?" if valor is None else "%s%s" % (valor, sufijo)


print("banco_plymouth: veredicto %s (codigo %d) | renderer %s | plugin %s | pantalla %s" % (
    veredicto, codigo, mostrar(renderer), mostrar(plugin), mostrar(resolucion)))
print("banco_plymouth: fotogramas %d capturados, %d distintos del anterior, %d no negros | animacion %s fps" % (
    fot["capturados"], fot["distintos"], fot["no_negros"], mostrar(tasa_animacion)))
print("banco_plymouth: CPU plymouthd %s de un nucleo | RSS max %s | errores de script: %d" % (
    mostrar(cpu_ply, " %"), mostrar(metricas["rss_max_plymouthd_kb"], " kB"), len(errores_script)))
for texto in avisos:
    print("banco_plymouth: AVISO: " + texto, file=sys.stderr)
for _, texto in problemas:
    print("banco_plymouth: PROBLEMA: " + texto, file=sys.stderr)
sys.exit(codigo)
PYEOF
}

# ---------------------------------------------------------------------------
# __interno: lo que corre DENTRO de los namespaces (uid 0 solo ahi dentro)
# ---------------------------------------------------------------------------

interno_tiene_submontajes() {
    awk -v p="$1/" '{ if (index($5, p) == 1) { e = 1; exit } } END { exit e ? 0 : 1 }' /proc/self/mountinfo
}

# Superpone (overlay de solo lectura) las capas sobre /<ruta>. Si /<ruta> contiene
# montajes heredados (p. ej. /usr/lib/wsl en WSL) el kernel rechaza usarla como capa
# inferior, y entonces se desciende a sus subdirectorios.
interno_superponer() {
    local rel="$1" capa capas="" hijo
    for capa in "${CAPAS[@]}"; do
        [ -d "$capa/$rel" ] && capas="${capas:+$capas:}$capa/$rel"
    done
    [ -n "$capas" ] || return 0
    if [ ! -d "/$rel" ] || [ -L "/$rel" ]; then
        echo "omitido: /$rel no existe en el sistema anfitrion (no se puede crear ahi sin root)" >> "$BITACORA_MONTAJES"
        return 0
    fi
    if interno_tiene_submontajes "/$rel"; then
        echo "desciende: /$rel contiene montajes heredados" >> "$BITACORA_MONTAJES"
        while IFS= read -r hijo; do
            interno_superponer "$rel/$hijo" || return 1
        done < <(for capa in "${CAPAS[@]}"; do
                     [ -d "$capa/$rel" ] && find "$capa/$rel" -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
                 done | sort -u)
        for capa in "${CAPAS[@]}"; do
            [ -d "$capa/$rel" ] && find "$capa/$rel" -mindepth 1 -maxdepth 1 ! -type d -printf "omitido: archivo suelto /$rel/%f\n" >> "$BITACORA_MONTAJES"
        done
        return 0
    fi
    if mount -t overlay overlay -o "lowerdir=$capas:/$rel" "/$rel" 2>> "$BITACORA_MONTAJES"; then
        echo "overlay: /$rel <= $capas" >> "$BITACORA_MONTAJES"
    else
        echo "ERROR: no se pudo montar el overlay sobre /$rel" >> "$BITACORA_MONTAJES"
        return 1
    fi
}

interno_montar() {
    CAPAS=("$R/capa" "$CACHE/root")
    local d
    for d in usr etc var; do
        interno_superponer "$d" || return 1
    done
    # /tmp y /run privados: el Xvfb de esta ejecucion no se cruza con ningun otro X,
    # y los sockets de la sesion del usuario (X0 de WSLg, wayland-0...) quedan tapados.
    mount -t tmpfs -o mode=1777 tmpfs /tmp 2>> "$BITACORA_MONTAJES" || return 1
    mount -t tmpfs -o mode=755 tmpfs /run 2>> "$BITACORA_MONTAJES" || return 1
    mkdir -p /run/plymouth
    echo "tmpfs: /tmp y /run privados" >> "$BITACORA_MONTAJES"
    if [ -d /var/lib/plymouth ]; then
        mount -t tmpfs tmpfs /var/lib/plymouth 2>> "$BITACORA_MONTAJES" \
            && echo "tmpfs: /var/lib/plymouth (escribible)" >> "$BITACORA_MONTAJES"
    fi
    if [ -d /mnt/wslg ]; then
        mount -t tmpfs tmpfs /mnt/wslg 2>> "$BITACORA_MONTAJES" \
            && echo "tmpfs: /mnt/wslg tapado (sockets graficos del usuario fuera de alcance)" >> "$BITACORA_MONTAJES"
    fi
    return 0
}

interno_entorno() {
    export PATH=/usr/sbin:/usr/bin:/sbin:/bin
    export HOME=/tmp/banco-home XDG_RUNTIME_DIR=/tmp/banco-run
    mkdir -p "$HOME" "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"
    export DISPLAY="$PANTALLA" GDK_BACKEND=x11 XDG_SESSION_TYPE=x11
    # GTK no debe buscar buses, accesibilidad ni GL acelerada (en WSL eso demora >15 s).
    export NO_AT_BRIDGE=1 GTK_A11Y=none GSETTINGS_BACKEND=memory GIO_USE_VFS=local
    export LIBGL_ALWAYS_SOFTWARE=1 GDK_SCALE=1 GDK_DPI_SCALE=1
    export DBUS_SESSION_BUS_ADDRESS=unix:path=/nonexistent/banco-plymouth
}

interno_verificar() {
    local falta=0 c f dirplug
    for c in plymouthd plymouth Xvfb xkbcomp; do
        if ! command -v "$c" >/dev/null 2>&1; then
            echo "FALTA comando: $c"
            falta=1
        fi
    done
    dirplug=$(plymouth --get-splash-plugin-path 2>/dev/null) || dirplug=""
    [ -n "$dirplug" ] || dirplug=/usr/lib/x86_64-linux-gnu/plymouth/
    dirplug="${dirplug%/}"
    for f in "$dirplug/script.so" "$dirplug/renderers/x11.so"; do
        if [ ! -f "$f" ]; then
            echo "FALTA plugin: $f"
            falta=1
        fi
    done
    for f in "$(command -v plymouthd)" "$(command -v plymouth)" "$(command -v Xvfb)" \
             "$dirplug/script.so" "$dirplug/renderers/x11.so" "$dirplug/label-pango.so"; do
        [ -e "$f" ] || continue
        if ldd "$f" 2>/dev/null | grep 'not found' | sed "s|^|FALTA biblioteca para $f:|"; then
            falta=1
        fi
    done
    echo "plymouthd: $(command -v plymouthd)"
    echo "plugins de plymouth: $dirplug (script.so, renderers/x11.so$([ -f "$dirplug/label-pango.so" ] && echo ', label-pango.so'))"
    echo "Xvfb: $(command -v Xvfb)"
    [ -d /usr/share/plymouth/themes/script ] && echo "tema de ejemplo: /usr/share/plymouth/themes/script"
    return "$falta"
}

# utime y stime (en ticks) de un proceso.
interno_ticks() {
    local s
    s=$(cat "/proc/$1/stat" 2>/dev/null) || { echo "0 0"; return; }
    s="${s##*) }"
    # shellcheck disable=SC2086
    set -- $s
    echo "${12} ${13}"
}

interno_estado_campo() {
    awk -v c="$2:" '$1 == c { print $2; exit }' "/proc/$1/status" 2>/dev/null
}

interno_muestreador() {
    local pu ps xu xs
    echo "epoca,ply_utime_ticks,ply_stime_ticks,ply_rss_kb,xvfb_utime_ticks,xvfb_stime_ticks" > "$R/logs/muestras.csv"
    while kill -0 "$PID_PLY" 2>/dev/null; do
        read -r pu ps < <(interno_ticks "$PID_PLY")
        read -r xu xs < <(interno_ticks "$PID_XVFB")
        echo "$EPOCHREALTIME,$pu,$ps,$(interno_estado_campo "$PID_PLY" VmRSS),$xu,$xs" >> "$R/logs/muestras.csv"
        sleep 0.5
    done
}

interno_evento() {
    local t="$1" accion="$2" arg="$3" rc fondo=0 inicio
    local -a orden=()
    case "$accion" in
        mensaje) orden=(display-message "--text=$arg") ;;
        ocultar-mensaje) orden=(hide-message "--text=$arg") ;;
        clave) orden=(ask-for-password "--prompt=$arg"); fondo=1 ;;
        pregunta) orden=(ask-question "--prompt=$arg"); fondo=1 ;;
        progreso) orden=(system-update "--progress=$arg") ;;
        estado) orden=(update "--status=$arg") ;;
        modo) orden=(change-mode "--$arg") ;;
        pausar) orden=(pause-progress) ;;
        reanudar) orden=(unpause-progress) ;;
        ocultar) orden=(hide-splash) ;;
        mostrar) orden=(show-splash) ;;
        desactivar) orden=(deactivate) ;;
        reactivar) orden=(reactivate) ;;
        raiz-montada) orden=(update-root-fs --new-root-dir=/) ;;
        raiz-rw) orden=(update-root-fs --read-write) ;;
        recargar) orden=(reload) ;;
        crudo) read -r -a orden <<< "$arg" ;;
    esac
    inicio="$EPOCHREALTIME"
    if [ "$fondo" = 1 ]; then
        plymouth "${orden[@]}" > /dev/null 2>&1 &
        echo "$!" >> "$R/clientes.pids"
        rc=en-espera
    else
        timeout 10 plymouth "${orden[@]}" >> "$R/logs/eventos-salida.log" 2>&1
        rc=$?
    fi
    # columnas: inicio (epoca), fin (epoca), segundo pedido, codigo de salida, orden
    printf '%s\t%s\t%s\t%s\t%s\n' "$inicio" "$EPOCHREALTIME" "$t" "$rc" "plymouth ${orden[*]}" >> "$R/logs/eventos.tsv"
}

# Dispara cada evento en su segundo absoluto, contado desde $1 (el instante en que
# termino "plymouth show-splash"), sin acumular lo que tarde cada orden.
interno_eventos() {
    local origen="$1" t accion arg espera
    while IFS=$'\t' read -r t accion arg; do
        espera=$(awk -v o="$origen" -v t="$t" -v a="$EPOCHREALTIME" \
            'BEGIN { d = o + t - a; if (d < 0) d = 0; printf "%.3f", d }')
        sleep "$espera"
        interno_evento "$t" "$accion" "${arg:-}"
    done < "$R/eventos.tsv"
}

interno_esperar_fin() {
    # $1 = pid, $2 = decimas de segundo como maximo
    local i=0
    while kill -0 "$1" 2>/dev/null && [ "$i" -lt "$2" ]; do
        sleep 0.1
        i=$((i + 1))
    done
    ! kill -0 "$1" 2>/dev/null
}

interno_probar() {
    local M="$R/medidas.env" i u s
    : > "$M"
    medida() { printf '%s=%s\n' "$1" "$2" >> "$M"; }
    medida clk_tck "$(getconf CLK_TCK 2>/dev/null || echo 100)"

    # 1) Xvfb privado. Sin GLX: nadie lo necesita y en WSL su arranque diferido cuesta >15 s.
    Xvfb "$PANTALLA" -screen 0 "${ANCHO}x${ALTO}x24" -nolisten tcp -noreset -extension GLX \
        > "$R/logs/xvfb.log" 2>&1 &
    PID_XVFB=$!
    i=0
    while [ ! -S "/tmp/.X11-unix/X${PANTALLA#:}" ] && kill -0 "$PID_XVFB" 2>/dev/null && [ "$i" -lt 150 ]; do
        sleep 0.1
        i=$((i + 1))
    done
    if [ ! -S "/tmp/.X11-unix/X${PANTALLA#:}" ]; then
        echo "banco_plymouth: error: Xvfb no arranco (ver logs/xvfb.log)" >&2
        kill "$PID_XVFB" 2>/dev/null
        return 71
    fi

    # 2) plymouthd real, en primer plano, con registro de depuracion.
    [ -n "${ESCALA:-}" ] && export PLYMOUTH_FORCE_SCALE="$ESCALA"
    medida t_demonio_inicio "$EPOCHREALTIME"
    plymouthd --no-daemon --debug --debug-file="$R/logs/plymouth-debug.log" --mode="$MODO" \
        --kernel-command-line="$CMDLINE" > "$R/logs/plymouthd.stdout" 2> "$R/logs/plymouthd.stderr" &
    PID_PLY=$!
    local arranco=0 limite=$((SECONDS + 40))
    while [ "$SECONDS" -lt "$limite" ] && kill -0 "$PID_PLY" 2>/dev/null; do
        if timeout 3 plymouth --ping > /dev/null 2>&1; then
            arranco=1
            break
        fi
        sleep 0.1
    done
    medida t_demonio_listo "$EPOCHREALTIME"
    medida arranco "$arranco"
    if [ "$arranco" != 1 ]; then
        kill -TERM "$PID_PLY" 2>/dev/null
        interno_esperar_fin "$PID_PLY" 20 || kill -KILL "$PID_PLY" 2>/dev/null
        wait "$PID_PLY" 2>/dev/null
        medida codigo_salida_plymouthd "$?"
        kill "$PID_XVFB" 2>/dev/null
        wait "$PID_XVFB" 2>/dev/null
        return 0
    fi

    interno_muestreador &
    local pid_muestreo=$!

    # 3) Captura sin perdida de la pantalla virtual; arranca antes del splash para
    #    registrar el primer fotograma de la animacion.
    local tope
    tope=$(awk -v s="$SEGUNDOS" 'BEGIN { printf "%d", s + 60 }')
    # shellcheck disable=SC2086
    ffmpeg -nostdin -hide_banner -loglevel warning -f x11grab -draw_mouse 0 -framerate "$FPS" \
        -video_size "${ANCHO}x${ALTO}" -i "$PANTALLA" -t "$tope" -c:v $CODEC_CAPTURA \
        -fps_mode passthrough -enc_time_base 1:1000 -stats_period 0.1 -progress "$R/ffmpeg.progreso" \
        "$R/captura.mkv" > "$R/logs/ffmpeg-captura.log" 2>&1 &
    local pid_ff=$!
    i=0
    while ! grep -q '^frame=[1-9]' "$R/ffmpeg.progreso" 2>/dev/null && kill -0 "$pid_ff" 2>/dev/null && [ "$i" -lt 100 ]; do
        sleep 0.1
        i=$((i + 1))
    done

    # 4) Mostrar el splash.
    medida ply_rss_antes_show_kb "$(interno_estado_campo "$PID_PLY" VmRSS)"
    medida t_show_inicio "$EPOCHREALTIME"
    timeout 30 plymouth show-splash > "$R/logs/show-splash.log" 2>&1
    medida show_rc "$?"
    local t_show_fin="$EPOCHREALTIME"
    medida t_show_fin "$t_show_fin"
    read -r u s < <(interno_ticks "$PID_PLY")
    medida ply_ticks_tras_show "$((u + s))"
    medida ply_utime_0 "$u"
    medida ply_stime_0 "$s"
    read -r u s < <(interno_ticks "$PID_XVFB")
    medida xvfb_utime_0 "$u"
    medida xvfb_stime_0 "$s"
    medida t_cpu_0 "$EPOCHREALTIME"

    # 5) Eventos programados y espera.
    : > "$R/logs/eventos.tsv"
    : > "$R/clientes.pids"
    interno_eventos "$t_show_fin" &
    local pid_eventos=$!
    sleep "$SEGUNDOS"

    # 6) Medidas de CPU y memoria de plymouthd al cierre de la ventana.
    read -r u s < <(interno_ticks "$PID_PLY")
    medida t_cpu_1 "$EPOCHREALTIME"
    medida ply_utime_1 "$u"
    medida ply_stime_1 "$s"
    read -r u s < <(interno_ticks "$PID_XVFB")
    medida xvfb_utime_1 "$u"
    medida xvfb_stime_1 "$s"
    medida ply_rss_max_kb "$(interno_estado_campo "$PID_PLY" VmHWM)"
    medida ply_rss_final_kb "$(interno_estado_campo "$PID_PLY" VmRSS)"
    if kill -0 "$PID_PLY" 2>/dev/null; then
        medida vivo_al_final 1
    else
        medida vivo_al_final 0
    fi

    # 7) Cerrar la captura (ffmpeg termina el archivo al recibir SIGTERM).
    kill -TERM "$pid_ff" 2>/dev/null
    interno_esperar_fin "$pid_ff" 150 || kill -KILL "$pid_ff" 2>/dev/null
    wait "$pid_ff" 2>/dev/null
    medida ffmpeg_rc "$?"

    # 8) Clientes que quedaron esperando (ask-for-password...) y cierre del demonio.
    kill "$pid_eventos" 2>/dev/null
    local p
    while IFS= read -r p; do
        [ -n "$p" ] && kill "$p" 2>/dev/null
    done < "$R/clientes.pids"
    timeout 10 plymouth quit > "$R/logs/quit.log" 2>&1
    medida quit_rc "$?"
    if interno_esperar_fin "$PID_PLY" 100; then
        medida termino_limpio 1
    else
        medida termino_limpio 0
        kill -TERM "$PID_PLY" 2>/dev/null
        interno_esperar_fin "$PID_PLY" 20 || kill -KILL "$PID_PLY" 2>/dev/null
    fi
    wait "$PID_PLY" 2>/dev/null
    medida codigo_salida_plymouthd "$?"
    kill "$pid_muestreo" 2>/dev/null
    kill "$PID_XVFB" 2>/dev/null
    wait "$PID_XVFB" 2>/dev/null
    return 0
}

cmd_interno() {
    local accion="${1:-}"
    R="${2:-}"
    if [ -z "$R" ] || [ ! -f "$R/config.sh" ] || [ "$(id -u)" != 0 ]; then
        error "__interno es de uso interno (se invoca dentro del aislamiento)"
        exit "$SAL_USO"
    fi
    # shellcheck disable=SC1091
    . "$R/config.sh" || exit 70
    mkdir -p "$R/logs"
    BITACORA_MONTAJES="$R/logs/montajes.log"
    : > "$BITACORA_MONTAJES"
    if ! interno_montar; then
        error "no se pudieron armar los montajes privados:"
        cat "$BITACORA_MONTAJES" >&2
        exit 70
    fi
    interno_entorno
    case "$accion" in
        verificar) interno_verificar ;;
        probar) interno_probar 2> "$R/logs/banco-interno.log" ;;
        *) exit "$SAL_USO" ;;
    esac
    exit $?
}

# ---------------------------------------------------------------------------
# video
# ---------------------------------------------------------------------------

cmd_video() {
    local dir="" ancho=640 fps=25 formato=ambos
    while [ $# -gt 0 ]; do
        case "$1" in
            --*=*) set -- "${1%%=*}" "${1#*=}" "${@:2}"; continue ;;
            -h|--help) ayuda; exit 0 ;;
            --ancho|--fps|--formato)
                [ $# -ge 2 ] || morir "falta el valor de $1" "$SAL_USO"
                case "$1" in
                    --ancho) ancho="$2" ;;
                    --fps) fps="$2" ;;
                    --formato) formato="$2" ;;
                esac
                shift 2 ;;
            --*) morir "opcion desconocida para video: $1" "$SAL_USO" ;;
            *)
                [ -z "$dir" ] || morir "sobra un argumento: $1" "$SAL_USO"
                dir="$1"; shift ;;
        esac
    done
    [ -n "$dir" ] || morir "falta <DIR> (un directorio de resultados de 'probar')" "$SAL_USO"
    [ -d "$dir/frames" ] || morir "no existe $dir/frames" "$SAL_USO"
    [[ "$ancho" =~ ^[0-9]+$ ]] || morir "--ancho debe ser un entero (0 = original)" "$SAL_USO"
    { [[ "$fps" =~ ^[0-9]+$ ]] && [ "$fps" -ge 1 ] && [ "$fps" -le 120 ]; } || morir "--fps debe ser un entero entre 1 y 120" "$SAL_USO"
    case "$formato" in
        gif|mp4|ambos) ;;
        *) morir "--formato debe ser gif, mp4 o ambos" "$SAL_USO" ;;
    esac
    exigir_comandos ffmpeg python3 || exit "$SAL_ENTORNO"
    local n
    n=$(find "$dir/frames" -maxdepth 1 -type f -name 'f_*.png' | wc -l)
    [ "$n" -gt 0 ] || morir "no hay fotogramas f_*.png en $dir/frames" "$SAL_USO"

    # Ritmo real de la captura (para que el video dure lo mismo que la prueba).
    local fps_entrada
    fps_entrada=$(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("fps_captura_efectivo") or d.get("fps_captura") or 30)
except Exception:
    print(30)
' "$dir/metricas.json")
    local escala_gif="" escala_mp4="scale=trunc(iw/2)*2:trunc(ih/2)*2"
    if [ "$ancho" -gt 0 ]; then
        escala_gif="scale=$ancho:-1:flags=lanczos,"
        escala_mp4="scale=$ancho:-2:flags=lanczos"
    fi
    local rc=0
    if [ "$formato" = gif ] || [ "$formato" = ambos ]; then
        if ffmpeg -nostdin -y -hide_banner -loglevel error -framerate "$fps_entrada" -i "$dir/frames/f_%05d.png" \
            -vf "fps=$fps,${escala_gif}split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5" \
            "$dir/animacion.gif"; then
            info "GIF: $dir/animacion.gif ($(du -h "$dir/animacion.gif" | cut -f1))"
        else
            error "ffmpeg no pudo armar el GIF"
            rc=$SAL_ERROR
        fi
    fi
    if [ "$formato" = mp4 ] || [ "$formato" = ambos ]; then
        if ffmpeg -nostdin -y -hide_banner -loglevel error -framerate "$fps_entrada" -i "$dir/frames/f_%05d.png" \
            -vf "fps=$fps,$escala_mp4" -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart \
            "$dir/animacion.mp4"; then
            info "MP4: $dir/animacion.mp4 ($(du -h "$dir/animacion.mp4" | cut -f1))"
        else
            error "ffmpeg no pudo armar el MP4"
            rc=$SAL_ERROR
        fi
    fi
    info "$n fotogramas de entrada a $fps_entrada fps; salida a $fps fps"
    return "$rc"
}

# ---------------------------------------------------------------------------
# autoprueba
# ---------------------------------------------------------------------------

campo_json() {
    # $1 = archivo JSON, $2 = expresion de Python sobre "d"
    python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); print(eval(sys.argv[2], {"d": d}))' "$1" "$2" 2>/dev/null
}

cmd_autoprueba() {
    local base=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --*=*) set -- "${1%%=*}" "${1#*=}" "${@:2}"; continue ;;
            -h|--help) ayuda; exit 0 ;;
            --salida) [ $# -ge 2 ] || morir "falta el valor de --salida" "$SAL_USO"; base="$2"; shift 2 ;;
            *) morir "opcion desconocida para autoprueba: $1" "$SAL_USO" ;;
        esac
    done
    cache_preparada || morir "la cache no esta preparada; ejecute primero: $(basename "$RUTA_SCRIPT") preparar" "$SAL_ENTORNO"
    exigir_comandos ffmpeg python3 || exit "$SAL_ENTORNO"
    [ -n "$base" ] || base="$DIR_REPO/output/temporales/banco/autoprueba-$(date +%Y%m%d-%H%M%S)-$$"
    mkdir -p "$base/temas/banco-minimo" "$base/temas/banco-roto" || morir "no se pudo crear $base" "$SAL_ERROR"
    base="$(readlink -f -- "$base")"
    local fallas=0 rc m
    resultado() {
        # $1 = PASA|FALLA, $2 = texto
        printf 'AUTOPRUEBA %s %s\n' "$1" "$2"
        [ "$1" = PASA ] || fallas=$((fallas + 1))
    }

    # Tema minimo: un cuadrado blanco de 40x40 que avanza 4 px por refresco sobre fondo negro.
    ffmpeg -nostdin -y -hide_banner -loglevel error -f lavfi -i "color=c=white:s=40x40" -frames:v 1 \
        "$base/temas/banco-minimo/punto.png" || morir "ffmpeg no pudo generar el sprite de prueba" "$SAL_ERROR"
    cat > "$base/temas/banco-minimo/banco-minimo.plymouth" <<'EOF'
[Plymouth Theme]
Name=Banco minimo
Description=Tema de autoprueba del banco: un sprite que se desplaza
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/banco-minimo
ScriptFile=/usr/share/plymouth/themes/banco-minimo/banco-minimo.script
EOF
    cat > "$base/temas/banco-minimo/banco-minimo.script" <<'EOF'
Window.SetBackgroundTopColor(0, 0, 0);
Window.SetBackgroundBottomColor(0, 0, 0);
punto.imagen = Image("punto.png");
punto.sprite = Sprite(punto.imagen);
punto.sprite.SetY(100);
global.x = 0;
fun refrescar() {
    global.x += 4;
    if (global.x > Window.GetWidth() - 40) global.x = 0;
    punto.sprite.SetX(global.x);
}
Plymouth.SetRefreshFunction(refrescar);
EOF
    # Tema roto: mismo tema con un error de sintaxis en la linea 3.
    cat > "$base/temas/banco-roto/banco-roto.plymouth" <<'EOF'
[Plymouth Theme]
Name=Banco roto
Description=Tema de autoprueba del banco: script con error de sintaxis
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/banco-roto
ScriptFile=/usr/share/plymouth/themes/banco-roto/banco-roto.script
EOF
    cat > "$base/temas/banco-roto/banco-roto.script" <<'EOF'
Window.SetBackgroundTopColor(0.3, 0, 0);
fun refrescar() {
    x = 1 + ;
}
Plymouth.SetRefreshFunction(refrescar);
EOF

    # a) tema "script" de stock: corre y hay animacion.
    bash "$RUTA_SCRIPT" probar stock:script --segundos 4 --tamano 1024x768 --salida "$base/a-stock" > "$base/a-stock.log" 2>&1
    rc=$?
    m="$base/a-stock/metricas.json"
    if [ "$rc" = 0 ] && [ "$(campo_json "$m" 'd["plugin_splash"] == "script" and d["renderer"] == "x11" and d["fotogramas_distintos"] > 0')" = True ]; then
        resultado PASA "a) tema script de stock: rc=$rc, $(campo_json "$m" '"renderer=%s plugin=%s capturados=%d distintos=%d cpu=%s%% rss_max=%skB" % (d["renderer"], d["plugin_splash"], d["fotogramas_capturados"], d["fotogramas_distintos"], d["cpu_plymouthd_pct"], d["rss_max_plymouthd_kb"])')"
    else
        resultado FALLA "a) tema script de stock: rc=$rc (ver $base/a-stock.log)"
    fi

    # b) tema minimo: el sprite se mueve. Analisis de pixeles independiente sobre los PNG.
    bash "$RUTA_SCRIPT" probar "$base/temas/banco-minimo" --segundos 4 --tamano 800x600 --salida "$base/b-minimo" > "$base/b-minimo.log" 2>&1
    rc=$?
    local analisis
    analisis=$(python3 - "$base/b-minimo/frames" 800 600 <<'PYEOF'
import subprocess
import sys

frames, ancho, alto = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
proc = subprocess.Popen(
    ["ffmpeg", "-nostdin", "-v", "error", "-i", frames + "/f_%05d.png", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
    stdout=subprocess.PIPE)
cajas = []
while True:
    buf = proc.stdout.read(ancho * alto)
    if len(buf) < ancho * alto:
        break
    xs, ys = [], []
    for y in range(alto):
        fila = buf[y * ancho:(y + 1) * ancho]
        if fila.count(0) == ancho:
            continue
        ys.append(y)
        xs.append(ancho - len(fila.lstrip(b"\0")))
        xs.append(len(fila.rstrip(b"\0")) - 1)
    cajas.append((min(xs), min(ys), max(xs), max(ys)) if ys else None)
proc.wait()
visibles = [c for c in cajas if c]
x0s = [c[0] for c in visibles]
movs = sum(1 for a, b in zip(x0s, x0s[1:]) if a != b)
tam_ok = sum(1 for c in visibles if c[2] - c[0] + 1 == 40 and c[3] - c[1] + 1 == 40 and c[1] == 100)
ok = len(visibles) >= 20 and movs >= len(visibles) // 2 and tam_ok >= len(visibles) * 0.9 and len(set(x0s)) >= 10
print("%s fotogramas=%d con_sprite=%d sprite_40x40_en_y100=%d cambios_de_x=%d posiciones_x_distintas=%d x0_muestra=%s" % (
    "OK" if ok else "MAL", len(cajas), len(visibles), tam_ok, movs, len(set(x0s)), x0s[:12]))
PYEOF
)
    if [ "$rc" = 0 ] && [ "${analisis%% *}" = OK ]; then
        resultado PASA "b) tema minimo con sprite movil: rc=$rc, pixeles: $analisis"
    else
        resultado FALLA "b) tema minimo con sprite movil: rc=$rc, pixeles: ${analisis:-sin analisis} (ver $base/b-minimo.log)"
    fi

    # c) script con error de sintaxis: codigo != 0 y el error queda informado.
    bash "$RUTA_SCRIPT" probar "$base/temas/banco-roto" --segundos 2 --tamano 800x600 --salida "$base/c-roto" > "$base/c-roto.log" 2>&1
    rc=$?
    m="$base/c-roto/metricas.json"
    if [ "$rc" = "$SAL_SCRIPT" ] && [ "$(campo_json "$m" 'd["veredicto"] == "FALLA" and any(e["tipo"] == "parseo" and e.get("linea") == 3 for e in d["errores_script"])')" = True ] \
        && grep -q 'Parser error' "$base/c-roto.log"; then
        resultado PASA "c) script con error de sintaxis: rc=$rc, $(campo_json "$m" 'd["errores_script"][0]["mensaje"]')"
    else
        resultado FALLA "c) script con error de sintaxis: rc=$rc (se esperaba $SAL_SCRIPT; ver $base/c-roto.log)"
    fi

    # d) dos ejecuciones concurrentes, con temas y resoluciones distintas, no se pisan.
    local pid1 pid2 rc1 rc2
    bash "$RUTA_SCRIPT" probar stock:script --segundos 5 --tamano 1024x768 --salida "$base/d-concurrente-1" > "$base/d-concurrente-1.log" 2>&1 &
    pid1=$!
    bash "$RUTA_SCRIPT" probar "$base/temas/banco-minimo" --segundos 5 --tamano 640x480 --salida "$base/d-concurrente-2" > "$base/d-concurrente-2.log" 2>&1 &
    pid2=$!
    wait "$pid1"; rc1=$?
    wait "$pid2"; rc2=$?
    local m1="$base/d-concurrente-1/metricas.json" m2="$base/d-concurrente-2/metricas.json" solape
    solape=$(python3 -c '
import json, sys
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
ini, fin = max(a["inicio_splash_epoca"], b["inicio_splash_epoca"]), min(a["fin_splash_epoca"], b["fin_splash_epoca"])
ok = (fin - ini > 1.0 and a["tema"] == "script" and b["tema"] == "banco-minimo"
      and a["resolucion"] == "1024x768" and b["resolucion"] == "640x480"
      and a["fotogramas_distintos"] > 0 and b["fotogramas_distintos"] > 0
      and a["bbox_no_negro_union"] != b["bbox_no_negro_union"])
print("%s solape=%.1fs | 1: tema=%s pantalla=%s distintos=%d bbox=%s | 2: tema=%s pantalla=%s distintos=%d bbox=%s" % (
    "OK" if ok else "MAL", fin - ini, a["tema"], a["resolucion"], a["fotogramas_distintos"], a["bbox_no_negro_union"],
    b["tema"], b["resolucion"], b["fotogramas_distintos"], b["bbox_no_negro_union"]))
' "$m1" "$m2" 2>/dev/null)
    if [ "$rc1" = 0 ] && [ "$rc2" = 0 ] && [ "${solape%% *}" = OK ]; then
        resultado PASA "d) dos ejecuciones concurrentes: rc=$rc1/$rc2, $solape"
    else
        resultado FALLA "d) dos ejecuciones concurrentes: rc=$rc1/$rc2, ${solape:-sin datos} (ver $base/d-concurrente-*.log)"
    fi

    info "resultados de la autoprueba en: $base"
    if [ "$fallas" -gt 0 ]; then
        error "autoprueba con $fallas falla(s)"
        return "$SAL_ERROR"
    fi
    info "autoprueba completa: 4 de 4"
    return 0
}

# ---------------------------------------------------------------------------

main() {
    local sub="${1:-}"
    [ $# -gt 0 ] && shift
    case "$sub" in
        preparar) cmd_preparar "$@" ;;
        probar) cmd_probar "$@" ;;
        video) cmd_video "$@" ;;
        estado) cmd_estado "$@" ;;
        autoprueba) cmd_autoprueba "$@" ;;
        limpiar) cmd_limpiar "$@" ;;
        __interno) cmd_interno "$@" ;;
        -h|--help|help|ayuda) ayuda ;;
        "") ayuda >&2; exit "$SAL_USO" ;;
        *) error "subcomando desconocido: $sub (ver --help)"; exit "$SAL_USO" ;;
    esac
}

main "$@"
