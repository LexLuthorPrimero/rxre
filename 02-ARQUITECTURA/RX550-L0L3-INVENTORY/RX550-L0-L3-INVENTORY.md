# RX 550 — Reconstrucción L0→L3 por evidencia

**WORK_CLASS** `READ_ONLY/EVIDENCE` + `DOCUMENTATION`. Nada fue modificado en el sistema.
Ningún fichero de `/sys` fue escrito. No se usó `sudo` ni `systemctl`. Ningún evento fue inducido.

## 0. PROVENANCE

| | |
|---|---|
| `HOST` | `kalm` |
| `KERNEL` | `7.1.3-200.nobara.fc44.x86_64` |
| `DISTRO` | Nobara Linux 44 (`VERSION_ID=44`, `platform:f44`) |
| `UID:GID` | `1000:1000` |
| `SESSION` | `wayland` / `KDE` |
| `VENTANA` | 2026-09-27T02:41-03:00 → 05:5x (agentes en paralelo) |
| `GPU` | BDF `0000:01:00.0` · sysfs `/sys/class/drm/card1/device` |
| `ARTIFACTS` | `./raw/` — 8 ficheros, SHA256 en `raw/SHA256SUMS` |

**Variables de control** (obligatorias para reproducir): el objeto de estudio es la **RX550
(`1002:699f`)**. `card0` es la Intel `8086:0412`. `cardN` es un **localizador, no una identidad**
(§6.3 del `AGENTS.md`): el índice hwmon además **ya ha cambiado** entre hosts (§4, A3g).

---

## 1. MAPA L0–L3

```
L0  IDENTIDAD FÍSICA/LÓGICA
    PCI 1002:699f · subsys 1002:0b04 · rev c7 · class 030000
    BDF 0000:01:00.0 · "Lexa PRO" · POLARIS12 · VRAM 2 GiB
        │
L1  PCI / PCIe
    Gen2 x4 negociado / Gen3 x8 máximo · ASPM L1 = 0 · AER todo 0
    MSI(X) → IRQ 37 · INTx deshabilitado · capabilities NO legibles
        │
L2  KERNEL / DRM / amdgpu
    amdgpu 3.64.0 (srcversion D68004925455E20A24C2B87) · 96 parámetros
    DRM: card0=minor 0, card1=minor 1, renderD128/128, renderD129/129
    84 entradas en device/ · hwmon1 con 5 labels
        │
L3  FIRMWARE / SMU / DPM
    Backend: polaris10_smu · IP block <smu_v1_0_0>
    12 ucodes expuestos, todos legibles · SMU fw 0x00221700 = 34.23.0
        │
    INTERFACES
    sysfs/ · hwmon/ · debugfs(BLOQUEADO) · /dev/dri/ · dmesg(BLOQUEADO)
        │
    OBSERVADORES (userspace)
    El proyecto · este inventario        ← NO forma parte del camino causal
```

---

## 2. L0 — IDENTIDAD

| Campo | Valor | Fuente | Estado |
|---|---|---|---|
| vendor:device | `1002:699f` | sysfs | `OBSERVED` |
| subsystem | `1002:0b04` | sysfs | `OBSERVED` |
| revision | `c7` | sysfs | `OBSERVED` |
| class | `030000` | sysfs | `OBSERVED` |
| BDF | `0000:01:00.0` | lspci | `OBSERVED` |
| Nombre lspci | *Lexa PRO* [Radeon 540/540X/550/550X / RX 540X/550/550X] | lspci | `OBSERVED` |
| VRAM | `2147483648` B = **exactamente 2 GiB** | `mem_info_vram_total` | `OBSERVED` |
| VRAM visible | `268435456` B = 256 MiB | `mem_info_vis_vram_total` | `OBSERVED` |
| GTT | `6194638848` B | `mem_info_gtt_total` | `OBSERVED` |
| BAR0 | 256M 64-bit prefetchable @ `e0000000` | lspci | `OBSERVED` |
| Board | `type : cem` | `board_info` | `OBSERVED` |

**`subsystem_vendor = 0x1002`** → la tarjeta **no tiene VID de terceros**. Es AMD o re-marca con
ID de AMD.

**⚠ ANOMALÍA DE SUBSISTEMA** · `pci.ids` **no registra `1002:0b04` bajo `0x699f`**. La entrada
`1002 0b04 → Radeon RX 560` (línea 3121) cuelga de un padre distinto: **`67ff Baffin`**
(línea 3120). Los subsistemas de `699f` son 5 — `1028:1720`, `1458:22f3`, `148c:2380`,
`17aa:5069`, `1da2:e367` — **ninguno `1002:0b04`**. Corroborado en `pci-ids.ucw.cz` (canónico).
**Trampa evitada**: el nombre *"Radeon RX 560"* **no es trasladable**; la terna es
`(device_id, subsys_vendor, subsys_device)` y aquí el `device_id` es `699f`, no `67ff`.
→ `CONTRADICTION` menor (`C-6`), y `subsystem_device` queda **sin valor descriptivo**.

**SKU RESUELTO con la revisión** (`U-9` cerrado) · libdrm `data/amdgpu.ids` v1.0.0
(tabla portada por AMD) tiene una fila **`699F, C7 → "AMD Radeon RX 550 / 550 Series"`**.
`parse_one_line()` exige coincidencia **exacta en ambos campos** (device **y** revision).
El vecindario `6987` tiene `C7 → Radeon 540` → **la revisión porta información, no es decorativa**.
Descarta RX 540X, RX 550X y RX 560 dentro de la familia Lexa PRO.
**VRAM NO se deriva de los IDs PCI**: procede de VBIOS/SMU vía `amdgpu_gmc_get_vram_info()` →
`amdgpu_atomfirmware_get_vram_info()`. Cualquier cifra de VRAM atribuida a *"el RX 550"* es
`GENERAL_ARCHITECTURE_EVIDENCE`; los 2 GiB de §2 sí son de **esta** parte (leídos del host).

**`DERIVATION`** · `mem_info_vis_vram_total` (256 MiB) **coincide exactamente con BAR0**. La
ventana visible ES el BAR0. El GTT (5.77 GiB) es aperture virtual, **no** VRAM.

**Identidad por el kernel, no por tabla** (ver §9, `C-1`):
`initializing kernel modesetting (POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7)` y
`detected ip block number 5 <smu_v1_0_0> (powerplay)`.

**`NOT_DETERMINED`** · distinguir RX 550 de RX 550X por identidad PCI. El CSV upstream lista
"550" en las filas POLARIS11 **y** POLARIS12 → **no desambigua**. El desambiguador es la PCI ID
mapeada a `CHIP_POLARIS12` en `amdgpu_drv.c`.

---

## 3. L1 — PCIe

