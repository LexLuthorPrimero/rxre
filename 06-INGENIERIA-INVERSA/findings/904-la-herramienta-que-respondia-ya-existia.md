# 904 · La herramienta que respondía mi pregunta ya existía, y estaba fuera del registro

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> Iba a construir un extractor de structs. **No hacía falta: ya existe, está
> hecha a propósito, y su docstring dice la respuesta que yo pasé cuatro
> iteraciones derivando a mano.**
>
> Y el hueco que lo provoca es localizable y pequeño: **está fuera del directorio que
> el registro de herramientas inventaría.**

## 1. Lo que ya existía

```
08-ARQUITECTURA/tools/btfq/btfq.py    645 lineas
```

Su docstring, textual:

> «Este proyecto razona sobre `RESEARCH/working/linux-7.1.3`: el **ÁRBOL DE
> FUENTES**. Ese árbol dice de dónde VENIMOS. `/sys/kernel/btf/amdgpu` es el
> **BINARIO que está corriendo ahora mismo en la RX550**. Son dos artefactos
> distintos y no tienen por qué coincidir: el host puede llevar parches que el
> corpus no tiene.»

Eso es **exactamente** la conclusión a la que llegué ayer con `pahole`, con cuatro
iteraciones de coste y dos conclusions falsas de por medio. Y está escrito.

Además resuelve las tres cosas que el prompt `§15` pide de un BTF:

```
1. que un struct tiene el tamaño y los offsets que el corpus asume
2. que un enumerador tiene el valor que el corpus asume
3. que un campo EXISTE en el binario, no solo en el fuente
```

Y documenta sus **cuatro fallos de parseo** que él mismo cometió — leer `btf_type` como 4
bytes, offsets de header como absolutos, sumar `str_off` dos veces, y tratar los
ids del módulo como locales. Con la prueba, no con la suposición: rangos de ids
del base y del módulo, 6433 y 30997 referencias, 3972 huecos que son todos `id 0 =
void`.

Eso es un parser validado, no un script de cinco líneas.

## 2. Lo que devuelve, y confirma `906` campo por campo

```
$ btfq.py struct ATOM_Tonga_POWERPLAYTABLE
      ucTableRevision             bitoff=32   bits=8    -> byte 4
      usTableSize                 bitoff=40   bits=16   -> byte 5
      ulGoldenPPID                bitoff=56   bits=32   -> byte 7
      usSclkDependencyTableOffset bitoff=360  bits=16   -> byte 45
      usPowerTuneTableOffset      bitoff=456  bits=16   -> byte 57
$ btfq.py size ATOM_Tonga_POWERPLAYTABLE
      size_declarado=77   ultimo_campo_ends=77   (28 miembros)  OK

$ btfq.py struct ATOM_Polaris_PowerTune_Table
      usTDP                    bitoff=8    bits=16   -> byte 1
      usClockStretchAmount     bitoff=200  bits=16   -> byte 25
$ btfq.py size ATOM_Polaris_PowerTune_Table
      size_declarado=53   ultimo_campo_ends=53   (32 miembros)  OK

$ btfq.py struct ATOM_Polaris10_PCIE_Record
      ucPCIEGenSpeed   bitoff=0    ucReserved bitoff=16
      usPCIELaneWidth  bitoff=8    ulPCIE_Sclk bitoff=32      size 8
```

Los tres, **empaquetados**. Idénticos a lo que me dio `pahole`, y por tanto
`906` queda confirmado por **dos herramientas independientes** leyendo el binario.

Y el cierre más bonito del día: **`size_declarado = 77`**, y **`usTableSize` en el
byte 5 del ROM vale 77**. El campo del BIOS y el tamaño del struct son el mismo
número. Eso confirma a la vez el empaquetado, la base `0x9C0A`, y que la lectura
del VBIOS es correcta.

`ATOM_Polaris10_PCIE_Record` sin relleno y tamaño 8: **`601` sigue `REFUTED`**.

## 3. Las otras dos, y por qué no bastaban

En `tools/` sí hay dos herramientas de layout, y **las dos están documentadas**:

```
struct_layout.py   TL-46    modelo de ABI, 71777 bytes
gccverify.py       TL-45    pregunta a gcc, 15067 bytes
```

`gccverify` es el enfoque correcto: incluir la **cabecera real** del corpus, que
arrastra el `#pragma pack` consigo, y comparar con el modelo. Ese diseño nunca
hubiera tenido mi error.

Lo probé sobre el struct disputado, y:

```
$ gccverify.py --header pptable_v1_0.h --struct ATOM_Tonga_POWERPLAYTABLE \
      --field usPowerTuneTableOffset
      gcc: NO_COMPILE
      in file included from .../include/linux/seq_file.h:5,
                       from .../pm/powerplay/inc/hwmgr.h:26
      CLASIFICACION: NO_COMPARABLE (no se inventa ningun numero)
```

Es el mismo muro que yo me comí: `pptable_v1_0.h` arrastra `hwmgr.h`, que arrastra
`linux/seq_file.h`, que arrastra `linux/types.h`, que exige el entorno de build del
kernel.

