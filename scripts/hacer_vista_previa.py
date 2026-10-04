#!/usr/bin/env python3
"""Arma docs/vista-previa.gif con fotogramas capturados del Plymouth real.

Corre el tema en el banco de pruebas, busca un tramo de la captura que sea un
bucle exacto (un fotograma que vuelve a aparecer idéntico un ciclo después),
recorta la bandera y lo guarda como GIF animado. No es una simulación: cada
cuadro del GIF salió de plymouthd.

Ejemplos:
  python scripts/hacer_vista_previa.py
  python scripts/hacer_vista_previa.py --ancho 480 --colores 48
  python scripts/hacer_vista_previa.py --reusar --cps 15      # rehace el GIF con la última captura
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_tema as gen  # noqa: E402
import validar_tema as val  # noqa: E402

# amarillo y verde del escudo (base, aclarado y oscurecido) y su gris
COLORES_DEL_ESCUDO = [(0xFF, 0xD5, 0x00), (0xFF, 0xEA, 0x80), (0xCC, 0xAA, 0x00),
                      (0x00, 0xA6, 0x51), (0x7F, 0xD2, 0xA8), (0x00, 0x7A, 0x3C), (0x4A, 0x4F, 0x59)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 2)[2])
    ap.add_argument("--tamano", default="1280x720", help="resolución de la captura (por defecto 1280x720)")
    ap.add_argument("--ancho", type=int, default=560, help="ancho del GIF en píxeles (por defecto 560)")
    ap.add_argument("--cps", type=int, default=20, help="cuadros por segundo del GIF (por defecto 20)")
    ap.add_argument("--reusar", action="store_true", help="no correr el banco: usar la última captura")
    ap.add_argument("--colores", type=int, default=112, help="colores de la paleta del GIF (por defecto 112)")
    ap.add_argument("--salida", type=Path, default=gen.RAIZ / "docs" / "vista-previa.gif")
    args = ap.parse_args()

    from PIL import Image

    if args.reusar:
        salida = val.DIR_SALIDA / "vista-previa"
        m = json.loads((salida / "metricas.json").read_text(encoding="utf-8-sig")) | {"_rc": 0}
    else:
        m, salida = val.correr_banco("vista-previa", ["--segundos", "9", "--tamano", args.tamano])
    if not m or m["_rc"] != 0 or m["errores_script"]:
        print(f"error: la corrida del banco falló (código {m.get('_rc')})", file=sys.stderr)
        return 1
    fot = val.Fotogramas(salida)
    numeros = [int(r["n"]) for r in fot.filas if float(r["pts_s"]) - fot.t0 >= 2.2]

    def cuadro(n: int):
        return Image.open(fot.dir / f"f_{n:05d}.png").convert("RGB")

    # Bucle exacto: un cuadro que reaparece idéntico al menos 2 s después. El banco no llega a
    # mostrar todos los cuadros, así que alguno reaparece recién a las dos vueltas: se prueban
    # varios y se elige la vuelta más corta.
    fps = m["fps_captura"]
    inicio = fin = None
    for a in numeros[:12]:
        ref = cuadro(a)
        for b in numeros:
            if b - a >= 2 * fps and val.iguales(ref, cuadro(b)):
                if inicio is None or b - a < fin - inicio:
                    inicio, fin = a, b
                break
    if not inicio:
        print("error: no encontré un bucle exacto en la captura", file=sys.stderr)
        return 1
    # el GIF va a menos cuadros por segundo que la captura: se elige el fotograma más cercano a cada instante
    duracion = (fin - inicio) / fps
    cantidad = max(2, round(duracion * args.cps))
    cuadros = [cuadro(inicio + round(k * (fin - inicio) / cantidad)) for k in range(cantidad)]

    # recorte: la caja que recorre la bandera en todo el bucle, con margen
    w, h = cuadros[0].size
    paso = val.paso_esperado(w, h)
    cajas = [val.caja(val.mascara_encendida(c)) for c in cuadros]
    x0 = max(0, min(c[0] for c in cajas) - 2 * paso)
    y0 = max(0, min(c[1] for c in cajas) - 2 * paso)
    x1 = min(w, max(c[2] for c in cajas) + 2 * paso)
    y1 = min(h, max(c[3] for c in cajas) + 2 * paso)
    alto = round(args.ancho * (y1 - y0) / (x1 - x0))
    chicos = [c.crop((x0, y0, x1, y1)).resize((args.ancho, alto), Image.LANCZOS) for c in cuadros]

    # Paleta común a todos los cuadros, para que el GIF no parpadee. Los colores del escudo se
    # agregan a mano: ocupan tan pocos píxeles que la reducción automática los descarta.
    libres = args.colores - len(COLORES_DEL_ESCUDO)
    muestra = Image.new("RGB", (args.ancho, alto * 4))
    for i in range(4):
        muestra.paste(chicos[i * len(chicos) // 4], (0, i * alto))
    valores = muestra.quantize(colors=libres, method=Image.Quantize.MEDIANCUT).getpalette()[:3 * libres]
    for rgb in COLORES_DEL_ESCUDO:
        valores += list(rgb)
    paleta = Image.new("P", (1, 1))
    paleta.putpalette(valores + valores[:3] * (256 - len(valores) // 3))
    indexados = [c.quantize(palette=paleta, dither=Image.Dither.NONE) for c in chicos]

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    indexados[0].save(args.salida, save_all=True, append_images=indexados[1:], duration=round(1000 / args.cps),
                      loop=0, optimize=True, disposal=1)
    print(f"{args.salida.relative_to(gen.RAIZ)}: {len(indexados)} cuadros de {args.ancho}x{alto} a {args.cps} por segundo, "
          f"{args.salida.stat().st_size / 1024:.0f} KiB (bucle de {duracion:.2f} s, cuadros {inicio}-{fin - 1} "
          f"de la captura a {args.tamano})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