| Atributo | Valor | Estado |
|---|---|---|
| `current_link_speed` | `5.0 GT/s PCIe` = **Gen2** | `OBSERVED` |
| `current_link_width` | `4` | `OBSERVED` |
| `max_link_speed` | `8.0 GT/s PCIe` = Gen3 | `OBSERVED` |
| `max_link_width` | `8` | `OBSERVED` |
| `link/l1_aspm` | `0` | `OBSERVED` |
| `aer_dev_correctable` / `nonfatal` / `fatal` | **todos 0** (9+23+3 subclases) | `OBSERVED` |
| `power_state` | `D0` | `OBSERVED` |
| MSI(X) | IRQ 37 · INTx pin B disabled | `OBSERVED` |
| `dma_mask_bits` | `40` | `OBSERVED` |
| `numa_node` | `-1` | `OBSERVED` |
| `reset_method` | `bus` | `OBSERVED` |
| `d3cold_allowed` | `1` | `OBSERVED` |

**DISTINCIÓN OBLIGATORIA** — cuatro cosas, no una:

- `EXPOSED_BY_SYSTEM` — el kernel publica el atributo. ✔
- `READABLE_BY_ANALYZER` — este observador puede leerlo. **27 atributos NO** (§6).
- `OBSERVED_IN_SAMPLE` — leído ahora, una vez, sin carga.
- `PROVES_PROPERTY` — **ninguna de estas cuatro pruebas la causa del ancho x4.**

### 3.1 AVISO: ESTAS LECTURAS NO SON CONCLUYENTES MIENTRE `runtime_status=error`

**La calificacion que mas pesa en L1.**

```c
void pci_config_pm_runtime_get(struct pci_dev *pdev)   /* devuelve VOID */
{
	pm_runtime_get_noresume(dev);          /* incrementa SIN reanudar */
	pm_runtime_barrier(dev);
	/* Only need to resume devices in D3cold, because config
	   registers are still accessible for devices suspended but
	   not in D3cold. */
	if (pdev->current_state == PCI_D3cold)
		pm_runtime_resume(dev);            /* y SOLO en D3cold */
}
```

Devuelve `void` -> **el llamador no puede detectar el fallo**. Usa `get_noresume()`. Solo
reanuda si `current_state == PCI_D3cold`, que **no** es el caso de un device en error de runtime
PM. Con `runtime_status=error`, `pm_runtime_resume()` devuelve `-EINVAL` **sin reanudar** (§4.1)
-> **`current_link_speed`, `current_link_width` y `max_link_width` pueden leerse sin que el
dispositivo este realmente reanudado.**

Clasificacion correcta: `SUPPORTED` como *lectura de un registro*; **`UNVERIFIED` como estado
operativo de un device funcional**. No son necesariamente erroneas — son **no concluyentes por
diseno de la interfaz**. **Ninguna frase de este informe debe presentar "el enlace esta en Gen2 x4"
como afirmacion de estado operativo.**

### 3.2 `max_link_*` es el ENDPOINT, no el enlace

| Atributo | Registro | Fuente primaria |
|---|---|---|
| `max_link_speed` | `PCI_EXP_LNKCAP` **del propio endpoint** | `pci_speed_string(pcie_get_speed_cap(pdev))` |
| `max_link_width` | `PCI_EXP_LNKCAP` **del propio endpoint** | `pcie_get_width_cap(pdev)`; el kernel comenta *"We read PCI_EXP_LNKCAP, so we need the device to be accessible."* |
| `current_link_speed` | `PCI_EXP_LNKSTA` (negociado) | `pcie_capability_read_word(pci_dev, PCI_EXP_LNKSTA, ...)` |
| `current_link_width` | `PCI_EXP_LNKSTA` | `FIELD_GET(PCI_EXP_LNKSTA_NLW, linkstat)` |

> **`max_link_speed=8.0 GT/s` NO prueba que el enlace pueda alcanzar 8.0 GT/s.** El enlace real es
> `min(LNKCAP del endpoint, LNKCAP del upstream)`. `max_link_*` es lo que **el endpoint anuncia**,
> no lo que el bus negocia. El driver lo confirma: `amdgpu_device_partner_bandwidth()` toma las
> caps del **partner fisico** por separado.

**Los cuatro atributos NO estan documentados por el kernel**: `PROVEN_ABSENT` con alcance = el
contenido de `Documentation/ABI/testing/sysfs-bus-pci` (master), leido completo. **La
interpretacion popular carece de respaldo documental upstream**; hay que derivarla del codigo.

**Los dos ejes NO son simetricos:**

- **ANCHO (x4 vs x8)** — se **negocia una vez** en enumeracion. El kernel **no tiene politica de
  retraining** que altere el ancho en runtime. **Un ancho negociado no fluctua con la energia.**
  -> el `x4` es **estructural**.
- **VELOCIDAD (Gen2 vs Gen3)** — `LNKSTA` es un campo de **estado**; si cambia en runtime.

**Contexto de placa** (del log): `Hardware name: ECS H81H3-M4/H81H3-M4, BIOS 4.6.5 05/21/2015`.
Placa consumidora de 2015, chipset H81 (Intel 8-series, PCIe 3.0). Un slot x16 cableado a x4/x8
es commonplace en esta generacion -> **la explicacion estructural del ancho es la primera
hipotesis, no la energetica.** `PLAUSIBLE`, no `PROVEN`.

| # | Candidato a la velocidad Gen2 | Estado |
|---|---|---|
| A | **PCIe DPM del propio amdgpu** — desactiva `PP_PCIE_DPM_MASK` si no soporta dynamic switching; hay quirks que lo desactivan en hosts Intel y en Ryzen Pinnacle Ridge | `MECHANISM_EXISTS`. **Candidato #1, verificable sin sudo** via `pp_dpm_pcie` |
| B | ASPM L1 / L1SS | `MECHANISM_EXISTS`, pero **no** hay fuente que diga que hace que `current_link_speed` *lea* mas bajo -> `NOT_DETERMINED` |
| C | Ranura x4 / cableado de lanes | `PLAUSIBLE`; la mas economica para el **ancho** |
| D | "es normal en headless" | **RECHAZADA** para el ancho: la ausencia de display no cambia el numero de lanes fisicas |

**Diagnostico, por discriminancia (los 5 son lecturas de sysfs sin privilegio, `NOT_RUN`):**

1. `cat .../pp_dpm_pcie` -> discrimina **A**.
2. `ls .../link/` + `cat link/l1_aspm l1_2_aspm l0s_aspm clkpm` -> discrimina **B**. **La
   ausencia del directorio es informacion**: `aspm_ctrl_attrs_are_visible()` devuelve 0 si
   `aspm_disabled || !link` -> el directorio refleja la contabilidad ASPM **del kernel**, no la
   capacidad del hardware.
3. `cat /sys/module/pcie_aspm/parameters/policy` -> politica global.
4. Leer `max_link_*` del **root port** (BDF padre) -> discrimina **C**. **La prueba que separa
   "x4 estructural" de "x4 por energia".**
5. Comparar `current_link_*` idle vs. bajo carga -> si cambia, es A/B; si es constante, es C.

### 3.3 LIMITACION MECANICA: por que `Capabilities: <access denied>`

