# R2-PM4OPS — el decodificador PM4 llama PREAMBLE_BEGIN a dos paquetes que las fuentes llaman COPY_DATA y CP_DMA

<!-- MEDIDO con tools/pm4ops.py. Artefacto: pm4ops.json.
     Regenerar: python3 tools/pm4ops.py --json > 08-ARQUITECTURA/artifacts/R2-PM4OPS/pm4ops.json -->

```
AGENCIA=RX550-INVESTIGACION · AGENT RE/TOOLING
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=NO · sin sudo · sin ejecucion · GPU=INTACTA
escritura=3 ficheros NUEVOS.  Ningun fichero existente modificado.
herramienta   tools/pm4ops.py 1.0.0
sha256        239d76e093bc1d1e
artefacto     08-ARQUITECTURA/artifacts/R2-PM4OPS/pm4ops.json
sha256        ad82371502e8b241
reproducible  d04c09134cfcc5095ed3666f5528b8c03b3a654ad4f44d7942c0406709be2b48
selftest      32 vectores, 0 fallos, rc=0   (HERMETICO: verificado en copia aislada y otro cwd)
```

## 0 bis · EL ERROR DE MÉTODO QUE ESTA HERRAMIENTA TENÍA

Esto va primero porque cambia cómo se lee todo lo demás.

La primera versión de `pm4ops` votaba por mayoría entre los seis headers. Al
aplicarla al target, la pregunta que sale es: **¿compila GFX8 esos seis
headers?** MEDIDO por cierre de `#include` desde `gfx_v8_0.c` — el driver de la
generación del ASIC:

| header | ¿lo compila `gfx_v8_0.c`? |
|---|---|
| **`vid.h`** | **sí** |
| `sid.h` | no |
| `cikd.h` | no |
| `nvd.h` | no |
| `soc15d.h` | no |
| `gfx_v12_1_pkt.h` | no |

**Cinco de las seis fuentes no son alcanzables desde el driver de esta
generacion**, en el corpus de este proyecto. Y el esquema `_pkt.h`, que es el
de `gfx_v12_1_pkt.h`, lo usan `gfx_v12_1.c`, `mes_v11_0.c` y `mes_v12_0.c`:
NAVI 12.1, no GFX8. `gfx_v8_0.c` incluye `vi.h`, `vi_structs.h` y `vid.h`, y
ningun `_pkt.h`.

### Y el limite se MIDIO dos veces, porque la primera medicion estaba mal

**La primera version resolvia el include en UN solo directorio**, el del propio
driver.  Dio 29 cabeceras "rotas".  MEDIDO que NO lo estaban:

```
$ find . -name amdgpu_dpm.h -not -path "./.git/*"
./RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/pm/inc/amdgpu_dpm.h
./RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/inc/amdgpu_dpm.h
./RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/pm/inc/amdgpu_dpm.h
./rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/pm/inc/amdgpu_dpm.h
```

Un include con comillas se busca en la **ruta de inclusion**, no en el directorio
desde el que se escribe.  El Makefile pone en la ruta `drivers/gpu/drm/amd/include/`
y `drivers/gpu/drm/amd/pm/inc/`, y `gfx_v8_0.c` esta en `amd/amdgpu/`.

**Resolver en un solo sitio no es aproximar: es resolver mal.** Y resolver mal
aqui era peor que no resolver, porque producia 29 roturas falsas y hacia que el
veredicto pareciera mucho menos firme de lo que es -- es decir, una limitacion
falsa de mi herramienta, que es justo la clase de defecto que este trabajo
denuncia en los demas.

Corregido: las raices de include se **DESCUBREN** (todo directorio bajo `amd/`
con al menos un `.h`: 331), no se declaran.  Y el vector `RAIZ_1` falla si
alguien vuelve a resolver en un solo directorio.

| medicion | ficheros en el cierre | includes rotos |
|---|---|---|
| un solo directorio | 86 | **29** (falsos) |
| raices de include reales | **141** | **1** |

La unica rotura que queda es `amdgpu_dal_power_if.h`, incluida por
`amdgpu_dm.h`: la cadena del DAL, que es otro subsistema.

Por tanto, con el estado actual del saber:

| afirmacion | estado |
|---|---|
| `gfx_v8_0.c` de este corpus no alcanza a esos cinco headers | **OBSERVADO** |
| el driver del kernel que compila el modulo tampoco los alcanza | **NOT_DETERMINED** |

**La segunda es la que responderia la pregunta, y no se puede cerrar con lo que
hay.** Por eso `pm4ops` imprime los includes rotos ANTES que los veredictos y
declara `alcance_integro: false`. Un alcance sin su lista de roturas se lee como
completo, y convertiria en PROVEN lo que es NOT_DETERMINED.

