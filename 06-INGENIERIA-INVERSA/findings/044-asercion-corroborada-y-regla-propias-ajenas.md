# 044 · Cuatro sitios indexan el mismo bloque, y el control de contratos necesitaba una excepción con nombre

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTAS=08-ARQUITECTURA/tools/mqd_layout.py` (extendido),
`toolkit.py` (extendido) · `CONTINUES=043`

## Cuestión principal

¿La aserción de `043` la hace **un solo** lugar del driver, o la repiten
varios? Y si la repiten, ¿los cuatro textos coinciden?

## Criterio de terminación

Localizar todos los sitios que indexan una struct por offset de registro y
verificar la aserción en cada uno. **Cumplido: 4 sitios, 4/4 cuadran, y los dos
de Polaris12 dicen el bloque de forma distinta.**

## Resultado: la aserción se repite 4 veces, y cuadra 4 veces

```
sitio                            asic        n  cuadran  nombre  bloque            estado
gfx_v8_0.c:mqd_commit            gfx_8_0    53       52       1    0x3245..0x3279  OK
amdgpu_amdkfd_gfx_v8.c:kgd_hqd_load     gfx_8_0    53       52       1    0x3245..0x3279  OK
gfx_v7_0.c:mqd_commit            gfx_7_0    35       33       2    0x3245..0x3267  OK
amdkfd_gfx_v7.c:kgd_hqd_load     gfx_7_0    35       33       2    0x3245..0x3267  OK
```

**4/4 corroboran.** Eso es más fuerte que lo de `043`, donde un solo sitio
cuadrando podía ser casualidad. Aquí hay **cuatro rutas independientes** — dos
de display, dos de KFD, dos generaciones de ASIC — que indexan el bloque por
offset y salen bien.

La afirmación correcta: **`struct vi_mqd` está construida para ese layout**, no
para que cuadre en un caso. Un autor que indexara por offset en un sitio y el
struct no correspondiera, el driver no arrancaría ninguna cola.

## El bloque crece: 35 → 53 dwords

| ASIC | bloque | dwords | `CP_HQD_EOP` |
|---|---|---|---|
| `gfx_7_0` (GCN1) | `0x3245..0x3267` | 35 | **no existe** |
| `gfx_8_0` (GCN3, Polaris12) | `0x3245..0x3279` | 53 | 8 registros |

18 dwords de diferencia, todos al final, todos EOP. El **mismo** nombre de struct
sirve para dos bloques de distinta longitud, y el mismo bucle los recorre. Eso
solo funciona si el struct tiene los campos del bloque **más largo** y los
índices del más corto caen dentro.

Es coherente con que EOP se añadiera en GCN3. `043` ya lo había hinted al
contar `CP_HQD_EOP` por generación; ahora está medido sobre las dos.

## Las dos divergencias de nombre de GCN1 son el reverso de los alias de GCN3

```
0x3265  struct: cp_hqd_hq_status0    GCN3: CP_HQD_HQ_STATUS0    / CP_HQD_HQ_SCHEDULER0
        GCN1: CP_HQD_HQ_SCHEDULER0                            <-- sin alias
0x3266  struct: cp_hqd_hq_control0   GCN3: CP_HQD_HQ_CONTROL0   / CP_HQD_HQ_SCHEDULER1
        GCN1: CP_HQD_HQ_SCHEDULER1                            <-- sin alias