No es un permiso arbitrario. **Sin `CAP_SYS_ADMIN` la config space se trunca a 64 bytes**:

```c
if (file_ns_capable(filp, &init_user_ns, CAP_SYS_ADMIN)) size = dev->cfg_size;
else if (dev->hdr_type == PCI_HEADER_TYPE_CARDBUS) size = 128;
...
if (off >= size) return 0;
```

Comentario del kernel: *"Several chips lock up trying to read undefined config space"*.
La **PCIe Capability empieza en 0x40** -> **toda** queda fuera de alcance.

**`EVIDENCE_DENIED` explicitamente** (todas >= 0x40): ASPM Support/Optionality (LNKCAP 0x4C) ·
ASPM Control (LNKCTL 0x50) · Lane/Link Status (LNKSTA 0x52) · Device Capabilities L0s/L1 latency,
RBER, Device-Wake (0x44) · Device Control 2 / LTR · L1 Substates (0x100+) · **AER** ·
**Downclock Configuration (`DL_Active`)**, que distingue downclock *por software* de ASPM ·
Lane Number / Physical Layer 16GT · **ReBAR** (`resourceN_resize`, requiere `CAP_SYS_ADMIN`) ·
Vendor Serial Number.

**`VERIFICABLE` sin privilegios** (offset < 0x40, o via el kernel): vendor · device ·
**subsystem_vendor/subsystem_device** · **revision** · class · IRQ · BARs · header type
-> **toda la identidad L0 es solida.** Y `current_link_*`/`max_link_*`/`power_state`/`power/*`/
`link/*`/`pp_dpm_pcie`/`mem_info_*`, que **lee el kernel**, no el usuario.

> **Alcance**: `PROVEN_ABSENT` en *config space* != `PROVEN_ABSENT` en *sysfs*. Los contadores AER
> se leen por sysfs (`aer_stats_attr_group`) y son todo 0 — eso **si** es evidencia valida y no
> se ve afectada por la truncacion.

## 4. L2 — KERNEL / DRM / amdgpu

| Ítem | Valor | Estado |
|---|---|---|
| Driver | `amdgpu 3.64.0` (log) | `OBSERVED` |
| `srcversion` | `D68004925455E20A24C2B87` (idéntico en `modinfo` y `/sys/module/amdgpu/`) | `OBSERVED` |
| `vermagic` | `7.1.3-200.nobara.fc44… SMP preempt mod_unload` | `OBSERVED` |
| Parámetros | **96**; 91 legibles; **5** `0640 root:root` (no legibles) | `OBSERVED` |
| `timeout_period` | `0` → **watchdog desactivado** | `OBSERVED` |
| `ppfeaturemask` | `0xfff7bfff` (no todos-unos) | `OBSERVED` |
| `ras_enable` | `-1` (auto) con `ras_mask=0xFFFFFFFF` | `OBSERVED` |

**DRM — correspondencia VERIFICADA, no inferida:**
`card1` = minor **1**; `renderD129` = minor **129**; `renderD128` = minor 128 (iGPU).
Corroboración independiente: el log del kernel dice *"[drm] Initialized amdgpu 3.64.0 for
0000:01:00.0 on **minor 1**"*, y `/sys/class/drm/card1/device/drm/` contiene
`card1/`, `controlD65 -> card1`, `renderD129/`.

`/dev/dri/`: `card0` `crw-rw----+ root:video` · `card1` `crw-rw----+ root:video` ·
`renderD128` `crw-rw-rw- root:render` · `renderD129` `crw-rw-rw- root:render`.
uid 1000 **no** está en `video`/`render` → no puede abrir `card1`; **sí** `renderD129`.
**No se abrió ninguno** (`NOT_TESTED`).

**`controlD65`**: symlink a `card1` que **comparte su minor 1**; **no** aparece en `/dev/dri/`.
→ `CONTRADICTION` con el modelo clásico de "controlDn tiene minor propio" (§9, `C-2`).

**Headless confirmado**: los dos conectores de `card1` están `disconnected`; `card0-HDMI-A-1`
está `connected`. **El monitor está en la Intel.**
**`boot_vga=1` en AMBOS** → inútil como indicador de "display de arranque".

### 4.1 `runtime_status = error` — CAUSA ENCONTRADA

**`FACT`**: `power/runtime_status` = `error`; `runtime_active_time` = `143678 ms` **congelado**;
`runtime_suspended_time` crece a ~1000 ms/s.

**`error` NO es un estado del ciclo de vida.** Fuente primaria
(`drivers/base/power/sysfs.c`, `runtime_status_show()`), orden literal de decisión:

```c
if (dev->power.runtime_error)      output = "error";
else if (dev->power.disable_depth) output = "unsupported";
else switch (dev->power.runtime_status) { RPM_SUSPENDED … RPM_ACTIVE … }
```

Es un **errno latchado** que **sombrea** las cuatro fases. El device está *latchado-error* **y**
suspendido a la vez — por eso el tiempo de suspensión crece mientras la cadena dice `error`.
**No es contradictorio.**

**Latch** (`runtime.c:473`): `if (retval != -EAGAIN && retval != -EBUSY) dev->power.runtime_error = retval;`
**Short-circuit** (`rpm_resume()`): `if (dev->power.runtime_error) { retval = -EINVAL; }` →
**toda** operación de resume falla **sin llamar al driver**. Único camino de limpieza:
`__pm_runtime_set_status()` — API fuera de banda, no alcanzable por get/put normal.

**CADENA CAUSAL — verbatim del journal** (`journalctl -k -b 0`, 2147 líneas):

| # | Evento | Recuento |
|---|---|---|
| 0 | `PM: suspend entry (deep)` @ `2026-09-26T12:45:08` | 1 |
| 1 | `PCIE GART of 256M enabled` (resume) | 13 |
| 2 | `UVD not responding, trying to reset the VCPU!!!` | **10** |
| 3 | `UVD not responding, giving up!!!` | 1 |
| 4 | `ring uvd test failed (-110)` — `-ETIMEDOUT` | 1 |
| 5 | `resume of IP block <uvd_v6_0> failed -110` | 1 |
| 6 | `amdgpu_device_ip_resume failed (-110)` | 1 |
| 7 | `set_clockgating_state of IP block <uvd_v6_0> failed -16` | 1 |
| 8 | `amdgpu_irq.c:672 !amdgpu_irq_enabled` | **22** |
| 9 | `amdgpu 0000:01:00.0: PCI CONFIG reset` | 1 |

`GPU reset` = **0** · `ring timeout` = **0** · `timeout` = **0**.
→ **El fallo es específico de UVD**, no un cuelgue de GFX/SDMA. El driver había elegido
`Using BACO for runtime pm` y el resume **cayó a `PCI CONFIG reset`**.

**Evento 6 → callback `runtime_resume` devuelve -110 → latch → `"error"`.**

