#!/usr/bin/env bash
# verificar_instalacion.sh -- comprueba, en el equipo, que el tema quedó bien instalado.
#
# Mira el efecto y no los mensajes de instalar.sh: que los archivos instalados sean
# los del repositorio, que el tema esté elegido y que el initramfs del kernel en uso
# se haya regenerado después y lleve dentro el tema, el plugin script y la elección.
# No cambia nada. Hace falta root para leer el initramfs (en Ubuntu es 0600).
#
# Uso: sudo scripts/verificar_instalacion.sh
# Sale con 0 si todo pasa. Lee el initramfs con unmkinitramfs (Debian/Ubuntu).
set -u
PATH="$PATH:/usr/local/sbin:/usr/sbin:/sbin"

case "${1:-}" in
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    "") ;;
    *) echo "error: opción desconocida: $1" >&2; exit 2 ;;
esac

NOMBRE=paraguay
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORIGEN="$REPO/$NOMBRE"
DESTINO="/usr/share/plymouth/themes/$NOMBRE"
PASAN=0
FALLAN=0

comprobar() {           # comprobar <descripción> <orden de prueba...>
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASA  $desc"; PASAN=$((PASAN + 1))
    else
        echo "FALLA $desc"; FALLAN=$((FALLAN + 1))
    fi
}
iguales() {             # iguales <dir A> <dir B>: cada archivo de A está idéntico en B
    local f
    for f in "$1"/*; do cmp -s "$f" "$2/${f##*/}" || return 1; done
}
plugin() {              # plugin <raíz> <patrón>: hay un plugin de Plymouth con ese nombre
    local f
    for f in "$1"/usr/lib/*/plymouth/$2 "$1"/usr/lib/plymouth/$2 "$1"/usr/lib64/plymouth/$2; do
        [ -f "$f" ] && return 0
    done
    return 1
}

[ "$(id -u)" -eq 0 ] || { echo "error: hace falta root para leer el initramfs (sudo $0)" >&2; exit 2; }
[ -d "$ORIGEN" ] || { echo "error: no encuentro $ORIGEN" >&2; exit 2; }
command -v unmkinitramfs >/dev/null 2>&1 ||
    { echo "error: falta unmkinitramfs (solo se sabe leer el initramfs de Debian/Ubuntu)" >&2; exit 2; }

ESPERADOS=$(ls "$ORIGEN" | wc -l)

# --- archivos instalados y tema elegido -----------------------------------------
comprobar "instalado en $DESTINO, $ESPERADOS archivos idénticos al repositorio" iguales "$ORIGEN" "$DESTINO"
elegido() {
    [ "$(readlink -f /usr/share/plymouth/themes/default.plymouth)" = "$DESTINO/$NOMBRE.plymouth" ] && return 0
    command -v plymouth-set-default-theme >/dev/null 2>&1 &&
        [ "$(plymouth-set-default-theme 2>/dev/null)" = "$NOMBRE" ] && return 0
    grep -q "^Theme=$NOMBRE\$" /etc/plymouth/plymouthd.conf 2>/dev/null
}
comprobar "«$NOMBRE» es el tema elegido" elegido

# --- initramfs del kernel en uso ------------------------------------------------
INITRD="/boot/initrd.img-$(uname -r)"
[ -f "$INITRD" ] || INITRD="$(readlink -f /boot/initrd.img)"
echo "      initramfs: $INITRD"
comprobar "el initramfs es posterior a la instalación del tema" test "$INITRD" -nt "$DESTINO/$NOMBRE.script"

DIR="$(mktemp -d)"
trap 'rm -rf "$DIR"' EXIT
unmkinitramfs "$INITRD" "$DIR" >/dev/null 2>&1
# unmkinitramfs separa el microcódigo (early*) del sistema principal (main/), si lo hay
RAIZ="$DIR"; [ -d "$DIR/main" ] && RAIZ="$DIR/main"
comprobar "el initramfs lleva los $ESPERADOS archivos del tema, idénticos" iguales "$ORIGEN" "$RAIZ$DESTINO"
comprobar "el initramfs lleva el plugin script.so" plugin "$RAIZ" script.so
elegido_initramfs() {
    grep -q "^Theme=$NOMBRE\$" "$RAIZ/etc/plymouth/plymouthd.conf" 2>/dev/null && return 0
    grep -q "^ScriptFile=$DESTINO/$NOMBRE.script\$" "$RAIZ/usr/share/plymouth/themes/default.plymouth" 2>/dev/null
}
comprobar "dentro del initramfs, el tema elegido es «$NOMBRE»" elegido_initramfs
if ! plugin "$RAIZ" 'label*.so'; then
    echo "aviso: el initramfs no lleva el plugin de texto (label): no se verán los mensajes"
fi

echo
if [ "$FALLAN" -eq 0 ]; then
    echo "INSTALACION: PASA ($PASAN/$((PASAN + FALLAN)) comprobaciones)"
    exit 0
fi
echo "INSTALACION: FALLA ($FALLAN de $((PASAN + FALLAN)) comprobaciones)"
exit 1
