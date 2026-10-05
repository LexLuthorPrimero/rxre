# 1443 — el artefacto lo produjo `amdgpu_ib_schedule` y **no** `amdgpu_vm_flush`: tres observables independientes lo dicen, y eso corrige a `1442`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt   dwords 3..53

AFECTADO=amdgpu_vm.c:896-903      patch, y el DOBLE switch buffer
         amdgpu_ib.c:319-323      patch, y el switch buffer SIMPLE
         gfx_v8_0.c:6280-6284     gfx_v8_ring_emit_sb = 2 dwords
         gfx_v8_0.c:6911          .emit_switch_buffer

CORRIGE=1442 §4, que afirmo que solo se parcheaba uno.  Hay DOS parcheos.
ESTADO=PROVEN con tres observables independientes que convergen
```

## 0 · MI ERROR EN `1442`, Y LA REGLA DE `1430` QUE LO CAZÓ

`1442` §4 escribió:

> *Dos emisiones, un parcheo. El de `amdgpu_vm.c` se guarda en `patch` y **no se
> parchea en ese punto**: hay que buscar quién lo usa.*

MEDIDO: **sí se parchea**, en `amdgpu_vm.c:896`.

```
  amdgpu_vm.c:833   patch      = init_cond_exec(...)
  amdgpu_vm.c:896   patch_cond_exec(ring, patch)          <- SI se parchea
  amdgpu_ib.c:247   cond_exec  = init_cond_exec(...)
  amdgpu_ib.c:319   patch_cond_exec(ring, cond_exec)      <- y este tambien
```

**Dos emisiones, dos parcheos.** Y lo escribí **dejando anotado que faltaba
mirarlo**, que es exactamente lo que `1430` §7 prohíbe: un `NOT_DETERMINED` sin
abrir el fichero. Lo había leído entero, había visto `unsigned int patch = 0;` en
la línea 789, y no subí a mirar el final de la función.

**Lo bueno es que el error no cambió la conclusión**; lo malo es que la dejó con
una explicación inventada —«no se parchea»— que era falsa y que además abría una
puerta a una hipótesis falsa sobre por qué hay un solo `COND_EXEC` en el
artefacto.

## 1 · LO QUE REALMENTE HAY: DOS EMISIONES, DOS PARCHEOS, Y UN `COND_EXEC` DE MÁS

Los dos caminos, con sus comentarios, que es donde está la información:

```c
/* amdgpu_vm.c, en amdgpu_vm_flush() */
        amdgpu_ring_patch_cond_exec(ring, patch);

        /* the double SWITCH_BUFFER here *cannot* be skipped by COND_EXEC */
        if (ring->funcs->emit_switch_buffer) {
                amdgpu_ring_emit_switch_buffer(ring);
                amdgpu_ring_emit_switch_buffer(ring);
        }
```

```c
/* amdgpu_ib.c, en amdgpu_ib_schedule() */
        amdgpu_ring_patch_cond_exec(ring, cond_exec);

        ring->current_ctx = fence_ctx;
        if (job && ring->funcs->emit_switch_buffer)
                amdgpu_ring_emit_switch_buffer(ring);
```

| | `amdgpu_vm_flush` | `amdgpu_ib_schedule` |
|---|---|---|
| emite `COND_EXEC` | sí, en 833 | sí, en 247 |
| lo parchea | sí, en 896 | sí, en 319 |
| switch buffer | **2** (el «doble») | **1** |

Y el artefacto tiene, en los **8 de 8** bloques:

```
  COND_EXEC        1
  SWITCH_BUFFER    1     (dwords 51 y 52, y el 53 ya es relleno .nop)
```

**Un `COND_EXEC` y un switch buffer.** Ese es el perfil de `amdgpu_ib_schedule`.

## 2 · EL «DOBLE» ES EXACTAMENTE 4 DWORDS, Y EL BUDGET LO DICE

`gfx_v8_ring_emit_sb` (`gfx_v8_0.c:6280-6284`), completo:

```c
static void gfx_v8_ring_emit_sb(struct amdgpu_ring *ring)
{
        amdgpu_ring_write(ring, PACKET3(PACKET3_SWITCH_BUFFER, 0));
        amdgpu_ring_write(ring, 0);
}
```

**2 dwords.** El doble son 4. Y el budget del anillo de gfx, en `gfx_v8_0.c:6887`:

```
        4 + /* double SWITCH_BUFFER,
               the first COND_EXEC jump to the place just
                   prior to this double SWITCH_BUFFER  */
