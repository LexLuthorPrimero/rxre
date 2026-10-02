# 082 · El acceso no mapeado no pasa de paso: pide página. Y `set_prt` está en la tabla de Polaris12

```
ID:           082
TIPO:        HALLAZGO — frontera F, y CRUCE con A y C
ALCANCE:     gmc_v8_0.c:760-790, amdgpu_vm.c:1422/2760, sid.h:99
TOOL:        lectura de corpus; tools/sysaccess.py cubre el enum hermano
GPU:         INTACTA. Todo esto es LECTURA (NIVEL 0).
CIERRA:      el punto 1 del NEXT ACTION de 081
```

## 1 · LO QUE SE PREGUNTA

`081` cerró `SYSTEM_ACCESS_MODE = 3`. El hermano inmediato es el bit de la línea
siguiente del mismo registro:

```
sid.h:99   SYSTEM_APERTURE_UNMAPPED_ACCESS_PASS_THRU   (0 << 5)
gmc_v8_0.c:843  REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL,
                               SYSTEM_APERTURE_UNMAPPED_ACCESS, 0);
```

El enum define **un solo valor**, `PASS_THRU`, y el driver escribe `0`. Pregunta:
¿qué hace el hardware con un acceso al system aperture **no mapeado** cuando el
driver elige *pass-through*?

La lectura del enum no basta, porque `081` dejó claro que el mecanismo real suele
estar en otro registro. Y lo está.

## 2 · LA RESPUESTA: NO PASA DE PASO. PIDE PÁGINA

```
gmc_v8_0.c:755   * gmc_v8_0_set_prt() - set PRT VM fault
gmc_v8_0.c:760   static void gmc_v8_0_set_prt(struct amdgpu_device *adev, bool enable)
gmc_v8_0.c:761   {
gmc_v8_0.c:762       if (enable && !adev->gmc.prt_warning) {
gmc_v8_0.c:763           dev_warn(adev->dev, "Disabling VM faults because of PRT request!\n");
gmc_v8_0.c:764           adev->gmc.prt_warning = true;
gmc_v8_0.c:765       }
gmc_v8_0.c:766
gmc_v8_0.c:767       tmp = RREG32(mmVM_PRT_CNTL);
gmc_v8_0.c:768       tmp = REG_SET_FIELD(tmp, VM_PRT_CNTL,
gmc_v8_0.c:769                   CB_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS, enable);
gmc_v8_0.c:770       tmp = REG_SET_FIELD(tmp, VM_PRT_CNTL,
gmc_v8_0.c:771                   CB_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS, enable);
gmc_v8_0.c:772       tmp = REG_SET_FIELD(tmp, VM_PRT_CNTL,
gmc_v8_0.c:773                   TC_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS, enable);
gmc_v8_0.c:774       tmp = REG_SET_FIELD(tmp, VM_PRT_CNTL,
gmc_v8_0.c:775                   TC_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS, enable);
gmc_v8_0.c:776       tmp = REG_SET_FIELD(tmp, VM_PRT_CNTL,
gmc_v8_0.c:777                   L2_CACHE_STORE_INVALID_ENTRIES, enable);
gmc_v8_0.c:778       tmp = REG_SET_FIELD(tmp, VM_PRT_CNTL,
gmc_v8_0.c:779                   L1_TLB_STORE_INVALID_ENTRIES, enable);
gmc_v8_0.c:780       tmp = REG_SET_FIELD(tmp, VM_PRT_CNTL, MASK_PDE0_FAULT, enable);
gmc_v8_0.c:781       WREG32(mmVM_PRT_CNTL, tmp);
```

**PRT = Page Request Table.** Y hay que leer el aviso con cuidado, porque es
**contradictorio con los nombres de los campos**:

| nombre del campo | valor cuando `enable = true` |
|---|---|
| `CB_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS` | **1** → el fault **se desactiva** |
| `CB_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS` | **1** → se desactiva |
| `TC_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS` | **1** → se desactiva |
| `TC_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS` | **1** → se desactiva |

Y el `dev_warn` lo dice sin ambigüedad:

```
"Disabling VM faults because of PRT request!"
```

Así que `enable = true` significa **«activar el PRT»**, y activar el PRT
consiste en **desactivar el fault de acceso no mapeado**. El hardware deja de
fault-ear y en su lugar **solicita la página**. Los dos grupos:

- `L2_CACHE_STORE_INVALID_ENTRIES` y `L1_TLB_STORE_INVALID_ENTRIES` a 1
- `MASK_PDE0_FAULT` a 1: **el PDE 0 deja de fault-ear**, es decir, un
  PDE con page fault 0 deja de ser un error.

Y en el `if (enable)` se escribe además el rango válido:

```
uint32_t low  = AMDGPU_VA_RESERVED_BOTTOM >> AMDGPU_GPU_PAGE_SHIFT;
uint32_t high = adev->vm_manager.max_pfn -
                (AMDGPU_VA_RESERVED_TOP >> AMDGPU_GPU_PAGE_SHIFT);
```

