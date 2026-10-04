#!/usr/bin/env python3
"""Valida el tema «paraguay» de extremo a extremo, sin intervención visual.

1. Estático: los archivos de paraguay/ coinciden con lo que produce el
   generador, tienen finales LF y sin BOM, el script evita las trampas del
   lenguaje de Plymouth y los atlas tienen los colores de la bandera.
2. Dinámico: corre el tema en el Plymouth real (scripts/banco_plymouth.sh) y
   comprueba por píxeles, sobre los fotogramas capturados, que se ve una
   bandera paraguaya (roja arriba, blanca al medio, azul abajo, escudo verde y
   amarillo al centro), que se mueve, y que el diálogo de clave, los mensajes,
   el apagado y la barra de actualización aparecen donde deben.

Sale con 0 si todo pasa. Corre en Windows (usa WSL para el banco) y en Linux.

Ejemplos:
  python scripts/validar_tema.py                # todo (unos 8 minutos)
  python scripts/validar_tema.py --rapida       # estático + una corrida del banco
  python scripts/validar_tema.py --sin-banco    # solo lo estático (segundos)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_tema as gen  # noqa: E402

RAIZ = gen.RAIZ
BANCO = RAIZ / "scripts" / "banco_plymouth.sh"
DIR_SALIDA = RAIZ / "output" / "temporales" / "validacion"
UMBRAL = 24          # un píxel cuenta como encendido si algún canal supera esto

resultados: list[tuple[bool, str, str]] = []


def anotar(ok: bool, nombre: str, detalle: str = "") -> bool:
    resultados.append((bool(ok), nombre, detalle))
    print(f"{'PASA ' if ok else 'FALLA'} {nombre}" + (f"  [{detalle}]" if detalle else ""), flush=True)
    return bool(ok)


# ------------------------------------------------------------------ estático
def codigo_sin_comentarios(texto: str) -> str:
    """Quita comentarios y cadenas del script (los /* */ de Plymouth se anidan)."""
    sal, i, n, prof = [], 0, len(texto), 0
    while i < n:
        c, par = texto[i], texto[i:i + 2]
        if prof:
            if par == "/*":
                prof, i = prof + 1, i + 2
            elif par == "*/":
                prof, i = prof - 1, i + 2
            else:
                i += 1
        elif par == "/*":
            prof, i = 1, i + 2
        elif c == "#" or par == "//":
            while i < n and texto[i] != "\n":
                i += 1
        elif c == '"':
            i += 1
            while i < n and texto[i] != '"':
                i += 2 if texto[i] == "\\" else 1
            i += 1
            sal.append('""')
        else:
            sal.append(c)
            i += 1
    return "".join(sal)


TRAMPAS = [
    (r"'", "comillas simples"),
    (r"\b(true|false|null|undefined)\b", "true/false/null/undefined no existen"),
    (r"\b(var|function|switch)\b", "palabra que el lenguaje no tiene"),
    (r"\?", "operador ternario"),
    (r"\b0x[0-9a-fA-F]+", "literal hexadecimal"),
    (r"\b\d+(\.\d+)?[eE][+-]?\d+", "número con exponente"),
    (r"(?<![\w.])\.\d", "número que empieza con punto"),
    (r";\s*;", "sentencia vacía (;;)"),
    (r"\}\s*;", "; después de }"),
    (r"\bSetPosition\s*\(([^(),]|\([^()]*\))*,([^(),]|\([^()]*\))*\)", "SetPosition sin z"),
    (r"\bMath\.(Floor|Ceil|Round|Pow|Exp|Log)\b", "función de Math inexistente"),
]

# Lo que el script puede llamar. Llamar a algo que no existe no da error en Plymouth
# (devuelve NULL en silencio), así que un nombre mal escrito solo se detecta aquí.
# Solo figura lo que existe desde Plymouth 0.9.5, más SetDisplayHotplugFunction (23.51),
# que en versiones anteriores simplemente no hace nada. String.Length (23.51) queda fuera
# a propósito: en una versión anterior devolvería NULL y rompería los textos.
API_METODOS = {
    "GetWidth", "GetHeight", "Crop", "Scale", "Text", "SetX", "SetY", "SetZ", "SetPosition", "SetOpacity",
    "SetImage", "SubString", "CharAt", "Int", "Min", "Max", "Sin", "Cos", "GetMode", "SetRefreshRate",
    "SetRefreshFunction", "SetBootProgressFunction", "SetDisplayNormalFunction", "SetDisplayPasswordFunction",
    "SetDisplayQuestionFunction", "SetDisplayMessageFunction", "SetHideMessageFunction",
    "SetSystemUpdateFunction", "SetDisplayHotplugFunction",
}
API_FUNCIONES = {"Image", "Sprite"}


def tono_correcto(letra: str, rgb) -> bool:
    """El color de un punto conserva el tono de su letra en cualquier nivel de sombra o brillo."""
    r, g, b = rgb
    if letra == "R":
        return r > 1.8 * max(g, b)
    if letra == "A":
        return b > 1.4 * max(r, g)
    if letra in "Bb":
        return max(rgb) - min(rgb) <= 8 and min(rgb) > 100
    if letra == "v":
        return g > 1.3 * b and g > 1.5 * r
    if letra == "a":
        return r >= g > 1.5 * b
    if letra == "n":
        return max(rgb) - min(rgb) <= 30 and 30 < max(rgb) < 140
    return False


def validar_estatico() -> None:
    archivos, d = gen.generar(gen.TRAMO, gen.FPS)
    esperados = {p.name for p in archivos}
    distintos = [p.name for p, datos in archivos.items() if not p.exists() or p.read_bytes() != datos]
    sobrantes = [p.name for p in gen.DIR_TEMA.glob("*.png") if p.name not in esperados]
    anotar(not distintos and not sobrantes, "paraguay/ coincide con lo que produce el generador",
           f"{len(archivos)} archivos; distintos: {distintos or 'ninguno'}; sobrantes: {sobrantes or 'ninguno'}")

    guion = gen.ARCHIVO_SCRIPT.read_bytes()
    tema = (gen.DIR_TEMA / "paraguay.plymouth").read_bytes()
    anotar(b"\r" not in guion and b"\r" not in tema, "finales de línea LF en .script y .plymouth")
    anotar(not guion.startswith(b"\xef\xbb\xbf") and not tema.startswith(b"\xef\xbb\xbf"), "sin BOM")
    anotar(all(b < 128 for b in guion), "el .script es ASCII puro")
    lineas = tema.decode("utf-8").splitlines()
    dir_tema = "/usr/share/plymouth/themes/paraguay"
    anotar("ModuleName=script" in lineas and f"ImageDir={dir_tema}" in lineas
           and f"ScriptFile={dir_tema}/paraguay.script" in lineas,
           ".plymouth: ModuleName, ImageDir y ScriptFile exactos (el hook de initramfs no tolera espacios)")

    codigo = codigo_sin_comentarios(guion.decode("utf-8"))
    halladas = [f"{motivo}: «{m.group(0)[:30]}»" for patron, motivo in TRAMPAS for m in re.finditer(patron, codigo)]
    anotar(not halladas, "el script evita las trampas conocidas del lenguaje", "; ".join(halladas[:5]))
    anotar(codigo.count("{") == codigo.count("}") and codigo.count("(") == codigo.count(")")
           and codigo.count("[") == codigo.count("]"), "llaves, paréntesis y corchetes balanceados")
    definidas = set(re.findall(r"\bfun\s+([A-Za-z_]\w*)\s*\(", codigo))
    metodos = set(re.findall(r"\.\s*([A-Za-z_]\w*)\s*\(", codigo))
    llamadas = set(re.findall(r"(?<![.\w])([A-Za-z_]\w*)\s*\(", codigo)) - {"if", "for", "while", "fun", "return"}
    desconocidos = sorted((metodos - API_METODOS) | (llamadas - definidas - API_FUNCIONES))
    anotar(not desconocidos, "todo lo que el script llama existe (API de Plymouth o función propia)",
           ", ".join(desconocidos))
    globales_min = sorted(set(re.findall(r"^([a-z_]\w*)\s*=", codigo, re.M)))
    anotar(not globales_min, "sin variables globales en minúsculas (chocarían con los locales)",
           ", ".join(globales_min))

    from PIL import Image
    nl = gen.NT * gen.NB
    reposo = (gen.NT // 2) * gen.NB + len(gen.SOMBRAS["*"])   # aspecto de reposo: tamaño y brillo centrales
    problemas, colores, tonos = [], {}, []
    for paso in gen.PASOS:
        for prefijo, familias in (("p", d.fam_p), ("e", d.fam_e), ("d", None)):
            ruta = gen.DIR_TEMA / f"{prefijo}{paso}.png"
            if not ruta.exists():
                problemas.append(f"falta {ruta.name}")
                continue
            try:
                im = Image.open(ruta).convert("RGBA")
            except Exception as e:          # un PNG dañado no debe tumbar la validación
                problemas.append(f"{ruta.name}: no se puede leer ({e})")
                continue
            if familias is None:
                if im.width % 2:
                    problemas.append(f"{ruta.name}: ancho impar")
                continue
            if im.width % nl or im.height % len(familias):
                problemas.append(f"{ruta.name}: {im.size} no se divide en {nl} x {len(familias)} celdas")
                continue
            if prefijo == "p":
                cw, ch = im.width // nl, im.height // len(familias)
                for f in range(3):   # centro del primer punto de cada familia regular
                    px = im.getpixel((reposo * cw + cw // 2, f * ch + round(d.pv * paso / 2)))
                    colores.setdefault(f, set()).add(px[:3])
            # Cada punto de cada celda existe y conserva su tono. No se usa el generador para
            # calcular lo esperado: un error suyo quedaría a ambos lados de la comparación.
            cw, ch = im.width // nl, im.height // len(familias)
            paso_v = d.pv * paso if prefijo == "p" else d.subp * paso
            for f, sec in enumerate(familias):
                for aspecto in range(nl):
                    for n_punto, letra in enumerate(sec):
                        if letra == ".":
                            continue
                        px = im.getpixel((aspecto * cw + cw // 2, f * ch + min(ch - 1, int((n_punto + 0.5) * paso_v))))
                        if px[3] < 60 or not tono_correcto(letra, px[:3]):
                            tonos.append(f"{ruta.name} familia {sec} aspecto {aspecto} punto {n_punto} ({letra}): {px}")
    anotar(not problemas, f"atlas presentes y divisibles en celdas para los pasos {gen.PASOS}", "; ".join(problemas[:4]))
    anotar(not tonos, "atlas: todos los puntos de todas las celdas están dibujados y conservan su tono",
           f"{len(tonos)} fallas; " + "; ".join(tonos[:3]) if tonos else "")
    esperado = [gen.hex_a_rgb("#D52B1E"), gen.hex_a_rgb("#E8E8E8"), gen.hex_a_rgb("#0038A8")]
    anotar(d.fam_p[:3] == ["R" * d.tramo, "B" * d.tramo, "A" * d.tramo]
           and all(colores.get(f) == {esperado[f]} for f in range(3)),
           "atlas: franjas roja #D52B1E, blanca #E8E8E8 y azul #0038A8, en ese orden, en todos los pasos",
           str({f: sorted(c) for f, c in colores.items()}))


# ------------------------------------------------------------------ dinámico
def ruta_para_banco(p: Path) -> str:
    if platform.system() != "Windows":
        return str(p)
    p = p.resolve()
    return f"/mnt/{p.drive[0].lower()}{p.as_posix()[2:]}"


def correr_banco(nombre: str, extra: list[str], tema: Path = gen.DIR_TEMA) -> tuple[dict, Path]:
    salida = DIR_SALIDA / nombre
    orden = ["bash", ruta_para_banco(BANCO), "probar", ruta_para_banco(tema),
             "--fps", "30", "--salida", ruta_para_banco(salida)] + extra
    if platform.system() == "Windows":
        orden = ["wsl", "--"] + orden
    r = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8", errors="replace")
    archivo = salida / "metricas.json"
    if not archivo.exists():
        anotar(False, f"{nombre}: el banco corrió", f"código {r.returncode}: {(r.stdout + r.stderr)[-300:]}")
        return {}, salida
    m = json.loads(archivo.read_text(encoding="utf-8-sig"))
    m["_rc"] = r.returncode
    return m, salida


def base_del_banco(nombre: str, m: dict, min_fps: float) -> bool:
    """Comprobaciones comunes a toda corrida. Devuelve si vale la pena analizar sus fotogramas."""
    if not m:
        return False
    cargo = anotar(m["_rc"] == 0 and m["renderer"] == "x11" and m["plugin_splash"] == "script",
                   f"{nombre}: Plymouth real cargó el tema (código 0, renderer x11, plugin script)",
                   f"código {m['_rc']}, {m.get('renderer')}, {m.get('plugin_splash')}, {m.get('resolucion')}")
    limpio = anotar(not m["errores_script"] and not m["imagenes_faltantes"],
                    f"{nombre}: sin errores de script ni imágenes faltantes",
                    json.dumps(m["errores_script"][:2], ensure_ascii=False) if m["errores_script"] else "")
    # El umbral es bajo a propósito: con el equipo cargado el banco muestra menos cuadros, y eso
    # no es un defecto del tema. Una bandera inmóvil da menos de 4.
    anotar(m["tasa_animacion_fps"] >= min_fps, f"{nombre}: la animación corre",
           f"{m['tasa_animacion_fps']} cuadros distintos por segundo (mínimo {min_fps})")
    return cargo and limpio


class Fotogramas:
    """Acceso a los fotogramas de una corrida por tiempo desde que apareció el splash."""

    def __init__(self, salida: Path):
        self.dir = salida / "frames"
        with open(salida / "logs" / "fotogramas.csv", newline="", encoding="utf-8") as f:
            self.filas = list(csv.DictReader(f))
        encendidas = [r for r in self.filas if float(r["fraccion_no_negra"]) > 0]
        self.t0 = float(encendidas[0]["pts_s"]) if encendidas else 0.0
        self.duracion = float(self.filas[-1]["pts_s"]) - self.t0

    def en(self, t: float):
        fila = min(self.filas, key=lambda r: abs(float(r["pts_s"]) - self.t0 - t))
        return self.numero(int(fila["n"]))

    def numero(self, n: int):
        from PIL import Image
        return Image.open(self.dir / f"f_{n:05d}.png").convert("RGB")

    def primero_bajo(self, y: int, desde: float) -> float | None:
        """Segundo en que por primera vez hay algo dibujado por debajo de la fila y."""
        for r in self.filas:
            t = float(r["pts_s"]) - self.t0
            if t >= desde and r["bbox_y1"] and int(r["bbox_y1"]) > y:
                return round(t, 2)
        return None

    def salto_del_borde(self, desde: float) -> int:
        """Mayor movimiento del borde superior de lo dibujado entre dos fotogramas seguidos, en píxeles.

        Ese borde lo marca la cresta de la onda y se mueve muy despacio (un píxel por fotograma);
        si la onda no cierra el bucle, pega un salto cada vez que vuelve a empezar.
        """
        ys = [int(r["bbox_y0"]) for r in self.filas if r["bbox_y0"] and float(r["pts_s"]) - self.t0 >= desde]
        return max((abs(b - a) for a, b in zip(ys, ys[1:])), default=0)

    def periodo(self, desde: float = 3.5) -> float | None:
        """Segundos reales que tarda la onda en repetirse (valor típico), o None si no se repite.

        Para varios cuadros se busca cuándo reaparecen idénticos. Si la onda avanza más de un
        paso por refresco, un cuadro puede saltearse en la vuelta siguiente y reaparecer recién
        dos vueltas después: esos lapsos dobles se descartan y se informa la mediana del resto.
        """
        tiempos = [(float(r["pts_s"]) - self.t0, int(r["n"])) for r in self.filas]
        lapsos = []
        for k in range(14):
            # primer fotograma de un cuadro nuevo a partir de desde + 0,2 k
            i = next((i for i, (t, _) in enumerate(tiempos)
                      if t >= desde + 0.2 * k and self.filas[i]["cambio"] == "1"), None)
            if i is None:
                break
            ref = self.numero(tiempos[i][1])
            for t, n in tiempos[i:]:
                if t - tiempos[i][0] >= 1.0 and iguales(ref, self.numero(n)):
                    lapsos.append(t - tiempos[i][0])
                    break
        if not lapsos:
            return None
        simples = sorted(g for g in lapsos if g < 1.6 * min(lapsos))
        return round(simples[len(simples) // 2], 2)


def caja(mascara) -> tuple[int, int, int, int] | None:
    return mascara.getbbox()


def mascara_encendida(im, zona=None):
    """Imagen L con 255 donde hay algo dibujado; zona = (x0, y0, x1, y1) limita la búsqueda."""
    from PIL import Image, ImageChops
    r, g, b = im.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > UMBRAL else 0)
    if zona:
        recorte = Image.new("L", im.size, 0)
        recorte.paste(m.crop(zona), zona[:2])
        m = recorte
    return m


def pixeles(im, zona):
    """Los píxeles RGB de una zona, de izquierda a derecha y de arriba abajo."""
    datos = im.crop(zona).tobytes()
    return zip(datos[0::3], datos[1::3], datos[2::3])


def color_medio(im, zona) -> tuple[float, float, float]:
    px = [p for p in pixeles(im, zona) if max(p) > UMBRAL]
    if not px:
        return (0.0, 0.0, 0.0)
    return tuple(sum(c[i] for c in px) / len(px) for i in range(3))


def contar(im, zona, predicado) -> tuple[int, tuple[float, float]]:
    x0, y0, x1, y1 = zona
    ancho = x1 - x0
    n = sx = sy = 0
    for i, p in enumerate(pixeles(im, zona)):
        if predicado(p):
            n += 1
            sx += x0 + i % ancho
            sy += y0 + i // ancho
    return n, ((sx / n, sy / n) if n else (0.0, 0.0))


def es_verde(p) -> bool:
    return p[1] > 110 and p[0] < 90 and p[1] > 1.35 * p[2]


def es_amarillo(p) -> bool:
    return p[0] > 190 and p[1] > 150 and p[2] < 100


def es_tinta(p) -> bool:
    """El gris azulado del anillo del escudo (los bordes de los puntos blancos son gris neutro)."""
    r, g, b = p
    return 35 < b < 150 and 6 <= b - r <= 40 and abs(g - (r + b) / 2) < 12


def clase(p) -> str | None:
    """Franja a la que pertenece un píxel: R, B, A, «?» si no es de ninguna, None si está apagado."""
    r, g, b = p
    if max(p) <= UMBRAL:
        return None
    if r > 90 and r > 1.6 * max(g, b):
        return "R"
    if b > 1.35 * max(r, g):
        return "A"
    if min(p) > 110 and max(p) - min(p) < 45:
        return "B"
    return "?"


def franjas_en(im, xa: int, xb: int, ya: int, yb: int, paso: float) -> list[tuple[str, int, int]]:
    """Colores dominantes de arriba abajo en una zona: lista de (clase, primera fila, última fila).

    Tolera el desplazamiento de la onda: mira el orden vertical, no posiciones fijas.
    """
    ancho = xb - xa
    datos = list(pixeles(im, (xa, ya, xb, yb)))
    corridas: list[list] = []
    for fila in range(yb - ya):
        cuenta: dict[str, int] = {}
        for px in datos[fila * ancho:(fila + 1) * ancho]:
            c = clase(px)
            if c and c != "?":               # los bordes suavizados de los puntos no son de ninguna franja
                cuenta[c] = cuenta.get(c, 0) + 1
        if sum(cuenta.values()) < 3:
            continue                         # fila entre puntos, o solo con bordes: no dice nada
        c = max(cuenta, key=cuenta.get)
        if corridas and corridas[-1][0] == c:
            corridas[-1][1] += 1
            corridas[-1][3] = ya + fila
        else:
            corridas.append([c, 1, ya + fila, ya + fila])
    # las corridas cortas son filas mezcladas en el límite entre franjas
    largas = [c for c in corridas if c[1] >= 2.5 * paso]
    unidas: list[list] = []
    for c in largas:
        if unidas and unidas[-1][0] == c[0]:
            unidas[-1][3] = c[3]
        else:
            unidas.append(c[:])
    return [(c[0], c[2], c[3]) for c in unidas]


def corridas_x(im, zona) -> int:
    """Cuántos grupos separados de columnas encendidas hay en una zona (p. ej. las ranuras en fila)."""
    m = mascara_encendida(im, zona).crop(zona)
    datos, ancho = m.tobytes(), m.width
    columnas = [any(datos[x::ancho]) for x in range(ancho)]
    return sum(1 for x in range(ancho) if columnas[x] and (x == 0 or not columnas[x - 1]))


ALTO_EN_PASOS = gen.COLS * 11 / 20      # alto de la bandera en pasos de grilla (24,2)


def paso_esperado(w: int, h: int) -> int:
    """El paso de grilla que el script debe elegir para una pantalla de w x h."""
    texto = gen.ARCHIVO_SCRIPT.read_text(encoding="utf-8")
    m = re.search(r"lim = Math\.Min\(ANCHO_MIN \* ([\d.]+) / COLS, ALTO_MIN \* ([\d.]+) / ALTO_BANDERA\);", texto)
    if not m:
        raise SystemExit("error: no encuentro en el script la regla que elige el paso de grilla")
    lim = min(w * float(m.group(1)) / gen.COLS, h * float(m.group(2)) / ALTO_EN_PASOS)
    return max([p for p in gen.PASOS if p <= lim] or [gen.PASOS[0]])


def zona_dialogo(im) -> tuple[int, int, int, int]:
    """Franja de pantalla del diálogo: desde 3 pasos bajo el borde inferior de la bandera en reposo.

    El borde inferior sube y baja con la onda (hasta 2,5 pasos bajo el reposo), así que el
    límite se calcula con la geometría y no con la caja medida en un fotograma.
    """
    paso = paso_esperado(*im.size)
    return (0, round(im.height / 2 + (ALTO_EN_PASOS / 2 + 3.0) * paso), im.width, im.height)


def iguales(a, b) -> bool:
    from PIL import ImageChops
    return ImageChops.difference(a, b).getbbox() is None


def encendidos(im, zona) -> int:
    return sum(mascara_encendida(im, zona).histogram()[255:])


def validar_bandera(nombre: str, im) -> tuple[int, int, int, int] | None:
    """Comprueba sobre un fotograma que lo dibujado es la bandera; devuelve su caja."""
    w, h = im.size
    paso = paso_esperado(w, h)
    x_asta = w / 2 - gen.COLS / 2 * paso                 # borde izquierdo de la grilla en reposo
    y_arriba = h / 2 - ALTO_EN_PASOS / 2 * paso          # borde superior de la grilla en reposo
    hasta = zona_dialogo(im)[1]
    c = caja(mascara_encendida(im, (0, 0, w, hasta)))
    if not anotar(c is not None, f"{nombre}: hay algo dibujado"):
        return None
    x0, y0, x1, y1 = c
    bw, bh = x1 - x0, y1 - y0
    anotar(x0 > 0 and y0 > 0 and x1 < w and y1 < h, f"{nombre}: la bandera entra completa en la pantalla",
           f"caja {c} en {w}x{h}")
    # Posición: junto al asta la onda casi no mueve los puntos, así que el primer punto de
    # arriba a la izquierda dice dónde está la bandera con menos de un paso de error.
    radio = gen.DIAMETROS_PUNTO[gen.NT // 2] / 2 * paso
    ex = x_asta + 0.5 * paso - radio
    ey = y_arriba + 0.5 * ALTO_EN_PASOS / gen.FILAS * paso - radio
    esquina = caja(mascara_encendida(im, (x0, 0, round(x0 + 2.5 * paso), hasta)))
    anotar(esquina is not None and abs(esquina[0] - ex) < 0.6 * paso and abs(esquina[1] - ey) < 0.6 * paso,
           f"{nombre}: la bandera está centrada (su esquina del asta está donde corresponde)",
           f"esquina en {esquina[:2] if esquina else None}, esperada ({ex:.0f}, {ey:.0f}), tolerancia {0.6 * paso:.0f} px")
    anotar(abs(bw - gen.COLS * paso) < 2.0 * paso, f"{nombre}: el tamaño corresponde al paso elegido para esta pantalla",
           f"ancho {bw} px, esperado {gen.COLS * paso} (paso {paso}); {bw / w:.0%} del ancho de pantalla")
    anotar(0.50 <= bh / bw <= 0.66, f"{nombre}: proporción de bandera",
           f"alto/ancho {bh / bw:.3f} (11:20 = 0,55 más el vuelo de la onda)")

    # Franjas: el orden se comprueba en tres zonas a lo largo de la bandera...
    for donde, (c0, c1) in {"junto al asta": (1, 9), "en el medio": (11, 17), "hacia el batiente": (30, 40)}.items():
        sec = franjas_en(im, round(x_asta + c0 * paso), round(x_asta + c1 * paso), y0, y1, paso)
        anotar([s[0] for s in sec] == ["R", "B", "A"],
               f"{nombre}: franjas roja, blanca y azul de arriba abajo {donde}", "-".join(s[0] for s in sec) or "nada")
        # ocho filas de puntos por franja: de la primera a la última van unos 7,6 pasos
        altos = {s[0]: (s[2] - s[1]) / paso for s in sec}
        anotar(len(sec) == 3 and all(6.3 <= a <= 10.5 for a in altos.values()),
               f"{nombre}: las tres franjas tienen su alto completo {donde}",
               ", ".join(f"{k} {a:.1f} pasos" for k, a in altos.items()))
    # ...y el color, junto al asta, donde cada franja está en su lugar de reposo.
    xa, xb = round(x_asta + 1 * paso), round(x_asta + 9 * paso)
    franjas = []
    for i in range(3):
        ya = round(y_arriba + (i + 0.12) * ALTO_EN_PASOS / 3 * paso)
        yb = round(y_arriba + (i + 0.88) * ALTO_EN_PASOS / 3 * paso)
        franjas.append(color_medio(im, (xa, ya, xb, yb)))
    r, b, a = franjas
    anotar(r[0] > 140 and r[0] > 2.5 * max(r[1], r[2]), f"{nombre}: franja de arriba roja", "RGB %.0f %.0f %.0f" % r)
    anotar(min(b) > 150 and max(b) - min(b) < 25, f"{nombre}: franja del medio blanca", "RGB %.0f %.0f %.0f" % b)
    anotar(a[2] > 110 and a[2] > 2.2 * a[1] and a[0] < 60, f"{nombre}: franja de abajo azul", "RGB %.0f %.0f %.0f" % a)

    nv, cv = contar(im, c, es_verde)
    na, ca = contar(im, c, es_amarillo)
    if not anotar(nv > 20 and na > 3, f"{nombre}: el escudo tiene corona verde y estrella amarilla",
                  f"{nv} px verdes, {na} px amarillos"):
        return c
    # El escudo sube y baja con la tela: su lugar se mide contra la franja blanca que lo rodea.
    alrededor = franjas_en(im, round(ca[0] - 3.4 * paso), round(ca[0] + 3.4 * paso), y0, y1, paso)
    blanca = [s for s in alrededor if s[0] == "B"]
    medio = (blanca[0][1] + blanca[0][2]) / 2 if blanca else None
    anotar(medio is not None and abs(ca[1] - medio) < 0.9 * paso and -1.4 * paso < ca[0] - w / 2 < 0.7 * paso,
           f"{nombre}: el escudo está en el centro de la franja blanca",
           f"estrella en ({ca[0]:.0f}, {ca[1]:.0f}); medio de la franja blanca en y = {medio}; centro de pantalla x = {w // 2}")

    def radio_medio(es) -> float | None:
        """Distancia media a la estrella, en pasos, de los píxeles de un color."""
        zona = (max(0, round(ca[0] - 3.6 * paso)), max(0, round(ca[1] - 3.6 * paso)),
                min(w, round(ca[0] + 3.6 * paso)), min(h, round(ca[1] + 3.6 * paso)))
        ancho = zona[2] - zona[0]
        n = suma = 0
        for i, px in enumerate(pixeles(im, zona)):
            if es(px):
                n += 1
                suma += math.hypot(zona[0] + i % ancho - ca[0], zona[1] + i // ancho - ca[1])
        return suma / n / paso if n else None
    ra, rv, rn = radio_medio(es_amarillo), radio_medio(es_verde), radio_medio(es_tinta)
    anotar(None not in (ra, rv, rn) and ra < 0.7 and 0.7 < rv < 2.0 and 2.0 < rn < 3.4,
           f"{nombre}: el escudo tiene su forma (estrella al centro, corona alrededor, anillo por fuera)",
           "distancia media a la estrella, en pasos: " + ", ".join(
               f"{n} {v:.2f}" if v is not None else f"{n} ausente" for n, v in (("estrella", ra), ("corona", rv), ("anillo", rn))))

    def de_escudo(p):
        return es_verde(p) or es_amarillo(p)
    total, _ = contar(im, c, de_escudo)
    cerca, _ = contar(im, (round(cv[0] - 4 * paso), round(cv[1] - 4 * paso),
                           round(cv[0] + 4 * paso), round(cv[1] + 4 * paso)), de_escudo)
    anotar(total == cerca, f"{nombre}: no hay verde ni amarillo fuera del escudo", f"{total - cerca} px fuera")
    return c


def validar_dialogo(nombre: str, im, con_texto: bool = True) -> None:
    """El diálogo está completo y en su lugar: texto arriba, fila de ranuras debajo, centrado."""
    w, h = im.size
    paso = paso_esperado(w, h)
    # mismas distancias que el script (DLG_Y, LINEA, Y_RANURAS)
    dlg_y = h / 2 + (ALTO_EN_PASOS / 2 + gen.ONDA["ay"] + gen.ONDA["caida"] + 1.5) * paso
    linea = max(paso * 1.2, max(9, int(paso * 0.7)) * 1.9)
    z = zona_dialogo(im)
    cz = caja(mascara_encendida(im, z))
    anotar(cz is not None and abs((cz[0] + cz[2]) / 2 - w / 2) < 0.03 * w and cz[3] < h - 2,
           f"{nombre}: el diálogo está centrado y dentro de la pantalla", f"caja {cz}")
    fila = (0, round(dlg_y + 1.45 * linea), w, round(dlg_y + 1.45 * linea + 0.75 * paso))
    n = corridas_x(im, fila)
    anotar(n == gen.RANURAS, f"{nombre}: la fila tiene sus {gen.RANURAS} ranuras", f"{n} grupos de puntos")
    if con_texto:
        px = encendidos(im, (0, round(dlg_y) - 2, w, round(dlg_y + 1.4 * linea)))
        anotar(px > 60, f"{nombre}: el texto del pedido está sobre las ranuras", f"{px} px")


def validar_dinamico(rapida: bool) -> None:
    fps_min = round(gen.FPS * 0.3, 1)

    # 1) arranque a 1080p con clave y mensaje
    nombre = "arranque 1920x1080"
    m, salida = correr_banco("arranque", ["--segundos", "14", "--tamano", "1920x1080",
                                          "--evento", "3:clave:Clave del disco", "--evento", "7:mensaje:Verificando discos"])
    if base_del_banco(nombre, m, fps_min):
        fot = Fotogramas(salida)
        antes = fot.en(2.3)
        c = validar_bandera(nombre, antes)
        z = zona_dialogo(antes)
        n0 = encendidos(antes, z)
        anotar(n0 == 0, f"{nombre}: nada debajo de la bandera antes de pedir la clave", f"{n0} px")
        # El diálogo no aparece en un instante fijo: el primer texto carga el plugin de etiquetas y
        # las fuentes (en el banco, más de un segundo). Se busca cuándo aparece en vez de suponerlo.
        aparece = fot.primero_bajo(z[1], desde=2.9)
        anotar(aparece is not None and aparece < 6.0, f"{nombre}: al pedir la clave (a los 3 s) aparece el diálogo",
               f"aparece a los {aparece} s")
        con_clave, con_mensaje = fot.en((aparece or 4.3) + 0.3), fot.en(9.5)
        validar_dialogo(f"{nombre}, pedido de clave", con_clave)
        n1, n2 = encendidos(con_clave, z), encendidos(con_mensaje, z)
        anotar(n2 > n1 * 1.15, f"{nombre}: el mensaje se dibuja además del diálogo", f"{n1} px -> {n2} px")
        # La onda no debe detenerse con una clave pendiente (el reloj de progreso se congela).
        anotar(not iguales(fot.en(9.0), fot.en(9.4)), f"{nombre}: la bandera sigue ondeando con la clave pendiente")
        # El bucle se repite exacto: los cuadros vuelven a aparecer idénticos un ciclo después.
        # (El refresco real va algo más lento que el nominal y dentro de ese margen no se corrige.)
        ciclo = gen.ONDA["ciclo_s"]
        periodo = fot.periodo(desde=8.0)
        anotar(periodo is not None and 0.93 * ciclo <= periodo <= 1.15 * ciclo,
               f"{nombre}: la onda es un bucle que se repite idéntico", f"se repite cada {periodo} s (nominal {ciclo} s)")
        paso = paso_esperado(*antes.size)
        salto = fot.salto_del_borde(desde=8.0)
        anotar(salto <= max(2, 0.1 * paso), f"{nombre}: la onda avanza sin saltos",
               f"el borde superior se mueve a lo sumo {salto} px entre fotogramas")
        ce = caja(mascara_encendida(fot.en(0.35)))
        anotar(c is not None and ce is not None and abs(ce[0] - c[0]) < paso and (ce[2] - ce[0]) < 0.75 * (c[2] - c[0]),
               f"{nombre}: la bandera se revela desde el asta", f"a los 0,35 s ocupa {ce}; completa, {c}")
    if rapida:
        return

    # 2) pantalla chica, con una pregunta
    nombre = "arranque 1024x768"
    m, salida = correr_banco("chica", ["--segundos", "8", "--tamano", "1024x768", "--evento", "3:pregunta:Continuar"])
    if base_del_banco(nombre, m, fps_min):
        fot = Fotogramas(salida)
        validar_bandera(nombre, fot.en(2.5))
        aparece = fot.primero_bajo(zona_dialogo(fot.en(2.5))[1], desde=2.9)
        if anotar(aparece is not None, f"{nombre}: al hacer una pregunta (a los 3 s) aparece el diálogo", f"a los {aparece} s"):
            validar_dialogo(f"{nombre}, pregunta", fot.en(aparece + 0.3))

    # 2b) la pantalla más chica: con el paso mínimo el escudo debe seguir viéndose
    nombre = "arranque 640x480"
    m, salida = correr_banco("minima", ["--segundos", "6", "--tamano", "640x480"])
    if base_del_banco(nombre, m, fps_min):
        validar_bandera(nombre, Fotogramas(salida).en(4.5))

    # 3) apagado
    nombre = "apagado 1366x768"
    m, salida = correr_banco("apagado", ["--segundos", "6", "--tamano", "1366x768", "--modo", "shutdown"])
    if base_del_banco(nombre, m, fps_min):
        validar_bandera(nombre, Fotogramas(salida).en(4.5))

    # 4) actualización: la fila de ranuras hace de barra de progreso
    nombre = "actualización 1280x720"
    m, salida = correr_banco("actualizacion", ["--segundos", "9", "--tamano", "1280x720", "--modo", "updates",
                                               "--evento", "4:progreso:25", "--evento", "6:progreso:75"])
    if base_del_banco(nombre, m, fps_min):
        fot = Fotogramas(salida)
        f0, f1, f2 = fot.en(3.0), fot.en(5.3), fot.en(7.5)
        validar_bandera(nombre, f0)
        z = zona_dialogo(f0)

        def claros(im):   # ranuras encendidas: puntos casi blancos
            return contar(im, z, lambda p: min(p) > 200)[0]
        n0, n1, n2 = claros(f0), claros(f1), claros(f2)
        anotar(encendidos(f0, z) > 100 and n0 == 0, f"{nombre}: la barra aparece vacía desde el inicio",
               f"{encendidos(f0, z)} px encendidos, {n0} claros")
        anotar(0 < n1 < n2, f"{nombre}: la barra avanza con el progreso (25 % -> 75 %)", f"{n1} -> {n2} px claros")

    # 5) el instalador: cada rama de activación en un arenero, y una copia instalada que funciona
    orden = ["bash", ruta_para_banco(RAIZ / "scripts" / "probar_instalador.sh")]
    if platform.system() == "Windows":
        orden = ["wsl", "--"] + orden
    r = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8", errors="replace")
    resumen = next((x for x in r.stdout.splitlines() if x.startswith("INSTALADOR:")), "sin resumen")
    fallas = [x[6:] for x in r.stdout.splitlines() if x.startswith("FALLA")]
    anotar(r.returncode == 0, "instalador: instalar.sh y desinstalar.sh pasan su prueba en el arenero",
           resumen + ("; " + "; ".join(fallas[:3]) if fallas else ""))
    nombre = "copia instalada"
    prefijo = DIR_SALIDA / "prefijo"
    orden = ["bash", ruta_para_banco(RAIZ / "instalar.sh"), "--prefijo", ruta_para_banco(prefijo)]
    if platform.system() == "Windows":
        orden = ["wsl", "--"] + orden
    r = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8", errors="replace")
    instalado = prefijo / "usr" / "share" / "plymouth" / "themes" / "paraguay"
    if anotar(r.returncode == 0 and instalado.is_dir(), f"{nombre}: instalar.sh --prefijo copia el tema", f"código {r.returncode}"):
        m, salida = correr_banco("instalado", ["--segundos", "5", "--tamano", "1280x720"], tema=instalado)
        if base_del_banco(nombre, m, fps_min):
            # una copia a la que le falten imágenes carga sin error, pero no dibuja la bandera entera
            validar_bandera(nombre, Fotogramas(salida).en(3.5))

    # 6) velocidad constante: la onda dura lo mismo aunque cambie el ritmo de refresco.
    # Se prueba con dos copias alteradas del tema (ver PARCHES en medir_tema.py).
    import medir_tema as med
    ciclo = gen.ONDA["ciclo_s"]
    for parche, cuando in (("sin_tasa", "Plymouth ignora SetRefreshRate y refresca a 50 por segundo"),
                           ("lento", "el equipo no alcanza los refrescos pedidos")):
        nombre = f"velocidad ({parche})"
        tema, _ = med.preparar_variante(f"t{gen.TRAMO}_{gen.FPS}_{parche}")
        m, salida = correr_banco(f"velocidad-{parche}", ["--segundos", "11", "--tamano", "1280x720"], tema=tema)
        if base_del_banco(nombre, m, 4):
            if parche == "lento":
                anotar(m["tasa_animacion_fps"] < 0.8 * gen.FPS, f"{nombre}: la copia alterada realmente va lenta",
                       f"{m['tasa_animacion_fps']} cuadros por segundo")
            # Con el ritmo estable la corrección es exacta; con altibajos, aproximada.
            margen = (0.93, 1.15) if parche == "sin_tasa" else (0.75, 1.3)
            periodo = Fotogramas(salida).periodo()
            anotar(periodo is not None and margen[0] * ciclo <= periodo <= margen[1] * ciclo,
                   f"{nombre}: la onda conserva su velocidad cuando {cuando}",
                   f"el bucle tarda {periodo} s (nominal {ciclo} s)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("Sale con 0")[1].split("\n\n", 1)[1])
    ap.add_argument("--rapida", action="store_true", help="estático + una sola corrida del banco (unos 2 minutos)")
    ap.add_argument("--sin-banco", action="store_true", help="solo las comprobaciones estáticas")
    ap.add_argument("--evidencia", type=Path, help="guardar el resultado en este archivo de texto")
    args = ap.parse_args()

    validar_estatico()
    if not args.sin_banco:
        validar_dinamico(args.rapida)

    fallas = [n for ok, n, _ in resultados if not ok]
    resumen = f"VALIDACION: {'PASA' if not fallas else 'FALLA'} ({len(resultados) - len(fallas)}/{len(resultados)} comprobaciones)"
    print("\n" + resumen)
    if args.evidencia:
        args.evidencia.parent.mkdir(parents=True, exist_ok=True)
        lineas = [f"{'PASA ' if ok else 'FALLA'} {n}" + (f"  [{d}]" if d else "") for ok, n, d in resultados]
        args.evidencia.write_text("\n".join(lineas + ["", resumen, ""]), encoding="utf-8")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
