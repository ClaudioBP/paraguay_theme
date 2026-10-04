# La bandera del Paraguay: especificación verificada y diseño en puntos

- **Fecha de consulta de todas las fuentes:** 2026-10-03 (las del SILpy, 2026-10-04).
- **Alcance:** fijar con rigor qué hay que dibujar (proporción, franjas, colores, escudo del
  anverso) y proponer cómo dibujarlo con una grilla de puntos circulares sobre fondo oscuro.
- **Método:** cada dato se cruzó en al menos dos fuentes; cuando solo hay una, o cuando el
  dato es una medición propia, se dice. Las claves entre corchetes (`[D]`, `[F]`, …) remiten
  a la sección 5. Lo incierto está reunido en la sección 6.
- **Verificación adversarial:** hecha el 2026-10-03 por un segundo agente. Lo que confirmó,
  lo que corrigió y lo que no pudo comprobar está en la sección 8. Los mapas de puntos de la
  sección 3.3 se validan y se dibujan con `scripts/render_mapa_puntos.py` (sección 7) y sus
  datos para código están en la sección 3.6.

## Resumen para quien implementa

| Dato | Valor a usar | Estado |
|------|--------------|--------|
| Proporción alto:ancho | **11:20** (el decreto dice `1:0.55` entre lado mayor y menor) | Oficial `[D]`, confirmado `[F][WES][WEN][C]` |
| Franjas | 3 horizontales **iguales**: roja (arriba), blanca, azul (abajo) | Oficial `[D]` |
| Rojo / azul de las franjas | **No hay valor numérico oficial.** Usar `#D52B1E` / `#0038A8` | Convención `[C][WES][WEN][F]` |
| Escudo | Anverso (Sello Nacional): círculo, inscripción negra, corona verde de palma y olivo, estrella amarilla | Oficial `[D]` |
| Colores del escudo | Verde `#00A651`, amarillo `#FFF100`, negro `#000000` | Oficial (Anexo del decreto) `[D]` |
| Posición del escudo | Centro de la franja blanca (y centrado en horizontal) | Oficial `[D]` |
| Diámetro del escudo | **No está reglamentado.** Usar ≈ **0,78 × alto de la franja blanca** (0,70 en la grilla de 18×33, donde 0,78 no cabe limpio; ver 3.3) | Convención medida en `[C]` y `[F]` |
| Grillas propuestas | 18×33, 24×44 y 27×49 puntos (6, 8 y 9 filas por franja) | Propuesta de este documento |
| Mapas del escudo | M13, M17 y M21 (sub-grilla) y M7, M6 (nativos); datos para código en 3.6 | Propuesta, validada con `scripts/render_mapa_puntos.py` |

Decisiones que este documento propone (para que el orquestador las pase a `DECISIONES.md`
si las acepta):

1. Dibujar el **anverso**, en proporción **11:20**, con tres franjas iguales.
2. Paleta base `#D52B1E` / `#FFFFFF` / `#0038A8`, con los ajustes para fondo oscuro de la
   sección 3.4.
3. Escudo de diámetro 0,78 × franja blanca (0,70 en la grilla de 18×33), dibujado con una
   **sub-grilla fina** (máscaras M13, M17 y M21 de la sección 3.3; el bloque JSON de la
   sección 3.6 es la fuente de verdad para el código).
4. Dejar como parámetros la proporción y la paleta del escudo, por si cambia la norma.

## 0. Norma vigente y estado legal

- La bandera se describe por primera vez en la resolución del Congreso General Extraordinario
  del **25 de noviembre de 1842**; el artículo 139 de la Constitución remite a ella `[D]`.
- La versión actual del diseño la fijó el **Decreto N.º 11.400 del 15 de julio de 2013**
  (Presidencia de la República, Ministerio del Interior), que reglamenta el pabellón, los
  escudos y el sello nacional y deroga los decretos N.º 26.506/1957 y N.º 23.136/1926 `[D]`.
  Leí el decreto original escaneado (copia de la Wayback Machine del PDF publicado en
  presidencia.gov.py) y lo contrasté con la traducción inglesa de FOTW `[F2]` y con la
  transcripción parcial de ABC Color `[ABC13]`.
- Qué cambió en 2013 respecto de la versión anterior (la de la época de Stroessner): se quitó
  la orla roja con letras amarillas alrededor de la inscripción, se quitó el disco azul que
  rodeaba a la estrella, la inscripción pasó a negro sobre fondo sin color y las ramas
  quedaron en verde liso `[UH13][F][WEN]`.
- **Atención, norma en disputa:** desde 2024 un grupo de diputados impulsa una ley que
  repondría la orla roja con letras amarillas y el disco azul, y que además cambiaría la
  proporción a 1:2 y fijaría el diámetro del escudo en "la mitad del ancho de la franja"
  `[LN24]`. El primer proyecto tuvo media sanción en Diputados (diciembre de 2024), fue
  rechazado por el Senado y archivado en 2025 `[UH25][ABC26a]`. Un proyecto nuevo se presentó
  el 7 de julio de 2026 `[ABC26a]`; el 18 de agosto de 2026 la sesión quedó sin quórum
  `[ABC26b]` y el 15 de septiembre de 2026 tenía dictamen de comisión y estaba en el orden
  del día de Diputados `[UH26]`.
  **No encontré el resultado de esa sesión.** Con la evidencia reunida, al 2026-10-03 no hay
  ley promulgada y sigue rigiendo el decreto de 2013; conviene volver a comprobarlo antes de
  publicar el tema (ver sección 6).
- **Segunda comprobación, 2026-10-04 (revisión independiente):** tampoco halló ley
  promulgada ni el resultado de la sesión del 15-09-2026. El decreto está además en el
  Digesto Legislativo oficial, <https://digestolegislativo.gov.py/ups/leyes/8871%20.pdf>,
  con el mismo sha256 que la copia de Wayback citada aquí, y su ficha no lista una norma
  posterior que lo modifique. El dictamen de comisión del proyecto (SILpy) confirma lo que
  cambiaría: proporción 1:2, escudo de la mitad de la franja blanca, orla roja con letras
  amarillas y estrella sobre círculo azul. Esa revisión no releyó el articulado del decreto
  ni contrastó proporción y colores con una fuente fuera de las de este documento.
