# 083 · En GFX8 el PRT se puede activar y no hay quien lo atienda

```
ID:           083
TIPO:        HALLAZGO — hueco de implementacion PROVEN, no NOT_DETERMINED
ALCANCE:     gmc_v8_0.c:1421-1470, amdgpu_gem.c:840, amdgpu_vm.c:1509/1791/2099/2114
TOOL:        lectura dirigida. tools/sysaccess.py cubre el enum hermano
GPU:         INTACTA. Todo NIVEL 0 (lectura de corpus).
CIERRA:      los dos puntos NIVEL 0 del NEXT ACTION de 082
```

## 1 · LO QUE SE PREGUNTABA

`082` dejó que el acceso no mapeado **pide página** en vez de pasar de paso, y
que `set_prt` está en la tabla de Polaris12. Abrió dos preguntas NIVEL 0:

> **1 · ¿Qué activa `set_prt`?**
> **2 · ¿Quién atiende la petición?**

Las dos se responden por lectura, y la segunda revela un hueco.

## 2 · QUÉ LO ACTIVA: UN FLAG DE IOCTL DE USERSPACE

```
amdgpu_gem.c:840        AMDGPU_VM_PAGE_PRT;          <- declarado como flag de ioctl
amdgpu_vm.c:1791       if (mapping->flags & AMDGPU_VM_PAGE_PRT)
                            amdgpu_vm_prt_get(adev);
amdgpu_vm.c:2099/2114  ídem, en los bordes de un rango parcial
amdgpu_vm.c:1509       ídem, en el alta
amdgpu_vm.c:1415       enable = !!atomic_read(&adev->vm_manager.num_prt_users);
amdgpu_vm.c:1422       adev->gmc.gmc_funcs->set_prt(adev, enable);
```

PRT es un **contador de referencias**, apagado mientras `num_prt_users == 0`, y
lo sube **una aplicación de userspace** pidiendo el flag en el ioctl de mapeo de
BO. No es una ruta que el driver active por su cuenta.

Y la puerta de entrada está **verificada y es alcanzable desde userspace**:

```
amdgpu_gem.c:832  const uint32_t valid_flags = AMDGPU_VM_DELAY_UPDATE |
                       AMDGPU_VM_PAGE_READABLE | AMDGPU_VM_PAGE_WRITEABLE |
                       AMDGPU_VM_PAGE_EXECUTABLE | AMDGPU_VM_MTYPE_MASK |
                       AMDGPU_VM_PAGE_NOALLOC;
amdgpu_gem.c:840  const uint32_t prt_flags = AMDGPU_VM_DELAY_UPDATE |
                       AMDGPU_VM_PAGE_PRT;

amdgpu_gem.c:882  if ((args->flags & ~valid_flags) &&
                      (args->flags & ~prt_flags)) {
                           dev_err(...);          <- se RECHAZA
                   }
amdgpu_gem.c:906  if ((args->operation != AMDGPU_VA_OP_CLEAR) &&
                      !(args->flags & AMDGPU_VM_PAGE_PRT)) {
                           gobj = drm_gem_object_lookup(filp, args->handle);
                   } else {
                           gobj = NULL;           <- sin BO
                   }
```

Dos consecuencias:

1. `:882` acepta los flags que estén en `valid_flags` **o** en `prt_flags`. Es
   decir, **`AMDGPU_VM_PAGE_PRT` es un flag de ioctl válido**, filters de
   userspace, no un interno.
2. `:906` —un mapping con `AMDGPU_VM_PAGE_PRT` **no necesita un BO**. El
   `gobj` queda `NULL` y el mapping se inserta igualmente.

Y `AMDGPU_VM_PAGE_PRT` **no aparece en ninguna parte de `drivers/gpu/drm/amd/`
fuera de `amdgpu/`**: cero apariciones en `kfd/`. No es un flag de KFD en este
árbol, y por tanto la pregunta que `083` dejó abierta —*«¿está el servicio de
página en `kfd/`?»* — tiene respuesta: **no**.

**Consecuencia directa**: `082` dijo que faltaba leer `VM_PRT_CNTL` en la placa.
Ahora se sabe que leerlomuy probablemente dará `0` en una sesión normal — y que **eso no
dirá nada sobre lo que pasaría si PRT se activara**. El registro solo
distinguible después de que alguien pida el flag.

## 3 · QUIÉN ATIENDE: NADIE, EN GFX8

El handler de fault existe y está registrado:

```
gmc_v8_0.c:1109  amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY,
                                  VISLANDS30_IV_SRCID_GFX_PAGE_INV_FAULT,
                                  &adev->gmc.vm_fault);
gmc_v8_0.c:1113  ... GFX_MEM_PROT_FAULT ...
gmc_v8_0.c:1751  adev->gmc.vm_fault.funcs = &gmc_v8_0_irq_funcs;
gmc_v8_0.c:1740      .process = gmc_v8_0_process_interrupt,
```

