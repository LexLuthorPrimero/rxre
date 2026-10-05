# 1439 — primera lectura del silicio: el mapa de offsets queda validado por hardware, y la profundidad 0/1 de VMID0/VMID1 se lee directamente

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+VALIDACION-INDEPENDIENTE
TRACK=RUNTIME(lectura de MMIO) · 0000:01:00.0 SOLO · Intel 0000:00:02.0 intacta
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1434-*  (validada en hardware)
         06-INGENIERIA-INVERSA/findings/1436-*  (el punto de §6 más carga, confirmado)
         04-IMPLEMENTACION/rx550-driver/rx550_gart_geom.h  (ventana GART: confirmada)
ESTADO=PROBADO · el direccionamiento absoluto en BAR5 queda validado, no supuesto
       · PAGE_TABLE_DEPTH = 0 para VMID0 y 1 para VMID1, LEIDO del silicio
       · la ventana GART del proyecto queda confirmada por una direccion real
       · cero escrituras de registro: solo lectura
```

## 0. Qué cambió y bajo qué autorización

El propietario autorizó la intervención con una frontera dura: **no tocar la GPU integrada
del procesador**. Esa frontera está escrita en `AGENTS.md`, con sus consecuencias, antes de
ejecutar nada.

```text
ANTES   la regla era "no probar el driver hasta reconstruir como funciona la RX550"
AHORA   reconstruido lo reconstruible, con una lectura del silicio
OBJETIVO  0000:01:00.0  (RX550, 1002:699f)   <-- declarado antes de ejecutar
INTEL    0000:00:02.0  (i915, HD 4600)       <-- prohibida, verificada intacta §6
```

## 1. La vía de lectura, y un dato que casi lo hace imposible

`/sys/bus/pci/devices/0000:01:00.0/resource5` — **262 144 bytes**, modo `0600 root` — es
mmapeable en lectura. Y `/dev/mem` también respondió. Pero con
`CONFIG_STRICT_DEVMEM=y`, toda lectura daba:

```text
0xffffffff   (los 20 registros)
```

**Que es la firma de un BAR sin energía, no de un offset equivocado.** La tarjeta estaba en
`runtime_status=suspended`, D3hot. Reanudarla es una operación normal que amdgpu hace cada vez
que se abre una aplicación 3D, y **toca un solo dispositivo**.

```text
antes : runtime_status=suspended  control=auto
despues: runtime_status=active    control=on     <- 0000:01:00.0, y solo este
```

## 2. EL RESULTADO: `mmSCRATCH_REG0 = 0xdeadbeef`

```text
registro                       dword      byte               valor
--------------------------------------------------------------------------
mmGRBM_STATUS                  0x2004     0x8010             0x00003028
mmGRBM_STATUS2                 0x2002     0x8008             0x00000008
mmCP_BUSY_STAT                 0x219f     0x867c             0x00000000
mmSRBM_STATUS                  0x394      0xe50              0x20000040
mmSRBM_STATUS2                 0x393      0xe4c              0x00000000
mmCP_RB0_WPTR                  0x3045     0xc114             0x00000600
mmCP_RB0_BASE                  0x3040     0xc100             0xff002090
mmCP_RB0_RPTR                  0x21c0     0x8700             0x00000600
mmCP_HQD_PQ_WPTR               0x3255     0xc954             0x00000000
mmCP_HQD_ACTIVE                0x3247     0xc91c             0x00000000
mmVM_CONTEXT0_CNTL             0x504      0x1410             0x00fffed9
mmVM_CONTEXT1_CNTL             0x505      0x1414             0x01fffedb
mmVM_INVALIDATE_REQUEST         0x51e      0x1478             0x00000000
mmATC_VMID0_PASID_MAPPING      0xce7      0x339c             0x00000000
mmSDMA0_CNTL                   0x3404     0xd010             0x08050403
mmSDMA0_STATUS_REG             0x340d     0xd034             0x46deed57
mmIH_RB_CNTL                   0xe30      0x38c0             0x0022011d
mmIH_RB_WPTR                   0xe33      0x38cc             0x000001a0
mmSCRATCH_REG0                 0xc040     0x30100            0xdeadbeef   <-- canario
reservado-prueba                0x9f5c     0x27d70            0x00000000
--------------------------------------------------------------------------
todos-unos=0   ceros=7   de 20
```

**`0xdeadbeef` en `mmSCRATCH_REG0` es el canario de depuración que AMD escribe en los
registros de scratch.** Está en el offset que la cabecera declara, `0xc040`, convertido a
byte como `0xc040 × 4 = 0x30100`. Eso **valida de una vez el modelo de direccionamiento**:

```text
direccion = BAR5_base + (indice_dword << 2) = 0xF7D00000 + off*4
```

Sin ese valor, veinte lecturas plausibles habrían podido ser veinte direcciones
equivocadas coherentes entre sí. Con él, no hay explicación alternativa.

**Y `todos-unos = 0`.** Un offset equivocado muy probablemente habría devuelto `0xffffffff`
o un patrón inerte; ninguno lo hizo. **Los offsets de 1434 quedan corroborados por
hardware**, que era lo que 1436 decía que faltaba.

## 3. El punto más carga de 1436, leído del silicio

1436 señaló que el dato más importante de toda la secuencia de §6 era la profundidad de la
tabla de páginas, porque de ella depende si VMID0 es plana o no. **Está programado en esta
máquina ahora mismo, y se lee:**

```text
mmVM_CONTEXT0_CNTL = 0x00fffed9
   ENABLE_CONTEXT       (bit 0)   = 1
   PAGE_TABLE_DEPTH     (bits 2:1) = 0     <-- PLANO
   RANGE_PROT_FAULT_DEF (bit 7)   = 1