- **Tercera comprobación, 2026-10-04 (SILpy, fuente oficial):** el proyecto nuevo es el
  expediente **D-2694226** `[SIL26a]`. Estado «EN TRÁMITE», etapa «Primer trámite
  constitucional – Discusión Plenario» en Diputados: **no tiene media sanción**. Su
  tramitación termina en dictámenes de comisión del 14-09-2026; no registra ningún
  tratamiento en el plenario. Estuvo en el orden del día de la sesión ordinaria del
  22-09-2026 (punto 24) `[SIL26b]` sin resultado registrado, y no figura en el de la sesión
  ordinaria del 29-09-2026 `[SIL26c]`. No se encontraron noticias posteriores al 15-09-2026.
  Los dictámenes no coinciden: Legislación y Codificación aconseja **rechazarlo**
  (27-07-2026); Defensa Nacional (14-09-2026) lo modifica y mantiene la proporción **1:2**
  `[SIL26d]`; Justicia, Trabajo y Previsión Social (14-09-2026) lo modifica y propone **2:3**
  `[SIL26e]`. Los dos textos modificados mantienen el escudo de la mitad de la franja
  blanca, la orla roja de 1/12 con letras amarillas y la estrella sobre círculo azul.
  Aunque Diputados lo aprobara, falta el Senado, que rechazó el proyecto anterior en 2025.
  Sigue rigiendo el decreto de 2013.

## 1. Proporción, franjas y colores

### 1.1 Proporción y franjas

- **Proporción:** el artículo 5 del decreto pide mantener una relación "lo más aproximada
  posible a 1:0.55 entre el lado mayor y el lado menor del rectángulo" `[D]`. Eso es
  **alto:ancho = 11:20** (0,55). FOTW llega a la misma lectura `[F]` y Wikipedia ES/EN y el
  SVG de Commons (1200×660) usan 11:20 `[WES][WEN][C]`.
- La expresión "lo más aproximada posible" admite desvíos pequeños; las tres grillas
  propuestas en la sección 3 se desvían menos del 1 % con paso cuadrado (dos de las
  descartadas, 15×27 y 30×54, llegan al 1,01 %) y todas pueden hacerse exactas ajustando el
  paso vertical.
- **Franjas:** "tres fajas horizontales, de medidas idénticas" `[D]`, en el orden del texto
  de 1842: **colorada, blanca y azul**, de arriba hacia abajo `[D][WES][WEN]`. Cada franja
  ocupa 1/3 del alto.
- Proporciones anteriores que todavía circulan y **no** hay que usar: 3:5 (FOTW la daba antes
  de 2013 y Vexilla Mundi aún la muestra `[F][VM]`), 2:3, 1:2 y 27:50 (históricas según
  `[WEN]`, dato no contrastado con una segunda fuente).

### 1.2 Colores de las franjas: no hay valor oficial

El decreto no da Pantone, CMYK ni RGB para las franjas. Solo dice que el colorado y el azul
"deben ser de los llamados colores primarios, es decir, sin mezcla con otros colores" `[D]`;
FOTW lo confirma y señala que el decreto no trae ninguna imagen de la bandera `[F][F2]`.
Los valores numéricos del Anexo son únicamente para los elementos de los escudos.

Valores de referencia encontrados:

| Fuente | Rojo | Azul | Carácter |
|--------|------|------|----------|
| Decreto 11.400/2013, art. 5 `[D]` | "color primario" (sin número) | "color primario" (sin número) | Oficial |
| SVG de Wikimedia Commons (código leído), Wikipedia ES y EN `[C][WES][WEN]` | `#D52B1E` (213, 43, 30) | `#0038A8` (0, 56, 168) | Convención digital |
| Imagen de FOTW `py.gif` (píxeles medidos) `[F]` | `#D7271B` | `#0039AA` | Convención digital |
| Album des Pavillons 2023, citado por FOTW `[F]` | Pantone 186 C, RGB 210-16-52 (`#D21034`) | Pantone 286 C, RGB 0-53-153 (`#003599`) | Vexilología (ver sección 6) |
| Manual de banderas Londres 2012, citado por FOTW `[F]` | PMS 032 | PMS 286 | Vexilología |
| Anexo del decreto, "rojo" del escudo (gorro frigio) `[D]` | Pantone 485 C, RGB 237-28-36 (`#ED1C24`) | (no hay azul) | Oficial, pero para el escudo |

**Recomendación para pantalla (color "fiel"):** rojo `#D52B1E`, blanco `#FFFFFF`, azul
`#0038A8`. Justificación: al no existir valor oficial, se elige el par que usan Commons y
las dos Wikipedias, que es la representación digital más difundida y la que el público
reconoce; los demás valores de referencia caen muy cerca (misma familia de rojo bermellón y
azul oscuro). El rojo del Anexo (`#ED1C24`) es una alternativa defendible por ser el único
rojo con respaldo oficial, pero está definido para el gorro frigio del reverso, no para la
franja. Los colores ajustados al fondo oscuro están en la sección 3.4.

### 1.3 Colores oficiales del escudo (Anexo del decreto)

Leídos directamente de la "Grilla de colores" del Anexo `[D]` y cruzados con `[F]` y `[WEN]`:

| Color | Elemento | Pantone | CMYK | RGB | Hex |
|-------|----------|---------|------|-----|-----|
| Rojo | Gorro frigio (reverso) | 485 C | 0-100-100-0 | 237-28-36 | `#ED1C24` |
| Amarillo | Estrella | Yellow C | 0-0-100-0 | 255-241-0 | `#FFF100` |
| Verde | Ramas de palma y olivo | 355 C | 100-0-100-0 | 0-166-81 | `#00A651` |
| Marrón | Pica (reverso) | 478 C | 40-65-100-0 | 136-83-33 | `#885321` |
| Ocre | León (reverso) | 4505 C | 35-30-100-0 | 178-163-54 | `#B2A336` |
| Negro | Inscripciones y círculos | Black C | 0-0-0-100 | 0-0-0 | `#000000` |

- El Anexo lista los seis colores sin rotular a qué elemento va cada uno; la asignación es
  evidente por los dibujos y es la que anota FOTW `[F]`.
- Diferencia menor entre fuentes: en el escaneo el amarillo es RGB 255-241-**0**; FOTW y
  Wikipedia EN transcriben 255-241-**8** (`#FFF108`). Me quedo con lo que se lee en el
  original.
- Commons y Wikipedia ES dibujan el escudo con verde `#009B3A` y amarillo `#FEDF00` /
  `#FDDE00` `[C][WES]`, que no son los del Anexo.
- Tipografía de las inscripciones: familia Arial, estilo Black `[D][F]`.

## 2. El escudo

### 2.1 Anverso (Sello Nacional): composición vigente

Texto del decreto (art. 6 y 7) `[D]`, contrastado con `[F2]`, `[WES2]` y `[UH13]`:

- Forma **circular**, sin más colores que los naturales de sus elementos.
- Inscripción "República del Paraguay" en **letras negras**, repartida en una **orla sin
  color de fondo** cuya anchura es "una doceava parte del círculo del escudo".
