# 1033 · Siete revisiones adversariales: lo que cayó, lo que se sostuvo, y un `NOT_DETERMINED` que se cerró

`CLASSIFICATION=CONTRADICTION_RESOLVED` · `TRACK=STATIC + HOST_OBSERVATION`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=READ_ONLY/EVIDENCE + REPAIR` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=11`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## Qué es esto

Siete revisiones independientes, sin acceso a la conclusión de las demás, sobre
los hallazgos de esta sesión y sobre el corpus. Este documento no resume lo que
dijeron: **compara lo que dijeron con lo que está en el árbol**, y sólo escribe
una cosa: **qué cambió**.

Tres refutaciones han resultado en conocimiento nuevo, y ninguna en daño. Y una
pregunta mia resulto ser falsa.

---

## R1 · La columna `access` no es del corpus, y eso hunde la foundation del 1031

**El hallazgo 1031 se clasificó `MEASUREMENT`. No lo era.** Medido:

```
gmc_8_1_d.h        :  "RW"=0   "W"=0   "access"=0
gmc_8_1_sh_mask.h  :  "RW"=0   "W"=0   "access"=0
```

Son listas planas de `#define` de índice y de `__MASK`/`__SHIFT`. **Un `#define`
de índice no puede expresar un permiso de lectura.** La columna `access` de
`rx550_vmid1_regs[]` es una **anotación de este proyecto**, y el 1031 la
argumentaba diciendo que una lista propia «se desincronizaría el día que **el
corpus** cambiase un `W` por un `RW`». El corpus no tiene el campo.

**Corrección aplicada.** `rx550_mmio_access.h` documenta ahora que la columna es
del proyecto, con el recuento de `RREG32` por mnemónico en todo
`drivers/gpu/drm/amd`:

| registro | `RREG32` en el corpus |
|---|---|
| `mmVM_CONTEXT1_CNTL` | 11 |
| `mmVM_CONTEXT0_CNTL` | 8 |
| `mmMC_VM_MX_L1_TLB_CNTL` | 4 |
| `mmVM_L2_CNTL` | 4 |
| `mmVM_L2_CNTL3` | 2 |
| `mmVM_L2_CNTL2` | 1 |
| `mmVM_L2_CNTL4` | 1 |
| **`mmVM_CONTEXT0_CNTL2`** | **0** |
| **`mmVM_CONTEXT1_CNTL2`** | **0** |

Los dos CNTL2 están marcados `"RW"` y **no tienen ni una lectura en todo el
driver de referencia**: se escriben a ciegas (`L892`, `L922`). Su
verificabilidad por lectura es `NOT_DETERMINED`, no `OBSERVED`.

> El hallazgo 1031 pasa de `MEASUREMENT` a derivación sobre una entrada no
> verificada. **La conclusión operativa —no exigir igualdad a los no
> verificables— sigue siendo defendible como política conservadora, pero no está
> probada por el corpus y no se vendía como medida.**

## R2 · `PAGE_TABLE_BLOCK_SIZE` del contexto 0: de `NOT_DETERMINED` a `CORROBORATED`, valor 0

**Cerrado, y por dos caminos que el hallazgo no buscó.**

**El valor de reset sí está en el corpus**, en los `*_default.h`:

```
include/asic_reg/mmhub/mmhub_1_0_default.h:682
    #define mmVM_CONTEXT0_CNTL_DEFAULT   0x007ffe80
```

Decodificado con las máscaras de `gmc_8_1_sh_mask.h`:

| campo | máscara | shift | valor de reset |
|---|---|---|---|
| `PAGE_TABLE_BLOCK_SIZE` | `0x0f000000` | 24 | **0** |
| `PAGE_TABLE_DEPTH` | `0x00000006` | 1 | 0 |
| `ENABLE_CONTEXT` | `0x00000001` | 0 | 0 |
| `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` | `0x10` | 4 | 0 |

**Matiz que hay que decir:** `mmhub_1_0_default.h` es de **otro ASIC** —MMHUB 1.0
es Vega10/GFX9— y para GFX8 **no existe** `gmc_8_1_default.h`. Es evidencia de
un ASIC hermano: `CORROBORATED`, no `PROVEN`.

**El segundo camino es más fuerte y no necesita hardware:**

```c
gmc_v8_0.c:972  static void gmc_v8_0_gart_disable(struct amdgpu_device *adev)
gmc_v8_0.c:976          /* Disable all tables */
gmc_v8_0.c:977          WREG32(mmVM_CONTEXT0_CNTL, 0);
gmc_v8_0.c:978          WREG32(mmVM_CONTEXT1_CNTL, 0);
```

