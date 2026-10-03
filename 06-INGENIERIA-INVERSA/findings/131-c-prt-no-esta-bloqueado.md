# 131 · §C: PRT no está bloqueado — hay un registro, y el driver lo contradice

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`099` cerró como `NOT_DETERMINED` porque los únicos contadores de PRT
(`num_prt_users`, `prt_warning`) viven en memoria del driver, sin observable. Esta
nota hace tres cosas: **encuentra el registro**, **conecta una observación previa
que no sabía a qué registro pertenecía**, y **levanta una contradicción**.

## 1 · El hardware PRT existe en GFX8, y hay un registro de control

```
gmc_8_1_d.h   mmVM_PRT_APERTURE0_HIGH_ADDR  0x530      mmVM_PRT_CNTL          0x534
gmc_8_1_d.h   mmVM_PRT_APERTURE0_LOW_ADDR   0x52c      ...
gmc_8_1_d.h   mmVM_PRT_APERTURE1_HIGH_ADDR  0x531
gmc_8_1_d.h   mmVM_PRT_APERTURE1_LOW_ADDR   0x52d
gmc_8_1_d.h   mmVM_PRT_APERTURE2_HIGH_ADDR  0x532
gmc_8_1_d.h   mmVM_PRT_APERTURE2_LOW_ADDR   0x52e
gmc_8_1_d.h   mmVM_PRT_APERTURE3_HIGH_ADDR  0x533
gmc_8_1_d.h   mmVM_PRT_APERTURE3_LOW_ADDR   0x52f
```

**Cuatro aperturas de dirección y un control. Y el driver lo configura:**

```
gmc_v8_0.c:775   tmp = RREG32(mmVM_PRT_CNTL);
gmc_v8_0.c:790   WREG32(mmVM_PRT_CNTL, tmp);
```

**`mmVM_PRT_CNTL` es legible y configurable en esta GPU. `099` estaba bloqueado por
buscar el observable en el sitio equivocado** — miraba contadores de software
cuando la máquina de estados está en un registro.

### Los siete campos

```
bit 0  CB_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS
bit 1  TC_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS
bit 2  L2_CACHE_STORE_INVALID_ENTRIES
bit 3  L1_TLB_STORE_INVALID_ENTRIES
bit 4  CB_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS
bit 5  TC_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS
bit 6  MASK_PDE0_FAULT
```

## 2 · Y esto conecta una observación previa que no tenía dirección

Según `099`: *"PRT se disparó en esta máquina (`00:26:43`) y enmascaró
`MASK_PDE0_FAULT` + 6 disable"*.

**`MASK_PDE0_FAULT` es el bit 6 de `mmVM_PRT_CNTL`.** El nombre que `099` reportó
y la cuenta de "6 disable" son exactamente los otros seis campos.

**Esos dos hallazgos son el mismo registro.** `099` tenía el dato correcto y no
sabía de dónde salen sus bits; yo tenía la dirección y no sabía que ya la había
visto.

**Y `130` explica los dos campos de invalidación que no había separado:**
`L1_TLB_STORE_INVALID_ENTRIES` y `L2_CACHE_STORE_INVALID_ENTRIES` son, en el
propio registro de PRT, **el mismo par L1/L2 que gobierna la coherencia.** Otra vez
el mismo hecho con dos nombres en dos sitios.

## 3 · La contradicción, que es lo más valioso de la nota

Por un lado, el flag de PTE:

```
gmc_v8_0.c:728   *flags &= ~AMDGPU_PTE_PRT;      GFX8 lo BORRA explícitamente
amdgpu_vm.h:73   #define AMDGPU_PTE_PRT (1ULL << 51)
amdgpu_vm.h:73   /* TILED for VEGA10, reserved for older ASICs */
```

Y el driver de GFX8, GFX7 y GFX6 **los tres borran el bit**:

```
gmc_v6_0.c:391   *flags &= ~AMDGPU_PTE_PRT;
gmc_v7_0.c:513   *flags &= ~AMDGPU_PTE_PRT;
gmc_v8_0.c:728   *flags &= ~AMDGPU_PTE_PRT;
```

Y sólo GFX9 en adelante lo **ponen**:

```
gmc_v9_0.c:1193      *flags |= AMDGPU_PTE_PRT;
gmc_v10_0.c:511      *flags |= AMDGPU_PTE_PRT;
gmc_v11_0.c:502      *flags |= AMDGPU_PTE_PRT;
gmc_v12_0.c:537      *flags |= AMDGPU_PTE_PRT_GFX12;
```

**Contra eso: `099` observó PRT dispararse en esta máquina.**

> **El driver borra el flag de PRT de cada PTE en GFX8, y sin embargo se observó
> actividad de PRT en esta GPU.**

**Las tres explicaciones posibles, y no elijo:**

| | lectura | consecuencia |
|---|---|---|
| A | el bit 51 no es lo que activa PRT en GFX8; el hardware PRT existe y funciona por otra vía | `AMDGPU_PTE_PRT` es un no-op en esta generación, y borrarlo es cosmético |
| B | PRT se activó en un momento en que el flag estuvo puesto | `gmc_v8_0.c:728` no cubre todos los caminos de escritura de PTE |
| C | la observación de `099` no es de PRT sino de otro mecanismo que comparte nombre | `099` atribuyó mal |