- Ramas de **palma y olivo**, en su color natural (verde), **entrelazadas en la base** y
  curvadas siguiendo la orla; el Anexo llama al conjunto "corona de ovación".
- **Estrella de cinco puntas, amarilla, en el centro geométrico, "sin círculo limitante"**
  (es decir, sin el disco azul de la versión anterior).

Lo que añade el dibujo del Anexo (páginas "Escudos - Caras", "Sello Nacional" y "Partes"),
visto por mí en el escaneo:

- De afuera hacia adentro: un **círculo exterior negro grueso**; una banda blanca vacía
  ("superficie o campo"); un círculo negro fino; la orla con la inscripción en mayúsculas
  **REPUBLICA DEL PARAGUAY** (dibujada sin tilde); otro círculo negro fino; el campo blanco
  interior con la corona y la estrella.
- La inscripción ocupa el arco superior, de aproximadamente 260°, y deja libre el cuarto
  inferior.
- La **palma queda a la izquierda del observador y el olivo a la derecha** (se distinguen
  por las hojas largas de la palma y los frutos del olivo); Wikipedia ES lo describe igual
  `[WES2]`. La corona está **abierta arriba** y los tallos **se cruzan abajo**.
- La estrella tiene **una punta hacia arriba** y un contorno negro fino.
- No se ve ninguna cinta atando los tallos. Wikipedia EN todavía describe una corona "atada
  con cintas" citando un libro de 2009, anterior al decreto `[WEN]`; no hay que dibujarla.

Medidas tomadas por mí sobre el dibujo del Anexo (perfil radial de píxeles sobre las páginas
"Sello Nacional" y "Partes"; radio exterior R = 1; precisión aproximada ±0,01 R). **No son
cifras oficiales**: el decreto solo fija la doceava parte de la orla.

| Elemento | Radio (fracción de R) |
|----------|-----------------------|
| Círculo exterior grueso | 0,975 a 1,00 (grosor ≈ 0,025 R) |
| Banda blanca exterior | 0,81 a 0,975 |
| Círculo fino exterior de la orla | ≈ 0,806 |
| Letras de la inscripción | 0,65 a 0,78 (altura ≈ 0,125 R); arco ≈ 260° centrado arriba |
| Círculo fino interior de la orla | ≈ 0,615 |
| Corona de palma y olivo | 0,33 a 0,56; abertura superior ≈ 40°; cruce de tallos abajo |
| Estrella (punta) | ≈ 0,18 (amarillo) a 0,20 (con contorno) |

El SVG de Commons da proporciones equivalentes (círculos finos a 0,82 y 0,61 del borde
exterior; punta de estrella a 0,22) `[C]`.

### 2.2 Tamaño y posición en la bandera

- **Posición:** los escudos van "ubicados en el centro de la franja blanca" `[D]`. En el
  SVG de Commons y en la imagen de FOTW el centro del escudo coincide con el centro
  geométrico de la bandera `[C][F]`.
- **Diámetro: el decreto vigente no lo fija.** Medí dos dibujos de referencia:
  Commons, diámetro exterior ≈ 171 sobre una franja de 220 → **0,78** `[C]`; imagen de FOTW,
  56 a 57 px sobre una franja de 72 px → **0,79** `[F]`. Es probable que el dibujo de FOTW
  derive del de Commons, así que no son dos fuentes independientes.
- **Valor adoptado:** diámetro = **0,78 × alto de la franja blanca** (≈ 0,26 × alto de la
  bandera ≈ 0,143 × ancho). El escudo cabe entero dentro de la franja blanca; nunca toca la
  roja ni la azul.
- **Excepción en la grilla de 18×33:** ahí se usa **0,70**. Con solo 6 filas de puntos por
  franja, un escudo de 0,78 obliga a quitar el punto central de la primera y de la última
  fila blanca y el hueco del escudo queda abierto hacia el rojo y el azul (sección 3.3).
  Como el tamaño no está reglamentado, reducirlo es preferible a romper el borde de la
  franja.

### 2.3 Reverso (Sello de Hacienda) y por qué usamos el anverso

El reverso lleva, en el mismo lugar, otro escudo circular: inscripción "Paz y Justicia" en
letras negras en un arco de 135° arriba; un **león** en su color natural (ocre), sentado, de
perfil, mirando a la derecha del observador, rugiente y con la cola levantada; detrás, sobre
el diámetro vertical, una **pica** (marrón) rematada por el **gorro frigio rojo** `[D][F2]`.
Es la única bandera nacional con anverso y reverso distintos `[F][WES][WEN]`.

Usamos el **anverso** porque: (1) es la cara que se representa normalmente, con el asta a la
izquierda del observador, y la que traen las referencias digitales `[C][WES][WEN][F]`;
(2) una pantalla tiene una sola cara; (3) el Sello Nacional (anillo, corona, estrella) se
puede reducir a puntos y seguir siendo reconocible, mientras que un león de perfil no
sobrevive a 13 o 21 puntos de diámetro.

## 3. Diseño en puntos

Supuesto: puntos circulares sobre fondo oscuro; cada punto es un elemento con color propio
y la ondulación se consigue desplazando y variando el brillo de los puntos.

### 3.1 Geometría común

Con el rectángulo de la bandera de ancho `W` y alto `H = 0,55 · W`, y una grilla de `F` filas
por `C` columnas (`F` múltiplo de 3):

- Centro del punto `(f, c)`, contando desde 0: `x = (c + 0,5) · W / C`, `y = (f + 0,5) · H / F`.
- Franja del punto: roja si `f < F/3`, blanca si `f < 2F/3`, azul en el resto.
- La proporción queda **exactamente 11:20** aunque `F/C` no sea 0,55, porque el paso vertical
  `H/F` y el horizontal `W/C` se calculan por separado (difieren menos del 1 %, imperceptible).
- Diámetro sugerido del punto: 0,66 × paso (deja ver el fondo entre puntos).

### 3.2 Grillas candidatas

| Filas × columnas | Filas por franja | Puntos | Filas/columnas | Desvío frente a 0,55 con paso cuadrado | Paso vertical / horizontal para 11:20 exacto |
|------------------|------------------|--------|----------------|----------------------------------------|----------------------------------------------|
| 15 × 27 | 5 | 405 | 0,5556 | +1,01 % | 0,9900 |
| **18 × 33** | **6** | **594** | 0,5455 | −0,83 % | 1,0083 |
| 21 × 38 | 7 | 798 | 0,5526 | +0,48 % | 0,9952 |
| **24 × 44** | **8** | **1056** | 0,5455 | −0,83 % | 1,0083 |
| **27 × 49** | **9** | **1323** | 0,5510 | +0,19 % | 0,9981 |
| 30 × 54 | 10 | 1620 | 0,5556 | +1,01 % | 0,9900 |
| 30 × 55 | 10 | 1650 | 0,5455 | −0,83 % | 1,0083 |
| 33 × 60 | 11 | 1980 | 0,5500 | 0,00 % (11:20 exacto) | 1,0000 |

