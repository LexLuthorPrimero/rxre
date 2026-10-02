# 190 · Los 4 `switch` de `GC_HWIP`, TMZ confirmado en runtime, y dos registros de versión IP paralelos

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC+RUNTIME_READ` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=LOG_READ_ONLY` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=los 8 switch que 185 dejo sin evaluar`
`COLISION_DE_NUMERO=SI` -- otra sesion reservo tambien el 190 para
`190-tres-correcciones-de-la-poda.md`. Ha renumerado su fichero a 198 pero su
H1 INTERIOR sigue diciendo `# 190`. Este fichero (190-dos-registros-...) es el mio.
CAUSA RAIZ: hay DOS numeradores sin coordinar. `08-ARQUITECTURA/tools/findnum.py`
usa flock + ficheros .res (4 usos de flock); `tools/nextnum.py` de la otra sesion
no tiene NINGUNA referencia a flock, .res ni _reservas. Dos contadores
independientes garantizan colisiones. No he tocado su fichero: es su ambito.

## Cuestión principal

`185` dejó **8 `switch` sin evaluar**. La pregunta era si alguno tiene un
`default:` que haga trabajo real, porque una rama que en esta placa **se ejecuta
siempre** es una rama que puede esconder comportamiento.

## Criterio de terminación

Evaluar los 4 `switch`, determinar qué rama toma cada uno con el valor 0, y
comprobar el resultado contra el log del kernel. **Cumplido**, y además se
corrigió el recuento de `185` y una afirmación previa sobre el número de bloques IP.

## Primero: los 8 eran 4

Mi corrección del doble conteo en `ipver_zero` no cubrió los `switch`: si el
`switch` empieza en la línea N+1, la ventana que empieza en N también lo contiene.
Atribuí cada coincidencia a la línea donde **empieza**, y los 8 pasaron a 4.

Eso también bajó las comparaciones de 86 a 46 y las siempre-verdaderas de 13 a 8.
**Verifiqué a mano** `amdgpu_ids.c:582-590`: la condición entera está en la línea
586, así que **8 es el número correcto**, uno por condición física.

```
sitios encontrados          : 50
  comparaciones             : 46
    SIEMPRE verdaderas      :  8
    NUNCA verdaderas        : 38
  switch                    :  4
```

## Los 4 `switch`, uno por uno

| sitio | función | qué hace el `default:` con 0 | alcanzable en GFX8 |
|---|---|---|---|
| `amdgpu_gmc.c:928` | `amdgpu_gmc_tmz_set` | **`tmz_enabled = false` + mensaje** | **sí, y CONFIRMADO** |
| `amdgpu_gmc.c:1765` | `amdgpu_gmc_get_vram_info` | `get_vram_info` (no `get_umc_info`) | sí, y correcto |
| `amdgpu_ucode.c:1383` | `amdgpu_ucode_legacy_naming` | `return NULL` | sí, y correcto |
| `amdgpu_xgmi.c:1757` | `amdgpu_xgmi_early_init` | `break` (nada) | **no**, inalcanzable |

**Solo uno hace trabajo real: TMZ.** Y ese está confirmado en runtime.

## Confirmación empírica: TMZ

`amdgpu_device.c:3877-3878` la llama **sin guarda**:

```c
/* Enable TMZ based on IP_VERSION */
amdgpu_gmc_tmz_set(adev);
```

Con 0, ningún `case` casa, y el `default:` pone `adev->gmc.tmz_enabled = false`
y escribe `"Trusted Memory Zone (TMZ) feature not supported"`.

El log del kernel lo dice, literalmente:

```
amdgpu 0000:01:00.0: Trusted Memory Zone (TMZ) feature not supported
```

**Es la primera confirmación directa en runtime de una degeneración
`GC_HWIP == 0` en este proyecto.** Predicción estática, observación de log,
cero escrituras.

**Consecuencia para el driver propio: TMZ está desactivado.** La Trusted Memory
Zone es lo que impide que la GPU escriba en VRAM del host; sin ella, no hay
aislamiento de memoria. No es un detalle de rendimiento.

## `get_vram_info`: el `default:` ES la rama GCN3

