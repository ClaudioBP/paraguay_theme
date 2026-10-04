#!/usr/bin/env bash
# probar_instalador.sh -- ejercita instalar.sh y desinstalar.sh sin root ni cambios en el sistema.
#
# Copia los dos scripts a un arenero temporal anteponiendo $RAIZ a las rutas del
# sistema, los corre con un PATH cerrado donde las herramientas de Plymouth y del
# initramfs son dobles que registran sus llamadas (update-alternatives es el real,
# con base de datos privada), y comprueba el resultado de cada rama de activación.
#
# Uso: scripts/probar_instalador.sh [-v]      (-v muestra la salida de cada corrida)
# Sale con 0 si todas las comprobaciones pasan. Corre en Linux o WSL.
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSO=0
case "${1:-}" in
    -v) VERBOSO=1 ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    "") ;;
    *) echo "error: opción desconocida: $1" >&2; exit 2 ;;
esac

BASE="$(mktemp -d)"
trap 'rm -rf "$BASE"' EXIT
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

nuevo() {               # nuevo <nombre>: arenero limpio con temas de fábrica
    SB="$BASE/$1"; RAIZ="$SB/raiz"; LOG="$SB/llamadas.log"
    mkdir -p "$SB/bin" "$SB/sbin" "$RAIZ/usr/share/plymouth/themes" "$RAIZ/etc/plymouth" \
             "$RAIZ/usr/lib/x86_64-linux-gnu/plymouth"
    : > "$LOG"
    for u in bash sh cat grep sed install rm rmdir ls dirname head mkdir printf true; do
        ln -s "$(command -v "$u")" "$SB/bin/$u"
    done
    printf '#!/bin/bash\necho 0\n' > "$SB/bin/id"; chmod +x "$SB/bin/id"      # «somos root»
    : > "$RAIZ/usr/lib/x86_64-linux-gnu/plymouth/script.so"
    : > "$RAIZ/usr/lib/x86_64-linux-gnu/plymouth/label-pango.so"
    for t in bgrt spinner; do
        mkdir -p "$RAIZ/usr/share/plymouth/themes/$t"
        : > "$RAIZ/usr/share/plymouth/themes/$t/$t.plymouth"
    done
    for s in instalar.sh desinstalar.sh; do
        sed -e 's#/usr/share/plymouth#$RAIZ/usr/share/plymouth#g' \
            -e 's#/etc/plymouth#$RAIZ/etc/plymouth#g' \
            -e 's#/usr/libexec/plymouth#$RAIZ/usr/libexec/plymouth#g' \
            -e 's#/etc/mkinitcpio.conf#$RAIZ/etc/mkinitcpio.conf#g' \
            -e 's#hook=/usr/share/initramfs-tools#hook=$RAIZ/usr/share/initramfs-tools#' \
            -e 's#-e /etc/fonts/fonts.conf#-e $RAIZ/etc/fonts/fonts.conf#' \
            -e 's#for d in /usr/lib/\*/plymouth /usr/lib/plymouth /usr/lib64/plymouth#for d in $RAIZ/usr/lib/*/plymouth#' \
            -e 's#:/usr/local/sbin:/usr/sbin:/sbin#:$SB/sbin#' \
            "$REPO/$s" > "$SB/$s"
    done
    ln -s "$REPO/paraguay" "$SB/paraguay"
}

doble() {               # doble <dir> <nombre> [código de salida]: registra la llamada
    printf '#!/bin/bash\necho "%s $*" >> "%s"\nexit %s\n' "$2" "$LOG" "${3:-0}" > "$SB/$1/$2"
    chmod +x "$SB/$1/$2"
}

doble_psdt() {          # plymouth-set-default-theme mínimo: lee y escribe Theme= en plymouthd.conf
    cat > "$SB/sbin/plymouth-set-default-theme" <<EOF
#!/bin/bash
echo "plymouth-set-default-theme \$*" >> "$LOG"
conf="$RAIZ/etc/plymouth/plymouthd.conf"
case "\${1:-}" in
    "") sed -n 's/^Theme=//p' "\$conf" 2>/dev/null | head -n 1 ;;
    --reset) sed -i '/^Theme=/d' "\$conf" ;;
    *) if grep -q '^Theme=' "\$conf" 2>/dev/null; then sed -i "s/^Theme=.*/Theme=\$1/" "\$conf"
       else printf '[Daemon]\nTheme=%s\n' "\$1" >> "\$conf"; fi ;;
esac
EOF
    chmod +x "$SB/sbin/plymouth-set-default-theme"
}