Propuestas (en negrita): **P600 = 18×33**, **P1000 = 24×44**, **P1500 = 27×49**.
La menor grilla de paso cuadrado exacto con filas por franja enteras es 33×60 (1980 puntos);
las demás son sus múltiplos (66×120, …). Las ocho grillas de la tabla tienen un número
entero de filas por franja (filas múltiplo de 3); lo comprueba
`scripts/render_mapa_puntos.py --validar`.

### 3.3 El escudo: sub-grilla fina (recomendada) o nativo

Con 6 a 9 filas por franja, el escudo mide entre 4,7 y 7 pasos de diámetro: en la grilla
principal apenas cabe un icono. La opción recomendada es dibujarlo con una **sub-grilla de
puntos más finos**, independiente de la principal y centrada en la franja blanca:

- Diámetro del escudo `D = k · H / 3`, con `k = 0,78` (y `k = 0,70` en la grilla de 18×33;
  ver "Encaje" más abajo). Centro `(W/2, H/2)`.
- Máscara cuadrada de `N × N` celdas (`N` impar, la celda central cae en el centro exacto);
  paso de la sub-grilla `s = D / N`.
- Sub-punto `(i, j)`: `x = W/2 + (i − (N−1)/2) · s`, `y = H/2 + (j − (N−1)/2) · s`.
  Diámetro sugerido: 0,78 × `s`.
- Se **retiran** los puntos de la grilla principal cuyo centro quede a menos de
  `D/2 + 0,30 · (W/C)` del centro de la bandera, para que no se monten sobre el escudo.
- En la animación, los sub-puntos deben moverse con la **misma función de onda** que la
  grilla principal, evaluada en su propia posición.

**Encaje con la grilla principal (comprobado por programa).** La regla de retiro no
garantiza por sí sola un buen encaje: el punto principal tiene 0,33 pasos de radio, más que
el margen de 0,30, y según la paridad de la grilla el hueco puede alcanzar la primera y la
última fila de la franja blanca. `scripts/render_mapa_puntos.py --validar` comprueba para
cada mapa dos condiciones: (a) que no se retire ningún punto de la primera ni de la última
fila blanca, para que el hueco del escudo no quede abierto hacia la franja roja ni hacia la
azul, y (b) que ningún punto principal conservado se solape con un sub-punto (holgura
borde a borde ≥ 0). Las máscaras originales de esta investigación fallaban en dos casos,
ya corregidos:

- **18×33 con M13 a 0,78:** se retiraba el punto central de la primera y de la última fila
  blanca y había un solape de 0,03 pasos con el anillo. Con 6 filas por franja las filas de
  borde quedan a 2,5 pasos del centro y el retiro llega a 2,34 + 0,30 = 2,64 pasos: un
  escudo de 0,78 no cabe sin morder. Corrección: anillo de un punto de grosor (se quitaron
  las 8 celdas de esquina) y escudo a `k = 0,70`.
- **24×44 con M17:** las cuatro celdas de esquina del anillo, en (±6, ±6), se solapaban
  0,06 pasos (≈ 1,4 px con la bandera a 960 px) con los puntos principales vecinos.
  Corrección: se quitaron esas cuatro celdas.

Si se cambia de grilla, de diámetro o de margen hay que volver a pasar el validador: el
encaje depende de la paridad y cambia a saltos.

| Grilla | Máscara | Paso sub-grilla / paso principal | Puntos retirados | Sub-puntos | Total de puntos | Diámetro / franja | Holgura mínima (pasos) | Alternativa nativa |
|--------|---------|----------------------------------|------------------|------------|-----------------|-------------------|------------------------|--------------------|
| P600 (18×33) | M13 | 0,326 | 16 | 129 | **707** | 0,70 | +0,11 | No viable (ver abajo) |
| P1000 (24×44) | M17 | 0,370 | 32 | 221 | **1245** | 0,78 | +0,08 | M6 (total 1056) |
| P1500 (27×49) | M21 | 0,334 | 45 | 349 | **1627** | 0,78 | +0,20 | M7 (total 1323) |

Orientación de tamaños con la bandera a 960 px de ancho (alto 528; escudo ≈ 137 px, o
≈ 123 px en P600): paso principal 29,1 / 21,8 / 19,6 px; sub-paso 9,5 / 8,1 / 6,5 px;
sub-punto 7,4 / 6,3 / 5,1 px. Para que el sub-punto no baje de 4 px, el ancho mínimo de la
bandera es de unos 520 px (M13), 610 px (M17) y 750 px (M21).

Códigos de los mapas (una letra por punto; los colores se justifican en 3.4 y 3.5):

| Código | Significado | Hex fiel | Hex sobre fondo oscuro |
|--------|-------------|----------|------------------------|
| `.` | Sin punto propio. En la sub-grilla: fuera del escudo, no se dibuja nada. En los mapas nativos: se deja el punto blanco de la franja | — | — |
| `n` | "Tinta": lo que en el escudo es negro (círculo exterior e inscripción) | `#000000` | `#4A4F59` |
| `b` | Blanco del campo del escudo | `#FFFFFF` | `#E8E8E8` |
| `v` | Verde de la corona | `#00A651` | `#00A651` |
| `a` | Amarillo de la estrella | `#FFF100` | `#FFD500` |

Los bloques que siguen son la versión legible (una letra por punto, separadas por
espacios). La versión para código, con las mismas filas sin espacios y la leyenda completa,
está en la sección 3.6; el validador comprueba que ambas coincidan.

#### Mapa M21 (21×21, para P1500): 349 puntos (n 83, b 196, v 56, a 14)

<!-- mapa:M21 -->
```text
. . . . . . . n n n n n n n . . . . . . .
. . . . . n n b b b b b b b n n . . . . .
. . . . n b b b b b b b b b b b n . . . .
. . . n b b b b b n n n b b b b b n . . .
. . n b b b n n b b b b b n n b b b n . .
. n b b b n b b v b b b v b b n b b b n .
. n b b n b b v v b b b v v b b n b b n .
n b b b n b v v v b b b v v v b n b b b n
n b b n b v v v b b a b b v v v b n b b n
n b b n b v v b a a a a a b v v b n b b n
n b b n b v v b b a a a b b v v b n b b n
n b b n b v v b b a a a b b v v b n b b n
n b b n b v v v b a b a b v v v b n b b n
n b b b n b v v v b b b v v v b n b b b n
. n b b n b b v v v v v v v b b n b b n .
. n b b b b b b v v v v v b b b b b b n .
. . n b b b b b b v b v b b b b b b n . .
. . . n b b b b b b b b b b b b b n . . .
. . . . n b b b b b b b b b b b n . . . .
. . . . . n n b b b b b b b n n . . . . .
. . . . . . . n n n n n n n . . . . . . .
```

