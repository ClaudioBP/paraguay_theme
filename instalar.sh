#!/usr/bin/env bash
# instalar.sh -- instala y activa el tema de Plymouth «paraguay».
#
# Copia paraguay/ a /usr/share/plymouth/themes/paraguay, lo elige como tema por
# defecto y regenera el initramfs. Cambia el arranque del equipo: hace falta root.
set -euo pipefail

# Las herramientas de Plymouth y del initramfs viven en sbin, que no siempre está
# en el PATH (usuario normal en Debian, root obtenido con «su»).
PATH="$PATH:/usr/local/sbin:/usr/sbin:/sbin"
export PATH

NOMBRE=paraguay
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGEN="$AQUI/$NOMBRE"
PREFIJO=""
SIMULAR=0
ACTIVAR=1
INITRAMFS=1

uso() {
    cat <<EOF
Uso: sudo ./instalar.sh [opciones]

Instala el tema de Plymouth «$NOMBRE», lo activa y regenera el initramfs.

Opciones:
  --simular         muestra lo que haría, sin cambiar nada (no pide root)
  --no-activar      solo copia los archivos: no cambia el tema por defecto ni
                    regenera el initramfs
  --sin-initramfs   no regenera el initramfs (el tema no se verá hasta hacerlo)
  --prefijo DIR     instala bajo DIR en vez de / (para empaquetar o probar);
                    implica --no-activar y no pide root
  -h, --help        esta ayuda

Ejemplos:
  ./instalar.sh --simular
  sudo ./instalar.sh
  ./instalar.sh --prefijo /tmp/paquete

Para volver atrás: sudo ./desinstalar.sh
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --simular) SIMULAR=1 ;;
        --no-activar) ACTIVAR=0; INITRAMFS=0 ;;
        --sin-initramfs) INITRAMFS=0 ;;
        --prefijo)
            [ $# -ge 2 ] || { echo "error: --prefijo necesita un directorio" >&2; exit 2; }
            PREFIJO="${2%/}"; ACTIVAR=0; INITRAMFS=0; shift ;;
        -h|--help) uso; exit 0 ;;
        *) echo "error: opción desconocida: $1" >&2; uso >&2; exit 2 ;;
    esac
    shift
done

DESTINO="$PREFIJO/usr/share/plymouth/themes/$NOMBRE"
# Qué había antes, para que desinstalar.sh lo restaure: método en la primera
# línea (psdt, alternativas o conf) y valor anterior en la segunda.
ANTERIOR="$DESTINO/.tema-anterior"
CONF=/etc/plymouth/plymouthd.conf

aviso() { echo "aviso: $*" >&2; }
correr() {
    echo "+ $*"
    [ "$SIMULAR" -eq 1 ] || "$@"
}

# --- comprobaciones previas ---------------------------------------------------
for f in "$NOMBRE.plymouth" "$NOMBRE.script"; do
    [ -f "$ORIGEN/$f" ] || { echo "error: falta $ORIGEN/$f" >&2; exit 1; }
done
if ! ls "$ORIGEN"/p*.png >/dev/null 2>&1; then
    echo "error: faltan las imágenes del tema; generarlas con: python3 scripts/generar_tema.py" >&2
    exit 1
fi
if grep -q $'\r' "$ORIGEN/$NOMBRE.plymouth" "$ORIGEN/$NOMBRE.script"; then
    echo "error: el tema tiene finales de línea CRLF y Plymouth no lo cargaría" >&2
    echo "       (clonar con: git clone -c core.autocrlf=false ...)" >&2
    exit 1
fi
if [ "$SIMULAR" -eq 0 ] && [ -z "$PREFIJO" ] && [ "$(id -u)" -ne 0 ]; then
    echo "error: hace falta root (sudo ./instalar.sh), o usar --simular / --prefijo DIR" >&2
    exit 1
fi