que es **la PRT**: el intervalo de PFN que el host está dispuesto a servir.

### Por qué esto NO es pass-through

`PASS_THRU` en `MC_VM_MX_L1_TLB_CNTL` y PRT en `VM_PRT_CNTL` son **cosas
distintas en registros distintos**:

- `PASS_THRU` gobierna qué hace el **L1 TLB** con un acceso no mapeado al system
  aperture.
- `PRT_CNTL` gobierna la **respuesta** a un acceso no mapeado: fault-ear y
  parar, o convertirlo en una **petición de página al host**.

La ruta de petición de página es la de **migración / GPUVM con ATS**: el hardware
no tiene la traducción, la pide, y el host responde. Un `PASS_THRU` en el TLB no
la deshabilita; el que la deshabilita es `PRT_CNTL`.

> Ésta es la clase de error que `081` avisó en el enum: leer el bit que se
> escribió y concluir qué hace el hardware, sin comprobar el registro que
> realmente gobierna el comportamiento. El campo `PASS_THRU` no es inútil —
> gobierna el TLB— pero **no** es el interruptor de la seguridad de un acceso no
> mapeado.

## 3 · `set_prt` ESTÁ EN POLARIS12, SIN NECESIDAD DE RESOLVER EL DISPATCH

`047` cerró que los diez selectores de `amdgpu_ip_version` son **inalcanzables**
en esta compilación, y por tanto que no se sabe qué minor de GMC se instancia.
Para esta pregunta, eso **no importa**:

```
gmc_v8_0.c:1706   static const struct amd_ip_funcs gmc_v8_0_ip_funcs = {
gmc_v8_0.c:1732           .set_prt = gmc_v8_0_set_prt,
...
gmc_v8_0.c:1754   gmc_v8_0_ip_block   { .major=8, .minor=0, .funcs=&gmc_v8_0_ip_funcs }
gmc_v8_0.c:1762   gmc_v8_1_ip_block   { .major=8, .minor=1, .funcs=&gmc_v8_0_ip_funcs }
gmc_v8_0.c:1770   gmc_v8_5_ip_block   { .major=8, .minor=5, .funcs=&gmc_v8_0_ip_funcs }
```

**Los tres bloques candidatos comparten la misma tabla de funciones.** No hay
ningún `gmc_v8_x_ip_funcs` distinto. Luego:

> **`.set_prt` está presente en Polaris12 con independencia de qué minor se
> instancie.** `PROVEN` por estructura, no por runtime, y no depende del
> dispatch que `047` dejó abierto.

Y el driver **lo detecta en runtime**, lo cual confirma que la ruta existe y se
usa:

```
amdgpu_vm.c:1422   adev->gmc.gmc_funcs->set_prt(adev, enable);
amdgpu_vm.c:1433   if (!adev->gmc.gmc_funcs->set_prt) ...
amdgpu_vm.c:1476   if (!adev->gmc.gmc_funcs->set_prt) ...
amdgpu_vm.c:2760   bool prt_fini_needed = !!adev->gmc.gmc_funcs->set_prt;
```

`!!gmc_funcs->set_prt` es **TRUE** en esta placa. Es una comprobación de
capacidad, no una asunción: el driver no asume, pregunta.

## 4 · EL CRUCE QUE `AGENTS.md` PIDE

Este hallazgo toca **tres fronteras a la vez**, y es el primero que lo hace:

| frontera | qué aporta |
|---|---|
| **A** PTE/PDE | `MASK_PDE0_FAULT`: el PDE 0 deja de ser inválido cuando PRT está activo. Es un flag de PTE que `AGENTS.md` §A enumera y que aquí aparece por el otro extremo |
| **F** memoria | `PASS_THRU` (TLB) y PRT (respuesta) son registros distintos. Separar *GPUVM translation* de *MC address decoding* empieza por separar *qué traduce* de *qué responde al fallo* |
| **C** TLB/invalidate | La ruta de fallo es un segundo camino del L1 TLB, complementario de la invalidación. `025:165` ya tenía abierto los 10 dwords ocultos de `emit_flush_gpu_tlb`; este es el registro que los activa |

Y `AGENTS.md` §A dice explícitamente: *«Separar "Linux escribe este bit" de
"hardware interpreta este bit así"»*. Este hallazgo **es** esa separación, en un
bit concreto:

```
Linux escribe 0 en SYSTEM_APERTURE_UNMAPPED_ACCESS
   -> eso gobierna el L1 TLB, no el acceso
El acceso lo gobierna VM_PRT_CNTL, que el driver escribe en OTRO momento
   (amdgpu_vm.c:1422, con un bool que el autor llama `enable`)
```

## 5 · LO QUE SIGUE ABIERTO, Y ES UN DISCRIMINANTE DE NIVEL 2

