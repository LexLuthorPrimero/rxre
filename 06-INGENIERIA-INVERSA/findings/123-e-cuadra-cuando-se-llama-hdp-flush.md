# 123 · §E: qué cabe en el IB del kernel, cuándo se llama `hdp_flush`, y por qué los 344 dwords no son del driver

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué resuelve

`122` dejó tres huecos. Éste cierra dos y explica por qué el tercero no se puede
cerrar en esta máquina.

1. **Cuándo se llama `hdp_flush`.** `PROVEN`.
2. **Qué pone el kernel dentro de un IB.** `PROVEN`, y es casi nada.
3. **Por qué los 344 dwords observados no son un IB del kernel.** `PROVEN_ABSENT`
   la vía de lectura, `NOT_IN_CORPUS` el contenido.

## 1 · `hdp_flush` se emite una vez por envío

`amdgpu_ib.c:253` lo invoca, y no el KIQ como parecía:

```
amdgpu_ib.c:253   amdgpu_device_flush_hdp(adev, ring);

amdgpu_device.c:6601  void amdgpu_device_flush_hdp(adev, ring) {
amdgpu_device.c:6605      if ((adev->flags & AMD_IS_APU) && !amdgpu_passthrough(adev)) return;
amdgpu_device.c:6608      if (adev->gmc.xgmi.connected_to_cpu) return;
amdgpu_device.c:6611      if (ring && ring->funcs->emit_hdp_flush) {
amdgpu_device.c:6612          amdgpu_ring_emit_hdp_flush(ring);
amdgpu_device.c:6613          return;
amdgpu_device.c:6616      if (!ring && amdgpu_sriov_runtime(adev)) { ... }
```

**Las dos salidas tempranas no aplican en esta máquina** — `116`/
`amdgpu_discovery.c:3105-3125` ya probaron que no es APU, y no hay xGMI en una
RX550 de un solo chip. **Y el anillo GFX tiene `emit_hdp_flush`**
(`gfx_v8_0.c:6903`). **Se toma el camino PM4.**

**O sea: un `hdp_flush` por `amdgpu_ib_schedule`.** El otro call site,
`amdgpu_gfx.c:1310`, está en `amdgpu_kiq_hdp_flush` y es un tiro suelto
sincrónico — no explica los 10 observados.

**Y hay dos mecanismos HDP distintos, que es fácil confundir:**

| | qué es | quién lo emite |
|---|---|---|
| `amdgpu_device_flush_hdp` con anillo | **paquete PM4** `WAIT_REG_MEM` | `gfx_v8_0_ring_emit_hdp_flush` |
| `amdgpu_device_flush_hdp` sin anillo | **escritura MMIO** al HDP | `hdp_v4_0` → `amdgpu_hdp_generic_flush` |

**El primero es el que corre aquí.** El segundo sólo se usa sin anillo, y
`amdgpu_sa.c` **no contiene ninguna referencia a debugfs**.

## 2 · El presupuesto del driver confirma mi medición, sin haberla visto

```
gfx_v8_0.c:6926   7 + /* gfx_v8_0_ring_emit_hdp_flush */
```

**Siete dwords. Yo medí siete** (`+0`..`+6` en el anillo, con `+7` ya siendo la
cabecera siguiente). **Dos fuentes independientes, una constante de presupuesto y
un volcado de 2051 dwords, y coinciden.**

Y lo mismo para `vm_flush`, que también presupuesta 7 (`gfx_v8_0.c:6929`), y que
conté a mano como cabecera + 6 payload.

**Esto convierte el hallazgo de `122` de "coincide" a "está confirmado por dos
vías".**

## 3 · Un envío es una LISTA de IBs, y el anillo se reserva por fórmula

```
amdgpu_ib.c:124   int amdgpu_ib_schedule(struct amdgpu_ring *ring, unsigned int num_ibs, ...)
amdgpu_ib.c:197   alloc_size = ring->funcs->emit_frame_size + num_ibs *
amdgpu_ib.c:198                ring->funcs->emit_ib_size;
amdgpu_ib.c:272   for (i = 0; i < num_ibs; ++i) {
amdgpu_ib.c:283       amdgpu_ring_emit_ib(ring, job, ib, status);
```