```c
switch (amdgpu_ip_version(adev, GC_HWIP, 0)) {
case IP_VERSION(12, 0, 0): ... return amdgpu_atomfirmware_get_umc_info(...);
case IP_VERSION(9, 5, 0): ... return amdgpu_atomfirmware_get_umc_info(...);
default:
        return amdgpu_atomfirmware_get_vram_info(...);
}
```

**Aquí el `default:` es deliberadamente la rama de los ASIC antiguos**, igual
que el `flush_tlb` de `185`. No es un error: es el patrón "si no lo reconozco,
es que soy viejo". GFX8 no está en la lista, cae en `default`, y
`get_vram_info` es la función correcta para GCN3. **Verde por diseño.**

Esto matiza `185`: la degeneración no es uniformemente mala. Donde el `default:`
es "lo antiguo", funciona.

## `gc_0_0_0_mes.bin`: un nombre roto que nunca se pide

`amdgpu_ucode_ip_version_decode` (`amdgpu_ucode.c:1484-1486`):

```c
maj = IP_VERSION_MAJ(version);   /* 0 */
min = IP_VERSION_MIN(version);   /* 0 */
rev = IP_VERSION_REV(version);   /* 0 */
snprintf(ucode_prefix, len, "%s_%d_%d_%d", ip_name, maj, min, rev);
```

Con `version = 0` el prefijo es **`gc_0_0_0`**. Y en `/lib/firmware/amdgpu/`
**no existe `gc_0_0_0*`**: hay 111 ficheros `gc_*`, todos con versión real.

Lo alarming: `amdgpu_mes_init_microcode` llama a `ip_version_decode` **sin guarda**
en `amdgpu_mes.c:677`, y la condición de `amdgpu_mes.c:683` (`>= 11 && < 12`) es
siempre falsa, así que caería al `else` y pediría `amdgpu/gc_0_0_0_mes.bin`.

**Pero es código muerto.** `amdgpu_mes_init_microcode` y `amdgpu_mes_init` solo se
llaman desde `mes_v11_0.c`, `mes_v12_0.c` y `mes_v12_1.c`. **No existe `mes_v9_*`**:
MES empieza en Vega20 (GC10), y Polaris12 es GFX8. El log lo confirma: **0 líneas**
`MES: vmid_mask` y **0** `gc_0_0_0`.

## La causa real de `182`: dos registros de versión IP, y solo uno se rellena

Esto es lo importante, y explica `182`, `185` y la confirmación de TMZ de una vez.

El driver tiene **dos arrays paralelos**, y no es lo mismo:

| registro | quién lo rellena | en Polaris12 |
|---|---|---|
| `adev->ip_blocks[]` / `num_ip_blocks` | **tabla ASIC** (`vi_set_ip_blocks`) | **poblado y correcto** |
| `adev->ip_versions[][]` | **`amdgpu_discovery`**, desde `ip_discovery.bin` | **todo ceros** |

`amdgpu_ip.c:241` imprime desde `ip_blocks[]` (`ip_block_version->major`), que es
por eso que el log dice `gfx_v8_0_0`. `amdgpu_ip_version()` lee `ip_versions[][]`,
que está a cero.

**Y la causa está en el dispatch**, `amdgpu_device.c:1980-1998`:

```c
case CHIP_POLARIS12:
...
        r = vi_set_ip_blocks(adev);        /* tabla ASIC */
        break;
default:
        r = amdgpu_discovery_set_ip_blocks(adev);   /* ip_discovery.bin */
```

**Polaris12 nunca entra por `default`.** `amdgpu_discovery` es el **único**
escritor de `ip_versions[][]` (`amdgpu_discovery.c:1640, 1659, 2798-2814`), y
`144` ya estableció que **no hay `ip_discovery.bin` para GCN3**. Por eso el array
legacy queda íntegro a cero.

**Así que `182` no solo es cierto: tiene causa identificada.** Las ~94
comparaciones leen un registro que en esta placa **nunca se escribió**, mientras
el registro que sí se escribió no lo consulta nadie en esas comparaciones.

**Y la corrección a mi propia afirmación**: dije "6 bloques IP". Son **9**.

## Corrección: 9 bloques IP, no 6

