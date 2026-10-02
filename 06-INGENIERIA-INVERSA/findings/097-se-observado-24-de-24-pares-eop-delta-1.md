# 097 · §E OBSERVADO: 24 de 24 pares de EOP difieren en 1. El dummy `seq-1` está en el ring vivo

```
CLASSIFICATION=DOCUMENTATION · TRACK=RUNTIME (READ_ONLY)
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión gráfica INTACTA
```

## Qué resuelve

`096` leyó el emisor de fences y **afirmó** que escribe dos EOP: uno con `seq-1`
y otro con `seq`, y que el primero es un dummy con el motivo escrito (*"Workaround
for cache flush problems"*). Esa era una afirmación sobre **código**.

**Esto la convierte en medición sobre el ring que la GPU está usando ahora mismo.**

Y lo hace sin F1, sin MMIO write, sin cargar módulos y sin tocar la TLB. Es
`debugfs`, sólo lectura.

## El observable

```
/sys/kernel/debug/dri/0000:01:00.0/amdgpu_ring_gfx     8204 bytes
```

Volcado binario crudo del ring GFX. Copiado a `/tmp/ring_gfx.bin`. 2051 dwords.

## Los opcodes reales, y un número que yo había supuesto mal

Antes de escanear nada verifiqué los valores en `sid.h`:

```
PACKET3_EVENT_WRITE_EOP    0x47      <-- yo iba buscando 0x36.  FALLO MIO.
PACKET3_PFP_SYNC_ME        0x42
PACKET3_NOP                0x10
PACKET3_INDIRECT_BUFFER    0x3F
PACKET3_COND_EXEC          0x22
```

Si hubiera escaneado `0x36` habría concluded "no hay EOP" y habría publicado un
resultado negativo falso. **`DERIVATION_BEFORE_OBSERVATION`, otra vez, y esta
consecuencia directa: 48 EOP frente a 0.**

Lo que hay en el ring vivo:

| tipo | opcode | apariciones |
|---|---|---|
| `PACKET3_NOP` | `0x10` | 1200 |
| **`PACKET3_EVENT_WRITE_EOP`** | **`0x47`** | **48** |
| `PACKET3_COND_EXEC` | `0x22` | 16 |
| `PACKET3_PFP_SYNC_ME` | `0x42` | **8** |
| `PACKET3_INDIRECT_BUFFER` | `0x3F` | 8 |

Los tres que `068`, `094`, `095` y `096` habían deducido por lectura **están
todos presentes**, con conteos que cuadran con el presupuesto de `094`.

## El resultado

Separo los 48 EOP en 24 pares consecutivos y comparo el dword de secuencia
(`lower_32_bits(seq)`) de cada uno:

```
par  idx   seq_dummy    seq_real     delta   DATA_SEL dummy/real
 0   39    0x000D74C6   0x000D74C7   1       1/1   OK
 1   83    0x000B4BA0   0x000B4BA1   1       1/2   OK
 2   95    0x000D74C7   0x000D74C8   1       1/1   OK
 3   295   0x000D74C8   0x000D74C9   1       1/1   OK
 4   339   0x0000B883   0x0000B884   1       1/2   OK
...                                                       (24 filas)
23  1887   0x000D74C5   0x000D74C6   1       1/1   OK

pares con delta EXACTAMENTE 1: 24 de 24
```

**24 de 24. Sin una sola excepción.**

El primer EOP decodificado, dword a dword, contra lo que dice `gfx_v8_0.c`:

```
L39  0xC0044700   PKT3, type=0x47 (EVENT_WRITE_EOP), count=4
L40  0x00038514   EOP_TCL1|TC|TC_WB + EVENT_TYPE + EVENT_INDEX(5)
L41  0x00001040   addr & 0xfffffffc
L42  0x200000FF   (upper32(addr)&0xffff) | DATA_SEL(1) | INT_SEL(0)
                       bit 29 = 1  ->  DATA_SEL = 1   EXACTO
L43  0x000D74C6   lower_32_bits(seq - 1)  = 881862
L44  0x00000000   upper_32_bits(seq - 1)  = 0
L45  0xC0044700   el EOP real empieza aquí
```

**Coincidencia exacta, dword por dword**, incluida la posición del bit de
`DATA_SEL`.

## Y aparece el segundo eje: dos series de secuencia independientes

`DATA_SEL` del EOP real es 1 en 16 pares y 2 en 8. Y **no están mezclados**:

```
DATA_SEL real = 1  (fence de 32 bits):  16 pares
  0xd74c7 0xd74c8 0xd74c9 0xd74ca 0xd74cb 0xd74cc 0xd74cd 0xd74ce
  0xd74cf 0xd74d0 0xd74d1 0xd74d2 0xd74d3 0xd74d4 0xd74c5 0xd74c6

DATA_SEL real = 2  (fence de 64 bits):   8 pares
  0xb4ba1 0xb884 0xb4ba2 0xb885 0xb4ba3 0xb886 0xb4ba4 0xb883
```

**Dos contadores distintos, en el mismo ring.** El primero es monotono y
reinicia al llegar al final del buffer — que es exactamente el comportamiento
de un contador módulo `num_hw_submission` que `096` describió
(`amdgpu_fence.c:226-233`). El segundo va por otro sitio y avanza a otro ritmo.

**Esto es `AMDGPU_FENCE_FLAG_64BIT` observado.** `096` lo dedujo de
`DATA_SEL(write64bit ? 2 : 1)`; aquí se ven las dos ramas funcionando a la vez
en el mismo ring, con conteos 16 y 8.

Y el **dummy siempre tiene `DATA_SEL=1`**, sin excepción, que es literal de
`gfx_v8_0.c:6153` (`DATA_SEL(1) | INT_SEL(0)`, fijo). El driver no le da la
opción al dummy, sólo al EOP real.

## Y tres direcciones de fence distintas

```
0x00001040   4160
0x16B4E00   23818240
0x36C8A00   57384960
```

**Tres ranuras de fence en uso simultáneo** dentro del mismo ring. No es un
fence por ring: son tres. Eso encaja con `amdgpu_fence.c:463`, que reserva
`num_hw_submission * 2` ranuras — y con que varios clientes tengan su propia
secuencia.

## Un hallazgo lateral: el campo `count` no describe lo que se escribe

Cada EOP ocupa **6 dwords** (cabecera + 5 de payload), medido: las separaciones
entre EOP consecutivos son `{6: 32, 38: 8, 194: 7}` — cuando son adyacentes, 6.

Pero la cabecera dice `count = 4`:

```
amdgpu_ring.h:   PACKET3(op, n) = (TYPE3 << 30) | (op << 8) | ((n & 0x3FFF) << 16)
gfx_v8_0.c:6145 PACKET3(PACKET3_EVENT_WRITE_EOP, 4)
```

Y `amdgpu_ring_write` se llama **6 veces** para ese packet (L6145 a L6155). Con
la convención de GCN3, `count = 4` significaría 5 dwords en total.

**Mismo patrón en los 48.** El driver emite 6 y declara 4.

**Y no lo interpreto**, porque no puedo: si el hardware consume 5 y el sexto
dword pertenece al siguiente packet, o si consume 6 e ignora el count para este
tipo, o si `EVENT_WRITE_EOP` tiene una regla especial — **el corpus no lo dice**.
Lo que sí es medible es que **el ring funciona**: las secuencias avanzan y los
jobs terminan, así que el hardware no se queda corto.

**Lo dejo como discrepancia medida con la interpretación abierta.** No como error.

## Por qué esto importa más que el resto de §E

| lo que `096` afirmó | estado antes | estado ahora |
|---|---|---|
| Dos EOP, `seq-1` y `seq` | `PROVEN` (código) | **`OBSERVED`** (24/24) |
| El dummy es siempre `DATA_SEL=1` | `PROVEN` (código) | **`OBSERVED`** (24/24) |
| Eje de 32/64 bits vía `DATA_SEL` | `PROVEN` (código) | **`OBSERVED`** (16 y 8) |
| El contador es módulo el tamaño del ring | `PROVEN_DERIVED` | **`OBSERVED`** (reinicia al llegar al final) |
| Varias direcciones de fence por ring | `NOT_DETERMINED` | **`OBSERVED`** (3) |
| Por qué hace falta el dummy | `NOT_DETERMINED` | `NOT_DETERMINED` |

**Cinco afirmaciones pasan de lectura a medición en una sola operación de sólo
lectura.**

Y abre una vía que `AGENTS.md` no tenía registrada: **`amdgpu_ring_gfx` es un
observable de sólo lectura del estado de ejecución, y funciona con la sesión
gráfica viva.** Eso no estaba en el plan deDiscriminantes porque nadie había
mirado qué expone `debugfs`.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| 24/24 pares con delta 1 | `OBSERVED` |
| EOP = opcode 0x47 | `OBSERVED` + `PROVEN` (`sid.h`) |
| Dos series de secuencia, 32 y 64 bits | `OBSERVED` |
| 3 direcciones de fence simultáneas | `OBSERVED` |
| Separación de 6 dwords por EOP | `OBSERVED` |
| Por qué el dummy `seq-1` hace falta | **`NOT_DETERMINED`** |
| Por qué `count=4` con 6 dwords escritos | **`NOT_DETERMINED`** |
| Qué son exactamente esas 3 direcciones | `NOT_DETERMINED` — no las seguí hasta sus BOs |
| Quién emite cada serie (scheduler, IRQ, cliente) | `NOT_DETERMINED` |
| Si el dummy es necesario en GFX8 o es herencia | `NOT_DETERMINED` |

**La primera sigue abierta y es la que más importa.** Saber que el delta es 1 no
explica por qué existe el dummy. Pero ahora hay un discriminante que no
existía: **el valor que se lee en la página de fence es el del EOP real, no el
del dummy.** Eso se puede comprobar leyendo la página de fence — que `096`
dijo que está en RAM del sistema y es legible sin TLB. **Y eso sí cerraría el
`hardware execution ordering` que F1Ogigualmente prometía, sin F1.**

## Procedencia

- `RUNTIME` — `/sys/kernel/debug/dri/0000:01:00.0/amdgpu_ring_gfx`, copiado a
  `/tmp/ring_gfx.bin` (8204 bytes, 2051 dwords). **Sólo lectura.**
- `STATIC` — `sid.h` (los cinco opcodes), `gfx_v8_0.c:6135-6172`,
  `gfx_v8_0.c:6870-6896`, `amdgpu_fence.c:79-90` y `:211-248` y `:443-470`.
- **NIVEL 2** (lectura de hardware). No hubo `WRITE_EXECUTION`, ni MMIO write, ni
  carga de módulo. **La sesión gráfica sigue intacta** — `sway` (pid 1705) no se
  tocó, y por eso esto no es F1.
- Encadenada con `096` (la que esto verifica), `094` (los 3 FENCE del frame),
  `095` (PFP_SYNC_ME, observado 8 veces), `068` (COND_EXEC, observado 16),
  `083`/`090` (§G).
- Corrige una suposición mía anterior sobre el opcode del EOP.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método.**

La primera: busqué `0x36` porque lo saqué de la cabeza. El valor real es `0x47`
y lo tenía a un `grep` de distancia, en el mismo fichero donde había leído los
otros opcodes. **Un escaneo con el número equivocado no da cero: da un cero
inventado**, y ese cero habría parecido un resultado negativo sólido. Lo que me
salvó fue verificar los opcodes *antes* de contar, no después.

La segunda, y es una corrección de estado: **la sesión gráfica de esta máquina
es `sway` (pid 1705), no `kwin_wayland` como tenía anotado.** Verificado con
`fuser -v /dev/dri/card1 /dev/dri/renderD128`, que devuelve sway en ambos. El
bloqueo de F1 sigue existiendo y por el mismo motivo, pero el proceso es otro,
y `docs/ESTADO-BASE-PRE-F1.md` tiene el nombre equivocado. **Es de otra sesión;
lo informo y no lo edito.**