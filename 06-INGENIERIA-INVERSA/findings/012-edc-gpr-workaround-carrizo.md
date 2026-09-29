# 012 — El workaround EDC/GPR de Carrizo: qué es y si aplica a Polaris 12

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`
**Tarea**: por qué existe `gfx_v8_0_do_edc_gpr_workarounds`, y si el defecto de silicio
subyacente alcanza a la RX 550 (Polaris 12).
**Clase de la tarea**: `READ_ONLY/EVIDENCE` — nada ejecutado sobre la GPU.

## Procedencia de las fuentes

| Fuente | Identificador | Verificado por mí |
|---|---|---|
| Fuente upstream | `rx550-upstream-7.2.8/linux-7.2.8.tar.xz`, sha256 `12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941` | **sí** — `sha256sum` coincide con `upstream.sha256` y `local.sha256` del repo |
| Módulo | `amdgpu.ko` de `7.1.3-200.nobara.fc44.x86_64`, sha256 `a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024`, srcversion `D68004925455E20A24C2B87` | **sí** — `modinfo`, `sha256sum`. Coincide con `register-maps/gfx-v8-compute.md` §cabecera |
| Árbol parcial del repo | `RESEARCH/working/linux-7.1.3/` (632 ficheros de `amdgpu/`) | usado sólo como contraste, ver §6 |
| Enum `amd_asic_type` | BTF del módulo cargado: `pahole -C amd_asic_type /sys/kernel/btf/amdgpu` | **sí** |

Las dos fuentes de C que uso son **7.2.8 upstream**, no el árbol parcial de 7.1.3 del repo. El
motivo está en §6 y es una corrección de método.

---

## 1. Qué hace la función

`gfx_v8_0.c:1474` (7.2.8), 160 líneas. Estructura completa:

| Fase | Líneas | Qué hace |
|---|---|---|
| Gate 1 | 1484-1486 | `if (adev->asic_type != CHIP_CARRIZO) return 0;` |
| Gate 2 | 1488-1490 | `if (!ring->sched.ready) return 0;` |
| Desactiva EDC | 1492-1493 | `tmp = RREG32(mmGB_EDC_MODE); WREG32(mmGB_EDC_MODE, 0);` |
| Reserva IB | 1495-1514 | calcula tamaño, `amdgpu_ib_get()` |
| Carga shaders | 1516-1521 | copia `vgpr_init_compute_shader` y `sgpr_init_compute_shader` al IB |
| **VGPR** | 1528-1550 | escribe `vgpr_init_regs` con `SET_SH_REG`, `COMPUTE_PGM_LO/HI`, **`DISPATCH_DIRECT` (x=8,y=1,z=1)**, `EVENT_WRITE` |
| **SGPR1** | 1554-1576 | idem con `sgpr1_init_regs` |
| **SGPR2** | 1580-1602 | idem con `sgpr2_init_regs` |
| Espera | 1605-1616 | `amdgpu_ib_schedule` + `dma_fence_wait` |
| **Activa EDC** | 1618-1620 | `GB_EDC_MODE`: `DED_MODE=2`, `PROP_FED=1` |
| **Activa EDC** | 1622-1624 | `CC_GC_EDC_CONFIG`: `DIS_EDC=0 \| 1` |
| Limpia contadores | 1627-1629 | `RREG32` de los 25 `sec_ded_counter_registers[]` |

Los tres shaders son `vgpr_init_compute_shader` y `sgpr_init_compute_shader` (líneas 1395-1443
y anteriores): no calculan nada. **Escriben un patrón conocido en el fichero de registros.**

## 2. Por qué existe: es una routine de ECC, no una ruta de dispatch

Cuatro evidencias, todas del mismo fichero y todas verificables:

1. **El nombre del bloque que la contiene.** Se llama desde
   `gfx_v8_0_late_init` (`gfx_v8_0.c:5296`), y la línea siguiente es
   `amdgpu_irq_get(adev, &adev->gfx.cp_ecc_error_irq, 0)` con el mensaje
   `"amdgpu_irq_get() failed to get IRQ for EDC"`. El bloque es de ECC.
2. **Lo que hace al final.** Reactiva `DED_MODE` (*deferred error detection*) y
   `PROP_FED`, y después **lee los 25 contadores `*_EDC_CNT` para descartarlos**. Eso sólo
   tiene sentido si esos contadores acaban de ser invalidados por lo que se acaba de
   ejecutar. Leer un contador para "limpiarlo" sólo tiene sentido tras una perturbación
   conocida.
3. **El orden es tren →_error_.** Primero se perturba el hardware (los shaders), después
   se enciende la detección, después se tiran los contadores. Es la secuencia clásica de
   *training* de un detector de errores.
4. **El mismo nombre existe en gfx9, donde sí está generalizado.**
   `gfx_v9_0_do_edc_gpr_workarounds` (`gfx_v9_0.c:4683`) tiene **la misma estructura**
   —mismos shaders, mismos `DISPATCH_DIRECT`, mismo `sec_ded_counter_registers`— pero
   **sin gate de chip**: sólo `amdgpu_ras_is_supported(adev, AMDGPU_RAS_BLOCK__GFX)`
   (`gfx_v9_0.c:4702`). En `gfx_v9_0_ecc_late_init` (`gfx_v9_0.c:4881-4903`) se elige entre
   esa y `gfx_v9_4_2_do_edc_gpr_workarounds`.

**Conclusión**: es una routine de **inicialización del GPR file para que el scrub/ECC del GFX
tenga una base conocida**. El `DISPATCH_DIRECT` es el *medio* de escribir el registro
completo, no el objetivo. En gfx9 corre en todos los chips con RAS; en gfx8 el autor lo
limitó a Carrizo.

### Lo que NO puedo establecer

**Por qué Carrizo sí y los demás gfx8 no: `NOT_DETERMINED`.** El árbol no lleva el motivo.
Lo intenté por tres vías y las tres fallaron:

| Vía | Resultado |
|---|---|
| Comentario en el código | sólo `/* only supported on CZ */` (`gfx_v8_0.c:1484`). No explica por qué |
| `lore.kernel.org` | bloqueado por Anubis (proof-of-work anti-bot) el 2026-09-29 |
| Web search (3 consultas distintas) | 0 resultados en las tres |

No lo relleno. Dos hipótesis, ambas compatibles con lo observado y **ninguna verificada**:

- **H1 — silicio.** Carrizo (y sólo Carrizo) necesita que el GPR file esté inicializado
  antes de que el EDC sea fiable; Polaris 12 no tiene el defecto.
- **H2 — capacidad.** El EDC de GFX8 no se expone como RAS fuera de Carrizo, así que
  inicializarlo no serviría de nada aunque el silicio lo permitiera.

Lo que **sí** se puede afirmar es que **en gfx8 no hay infraestructura RAS**: `gfx_v8_0.c`
no contiene ni una mención de `ras` (grep sobre las 184 referencias a `gfx_v8` del módulo
y sobre el fichero), y no existe `gfx_v8_1.c` en el árbol — gfx8.1 corre el mismo
`gfx_v8_0_ip_block`. H2 es más económica que H1, pero es interpretación, no medición.

### Condición que refutaría esto

Si apareciera un paquete PM4 de EDC/GPR obligatorio en el flujo normal de submit de gfx8
—distinto del de Carrizo— la clasificación "no aplica a Polaris 12" sería falsa. Mi
evidencia de que no existe es binaria y la doy entera en §4.

---

## 3. Veredicto para Polaris 12: NO APLICA

`SUPPORTED`. La cadena completa:

```
PCI 1002:699f  (amdgpu_drv.c:2054, 7.2.8)
  └─> CHIP_POLARIS12  (valor 17, BTF del módulo cargado)
        └─> vi.c:2107-2112  -> gfx_v8_0_ip_block   [mismo fichero que Carrizo]
             └─> gfx_v8_0_late_init
                  └─> gfx_v8_0_do_edc_gpr_workarounds
                       └─> 1485: asic_type(17) != CHIP_CARRIZO(13)  ==> return 0