**La lectura A es la que el registro sugiere**, porque `mmVM_PRT_CNTL` está en el
mapa de GFX8 con sus siete campos y el driver lo configura. **Un hardware sin
registros de PRT no tendría un `mmVM_PRT_CNTL` con campos para desactivar faults.**

**Pero no la doy por buena.** `AMDGPU_PTE_PRT_FLAG(adev)` elige entre dos
codificaciones según la versión de IP:

```
amdgpu_vm.h:121   AMDGPU_PTE_PRT_GFX12   (1ULL << 56)
amdgpu_vm.h:122   AMDGPU_PTE_PRT_FLAG(adev)  ->  IP >= 12.0.0
```

**En GFX8 `AMDGPU_PTE_PRT_FLAG` es falso**, así que el chequeo es sobre el bit 51
— que el driver borra. **Y ese "que el driver borra" es el que hay que
desmentir o confirmar, y se desmentiría leyendo el registro.**

## Lo que esto cambia: una frontera de bloqueada pasa a leíble

`099` estaba en `BLOCKED_BY_CONDICIÓN_DE_SESIÓN` con la explicación *"no hay
observable"*. **Esa explicación era incorrecta: el observable es un registro.**

**Y se acumula con `229`. Hay ahora un bloque de lectura que responde a más
preguntas abiertas que ninguna otra cosa del proyecto:**

| registro | dirección | qué responde |
|---|---|---|
| `VM_L2_CNTL2` | **`0x501`** | si el invalidate por dominio está activo (bit 21); valor de reset de 5 campos de configuración |
| `VM_PRT_CNTL` | **`0x534`** | si PRT está activo; por qué se disparó pese a que el driver borra el flag |

**Dos registros, ocho dwords en total, y contiguos en el mapa de GMC.** Con eso se
pueden cerrar simultáneamente `099`, la última fila abierta de `229`, y la
pregunta de `130` sobre las particiones del L2 — **sin placa y sin nada que no sea
un `RREG32`.**

**No lo he ejecutado.** Requiere mapear la MMIO de la GPU con la sesión gráfica
viva, y eso es una decisión explícita tuya, no mía. Lo que hago aquí es dejar el
observable escrito, con dirección y bits, para que la ejecución sea de dos
lecturas.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| GFX8 tiene hardware PRT en el mapa de registros | `PROVEN` (`gmc_8_1_d.h`) |
| `mmVM_PRT_CNTL` es legible y configurable en GFX8 | `PROVEN` (`gmc_v8_0.c:775-790`) |
| `MASK_PDE0_FAULT` es el bit 6 | `PROVEN` |
| `099` estaba bloqueado por el sitio equivocado | `PROVEN` |
| GFX6/GFX7/GFX8 borran el flag, GFX9+ lo ponen | `PROVEN` (7 sitios) |
| PRT observado pese a borrar el flag | `CONTRADICTION` |
| Cuál de A, B o C es | **`NOT_DETERMINED`** |
| Si PRT es funcionalmente útil en GFX8 | **`NOT_DETERMINED`** |

**La contradicción queda abierta y es real.** AGENTS.md no permite resolver una
contradicción eligiendo la lectura que me resulta más plausible, y no lo hago.

**Lo que sí es `NOT_PROVEN` y quiero que quede dicho:** que el hardware de GFX8
realmente genere page faults de PRT. Los registros existen y el driver los
configura — eso es `PROVEN`. Que la máquina genere faults por esa vía es
`NOT_PROVEN`, y el registro es lo que lo decidiría.

## Procedencia

- `STATIC` -- `include/asic_reg/gmc/gmc_8_1_d.h` (`mmVM_PRT_CNTL`,
  `mmVM_PRT_APERTURE0-3`), `include/asic_reg/gmc/gmc_8_1_sh_mask.h`
  (los siete campos), `amdgpu_vm.h:73` `:121-123`,
  `gmc_v8_0.c:728` `:775-790`, `gmc_v6_0.c:391`, `gmc_v7_0.c:513`,
  `gmc_v9_0.c:1193`, `gmc_v10_0.c:511`, `gmc_v11_0.c:502`, `gmc_v12_0.c:537`,
  `gmc_v8_0.c:71-83`.
- `OBSERVED` — la actividad de PRT de `099`, de sesión anterior, registrada como
  `NOT_DETERMINED`. No es una observación nueva; es una anterior a la que esta nota
  le encuentra la dirección.
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `099` (PRT bloqueado — esta nota lo reabre), `130` (el L1 guarda
  un PTE por fragmento), `229` (los dos mecanismos de invalidate), `127`/`129`
  (la caché de fragmentos), `212`/`207` (faults de VM).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Un hallazgo bloqueado se desbloqueó buscando el observable en la capa
equivocada.**

`099` buscó `num_prt_users` y `prt_warning`, que son contadores de software, y
concluyó que no había observable. **El observable era un registro, y estaba a
cuatro líneas del nombre del flag en el mismo header.**

**Y salió una contradicción, que es lo que AGENTS.md llama el resultado más
valioso de una investigación de frontera: dos cosas que no pueden ser verdad a la
vez, y las dos están `PROVEN`.**

La una es `gmc_v8_0.c:728`: el driver borra el flag. La otra es la observación de
`099`. **Ninguna deroga a la otra, y no he elegido.**

*Una frontera declarada `BLOCKED` merece una revisión del sitio donde se buscó el
observable antes de aceptarla como bloqueada.* Esta estaba bloqueada por una razón
que ya no era cierta.