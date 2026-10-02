# 095 · §E: PFP, ME y CE son tres motores reales con tres instruction caches, y el driver no toca ninguno

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

Estaba en `NOT_DETERMINED` desde hacía rato, por dos vías distintas:

1. `084`RETIRÓ una afirmación mía de que PFP y ME eran inertes en GFX8. Fue
   un error mío, y lo retiré — pero sin comprobarlo.
2. `068` vio que la secuencia de `ring_emit_vm_flush` acaba en `PFP_SYNC_ME`, y
   eso **no significa nada** hasta que se sepa si PFP y ME existen y si hay algo
   que sincronizar.

Aquí está la respuesta, y es afirmativa en las dos direcciones.

## Existence: los tres motores están en un solo registro

`gfx_8_0_sh_mask.h`, `CP_ME_CNTL`. **Nueve campos, tres motores, tres campos
cada uno:**

```
campo                  máscara      shift
CE_HALT                0x1000000    0x18   (bit 24)
CE_STEP                0x2000000    0x19   (bit 25)
CE_INVALIDATE_ICACHE   0x10         0x4    (bit 4)

PFP_HALT               0x4000000    0x1a   (bit 26)
PFP_STEP               0x8000000    0x1b   (bit 27)
PFP_INVALIDATE_ICACHE  0x40         0x6    (bit 6)

ME_HALT                0x10000000   0x1c   (bit 28)
ME_STEP                0x20000000   0x1d   (bit 29)
ME_INVALIDATE_ICACHE   0x100        0x8    (bit 8)
```

**Cada motor tiene su propia instruction cache.** Eso es un hecho de hardware
consecuencia directa del layout: invalidar la de uno no toca la de los otros.

Y hay un tercer motor del que nadie había hablado: **CE**, el Command Engine.

**Consecuencia para `068`**: la secuencia `… → PFP_SYNC_ME` **sí es una
sincronización real entre dos motores**. PFP existe, ME existe, y el opcode
`0x42` los coordina. `068` dejó `hardware execution ordering NOT_PROVEN`, y
sigue sin estar probada, pero la pregunta "¿hay dos motores que sincronizar?"
ahora tiene respuesta afirmativa y con registro.

## Y `PFP_SYNC_ME` es el mismo opcode en nueve generaciones

```
sid.h:465          #define PACKET3_PFP_SYNC_ME  0x42
vid.h:200          #define PACKET3_PFP_SYNC_ME  0x42
cikd.h:324         #define PACKET3_PFP_SYNC_ME  0x42
nvd.h:322          #define PACKET3_PFP_SYNC_ME  0x42
soc15d.h:292       #define PACKET3_PFP_SYNC_ME  0x42
```

Y lo emite el driver en: `gfx_v6_0.c:2396`, `gfx_v7_0.c:3160`,
**`gfx_v8_0.c:6212`**, `gfx_v9_0.c:5623`, `gfx_v10_0.c:8766`, `gfx_v11_0.c:6064`,
`gfx_v12_0.c:4552`, `gfx_v12_1.c:3448`.

**`0x42` en nueve generaciones, de GFX6 a GFX12, sin cambiar.** Es uno de los
opcodes más estables del ISA de packets, y `include_closure.py` lo confirma
como `#define` único, sin redefiniciones que compitan.

## El driver los treats como un bloque indivisible

```
gfx_v8_0.c:4084   static void gfx_v8_0_cp_gfx_enable(struct amdgpu_device *adev, bool enable)
gfx_v8_0.c:4086       u32 tmp = RREG32(mmCP_ME_CNTL);
gfx_v8_0.c:4089           tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, ME_HALT, 0);
gfx_v8_0.c:4090           tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, PFP_HALT, 0);
gfx_v8_0.c:4091           tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, CE_HALT, 0);
gfx_v8_0.c:4093           tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, ME_HALT, 1);
gfx_v8_0.c:4094           tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, PFP_HALT, 1);
gfx_v8_0.c:4095           tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, CE_HALT, 1);
```

**Una lectura, una escritura, tres halt.** Nunca uno suelto. Ni una sola vez en
todo el fichero se para PFP sin parar ME.

## Y sólo se llama en tres sitios, ninguno de ellos el envío normal

| línea | función | efecto |
|---|---|---|
| `gfx_v8_0.c:4142` | `gfx_v8_0_cp_gfx_start`, L4130 | enable = true |
| `gfx_v8_0.c:4740` | `gfx_v8_0_cp_enable`, L4738 | el bool que le pase |
| `gfx_v8_0.c:4969` | `gfx_v8_0_pre_soft_reset`, L4952 | enable = false |

**Ni uno en el camino de un job.** Los tres motores se paran antes de un soft
reset y se arrancan al iniciar el subsistema. Durante el envío normal de
comandos no se tocan.

## El resultado negativo que importa: ningún icache se invalida en GFX8

`CP_ME_CNTL` ofrece tres campos para ello. El driver los usa en GFX9:

```
gfx_v9_0.c:3249   tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, CE_INVALIDATE_ICACHE, enable ? 0 : 1);
gfx_v9_0.c:3250   tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, PFP_INVALIDATE_ICACHE, enable ? 0 : 1);
gfx_v9_0.c:3251   tmp = REG_SET_FIELD(tmp, CP_ME_CNTL, ME_INVALIDATE_ICACHE, enable ? 0 : 1);
```