**Nada de esto dice qué está realmente escrito en `VM_PRT_CNTL` en esta placa.**
El driver tiene la capacidad y la usa bajo demanda, pero no hay en el corpus
ningún camino que la active siempre.

| afirmación | estado |
|---|---|
| El enum de `SYSTEM_APERTURE_UNMAPPED_ACCESS` tiene un solo valor (`PASS_THRU`) | `PROVEN` (`sid.h:99`) |
| Los tres bloques GMC de GFX8 comparten `gmc_v8_0_ip_funcs` | `PROVEN` (`gmc_v8_0.c:1754/1762/1770`) |
| `.set_prt` está en la tabla, luego `!!set_prt` es TRUE | `PROVEN` |
| PRT desactiva el fault de acceso no mapeado, en CB y en TC, lectura y escritura | `PROVEN` (`gmc_v8_0.c:769-775`) |
| PRT invalida L1 y L2 e ignora `PDE0_FAULT` | `PROVEN` (`:777-780`) |
| El rango válido es `VA_RESERVED_BOTTOM..max_pfn−VA_RESERVED_TOP` | `PROVEN` (`:783-786`) |
| **Qué valor tiene `VM_PRT_CNTL` en esta placa** | **`NOT_DETERMINED` — NIVEL 2** |
| **Si el host sirve la PRT o devuelve un error** | **`NOT_DETERMINED`** |
| Si PRT está detrás de una bandera de módulo y por tanto inactivo | `NOT_IN_CORPUS` |

**El discriminante es un registro y es NIVEL 2 — AUTORIZADO** dentro de
investigación, read-only, con registro antes/después (`AGENTS.md` §JERARQUÍA DE
PERMISOS, líneas 46-88). Es una lectura de `VM_PRT_CNTL` desde debugfs o desde
el propio registro en runtime, y distingue tres estados que el corpus no
distingue:

```
VM_PRT_CNTL con los 4 bits DISABLE_* a 0   ->  acceso no mapeado FAULTEA (seguro)
VM_PRT_CNTL con los 4 bits a 1             ->  PRT activo: el hardware PIDE
VM_PRT_CNTL ≠ cualquiera de los dos         ->  hay un tercer modo, y no está
                                              en el enum
```

El tercer caso es el que haría falta buscar primero, porque el enum solo define
**un** valor de `PASS_THRU` y eso no significa que el campo tenga un bit.

## 6 · ERRORES PROPIOS

Ninguno: esta iteración fue lectura dirigida por `AGENTS.md` y no hubo
medición que saliera mal. Se declara porque el hallazgo anterior (`081`) tuvo
tres, y el patrón de errores es un dato.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  082: el acceso no mapeado al system aperture no pasa de paso; PRT lo
    convierte en peticion de pagina al host
  la estructura del PRT_CNTL: 4 bits DISABLE_* (CB/TC x R/W), invalidacion de
    L1 y L2, MASK_PDE0_FAULT, y el rango de PFN valido
  .set_prt PROVEN en Polaris12 sin necesitar el dispatch de 047

Medido:
  3 bloques GMC de GFX8 comparten gmc_v8_0_ip_funcs -> .set_prt incondicional
  amdgpu_vm.c:2760 comprueba !!gmc_funcs->set_prt -> TRUE en esta placa
  4 llamadas a set_prt en amdgpu_vm.c (1422, 1433, 1476, 2760)

Nuevo cruce de fronteras:
  A  MASK_PDE0_FAULT: el PDE 0 deja de fault-ear con PRT activo
  F  PASS_THRU (TLB) y PRT (respuesta) son registros distintos
  C  la ruta de fallo es el segundo camino del L1 TLB

NEXT ACTION:
  El discriminante es NIVEL 2 y esta AUTORIZADO (AGENTS.md 46-88), read-only,
  con registro antes/despues. Es la lectura de VM_PRT_CNTL en 01:00.0.

  Antes de esa lectura, que es NIVEL 2 y por tanto cheap, hay dos preguntas
  NIVEL 0 que pueden cambiar el resultado y que se resuelven por lectura:

  1. QUE ACTIVA set_prt. amdgpu_vm.c:1422 es el unico escritor. Quien lo
     llame decide si PRT esta activo; si es una bandera de modulo o una ruta
     de KFD, entonces la lectura del registro dara 0 y el resultado
     "seguro por defecto" no dira nada sobre lo que pasaria si se activara.
     Eso hay que saberlo ANTES de leer, para no concluir mal.

  2. Si el host responde de verdad. PRT sin respuesta del host es un modo de
     fallo, no un modo de seguridad. amdgpu_vm.c tiene el rango, pero quien
     ATIENDE la peticion es otra funcion: buscarla y leer si responde o si
     devuelve fault es lo que convierte "el hardware pide" en "el sistema
     entero pide y responde".

  Y despues de esas dos, la lectura de NIVEL 2 con su registro antes/despues.
```