El ciclo real es `suspend → hw_fini → resume → sw_init`, con `gart_disable()` en
la ida y `gart_enable()` en la vuelta. **El RMW de `L893` lee siempre un registro
que el propio driver puso a cero hace un momento.**

Mi pregunta original tenía tres salidas («reset=0 da igual», «a profundidad 0 no
se usa», «reset=otro y funciona por casualidad») y **me faltaba la cuarta, que
es la que vale: nadie depende del valor de reset.**

El discriminante que yo proponía —leer el registro antes y después de un reset—
era innecesario.

## R3 · El hallazgo 1028 afirmaba que no hay escrituras ciegas. No las hay: hay 27

> «Las **34 son `RREG32 → REG_SET_FIELD → WREG32`». No hay ni una sola escritura
> ciega en toda la función.»

**Falso, y no por un número.** Medido: **7 RMW y 27 escrituras directas.** Dos
de cada tres.

Lo que hace el trabajo es que el documento razonaba correctamente sobre por qué
una escritura directa a `mmVM_CONTEXT0_CNTL` pondría a cero 19 campos, mientras
afirmaba en la misma página que ese patrón no ocurría en la función que estaba
transcribiendo.

**El error estaba propagado al driver**: `rx550_mmio_access.h:749` decía «las 21
escrituras son **TODAS** de esa forma». Las dos partes eran falsas, y el 21 ya
había sido corregido en el hallazgo sin llegar al header. Corregido.

## R4 · Las citas de línea que escribí a mano estaban desplazadas una línea

El hallazgo 1028 pasó tres correcciones el mismo día, y las tres por lo mismo:
**contar líneas donde había que contar hechos.**

| lo que decía | real |
|---|---|
| L843 `mmMC_VM_MX_L1_TLB_CNTL` | **L849** |
| L891 `mmVM_CONTEXT0_CNTL2 = 0` | **L892** |
| L893 `mmVM_CONTEXT0_CNTL` | **L897** |
| L921 `mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR` | **L920** |
| L923 `mmVM_CONTEXT1_CNTL2 = 4` | **L922** |
| L925 `mmVM_CONTEXT1_CNTL` | **L935** |

**Todas las que apuntaban al comienzo de una sentencia de dos líneas.** Y las
citas de los **campos** en `rx550_reg_fields[]` **son exactas** — las 27, una a
una. La diferencia es el método: **las generé con un script y escribí estas a
mano.**

Ahora las veinte están regeneradas desde el corpus, y el enum de orden lleva el
número medido al lado. Es la tercera vez que la lección sale en este componente:
**lo generado no se desincroniza; lo escrito a mano sí.**

## R5 · Dos recuentos que usaban dos unidades sin decirlo

- **42 ≠ 39.** Hay **42 pares `(registro, campo)`** y **39 nombres distintos**,
  porque `ENABLE_CONTEXT`, `PAGE_TABLE_DEPTH` y
  `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` se escriben en los dos contextos.
- **`REG_SET_FIELD` son 42**, no 41. El 41 era residuo de una sonda fallida
  anterior.
- **Los 8 campos de más de un bit son 7 nombres**, por la misma razón.

El documento usaba las dos unidades en el mismo texto. Corregido: cada cantidad
dice si cuenta pares o nombres.

## R6 · El corpus no es un árbol upstream limpio

**Hay un driver de este proyecto injertado dentro del corpus:**

```
linux-7.1.3/drivers/gpu/drm/polaris12xl/         existe, con polaris12xl.ko
linux-7.1.3/drivers/gpu/drm/Kconfig:367          source "drivers/gpu/drm/polaris12xl/Kconfig"
linux-7.1.3/drivers/gpu/drm/Makefile:259         obj-$(CONFIG_DRM_POLARIS12XL) += polaris12xl/
```

Las dos costuras son anómalas —Kconfig después del `endif`, Makefile después de
las reglas `hdrtest`— y el único `.ko` de todo el árbol es el suyo. **No hay
`amdgpu.ko`.**

> `RESEARCH/kernelbuild/linux-7.1.3` es *basado en* 7.1.3, no *es* 7.1.3. Cualquier
> frase del proyecto que diga «el corpus» tiene que excluir
> `drivers/gpu/drm/polaris12xl/`. La versión como cadena está verificada
> (`Makefile`, `kernel.release`) y corroborada contra kernel.org; la identidad
> fichero a fichero es `NOT_DETERMINED`.

## R7 · El comentario del corpus contradice a su propio código

```c
gmc_v8_0.c:871     /* XXX: set to enable PTE/PDE in system memory */
gmc_v8_0.c:873-884   doce REG_SET_FIELD(..., VMC_TAP_*, 0)
```

