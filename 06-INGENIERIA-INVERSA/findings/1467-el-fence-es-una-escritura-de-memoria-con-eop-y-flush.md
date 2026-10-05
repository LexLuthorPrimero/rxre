# 1467 — el fence queda nombrado y citado, y el hallazgo 1438 estaba equivocado en dos puntos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-FUENTE+CIERRE-DE-BLOQUEADO+REVISION-PROPIA
TRACK=STATIC(corpus) + lectura de blob · 0000:01:00.0 · Intel intacta · cero escrituras
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1438-*   (decia que el nombre del evento no aparecia)
         el bloqueado "fence mechanism package name unverified"
         06-INGENIERIA-INVERSA/findings/1466-*   (el blob correcto)
ESTADO=PROBADO · el fence es una ESCRITURA DE MEMORIA de un numero de secuencia, ordenada por
       un evento EOP con flush de cache.  No es un registro, no es el rptr
       · PACKET3_EVENT_WRITE_EOP (0x47) en el anillo GFX, PACKET3_RELEASE_MEM (0x49) en compute
       · EVENT_TYPE_CACHE_FLUSH_AND_INV_TS_EVENT = 0x14 | EVENT_INDEX(5)
       · cierra el bloqueado del mecanismo del fence
       · y REFUTA dos afirmaciones del 1438, una de ellas mia
