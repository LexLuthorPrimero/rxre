# 047 · La ruta real de Polaris12: canal SMC con argumento, mutex y vtable

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu`
`CORRECTS_RUTA=046-correccion-smu-ruta-no-compilada-para-polaris12.md`

> 046 estableció que `si_dpm.c` no se compila para Polaris12. Este documento
> reconstruye el camino **real** y confirma que el hallazgo central de 040 —el
> centinela `SMC_RESP_0 == 0`— **sí** es válido en la ruta activa.

---

## CUDA principal

Polaris12 envía mensajes al SMC con **12 registros de argumento** y un **mutex de
serialización**, a través de una **vtable por ASIC**. El canal de un registro de
respuesta es el mismo, pero la arquitectura alrededor es otra.

---

## 1. La cadena real, completa

```
polaris10_smumgr.c:2690   .send_msg_to_smc_with_parameter = smu7_send_msg_to_smc_with_parameter
polaris10_smumgr.c:2xxx   llamadas: 102, 1089, 2152, 2260, 2268, 2307, 2340
          │
          ▼
smumgr.c:155              smum_send_msg_to_smc_with_parameter(hwmgr, msg, parameter, resp)
  :161   if (hwmgr == NULL || !send_msg_to_smc_with_parameter || (resp && !get_argument))
  :162       return -EINVAL;
  :165   mutex_lock(&hwmgr->msg_lock);                    ◄ SERIALIZACIÓN
  :166   hwmgr->smumgr_funcs->send_msg_to_smc_with_parameter(hwmgr, msg, parameter);
  :172   if (resp) *resp = hwmgr->smumgr_funcs->get_argument(hwmgr);
  :173   mutex_unlock(&hwmgr->msg_lock);
          │
          ▼
smu7_smumgr.c:161         smu7_send_msg_to_smc_with_parameter(hwmgr, msg, parameter)
  :163   PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, SMC_RESP, 0);   ◄ espera != 0
  :164   cgs_write_register(device, mmSMC_MSG_ARG_0, parameter);    ◄ ARGUMENTO
  :165   return smu7_send_msg_to_smc(hwmgr, msg);                  ◄ MENSAJE
          │
          ▼
smu7_smumgr.c:170         smu7_get_argument(hwmgr)
  :172   return cgs_read_register(device, mmSMC_MSG_ARG_0);         ◄ LEE ARGUMENTO
```

## 2. Confirmación del centinela

```
smu_7_1_1_d.h:92   #define mmSMC_RESP_0
smu_6_0_sh_mask.h:446  #define SMC_RESP_0__SMC_RESP_MASK  0xffffffffL
smu_6_0_sh_mask.h:447  #define SMC_RESP_0__SMC_RESP__SHIFT 0x00000000
```

`SMC_RESP` ocupa **el registro entero**, y el driver espera a que sea **distinto
de cero**.

```
SMC_RESP_SENTINEL_ZERO = PROVEN   en la RUTA ACTIVA de Polaris12
  SMC_RESP_0 == 0x00000000  significa "el SMC todavía no terminó"
  el campo es la palabra completa, no una sub-máscara
```

**Esto valida 040.** El hallazgo se trazó sobre `si_smc.c` (ruta SI) pero el
mismo registro, el mismo centinela y la misma espera aparecen en la ruta que
Polaris12 ejecuta de verdad.

```
SMU_SENTINEL_RULE_CONFIRMED_ON_ACTIVE_PATH = PROVEN
  centinela explícito  →  poll/wait con predicto
  y el ejemplo contrario (VM_INVALIDATE_REQUEST, sin centinela documentado)
      usa primitiva sin comparación
  la regla de diseño que se derivó en 040 se sostiene en hardware real de GFX8
