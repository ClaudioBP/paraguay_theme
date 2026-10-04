#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida y dibuja los mapas de puntos del escudo de la bandera paraguaya.

Fuente de datos: el bloque JSON delimitado por
``<!-- mapas-json:inicio -->`` y ``<!-- mapas-json:fin -->`` dentro de
``docs/investigacion/bandera-paraguay.md`` (o un archivo JSON suelto con el
mismo esquema, opcion --json). Ese bloque contiene la leyenda
caracter -> color, la geometria comun y las filas de cada mapa.

Que hace:

* ``--validar``: comprueba la coherencia de los datos y del documento
  (dimensiones declaradas = reales, simetria, centrado, leyenda completa,
  proporcion de las grillas, filas enteras por franja, totales de puntos y
  coincidencia entre los mapas ASCII legibles y el bloque JSON). No necesita
  Pillow. Sale con 0 si todo pasa y con 1 si algo falla.
* sin ``--validar``: ademas dibuja cada mapa en PNG sobre fondo oscuro
  (escudo suelto ampliado, bandera completa y detalle del centro) y deja
  ``metricas.json`` en la carpeta de salida. Necesita Pillow.

No abre ventanas ni usa pantalla: solo escribe archivos.

Codigos de salida: 0 correcto; 1 validacion fallida; 2 argumentos invalidos;
3 no se pudo leer la fuente o falta Pillow.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOC_DEFECTO = RAIZ / "docs" / "investigacion" / "bandera-paraguay.md"
SALIDA_DEFECTO = RAIZ / "output" / "temporales" / "verif-bandera"

RE_JSON = re.compile(
    r"<!-- mapas-json:inicio -->\s*```json\n(.*?)```\s*<!-- mapas-json:fin -->", re.S)
RE_ASCII = re.compile(r"<!-- mapa:(\w+) -->\s*```text\n(.*?)```", re.S)
RE_TITULO = re.compile(
    r"^#### Mapa (M\d+) \((\d+)×(\d+)[^)]*\): (\d+) puntos \(([^)]*)\)", re.M)
RE_FILA_TOTALES = re.compile(
    r"^\| P\d+ \((\d+)×(\d+)\) \| (M\d+) \| ([\d,]+) \| (\d+) \| (\d+) \| \*\*(\d+)\*\* \|"
    r" ([\d,]+) \| ([+−-]?[\d,]+) \|", re.M)
RE_FILA_GRILLA = re.compile(
    r"^\|\s*\**(\d+) × (\d+)\**\s*\|\s*\**(\d+)\**\s*\|\s*\**(\d+)\**\s*\|"
    r"\s*([\d,]+)\s*\|\s*([+−-]?[\d,]+) %[^|]*\|\s*([\d,]+)\s*\|", re.M)
RE_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

CODIGOS_FRANJA = ("R", "B", "A")


class ErrorFuente(Exception):
    """La fuente de datos no existe o no tiene el formato esperado."""


# --------------------------------------------------------------------------
# Carga de datos
# --------------------------------------------------------------------------

def cargar(ruta_doc, ruta_json):
    """Devuelve (datos, texto_del_documento o None)."""
    if ruta_json is not None:
        try:
            datos = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ErrorFuente(f"no se pudo leer el JSON {ruta_json}: {e}")
        return datos, None
    try:
        texto = Path(ruta_doc).read_text(encoding="utf-8")
    except OSError as e:
        raise ErrorFuente(f"no se pudo leer el documento {ruta_doc}: {e}")
    m = RE_JSON.search(texto)
    if not m:
        raise ErrorFuente(
            f"{ruta_doc} no contiene el bloque <!-- mapas-json:inicio --> ... "
            "<!-- mapas-json:fin -->")
    try:
        datos = json.loads(m.group(1))
    except ValueError as e:
        raise ErrorFuente(f"el bloque mapas-json de {ruta_doc} no es JSON valido: {e}")
    return datos, texto


def mapas_ascii(texto):
    """Extrae del Markdown los mapas legibles (una letra por punto, con espacios)."""
    res = {}
    for m in RE_ASCII.finditer(texto):
        res[m.group(1)] = ["".join(l.split()) for l in m.group(2).strip("\n").split("\n")]
    return res


