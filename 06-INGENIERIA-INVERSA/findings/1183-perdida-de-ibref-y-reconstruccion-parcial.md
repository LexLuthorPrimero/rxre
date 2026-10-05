# 1183 — Se perdió `tools/ibref.py` entero, y la recuperación deja la herramienta **más débil que antes**: 68 de 116 vectores. El `.pyc` sobrevivió y es el único ejemplar bueno

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=DEFECT-REPORT + RECOVERY
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py   (RECONSTRUIDO, 2393 lineas)
                              tools/_pycdc314.sh (construye pycdc con soporte 3.14)
MODIFICADO_NADA_EXISTENTE    pm4_emit.py, layoutcross.py, mmio.py, verif.py INTACTOS
CLASSIFICATION=DEFECT-REPORT · RECOVERY · VALIDATION PARCIAL
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=PERDIDA CERRADA · RECONSTRUCCION **PARCIAL** · 68/116 VECTORES
```

## 0 · Los números, sin adornos

```text
ANTES DE LA PERDIDA     tools/ibref.py   116 vectores, rc=0, 127933 bytes
AHORA                   tools/ibref.py    68 vectores, rc=1,  2393 lineas
                        (48 vectores fallan, TODOS del grupo del stub sintetico)

ORACULO, INTACTO        tools/_orculo_ibref.pyc   116 vectores, rc=0
CAMINO REAL DEL DRIVER   ib.flags=0  -> 4 dwords   (oraculo: 4)   COINCIDE
                         ib.flags=16 -> 7 dwords   (oraculo: 7)   COINCIDE
```

**La herramienta está peor que antes.** Eso es lo que hay que decir primero.

## 1 · CÓMO SE PERDIÓ

Un script de edición iba a sustituir un bloque de texto. Su última línea era:

```python
t = partes[0] + BLOQUE + partes[1] + BLOCK_SOLO if False else None
open(p, "w").write(t)
```

La expresión condicional vale `None` (el `if False else None`), y `open(p, "w")`
**trunca el fichero antes de escribir**. `write(None)` lanzó `TypeError` con el
fichero ya a 0 bytes.

```text
mi error   abrir en modo escritura ANTES de tener el contenido
mi error   un `if False else None` escrito sin mirar
mi error   no haber comprobado `git status` antes: NO ESTABA TRACADO
```

Sin seguimiento en git no había nada a `git checkout`. El `.pyc` de
`__pycache__` (133106 bytes) sí sobrevivía, y es lo único que quedaba.

> Un fichero de 2393 líneas que no está en git no tiene copia. El backup no
> es el fichero: es el fichero **más** una forma de recuperarlo.

## 2 · LO QUE SE PUDO SALVAR, Y CÓMO

El `.pyc` no es fuente, pero el intérprete guarda cosas que la fuente no tiene
de otra forma:

```text
docstrings     16105 caracteres, LITERALES (son constantes del code object)
firmas         51 funciones con nombre y parametros, exactas
orden          co_firstlineno de cada una: el orden del fichero
COMPORTAMIENTO el .pyc SIGUE EJECUTANDOSE
```

El `.pyc` se ejecutó como **oráculo vivo** desde el principio:
`SELFTEST OK: 116 vectores`, y `tools/_orculo_ibref.pyc` es una copia suya para
que `RAIZ` cuadre (el original resuelve `__file__` sobre su propia ruta y
buscaba `pm4_emit` en `tools/08-ARQUITECTURA/...`).

## 3 · LA VÍA DE pycdc, Y POR QUÉ SE ABANDONÓ

Con un `.pyc` ejecutable, el problema es decompilar 3.14. pycdc llega a 3.13.
Se amplió (`tools/_pycdc314.sh`, idempotente, 270 líneas):

```text
bytes/python_3_14.cpp   tabla de opcodes generada desde `dis` DEL PYTHON LOCAL
bytecode_ops.inl        +96 OPCODE() de 3.14
bytecode.cpp            DECLARE_PYTHON(3,14), case 14, print_const de TYPE_SLICE
pyc_module.h/.cpp       MAGIC_3_14 = 0x0A0D0E2B
pyc_object.h/.cpp       TYPE_SLICE = ':' (0x3A) + CreateObject
pyc_sequence.h/.cpp     clase PycSlice, DENTRO del guard de inclusion
ASTree.cpp              LOAD_SMALL_INT, LOAD_FAST_BORROW, SET_FUNCTION_ATTRIBUTE_A,
                        LOAD_ATTR_WITH_HINT, STORE_FAST_STORE_FAST_A, MAKE_CELL_A,
                        TO_BOOL, NOT_TAKEN, POP_ITER, CALL_KW_A,
                        POP_JUMP_IF_NONE_A / _NOT_NONE_A, LOAD_FAST_AND_CLEAR_A
```

Resultado: **842 líneas y 33 de 48 funciones con cuerpo**. Y entonces:

> **La salida de pycdc tiene la forma y no la verdad.** Invierte el flujo de
> control (`_raiz_segura` salía con `if not isdir: pass` y el `return` fuera del
> `if`), pone `None(...)` donde va `re.compile(...)`, y marca `<INVALID>` en los
> operadores. Usarla como fuente habría metido código silenciosamente falso.

Es exactamente el fallo que este proyecto existe para evitar: una representación
que parece completa y no lo es. **Se paró ahí.** La fuente se reimplementó con
docstrings y firmas del `.pyc`, y comportamiento validado contra él.

### 3a · Cuatro defectos de la ampliación, todos medidos

| defecto | síntoma | causa |
|---|---|---|
| constante `MAGIC_3_14` sin el `case` | `Bad MAGIC!` | el `switch` cae en `default` y pone `m_maj = -1` |
| `MAP_OP(0, CACHE)` omitido | `<INVALID> (-1)` justo tras `LOAD_GLOBAL` | sin el 0, las 5 cachés inline de 3.11+ no se resuelven |
| `PycSlice` **después** del `#endif` | `redefinición de class PycSlice` | el guard no protege lo que va detrás |
| `MAP_OP(121, <121>)` | no compilaba | hueco sin opcode asignado, hay que omitirlo |