Contarlas como votos iguales es exactamente el error que la herramienta existe
para evitar — *"una mayoría puede estar mal cuando la generación correcta es la
minoría"* — y aquí la minoría es **una de seis y además es la única que aplica**.

Por eso el veredicto se emite dos veces y no se sustituye uno por otro: son dos
preguntas distintas, y contestar una sola es ocultar cuál se contesta.

**Y el hallazgo de `0x59` sobrevive al método correcto**, que es lo que había que
comprobar. Con el consenso de los seis, la evidencia era «5 headers contra 1».
Con el método correcto la evidencia es más fuerte y más simple:

```
$ grep -E "^[[:space:]]*#[[:space:]]*define[[:space:]]+PACKET3_[A-Z0-9_]+[[:space:]]+0x49\b" vid.h
#define PACKET3_RELEASE_MEM   0x49
$ ... 0x59 ...
#define PACKET3_REWIND        0x59
```

**El único header que GFX8 compila dice `0x49` para `RELEASE_MEM` y `0x59` para
`REWIND`.** No hay mayoría, no hay nada que omitir. Es una lectura directa de la fuente
que aplica.

### El veredicto completo, por generación

| opcode | `vid.h` (la que aplica) | `pm4decode.c` | veredicto |
|---|---|---|---|
| `0x40` | `COPY_DATA` | `PREAMBLE_BEGIN` | **TRUNCADO_NO_OPCODE** |
| `0x41` | — | `PREAMBLE_END` | **TRUNCADO_NO_OPCODE** |
| `0x49` | `RELEASE_MEM` | *(sin nombre)* | — |
| `0x59` | `REWIND` | `RELEASE_MEM` | **DISIDENTE** |
| `0xc0` | — | `CONTROL_SWITCH` | **FUERA_DE_FUENTES** |

## 0 · DE DONDE SALIO LA PREGUNTA

Cuatro decodificadores de PM4, cuatro tablas de opcode independientes, y
**nadie las había comparado nunca**. El proyecto tiene la Materia Prima para
detectarlo y no la usa: `revkit/pm4dec.py` yaestablished, con medicion, que

> la numeración de opcodes NO es estable entre generaciones de ASIC

y que `sid.h` está desplazado una posición en la familia `LOAD_*`, con cinco
headers contra uno. Y el propio `tools/pm4decode.c` avisa en su cabecera:

> la primera versión de esta tabla estaba hecha de memoria y tenía SIETE
> entradas equivocadas. Lo encontró el test, no la lectura
> un nombre equivocado en un diagnóstico es peor que un número

La tabla se corrigió una vez. Lo que no existía era la puerta que hiciera que
la **siguiente** se notara sin un test escrito a mano. Eso es lo que este
trabajo construye, y al construirlo encontró tres entradas más.

## 1 · LAS FUENTES, Y SU IDENTIDAD

Seis headers, y se **comprueba** que las tres copias del árbol son byte-idénticas
en vez de suponerlo:

| header | sha256[:16] | definiciones |
|---|---|---|
| `sid.h` | `dd03da7ad3a67f92` | 80 |
| `vid.h` | `4b42454a90a714c4` | 78 |
| `cikd.h` | `3a3940dd1753918a` | 74 |
| `nvd.h` | `0a4de0b61f8be33d` | 128 |
| `soc15d.h` | `f39adef602b90ac3` | 78 |
| `gfx_v12_1_pkt.h` | `28761ba492b815ed` | 71 |

**135 opcodes, 145 nombres.** La lista de headers no se inventa: es la de
`revkit/pm4dec.py`, que la auditó y la corrigió con `tools/rx550ref --sym` de
otra sesión. Se declara aquí y además se contrasta contra aquel fichero.

### 1.1 · Cuatro disidencias ENTRE LOS PROPIOS HEADERS

Esto **no es un defecto del proyecto**: es una propiedad de las fuentes. Se
emite aparte y con su nombre, porque un decodificador de un solo header hereda
el desplazamiento sin saberlo.

| nombre | mayoría | disidente |
|---|---|---|
| `LOAD_SH_REG` | `0x5f` (5 headers) | `0x61` segun `sid.h` |
| `LOAD_CONFIG_REG` | `0x60` (5 headers) | `0x5f` segun `sid.h` |
| `LOAD_CONTEXT_REG` | `0x61` (5 headers) | `0x60` segun `sid.h` |
| `INDIRECT_BUFFER_CONST` | `0x33` (3 headers) | `0x31` segun `sid.h` |

