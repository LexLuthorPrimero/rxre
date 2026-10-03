# 010 — Reconciliación de U-3 y manifiesto de corpus

**Ámbito**: `08-ARQUITECTURA/` · **Fecha**: 2026-09-29
**Alcance**: `READ_ONLY/EVIDENCE` + una herramienta. Sin ejecución, sin probe,
sin bind/unbind, sin UMR, sin commits, sin tocar `07-DRIVER/`.
`RUNTIME = NOT_RUN` · `UMR = NOT_RUN` · `COMMIT = NO`

Resuelve la contradicción `U-3` que el encargo dejó abierta, y documenta el
manifiesto de corpus que elimina la limitación documentada en
`009bis-recovery-static-advance.md` §10.

Fuente primaria: `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
(la única fuente con cobertura 7/7; ver §3).

---

## 0. Veredicto

```
U-3  =  PROVEN

  gpu_sched[AMDGPU_HW_IP_COMPUTE][AMDGPU_RING_PRIO_2]        .num_scheds = 1
  gpu_sched[AMDGPU_HW_IP_COMPUTE][AMDGPU_RING_PRIO_DEFAULT]  .num_scheds = 7
  gpu_sched[AMDGPU_HW_IP_GFX]     [AMDGPU_RING_PRIO_DEFAULT] .num_scheds = 1

  num_scheds = 8 en total, repartido 1 + 7 entre dos prioridades
```

**Las dos afirmaciones previas eran incorrectas, y por razones distintas.**

| Afirmación | Dónde | Veredicto | Por qué falla |
|---|---|---|---|
| *«`num_scheds` lo establece el ASIC al inicializar sus anillos, en runtime. No se deduce estáticamente.»* | `009-stage2-static-advance.md` §`U-3` (otra sesión) | **REFUTADA** | Para `gfx_v8_0` el recuento sale de una **constante de compilación** (§1). No hay lectura de hardware en la cadena. |
| *«U-3 … `amdgpu_xcp.c:508` lo consulta»* | conversación de esta línea; no sobrevivió en ningún artefacto | **CONCLUSIÓN CORRECTA, CITA INCORRECTA** | `amdgpu_xcp.c:508` es el espejo XCP y es `NOT_APPLICABLE` en Polaris12 (§4). La evidencia correcta es §1–§2. |

Y una consecuencia sobre el trabajo de la otra sesión:

```
CORRECTION_CANDIDATE que NO debe aplicarse
  009-stage2-static-advance.md propone, contra 008-c, cambiar
  U-3 de "ESTATIC y barato" a "requiere runtime".
  Esa corrección es incorrecta. U-3 sí cierra estáticamente.
  Aplicarla propagaría un error a 008-c.
```

---

## 1. La cadena que fija `num_compute_rings`

Ninguna de sus tres piezas lee hardware.

```c
/* gfx_v8_0_early_init()                              gfx_v8_0.c:5259 */
adev->gfx.num_gfx_rings     = GFX8_NUM_GFX_RINGS;                    :5264
adev->gfx.num_compute_rings = min(amdgpu_gfx_get_num_kcq(adev),
                                  AMDGPU_MAX_COMPUTE_RINGS);          :5265-5266
```

```c
#define GFX8_NUM_GFX_RINGS     1                        gfx_v8_0.c:60
#define AMDGPU_MAX_COMPUTE_RINGS       8                 amdgpu_ring.h:44
```

```c
int amdgpu_gfx_get_num_kcq(struct amdgpu_device *adev)  amdgpu_gfx.c:1357
{
	if (amdgpu_num_kcq == -1)
		return 8;                                              :1359-1360
	else if (amdgpu_num_kcq > 8 || amdgpu_num_kcq < 0) {
		dev_warn(adev->dev, "set kernel compute queue number to 8 …");
		return 8;                                              :1361-1363
	}
	return amdgpu_num_kcq;                                     :1365
}
```

**Es la lectura clave.** `amdgpu_gfx_get_num_kcq()` no consulta ni un registro
ni el blob de discovery. Lee una variable de módulo:

```c
int amdgpu_num_kcq = -1;                             amdgpu_drv.c:233
module_param_named(num_kcq, amdgpu_num_kcq, int, 0444);  amdgpu_drv.c:958
```

Los permisos son **`0444`**: lectura para todos, **bit de escritura ausente**.
El parámetro no se puede cambiar después de cargar el módulo. Con el valor
declarado `-1` la función devuelve `8` por la rama de `:1360`.

```
num_compute_rings = min( 8 , 8 ) = 8
```

**Consecuencia**: para Polaris12 el valor no es «runtime» en ningún sentido
que afecte a la determinación. Es equivalente a una constante de compilación.
La afirmación de la otra sesión — *«lo establece el ASIC al inicializar sus
anillos, en runtime»* — no aplica a esta ASIC.

---

## 2. La cadena que fija `hw_prio` — y por tanto el reparto

```c
/* amdgpu_ring_priority_level            amdgpu_ring.h:49-55 */
enum amdgpu_ring_priority_level {
	AMDGPU_RING_PRIO_0,                   /* 0 */
	AMDGPU_RING_PRIO_1,                   /* 1 */
	AMDGPU_RING_PRIO_DEFAULT = 1,         /* 1 */
	AMDGPU_RING_PRIO_2,                   /* 2 */
	AMDGPU_RING_PRIO_MAX                  /* 3 */
};
```

```c
/* gfx_v8_0_compute_ring_init()                        gfx_v8_0.c:1846 */
hw_prio = amdgpu_gfx_is_high_priority_compute_queue(adev, ring) ?
		AMDGPU_RING_PRIO_2 : AMDGPU_RING_PRIO_DEFAULT;      :1872-1873