```

## 1. Lo que el 1438 afirmaba, y por qué las dos son falsas

El 1438 cerró la frontera del fence con dos meridianos. **Las dos partes de la búsqueda
estaban mal**, y esta vez lo verifiqué yo antes de escribir nada:

```text
$ grep -rn 'CACHE_FLUSH_AND_INV_TS_EVENT' .
./include/asic_reg/gca/gfx_8_0_enum.h:5277:	CACHE_FLUSH_AND_INV_TS_EVENT = 0x14,
./include/soc24_enum.h:12857:             CACHE_FLUSH_AND_INV_TS_EVENT = 0x00000014,
./include/vega10_enum.h:15466:            CACHE_FLUSH_AND_INV_TS_EVENT = 0x00000014,
./amdgpu/sid.h:                           (lo USA, no lo define)
```

| afirmación del 1438 | veredicto |
|---|---|
| "`CACHE_FLUSH_AND_INV_TS_EVENT` not found where cited" | **falsa**: está en `include/asic_reg/gca/gfx_8_0_enum.h:5277`, dentro de `typedef enum VGT_EVENT_TYPE {` (`gfx_8_0_enum.h:5256-5318`) |
| "el `sid.h` de Mesa define `EVENT_TYPE_CACHE_FLUSH_AND_INV_TS_EVENT 0x14` y no está en el corpus" | **doble error**: (a) el símbolo se llama `CACHE_FLUSH_AND_INV_TS_EVENT`, no `EVENT_TYPE_...`; (b) **`amdgpu/sid.h` sí está en el corpus**, 792 líneas |

Y una fuente **más fuerte** que la que yo cité: el valor no está en un header de Mesa, sino
en **el enum de registros GFX8 de AMD**, concordante en tres ASIC distintos (soc24, vega10,
gfx_8_0). Mesa no lo define; el kernel sí.

### 1.1 El enum se explica solo

```c
/* include/asic_reg/gca/gfx_8_0_enum.h, dentro de VGT_EVENT_TYPE (:5256-5318) */
Reserved_0x00          = 0x0,
SAMPLE_STREAMOUTSTATS1 = 0x1,
...
CACHE_FLUSH_TS             = 0x4,     /* flush + timestamp            */
CONTEXT_DONE               = 0x5,
FLUSH_LS_OUTPUT            = 0x12,
Reserved_0x13              = 0x13,
CACHE_FLUSH_AND_INV_TS_EVENT = 0x14,   /* flush + invalidate + ts + evento */
ZPASS_DONE                 = 0x15,
CACHE_FLUSH_AND_INV_EVENT  = 0x16,
```

**El nombre del evento contiene su propia semántica:** flush de caché, *e invalidación*,
*timestamp*, *evento*. La parte `INV` es la que hace que un fence sea un fence y no una mera
escritura: obliga a que las cachés se despidan antes de que la escritura sea visible.

> **Esto no lo deduje yo: está escrito en la enumeración de AMD.** Es exactamente el tipo de
> evidencia que un nombre de macro bien elegido da gratis, y es la razón por la que buscar el
> valor en la fuente y no en la bibliografía era el camino correcto.

## 2. El mecanismo, en el código de la placa

`gfx_v8_0.c:6135-6152`, verbatim:

```c
static void gfx_v8_0_ring_emit_fence_gfx(struct amdgpu_ring *ring, u64 addr,
                                         u64 seq, unsigned flags)
{
        ...
        /* Workaround for cache flush problems. First send a dummy EOP
         * event down the pipe with seq one below.
         */
        amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
        amdgpu_ring_write(ring, (EOP_TCL1_ACTION_EN |
                                 EOP_TC_ACTION_EN |
                                 EOP_TC_WB_ACTION_EN |
                                 EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) |
                                 EVENT_INDEX(5)));
        amdgpu_ring_write(ring, addr & 0xfffffffc);
```

```text
macros   amdgpu/sid.h:490   #define EVENT_TYPE(x)   ((x) << 0)
         amdgpu/sid.h:491   #define EVENT_INDEX(x)  ((x) << 8)
         amdgpu/sid.h:336   #define PACKET3(op, n) ((RADEON_PACKET_TYPE3 << 30) | ...)
opcode   PACKET3_EVENT_WRITE_EOP = 0x47   amdgpu/sid.h:503
                           concordante en amdgpu/cikd.h:361 y amdgpu/nvd.h:352
```

**Los tres anillos:**

| anillo | paquete | site |
|---|---|---|
| GFX | `PACKET3_EVENT_WRITE_EOP` (0x47), dos veces: un dummy y el real | `gfx_v8_0.c:6135-6172` |
| compute | `PACKET3_RELEASE_MEM` (0x49), con el mismo dword de control | `gfx_v8_0.c:6231-6250` |
| KIQ | `PACKET3_WRITE_DATA` (0x37), 32 bits, confirmación de escritura | `gfx_v8_0.c:6252-6280` |

Dispatch: `.emit_fence = gfx_v8_0_ring_emit_fence_gfx` en `gfx_v8_0.c:6899`, compute `:6936`,
KIQ `:6967`.

**La compleción se observa por sondeo de esa misma memoria**, `gfx_v8_0.c:6174-6189`:
`PACKET3_WAIT_REG_MEM` con `MEM_SPACE(1)` `FUNCTION(3)` `ENGINE(usepfp)`, máscara
`0xffffffff`, contra la dirección del fence, comparando con `seq`.

### 2.1 El veredicto

> **El fence es una escritura atómica de 32/64 bits de un número de secuencia del driver a una
> dirección de fence, ordenada por un evento EOP con invalidación de L2/TCL1/TCC, con
> notificación opcional de escritura confirmada; la compleción se observa sondeando esa
> misma dirección con `PACKET3_WAIT_REG_MEM` contra el valor de secuencia.**
>
> Mecanismo y valor del tipo de evento: **`PROVEN`**, desde el código del driver.

Lo que **queda** `NOT_DETERMINED`: **qué emite exactamente el microcódigo del MEC.** Eso exige
la ISA del MEC, que es la frontera siguiente (§4).

## 3. La ISA del MEC: `NOT_DETERMINED`, con el negativo bien acotado

Dos negativos con método, que es lo que los hace valiosos:

1. **Test de posición de bit.** Sobre la región densa `0x100..0xBA38` (11 854 dwords),
   **ninguna posición de bit es constante ni casi constante**: el rango va de 0.0935 (bit 11)
   a 0.6264 (bit 31). No hay campo de opcode fijo, ni bits de alineación, ni campo libre. Un
   ISA de formato fijo con opcode de N bits tendría bits de relleno casi a cero.
2. **Test de cobertura (con control).** `capstone 5.0.7`, las **36** combinaciones de
   `CS_ARCH_*` × 16/32/64 bits × LE/BE sobre `0x100..0x1100` con `skipdata=True`. **Mejor
   resultado: 66.0 %** (m680x/16); **combinaciones que llegan a ≥90 %: 0.** El mismo test da
   resultados altos sobre **cualquier** blob, así que el método no discrimina: prueba que no
   hay decodificador local, no qué es.

Y el dato estructural que **sí** se puede registrar:

```text
jt_offset va en DWORDs        amdgpu_cgs.c:239     image_size = jt_offset << 2
instrucciones alineadas a 2    41 de 56 destinos de salto serian impares si fuesen bytes
```

**Y la tabla de saltos está localizada**, con las dos fórmulas del driver coincidiendo:

```text
polaris12_mec_2.bin  (el que corre, v. 1466)
  header_size=44  ip=8.0  ucode_version=0x2da  ucode_feature_version=49
  ucode_array_offset=0x100  ucode_size=262568  jt_offset=0x10005  jt_size=101

  amdgpu_cgs.c:239         jt = ucode_array_offset + (jt_offset << 2) = 256 + 262164 = 0x40114
  amdgpu_gfx.c:1450-1451   jt = ucode_size - jt_size*4              = 262568 - 404 = 262164

  0x40114 + 101*4 = 0x402A8 = fin de fichero.  EXACTO.
```

**Los últimos 404 bytes del fichero son la tabla de saltos**, y están inmediatamente después
de una **carrera de 17 306 dwords a cero** — la única carrera larga de la imagen.

### 3.1 Y un hecho estructural que no esperaba: el 55 % de la imagen es una alternancia

```text
0xBA38..0x2ED08 = 36020 dwords, de los cuales 36003 (99.95 %) son
                   alternancia estricta de  0x05980001  /  0x05540001
extremos: 0xBA38 .. 0x2ED04  ->  140.7 KiB sobre una imagen de 256.7 KiB
```

Es decir: **más de la mitad del microcódigo que el MEC ejecuta es un patrón de dos valores que
se alterna.** No tengo los bytes sin la semántica, y **no la voy a inventar**: significa
`NOT_DETERMINED`. Pero que sea el 55 % lo convierte en el mayor bloque sin explicar de la
imagen, y por tanto en la pregunta más grande que queda sobre este firmware.

## 4. Dos errores míos que casi invalidan este trabajo

Los dos estaban **en el encargo que le di al subagente**, y los dos habrían hecho que todo
saliera vacío sin dar error.

| # | lo que puse en el encargo | la realidad |
|---|---|---|
| 1 | "el payload empieza en `ucode_array_offset_bytes` = 448 = 0x1C0" | **`0x100` = 256**. Me había confundido con el firmware de MC |
| 2 | "una cabecera PM4 es `(count<<16)\|(type<<8)\|opcode`" | **layout pre-GCN.** En gfx8 es `(3<<30)\|(count<<16)\|(opcode<<8)`, con `type` en los bits [31:30] (`sid.h:336-338`) |

El segundo es el peligroso: **con mi fórmula, cualquier barrido de cabeceras PM4 encuentra
nada y no produce error.** Es la misma clase de fallo que el 1466: una suposición plausible
que anula el resultado entero sin avisar.

**Y un tercero mío, ya en la verificación:** comparé `ucode_size - jt_size*4` contra la
dirección **absoluta** de la tabla, que lleva la base del payload sumada, y concluí que las
dos fórmulas **no** coincidían. Coinciden: `262164` en ambas. Resté mal.

## 5. Procedencia

```text
fuente   include/asic_reg/gca/gfx_8_0_enum.h:5256-5318   VGT_EVENT_TYPE, 0x14 en :5277
         include/soc24_enum.h:12857  include/vega10_enum.h:15466   mismo valor, 3 ASIC
         amdgpu/sid.h:336  PACKET3()  :490-491 EVENT_TYPE/EVENT_INDEX  :503 opcode 0x47
         amdgpu/cikd.h:361  amdgpu/nvd.h:352   0x47 concordante
         amdgpu/gfx_v8_0.c:6135-6172  :6174-6189  :6231-6250  :6252-6280  :6899/:6936/:6967
         amdgpu/amdgpu_cgs.c:239      jt_offset en dwords
         amdgpu/amdgpu_gfx.c:1450-1451  la segunda formula de la tabla de saltos
         amdgpu/amdgpu_ucode.h:181-186  gfx_firmware_header_v1_0: feat@32, jt_off@36, jt_size@40
blob     /tmp/opencode/fw/mec_2.bin = /lib/firmware/amdgpu/polaris12_mec_2.bin.xz
         262824 B  sha256 1e0ce977d292…  ucode_version 0x2da  (v. 1466: este es el que corre)
```

```text
ESTADO=PROBADO · el fence es una escritura de memoria de un numero de secuencia, ordenada por un
       evento EOP con flush+invalidacion de cache; la complecion se sondea con WAIT_REG_MEM
CIERRA BLOQUEADO  "fence mechanism package name unverified" -> CERRADO, con file:line
REVISION PROPIA  el 1438 decia que el simbolo no aparecia y que sid.h no estaba en el corpus.
       Las dos son falsas.  El valor 0x14 esta en gfx_8_0_enum.h:5277, en el enum de registros
       de AMD, concordante en tres ASIC.  Y amdgpu/sid.h SI esta (792 lineas)
DECISION DE FUENTE  antes se cita Mesa; la fuente correcta es el enum de registros del propio
       ASIC.  Tres ASIC independientes coinciden en 0x14
PROBADO  la tabla de saltos del MEC esta en los ultimos 404 bytes, con las dos formulas del
       driver coincidiendo exactamente, y precedida por una carrera de 17306 ceros
PROBADO NEGATIVO  la ISA del MEC es NOT_DETERMINED: ninguna posicion de bit es casi constante
       en 11854 dwords, y 0 de 36 combinaciones de capstone llegan a 90 %.  Con control: el
       mismo metodo da puntuaciones altas sobre cualquier blob, asi que acota, no identifica
NUEVO, SIN EXPLICAR  el 55 % del microcodigo del MEC (140.7 KiB) es una alternancia estricta
       de 0x05980001 / 0x05540001.  Es el mayor bloque sin explicar de la imagen
NOT_DETERMINED  que PM4 emite realmente el MEC: solo se alcanzo la categoria (a), coincidencias
       de bytes con constantes conocidas.  La categoria (b), atribucion a instrucciones, exige la ISA
MIS ERRORES  dos, ambos en el encargo al subagente: el offset del payload (448 en vez de 256) y
       la formula de cabecera PM4 (layout pre-GCN, que con mi formula anula todo el barrido
       sin dar error).  Y uno en la verificacion: compare un offset relativo con uno absoluto
RIESGO  ninguno.  CERO escrituras.  El GPU no se toco
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, card0 control=auto runtime=active, un /dev/fb0
Siguiente  1) la alternancia de 140.7 KiB: es la pregunta mas grande que queda sobre este
           firmware, y es un bloque de datos, no de codigo, asi que se puede atacar sin la ISA
         2) la ISA: hace falta un corpus de microcodigo GFX8 decodificado, que no esta en el
           arbol.  Sin el, la frontera es SATURATED con motivo legitimo
```

## 6. La regla del hallazgo

**Un bloqueado de este proyecto estaba mal cerrado, y la causa fue no buscar el símbolo en la
fuente de la propia familia de hardware.** El valor estaba en un enum de registros de AMD
concordante en tres ASIC, y yo había citado a un header de Mesa que ni siquiera contiene el
símbolo con ese nombre. **Tres veces en esta sesión que el proyecto escribe "no lo sé" y era
"no lo miré en el sitio correcto"**: `SBAR` en `CROSSBAR`, `pp_dpm_mclk` en debugfs, y ahora
esto. La respuesta no es buscar más rápido: es **no declarar ausencia antes de haber leído el
enum del ASIC**.