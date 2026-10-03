# 016 — Contrato estático de observabilidad para el primer camino RX550

> `AGENT_SCOPE = OBSERVABILITY_ONLY` · host Nobara 44 · kernel `7.1.3-200.nobara.fc44.x86_64`
> Clasificación: `READ_ONLY/EVIDENCE` + `DOCUMENTATION`. Ningún código, ningún runtime.
> Fuentes: corpus `RESEARCH/kernelbuild/linux-7.1.3`, BTF del módulo **cargado**, sysfs.

---

## 0. Las tres separaciones que gobiernan este documento

```
EXPOSED ≠ READABLE ≠ OBSERVED ≠ PROVES_PROPERTY
```

- **EXPOSED** — hay una interfaz que lo publica. No implica que se pueda leer.
- **READABLE** — hay una lectura que devuelve un valor. No implica que el valor signifique nada.
- **OBSERVED** — se obtuvo un valor en runtime. No implica que la propiedad sea cierta.
- **PROVES_PROPERTY** — la observación, junto con su cadena de condiciones, sostiene la propiedad.

Una fila de la matriz es una **afirmación sobre el acceso**, no sobre el hardware.

### 0.1 Ausencias: cómo se validaron

Ninguna ausencia de este documento es un `grep` negativo sin validar. Para cada una se
registra QUERY y la validez de la query.

| ausencia | QUERY | validez de la query | resultado |
|---|---|---|---|
| GFX8 lee `mmCP_RB0_RPTR` | símbolo exacto, `drivers/gpu/drm/amd/**/*.c` | el símbolo está definido en 10 cabeceras ⇒ la query tiene dónde encontrarlo | **0 en `gfx_v8_0.c`**. 2 ocurrencias totales, ambas en `gfx_v9_0.c:169` y `gfx_v10_0.c:299` |
| GFX8 lee `mmCP_BUSY_STAT` | ídem | ídem | **0 en `gfx_v8_0.c`**. 2 ocurrencias, `gfx_v9_0.c:160`, `gfx_v10_0.c:287` |
| existe ioctl que mapee BAR5 | `user_ptr\|mmap.*ioctl\|amdgpu_mmap` en `amdgpu_kms.c`, `amdgpu_fusion.c` | los ficheros existen y contienen los handlers DRM | **0**. Ausencia de la búsqueda, no del sistema |

Las 2+2 ocurrencias no son lecturas: `SOC15_REG_ENTRY_STR(ip,inst,reg)` expande a
`{ ip##_HWIP, inst, reg##_BASE_IDX, reg, #reg }` (`soc15.h:91-92`) — el último
elemento es `#reg`, **una cadena**. Registran un nombre para RAS; no tocan el
registro. Y ambas están en ficheros **GFX9/GFX10**, no GFX8.

---

## 1. EVIDENCE

| # | hecho | fuente exacta |
|---|---|---|
| E1 | la apertura de registros es **BAR5** | `amdgpu_device.c:3814` `adev->rmmio_size = pci_resource_len(adev->pdev, 5)`; fallback BAR2 en `:3817` |
| E2 | `amdgpu_regs` lee con **MMIO in-kernel**, no con mmap de userspace | `amdgpu_debugfs.c:153` `value = RREG32(*pos >> 2)` |
| E3 | la entrada es **0400**, y sólo para `amdgpu_regs` se publica el tamaño | `:1745` `S_IFREG \| 0400`; `:1748` `i_size_write(ent->d_inode, adev->rmmio_size)` bajo `if (!i)` |
| E4 | **leer un registro no es pasivo** | `:119` `pm_runtime_get_sync(...)`, con `pm_runtime_put_autosuspend` al salir |
| E5 | el WPTR se publica en el WB **antes** del doorbell, y en **dos** sitios | `gfx_v8_0.c:6028` (graphics) y `:6227` (compute), ambos seguidos de `WDOORBELL32` en `:6029`/`:6228` |
| E6 | el **único** write físico del doorbell | `amdgpu_doorbell_mgr.c:65` `writel(v, adev->doorbell.cpu_addr + index)`, guardado por `:61-62` |
| E7 | `WPTR_POLL_ADDR` se programa una vez y no se reescribe | `gfx_v8_0.c:4263-4264` |
| E8 | `CP_RB_WPTR_POLL_CNTL` **no tiene bit de enable** | `gfx_8_1_sh_mask.h`: sólo `POLL_FREQUENCY` 0xffff y `IDLE_POLL_COUNT` 0xffff0000 |
| E9 | el idle del driver es un predicado propio | `gfx_v8_0.c:4798-4807` `gfx_v8_0_is_idle()`: `GUI_ACTIVE == 0` **y** `mmGRBM_STATUS2 == 0x8` |
| E10 | el fence de GFX8 se escribe con dos packets distintos según el ring | `gfx_v8_0.c:6145`, `:6159` `PACKET3_EVENT_WRITE_EOP` (GFX); `:6239` `PACKET3_RELEASE_MEM` (compute) |
| E11 | el destino del fence lo lee la CPU | `gfx_v8_0.c:910` `tmp = adev->wb.wb[index]` |
| E12 | `amdgpu_test_ib` detiene el scheduler, no lo cancela | `amdgpu_debugfs.c:1777` `drm_sched_wqueue_stop(&ring->sched)`; `:1781` `amdgpu_ib_ring_tests(adev)`; modo 0400 en `:2468` |