En las cuatro, `sid.h` es el disidente. **Esto ya estaba medido en el proyecto**
y este trabajo lo re-deriva, no lo descubre.

---

## R2-01 · `0x40` y `0x41`: NOMBRES QUE NO PUEDEN SER CORRECTOS

`tools/pm4decode.c:293-294`:

```c
/* vid.h: no están en sid.h */
case 0x40: return "PREAMBLE_BEGIN";
case 0x41: return "PREAMBLE_END";
```

Medido:

| opcode | qué pone el decoder | qué ponen las fuentes | cuántos headers |
|---|---|---|---|
| `0x40` | `PREAMBLE_BEGIN` | **`COPY_DATA`** | **6 de 6** |
| `0x41` | `PREAMBLE_END` | **`CP_DMA`** | 2 (`sid.h`, `nvd.h`) |

No es una disputa de mayoría. Es que **`0x40` y `0x41` sí tienen nombre en los
headers, y es otro**. Un IB con `COPY_DATA` se decodifica como `PREAMBLE_BEGIN`.

### Y el nombre no existe como opcode

No hay macro `PACKET3_PREAMBLE_BEGIN`. Lo más parecido es
`PACKET3_PREAMBLE_BEGIN_CLEAR_STATE`, y su valor es **`(2 << 28)`**: una
cabecera de 32 bits con otra codificación, **no un opcode de un byte**. Y está
**comentada** en los cuatro headers donde aparece, con la forma
`#              define …` y sin `#if` que la cubra.

Que el nombre del decoder venga de ahí es una **HIPOTESIS**, y se emite marcada
como tal. Lo que **no** es hipótesis: que `0x40` es `COPY_DATA` y que
`(2 << 28)` no es un opcode de byte.

### Y hay una third cosa, medida en el CÓDIGO del driver

`amdgpu_gfx.c:2493` escribe el paquete que el driver de verdad emite:

```c
buffer[count++] = cpu_to_le32(PACKET3_PREAMBLE_BEGIN_CLEAR_STATE);
```

Esa palabra es `0x20000000`. Decodificada como cabecera PACKET3 da
**`type=0`, `opcode=0x00`** — es un TYPE0, no un TYPE3. Y `pm4decode.c:311`
solo nombra cuando `PM4_HDR_TYPE(buf[i]) == PM4_TYPE3`.

**Es decir: el paquete al que el nombre `PREAMBLE_BEGIN` se refiere no puede
entrar nunca por la rama que lo imprime.** El nombre está en un opcode de byte
que el decoder sí ve, y ese opcode es otro paquete. El enlace es
estructuralmente imposible, no una opinión sobre cuál valor es el bueno.

## R2-02 · `0x59`: `RELEASE_MEM` con el valor equivocado

| opcode | decoder | mayoría de fuentes |
|---|---|---|
| `0x49` | *(sin nombre)* | **`RELEASE_MEM`** — 5 headers |
| `0x59` | `RELEASE_MEM` | **`REWIND`** — 4 headers |

`pm4decode.c` asigna `RELEASE_MEM` a `0x59` cuando vale `0x49`, y `0x59` es
`REWIND`, que es otro paquete. Un IB con `REWIND` sale como `RELEASE_MEM`.

## R2-03 · LA ZONA SILENCIOSA: 117 de 135

`pm4decode.c` nombra 16 de los 135 opcodes que las fuentes nombran. Los otros
**117 salen sin nombre**, y `pm4_volcar()` **no dice que no los sepa**:

```c
if (PM4_HDR_TYPE(buf[i]) == PM4_TYPE3 && n)
        fprintf(f, "  %s%s count=%u", n, …);
fputc('\n', f);
```

La línea de un opcode no nominado es **idéntica** a la de un paquete que
realmente no tiene nombre. `NOT_FOUND` presentado como ausencia. El 87 % del
espacio de opcodes es indistinguible de "aquí no hay nada".

---

## R2-04 · LA CONTAMINACIÓN ES LATENTE, Y ESTO ES LO QUE LA HACE ACCIONABLE

Los defectos de `pm4decode.c` importan solo si algo se decodificó con él. Se
comprobó, y la respuesta cierra el hallazgo por los dos lados:

**Los hallazgos que usan `RELEASE_MEM` son CORRECTOS.** `013-real-submit-path`
y `BARRERAS-GFX8.md` citan `gfx_v8_0.c:6239`, y ahí está:

```c
/* RELEASE_MEM - flush caches, send int */
amdgpu_ring_write(ring, PACKET3(PACKET3_RELEASE_MEM, 5));
```

