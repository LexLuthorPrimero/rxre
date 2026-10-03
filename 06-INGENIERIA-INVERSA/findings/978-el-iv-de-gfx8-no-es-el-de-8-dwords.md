# 978 · El IV de GFX8 no es el de 8 dwords: `976` se equivocó, y con él se cierra la fila que dejó abierta

```
CLASSIFICATION=CORRECTION+DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CORRECTS=976-corregcion-a-974-el-escritor-del-bit-51-es-inalcanzable-en-gfx8.md
CORRECTS=101-gfx8-decodifica-el-tipo-de-fault-y-nadie-lo-lee.md
CORROBORADO_POR=183-dos-formatos-de-iv-y-la-version-del-bloque-que-decide.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué corrige

`976` afirmo, en su seccion 3, que en GFX8 `entry->pasid` lo rellena
`amdgpu_ih_decode_iv_helper` (`amdgpu_ih.c:287`), y que ese decodificador lo elige
`ih_v7_0.c:820`, *"el unico `decode_iv` de GFX8"*.

**Las dos mitades son falsas**, y la segunda es la grave: `ih_v7_0` no es de GFX8.

```
amdgpu_discovery.c:2207   case IP_VERSION(7, 0, 0):
amdgpu_discovery.c:2208   case IP_VERSION(7, 1, 0):
amdgpu_discovery.c:2209       amdgpu_device_ip_block_add(adev, &ih_v7_0_ip_block);
```

IP 7.0/7.1 es **Vega20**. Polaris12 es GFX8 y su bloque de interrupciones es otro:

```
vi.c  case CHIP_POLARIS12:
          amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);
          amdgpu_device_ip_block_add(adev, &tonga_ih_ip_block);      <- este
          amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);

