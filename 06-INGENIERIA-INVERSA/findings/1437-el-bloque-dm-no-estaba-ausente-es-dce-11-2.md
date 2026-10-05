# 1437 — el bloque `dm` no estaba ausente: era un error de ruta, y la generación real es **DCE 11.2**, no «dce_v1_0_0»

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=REFUTACION-DE-MOTIVO+CORRECCION-DE-NOMBRES
TRACK=STATIC(corpus) + STATIC(el .ko del kernel que corre, sin sudo) · sin GPU
GENERADO=2026-10-04
CORRIGE=06-INGENIERIA-INVERSA/findings/1434-* fila 6  (decía "NOT_FOUND, corpus podado")
ORIGEN=1434 marcaba la fila 6: `dce_v1_0_0 | NOT_FOUND (corpus podado) | NOT_FOUND`.
       El motivo era FALSO. El código está, en este árbol, en este kernel, y además
       compilado dentro del módulo que está corriendo ahora mismo.
ESTADO=PROBADO · el fichero es display/amdgpu_dm/amdgpu_dm.c, no amdgpu/dc_dm.c
       · dc_dm.c NUNCA existió en esta serie: find sobre el árbol entero devuelve 0
       · la generación de hardware es DCE 11.2, por dos vías independientes
       · dce_v8_0.c y dce_v10_0.c NO son el camino: 0 apariciones de POLARIS12
       · «dce_v1_0_0» es versión de abstracción de software, NO generación de silicio
```

## 1. Por qué la búsqueda falló, y por qué eso importa más que el resultado

Alguien —o algo— buscó `amdgpu/dc_dm.c`, `dm.c` y `dc_dm.h` en `amdgpu/`, no los encontró,
y escribió *"corpus podado"*.

```text
find . -name 'dc_dm.c' -o -name 'dc_dm.h'    ->  0 resultados
```

**Esos nombres nunca existieron en esta serie.** Desde amdgpu 6.10 el gestor de display
legacy se movió a `display/amdgpu_dm/amdgpu_dm.{c,h}`. Quien busque el nombre antiguo
concluye "podado", y con ello **retira de la lista un bloque entero que sí está**.

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/display/amdgpu_dm/
    amdgpu_dm.c      421 443 bytes
    amdgpu_dm.h       30 085
    amdgpu_dm_crtc.c  amdgpu_dm_plane.c  amdgpu_dm_irq.c  amdgpu_dm_helpers.c
    amdgpu_dm_pp_smu.c  amdgpu_dm_psr.c  amdgpu_dm_replay.c  amdgpu_dm_color.c
    amdgpu_dm_ism.c  amdgpu_dm_services.c  dc_fpu.c  ...  35 ficheros
include/asic_reg/dce/dce_11_2_d.h   874 647 bytes
```

Y el módulo del kernel en ejecución, leído sin sudo, descomprimido en `/tmp/opencode/`:

```text
/lib/modules/7.1.3-200.nobara.fc44.x86_64/.../amdgpu.ko.zst   5.95 MB
-> 37 MB descomprimido,  NOT stripped,  BuildID 4d5342509f84dd84f0d5d515b03eb6c7659fb492
-> vermagic 7.1.3-200.nobara.fc44.x86_64   (igual que uname -r)
-> 34 773 símbolos de texto
-> 491 símbolos dce110_*     44 símbolos dce112_*     44 símbolos dce112_* de Resource Pool
-> strings: "3.2.378"        (== DC_VER en el fuente)
-> parámetro de módulo:  dc:Display Core driver (1 = enable, 0 = disable, -1 = auto)
```

**Y el log de arranque de esta máquina, que el proyecto ya tenía desde el hallazgo 155:**

```text
Display Core v3.2.378 initialized on DCE 11.2
```

> **La conclusión de 1434 fila 6 era una `NOT_FOUND` por ruta equivocada, y eso no es un
> detalle de método: es la clase de error que hace que un hueco parezca una frontera.**
> Corregir la fila: `| 6 | dce_v1_0_0 | display/amdgpu_dm/amdgpu_dm.c | dce/dce_11_2_d.h |`

## 2. `dm_ip_block`: confirmado, y el nombre engaña

```c
/* display/amdgpu_dm/amdgpu_dm.c:3818-3824 */
const struct amdgpu_ip_block_version dm_ip_block = {
        .type  = AMD_IP_BLOCK_TYPE_DCE,
        .major = 1,  .minor = 0,  .rev = 0,
        .funcs = &amdgpu_dm_funcs,
};
```

Y el formato del log lo reproduce exactamente:

```c
/* amdgpu/amdgpu_ip.c:241 */
dev_info(..., "detected ip block number %d <%s_v%d_%d_%d> (%s)\n",
         ..., ip_block_names[AMD_IP_BLOCK_TYPE_DCE],   /* "dce" */
             major, minor, rev,                        /* 1 _0_0 */
             ip_block_version->funcs->name);           /* amdgpu_dm_funcs.name = "dm" */
```

