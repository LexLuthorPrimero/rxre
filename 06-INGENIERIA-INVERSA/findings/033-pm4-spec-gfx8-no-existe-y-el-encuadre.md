# 033 · La especificación PM4 de GFX8 no existe: resultado negativo, y el encuadre por fin medido

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC+CORPUS_EXTERNAL` · `CORPUS=linux-7.1.3 + fuentes`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`RESOLVES=el BLOCKED de 022/023/029` · `CONTINUES=023-pm4-count-convencion-medida.md`
`COMPLEMENTS=031`, `032`

## CUDA principal

Dos cosas, y la segunda es la que vale.

**1.** La especificación primaria de GFX8 **existe, es accesible, tiene 637 páginas, y no
contiene absolutamente nada de PM4.** Lo he contado, no lo he supuesto: cero apariciones
de `PACKET3`, `PKT3`, `RELEASE_MEM`, `COND_EXEC`, `VM_INVALIDATE`, `INT_SEL`,
`WRITE_AT`, `GRBM`, `mmCP`. El `BLOCKED` que arrastraban `022`, `023` y `029` no es
"no hemos encontrado la fuente": es que **AMD nunca publicó la especificación del
framing PM4 para GCN3**. Deja de ser una búsqueda pendiente y pasa a ser un
`NEGATIVE_RESULT` con su causa identificada.

**2.** Aun así, la estructura de la cabecera PM4 sí quedó documentada por una
implementación de terceros, y **`023` queda corroborado de forma independiente**. Pero la
corroboración es *parcial*: la fórmula coincide y **una de sus aserciones queda refutada
contra el corpus**, con un caso vivo.

## Alcance exacto

1. Buscar la fuente primaria y **contar** lo que contiene o no contiene.
2. Extraer de una implementación independiente la codificación del encuadre PM4.
3. Contrastar esa implementación contra el corpus GFX8, aceptando y rechazando parte por
   parte.
4. Cerrar el `NOT_DETERMINED` que `023` dejo sobre cual es el referente exacto del `−1`.

## Criterio de terminacion (cumplido)

Fuente localizada, descargada, hasheada y medida. Contraste hecho contra el corpus con
predicciones falsables. Lo que no se resuelve queda nombrado como lo que es.

---

## 1 · La fuente primaria: existe, y no tiene PM4

**Classification de la fuente: `PRIMARY_DOCUMENTATION`**, y el resultado es un
`NEGATIVE_RESULT`.

| | |
|---|---|
| Documento | *Reference Guide — Graphics Core Next Architecture, Generation 3* |
| Revision | **1.0, March 2015** (la vigente en docs.amd.com es 1.1 de 2016-08-01, doc 70645) |
| Paginas | **637** |
| bytes | 6 293 908 |
| sha256 | `2e8318db0bc60c609ab84b9465b1f299d9b1c90fd1c57862a990cad201ca4a6f` |
| obtencion | mirror de terceros, porque `docs.amd.com` es una SPA con Anubis y la ruta `/api/khub/...` devuelve 404 |

**Nota de clasificacion que no debo saltarme:** el *contenido* es
`PRIMARY_DOCUMENTATION` de AMD, pero el *alojamiento* es un mirror de terceros
(`tpn/pdfs`). Es el mismo PDF que AMD firma, con su pagina de copyright. Lo anoto como
`PRIMARY_DOCUMENTATION (contenido) / mirror (transporte)` para que nadie lo cite como si
lo hubiera servido AMD.

### 1.1 · Conteo, no impression

`pdftotext -layout` sobre el documento completo, y cuenta de ocurrencias:

```
PACKET3          0        RELEASE_MEM     0        COND_EXEC      0
PKT3             0        VM_INVALIDATE   0        INT_SEL        0
WRITE_AT         0        SET_SH_REG      0        GRBM           0
mmCP             0        "Ring Control"  0        "reg op"       0
```

Y los 4 hits de "command processor" son prosa de la introduction (lineas 605-608, 686):
"includes a data-parallel processor (DPP) array, a command processor, a memory
controller". Los 18 hits de `CP_` son **falsos positivos de mnemonicos** de shader:
`CP_EN` (5), `CP_IFLAG_F32` (3), `CP_CYCLE` (3), `CP_F64`/`CP_F32`/`CP_F16` (2 cada uno).

Cero. No "pocas". No "no como tabla". Cero.

### 1.2 · Que si contiene, y por que no sirve para la frontera D

El documento es de **ISA de shader**. Cubre lo que un driver propio necesita del lado
del shader: microcode e instrucciones, `SDWA` (25 lineas), `DPP` (24), registros de
estado (tabla 3.2, *campos*, no offsets), registro `MODE`, `VCCZ` (24), traps y
excepciones (193), scratch (45), wavefront, flat/scratch addressing, `MUBUF` (406).

Lo que **no** contiene, verificado: **no hay tabla de offsets de registros MMIO**. La
busqueda de "register offset", "SPI_SHADER", "Register Name Address" da 0 resultados
relevantes. Los 3 hits de "SBASE" y "lds_param_offset" son operandos de instrucciones,
no un mapa de registros.

Asi que el documento es primario y de alta calidad, y **para el command processor es
irrelevante**. Es exactamente el tipo de fuente que uno dejaria de buscar dos veces.

### 1.3 · Lo que esto hace con los tres `BLOCKED`

| bloqueo original | estado nuevo |
|---|---|
| `022` · identidad del campo `num_skip` de `COND_EXEC` | **sigue `NOT_DETERMINED`**, pero por causa nueva y mejor nombrada |
| `029` · dword extra de `RELEASE_MEM` en GFX9 | sigue `NOT_DETERMINED`, misma causa |
| `023` · la convencion de `PACKET3` | **`RESOLVED`**, ver §3 |
| semantica de `INT_SEL=2` | sigue `NOT_DETERMINED`, misma causa |
| `VM_INVALIDATE_RESPONSE` (`0x51f`) | sigue `NOT_DETERMINED`, misma causa |

La causa nueva y mejor nombrada: **no hay documento primario del framing PM4 para GCN3,
ni lo hubo.** No es un hueco del corpus local ni una fuente que no se haya buscado. Es
una ausencia en el plano del fabricante.

Y eso tiene una consecuencia de metodo que importa mas que los casos individuales: **el
framing PM4 es la parte del command processor que hay que reconstruir por ingenieria
inversa, no leer.** El corpus del kernel es la unica fuente seria que hay, y para el
*payload* de cada paquete lo es todo.

## 2 · El encuadre, documentado por un tercero

**Classification: `SECONDARY_CORROBORATION`.** No es una especificacion: es codigo de
Mesa (freedreno, driver para Adreno), escrito por otra persona, en otro lenguaje, para
otra familia de GPU. Vale por lo que aporta, que es la forma de las cabeceras —que si es
compartida por linaje— y **no** por aserciones sobre ASICs que no son GCN3.

Fuente: `mesa-23.0.0/src/freedreno/common/freedreno_pm4.h` (139 lineas, descargado de
`archive.mesa3d.org`, sin proteccion anti-bot).

```c
#define CP_TYPE0_PKT 0x00000000
#define CP_TYPE2_PKT 0x80000000
#define CP_TYPE3_PKT 0xc0000000
#define CP_TYPE4_PKT 0x40000000
#define CP_TYPE7_PKT 0x70000000