El comentario dice «enable» y el código pone **cero** en los doce. Y no hay
ningún sitio en el árbol que diga cuál de los dos es el pretendido. **Se sigue al
código**, que es lo único ejecutable, y la intención queda `NOT_DETERMINED`.

Esto también corrigió una frase mía: dije que los doce `VMC_TAP` eran campos
«declarados y no escritos, que hay que preservar». **Falso: el corpus los
escribe, a cero.** Por eso están `PROVEN_CORPUS_WRITES` con valor `0` en la tabla,
y por eso el compositor los aplica. El código estaba bien; la prosa no.

## R8 · El `-EBUSY` que yo daba por hecho viene de otro sitio

Yo he repetido que «`target_res_claim_regions()` devolvería `-EBUSY` mientras
amdgpu tenga el dispositivo». **Medido: es falso.**

| | |
|---|---|
| `pci_request_region` en `amdgpu.ko` | **0 apariciones** |
| `pci_iomap` en `amdgpu.ko` | **0** |
| lo que amdgpu usa | `ioremap()`, `ioremap_cache()`, `ioremap_wc()` |
| `pci_request_region` en los 635 fuentes de amdgpu | **0** |
| `amdgpu_device.c:3813-3823` | `pci_resource_start(pdev, 5)` → `ioremap()` |

**amdgpu mapea BAR5 sin reclamar la región.** Así que nuestro
`pci_request_region()` **devolvería 0**, no `-EBUSY`. El `-EBUSY` real lo emite
el core antes de llamar a `probe()`:

```c
drivers/base/dd.c:836-837   if (dev->driver) return -EBUSY;
```

Es decir: **`rx550_target_probe()` no se ejecutaría nunca**, y la rama
`" (ya la posee otro driver)"` de `rx550_target.c:190` **no se alcanza en este
host**. El diagnóstico es correcto; la rama es inalcanzable.

> Consecuencia más seria: **«región reclamada» no distingue «tengo la GPU» de
> «amdgpu tiene la GPU»**. Un test que usara `target_res_claim_regions() == 0`
> como oráculo de posesión daría un **falso verde**. Falta además
> `pci_enable_device()`, que está en `DEFERRED` y prohibido por la auditoría
> estática: sin él no hay `PCI_COMMAND_MEMORY` y el mapa no responde.

## R9 · La función escribe 44 registros, no 34

`gmc_v8_0_gart_enable()` **no termina en la operación 33.** Termina en:

```c
gmc_v8_0.c:936-939   if (amdgpu_vm_fault_stop == AMDGPU_VM_FAULT_STOP_ALWAYS)
                          gmc_v8_0_set_fault_enable_default(adev, false);
                      else
                          gmc_v8_0_set_fault_enable_default(adev, true);
gmc_v8_0.c:940       gmc_v8_0_flush_gpu_tlb(adev, 0, 0, 0);
```

Y esos dos-called escriben **10 registros más**:

- `gmc_v8_0.c:789` `mmVM_PRT_CNTL`
- `gmc_v8_0.c:797-806` ocho `mmVM_PRT_APERTURE*_ADDR`
- `gmc_v8_0.c:665` `mmVM_INVALIDATE_REQUEST`, dentro del flush

**El plan de 34 omite los diez**, y no puede incluirlos tal cual: la rama de
`L936` depende de **`amdgpu_vm_fault_stop`**, un parámetro de módulo en runtime
que elige entre dos conjuntos de valores PRT distintos.

Peor, y esto no lo había visto: **`gmc_v8_0_set_fault_enable_default()` hace un
segundo RMW de `mmVM_CONTEXT1_CNTL`** en `L757`. **El corpus escribe ese registro
dos veces y el plan una.** El valor resultante es idéntico bajo la hipótesis de
que todo venga de cero, pero **esa hipótesis no estaba escrita en ninguna parte**.

**Lo que sí se ha hecho con esto:** el **vaciado de TLB**, que era un `❌ NO
EXISTE` y son seis líneas.

```c
/* rx550_gart_seq.c */
int rx550_gart_tlb_flush(const struct rx550_mmio_map *map, unsigned vmid)
{
	...
	if (vmid >= 16u)
		return RX550_GART_SEQ_ERR_GEOMETRY;
	...
	return rx550_mmio_write32(map, req, (uint32_t)1u << vmid);
}
```

**Y no es un anillo de PM4.** Hay dos funciones con el mismo nombre y la
confusión es fácil:

| | | |
|---|---|---|
| `gmc_v8_0_flush_gpu_tlb()` | `L661-666` | la que usa `gart_enable`: **un `WREG32`** |
| `gmc_v8_0_emit_flush_gpu_tlb()` | `L668-683` | la que usa el ring: `amdgpu_ring_emit_wreg()` |