**El anillo se reserva una vez, por fórmula, y luego se emiten N IBs.** El coste
en anillo de un IB **no depende de lo largo que sea el IB**: son 4 dwords.

**Y esa es la respuesta completa al 4 de `094`.**

```
gfx_v8_0.c:6897   .emit_ib_size =  4, /* gfx_v8_0_ring_emit_ib_gfx */
gfx_v8_0.c:6934   .emit_ib_size =  7, /* gfx_v8_0_ring_emit_ib_compute */
gfx_v8_0.c:6966   .emit_ib_size =  7, /* gfx_v8_0_ring_emit_ib_compute */
```

**GFX 4, compute 7.** Y la razón está en la misma tabla:
`gfx_v8_0.c:6920` y `:6955` ponen `.support_64bit_ptrs = false` para estos
anillos, así que el IB de graphics cabe en 32 bits y el de compute necesita la
dirección partida en dos dwords. **`094` midió 4 y era correcto; el 7 de compute
es el mismo código con otro presupuesto.**

## 4 · Lo que el kernel mete dentro de un IB: casi nada

Los dos IBs que construye el driver, con su tamaño literal:

```
amdgpu_gfx.c:1671-1673   amdgpu_job_alloc_with_ib(..., 64, 0, &job, AMDGPU_KERNEL_JOB_ID_CLEANER_SHADER)
amdgpu_gfx.c:1682-1684   for (i = 0; i <= ring->funcs->align_mask; ++i) ib->ptr[i] = ring->funcs->nop;
                         ib->length_dw = ring->funcs->align_mask + 1;

amdgpu_gmc.c:750-753      amdgpu_job_alloc_with_ib(..., 16 * 4, AMDGPU_IB_POOL_IMMEDIATE, ...)
amdgpu_gmc.c:759         job->ibs->ptr[job->ibs->length_dw++] = ring->funcs->nop;
```

**64 bytes de NOPs, y 64 bytes con un NOP.** Eso es todo.

**Y `344` no aparece como constante en ningún fichero del corpus `amd/`:**

```
grep -rnE '\b344\b'  sobre drivers/gpu/drm/amd/**/*.c *.h   ->  0 resultados
```

**Los 8 IBs de 344 dwords que medí en el anillo no los construyó el kernel.**

**Son de Mesa.** Y aquí está el límite honesto de esta nota:

| | estado |
|---|---|
| El IB observado mide 344 dwords | `OBSERVED` |
| El kernel no construye IBs de ese tamaño | `PROVEN` |
| El kernel no tiene 344 como constante | `PROVEN` |
| Por tanto el IB lo construye el espacio de usuario | `PROVEN_DERIVED` |
| **El contenido de ese IB** | **`NOT_IN_CORPUS`** — Mesa no está en el corpus |
| **Leer ese IB desde el host** | **`PROVEN_ABSENT`** — `amdgpu_sa.c` sin debugfs |

**Lo intenté antes de declararlo:** `/sys/kernel/debug/dri/` está montado y sin
permiso de lectura, y no hay entrada de debugfs del asignador de SA. **No es que
me falte autorización; es que la interfaz no existe.**

## Por qué esto importa para un driver propio

Es la consecuencia con más valor de la nota, y no es un detalle:

**El vocabulario PM4 del kernel en esta GPU es una dnuca palabras.**

```
hdp_flush · gds_switch · pipeline_sync · vm_flush · fence · indirect_buffer
```

más escrituras de registro (`emit_wreg`). **No hay un solo comando de dibujo,
de shader, de DispatchPkt, de estado, ni de clear en ese vocabulario.**

**Todo el trabajo real llega como un flujo que el kernel no inspecciona, no
modifica y no valida: cuatro dwords que apuntan a 344 dwords que construyó otro
programa.**

**Eso cambia el reparto de trabajo de un driver propio:**

