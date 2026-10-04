#!/usr/bin/env bash
# desinstalar.sh -- quita el tema de Plymouth «paraguay» y restaura el anterior.
set -euo pipefail

# Las herramientas de Plymouth y del initramfs viven en sbin, que no siempre está
# en el PATH (usuario normal en Debian, root obtenido con «su»).
PATH="$PATH:/usr/local/sbin:/usr/sbin:/sbin"
export PATH

NOMBRE=paraguay
PREFIJO=""
SIMULAR=0
INITRAMFS=1

uso() {
    cat <<EOF
Uso: sudo ./desinstalar.sh [opciones]

Deja de usar el tema «$NOMBRE», borra /usr/share/plymouth/themes/$NOMBRE y
regenera el initramfs. Restaura el tema que instalar.sh anotó como anterior.

Opciones:
  --simular         muestra lo que haría, sin cambiar nada (no pide root)
  --sin-initramfs   no regenera el initramfs
  --prefijo DIR     quita la copia instalada bajo DIR (no toca el tema activo)
  -h, --help        esta ayuda
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --simular) SIMULAR=1 ;;
        --sin-initramfs) INITRAMFS=0 ;;
        --prefijo)
            [ $# -ge 2 ] || { echo "error: --prefijo necesita un directorio" >&2; exit 2; }
            PREFIJO="${2%/}"; INITRAMFS=0; shift ;;
        -h|--help) uso; exit 0 ;;
        *) echo "error: opción desconocida: $1" >&2; uso >&2; exit 2 ;;
    esac
    shift
done

DESTINO="$PREFIJO/usr/share/plymouth/themes/$NOMBRE"
ANTERIOR="$DESTINO/.tema-anterior"
CONF=/etc/plymouth/plymouthd.conf

aviso() { echo "aviso: $*" >&2; }
correr() {
    echo "+ $*"
    [ "$SIMULAR" -eq 1 ] || "$@"
}

if [ "$SIMULAR" -eq 0 ] && [ -z "$PREFIJO" ] && [ "$(id -u)" -ne 0 ]; then
    echo "error: hace falta root (sudo ./desinstalar.sh), o usar --simular / --prefijo DIR" >&2
    exit 1
fi
if [ ! -d "$DESTINO" ]; then
    echo "El tema «$NOMBRE» no está instalado en $DESTINO: nada que hacer."
    exit 0
fi

# --- dejar de usarlo --------------------------------------------------------------
# instalar.sh anotó cómo lo activó (primera línea) y qué había antes (segunda).
metodo=""
tema_anterior=""
if [ -f "$ANTERIOR" ]; then
    metodo="$(sed -n 1p "$ANTERIOR")"
    tema_anterior="$(sed -n 2p "$ANTERIOR")"
fi
if [ -z "$PREFIJO" ]; then
    # Sin anotación (copia hecha con --no-activar, o archivo perdido) se revisan
    # los tres mecanismos por si alguno apunta al tema.
    if { [ -z "$metodo" ] || [ "$metodo" = psdt ]; } && command -v plymouth-set-default-theme >/dev/null 2>&1; then
        if [ "$(plymouth-set-default-theme 2>/dev/null || true)" = "$NOMBRE" ]; then
            if [ -n "$tema_anterior" ] && [ -d "/usr/share/plymouth/themes/$tema_anterior" ]; then
                correr plymouth-set-default-theme "$tema_anterior"
            else
                correr plymouth-set-default-theme --reset
            fi
        fi
    fi
    if { [ -z "$metodo" ] || [ "$metodo" = alternativas ]; } && command -v update-alternatives >/dev/null 2>&1; then
        # Sin tubería: con pipefail, un «| grep -q» puede cortar a update-alternatives
        # antes de que termine de escribir y hacer que la condición falle.
        consulta="$(update-alternatives --query default.plymouth 2>/dev/null || true)"
        case "$consulta" in
            *"$DESTINO/$NOMBRE.plymouth"*)
                # al quitar la alternativa el sistema vuelve sola a la de mayor prioridad;
                # si antes había una elegida a mano, se repone
                correr update-alternatives --remove default.plymouth "$DESTINO/$NOMBRE.plymouth"
                if [ -n "$tema_anterior" ] && [ -f "$tema_anterior" ]; then
                    correr update-alternatives --set default.plymouth "$tema_anterior"
                fi ;;
        esac
    fi
    if { [ -z "$metodo" ] || [ "$metodo" = conf ]; } && [ -f "$CONF" ] && grep -q "^Theme=$NOMBRE\$" "$CONF"; then
        if [ "$metodo" = conf ] && [ -n "$tema_anterior" ]; then
            correr sed -i "s/^Theme=$NOMBRE\$/Theme=$tema_anterior/" "$CONF"
        else
            correr sed -i "/^Theme=$NOMBRE\$/d" "$CONF"
        fi
    fi
fi

# --- borrar los archivos ------------------------------------------------------------
# Solo lo que instalar.sh puso; si alguien dejó algo más, el directorio queda.
for f in "$DESTINO/$NOMBRE.plymouth" "$DESTINO/$NOMBRE.script" "$DESTINO"/[ped][0-9]*.png "$ANTERIOR"; do
    if [ -e "$f" ]; then
        correr rm -f "$f"
    fi
done
if [ "$SIMULAR" -eq 1 ]; then
    echo "+ rmdir $DESTINO"
elif ! rmdir "$DESTINO" 2>/dev/null; then
    aviso "$DESTINO no quedó vacío: contiene archivos que no son del tema y no se borra"
fi

# --- initramfs --------------------------------------------------------------------
if [ "$INITRAMFS" -eq 1 ]; then
    if command -v update-initramfs >/dev/null 2>&1; then
        correr update-initramfs -u
    elif [ -x /usr/libexec/plymouth/plymouth-update-initrd ]; then
        correr /usr/libexec/plymouth/plymouth-update-initrd
    elif command -v dracut >/dev/null 2>&1; then
        correr dracut --force
    elif command -v mkinitcpio >/dev/null 2>&1; then
        correr mkinitcpio -P
    else
        aviso "no sé regenerar el initramfs en este sistema; hacerlo a mano"
    fi
fi

if [ "$SIMULAR" -eq 1 ]; then
    echo "simulación: no se cambió nada."
else
    echo "Tema «$NOMBRE» desinstalado."
fi