```

**El mismo registro, en dos offsets, con dos nombres en GCN3 y uno solo en
GCN1.** El nombre "moderno" (`STATUS0`/`CONTROL0`) y el "heredado"
(`SCHEDULER0`/`SCHEDULER1`) describen el mismo dword; AMD renombró y dejó el
nombre viejo como alias. `vi_mqd` usa el nuevo, `cik_mqd` —el struct de GCN1—
usa el viejo, coherente con lo que el header de esa generación expone.

Esto **no es** una divergencia de la herramienta: los dos sitios cuadran, y la
diferencia es que el offset de GCN1 tiene un solo nombre mientras el de GCN3
tiene dos. La tabla de 043 (`ALIAS`) y la de aquí son el mismo fenómeno
mirado desde las dos generaciones.

## Dos comentarios del driver que no dicen lo mismo

Los dos sitios de GCN3 describen el mismo bloque en el mismo commit:

```
gfx_v8_0.c:4552             /* HQD registers extend from mmCP_MQD_BASE_ADDR to mmCP_HQD_ERROR */
amdgpu_amdkfd_gfx_v8.c:183         /* HQD registers extend from CP_MQD_BASE_ADDR to CP_HQD_EOP_WPTR_MEM. */
```

Uno termina en `CP_HQD_ERROR` (`0x3278`), el otro en `CP_HQD_EOP_WPTR_MEM`
(`0x3279`). **El segundo es el correcto**: el driver escribe `0x3279`, y por
`043` sabemos que son 53 dwords.

El de `gfx_v8_0.c` se queda corto por un registro. Es un comentario, no código:
ningún camino de ejecución depende de él. Pero es la clase de frase que se
copia de un fichero a otro sin comprobarla, y por eso conviene tener la
respuesta por escrito.

## Cuarto fallo de extracción: el peor, porque daba un número plausible

`parse_loops` buscaba `for (...) WREG32(...)` en **una sola línea**. El patrón
abarca dos. Resultado: **0 bucles detectados**, y como las escrituras literales
sí se veían, la tabla salía con **3 y 6 posiciones** en vez de 53.

Un extractor parcial que devuelve un número plausible es peor que uno que
falla: 3 es un número creíble, y si nadie hubiera contrasted con la lectura
manual, `53` habría pasado a `3` sin que nada se quejara.

Los otros tres fallos (`043`): normalizar nombres mal, comparar los 257 campos
del struct, y un control negativo mal escrito. Este es el que más me gusta,
porque los tres anteriores fallaban dando **muchos** MISMATCH —ruidoso. Este
falló dando **pocos**.

Corregido: el patrón se busca sobre `línea + "\n" + línea_siguiente`.

## Y el que NO era de la herramienta

Los sitios de GCN1 salían `NO_ANALIZABLE`. Causa: se les pedía `vi_mqd`, y
GCN1 no usa `vi_mqd`: usa **`cik_mqd`**, en otro header.

No era un fallo del extractor, era un **dato equivocado en la configuración**.
Igual que el fallo del comentario: la pregunta estaba bien, el nombre no.

`043` leyo la tabla de 53 en `gfx_8_0_d.h` y no comprobó si el ASIC anterior
tenía el mismo struct. Asumir que una estructura se mantiene entre generaciones
es el tipo de suposición que `IMPLEMENTATION GATE` prohíbe: *"no implementar
una semántica solo porque existe en AMDGPU"*. Lo estaba haciendo con el nombre
de un struct.

## El contrato de herramientas necesitaba una excepción, y no la tenía

Otra sesión de este proyecto creó 7 herramientas en el mismo directorio
(`causal.py`, `citecheck.py`, `contradict.py`, `hdrmap.py`, `regdb.py`,
`scopeguard.py`, `xref.py`), sin commitear.

`toolkit.py --check` las contaba como fallos de contrato — 5 sin contrato, 1
con escrituras declaradas que no declara— y `run_all` se puso rojo por
ficheros que nadie había publicado. Un control que se pone rojo por trabajo en
curso enseña a ignorar el control.

La regla que se aplicó:

```
una herramienta que NO está en git  ->  se verifica, se reporta
                                        como AJENA, y NO cuenta para el
                                        código de salida