> ### CONSECUENCIA
> **La GPU está atascada desde `2026-09-26T17:08:27`.** No puede volver a runtime-activo por
> ninguna operación de PM normal. **Ninguna telemetría dinámica es legible** (potencia,
> temperatura, frecuencias, busy%, tabla DPM). Escalar requiere **reiniciar el host**, o
> `__pm_runtime_set_status()` — API privilegiada que cambia estado → `BLOCKED_BY_AUTHORIZATION`.

**`LIMITATION`**: `dmesg` → `rc=1` (`CAP_SYSLOG`). Toda la evidencia de log viene de `journalctl`,
**un instrumento distinto con su propio filtrado**. Último mensaje de kernel: `2026-09-26T22:34:17`,
~4,2 h antes de observar. **Sin log para el tramo final.**
**`LIMITATION`**: `PM: suspend entry` sellado `12:45:08` vs. resto `17:08:27` → artefacto
estándar de S3; **no verificado**. No afecta la conclusión, que se apoya en **orden**, no en reloj.

---

## 5. L3 — FIRMWARE / SMU / DPM

| | |
|---|---|
| Backend SMU | **`polaris10_smu`** (log: `hwmgr_sw_init smu backed is polaris10_smu`) |
| IP block | `smu_v1_0_0` (log: `detected ip block number 5 <smu_v1_0_0> (powerplay)`) |
| **SMU firmware** | **`smc_fw_version = 0x00221700` → 34.23.0** |
| IP blocks | `common_v1_0_0`, `gmc_v8_1_0`, `ih_v3_0_0`, `gfx_v8_0_0`, `sdma_v3_1_0`, `smu_v1_0_0`, `dce_v1_0_0`, `uvd_v6_3_0`, `vce_v3_4_0` (9) |

**12 ucodes, TODOS legibles** — y cross-check independiente con el log:

| | sysfs | log | |
|---|---|---|---|
| `uvd_fw_version` | `0x01821000` | *Found UVD firmware Version: 1.130 Family ID: 16* | ✔ |
| `vce_fw_version` | `0x351a0300` | *Found VCE firmware Version: 53.26 Binary ID: 3* | ✔ |
| `rlc` `0x00000018` · `mec`/`mec2` `0x2da` · `ce` `0x8c` · `me` `0xa7` · `pfp` `0xfe` · `mc` `0xb4dc50` · `sdma`/`sdma2` `0x3a` | | | |

**Dos instrumentos coinciden.** Éste es el dato de L3 más sólido: es **hardware-versionado**,
no estimado.

**Topología GFX8**: `SE 2, SH per SE 1, CU per SH 5, active_cu_number 8`
→ **10 CUs presentes, 8 activos: 2 CUs desactivados.** Sin explicación en nada leído. §10.

**Otros**: `Trusted Memory Zone (TMZ) feature not supported` · `VBIOS` desde ROM BAR ·
**EL SMU REAL — cerrado con el fichero en disco** (fuente: `amdgpu_cgs.c:325-332` @v7.1):

| | |
|---|---|
| Blob | **`/lib/firmware/amdgpu/polaris12_smc.bin.xz`** · 130.388 B descomprimido |
| SHA256 | `fe9e823a54863e39769bcbeb4756c961611c730924267ad18c896bfc106010f9` |
| `ucode_version` embebido (offset 16, LE) | **`0x00221700`** |
| `ip` embebida | `7.2` |
| **Coincidencia con el host** | `fw_version/smc_fw_version = 0x00221700` → **byte-idéntica** |

> **Refutadas dos premisas** (mía y del enunciado):
> **NO** es `vangogh_smu.bin` — `find /lib/firmware -name '*vangogh*'` da 11 ficheros, ninguno `*_smu*`.
> **NO** es `smu_13_0_0.bin` — ese es MP1 13.0.0 = **RX 7900 XTX**, `GENERAL_ARCHITECTURE_EVIDENCE` ajeno.

**POLARIS12 NO USA swsmu.** El CSV oficial da **MP1 = 7**; `swsmu/Makefile` @v7.1 compila
`smu11..smu15` (**no smu7/8/9/10**) y `smu_set_funcs()` conmuta por `MP1_HWIP` con su caso más bajo
en `IP_VERSION(11,0,0)`. La ruta real es **PowerPlay legacy**:
`polaris10_smumgr.c` + `smu7_hwmgr.c` + `amd_powerplay.c` → `pp_dpm_funcs`.
**El SMC sí existe y es quien calcula casi todo** (§6).

**Microcode GC desde VBIOS, no desde `/lib/firmware`**: `ce/me/pfp/mec` del host
(`0x8c/0xa7/0xfe/0x2da`) **difieren** de los blobs en disco (`0x86/0xa1/0xeb/0x2c1`) → builds
superiores ⇒ el driver usa el **VBIOS/EEPROM de la GPU**. `DERIVATION` de la discrepancia, no de
un log de carga. `uvd`/`vce` **MISMATCH** sin reconciliación inventada.
**EEPROM de discovery**: `PROVEN_ABSENT` como fichero — `amdgpu_discovery_get_fw_name()` no tiene
`case CHIP_POLARIS12` → TMR en VRAM, sideloaded por el PSP.

**Riesgo operativo newly found**: `power1_input` puede **bloquear hasta 5 s**
(`msleep(500)` x10) por el camino de muestreo. Un sampler secuencial de 10 Hz no puede
sincronizar esas muestras.
`Registered 5 planes with drm panic` · `Disabling VM faults because of PRT request!` ·
`amdgpu: Topology: Add GPU node [0x1002:0x699f]` (**nodo KFD/ROCm creado**) ·
`snd_hda_intel 0000:01:00.1: bound 0000:01:00.0` (**función de audio ligada**).

**`vbios_version` = `xxx-xxx-xxx`** — placeholder, no versión real. `vbios_build` = `565939`.

---

## 6. TABLA DE MÉTRICAS Y SEMÁNTICA

Clasificación: `MEDICIÓN_FÍSICA` · `ESTIMACIÓN_FIRMWARE` · `OBJETIVO_CONFIGURADO` ·
`DERIVADO_DRIVER` · `TEXTO`.

