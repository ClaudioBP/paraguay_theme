# Referencia del plugin `script` de Plymouth (basada en el código fuente)

Referencia de trabajo para escribir el tema "bandera paraguaya de puntos". Todo lo que
sigue sale del **código fuente de Plymouth 24.004.60** (la versión de Ubuntu 24.04), no de
blogs. Las afirmaciones llevan su evidencia:

- **[F]** leído en el fuente (se cita `archivo:línea`).
- **[A]** además ejecutado en un arnés que compila el intérprete real (ver §0.2).
- **[P]** comprobado en un paquete real descargado (`dpkg -c`, `strings`, scripts de mantenedor).
- Lo que no se pudo respaldar o ejecutar está reunido en §9.

## 0. Fuente y método

### 0.1 Fuente usada

| Qué | Detalle |
|---|---|
| Upstream | `git clone --depth 1 --branch 24.004.60 https://gitlab.freedesktop.org/plymouth/plymouth.git` → commit `d6e6366d622962dce02d8c7e4ab814f54a202509` (2024-01-04). El tag exacto existe. |
| Parches Ubuntu | `plymouth_24.004.60-1ubuntu7.2.debian.tar.xz` de archive.ubuntu.com (sha256 `604e6a37…25c9`, según el `.dsc`). El único parche que toca el plugin script es `debian/patches/misc-changes.patch`. |
| Paquetes reales | `.deb` de Ubuntu noble 24.004.60-1ubuntu7.2 (`apt-get download`) y de Debian trixie 24.004.60-5 (deb.debian.org). Fedora, Arch y openSUSE: solo spec/PKGBUILD de su VCS. |
| Ubicación | WSL: `~/.cache/paraguay-theme-rig/src/{plymouth,ubuntu-src,debs,otras-distros,arnes}`. |

Abreviaturas de rutas: `S/` = `src/plugins/splash/script/`, `core/` = `src/libply-splash-core/`,
`gfx/` = `src/libply-splash-graphics/`, `ply/` = `src/libply/`.

**Diferencias Ubuntu ↔ upstream que afectan a un tema script** [F: `misc-changes.patch`] [P: `strings script.so`]:
- Ubuntu añade `Window.GetBitsPerPixel([window])`. No existe en upstream ni en Debian
  (`strings` del `script.so` de Debian: 0 apariciones). Solo el renderer frame-buffer lo
  implementa; con DRM devuelve 0.
