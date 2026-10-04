# Cuánto cuesta animar la bandera: mediciones en el Plymouth real

Mediciones hechas con el tema `paraguay` y variantes suyas en el banco de
pruebas (`scripts/banco_plymouth.sh`). Sirven para elegir cómo animar; no son
una predicción del consumo en un arranque real (ver «Qué miden y qué no»).

Para repetirlas, con el equipo sin otra carga:

```bash
python scripts/medir_tema.py t4_30_quieto t4_30_solo_cobertor t4_30 t4_30_sin_cobertor t8_30 t2_30 t1_30 t4_50 --repeticiones 3
```

## Resultados

2026-10-04. Plymouth 24.004.60-1ubuntu7.2, renderer X11 sobre Xvfb a 1920×1080
(bandera de 1056 px de ancho, paso de grilla 24), WSL2 en un Intel i7-8550U.
Doce segundos por corrida, mediana de tres corridas; las tres corridas de cada
variante difirieron en menos de 2 puntos. Datos en
`output/evidencias/mediciones-2026-10-04.json`.

| Variante | Qué es | Sprites | CPU de `plymouthd` (% de un núcleo) | Cuadros distintos por segundo |
|---|---|---|---|---|
| `t4_30_quieto` | La bandera se revela y queda inmóvil | 298 | 8,3 | — |
| `t4_30_solo_cobertor` | Se redibuja la caja de la bandera en cada refresco, sin mover nada | 298 | 20,6 | — |
| **`t4_30`** | **El tema: tramos de 4 puntos, 30 refrescos por segundo** | **298** | **26,7** | **27** |
| `t4_30_sin_cobertor` | El tema sin el sprite cobertor | 298 | 71,4 | 29 |
| `t8_30` | Tramos de 8 puntos (una franja entera) | 149 | 23,2 | 25 |
| `t2_30` | Tramos de 2 puntos | 572 | 32,2 | 28 |
| `t1_30` | Un sprite por punto | 1110 | 42,4 | 29 |
| `t4_50` | El tema pidiendo 50 refrescos por segundo | 298 | 34,8 | 39 |

Después de estas mediciones el escudo pasó de 34 piezas a 17 (281 sprites en
total) y los atlas cambiaron el alfa de sus bordes. Repetida la medición del
tema ya corregido: 26,6 % de un núcleo, con 7,9 % de costo fijo (mediana de 3;
una de las tres corridas dio 42,8 %, un pico de carga del equipo). Datos en
`output/evidencias/mediciones-2026-10-04-tema-final.json`. La tabla de arriba
sigue valiendo para comparar variantes.

La memoria residente máxima fue de 45 a 48 MB en todas las variantes (de los
cuales unos 16 MB ya estaban antes de mostrar el tema), y el tiempo de CPU hasta
mostrar el primer cuadro, de 0,14 a 0,19 s.

## Lectura

- **Costo fijo del banco: 8 %.** Es lo que usa `plymouthd` con la bandera quieta;
  incluye el renderer X11.
- **Redibujar la caja de la bandera cuesta 12 puntos.** Es la diferencia entre
  `quieto` y `solo_cobertor`: pintar el fondo, componer los 298 sprites y
  presentar unos 0,8 megapíxeles, 30 veces por segundo. Es la parte mayor del
  costo del tema y casi no depende de cuántos sprites haya.
- **El intérprete cuesta unos 6,5 µs por sprite y refresco.** Sale de comparar
  298, 572 y 1110 sprites: 6 puntos para el tema, 22 para un sprite por punto.
- **El cobertor es imprescindible.** Sin él, el mismo tema pasa de 27 % a 71 %:
  Plymouth compara cada rectángulo dañado con todos los anteriores.
- **Tramos de 8 ahorran poco** (3,5 puntos) y se nota: cada franja se mueve
  como una cinta rígida y las tres quedan desalineadas en el batiente.
- **50 refrescos por segundo cuestan 8 puntos más** y el banco solo llega a
  mostrar 39 cuadros distintos.

De ahí la elección registrada en `DECISIONES.md` (D-0004 y D-0005): tramos de 4
puntos, cobertor y 30 refrescos por segundo. Descontado el costo fijo, el tema
usa unos 18 puntos de un núcleo en este equipo.

## Qué miden y qué no

- El banco presenta con el renderer X11 (GTK sobre un servidor X virtual). En un
  arranque real Plymouth usa DRM o framebuffer: la composición de sprites y el
  intérprete son el mismo código, pero la presentación es otra. Los 12 puntos de
  redibujo incluyen una parte, no separada aquí, que es propia de X11.
- Son comparaciones entre variantes en un mismo equipo. En uno más lento el
  intérprete rinde menos; el tema lo compensa avanzando la onda en pasos más
  largos (ver `docs/arquitectura/tema.md`), no bajando el consumo.
- «Cuadros distintos por segundo» es una cota inferior: el renderer del banco
  agrupa actualizaciones y algunos cuadros no llegan a la captura.
- Las cifras solo valen con el equipo quieto. Una primera tanda, corrida mientras
  se hacían otras pruebas, dio 39 % para la misma variante que aquí da 27 %.
- No hay mediciones en un equipo real ni en uno de bajo consumo (por ejemplo una
  Raspberry Pi). Si allí el costo importa, `FPS` y `TRAMO` en
  `scripts/generar_tema.py` son las dos perillas: 20 refrescos por segundo y
  tramos de 8 bajarían el costo a costa de fluidez y del pliegue diagonal.

## Mediciones previas, sobre el intérprete aislado

Antes de existir el tema, la referencia del lenguaje midió el intérprete y el
refresco de sprites de Plymouth compilados en un arnés, sin renderer
(`docs/investigacion/plymouth-script-referencia.md`, sección 4.4). De ahí salió
la idea del cobertor (2160 puntos moviéndose: de unos 230 ms por cuadro a unos
4 ms) y el descarte de un sprite por punto sin agrupar. Esas cifras son órdenes
de magnitud tomados con el equipo cargado; las de este documento, hechas con el
Plymouth completo, son las que respaldan la decisión.