**Tres líneas seguidas, los tres motores.** Y en GFX8:

```
grep -rn 'INVALIDATE_ICACHE' amdgpu/*.c  ->  gfx_v9_0.c, gfx_v9_4_3.c,
                                              gfx_v11_0.c, gfx_v12_0.c, gfx_v12_1.c,
                                              mes_v11_0.c, mes_v12_0.c, mes_v12_1.c,
                                              umsch_mm_v4_0.c
```

**`gfx_v8_0.c` no aparece.** Cero invalidaciones de icache de motor en esta GPU.

Los otros usos son de motores que **no existen en GFX8**: `CP_MEC_CNTL`
(`MEC_INVALIDATE_ICACHE`, gfx_v9_4_3 y posteriores) es el Compute Engine
separado, y `MES_INVALIDATE_ICACHE` es el Media Engine. **GFX8 tiene CE, ME y
PFP; el MEC y el MES son de GFX9 en adelante.**

**Y esto tiene una consecuencia práctica.** El hardware mantiene tres caches de
instrucciones, el driver de esta GPU **no invalida ninguna**, y el software no
puede saber qué hay dentro de ellas. Un driver propio tiene tres opciones, y
ninguna está resuelta por el corpus:

1. Copiar el comportamiento de amdgpu: no invalidar, y aceptar que las caches
   conservan lo que un reset haya dejado.
2. Invalidar los tres juntos al arrancar, como hace GFX9 pero sólo en un punto.
3. No tocar PFP ni ME y trabajar sólo sobre CE, que es el motor que consume
   `DE_META` y `CE_META` (los dos paquetes más caros del frame, `094`).

**La opción 3 es la que menos se ha considerado y la que más conviene para un
driver propio**, porque `094` acaba de medir que `CE_META` (14 dw) y `DE_META`
(31 dw) son el 26 % del frame GFX. Si PFP y ME no se usan fuera de
`PFP_SYNC_ME`, el camino crítico de graphics pasa por CE.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| PFP, ME y CE existen en GFX8 | `PROVEN` (`CP_ME_CNTL`, `gfx_8_0_sh_mask.h`) |
| Cada uno tiene instruction cache propia | `PROVEN` (tres campos separados) |
| `PFP_SYNC_ME = 0x42` en nueve generaciones | `OBSERVED` (`sid.h` + 8 ficheros) |
| El driver halt/unhalt los tres a la vez | `PROVEN` (`gfx_v8_0.c:4084-4096`) |
| No los toca en el envío normal | `PROVEN` (3 sitios, ninguno de envío) |
| Ningún icache de motor se invalida en GFX8 | `PROVEN_ABSENT` (0 sitios) |
| Que hace exactamente `PFP_SYNC_ME` | **`NOT_DETERMINED`** |
| Qué hay dentro de los tres icache | **`NOT_DETERMINED`** |
| Si PFP ejecuta trabajo o sólo secuencia | **`NOT_DETERMINED`** |
| Si ME y CE se pueden usar de forma independiente | **`NOT_DETERMINED`** |

**Las cuatro últimas son el hueco honesto y no voy a cerrarlas por
razonamiento.** `084` ya me pilló suponiendo que PFP y ME eran inertes; el
error no fue el unknown, fue **declarar inerte lo que no había comprobado**.
Esta vez lo que sé es qué registers existen y qué hace el driver con ellos. Lo
que el hardware hace por dentro sigue siendo `NOT_DETERMINED`, y esa es una
frontera legítima, no un agujero del trabajo.

Lo que sí cambia es la pregunta: ya no es "¿existen PFP y ME?" sino **"¿qué
gana un driver propio usándolos, y qué se pierde si no los usa?"** — y esa se
responde midiendo, no leyendo.

## Procedencia

- `STATIC` — `gfx_8_0_sh_mask.h` (`CP_ME_CNTL`), `gfx_v8_0.c:4084-4096`,
  `gfx_v8_0.c:4142`, `gfx_v8_0.c:4740`, `gfx_v8_0.c:4969`,
  `gfx_v8_0.c:6212`, `sid.h:465`, `vid.h:200`, `cikd.h:324`,
  `nvd.h:322`, `soc15d.h:292`, y los ocho ficheros emisores de GFX6 a GFX12.
- Sin `RUNTIME`. Sin lectura de la GPU. Sin escrituras.
- Cierra el `NOT_DETERMINED` de PFP y ME. Encadenada con `068` (la secuencia de
  emisión), `084` (packet consumption, y la corrección de mi error),
  `094` (el presupuesto del frame, y el peso de CE_META/DE_META).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método.** Busqué `ME_[A-Z]` con regex y sali 0 en **todas** las
generaciones, GFX10 incluida. Casi concluyo "el ME no existe", que era la
confirmación de lo que ya había afirmado mal en `084` — por segunda vez. Lo que
salió fue que el nombre de los registros de ME es `CP_DMA_ME_*` y
`CP_ME_CNTL__ME_*`, no `ME_*`.

**Si el resultado encaja con lo que yo ya creía, eso es una señal de alarma y
no de confirmación.** Un resultado negativo que confirma una conclusión previa
hay que tratarlo como error de método hasta que se demuestre lo contrario.
Antes de dar por bueno el `0` miré GFX10, y en GFX10 no puede faltar el ME.
Eso fue lo que me avisó de que el `0` era mío y no del hardware.