# --------------------------------------------------------------------------
# Geometria
# --------------------------------------------------------------------------

def conteo(celdas):
    c = {}
    for fila in celdas:
        for ch in fila:
            c[ch] = c.get(ch, 0) + 1
    return c


def diametro_relativo(datos, mapa):
    """Diametro del escudo / alto de la franja blanca (el mapa puede fijar el suyo)."""
    return mapa.get("diametro_escudo_sobre_franja",
                    datos["geometria"]["diametro_escudo_sobre_franja"])


def medidas(datos, mapa, ancho):
    """Magnitudes de la bandera y del escudo para un ancho dado (en px)."""
    g = datos["geometria"]
    filas, cols = mapa["grilla"]["filas"], mapa["grilla"]["columnas"]
    alto = ancho * g["proporcion_alto"] / g["proporcion_ancho"]
    dx, dy = ancho / cols, alto / filas
    franja = alto / 3
    m = {"ancho": ancho, "alto": alto, "filas": filas, "cols": cols, "dx": dx, "dy": dy,
         "franja": franja, "r_punto": g["punto_sobre_paso"] * min(dx, dy) / 2}
    if mapa["tipo"] == "subgrilla":
        n = mapa["lado"]
        d = diametro_relativo(datos, mapa) * franja
        m.update(diametro=d, subpaso=d / n,
                 r_subpunto=g["subpunto_sobre_subpaso"] * (d / n) / 2,
                 r_retiro=d / 2 + g["margen_retiro_en_pasos"] * dx)
    return m


def retirados(datos, mapa, ancho=960.0):
    """Puntos de la grilla principal que se quitan para dejar sitio a la sub-grilla."""
    if mapa["tipo"] != "subgrilla":
        return []
    m = medidas(datos, mapa, ancho)
    res = []
    for f in range(m["filas"]):
        for c in range(m["cols"]):
            x, y = (c + 0.5) * m["dx"], (f + 0.5) * m["dy"]
            if math.hypot(x - ancho / 2, y - m["alto"] / 2) < m["r_retiro"]:
                res.append((f, c))
    return res


def holgura_minima(datos, mapa, ancho=960.0):
    """Menor separacion borde a borde entre un punto principal y un sub-punto, en pasos
    de la grilla principal (negativa = se solapan). None si el mapa no usa sub-grilla."""
    if mapa["tipo"] != "subgrilla":
        return None
    pts, m = puntos_bandera(datos, mapa, ancho)
    principales = [p for p in pts if p[3] in CODIGOS_FRANJA]
    sub = [p for p in pts if p[3] not in CODIGOS_FRANJA]
    alcance = m["r_retiro"] + 2 * m["dx"]
    cerca = [p for p in principales
             if math.hypot(p[0] - ancho / 2, p[1] - m["alto"] / 2) < alcance]
    menor = min(math.hypot(a[0] - b[0], a[1] - b[1]) - a[2] - b[2] for a in cerca for b in sub)
    return menor / m["dx"]