Anillo exterior en radio 10; inscripción en radio 7, dibujada como **tres arcos de tinta**
separados por un hueco de un punto: 12 puntos a la izquierda (REPUBLICA), 3 arriba (DEL) y
12 a la derecha (PARAGUAY), sobre el arco superior de ≈ 250° y con el cuarto inferior
libre; corona de dos puntos de grosor en radios 4 y 5, abierta arriba (3 puntos) y con los
dos tallos cruzados asomando abajo; estrella de 5×5 con una punta arriba.

Sobre la inscripción: la versión original usaba 15 trazos alternos (un punto sí, uno no).
Dibujada, se veía como puntos grises sueltos más que como una orla. Los tres arcos repiten
la estructura real de la leyenda (tres palabras, con DEL arriba al centro) y a tamaño real
se leen como el anillo gris que forma el texto visto de lejos. Si aun así estorba, la
variante sin inscripción se obtiene cambiando por `b` toda `n` que no esté en el borde de
la silueta.

#### Mapa M17 (17×17, para P1000): 221 puntos (n 69, b 103, v 44, a 5)

<!-- mapa:M17 -->
```text
. . . . . . n n n n n . . . . . .
. . . . n n b b b b b n n . . . .
. . . n b b b n n n b b b n . . .
. . n b n n b b b b b n n b n . .
. n b n b b v b b b v b b n b n .
. n b n b v v b b b v v b n b n .
n b n b v v v b b b v v v b n b n
n b n b v v b b a b b v v b n b n
n b n b v v b a a a b v v b n b n
n b n b v v b b a b b v v b n b n
n b n b v v v b b b v v v b n b n
. n b n b v v v v v v v b n b n .
. n b n b b v v v v v b b n b n .
. . n b b b b v b v b b b b n . .
. . . n b b b b b b b b b n . . .
. . . . n n b b b b b n n . . . .
. . . . . . n n n n n . . . . . .
```

Anillo en radio 8, sin las cuatro celdas de esquina (±6, ±6) que se solapaban con la grilla
principal; inscripción en radio 6 en tres arcos (11 + 3 + 11 puntos); corona en radios 3 y
4, con los tallos asomando abajo; la estrella se reduce a una cruz de 5 puntos.

#### Mapa M13 (13×13, para P600): 129 puntos (n 32, b 79, v 13, a 5)

<!-- mapa:M13 -->
```text
. . . . n n n n n . . . .
. . . n b b b b b n . . .
. . n b b b b b b b n . .
. n b b b b b b b b b n .
n b b b v b b b v b b b n
n b b v b b a b b v b b n
n b b v b a a a b v b b n
n b b v b b a b b v b b n
n b b b v b b b v b b b n
. n b b b v v v b b b n .
. . n b b b b b b b n . .
. . . n b b b b b n . . .
. . . . n n n n n . . . .
```

Anillo de un punto de grosor en radio 6 (octógono redondeado; la versión original tenía
dos puntos de grosor en las diagonales); **sin inscripción** (probé una variante con trazos
y ensucia la lectura; además no hay sitio: quedaría pegada al anillo o a la corona); corona
de un punto de grosor en radio 3, abierta arriba; estrella en cruz de 5 puntos. En 18×33 se
dibuja con `k = 0,70` (ver "Encaje").

#### Escudos nativos (sobre la propia grilla principal, sin sub-grilla)

Más baratos (no añaden puntos) pero mucho más toscos. Solo son viables cuando la paridad de
filas por franja y de columnas coincide, para que el escudo quede centrado.

M7, para 27×49 (9 filas por franja, columnas impares). Ocupa las filas 10 a 16 y las
columnas 21 a 27 (contando desde 0); diámetro 7/9 = 0,78 de la franja:

<!-- mapa:M7 -->
```text
. . n n n . .
. n b b b n .
n b v b v b n
n b v a v b n
n b v v v b n
. n b b b n .
. . n n n . .
```

M6, para 24×44 (8 filas por franja, columnas pares). Ocupa las filas 9 a 14 y las columnas
19 a 24; diámetro 6/8 = 0,75 de la franja:

<!-- mapa:M6 -->
```text
. n n n n .
n b b b b n
n v a a v n
n v a a v n
n b v v b n
. n n n n .
```

La versión original de M6 llenaba de verde todo el interior salvo dos puntos y, dibujada,
se leía como un cuadro verde con centro amarillo; esta deja ver el campo blanco (6 puntos)
y la corona queda como una U de 6 puntos que abraza la estrella.

En los mapas nativos `.` significa "se deja el punto blanco de la franja". Para **18×33 no
hay escudo nativo aceptable**: 33 columnas (impar) y 6 filas por franja (par) obligan a un
escudo de 5×4 puntos, que se ve ovalado; ahí la sub-grilla es obligatoria.

#### Qué se conserva y qué se simplifica

| Elemento oficial | M21 | M17 | M13 | M7 / M6 |
|------------------|-----|-----|-----|---------|
| Círculo exterior grueso | Anillo de tinta | Anillo de tinta | Anillo de tinta | Anillo de tinta |
| Dos círculos finos de la orla | Omitidos | Omitidos | Omitidos | Omitidos |
| Inscripción | 3 arcos de tinta (12 + 3 + 12) | 3 arcos de tinta (11 + 3 + 11) | Omitida | Omitida |
| Corona verde abierta arriba | 2 puntos de grosor, cruce de tallos | 2 puntos de grosor, cruce de tallos | 1 punto de grosor | U de 7 puntos / U de 6 puntos |
| Diferencia entre palma y olivo | No | No | No | No |
| Estrella amarilla central | 5×5 con forma de estrella | Cruz de 5 puntos | Cruz de 5 puntos | 1 punto / 2×2 |
| Contorno negro de la estrella | No | No | No | No |

Lo que identifica al escudo a cualquier tamaño es, en este orden: **anillo oscuro, corona
verde abierta arriba y centro amarillo sobre blanco**. Todo lo demás es prescindible.

### 3.4 Colores por tipo de punto