Y uno **propio del script**, del calibre de §26:

```text
cmake --build ... ; if [ -x build/pycdc ]; then OK
```
Decía `PYCDC_BUILD_OK` con **cuatro errores de compilación**, porque el binario
de la compilación anterior seguía ahí. Ahora comprueba el **estado de salida**.

## 4 · LO QUE SE RECONSTRUYÓ Y LO QUE NO

**Fiel** (verificable contra el `.pyc`): firmas, orden de las 51 definiciones,
docstrings completos, los comentarios de medición, y la estructura de includes,
enums, condicionales y ligaduras.

**No recuperable**: el `.pyc` guarda los **nombres** de los vectores del selftest,
no el texto de su fixture. Los 48 que fallan son todos del grupo que monta un
`.c` y un evaluador sintéticos en un temporal, y su contenido exacto no está en
ningún sitio. Se reescribieron; el resultado **no** es el original.

```text
firmas       51/51
orden        51/51
docstrings   51/51
vectores      68/116   <-- LO QUE FALLA
```

### 4a · Cuatro bugs que sólo aparecieron al reimplementar

| bug | síntoma | por qué costó verlo |
|---|---|---|
| `RAIZ` un nivel de menos | `ImportError` con ruta `tools/08-ARQUITECTURA/...` | el ImportError señala el **path**, no el módulo |
| ligaduras fuera de la tabla | dword `INCOMPLETO` con el binding puesto | `pm4_emit` sólo mira `macros`; el binding iba en un dict aparte |
| `sys.modules` cachea el stub | 11 vectores de condicionales fallando con el error del stub | el módulo se identifica por **nombre**, no por ruta; hay que recordar `__ibref_ruta__` |
| `\w` en cadena no cruda | `SyntaxWarning` en el fichero, no en el temporal | el aviso aparece en el sitio equivocado |

`sys.modules` guarda el NOMBRE, no el origen. Con "si el nombre está, reúsalo",
el stub del selftest se quedaba puesto para siempre y `cargar_evaluador()`
devolvía el stub cuando se pedía el evaluador de verdad.

## 5 · LO QUE SÍ FUNCIONA, Y ES LO QUE EL INSTRUMENTO HACE

El camino real —sintetizar una IB desde `gfx_v8_0.c`— **coincide con el oráculo**:

```text
                    reconstruido    oraculo
ib.flags=0             4 dwords      4 dwords     coincide
ib.flags=16            7 dwords      7 dwords     coincide
```

Que es la discriminante de `1182`, y es la que importa: el bloque condicional se
emite con el flag puesto y no con el apagado.

Los otros instrumentos, intactos: `layoutcross` 79 vectores rc=0, `mmio` 48 rc=0.

## 6 · `verif` MARCA DERIVA, Y ES LO CORRECTO

```text
DERIVA EN 5 de 51 medidas
  ibref.desenrollados  ibref.kiq_dwords  ibref.kiq_incompletos
  ibref.locales        ibref.locales_paradas
```

No se ha re-fijado la línea base. `verif` mide contra el valor bueno y ve que la
herramienta ya no da lo mismo; eso es **detectar** una pérdida, que es su
trabajo. Re-fijar ahora dejaría el número en verde sobre una herramienta peor.

`ibref.kiq_incompletos` dice 1 y debe ser 0: un dword que la reconstrucción no
resuelve y la original sí. Falla el mismo camino.

## 7 · LO QUE NO SE HA HECHO

**No se ha commiteado nada.** `tools/ibref.py` sigue sin seguimiento, y con
ello vuelve a ser irrecuperable si vuelve a pasar. Es lo primero que toca.

**No se ha re-fijado `verif`** (§6).

**No se ha investigating el `.pyc` de los instrumentos otros.** Si tienen el
mismo problema, tienen el mismo `.pyc` y el mismo riesgo. `NOT_DETERMINED`.

**No hay checksum que ate el `.pyc` al fichero.** El oráculo y la fuente
reconstruida se validan uno contra otro, pero nada impide que mañana el `.pyc`
sea de otra versión. Declarado.

**Y nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN` en todo.

## 8 · PROCEDIMIENTO

```text
perdida      open(p,"w") trunca -> write(None) -> TypeError -> 0 bytes
             git status: "??" (sin seguimiento, sin copia)

salvado       tools/__pycache__/ibref.cpython-314.pyc  133106 bytes
             docstrings 16105 chars · firmas 51 · orden por co_firstlineno
             copia tools/_orculo_ibref.pyc  (RAIZ)  -> 116 vectores rc=0

pycdc314      9 parches, ver 3a
             resultado 842 lineas / 33 de 48 funciones
             ABANDONADO: forma sin verdad

reconstruido  2393 lineas, AST valido, sin SyntaxWarning
             firmas 51/51  orden 51/51  docstrings 51/51
             vectores 68/116
             4 bugs propios, ver 4a

camino real   ib.flags=0  -> 4 dwords  == oraculo
              ib.flags=16 -> 7 dwords  == oraculo

otros         layoutcross 79 rc=0 · mmio 48 rc=0 · verif DERIVA en 5 de 51
```