- Ubuntu cambia la heurística de escala HiDPI (parches 0016/0017): escala 2 solo si
  DPI físico / (135 portátil, 110 monitor ≥ 20") ≥ 1,75.
- Ubuntu no instala `plymouthd.defaults`, `plymouthd.conf` ni `plymouth-set-default-theme`
  (`debian/rules`); el tema se elige con alternativas (§7).
- Las unidades systemd de Ubuntu exigen `splash` en la línea del kernel
  (`ubuntu-add-splash-option.patch`).

### 0.2 Arnés de verificación [A]

Sin `sudo` no se puede instalar Plymouth, así que se compiló con `gcc` un arnés que enlaza el
código **real** de `S/script*.c`, `ply/` (listas, hash, regiones, bucle de eventos),
`core/ply-pixel-buffer.c` y `core/ply-pixel-display.c`. Sustitutos declarados: el renderer
(el *flush* copia las áreas a un framebuffer en memoria), `ply-image` (no hay `libpng-dev`;
las imágenes se generan por nombre) y `ply-label` (ausente, como si faltara el plugin de
texto). Fuentes y salidas: `output/evidencias/ref-fuente/`. Los tiempos se midieron en un
i7-8550U bajo WSL2 con otros procesos corriendo: son **órdenes de magnitud**, no cifras de
arranque real.

## 1. Archivo `.plymouth` para `ModuleName=script`

```ini
[Plymouth Theme]
Name=Paraguay
Description=Bandera de puntos
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/paraguay
ScriptFile=/usr/share/plymouth/themes/paraguay/paraguay.script

[script-env-vars]
clave=valor
```

| Clave | Quién la lee | Notas |
|---|---|---|
| `[Plymouth Theme] ModuleName` | `core/ply-boot-splash.c:225-228` | Se carga `<dir plugins>/<ModuleName>.so`. Es la **única** clave de este grupo que lee el demonio; `Name` y `Description` son informativas. |
| `[script] ImageDir` | `S/plugin.c:171-173` | **Obligatoria**: si falta, `script_lib_image_setup` hace `strdup(NULL)` (`S/script-lib-image.c:269`) y plymouthd cae. `Image("x.png")` abre `ImageDir + "/" + "x.png"` (`:69`); se admiten subcarpetas. |
| `[script] ScriptFile` | `S/plugin.c:174-176`, `:304` | Se abre tal cual con `open()`; plymouthd hace `chdir("/")` (`src/main.c:2441`), así que debe ser **ruta absoluta**. |
| `[script-env-vars] k=v` | `S/plugin.c:146-163`, `:259-267` | Cada par se vuelve una variable **global de tipo cadena** antes de ejecutar el script. No hay otra forma de pasar parámetros. |

No hay más claves para este plugin. `Font=`, `TitleFont=` y `MonospaceFont=` solo las leen
los generadores de initrd de dracut/Arch para copiar fuentes
(`scripts/plymouth-populate-initrd.in:553-578`).

Sintaxis del archivo (`ply/ply-key-file.c:185-225`, `:258`): grupos `[nombre]`; pares leídos
con `fscanf(" %m[^= \t\n] = %m[^\n] ")`; la clave no admite espacios; el valor es el resto de
la línea; comentario = línea que empieza con `#`. Un `\r` final queda **dentro del valor**
(`script\r` → no se encuentra el plugin): el archivo debe tener finales LF.

Selección del tema por el demonio (`src/main.c:274-301`, `:303-352`, `:378-404`, `:450-498`),
en orden: `plymouth.splash=<nombre>` en la línea del kernel → `Theme=` (y `ThemeDir=`) de
`/etc/plymouth/plymouthd.conf` → `plymouthd.defaults` (`/run/plymouth/` o
`/usr/share/plymouth/`) → enlace `/usr/share/plymouth/themes/default.plymouth` → tema de texto
→ tema incorporado. Un nombre se resuelve como `<dir>/<nombre>/<nombre>.plymouth` buscando en
`/run/plymouth/themes/`, `ThemeDir` y `/usr/share/plymouth/themes/`. Otras claves de
`[Daemon]`: `ShowDelay`, `DeviceTimeout`, `DeviceScale`.

## 2. Lenguaje: gramática y semántica

### 2.1 Léxico (`S/script-scan.c`)

| Elemento | Regla | Línea |
|---|---|---|
| Espacio en blanco | Solo espacio, `\n` y tab. **`\r` no**: un archivo CRLF no se analiza [A]. Un BOM UTF-8 tampoco [A]. | 161-175 |
| Identificadores | `[A-Za-z_][A-Za-z0-9_]*`, solo ASCII | 53-64 |
| Números | `dígitos` o `dígitos.dígitos`. No hay `1e3`, `.5`, `0x10` ni sufijos [A]. `5.` vale 5. | 200-226 |
| Cadenas | Solo comillas dobles, en una sola línea. Escapes: `\n`, `\e`, `\0` (corta la cadena), `\"`; cualquier otro `\x` es `x` (`"\t"` es la letra t [A], `"\\"` es `\`). Bytes UTF-8 pasan tal cual. | 231-281 |
| Comentarios | `# …`, `// …` y `/* … */` **anidables** | 282-340 |
| Lectura | Un `read()` de 1 byte por carácter | 143-145 |

### 2.2 Tipos (`S/script.h:93-123`)

| Tipo | Notas |
|---|---|
| null | Literal `NULL`. Toda variable o clave no definida vale null. |
| número | Siempre `double` (`script.h:85`). Literales `INFINITY` y `NAN` (`S/script-parse.c:316-319`). |
| cadena | Bytes; inmutable. |
| hash | Único contenedor. `[a, b, c]` crea un hash con claves `"0"`, `"1"`, `"2"` (`S/script-execute.c:135-156`). No hay longitud ni forma de enumerar claves. |
| función | `fun (a, b) { … }`, de script o nativa. Sin clausuras. |
| nativo | Imagen o sprite. |
| extend | `a | b`: objeto compuesto que busca primero en `a` y luego en `b` (`S/script-object.c:210-252`). Es el mecanismo de herencia. |

No existen `true`, `false`, `null` ni `undefined`: son identificadores sin definir (valen null,
es decir, **falso**) [A]. Usar `1`, `0` y `NULL`.

**Verdad** (`S/script-object.c:276-304`): falsos son null, `0`, `NAN` y `""`. Todo lo demás es
verdadero, incluidos `"0"` y `[]` [A].

**Conversión a cadena** (`:306-321`): número → `printf("%g")` (6 cifras significativas:
`1000000` → `"1e+06"`, `1234567` → `"1.23457e+06"`, `0.1 + 0.2` → `"0.3"`) [A]; null → `"#NULL"`;
otros → `"#(0x…)"`.
**Conversión a número** (`:269-274`): solo si ya es número; cualquier otra cosa da `NAN`.
**No hay forma nativa de convertir cadena a número**: `"3" * 2` es null y `"3" + 4` es `"34"` [A].

### 2.3 Operadores (`S/script-parse.c:471-573`, `S/script-object.c:518-615`)

Precedencia de menor a mayor; los binarios asocian a la izquierda:

| Nivel | Operadores |
|---|---|
| asignación (a la derecha) | `=` `+=` `-=` `*=` `/=` `%=` `|=` |
| 0 | `|` (extend) |
| 1 | `||` |
| 2 | `&&` |
| 3 | `==` `!=` |
| 4 | `<` `<=` `>` `>=` |
| 5 | `+` `-` |
| 6 | `*` `/` `%` |
| unarios | prefijos `!` `-` `+` `++` `--`; sufijos `++` `--` |
| primarios | llamada `f(…)`, índice `a[k]`, miembro `a.k`, `( … )` |

No hay ternario, operadores de bits, `switch`, `**`, `var`, `function` ni `for…in` [A]. Los
operadores de dos caracteres no admiten espacio en medio (`> =` es error) [A] (`:209-213`).

| Operación | Resultado |
|---|---|
| `+` | número + número → suma. Si **alguno** es cadena → concatenación (`"a" + 1` → `"a1"`, `"a" + NULL` → `"a#NULL"`). Otro caso → null. |
| `-` `*` `/` `%` | Solo número con número; si no, **null** (no `NAN`). |
| `/` | División real: `7 / 2` = 3.5; `1 / 0` = inf; `0 / 0` = nan [A]. |
| `%` | `fmodl` (`:578`): acepta no enteros y el signo es el del dividendo. `7.5 % 2` = 1.5; `-7 % 3` = -1; `-7.5 % 2` = -1.5; `7 % -3` = 1; `5 % 0` = nan [A]. Para índices cíclicos: `((i % P) + P) % P`. |
| Comparación | null con null → igual. Número con número: numérica (`NAN == NAN` es 0). Cadena con cadena: `strcmp` (`"10" < "9"` es 1). Tipos mezclados → siempre "distinto" (`"1" == 1` es 0, `NULL == 0` es 0). Hashes, funciones y nativos: por identidad (`[] == []` es 0) [A]. El resultado es 1 o 0. |
| `&&` `||` | Cortocircuito; devuelven **el operando**, no 0/1 (`1 && 2` → 2, `NULL || 5` → 5) [A]. |
| `!x` | 1 o 0. |
| `-x` | Solo números; si no, error en el log y null (`S/script-execute.c:213-219`). |
| `++` `--` | Solo números; sobre null escriben error y **dejan null** (`:244-248`) [A]. |
| `x += y` | Evalúa `x + y` y asigna. Con `x` sin definir: null + 1 = null, **queda null** [A]. |

Asignación (`S/script-object.c:399-407`): la variable pasa a referenciar el objeto. Los números
y cadenas se comportan como valores (cada operación crea un objeto nuevo); los hashes, imágenes
y sprites se comparten (`b = a; b[0] = 9;` cambia `a[0]`) [A].

### 2.4 Variables y alcance

- No se declaran. Al **leer** un nombre se busca en `local` → `this` → `global`; si no existe
  se crea como null en `local` (`S/script-execute.c:120-133`).
- En el nivel superior del script `local` **es** `global` (`S/script.c:117-128`).
- Cada llamada crea un `local` nuevo con los parámetros, `_args` (hash con los argumentos por
  posición y `_args.count`) y `this` (`S/script-execute.c:574-632`).
- Asignar dentro de una función a un nombre que **ya existe como global modifica el global**; si
  no existe, crea un local [A]. Para forzar: `local.x = …` o `global.x = …` (`local`, `global` y
  `this` son palabras reservadas, `S/script-parse.c:320-325`).
- Un parámetro que el llamador **omite** no se crea: su nombre se resuelve con la regla
  general y puede tomar el valor de un global homónimo [A].
- Una variable de bucle (`for (i = 0; …)`) dentro de una función pisa al global `i` si
  existe [A].
- Índices: `a[k]` y `a.k` convierten la clave a cadena (`"%g"`). `a[1]`, `a[1.0]` y `a["1"]`
  son lo mismo; `a[1.5]` es otra clave; `a[7.9]` no es `a[7]` (usar `Math.Int`) [A].
  **Claves numéricas ≥ 1 000 000 colisionan** (`big[1000000]` y `big[1000001]` son la misma) [A].
- Indexar algo que no es hash lo **convierte en hash**, incluso al solo leer: con `q = 9`,
  evaluar `q.algo` deja `q` convertido en hash (`S/script-execute.c:106-110`) [A].
- No hay clausuras: una función anónima no ve los locales de quien la creó [A].
- Memoria por conteo de referencias (`S/script-object.c:51-63`): un objeto se libera al quedar
  sin referencias. Para sprites esto es visible (§3.2).

### 2.5 Sentencias (`S/script-parse.c:600-892`)

```
expresión ;                       # el ; es obligatorio
{ … }
if (c) s  [else s]                # "else if" funciona encadenando
while (c) s
do s while (c);
for (ini; cond; paso) s           # las tres partes son obligatorias
return [expr];   break;   continue;   fail;
fun nombre (a, b) { … }           # SIN ; al final
nombre = fun (a, b) { … };        # CON ; (es una asignación)
```

- **No existe la sentencia vacía**: un `;` suelto (después del `}` de `fun`, `if`, `for`, o un
  `;;`) hace fallar el análisis de **todo** el archivo [A].
- Una función sin `return` devuelve el valor de su última expresión ejecutada [A]
  (`S/script-execute.c:548-571`, `:629-630`). `return;` devuelve null.
- Llamar a algo que no es función no da error: devuelve null [A] (`:259-291`).
- Error de sintaxis: `script_parse_file` devuelve NULL (`S/script-parse.c:1051-1073`), no se
  ejecuta **nada** y queda el fondo negro; el mensaje (`Parser error "archivo" L:n C:n`) solo
  va al log de plymouthd. Una `{` sin cerrar no aborta: se traga el resto del archivo [A].
- Errores de ejecución: solo un mensaje `Execution error` en el log; la ejecución sigue.

### 2.6 Objetos y herencia

`obj.metodo(args)` busca `metodo` en `obj` y llama con `this = obj`
(`S/script-execute.c:300-316`). Si `obj` es una cadena y no tiene esa clave, se busca en el
global `String` (`:307-311`). `f = obj.metodo; f()` pierde el `this` [A].

Patrón de clase que usa la propia librería (`S/script-lib-sprite.script:8-13`):

```
Clase = fun (v) { o = [] | Clase; o.v = v; return o; } | [];
Clase.Doble = fun () { return this.v * 2; };
x = Clase(3);  x.Doble();   # 6
```

**Diferencia con JavaScript**: `obj.x = v` escribe donde encuentre la clave. Si `x` ya existe
en el "prototipo", **se modifica el prototipo** y lo ven todas las instancias; solo las claves
nuevas se crean en el hash propio de la instancia (`S/script-object.c:435-454`) [A].

## 3. API

Los parámetros que faltan valen null → `NAN` al leerlos como número. Los nombres de parámetros
son los reales del fuente. En las columnas "Fuente", `c:`, `h:` y `script:` son el `.c`, el
`.h` y el `.script` embebido de la librería nombrada en el título.

### 3.1 `Image` (`S/script-lib-image.c`, `S/script-lib-image.script`)

| Firma | Comportamiento | Fuente |
|---|---|---|
| `Image(filename)` | Carga `ImageDir/filename`. Devuelve **NULL sin error** si falla. `"special://logo"` carga el logo de la distro (en Ubuntu `/usr/share/plymouth/ubuntu-logo.png` [P]). | c:49-83 |
| `Image.Text(text, red, green, blue, alpha, font, align)` | Imagen con el texto. Colores 0..1 (omitidos → 0). `alpha` opcional (1). `font` opcional (cadena). `align`: `"left"`, `"center"` o `"right"`. Ver §5. | c:183-261 |
| `img.GetWidth()` / `img.GetHeight()` | Tamaño en píxeles lógicos. | c:85-113 |
| `img.Scale(width, height)` | **Nueva** imagen, interpolación bilineal. Trunca a entero (`Scale(2.9, 3.9)` → 2 de ancho [A]). | c:153-166; `core/ply-pixel-buffer.c:965-996` |
| `img.Rotate(angle)` | Nueva imagen del **mismo tamaño**, girada `angle` radianes alrededor del centro; lo que sale se recorta. | c:115-132; `:998-1042` |
| `img.Crop(x, y, width, height)` | Nueva imagen `width`×`height` con ese recorte; puede ser mayor que el original (relleno transparente). Existe desde 0.9.5. **Oscurece los bordes suavizados**: mezcla sobre un lienzo transparente y vuelve a multiplicar el color por el alfa (medido en el Plymouth real; ver `docs/arquitectura/tema.md`). | c:134-151 |
| `img.Tile(width, height)` | Nueva imagen `width`×`height` repitiendo el original. | c:168-181 |

Formatos (`gfx/ply-image.c:279-309`): **PNG** (cualquier tipo de color; se convierte a ARGB
premultiplicado) y **BMP de 24 bits sin compresión**. Nada más.
Compatibilidad antigua: `ImageNew`, `ImageScale(image, w, h)`, `ImageRotate(image, angle)`,
`ImageGetWidth(image)`, `ImageGetHeight(image)`.
No existe: leer o escribir píxeles, dibujar primitivas, componer imágenes, voltear, teñir.

### 3.2 `Sprite` (`S/script-lib-sprite.c`, `S/script-lib-sprite.script`)

| Firma | Comportamiento | Fuente |
|---|---|---|
| `Sprite()` / `Sprite(image)` | Crea un sprite en (0,0), z = 0, opacidad 1. | c:47-73; script:8-13 |
| `s.SetImage(image)` | Cambia la imagen y marca el sprite para redibujar. Con algo que no sea imagen (p. ej. NULL) **no hace nada** [A]. | c:88-110 |
| `s.GetImage()` | La imagen o NULL. | c:75-86 |
| `s.SetX(value)`, `s.SetY(value)`, `s.SetZ(value)` | Se guardan como **`int`** (trunca hacia cero: 10.7 → 10, -10.7 → -10) [A]. `NAN` → -2147483648 [A]. | c:156-187; h:50-66 |
| `s.SetPosition(x, y, z)` | Llama a los tres; **`z` no es opcional** (`SetPosition(3, 4)` deja z = -2147483648) [A]. | script:1-6 |
| `s.SetOpacity(value)` | `double` **sin acotar**. | c:189-198 |
| `s.GetX()`, `GetY()`, `GetZ()`, `GetOpacity()` | Valores guardados. | c:112-154 |

- La posición es la esquina superior izquierda de la imagen.
- Orden de dibujo: z ascendente; a igual z, orden de creación (orden estable, c:769).
- Opacidad: menor que 0.011 no se dibuja (c:463). Al dibujar se convierte con
  `(uint8_t)(opacidad * 255)` (`core/ply-pixel-buffer.c:739`): **valores fuera de [0, 1] se
  desbordan** (1.01 → 1, casi transparente; 2.0 → 254; -0.5 → 129, medido con gcc en x86-64).
  Acotar siempre con `Math.Clamp`.
- **Un sprite vive mientras exista una referencia al objeto.** Si la variable se pisa o era
  local de una función que ya retornó, el sprite desaparece en el siguiente refresco
  (c:40-45, c:791-802) [A]. No hay `Delete()`: para ocultar, `SetOpacity(0)`.
- Se le pueden colgar datos propios (`s.dato = 42`) [A].
- No existe: tamaño, escala, rotación ni color por sprite (se hace sobre la imagen).

Compatibilidad: `SpriteNew()`, `SpriteSetImage(sprite, image)`, `SpriteSetX/Y/Z(sprite, value)`,
`SpriteSetPosition(sprite, x, y, z)`, `SpriteSetOpacity(sprite, value)`.

### 3.3 `Window` (`S/script-lib-sprite.c:200-396`, registro en `:629-685`)

| Firma | Comportamiento |
|---|---|
| `Window.GetWidth([window])`, `Window.GetHeight([window])` | Con índice: tamaño de esa pantalla (0 = primera); índice inexistente → NULL. **Sin argumento: el máximo** entre todas las pantallas desde 22.02; **en 0.9.5, el mínimo** (el cambio es el commit b2bf5d5c, posterior a esa etiqueta). Para no depender de la versión, recorrer los índices. Píxeles lógicos. |
| `Window.GetX([window])`, `Window.GetY([window])` | Con índice: desplazamiento de esa pantalla dentro del lienzo común. Sin argumento: el máximo de los desplazamientos (0 con una sola pantalla). |
| `Window.SetX(window, value)`, `Window.SetY(window, value)` | Cambia el desplazamiento de una pantalla; provoca redibujo completo. |
| `Window.SetBackgroundTopColor(red, green, blue)` | Componentes 0..1 (acotados, `:369-376`). Provoca redibujo completo **siempre**, aunque el color no cambie. |
| `Window.SetBackgroundBottomColor(red, green, blue)` | Igual. Si arriba ≠ abajo se dibuja un degradado vertical con ruido anti-bandas (`:398-412`). |
| `Window.GetBitsPerPixel([window])` | **Solo Ubuntu.** En upstream/Debian la llamada devuelve NULL [A]. |

El fondo inicial es negro (`:688-689`), sin importar el color de fondo con que se compiló la distro.
Compatibilidad: `SpriteWindowGetWidth()`, `SpriteWindowGetHeight()`,
`SpriteWindowSetBackgroundTopColor(r, g, b)`, `SpriteWindowSetBackgroundBottomColor(r, g, b)`.

### 3.4 `Plymouth` (`S/script-lib-plymouth.c:143-248`; callbacks en `:280-513`)

| Registro | El callback recibe | Cuándo |
|---|---|---|
| `Plymouth.SetRefreshFunction(function)` | `()` | Cada cuadro (§4.1). |
| `Plymouth.SetBootProgressFunction(function)` | `(duration, progress)`: segundos desde que arrancó plymouthd y fracción 0..1 | ~30 veces por segundo, en cualquier modo (§6.2). |
| `Plymouth.SetRootMountedFunction(function)` | `()` | Al pasar del initramfs a la raíz real. |
| `Plymouth.SetKeyboardInputFunction(function)` | `(keyboard_input)`: cadena con la tecla | Cada tecla, salvo Esc, Enter, Retroceso y Ctrl-U/W/V, que consume el núcleo (`core/ply-keyboard.c:185-254`). |
| `Plymouth.SetUpdateStatusFunction(function)` | `(new_status)`: cadena | `plymouth update --status=…`. |
| `Plymouth.SetDisplayNormalFunction(function)` | `()` | Al mostrarse y cada vez que no queda ninguna pregunta pendiente (`src/main.c:1541-1575`). |
| `Plymouth.SetDisplayPasswordFunction(function)` | `(prompt, bullets)`: cadena y número de caracteres tecleados | Petición de contraseña y cada tecla. |
| `Plymouth.SetDisplayQuestionFunction(function)` | `(prompt, entry_text)` | Pregunta con eco y cada tecla. |
| `Plymouth.SetDisplayPromptFunction(function)` | `(prompt, entry_text, is_secret)` | Se llama **además** de las dos anteriores. |
| `Plymouth.SetValidateInputFunction(function)` | `(entry_text, add_text)`; devolver falso descarta la tecla | Antes de aceptar cada tecla, Enter (`"\n"`) y Esc (`"\e"`). |
| `Plymouth.SetDisplayMessageFunction(function)` | `(message)` | `plymouth display-message --text=…`. Alias: `Plymouth.SetMessageFunction`. |
| `Plymouth.SetHideMessageFunction(function)` | `(message)` | `plymouth hide-message --text=…`. |
| `Plymouth.SetDisplayHotplugFunction(function)` | `()` | Se añade o quita una pantalla (`S/plugin.c:390-412`). |
| `Plymouth.SetSystemUpdateFunction(function)` | `(progress)`: entero 0..100 | `plymouth system-update --progress=N`. |
| `Plymouth.SetQuitFunction(function)` | `()` | Una vez, justo antes de destruir el script (§6.5). |

| Otra función | Resultado |
|---|---|
| `Plymouth.GetMode()` | `"boot"`, `"shutdown"`, `"reboot"`, `"updates"`, `"system-upgrade"`, `"firmware-upgrade"`, `"system-reset"` o `"unknown"` (`:61-95`). |
| `Plymouth.SetRefreshRate(value)` | Cuadros por segundo del callback de refresco; se guarda como `int` (`:51-59`). Por defecto 50. |
| `Plymouth.GetCapslockState()` | 1 o 0. |

Compatibilidad: `PlymouthSetRefreshFunction`, `PlymouthSetBootProgressFunction`,
`PlymouthSetRootMountedFunction`, `PlymouthSetKeyboardInputFunction`,
`PlymouthSetUpdateStatusFunction`, `PlymouthSetDisplayNormalFunction`,
`PlymouthSetDisplayPasswordFunction`, `PlymouthSetDisplayQuestionFunction`,
`PlymouthSetValidateInputFunction`, `PlymouthSetMessageFunction`, `PlymouthSetQuitFunction`,
`PlymouthGetMode` (`S/script-lib-plymouth.script`).

### 3.5 `Math` (`S/script-lib-math.c:75-116`, `S/script-lib-math.script`)

`Math.Cos(value)`, `Math.Sin(value)`, `Math.Tan(value)` (radianes), `Math.ATan2(value_a, value_b)`,
`Math.Sqrt(value)`, `Math.Int(value)` (es **`floor`**: `Math.Int(-1.5)` = -2 [A]),
`Math.Random()` (0 ≤ r < 1), `Math.Abs(value)`, `Math.Min(value_a, value_b)`,
`Math.Max(value_a, value_b)`, `Math.Clamp(value, min, max)`, `Math.Pi`.
Alias sin punto: `MathAbs`, `MathMin`, `MathMax`, `MathClamp`, `MathPi`, `MathCos`, `MathSin`,
`MathTan`, `MathATan2`, `MathSqrt`, `MathInt`.
No existe: `Floor`, `Ceil`, `Round`, `Pow`, `Exp`, `Log`, `ASin`, `ACos` (llamarlas devuelve NULL [A]).
`Abs`, `Min`, `Max` y `Clamp` están escritas en script: cuestan una llamada interpretada.

### 3.6 `String` (`S/script-lib-string.c:38-124`)

Sobre cualquier cadena: `s.CharAt(index)` (un byte; `""` si se pasa del final),
`s.SubString(start, end)` (desde `start` hasta `end` sin incluirlo), `s.Length()` (bytes:
`"ñandú".Length()` = 7 [A]). `String(valor)` envuelve un valor para llamarle estos métodos.
Sobre un número no funcionan (`n.Length()` → NULL [A]). No hay búsqueda, reemplazo, mayúsculas
ni conversión a número.

## 4. Modelo de ejecución y rendimiento

### 4.1 Cuándo corre el script

1. `show_splash_screen` falla si no hay pantallas gráficas (`S/plugin.c:422-425`): el tema
   script nunca corre en consolas de solo texto; plymouthd cae al tema de texto.
2. Se analiza el archivo, se crean las variables de `[script-env-vars]`, se registran las
   librerías y se ejecuta el script completo **una vez** (`S/plugin.c:247-292`).
3. Un temporizador llama a `on_timeout` (`S/plugin.c:217-234`): primero **reprograma** el
   siguiente disparo a `1.0 / refresh_rate` segundos desde ese instante, luego llama a la
   función de refresco y después a `script_lib_sprite_refresh`.
4. Todo es un solo hilo con un bucle de eventos; los demás callbacks corren entre cuadros.

**Frecuencia**: 50 Hz por defecto (`FRAMES_PER_SECOND`, `S/plugin.c:67-69`), configurable con
`Plymouth.SetRefreshRate(n)`. El temporizador se arma al **inicio** del cuadro, así que el
período es 20 ms mientras el trabajo dure menos; si dura más, el siguiente cuadro arranca
enseguida y **no se saltan cuadros**: una animación que avanza un paso fijo por cuadro se
enlentece. `SetRefreshRate(0)` la detiene para siempre (espera infinita);
`SetRefreshRate()` sin número o con valores > 1000 dejan plymouthd en bucle ocupado
(`ply/ply-event-loop.c:908-930`, `:1220-1232`).

**Volcado a pantalla**: el núcleo mantiene las pantallas "en pausa" y las vuelca con otro
temporizador a **60 Hz** (`core/ply-boot-splash.c:50-52`, `:501-514`, `:552-569`). Con 50 cuadros
de script sobre 60 volcados hay un batido leve; 30 o 60 lo evitan. No hay sincronía vertical.

**Reloj**: no hay ninguna función de tiempo. La única fuente de tiempo real es el primer
argumento de `SetBootProgressFunction` (`CLOCK_MONOTONIC` desde el inicio de plymouthd,
`ply/ply-progress.c:274-280`), actualizado ~30 veces por segundo y **congelado** mientras el
progreso está en pausa (p. ej. durante una petición de contraseña).

### 4.2 Refresco de sprites: algoritmo de áreas dañadas

`script_lib_sprite_refresh` (`S/script-lib-sprite.c:757-853`). N = sprites totales,
M = sprites que cambiaron en el cuadro:

1. Ordena la lista por z con **inserción** sobre lista enlazada (`ply/ply-list.c:334-354`):
   O(N) si ya está ordenada, O(N²) si cambian muchos z.
2. Si `full_refresh` está activo, añade a la región el rectángulo de cada pantalla.
3. Quita los sprites sin referencias y añade su rectángulo viejo.
4. Recorre los N sprites. Uno "cambió" si varió x, y o z, si la opacidad varió **más de 0.01**
   o si se llamó a `SetImage` (`:811-815`). Por cada uno añade **dos** rectángulos (posición
   nueva y vieja) a una región. Cada alta recorre los rectángulos ya presentes y los recorta
   para que no se solapen (`ply/ply-region.c:91-438`): el costo crece como **M²**. Un
   rectángulo contenido en otro ya presente se descarta de inmediato (`:355-357`).
5. Por cada rectángulo resultante y cada pantalla llama a `script_lib_sprite_draw_area`
   (`:414-480`): pinta el fondo en ese recorte, **recorre los N sprites** y mezcla los que lo
   intersecan. Cada mezcla anota además el área en la región de "actualizado" del lienzo (otra
   pasada de recortes).
6. En el siguiente volcado se copian esas áreas al framebuffer
   (`src/plugins/renderers/drm/plugin.c`, `flush_head`).

`full_refresh` (redibujo de toda la pantalla) lo activan: el inicio, añadir o quitar una
pantalla (`:528`), `Window.SetX/SetY` con un valor distinto (`:341`, `:363`) y **toda** llamada
a `Window.SetBackgroundTopColor/BottomColor` (`:384`, `:394`).

Mezcla de píxeles (`core/ply-pixel-buffer.c:699-775`, `:843-897`): bucle por píxel; alfa 0 se
salta, alfa 255 con opacidad 1 se copia, el resto se mezcla. Hay un camino rápido con `memcpy`
solo si la imagen está marcada opaca, la opacidad es exactamente 1 y la escala coincide
(`:858-883`). **Un PNG nunca queda marcado opaco**; solo un BMP de 24 bits cargado tal cual
(`gfx/ply-image.c:272`). `Scale`, `Rotate`, `Crop` y `Tile` devuelven imágenes no opacas.

### 4.3 Costos por operación

- **Image.Scale / Rotate / Crop / Tile / Text**: crean un buffer nuevo en cada llamada; **no
  hay caché**. Costo proporcional a los píxeles de salida. La imagen anterior se libera al
  perder su última referencia. Hacerlas una vez al inicio, no por cuadro.
- **SetOpacity / SetX / SetY / SetZ**: solo guardan un número. El costo aparece en el refresco
  si el valor cambió.
- **Intérprete**: recorre el árbol sintáctico; no hay bytecode. Cada literal, cada resultado
  aritmético y cada comparación crea un objeto con `malloc` (`script_obj_t`, 24 bytes;
  `S/script-object.c:157-165`). Cada índice `a[k]` formatea la clave con `asprintf("%g")` y
  busca en una tabla hash (`S/script-execute.c:98-118`). Cada llamada crea un estado, un hash de
  locales, el hash `_args` y una entrada por argumento (`:574-632`).

Medido en el arnés [A] (`malloc`/`calloc` contados con `ld --wrap`, no incluye los internos de `asprintf`):

| Operación | `malloc` | Tiempo aprox. |
|---|---|---|
| Iteración de bucle vacía (`k < n; k++`) | 2 | 0.2 µs |
| `y = by[k] + amp * Math.Sin(t + ph[k]);` | 34 | 3 – 4 µs |
| `sp[k].SetY(by[k] + amp * Math.Sin(t + ph[k]));` | 67 | 6 – 12 µs |
| `fila[r].SetY(dy + r * pitch);` | 37 | 3 – 6 µs |
| Sentencia de inicio `tabla[i] = 0.123;` | — | ~5 µs |
| Análisis del archivo | — | ~1.7 µs por byte (8 KB → 14 ms; 459 KB → 0.8 s) |

### 4.4 Mediciones del refresco [A]

Puntos de 8×8 con alfa, paso 16 px, 1920×1080, escala 1. Milisegundos por cuadro
(script + refresco + volcado). El presupuesto a 50 Hz es 20 ms.

| Caso | ms/cuadro |
|---|---|
| 150 puntos, todos se mueven | ~1.6 |
| 600 puntos, todos se mueven | 8 – 20 |
| 1350 puntos, todos se mueven | ~55 |
| 2160 puntos, todos se mueven | 90 – 220 |
| 3840 puntos, todos se mueven | 230 – 520 |
| 2160 o 3840 puntos en pantalla, solo ~150 se mueven | 1.5 – 2 |
| 2160 puntos en pantalla, se mueven 540 / 1080 | ~21 / ~84 |
| 2160 puntos quietos, sin función de refresco | 0.08 |
| 2160 puntos quietos, invertir el z de todos cada cuadro | ~280 |
| 600 puntos, solo cambia la opacidad de todos | ~14 |
| 60 tiras de 8×576 moviéndose en Y | ~2.2 |
| 1 sprite de 960×576 con `SetImage` por cuadro (PNG / BMP opaco) | ~3.7 / ~0.7 |
| Redibujo completo 1080p por cuadro + 600 puntos quietos | 4 – 8 |
| `Rotate` de 256×256 por cuadro / `Scale` de 64×64 por cuadro | ~3.6 / ~0.4 |

"Todos se mueven" significa que el script mueve todos; como las coordenadas son enteras, en
cada cuadro cambia de píxel entre el 40 % y el 85 % según la velocidad de la onda. El rango
refleja corridas distintas.

Lecturas:

- El costo lo manda **M (sprites que cambian)** y crece de forma cuadrática; **N casi no
  importa** si los sprites están quietos.
- El tamaño del punto (4 a 32 px) casi no influye con 600 puntos: domina la gestión de
  rectángulos, no los píxeles.
- **Truco verificado**: si el primer rectángulo de la región contiene a todos los demás, las
  altas siguientes se descartan en O(1) y se dibuja una sola área. Basta un sprite "cobertor"
  con z menor que todos, del tamaño de la caja de la bandera, con `SetOpacity(0)` (nunca se
  dibuja) y `SetImage(misma_imagen)` en cada cuadro. Con 2160 puntos moviéndose, el refresco
  baja de ~190-270 ms a ~2.5-5.5 ms; el total queda en lo que cueste el script (~9-20 ms). La
  imagen cobertor se obtiene sin archivo extra con `punto.Crop(0, 0, ancho, alto)`.
  Llamar a `Window.SetBackgroundTopColor` cada cuadro logra lo mismo redibujando toda la
  pantalla (más caro: ~7 ms a 1080p, ~20 ms a 4K).
- Con el cobertor el límite pasa a ser el intérprete: calcular el desplazamiento una vez por
  columna y aplicarlo a sus puntos (2160 puntos: 6 – 12 ms de script) cuesta la mitad que un
  `Math.Sin` por punto (17 – 21 ms).

### 4.5 Varias pantallas y HiDPI

- Hay **una sola lista de sprites** y un único sistema de coordenadas. Cada pantalla tiene un
  desplazamiento `(x, y) = ((max_ancho − ancho) / 2, (max_alto − alto) / 2)`
  (`S/script-lib-sprite.c:504-529`) y dibuja cada sprite en `sprite.x − pantalla.x`
  (`:465-466`). Es decir: todas las pantallas muestran, **centrada**, la misma escena de tamaño
  `Window.GetWidth() × Window.GetHeight()` (los máximos); las pantallas menores la ven recortada.
- Para centrar algo en todas: `x = Window.GetWidth() / 2 − ancho / 2`. Para que quepa en todas,
  dimensionar con el mínimo de `Window.GetWidth(i)` recorriendo `i` hasta que devuelva NULL.
- Con varias pantallas cada rectángulo dañado se dibuja una vez por pantalla.
- HiDPI: si la pantalla tiene escala 2, `Window.GetWidth()` devuelve píxeles **lógicos** (la
  mitad; `core/ply-pixel-display.c:75-80`) y cada imagen se **amplía ×2 con interpolación
  bilineal en cada dibujo** (`core/ply-pixel-buffer.c:754-763`): se ve suavizada y cuesta más
  (2160 puntos con cobertor: ~60 ms de refresco en el arnés [A]). El script no puede consultar
  la escala. Se fuerza con `plymouth.force-scale=N` en el kernel, `DeviceScale=` en
  `plymouthd.conf` o la variable `PLYMOUTH_FORCE_SCALE` (`ply/ply-utils.c:1015-1059`).
- Pantallas rotadas: el buffer aplica la rotación por píxel (`core/ply-pixel-buffer.c:157-201`)
  y desactiva el camino rápido.

## 5. Texto (`Image.Text`)

- Usa `ply_label` (`S/script-lib-image.c:242-254`), que carga en este orden
  `label-pango.so` y, si no está, `label-freetype.so` del directorio de plugins
  (`gfx/ply-label.c:104-118`).
- **Si no hay ninguno, no hay error**: devuelve una imagen de 0×0 (`gfx/ply-label.c:385-403`)
  [A] y no se ve nada.
- `font` con label-pango es una descripción Pango (`"Sans 12"` por defecto,
  `src/plugins/controls/label-pango/plugin.c:278-281`) resuelta con fontconfig: necesita
  fuentes y configuración de fontconfig **dentro del initramfs**.
- Con label-freetype solo se respetan el tamaño (`"… 14"` en puntos o `"… 14px"`) y si el
  nombre contiene `Mono`; la fuente es la que diga `fc-match` o, en el initramfs,
  `/usr/share/fonts/Plymouth.ttf` y `Plymouth-monospace.ttf`
  (`src/plugins/controls/label-freetype/plugin.c:43-45`, `:124-156`, `:757-833`).
- El primer argumento se convierte a cadena: `Image.Text(NULL, …)` dibuja `#NULL`.
- Cada llamada crea una etiqueta, mide, dibuja y la destruye: cara. No llamarla por cuadro.
- Qué llega al initramfs depende de la distro (§7). En Ubuntu el hook copia `label-pango.so`,
  fontconfig y la fuente Ubuntu solo si `plymouth-label` está instalado [P].
- Un tema sin texto no depende de nada de esto.

## 6. Ciclo de vida

### 6.1 Modos

`plymouthd --mode=` acepta `boot`, `shutdown`, `reboot`, `updates`, `system-upgrade`,
`firmware-upgrade`, `system-reset` (`src/main.c:2409-2426`); `plymouth change-mode --<modo>`
lo cambia en caliente. **No existe modo de suspensión ni de reanudación** (no hay ninguna
mención en el fuente). Un cambio de modo, alternar a detalles con Esc y volver, o
`plymouth reload`, **destruyen y vuelven a ejecutar el script desde cero**
(`core/ply-boot-splash.c:528-539`, `src/main.c:1577-1595`, `:936-972`).

El splash gráfico solo se muestra si la línea del kernel tiene `splash` o `rhgb` (y no
`single`, `splash=verbose`, etc.; `src/main.c:887-934`). Unidades systemd (`systemd-units/`):
`plymouth-start` (arranque), `plymouth-poweroff`, `-halt`, `-kexec` (lanzan
`plymouthd --mode=shutdown`), `plymouth-reboot` (`--mode=reboot`), `plymouth-quit`,
`plymouth-quit-wait`, `plymouth-read-write`, `plymouth-switch-root`. Todas con
`ConditionVirtualization=!container`.

### 6.2 Progreso de arranque

`ply_boot_splash_update_progress` llama al plugin cada 1/30 s
(`core/ply-boot-splash.c:46-48`, `:435-457`) con `(tiempo, porcentaje)`. El porcentaje es una
estimación (`ply/ply-progress.c:237-262`) basada en la caché del arranque anterior
(`/var/lib/plymouth/boot-duration`, o `shutdown-duration`); sin caché avanza como si el
arranque durara 60 s (`:48-50`). Al salir se fuerza una última llamada con 1.0
(`core/ply-boot-splash.c:787-793`). El valor no decrece, pero es solo una estimación: puede
llegar a 1.0 antes de que termine el arranque (si tarda más que la vez anterior) o quedarse
lejos de 1.0 hasta esa última llamada.

### 6.3 Contraseña (LUKS) y preguntas

`plymouth ask-for-password --prompt=…` (lo invoca el agente de systemd) →
`on_ask_for_password` → `update_display` (`src/main.c:513-552`, `:1541-1575`), que llama a
`DisplayPassword(prompt, bullets)` **y** a `DisplayPrompt(prompt, texto, 1)`. Cada tecla repite
la llamada con el nuevo número de viñetas; Enter responde y se llama a `DisplayNormal`.
**El tema debe dibujar el diálogo**: si no registra estos callbacks no aparece nada y el
usuario teclea a ciegas. El progreso se pausa mientras se pregunta (salvo
`--dont-pause-progress`).

### 6.4 Mensajes y estado

`plymouth display-message --text=T` → `DisplayMessage(T)`; `hide-message --text=T` →
`HideMessage(T)`. Los mensajes enviados antes de mostrarse el splash se reenvían al mostrarlo
(`src/main.c:253-272`). `plymouth update --status=S` → `UpdateStatus(S)`. En Ubuntu llegan
además estados `fsck:…` (`misc-changes.patch`).

### 6.5 Salida y paso al gestor de sesión

`plymouth quit [--retain-splash]` → `on_quit` → `ply_boot_splash_become_idle`
(`src/main.c:1414-1464`). El plugin script responde "listo" **de inmediato**
(`S/plugin.c:480-485`): **no hay forma de pedir tiempo para una animación de salida**. A los
10 ms se llama al callback de `SetQuitFunction`, se hace **un** refresco de sprites y se
destruye todo (`S/plugin.c:312-338`). Según el fuente, **ese último dibujo no llega a la
pantalla**: sin `--retain-splash` los renderers se desactivan antes de ocultar el splash
(`src/main.c:1216-1235`; el volcado DRM retorna si no está activo), y con `--retain-splash`
las pantallas se retiran del plugin antes de destruirlo (`core/ply-boot-splash.c:415-425`).
El callback de salida sirve para liberar estado, no para dibujar. Con `--retain-splash` no se
limpia la pantalla y queda el último cuadro ya volcado hasta que el gestor de sesión pinte
encima. `plymouth deactivate` (previo a que el gestor de sesión tome la pantalla) desactiva
los renderers pero no destruye el script.

## 7. Empaquetado e instalación por distro

| Distro | `script.so` | Plugin de texto | Selector de tema | Evidencia |
|---|---|---|---|---|
| Ubuntu 24.04 | `plymouth` | `plymouth-label` (`label-pango.so`); `plymouth-label-ft` (`label-freetype.so`, universe) | alternativas `default.plymouth` | [P] `dpkg -c` |
| Debian 13 | `plymouth` | `plymouth-label` (ambos `.so`) | `plymouth-set-default-theme` (en `plymouth`) | [P] `dpkg -c` |
| Fedora (rawhide, 26.134.222) | `plymouth-plugin-script` | `plymouth-plugin-label` (ambos) | `plymouth-set-default-theme` (en `plymouth-scripts`) | spec |
| Arch (26.134.222-3) | `plymouth` (paquete único) | incluido en `plymouth` | `plymouth-set-default-theme` | PKGBUILD |
| openSUSE Factory | `plymouth-plugin-script` | `plymouth-plugin-label` (pango), `plymouth-plugin-label-ft` | `plymouth-set-default-theme` (en `plymouth-scripts`) | spec |

Directorio de temas en todas: `/usr/share/plymouth/themes/<nombre>/<nombre>.plymouth`.
Plugins: `/usr/lib/x86_64-linux-gnu/plymouth/` en Debian/Ubuntu [P], `/usr/lib/plymouth/` en
Arch, `%{_libdir}/plymouth/` en Fedora/openSUSE. Renderer X11 para pruebas: `plymouth-x11`
(Debian/Ubuntu), `plymouth-devel` (Fedora), `plymouth-x11-renderer` (openSUSE), `gtk3` (Arch).
El tema de ejemplo `script` viene en `plymouth-themes` (Debian/Ubuntu) o `plymouth-theme-script`.

### 7.1 Activar el tema

**Ubuntu** (no trae `plymouth-set-default-theme`) [P: postinst de `plymouth-themes` y hook]:

```sh
sudo update-alternatives --install /usr/share/plymouth/themes/default.plymouth \
     default.plymouth /usr/share/plymouth/themes/paraguay/paraguay.plymouth 200
sudo update-alternatives --set default.plymouth \
     /usr/share/plymouth/themes/paraguay/paraguay.plymouth
sudo update-initramfs -u
```

**Debian**: `sudo plymouth-set-default-theme -R paraguay` (`-R` ejecuta
`/usr/libexec/plymouth/plymouth-update-initrd`, que en Debian es `update-initramfs -u -k all` [P]).
**Fedora / openSUSE**: `sudo plymouth-set-default-theme -R paraguay` (upstream: `dracut -f`,
`scripts/plymouth-update-initrd`).
**Arch**: hook `plymouth` en `HOOKS` de `/etc/mkinitcpio.conf` y
`sudo plymouth-set-default-theme -R paraguay` (el PKGBUILD lo cambia a `mkinitcpio -P`).

`plymouth-set-default-theme` escribe `Theme=<nombre>` en `/etc/plymouth/plymouthd.conf` y exige
que existan el `.plymouth` y `<ModuleName>.so` (`scripts/plymouth-set-default-theme.in:203-222`).

### 7.2 Qué copia el hook de initramfs de Debian/Ubuntu [P]

`/usr/share/initramfs-tools/hooks/plymouth` (Ubuntu):

- Nombre del tema = nombre base del `.plymouth` elegido; copia
  `/usr/share/plymouth/themes/<nombre>/` **entero** (`cp -a`). El directorio debe llamarse
  igual que el `.plymouth` y estar bajo `/usr/share/plymouth/themes/`.
- Módulo: `sed -n 's/^ModuleName=\(.*\)/\1/p'`. La línea debe ser **exactamente**
  `ModuleName=script`, al inicio y sin espacios; si no, avisa
  `plymouth module (...) missing, skipping that theme` y **no copia el tema**. El hook de
  Debian usa la misma expresión.
- `ImageDir` fuera de la carpeta del tema no se copia bien: dejar las imágenes dentro.
- Para temas no de texto añade `label-pango.so` si existe, fontconfig y la fuente Ubuntu.
- Arranque: `scripts/init-premount/plymouth` lanza
  `plymouthd --mode=boot --attach-to-session --pid-file=/run/plymouth/pid` y
  `plymouth --show-splash` solo si la línea del kernel contiene `splash`;
  `init-bottom` avisa el cambio de raíz.

### 7.3 Probar sin reiniciar

Rutas compiladas en los binarios de Ubuntu [P: `strings`]: plugins en
`/usr/lib/x86_64-linux-gnu/plymouth/`, temas en `/usr/share/plymouth/themes/` y
`/run/plymouth/themes/`, configuración en `/etc/plymouth/plymouthd.conf`.

```sh
sudo plymouthd --debug --debug-file=/tmp/plymouth-debug.log --no-daemon \
     --kernel-command-line="splash plymouth.splash=paraguay" &
sudo plymouth show-splash
sudo plymouth display-message --text="hola"
sudo plymouth ask-for-password --prompt="Clave"
sudo plymouth change-mode --shutdown
sudo plymouth quit
```

- plymouthd exige `geteuid() == 0` (`src/main.c:2434-2437`) y rechaza las órdenes de un
  cliente que no sea root (`src/ply-boot-server.c:426-427`).
- Con `DISPLAY` definido y `renderers/x11.so` instalado usa el **renderer X11**
  (`src/main.c:2089-2091`, `:2541-2543`): una ventana a pantalla completa en el monitor primario,
  o dos ventanas falsas de 800×600 y 640×480 si existe la variable
  `PLY_CREATE_FAKE_MULTI_HEAD_SETUP` (`src/plugins/renderers/x11/plugin.c:219-299`), útil para
  probar varias pantallas.
- `--kernel-command-line` sustituye a `/proc/cmdline`: sin `splash` plymouthd entra en modo
  detalles y no carga el tema. `plymouth.splash=<nombre>` elige el tema sin tocar la
  configuración del sistema.
- `--debug` activa las trazas: ahí aparecen los `Parser error` y `Execution error`. Opciones
  de kernel equivalentes: `plymouth.debug`, `plymouth.debug=file:/ruta`.
- El socket de control es abstracto (`/org/freedesktop/plymouthd`): solo puede haber un
  plymouthd por espacio de nombres de red.

## 8. Trampas concretas

Formato y sintaxis:

1. **CRLF o BOM** en el `.script` rompen el análisis; `\r` en el `.plymouth` rompe `ModuleName`.
2. **`;` suelto** después de `}` (de `fun nombre`, `if`, `for`, `while`) o `;;`: falla todo el
   archivo. Y al revés: `x = fun () { … }` **necesita** `;`.
3. Un error de sintaxis descarta el script entero y deja la pantalla negra sin aviso visible.
   Una `{` sin cerrar se traga el resto del archivo sin abortar.
4. `true`, `false`, `null`, `undefined` no existen: valen NULL (falso).
5. No hay `1e3`, `.5`, hexadecimal, comillas simples, ternario, `switch`, `var`, `function`.
6. `"\t"` no es tabulador; solo existen `\n`, `\e`, `\0`, `\"`.

Semántica:

7. Variable sin inicializar + número = NULL; `x += 1` y `x++` sobre algo sin definir dejan
   NULL. Inicializar todo contador.
8. Asignar dentro de una función a un nombre que existe como global **modifica el global**;
   los contadores de bucle (`i`, `k`) pisan globales homónimos. Usar `local.i`.
9. Parámetro omitido = se busca un global con ese nombre. Afecta a `Image.Text` (`alpha`,
   `font`, `align`) y a `Sprite.SetPosition` (`x`, `y`, `z`): no usar esos nombres como globales.
10. `SetPosition(x, y)` sin z manda el sprite a z = -2147483648.
11. `obj.x = v` modifica el "prototipo" si la clave ya existe allí.
12. Leer `v.campo` o `v[i]` sobre un número o cadena **lo convierte en hash** y pierde su valor.
13. Claves numéricas: se formatean con `%g`. Enteros ≥ 1 000 000 colisionan; un índice con
    decimales no encuentra nada (`Math.Int`); `"txt" + 1234567` da notación científica.
14. No hay conversión de cadena a número: las variables de `[script-env-vars]` son cadenas y
    `"480" * 2` es NULL. Hay que convertir dígito a dígito con `CharAt` (probado en el arnés).
15. `%` devuelve negativos con dividendo negativo; `Math.Int` es `floor`.
16. Comparar tipos distintos siempre da "distinto"; las cadenas se comparan con `strcmp`.
17. Una función sin `return` devuelve su última expresión; llamar a algo inexistente devuelve
    NULL sin error (un nombre de API mal escrito no se nota).
18. No hay clausuras ni forma de recorrer las claves de un hash ni de saber su tamaño.

Imágenes y sprites:

19. `Image("no-existe.png")` devuelve NULL en silencio; `Sprite(NULL)` es un sprite invisible
    y `NULL.GetWidth()` es NULL, que contamina los cálculos.
20. Solo PNG y BMP de 24 bits. Los PNG nunca usan el camino rápido de copia.
21. Sprite sin referencia = sprite destruido. Guardarlos en un hash global.
22. `SetImage(NULL)` no quita la imagen. Para ocultar: `SetOpacity(0)`.
23. Opacidad fuera de [0, 1] se desborda (1.01 se ve casi transparente). Cambios de opacidad
    ≤ 0.01 se ignoran hasta acumularse.
24. Las coordenadas son enteras: un movimiento menor a 1 px por cuadro avanza a saltos.
25. `Rotate` no agranda el lienzo: recorta las esquinas. Ángulo en radianes.
26. `Scale`, `Rotate`, `Crop`, `Tile` y `Text` por cuadro: asignan un buffer nuevo cada vez.
27. `ImageDir` ausente en el `.plymouth` hace caer plymouthd.

Ejecución:

28. No hay reloj y no se saltan cuadros: si el cuadro excede el período, la animación se
    enlentece. El progreso de arranque trae tiempo real, pero se congela con las preguntas.
29. Mover cientos de sprites por cuadro tiene costo cuadrático (§4.4). Usar el sprite cobertor
    o agrupar puntos en menos sprites. No cambiar z en masa.
30. `Window.SetBackground…Color` en el callback de refresco redibuja la pantalla entera.
31. `SetRefreshRate(0)` congela la animación; un valor no numérico o enorme deja la CPU al 100 %.
32. Script grande = arranque lento: se lee byte a byte y cada sentencia de inicialización
    cuesta microsegundos. Calcular tablas en bucle, no pegarlas como miles de líneas.
33. El script se reinicia desde cero al cambiar de modo, con Esc (ida y vuelta) y con `reload`.
34. No hay animación de salida, y lo que dibuje el callback de `Quit` no llega a verse (§6.5).
35. Sin callbacks de contraseña el diálogo de LUKS es invisible. `DisplayNormal` puede
    llamarse antes de que exista cualquier diálogo.
36. `Image.Text` sin plugin label devuelve 0×0 sin error; con label-freetype el nombre de la
    fuente se ignora.
37. En HiDPI (escala 2) las imágenes se amplían con interpolación y el script no se entera.
38. `Window.GetWidth()` sin índice es el máximo entre pantallas, no la primera; y en 0.9.5
    era el mínimo. Con varias pantallas, recorrer los índices.
39. `Window.GetBitsPerPixel` solo existe en Ubuntu.

Empaquetado:

40. En Debian/Ubuntu `ModuleName = script` (con espacios) funciona en plymouthd pero el hook
    de initramfs **no copia el tema**.
41. La carpeta del tema debe llamarse igual que el `.plymouth` y contener imágenes y script;
    `ImageDir` y `ScriptFile` deben ser rutas absolutas a esa carpeta.
42. Tras cambiar cualquier archivo del tema hay que **regenerar el initramfs**; si no, el
    arranque usa la copia vieja.
43. Ubuntu no trae `plymouth-set-default-theme`; Debian sí. Las instrucciones difieren.
44. Sin `splash` en la línea del kernel no hay splash gráfico (en Ubuntu ni siquiera arrancan
    las unidades).

## 9. No verificado

- **Plymouthd real**: no se ejecutó (sin `sudo`). El comportamiento del demonio, del renderer
  DRM/X11 y del arranque sale de leer el fuente; lo ejecutado es solo el intérprete y el
  refresco de sprites dentro del arnés. En particular no se observó: el batido 50/60 Hz, que
  el dibujo del callback de salida no se vea (§6.5), ni la caída por falta de `ImageDir`.
- **Tiempos**: medidos en el arnés, bajo WSL2, en una máquina con carga variable (hasta ×2 de
  diferencia entre corridas iguales). Sin medir: hardware real, arranque en frío, CPU lentas,
  costo del volcado DRM.
- **Varias pantallas**: derivado del fuente; el arnés simula una sola.
- **Carga real de PNG/BMP y `Image.Text`**: el arnés sustituye `ply-image` y `ply-label`. Lo
  dicho sobre formatos, marca "opaca" y fuentes viene solo del fuente.
- **Fedora, Arch, openSUSE**: solo spec/PKGBUILD de ramas actuales (versiones 26.x y 22.02),
  no paquetes construidos ni la versión 24.004.60. Sus hooks de dracut no se revisaron.
- **Debian**: se inspeccionaron los `.deb` de trixie, no los archivos `debian/` del fuente
  (salvo la lista de parches).
- **Qué envía systemd como `status`** y **qué órdenes usa cada gestor de sesión**
  (`deactivate`, `quit --retain-splash`): no están en el fuente de Plymouth.
- **Versiones anteriores**: no se comprobó qué funciones de §3 faltan en Plymouth 0.9.x o 22.x.
- **Desbordes de opacidad y de `NAN` a entero**: son comportamiento indefinido en C; los
  valores citados son los observados con gcc 13 en x86-64.