`vid.h` —el header que GFX8 compila— dice `PACKET3_RELEASE_MEM = 0x49`. Los
hallazgos usan la macro del driver, que resuelve a `0x49`. **No están
contaminados.**

**Y no hay IB decodificado en el proyecto.** Se buscó en `revkit/capturas/`,
en `03-EXPERIMENTOS/` y por forma en todo el árbol: no hay ninguna secuencia de
dwords de anillo. Así que ningún artefacto publicado lleva el nombre equivocado.

Por eso la prioridad es exactamente la que es: `pm4decode.c` hay que
arreglarlo **antes** de que alguien decodifique un IB con él, no después de
que uno se haya decodificado mal. Es un riesgo con fecha de vencimiento, y
decirlo asi es mas util que presentarlo como una alarma.

## R2-05 · RESULTADO NEGATIVO: LA EXPOSICIÓN DE `sid.h` ES CERO

Las cuatro disidencias entre headers son reales. La pregunta que faltaba era si
**el driver del proyecto usa alguno de esos cuatro nombres**:

```
$ grep -rnE "PACKET3_(LOAD_SH_REG|LOAD_CONFIG_REG|LOAD_CONTEXT_REG|
             INDIRECT_BUFFER_CONST)" 04-IMPLEMENTACION/rx550-driver/
  (vacio)
```

**No usa ninguno.** Los valores, confirmados:

| nombre | `vid.h` | `sid.h` |
|---|---|---|
| `LOAD_SH_REG` | `0x5F` | `0x61` |
| `LOAD_CONFIG_REG` | `0x60` | `0x5F` |
| `LOAD_CONTEXT_REG` | `0x61` | `0x60` |
| `INDIRECT_BUFFER_CONST` | `0x33` | `0x31` |

Un riesgo que estaba abierto y que nadie había medido, cerrado con un número.
Un resultado negativo es informacion: dice que NO hay que dedicarle atencion.

## R2-06 · RESULTADO NEGATIVO: LA CLASE DE TABLAS ES AGOTADA

Antes de dar por buena la clase «tabla escrita a mano sin contrastar», se
buscó en los siete directorios declarados con dos formas:

| forma | umbral | instancias |
|---|---|---|
| pares `(nombre, hex)` densos | ≥6 | **2** — `amdmmr.c`, `rx550pm4val.c` |
| `#define NOMBRE 0xVALOR` | ≥5 | **2** — `rx550pm4val.c`, `regtable_audit.py` |

Cuatro instancias, las cuatro del dominio PM4/registro. **La clase está
agotada en este árbol**: no hay una quinta tabla escondida, y eso se sabe con
un número y no con una impresión.

- **No se corrige ninguna tabla.** `tools/pm4decode.c` y `revkit/pm4dec.py` son
  de otra sesión. Este fichero mide y dice.
- **No se decide cuál opcode es el bueno para GFX8.** Eso es semántica del
  agente principal: la generación del ASIC no está en una tabla de opcodes, y
  una mayoría de headers puede ser la minoritaria correcta.
- **El origen de los nombres `PREAMBLE_BEGIN`/`PREAMBLE_END` es HIPÓTESIS.**
  Lo que es dato es que no existen como opcode de byte y que `0x40`/`0x41` tienen
  otro nombre.
- **Los otros dos decodificadores no se critican.** `revkit/pm4dec.py` y
  `pm4_codec.py` derivan la tabla de los headers en tiempo de ejecución:
  estáticamente no hay tabla que extraer y la herramienta lo dice
  (`DERIVADA_de_headers`) en vez de devolver una lista vacía que parecería "no
  define ninguno". Un decodificador derivado de las fuentes no puede discrepar
  de ellas por su tabla; puede discrepar por **qué** headers elige, que es otra
  pregunta.
- **Análisis estático.** No se decodificó ningún IB real.

---

## 4 · LO QUE ESTO PERMITE Y NO PERMITÍA ANTES

`python3 tools/pm4ops.py --opcode 0x40` responde, por opcode, qué dicen las
fuentes y qué dice cada decodificador, con los headers que lo contradicen
nombrados uno a uno. Antes eso exigía abrir seis cabeceras y cuatro
decodificadores y comparar a ojo — que es exactamente la operación que nadie
hace.

Y la cobertura sale como número: **16/135**. Eso no es un detalle de una
herramienta, es un límite del volumcado de IB del proyecto, y no estaba
escrito en ninguna parte.

```
ESTADO
  ficheros escritos   3, todos nuevos
  ficheros modificados 0
  GPU                 INTACTA
  sudo                NO usado
  IB real decodificado NINGUNO
  commits             NINGUNO
```