if [ -z "$PREFIJO" ]; then
    command -v plymouth >/dev/null 2>&1 || aviso "no encuentro el programa plymouth: ¿está instalado?"
    # «|| true»: sin el programa plymouth la tubería falla y, con set -e, cortaría el script
    version="$(plymouth --version 2>/dev/null | sed -n 's/^plymouth //p' || true)"
    case "$version" in
        0.[0-8].*|0.9.[0-4]*)
            aviso "Plymouth $version: el tema necesita 0.9.5 o posterior (usa Image.Crop)."
            aviso "  Con una versión anterior la pantalla de arranque queda en negro." ;;
    esac
    modulo=""
    for d in /usr/lib/*/plymouth /usr/lib/plymouth /usr/lib64/plymouth; do
        if [ -f "$d/script.so" ]; then
            modulo="$d"
            break
        fi
    done
    if [ -z "$modulo" ]; then
        aviso "no encuentro el plugin script.so de Plymouth; sin él el tema no carga."
        aviso "  Fedora/openSUSE: instalar plymouth-plugin-script. Debian/Ubuntu/Arch: viene en plymouth."
    elif ! ls "$modulo"/label*.so >/dev/null 2>&1; then
        aviso "no hay plugin de texto (label): los mensajes y el texto de las preguntas no se verán."
        aviso "  El pedido de clave igual se indica con una fila de puntos."
        aviso "  Debian/Ubuntu: plymouth-label. Fedora/openSUSE: plymouth-plugin-label."
    fi
    if [ -r /proc/cmdline ] && ! grep -qw -e splash -e rhgb /proc/cmdline; then
        aviso "la línea del kernel no tiene 'splash': Plymouth no mostrará ningún tema gráfico."
    fi
fi

# En Debian y Ubuntu el hook de initramfs de Plymouth, para cualquier tema gráfico,
# copia la configuración de fontconfig y ejecuta fc-cache sin comprobar que existan.
# Si faltan, update-initramfs falla ahora y en cada actualización del kernel.
if [ "$ACTIVAR" -eq 1 ]; then
    hook=/usr/share/initramfs-tools/hooks/plymouth
    faltan=""
    if [ -f "$hook" ]; then
        if grep -q '/etc/fonts/fonts.conf' "$hook" && [ ! -e /etc/fonts/fonts.conf ]; then
            faltan="$faltan /etc/fonts/fonts.conf"
        fi
        if grep -q 'fc-cache' "$hook" && ! command -v fc-cache >/dev/null 2>&1; then
            faltan="$faltan fc-cache"
        fi
    fi
    if [ -n "$faltan" ]; then
        echo "error: falta fontconfig (${faltan# }): con un tema gráfico activo, el hook de" >&2
        echo "       initramfs de Plymouth fallaría. Instalar primero: apt install plymouth-label fontconfig" >&2
        if [ "$SIMULAR" -eq 0 ]; then
            exit 1
        fi
        aviso "(simulación) la instalación real se detendría aquí"
    fi
fi

# --- qué tema hay ahora ---------------------------------------------------------
# Se averigua antes de copiar nada. Al reinstalar se conserva lo ya anotado.
metodo=""
tema_anterior=""
if [ "$ACTIVAR" -eq 1 ]; then
    if command -v plymouth-set-default-theme >/dev/null 2>&1; then
        metodo=psdt
        tema_anterior="$(plymouth-set-default-theme 2>/dev/null || true)"
    elif command -v update-alternatives >/dev/null 2>&1 &&
         consulta="$(update-alternatives --query default.plymouth 2>/dev/null)"; then
        # Ubuntu no trae plymouth-set-default-theme: el tema se elige con alternativas.
        # Solo hace falta recordar una elección manual; en modo automático, al quitar
        # nuestra alternativa el sistema vuelve sola a la de mayor prioridad.
        metodo=alternativas
        if [ "$(printf '%s\n' "$consulta" | sed -n 's/^Status: //p')" = manual ]; then
            tema_anterior="$(printf '%s\n' "$consulta" | sed -n 's/^Value: //p')"
        fi
    else
        metodo=conf
        if [ -f "$CONF" ]; then
            tema_anterior="$(sed -n 's/^Theme=//p' "$CONF" | head -n 1)"
        fi
    fi
    case "$tema_anterior" in
        "$NOMBRE"|"$DESTINO/$NOMBRE.plymouth")
            tema_anterior=""
            if [ -f "$ANTERIOR" ] && [ "$(sed -n 1p "$ANTERIOR")" = "$metodo" ]; then
                tema_anterior="$(sed -n 2p "$ANTERIOR")"
            fi ;;
    esac
fi

# --- copia ----------------------------------------------------------------------
correr install -d -m 755 "$DESTINO"
for f in "$ORIGEN/$NOMBRE.plymouth" "$ORIGEN/$NOMBRE.script" "$ORIGEN"/*.png; do
    correr install -m 644 "$f" "$DESTINO/"
done
if [ -n "$metodo" ]; then
    echo "+ anotar en $ANTERIOR: método $metodo, tema anterior «${tema_anterior:-ninguno}»"
    [ "$SIMULAR" -eq 1 ] || printf '%s\n%s\n' "$metodo" "$tema_anterior" > "$ANTERIOR"
fi

# --- activación ----------------------------------------------------------------
case "$metodo" in
    psdt)
        correr plymouth-set-default-theme "$NOMBRE" ;;
    alternativas)
        correr update-alternatives --install /usr/share/plymouth/themes/default.plymouth \
            default.plymouth "$DESTINO/$NOMBRE.plymouth" 200
        correr update-alternatives --set default.plymouth "$DESTINO/$NOMBRE.plymouth" ;;
    conf)
        echo "+ poner Theme=$NOMBRE en $CONF"
        if [ "$SIMULAR" -eq 0 ]; then
            install -d -m 755 "$(dirname "$CONF")"
            if [ -f "$CONF" ] && grep -q '^Theme=' "$CONF"; then
                sed -i "s/^Theme=.*/Theme=$NOMBRE/" "$CONF"
            elif [ -f "$CONF" ] && grep -q '^\[Daemon\]' "$CONF"; then
                sed -i "/^\[Daemon\]/a Theme=$NOMBRE" "$CONF"
            else
                printf '[Daemon]\nTheme=%s\n' "$NOMBRE" >> "$CONF"
            fi
        fi ;;