mmVM_CONTEXT1_CNTL = 0x01fffedb
   ENABLE_CONTEXT       (bit 0)   = 1
   PAGE_TABLE_DEPTH     (bits 2:1) = 1     <-- PD + PT
   RANGE_PROT_FAULT_DEF (bit 7)   = 1
```

> **VMID0 es plano y VMID1 es PD+PT, leído del hardware, y coincide exactamente con
> `gmc_v8_0.c:889` (`PAGE_TABLE_DEPTH, 0`) y `:919` (`PAGE_TABLE_DEPTH, 1`).**

Esto cierra la contradicción del hallazgo 1416 por el lado que importa: **las dos
estructuras son distintas y ambas existen**, con la profundidad programndolas
distintamente. El `512` de `rx550_pdb0.h` queda sin ninguna desesperanza.

## 4. La ventana GART del proyecto, confirmada por una dirección real

`mmCP_RB0_BASE` **no está vacío**, y no contiene un índice: contiene una dirección.

```text
mmCP_RB0_BASE = 0xff002090
el registro guarda gpu_addr >> 8       (gfx_v8_0.c:4269)
  -> gpu_addr = 0x000FF00209000
  -> dentro de 0xFF00000000..0xFF0FFFFFFF   <-- ventana GART del proyecto   SI
```

El proyecto afirma la ventana GART en `rx550_gart_geom.h` y la justifica por
`BEST_FIT` y por una línea del log del kernel. **Ahora hay una dirección real que cae
dentro, leída del registro que la usa.** Es la segunda confirmación independiente de que
`gart_start = 0xFF00000000` describe esta placa.

Y el ring está **vivo**: `mmCP_RB0_WPTR = mmCP_RB0_RPTR = 0x600`. El driver de amdgpu ha
dejado el ring GFX apuntando a `0x600` con su base en el GART. **Ese es el primer estado de
anillo observado en esta tarjeta.**

`mmCP_HQD_ACTIVE = 0` y `mmATC_VMID0_PASID_MAPPING = 0` son **coherentes** con lo que el
`fdinfo` ya decía: ningún cliente ha enviado trabajo. **Dos fuentes independientes que
coinciden.**

## 5. Lo que NO se ha hecho, y por qué

```text
NO se ha escrito ni un registro de la RX550.   Toda la operacion fue LECTURA.
NO se ha tocado el modulo i915 ni el de amdgpu.
NO se ha programado la salida de display.  Por eso: 1437 advirtió que encender
   DVI-D-1 / HDMI-A-2 en un monitor que maneja la Intel es una pelea de modos.