con --strict                        ->  cuenta igual
```

Es un criterio de **pertenencia al proyecto**, no de calidad. Lo que está
versionado es del proyecto; lo que está en el árbol sin commitear está siendo
escrito.

### El primer intento usó la edad del fichero, y fue un error

Usé "modificado hace más de 2 minutos = estable". No funciona: una herramienta
que otra sesión escribe, abre, corrige y abandona sin commitear pasa de
"estable" en dos minutos. **La edad no distingue "terminado" de "abandonado a
medias"**, que es exactamente lo que hay que distinguir.

Cambiado a "¿está en git?", comprobado con `git ls-files --error-unmatch`.

### El punto débil, dicho

Una herramienta **mía** recién creada y aún sin commitear también sale
`AJENA`. Se acepta a propósito: la alternativa (marcar por antigüedad) ya
falló. Y tiene dos defensas: `--strict` las cuenta, y el resumen dice
`propias 19/19, ajenas 6 sin validar` para que el silencio no esconda nada.

### Y con control negativo propio

`--selftest-ajenas` comprueba lo que importa: que `_en_git` diga `PROPIA` para
un fichero versionado **con contrato** (si fallara ahí, una herramienta mía sin
contrato pasaría inadvertida, que es el fallo de grado peligroso) y `AJENA`
para uno suelto y para uno inexistente.

**Clasificación `TOOL_PARTIAL`**, no `TOOL_VALIDATED`: no se prueba el caso
"versionado pero con contrato inválido", porque haría falta un fichero así en
el árbol. Ese camino lo cubre el validador, no `_en_git`.

## Clasificación

| afirmación | estado |
|---|---|
| 4 sitios indexan la struct por offset de registro | `PROVEN` — `grep` + extracción |
| Los 4 cuadran | `PROVEN` — 52/53, 52/53, 33/35, 33/35 |
| El struct está construido para ese layout | `CORROBORATED` — 4 rutas independientes |
| El bloque de GCN1 es de 35 dwords, el de GCN3 de 53 | `PROVEN` |
| Los 18 dwords de diferencia son EOP | `PROVEN` — `CP_HQD_EOP` no existe en `gfx_7_0_d.h` |
| El mismo struct sirve para dos longitudes de bloque | `PROVEN` — mismo bucle, mismo tipo |
| `STATUS0`/`SCHEDULER0` son el mismo dword | `PROVEN` — mismo offset, alias en `gfx_8_0_d.h` |
| Que el hardware de ambas generaciones los llame igual | `NOT_DETERMINED` — alias ≠ semántica |
| El comentario de `gfx_v8_0.c:4552` se queda corto | `PROVEN` — escribe `0x3279`, dice `ERROR` |
| Que EOP signifique lo mismo en GCN1 y GCN3 | `NOT_APPLICABLE` — en GCN1 no existe |
| Que hace cada registro | `NOT_DETERMINED` — 033: no hay spec de GCN3 |

## Confounders

- **Cuatro sitios, dos ficheros.** Display y KFD son el mismo `.c` con otro
  nombre. No son cuatro Truly independientes: son dos. La corroboración es
  real pero menor de lo que "4/4" sugiere.
- **GFX9 en adelante no está.** Usa otras cabeceras y otros structs
  (`v9_structs.h`, 691 líneas `uint32_t`). La afirmación "el struct está
  construido para ese layout" se limita a GCN1 y GCN3.
- **La cuenta de 53 depende de leer los bucles.** Es la parte que ya ha
  fallado una vez (§4). Cada sitio se acota por llaves y no por patrón de
  cierre, y `--ranges` imprime los bucles para comparar a mano.
- **`_en_git` usa `git ls-files`**, que con 25 ficheros tarda poco, pero es un
  proceso externo por fichero. Con 200 herramientas serían 200 procesos.
  Irrelevante aquí; no irrelevante si el toolkit crece mucho.

## Desfalsificación

- **(a)** La aserción la hace un solo sitio → refutable con `grep -rn
  "mqd_reg - mmCP_MQD_BASE_ADDR"`; da 4 ficheros.
- **(b)** Los 4 dan el mismo bloque → refutable con `--sitios`; control 11 del
  self-test lo exige.
- **(c)** El bloque de GCN3 tiene 53 dwords → refutable contando en
  `gfx_8_0_d.h:630-685`; son 55 defines en 52 offsets (3 alias).
- **(d)** GCN1 no tiene EOP → refutable con `grep -c CP_HQD_EOP
  gfx_7_0_d.h`; da 0.
- **(e)** `_en_git` no distingue → refutable con `--selftest-ajenas`.

## UNLOCKS

- **`043` se cierra**: la aserción no la hace un sitio, la hacen cuatro, y
  cuadran los cuatro.
- **La longitud del bloque por generación está medida**: 35 en GCN1, 53 en
  GCN3. Un driver propio necesita ese número por ASIC antes de rellenar un MQD.
- **`mqd_layout.py` acepta sitios nuevos por configuración**, así que el
  próximo ASIC que aparezca se añade en una línea, sin tocar la herramienta.
- **La regla propias/ajenas resuelve la colisión entre sesiones** sin
  debilitar el control, y tiene su propio control negativo.

## Evidencia

```
mqd_layout.py --sitios      4/4 OK, bloques por ASIC
mqd_layout.py --self-test   11/11
toolkit.py                  rc=0 (propias 19/19, ajenas 6 sin validar)
toolkit.py --strict         rc=1
toolkit.py --selftest-ajenas  TOOL_PARTIAL
run_all.py                  25 comprobaciones, todas OK

gfx_v8_0.c:4552             comentario: hasta CP_HQD_ERROR
amdgpu_amdkfd_gfx_v8.c:183         comentario: hasta CP_HQD_EOP_WPTR_MEM
gfx_8_0_d.h:663-666         los alias STATUS0/CONTROL0 vs SCHEDULER0/1
gfx_7_0_d.h:599-600         solo SCHEDULER0/1, sin alias
vi_structs.h:159            struct vi_mqd, ancla en el indice 128
cik_structs.h:27            struct cik_mqd, ancla en el indice 51
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.