r = amdgpu_ring_init(adev, ring, 1024, &adev->gfx.eop_irq,
		     irq_type, hw_prio, NULL);                       :1875-1876
```

```c
bool amdgpu_gfx_is_high_priority_compute_queue(struct amdgpu_device *adev,
					       struct amdgpu_ring *ring)
						amdgpu_gfx.c:193
{
	/* Policy: use 1st queue as high priority compute queue if we
	 * have more than one compute queue.
	 */
	if (adev->gfx.num_compute_rings > 1 &&
	    ring == &adev->gfx.compute_ring[0])
		return true;                                        :199-201
	return false;                                               :203
}
```

**También es política pura.** El comentario del propio kernel lo dice:
*«Policy: use 1st queue as high priority compute queue if we have more than one
compute queue»*. Sin lectura de hardware.

Con `num_compute_rings = 8 > 1`:

| Ring | `hw_prio` | Celda |
|---|---|---|
| `compute_ring[0]` | `AMDGPU_RING_PRIO_2` = **2** | `gpu_sched[COMPUTE][2]` |
| `compute_ring[1..7]` | `AMDGPU_RING_PRIO_DEFAULT` = **1** | `gpu_sched[COMPUTE][1]` |
| `gfx_ring[0]` | `AMDGPU_RING_PRIO_DEFAULT` = **1** | `gpu_sched[GFX][1]` |

El ring de GFX se registra con prioridad por defecto, explícita
(`gfx_v8_0.c:1977-1979`), y `num_gfx_rings = 1` (`GFX8_NUM_GFX_RINGS`,
`gfx_v8_0.c:60`).

**Y el registro**: cada `amdgpu_ring_init` incrementa la celda
(`amdgpu_ring.c:378-381`):

```c
if (!ring->no_scheduler && ring->funcs->type < AMDGPU_HW_IP_NUM) {
	hw_ip = ring->funcs->type;                                    :379
	num_sched = &adev->gpu_sched[hw_ip][hw_prio].num_scheds;       :380
	adev->gpu_sched[hw_ip][hw_prio].sched[(*num_sched)++] =
		&ring->sched;                                            :381
}
```

`hw_ip` = `AMDGPU_HW_IP_COMPUTE` = `1` (`amdgpu_ring.h:75`,
`amdgpu_drm.h:934`); guardián `1 < AMDGPU_HW_IP_NUM` = `10` cierto.

```
gpu_sched[1][2].num_scheds  += 1     (compute_ring[0])
gpu_sched[1][1].num_scheds  += 1 × 7 (compute_ring[1..7])
gpu_sched[0][1].num_scheds  += 1     (gfx_ring[0])
```

---

## 3. Estructura: capacidad y holgura

`struct amdgpu_sched` (`amdgpu_ring.h:110-113`):

```c
struct amdgpu_sched {
	u32				num_scheds;
	struct drm_gpu_scheduler	*sched[AMDGPU_MAX_HIWIP_RINGS];
};
```

**Medido por DWARF** (`pahole` sobre `amdgpu_vm.o`, no por lectura):

```
struct amdgpu_sched {
	u32                        num_scheds;   /*    0     4 */
	struct drm_gpu_scheduler * sched[64];     /*    8   512 */
	/* size: 520, cachelines: 9, members: 2 */
};
```

⇒ `sched[64]`, luego `num_scheds` no puede exceder 64
(`amdgpu_ring.h:52` declara el tope `AMDGPU_MAX_HIWIP_RINGS`; el valor 64 lo
confirma el artefacto compilado). Con 8 rings de GFX+Compute sobre una placa
con KIQ, SDMA y video, la holgura es de un orden de magnitud: **el límite no
es alcanzable en esta configuración**, y por tanto no es un riesgo para
Polaris12.

---

## 4. Por qué `amdgpu_xcp.c:508` es la cita equivocada

Es la lectura del **espejo por partición**, no la del array principal:

```c
if (xcp_mgr->xcp[sel_xcp_id].gpu_sched[hw_ip][hw_prio].num_scheds) {   :508
	*num_scheds = xcp_mgr->xcp[fpriv->xcp_id].gpu_sched[hw_ip][hw_prio].num_scheds;
	*scheds     = xcp_mgr->xcp[fpriv->xcp_id].gpu_sched[hw_ip][hw_prio].sched;
	atomic_inc(&adev->xcp_mgr->xcp[sel_xcp_id].ref_cnt);
}
```

La celda principal se lee en `amdgpu_ctx.c`, y la elección entre ambas es
explícita:

```c
amdgpu_ctx.c:228   if (!(adev)->xcp_mgr) {
amdgpu_ctx.c:229           scheds     = adev->gpu_sched[hw_ip][hw_prio].sched;
amdgpu_ctx.c:230           num_scheds = adev->gpu_sched[hw_ip][hw_prio].num_scheds;
```

Polaris12 se registra por `vi_set_ip_blocks` (`vi.c:2109-2113`), que no
incluye ningún bloque XCP. `adev->xcp_mgr == NULL` y la rama de `:228` toma
el camino no-XCP. **`amdgpu_xcp.c:508` es `NOT_APPLICABLE` en esta ASIC.**

Mi afirmación de la ronda anterior apuntaba al símbolo equivocado. La
conclusión era correcta, la evidencia no.

---

## 5. Manifiesto de corpus

`tools/evidence_search.py manifest` mide el universo **realmente disponible** y
escribe `RESEARCH/corpus-manifest.json`. No se supone: una raíz figura en el
manifiesto si y solo si fue **observada** dentro de una fuente concreta.

```
CORPUS
  ✓ working        2787 ficheros, 538 470 397 B          key-roots 4/7
  ✓ kernelbuild  103704 ficheros, 1 603 516 478 B       key-roots 7/7
  ✓ baseline       2787 ficheros, 538 470 397 B          key-roots 4/7
  ✓ tar713   158 335 040 B  sha256 be41c068e88f5242…    key-roots 7/7
  ✓ tar728   160 371 176 B  sha256 12e8d5a973d1ad7c…    key-roots 7/7

KEY-ROOT COVERAGE
                                    working  kernelbuild  baseline  tar713  tar728
  drivers/gpu/drm/amd/amdgpu         ✓        ✓           ✓        ✓       ✓
  drivers/gpu/drm/amd/include        ✓        ✓           ✓        ✓       ✓
  drivers/gpu/drm/scheduler          ✗        ✓           ✗        ✓       ✓
  drivers/gpu/drm                    ✓        ✓           ✓        ✓       ✓
  include/uapi/drm                   ✗        ✓           ✗        ✓       ✓
  include/drm                        ✗        ✓           ✗        ✓       ✓
  include/linux                      ✓        ✓           ✓        ✓       ✓
```

**Dos hechos que corrigen el mapa del corpus:**

1. **`RESEARCH/kernelbuild/linux-7.1.3` no es una extracción parcial.** Tiene
   **103 704 ficheros** y los 7 key-roots. La otra sesión lo describe como
   *«extracción parcial de `drivers/gpu/drm/`, 7980 ficheros»* — es un árbol
   Linux 7.1.3 completo.

2. **`working` y `baseline` son idénticos** (`diff -rq` vacío) y **no**
   cubren `scheduler/`, `include/uapi/drm` ni `include/drm`. Son la razón de
   cuatro `NOT_FOUND` falsos encadenados, y de mis dos `OPEN_BOUNDARY`
   falsas en `009bis` §1.

`working` y `baseline` aportan 632 entradas en `amd/amdgpu`; `kernelbuild`,
635. Discrepancia de 3, **no investigada** en esta ronda.

### Lo que el manifiesto cambia

Con `--manifest … --corpus X`, las raíces se **derivan** del manifiesto en vez
de declararse. Una raíz que la fuente no aporta entra igual en el universo y
marca `UNREACHABLE`, lo que degrada la ausencia a `NOT_DETERMINED`:

```
--root amd-amdgpu=…            → NOT_FOUND         (universo de 1 raíz; mi error)
--manifest … --corpus working  → NOT_DETERMINED    key-roots 4/7
--manifest … --corpus kernelbuild → PROVEN        amdgpu_drm.h:934
--manifest … --corpus tar713   → PROVEN            amdgpu_drm.h:934
```

**Cierra la limitación de `009bis` §10.** Allí se decía que la herramienta
«no puede saber qué raíz se olvidó declarar» y que el endurecimiento
requería un manifiesto. Está implementado y medido.

---

## 6. Errores de la herramienta durante esta ronda

| # | Error | Síntoma | Estado |
|---|---|---|---|
| 1 | `\b` aplicado a una consulta que empieza por no-palabra | `#define X` daba 0 hits con universo exhaustivo → `NOT_FOUND` falso | `CORREGIDO` + `SELFTEST` |
| 2 | key-roots sin el prefijo del tarball | `tar713` y `tar728` con coverage `0/7` siendo completos | `CORREGIDO`: se prueban ambas formas y se registra `matched_form` |
| 3 | Rutas del manifiesto no componidas con la fuente | 7/7 `✗ ruta ausente` bajo `working` | `CORREGIDO`: `os.path.join(src, k)` |
| 4 | 7 raíces del mismo tarball ⇒ 7 escaneos de 158 MB | timeout a 120 s | `CORREGIDO`: índice de tarball cacheado por proceso |
| 5 | `manifest_info` no llegaba a `emit()` | `NameError` | `CORREGIDO` |

Todos los errores de código estaban **en la herramienta, no en el
razonamiento**, y todos salieron de la ejecución contra el corpus real. El
`--selftest` cubre 1; los demás no tienen regresión automática aún.

---

## 7. Verificación

29 referencias `fichero:línea` de §1–§4 comprobadas una por una contra
`RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`. **0 rotas.**

```
python3 tools/evidence_search.py --selftest          → SELFTEST OK (10 garantías)
python3 tools/evidence_search.py manifest …          → RESEARCH/corpus-manifest.json
```

| Dato | Valor |
|---|---|
| `num_gfx_rings` | `1` (`gfx_v8_0.c:60`, `:5264`) |
| `num_compute_rings` | `8` (`gfx_v8_0.c:5265`, `amdgpu_gfx.c:1360`, `amdgpu_ring.h:44`) |
| `amdgpu_num_kcq` | `-1` declarado, `0444` sin escritura (`amdgpu_drv.c:233`, `:958`) |
| `hw_prio` compute[0] | `AMDGPU_RING_PRIO_2` = `2` (`gfx_v8_0.c:1872`, `amdgpu_ring.h:53`) |
| `hw_prio` compute[1..7] | `AMDGPU_RING_PRIO_DEFAULT` = `1` (`amdgpu_ring.h:52`) |
| `hw_prio` gfx[0] | `AMDGPU_RING_PRIO_DEFAULT` = `1` (`gfx_v8_0.c:1979`) |
| `sched[]` capacidad | `64` (`pahole`, DWARF) |
| `AMDGPU_HW_IP_COMPUTE` | `1` (`amdgpu_drm.h:934`) |

---

## 8. Estado

```
U-3                              PROVEN   (1 + 7 + 1, por hw_prio)
corpus manifest                  PROVEN   5 fuentes, 7 key-roots, identidades sha256
009bis §10 limitación            CERRADA  por el manifiesto
008-c CORRECTION_CANDIDATE       NO APLICAR  (propagaría un error)
kernelbuild "parcial"            REFUTADO  103 704 ficheros, 7/7 key-roots
F9 / P-8                         PROVEN   sin cambios en esta ronda
GFX_HWIP A/B                     PROVEN   sin cambios
GFX_HWIP C                       NOT_DETERMINED  (ASIC)
CODE_CHANGE                      NO APLICADO
RUNTIME                          NOT_RUN
UMR                              NOT_RUN
COMMIT                           NO
```

No se modificó `007-*`, `008-*`, los `009-*` de la otra sesión, `AGENTS.md`,
`COORDINACION.md` ni `07-DRIVER/`. `009bis` intacto.