#define CP_NOP_MESG 0x4D455347   /* 'MESG' */
#define CP_NOP_BEGN 0x4245474E   /* 'BEGN' */
#define CP_NOP_END  0x454E4400   /* 'END\0' */
```

Las cuatro constructoras:

```c
pm4_pkt0_hdr(regindx, cnt) = CP_TYPE0_PKT | ((cnt - 1) << 16) | (regindx & 0x7fff)
pm4_pkt3_hdr(opcode, cnt) = CP_TYPE3_PKT | ((cnt - 1) << 16) | ((opcode & 0xff) << 8)
pm4_pkt4_hdr(regindx, cnt) = CP_TYPE4_PKT | cnt | (parity(cnt) << 7)
                                        | ((regindx & 0x3ffff) << 8) | (parity(regindx) << 27)
pm4_pkt7_hdr(opcode, cnt) = CP_TYPE7_PKT | cnt | (parity(cnt) << 15)
                                        | ((opcode & 0x7f) << 16) | (parity(opcode) << 23)
```

### 2.1 · Lo que se aprende aqui que el corpus no da

1. **TYPE4 y TYPE7 llevan bit de paridad impar.** TYPE0 y TYPE3 no. El corpus del kernel
   tiene las macros de cabecera pero no hace falta ninguna de TYPE4/7 para GFX8, asi que
   nunca aparecio la pregunta. Ahora esta.
2. **Los 4 magic de NOP son ASCII**: `MESG`, `BEGN`, `END`. El driver de referencia
   usa `CP_NOP_MESG`/`BEGN`/`END` para marcar regiones en el IB. Que sean ASCII es un
   detalle de diseno, no un accidente.
3. **TYPE2 es exactamente `0x80000000`, sin payload.** Un dword entero.
4. Anchos de campo: indice de registro TYPE0 = 15 bits, opcode TYPE3 = 8 bits,
   longitud = 14 bits.

### 2.2 · Y la asercion que queda REFUTED

El mismo fichero trae el predicado de validacion:

```c
#define pkt_is_type3(pkt)  ((((pkt)&0xC0000000) == CP_TYPE3_PKT) && (((pkt)&0x80FE) == 0))
```

`0x80FE` = `1000_0000_1111_1110`: exige bits 1..7 y bit 15 a cero. El opcode vive en
bits 8..15, asi que el bit 15 **es el bit 7 del opcode**. La asercion que implica es:

> **el opcode de un TYPE3 debe ser menor que `0x80`.**

Eso se puede falsar contra el corpus. Y se falsa. Ver §4.

## 3 · El referente exacto del `−1`: cerrado

`023` midio que `n − payload = −1` en 68/68 sitios de GFX8, con `payload` = dwords de
datos escritos tras la cabecera. Eso deja una ambiguedad: *de que se resta el uno*, del
total o de los datos. freedreno **no** la resuelve, porque su parametro `cnt` no esta
documentado respecto a esa distincion y su `type3_pkt_size()` devuelve `cnt`.

El corpus si, con tres casos que se leen enteros.

### 3.1 · `WAIT_REG_MEM` ×3, F = 5 con 6 dwords de datos

`gfx_v8_0.c:6180` (`emit_pipeline_sync`), leido completo:

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));      /* F = 5 */
amdgpu_ring_write(ring, (WAIT_REG_MEM_MEM_SPACE(1) |
                         WAIT_REG_MEM_FUNCTION(3) |
                         WAIT_REG_MEM_ENGINE(usepfp)));        /* 1 */
amdgpu_ring_write(ring, addr & 0xfffffffc);                      /* 2 */
amdgpu_ring_write(ring, upper_32_bits(addr) & 0xffffffff);       /* 3 */
amdgpu_ring_write(ring, seq);                                    /* 4 */
amdgpu_ring_write(ring, 0xffffffff);                             /* 5 */
amdgpu_ring_write(ring, 4); /* poll interval */                   /* 6 */
```