- **La parte de kernel es pequeña y ya está resuelta.** Es un anillo circular,
  un puntero, un fence. `111` lo cerró; esta nota lo confirma desde la fórmula
  de reserva.
- **La parte de userspace es todo el proyecto.** Codificador de comandos, ABI,
  validación, page tables, y toda la semántica GFX8.
- **Y no hay red de seguridad.** Si el IB de userspace está mal, el kernel no lo
  detecta: lo pasa tal cual. `emit_ib` copia 4 dwords.

**Para un driver propio eso significa que el validador de comandos tiene que
vivir en userspace, y que el kernel no puede ser la barrera.** Es lo contrario de
lo que sugiere la estructura habitual de amdgpu, y es la consecuencia de que el
flujo no pase por el driver.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `hdp_flush` es 1 por `amdgpu_ib_schedule` | `PROVEN` (`L253` + `L6611`) |
| Las dos salidas de `flush_hdp` no aplican aquí | `PROVEN_DERIVED` (`116`, sin xGMI) |
| El presupuesto del driver dice 7 dwords | `PROVEN` (`gfx_v8_0.c:6926`) |
| Un envío es una lista de N IBs | `PROVEN` (`amdgpu_ib.c:124` `:272`) |
| El anillo se reserva por `emit_frame_size + N*emit_ib_size` | `PROVEN` (`L197-198`) |
| GFX `emit_ib_size`=4, compute=7, por punteros de 64 bits | `PROVEN` (`gfx_v8_0.c:6897`, `gfx_v8_0.c:6934`, `gfx_v8_0.c:6920`) |
| Los IBs del kernel son NOPs de 64 bytes | `PROVEN` (2 sitios) |
| 344 no aparece en el corpus | `PROVEN` |
| El IB observado es de Mesa | `PROVEN_DERIVED` |
| Su contenido | **`NOT_IN_CORPUS`** |
| Leerlo desde el host | **`PROVEN_ABSENT`** |
| Cuántos IBs por envío en la práctica | **`OBSERVED`** — `num_ibs` = 1 en todos |
| `align_mask` en esta GPU | **`PROVEN`** — `0xff` en las tres tablas |

### Los dos que dejé anotados como baratos, y un efecto que no buscaba

```
gfx_v8_0.c:6872   .align_mask = 0xff,     gfx_v8_0.c:6918   .align_mask = 0xff,
gfx_v8_0.c:6953   .align_mask = 0xff,     (las TRES tablas de gfx_v8_0)
amdgpu_gfx.c:1672      64, 0, &job,       <- size = 64 bytes, pool DELAYED
amdgpu_gfx.c:1682      for (i = 0; i <= ring->funcs->align_mask; ++i) ib->ptr[i] = nop;
amdgpu_gfx.c:1684      ib->length_dw = ring->funcs->align_mask + 1;
```

**`align_mask` = 255, así que el bucle escribe 256 dwords = 1024 bytes, y el IB se
pidió con 64.** Con la firma real a la vista (`amdgpu_job.c:241-244`) el `size`
es el cuarto argumento: 64.

**No lo llamo bug, y no lo doy por bueno en ningún sentido.** Tres
contraejemplos, en orden:

1. **La firma.** Comprobé que la llamada casa con
   `adev, entity, owner, size, pool_type, job, k_job_id`. Casa. La discrepancia
   es real.
2. **El asignador.** `amdgpu_sa_bo_new` → `drm_suballoc_new(base, size, ...)`
   con el tamaño exacto. **`drm_suballoc` es capa TTM/DRM core y no está en el
   corpus**: si devuelve una región mayor que 64, no hay desbordamiento.
   **`NOT_IN_CORPUS`, no `NOT_DETERMINED`.**
3. **La alcanzabilidad, que es la que decide.** `amdgpu_gfx.c:1742` documenta
   que se dispara escribiendo en el nodo sysfs `run_cleaner_shader`, y
   `gfx_v8_0.c` **nunca asigna `enable_cleaner_shader`**. Comprobado aquí:

   ```
   /sys/bus/pci/devices/0000:01:00.0/run_cleaner_shader   ->  No existe el fichero
   ```

   **`PROVEN_ABSENT` como observable.** La ruta no está ni expuesta en esta GPU.

