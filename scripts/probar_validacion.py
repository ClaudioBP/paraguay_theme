#!/usr/bin/env python3
"""Prueba que la validación detecta un tema roto (pruebas de mutación).

Para cada defecto de la lista crea una copia del proyecto en
output/temporales/mutantes/<nombre>/, le introduce el defecto y corre sobre la
copia su propio scripts/validar_tema.py. La validación sirve si rechaza todos
los mutantes y aprueba la copia sin tocar («base»).

Cada mutante indica cuánta validación hace falta para verlo: «sin-banco»
(segundos), «rapida» (una corrida del banco, unos 2 minutos) o «completa»
(unos 10 minutos). Por defecto se corren los dos primeros grupos.

Ejemplos:
  python scripts/probar_validacion.py                 # base + mutantes rápidos (unos 40 minutos)
  python scripts/probar_validacion.py --todos         # también los que piden la validación completa
  python scripts/probar_validacion.py escudo_ausente franjas_invertidas
  python scripts/probar_validacion.py --lista
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_MUTANTES = RAIZ / "output" / "temporales" / "mutantes"
COPIAR = ["scripts", "paraguay", "instalar.sh", "desinstalar.sh", "docs/investigacion/bandera-paraguay.md"]

S = "paraguay/paraguay.script"
G = "scripts/generar_tema.py"
TRAMO = "if (!f) f = FAMB[b] + 1;"
PIEZA_Y = "Math.Int(Y0 + FH / 2 + (p[2] - EMED) * SUB - SUB / 2), 2);"
TEXTO_CLAVE = "    if (DLG_TIPO != 1 || pregunta != DLG_PREG) poner_texto(TXT_PREGUNTA, pregunta, DLG_Y);\n"
REFRESCO = "Plymouth.SetRefreshFunction(al_refrescar);"

# nombre: (validación necesaria, qué defecto es, cambios [(archivo, viejo, nuevo)] o acción, regenerar imágenes)
MUTANTES: dict[str, tuple[str, str, object, bool]] = {
    "base": ("rapida", "sin defecto: debe aprobar", [], False),
    # --- bandera ---
    "franjas_invertidas": ("rapida", "azul arriba y roja abajo",
                           [(S, TRAMO, "if (!f) f = FAMB[NBANDAS - 1 - b] + 1;")], False),
    "franjas_blanca_azul": ("rapida", "franjas blanca y azul intercambiadas",
                            [(S, TRAMO, "if (!f) { f = FAMB[b] + 1; if (f == 2) f = 3; else if (f == 3) f = 2; }")], False),
    "franjas_mal_desde_col10": ("rapida", "franjas invertidas salvo junto al asta",
                                [(S, TRAMO, "if (!f) { f = FAMB[b] + 1; if (c > 9) f = FAMB[NBANDAS - 1 - b] + 1; }")], False),
    "banda_ausente": ("rapida", "falta una banda de tramos",
                      [(S, "            if (f > 0) nuevo_tramo(b, c, IMP[f - 1], y, 1);",
                        "            if (f > 0 && b != 1) nuevo_tramo(b, c, IMP[f - 1], y, 1);")], False),
    "escudo_ausente": ("rapida", "sin escudo", [(S, "for (q = 0; q < NEP; q++) {", "for (q = 0; q < 0; q++) {")], False),
    "escudo_en_roja": ("rapida", "escudo en la franja roja", [(S, PIEZA_Y, PIEZA_Y.replace("FH / 2", "FH / 6"))], False),
    "escudo_2_pasos_arriba": ("rapida", "escudo corrido dos pasos hacia arriba",
                              [(S, PIEZA_Y, PIEZA_Y.replace("- SUB / 2)", "- SUB / 2 - 2 * PASO)"))], False),
    "escudo_revuelto": ("rapida", "piezas del escudo en desorden",
                        [(S, "nuevo_tramo(p[1], COLS + p[0], IME[p[3]],", "nuevo_tramo(p[1], COLS + p[0], IME[NFE - 1 - p[3]],")], False),
    "descentrada_mucho": ("rapida", "bandera a un tercio del ancho",
                          [(S, "global.X0 = Math.Int(ANCHO / 2 - FW / 2);", "global.X0 = Math.Int(ANCHO / 3 - FW / 2);")], False),
    "descentrada_2_pasos": ("rapida", "bandera corrida dos pasos a la derecha",
                            [(S, "global.X0 = Math.Int(ANCHO / 2 - FW / 2);",
                              "global.X0 = Math.Int(ANCHO / 2 - FW / 2 + 2 * PASO);")], False),
    # --- animación ---
    "quieta": ("rapida", "la bandera se revela y queda inmóvil",
               [(S, REFRESCO, "fun al_medir () {\n    if (INTRO) al_refrescar();\n}\nPlymouth.SetRefreshFunction(al_medir);")], False),
    "bucle_con_salto": ("rapida", "la onda no cierra el bucle",
                        [(S, "    local.w1 = W1 * st;", "    local.w1 = W1 * st * 0.9;")], False),
    "cobertor_visible": ("rapida", "el sprite cobertor se dibuja", [(S, "    COBERTOR.SetOpacity(0);\n", "")], False),
    "revela_desde_batiente": ("rapida", "la entrada empieza por el batiente",
                              [(S, "            n = (o - CU[k]) / REV_A;", "            n = (o - (1 - CU[k])) / REV_A;")], False),
    # --- diálogo ---
    "sin_dialogo_clave": ("rapida", "el pedido de clave no se dibuja",
                          [(S, "Plymouth.SetDisplayPasswordFunction(al_pedir_clave);\n", "")], False),
    "clave_sin_ranuras": ("rapida", "pedido de clave sin la fila de ranuras",
                          [(S, "    TXT_ENTRADA.SetOpacity(0);\n    poner_ranuras(tecleados, 1);",
                            "    TXT_ENTRADA.SetOpacity(0);\n    poner_ranuras(tecleados, 0);")], False),
    "clave_sin_texto": ("rapida", "pedido de clave sin su texto", [(S, TEXTO_CLAVE, "")], False),
    "texto_clave_sobre_bandera": ("rapida", "el texto del pedido se dibuja sobre la bandera",
                                  [(S, TEXTO_CLAVE, TEXTO_CLAVE.replace("pregunta, DLG_Y);", "pregunta, Y0 + FH / 2);"))], False),
    "dialogo_sobre_bandera": ("rapida", "todo el diálogo sobre la bandera",
                              [(S, "global.DLG_Y = Math.Int(Y0 + FH + PASO * (AY + CAIDA + 1.5));",
                                "global.DLG_Y = Math.Int(Y0 + FH / 2 - PASO * 2);")], False),
    # --- errores del script ---
    "error_ejecucion": ("rapida", "error de ejecución en cada refresco",
                        [(S, "    CUADROS = CUADROS + 1;\n", "    CUADROS = CUADROS + 1;\n    local.basura = -FUENTE;\n")], False),
    "error_silencioso": ("sin-banco", "llamada a un método que no existe",
                         [(S, "    TXT_PREGUNTA.SetOpacity(0);\n    if (ACTUALIZANDO) {",
                           "    TXT_PREGUNTA.SetOpacidad(0);\n    if (ACTUALIZANDO) {")], False),
    "crlf": ("sin-banco", "script con finales de línea CRLF", "CRLF", False),
    # --- imágenes y generador ---
    "atlas_ausente": ("sin-banco", "falta el atlas de un paso", "BORRAR:paraguay/p20.png", False),
    "atlas_corrupto": ("sin-banco", "un atlas dañado", "CORROMPER:paraguay/e10.png", False),
    "rojo_equivocado": ("sin-banco", "rojo #FF0000 en el documento de la bandera", "ROJO", True),
    "gen_escudo_vacio": ("sin-banco", "el generador deja vacío el escudo en algunos pasos",
                         [(G, "d.fam_e, ancho, alto, d.subp * paso, DIAMETROS_SUBPUNTO, d.subp * paso, d.paleta))",
                           "d.fam_e if paso in (12, 16, 24) else ['.' * len(s) for s in d.fam_e], ancho, alto, "
                           "d.subp * paso, DIAMETROS_SUBPUNTO, d.subp * paso, d.paleta))")], True),
    "gen_sombras_cruzadas": ("sin-banco", "el generador cruza rojo y azul en las sombras",
                             [(G, "        return tuple(round(FONDO[i] + (base[i] - FONDO[i]) * m) for i in range(3))",
                               "        return tuple(round(FONDO[i] + (base[2 - i if ib < 2 else i] - FONDO[i]) * m) for i in range(3))")], True),
    # --- solo con la validación completa ---
    "sin_pregunta": ("completa", "las preguntas no se dibujan",
                     [(S, "Plymouth.SetDisplayQuestionFunction(al_preguntar);\n", "")], False),
    "barra_no_avanza": ("completa", "la barra de actualización no avanza",
                        [(S, "    if (DLG_TIPO) return;\n    poner_ranuras(AVANCE, 1);\n", "    if (DLG_TIPO) return;\n")], False),
    "instalador_incompleto": ("completa", "el instalador no copia todas las imágenes",
                              [("instalar.sh", '"$ORIGEN/$NOMBRE.script" "$ORIGEN"/*.png; do',
                                '"$ORIGEN/$NOMBRE.script" "$ORIGEN"/p*.png; do')], False),
    "velocidad_sin_ajuste": ("completa", "la onda no corrige su velocidad",
                             [(S, "    else PASO_T = FPS / RITMO;\n", "    else PASO_T = 1;\n")], False),
}


def crear(nombre: str) -> Path:
    _, _, cambios, regenerar = MUTANTES[nombre]
    destino = DIR_MUTANTES / nombre
    if destino.exists():
        shutil.rmtree(destino)
    for rel in COPIAR:
        origen, copia = RAIZ / rel, destino / rel
        copia.parent.mkdir(parents=True, exist_ok=True)
        if origen.is_dir():
            shutil.copytree(origen, copia, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(origen, copia)
    if cambios == "CRLF":
        p = destino / S
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    elif cambios == "ROJO":
        p = destino / "docs/investigacion/bandera-paraguay.md"
        texto = p.read_bytes().decode("utf-8")
        if "#D52B1E" not in texto:
            raise SystemExit(f"error: el mutante {nombre} ya no encaja (no está #D52B1E en el documento)")
        p.write_bytes(texto.replace("#D52B1E", "#FF0000").encode("utf-8"))
    elif isinstance(cambios, str) and cambios.startswith("BORRAR:"):
        (destino / cambios.split(":", 1)[1]).unlink()
    elif isinstance(cambios, str) and cambios.startswith("CORROMPER:"):
        p = destino / cambios.split(":", 1)[1]
        datos = bytearray(p.read_bytes())
        for i in range(len(datos) // 2, len(datos) // 2 + 40):
            datos[i] ^= 0xFF
        p.write_bytes(bytes(datos))
    else:
        for rel, viejo, nuevo in cambios:
            p = destino / rel
            texto = p.read_bytes().decode("utf-8")
            if texto.count(viejo) != 1:
                raise SystemExit(f"error: el mutante {nombre} ya no encaja en {rel}: actualizar MUTANTES")
            p.write_bytes(texto.replace(viejo, nuevo).encode("utf-8"))
    if regenerar:
        subprocess.run([sys.executable, str(destino / "scripts" / "generar_tema.py")], capture_output=True)
    return destino


def validar(destino: Path, modo: str) -> tuple[int, str, float]:
    argumentos = {"sin-banco": ["--sin-banco"], "rapida": ["--rapida"], "completa": []}[modo]
    inicio = time.time()
    r = subprocess.run([sys.executable, str(destino / "scripts" / "validar_tema.py")] + argumentos,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=destino,
                       env=dict(os.environ, PYTHONUTF8="1"))
    (destino / "salida.txt").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
    return r.returncode, r.stdout, time.time() - inicio


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("Ejemplos:")[1])
    ap.add_argument("mutantes", nargs="*", help="nombres a correr (por defecto: base y los que no piden la validación completa)")
    ap.add_argument("--todos", action="store_true", help="incluir los que necesitan la validación completa")
    ap.add_argument("--lista", action="store_true", help="listar los mutantes y salir")
    args = ap.parse_args()

    if args.lista:
        for nombre, (modo, que, _, _) in MUTANTES.items():
            print(f"{nombre:26} {modo:10} {que}")
        return 0
    desconocidos = [m for m in args.mutantes if m not in MUTANTES]
    if desconocidos:
        print(f"error: mutantes desconocidos: {', '.join(desconocidos)}", file=sys.stderr)
        return 2
    elegidos = args.mutantes or [n for n, m in MUTANTES.items() if args.todos or m[0] != "completa"]

    escapan = []
    for nombre in elegidos:
        modo, que, _, _ = MUTANTES[nombre]
        rc, salida, segundos = validar(crear(nombre), modo)
        resumen = next((linea for linea in salida.splitlines() if linea.startswith("VALIDACION:")), "sin resumen (la validación se cortó)")
        fallas = [linea[6:].split("  [")[0] for linea in salida.splitlines() if linea.startswith("FALLA")]
        if nombre == "base":
            ok, veredicto = rc == 0, "APRUEBA" if rc == 0 else "RECHAZA EL TEMA SANO"
        else:
            ok, veredicto = rc != 0, "detectado" if rc != 0 else "NO DETECTADO"
        if not ok:
            escapan.append(nombre)
        print(f"{'PASA ' if ok else 'FALLA'} {nombre} ({que}; {modo}, {segundos:.0f} s): {veredicto}. {resumen}", flush=True)
        for f in fallas[:3]:
            print(f"        {f}", flush=True)

    print()
    if escapan:
        print(f"MUTACION: FALLA ({len(elegidos) - len(escapan)}/{len(elegidos)}); sin detectar o mal juzgados: {', '.join(escapan)}")
        return 1
    print(f"MUTACION: PASA ({len(elegidos)}/{len(elegidos)}: la validación aprueba el tema sano y rechaza cada mutante)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