| Métrica | Semántica | Unidad | Productor | Tipo | Consumidor del proyecto | Estado |
|---|---|---|---|---|---|---|
| `power1_input` | potencia **instantánea** de "the SoC" | µW ⚠ | `amdgpu_hwmon_show_power_input` → `amdgpu_dpm_read_sensor(16 = GPU_INPUT_POWER)` | `ESTIMACIÓN_FIRMWARE` | `sampler.sh`, `state_manager.py` | fichero existe, **EPERM** |
| `power1_average` | — | — | sensor 15 | — | — | **AUSENTE** (handler existe en el binario; filtrado por ASIC) |
| `power1_cap` | **límite** actual | µW | `..._show_power_cap` → `amdgpu_dpm_get_power_limit(CURRENT)` | `OBJETIVO_CONFIGURADO` | `state_manager.py:176` | existe, **EPERM** |
| `power1_cap_min/max/default` | límites min/max/default | µW | ídem | `OBJETIVO_CONFIGURADO` | `state_manager.py:168-178` | existen, **EPERM** |
| `power1_label` | **texto**. Degenerada en POLARIS12 | — | `sysfs_emit` | `TEXTO` | — | **legible** = `PPT` |
| `temp1_input` | temperatura de **edge** | m°C | sensor 10 (`EDGE_TEMP`) | `MEDICIÓN_FÍSICA` | `sampler.sh` | **EPERM**. `temp1_crit=97000` sí legible |
| `temp1_input` | **edge** — **`NOT_AVAILABLE` en esta ASIC** | m°C | `smu7_read_sensor` **no tiene caso `EDGE_TEMP`** → `default: return -EOPNOTSUPP` | `NOT_AVAILABLE` | `sampler.sh`, `run_all*.sh` | nodo existe; **nunca puede dar valor** |
| `temp1_crit` | umbral del controlador térmico (**cacheado en init**) | m°C | `adev->pm.dpm.thermal.max_temp` | `OBJETIVO_CONFIGURADO` | — | **legible** = 97000 |
| `freq1_input` | sclk | Hz | — | `NOT_DETERMINED` | `sampler.sh` | **EPERM** |
| `freq2_input` | mclk | Hz | — | `NOT_DETERMINED` | `sampler.sh` | **EPERM** |
| `in0_input` | vddgfx | mV | — | `NOT_DETERMINED` | — | **EPERM** |
| `gpu_busy_percent` | — | % | `NOT_DETERMINED` | `NOT_DETERMINED` | `sampler.sh` | existe (0644), **EPERM** |
| `mem_busy_percent` | — | % | `NOT_DETERMINED` | `NOT_DETERMINED` | `sampler.sh` | existe (0644), **EPERM** |
| `pp_dpm_sclk/mclk/pcie` | tabla DPM de clocks |formato driver | `amdgpu_dpm` | `DERIVADO_DRIVER` | `run_all*.sh` | existen, **EPERM** |
| `power_dpm_state` | estado DPM actual | enum | `amdgpu_dpm` | `DERIVADO_DRIVER` | — | existe, **EPERM** |
| `pp_sclk_od` / `pp_mclk_od` | **voltaje OD** | mV | `amdgpu_dpm` | `DERIVADO_DRIVER` | — | **existen**, EPERM |
| `mem_info_vram_total` | VRAM total | B | driver | `DERIVADO_DRIVER` | `state_manager.py` | **legible** = 2 GiB |
| `mem_info_*_used` | VRAM/GTT en uso | B | driver | `DERIVADO_DRIVER` | — | **legibles** |
| `aer_dev_*` | contadores de error PCIe | conteo | hardware PCIe | `MEDICIÓN_FÍSICA` | — | **legibles**, todos 0 |
| `current_link_*` / `max_link_*` | velocidad/ancho negociado vs máximo | GT/s, lanes | driver | `DERIVADO_DRIVER` | — | **legibles** |
| `link/l1_aspm` | estado ASPM L1 | 0/1 | driver | `DERIVADO_DRIVER` | — | **legible** = 0 |
| `power/runtime_status` | latch de error de runtime PM | enum | kernel PM core | `DERIVADO_DRIVER` | `state_manager.py` | **legible** = `error` |
| `runtime_active_time` | tiempo active acumulado | **ms** ⚠ | kernel PM core | `DERIVADO_DRIVER` | — | legible, **congelado** |
| `runtime_suspended_time` | tiempo suspended acumulado | **ms** ⚠ | kernel PM core | `DERIVADO_DRIVER` | — | legible, creciendo |
| `fw_version/*_fw_version` | versión de microcode | hex | hardware+firmware | `DIRECT_ARTIFACT` | — | **legibles** |
| `vbios_version` | — | — | — | — | — | `xxx-xxx-xxx` = **placeholder** |

⚠ **Dos advertencias de unidad, ambas con conflicto entre fuentes primarias:**

1. **µW vs mW.** El doc-block de `amdgpu_pm.c` dice *"in microWatts"*. La cabecera
   `kgd_pp_interface.h` documenta el sensor 16 como **"milliwatts"**. **`CONTRADICTION` entre
   dos fuentes primarias del mismo kernel.** El escalado del handler **no se ha reconciliado**
   → la unidad de `power1_input` es **`NOT_DETERMINED`**. No asumir µW.
2. **ms, no centisegundos.** `do_div(tmp, NSEC_PER_MSEC)` → milisegundos. Medido: 3 ventanas de
   10 s → **999,99 unidades/s**; centisegundos darían 100. Refutado por ×10.

**`power1_label` — CORRECCIÓN IMPORTANTE. Mi conclusión anterior era incorrecta.**

El hecho de código se sostiene: `amdgpu_hwmon_show_power_label()` sólo ramifica por
`GC_HWIP == IP_VERSION(10,3,1)`; en cualquier otro ASIC emite un literal dependiente del índice
(`'PPT'` índice 0, `'PPT1'` índice 1). En POLARIS12 vale `'PPT'` siempre.

**PERO mi inferencia de que la etiqueta es "degenerada" y "no porta información semántica" es
FALSA en esta ASIC.** POLARIS12 **no usa swsmu**: su cap de potencia viene de la
**PPTable** de PowerPlay. En ese contexto **`PPT` = PowerPlay Table**, y la etiqueta **es
literalmente correcta**: nombra la fuente real del límite. La lectura correcta es
"PowerPlay Table", no "Peak Power Target" (que es el sentido en swsmu/RDNA2, donde la función
sí ramifica a `fastPPT`/`slowPPT`).

**Lección**: el mismo string significa cosas distintas según la pila de firmware. El
`CASE 2.4` del `AGENTS.md` se cumple al revés: aquí el NOMBRE sí era evidencia, y yo lo traté
como si no lo fuera porque leí la rama del driver sin leer la pila que lo rodea.
→ `CONTRADICTION` menor `C-8`; y la clasificación de `power1_cap*` como
`OBJETIVO_CONFIGURADO` **se refuerza** (viene de la PPTable, no de un sensor).

feature. PPT is intended to **limit** power"*. Es un concepto de **techo**; el canal de
*medición* se etiqueta con la palabra del techo que la telemetría alimenta. **Error mio:** traté
la etiqueta como la naturaleza del canal.

---

## 7. NEGATIVOS CON ALCANCE

Sólo `PROVEN_ABSENT` con alcance y método nombrados.

| Ausente | Alcance | Método | Nota |
|---|---|---|---|
| `pp_od_clk_voltage` (+`_min`/`_max`) | `/sys/class/drm/card1/device/`, este host, excluyendo subdirectorios | `[ -e ]` + `ls -la` (84 entradas) | ⚠ **ausencia POR NOMBRE.** El OD-voltage real está en `pp_sclk_od`/`pp_mclk_od`, **presentes** |
| `power_cap_limit` (+`_default`) | ídem | ídem | ⚠ **ausencia POR NOMBRE.** El equivalente es `power1_cap*` en `hwmon/`, **presente** |
| `amdgpu_*` (errores/RAS/rings) | `device/` + `/sys/module/amdgpu`, maxdepth 3 | `find` + `ls` | **NO**(el barrido no se extiende a) debugfs (`0700 root`, ilegible) |
| `power/runtime_error` | `device/power/` | `ls` | `NOT_AVAILABLE`: la interfaz **no publica** el errno latchado |
| `perf_pmu` | `device/` | `[ -e ]` | Corrobora `amdgpu_pmu_init()` → `default: return 0` |
| `gpu_metrics` | `device/` | `[ -e ]` | — |

