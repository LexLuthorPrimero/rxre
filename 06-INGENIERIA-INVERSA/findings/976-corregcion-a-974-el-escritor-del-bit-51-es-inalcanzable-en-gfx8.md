# 976 · Corrección a `974`: el segundo escritor del bit 51 es inalcanzable en GFX8, y el tipo de fault sí tiene observador

```
CLASSIFICATION=CORRECTION+DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CORRECTS=974-el-bit-51-si-llega-a-un-pte-de-gfx8-por-el-manejador-de-faults.md
CORRECTS=101-gfx8-decodifica-el-tipo-de-fault-y-nadie-lo-lee.md
CONTINUES=131-c-prt-no-esta-bloqueado.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué corrige

`974` afirmo que en GFX8 `amdgpu_vm_handle_fault()` escribe un PTE con el bit 51
puesto. **La afirmacion es correcta sobre el codigo y falsa sobre esta placa.** No
llego a ningun sitio desde un IP block de GFX8, y con ella se cae la segunda mitad de
`974`.

Lo que **no** se cae es la primera mitad: la disolucion de la contradiccion de `131`
sigue en pie, porque no dependia de este camino.

Y del mismo rastreo sale otra cosa, que es una refutacion: **`101` esta mal.**

## 1 · Alcanzabilidad de `amdgpu_vm_handle_fault()` en GFX8

`974` encontro el escritor del bit 51 pero no pregunto quien lo llama. La cadena, de
capa a capa:

```
amdgpu_vm.c:3013   amdgpu_vm_handle_fault()                  <- el escritor
```

Sus unicos llamantes, en todo el driver:

```
amdgpu_gmc.c:554   dentro de amdgpu_gmc_handle_retry_fault()
amdgpu_gmc.c:577   idem
gmc_v12_1.c:155    GFX12.1
gmc_v12_1.c:178    GFX12.1
```

Y los unicos llamantes del camino generico:

```
gmc_v9_0.c:588     amdgpu_gmc_handle_retry_fault()
gmc_v10_0.c:118    idem
gmc_v11_0.c:117    idem
gmc_v12_0.c:113    idem
```

**No hay ninguno en `gmc_v8_0.c`.** Y no hay puerta de atrás por puntero a funcion:

```
gmc_v8_0.c:1732   static const struct amdgpu_gmc_funcs gmc_v8_0_gmc_funcs = {
                      .flush_gpu_tlb, .flush_gpu_tlb_pasid, .emit_flush_gpu_tlb,
                      .emit_pasid_mapping, .set_prt, .get_vm_pde, .get_vm_pte,
                      .get_vbios_fb_size            <- 8 campos, ninguno de dispatch de fault
                  };
