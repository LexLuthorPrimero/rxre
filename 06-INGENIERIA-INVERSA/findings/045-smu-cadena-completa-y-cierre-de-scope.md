# 045 · Cadena cerrada: del BIOS y del hardware al reloj de GFX8

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu`
`COMPLEMENTS=040-smu-canal-mensajes-gfx8.md,041-curva-at-histeresis-dvfs-gfx8.md,
042-at-wire-format-inversion-cg-r-l.md,043-pll-bsp-asi-pasi.md,044-xclk-fuentes-y-constantes-legacy.md`

---

## Estado del scope `smu` tras cinco documentos

```
CERRADO          el canal host ↔ SMU, la protocolo de mensaje, el reloj de
                 referencia, el divisor de PLL, la banda de histéresis A-T
                 y su formato de wire

ABIERTO          la semántica del firmware, que no es código del driver
NOT_IN_CORPUS   qué hace el firmware con [t_l, t_h]
```

---

## 1. La cadena completa, de la fuente del reloj a la banda

```
┌─ adev->clock.spll.reference_freq ──────────────┐  del VBIOS
└─ RREG32_SMC(ixCG_CLKPIN_CNTL_2 / CLKPIN_CNTL) ─┘  del HARDWARE
                          │
                          ▼
                       xclk
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
   asi = 1000                          pasi = 400000
   (RV770_ASI_DFLT)                    (CYPRESS_HASI_DFLT)
   constante heredada                  constante heredada
        │                                   │
        ▼                                   ▼
  r600_calculate_u_and_p(asi,  xclk, 16)   ...pasi, xclk, 16
        │                                   │
     bsp,  bsu                           pbsp, pbsu
        │                                   │
        ├──► mmCG_BSP = bsp | bsu<<16 ───┐    │
        │                               │    │
        └──► t_l * bsp  / 20000 ◄────────┼────┤
                      t_h * pbsp /20000  │    │
                                         ▼    ▼
                              ┌──────────────────────┐
                              │  bandas A-T por nivel  │  041
                              │  r600_calculate_at()   │
                              └──────────┬───────────┘
                                         ▼
                          bits 0-15 = t_l · bsp / 20000   ◄ CG_AT__CG_R
                          bits 16-31= t_h · pbsp/ 20000   ◄ CG_AT__CG_L
                                         ▼
                                  cpu_to_be32()      ◄ BIG-ENDIAN
                                         ▼
                        amdgpu_si_copy_bytes_to_smc()
                                         ▼
                              SRAM del SMC
                                         ▼
                    WREG32(mmSMC_MESSAGE_0 = 0x94) + poll a 0x95
                                         ▼
                              FIRMWARE SMU  aplica
```

**Cero escrituras a registros de reloj por parte del driver.** El último punto de
contacto real del driver es la SRAM del SMC y el registro de mensaje.

---

## 2. Inventario de lo cerrado en este scope

| # | documento | cierra |
|---|---|---|
| 040 | canal de mensajes SMU | `mmSMC_MESSAGE_0`=0x94, `mmSMC_RESP_0`=0x95, protocolo 0x00/0x01/0xFF, timeouts 1 s / 200 ms |
| 041 | curva A-T | algoritmo `r600_calculate_at`, tres límites de niveles (efectivo **9**), big-endian |
| 042 | formato de wire A-T | `CG_AT__CG_R`=t_l, `CG_AT__CG_L`=t_h — **invertidos** frente al nombre |
| 043 | PLL | `r600_calculate_u_and_p` reparto P/U, `CG_BSP__BSU` de 4 bits, un cálculo dos consumidores |
| 044 | reloj de referencia | `xclk` con 5 caminos, 2 leídos del hardware, `asi`/`pasi` constantes heredadas |

## 3. Lo que este scope aporta al resto del proyecto

```
CONEXIÓN CON EL DOMINIO INVALIDATE   ya registrada en 040
  SMU:  RESP_0 == 0 es centinela de "pendiente"  → poll con predicto
  VMID: no hay centinela documentado            → primitiva sin comparación
  regla reutilizable para el driver propio

CONEXIÓN CON FIRMWARE               dominio 33 del universo
  el reloj NO lo aplica el driver; es el firmware
  cualquier implementación propia necesita el firmware, no solo registros

CONEXIÓN CON COHERENCIA DE HARDWARE  el propio driver admite que el BIOS miente
                                      sobre la frecuencia (vi.c:545)
                                      ⇒ el VBIOS es fuente no fiable por diseño

CONEXIÓN CON VALIDACIÓN              5 unidades y 2 constantes medidas,
                                      toda la aritmética es verificable en software
```

## 4. Reglas metodológicas queurangi este scope

```
SUBDIRECTORY_INVENTORY_GATE
  la sexta vez que un subdirectorio sin inventariar dio falso negativo:
  asic_reg/smu/  y  pm/   era donde estaba casi todo

GREP_FILTER_FALSELY_NEGATIVE
  un filtro alternativo sobre un grep puede eliminar exactamente lo que
  se busca; hay que contar ANTES de filtrar

GREP_TOO_SPECIFIC_AS_ABSENCE
  exigir tipo+nombre+firma a la vez produce ceros falsos

OUT_PARAMETER_NOT_IN_ASSIGNMENT_SEARCH
  un valor que se rellena como parámetro de salida no aparece en ninguna
  asignación; hay que mirar el constructor
```

## 5. Estado de los otros agentes

```
Al tomar este scope se verificó:
  pm4dw / pteflags / findings  → occupied, no tocados
  SMU/DPM/thermal              → 0 findings, 0 tools  ← elegido
Tres documentos 017/018/019 cubren invalidación y execution order:
  son de otro agente, coherentes con lo que cerré antes, NO los toqué
Al terminar: pm4dw, pteflags y findings se liberaron; solo queda docs
```

---

## 6. Lo único que queda abierto en este dominio

```
FIRMWARE_SMU_INTERPRETATION   NOT_IN_CORPUS
  qué hace el firmware con la tabla de estados
  qué hace con [t_l, t_h]
  por qué 1 s para cinco mensajes concretos

RUNTIME: los valores reales de xclk, asi, pasi, bsp
  → requiere lectura de hardware, NO autorizado
```

Esa frontera no es cerrable con el corpus disponible. Todo lo demás del scope
`smu` queda cerrado en el lado software.

---

## Valor consolidado para el driver propio

Para controlar el reloj de GFX8 hace falta, y esto es lo que la investigación
establece:

1. **leer** `xclk` de la fuente que el hardware indique — nunca asumirla
2. calcular el divisor con el reparto P/U usando las constantes `asi`/`pasi`,
   sabiendo que vienen de otros ASICs y **verificarlas** contra el hardware real
3. escalar las bandas A-T con el mismo `bsp`/`pbsp`, invirtiendo `CG_R`↔`CG_L`
4. byte-swappear a big-endian
5. subir la tabla a la SRAM del SMC y mandar el mensaje por `0x94`/`0x95`

Cada paso tiene ahora su evidencia de archivo y línea. El paso 2 es el único
donde el upstream carga con una suposición que **no ha sido validada para
Polaris12**, y por eso es el primero que un driver propio debería medir en vez
de copiar.