# 143 · §C: los "registros golden" de esta GPU son cuatro escrituras, y el PRT es un contador de referencias

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

1. **El conjunto completo de "registros golden" de esta GPU**: cuatro escrituras, y
   ninguna más. El nombre `golden_settings_polaris11_a11` sugiere ajuste por chip y
   **no lo hay**.
2. **El ciclo de vida completo del PRT**, que es un **contador de referencias**, y
   con él queda cerrada la cadena que empezó en `099` y pasó por `131`, `139` y
   `142`.
3. **El fichero de registros del PRT entero, por primera vez, en un mapa.**

**Y un resultado negativo sobre mi propio método, que va al final y es obligatorio.**

## 1 · Los registros golden de esta GPU: cuatro escrituras

`gmc_v8_0.c:121-167`, `gmc_v8_0_init_golden_registers`, 48 líneas de `switch`. Y
`CHIP_POLARIS12` cae en el mismo caso que `POLARIS11` y `VEGAM`:

```c
case CHIP_POLARIS11:
case CHIP_POLARIS12:
case CHIP_VEGAM:
        amdgpu_device_program_register_sequence(adev,
                                                golden_settings_polaris11_a11,
                                                ARRAY_SIZE(golden_settings_polaris11_a11));
        break;
```

**Y la tabla, `gmc_v8_0.c:92-97`, completa:**

```c
static const u32 golden_settings_polaris11_a11[] = {
        mmVM_PRT_APERTURE0_LOW_ADDR, 0x0fffffff, 0x0fffffff,
        mmVM_PRT_APERTURE1_LOW_ADDR, 0x0fffffff, 0x0fffffff,
        mmVM_PRT_APERTURE2_LOW_ADDR, 0x0fffffff, 0x0fffffff,
        mmVM_PRT_APERTURE3_LOW_ADDR, 0x0fffffff, 0x0fffffff
};
```

**Cuatro tripletas, un solo registro repetido cuatro veces, un solo valor.** Eso es
todo lo que esta GPU recibe como "golden registers", y es la primera llamada de
`gmc_v8_0_hw_init` (`L1208`). `PROVEN`.

### Y la tabla no es de Polaris11

Comparando el contenido de las cinco tablas golden del fichero, impreso por
programa:

| tabla | entradas | sha256 del contenido (12) |
|---|---|---|
| `golden_settings_tonga_a11` (`L67`) | 7 | `c9bbb750f4e4` |
| `golden_settings_fiji_a10` (`L81`) | 4 | **`3d9e17ec629d`** |
| `golden_settings_polaris11_a11` (`L92`) | 4 | **`3d9e17ec629d`** |
| `golden_settings_polaris10_a11` (`L99`) | 5 | `c5ff4590d72a` |
| `golden_settings_stoney_common` (`L116`) | 1 | `2e38e77b22c3` |

**`golden_settings_fiji_a10` y `golden_settings_polaris11_a11` son byte-idénticas.**
Una GPU Fiji y una RX550 reciben exactamente las mismas cuatro escrituras. Tonga y
Polaris10 tienen más entradas y sí difieren.

**El nombre `polaris11_a11` no describe el contenido: lo describe el chip para el
que se escribió primero.** Para un driver propio esto importa: **copiar la tabla
"de Polaris11" es copiar cuatro escrituras que no tienen nada de específico de
Polaris**, y no hay nada más que copiar. `PROVEN`.

### Y esta GPU no recibe ajustes de clock gating

Fiji, Tonga, Carrizo y Stoney programan antes una tabla `*_mgcg_cgcg_init`. **El
caso de Polaris no.** Y `gmc_v8_0.c:1667-1684` lo confirma:

```c
switch (adev->asic_type) {
case CHIP_FIJI:
        fiji_update_mc_medium_grain_clock_gating(adev, state == AMD_CG_STATE_GATE);
        fiji_update_mc_light_sleep(adev, state == AMD_CG_STATE_GATE);
        break;
default:
        break;
}
```

**En esta GPU el clock gating y el light sleep del controlador de memoria no se
programan nunca.** `PROVEN_ABSENT`, y es coherente con que `fiji_update_mc_*` sean
las únicas implementaciones y con que el `default` no haga nada.