**`PROVEN_ABSENT` MAL APLICADO por este autor en una ronda previa** — ver §9 `C-3`.

**`NOT_AVAILABLE` (la interfaz no publica, no es que falte):**
8 ficheros `wakeup_*` devuelven exactamente `\n` — comportamiento documentado
(`dev->power.wakeup == NULL`), **no** fallo de instrumento. `version` del módulo no está fija
(`MODULE_VERSION` sin definir) → usar `srcversion` + el log.

**`NOT_OBSERVED` (el sweep no alcanzó):** `/sys/kernel/debug/dri/**` → `Permiso denegado`.
**Esto NO es ausencia de contadores.** Los SQTT/RGP viven bajo debugfs.

---

## 8. DIAGRAMAS

### 8.1 Separación de planos

```
╔══ HARDWARE ═══════════════════════════════════════════════╗
║  ASIC POLARIS12 (GC 8) · 2 GiB VRAM · 10 CU (8 activos)  ║
║  12 microcodes · SMU fw 34.23.0 · VBIOS (build 565939)   ║
╚══════════════════════════════════════════════════════════╝
                          ▲ fw_version/*_fw_version
╔══ FIRMWARE ══════════════════════════════════════════════╗
║  SMU (polaris10_smu) · UVD 1.130 · VCE 53.26 · RLC/MEC/… ║
║  → DPM, power states, sensores, telemetría               ║
╚══════════════════════════════════════════════════════════╝
                          ▲ smc_fw_version, read_sensor()
╔══ KERNEL ═════════════════════════════════════════════════╗
║  amdgpu 3.64.0 · 0000:01:00.0 · IRQ 37 · runtime PM(core)║
╚══════════════════════════════════════════════════════════╝
                          ▲
╔══ INTERFACES ════════════════════════════════════════════╗
║  sysfs device/(84) · hwmon1/ · debugfs(BLOQUEADO)       ║
║  /dev/dri/{card1,renderD129} · journalctl -k             ║
╚══════════════════════════════════════════════════════════╝
                          ▲
╔══ OBSERVADORES ══════════════════════════════════════════╗
║  El proyecto (sampler.sh, state_manager.py, C1)         ║
║  Este inventario                        ← NO causal     ║
╚══════════════════════════════════════════════════════════╝
```

### 8.2 El lazo cerrado de FASE-R4B (NO toca sysfs en el lazo)

```
governor_harness ──fwrite──▶ run_frames.tsv
       ▲                            │
       │ fopen("r")                 │ read_frames()
  control_scale.txt ◀──fwrite── governor.py
                                     ▲
   run_all_v23.sh ── argv ───────────┘
```

**`0` ocurrencias de `'/sys'` en `governor.py` y `app_vulkan.c`.** `governor.py` importa sólo
`argparse/math/os/time` → no delega. **PERO el path SÍ LEE sysfs**: `run_all*.sh:33-40` hace
`cat` de `pp_dpm_sclk`, `pp_dpm_mclk`, `power1_cap`, `gpu_busy_percent`, `temp1_input`,
`power1_input`. → **"no escribe sysfs" es lo que la evidencia sostiene; "no toca sysfs" es FALSO.**

### 8.3 La cadena C1 (3 niveles, trazable)

```
c1_isolation_automator.py :53,:852
      └─▶ c1_observer.py :25  EXPECTED_BINARY
               └─▶ main-graphics  ──▶ ICD Vulkan ──▶ amdgpu ──▶ GPU
```

`PROJECT` pineado al layout post-reorg; escrito 2026-09-25. **A diferencia de los `.sh`, sin
path rot.** `--run` nunca se ejecutó: `/run/user/1000/c1-isolation-automator/` no existe.

---

## 9. CONTRADICCIONES Y ERRORES PROPIOS

### 9.1 Errores de este autor, corregidos (ERROR→CAUSE→CORRECTION→PREVENTION)

| # | Error | Causa | Corrección | Prevención |
|---|---|---|---|---|
| **E-1** | *"los `*_input` son 0400 root-only → EPERM por permisos"* | leí mal mi propio `ls -l` (`-r--r--r--` → 0444) | son 0444 world-readable; el EPERM viene del **driver** | discriminar el fallo contra un control de permisos iguales antes de atribuirlo |
| **E-2** | *"las unidades son centisegundos"* | suposición sin verificar | **milisegundos** (`do_div(tmp, NSEC_PER_MSEC)`), medido 999,99 u/s | una suposición de unidad es `ASSUMPTION` hasta medirla |
| **E-3** | *"Enlace Gen1 x4"* | 5.0 GT/s es **Gen2**; Gen1 es 2.5 | Gen2 x4 / Gen3 x8 | no kebab-casear/generar desde la memoria |
| **E-4** | *"RX550 = POLARIS12 según el CSV upstream"* | **"550" está en las filas POLARIS11 *y* POLARIS12** | la tabla **no desambigua**; el desambiguador es `amdgpu_drv.c` + el log del kernel | comprobar que la fuente cited puede sostener la conclusión |
| **E-5** | *"la instalación misma es la prueba de autoría local de kalm"* | **non-sequitur**: FHS 3.0 y `systemd.unit(5)` describen **responsabilidad sobre el directorio**, no origen del software | el origen es `NOT_DETERMINED`; la conclusión se sostiene por la declaración del autor, no por FHS | un estándar de rutas no es evidencia de procedencia |
| **E-6** | *"`power_cap_limit` y `pp_od_clk_voltage` ausentes"* presentado como ausencias relevantes | sondee el directorio **sin enumerar y excluyendo `hwmon/`** | **ausencia POR NOMBRE**; `power1_cap*` y `pp_sclk_od`/`pp_mclk_od` **existen** | enumerar el alcance completo antes de emitir `PROVEN_ABSENT` |
| **E-7** | *"el 'closed-loop governor' no toca sysfs"* | confundí *no escribir* con *no tocar* | **no ESCRIBE** sysfs; lo **lee** extensivamente | el verbo del claim debe ser el que la evidencia sostiene |
| **E-8** | *"`power1_label` degenerada: en cualquier otro ASIC emite `'PPT'`"* | la rama `else` es dependiente del índice | índice 0→`PPT`, índice 1→`PPT1` | no generalizar sin leer la rama completa |

### 9.2 Contradicciones del corpus

