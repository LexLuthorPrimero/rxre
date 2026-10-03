# GPUVM-AGENT-03 · PO-10-C: el presupuesto de VMID es 1-7

> Cierra una de las tres proof obligations que dejo abiertas
> `GPUVM-10-VMID-Y-PTBA.md` (commit `dd7802b`). Es la que ese documento
> declaro `BLOQUEO: ninguno tecnico`.
>
> **Y corrige una cadena de ese mismo documento**, recien commiteada.

```
AUTORIA=AGENT-03 GPU-SEMANTICS (workspace 03-GPU-SEMANTICS)
WORK_CLASS=cierre-de-proof-obligation
METODO=ESTATICO sobre las fuentes del corpus. Sin hardware, sin captura.
ARBOLES=linux-7.1.3 (RESEARCH/working) y linux-7.2.8 (rx550-upstream)
VEREDICTO=PROVEN_DERIVED. La cota es una consecuencia logica del codigo, no
          una observacion. EV-21 la corrobora pero no la prueba.
```

## 0 · LA PREGUNTA

`GPUVM-10` dejo escrito:

```text
CADENA  gmc_v8_0.c:1168 (first_kfd_vmid=8) -> amdgpu_ids.c:588 (num_ids)
        -> job->vmid = id - id_mgr->ids  \u2208 [0,8)
```

Eso son **ocho** valores. Pero el comentario del propio GMC, dos lineas mas
arriba, dice que son **siete**:

```c
/* gmc_v8_0.c:1164-1167
 * VMID 0 is reserved for System
 * amdgpu graphics/compute will use VMIDs 1-7
 * amdkfd will use VMIDs 8-15
 */
adev->vm_manager.first_kfd_vmid = 8;      /* :1168 */
```

Un comentario no es una cota. O la cadena de `GPUVM-10` esta mal, o el
comentario esta mintiendo, o hay un salto que excluye el 0 y `GPUVM-10` no
menciono. **La pregunta es cual de las tres.**

## 1 · EL SALTO EXISTE, Y DICE POR QUE

`amdgpu_ids.c:596-601`, en `amdgpu_vmid_mgr_init`:

```c
/* skip over VMID 0, since it is the system VM */
for (j = 1; j < id_mgr->num_ids; ++j) {
        amdgpu_vmid_reset(adev, i, j);
        amdgpu_sync_create(&id_mgr->ids[j].active);
        list_add_tail(&id_mgr->ids[j].list, &id_mgr->ids_lru);
}
```

El bucle **empieza en 1**. El indice 0 de `id_mgr->ids[]` existe pero **nunca
se inserta en la LRU**. El motivo esta escrito en el propio codigo: VMID 0 es
el VM del sistema.

Corolario: `id_mgr->ids_lru` contiene exactamente los indices `[1, num_ids)`.

## 2 · LAS CUATRO VIAS DE ASIGNACION RESPETAN ESE CONJUNTO

Este es el punto que hay que probar de verdad, porque `amdgpu_vmid_grab`
intenta cuatro caminos y no todos pasan por la LRU a simple vista.

| via | de donde saca el `id` | fuente |
|---|---|---|
| `amdgpu_vmid_grab_idle` | recorre `ids_lru` con `list_for_each_entry_reverse` | `amdgpu_ids.c:223` |
| `amdgpu_vmid_grab_used` | recorre `ids_lru` con `list_for_each_entry_reverse` | `amdgpu_ids.c:337` |
| `amdgpu_vmid_grab_reserved` | usa `vm->reserved_vmid[vmhub]`, que **no** esta en la LRU | `amdgpu_ids.c:270` |
| reuso del idle (`!id`) | `id = idle`, y `idle` salio de la LRU | `amdgpu_ids.c:411` |

La tercera es la unica que escapa de la LRU, asi que hay que abrirla:

```c
/* amdgpu_ids.c:487-491, amdgpu_vmid_alloc_reserved */
id = list_first_entry(&id_mgr->ids_lru, struct amdgpu_vmid, list);
list_del_init(&id->list);
vm->reserved_vmid[vmhub] = id;
```

El VMID reservado se **taca de la LRU**, no se inventa. Nace en `[1, num_ids)`.
`amdgpu_vmid_free_reserved` lo devuelve a la LRU (`amdgpu_ids.c:513`).

Por tanto las cuatro vias devuelven `id` con `id \u2212 id_mgr->ids \u2208 [1, num_ids)`.
**El 0 no es alcanzable por ninguna.**

## 3 · LA RAMA QUE SE TOMA EN POLARIS12

`amdgpu_ids.c:585-594`:

```c
/* for GC <10, SDMA uses MMHUB so use first_kfd_vmid for both GC and MM */
if (amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(10, 0, 0))
        /* manage only VMIDs not used by KFD */
        id_mgr->num_ids = adev->vm_manager.first_kfd_vmid;
else if (AMDGPU_IS_MMHUB0(i) || AMDGPU_IS_MMHUB1(i))
        id_mgr->num_ids = 16;
```

El `16` de la rama de al lado es el que produjo la duda "1-7 y no 16". No es
la rama de esta GPU. Se comprobó la rama, no se asumió:

```
1002:699f                          amdgpu_drv.c:2041   -> CHIP_POLARIS12
AMDGPU_FAMILY_VI                   amdgpu_device.c:1987
vi_set_ip_blocks()                 amdgpu_device.c:1989
gfx_v8_0_ip_block { .major = 8 }   gfx_v8_0.c:7128-7135
GC_HWIP = 8.0.0                    amdgpu.h:1217  (ip_versions[GC_HWIP][0] & ~0xFF)
8.0.0 < 10.0.0                     VERDADERO
=> num_ids = first_kfd_vmid = 8    amdgpu_ids.c:588 + gmc_v8_0.c:1168
```

El `0x699F` de `amdgpu_drv.c:2041` es el PCI ID de esta tarjeta, leido de la
fuente primaria y no delREADME.

## 4 · VEREDICTO

```text
job->vmid \u2208 [1, num_ids) = [1,8) = {1,2,3,4,5,6,7}

VMID 0    sistema, nunca asignable por el allocator
VMID 1-7 graphics/compute de amdgpu   <-- el presupuesto del driver
VMID 8-15 KFD, y el allocator ni los alcanza porque num_ids=8
```

**Un VM propio tiene 7 slots de VMID, no 8 y no 16.**

### CORRECCION a `GPUVM-10-VMID-Y-PTBA.md`

```text
ANTES   job->vmid = id - id_mgr->ids \u2208 [0,8)
AHORA   job->vmid = id - id_mgr->ids \u2208 [1,8)

El rango corregido no cambia la conclusion de PO-10-C (siete slots), pero
si su CADENA, que estaba mal en el extremo que importa: el conjunto que
recorre el allocator no incluye el 0.
```

## 5 · LO QUE ESTO NO ESTABLECE

1. **No es una observacion.** Es `PROVEN_DERIVED`: una consecuencia logica de
   cuatro lineas de codigo. En runtime sigue sin haberse visto un job con
   vmid 1..7 emitido por esta placa.
2. **EV-21 no prueba esto.** Observar `vmid = 7` en el anillo es coherente con
   el tope del rango, pero un 7 observado **tambien** es lo que se veria si
   el rango fuera `[1,16)`. Corrobora; no discrimina. Por eso no sube el
   estado a `PROVEN`.
3. **Solo en estos dos arboles.** Ver §6.
4. **KFD presente o no** sigue `NOT_DETERMINED`. Si esta maquina no carga KFD,
   los VMID 8-15 no estan(ms) protegidos por nada: son alcanzables por un
   driver propio si ese driver cambia `num_ids`. La cota de 7 es lo que
   **impide** tocarlos, no una proteccion del hardware.
5. **`concurrent_flush == false`** en esta placa no se re-verifico aqui. Solo
   se cita el uso de AGENT-10, porque PO-10-C no depende de el.

## 6 · CRUCE ENTRE LOS DOS ARBOLES

```
amdgpu_ids.c   7.1.3 = 6af26b1da5496f73
               7.2.8 = 6af26b1da5496f73   IDENTICOS
gmc_v8_0.c     7.1.3 = d76f4144138297ee
               7.2.8 = a1fc653ca38b0ea5   DIFIEREN
```

El fichero que decide el rango es **identico** en los dos arboles, asi que la
cota no depende de la version.

El `gmc_v8_0.c` que difiere si cambia, pero **no en lo que importa**: el diff
es el `switch` del GART size reescrito a `amdgpu_gmc_set_gart_size()`, y
`first_kfd_vmid = 8` esta **igual en los dos** (`7.1.3:1168`, `7.2.8:1162`).

De paso queda anotado, sin actuar sobre ello: para `CHIP_POLARIS12` el GART son
`256ULL << 20` en 7.1.3 (`gmc_v8_0.c:595`), lo que toca `204-` sobre la
semantica de los 256 MiB del GART. **No se toca aqui**: es otra pregunta.

## 7 · LO QUE QUEDA ABIERTO DE LAS TRES OBLIGACIONES

```text
PO-10-A  un VMID reutilizado apunta a la tabla correcta   RUNTIME. Sin F1.
PO-10-B  flushed_updates es cota y no bandera              RUNTIME + cobertura
PO-10-C  el presupuesto es 1-7 y no 16                     CERRADA. Este doc.
```

PO-10-C era la unica cerrable sin hardware. Las otras dos dependen del mismo
hueco: **no hay ack de invalidate**, asi que "cuando se hace visible" no es
observable con lo que hay.

## 8 · PROCEDENCIA

```
artefacto   08-ARQUITECTURA/artifacts/GPUVM/GPUVM-11-VMID-PRESUPUESTO-1-7.md
cerrojo     .write-lock/gpuvm/owner
tomado de  AGENT-10 (dd7802b), liberado a las 15:57:43. Verificado que
            .write-lock/gpuvm/ NO existia antes de tomar: desbloqueado, no
            abandonado.
fuentes     4 copias en disco; se leyo la de working/linux-7.1.3 y se cruzo
            el hash contra rx550-upstream-7.2.8
SIN TOCAR   ninguna fuente, ningun finding, ninguna vista generada
por que no es un finding numerado
            el renumerado esta en vivo: el 998 fue reasignado bajo estos pies
            a las 16:00:29. Un artefacto con ruta propia no compite por la
            clave primaria.
reversible  borrar este fichero
```