```

**El `4` es exactamente el doble, y el comentario explica la razón:** el
`COND_EXEC` salta hasta justo antes del doble switch buffer, porque **ese switch
buffer no se puede saltar**. Es una excepción escrita a conciencia por el autor,
junto al código que la aplica.

Y el artefacto lo confirma por el otro lado: el `COND_EXEC` patcheado vale 43 y
gobierna los dwords **8 a 50**, con el switch buffer en el **51**, justo fuera.
**La frontera medida es exactamente la que el comentario predice.**

## 3 · LOS TRES OBSERVABLES CONVERGEN, Y ESO ES LO QUE CONVIERTE

Es lo importante. Tres measurements independientes, y las tres apuntan a lo mismo:

| observable | si fuera `amdgpu_vm_flush` | si fuera `amdgpu_ib_schedule` | MEDIDO |
|---|---|---|---|
| `COND_EXEC` por frame | 2 (833 **y** 247) | 1 | **1** |
| `SWITCH_BUFFER` | 4 dwords (el doble) | 2 dwords | **2** |
| flush de VM en el anillo | sí, con su fence de 12 | no | **no hay** |

**El tercero es el más fuerte, porque viene de un sitio al que no llegué buscando
esto:**

```
  1412 §4   cero paquetes de flush de VM en el artefacto
  1441      el budget nombra 3 vallas; el artefacto tiene 2
            -> la que falta es la del flush de VM
  1443      y ademas hay 1 COND_EXEC, no 2, y 1 switch buffer, no 2
```

> **Tres cosas que se podrian haber dado por separado y se dieron a la vez.**
> `1412` concluir «aquí no se flushea TLB», `1441` «el budget espera una valla más
> y no está», y `1443` «faltan paquetes que ese camino siempre emite». **Los tres
> son el mismo hecho: en esta captura no se ejecutó `amdgpu_vm_flush`.**

**Y eso es lo que hay que saber antes de usar el artefacto para otra cosa.** Un IB
sabiendo qué código lo produjo vale mucho más que un IB sin saberlo, porque
cada línea del artefacto se puede atribuir a una función concreta en vez de
adivinarse.

## 4 · LO QUE ESTO LE PASA A LA LISTA DE `1412`

`1412` §4 cerró el negativo con «hace falta una captura con un trabajo que
actualice la tabla de páginas de un VMID de usuario». **Eso sigue siendo
cierto**, y ahora se sabe **exactamente qué hay que.capturear**, porque el camino
que falta es conocido:

```
  para obtener el flush de VM hay que ejecutar amdgpu_vm_flush(), y eso exige
     job->vm_pd_addr != AMDGPU_BO_INVALID_OFFSET        (amdgpu_vm.c:807)
     y ademas  job->vmid >= first_kfd_vmid = 8         (1404)

  o sea: un fallo de pagina, no una invalidación
     INVALIDACIÓN  -> gmc_v8_0_flush_gpu_tlb      -> vmid fijo 0   (1412)
     FALLO DE PAGINA  -> amdgpu_vm_flush           -> vmid de usuario
```

**Son dos caminos distintos y `1412` los confundió en uno solo.** La
invalidación de TLB (`1411`, `1401`) y el flush de VM por fallo de página
(`amdgpu_vm_flush`) son **rutas distintas**, y el artefacto capturó la segunda
vacía.

## 5 · LO QUE NO SE AFIRMA

- **No se dice que `amdgpu_vm_flush` esté roto.** Se dice que **no se ejecutó** en
  esta captura, y que su firma está ausente en tres sitios a la vez.
- **No se dice que un solo switch buffer sea un error.** Es lo que emite
  `amdgpu_ib_schedule`, y es el camino normal de un submit sin cambio de tabla.
- **No se atribuye la causa.** Por qué no hubo fallo de página es `NOT_DETERMINED`
  y no se puede saber sin traza.
- **No se toca el corpus ni el artefacto.**

```
ESTADO
  COND_EXEC y switch buffer, por camino
     amdgpu_vm_flush     COND_EXEC en 833, parche en 896,  DOBLE switch buffer
     amdgpu_ib_schedule  COND_EXEC en 247, parche en 319,  switch buffer SIMPLE

  el DOBLE
     gfx_v8_ring_emit_sb          2 dwords
     dos llamadas                 4 dwords
     el budget dice 4             PROVEN
     y el comentario dice que el COND_EXEC salta justo antes, porque
     ese switch buffer no se puede saltar
     el artefacto: span 8..50, switch buffer en 51   la frontera, medida

  QUE CAMINO PRODUJO EL ARTEFACTO:  amdgpu_ib_schedule
     tres observables independientes y convergentes
        COND_EXEC            1 de 2
        SWITCH_BUFFER        2 dwords, no 4
        flush de VM          ausente (1412 §4 y 1441)

  CORRIGE 1442 §4:  dos parcheos, no uno

  para capturar el flush de VM
     hace falta un fallo de pagina, no una invalidación
     y con vmid >= first_kfd_vmid = 8                          2 condiciones

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
  artefacto  solo lectura
```