**Y hay una asimetría que conviene conocer:** `gmc_v8_0_get_clockgating_state`
(`L1694`) **no** tiene ese `switch` — lee `mmMC_HUB_MISC_HUB_CG` y
`mmMC_HUB_MISC_HUB_CG__MEM_LS_ENABLE_MASK` para **todas** las GPU. **Así que el
driver informa de capacidades de clock gating que en esta GPU nunca se
programaron.** No es un bug —el registro se lee, no se escribe— pero un driver
propio no debe confiar en ese informe para decidir que puede gatear. `PROVEN`.

## 2 · El fichero de registros del PRT, entero, por primera vez

Ocho aperturas más el control, **y son contiguos**:

| registro | offset |
|---|---|
| `mmVM_PRT_APERTURE0_LOW_ADDR` | `0x52c` |
| `mmVM_PRT_APERTURE1_LOW_ADDR` | `0x52d` |
| `mmVM_PRT_APERTURE2_LOW_ADDR` | `0x52e` |
| `mmVM_PRT_APERTURE3_LOW_ADDR` | `0x52f` |
| `mmVM_PRT_APERTURE0_HIGH_ADDR` | `0x530` |
| `mmVM_PRT_APERTURE1_HIGH_ADDR` | `0x531` |
| `mmVM_PRT_APERTURE2_HIGH_ADDR` | `0x532` |
| `mmVM_PRT_APERTURE3_HIGH_ADDR` | `0x533` |
| `mmVM_PRT_CNTL` | **`0x534`** |

**`0x52c` a `0x534`, nueve registros consecutivos, sin huecos.** `131` encontró
`0x534` contando siete campos; `139` encontró el nombre de los siete; esta nota
cierra el bloque entero. **Y explica por qué `131` buscó un solo registro: era el
último de un bloque de nueve, y el bloque no tiene nombre propio en ninguna parte.**

**Y las cuatro aperturas son cuatro rangos disjuntos** — de ahí el plural, y de ahí
que el control sea global y los rangos independientes. `PROVEN_DERIVED`.

### El ancho, y una corroboración cruzada con `138`

La máscara de los golden registers es `0x0fffffff`, **28 bits**. Y `138` encontró
que `VM_CONTEXT1_PROTECTION_FAULT_ADDR__LOGICAL_PAGE_ADDR` es `0xfffffff`,
**también 28 bits**, y que el driver lo desplaza por `AMDGPU_GPU_PAGE_SHIFT`.

**Dos registros distintos, los mismos 28 bits, los dos números de página de 4 KiB.**
2^28 páginas = **1024 GiB** de rango. Uno dice dónde falló un acceso; el otro
declara un rango donde no deben fallar. `CORROBORATED`.

## 3 · El PRT es un contador de referencias, y su ciclo entero

`amdgpu_vm.c:1431-1452`:

```c
static void amdgpu_vm_update_prt_state(struct amdgpu_device *adev)
{
        unsigned long flags;
        bool enable;

        spin_lock_irqsave(&adev->vm_manager.prt_lock, flags);
        enable = !!atomic_read(&adev->vm_manager.num_prt_users);
        adev->gmc.gmc_funcs->set_prt(adev, enable);
        spin_unlock_irqrestore(&adev->vm_manager.prt_lock, flags);
}

static void amdgpu_vm_prt_get(struct amdgpu_device *adev)
{
        if (!adev->gmc.gmc_funcs->set_prt)
                return;
        if (atomic_inc_return(&adev->vm_manager.num_prt_users) == 1)
                ...
```

**El estado del PRT es global a la GPU, con recuento de usuarios, y sólo cambia en
las transiciones 0→1 y 1→0.** `PROVEN`.

### El ciclo completo, con lo que escribe en cada fase

| fase | quién | qué escribe |
|---|---|---|
| **arranque** | `gmc_v8_0.c:92-97` (golden) | los **cuatro `LOW`** = `0x0fffffff` |
| **0 usuarios** | `set_prt(false)` (`L806-815`) | 4 `LOW` = `0xfffffff` **y** 4 `HIGH` = `0x0` |
| **≥1 usuario** | `set_prt(true)` (`L792-805`) | 4 `LOW` + 4 `HIGH` al rango real, **y** `VM_PRT_CNTL` con los 7 bits, **y** el `dev_warn` |
| **soltar** | `atomic_dec` → 0 → `update_prt_state` | vuelve a `set_prt(false)` |

