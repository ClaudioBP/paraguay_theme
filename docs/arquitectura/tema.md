# Arquitectura del tema `paraguay`

Cómo está hecho el tema y por qué. Los números que respaldan cada elección
están en [plymouth-script-mediciones.md](../investigacion/plymouth-script-mediciones.md);
las reglas del lenguaje, en
[plymouth-script-referencia.md](../investigacion/plymouth-script-referencia.md);
la bandera, en [bandera-paraguay.md](../investigacion/bandera-paraguay.md).

## Piezas

| Pieza | Qué es | Quién la produce |
|---|---|---|
| `paraguay/paraguay.plymouth` | Descriptor del tema (`ModuleName=script`) | A mano |
| `paraguay/paraguay.script` | La animación, en el lenguaje de script de Plymouth | A mano, salvo el bloque «DATOS GENERADOS» |
| `paraguay/p<paso>.png` | Atlas de tramos de la grilla principal | `scripts/generar_tema.py` |
| `paraguay/e<paso>.png` | Atlas de piezas del escudo | `scripts/generar_tema.py` |
| `paraguay/d<paso>.png` | Puntos del diálogo (apagado y encendido) | `scripts/generar_tema.py` |

`<paso>` es la separación entre puntos en píxeles. Hay un juego de atlas por
cada paso soportado (8 a 32 px); el script elige el mayor que deje la bandera
dentro del 56 % del ancho y del 54 % del alto de la pantalla más chica.

## La bandera en puntos

- Grilla principal de 24 × 44 puntos (8 filas por franja), proporción 11:20
  exacta: el paso vertical es 1,00833 veces el horizontal.
- El escudo del anverso se dibuja con una sub-grilla más fina de 17 × 17
  (mapa M17), centrada en la franja blanca; los 32 puntos principales que
  taparía se retiran.
- El generador lee el mapa y la paleta del bloque JSON de
  `docs/investigacion/bandera-paraguay.md`, que es la fuente de verdad.

## Por qué tramos y no puntos sueltos

En Plymouth cada cosa que se mueve es un *sprite*, y mover un sprite cuesta dos
veces: el intérprete tarda unos 6,5 µs por sprite y refresco (tres llamadas
nativas: `SetX`, `SetY`, `SetImage`), y el compositor recorta rectángulos con
costo cuadrático en la cantidad de sprites que cambiaron.

Un sprite por punto serían 1110 sprites. El tema agrupa los puntos en **tramos
verticales de 4** (media franja): 264 tramos de la grilla más 17 piezas del
escudo (una por sub-columna), 281 sprites. Los cuatro puntos de un tramo se
mueven juntos y comparten tamaño y brillo.

Cada sub-columna del escudo va entera en una sola pieza y todas cuelgan de la
misma banda. El escudo cae a caballo de dos bandas; partirlo entre ambas hacía
que sus dos mitades se encimaran o se separaran un par de píxeles al pasar la
cresta, justo sobre la estrella.

Cada tramo está dibujado de antemano en un atlas, en 5 tamaños × 7 brillos
(35 *aspectos*). El tamaño da la sensación de relieve (la cresta se acerca) y el
brillo, la de luz lateral. El nivel central de cada eje es el reposo: punto de
0,66 pasos de diámetro y color base exacto. Como el brillo va dibujado en la
imagen, no hace falta una cuarta llamada (`SetOpacity`) por sprite.

Un atlas es una cuadrícula uniforme: una fila por *familia* (la secuencia de
colores del tramo: `RRRR`, `BBBB`, `AAAA`, y las variantes recortadas por el
escudo) y una columna por aspecto. El script la parte con `Image.Crop`
dividiendo el ancho y el alto, sin conocer medidas en píxeles.

## Los bordes de los puntos

Plymouth guarda las imágenes con el color ya multiplicado por el alfa. Al
recortar una celda del atlas con `Image.Crop` la mezcla sobre un lienzo
transparente, y en esa mezcla vuelve a multiplicar el color por el alfa: un
píxel de borde con 50 % de cobertura llega a pantalla con el 25 % del color.
En los puntos grandes apenas se nota; los sub-puntos del escudo en pantallas
chicas (2 a 3 px) son casi todo borde y el escudo quedaba como una mancha gris.
El generador lo compensa guardando en el PNG la raíz cuadrada del alfa. La
revisión lo midió en el Plymouth real a 640×480 con una variante de prueba: el
brillo del escudo respecto de la franja blanca pasó de 0,72 a 0,96.

## La onda

Para cada columna de la bandera y cada paso de tiempo se calculan tres valores:
la posición horizontal del tramo, su desplazamiento vertical y su aspecto. Son
61 columnas (44 de la grilla y 17 del escudo, que se evalúan en su propia
posición para que el escudo se doble con la tela).

El desplazamiento es la suma de dos ondas que viajan del asta al batiente,
multiplicada por una envolvente que vale casi cero en el asta y uno en el
batiente; a eso se suman una caída por gravedad y un acortamiento horizontal.
La luz usa las mismas dos ondas con un desfase, así que no cuesta trigonometría
adicional.

Las filas de la tabla se calculan la primera vez que hacen falta y se guardan
(`TX`, `TY`, `TK`). La onda es un bucle de 3 s (90 pasos a 30 refrescos por
segundo): pasada la primera vuelta, el script ya no calcula nada y solo lee.

**Pliegue diagonal.** Las seis bandas de tramos leen la misma tabla, cada una
`RET` pasos más atrás que la de arriba. La onda llega un instante después a
cada banda y los pliegues salen inclinados, como en una tela, sin calcular nada
por tramo.

## El cobertor

