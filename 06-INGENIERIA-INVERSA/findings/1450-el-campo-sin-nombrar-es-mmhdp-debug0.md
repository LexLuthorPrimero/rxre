# 1450 — el último campo sin nombrar del IB real es `mmHDP_DEBUG0`, y la cadena que lo lleva desde el submit hasta el anillo cierra con dirección **y** valor exactos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt   dwords 22-26
CORPUS=rx550-upstream-7.2.8 (solo lectura)

AFECTADO=amdgpu_ib.c:290           amdgpu_device_invalidate_hdp(adev, ring)
         amdgpu_device.c:6805-6815 los guards, y la llamada
         amdgpu_hdp.c:70-75        el dispatch a asic_funcs->invalidate_hdp
         vi.c:1320-1328            vi_invalidate_hdp
         vi.c:1439                 .invalidate_hdp = &vi_invalidate_hdp
         oss/oss_3_0_d.h           mmHDP_DEBUG0 = 0xbcc
         gfx_v8_0.c:6896           5 + /* HDP_INVL */

CIERRA=1412 §5, el unico campo del artefacto que quedaba sin nombre
ESTADO=PROVEN
```

## 0 · LO QUE QUEDABA ABIERTO

`1412` §5 encontró, en el `WRITE_DATA` del `dword 22`, una dirección que
**no se podía nombrar**:

```
  dword 22  PACKET3_WRITE_DATA count=3
  dword 23  0x40100000   cmd
  dword 24  0x00000bcc   reg     <- sin nombre
  dword 25  0x00000000
  dword 26  0x00000001   value
