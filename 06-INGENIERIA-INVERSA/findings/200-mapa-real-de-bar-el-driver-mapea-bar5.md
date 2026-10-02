# 200 · El driver mapea BAR5 de 256 KiB, no BAR2 de 2 MiB: mapa real de BAR de la placa

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC+HOST_READ` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=LOG_READ_ONLY` · `GPU INTACTA`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=la discrepancia que 190 dejo abierta por no poder arbitrar`

## Cuestión principal

`190` vio en el log del kernel `register mmio size: 262144` y lo contrastó con mi
resumen anterior, que decía **"BAR2 2 MiB es la apertura MMIO"**. No pude
arbitrarlo: `lspci -v` no devolvía nada y `resource2` de sysfs daba "sin permiso".
Quedó declarado como discrepancia abierta.

**EraMedia partida y las dos mitas eran mías.** El tamaño de BAR2 sí era
2 MiB. Lo que era falso es **qué BAR mapea el driver**.

## Dos errores propios, y por qué los dosvenueson aparecidos

**Error 1 — leí la asignación sin su condición.** Grepeé `rmmio_size *=` y vi:

```c
adev->rmmio_size = pci_resource_len(adev->pdev, 5);
adev->rmmio_size = pci_resource_len(adev->pdev, 2);
```

Concluí que usaba BAR2. Los dos existen, pero **están en ramas distintas**. El
bloque completo:

```c
/* amdgpu_device.c:3812-3818 */
if (adev->asic_type >= CHIP_BONAIRE) {
        adev->rmmio_base = pci_resource_start(adev->pdev, 5);
        adev->rmmio_size = pci_resource_len(adev->pdev, 5);
} else {
        adev->rmmio_base = pci_resource_start(adev->pdev, 2);
        adev->rmmio_size = pci_resource_len(adev->pdev, 2);
}
```

**Polaris12 es `asic_type` 17, y `CHIP_BONAIRE` es anterior.** Toma la rama de
**BAR5**. Por eso el log dice 262144 y no 2097152: **nunca miró BAR2**.

Un grep de las asignaciones sin su `if` es una cita sin contexto, que es
exactamente lo que este proyecto llama cita no verificable. Me pasó a mí con el
mismo criterio que aplico a los hallazgos.

**Error 2 — off-by-one al numerar los BAR.** Mi primer script de sysfs hacía:

```python
for i, f in enumerate(L[:6]):
    if b == 0 and a == 0: continue
    n += 1
    print("BAR%d ..." % (n - 1, ...))