```

**El driver de referencia no ejecuta nada de este bloque en la RX 550.** La rama está
tomada antes de tocar `GB_EDC_MODE`, antes de reservar el IB y antes de los tres
`DISPATCH_DIRECT`.

## 4. La mismagate, vista en el binario

No me fié de leer el C. Conté los inmediatos PM4 en `.text` y los atribuí a funciones
(herramienta en §7; **no está en el repo**, ver nota al final de §7).

`0xC0031500` = `PACKET3(DISPATCH_DIRECT, 3)`. **10 apariciones en todo el `.text`
(9 617 163 B)**, todas atribuidas:

| Símbolo | Nº |
|---|---|
| `gfx_v8_0_late_init` | **3** (offsets `+0x29a`, `+0x405`, `+0x57c`) |
| `gfx_v9_0_late_init` | 3 |
| `gfx_v9_4_2_do_sgprs_init.isra.0` | 3 |
| `gfx_v9_4_2_do_edc_gpr_workarounds` | 1 |

**Las 3 de gfx8 están todas dentro de `gfx_v8_0_late_init`**, que es donde el compilador
inlinó `gfx_v8_0_do_edc_gpr_workarounds`. **No hay ninguna otra función de gfx8 que
emita `DISPATCH_DIRECT`.**

Corroboración: `0xC0004600` = `PACKET3(EVENT_WRITE, 0)`. 15 apariciones, 3 de ellas en
`gfx_v8_0_late_init` (`+0x30d`, `+0x478`, `+0x5ef`), y en los tres casos el `0x407`
—`EVENT_TYPE(7)|EVENT_INDEX(4)`— aparece **23 bytes después** (`+0x324`, `+0x48f`, `+0x606`),
como dword separado. Esto confirma de forma independiente lo que sostiene el commit
`cc03e33`: el token va en su propio dword, no OR'd en el header. Lo medí con otro método
(recuento de dwords alineados) y salen los mismos números que ese commit: 15 y 10.

### El gate, desensamblado

`gfx_v8_0_late_init` está en `0x14a0a0`, tamaño `0x785`. En `+0xa4`:

```asm
14a144: 83 bb 68 06 00 00 0d   cmpl  $0xd,0x668(%rbx)    ; adev->asic_type == 13 ?
14a14b: 0f 85 37 06 00 00      jne   14a788              ; != 13 -> salta el bloque
14a151: 80 bb 04 a6 01 00 00   cmpb  $0x0,0x1a604(%rbx)   ; ring->sched.ready == 0 ?
14a158: 0f 84 2a 06 00 00      je    14a788              ; -> salta el bloque
14a160: be 7e 30 00 00         mov   $0x307e,%esi        ; mmGB_EDC_MODE
```

`$0xd` = 13 = `CHIP_CARRIZO`. Valor tomado del BTF del módulo **cargado** en esta host
(`pahole -C amd_asic_type /sys/kernel/btf/amdgpu` → `CHIP_CARRIZO = 13`,
`CHIP_POLARIS12 = 17`, `CHIP_STONEY = 14`), no del C, porque el enum **no está en el árbol**
(§6). Y `0x307e` es `mmGB_EDC_MODE`, confirmado en
`include/asic_reg/gca/gfx_8_0_d.h:825`.

Es decir: la condición se evalúa **antes** de la primera lectura de `GB_EDC_MODE`, tal
como en el C. Las dos puertas del fuente están en el binario.

---

## 5. Qué significa para el driver propio

| Pregunta de IA-2 | Respuesta |
|---|---|
| ¿Necesito `DISPATCH_DIRECT`? | **NO**, salvo que implemente RAS/ECC, que no es el objetivo |
| ¿Necesito `GB_EDC_MODE` / `CC_GC_EDC_CONFIG`? | **NO**. El driver de referencia no los toca en Polaris 12 |
| ¿Necesito los 25 `sec_ded_counter_registers`? | **NO** |
| ¿Necesito los shaders `vgpr_init_compute_shader` / `sgpr_init_compute_shader`? | **NO** |

**Consecuencia de método, y es la que más importa**: el codificador PM4 que IA-2 ya tiene
(`07-DRIVER/kernel/rx550_pm4.c`, 49/49 checks) **modela la secuencia de tres `DISPATCH_DIRECT`
del workaround de Carrizo**. Ese es el único consumidor de `DISPATCH_DIRECT` en gfx8, y no
se ejecuta en nuestra GPU. El codificador no está *mal*: está validando un camino que la RX
550 no recorre.

**No lo borro y no lo propongo tocar sin decisión de IA-3.** Lo que sí afirmo es que su
valor probatorio actual es sobre una ruta que el hardware objetivo no ejecuta, y que su
utilidad real pasa a ser "formateador de dwords PM4 genérico", que es otra cosa. Queda
`DEFERRED`: la decisión de mantenerlo, reorientarlo o reducirlo es de diseño, no mía.

**Riesgo concreto si no se tiene esto en cuenta**: un driver propio que implemente la
secuencia por costumbre descartaría los 25 contadores EDC y encendería `DED_MODE=2` sobre
una GPU cuya lógica de EDC nunca fue entrenada. El síntoma sería silencioso.

---

## 6. Corrección de método: el árbol del repo **no** sirve para esto

Al principio busqué Polaris 12 en `soc15.c`, como indica `register-maps/gfx-v8-compute.md`
§1 ("`soc15.c` es el archivo clave"). **No está, y no porque falte el fichero**:

| Comprobación | Resultado |
|---|---|
| `soc15.c` líneas | 1521 (7.2.8) / 1521 (7.1.3 del repo) |
| `CHIP_POLARIS12` en `soc15.c` | **0 ocurrencias** |
| `enum amd_asic_type` (el que define `CHIP_CARRIZO`) en **todo** `drivers/gpu/drm/amd/` | **no está** |
| Ficheros que mencionan `CHIP_CARRIZO` | 17, **todos `.c`**, ninguno `.h` |
| Cómo entra Polaris 12 en el driver | `vi.c:2107` (`vi_set_ip_blocks`), no `soc15.c` |

Dos consecuencias:

1. **Polaris 12 no pasa por `soc15.c`.** Va por la generación **VI** (`vi_common_ip_block`).
   Cualquier mapa de registros construido leyendo `soc15.c` describe el camino equivocado
   para nuestra GPU. La afirmación de §1 de ese documento ("en GFX8 el acceso a registros
   no es un `writel` directo sino a través de `soc15_wreg`/`soc15_rreg`") **no la puedo
   confirmar y en este camino no se aplica**: en `gfx_v8_0.c` los accesos son `RREG32(x)` /
   `WREG32(x, v)`, que en `amdgpu.h:1261-1263`-expanden a `amdgpu_device_rreg/wreg`, y el
   argumento es un **offset plano** (`0x307e`), sin indirección de IP version. Reporto el
   nivel que verifiqué; no sigo la cadena `amdgpu_device_rreg` porque no cambia la
   conclusión.
2. **Los valores numéricos de `CHIP_*` no salen de estos árboles.** Los tomé del BTF del
   módulo cargado, que es la fuente primaria en esta host.

**Material mejor disponible que el del repo**: `rx550-upstream-7.2.8/linux-7.2.8.tar.xz`,
sha256 verificado. La extracción parcial del repo (`linux-7.2.8/` con 2 839 ficheros, sólo
`drivers/gpu/drm/amd/`) es **más pobre** que el árbol de 7.1.3 del repo en ficheros de
`amdgpu/` (635 vs 632) y tiene el mismo `soc15.c` de 1521 líneas. La diferencia es que
`7.2.8` es **upstream íntegro y verificado por hash**, y el del repo no lo está.

---

## 7. Herramienta: atribución de inmediatos a símbolos

**La herramienta NO está en el repositorio.** Vive en `/tmp/opencode/pm4count.py` y
`/tmp/opencode/pm4who.py`, porque este hallazgo es material de Fase 4 y la directiva del
2026-09-29 detiene el avance hacia Fase 4: queda escrito y **sin commitear**. Si se retoma,
la herramienta debe ir a `06-INGENIERIA-INVERSA/tools/` con rutas relativas, no `/tmp`.

Función: cuenta un dword de 32 bits en `.text`, alineado a 4 y libre, y **atribuye cada
aparición a la función que la contiene** cruzando con `nm -S`.

Por qué existe: un recuento de un valor no dice quién lo escribe, y "hay 10 apariciones de
`0xC0031500`" no distingue "el submit" de "un workaround". La atribución por rango de
símbolo es lo que convierte el recuento en una afirmación sobre código. Sin ella, esta
ronda sólo habría podido decir "el valor está en el módulo", que es un dato mucho más
débil y no habría separado las dos hipótesis.

Salida usada en §4 (`--path` al `.ko` descomprimido de `7.1.3`):

```
$ python3 /tmp/opencode/pm4who.py amdgpu.ko c0031500
== 0xc0031500  10 apariciones en .text ==
  0x0014a33a  gfx_v8_0_late_init+0x29a
  0x0014a4a5  gfx_v8_0_late_init+0x405
  0x0014a61c  gfx_v8_0_late_init+0x57c  (dword alineado)
  ...