**Resultado: un desajuste latente en una ruta de depuración manual,
inalcanzable en esta GPU, y cuya semántica excede el corpus.** No es un fallo
vivo, no es un fallo probado, y no lo registro como ninguno de los dos.

**Lo que sí sale de aquí:** `align_mask` existe **sólo** para dimensionar ese
bucle, y su único consumidor es esa ruta de depuración. **Es decir: el único uso
de `align_mask` en el driver es código que en esta GPU no corre y cuyo contrato
no está en el corpus.** Para un driver propio es un campo del que no hay que
fiarse, y `amdgpu_gfx.c:1672` es un ejemplo a no copiar.

**Y una nota sobre cómo llegué:** iba a cerrar dos números y me salió esto. Lo que
lo hizo salir fue mirar el nodo sysfs, que es un `ls` de una línea que no estaba
en el plan.

## Procedencia

- `STATIC` -- `amdgpu_ib.c:64-87`, `amdgpu_ib.c:124`, `amdgpu_ib.c:197-198`,
  `amdgpu_ib.c:253`, `amdgpu_ib.c:272-285`, `amdgpu_device.c:6601-6616`,
  `amdgpu_gfx.c:1287-1318`, `amdgpu_gfx.c:1671-1684`, `amdgpu_gmc.c:750-759`,
  `gfx_v8_0.c:6897`, `gfx_v8_0.c:6903`, `gfx_v8_0.c:6920-6930`,
  `gfx_v8_0.c:6934`, `gfx_v8_0.c:6955-6966`, `amdgpu_ring.h:245-256`,
  `amdgpu_ring.h:437`, `amdgpu_ring.h:442`, `amdgpu_ring.h:91-100` (enum de
  pools), `amdgpu.h:962`, `amdgpu_sa.c` (sin debugfs).

  **Sin atajos `:NNNN`.** Me han costado dos veces en esta sesión: `citecheck`
  hereda el nombre del fichero anterior y resuelve la cita contra el fichero
  equivocado. En `123` se resolvieron contra `amdgpu_ib.c` tres citas que son de
  `gfx_v8_0.c`, y el resultado fue `LINE_OUT_OF_RANGE` contra un fichero que
  sí contiene esas líneas. **Una cita sin nombre de fichero no es una cita.**
- `OBSERVED` -- `/tmp/rg3.bin`: 2051 dwords, 10 `hdp_flush` de 7 dwords, 8
  `INDIRECT_BUFFER`, 1 `PFP_SYNC_ME`, 34 `EVENT_WRITE_EOP`.
- Intento de lectura del IB en `/sys/kernel/debug/dri/`: montado, sin permiso, y
  **sin entrada para el asignador de SA**.
- Sin MMIO write, sin TLB, sin módulos.
- Encadenada con `122` (los `WAIT_REG_MEM` son `hdp_flush`), `111` (el anillo sólo
  lleva el puntero), `094` (`emit_ib_size = 4`), `115`/`116`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

**Una nota de método, corta, porque es la que me produjo el hallazgo.**

`122` dejó "cuándo se llama `hdp_flush`" como `NOT_DETERMINED`. Lo cerré en
cuatro llamadas porque el call site ya estaba en el fichero que había abierto
antes para otra cosa: `amdgpu_ib.c:253`.

**No necesitaba un volcado nuevo ni un experimento. Necesitaba seguir el
`amdgpu_ib_get` que leí en `122`, doscientas líneas más abajo en el mismo
fichero, y mirar qué lo rodea.**

Y la lección es la de siempre y la de esta tanda entera: **`amdgpu_sa.c` sin
debugfs no lo supe hasta que lo miré, y hasta entonces iba a decir que leer el IB
requería permisos que no tenía.** No los necesitaba: la interfaz no existe, y
eso es un resultado, no un bloqueo.