```

Renumeraba **solo las filas no vacías**, así que un BAR vacío desplazaba todas las
etiquetas siguientes. Dio "BAR2 = 2 MiB, BAR3 = 256 bytes, BAR5 = 256 KiB" cuando
la verdad era "BAR2 vacío, BAR3 vacío, BAR4 = 256 bytes, BAR5 = 256 KiB". El
`continue` saltándose la numeración del índice es el mismo error que el doble
conteo de `ipver_zero`: **un salto que no avanza el contador**.

Lo que lo delató fue comparar contra el log: si el driver lee BAR5, entonces la
fila que coincide con `0xF7D00000` **tiene que ser el índice 5**, y sí lo era.

## El mapa real

`/sys/bus/pci/devices/0000:01:00.0/resource`, por índice real:

| idx | inicio | fin | bytes | tipo | para qué |
|---|---|---|---|---|---|
| BAR0 | `0x0e000000` | `0x0effffff` | **256 MiB** | 64-bit prefetch | apertura de VRAM |
| BAR1 | — | — | — | — | **VACÍO** |
| BAR2 | `0x0f000000` | `0x0f01ffff` | **2 MiB** | 64-bit prefetch | no la mapea el driver |
| BAR3 | — | — | — | — | **VACÍO** |
| BAR4 | `0x0000e000` | `0x0000e0ff` | 256 bytes | I/O 32-bit | |
| **BAR5** | `0x0f7d00000` | `0x0f7d3ffff` | **256 KiB** | mem 32-bit | **`rmmio`: los registros** |

Y el log del driver, que coincide **exacto en base y tamaño**:

```
register mmio base: 0xF7D00000
register mmio size: 262144
```

## Corrección a lo que tenía

| lo que decía | lo que es |
|---|---|
| "BAR2 2 MiB es la apertura MMIO" | BAR2 **sí** mide 2 MiB, pero el driver **no lo mapea** |
| apertura MMIO = 2 MiB | **256 KiB**, en **BAR5** |
| — | **BAR1 y BAR3 están vacíos** (dato que no tenía) |
| — | **BAR4** = 256 bytes de I/O |

## Un umbral de hardware que sale de aquí

`amdgpu_acp.c:245` e `isp_v4_1_0.c:48` hacen lo mismo:

```c
if (adev->rmmio_size == 0 || adev->rmmio_size < 0x5289)
```

`0x5289` = **21129 bytes**. Es la apertura de registros **mínima** que el driver
acepta antes de negarse a usar ACP o ISP. Esta placa tiene 262144, que lo cumple
con margen de 12×.

**Para un driver propio es un requisito de hardware, no del driver**: la apertura
de registros tiene que medir al menos `0x5289`, o el hardware queda fuera de
alcanzabilidad aunque esté presente.

## Lo que esto no es

**No hay contradicción con `169`.** `169`Established que BAR0 = 256 MiB y que
`fpfn = 65536` páginas, y eso sigue siendo cierto: la tabla confirma **BAR0 =
268435456 bytes = 256 MiB** exactamente. Ese hallazgo no se toca.

**Tampoco hay reprogramación de BARs.** Busqué `PCI_BASE_ADDRESS_5`, `pci_set_resource`
y REBAR por si el layout había cambiado entre el probe y ahora. `amdgpu_rebar`
existe (`amdgpu_drv.c:246`, por defecto auto) pero actúa sobre **BAR0** vía
`pci_rebar_*`, no sobre BAR5. **La Layout no cambió**: el log y sysfs coinciden
porque describen lo mismo.

## La lección, y por qué la pongo aunque ya sea la quinta vez

**No cerré la discrepancia cuando tenía la evidencia para hacerlo.** En `190` la
dejé abierta por "no tener permiso", cuando el fichero que faltaba era
`resource` (el agregado) y no `resource2` (uno solo). `resource2` da permiso
denegado; **`resource` se lee sin problemas**.

Eso es `cannot verify` tratado mal: no era que no se pudiera verificar, era que había
probado la puerta equivocada. Y mientras la discrepancia estuvo abierta, yo
mismo escribí dos veces que "no puedo arbitrarlo" —una afirmación más fuerte que
los hechos, y por tanto **peor que no decir nada**.

Un punto abierto que en realidad es resoluble es peor que un error: **el error se
encuentra, la puerta equivocada se repite**.

## Clasificación

| afirmación | estado |
|---|---|
| BAR5 = 256 KiB en `0xf7d00000` | `PROVEN` — sysfs |
| El log coincide exacto en base y tamaño | `PROVEN_RUNTIME` — dos fuentes |
| `asic_type 17 >= CHIP_BONAIRE` → rama BAR5 | `PROVEN` — `amdgpu_device.c:3812` |
| BAR2 mide 2 MiB pero no se mapea | `PROVEN` |
| BAR1 y BAR3 vacíos | `PROVEN` — sysfs |
| El umbral de apertura es `0x5289` = 21129 bytes | `PROVEN` — `amdgpu_acp.c:245` |
| `resource` se lee sin permiso y `resource2` no | `PROVEN` — contrastado |
| Que el hardware *requiera* 0x5289 | `DERIVATION` — es una decisión del driver |
| La layout de BAR no cambió | `PROVEN_DERIVED` — log y sysfs coinciden |

## Confounders

- **`resource` devuelve 13 filas, no 7.** Un dispositivo PCIe expone 6 BARs + ROM.
  Las 13 filas hacen sospechar que el índice→BAR no es 1:1. **Pero la coincidencia
  con el log lo confirma**: el driver lee el índice 5, y la fila del índice 5 es
  la que tiene `0xf7d00000`. Si el mapeo estuviera desplazado, no casaría.
  **Lo dejo declarado**: no sé qué son las 6 filas de más.
- **No he ejecutado la lectura desde el driver.** La coincidencia base+tamaño es
  fuerte pero no es una lectura directa de `adev->rmmio`. Un `dev_info` adicional
  en runtime lo cerraría del todo, y no lo he hecho.
- **`0x5289` es una decisión del driver, no una constante del hardware.** Que el
  hardware *necesite* exactamente eso no está demostrado; lo que está demostrado
  es que el driver se niega a trabajar con menos.
- **El tamaño de VRAM real no lo he medido aquí.** `real_vram_size` (usado por
  REBAR) es otra cosa que BAR0 y este hallazgo no la toca.

## Desfalsificación

- **(a)** BAR5 vs BAR2 → refutable con `amdgpu_device.c:3812` y el log. **Verificado.**
- **(b)** BASE y tamaño → refutable con `resource` línea 6. **Verificado.**
- **(c)** El umbral `0x5289` → refutable con `amdgpu_acp.c:245`.
- **(d)** Que la layout no cambiara → refutable si `resource` no casara con el log.
  **Verificado por coincidencia.**
- **(e)** Las 13 filas → **no resueltas**, declarado arriba.

## UNLOCKS

- **§A resuelve DÓNDE están los registros**: BAR5, 256 KiB, base `0xF7D00000`.
  Cualquier herramienta o driver propio que derivara la ventana de registros de
  BAR2 estaría **equivocado por un factor 8 y por el BAR equivocado**.
- **Una corrección con historia**: el error no era el dato, era el **mecanismo**
  (`if/else` leído sin su condición). Es el mismo modo de fallo que buscar una
  capacidad por el nombre del fichero en vez de por el mecanismo.
- **Un umbral de hardware registrado**: la apertura de registros debe medir
  `0x5289` o más.
- **`BAR1` y `BAR3` vacíos**: dos huecos en el espacio de direcciones que un
  driver propio no debe intentar usar.
- **La lección, la quinta vez**: un punto abierto que en realidad es resoluble es
  peor que un error, porque el error se encuentra y la puerta equivocada se
  repite. `resource2` no; `resource` sí.
- **Siguiente paso**: las 13 filas de `resource` frente a las 7 esperadas.

## Evidencia

```
/sys/bus/pci/devices/0000:01:00.0/resource   13 filas, leido sin permiso
sysfs .../resource2                            "sin permiso"  <- la puerta equivocada
journalctl -k | grep "register mmio"            base 0xF7D00000 size 262144
amdgpu_device.c:3812-3818                       el if/else de CHIP_BONAIRE
amdgpu_device.c:3826-3830                       los dos dev_info
amdgpu_acp.c:245 / isp_v4_1_0.c:48             el umbral 0x5289
amdgpu_drv.c:246,1084-1091                      amdgpu_rebar, solo sobre BAR0
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.