Y `gmc_v8_0_process_interrupt` (`:1421`) hace esto:

```c
addr      = RREG32(mmVM_CONTEXT1_PROTECTION_FAULT_ADDR);
status    = RREG32(mmVM_CONTEXT1_PROTECTION_FAULT_STATUS);
mc_client = RREG32(mmVM_CONTEXT1_PROTECTION_FAULT_MCCLIENT);
WREG32_P(mmVM_CONTEXT1_CNTL2, 1, ~1);
if (!addr && !status) return 0;
amdgpu_vm_update_fault_cache(...);
if (amdgpu_vm_fault_stop == AMDGPU_VM_FAULT_STOP_FIRST)
        gmc_v8_0_set_fault_enable_default(adev, false);
dev_err(...);  /* imprime el fault */
```

**No hay rama `AMDGPU_VM_PAGE_PRT`.** Registra, imprime y sigue. En GFX9 y
posteriores, sí:

```
gmc_v9_0.c:1192    if (vm_flags & AMDGPU_VM_PAGE_PRT) { ...
gmc_v10_0.c:510    ídem
gmc_v11_0.c:501    ídem
gmc_v12_0.c:536    ídem
gmc_v8_0.c         NINGUNA APARICIÓN
```

Y hay un segundo hecho, en el mismo handler:

> **Solo se lee `VM_CONTEXT1_*`.** La dirección y el estado del fault se leen de
> `VM_CONTEXT1_PROTECTION_FAULT_ADDR` y `..._STATUS`, con el contexto **1
> escrito a mano**. Un fault de protección en `VM_CONTEXT0` o en cualquier otro
> contexto se leería como `addr == 0 && status == 0` y **se descartaría** por el
> `if (!addr && !status) return 0;`.

Esto último es independiente del PRT y es un hallazgo propio sobre la frontera
C.

## 4 · EL RESULTADO

```
usuarios pide ioctl con AMDGPU_VM_PAGE_PRT
   -> amdgpu_vm_prt_get()           num_prt_users++
   -> set_prt(adev, true)          escribe VM_PRT_CNTL:
                                       CB_DISABLE_READ/WRITE_FAULT_ON_UNMAPPED = 1
                                       TC_DISABLE_READ/WRITE_FAULT_ON_UNMAPPED = 1
                                       L1_TLB_STORE_INVALID_ENTRIES          = 1
                                       L2_CACHE_STORE_INVALID_ENTRIES        = 1
                                       MASK_PDE0_FAULT                       = 1
                                       + el rango PFN que el host sirve
   -> el acceso no mapeado YA NO FAULTEA: el hardware pide página
   -> gmc_v8_0_process_interrupt corre
   -> no tiene rama PRT: registra, imprime, y NO responde
```

**El hardware pide una página que nadie le da.** El modo de fallo de esa ruta en
GFX8 no es «devuelve un hueco»: es «el acceso no falla nunca y no se hace nada».

Y es un hecho sobre el **código**, no sobre la spec y no sobre la placa:

| afirmación | estado |
|---|---|
| PRT lo activa un flag de ioctl de userspace | `PROVEN` (`amdgpu_gem.c:840`) |
| `enable = !!num_prt_users`, contador de referencias | `PROVEN` (`amdgpu_vm.c:1415`) |
| `set_prt` desactiva 4 faults de acceso no mapeado | `PROVEN` (`gmc_v8_0.c:769-775`) |
| `set_prt` invalida L1 y L2 e ignora `PDE0_FAULT` | `PROVEN` (`:777-780`) |
| La IRQ de `GFX_PAGE_INV_FAULT` se registra en GFX8 | `PROVEN` (`:1109`) |
| **`gmc_v8_0_process_interrupt` no tiene rama `AMDGPU_VM_PAGE_PRT`** | **`PROVEN` (0 apariciones en el fichero)** |
| GFX9/10/11/12 sí la tienen | `PROVEN` |
| El handler solo decodifica `VM_CONTEXT1_*` | `PROVEN` (`:1444-1446`) |
| Un fault en otro contexto se lee como 0 y se descarta | `PROVEN` (`if (!addr && !status) return 0`) |
| Si el host tiene otro camino para servir la PRT fuera de GMC | `NOT_IN_CORPUS` — no buscado en `kfd/` todavía |

## 5 · POR QUÉ EL HALLAZGO ES DE FRONTERA, Y NO DE ARQUITECTURA

`AGENTS.md` §F pide *«Resolver GART: GPUVA → GART PTE → physical RAM → PCIe»*, y
§C pide *«Resolver VM_INVALIDATE_REQUEST → hardware action → invalidation →
completion → visibility»*.