alternativas_reales() { # update-alternatives real, con base de datos privada
    mkdir -p "$SB/alt" "$SB/adm"
    printf '#!/bin/bash\necho "update-alternatives $*" >> "%s"\nexec %s --altdir "%s/alt" --admindir "%s/adm" "$@"\n' \
        "$LOG" "$(command -v update-alternatives)" "$SB" "$SB" > "$SB/bin/update-alternatives"
    chmod +x "$SB/bin/update-alternatives"
    local t
    for t in bgrt:110 spinner:70; do
        "$SB/bin/update-alternatives" --quiet --install "$RAIZ/usr/share/plymouth/themes/default.plymouth" \
            default.plymouth "$RAIZ/usr/share/plymouth/themes/${t%:*}/${t%:*}.plymouth" "${t#*:}"
    done
    : > "$LOG"
}

correr() {              # correr <script> [argumentos]: PATH cerrado, sin sbin
    local s="$1"; shift
    if [ "$VERBOSO" -eq 1 ]; then
        ( cd / && env -i PATH="$SB/bin" RAIZ="$RAIZ" SB="$SB" bash "$SB/$s" "$@" )
    else
        ( cd / && env -i PATH="$SB/bin" RAIZ="$RAIZ" SB="$SB" bash "$SB/$s" "$@" ) >/dev/null 2>&1
    fi
}

TEMA() { echo "$RAIZ/usr/share/plymouth/themes/paraguay"; }
conf_dice() { grep -qx "Theme=$1" "$RAIZ/etc/plymouth/plymouthd.conf"; }
valor_alt() { "$SB/bin/update-alternatives" --query default.plymouth 2>/dev/null | sed -n "s/^$1: //p"; }
llamo() { grep -q "$1" "$LOG"; }

# --- A: plymouth-set-default-theme (Debian, Fedora, Arch), que vive en sbin ---
nuevo psdt; doble_psdt; doble sbin update-initramfs
printf '[Daemon]\nTheme=spinner\n' > "$RAIZ/etc/plymouth/plymouthd.conf"
correr instalar.sh
comprobar "psdt: encuentra las herramientas aunque sbin no esté en el PATH y activa el tema" conf_dice paraguay
comprobar "psdt: copia todos los archivos del tema" [ "$(ls "$(TEMA)" | wc -l)" -eq "$(ls "$REPO/paraguay" | wc -l)" ]
comprobar "psdt: regenera el initramfs" llamo "update-initramfs -u"
correr instalar.sh
comprobar "psdt: al reinstalar conserva anotado el tema anterior" [ "$(sed -n 2p "$(TEMA)/.tema-anterior")" = spinner ]
correr desinstalar.sh
comprobar "psdt: al desinstalar vuelve al tema anterior" conf_dice spinner
comprobar "psdt: al desinstalar borra el directorio del tema" [ ! -e "$(TEMA)" ]

# --- B: alternativas (Ubuntu) ---
if command -v update-alternatives >/dev/null 2>&1; then
    nuevo alt-auto; alternativas_reales; doble sbin update-initramfs
    correr instalar.sh
    comprobar "alternativas: activa el tema" [ "$(valor_alt Value)" = "$(TEMA)/paraguay.plymouth" ]
    correr desinstalar.sh
    comprobar "alternativas (modo automático): al desinstalar vuelve a la de mayor prioridad" \
        [ "$(valor_alt Status) $(valor_alt Value)" = "auto $RAIZ/usr/share/plymouth/themes/bgrt/bgrt.plymouth" ]

    nuevo alt-manual; alternativas_reales; doble sbin update-initramfs
    "$SB/bin/update-alternatives" --quiet --set default.plymouth "$RAIZ/usr/share/plymouth/themes/spinner/spinner.plymouth"
    correr instalar.sh; correr instalar.sh
    correr desinstalar.sh
    comprobar "alternativas (elección manual): al desinstalar repone el tema que el usuario había elegido" \
        [ "$(valor_alt Status) $(valor_alt Value)" = "manual $RAIZ/usr/share/plymouth/themes/spinner/spinner.plymouth" ]

    # si falla la regeneración del initramfs, la instalación se deshace
    nuevo alt-falla; alternativas_reales; doble sbin update-initramfs 1
    correr instalar.sh; rc=$?
    comprobar "falla del initramfs: instalar.sh sale con error" [ "$rc" -ne 0 ]
    comprobar "falla del initramfs: el tema no queda activado" [ "$(valor_alt Value)" = "$RAIZ/usr/share/plymouth/themes/bgrt/bgrt.plymouth" ]
    comprobar "falla del initramfs: no quedan archivos del tema" [ ! -e "$(TEMA)" ]

    # hook de initramfs de Debian/Ubuntu sin fontconfig: no se activa nada
    nuevo hook; alternativas_reales; doble sbin update-initramfs
    mkdir -p "$RAIZ/usr/share/initramfs-tools/hooks"
    printf 'cp -dRp /etc/fonts/fonts.conf "${DESTDIR}/etc/fonts"\nfc-cache -s -y "${DESTDIR}"\n' \
        > "$RAIZ/usr/share/initramfs-tools/hooks/plymouth"
    correr instalar.sh; rc=$?
    comprobar "sin fontconfig: instalar.sh se niega antes de tocar nada" [ "$rc" -ne 0 ]
    comprobar "sin fontconfig: no copia ni activa" [ ! -e "$(TEMA)" ]
    mkdir -p "$RAIZ/etc/fonts"; : > "$RAIZ/etc/fonts/fonts.conf"; doble bin fc-cache
    correr instalar.sh
    comprobar "con fontconfig: instala normalmente" [ "$(valor_alt Value)" = "$(TEMA)/paraguay.plymouth" ]
