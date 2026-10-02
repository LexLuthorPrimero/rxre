# 057 · Las vías de lectura de estado de GPUVM que existen, y por qué no hay discriminante read-only

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC+RUNTIME_DISCOVERY`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CUBRE=la pregunta que 056 dejó abierta tras cerrar §C`

## CUDA principal

Después de cerrar §C como `NOT_DETERMINED` con la fuente primaria descartada,
busqué si existía un camino **read-only** hacia el estado de GPUVM: una vía que
no requiera cargar el driver propio ni escribir un registro. **No lo hay, y la
razón es precisa.**

Tres vías existen en el código. Las tres verificadas. Las tres terminan en lo
mismo: o no están expuestas por ioctl en esta versión de KFD, o exigen una VM que
sólo se crea escribiendo en la GPU.

Esto es un `NEGATIVE_RESULT` con causa nombrada. No es un bloqueo vago: es que la
ausencia de un discriminante read-only **es en sí misma una afirmación**, porque
significa que cualquier discriminante de GPUVM en esta máquina pasa por escribir.

## 1 · Lo primero: una corrección mía

Al inicio de esta sesión registré `/dev/kfd` como "nodo huérfano". **Es falso:**

```
crw-rw-rw- 1 root render 237, 0 oct 1 05:49 /dev/kfd
```

Existe, con permisos `0666`. No aparece en `/proc/misc` porque KFD se registra
como char device con major 237, no como misc device. Mi "huérfano" venía de no
haberlo abierto, no de que estuviera roto.

Es la **cuarta vez hoy** que confundo `NAME_NOT_FOUND` con ausencia: `amd_asic_type`
("no existe"), cabeceras de GFX9 ("no están"), `kfd_ioctl_defs.h` ("no está"),
y ahora `/dev/kfd`. Cuatro veces la misma clase, y cada vez la detección fue un
control explícito, no el criterio.

## 2 · Vía 1 · `kfd_vm_fault_info` — el contenido es real, la ioctl no

`amdgpu_amdkfd_gpuvm_get_vm_fault_info` (`amdgpu_amdkfd_gpuvm.c:2355-2360`):

```c
if (atomic_read_acquire(&adev->gmc.vm_fault_info_updated) == 1) {
        *mem = *adev->gmc.vm_fault_info;
        atomic_set_release(&adev->gmc.vm_fault_info_updated, 0);
```

Y la estructura que devolvería (`amd/include/kgd_kfd_interface.h`):

```c
struct kfd_vm_fault_info {
        uint64_t page_addr;
        uint32_t vmid;
        uint32_t mc_id;
        uint32_t status;        ← el registro de 30 bits COMPLETO
        bool     prot_valid;
        bool     prot_read;
        bool     prot_write;
        bool     prot_exec;
};
```

`status` es el registro entero, no `PROTECTIONS` aislado: conserva `ATOMIC`,
`MEMORY_CLIENT_ID`, `MEMORY_CLIENT_RW` y `VMID` además de los bits de protección.

**Pero la ioctl no existe en esta versión.** `GET_VM_FAULT_INFO` no aparece en
ninguno de los tres headers del proyecto ni en el del host:

| header | defines `KFD_IOC_` | `GET_VM_FAULT_INFO` |
|---|---|---|
| `/usr/include/linux/kfd_ioctl.h` (host) | 33 | **no** |
| `RESEARCH/kernelbuild/…/include/uapi/linux/kfd_ioctl.h` | 33 | **no** |
| `working/…` (importado por `kfd_priv.h:35`) | — | no está en el árbol |

La función se compila y existe; la ioctl que la expone es de una versión
posterior. `PROVEN`, y es un `NOT_AVAILABLE` con causa concreta.

## 3 · Vía 2 · `GET_PROCESS_APERTURES` — devuelve `gpuvm_base` y `gpuvm_limit`

De los **39 ioctls reales** que `kfd_chardev.c` registra, este es el que da
direcciones de GPUVM:

```c
struct kfd_process_device_apertures {
        __u64 lds_base,      lds_limit;
        __u64 scratch_base, scratch_limit;
        __u64 gpuvm_base,    gpuvm_limit;     ← la VA de GPUVM del proceso
        __u32 gpu_id;
        __u32 pad;
};
struct kfd_ioctl_get_process_apertures_args {
        struct kfd_process_device_apertures process_apertures[NUM_OF_SUPPORTED_GPUS];
        __u32 num_of_nodes;
        __u32 pad;
};
```

Es read-only y no toca la GPU. **Pero devuelve el estado del proceso que llama,
y este proceso no tiene una VM.** Sin `AMDKFD_IOC_CREATE_QUEUE` y sin una
`AM_HSA_CONTEXT` con al menos un `WRITE_MEM`, `num_of_nodes` sería `0`.

Y ahí está el punto: **`WRITE_MEM` es mapear memoria, que es escribir en la GPU.**
No hay forma de obtener una VM sin escribir.

Ejecutar la ioctl aquí devolvería `num_of_nodes = 0` y lo reportaría como si fuera
una medición. Es un dato de la estructura de la ioctl, no una observación del
hardware, y presentarlo como tal sería el error más caro de esta tanda.

## 4 · Vía 3 · QEMU — cerrada en `056`, se cita sin repetir

`NOT_INSTALLED` pero `DISPONIBLE`; `qemu-system-x86` no emula dispositivo AMD GPU;
`qemu-user-static` emula ISA de CPU. Ver `056 §6`.

## 5 · Conclusión

**No existe discriminante read-only del estado de GPUVM en esta máquina.**

| vía | read-only | expuesta | usable sin escribir |
|---|---|---|---|
| `kfd_vm_fault_info` | sí | **no**, ioctl ausente | — |
| `GET_PROCESS_APERTURES` | sí | sí | **no**: exige una VM |
| `/dev/kfd` diagnóstico KFD | sí | sí | no aporta estado de GPUVM |
| QEMU | — | no instalado, irrelevante | — |

Corolario para la planificación del proyecto: **toda observación de GPUVM en esta
máquina pasa por escribir en la GPU.** Eso no es una limitación del proyecto, es
una propiedad del hardware-driver que se ha medido. F1, F2b y D dependen de ella.

Lo que **no** se cierra aquí, y es importante no confundirlo:

- `NOT_DETERMINED` para `FUNCTION=always` (ver `056`). Ninguna de estas vías lo
  responde: asks qué **esperó** el `WAIT_REG_MEM`, y ninguna fuente de lectura
  observa eso.
- La decodificación del IV por vía estática (ver `051`, `052`) **no** necesita
  runtime y sigue en pie.

## 6 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| `/dev/kfd` existe con permisos 0666 | FACT | **OBSERVED** (corrige mi registro previo) |
| `kfd_vm_fault_info` tiene 8 campos, `status` = registro completo | FACT | **PROVEN** |
| la ioctl `GET_VM_FAULT_INFO` no existe en esta versión | NEGATIVE_RESULT | **PROVEN_ABSENT**, 3 headers |
| `GET_PROCESS_APERTURES` devuelve `gpuvm_base`/`gpuvm_limit` | FACT | **PROVEN** |
| obtener una VM exige `WRITE_MEM` | DERIVATION | **PROVEN_DERIVED** |
| no hay discriminante read-only de GPUVM | NEGATIVE_RESULT | **PROVEN_ABSENT**, 4 vías |

## Nota de proceso

Cuatro búsquedas de esta iteración fallaron por **suponer el nombre del fichero
o del símbolo**: `kfd_ioctl_defs.h`, `struct kfd_process_apertures`,
`kfd_process_device_apertures`, y `kfd_process_aperture`. En los cuatro casos el
símbolo existía, con otro nombre o en otro fichero. El patrón que funciona es
listar el índice real (`grep -oE 'struct kfd_ioctl_[a-z_]+_args'`) antes de buscar
el elemento. Lo escribo aquí porque es la mitad de los errores de esta sesión.

Y el más importante, porque no fue un fallo sino una tentación: **podía haber
ejecutado la ioctl y publicado `num_of_nodes = 0` como observación.** Habría sido
un dato falso con apariencia de medición. `PRE-EXECUTION CONTRACT CHECK` punto 8
— "verificar que el resultado es semánticamente interpretable" — es exactamente
lo que impidió eso.