**Y eso no es un fallo de la herramienta: es la clasificación correcta.** Dice
`NO_COMPARABLE` y no inventa un número. Es exactamente la disciplina que a mí me
faltaba.

Las tres se reparten bien:

| herramienta | pregunta | estado en este caso |
|---|---|---|
| `struct_layout` | ¿qué dice el **modelo**? | modelo, se equivoca si hay contexto que no conoce |
| `gccverify` | ¿qué dice **gcc** con la cabecera real? | `NO_COMPARABLE`: el muro de las cabeceras del kernel |
| `btfq` | ¿qué dice el **binario que corre**? | **responde** |

La que responde es la que está fuera del registro.

## 4. El hueco, con su sitio exacto

```
$ toolreg.py --repo <repo> --no-selftest
  121 source tools in tools/
```

Y `btfq` **no está entre los 121**, porque vive en
`08-ARQUITECTURA/tools/btfq/` y `toolreg` inventaría `tools/`.

Peor: la cobertura documental está en **92 de 121 sin ninguna referencia**.

```
docs: 92 sin referencia   ·   solo unas 16 citadas (TL-07, TL-35, TL-41, TL-46…)
```

Y el docstring de `toolreg` describe el fallo antes de que ocurra:

> «23 herramientas fuente construidas por tres sesiones en una mañana. Ninguna
> sabía de la existencia de las demás […] un agente a punto de transcribir un
> campo de registro a mano **no sabría que existe una herramienta para eso**.»

**Eso es literalmente lo que me pasó.** Construí un pipeline de probes, lo
instrumenté, y nunca miré el registro ni el directorio `08-ARQUITECTURA/tools/`.
Peor: cuando `gccverify` me devolvió `NO_COMPARABLE`, leí «no se puede medir»
cuando quería decir «no se puede medir *por esa vía*, y hay otra».

## 5. Lo que cuesta, y por qué lo digo

Cuatro hallazgos —`604`, `608`, `901`, `906`— y una medición completa con dos
herramientas que no eran la adecuada. Todo por no mirar dónde estaban las
herramientas.

Y hay una ironía que conviene registrar: **`906`**, que es el hallazgo siguiente, dice en su
sección 7 que «el layout de un struct se afirma con el BTF del módulo cargado, que
es el código que corre» — y esa frase es **literalmente** la que ya estaba escrita
en el docstring de `btfq`. Llegué a la regla correcta por el camino largo, con
cuatro hallazgos de coste.

## 6. Los errores de esta iteración

**1.** Anuncié «construir el extractor» sin haber buscado. `§40` pone la pregunta
`EXISTING TOOL?` antes que `BUILD TOOL?`, y el prompt lo tiene escrito en dos
sitios (`AGENTS.md:1416` y `:2481`). **No lo consulté.** Eso es fallar en la
primera pregunta de un ciclo que dura un minuto.

**2.** Busqué BTF solo dentro de `tools/`, un directorio. El prompt `§13` exige
inspeccionar el ámbito antes de concluir, y `§11` dice buscar primero
equivalentes existentes.

**3.** `toolreg.py` sin `--repo` falla con «no source tools under
…/tools/tools», porque por defecto espera el repo en el directorio actual. Un
error de usabilidad pequeño, de alguien que no es de este hilo.

**4.** `--json` no emite JSON válido desde esta invocación: `toolreg` escribió
cero bytes en stdout y un error en stderr. No concluyo concluyo que el `--json` esté
roto: no lo he probado con `--repo`.

## 7. Lo que queda hecho, y lo que queda abierto

**Hecho:**

- `906` confirmado por **dos** herramientas independientes.
- El mapa de las tres herramientas de layout, con qué respuesta da cada una y
  cuándo.
- El hueco localizado: la que responde está fuera del registro, y el registro
  tiene 92 de 121 sin documentar.

**Abierto, y no es mío:**

`08-ARQUITECTURA/tools/btfq/` es trabajo de otra sesión. No lo toco. Lo que
corresponde es que quede **registrado**, y eso lo escribe quien lo revise.

## Frontier siguiente

**Cerrar el escarabajo de los 4 campos del PowerTune y devolver el trabajo a la
línea viva, que es donde sigue el valor.**

El cap de Clock Stretcher **está activo** (`608`, `PROVEN`, y el BTF lo confirma:
`usClockStretchAmount` = 2, en el byte 25, dentro del dominio 1..5). La pregunta
que queda es la que `608` dejó abierta y que el BTF no responde:

> **¿Con qué semántica ejecuta el SMC la cadena que empieza en `init_smc_table:1913`?**

Criterio de cierre: los campos que la tabla de 95 de `502` declara «suben en cero
siempre», contrastados contra lo que la ruta viva realmente escribe, y una lista
de los que **no** tienen escritor identificado.

Y una nota de método que ya no es opcional: **todo offset de struct va contra
`btfq`, y si `btfq` no lo tiene, el estado es `NOT_VERIFIED`.** Nunca contra un
probe mío. Es la regla que me habría ahorrado el día.