```

Y el recuento: `0x0bcc` correspondía a **diez símbolos en cinco bloques de
registro**, ninguno descartable. `1412` lo dejó así, con el motivo, y `1420` §5 dedujo el
método que lo resolvería:

> **la RE de un IB tiene que ser comparativa, no por catálogo: primero los
> campos con nombre, después las direcciones.**

Eso es exactamente lo que se ha hecho aquí. Y el resultado es que **el artefacto
ya no tiene ni un solo campo sin nombrar.**

## 1 · LA CADENA, DE CABECERA A COLA

MEDIDO, seis saltos, todos con fichero y línea:

```
  amdgpu_ib.c:290
        amdgpu_device_invalidate_hdp(adev, ring);

  amdgpu_device.c:6805-6815
        void amdgpu_device_invalidate_hdp(struct amdgpu_device *adev,
                                          struct amdgpu_ring *ring)
        {
  #ifdef CONFIG_X86_64
                if ((adev->flags & AMD_IS_APU) && !amdgpu_passthrough(adev))
                        return;
  #endif
                if (adev->gmc.xgmi.connected_to_cpu)
                        return;

                amdgpu_hdp_invalidate(adev, ring);
        }

  amdgpu_hdp.c:70-75
        void amdgpu_hdp_invalidate(struct amdgpu_device *adev, ...)
        {
                if (adev->asic_funcs && adev->asic_funcs->invalidate_hdp)
                        adev->asic_funcs->invalidate_hdp(adev, ring);

  vi.c:1439
                .invalidate_hdp = &vi_invalidate_hdp,

  vi.c:1320-1328
        static void vi_invalidate_hdp(struct amdgpu_device *adev,
                                      struct amdgpu_ring *ring)
        {
                if (!ring || !ring->funcs->emit_wreg) {
                        WREG32(mmHDP_DEBUG0, 1);
                        RREG32(mmHDP_DEBUG0);
                } else {
                        amdgpu_ring_emit_wreg(ring, mmHDP_DEBUG0, 1);
                }
        }

  oss/oss_3_0_d.h
        #define mmHDP_DEBUG0      0xbcc
```

**Y el valor, no solo la dirección:**

```
  el codigo escribe   1
  el artefacto tiene  0x00000001
```

## 2 · LOS GUARDS, QUE EN ESTA PLACA NO DISPARAN

Los dos filters de `amdgpu_device_invalidate_hdp` importan, porque si dispararan
el paquete no estaría en el anillo. MEDIDO:

```
  (adev->flags & AMD_IS_APU)          Polaris12 es discreta -> guard NO salta
  adev->gmc.xgmi.connected_to_cpu     GFX8 no tiene xGMI   -> guard NO salta
```

**Y de paso, `vi.c:1439` es la tabla de HDP de GFX8**, no la de GCN7: `vi.c` es el
fichero de esta generación, y es el que `vi.c:2110` usa para registrar
`gmc_v8_1_ip_block`.

**Y el gemelo de GCN7, `cik.c:1875`, escribe lo mismo** —
`amdgpu_ring_emit_wreg(ring, mmHDP_DEBUG0, 1)`. El patrón **no es una casualidad
de GFX8: es la forma en que se invalida el HDP en toda esta familia.** Eso es lo
que convierte un acierto de dirección en una confianza: **el mismo código, con el
mismo valor, en el fichero de GCN7 y en el de GFX8.**

## 3 · Y EL BUDGET DEL ANILLO CONFIRMA EL TAMAÑO

`gfx_v8_0.c:6896`, en la tabla del anillo **de gfx**:

```
        5 + /* HDP_INVL */
```

**5 dwords.** Y `gfx_v8_0_ring_emit_wreg` escribe exactamente 5
(`6369-6373`: header, `cmd`, `reg`, `0`, `val`). **Coincide.**

Eso no es un detalle: es `1441` confirmando una línea más de su lectura del
budget. El budget no es una estimación vaga, es un inventario, y ahora lleva
cuatro líneas confirmadas contra el artefacto:

| línea del budget | dwords | confirmado por |
|---|---|---|
| `7 + HDP_flush` | 7 | `1412`, byte a byte |
| `5 + HDP_INVL` | 5 | **este hallazgo**, dirección y valor |
| `12 + 12 FENCE x2` | 24 | `1440`, y solo hay 2 de las 3 vallas |
| `2 + SWITCH_BUFFER` | 2 | `1441`, byte a byte |

## 4 · POR QUÉ ESTE REGISTRO NO SE PODÍA RESOLVER CON UN CATÁLOGO

`1412` §5 ya lo dijo con la medición, y aquí está el mecanismo, que es lo que
faltaba:

```
  SOC15_REG_OFFSET(ip, inst, reg)
        = adev->reg_offset[ip][inst][reg##_BASE_IDX] + reg

  SOC15_REG_OFFSET_NO_BASE
        = adev->reg_offset[ip##_HWIP][inst] + reg

  amdgpu_hdp_generic_flush
        escribe (adev->rmmio_remap.reg_offset + KFD_MMIO_REMAP_HDP_MEM_FLUSH_CNTL) >> 2
```

**Tres rutas distintas, las tres con un sumando de runtime**, y la tercera con un
detalle que es una trampa por sí solo:

```
  nbio_v6_3_1.c:618      adev->rmmio_remap.reg_offset = MMIO_REG_HOLE_OFFSET;
  nbio_v7_11_0.c         #define MMIO_REG_HOLE_OFFSET 0x44000
  nbio_v7_9_0.c          #define MMIO_REG_HOLE_OFFSET 0x1A000
  los demas              #define MMIO_REG_HOLE_OFFSET (0x80000 - PAGE_SIZE)
```

**El centinela no es el mismo valor en cuatro ficheros**, y `KFD_MMIO_REMAP_HDP_MEM_FLUSH_CNTL`
**no está definido en ninguna parte del corpus**. Así que esa ruta, para un anillo
de GFX8, escribe una dirección que **no se puede calcular con lo que hay en el
proyecto** — ni siquiera con la fuente completa.

> **Y esa es la lección práctica, y es la razón de que este hallazgo cerrara en
> veinte minutos lo que `1412` dejó abierto:**
>
> **Un catálogo de direcciones no sirve. Un contexto de frame sí.** La dirección
> `0x0bcc` con valor `1` no tiene nombre propio: lo tiene **por lo que la rodea** —
> un bloque HDP, en un submit, con un budget que dice 5 dwords. **El mismo
> `1412` lo dejó escrito como método en `1420` §5, y funcionó.**

## 5 · LO QUE NO SE AFIRMA

- **No se dice que sea el único sitio que escribe `mmHDP_DEBUG0`.** Es el único
  en el camino de submit de un anillo de gfx; hay otras llamadas a
  `amdgpu_device_invalidate_hdp` con `ring = NULL` (`amdgpu_device.c:853`,
  `amdgpu_psp.c:750` y `763`) que van por MMIO, no por el anillo.
- **No se dice que `mmHDP_DEBUG0 = 0xbcc` sea la dirección «verdadera».** Es la
  dirección del bloque OSS de GFX8 tal como la publica `oss_3_0_d.h`, que es el
  header que `gfx_v8_0.c:44` incluye. Que coincida con el anillo **confirma** que
  el bloque es el correcto.
- **No se toca el corpus ni el artefacto.**

```
ESTADO
  el campo que quedaba sin nombre
     dword 24 = 0x00000bcc,  dword 26 = 0x00000001
     identificado como  vi_invalidate_hdp -> mmHDP_DEBUG0
     direccion  oss_3_0_d.h  0xbcc        coincide
     valor      vi.c:1327    1            coincide
     bloque     gfx_v8_0.c:44 incluye oss/oss_3_0_d.h
     budget     gfx_v8_0.c:6896  5 + HDP_INVL = 5 dwords, coincide
     el gemelo GCN7 hace lo mismo en cik.c:1875

  cadena completa, 6 saltos
     amdgpu_ib.c:290 -> amdgpu_device.c:6815 -> amdgpu_hdp.c:70
     -> vi.c:1439 -> vi.c:1327 -> oss_3_0_d.h

  por que no se podia resolver con un catalogo
     SOC15_REG_OFFSET          suma reg_offset[] de runtime
     SOC15_REG_OFFSET_NO_BASE  idem
     rmmio_remap.reg_offset    idem, y con centinela de 4 valores distintos
     KFD_MMIO_REMAP_HDP_MEM_FLUSH_CNTL   NO ESTA EN EL CORPUS

  EL ARTEFACTO YA NO TIENE NINGUN CAMPO SIN NOMBRAR
     WAIT_REG_MEM   mmGPU_HDP_FLUSH_REQ / _DONE        1412
     INDIRECT_BUFFER  control con vmid 7               1420
     EVENT_WRITE_EOP  dos vallas, ref==mask            1440
     COND_EXEC        cuenta 43 = 50 - 7, parcheada    1442
     .nop             0xffff1000                       1441
     SWITCH_BUFFER    2 dwords                         1441
     WRITE_DATA       mmHDP_DEBUG0 = 1                 este

  budget del anillo de gfx, 4 lineas confirmadas contra el artefacto
     HDP_flush 7,  HDP_INVL 5,  FENCE 12+12,  SWITCH_BUFFER 2

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
  artefacto  solo lectura
```