Plymouth redibuja solo las áreas que cambiaron, pero arma esa lista comparando
cada rectángulo nuevo con todos los anteriores. Con unos 300 tramos moviéndose
son unos 600 rectángulos por refresco y el costo se dispara (71 % de un núcleo en el
banco, contra 27 %).

El *cobertor* es un sprite invisible, por debajo de todos, del tamaño de la caja
que recorre la bandera. En cada refresco se le reasigna su misma imagen, lo que
lo marca como cambiado. Como es el primero de la lista y contiene a todos los
demás, Plymouth descarta los otros rectángulos en cuanto los ve y redibuja la
caja una sola vez.

## Velocidad constante

El lenguaje no tiene reloj y Plymouth no saltea cuadros: si un equipo no llega a
refrescar 30 veces por segundo, una animación que avanza un paso por refresco
se vuelve lenta. La única medida de tiempo real llega con el aviso de progreso
de arranque. El tema la usa para medir, cada medio segundo, cuántos refrescos
por segundo está logrando (con un promedio móvil que amortigua los altibajos)
y, si son menos o más que los pedidos, avanza la onda en pasos más largos o
más cortos. Dentro de un ±15 % no corrige, para no introducir saltos.

Con un ritmo estable la corrección es exacta: en el banco, con Plymouth
refrescando a 50 por segundo, el bucle sigue durando 3,0 s. Con un ritmo que
sube y baja es aproximada. Cuando el paso es menor que uno, los refrescos que
no traen un paso nuevo no mueven ni redibujan nada.

Ese reloj se congela mientras se pide una clave; en ese caso el tema conserva
el último paso medido y la bandera sigue ondeando. Una medida imposible (la que
sale al descongelarse) se descarta.

## Entrada

La bandera aparece desde el asta hacia el batiente en 1,4 s: durante la entrada
cada tramo recibe además una opacidad que depende de su columna. No hay
animación de salida porque Plymouth destruye el tema en cuanto recibe la orden
de terminar.

## Diálogo

Debajo de la bandera, y solo cuando hace falta:

- **Clave (LUKS):** el texto del pedido y una fila de 24 ranuras; cada carácter
  tecleado enciende una.
- **Pregunta:** igual, más el texto que se va escribiendo.
- **Mensajes:** una línea de texto.
- **Actualizaciones sin conexión:** las ranuras hacen de barra de progreso.

Las ranuras son imágenes del tema, no texto: si en el initramfs no hay plugin
de etiquetas ni fuentes, `Image.Text` devuelve una imagen vacía y el pedido de
clave sigue siendo visible por la fila de puntos.

## Cuando cambian las pantallas

En un arranque real Plymouth suele empezar con una pantalla provisoria y agrega
la definitiva cuando termina de cargar el controlador de video: cambian el
tamaño del lienzo y el paso de grilla que corresponde. El tema registra
`SetDisplayHotplugFunction` y, cuando llega ese aviso, vuelve a medir las
pantallas. Si las medidas cambiaron arma la escena de nuevo (tamaño, atlas,
tramos, cobertor), repite la entrada y repone lo que hubiera en el diálogo. El
aviso llega una vez por cada pantalla quitada y por cada una agregada: sin
pantallas, o si al final quedaron las mismas medidas, no hace nada. El renderer
del banco no emite ese aviso; el rearmado se prueba llamándolo a mano (variante
`rearmar` de `scripts/medir_tema.py`).

## Versiones de Plymouth

El tema necesita **Plymouth 0.9.5 o posterior** (2020): es la primera versión
con `Image.Crop`, sin la cual no se pueden partir los atlas y la pantalla queda
en negro. Sacado del historial del repositorio de Plymouth:

| Qué usa el tema | Desde | Si falta |
|---|---|---|
| `Image.Crop` | 0.9.5 | No hay imágenes: pantalla en negro. Es el requisito. |
| `Plymouth.SetRefreshRate`, `SetSystemUpdateFunction` | 0.9.2 | — |
| `SetDisplayMessageFunction`, `SetHideMessageFunction` | 0.8.4 | — |
| `String.SubString`, `CharAt` | 0.8.0 | — |
| `Plymouth.SetDisplayHotplugFunction` | 23.51 | La llamada no hace nada; el tema no se rearma si cambia la pantalla. |
| `Window.GetWidth()` sin índice = el máximo entre pantallas | 22.02 | **No se usa**: en 0.9.5 daba el mínimo. El lienzo se calcula recorriendo las pantallas por índice. |
| `String.Length` | 23.51 | **No se usa**: en 0.9.5 y 22.02 devolvería NULL. El largo se cuenta con `CharAt`. |

Llamar a algo que no existe devuelve NULL sin error; por eso lo que apareció
después de 0.9.5 se usa solo donde un NULL es inofensivo, y
`scripts/validar_tema.py` rechaza cualquier llamada que no esté en su lista.
Solo está probado con 24.004.60 (Ubuntu 24.04); lo demás sale del código fuente.

## Qué tocar para cambiar algo

| Quiero cambiar | Dónde |
|---|---|
| Forma, velocidad o amplitud de la onda | `ONDA` en `scripts/generar_tema.py` |
| Colores, tamaños o brillos de los puntos | `SOMBRAS`, `BRILLOS`, `DIAMETROS_*` en el generador |
| Grilla o mapa del escudo | `COLS`, `FILAS`, `MAPA_ESCUDO` en el generador, y pasar `scripts/render_mapa_puntos.py --validar` |
| Costo en equipos lentos | `FPS` y `TRAMO` en el generador |
| Tamaño de la bandera en pantalla | La línea `lim = Math.Min(...)` del script |
| Textos y posiciones del diálogo | Sección «dialogo» del script |

Después de cualquier cambio: `python scripts/generar_tema.py` y
`python scripts/validar_tema.py`.