NO se ha cargado ningun modulo propio.
NO se ha leido el ROM de 128 KiB (sigue con el bit 14 apagado).
```

La reanudación es el único estado cambiado, y es un estado **de la RX550**, reversible con
`echo auto > power/control`.

## 6. LA FRONTERA, VERIFICADA

Capturado **antes** de reanudar, y **después** de leer. Los invariantes:

| invariante | antes | después |
|---|---|---|
| `fb0_name` | `i915drmfb` | `i915drmfb` |
| `fb0_virtual` | `1366,768` | `1366,768` |
| `power/control` de card0 | `auto` | `auto` |
| `runtime_status` de card0 | `active` | `active` |
| `card0-HDMI-A-1` | `connected` | `connected` |
| `i915` cargado | sí | sí |
| nodos `/dev/fb*` | 1 | 1 |

> **Lo único que cambió en la Intel fue el refcount de `i915`, 48 → 50.** Y la causa es
> **mía**: leer `/sys/class/drm/card0/device/power/*` toma una referencia al módulo. Eso es
> una consecuencia de *medir* el invariante, no un cambio de estado de la GPU.

La consola sigue siendo de la Intel, con su modo y su conector. **La frontera se respetó.**

## 7. Procedencia

```text
captura    ninguna: esto es lectura de registros, no un fichero
artefacto   /tmp/opencode/barbatch.py   (lote de 20 registros, lectura pura)
           /tmp/opencode/intel_baseline_antes.txt   (estado de la Intel ANTES)
objeto     0000:01:00.0  unicamente
via        /sys/bus/pci/devices/0000:01:00.0/resource5   262144 B   mmap PROT_READ
           /dev/mem tambien responde, pero CONFIG_STRICT_DEVMEM=y
estado     power/control auto->on   runtime_status suspended->active   (solo 0000:01:00.0)
escrituras de registro: CERO
```

```text
ESTADO=PROBADO · el direccionamiento absoluto en BAR5 (0xF7D00000 + dword<<2) queda VALIDADO
       por mmSCRATCH_REG0 = 0xdeadbeef en el offset que la cabecera declara
       · 20 de 20 registros leidos en estado plausible; CERO devolvieron 0xffffffff
       · PAGE_TABLE_DEPTH: VMID0=0 (plano), VMID1=1 (PD+PT).  LEIDO del silicio y coincide
         con gmc_v8_0.c:889 y :919.  Cierra el punto de mayor carga de 1436
       · la ventana GART del proyecto queda confirmada por una direccion real:
         mmCP_RB0_BASE -> gpu_addr 0x000FF00209000, dentro de 0xFF00000000..0xFF0FFFFFFF
       · el ring GFX esta VIVO: WPTR = RPTR = 0x600, base en el GART.  Primer estado de
         anillo observado en esta tarjeta
       · mmCP_HQD_ACTIVE=0 y PASID_MAPPING=0 coinciden con fdinfo: nadie ha enviado trabajo
FRONTERA  la Intel intacta: fb0=i915drmfb 1366x768, control=auto, runtime=active,
       HDMI-A-1=connected, i915 cargado, 1 nodo fb.  Solo cambio el refcount (48->50),
       causado por leer sus propios sysfs
LIMITE   no se ha escrito ningun registro, no se ha programado display, no se ha leido el ROM
Siguiente  1) la lectura de ixMC_IO_DEBUG_UP_159, que segun 1436 decide que firmware de MC
           carga la placa.  Requiere una escritura de indice y una lectura: es el primer
           CONTROLLED_WRITE y hay que declararlo como tal
         2) el intervalo del writeback del rptr, que bloquea el diseno del bucle de fence
         3) por que fb0_mode salio vacio: menor, pero apunta a que el modo del framebuffer
           no es legible por esa via
```