**6 dwords de datos. Los tres sitios de GFX8** (`:6047` flush de HDP, `:6180` pipeline
sync, `:6199` espera de invalidate) usan `PACKET3(WAIT_REG_MEM, 5)` con exactamente 6.

Y el paquete `WAIT_REG_MEM` de GCN3 ocupa 7 dwords: cabecera + operacion + addr_hi +
addr_lo + data + mask + intervalo. **7 = 6 + 1.** De ahi:

> **el campo vale `datos − 1`, y el paquete ocupa `F + 2` dwords.**

### 3.2 · `insert_nop`: la segunda confirmacion, independiente

`gfx_v11_0.c:553-568`:

```c
static void gfx_v11_ring_insert_nop(struct amdgpu_ring *ring, uint32_t num_nop)
{
        /* Header itself is a NOP packet */
        if (num_nop == 1) {
                amdgpu_ring_write(ring, ring->funcs->nop);
                return;
        }

        /* Max HW optimization till 0x3ffe, followed by remaining one NOP at a time*/
        amdgpu_ring_write(ring, PACKET3(PACKET3_NOP, min(num_nop - 2, 0x3ffe)));

        /* Header is at index 0, followed by num_nops - 1 NOP packet's */
        amdgpu_ring_insert_nop(ring, num_nop - 1);
}
```