def totales(datos, mapa):
    filas, cols = mapa["grilla"]["filas"], mapa["grilla"]["columnas"]
    cuenta = conteo(mapa["celdas"])
    propios = sum(v for k, v in cuenta.items() if k != ".")
    if mapa["tipo"] == "subgrilla":
        quitados = retirados(datos, mapa)
        m = medidas(datos, mapa, 960.0)
        return {"principal": filas * cols, "retirados": len(quitados), "subpuntos": propios,
                "total": filas * cols - len(quitados) + propios,
                "diametro_sobre_franja": diametro_relativo(datos, mapa),
                "subpaso_sobre_paso": round(m["subpaso"] / m["dx"], 3),
                "holgura_minima_en_pasos": round(holgura_minima(datos, mapa), 3),
                "franja_blanca_mordida": sorted({f for f, _ in quitados
                                                 if f in (filas // 3, 2 * filas // 3 - 1)}) != []}
    return {"principal": filas * cols, "retirados": 0, "subpuntos": 0, "total": filas * cols,
            "puntos_recoloreados": propios}


def puntos_bandera(datos, mapa, ancho):
    """Lista de (x, y, radio, codigo) de toda la bandera, en px, origen arriba a la izquierda."""
    m = medidas(datos, mapa, ancho)
    por_franja = m["filas"] // 3
    cx, cy = ancho / 2, m["alto"] / 2
    celdas = mapa["celdas"]
    pts = []
    for f in range(m["filas"]):
        for c in range(m["cols"]):
            x, y = (c + 0.5) * m["dx"], (f + 0.5) * m["dy"]
            cod = CODIGOS_FRANJA[min(f // por_franja, 2)]
            if mapa["tipo"] == "subgrilla":
                if math.hypot(x - cx, y - cy) < m["r_retiro"]:
                    continue
            else:
                j, i = f - mapa["fila0"], c - mapa["columna0"]
                if 0 <= j < len(celdas) and 0 <= i < len(celdas[0]) and celdas[j][i] != ".":
                    cod = celdas[j][i]
            pts.append((x, y, m["r_punto"], cod))
    if mapa["tipo"] == "subgrilla":
        n, s = mapa["lado"], m["subpaso"]
        for j, fila in enumerate(celdas):
            for i, ch in enumerate(fila):
                if ch != ".":
                    pts.append((cx + (i - (n - 1) / 2) * s, cy + (j - (n - 1) / 2) * s,
                                m["r_subpunto"], ch))
    return pts, m


def puntos_escudo(datos, mapa, celda):
    """El mapa solo, ampliado. En los nativos '.' se dibuja como punto de franja blanca."""
    g = datos["geometria"]
    celdas = mapa["celdas"]
    if mapa["tipo"] == "subgrilla":
        k, borde, relleno = g["subpunto_sobre_subpaso"], 1, None
    else:
        k, borde, relleno = g["punto_sobre_paso"], 1, "B"
    alto, ancho = len(celdas), len(celdas[0])
    pts = []
    for j in range(-borde, alto + borde):
        for i in range(-borde, ancho + borde):
            dentro = 0 <= j < alto and 0 <= i < ancho
            ch = celdas[j][i] if dentro else "."
            if ch == ".":
                ch = relleno
            if ch is not None:
                pts.append(((i + borde + 0.5) * celda, (j + borde + 0.5) * celda,
                            k * celda / 2, ch))
    return pts, ((ancho + 2 * borde) * celda, (alto + 2 * borde) * celda)


# --------------------------------------------------------------------------
# Validacion
# --------------------------------------------------------------------------

def luminancia(hx):
    h = hx.lstrip("#")
    canales = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def num(texto):
    """Numero con coma decimal y signo menos tipografico -> float."""
    return float(texto.replace(",", ".").replace("−", "-"))


def validar(datos, texto):
    """Devuelve una lista de (nombre, ok, detalle)."""
    res = []

    def anotar(nombre, ok, detalle=""):
        res.append((nombre, bool(ok), detalle))

    g = datos.get("geometria", {})
    leyenda = datos.get("leyenda", {})
    mapas = datos.get("mapas", {})
    anotar("json: claves principales", all(k in datos for k in
                                           ("leyenda", "geometria", "mapas", "fondo")))
    anotar("geometria: proporcion 11:20",
           g.get("proporcion_alto") == 11 and g.get("proporcion_ancho") == 20,
           f"{g.get('proporcion_alto')}:{g.get('proporcion_ancho')}")
    anotar("fondo: hex valido", bool(RE_HEX.match(str(datos.get("fondo", "")))),
           str(datos.get("fondo")))

    # Leyenda: cada codigo usado tiene color fiel y color para fondo oscuro.
    usados = set(CODIGOS_FRANJA)
    for mp in mapas.values():
        usados |= set("".join(mp.get("celdas", [])))
    for cod in sorted(usados):
        e = leyenda.get(cod)
        if e is None:
            anotar(f"leyenda: codigo '{cod}'", False, "falta en la leyenda")
            continue
        if cod == ".":
            ok = e.get("fiel") is None and e.get("oscuro") is None
            anotar("leyenda: '.' sin color", ok)
        else:
            ok = all(RE_HEX.match(str(e.get(p, ""))) for p in ("fiel", "oscuro"))
            anotar(f"leyenda: '{cod}' tiene hex fiel y oscuro", ok,
                   f"{e.get('fiel')} / {e.get('oscuro')}")
    sobran = sorted(set(leyenda) - usados)
    anotar("leyenda: sin codigos sin usar", not sobran, " ".join(sobran))

    ascii_doc = mapas_ascii(texto) if texto else {}
    titulos = {m.group(1): m for m in RE_TITULO.finditer(texto)} if texto else {}

    for nombre, mp in mapas.items():
        pre = f"{nombre}:"
        celdas = mp.get("celdas", [])
        tipo = mp.get("tipo")
        anotar(f"{pre} tipo conocido", tipo in ("subgrilla", "nativo"), str(tipo))
        lado = mp.get("lado")
        cuadrado = len(celdas) == lado and all(len(f) == lado for f in celdas)
        anotar(f"{pre} dimensiones declaradas = reales", cuadrado,
               f"declarado {lado}x{lado}, real {len(celdas)}x"
               f"{sorted({len(f) for f in celdas})}")
        if not cuadrado or tipo not in ("subgrilla", "nativo"):
            continue
        n = lado
        c = (n - 1) / 2
        anotar(f"{pre} simetria izquierda-derecha", all(f == f[::-1] for f in celdas))
        silueta = ["".join("#" if ch != "." else "." for ch in f) for f in celdas]
        anotar(f"{pre} silueta simetrica arriba-abajo", silueta == silueta[::-1])
        anotar(f"{pre} la silueta llena la mascara (toca los cuatro bordes)",
               "#" in silueta[0] and "#" in silueta[-1]
               and any(f[0] == "#" for f in silueta) and any(f[-1] == "#" for f in silueta))
        # Silueta redonda: ninguna celda dibujada cae fuera del circulo circunscrito.
        fuera = [(i, j) for j, f in enumerate(silueta) for i, ch in enumerate(f)
                 if ch == "#" and math.hypot(i - c, j - c) > n / 2 + 0.25]
        anotar(f"{pre} silueta circular", not fuera, f"celdas fuera del circulo: {fuera}")
        amar = [(i, j) for j, f in enumerate(celdas) for i, ch in enumerate(f) if ch == "a"]
        if amar:
            mx = sum(i for i, _ in amar) / len(amar)
            my = sum(j for _, j in amar) / len(amar)
            anotar(f"{pre} estrella centrada", abs(mx - c) < 1e-9 and abs(my - c) <= 0.5,
                   f"centroide ({mx:.2f}, {my:.2f}), centro ({c:.1f}, {c:.1f})")
        else:
            anotar(f"{pre} tiene estrella (codigo a)", False)
        verdes = [(i, j) for j, f in enumerate(celdas) for i, ch in enumerate(f) if ch == "v"]
        anotar(f"{pre} tiene corona (codigo v)", bool(verdes))
        if verdes and amar:
            techo = min(j for _, j in amar)
            piso = max(j for _, j in amar)
            centro = {int(math.floor(c)), int(math.ceil(c))}
            arriba = [p for p in verdes if p[0] in centro and p[1] < techo]
            abajo = [p for p in verdes if abs(p[0] - c) <= 1 and p[1] > piso]
            anotar(f"{pre} corona abierta arriba", not arriba, f"verdes sobre la estrella: {arriba}")
            anotar(f"{pre} corona cerrada abajo", bool(abajo))
        anotar(f"{pre} anillo de tinta continuo en el borde",
               all(celdas[j][i] == "n" for j, f in enumerate(silueta) for i, ch in enumerate(f)
                   if ch == "#" and _es_borde(silueta, i, j)))

        filas, cols = mp["grilla"]["filas"], mp["grilla"]["columnas"]
        anotar(f"{pre} grilla {filas}x{cols}: filas multiplo de 3", filas % 3 == 0)
        desvio = (filas / cols) / (g["proporcion_alto"] / g["proporcion_ancho"]) - 1
        anotar(f"{pre} grilla {filas}x{cols}: paso casi cuadrado (desvio <= 1,1 %)",
               abs(desvio) <= 0.011, f"{100 * desvio:+.2f} %")
        if tipo == "subgrilla":
            anotar(f"{pre} lado impar (hay celda central)", n % 2 == 1)
            rel = diametro_relativo(datos, mp)
            anotar(f"{pre} el escudo cabe en la franja blanca", 0.0 < rel < 1.0,
                   f"diametro {rel:g} x franja")
            t = totales(datos, mp)
            anotar(f"{pre} el hueco no muerde las filas de borde de la franja blanca",
                   not t["franja_blanca_mordida"], f"retirados {t['retirados']}")
            hol = holgura_minima(datos, mp)
            anotar(f"{pre} ningun punto principal se solapa con un sub-punto", hol >= 0,
                   f"holgura minima {hol:+.3f} pasos")
        else:
            por_franja = filas // 3
            f0, c0 = por_franja + (por_franja - n) / 2, (cols - n) / 2
            anotar(f"{pre} nativo centrable (paridades compatibles)",
                   f0 == int(f0) and c0 == int(c0), f"fila0 {f0}, columna0 {c0}")
            anotar(f"{pre} fila0/columna0 declarados = calculados",
                   mp.get("fila0") == f0 and mp.get("columna0") == c0,
                   f"declarado ({mp.get('fila0')}, {mp.get('columna0')})")
            anotar(f"{pre} cabe en la franja blanca", n <= por_franja)

        if texto:
            anotar(f"{pre} mapa ASCII del documento = bloque JSON",
                   ascii_doc.get(nombre) == celdas,
                   "" if nombre in ascii_doc else "no hay bloque <!-- mapa:NOMBRE -->")
            t = titulos.get(nombre)
            if t:
                cuenta = conteo(celdas)
                propios = sum(v for k, v in cuenta.items() if k != ".")
                declarado = dict((p.split()[0], int(p.split()[1]))
                                 for p in t.group(5).split(","))
                real = {k: v for k, v in cuenta.items() if k != "."}
                anotar(f"{pre} titulo del documento: dimensiones y conteos",
                       int(t.group(2)) == n and int(t.group(3)) == n
                       and int(t.group(4)) == propios and declarado == real,
                       f"real {n}x{n}, {propios} puntos, {real}")

    if texto:
        # Tabla de grillas candidatas (seccion 3.2).
        filas_tabla = list(RE_FILA_GRILLA.finditer(texto))
        anotar("tabla 3.2: se encontraron filas", len(filas_tabla) >= 3, str(len(filas_tabla)))
        for m in filas_tabla:
            f, c = int(m.group(1)), int(m.group(2))
            ok = (f % 3 == 0 and int(m.group(3)) == f // 3 and int(m.group(4)) == f * c
                  and abs(num(m.group(5)) - f / c) < 5e-5
                  and abs(num(m.group(6)) - 100 * (f / c / 0.55 - 1)) < 5e-3
                  and abs(num(m.group(7)) - 0.55 * c / f) < 5e-5)
            anotar(f"tabla 3.2: fila {f}x{c}", ok,
                   f"por franja {f / 3:g}, puntos {f * c}, F/C {f / c:.4f}, "
                   f"desvio {100 * (f / c / 0.55 - 1):+.2f} %, paso v/h {0.55 * c / f:.4f}")
        # Tabla de totales con sub-grilla (seccion 3.3).
        filas_totales = list(RE_FILA_TOTALES.finditer(texto))
        con_sub = [n for n, mp in mapas.items() if mp.get("tipo") == "subgrilla"]
        anotar("tabla 3.3: una fila por cada mapa de sub-grilla",
               sorted(m.group(3) for m in filas_totales) == sorted(con_sub),
               f"filas: {[m.group(3) for m in filas_totales]}")
        for m in filas_totales:
            f, c, nombre = int(m.group(1)), int(m.group(2)), m.group(3)
            mp = mapas.get(nombre)
            if not mp:
                anotar(f"tabla 3.3: {nombre} existe", False)
                continue
            t = totales(datos, mp)
            ok = ((mp["grilla"]["filas"], mp["grilla"]["columnas"]) == (f, c)
                  and abs(num(m.group(4)) - t["subpaso_sobre_paso"]) < 5e-4
                  and int(m.group(5)) == t["retirados"] and int(m.group(6)) == t["subpuntos"]
                  and int(m.group(7)) == t["total"]
                  and abs(num(m.group(8)) - t["diametro_sobre_franja"]) < 5e-3
                  and abs(num(m.group(9)) - t["holgura_minima_en_pasos"]) < 5e-3)
            anotar(f"tabla 3.3: fila {f}x{c} {nombre}", ok,
                   f"calculado: {t['subpaso_sobre_paso']}, {t['retirados']} retirados, "
                   f"{t['subpuntos']} sub-puntos, total {t['total']}, diametro "
                   f"{t['diametro_sobre_franja']:g}, holgura {t['holgura_minima_en_pasos']:+.2f}")
    return res


def _es_borde(silueta, i, j):
    """Una celda dibujada es de borde si algun vecino (4-conexo) queda fuera de la silueta."""
    n = len(silueta)
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = i + di, j + dj
        if not (0 <= a < n and 0 <= b < n) or silueta[b][a] == ".":
            return True
    return False


# --------------------------------------------------------------------------
# Dibujo (Pillow)
# --------------------------------------------------------------------------

def pintar(puntos, caja, escala, fondo, colores, ss=4):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = caja
    w, h = max(1, round((x1 - x0) * escala)), max(1, round((y1 - y0) * escala))
    im = Image.new("RGB", (w * ss, h * ss), fondo)
    d = ImageDraw.Draw(im)
    k = escala * ss
    for x, y, r, cod in puntos:
        if x + r < x0 or x - r > x1 or y + r < y0 or y - r > y1:
            continue
        d.ellipse([(x - r - x0) * k, (y - r - y0) * k, (x + r - x0) * k, (y + r - y0) * k],
                  fill=colores[cod])
    return im.resize((w, h), Image.LANCZOS)


def comprobar_bandera(im, borde, medida, colores):
    """Analisis de pixeles del PNG de la bandera: orden de franjas y colores del escudo."""
    def hex_a_rgb(hx):
        return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))

    def cerca(p, hx, tol=40):
        return all(abs(a - b) <= tol for a, b in zip(p, hex_a_rgb(hx)))

    px = im.load()
    w, h = im.size
    alto = medida["alto"]

    def cuenta_en(y_rel0, y_rel1, cod, x0=0, x1=w):
        y0, y1 = int(borde + y_rel0 * alto), int(borde + y_rel1 * alto)
        return sum(1 for y in range(y0, y1) for x in range(x0, x1) if cerca(px[x, y], colores[cod]))

    res = {"rojo_arriba": cuenta_en(0, 1 / 3, "R"), "rojo_abajo": cuenta_en(2 / 3, 1, "R"),
           "azul_abajo": cuenta_en(2 / 3, 1, "A"), "azul_arriba": cuenta_en(0, 1 / 3, "A"),
           "blanco_centro": cuenta_en(1 / 3, 2 / 3, "B"),
           "verde_centro": cuenta_en(1 / 3, 2 / 3, "v"),
           "amarillo_centro": cuenta_en(1 / 3, 2 / 3, "a"),
           "verde_fuera": cuenta_en(0, 1 / 3, "v") + cuenta_en(2 / 3, 1, "v")}
    res["ok"] = (res["rojo_arriba"] > 0 and res["rojo_abajo"] == 0 and res["azul_abajo"] > 0
                 and res["azul_arriba"] == 0 and res["blanco_centro"] > 0
                 and res["verde_centro"] > 0 and res["amarillo_centro"] > 0
                 and res["verde_fuera"] == 0)
    return res


def dibujar(datos, nombre, mapa, salida, modos, paleta, ancho, celda, zoom, fondo):
    colores = {k: v.get(paleta) for k, v in datos["leyenda"].items()}
    sufijo = "" if paleta == "oscuro" else f"_{paleta}"
    grilla = f"{mapa['grilla']['filas']}x{mapa['grilla']['columnas']}"
    hechos = {}
    if "escudo" in modos:
        pts, (w, h) = puntos_escudo(datos, mapa, celda)
        ruta = salida / f"escudo_{nombre}{sufijo}.png"
        pintar(pts, (0, 0, w, h), 1, fondo, colores).save(ruta)
        hechos["escudo"] = str(ruta)
    if "bandera" in modos or "detalle" in modos:
        pts, m = puntos_bandera(datos, mapa, ancho)
        if "bandera" in modos:
            borde = 40
            im = pintar(pts, (-borde, -borde, ancho + borde, m["alto"] + borde), 1, fondo, colores)
            ruta = salida / f"bandera_{grilla}_{nombre}{sufijo}.png"
            im.save(ruta)
            hechos["bandera"] = str(ruta)
            hechos["pixeles"] = comprobar_bandera(im, borde, m, colores)
        if "detalle" in modos:
            mitad = 0.8 * m["franja"]
            cx, cy = ancho / 2, m["alto"] / 2
            im = pintar(pts, (cx - mitad, cy - mitad, cx + mitad, cy + mitad), zoom, fondo, colores)
            ruta = salida / f"detalle_{grilla}_{nombre}{sufijo}.png"
            im.save(ruta)
            hechos["detalle"] = str(ruta)
    return hechos


# --------------------------------------------------------------------------
# Linea de ordenes
# --------------------------------------------------------------------------

def crear_parser():
    p = argparse.ArgumentParser(
        prog="render_mapa_puntos.py",
        description="Valida y dibuja (PNG, fondo oscuro) los mapas de puntos del escudo "
                    "definidos en el bloque mapas-json de docs/investigacion/bandera-paraguay.md.",
        epilog="Ejemplos:\n"
               "  python scripts/render_mapa_puntos.py --validar\n"
               "  python scripts/render_mapa_puntos.py --mapa M21 --modo detalle --zoom 4\n"
               "  python scripts/render_mapa_puntos.py --paleta fiel --salida output/temporales/x\n"
               "  python scripts/render_mapa_puntos.py --exportar-json output/temporales/mapas.json\n"
               "Codigos de salida: 0 correcto; 1 validacion fallida; 2 argumentos; "
               "3 fuente ilegible o falta Pillow.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    fuente = p.add_mutually_exclusive_group()
    fuente.add_argument("--doc", type=Path, default=DOC_DEFECTO, metavar="RUTA",
                        help="documento Markdown con el bloque mapas-json "
                             "(por defecto: docs/investigacion/bandera-paraguay.md)")
    fuente.add_argument("--json", type=Path, default=None, metavar="RUTA",
                        help="leer los datos de un JSON suelto en vez del documento "
                             "(se omiten las comprobaciones contra el texto del documento)")
    p.add_argument("--salida", type=Path, default=SALIDA_DEFECTO, metavar="DIR",
                   help="carpeta de salida (por defecto: output/temporales/verif-bandera)")
    p.add_argument("--mapa", action="append", metavar="NOMBRE",
                   help="mapa a dibujar; se puede repetir (por defecto: todos)")
    p.add_argument("--modo", choices=("todo", "escudo", "bandera", "detalle"), default="todo",
                   help="que dibujar: el escudo suelto ampliado, la bandera completa, "
                        "el detalle del centro o todo (por defecto: todo)")
    p.add_argument("--paleta", choices=("oscuro", "fiel"), default="oscuro",
                   help="colores recomendados sobre fondo oscuro o colores fieles "
                        "(por defecto: oscuro)")
    p.add_argument("--ancho", type=int, default=960, metavar="PX",
                   help="ancho de la bandera en la imagen (por defecto: 960)")
    p.add_argument("--celda", type=int, default=24, metavar="PX",
                   help="paso entre puntos en la imagen del escudo suelto (por defecto: 24)")
    p.add_argument("--zoom", type=float, default=3.0, metavar="Z",
                   help="ampliacion del detalle del centro (por defecto: 3)")
    p.add_argument("--fondo", default=None, metavar="HEX",
                   help="color de fondo #RRGGBB (por defecto: el del bloque JSON)")
    p.add_argument("--validar", action="store_true",
                   help="solo validar, sin dibujar (no necesita Pillow)")
    p.add_argument("--listar", action="store_true",
                   help="listar los mapas con sus conteos y salir")
    p.add_argument("--exportar-json", type=Path, default=None, metavar="RUTA",
                   help="escribir en RUTA el bloque JSON extraido del documento")
    return p


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    p = crear_parser()
    a = p.parse_args(argv)
    if a.ancho < 100 or a.celda < 4 or a.zoom <= 0:
        p.error("--ancho debe ser >= 100, --celda >= 4 y --zoom > 0")
    if a.fondo is not None and not RE_HEX.match(a.fondo):
        p.error("--fondo debe tener la forma #RRGGBB")
    try:
        datos, texto = cargar(a.doc, a.json)
    except ErrorFuente as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    mapas = datos.get("mapas", {})
    elegidos = a.mapa or list(mapas)
    desconocidos = [n for n in elegidos if n not in mapas]
    if desconocidos:
        p.error(f"mapa desconocido: {', '.join(desconocidos)} (hay: {', '.join(mapas)})")

    if a.listar:
        for nombre, mp in mapas.items():
            t = totales(datos, mp)
            print(f"{nombre}: {mp['tipo']}, {mp['lado']}x{mp['lado']}, grilla "
                  f"{mp['grilla']['filas']}x{mp['grilla']['columnas']}, "
                  f"conteo {conteo(mp['celdas'])}, totales {t}")
        return 0

    if a.exportar_json:
        a.exportar_json.parent.mkdir(parents=True, exist_ok=True)
        a.exportar_json.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
        print(f"JSON exportado: {a.exportar_json}")

    resultados = validar(datos, texto)
    fallos = [r for r in resultados if not r[1]]
    for nombre, ok, detalle in resultados:
        print(f"{'PASS' if ok else 'FAIL'}  {nombre}" + (f"  [{detalle}]" if detalle else ""))
    print(f"VALIDACION: {'PASS' if not fallos else 'FAIL'} "
          f"({len(resultados) - len(fallos)}/{len(resultados)} comprobaciones)")

    metricas = {"fuente": str(a.json or a.doc), "validacion_ok": not fallos,
                "comprobaciones": len(resultados),
                "fallos": [f"{n} [{d}]" for n, _, d in fallos], "mapas": {}}
    for nombre in elegidos:
        metricas["mapas"][nombre] = {"conteo": conteo(mapas[nombre]["celdas"]),
                                     "totales": totales(datos, mapas[nombre])}
    pixeles_ok = True
    if not a.validar:
        try:
            import PIL  # noqa: F401
        except ImportError:
            print("ERROR: falta Pillow (pip install Pillow); use --validar para validar "
                  "sin dibujar", file=sys.stderr)
            return 3
        a.salida.mkdir(parents=True, exist_ok=True)
        modos = ("escudo", "bandera", "detalle") if a.modo == "todo" else (a.modo,)
        fondo = a.fondo or datos.get("fondo", "#000000")
        for nombre in elegidos:
            try:
                hechos = dibujar(datos, nombre, mapas[nombre], a.salida, modos, a.paleta,
                                 a.ancho, a.celda, a.zoom, fondo)
            except (KeyError, IndexError, TypeError) as e:
                # Datos incoherentes (ya senalados arriba por la validacion): no se dibuja.
                print(f"FAIL  {nombre}: no se pudo dibujar ({type(e).__name__}: {e})")
                pixeles_ok = False
                continue
            metricas["mapas"][nombre]["archivos"] = hechos
            for modo in modos:
                print(f"PNG  {hechos[modo]}")
            if "pixeles" in hechos:
                ok = hechos["pixeles"]["ok"]
                pixeles_ok = pixeles_ok and ok
                print(f"{'PASS' if ok else 'FAIL'}  {nombre}: pixeles de la bandera "
                      f"(franjas en orden, verde y amarillo solo en el centro)")
        metricas["pixeles_ok"] = pixeles_ok
        ruta = a.salida / "metricas.json"
        ruta.write_text(json.dumps(metricas, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
        print(f"METRICAS  {ruta}")
    return 0 if not fallos and pixeles_ok else 1


if __name__ == "__main__":
    sys.exit(main())
