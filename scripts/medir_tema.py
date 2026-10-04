#!/usr/bin/env python3
"""Mide en el banco de pruebas cuánto cuesta el tema según cómo se anime.

Genera variantes del tema en output/temporales/medicion/<variante>/paraguay/
(sin tocar paraguay/), corre cada una en el Plymouth real con
scripts/banco_plymouth.sh y tabula CPU de plymouthd, tasa de animación y
memoria. Sirve para decidir con números el tamaño del tramo y los refrescos
por segundo, y para repetir la medición cuando cambie el script.

Variantes: t<TRAMO>_<FPS>[_<parche>], p. ej. t4_30, t1_50, t4_30_quieto.
Parches:
  quieto         la bandera se revela y queda inmóvil (costo fijo del banco)
  solo_cobertor  solo se redibuja la caja de la bandera, sin mover tramos
  sin_cobertor   se mueven los tramos sin el sprite cobertor
  sin_tasa       no se llama a SetRefreshRate (Plymouth refresca a 50 por segundo)
  lento          cada refresco gasta tiempo de más, como en un equipo lento
  rearmar        a los 5 s rehace la escena, como cuando Plymouth agrega una pantalla

Corre en Windows (usa WSL) y en Linux. Ejemplos:
  python scripts/medir_tema.py
  python scripts/medir_tema.py t4_30 t1_30 --segundos 12 --repeticiones 3
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_tema as gen  # noqa: E402

RAIZ = gen.RAIZ
BANCO = RAIZ / "scripts" / "banco_plymouth.sh"
DIR_MEDICION = RAIZ / "output" / "temporales" / "medicion"

VARIANTES_POR_DEFECTO = ["t4_30_quieto", "t4_30_solo_cobertor", "t4_30", "t4_30_sin_cobertor",
                         "t4_50", "t2_30", "t1_30", "t1_50"]

REGISTRO = "Plymouth.SetRefreshFunction(al_refrescar);"
PARCHES = {
    "quieto": (REGISTRO,
               "fun al_medir () {\n    if (INTRO) al_refrescar();\n}\n"
               "Plymouth.SetRefreshFunction(al_medir);"),
    "solo_cobertor": (REGISTRO,
                      "fun al_medir () {\n    if (INTRO) al_refrescar();\n    else COBERTOR.SetImage(IMG_COB);\n}\n"
                      "Plymouth.SetRefreshFunction(al_medir);"),
    "sin_cobertor": ("    COBERTOR.SetImage(IMG_COB);\n", ""),
    # Los dos siguientes los usa validar_tema.py para comprobar que la onda conserva su velocidad:
    # sin_tasa imita un Plymouth que ignora SetRefreshRate; lento, un equipo que no llega a FPS.
    "sin_tasa": ("Plymouth.SetRefreshRate(FPS);\n", ""),
    # rearmar: llama a mano al aviso de cambio de pantallas (el renderer del banco no lo emite)
    "rearmar": (REGISTRO,
                "fun al_medir () {\n    al_refrescar();\n    if (CUADROS == 150) rearmar();\n}\n"
                "Plymouth.SetRefreshFunction(al_medir);"),
    "lento": ("    local.base = Math.Int(POS);\n",
              "    local.base = Math.Int(POS);\n    local.carga = 0;\n"
              "    for (carga = 0; carga < 150000; carga++) {\n        o = carga;\n    }\n"),
}


def ruta_para_banco(p: Path) -> str:
    """Ruta tal como la ve el banco: /mnt/<unidad>/... si se corre desde Windows."""
    if platform.system() != "Windows":
        return str(p)
    p = p.resolve()
    return f"/mnt/{p.drive[0].lower()}{p.as_posix()[2:]}"


def preparar_variante(nombre: str) -> tuple[Path, int]:
    m = re.fullmatch(r"t([1248])_(\d+)(?:_(\w+))?", nombre)
    if not m or (m.group(3) and m.group(3) not in PARCHES):
        raise SystemExit(f"error: variante desconocida: {nombre}")
    tramo, fps, parche = int(m.group(1)), int(m.group(2)), m.group(3)
    archivos, d = gen.generar(tramo, fps)
    destino = DIR_MEDICION / nombre / "paraguay"
    destino.mkdir(parents=True, exist_ok=True)
    for viejo in destino.glob("*"):
        viejo.unlink()
    for origen, datos in archivos.items():
        if origen == gen.ARCHIVO_SCRIPT and parche:
            viejo, nuevo = PARCHES[parche]
            texto = datos.decode("utf-8")
            if texto.count(viejo) != 1:
                raise SystemExit(f"error: el parche {parche} ya no encaja en el script")
            datos = texto.replace(viejo, nuevo).encode("utf-8")
        (destino / origen.name).write_bytes(datos)
    (destino / "paraguay.plymouth").write_bytes((gen.DIR_TEMA / "paraguay.plymouth").read_bytes())
    sprites = gen.COLS * d.nbandas - sum(1 for v in d.exc.values() if v < 0) + len(d.piezas)
    return destino, sprites


def correr(tema: Path, salida: Path, segundos: int, tamano: str) -> dict:
    orden = ["bash", ruta_para_banco(BANCO), "probar", ruta_para_banco(tema),
             "--segundos", str(segundos), "--tamano", tamano, "--fps", "60", "--sin-frames",
             "--salida", ruta_para_banco(salida)]
    if platform.system() == "Windows":
        orden = ["wsl", "--"] + orden
    r = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8", errors="replace")
    archivo = salida / "metricas.json"
    if not archivo.exists():
        raise SystemExit(f"error: el banco no dejó métricas (código {r.returncode}):\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    m = json.loads(archivo.read_text(encoding="utf-8-sig"))
    m["_rc"] = r.returncode
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 2)[2])
    ap.add_argument("variantes", nargs="*", default=VARIANTES_POR_DEFECTO)
    ap.add_argument("--segundos", type=int, default=12, help="duración de cada corrida (por defecto 12)")
    ap.add_argument("--tamano", default="1920x1080", help="resolución del Xvfb (por defecto 1920x1080)")
    ap.add_argument("--repeticiones", type=int, default=1, help="corridas por variante; se informa la mediana")
    ap.add_argument("--json", type=Path, help="guardar también los resultados en este archivo JSON")
    args = ap.parse_args()

    filas = []
    for nombre in args.variantes:
        tema, sprites = preparar_variante(nombre)
        corridas = []
        for n in range(args.repeticiones):
            m = correr(tema, DIR_MEDICION / nombre / f"corrida{n + 1}", args.segundos, args.tamano)
            corridas.append(m)
            print(f"  {nombre} #{n + 1}: rc={m['_rc']} cpu={m['cpu_plymouthd_pct']} % "
                  f"anim={m['tasa_animacion_fps']} fps errores={len(m['errores_script'])}", flush=True)

        def med(clave):
            return round(statistics.median(c[clave] for c in corridas), 2)

        filas.append(dict(variante=nombre, sprites=sprites, rc=max(c["_rc"] for c in corridas),
                          errores=max(len(c["errores_script"]) for c in corridas),
                          cpu=med("cpu_plymouthd_pct"), cpu_xvfb=med("cpu_xvfb_pct"),
                          anim=med("tasa_animacion_fps"), rss_mb=round(med("rss_max_plymouthd_kb") / 1024, 1),
                          carga_s=med("cpu_arranque_y_carga_s")))

    print(f"\n{args.tamano}, {args.segundos} s por corrida, mediana de {args.repeticiones}\n")
    print("| Variante | Sprites | CPU plymouthd (% de un núcleo) | CPU Xvfb (%) | Animación (cuadros distintos/s) | RSS máx. (MB) | CPU de arranque y carga (s) |")
    print("|---|---|---|---|---|---|---|")
    for f in filas:
        print(f"| `{f['variante']}` | {f['sprites']} | {f['cpu']} | {f['cpu_xvfb']} | {f['anim']} | {f['rss_mb']} | {f['carga_s']} |")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(filas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    malas = [f["variante"] for f in filas if f["errores"] or f["rc"] not in (0, 14)]
    if malas:
        print(f"\nFALLA: variantes con errores de script o del banco: {', '.join(malas)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