| Código | Punto | Hex fiel | Hex recomendado sobre fondo oscuro | Contraste del recomendado contra negro |
|--------|-------|----------|-------------------------------------|----------------------------------------|
| `R` | Franja roja | `#D52B1E` | `#D52B1E` | 4,19 : 1 |
| `B` | Franja blanca | `#FFFFFF` | `#E8E8E8` (crestas de la onda hasta `#FFFFFF`) | 17,14 : 1 |
| `A` | Franja azul | `#0038A8` | `#1450D2` (azul realzado) | 3,11 : 1 (el fiel da 2,13 : 1) |
| `n` | Tinta del escudo | `#000000` | `#4A4F59` | 2,55 : 1 (y 6,71 : 1 contra el blanco) |
| `b` | Blanco del escudo | `#FFFFFF` | `#E8E8E8` | 17,14 : 1 |
| `v` | Verde de la corona | `#00A651` | `#00A651` | 6,57 : 1 |
| `a` | Amarillo de la estrella | `#FFF100` | `#FFD500` | 14,77 : 1 |
| fondo | Fondo | — | `#000000` o un casi negro neutro | — |

Contrastes calculados con la fórmula de luminancia relativa de WCAG 2.x.

### 3.5 Cómo resolver el blanco (y el negro) sobre fondo oscuro

1. **El blanco deslumbra.** Un punto `#FFFFFF` tiene 21:1 contra negro; el rojo, 4,2:1 y el
   azul fiel, 2,1:1. La franja blanca se comería a las otras dos. Usar `#E8E8E8` como blanco
   base: sigue leyéndose como blanco (no hay nada más claro en pantalla) y deja margen para
   que las crestas de la onda suban a `#FFFFFF`. Si aun así domina, reducir un 6 a 8 % el
   diámetro de los puntos blancos.
2. **El azul fiel se apaga.** `#0038A8` queda por debajo de 3:1 y, si la onda lo oscurece,
   desaparece. Opciones: usar el azul realzado `#1450D2` (mismo tono, más luminoso), o
   mantener `#0038A8` y que la onda solo aclare, nunca oscurezca. No aclarar más allá de
   `#1450D2`: empezaría a parecer el celeste de Luxemburgo.
3. **El negro del escudo no puede ser negro.** Sobre fondo oscuro un punto negro es un
   hueco. Se dibuja como punto "apagado" `#4A4F59`: se ve como punto y, al lado de los
   blancos, se lee como negro. Sirve además de frontera entre la grilla principal y la
   sub-grilla.
4. **Amarillo junto a blanco.** El amarillo oficial `#FFF100` tiene casi la misma
   luminancia que el blanco base `#E8E8E8` (1,04:1; contra `#FFFFFF`, 1,18:1) y se
   confunde; `#FFD500` separa mejor por tono, aunque su contraste de luminancia con el
   blanco base sigue siendo bajo (1,16:1): la estrella se distingue por color, no por
   brillo. **No** añadir un disco azul detrás de la estrella para ganar contraste: es justo
   lo que el decreto de 2013 eliminó.
5. **Verde:** el oficial `#00A651` funciona tal cual sobre negro y junto al blanco.

### 3.6 Mapas en formato para código (fuente de verdad)

El bloque JSON que sigue reúne todo lo que el código necesita: la leyenda carácter → color
(fiel y recomendado sobre fondo oscuro), la geometría común y las filas de cada mapa como
cadenas sin espacios. Es lo que lee `scripts/render_mapa_puntos.py`; con
`--exportar-json RUTA` lo vuelca a un archivo. No lo edites a mano sin pasar después
`--validar`, que comprueba que coincide con los mapas legibles de la sección 3.3.

Campos:

- `leyenda`: por cada carácter, `nombre`, color `fiel` y color `oscuro` (el recomendado
  sobre fondo oscuro). `R`, `B` y `A` son los puntos de las franjas; `n`, `b`, `v` y `a`,
  los del escudo; `.` no tiene color (ver la tabla de códigos de 3.3).
- `geometria`: proporción alto:ancho, diámetro del escudo sobre el alto de la franja
  blanca, diámetro del punto sobre el paso, diámetro del sub-punto sobre el sub-paso y
  margen de retiro en pasos de la grilla principal.
- `mapas.<nombre>.tipo`: `subgrilla` (escudo en sub-grilla fina centrada en la bandera) o
  `nativo` (se recolorean puntos de la grilla principal).
- `mapas.<nombre>.grilla`: filas y columnas de la grilla principal para la que se diseñó.
- `mapas.<nombre>.lado`: lado `N` de la máscara; `celdas`: `N` cadenas de `N` caracteres,
  de arriba hacia abajo y de izquierda a derecha.
- `mapas.<nombre>.diametro_escudo_sobre_franja` (opcional): sustituye al valor común.
- `mapas.<nombre>.fila0` y `columna0` (solo nativos): fila y columna de la grilla
  principal, contando desde 0, donde cae la esquina superior izquierda de la máscara.