`vi.c:2103-2119`, `case CHIP_POLARIS12` (compartido con POLARIS10, POLARIS11,
VEGAM) añade, **en este orden**:

```
vi_common, gmc_v8_1, tonga_ih, gfx_v8_0, sdma_v3_1, pp_smu,
[dm si hay soporte DC], uvd_v6_3, vce_v3_4
```

Y el log del kernel, en ese orden exacto:

```
0 <common_v1_0_0> (vi_common)
1 <gmc_v8_1_0>    (gmc_v8_0)
2 <ih_v3_0_0>     (tonga_ih)
3 <gfx_v8_0_0>    (gfx_v8_0)
4 <sdma_v3_1_0>   (sdma_v3_0)
5 <smu_v1_0_0>    (powerplay)
6 <dce_v1_0_0>    (dm)
7 <uvd_v6_3_0>    (uvd_v6_0)
8 <vce_v3_4_0>    (vce_v3_0)
```

**9 de 9.** Mi "6" contaba solo los no condicionales; me faltaban **`dm`,
`uvd_v6_3` y `vce_v3_4`**.

**El RX550 decodifica vídeo (UVD 6.3) y codifica vídeo (VCE 3.4)**, y tiene
**DCE 1.0** para display. Eso no estaba registrado, y para un driver propio es
media acceleration, no un detalle.

### Un detalle estructural: falta el `else`

En FIJI y TONGA el display es `#if DC ... else dce_v10_N_ip_block; #endif`.
**En POLARIS12 el `else` no existe.** Con `CONFIG_DRM_AMD_DC` desactivado,
Polaris12 se queda **sin bloque de display**. Es una asymetría real entre ASICs de
la misma generación.

### Y otra: UVD/VCE sin guarda de VF

POLARIS10/11/12/VEGAM añaden `uvd_v6_3` y `vce_v3_4` **sin**
`if (!amdgpu_sriov_vf(adev))`, que sí está en FIJI y TONGA.

## Clasificación

| afirmación | estado |
|---|---|
| Los 8 `switch` de `185` eran 4 | `PROVEN` — atribución por línea de inicio |
| 8 siempre verdaderas (no 13) | `PROVEN` — verificado a mano en `amdgpu_ids.c` |
| TMZ desactivado por el `default:` | `PROVEN_RUNTIME` — log del kernel |
| `get_vram_info` recibe la rama GCN3 | `PROVEN` — lectura |
| `amdgpu_ucode_legacy_naming` devuelve `NULL` | `PROVEN` — no casa ningún `case` |
| `xgmi_early_init` inalcanzable | `PROVEN` — `xgmi.supported` falso |
| `gc_0_0_0_mes.bin` es código muerto | `PROVEN` — no hay `mes_v9_*` |
| No existe `gc_0_0_0*` en el firmware | `PROVEN` — 111 `gc_*`, ninguno con 0 |
| `ip_versions[][]` solo lo escribe `amdgpu_discovery` | `PROVEN` — grep de escritores |
| Polaris12 no entra por `default:` | `PROVEN` — `amdgpu_device.c:1980-1998` |
| **9 bloques IP, no 6** | `PROVEN_RUNTIME` — 9/9 estático↔log |
| El RX550 tiene UVD 6.3 y VCE 3.4 | `PROVEN_RUNTIME` — log |
| Falta el `else` de display en POLARIS12 | `PROVEN` — lectura de `vi.c` |
| TMZ ausente es un riesgo de seguridad | `DERIVATION` — de la ausencia de TMZ |
| Que el resto de los 8 de `185` fuera inofensivo | `NOT_DETERMINED` |

## Confounders

- **`dmesg` estaba vacío (0 líneas) y mi primer intento de P1/P2/P3 probó contra
  él.** La ausencia de `gc_0_0_0` en un log vacío **no prueba nada**. La fuente
  real era `journalctl -k` (80 líneas de amdgpu). Lo digo porque es la clase de
  error que hace creer que algo está verificado cuando no lo está: **un resultado
  negativo desde una fuente vacía no es evidencia de ausencia.**
