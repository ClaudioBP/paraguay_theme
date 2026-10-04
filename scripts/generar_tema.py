#!/usr/bin/env python3
"""Genera las imágenes y el bloque de datos del tema de Plymouth «paraguay».

El tema dibuja la bandera con sprites que son *tramos* verticales de puntos
(por defecto 4 puntos) y los mueve con una tabla de onda calculada en el propio
script de Plymouth. Este generador produce, para cada paso de grilla soportado:

  paraguay/p<PASO>.png   atlas de tramos de la grilla principal
  paraguay/e<PASO>.png   atlas de tramos del escudo (sub-grilla fina)
  paraguay/d<PASO>.png   atlas de los puntos del diálogo (apagado / encendido)

y reescribe, dentro de paraguay/paraguay.script, el bloque delimitado por
«DATOS GENERADOS», con las constantes que el script comparte con las imágenes.

Cada atlas es una cuadrícula uniforme: una fila por familia (secuencia de
colores del tramo) y una columna por aspecto (tamaño × brillo). El script
recorta las celdas dividiendo el ancho y el alto del atlas, así que no necesita
conocer medidas en píxeles.

La bandera (proporción, colores, mapa del escudo) sale del bloque JSON de
docs/investigacion/bandera-paraguay.md, que es la fuente de verdad.

Uso:
  python scripts/generar_tema.py              # regenera todo
  python scripts/generar_tema.py --comprobar  # sale con 1 si algo está desactualizado
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOC_BANDERA = RAIZ / "docs" / "investigacion" / "bandera-paraguay.md"
DIR_TEMA = RAIZ / "paraguay"
ARCHIVO_SCRIPT = DIR_TEMA / "paraguay.script"

MARCA_INICIO = "# >>> DATOS GENERADOS por scripts/generar_tema.py -- no editar a mano"
MARCA_FIN = "# <<< FIN DE DATOS GENERADOS"

# --------------------------------------------------------------------------
# Diseño. Cambiar aquí y regenerar; el script de Plymouth no repite estos valores.
# --------------------------------------------------------------------------
PASOS = [8, 10, 12, 14, 16, 20, 24, 32]   # pasos de grilla (px) con atlas propio
COLS, FILAS = 44, 24                       # grilla principal (8 filas por franja)
MAPA_ESCUDO = "M17"                        # máscara de la sub-grilla del escudo
TRAMO = 4                                  # puntos por tramo vertical (1, 2, 4 u 8)
FPS = 30                                   # refrescos por segundo que pide el tema

# Azul fiel (#0038A8) en vez del azul realzado que el documento propone para fondo
# oscuro: ver DECISIONES.md. El resto de la paleta es la columna «oscuro».
COLOR_FRANJA_AZUL = "#0038A8"
FONDO = (0, 0, 0)

# Aspectos: NT tamaños × NB brillos. El índice central de cada eje es el reposo.
DIAMETROS_PUNTO = [0.50, 0.58, 0.66, 0.74, 0.82]       # diámetro / paso
DIAMETROS_SUBPUNTO = [0.64, 0.71, 0.78, 0.85, 0.92]    # diámetro / sub-paso
NT = len(DIAMETROS_PUNTO)
# Por letra: multiplicadores de sombra (3 niveles, del más oscuro al más claro)
# y mezcla hacia blanco en las crestas (3 niveles). El nivel central es el color base.
SOMBRAS = {
    "*": [0.62, 0.76, 0.89],
    "A": [0.80, 0.87, 0.94],      # el azul casi no se oscurece: sobre negro se perdería
    "B": [0.60, 0.74, 0.88],
    "b": [0.60, 0.74, 0.88],
    "n": [0.75, 0.84, 0.93],
    "a": [0.70, 0.80, 0.90],
}
BRILLOS = {
    "*": [0.10, 0.20, 0.32],
    "A": [0.10, 0.22, 0.36],
    "B": [0.35, 0.70, 1.00],      # blanco base #E8E8E8; la cresta llega a #FFFFFF
    "b": [0.35, 0.70, 1.00],
    "n": [0.04, 0.08, 0.12],
    "a": [0.08, 0.16, 0.24],
}
NB = len(SOMBRAS["*"]) + 1 + len(BRILLOS["*"])

# Onda. Distancias en pasos de grilla; u = 0 en el asta, 1 en el batiente.
ONDA = dict(
    ciclo_s=3.0,          # duración del bucle
    retardo_fila_s=0.01,  # retardo por fila entre bandas de tramos (pliegue diagonal)
    base=0.05, exp=1.1,   # envolvente: base + (1 - base) * u^exp
    k1=1.2, n1=2,         # armónica principal: ondas a lo largo, ciclos por bucle
    k2=2.5, n2=3, a2=0.30, fase2=1.3,   # armónica secundaria (n1 y n2 coprimos: ver Diseno)
    ax=0.5, ay=1.2,       # amplitud horizontal y vertical
    caida=0.9,            # caída por gravedad hacia el batiente
    encoge=0.7, encoge_z=0.4,   # acortamiento horizontal por los pliegues
    fase_luz=0.9,         # desfase de la luz respecto de la cresta
    luz0=0.35, luz1=0.65, # el contraste de luz crece con la envolvente
)
REVELADO_S = 1.4          # entrada: la bandera aparece desde el asta
REVELADO_ANCHO = 0.35     # ancho del frente de revelado, en unidades de u

# Diálogo (contraseña, pregunta, progreso de actualización)
RANURAS = 24
DIAMETRO_RANURA = 0.42    # diámetro / paso
COLOR_RANURA_APAGADA = "#4A4F59"
COLOR_RANURA_ENCENDIDA = "#E8E8E8"

SUPERMUESTREO = 8


# --------------------------------------------------------------------------
def leer_bandera(doc: Path) -> dict:
    texto = doc.read_text(encoding="utf-8")
    m = re.search(r"<!-- mapas-json:inicio -->\s*```json\s*(.*?)```\s*<!-- mapas-json:fin -->", texto, re.S)
    if not m:
        raise SystemExit(f"error: no encuentro el bloque mapas-json en {doc}")
    return json.loads(m.group(1))


def hex_a_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class Diseno:
    """Geometría y listas de tramos, independientes del paso en píxeles."""

    def __init__(self, bandera: dict, tramo: int, fps: int):
        if FILAS % 3 or FILAS % tramo:
            raise SystemExit("error: FILAS debe ser múltiplo de 3 y de TRAMO")
        geo = bandera["geometria"]
        mapa = bandera["mapas"][MAPA_ESCUDO]
        if mapa["tipo"] != "subgrilla" or mapa["grilla"] != {"filas": FILAS, "columnas": COLS}:
            raise SystemExit(f"error: el mapa {MAPA_ESCUDO} no es una sub-grilla para {FILAS}x{COLS}")
        self.tramo, self.fps = tramo, fps
        self.celdas = mapa["celdas"]
        self.lado = mapa["lado"]
        self.medio = (self.lado - 1) / 2
        self.nbandas = FILAS // tramo
        # paso vertical / paso horizontal, para que la proporción sea exacta
        self.pv = (geo["proporcion_alto"] / geo["proporcion_ancho"]) * COLS / FILAS
        k = mapa.get("diametro_escudo_sobre_franja", geo["diametro_escudo_sobre_franja"])
        diametro = k * (FILAS / 3) * self.pv                 # en pasos
        self.subp = diametro / self.lado                     # sub-paso / paso
        self.retiro = diametro / 2 + geo["margen_retiro_en_pasos"]

        self.paleta = {l: hex_a_rgb(v["oscuro"]) for l, v in bandera["leyenda"].items() if v["oscuro"]}
        self.paleta["A"] = hex_a_rgb(COLOR_FRANJA_AZUL)

        self._tramos_principales()
        self._piezas_escudo()
        self._columnas_tabla()

        # Con n1 y n2 coprimos la onda tarda el ciclo entero en repetirse; si tuvieran un divisor
        # común se repetiría antes y parte de la tabla del script sería trabajo y memoria de más.
        if math.gcd(ONDA["n1"], ONDA["n2"]) != 1:
            raise SystemExit("error: ONDA n1 y n2 deben ser coprimos")
        self.ciclo = round(ONDA["ciclo_s"] * fps)            # pasos de tiempo del bucle
        self.ret = max(1, round(ONDA["retardo_fila_s"] * tramo * fps))

    @staticmethod
    def franja(fila: int) -> str:
        return "RBA"[fila * 3 // FILAS]

    def retirado(self, c: int, f: int) -> bool:
        dx = c + 0.5 - COLS / 2
        dy = (f + 0.5 - FILAS / 2) * self.pv
        return math.hypot(dx, dy) < self.retiro

    def _tramos_principales(self) -> None:
        self.fam_p: list[str] = []       # familias del atlas principal
        self.fam_banda: list[int] = []   # familia regular de cada banda
        self.exc: dict[int, int] = {}    # banda*100+col -> familia+1, o -1 si no hay tramo
        for b in range(self.nbandas):
            filas = range(b * self.tramo, (b + 1) * self.tramo)
            regular = "".join(self.franja(f) for f in filas)
            if regular not in self.fam_p:
                self.fam_p.append(regular)
            self.fam_banda.append(self.fam_p.index(regular))
        for b in range(self.nbandas):
            filas = range(b * self.tramo, (b + 1) * self.tramo)
            for c in range(COLS):
                sec = "".join("." if self.retirado(c, f) else self.franja(f) for f in filas)
                if sec == self.fam_p[self.fam_banda[b]]:
                    continue
                if not sec.strip("."):
                    self.exc[b * 100 + c] = -1
                    continue
                if sec not in self.fam_p:
                    self.fam_p.append(sec)
                self.exc[b * 100 + c] = self.fam_p.index(sec) + 1

    def _piezas_escudo(self) -> None:
        """Una pieza por sub-columna del escudo, todas en la banda que contiene su centro.

        El escudo cae a caballo de dos bandas de tramos. Partir cada sub-columna entre las
        dos (cada mitad con su retardo) hacía que las mitades se encimaran o se separaran
        al pasar la cresta, justo sobre la estrella; entera, cada sub-columna se mueve rígida.
        """
        self.fam_e: list[str] = []
        self.piezas: list[tuple[int, int, int, int]] = []   # (sub-columna, banda, sub-fila inicial, familia)
        banda = min(self.nbandas - 1, int(FILAS / 2 / self.tramo + 1e-9))
        for i in range(self.lado):
            js = [j for j in range(self.lado) if self.celdas[j][i] != "."]
            if not js:
                continue
            sec = "".join(self.celdas[j][i] for j in range(js[0], js[-1] + 1))
            if sec not in self.fam_e:
                self.fam_e.append(sec)
            self.piezas.append((i, banda, js[0], self.fam_e.index(sec)))
        self.largo_pieza = max(len(s) for s in self.fam_e)

    def _columnas_tabla(self) -> None:
        """Columnas de la tabla de onda: las COLS principales y las sub-columnas del escudo."""
        centros = [c + 0.5 for c in range(COLS)]
        centros += [COLS / 2 + (i - self.medio) * self.subp for i in range(self.lado)]
        self.cu = [(x - 0.5) / (COLS - 1) for x in centros]
        self.ce = [ONDA["base"] + (1 - ONDA["base"]) * max(u, 0.0) ** ONDA["exp"] for u in self.cu]

    # -- medidas en píxeles para un paso dado -------------------------------
    def celda_principal(self, paso: int) -> tuple[int, int]:
        return paso, math.ceil(self.tramo * self.pv * paso - 1e-9)

    def celda_escudo(self, paso: int) -> tuple[int, int]:
        s = self.subp * paso
        return math.ceil(s - 1e-9), math.ceil(self.largo_pieza * s - 1e-9)

    @staticmethod
    def celda_dialogo(paso: int) -> tuple[int, int]:
        lado = max(4, math.ceil(DIAMETRO_RANURA * paso) + 2)
        return lado, lado


# --------------------------------------------------------------------------
def color_aspecto(letra: str, ib: int, paleta: dict) -> tuple[int, int, int]:
    base = paleta[letra]
    sombras = SOMBRAS.get(letra, SOMBRAS["*"])
    brillos = BRILLOS.get(letra, BRILLOS["*"])
    if ib < len(sombras):
        m = sombras[ib]
        return tuple(round(FONDO[i] + (base[i] - FONDO[i]) * m) for i in range(3))
    if ib == len(sombras):
        return base
    t = brillos[ib - len(sombras) - 1]
    return tuple(round(base[i] + (255 - base[i]) * t) for i in range(3))


def pintar_punto(celda, cx: float, cy: float, diametro: float, rgb) -> None:
    """Pinta un disco con bordes suavizados (alfa recta, color constante) dentro de la celda."""
    from PIL import Image, ImageDraw

    r = diametro / 2
    x0, y0 = max(0, math.floor(cx - r - 1)), max(0, math.floor(cy - r - 1))
    x1, y1 = min(celda.width, math.ceil(cx + r + 1)), min(celda.height, math.ceil(cy + r + 1))
    if x1 <= x0 or y1 <= y0:
        return
    ss = SUPERMUESTREO
    mascara = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    ImageDraw.Draw(mascara).ellipse(
        ((cx - r - x0) * ss, (cy - r - y0) * ss, (cx + r - x0) * ss - 1, (cy + r - y0) * ss - 1), fill=255)
    mascara = mascara.resize((x1 - x0, y1 - y0), Image.BOX)
    # Plymouth, al recortar el atlas con Image.Crop, mezcla cada celda sobre un lienzo
    # transparente y en esa mezcla vuelve a multiplicar el color por el alfa: los bordes
    # suavizados llegan a pantalla con color × alfa² y los puntos chicos, que son casi todo
    # borde, se apagan. Guardar la raíz cuadrada del alfa lo compensa.
    mascara = mascara.point(lambda v: round(255 * (v / 255) ** 0.5))
    capa = Image.new("RGBA", mascara.size, tuple(rgb) + (0,))
    capa.putalpha(mascara)
    celda.alpha_composite(capa, (x0, y0))


def atlas_de_tramos(familias, ancho: int, alto: int, paso_v: float, diametros, paso_base: float, paleta):
    """Una fila por familia y una columna por aspecto (it * NB + ib)."""
    from PIL import Image

    atlas = Image.new("RGBA", (ancho * NT * NB, alto * len(familias)), (0, 0, 0, 0))
    for f, sec in enumerate(familias):
        for it in range(NT):
            for ib in range(NB):
                celda = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
                for m, letra in enumerate(sec):
                    if letra == ".":
                        continue
                    pintar_punto(celda, ancho / 2, (m + 0.5) * paso_v, diametros[it] * paso_base,
                                 color_aspecto(letra, ib, paleta))
                atlas.paste(celda, ((it * NB + ib) * ancho, f * alto))
    return atlas


def atlas_dialogo(paso: int):
    from PIL import Image

    lado, _ = Diseno.celda_dialogo(paso)
    atlas = Image.new("RGBA", (lado * 2, lado), (0, 0, 0, 0))
    for n, color in enumerate((COLOR_RANURA_APAGADA, COLOR_RANURA_ENCENDIDA)):
        celda = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        pintar_punto(celda, lado / 2, lado / 2, DIAMETRO_RANURA * paso, hex_a_rgb(color))
        atlas.paste(celda, (n * lado, 0))
    return atlas


def png(imagen) -> bytes:
    buf = io.BytesIO()
    imagen.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# --------------------------------------------------------------------------
def num(x: float) -> str:
    """Número en la sintaxis del script de Plymouth: sin exponente ni punto inicial."""
    if float(x) == int(x):
        return str(int(x))
    s = f"{x:.6f}".rstrip("0")
    return s + "0" if s.endswith(".") else s


def lista(valores, por_linea: int = 12) -> str:
    partes = [num(v) for v in valores]
    if len(partes) <= por_linea:
        return "[" + ", ".join(partes) + "]"
    filas = [", ".join(partes[i:i + por_linea]) for i in range(0, len(partes), por_linea)]
    return "[\n    " + ",\n    ".join(filas) + "]"


def bloque_datos(d: Diseno) -> str:
    o = ONDA
    dos_pi = 2 * math.pi
    lin = [MARCA_INICIO]
    lin.append(f"# grilla {FILAS}x{COLS}, escudo {MAPA_ESCUDO}, tramos de {d.tramo}, {d.fps} refrescos por segundo")
    lin.append(f"FPS = {d.fps};")
    lin.append(f"PASOS = {lista(PASOS)};")
    lin.append(f"NPASOS = {len(PASOS)};")
    lin.append(f"COLS = {COLS};")
    lin.append(f"NBANDAS = {d.nbandas};")
    lin.append(f"ALTO_BANDA = {num(d.tramo * d.pv)};      # alto de una banda de tramos, en pasos")
    lin.append(f"ALTO_BANDERA = {num(FILAS * d.pv)};    # alto de la bandera, en pasos")
    lin.append(f"NT = {NT};")
    lin.append(f"NB = {NB};")
    lin.append(f"NFP = {len(d.fam_p)};                 # familias (filas) del atlas principal p<paso>.png")
    lin.append(f"NFE = {len(d.fam_e)};                # familias (filas) del atlas del escudo e<paso>.png")
    lin.append(f"FAMB = {lista(d.fam_banda)};   # familia regular de cada banda")
    lin.append("# tramos recortados por el escudo: banda * 100 + columna -> familia + 1 (-1: sin tramo)")
    lin.append("EXC = [];")
    claves = sorted(d.exc)
    for i in range(0, len(claves), 4):
        lin.append(" ".join(f"EXC[{k}] = {d.exc[k]};" for k in claves[i:i + 4]))
    lin.append(f"SUBP = {num(d.subp)};            # sub-paso del escudo / paso")
    lin.append(f"EMED = {num(d.medio)};                # sub-columna central del escudo")
    lin.append("# piezas del escudo: sub-columna, banda, sub-fila inicial, familia")
    lin.append(f"NEP = {len(d.piezas)};")
    lin.append("EP = [")
    for i in range(0, len(d.piezas), 6):
        trozo = ", ".join("[" + ", ".join(str(v) for v in p) + "]" for p in d.piezas[i:i + 6])
        lin.append("    " + trozo + ("," if i + 6 < len(d.piezas) else "];"))
    lin.append(f"NK = {len(d.cu)};                 # columnas de la tabla de onda: {COLS} principales + {d.lado} del escudo")
    lin.append(f"CU = {lista(d.cu, 8)};")
    lin.append(f"CE = {lista(d.ce, 8)};")
    lin.append("# onda (ver ONDA en scripts/generar_tema.py)")
    lin.append(f"CICLO = {d.ciclo};")
    lin.append(f"RET = {d.ret};")
    lin.append(f"A1 = {num(dos_pi * o['k1'])};")
    lin.append(f"W1 = {num(dos_pi * o['n1'] / d.ciclo)};")
    lin.append(f"A2 = {num(dos_pi * o['k2'])};")
    lin.append(f"W2 = {num(dos_pi * o['n2'] / d.ciclo)};")
    lin.append(f"F2 = {num(o['fase2'])};")
    lin.append(f"AM2 = {num(o['a2'])};")
    lin.append(f"NORM = {num(1 / (1 + o['a2']))};")
    lin.append(f"AX = {num(o['ax'])};")
    lin.append(f"AY = {num(o['ay'])};")
    lin.append(f"CAIDA = {num(o['caida'])};")
    lin.append(f"ENCOGE = {num(o['encoge'])};")
    lin.append(f"ENCOGE_Z = {num(o['encoge_z'])};")
    lin.append(f"COSFL = {num(math.cos(o['fase_luz']))};")
    lin.append(f"SINFL = {num(math.sin(o['fase_luz']))};")
    lin.append(f"LUZ0 = {num(o['luz0'])};")
    lin.append(f"LUZ1 = {num(o['luz1'])};")
    lin.append(f"REV_T = {round(REVELADO_S * d.fps)};")
    lin.append(f"REV_A = {num(REVELADO_ANCHO)};")
    lin.append(f"RANURAS = {RANURAS};")
    lin.append(MARCA_FIN)
    return "\n".join(lin)


def script_con_bloque(texto: str, bloque: str) -> str:
    i, j = texto.find(MARCA_INICIO), texto.find(MARCA_FIN)
    if i < 0 or j < i:
        raise SystemExit(f"error: {ARCHIVO_SCRIPT} no tiene las marcas del bloque de datos generados")
    return texto[:i] + bloque + texto[j + len(MARCA_FIN):]


def generar(tramo: int, fps: int) -> tuple[dict[Path, bytes], Diseno]:
    """Devuelve el contenido de cada archivo del tema, sin escribir nada."""
    d = Diseno(leer_bandera(DOC_BANDERA), tramo, fps)
    archivos: dict[Path, bytes] = {}
    for paso in PASOS:
        ancho, alto = d.celda_principal(paso)
        archivos[DIR_TEMA / f"p{paso}.png"] = png(atlas_de_tramos(
            d.fam_p, ancho, alto, d.pv * paso, DIAMETROS_PUNTO, paso, d.paleta))
        ancho, alto = d.celda_escudo(paso)
        archivos[DIR_TEMA / f"e{paso}.png"] = png(atlas_de_tramos(
            d.fam_e, ancho, alto, d.subp * paso, DIAMETROS_SUBPUNTO, d.subp * paso, d.paleta))
        archivos[DIR_TEMA / f"d{paso}.png"] = png(atlas_dialogo(paso))
    texto = ARCHIVO_SCRIPT.read_bytes().decode("utf-8")
    archivos[ARCHIVO_SCRIPT] = script_con_bloque(texto, bloque_datos(d)).encode("utf-8")
    return archivos, d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="Ejemplos:\n  python scripts/generar_tema.py\n"
                                        "  python scripts/generar_tema.py --comprobar")
    ap.add_argument("--tramo", type=int, default=TRAMO, choices=(1, 2, 4, 8),
                    help=f"puntos por tramo vertical (por defecto {TRAMO}); 1 = un sprite por punto")
    ap.add_argument("--fps", type=int, default=FPS, help=f"refrescos por segundo del tema (por defecto {FPS})")
    ap.add_argument("--comprobar", action="store_true",
                    help="no escribe: sale con 1 si los archivos del tema no coinciden con lo que se generaría")
    args = ap.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("error: hace falta Pillow (pip install pillow)", file=sys.stderr)
        return 3

    archivos, d = generar(args.tramo, args.fps)
    esperados = {p.name for p in archivos}
    sobrantes = sorted(p.name for p in DIR_TEMA.glob("*.png") if p.name not in esperados)
    distintos = [p for p, datos in archivos.items() if not p.exists() or p.read_bytes() != datos]

    if args.comprobar:
        for p in distintos:
            print(f"DESACTUALIZADO  {p.relative_to(RAIZ)}")
        for n in sobrantes:
            print(f"SOBRA           paraguay/{n}")
        ok = not distintos and not sobrantes
        print(f"comprobar: {'PASA' if ok else 'FALLA'} ({len(archivos)} archivos, "
              f"{len(distintos)} desactualizados, {len(sobrantes)} sobrantes)")
        return 0 if ok else 1

    for p in distintos:
        p.write_bytes(archivos[p])
    for n in sobrantes:
        (DIR_TEMA / n).unlink()
    total = sum(len(v) for p, v in archivos.items() if p.suffix == ".png")
    print(f"tramos de {d.tramo} | bandas {d.nbandas} | familias: {len(d.fam_p)} principales, {len(d.fam_e)} del escudo")
    print(f"sprites: {COLS * d.nbandas - sum(1 for v in d.exc.values() if v < 0)} tramos + {len(d.piezas)} piezas del escudo")
    print(f"archivos: {len(archivos)} ({len(distintos)} escritos, {len(sobrantes)} borrados); PNG: {total / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