**Y los golden registers escriben exactamente el valor de "desactivado"** —`0x0fffffff`
en los `LOW`— que es lo que escribe el camino `false` de `set_prt`. **El estado de
arranque y el estado de desactivado coinciden en los cuatro `LOW`.** `PROVEN`.

**Eso deja un hueco honesto, y no lo voy a tapar:** los golden registers **no**
escriben los cuatro `HIGH`. Si el valor de reset del hardware de `0x530`–`0x533` no
fuera cero, el rango de arranque no estaría vacío. **No hay forma de saberlo desde
el corpus**: es el valor de reset, y verlo es un `RREG32`. `NOT_DETERMINED`.

**Pero el hueco es menor de lo que parece:** la primera transición 0→1 escribe los
ocho, y `set_prt(false)` también. **Los ocho registros sólo quedan sin programar
entre el arranque y el primer `prt_get`, y ese estado no lo consulta nadie.** El
impacto real, si lo hay, es que un protection fault en esa ventana no tendría
rango PRT que applies — lo que significaría que **no** se silencia, que es el
comportamiento prudente. `PROVEN_DERIVED`, y anotado como tal.

### Y esto cierra la cadena de `099`, de una vez

| nota | qué Contribution |
|---|---|
| `099` | observó PRT dispararse |
| `131` | encontró `VM_PRT_CNTL` = `0x534` con 7 campos |
| `139` | separó `AMDGPU_PTE_PRT` (bit 51, reservado) de `VM_PRT_CNTL` |
| `142` | dejó la apertura AGP vacía y el bloque HDP |
| **`143`** | **el PRT es un contador global, se silencia por rango, y su `dev_warn` lo dice: "Disabling VM faults because of PRT request"** |

**Un PRT que dispara en esta GPU significa que hay ≥1 usuario de PRT registrado, y
que en ese rango los faults de VM están deliberadamente desactivados.** No es un
fallo, no es una contradicción, y no es un bug: es el diseño. **`099` resuelto
completamente**, con el mecanismo, no sólo con la explicación.

## 4 · Lo que esta GPU necesita, completo, como lista de trabajo

**Con `137`, `138`, `139`, `140` y `143` la lista de arranque de esta GPU está
cerrada en software.** En orden:

1. 160 escrituras HDP a cero, `0xb05 + 0x6*j` — sin nombre, heredadas de GFX6 (`142`)
2. 4 escrituras golden a `0x0fffffff` (`143`)
3. Agp aperture vacía, `AGP_BOT > AGP_TOP` en unidades de 4 MiB (`142`)
4. `mmMC_VM_MX_L1_TLB_CNTL`: 5 campos (`137`)
5. `mmVM_L2_CNTL`: 7 campos (`137`)
6. `mmVM_L2_CNTL2`: 2 invalidaciones (`137`)
7. `mmVM_L2_CNTL3`: `fragment_size` leído del hardware (`137`)
8. `mmVM_L2_CNTL4`: 12 campos a cero (`137`)
9. contexto 0: `PAGE_TABLE_DEPTH = 0`, y la ventana `[gart_start, gart_end]` (`139`, `140`)
10. contextos 1-15: `PAGE_TABLE_DEPTH = 1`, ventana `[0, max_pfn-1]` (`139`)
11. `mmVM_CONTEXT1_CNTL2 = 4` = interrumpir faults subsecuentes (`139`)
12. TLB flush de VMID 0 (`137`)
13. y un invalidate de TLB por cada cambio de page table, **obligatorio** (`136`, `137`)