---

## 2. OBSERVABILITY_MATRIX

`SRC` = fuente · `KI` = interfaz de kernel · `EXP` = expuesto a userspace ·
`DRV` = legible por el driver · `ANL` = legible por analizador · `RT` = requiere runtime

| propiedad | SRC | KI | EXP | DRV | ANL | RT |
|---|---|---|---|---|---|---|
| identidad PCI 5 campos | `amdgpu_drv.c:2034-2041` | `pdev->vendor/device/subsystem_*/revision` | **sí**, sysfs `/sys/bus/pci/devices/0000:01:00.0/` | sí | sí | **no** |
| BAR5 declarada, base, longitud | E1 | `pci_resource_start/len` | **sí**, sysfs `resource5`, `config` | sí | sí | **no** |
| BAR5 **reclamada** por nosotros | C4 propio | `pci_request_region` | no | sí | no | **sí** |
| **mmap de BAR5 desde userspace** | — | — | **no** | — | — | n/a |
| lectura de registro MMIO | E2,E3,E4 | `amdgpu_regs` 0400 + `RREG32` | **sí**, debugfs | sí | sí | **sí** |
| WPTR publicado en el WB | E5 | memoria del kernel | no | sí | no | **sí** |
| WPTR visto por el hardware | `mmCP_RB0_WPTR` 0x3045 | MMIO | **sí** | sí | sí | **sí** |
| doorbell **escrito** | E6 | MMIO a BAR2 | no | sí | no | **sí** |
| doorbell **armado** | `mmCP_RB_DOORBELL_CONTROL` 0x3059 | MMIO | **sí** | **no**: GFX8 no lo lee | sí | **sí** |
| RPTR avanzado | `mmCP_RB0_RPTR` 0x21c0 | MMIO | **sí** | **no**: 0 lecturas en `gfx_v8_0.c` | sí | **sí** |
| RPTR writeback a memoria | `gfx_v8_0.c:4259-4260` | `RB_RPTR_WR_ENA` | **no**: enable sólo init (`:4253`→`:4266`) | no | no | **sí** |
| CP ocupado | `mmCP_BUSY_STAT` 0x219f | MMIO | **sí** | **no**: 0 lecturas en `gfx_v8_0.c` | sí | **sí** |
| GFX activo | `mmGRBM_STATUS` 0x2004 | MMIO | **sí** | **sí** `:4802`, `:4897` | sí | **sí** |
| GFX idle (predicado del driver) | `mmGRBM_STATUS2` 0x2002 | MMIO | **sí** | **sí** `:4803`, `:4813`, `:4914` | sí | **sí** |
| `WPTR_POLL_ADDR` programada | E7 | MMIO | **sí** | sí (escribe) | sí | **sí** |
| `WPTR_POLL_CNTL` — sondeo activo | E8 | MMIO | **sí** | no | sí | **sí** |
| IB descriptor | `amdgpu_ib.h`, `amdgpu_ib_schedule` `amdgpu_ib.c:124` | ioctl de amdgpu | no sin driver | sí | sí | **sí** |
| write del fence en el WB | E10 | packet en el ring | no | — | sí | **sí** |
| valor en el destino del fence | E11 | memoria del kernel | no | **sí** | no | **sí** |
| scheduler en reposo | E12 | `drm_sched_wqueue_stop` | no | sí | no | **sí** |

### 2.1 Las tres filas que no se leen como las demás

- **`mmCP_RB_DOORBELL_CONTROL`**: legible por analizador, **no por el driver**. No hay
  lectura en GFX8. Su valor sólo se obtiene por `amdgpu_regs`, y eso es nuestro, no del driver.
- **`mmCP_BUSY_STAT`**: igual. Además su semántica es **por nombre de campo**, no
  autoritativa del driver. `STATICALLY_SUPPORTED`, no `PROVEN`.