Lo que hay aquí es un **tercer modo de fallo** que no está en ninguna de las dos
listas y que ninguna cubre: **el fallo que se ha desactivado**. El modo de
seguro por defecto de esta placa es *el acceso no mapeado no hace nada porque
nadie le pide la página* — no porque se haya comprobado que no puede ocurrir.

Y `AGENTS.md` §A dice *«Separar "Linux escribe este bit" de "hardware
interpreta este bit así"»*. El bit lo escribe Linux (`amdgpu_gem.c:840` lo
pide, `amdgpu_vm.c:1422` lo aplica), y lo que el hardware interpretaría es
justamente lo que el handler de GFX8 **no implementa**.

## 6 · ERRORES PROPIOS, Y UNO IMPORTANTE

| error | detectado por |
|---|---|
| sospeché que `gmc_v8_0_ip_funcs` no tenía `.vm_fault` | **verifiqué antes de afirmarlo**: `gmc_v8_0.c:1751` sí lo fija, y estaba fuera del rango que grepé. La sospecha era falsa |

Ese error es exactamente el de `072` (ancla `^` que producía 0), `075` (índice
que no casaba) y `080` (criterio binario sobre 3 candidatos): **un rango de
búsqueda que no cubre el caso que se quiere concluir**. Aquí, el rango
`1706-1732` cortaba justo antes de `1751`, y de ahí salió «no hay handler» con
la tabla puesta 19 líneas más abajo.

> **Una ausencia de un rango no es una ausencia del fichero.** Se comprobó, y
> era falsa. Se declara porque la sospecha parecía muy plausible y porque
> casi se escribe.

## 7 · LO QUE ABRE

- **`kfd/`**: `AMDGPU_VM_PAGE_PRT` es un flag de **KFD** (GPUVM para
  processes). Si el servicio de página está en `amdgpu_kfd` y no en `gmc_v8_0.c`,
  el hallazgo se convierte en «la ruta está repartida» en vez de «no existe». Es
  una búsqueda de un fichero, y es la que toca antes de dar el hallazgo por
  bueno.
- **`VM_CONTEXT1` a mano.** Si el handler solo lee el contexto 1, entonces
  `amdgpu_vm_update_fault_cache()` —que se llama con `entry->pasid`— mete en
  caché un fault que se ha leído de un registro fijo. Es un desacople entre el
  contexto que se registra en la IRQ y el contexto cuyo registro se lee.
- **`gmc_v8_0_set_fault_enable_default(adev, false)`** con
  `AMDGPU_VM_FAULT_STOP_FIRST`: deshabilita faults **para siempre** después del
  primero, no para ese acceso. Es una política de depuración en producción.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  083: en GFX8 el PRT se puede ACTIVAR por ioctl y NO hay quien lo ATIENDA
 RESPUESTA: PRT lo activa un flag de ioctl de userspace, con contador de referencias
  hallazgo lateral: el handler de fault de GFX8 solo decodifica VM_CONTEXT1

Medido:
  AMDGPU_VM_PAGE_PRT: amdgpu_gem.c:840 (ioctl), 4 consumidores en amdgpu_vm.c
  gmc_v8_0.c: 0 apariciones de la rama PRT; gmc_v9_0/v10_0/v11_0/v12_0 si la tienen
  gmc_v8_0_process_interrupt lee solo VM_CONTEXT1_PROTECTION_FAULT_{ADDR,STATUS}
  if (!addr && !status) return 0  -> un fault en otro contexto se descarta

Retractado por este hallazgo:
  mi sospecha de que gmc_v8_0 no registraba handler de fault. FALSA:
  gmc_v8_0.c:1751 lo fija. Se comprobo antes de escribir el hallazgo.

NEXT ACTION:
  La busqueda que falta, y es NIVEL 0 y es de un fichero:

  1. AMDGPU_VM_PAGE_PRT en kfd/ y en amdgpu_kfd*. Si el servicio de la pagina
     esta ahi y no en gmc_v8_0.c, 083 se corrige a "ruta repartida" y el
     proyecto gana la respuesta correcta en vez de un hueco inexistente.
     Esto hay que hacerlo ANTES que 083 circule.

  2. gmc_v8_0_set_fault_enable_default(adev, false) con STOP_FIRST: deshabilita
     los faults de forma permanente tras el primero. Frontera C. Si eso esta
     activo en esta placa, un unico fallo de GPU deja de reportar todos los
     siguientes, y eso SI es observable por el usuario sin nada raro.

  3. Lo que 081 dejo: el equivalente de SYSTEM_ACCESS_MODE en el PTE. A y F se
     juntan ahi, y es el mismo patron que acabo de cerrar dos veces.
```