**Y ninguno de los trece se puede leer de vuelta sin MMIO, y ninguno se imprime.**
Ver §6.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Los golden de esta GPU son 4 escrituras | `PROVEN` |
| `golden_settings_fiji_a10` == `golden_settings_polaris11_a11` | `PROVEN` (sha) |
| Esta GPU no recibe ajustes de clock gating | `PROVEN_ABSENT` |
| `get_clockgating_state` informa de algo no programado | `PROVEN` |
| El bloque PRT es `0x52c`–`0x534`, contiguo | `PROVEN` |
| 28 bits en el rango PRT y en la dirección de fault | `CORROBORATED` |
| El PRT es un contador de referencias | `PROVEN` |
| Los golden = el estado "desactivado" en los `LOW` | `PROVEN` |
| `099` resuelto con el mecanismo | `PROVEN_DERIVED` |
| Los 13 pasos de arranque, en software | `PROVEN_DERIVED` |
| El valor de reset de `0x530`–`0x533` | **`NOT_DETERMINED`** — un `RREG32` |
| Si ese hueco tiene algún efecto observable | **`PROVEN_DERIVED`** que ninguno, y por qué |
| Quién es el primer `prt_get` en esta máquina | **`NOT_DETERMINED`** |
| Cuándo se llama a `amdgpu_vm_prt_get` por primera vez | **`NOT_DETERMINED`** — `CORPUS` |
| Los 160 registros HDP, qué hacen | **`NOT_IN_CORPUS`** (`142`) |
| Cualquiera de los trece valores tras el reset | **`NOT_PROVEN`** — MMIO |

**Las dos primeras filas del final son el mismo hueco y son hardware, y las otras
dos son corpus.** La cuarta —*cuándo se llama `amdgpu_vm_prt_get` por primera vez*—
es `CORPUS` y es la siguiente ruta: un `grep` por los llamadores de
`amdgpu_vm_prt_get` dice si en esta ruta de GFX8 el PRT llega a activarse alguna
vez, o si los cuatro registros golden son el estado permanente.

## Procedencia

- `STATIC` -- `gmc_v8_0.c:67-119` `:121-167` `:766-816` `:1667-1710`,
  `amdgpu_vm.c:1431-1452` `:1487-1492` `:2791`, `gmc_8_1_d.h` (offsets del PRT),
  `gmc_8_1_sh_mask.h` (`LOGICAL_PAGE_ADDR`).
- Comparación de tablas golden: `sha256` del contenido de cada tabla, impreso por
  programa. Los hashes salen idénticos para Fiji y Polaris11.
- Encadenada con `142` (la apertura AGP y el bloque HDP, los dos primeros pasos de
  la lista de §4), `140` (el mapa de direcciones, pasos 3 y 9),
  `139` (la homonimia PRT, el contexto 0, `PAGE_TABLE_DEPTH`, pasos 8-11),
  `138` (la geometría y el `CNTL2`), `137` (pasos 4-8 y 12),
  `136` (la cadena de coherencia, paso 13), `131` (los 7 campos de `VM_PRT_CNTL`),
  `099` (**cerrado aquí**).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Este bloque no se puede observar por la vía que funcionó dos veces.** `140` y
`142` resolvieron sus preguntas con `journalctl`, porque el driver **imprime** lo
que calcula. **Aquí no imprime nada:** ni `init_golden_registers`, ni
`program_register_sequence`, ni `set_prt` con su `dev_warn` — que sólo salta en el
camino `true`, y ese camino depende de un contador que empieza en cero.

**Así que el resultado de esta nota es enteramente `STATIC`, y eso es un
`NEGATIVE_RESULT` sobre mi propio método, no sobre el hardware.**

*Un `dev_info` es un puerto de observabilidad que existe o no existe. Cuando existe,
es el camino más barato y hay que buscarlo primero — dos veces seguidas funcionó.
Cuando no existe, el mismo camino no da nada, y hay que decirlo en vez de
presentar un resultado derivado como si fuera observado.*

**Y la segunda lección es sobre el alcance de un nombre.** El prefijo
`golden_settings_` sugiere ajuste por chip: cinco tablas, cinco nombres, cinco chips. **El contenido son dos
tablas repetidas.** El nombre promete una cosa y el código hace otra, y un nombre
que promete más de lo que hace es un sitio donde buscar más, no menos: si la tabla
"de Polaris11" fuera realmente de Polaris11, tendría entradas que las de Fiji no
tuvieran. **No las tiene, así que la pregunta correcta era "qué hay en la tabla", no
"qué más hay en el switch".**