```

## 3. Lo que la ruta PowerPlay añade sobre la de SI

| aspecto | SI (`si_smc.c`) | Polaris12 (`smu7_smumgr.c`) |
|---|---|---|
| argumento | no | **12 registros** `mmSMC_MSG_ARG_0..11` |
| despacho | función directa | **vtable** `hwmgr->smumgr_funcs->...` |
| serialización | ninguna | **`mutex_lock(&hwmgr->msg_lock)`** |
| respuesta | valor de retorno | `*resp` vía `get_argument` |

```
smc_message_argument_registers = PROVEN
  mmSMC_MSG_ARG_0 .. mmSMC_MSG_ARG_11    smu7_7_1_1_d.h:107-126
  smc_msg_mutex_required       = PROVEN
  la ruta PP asume que varios hilos pueden pedir mensajes a la vez
```

El mutex es una diferencia arquitectónica relevante: la versión legacy
`amdgpu_si_send_msg_to_smc` **no serializa**, mientras la de PowerPlay sí.
Un driver propio necesita el mutex o necesita demostrar que no puede haber
contención.

## 4. El modelo de energía real de Polaris: tablas de voltaje

```
polaris10_smumgr.c:664   polaris10_populate_smc_mvdd_table()    memoria
polaris10_smumgr.c:691   polaris10_populate_smc_vddc_table()    nucleo
polaris10_smumgr.c:716   polaris10_populate_smc_vddci_table()   E/S
polaris10_smumgr.c:230   smu7_send_msg_to_smc_offset()   = PPSMC_MSG_Test, 0x20000
```

El control de energía de Polaris12 se organiza por **dominio de voltaje**
(mvdd / vddc / vddci), no por la curva de histéresis A-T que documenté en 041-042.

```
POLARIS_POWER_MODEL = PROVEN   voltage tables per domain
  la curva A-T de 041/042 pertenece a la ruta SI y NO a Polaris12
```

## 5. Lo que hay que rehacer y lo que no

```
A REHACER sobre la ruta real:
  · dónde se selecciona y aplica el nivel de voltaje
  · el equivalente de reloj en smu7_hwmgr.c
  · smu7_send_msg_to_smc() — el envío base, todavía sin leer
  · el significado de PPSMC_MSG_PerformBtc y avfs_btc

A CONSERVAR de 040-045:
  · 040  canal SMC y centinela 0x00  → CONFIRMADO en 047
  · 044  "el VBIOS miente"          → aplica a clock.spll.reference_freq
  · 046  las 5 reglas metodológicas
  · 041/042/043  como REFERENCIA DE GENERACIÓN para SI
                    (Tonga, Fiji, Carrizo, Stoney), no para Polaris12

A DESCARTAR para Polaris12:
  · curva A-T, CG_AT__CG_R/L, bsp, asi/pasi, r600_calculate_u_and_p
```

## 6. La regla que faltó en todo el scope

```
COMPILE_GATE_BEFORE_TRACE_GATE

  antes de invertir un hallazgo en un fichero:
     1. ¿compila este .c para mi ASIC?
        → grep del CONFIG en el Makefile que lo incluye
     2. ¿ese CONFIG existe en el Kconfig y describe a mi ASIC?
        → leer el help, no solo el nombre
     3. ¿existe una ruta alternativa que sí se compile?
        → buscar el selector de ASIC en la vtable

  Coste de omitirlo: 6 documentos y ~1250 líneas sobre código
  que no entra en el build del hardware objetivo.
```

El nombre del fichero y del símbolo eran correctos. El modelo mental era
correcto. Lo que no se comprobó fue **si ese código se ejecuta en esta placa**.

## 7. Siguiente tarea

```
smu7_send_msg_to_smc()                      ← el envío base, sin leer
smu7_get_argument()                          ← lectura del argumento
polaris10_populate_smc_{mvdd,vddc,vddci}_table  ← el modelo de energía real
smu7_hwmgr.c: dónde se aplica voltaje → reloj
```

Los tres primeros son alcance local y determinista. El cuarto es el que hace
falta para responder a la pregunta original —"quién cambia el reloj"— por el
camino que Polaris12 ejecuta de verdad.