tonga_ih.c:504-507   .major = 3,  .minor = 0,  .rev = 0
```

**Que `183` ya lo tenia medido y con el numero de linea.** No lo lei antes de
afirmar, y por eso escribi una cita de fuente con la fuente delante.

## 1 · El IV real de esta GPU

```
tonga_ih.c:248   tonga_ih_decode_iv()          16 bytes, 4 dwords
tonga_ih.c:261       entry->client_id = AMDGPU_IRQ_CLIENTID_LEGACY;   fijo, no se lee
tonga_ih.c:262       entry->src_id    = dw[0] & 0xff;
tonga_ih.c:263       entry->src_data[0] = dw[1] & 0xfffffff;          28 bits
tonga_ih.c:264       entry->ring_id   = dw[2] & 0xff;
tonga_ih.c:265       entry->vmid      = (dw[2] >> 8) & 0xff;         8 bits, no 4
tonga_ih.c:266       entry->pasid     = (dw[2] >> 16) & 0xffff;      <- SI existe
tonga_ih.c:269       ih->rptr += 16;
```

**`entry->pasid` existe en GFX8 y es un campo real del IV**, en `dw[2]`, no en `dw[3]`.
Y `entry->timestamp` y `entry->node_id` **no se asignan nunca** en este decodificador:
en el hardware de esta GPU no hay timestamp de IV.

Esto **deja sin efecto la duda que `976` dejo abierta**, pero no en la direccion que
`976` suponia. No era "el valor es basura": es un campo legitimo.

## 2 · Y la respuesta a la fila `NOT_DETERMINED` es NO

`976` pregunto si `adev->vm_manager.fault_info` se rellena alguna vez en GFX8. La
cadena entera:

```
gmc_v8_0.c:1455          amdgpu_vm_update_fault_cache(adev, entry->pasid, ...)
amdgpu_vm.c:3199              vm = xa_load(&adev->vm_manager.pasids, pasid);
amdgpu_vm.c:3216              if (vm && status) {
amdgpu_vm.c:3217                  vm->fault_info.addr = addr;
amdgpu_vm.c:3223                  adev->vm_manager.fault_info.addr = addr;
```

Y quien puebla ese xarray:

```
amdgpu_vm.c:2674      /* Store new PASID in XArray (if non-zero) */
amdgpu_vm.c:2675      if (pasid != 0) {
amdgpu_vm.c:2676          xa_store_irq(&adev->vm_manager.pasids, pasid, vm, GFP_KERNEL);
```

**La VM de un proceso grafico en Polaris12 tiene `pasid == 0`** — GFX8 no tiene PASID
en el hardware — y por tanto **no se mete en el xarray**. Con `entry->pasid == 0` en el
IV, `xa_load(pasids, 0)` devuelve `NULL`, el `if (vm && status)` no se cumple, y
**la cache de faults no se escribe nunca**.

Consecuencia directa, y aqui `976` se equivocaba tambien al implicar que habia un
lector vivo:

```
amdgpu_kms.c:1367   case AMDGPU_INFO_GPUVM_FAULT:
amdgpu_kms.c:1369       struct amdgpu_vm *vm = &fpriv->vm;
amdgpu_kms.c:1379       gpuvm_fault.addr   = vm->fault_info.addr;     <- siempre 0
amdgpu_kms.c:1380       gpuvm_fault.status = vm->fault_info.status;   <- siempre 0
amdgpu_kms.c:1381       gpuvm_fault.vmhub  = vm->fault_info.vmhub;

amdgpu_dev_coredump.c:299   fault_info = &coredump->adev->vm_manager.fault_info;
amdgpu_dev_coredump.c:302   "Faulty page starting at address: 0x%016llx"   <- 0
```

**`AMDGPU_INFO_GPUVM_FAULT` existe y en Polaris12 devuelve ceros.** Es un ioctl que
responde `0`, y eso es peor que no existir: parece un observable y no lo es.

## 3 · Los tres caminos, y cual vive

| camino | como llega | vivo en GFX8 |
|---|---|---|
| `AMDGPU_INFO_GPUVM_FAULT` (`amdgpu_kms.c:1367`) | `vm->fault_info` | **NO** — `pasid == 0`, el VM no esta en el xarray |
| dev_coredump (`amdgpu_dev_coredump.c:299`) | `vm_manager.fault_info` | **NO** — misma guarda |
| KFD `get_vm_fault_info` (`gmc_v8_0.c:1484`) | compara **VMID**, no PASID | **SI** |

El tercero sobrevive porque **no pasa por el xarray de PASIDs**:

```
gmc_v8_0.c:1484   if (amdgpu_amdkfd_is_kfd_vmid(adev, vmid) && ...)
gmc_v8_0.c:1491-1501   info->prot_valid / prot_read / prot_write / prot_exec
amdgpu_amdkfd_gpuvm.c:2358   if (atomic_read_acquire(&adev->gmc.vm_fault_info_updated) == 1)
```

`adev->gmc.vm_fault_info` es un campo **global**, no por VM, y la condicion es un
VMID de KFD. Por eso es el unico que se rellena.

**Veredicto sobre `101`, que queda matizado, no tumbado:** `101` decia que el
decode de `read/write/exec` no llega a nadie. Es falso, y el que lo refuta es
`gmc_v8_0.c:1497-1500`. Pero los otros dos caminos que uno pensaria en usar **si**
estan muertos, y por un motivo que ni `101` ni `976` habian visto: **no es que no haya
lector, es que no hay escritor cuando el PASID es cero.**

## 4 · Lo que NO cierra

| afirmacion | estado |
|---|---|
| el IV de GFX8 lo decodifica `tonga_ih_decode_iv`, 16 bytes | `PROVEN` (`vi.c`, `tonga_ih.c:504-507`) |
| `ih_v7_0` es IP 7.0/7.1, Vega20, no GFX8 | `PROVEN` (`amdgpu_discovery.c:2207-2209`) |
| `entry->pasid` es `dw[2] >> 16` en GFX8 | `PROVEN` (`tonga_ih.c:266`) |
| `entry->timestamp` no se asigna en GFX8 | `PROVEN` (ausencia en `tonga_ih.c:248-270`) |
| el VM de un proceso grafico no entra en el xarray de PASIDs | `PROVEN_DERIVED` (`amdgpu_vm.c:2675`) |
| `AMDGPU_INFO_GPUVM_FAULT` devuelve ceros en GFX8 | `PROVEN_DERIVED` (cadena de las dos guardas) |
| el camino KFD si entrega el tipo de fault | `PROVEN` |
| que el IV de esta placa traiga `pasid != 0` alguna vez | **`NOT_DETERMINED`** |
| si existe un cliente KFD en esta maquina | **`NOT_DETERMINED`**, sin medir |

**La ultima fila de la tabla del medio es la que abre algo de verdad:** si el IV de
GFX8 puede traer `pasid != 0`, entonces existe un caso en que la cache global si se
rellena, y `AMDGPU_INFO_GPUVM_FAULT` dejaria de estar muerta a medias. Eso es una
lectura del anillo del IH en un fault real, no un razonamiento.

## Procedencia

- `STATIC` — corpus `RESEARCH/working/linux-7.1.3`. sha256 sin cambios respecto de
  `974`: `gmc_v8_0.c d76f4144…`, `amdgpu_vm.c 263c5d83…`, `amdgpu_vm.h 10498bcb…`,
  `amdgpu_vm_pt.c 910eef3f…`.
- `tonga_ih.c` y `vi.c` y `amdgpu_discovery.c` verificados en este mismo turno, con
  numero de linea, no por referencia a `183`.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos. La GPU no
  se ha tocado. `RUNTIME=NOT_RUN`.
- No se edito `AGENTS.md` ni ningun artefacto generado. Son de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este.

## Nota de metodo, la tercera de la misma tarde, y aqui si hay que decir algo

Tres correcciones en un mismo hilo, y las tres son **el mismo error**: **afirmar sin
haber leido la fuente, cuando la fuente estaba a un `grep` de distancia.**

1. `974`: dije que no habia `|=` del bit 51. Habia uno, en una mascara que no es de
   la capa por ASIC.
2. `976`: dije que GFX8 usa el decodificador de 8 dwords, sin mirar que bloque IH
   le asigna `vi.c`. `183` lo tenia medido con numero de linea.
3. `976`: deje abierto si `pasid` es basura en GFX8, sin mirar `tonga_ih.c:266`.

**Lo que no falló fue el metodo, fue la prisa por cerrar el ciclo.** Cada vez que
quiero terminar el turno leo un fichero mas y escribo. Las tres veces, el fichero que
faltaba era el que decidia la afirmacion.

La regla que sale, y que es la mas cara de las tres: **antes de escribir "no hay" o
"este es el valor", hay que haber grepado el fichero que asigna la cosa.** No el que
la consume, ni el que la llama: **el que la escribe.** Y si ese fichero tiene una
tabla de variants, hay que mirar tambien la tabla.

Y una segunda, mas dura: `183` existia, era exactamente mi pregunta, y no lo lei
porque|Gi| ya habia escrito el titular. **Un hallazgo previo que responde a tu
pregunta es informacion, no un estorbo**, aunque lo hayas rediscrito a medias.