- **La confirmación de TMZ depende de que el log sea de esta placa.** Todas las
  líneas son `amdgpu 0000:01:00.0`, que es el RX550. Es consistente.
- **La conclusión "TMZ = riesgo de seguridad" es `DERIVATION`, no observación.**
  No he medido si la GPU puede tocar VRAM del host; solo he confirmado que el
  driver no activa la zona.
- **Discrepancia sin resolver**: el log dice `register mmio size: 262144`
  (256 KiB) y mi resumen anterior decía "BAR2 2 MiB". **No he podido arbitrarlo**:
  `lspci -v` no devolvió nada y `resource2` de sysfs dio "sin permiso". Lo dejo
  abierto en vez de afirmar una corrección que no puedo comprobar.
- **`amdgpu_dev_coredump.c:273` también lee `ip_versions[][]`**, así que un
  crash dump del RX550 registraría versión 0 para todos los bloques. **No lo he
  verificado**: no hay coredump en disco que mirar.
- **`num_ip_blocks` es el índice que se imprime**, no un campo del ASIC. El
  orden del log lo produce el orden de las llamadas a `amdgpu_device_ip_block_add`,
  así que el 9/9 es una coincidencia de orden, no de conteo.

## Desfalsificación

- **(a)** TMZ → refutable con `journalctl -k | grep TMZ`. **Verificado.**
- **(b)** 9 bloques → refutable comparando `vi.c:2103-2119` con el log. **Verificado.**
- **(c)** 4 `switch` → refutable con `ipver_zero`. **Verificado.**
- **(d)** `gc_0_0_0` muerto → refutable por la existencia de `mes_v9_*`. No existe.
- **(e)** `ip_versions` solo por discovery → refutable grepando escritores.
  **Verificado.**
- **(f)** La discrepancia del MMIO → **no falsable aquí**, falta permiso.

## UNLOCKS

- **La causa de `182` está identificada en el dispatch**, no inferida:
  `CHIP_POLARIS12` → `vi_set_ip_blocks`, y el único escritor de `ip_versions[][]`
  es `amdgpu_discovery`, que no se ejecuta en esta rama.
- **Un patrón de autoverificación que ahora es rutina**: predecir la línea de
  log desde el `default:` de un switch, y encontrarla. Es la primera vez que una
  degeneración de `GC_HWIP == 0` se confirma en runtime.
- **El proyecto tiene dos registros de versión IP** y hay que saber cuál se
  consulta antes de razonar sobre una comparación.
- **§C/§G**: TMZ desactivado significa que **no hay aislamiento de VRAM**; es un
  requisito de seguridad, no de rendimiento, para el driver propio.
- **Corrección de inventario**: el RX550 tiene UVD 6.3, VCE 3.4 y DCE 1.0. Hay
  bloques de media y display sin explorar.
- **Lección, la tercera vez**: probé P1/P2/P3 contra `dmesg`, que devolvió 0
  líneas, y estuve a punto de concluir "TMZ: sin línea". **Una fuente vacía no
  refuta nada.** El control era buscar `journalctl`.

## Evidencia

```
08-ARQUITECTURA/tools/ipver_zero.py  --todos --fichero F --resumen --self-test
amdgpu_gmc.c:927-986      amdgpu_gmc_tmz_set, el default que desactiva TMZ
amdgpu_device.c:3877-3878 llamada sin guarda
amdgpu_gmc.c:1765-1785    get_vram_info, default = rama GCN3
amdgpu_ucode.c:1383-1429  legacy_naming, sin case que case con 0 -> NULL
amdgpu_ucode.c:1484-1486  snprintf del prefijo -> "gc_0_0_0"
amdgpu_mes.c:677-695      llamada sin guarda + guarda 683 siempre falsa
amdgpu_ip.c:228-247       amdgpu_device_ip_block_add, lee ip_blocks[]
amdgpu_device.c:1980-1998 el dispatch: vi_set_ip_blocks vs discovery
amdgpu_discovery.c:1640,1659,2798-2814  unicos escritores de ip_versions[][]
vi.c:2103-2119            los 9 bloques de CHIP_POLARIS12
journalctl -k             "Trusted Memory Zone (TMZ) feature not supported"
                          9x "detected ip block number" en orden
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.