Se implementa la primera. **Sin `mb()` y sin `flush_hdp`**: la ruta de runtime
(`amdgpu_gart.c:499-505`) sí los hace, pero `gmc_v8_0.c:940` no, y las 34
escrituras anteriores son del mismo mapa y del mismo driver.

**Las 10 escrituras de PRT siguen faltando** y quedan declaradas como
`NOT_IMPLEMENTED` con la razón: dependen de un parámetro de módulo en runtime, y
elegir una de las dos ramas sin evidencia sería inventar.

## R10 · El oráculo de la 1030 no existe como artefacto

La 1030 dice «las 34 operaciones coinciden con un oráculo escrito aparte». **El
oráculo era un heredoc de shell en `/tmp`, sin fichero, sin hash y sin comando.**
No es evidencia auditable, que es lo que exigen las reglas de procedencia del
proyecto.

**Corrección aplicada:** el contenido del oráculo se ha re-ejecutado y las 34
siguen coincidiendo, pero **deja de presentarse como evidencia sin artefacto** y
pasa a `OBSERVED_UNREPRODUCIBLE` con la transcripción citada en el commit.

## Lo que se sostuvo, y por qué importa que se sostenga

| afirmación | veredicto |
|---|---|
| 34 escrituras, 19 explícitas + 15 del bucle | confirmada, dos veces, por dos revisores |
| 42 `REG_SET_FIELD`, 42 pares, 39 nombres | confirmada |
| invariante `(mask>>shift) == 2^ancho−1` sin excepciones | confirmada contra `gmc_8_1_sh_mask.h` |
| `__SHIFT == trailing_zeros(MASK)` en los 42 | confirmada |
| `PAGE_TABLE_DEPTH` ctx0=0, ctx1=1 | confirmada literalmente |
| `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + 1 = 0x550` | confirmada en corpus, header y driver |
| dummy page = `ttm_glob.dummy_read_page`, `DMA_BIDIRECTIONAL` | confirmada |
| la ventana del GART **no** tiene que caber en la del VM | confirmada |
| 55 campos, 26→39 registros, 14 TU, 11 bajo kbuild | confirmadas |

## Un defecto que no es de este trabajo

La auditoría del directorio de hallazgos encontró que
`050-la-frontera-ordenada-por-su-via-de-cierre.md` son **8619 bytes de NUL puro**.
No es un hallazgo sin numerar: es un fichero corrupto que ocupa uno de los 74
números duplicados.

Y encontró que **16 de las 84 macros de los campos tienen definiciones
conflictivas** en el corpus: `PAGE_TABLE_BLOCK_SIZE_MASK` es `0xf000000` en
`gmc_8_1` y `0x78` en `mmhub_1_0` y `gc_9_0`.

> Por eso «comprobable contra el corpus entero», que dice la 1028, es **falso**:
> indexar el corpus entero sin fijar el header devuelve `0x78`. La regla es
> «comprobable contra `gmc_8_1_sh_mask.h`». Corregido.

## Lo que NO dice

- **No dice que el corpus sea incorrecto para nuestra ASIC.** Dice que no es
  limpio, y que tiene un contradictorio interno documentado.
- **No dice que las 10 escrituras de PRT sean innecesarias.** Dice que son
  replication-dependent y que elegirlas sería inventar.
- **No dice que `access` sea falso.** Dice que es una decisión del proyecto, y que
  2 de los 9 que marcados como legibles no tienen lectura en el corpus.
- **No toca el hardware.** Cero escrituras, cero registros leídos.

## Trazabilidad

- Corpus: `include/asic_reg/mmhub/mmhub_1_0_default.h:682`;
  `gmc_v8_0.c:661-666, 789, 797-806, 871-884, 936-940`;
  `drivers/base/dd.c:836`; `amdgpu_device.c:3813-3823`
- Injerto: `drivers/gpu/drm/Kconfig:367`, `drivers/gpu/drm/Makefile:259`
- Correcciones aplicadas: `rx550_mmio_access.h` (columna `access`, «21 escrituras
  todas RMW»), `rx550_mmio_access.c` (citas de 7 entradas, tabla de 39),
  `rx550_gart_seq.c`/`h` (orden con líneas medidas, VMC_TAP, lista de 3
  simbólicos), `test_update_field.c`, `test_mmio_access.c`, `test_gart_apply.c`
- Hallazgos reparados: `1028` (tres correcciones), `1030` (citas y oráculo)
- Prefijo de numeración: 1033, reservado antes de escribir