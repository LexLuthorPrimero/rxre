# 049 · Los 497 respaldos en código, resueltos contra el corpus: cero errores y tres marcas

`CLASSIFICATION=TOOL+NEGATIVE_RESULT` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`TOOL=tools/claims.py §3` · `COMPLETA=048` · `MODIFICATIONS=0` en el corpus

## CUDA principal

`048` dejó 208 afirmaciones respaldadas por **código copiado**, sin verificación automática, y
dijo que several eran tablas comparativas contra otras generaciones — el patrón de `035`. Era una
sospecha sin comprobar. Esto la comprueba.

`claims.py` §3 resuelve **cada símbolo citado** en el respaldo de las 497 filas `CODIGO`, y lo
clasifica. El resultado:

```
803  USADO_POR_MI_ASIC   el codigo de esta placa lo toca
  0  DEFINIDO_AQUI
 47  SIN_RELACION        no aparece en el codigo de esta placa
794  NO_RESUELTO         no esta en el corpus
```

**Y los 47 son 3 símbolos distintos.** Dos de ellos son correctos y uno exige mirar:

| símbolo | usos | dónde está | veredicto |
|---|---|---|---|
| `EOP_TC_MD_ACTION_EN` | 22 | `soc15d.h`, `gfx_v9_0.c`, `gfx_v9_4_3.c` | **GFX9+** |
| `VM_INVALIDATE_RESPONSE` | 19 | `sid.h` | no lo usa GFX8 |
| `VM_INVALIDATE_REQUEST` | 6 | `sid.h` | no lo usa GFX8 |

**Comprobado uno a uno, y el resultado es que no hay ningún error:**

`EOP_TC_MD_ACTION_EN` solo existe en `soc15d.h`, `gfx_v9_0.c` y `gfx_v9_4_3.c` — Navi. Y
`029`/`034` lo citan 22 veces **declarando que es de GFX9**:

```
029:262   "`EOP_TC_MD_ACTION_EN` esta en `soc15d.h`, que es el header de SOC15/GFX9. Que el bit
           [no exista en GFX8] es [el hallazgo]"
029:241   | GFX9 anade `EOP_TC_MD_ACTION_EN` (bit 21, "L2 metadata") | `PROVEN` |
```

Es un `NEGATIVE_RESULT` sobre GFX9, escrito como contraste deliberado, y el propio finding
explica por qué cita esa cabecera. **La herramienta lo marca; el documento ya lo declara.**

`VM_INVALIDATE_REQUEST` (desnudo, sin el prefijo `mm`) tampoco lo usa GFX8 — el vm-flush de
`gfx_v8_0.c:6209` espera `mmVM_INVALIDATE_REQUEST`:

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | WAIT_REG_MEM_FUNCTION(0) |
                         WAIT_REG_MEM_ENGINE(0)));
amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
```

Comprobado: `VM_INVALIDATE_REQUEST` desnudo aparece en `cik_sdma.c`, `gfx_v6_0.c`, `gmc_v6_0.c` —
otros ASICs. Los findings citan el nombre del campo que van a esperar, que es correcto para
describir el hardware, aunque el driver de esta placa escriba el `mm`.

**Veredicto: cero afirmaciones apoyadas en código de otro ASIC sin declararlo.** Es un
`NEGATIVE_RESULT` con valor: la sospecha de `048` era razonable y **queda cerrada sin encontrar
nada**, que es un resultado y no una ausencia de trabajo.

## El criterio tiene que ser el USO, y no qué cabecera lo define

La primera versión de esta sección comparaba los símbolos contra **qué fichero los define**, y
dio `SIN_RELACION` sobre `sid.h` y `soc15d.h`. Eso es un falso positivo por partida doble:

- `sid.h`, `soc15d.h`, `amdgpu.h` son cabeceras **comunes a la familia**, no de otra generación.
  No llevan versión en el nombre, y no hay forma de saber a qué ASIC pertenecen.
- La afirmación «está en `gmc_8_2_sh_mask.h`» **no** significa «es de otra generación»: una
  cabecera compartida puede ser la fuente de un nombre que esta placa sí usa.

El criterio correcto es el que ya usa `043`: **¿lo toca el código de esta placa?**

```python
usado = simbolo in usos_chip
```

`usos_chip` son los 22 697 identificadores que aparecen en los 7 `.c` que el `case` del chip
añade y en las 115 cabeceras que esos incluyen, resueltas por `#include`. Con ese criterio, la
tabla de arriba es exacta.

**La asimetría es deliberada y hay que declararla:** un símbolo de más se clasifica como usado y
no se marca; un símbolo de menos hace que una afirmación que se apoya en el código de esta placa
aparezca como `SIN_RELACION`, que es una acusación falsa. Entre los dos errores, el segundo es el
que cuesta tiempo a un lector.

## Cinco bugs, y cuatro de ellos de la misma clase