Con `F = datos − 1`: el header declara `num_nop − 1` dwords de datos siguientes, y la
recursion escribe exactamente `num_nop − 1`. **Cuadra sin ningun truco de solapamiento.**
El total es `num_nop`, que es lo que se pedia.

Con la lectura de freedreno (`total = F + 1`) el mismo codigo obliga a un solapamiento
entre paquetes y el total sale `2·num_nop − 2`. No cuadra.

### 3.3 · `0x3FFF` esta reservado: la prueba por el tope

El tope `min(num_nop - 2, 0x3ffe)` no es arbitrario. Con `F = datos − 1`, `0x3ffe` da
datos `= 0x3FFF = 16383`, paquete `= 16384 = 2^14` — exactamente el maximo representable.
**Se capta justo por debajo de `0x3FFF` porque `0x3FFF` esta reservado.**

Y el caso base lo confirma: `ring->funcs->nop` vale

```c
.nop = PACKET3(PACKET3_NOP, 0x3FFF),      /* gfx_v8_0.c:6873, :6919, :6954 */
```

Se usa como **un solo dword**, con el comentario *"Header itself is a NOP packet"*. Si
`0x3FFF` obeyed la formula general, el hardware esperaria `0x3FFF + 2 = 16385` dwords.
No puede ser. `0x3FFF` significa **"esta cabecera sola es el paquete"**.

`PROVEN_DERIVED`, y el razonamiento es deductivo: el tope del §3.2 y el caso base solo
tienen sentido juntos si `0x3FFF` esta fuera de la formula.

### 3.4 · El modelo completo

```
TYPE3, campo de longitud F  (14 bits, bits 16..29):
    F          = numero de dwords de DATOS - 1
    paquete    = F + 2 dwords
    F = 0x3FFF = RESERVADO: la cabecera sola es el paquete (NOP unitario)
    maximo util F = 0x3FFE  ->  16384 dwords
```

Y esto es exactamente lo que `023` midio: `n − payload = −1`, 68/68. Lo que cambia es
que **ahora se sabe de que se resta el uno**, que era el `NOT_DETERMINED` que `023`
dejo abierto.

### 3.5 · Corroboracion cruzada, con su alcance exacto

| afirmacion | freedreno | corpus | veredicto |
|---|---|---|---|
| el offset `-1` se aplica antes de almacenar | si | si | **coinciden** |
| el campo es de 14 bits | si (`0x3FFF`) | si (`& 0x3FFF`) | **coinciden** |
| el opcode va en bits 8..15 | si | si (`(op & 0xFF) << 8`) | **coinciden** |
| `F = datos − 1` | no determinable | si | **el corpus lo fija** |
| `0x3FFF` reservado | no menciona | si, por el tope y el caso base | **solo corpus** |

O sea: **la forma coincide, y el corpus aporta los dos hechos que freedreno no dice.**
Eso es exactamente el reparto correcto entre `SECONDARY_CORROBORATION` y `PROVEN`.

## 4 · La asercion de freedreno, falsada con un caso vivo

`pkt_is_type3` exige bit 15 = 0, es decir opcode `< 0x80`. Prediccion falsable. La mido.

Del bloque `/* Packet 3 types */` de `sid.h` (el fichero que define los opcode de GFX8),
separando opcodes de offsets de registro —**los `*_START` / `*_END` de los `SET_*_REG` son
offsets, no opcodes**, y mi primer barrido sin esa distincion los conto como opcodes y
produjo 12 falsos positivos que casi invalidan la prediccion):

```
74 opcodes PACKET3 en GFX8, 74 valores unicos, rango 0x10 .. 0x8B
opcodes >= 0x80:  12
    0x80 PACKET3_LOAD_CONST_RAM          0x88 PACKET3_WAIT_ON_DE_COUNTER_DIFF
    0x81 PACKET3_WRITE_CONST_RAM         0x89 PACKET3_SET_CE_DE_COUNTERS
    0x82 PACKET3_WRITE_CONST_RAM_OFFSET  0x8A PACKET3_WAIT_ON_AVAIL_BUFFER
    0x83 PACKET3_DUMP_CONST_RAM          0x8B PACKET3_SWITCH_BUFFER
    0x84 PACKET3_INCREMENT_CE_COUNTER    0x85 PACKET3_INCREMENT_DE_COUNTER
    0x86 PACKET3_WAIT_ON_CE_COUNTER      0x87 PACKET3_WAIT_ON_DE_COUNTER
```

