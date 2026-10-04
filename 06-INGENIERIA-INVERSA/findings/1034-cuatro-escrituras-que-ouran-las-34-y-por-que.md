# 1034 · Cuatro escrituras que OURAN las 34, y por qué el componente las daba poryllacaso

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA` · `MODIFIES_CODE=NO`

---

## La pregunta

El plan de 34 escrituras replica `gmc_v8_0_gart_enable()`
(`gmc_v8_0.c:829-946`). Hay **cuatro escrituras más en el camino de
hardware** que la secuencia no contiene y que el componente no programa:
¿qué son, cuándo ocurren, y importan?

Respuesta corta: son un **deshabilitador de PRT**, no un habilitador, y
ocurren **antes** de las 34.

## MEDIDO

### Qué escribe

`gmc_v8_0.c:92-97`, tabla `golden_settings_polaris11_a11`:

```c
static const u32 golden_settings_polaris11_a11[] = {
mmVM_PRT_APERTURE0_LOW_ADDR, 0x0fffffff, 0x0fffffff,
mmVM_PRT_APERTURE1_LOW_ADDR, 0x0fffffff, 0x0fffffff,
mmVM_PRT_APERTURE2_LOW_ADDR, 0x0fffffff, 0x0fffffff,
mmVM_PRT_APERTURE3_LOW_ADDR, 0x0fffffff, 0x0fffffff
```

Despachada para **nuestra ASIC**: `gmc_v8_0.c:141` `case CHIP_POLARIS12:`
→ `:144` la tabla. El nombre dice `polaris11`, y el despacho dice
`POLARIS12`: amdgpu **reutiliza deliberadamente** los golden de Polaris11 en
Polaris12. Es evidencia de intención, no un accidente, pero es reutilización
entre ASICs y queda registrada como tal.

### Cuándo ocurre

```
gmc_v8_0.c:1208   gmc_v8_0_init_golden_registers(adev);
gmc_v8_0.c:1228   r = gmc_v8_0_gart_enable(adev);
```

**Antes.** No son parte de `gart_enable()`: son una función distinta que la
precede en `hw_init`.

### Cómo se aplica: RMW, no escritura ciega

`program_register_sequence()` → `amdgpu_device.c:959-975`: si
`and_mask == 0xffffffff` escribe el literal; si no, hace
`tmp = RREG32(reg); tmp &= ~and_mask; tmp |= or_mask;`. Con
`and_mask = 0x0fffffff ≠ 0xffffffff`, son **4 `RREG32` + 4 `WREG32`**, y el
valor final depende del contenido previo.

### Qué efecto tiene

`LOGICAL_PAGE_NUMBER_MASK = 0xfffffff` — 28 bits
(`gmc_8_1_sh_mask.h`, campo `mmVM_PRT_APERTURE*_LOW_ADDR__LOGICAL_PAGE_NUMBER_MASK`).

Poner `LOW = 0x0fffffff` deja la ventana `[LOW, HIGH)` **vacía para
cualquier HIGH posible**, porque `HIGH` es un campo de 28 bits y
`HIGH > 0x0fffffff` es imposible. Es un **deshabilitador**: garantiza que PRT
no cubre nada, sea cual sea el contenido previo de los cuatro `HIGH`.

## Por qué el componente no lo tenía registrado, y el error que produjo

**El componente se REFERÍA a estas escrituras y las atribuía a la función
equivocada.** `rx550_gart_seq.c:50-51` (versión anterior a la corrección de
hoy) decía que las 34 de la tabla más las que escriben sus "dos called"
—`mmVM_PRT_CNTL` y las ocho `mmVM_PRT_APERTURE*`— son 44.

Eso es falso por dos razones independientes, ambas medidas:

1. **`gmc_v8_0_gart_enable()` no llama a `set_prt()`.** Cero ocurrencias de
   `set_prt` en `L829-946`. Se llama desde `amdgpu_vm.c:1450`, por el
   recuento de usuarios PRT (`amdgpu_vm_update_prt_state`). Las 9 escrituras
   de PRT son de una **vía reactiva** que dispara un VM de userspace con el
   flag PRT, no de la secuencia del GART.
2. **`gmc_v8_0_init_golden_registers()` tampoco se llama desde `gart_enable`.**
   Se llama desde `hw_init` en `L1208`, y escribe **otras 4**, las LOW, no
   `mmVM_PRT_CNTL` ni las HIGH.

De ese doble error salían el número «44», el `NOT_IMPLEMENTED` de las
escrituras PRT atribuido a un parámetro de módulo que no las gobierna, y el
gap que este hallazgo describe. Corregido el 2026-10-04 en el propio
componente y en el hallazgo 1033 §R9.

## ¿Importan?

**Análisis causal, con su veredicto.**

| | veredicto |
|---|---|
| ¿Puede OURAN activarse desde este driver? | **NO.** Requiere el ioctl GEM_VA con `AMDGPU_VM_PAGE_PRT`. El componente no expone ioctls. |
| ¿Puede OURAN quedar en un estado indeterminado? | **SÍ.** Si no se programa, los cuatro `LOW` conservan el valor del reset, y el reset **no está en el corpus**: no existe ningún `asic_reg/gmc/*_default.h` (medido: 22 ficheros `*default*` en el árbol, ninguno en `gmc/`). `NOT_DETERMINED`. |
| ¿Qué pasaría si PRT quedara activo solapando la ventana del GART? | Un acceso no mapeado se serviría por *page-request* en vez de fallar. Nuestro plan pone `*_PROTECTION_FAULT_ENABLE_DEFAULT = 1` (el valor del corpus) justamente para que esos accesos fallen a la página de relleno. Sería **dato silenciosamente incorrecto en vez de fault**. |
| ¿Es observable hoy? | **NO.** Sin ruta de activación, y sin lectura posible: nadie lee estos nueve registros en `drivers/gpu/drm/amd/`, y no hay registro `STATUS` asociado (barrido de `gmc_8_1_d.h`: solo los 9 de apertura y `CNTLE`; cero `*_STATUS`). |

**Clasificación: `GAP` + `NOT_DETERMINED`. No es un bug del plan.** El plan
se declara como transcripción de `gart_enable()` y lo es; estas escrituras son
de otra función.

## Qué NO se hizo, y por qué

**No se implementaron.** Motivo, con su coste:

- **Es un RMW cuyo valor previo no se conoce.** Sin el reset de GFX8 en el
  corpus, un RMW de esos cuatro registros es exactamente la clase de
  escritura que §43 del proyecto llama `WRITE_SEMANTICS_UNKNOWN`: hay una
  lectura, hay un objetivo identificado, pero no hay evidencia del punto de
  partida.
- **El riesgo actual es nulo** por la primera fila de la tabla: PRT no se
  puede activar desde aquí.
- **Añadirlos exige tocar la tabla de registros**, que está ordenada por
  `byte_offset` y es posicional en el resolver. Los cuatro entrarían entre los
  índices 16 (`mmVM_INVALIDATE_RESPONSE`, `0x147C`) y 17
  (`mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR`, `0x1518`), con los
  índices `0x52C-0x52F` / offsets `0x14B0-0x14BC`, todos dentro de la ventana
  BAR5 de `0x40000`. Eso obliga a actualizar el enum, `RX550_REG_NR`
  (39 → 43) y las comprobaciones M12/M13 de `test_mmio_access.c`.

Ese trabajo **está especificado y es de bajo riesgo**, pero es una decisión de
alcance, no una corrección: el componente funciona igual sin él y el
`NOT_DETERMINED` no se cierra escribiéndolo, se cierra midiéndolo.

## Lo que cerraría el `NOT_DETERMINED`

En orden de coste, y **ninguno es accesible todavía**:

1. `READ_ONLY` de los nueve registros con el driver actual en la máquina.
   Es lo único que da el valor **de nuestra generación**. Requiere el mismo
   takeover que el resto del MMIO.
2. Extraer el bloque GART de `gmc_8_1_enum.h` buscando un enum de reset.
   Coste bajo, resultado esperable `NOT_FOUND` dado el filtro de §FALTANTE-1
   del hallazgo de valores de reset.
3. Las cuatro pistas de atombios, para fijar la versión de MMHUB de Polaris12.

## Tabla de los nueve registros, por completitud

De `gmc_8_1_d.h`, todos con byte offset dentro de la ventana BAR5:

| registro | índice | byte offset | en nuestra tabla |
|---|---|---|---|
| `mmVM_PRT_APERTURE0_LOW_ADDR` | `0x52C` | `0x14B0` | no |
| `mmVM_PRT_APERTURE1_LOW_ADDR` | `0x52D` | `0x14B4` | no |
| `mmVM_PRT_APERTURE2_LOW_ADDR` | `0x52E` | `0x14B8` | no |
| `mmVM_PRT_APERTURE3_LOW_ADDR` | `0x52F` | `0x14BC` | no |
| `mmVM_PRT_APERTURE0_HIGH_ADDR` | `0x530` | `0x14C0` | no |
| `mmVM_PRT_APERTURE1_HIGH_ADDR` | `0x531` | `0x14C4` | no |
| `mmVM_PRT_APERTURE2_HIGH_ADDR` | `0x532` | `0x14C8` | no |
| `mmVM_PRT_APERTURE3_HIGH_ADDR` | `0x533` | `0x14CC` | no |
| `mmVM_PRT_CNTL` | `0x534` | `0x14D0` | no |

## Lo que este hallazgo NO dice

- **No dice que el GART quede mal por no programarlas.** El plan programa la
  tabla y sus 34 escrituras; estas cuatro son de otra función.
- **No dice quearlas sean seguras de escribir a ciegas.** No lo son: son un
  RMW sobre un valor de reset desconocido, y §43 lo prohíbe por escrito.
- **No dice que PRT sea alcanzable desde aquí.** No lo es, hoy.
- **No toca hardware.** Cero escrituras, cero registros leídos.