**`<dce_v1_0_0> (dm)` es exactamente esta estructura.** `PROBADO`.

**Pero `dce_v1_0_0` no es una generación de silicio.** No existe "DCE 1.0". El `.major = 1`
es la versión de la tabla de ganchos `amdgpu_dm_funcs`, y **es el mismo valor para toda ASIC
que use el DC display manager**, de Polaris a Vega.

> **Consecuencia práctica: el nombre del bloque NO dice qué cabecera de registros usar.**
> `dce_v1_0_0` → `dce_11_2_d.h` requiere un salto de razonamiento que el nombre no sugiere.

## 3. La generación real: **DCE 11.2**, por dos vías

**Vía A — fuente primaria**, `display/dc/core/dc_resource.c:176-179`:

```c
if (ASIC_REV_IS_POLARIS10_P(asic_id.hw_internal_rev) ||
        ASIC_REV_IS_POLARIS11_M(asic_id.hw_internal_rev) ||
        ASIC_REV_IS_POLARIS12_V(asic_id.hw_internal_rev)) {
        dc_version = DCE_VERSION_11_2;
}
if (ASIC_REV_IS_VEGAM(asic_id.hw_internal_rev))
        dc_version = DCE_VERSION_11_22;
```

**Vía B — runtime**, el log de esta máquina: `Display Core v3.2.378 initialized on DCE 11.2`,
y `dc.h:66` define `DC_VER "3.2.378"`, que es exactamente el `3.2.378` que sale de los
strings del `.ko`.

### 3.1 Dos `.c` que el nombre sugiere y que NO son el camino

```text
grep -c POLARIS12 amdgpu/dce_v8_0.c     ->  0
grep -c POLARIS12 amdgpu/dce_v10_0.c    ->  0
```

- `dce_v8_0.c` cubre sólo `CHIP_BONAIRE / HAWAII / KAVERI / KABINI / MULLINS`
- `dce_v10_0.c` cubre sólo `CHIP_FIJI / CHIP_TONGA`

**Ninguno menciona Polaris12 ni una vez.** Y el header `dce_10_0_d.h` es un eje distinto
del camino de código `dce112`: el hallazgo 155 ya hizo esa distinción y se sostiene.

## 4. La trampa de los 160 líneas: la mayoría del código no está donde el nombre dice

```c
/* display/dc/hwss/dce112/dce112_hwseq.c  — 160 líneas, y esto es todo: */
void dce112_hw_sequencer_construct(struct dc *dc)
{
        /* All registers used by dce11.2 match those in dce11 in offset and structure */
        dce110_hw_sequencer_construct(dc);
        dc->hwseq->funcs->enable_display_power_gating = dce112_enable_display_power_gating;
}
```

**Eso explica los 491 `dce110_*` contra 44 `dce112_*` del módulo.** La mayor parte de la
programación de registros de DCE 11.2 vive en
**`display/dc/hwss/dce110/dce110_hwseq.c`**, no en `dce112_hwseq.c`.

> **Quien busque "el código de DCE 11.2" y encuentre sólo el shim de 160 líneas concluirá
> que no hay nada.** Es el mismo error que §1, con otro disfraz: un hueco aparente creado
> por dónde se mira.

## 5. Convención de direccionamiento: la misma de 1434, confirmada también en DM

```c
/* display/amdgpu_dm/amdgpu_dm.c:14168 */
uint32_t dm_read_reg_func(const struct dc_context *ctx, uint32_t address, ...)
{
        value = cgs_read_register(ctx->cgs_device, address);   /* address, sin transformar */
```

`address` pasa **sin modificar** a la lectura de registro CGS. **Mismo índice dword
absoluto en BAR5**, `0xF7D00000 + off*4`. **Ningún reescalado dentro de la capa DM.**

Muestra del bloque CRTC, en la cabecera que **sí** aplica (`dce_11_2_d.h`):

```text
mmCRTC0_CRTC_GSL_CONTROL   0x1b7b      mmCRTC0_CRTC_H_TOTAL            0x1b80
mmCRTC0_CRTC_H_BLANK_START_END 0x1b81   mmCRTC0_CRTC_H_SYNC_A_CNTL      0x1b85
mmCRTC0_CRTC_V_TOTAL       0x1b87      mmCRTC0_CRTC_V_SYNC_A_CNTL      0x1b8f
mmCRTC0_CRTC_MASTER_UPDATE_MODE 0x1bbe
```

**Stride CRTC = 0x200 dwords = 2048 bytes, seis controladores**, y amdgpu lo indexa como
*delta*, no como tabla de literales:

```c
static const struct dce112_hw_seq_reg_offsets reg_offsets[] = {
  { .crtc = (mmCRTC0_CRTC_GSL_CONTROL - mmCRTC_GSL_CONTROL) }, ...  /* hasta CRTC5 */
};
#define HW_REG_CRTC(reg, id) (reg + reg_offsets[id].crtc)
```

## 6. Qué tendría que hacer el DM en esta tarjeta

**DM es la capa de pegamento; DC es la capa de hardware.** No son lo mismo, y el hallazgo
149 ya dibujó esa frontera bien.

`amdgpu_dm_funcs` expone 15 ganchos (`amdgpu_dm.c:4024-4051`): `early_init`, `late_init`,
`sw_init`, `sw_fini`, `early_fini`, `hw_init`, `hw_fini`, `suspend`, `resume`, `is_idle`,
`wait_for_idle`, `check_soft_reset`, `soft_reset`, `set_clockgating_state`,
`set_powergating_state`. Todos confirmados presentes en el `.ko`.

Trabajo mínimo a nivel de registro para un modeset:

1. **`dce112_init_pte()`** — lee/escribe `mmDVMM_PTE_REQ 0x330`. Es uno de **dos** programas
   de registro genuinamente específicos de 11.2 en todo el shim.
2. **Timing por CRTC** — base `0x1b80`, stride `0x200`. Luego
   `mmCRTC*_CRTC_MASTER_UPDATE_MODE 0x1bbe` con **0**, no 2: el BIOS lo deja en 2 y
   `dce112_enable_display_power_gating()` lo revierte explícitamente.
3. **`dce112_enable_display_power_gating()`** — delega el gating de tubería a la **tabla de
   comandos del BIOS**, no a MMIO directo. Índice de controlador **+1**.
4. **Todo lo demás** lo hereda `dce110_hw_sequencer_construct()`: planos y escalador
   (`GRPH_*`, `DC_*`), codificador de enlace (`DP_AUX`, `DP_LINK`), reloj (`DCE_PPLL*`),
   interrupción (`DCE_INT*`), audio.

**Restricción de recursos para un driver propio**: `dce112_resource_cap()` elige
`polaris_11_resource_cap` para esta tarjeta, con **`dual_link_dvi = true`**, `pipe_count =
timing_generator_count`, `max_downscale_ratio = 200`, `i2c_speed_in_khz = 100`,
`max_cursor_size = 128`, `min_horizontal_blanking_period = 80`.

> Combinado con el hallazgo 166/167 (**DVI-D-1 + HDMI-A-2** en la RX550): la salida de
> display es **DVI + HDMI, con DVI dual-link, y sin DisplayPort**. Cualquier trabajo de PLL o
> codificador tiene que apuntar a DVI/HDMI. Y si se asume DisplayPort porque el nombre
> `DP_AUX` aparece en la lista de símbolos, **se falla**: es el nombre de un campo, no la
> salida que esta placa tiene.

## 7. LA SEGURIDAD DE LA TOMA DE POSICIÓN: el riesgo no es perder la consola

El hallazgo 1085 resolvió un aparente absurdo. Los hechos, que se sostienen:

| observable | valor | qué significa |
|---|---|---|
| `/sys/class/graphics/fb0/name` | `i915drmfb`, 1366×768 | **el framebuffer de consola es el de la Intel** |
| nodos `fb*` | sólo `fb0` en el sistema | una sola consola |
| `01:00.0/drm` | `card1 controlD65 renderD129` | **la RX550 no tiene nodo fb** |
| conectores de `card1` | `DVI-D-1`, `HDMI-A-2`, **conectados** | la RX550 tiene salidas vivas |
| `00:02.0` `boot_vga` | ausente | no es la VGA de arranque |
| `01:00.0` `boot_vga` | **1** | sí lo es según el arbitro legacy |
| log | `vgaarb: VGA device added: decodes=io+mem, owns=io+mem` | **posee el rango VGA legacy** |

> **El riesgo real no es una pantalla negra.** La Intel ya tiene la consola y ya la
> conduce. La RX550 **ya posee** el rango VGA legacy y tiene **dos salidas conectadas que
> nada está excitando**.
>
> Un driver que programe DM correctamente en esta tarjeta **encenderá `DVI-D-1` y/o
> `HDMI-A-2` en un monitor que la Intel también está excitando**. El síntoma esperable es
> **duplicación silenciosa de salida, o una pelea de modos** — no una consola perdida.

Eso cambia la conversación con el propietario: antes de tomar posición hay que decidir
**qué se quiere que pase con esas dos salidas**, no sólo si se conserva la consola.

## 8. Lo que este hallazgo NO hace

- **No inventarié offset a offset** la superficie de `dce110_hwseq.c` (491 símbolos). La
  cabecera está localizada y es la autoridad; el catálogo es trabajo aparte.