La prediccion se cumple para 62/74 y **falla para 12**.

### 4.1 · Pero once de esos doce estan muertos: verificacion que podia haberlo dejado todo igual

Que un opcode este *definido* no es que se *emita*. Si los 12 fueran codigo muerto, la
contradiccion seria vacua y no valdria nada:

```
LOAD_CONST_RAM 0 · WRITE_CONST_RAM 0 · WRITE_CONST_RAM_OFFSET 0 · DUMP_CONST_RAM 0
INCREMENT_CE_COUNTER 0 · INCREMENT_DE_COUNTER 0 · WAIT_ON_CE_COUNTER 0
WAIT_ON_DE_COUNTER 0 · WAIT_ON_DE_COUNTER_DIFF 0 · SET_CE_DE_COUNTERS 0
WAIT_ON_AVAIL_BUFFER 0 · SWITCH_BUFFER 13
```

Once con **cero usos en todo el arbol amdgpu**. Uno con 13. Ese es el que decide, y hay
que verificarlo bien porque es el unico que sostiene el hallazgo.

### 4.2 · El superviviente: `SWITCH_BUFFER`, vivo en GFX8

```c
/* gfx_v8_0.c:6277-6281 */
static void gfx_v8_ring_emit_sb(struct amdgpu_ring *ring)
{
        amdgpu_ring_write(ring, PACKET3(PACKET3_SWITCH_BUFFER, 0));
        amdgpu_ring_write(ring, 0);
}
```

Vivo de verdad, no una definicion colgada: esta en la tabla de funciones,
`.emit_switch_buffer = gfx_v8_ring_emit_sb` (`gfx_v8_0.c:6908`), y se llama desde dos
sitios del path comun — `amdgpu_ib.c:322` y `amdgpu_vm.c:909-910` (este ultimo **dos
veces seguidas**). Idéntico en `gfx_v9_0.c:5684` y `gfx_v10_0.c:8800`, o sea que no es
un descuido de GFX8 sino un patron deliberado y compartido.

Aplicando la macro del kernel:

```c
#define PACKET3(op, n)  ((RADEON_PACKET_TYPE3 << 30) | (((op) & 0xFF) << 8) | ((n) & 0x3FFF) << 16)
```

```
PACKET3(0x8B, 0)              = 0xC0008B00
  bit 15                      = 1        <- freedreno exige 0
  v & 0x80FE                  = 0x8000   <- freedreno exige 0
  (v >> 8) & 0xFF             = 0x8B     <- el opcode, se lee de vuelta bien
```

**`REFUTED`, con caso vivo:** `pkt_is_type3` de freedreno rechaza un paquete que amdgpu
emite en produccion en GFX8. Su mascara presupone un espacio de opcodes de 7 bits que
GFX8 no respeta.

Explicacion coherente: freedreno cubre A2xx..A6xx, donde esos opcode ≥ `0x80` no existen.
El predicado es correcto **para su ASIC** y falso **para el mio**. No es un error de
freedreno; es que el framing de TYPE3 **cambio** entre Adreno y GCN3 en el rango del bit
7 del opcode.

### 4.3 · Lo que si se aprende del contraste

Un invariante que el corpus no expresaba: **el campo de longitud es de 14 bits pero el
opcode ocupa 8, y ambos compiten por los 32 bits de la cabecera junto con el tipo.** El
kernel enmascara con `& 0x3FFF` y `& 0xFF` sin-solapamiento exacto; freedreno ademas
valida que los bits intermedios esten a cero. Para un driver propio, la mascara de
construccion es lo que importa, y ya se tiene.

## 5 · Clasificacion