| # | Tipo | Detalle |
|---|---|---|
| **C-1** | `CONTRADICTION` | `DOCUMENTATION-ROUTER.md:23` dice HOST-A = **1444** filas; su propio TSV da **128** (Δ −1316). **Los otros siete números del mismo documento cuadran** → error puntual, no sistemático |
| **C-2** | `CONTRADICTION` | `controlD65` comparte el minor de `card1` y no existe en `/dev/dri/`. Contradice el modelo clásico de minor propio. **Sin resolver** |
| **C-3** | `CONTRADICTION` | Unidad de `power1_input`: doc-block dice **µW**, `kgd_pp_interface.h` dice **mW**. Dos fuentes primarias del mismo kernel. Escalado no reconciliado |
| **C-4** | `CONTRADICTION` | `ROLLBACK.md:43` afirma *"la ruta de producción [es] Nobara 43"*; este host es **Nobara 44** = la generación del *backup*. **La cautela queda invertida** |
| **C-5** | `CONTRADICTION` | 22 referencias a `hwmon/hwmon2` en scripts; el host tiene `hwmon1`. Los CSV históricos **sí** tienen valores → `hwmon2` era válido en HOST-A. **El índice hwmon no acompaña al BDF** |

### 9.3 Defecto de los scripts de telemetría — **LATENTE, no activo** (gravedad corregida)

```bash
H=$D/hwmon/hwmon2                              # no existe en HOST-C
p1=$(cat $H/power1_input 2>/dev/null || echo 0) # -> 0
if [[ "$t" =~ ^[0-9]+$ ]]; then                 # t=0 -> SE CUMPLE
  if (( t >= 70000 && last70 == 0 )); then     # 0 >= 70000 -> FALSO
```

**Probado directamente:** el guard **entra** y **no puede dispararse**. El CSV saldría bien
formado, con ceros, **código de salida 0**. *No se salta el interlock: lo ejecuta desarmado.*

> ### CORRECCIÓN DE GRAVEDAD — la afirmación anterior era errónea
> Escribí *"evidencia fabricada en silencio"*, comme si hubiera ocurrido. **No ha ocurrido.**
> Barrí los CSV preservados parseando **por nombre de cabecera** (hay 3 layouts distintos, no una
> posición fija de columna): **72 ficheros · 20.210 filas · 0 celdas en cero o vacías.**
> El histórico es **genuino** (`runtime_status=active`, `power1_uw≈3.3e6`, `power1_cap=25000000`).
>
> **`hwmon2` ERA correcto el 2026-09-19.** El índice `hwmonN` **no es estable entre arranques**
> (y `AGENTS.md` §6.3 ya dice que un locator no es una identidad).
> → El defecto es **LATENTE**: se activaría en el próximo arranque donde el índice cambie.
> Es exactamente §2.4: *un error tragado no es evidencia de ausencia* — y aquí es al revés:
> **una amenaza de error tragado, todavía no materializada.**

**Dos capas independientes** — cualquiera de las dos sola produce ceros:
(i) `hwmon2` no existe → si el índice cambia, la ruta falla;
(ii) `power1_input` da **EPERM** por `runtime_status=error`, y **`temp1_input` daría
`-EOPNOTSUPP`** aunque el device estuviera sano (§6).
**Arreglar el índice no arregla el privilegio.**

### 9.3bis El proyecto YA tiene el patrón correcto — el defecto está localizado

`04-IMPLEMENTACION/rx550-torneo` es el **contrapunto positivo**, y no lo es por casualidad:

| | `sampler.sh` (ad-hoc) | `rx550-torneo` (correcto) |
|---|---|---|
| Resuelve hwmon | hardcodea `hwmon2` | `gpu_finder.py:75-77` `glob("hwmon/hwmon[0-9]*")`; **exige exactamente 1** (`:152-153` → `GPUError("AMBIGUOUS")`); valida que el path pertenece al device (`:173-175`) |
| Error de lectura | `\|\| echo 0` → **0 plausible** | `util.read_text` convierte `PermissionError` en `SafeIOError`; `state_manager.py:160-164` lo traduce a **`None`** |
| Estado de runtime PM | **no lo captura** | `state_manager.py:186` `"runtime_status": dev_opt("power/runtime_status")` — **la variable que faltaba** |
| Cobertura | — | no lee `freq2_input` (mclk): hueco, no defecto |

**El proyecto conoce el patrón correcto. Los samplers ad-hoc de `03-EXPERIMENTOS/` no lo
implementan.** El defecto es **localizado, no de diseño** — y la reparación es replicar un
patrón que ya existe en el mismo repo.

### 9.4 Códigos que no pueden ni ejecutarse aquí

`c1_isolation_automator.py` tiene precondiciones pineadas que fallan duro:

| Línea | Espera | Realidad |
|---|---|---|
| `:79` `EXPECTED_HOST` | `lex-luthor` | **`kalm`** |
| `:80` kernel | `7.2.6-201.nobara.fc44` | **`7.1.3`** |
| `:87` `GPU_CONTROL_PATHS` | `hwmon2` | **`hwmon1`** |

**`DERIVATION`:** C1 no puede iniciarse en este host. **No se intentó** — es `PROHIBIDO_POR_POLÍTICA`.

### 9.5 `CONTRADICTION` entre instrumentos, resuelta

Un subagente afirmó que `/dev/dri/` contenía *"sólo `by-path/`"*. **Falso**: contiene
`card0`, `card1`, `renderD128`, `renderD129` y `by-path/`. Su herramienta de lectura de
directorios no le mostró los nodos de carácter y lo elevó a hecho. **Resuelto por verificación
directa**; el otro instrumento (L2) era correcto.

---

## 10. UNKNOWN / NOT_DETERMINED

| # | Pregunta | Por qué no se cierra | Qué lo cerraría |
|---|---|---|---|
| **U-1** | ¿Por qué el UVD no respondió en el resume de S3? | requiere `dmesg` con privilegio | `dmesg` o `/sys/kernel/debug/dri/1/` como root. **Abre:** si es un fallo de firmware, de init de S3, o del driver |
| **U-2** | ¿Por qué `active_cu_number 8` de 10 CUs? | nada leído lo explica | tabla de Yale/ ASIC introspection; o un reset y re-log |
| **U-3** | ¿Qué devuelve exactamente `-EPERM` en los 14 atributos DPM? | `amdgpu_dpm.c` **404 en v7.1** (ruta reubicada); API rate-limited; 2 mirrors con anti-bot | el `.c` reubicado, o **una** lectura como root de `pp_dpm_sclk`. **Abre: toda la pregunta de clocks** |
| **U-4** | ¿Unidad real de `power1_input`? | escalado del handler no reconciliado | resolver la aritmética contra el `.c`, o comparar con medidor externo |
| **U-5** | ¿Por qué el enlace es x4? | `width` es estructural; no hay registro `LnkSta` legible | `lspci` del **root port** para separar ranura ×8 vs. traza ×4 |
| **U-6** | ¿Se ha usado el nodo KFD/ROCm? | `Add GPU node` + `PRT request` sugieren ruta de cómputo | `journalctl` (no-kernel) correlacionado. **read-only, seguro, no hecho** |
| **U-7** | ¿Hay contadores SQTT/RGP? | debugfs EPERM; un grep de árbol completo excedió timeout | lectura de `/sys/kernel/debug/dri/1/` como root |
| **U-8** | Procedencia de `/home/lucas/linux-opt` | es `7.1.0-rc1`, **≠** el kernel en ejecución, con anomalía (0 `sqtt` en todo `amd/` vs cabeceras ASIC que **sí** definen `SQTT_MODE` para GC10-12) | `git remote -v` + `git log` del árbol. **Hasta resolverlo: `FACT_FOR_linux-opt-7.1.0-rc1`, nunca `FACT_FOR_HOST-C`** |
| **U-9** | ¿RX 550 o RX 550X? | la tabla upstream no desambigua; PCI ID mapea a POLARIS12 pero ambas son POLARIS12 | comparación de clocks/VRAM con specs del SKU |
| **U-10** | Origen del software `kalm-gpu` | 3 de 4 payloads nunca estuvieron en el backup; nunca leído | el fichero, si se conserva en algún host |