- **No lee los conectores** ni `/sys/bus/pci`. Que figuren como "conectados" no dice si hay
  un monitor encendido al otro extremo: eso **no está medido**.
- **No re-verifiqué** que `baseline/` sea bit-exacto al kernel que se compiló. Hay tres
  correspondencias fuertes (`DC_VER` por dos vías, `vermagic`, `amdgpu_dm.c` estable) pero
  el árbol no tiene `Makefile` raíz y no pude confirmar `VERSION = 7`.
- **No comprueba `CONFIG_DRM_AMD_DC`**. Que DC esté compilado y activo lo prueba el log;
  qué pasaría con `dc=0` no lo miré en esta pasada.
- **No toca la GPU.** Lectura de fuentes y del `.ko`, sin sudo.

## 9. Procedencia

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/     (fuente del kernel que corre)
  display/amdgpu_dm/amdgpu_dm.c:3818-3824      dm_ip_block, 1.0.0
  display/amdgpu_dm/amdgpu_dm.c:4024-4051      los 15 ganchos de amdgpu_dm_funcs
  display/amdgpu_dm/amdgpu_dm.c:14168          dm_read_reg_func, address sin transformar
  display/amdgpu_dm/                           35 ficheros, amdgpu_dm.c = 421 443 B
  display/dc/core/dc_resource.c:176-179       POLARIS12_V -> DCE_VERSION_11_2
  display/dc/hwss/dce112/dce112_hwseq.c       160 lineas, delega en dce110
  display/dc/resource/dce112/dce112_resource.c:1222-1230  polaris_11_resource_cap
  display/include/dal_types.h:34               enum dce_version
  include/asic_reg/dce/dce_11_2_d.h            874 647 B  (sha identico en los dos arboles)
  amdgpu/amdgpu_ip.c:241                       el formato del log
  amdgpu/dce_v8_0.c, amdgpu/dce_v10_0.c        0 apariciones de POLARIS12
  find -name 'dc_dm.c' -o -name 'dc_dm.h'      0 resultados
module  /lib/modules/7.1.3-200.nobara.fc44.x86_64/.../amdgpu.ko.zst
        34773 simbolos ; 491 dce110_* ; 44 dce112_* ; strings "3.2.378" ; param dc=
log     Display Core v3.2.378 initialized on DCE 11.2
otro    rx550-upstream-7.2.8/display/amdgpu_dm/amdgpu_dm.c:4053  identico
```

```text
ESTADO=PROBADO · el bloque dm existe en este arbol, en este kernel y dentro del modulo que
       corre.  El NOT_FOUND de 1434 fila 6 era un ERROR DE RUTA, no un podado
       · el fichero es display/amdgpu_dm/amdgpu_dm.c; dc_dm.c nunca existio en la serie
       · la generacion de hardware es DCE 11.2, por dc_resource.c:176-179 y por el log
       · dce_v8_0.c y dce_v10_0.c NO son el camino: 0 menciones de POLARIS12
       · "dce_v1_0_0" es version de abstraccion de software, no generacion de silicio
       · la cabecera que aplica es dce_11_2_d.h, indice dword absoluto en BAR5, igual que
         el resto de bloques
CONFIRMA 155  el DC de esta maquina es DCE 11.2
REFUTADO  "corpus podado" como motivo: los dos arboles vendorizados contienen el gestor de
       display, la cabecera DCE 11.2 y los cinco subdirectorios dce112/
RIESGO     hay TRES trampas de direccionamiento que hacen falta:
       (a) la mayoria del codigo esta en dce110_hwseq.c, no en el shim de 160 lineas
       (b) el nombre del bloque no dice que cabecera usar: dce_v1_0_0 -> dce_11_2_d.h
       (c) DP_AUX aparece en los simbolos pero la placa NO tiene DisplayPort
SEGURIDAD  el riesgo de tomar posicion no es perder la consola: la Intel ya la tiene y ya la
       conduce.  La RX550 ya posee el rango VGA legacy y tiene dos salidas conectadas sin
       excitar.  Programar DM bien las encendera en un monitor que la Intel tambien maneja:
       duplicacion silenciosa o pelea de modos
LIMITE   no se inventariaron los offsets de dce110_hwseq.c; el estado del sink fisico no
       esta medido; CONFIG_DRM_AMD_DC y el caso dc=0 no se revisaron
Siguiente  1) decidir con el propietario QUE debe pasar con DVI-D-1 y HDMI-A-2 antes de
          cualquier trabajo de DM: eso es una decision de producto, no tecnica
         2) inventariar dce110_hwseq.c por bloques (planos, escalador, PLL, enlace, IRQ):
           es el trabajo real de display, y ahora se sabe donde esta
         3) el bloque 5 (powerplay / smu) sigue NOT_FOUND de verdad: ese si es un hueco
```