| afirmacion | estado |
|---|---|
| La ISA de GCN3 es publica y accesible | `PROVEN` — 637 paginas, sha256 registrado |
| La ISA de GCN3 no contiene ninguna especificacion PM4 | `PROVEN` — conteo, cero en 10 terminos |
| `ttm/` ausente del corpus | `PROVEN` — confirmado otra vez |
| No hay documento primario del framing PM4 para GCN3 | `NEGATIVE_RESULT`, con causa nombrada |
| Las cabeceras TYPE0/2/3/4/7 y sus mascaras | `SECONDARY_CORROBORATION` |
| TYPE4 y TYPE7 llevan bit de paridad impar | `SECONDARY_CORROBORATION` |
| Los 4 magic de NOP son ASCII | `SECONDARY_CORROBORATION` |
| `F = datos − 1`, paquete = `F + 2` dwords | `PROVEN_DERIVED` — `WAIT_REG_MEM` ×3 + `insert_nop` |
| `0x3FFF` reservado para NOP unitario | `PROVEN_DERIVED` — el tope + el caso base |
| El `-1` de freedreno es la misma formula | `SECONDARY_CORROBORATION` — la forma coincide |
| `pkt_is_type3` exige opcode `< 0x80` | `PROVEN` |
| Esa asercion vale para GFX8 | **`REFUTED`** — 12/74 opcodes ≥ `0x80`, uno vivo |
| `COND_EXEC` campos nombrados | sigue `NOT_DETERMINED` |
| `RELEASE_MEM` dword extra GFX9 | sigue `NOT_DETERMINED` |
| `VM_INVALIDATE_RESPONSE`, `INT_SEL=2` | sigue `NOT_DETERMINED` |

## 6 · Confounders

- **El documento que descargue es la Rev 1.0 de 2015, y la vigente es la Rev 1.1 de
  2016.** No pude comparar: la ruta de `docs.amd.com` devuelve 404 y el mirror solo tiene
  1.0. Una revision podria anadir PM4. Es improbable —un manual de ISA de shader no crece
  en framing de paquetes de un ano al siguiente— pero es un hueco real, y lo nombro en
  vez de asumirlo. `Falsable`: comparar la Rev 1.1 con el mismo conteo de 10 terminos.
- **freedreno es Adreno, no GCN3.** Todo lo que he marcado
  `SECONDARY_CORROBORATION` es correlacion de linaje, no especificacion. Y §4 acaba de
  demostrar que la correlacion **falla** en al menos una asercion. Es exactamente por eso
  que §3 no la uso para el referente del `−1`.
- **Los 12 opcodes ≥ `0x80` los separé a mano** de los macros `*_START`/`*_END`, que son
  offsets de registro. Un barrido automatico los mezcla y produce 12 falsos positivos. Lo
  dejo escrito porque es el error que casi me hace concluir lo contrario.
- El hecho de que `.nop` valga `0x3FFF` y el tope sea `0x3ffe` **no demuestra por si solo**
  que `0x3FFF` este reservado: una de las dos tiene que ser. Lo que lo cierra es que
  `.nop` se usa para un NOP de un solo dword con el comentario *"Header itself is a NOP
  packet"*. Sin ese comentario, la conclusion seria `HYPOTHESIS`.
- `RELEASE_MEM`, `COND_EXEC` y `VM_INVALIDATE` los busca el hardware por numero de opcode
  leido del IB. Que el framing este claro **no** dice nada de la semantica del payload.
  No he dejado que el avance en §3 se/contamine en §5.

## 7 · UNLOCKS

- **La frontera D deja de ser "buscar la spec".** Es un problema de ingenieria inversa
  con el corpus del kernel como unica fuente seria, y eso cambia como se aborda: no se
  espera una fuente, se construye evidencia.
- **Un driver propio puede construir cabeceras PM4 con reglas exactas y medidas**:
  tipo en bits 31..30, longitud `F = datos − 1` en bits 16..29 (14 bits), opcode en bits
  8..15 (8 bits), y `0x3FFF` reservado. Eso es lo que necesita el ensamblador PM4 de
  `012`, que hasta ahora asumia la convencion.
- **`DESIGN_FREEDOM` con base medida**: si se necesita un opcode ≥ `0x80` en GFX8, esta
  prohibido decirlo por analogia con Adreno. El hardware lo acepta —`SWITCH_BUFFER` lo
  demuestra en produccion— aunque freedreno lo rechace.