esac

# --- initramfs ----------------------------------------------------------------
# Si la regeneración falla, el tema queda elegido pero el arranque sigue con la
# imagen vieja y cada regeneración posterior volvería a fallar: se deshace todo.
regenerar() {
    if command -v update-initramfs >/dev/null 2>&1; then
        correr update-initramfs -u
    elif [ -x /usr/libexec/plymouth/plymouth-update-initrd ]; then
        correr /usr/libexec/plymouth/plymouth-update-initrd
    elif command -v dracut >/dev/null 2>&1; then
        correr dracut --force
    elif command -v mkinitcpio >/dev/null 2>&1; then
        grep -Eq '^HOOKS=.*plymouth' /etc/mkinitcpio.conf 2>/dev/null ||
            aviso "falta el hook 'plymouth' en HOOKS de /etc/mkinitcpio.conf"
        correr mkinitcpio -P
    else
        aviso "no sé regenerar el initramfs en este sistema; hacerlo a mano para que el tema se vea al arrancar"
    fi
}
if [ "$INITRAMFS" -eq 1 ] && ! regenerar; then
    echo "error: falló la regeneración del initramfs; se deshace la instalación" >&2
    bash "$AQUI/desinstalar.sh" --sin-initramfs >&2 || true
    echo "error: el tema «$NOMBRE» NO quedó instalado. Revisar el mensaje de arriba y reintentar." >&2
    exit 1
fi

if [ "$SIMULAR" -eq 1 ]; then
    echo "simulación: no se cambió nada."
elif [ "$ACTIVAR" -eq 0 ]; then
    echo "Tema «$NOMBRE» copiado en $DESTINO (sin activar)."
elif [ "$INITRAMFS" -eq 0 ]; then
    echo "Tema «$NOMBRE» instalado y activado. Falta regenerar el initramfs para que se vea al arrancar."
else
    echo "Tema «$NOMBRE» instalado y activado. Se verá en el próximo arranque."
fi