else
    echo "OMITE alternativas: este sistema no tiene update-alternatives"
fi

# --- C: sin ninguna de las dos herramientas: se edita plymouthd.conf ---
nuevo conf-nueva; doble sbin dracut
rm -f "$RAIZ/etc/plymouth/plymouthd.conf"
correr instalar.sh; correr instalar.sh
comprobar "conf: activa el tema y regenera con dracut" conf_dice paraguay
comprobar "conf: llama a dracut --force" llamo "dracut --force"
correr desinstalar.sh
comprobar "conf (sin tema previo): tras reinstalar y desinstalar no queda Theme=paraguay" \
    [ -z "$(grep '^Theme=' "$RAIZ/etc/plymouth/plymouthd.conf")" ]
nuevo conf-previa; doble sbin dracut
printf '[Daemon]\nTheme=spinner\nShowDelay=0\n' > "$RAIZ/etc/plymouth/plymouthd.conf"
correr instalar.sh
printf 'DeviceTimeout=8\n' >> "$RAIZ/etc/plymouth/plymouthd.conf"       # cambio posterior del usuario
correr desinstalar.sh
comprobar "conf (con tema previo): al desinstalar vuelve Theme=spinner" conf_dice spinner
comprobar "conf: no pisa los cambios hechos después de instalar" grep -qx "DeviceTimeout=8" "$RAIZ/etc/plymouth/plymouthd.conf"

# --- D: opciones que no deben tocar el arranque ---
nuevo no-activar; doble_psdt; doble sbin update-initramfs
printf '[Daemon]\nTheme=spinner\n' > "$RAIZ/etc/plymouth/plymouthd.conf"
correr instalar.sh --no-activar
comprobar "--no-activar: copia los archivos" [ -f "$(TEMA)/paraguay.script" ]
comprobar "--no-activar: no cambia el tema ni regenera el initramfs" [ ! -s "$LOG" ]
correr desinstalar.sh --sin-initramfs
comprobar "--no-activar: se desinstala sin tocar el tema activo" conf_dice spinner

nuevo simular; doble_psdt; doble sbin update-initramfs
printf '[Daemon]\nTheme=spinner\n' > "$RAIZ/etc/plymouth/plymouthd.conf"
antes="$(cd "$RAIZ" && ls -R . | sort | cksum)"
correr instalar.sh --simular; rc=$?
comprobar "--simular: sale con 0" [ "$rc" -eq 0 ]
comprobar "--simular: no escribe nada" [ "$antes" = "$(cd "$RAIZ" && ls -R . | sort | cksum)" ]
comprobar "--simular: no ejecuta herramientas que cambien el sistema" [ -z "$(grep -v '^plymouth-set-default-theme $' "$LOG")" ]

nuevo prefijo
correr instalar.sh --prefijo "$SB/pre fijo"
comprobar "--prefijo: instala bajo el directorio dado, aunque tenga espacios" [ -f "$SB/pre fijo$RAIZ/usr/share/plymouth/themes/paraguay/paraguay.plymouth" ]
correr desinstalar.sh --prefijo "$SB/pre fijo"
comprobar "--prefijo: se desinstala" [ ! -e "$SB/pre fijo$RAIZ/usr/share/plymouth/themes/paraguay" ]

echo
if [ "$FALLAN" -eq 0 ]; then
    echo "INSTALADOR: PASA ($PASAN/$PASAN comprobaciones)"
else
    echo "INSTALADOR: FALLA ($PASAN/$((PASAN + FALLAN)) comprobaciones)"
    exit 1
fi
