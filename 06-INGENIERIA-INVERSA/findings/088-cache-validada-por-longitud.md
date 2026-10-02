# 088 · Una cache validada por longitud: el fallo que hacia desaparecer un struct segun el orden de ficheros

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Que pasaba

El modo `--coverage` de `smc_layout.py` daba solo 2 de 39 escrituras medidas, y la
mas importante —la copia de la tabla DPM completa, `polaris10_smumgr.c:2118`— salia
**sin medir**. Todo lo demas funcionaba: 124/124 structs conformes con gcc, la copia
de 1776 bytes resuelta en la auditoria, la conformidad intacta.

Un fallo masificado no con el alcance de la conclusion, sino con lo que la conclusion
sostenida. Y no lo causaba el codigo bajo analisis.

## La causa

`struct_layout._TEXT_CACHE` guardaba el texto limpio de cada fichero y validaba la
entrada comparando **la longitud del needle**:

```python
_TEXT_CACHE: Dict[str, Tuple[float, int, str]] = {}   # mtime, len(needle), texto

def _clean_text(path: str, needle: str) -> str:
    ...
    if needle not in raw:
        _TEXT_CACHE[path] = (st.st_mtime, len(needle), "")   # <- cachea ""
        return ""
    ...
```

Buscando `SMU73_Discrete_DpmTable`, `smu74_discrete.h` no contiene ese nombre, asi que
se cachea como **cadena vacia**, con la longitud 23. Buscando despues
`SMU74_Discrete_DpmTable`, que tambien mide **23**, la comprobacion `cached[1] ==
len(needle)` da correcta y la cache devuelve `""` como si esa fuera la respuesta
correcta. El struct no existia.

Medido:

```
longitud de los dos nombres: 23 23
cacheado tras buscar SMU73: ''
ahora se busca SMU74      : ''
```

Y el orden que lo dispara es el de `os.walk`: `fiji_smumgr.c` se recorre antes que
`polaris10_smumgr.c`. En el subarbol hay seis generaciones con el mismo esquema de
nombre, y `SMU71/72/73/74/75_Discrete_DpmTable` **todos miden 23**.

Un resultado que depende del orden en que se recorre el arbol no es un resultado.

## Por que el self-test no lo cazaba

Porque los vectores usaban un solo needle por fichero temporal. Con un needle, la
longitud coincide siempre y la cache nunca puede equivocarse. **La colision necesita dos
nombres de la misma longitud, y eso no aparece en un fixture de un solo caso.**

El mismo fallo de forma, en `gccverify`: pide un unico campo y da por buena la primera
compilacion que funciona. Los dos necesitan **dos entradas que se confirmen
mutuamente**, y un fixture con un caso no lo tiene.

## La correccion

La clave incluye el needle completo y el mtime, y la longitud desaparece:

```python
_TEXT_CACHE: Dict[Tuple[str, str], Tuple[float, str]] = {}   # (ruta, needle) -> (mtime, texto)
```

Y un vector que reproduce la colision explicitamente:

```python
_A = "SMU73_Discrete_DpmTable"      # mismo numero de caracteres que _B
_B = "SMU74_Discrete_DpmTable"
check("cache.misma_longitud", len(_A), len(_B))
_clean_text(_f, _A)
check("cache.no_colisiona", _B in _clean_text(_f, _B), True)
```

## La regla

**Una clave derivada de una magnitud no identifica a la entrada.**

La longitud no es una identidad. Dos entradas distintas que ocupan lo mismo se
confirman mutuamente, y el resultado es un `""` que se presenta como respuesta. Es el
mismo patron que el resto de los fallos de `082`, con un disfraz distinto: aqui no es
un valor inventado, es un valor **omitido** que se lee como medido.

La forma general: `082` inventaba un `0`; aqui se omite un struct. Inventar y omitir
son el mismo fallo: uno pone un numero falso y el otro borra el que hubiera.

## Efecto secundario encontrado de paso

Al instrumentar el fallo aparecio otra cosa: `find_struct_scoped` derivaba la raiz de
la busqueda global **subiendo cuatro directorios** desde el fichero de contexto. Desde
un arbol temporal eso acaba en `/tmp`, y la herramienta se colgaba recorriendolo.

Ahora la raiz es **explicita**:

```python
def find_struct_scoped(name, ctx_file, fallback_root=""):
```

Que es lo correcto: un sitio que pide una busqueda global sabe cual es la raiz.
Adivinarla es lo que la hacia colgarse. Este no lo delata ningun test: solo se ve al
usar la herramienta con un arbol pequeno.

## Verificacion

Despues de las correcciones, sin ninguna regresion:

```
gccverify  struct_layout  DpmTable  1884 bytes   COMPARACION: COINCIDE
conformidad  124 comparadas · COINCIDEN 124 · divergen 0
smc_layout --copies  110 llamadas · 83 medidas · 0 sin clasificar · 0 truncadas
smc_layout --coverage  [108, 1884) · hueco unico [0, 108)
```

El hueco unico de 108 bytes es la confirmacion automatizada de `087`: los tres
`PIDController` son del firmware.

## Clasificacion

- `TEXT_CACHE_COLLISION = PROVEN`: nombres de igual longitud, cache vacia devuelta como
  respuesta.
- `TEXT_CACHE_EFFECT = PROVEN`: `SMU74_Discrete_DpmTable` sin medir segun el orden de
  `os.walk`.
- `TOOL_FIND_STRUCT_SCOPED_ROOT = REFUTED`: la raiz global era adivinada y colgaba.
- `COVERAGE = TOOL_VALIDATED`: 3 escrituras medidas, 36 de otra struct, 0 sin medir,
  hueco unico [0, 108).

## Lo que esto NO dice

No dice nada de la tabla DPM ni del firmware. El fallo era de la herramienta que mide,
y lo que la herramienta mediria al estar bien sigue siendo lo que ya estaba medido: 1884
bytes, 1776 de copia, `[108, 1884)`.

Lo que cambia es la confianza en el metodo, no el resultado. Y eso es justo lo que hay
que registrar cuando una herramienta resulta tener un fallo: la conclusion
anterior no se movio, pero ahora se sabe que se obtuvo por un camino que podia dar
otra cosa. Un resultado obtenido por un metodo con un fallo conocido esta en
cuarentena hasta que el metodo se arregla y se vuelve a obtener.