<!-- mapas-json:inicio -->
```json
{
  "formato": "paraguay_theme/mapas-puntos",
  "version": 1,
  "fondo": "#000000",
  "leyenda": {
    ".": {"nombre": "sin punto propio (sub-grilla: no se dibuja; nativo: se deja el punto de la franja)", "fiel": null, "oscuro": null},
    "n": {"nombre": "tinta del escudo: círculo exterior e inscripción", "fiel": "#000000", "oscuro": "#4A4F59"},
    "b": {"nombre": "blanco del campo del escudo", "fiel": "#FFFFFF", "oscuro": "#E8E8E8"},
    "v": {"nombre": "verde de la corona", "fiel": "#00A651", "oscuro": "#00A651"},
    "a": {"nombre": "amarillo de la estrella", "fiel": "#FFF100", "oscuro": "#FFD500"},
    "R": {"nombre": "franja roja", "fiel": "#D52B1E", "oscuro": "#D52B1E"},
    "B": {"nombre": "franja blanca", "fiel": "#FFFFFF", "oscuro": "#E8E8E8"},
    "A": {"nombre": "franja azul", "fiel": "#0038A8", "oscuro": "#1450D2"}
  },
  "geometria": {
    "proporcion_alto": 11,
    "proporcion_ancho": 20,
    "diametro_escudo_sobre_franja": 0.78,
    "punto_sobre_paso": 0.66,
    "subpunto_sobre_subpaso": 0.78,
    "margen_retiro_en_pasos": 0.3
  },
  "mapas": {
    "M21": {
      "tipo": "subgrilla", "grilla": {"filas": 27, "columnas": 49}, "lado": 21,
      "celdas": [
        ".......nnnnnnn.......",
        ".....nnbbbbbbbnn.....",
        "....nbbbbbbbbbbbn....",
        "...nbbbbbnnnbbbbbn...",
        "..nbbbnnbbbbbnnbbbn..",
        ".nbbbnbbvbbbvbbnbbbn.",
        ".nbbnbbvvbbbvvbbnbbn.",
        "nbbbnbvvvbbbvvvbnbbbn",
        "nbbnbvvvbbabbvvvbnbbn",
        "nbbnbvvbaaaaabvvbnbbn",
        "nbbnbvvbbaaabbvvbnbbn",
        "nbbnbvvbbaaabbvvbnbbn",
        "nbbnbvvvbababvvvbnbbn",
        "nbbbnbvvvbbbvvvbnbbbn",
        ".nbbnbbvvvvvvvbbnbbn.",
        ".nbbbbbbvvvvvbbbbbbn.",
        "..nbbbbbbvbvbbbbbbn..",
        "...nbbbbbbbbbbbbbn...",
        "....nbbbbbbbbbbbn....",
        ".....nnbbbbbbbnn.....",
        ".......nnnnnnn......."
      ]
    },
    "M17": {
      "tipo": "subgrilla", "grilla": {"filas": 24, "columnas": 44}, "lado": 17,
      "celdas": [
        "......nnnnn......",
        "....nnbbbbbnn....",
        "...nbbbnnnbbbn...",
        "..nbnnbbbbbnnbn..",
        ".nbnbbvbbbvbbnbn.",
        ".nbnbvvbbbvvbnbn.",
        "nbnbvvvbbbvvvbnbn",
        "nbnbvvbbabbvvbnbn",
        "nbnbvvbaaabvvbnbn",
        "nbnbvvbbabbvvbnbn",
        "nbnbvvvbbbvvvbnbn",
        ".nbnbvvvvvvvbnbn.",
        ".nbnbbvvvvvbbnbn.",
        "..nbbbbvbvbbbbn..",
        "...nbbbbbbbbbn...",
        "....nnbbbbbnn....",
        "......nnnnn......"
      ]
    },
    "M13": {
      "tipo": "subgrilla", "grilla": {"filas": 18, "columnas": 33}, "lado": 13, "diametro_escudo_sobre_franja": 0.7,
      "celdas": [
        "....nnnnn....",
        "...nbbbbbn...",
        "..nbbbbbbbn..",
        ".nbbbbbbbbbn.",
        "nbbbvbbbvbbbn",
        "nbbvbbabbvbbn",
        "nbbvbaaabvbbn",
        "nbbvbbabbvbbn",
        "nbbbvbbbvbbbn",
        ".nbbbvvvbbbn.",
        "..nbbbbbbbn..",
        "...nbbbbbn...",
        "....nnnnn...."
      ]
    },
    "M7": {
      "tipo": "nativo", "grilla": {"filas": 27, "columnas": 49}, "lado": 7, "fila0": 10, "columna0": 21,
      "celdas": [
        "..nnn..",
        ".nbbbn.",
        "nbvbvbn",
        "nbvavbn",
        "nbvvvbn",
        ".nbbbn.",
        "..nnn.."
      ]
    },
    "M6": {
      "tipo": "nativo", "grilla": {"filas": 24, "columnas": 44}, "lado": 6, "fila0": 9, "columna0": 19,
      "celdas": [
        ".nnnn.",
        "nbbbbn",
        "nvaavn",
        "nvaavn",
        "nbvvbn",
        ".nnnn."
      ]
    }
  }
}
```
<!-- mapas-json:fin -->

## 4. Notas de fidelidad: errores comunes

1. **Orden de franjas.** Roja arriba, blanca al centro, azul abajo. Invertida (azul arriba)
   deja de ser la bandera paraguaya.
2. **Confusión con Países Bajos.** Mismos tres colores y mismo orden, pero la neerlandesa
   es 2:3 y **no lleva escudo** `[WEN][WNL]`. Sin escudo, o con el escudo ilegible, nuestra
   animación se lee como bandera neerlandesa: el escudo no es opcional.
3. **Confusión con Croacia.** También roja, blanca y azul con escudo al centro, pero su
   escudo es ajedrezado rojo y blanco con corona, invade las franjas roja y azul, y la
   bandera es 1:2 `[WHR]`. El escudo paraguayo es un círculo blanco que cabe dentro de la
   franja blanca.
4. **Confusión con Luxemburgo.** Azul celeste y sin escudo `[WLU]`. No aclarar demasiado
   el azul.
5. **Franjas verticales.** Las franjas son horizontales; estos tres colores en vertical
   remiten a Francia.
6. **Proporción.** Usar 11:20; no 2:3, 3:5 ni 1:2.
7. **Escudo de la versión anterior.** Orla roja con letras amarillas y disco azul tras la
   estrella corresponden al diseño previo a 2013 (hoy objeto de disputa política); el
   vigente es blanco, con letras negras, corona verde y estrella amarilla.
8. **Escudo equivocado de cara.** El anverso lleva la estrella; el león con el gorro frigio
   es el reverso.
9. **Escudo mal puesto.** Va centrado en la franja blanca y en el centro horizontal (no
   corrido hacia el asta) y no debe tocar las franjas roja ni azul.
10. **Detalles del escudo.** Estrella de cinco puntas con una punta arriba; corona abierta
    arriba y cruzada abajo; palma a la izquierda y olivo a la derecha (irrelevante en
    puntos); sin cinta.
11. **Franjas desiguales.** Las tres miden lo mismo; hay versiones estilizadas con la blanca
    más angosta que no son reglamentarias `[F]`.

## 5. Fuentes

Primaria:

- `[D]` Decreto N.º 11.400 del 15 de julio de 2013, con su Anexo "Símbolos Nacionales -
  Aplicación de Colores". PDF escaneado de 15 páginas publicado en presidencia.gov.py;
  copia de la Wayback Machine del 18-09-2013:
  <http://web.archive.org/web/20130918171505/http://www.presidencia.gov.py/uploads/pdf/presidencia-8101464d737707beb2027355e3a1f055bf86ffb6af9c5006247d795132c361fc.pdf>
  (6 348 911 bytes, sha256 `27b76faba92c594791122d37d58e2f666b49107a24218a30875ae420782ad0d8`).
  Leído en memoria; no se guardó copia en el repositorio. El enlace original ya no responde.

Vexilología:

- `[F]` Flags of the World, "Paraguay": <https://www.crwflags.com/fotw/flags/py.html>
  (imagen medida: <https://www.crwflags.com/fotw/images/p/py.gif>).
- `[F2]` Flags of the World, "Paraguay - Flag Laws" (traducción del decreto por Ivan Sache):
  <https://www.crwflags.com/fotw/flags/py_law.html>
- `[VM]` Vexilla Mundi, "Paraguay": <https://www.vexilla-mundi.com/paraguay_flag.html>

Wikipedia y Commons:

- `[C]` Wikimedia Commons, `Flag of Paraguay.svg` (versión del 09-09-2019, 1200×660):
  <https://commons.wikimedia.org/wiki/File:Flag_of_Paraguay.svg>
- `[WES]` Wikipedia ES, "Bandera de Paraguay": <https://es.wikipedia.org/wiki/Bandera_de_Paraguay>
- `[WES2]` Wikipedia ES, "Escudos del Paraguay": <https://es.wikipedia.org/wiki/Escudo_de_Paraguay>
- `[WEN]` Wikipedia EN, "Flag of Paraguay": <https://en.wikipedia.org/wiki/Flag_of_Paraguay>
- `[WNL]` `[WHR]` `[WLU]` Wikipedia EN, "Flag of the Netherlands", "Flag of Croatia" y
  "Flag of Luxembourg" (solo para proporción y descripción):
  <https://en.wikipedia.org/wiki/Flag_of_the_Netherlands>,
  <https://en.wikipedia.org/wiki/Flag_of_Croatia>,
  <https://en.wikipedia.org/wiki/Flag_of_Luxembourg>

Prensa (cambios de 2013 y estado legal):

- `[UH13]` Última Hora, 16-07-2013, sobre las modificaciones de los escudos:
  <https://www.ultimahora.com/escudos-la-bandera-tendran-modificaciones-n704605>
- `[ABC13]` ABC Color, suplemento escolar, 26-08-2013, artículos del decreto:
  <https://www.abc.com.py/edicion-impresa/suplementos/escolar/decreto-sobre-simbolos-nacionales-2-611141.html>
- `[LN24]` La Nación, 19-12-2024, texto del proyecto de ley:
  <https://www.lanacion.com.py/politica/2024/12/19/proyecto-de-ley-plantea-el-diseno-y-uso-de-simbolos-patrios-despues-de-182-anos/>
- `[UH25]` Última Hora, 19-08-2025, ratificación en Diputados tras el rechazo del Senado:
  <https://www.ultimahora.com/diputados-se-ratifican-en-volver-a-tener-la-bandera-son-simbolos-stronistas>
- `[ABC26a]` ABC Color, 11-08-2026, archivo del primer proyecto y nuevo proyecto de julio de 2026:
  <https://www.abc.com.py/politica/2026/08/11/dia-de-la-bandera-el-rojo-el-blanco-y-el-azul-que-yamil-esgaib-pretende-vincular-con-el-stronismo/>
- `[ABC26b]` ABC Color, 18-08-2026, sesión sin quórum:
  <https://www.abc.com.py/politica/2026/08/18/simbolos-stronistas-cartistas-intentaron-aprobar-proyecto-pero-opositores-dejaron-sin-quorum-la-sesion/>
- `[UH26]` Última Hora, 15-09-2026, dictamen de comisión:
  <https://www.ultimahora.com/dictaminan-el-proyecto-de-esgaib-de-simbolos-patrios>

Congreso Nacional, SILpy (consultado el 2026-10-04):

- `[SIL26a]` Expediente D-2694226, estado y tramitación:
  <https://silpy.congreso.gov.py/web/expediente/156451>
- `[SIL26b]` Sesión ordinaria 136 de Diputados, 22-09-2026, y su orden del día:
  <https://silpy.congreso.gov.py/web/sesion/112542>,
  <https://silpy.congreso.gov.py/web/descarga/sesion-138746?preview>
- `[SIL26c]` Sesión ordinaria 137 de Diputados, 29-09-2026, y su orden del día:
  <https://silpy.congreso.gov.py/web/sesion/112562>,
  <https://silpy.congreso.gov.py/web/descarga/sesion-138895?preview>
- `[SIL26d]` Proyecto modificado por la Comisión de Defensa Nacional (1:2):
  <https://silpy.congreso.gov.py/web/descarga/dictamencomision-467024?preview=>
- `[SIL26e]` Proyecto modificado por la Comisión de Justicia, Trabajo y Previsión Social (2:3):
  <https://silpy.congreso.gov.py/web/descarga/dictamencomision-467070?preview=>

## 6. Lo incierto y lo no verificado

1. **Vigencia.** Al 2026-10-04 el proyecto D-2694226 sigue en Diputados sin media sanción
   (sección 0). Si llegara a promulgarse cambiarían la proporción (1:2 o 2:3, según qué
   dictamen prevalezca), el escudo (orla roja, letras amarillas, disco azul) y su diámetro
   (la mitad de la franja blanca). Conviene volver a mirar el expediente en SILpy antes de
   publicar.
2. **Colores de las franjas.** No existe valor oficial; `#D52B1E` y `#0038A8` son una
   convención. Las tres referencias que los respaldan (Commons, Wikipedia ES, Wikipedia EN)
   no son independientes entre sí.
3. **Diámetro del escudo.** No está reglamentado; 0,78 sale de medir dos dibujos que
   probablemente comparten origen.
4. **Medidas internas del escudo.** Son mediciones mías sobre un escaneo, no cifras
   oficiales. La orla dibujada mide ≈ 0,19 R (≈ 1/10,5 del diámetro), algo más que la
   doceava parte del texto; no sé si "doceava parte del círculo" se refiere al diámetro.
5. **Album des Pavillons 2023.** En la tabla de FOTW los encabezados de rojo y azul parecen
   intercambiados; asigné los valores por el propio color (0-53-153 es azul). No vi el álbum.
6. **Publicación en la Gaceta Oficial.** Wikipedia ES enlaza una Gaceta Oficial del
   21-10-2013; no la abrí.
7. **Páginas del decreto.** Vi como imagen las páginas 1, 4, 5, 7, 9, 10, 11 y 13; de las
   demás solo leí la capa de texto del OCR, que es defectuosa.
8. **Reconocibilidad de los mapas.** La juzgué yo sobre vistas previas generadas por
   programa (sin abrir ventanas); no hay prueba con personas ni en un arranque real, y no se
   probó con la bandera ondeando.
9. **Rendimiento.** No sé cuántos puntos animados soporta Plymouth con fluidez; los totales
   de la sección 3.3 son presupuesto de diseño, no un dato medido.

## 7. Material de apoyo y validación

En `output/temporales/bandera-investigacion/` (ignorado por git, no forma parte del tema):

- `generar_mapas_escudo.py`: genera las máscaras, la tabla de grillas, los contrastes y,
  con `--png`, las vistas previas `previa_*.png`.
- Validación de este documento:
  `python output/temporales/bandera-investigacion/generar_mapas_escudo.py --validar docs/investigacion/bandera-paraguay.md`
  compara los cinco mapas de la sección 3.3 con los del generador y comprueba su simetría
  izquierda-derecha. Resultado al cerrar esta investigación: `PASS`.