- **`mmCP_RB0_RPTR`**: el driver no lo lee, pero **el hardware sí lo actualiza** y es
  un registro real del mapa. Que el driver no lo use no lo convierte en inválido para
  nosotros; sólo significa que su lectura es **nuestra** y por tanto nuestra
  responsabilidad de interpretarlo.

---

## 3. DISCRIMINANTS

`POSSIBLE VALUES` → `DISCRIMINATES` → `H1/H2`

| # | observación | valores posibles | discrimina | entre |
|---|---|---|---|---|
| D1 | `amdgpu_test_ib` | `"ib ring tests passed."` / `failed (-22)` / `failed (-110)` / otro | sólo `passed` prueba que la cadena WB→fence→lectura cerró. `(-22)` = fence_ok, valor no. `(-110)` = **ambiguo**, no se consumption | ejecución vs no-ejecución, **sólo** en el caso `passed` |
| D2 | `mmCP_RB_DOORBELL_CONTROL` | `DOORBELL_EN` 0/1 | que la capacidad de doorbell está armada. **NO** que se escribió una puerta | nada sobre escritura |
| D3 | `mmCP_RB0_RPTR` antes/después | avanza / no avanza | consumo o progreso del **ring 0**. **NO** ejecución | consumo vs no-consumo |
| D4 | `mmCP_RB_WPTR_POLL_ADDR_LO/HI` | valor distinto | que se programó la dirección. **NO** que se sondee | nada sobre sondeo |
| D5 | `mmCP_RB_WPTR_POLL_CNTL` | cualquier valor | **nada**: no hay bit de enable (E8). El valor no separa "sondeo activo" de "sondeo apagado" | nada |
| D6 | `mmGRBM_STATUS2` + `GUI_ACTIVE` | `0x8` y 0 / distinto | idle **según el predicado del driver** (E9) | precondición sí/no, no resultado |
| D7 | `mmCP_BUSY_STAT` | bits `SEM_CMDFIFO_NOT_EMPTY`, `CE_PARSING_PACKETS` | actividad del CP y del Command Engine. Semántica por nombre de campo | indicio, no prueba |
| D8 | destino del fence (WB) | centinela presente / ausente | **única** prueba de efecto | efecto presente vs no |
| D9 | `mmCP_RB0_WPTR` | valor publicado | que la CPU publicó | publicación, no consumo |

### 3.1 La pregunta central, respondida

**Discriminable estáticamente, sin runtime:**

- La tupla de identidad de 5 campos, y que satisface el contrato.
- Base, longitud y tipo de BAR5, y que cabe el mayor offset de registro conocido.
- Que el código GFX8 **no lee** `mmCP_RB0_RPTR` ni `mmCP_BUSY_STAT`.
- Que `CP_RB_WPTR_POLL_CNTL` no tiene enable: **la lectura de D5 no puede discriminar**.
- Que los 10 registros coinciden entre `gfx_8_0_d.h` y `gfx_8_1_d.h`.
- Qué packet escribe el fence en cada tipo de ring (E10).

**Sólo observable en runtime:**

- Que cualquier lectura devuelva un valor vivo, y no un registro muerto.
- Que la publicación del WPTR llegue al hardware.
- Que la escritura del doorbell ocurra.
- Que el RPTR avance.
- Que el fence se escriba y la CPU lo observe.
- Que el destino contenga el centinela.
- Que la precondición de idle se cumpla en ese instante.

**La observación que separa las hipótesis Doorbell vs Sondeo:** el par
`(D3, D1)` bajo las dos condiciones de doorbell. Con la puerta escrita, `D1 = passed`
y `D3` avanza. Con la puerta suprimida, `D1 = failed` distingue dos casos que `D3`
separa: si `D3` **no** avanza ⇒ no consumo; si `D3` **sí** avanza ⇒ consumed sin
efecto, que es compatible con «la puerta es necesaria» pero **no lo prueba**, porque
`D5` no puede confirmar que el sondeo esté activo y algún otro mecanismo podría
haber reaccionado a la publicación.

`D5` es el discriminante que **falta**, y su ausencia es estructural: no existe un
registro que loProvea. No es un hueco de esta investigación.

---

## 4. RUNTIME_BOUNDARY

El contrato del preflight, con las cuatro cosas que **no** son la misma:

```
IDLE         mmGRBM_STATUS2 == 0x8  ∧  GUI_ACTIVE == 0        (E9, predicado del driver)
   ≠
CONSUMPTION  mmCP_RB0_RPTR avanza                              (D3)
   ≠
EXECUTION    el destino contiene el centinela                  (D8)
   ≠
COMPLETION   la CPU observó la escritura del fence             (D1 "passed")
```

Y dos fronteras que la evidencia fija:

- **Una lectura de registro cambia el estado de energía.** E4: `amdgpu_regs` hace
  `pm_runtime_get_sync`. «Observar» no es neutro. Cualquier Discriminante que lea
  MMIO hereda ese coste, y una secuencia de lecturas puede mantener el dispositivo
  despierto que antes estaba en gfxoff.
- **Reclamar BAR5 no es una operación pasiva de software.** Con `amdgpu` enlazado,
  `pci_request_region` devuelve `-EBUSY` (`pci.c:3786`). Es precondición de
  integración futura; no se resuelve aquí.

---

## 5. LIMITATIONS

1. **`EXPOSED` no implica `PROVES`.** `mmCP_BUSY_STAT` se expone y no lo lee el
   driver: su semántica viene del nombre del campo, no de una lectura del driver.
   `STATICALLY_SUPPORTED`.
2. **D5 no discrimina nada.** Sin bit de enable, leer `CP_RB_WPTR_POLL_CNTL` no
   separa sondeo activo de sondeo apagado. Consecuencia directa: el resultado
   «polling es suficiente» **no será demostrable** con esta instrumentación.
3. **RPTR es del ring 0.** Los compute rings necesitarían selección SRBM; el
   mecanismo está en `amdgpu_debugfs.c:174-177` pero no se ha ejercitado.
4. **El RPTR en memoria no sirve.** `RB_RPTR_WR_ENA` se activa en `:4253` y se
   desactiva en `:4266`: durante el test, el slot de RPTR en memoria no sigue el
   consumo. Sólo sirve el registro MMIO.
5. **`IDLE` no se garantiza:** No hay garantía: `drm_sched_wqueue_stop` (E12) pausa
   entradas nuevas y no espera a la GPU. Un trabajo ya en vuelo puede seguir
   ejecutándose durante la ventana.
6. **D1 `(-110)` es ambiguo por construcción.** Un timeout de fence no separa
   «no consumido» de «consumido sin efecto». Sólo D3 desempata, y sólo para el
   ring 0.
7. **`TARGET_MATCH_COMPLETENESS` sigue `NOT_DETERMINED`.** No se ha tocado.
8. **La matriz describe el driver `amdgpu` en ejecución.** No dice qué hará
   nuestro driver: es el estado de partida, no un requisito de hardware.

---

## 6. OPEN_ITEMS

| # | item | por qué no avanza aquí |
|---|---|---|
| O1 | ¿qué mecanismo observa el WPTR tras la publicación? | requiere runtime **y** un discriminante que no existe (L2) |
| O2 | semántica real de los bits de `CP_BUSY_STAT` | requiere documento ISA GFX8, `NOT_AVAILABLE` en el corpus |
| O3 | valor efectivo de `POLL_FREQUENCY` / `IDLE_POLL_COUNT` | el driver no los escribe; los deja el firmware o el default |
| O4 | `mmCP_RB_DOORBELL_CONTROL` leído por GFX8 | no hay lectura; sólo se obtiene por `amdgpu_regs` |
| O5 | treadmill de la ventana `rmmod → insmod` | se documenta en el arnés de EP08, fuera de este artefacto |
| O6 | aislamiento por proceso entre agentes | fuera de alcance; afecta al proceso, no al hardware |

---

## 7. Procedencia y alcance

- **Ningún fichero existente modificado.** Un artefacto nuevo.
- **Ninguna implementación de AMDGPU convertida en requisito de hardware.** Las
  columnas `DRV` describen lo que hace el driver de referencia; no son
  requisitos. Donde el driver no lee (`RPTR`, `CP_BUSY_STAT`, `DOORBELL_CONTROL`),
  la fila lo dice explícitamente.
- **Ninguna semántica inventada.** Los nombres de campo se citan como
  `STATICALLY_SUPPORTED` cuando proceden del nombre, nunca como `PROVEN`.
- **Sin reauditar** P-8, Q1 GPUVM, Q2 MEMORY, Q3 FENCE ni Q4 SUBMISSION. Sólo se
 .cruzaron referencias concretas (`gfx_v8_0.c:6145/6159/6239` para E10), porque la
  matriz necesitaba una cita, no una reinvestigación.

### Contradicciones con otras sesiones

- **`012 §7`** ya resuelto en ronda previa: la refutación de `pci.ids` usó
  `grep -c 699F` en mayúsculas; el fichero usa minúsculas. Confirmado.
- **Colisión de workspace** en `Q1` y `Q2`: otras sesiones escribieron
  `013`, `014` y sus versiones de Q1/Q2 sobre los mismos paths de esta sesión.
  Este artefacto no toca ninguno de esos ficheros.