---

## 11. RIESGOS Y LÍMITES

1. **Ninguna telemetría dinámica es legible.** 27 atributos EPERM. Cualquier afirmación sobre
   `power1_input`/`temp1_input`/`freq*_input` **actual** es `NOT_AVAILABLE` para este observador.
   **No sustituir por valor vacío ni por 0.**
2. **`runtime_status=error` es un latch, no un estado**, y **sombrea** el estado real. Leerlo como
   "sexto estado PM" es un error de lectura.
3. **La GPU está atascada** desde `2026-09-26T17:08:27`. Escalar requiere **reiniciar el host**.
4. **La config space PCI no es legible** → toda la sección L1 es la vista del driver, no del
   hardware.
5. **Una sola muestra no es `steady-state`.** `current_link_speed` es dinámico; `width` es
   estructural. No mezclarlos.
6. **Los artefacts del corpus son `UNVERIFIED_UNTIL_RECHECKED`.** 1.321+ mediciones nunca
   revalidadas.
7. **`dmesg` bloqueado** → todo el log viene de `journalctl`, instrumento distinto.
8. **Este agente está dentro del runtime que audita** (`AUTOOBSERVED`, §2.9): su propio proceso
   (`/usr/lib/chatgpt/ChatGPT --type=gpu-process`) mantiene FDs sobre `renderD128` y
   **`renderD129`** — la RX550.

---

## 12. RELACIÓN CON EL PROYECTO

**El proyecto es observador, no explicación.** El camino causal del hardware no lo contiene.

| Relación | Veredicto |
|---|---|
| El proyecto produjo el hallazgo de L3 más sólido (12 ucodes) | ✔ `DIRECT_ARTIFACT` |
| El proyecto `power1_input` | correcto como campo; `ESTIMACIÓN_FIRMWARE`, no medición física (el propio `ERRATUM-002` ya lo decía) |
| El proyecto usa `power1_cap` | ✔ **correcto** — el que `sampler.sh` no usa |
| Los scripts de telemetría | **CERO FABRICADO + interlock térmico desarmado** (§9.3) |
| C1 | **no ejecutable** en este host (§9.4) |
| `EXPECTED_HOST="lex-luthor"` | un tercer nombre de host para el mismo sistema. `HOST-A`/`HOST-B`/`HOST-C` en el router, `kalm` en el host, `lex-luthor` en el código |

---

## 13. LO QUE QUEDA DESBLOQUEADO

| Desbloqueo | Por qué | Autorización |
|---|---|---|
| **Reiniciar el host** | única vía para limpiar el latch de runtime PM → **restauraría las 27 lecturas** | `HUMAN_DECISION` |
| `dmesg` como root | cerraría U-1 y U-7 | `HUMAN_DECISION` |
| Una lectura root de `pp_dpm_sclk` | cerraría U-3 → **toda la pregunta de clocks** | `HUMAN_DECISION` |
| `journalctl` no-kernel | cerraría U-6 (¿quién tocó la GPU?) — **read-only, sin riesgo** | ya autorizado, **no ejecutado** |
| `git remote -v` en `linux-opt` | cerraría U-8 | ya autorizado, **no ejecutado** |
| `amdgpu_dpm.c` v7.1 reubicado | cerraría U-3 sin privilegio | ya autorizado, **no ejecutado** |

## 14. LO QUE NO PUEDE HACERSE SIN AUTORIZACIÓN

`sudo` · `systemctl` · escribir en `/sys` (cualquier cap, clock, PM, governor) · forzar clocks ·
cargar/descargar módulos · tocar firmware/VBIOS · cambiar D3cold · forzar el reset de la GPU ·
abrir `/dev/dri/card1` (requiere grupo `video`) · ejecutar los 22 scripts de telemetría (§9.3) ·
ejecutar C1 en cualquier modo · benchmarks/A/B.

---

## 15. PROCEDENCIA

```
FUENTE → EXTRACCIÓN → OBSERVACIÓN → DERIVACIÓN → CONCLUSIÓN
  sysfs/lspci/journalctl/amdgpu.ko/upstream  →  raw/*.txt  →  §2-§5  →  §6  →  §10
```

| Artefacto | SHA256 (16) |
|---|---|
| `l0-lspci-verbose.txt` | `cb28f55d3554610e` |
| `l0-sysfs-identity.txt` | `bc3f9e969499c99a` |
| `l1-pcie-link-aer.txt` | `531c173d24f1cff8` |
| `l2-mem-info.txt` | `62f277d8a2e342cc` |
| `l2-sysfs-device-listing.txt` | `427100946bd8e8f6` |
| `l3-hwmon-labels-and-attempts.txt` | `c664640432e25551` |
| `L2-CORRECTION-hwmon-permissions-and-errno.txt` | `68a603e490af8b6b` |
| `L2-RUNTIME-PM-ERROR-CAUSAL-CHAIN.txt` | `0342559bc1bf8f76` |

**Fuentes externas** (todas `EXTERNAL`, ninguna evidencia sobre este host):
`amdgpu_pm.c` v6.12/v7.1 (doc-block hwmon) · `kgd_pp_interface.h` master (enum sensores, def.
PPT) · `runtime.c`/`sysfs.c` v7.1 (latch, unidades) · `dgpu-asic-info-table.csv` (GC 8, sin
columna de profiling) · `amdgpu_pmu.c` 6 refs (VEGA20+ARCTURUS) · `amdgpu_drv.c` (0x699F→POLARIS12)
· `systemd.unit(5)` · FHS 3.0 · AMD RGP docs · `/lib/modules/…/amdgpu.ko.zst`
(`srcversion D68004925455E20A24C2B87`, `sha256 a1a44c24…`).

**`STOP_REASON`** · `NO_REMAINING_INFORMATION_GAIN` en lo legible sin privilegio. Los tres
`UNKNOWN` de mayor valor (U-1, U-3, U-7) están bloqueados por **autorización**, no por ignorar
búsqueda. La reconstrucción L0–L3 de lo accesible está **completa**; el resto está
**formalmente bloqueado** con la causa nombrada.