- Los cinco `NOT_DETERMINED` de §1.3 quedan **agrupados bajo una causa unica y ya
  nombrada**, que es lo unico que `032` §4 necesitaba: "falta la semantica de hardware,
  y la semantica del framing tampoco existe publicada". Un solo trabajo de hardware los
  resolveria, y ahora se sabe que no hay atajo documental.
- **Metodo, y es lo que mas valoro de esta ronda**: la fuente de terceros dio una
  prediccion (`opcode < 0x80`), y medirla contra el corpus la refuto. Si la hubiera
  citado como corroboracion sin comprobarla, esta ronda habria producido un hallazgo
  falso y habria contaminado `023`. La asercion de un tercero es una hipotesis con
  autor, no una evidencia.

## 8 · Criterio de falsificacion

Se refutaria si: (a) la Rev 1.1 de la ISA de GCN3 contuviera tablas PM4 — refutable
descargandola y contando los mismos 10 terminos; (b) `F = datos − 1` fuera erroneo y el
`WAIT_REG_MEM` de 7 dwords se interpretara como dos paquetes — refutable con el paquete
documentado de GCN3, que no esta, o leyendo una captura de IB, que requiere runtime;
(c) `gfx_v8_ring_emit_sb` no se ejecutara nunca en GFX8 — refutable solo con traza, es
`NOT_DETERMINED`; lo que si es `PROVEN` es que esta cableado en la tabla de funciones y
que dos call sites del path comun lo invocan; (d) el subtree `ttm/` apareciera en el
corpus y `ttm_bo_pin` no Guaranteizara coherencia — refutable, y resolveria el
`DERIVATION` de `032` §2 en una direccion o en la otra.

## 9 · Evidencia

```
PRIMARIA (descargada, medida):
  GCN3 ISA Rev 1.0 (Marzo 2015), 637 pag, sha256 2e8318db...ca4a6f
  conteo pdftotext -layout: PACKET3=0 PKT3=0 RELEASE_MEM=0 COND_EXEC=0
                          VM_INVALIDATE=0 INT_SEL=0 WRITE_AT=0 GRBM=0 mmCP=0
  los 18 "CP_" = CP_EN/CP_CYCLE/CP_F32/CP_F64/CP_F16/CP_IFLAG_F32 (mnemonicos)

SECUNDARIA (descargada):
  mesa-23.0.0/src/freedreno/common/freedreno_pm4.h  (139 lineas)
    CP_TYPE0/2/3/4/7_PKT, 4 constructoras pm4_pktN_hdr, pkt_is_type3, CP_NOP_*
  mesa-24.3.4/src/amd/common/ac_pm4.h  -- NOTA: no aporta. Mesa generalizo a
    ac_pm4_cmd_begin(opcode)+ac_pm4_cmd_add(dw); sin campos por paquete. Y
    src/gallium/drivers/radeonsi/nlt/ NO EXISTE (mi recollection de esa ruta
    era falsa; verificado con tar -t sobre mesa-24.3.4).

CORPUS (medido):
  gfx_v8_0.c:6180, 6047, 6199   PACKET3(WAIT_REG_MEM,5) + 6 dwords  [x3, leidos completos]
  gfx_v11_0.c:553-568           insert_nop: F=min(num_nop-2,0x3ffe), recursa num_nop-1
  gfx_v8_0.c:6873,6919,6954     .nop = PACKET3(PACKET3_NOP, 0x3FFF)
  gfx_v8_0.c:6277-6281, 6908    emit_sb, cableado .emit_switch_buffer
  amdgpu_ib.c:322, amdgpu_vm.c:909-910   call sites de emit_switch_buffer
  sid.h:335-339                PACKET3(op,n) = (3<<30)|((op&0xFF)<<8)|((n&0x3FFF)<<16)
  sid.h bloque "Packet 3 types"  74 opcodes, 12 >= 0x80, 11 con 0 usos, 1 con 13
  08-ARQUITECTURA/tools/pm4_count_census.py --only=fx8
                                n - payload = -1 en 68/68
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

## 10 · Lo que queda, en una linea

El framing PM4 de GFX8 esta **cerrado y medido**. El *payload* de cada paquete —lo que
`COND_EXEC`, `RELEASE_MEM` y `VM_INVALIDATE` hacen realmente— sigue abierto, y ya no
por falta de busqueda: **no hay documento, y habra que medirlo.**