```

Reproduce los recuentos del commit `cc03e33` con un método independiente: 15 para
`0xC0004600`, 10 para `0xC0031500`, 0 para la forma OR'd `0xC0004607`.

---

## 8. Resumen para el resto de IAs

| ID | Afirmación | Clase | Condición que la refutaría |
|---|---|---|---|
| F1-01 | El workaround EDC/GPR de gfx8 es una routine de ECC, no una ruta de submit | `SUPPORTED` | un paquete PM4 de propósito equivalente en otra función de gfx8 |
| F1-02 | Es training del GPR file para el EDC | `SUPPORTED` | que el orden observado no fuera necesario para un EDC fiable |
| F1-03 | **No se ejecuta en Polaris 12** | `SUPPORTED` (C **y** binario, dos vías) | que `asic_type` de la RX 550 no fuera 17 |
| F1-04 | gfx8 no tiene infraestructura RAS | `SUPPORTED` | un `adev->gfx.ras` asignado en algún camino de gfx8 |
| F1-05 | El motivo de la exclusión de Carrizo es un defecto de silicio | `NOT_DETERMINED` | el commit upstream que lo introdujera |
| F1-06 | `DISPATCH_DIRECT` no tiene ningún otro emisor en gfx8 | `SUPPORTED` | 11ª aparición de `0xC0031500` en otro símbolo |
| F1-07 | Polaris 12 entra por `vi.c`, no por `soc15.c` | `SUPPORTED` | — |
| F1-08 | Los valores `CHIP_*` no están en el árbol del repo | `SUPPORTED` | un `.h` del árbol con el enum |

**Acción requerida de nadie**: ninguna. Ninguna de estas cifras necesita autorización de
runtime.

**Lo que sigue abierto y no lo resuelvo**: `F1-05`. El único modo de cerrarlo sin upstream es
leer la documentación de silicio de GFX8, que no está en este host, o el commit, que está
bloqueado por Anubis. Se queda `NOT_DETERMINED` con la vía identificada.