**`^` sin `re.MULTILINE`.** `INCLUDE_RX` anclaba al principio del *string*, no de cada línea, así
que `finditer()` sobre un fichero entero devolvía **cero** includes sin error. La primera versión
emparejaba línea a línea — y por eso encontraba seis — y al pasar al texto entero, que es lo
natural, dejó de encontrar nada. **Tercera vez en esta sesión** que un ancla sin su flag da un cero
silencioso (las otras dos: `^` sin `re.M`, y `\b` tras `_`, que nunca casa entre `4` y `_2`).

**Comparaba símbolos contra `.c`, no contra cabeceras.** `EN_MI_ASIC = 0` sin una sola excepción,
porque **ningún símbolo está definido en un `.c`**. Un cero absoluto en una columna no es un
resultado, es un fallo de la comparación. Y la dirección importa: si hubiera aceptado los símbolos
sin comprobar, habría hecho pasar por «de mi ASIC» cosas que no lo son — el error de `043` al revés
y peor.

**Aviso que se disparaba por algo que no era un fallo.** El índice tiene 1 408 986 símbolos, y yo
escribí un aviso de «más de 200 000, puede estar indexando variables locales». **Falso**: los
`*_sh_mask.h` autogenerados traen un miembro de enum por campo de registro, y `dcn_3_2_0` solo
aporta 194 932. El índice era correcto; el corpus es enorme. **Un aviso que se dispara por algo
que no es un fallo entrena a ignorar los avisos**, y este habría entrenado a ignorar el resto de
la sección.

**Y un índice demasiado ambicioso.** Intenté indexar también los campos de `struct`
clasificándolos por nivel de llaves, y seguía dando 1.4 M. Se decidió por lo que aporta: los
símbolos que el proyecto cita son macros y funciones (`mb()`, `writeq`, `PACKET3_SET_CONFIG_REG`,
`REG_SET_FIELD`), todas `#define` o miembros de `enum`. Los campos de struct son la parte que más
ruido hace y menos informa, porque pertenecen a una estructura y no a un ASIC.

## Lo que `claims.py` §3 no hace

**No comprueba que el símbolo respalde la afirmación.** Solo que el código de esta placa lo toque.
`PACKET3_SET_SH_REG` estar en `gfx_v8_0.c` no demuestra que la frase que lo cita esté probada;
demuestra que el nombre existe aquí. La diferencia entre las dos cosas es un juicio, y aquí no se
hace.

**Y no distingue `NO_RESUELTO` de `SIN_RELACION`.** Un símbolo ausente del corpus puede ser una
abreviatura del autor (`OBSERVATION`, 37 usos) o una función auxiliar de un finding. La lista los
muestra juntos y **avisa explícitamente de que no se lean igual**.

## UNLOCKS

- **La sospecha de `048` queda cerrada: cero errores.** Y el hallazgo de valor es el criterio, que
  es el de `043`: *uso*, no *definición*. Las dos cosas se pueden reutilizar tal cual para auditar
  cualquier documento del proyecto.
- `usos_chip` son 22 697 identificadores del código que esta placa ejecuta. **Es el conjunto que
  un driver propio puede usar sin preguntar si existe en otro silicio**, y ahora está medido.
- Los 794 `NO_RESUELTO` son casi todos abreviaturas del autor. No son un defecto, pero son la
  razón por la que el 71% de las afirmaciones del proyecto no es verificable por herramienta, y
  eso ya está cuantificado.

## Falsación

- Los cero errores se refutan si `usos_chip` dejara de cubrir el fichero que toca un símbolo. El
  criterio es comprobable: `PACKET3_SET_SH_REG` sale como usado y `EOP_TC_MD_ACTION_EN` como no,
  y los dos se verifican con un `grep` en un segundo.
- `SIN_RELACION` se refuta si un símbolo marcado resulta estar en el camino de esta placa por un
  `#include` de tercer nivel. Se siguen **dos** niveles; si el camino fuera más largo, la
  clasificación sería demasiado agresiva. El número de includes no resueltos se imprime.
- Los 47 se refutan si el `grep` directo contradice la clasificación. Ya se hizo para los tres, y
  los tres cuadran.

## Evidencia

```
tools/claims.py          20 vectores de selftest
                         497 filas CODIGO, 1644 simbolos citados
                         803 USADO_POR_MI_ASIC, 47 SIN_RELACION, 794 NO_RESUELTO
                         47 marcas = 3 simbolos distintos, los 3 comprobados
                         7 .c del ASIC + 115 cabeceras, 22697 identificadores
                         indice de 1408986 simbolos, con su causa declarada
verificacion manual       grep de los 3 simbolos marcados, uno a uno
                         gfx_v8_0.c:6209 usa mmVM_INVALIDATE_REQUEST, no el desnudo
suite del driver          22 + 12 + 195 = 229 checks, 0 fallos
crosscheck                10 vectores CLEAN
rx550pm4val               16/16
audit_citations           267 citas, 0 fallos
corpus                    MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