```

`struct amdgpu_gmc_funcs` no tiene ningun puntero de dispatch de fault: los unicos
relacionados con faults son `flush_gpu_tlb*` y `set_prt`. El unico camino de fault de
GFX8 es directo:

```
gmc_v8_0.c:1744   static const struct amdgpu_irq_src_funcs gmc_v8_0_irq_funcs = {
gmc_v8_0.c:1746       .process = gmc_v8_0_process_interrupt,
```

**Veredicto: `amdgpu_vm_handle_fault()` es inalcanzable en GFX8.** `PROVEN`, por
cadena de llamantes exhaustiva y por ausencia de puntero que la alcance.

### Que queda de `974`

| afirmacion de `974` | estado tras esta nota |
|---|---|
| el log de PRT lo produce `AMDGPU_VM_PAGE_PRT`, no un bit de PTE | **sigue `PROVEN_DERIVED`**, no dependia de este camino |
| A confirmada, C refutada | **siguen** |
| existe un segundo escritor del bit 51 en el arbol de GFX8 | **`PROVEN` sobre el codigo** |
| ese camino se ejecuta en Polaris12 | **`REFUTED` por inalcanzable** |
| forzar no-retry-fault y marcar el bit 51 son la misma escritura | **`REFUTED` en esta placa**: no hay tal escritura |

**Y la ultima fila es la que mas duele, porque era la accionable.** `974` decia que
un driver propio deberia decidir si querer ese no-retry-fault. **En Polaris12 la
pregunta no existe**: no hay codigo que lo produzca. `gmc_v8_0.c:1059` asigna
`noretry_flags`, y ese campo **no lo consume nadie en GFX8** porque su unico consumidor
(`amdgpu_vm_pt.c:670`) solo se alcanza desde `amdgpu_vm_pte_update_flags()`, que solo
recibe flags de los caminos de fault de v9/v10/v11/v12/12.1.

`PROVEN_DERIVED`: en GFX8 el driver **no tiene ningun camino para codificar un
no-retry-fault**, porque su unica codificacion posible (`AMDGPU_VM_NORETRY_FLAGS`) usa
`AMDGPU_PTE_TF`, bit 56, que el propio driver declara *"PTE is handled as PDE for
VEGA10"* y que en el formato PTE de GFX8 cae en `63:40 reserved`.

## 2 · `101` esta refutado: el tipo de fault si tiene observador

`101` afirmo: *"GFX8 decodifica el tipo de fault (read/write/exec) y el resultado no
llega a nadie"*. Es **falso**, y el que lo refuta es el mismo `process_interrupt`.

La cache que `101` dio por muerta si se lee, en **tres** sitios:

```
gmc_v8_0.c:1455   amdgpu_vm_update_fault_cache(adev, entry->pasid, ...)
                        |
amdgpu_vm.c:3199       escribe en vm->fault_info y en adev->vm_manager.fault_info
                        |
amdgpu_dev_coredump.c:299   LEE adev->vm_manager.fault_info  (imprime addr y status)
amdgpu_kms.c:1379           LEE vm->fault_info               (query de userspace)
```

Y el camino KFD, que es el que decodifica **exactamente** los cuatro campos que `101`
declaró perdidos:

```
gmc_v8_0.c:1484   if (amdgpu_amdkfd_is_kfd_vmid(adev, vmid)
gmc_v8_0.c:1485       && !atomic_read_acquire(&adev->gmc.vm_fault_info_updated)) {
gmc_v8_0.c:1497       info->prot_valid = protections & 0x7  ? true : false;
gmc_v8_0.c:1498       info->prot_read  = protections & 0x8  ? true : false;
gmc_v8_0.c:1499       info->prot_write = protections & 0x10 ? true : false;
gmc_v8_0.c:1500       info->prot_exec  = protections & 0x20 ? true : false;
gmc_v8_0.c:1501       atomic_set_release(&adev->gmc.vm_fault_info_updated, 1);

amdgpu_amdkfd_gpuvm.c:2355  amdgpu_amdkfd_get_vm_fault_info()   lo LEE y lo devuelve
```

**`read`, `write`, `exec` y `valid` no se pierden: se entregar en un struct con un
ioctl de userspace.** `101` los dava por perdidos porque solo miro el camino del
`dev_err`.

**Condicion que no quiero ocultar:** el camino KFD solo se rellena si el VMID del fault
es un VMID de KFD (`amdgpu_amdkfd_is_kfd_vmid` compara con
`adev->vm_manager.first_kfd_vmid`). Un fault de un proceso que no usa KFD no lo
rellena. Y el `dev_err` con el texto decodificado va dentro de `printk_ratelimit()`.

## 3 · Lo que NO cierra

| afirmacion | estado |
|---|---|
| `amdgpu_vm_handle_fault()` es inalcanzable en GFX8 | `PROVEN` (cadena de llamantes + sin puntero) |
| `noretry_flags` no lo consume nadie en GFX8 | `PROVEN_DERIVED` |
| GFX8 no tiene codificacion de no-retry-fault | `PROVEN_DERIVED` |
| el log de PRT lo produce `AMDGPU_VM_PAGE_PRT` | `PROVEN_DERIVED`, desde `974` |
| el tipo de fault GFX8 llega a userspace por KFD | `PROVEN` (cadena de escritura y lectura) |
| que la cache global `fault_info` se rellene en GFX8 | **`NOT_DETERMINED`** |
| que el hardware heed el bit 51 en GFX8 | **`NOT_DETERMINED`** |

**La fila que dejo abierta y es la mas importante:** `amdgpu_vm_update_fault_cache()`
solo escribe `if (vm && status)`, y `vm` sale de `xa_load(&adev->vm_manager.pasids,
entry->pasid)`. En GFX8 no hay PASID en el hardware, y `entry->pasid` lo rellena el
decodificador **de 8 dwords** (`amdgpu_ih.c:287`, elegido por `ih_v7_0.c:820`, el unico
`decode_iv` de GFX8). **No he resuelto que vale ahi** y no lo voy a aducir: si el IV de
fault de GFX8 ocupa 4 dwords, `dw[3]` no es un PASID sino otra cosa, y la cache global
no se rellena nunca en esta placa. Es una pregunta de una lectura de log y de un
`RREG32` de un registro de fault, no de un razonamiento.

## 4 · Esta nota es el 976, y el motivo es un defecto del mecanismo

Escribí este hallazgo como `975`, lo commiteé, y al validar encontré **dos ficheros
con el mismo numero**, cosa que no había pasado en 974:

```
975-corregcion-a-974-el-escritor-del-bit-51-es-inalcanzable-en-gfx8.md   <- mio, commiteado
975-suite-gart-no-compila-y-no-era-un-maximo.md                           <- AGENT-06, sin commitear
```

Los dos con timestamp `14:37`. **Lo he creado yo, y no ha sido un descuido de
escritura: `nextnum.py --reservar 975` responded `RESERVADO`.** Comprobado:

```
.nextnum.lock   grep -c '^975$'   ->  1        una sola reserva, la mia
```

El otro fichero viene de `06-DRIVER-C-ASM-PERFORMANCE` y **no pasó por
`nextnum.py`**. O sea: la reserva funciona, y no alcanza. El mecanismo protege a los
que lo usan y no protege de los que no.

**Cedo yo, porque la reserva es mia**, y no toco el fichero del otro: `git mv` al 976
con la reserva hecha. El numero 975 es suyo.

**Lo dejo escrito porque es exactamente el defecto que el corpus ya denuncia.** Al
arrancar este turno medi, con dos herramientas independientes: **72 numeros de
hallazgo con mas de un fichero, 171 ficheros implicados, y 1002 referencias
colgando** en 42 numeros. `FINDINGS-RENUMERACIONES.md` es la tabla que existe para
arreglar eso, y el propio documento dice que el renumerado **no esta commiteado** y
que por eso la fuente es comparar contra HEAD.

**Esto es una reproduccion en vivo de esa deuda, no una cita.** Si alguien hubiera
citado "el 975 dice que..." en este repositorio dentro de diez minutos, la cita
habriaapuntaba al hallazgo equivocado y no habria habido ninguna senal: el numero
seguiria existiendo. Y el unico aviso es un `grep -c`, que nadie mira.

**Lo que no voy a hacer es arreglarlo aqui.** Son 72 numeros y 1002 referencias: es
trabajo de otro ambito, con su authority y su lock, y el protocolo es explicito en
que un ambito no se toca desde otro. Lo que si hago es dejar la medicion y esta
reproduccion, que es lo que faltaba: **el mecanismo de reserva tiene una tasa de
incidencia medible y no la tenia declarada.**

## Procedencia

- `STATIC` — corpus `RESEARCH/working/linux-7.1.3`. sha256 sin cambios respecto de `974`:
  `gmc_v8_0.c d76f4144…`, `amdgpu_vm.c 263c5d83…`, `amdgpu_vm.h 10498bcb…`,
  `amdgpu_vm_pt.c 910eef3f…`, `gmc_v9_0.c 3a5c4350…`.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos. La GPU no se
  ha tocado. `RUNTIME=NOT_RUN`.
- Herramientas: `grep`/`sed` sobre el corpus, y `grep` exhaustivo de llamantes para
  cada funcion de la cadena. Sin herramienta propia: la pregunta era de alcanzabilidad
  en fuente primaria y la fuente estaba ahi.
- Limite de corpus declarado: `include/uapi/drm/amdgpu_drm.h` no esta. El numero de
  ioctl exacto de KFD es `NOT_FOUND` aqui, **no** `PROVEN_ABSENT`.
- No se edito `AGENTS.md` ni ningun artefacto generado. Son de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo, la segunda de la misma tarde

`974` salio con una afirmacion que yo no habia comprobado: que un codigo se ejecuta.
Encontre el escritor del bit 51, vi la cadena de vuelta y **no segui la cadena hacia
arriba**. Un `grep` de "quien llama" sobre la funcion que escribe es el primer trabajo,
no el ultimo.

`101` cometio el error opuesto y en el mismo fichero: afirmo que algo no lo leia
mirando solo un consumidor. **Los dos errores son el mismo error de alcance**, y los
dos estaban a un `grep -rn` de distancia.

La regla que sale, y que ya no es nueva pero aqui se cumple dos veces en el mismo
hilo: **una afirmacion sobre lo que el driver hace necesita las dos direcciones del
grafo de llamadas, y una afirmacion sobre lo que se observa necesita todos los
consumidores.** Con una sola de las dos, se escribe la mitad de la verdad y se
publica.
