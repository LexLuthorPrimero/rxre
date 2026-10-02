# 048 · El protocolo SMC de Polaris12 completo — y dos correcciones a 040

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu` · `CORRECTS=040-smu-canal-mensajes-gfx8.md`

---

## CUDA principal

El host **arma** el handshake escribiendo `0` en el registro de respuesta antes
de enviar el mensaje. Y la función de envío **devuelve siempre 0**: el éxito y el
fallo solo se ven en el log y en el parámetro `resp`.

Ambos puntos contradicen lo que escribí en 040.

---

## 1. El envío base

```
int smu7_send_msg_to_smc(hwmgr, msg)                    smu7_smumgr.c:130
{
  :133   PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, SMC_RESP, 0);
  :134   ret = PHM_READ_FIELD(hwmgr->device, SMC_RESP_0, SMC_RESP);
  :135   if (ret == 0xFE)      dev_dbg("last message was not supported");
  :137   else if (ret != 1)    dev_info("last message was failed ret is %d", ret);

  :140   cgs_write_register(device, mmSMC_RESP_0, 0);        ◄ ARMA EL HANDSHAKE
  :141   cgs_write_register(device, mmSMC_MESSAGE_0, msg);   ◄ ENVÍA EL MENSAJE

  :142   PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, SMC_RESP, 0);
  :143   ret = PHM_READ_FIELD(hwmgr->device, SMC_RESP_0, SMC_RESP);
  :144   if (ret == 0xFE)      dev_dbg("message %x was not supported", msg);
  :147   else if (ret != 1)    dev_dbg("failed to send message %x ret is %d", msg);

  :150   return 0;
}
```

### La secuencia, paso a paso

| # | paso | registro | efecto |
|---|---|---|---|
| 1 | esperar ocioso | `mmSMC_RESP_0` | `(RESP & 0xffffffff) != 0` |
| 2 | leer | `mmSMC_RESP_0` | **diagnóstico del mensaje anterior** |
| 3 | escribir `0` | `mmSMC_RESP_0` | **arma** el handshake |
| 4 | escribir | `mmSMC_MESSAGE_0` | mensaje |
| 5 | esperar | `mmSMC_RESP_0` | respuesta != 0 |
| 6 | leer | `mmSMC_RESP_0` | código de resultado |
| 7 | — | — | `return 0` **siempre** |

Los pasos 1-2 y 5-6 son **simétricos**: mismo predicido, mismo registro, antes y
después. El paso 3 existe porque el registro es del host.

## 2. CORRECCIÓN 1 a 040 — `0x00` no es "pendiente", es "armado por el host"

```
040 afirmación:   "0x00 = PENDIENTE — el SMC todavía no terminó"
048 realidad:      el HOST escribe 0 explícitamente antes de enviar  (:140)
                   0x00 es el estado de espera,_blogado por el host
```

La distinción importa para un driver propio. En la ruta SI
(`amdgpu_si_send_msg_to_smc`) el driver **no** limpiaba el registro: solo escribía
el mensaje y esperaba. En la ruta PowerPlay el host es quien arma.

```
SMC_HANDSHAKE_ARMED_BY_HOST = PROVEN   smu7_smumgr.c:140
  ruta PP:  host escribe RESP=0, luego MENSAJE
  ruta SI:  host escribe solo MENSAJE
  ⇒ el registro de respuesta es escritura del host, no solo lectura
```

## 3. CORRECCIÓN 2 — hay cuatro códigos, no tres

```
0x00   sin resultado registrado   (estado tras armar)
0x01   OK                          :140, :147   ret != 1 → fallo
0xFE   mensaje NO SOPORTADO        :135, :144
otro   fallo                       :137, :147
```

`0xFE` no existe en el enum `PPSMC_Result` que leí en 040
(`ppsmc.h:67-68`: `OK=0x01`, `Failed=0xFF`). El valor real de "no soportado" es
**`0xFE`**, no `0xFF`.

```
PPSMC_FAILED_VALUE = 0xFF        la constante del enum legacy
SMC_NOT_SUPPORTED   = 0xFE        el valor realmente comprobado
  son DISTINTOS: el enum no describe el protocolo de la ruta PP
```

## 4. El retorno siempre es éxito

```
smu7_smumgr.c:150           return 0;              sin condición
smu7_smumgr.c:165           return smu7_send_msg_to_smc(hwmgr, msg);
smumgr.c:166-170            ret = hwmgr->smumgr_funcs->send_msg_to_smc_with_parameter(...)
                            if (ret) { unlock; return ret; }      ◄ nunca se cumple
```

```
SEND_ALWAYS_RETURNS_SUCCESS = PROVEN
  smu7_send_msg_to_smc  → return 0 incondicional
  smu7_send_msg_to_smc_with_parameter → lo propaga
  smum_send_msg_to_smc_with_parameter → comprueba un ret que nunca es != 0

  el fallo es observable por:
    · dev_info / dev_dbg           (smu7_smumgr.c:135,137,144,147)
    · el parámetro de salida resp   (smumgr.c:172 → get_argument)
  NO por el valor de retorno
```

Consecuencia práctica: un driver propio **no puede** comprobar el envío mirando
el retorno. Debe leer `resp` explícitamente o parsear el log.

## 5. La aritmética de la espera

```
smu_helper.h:234   PHM_WAIT_FIELD_UNEQUAL(hwmgr, reg, field, fieldval)
                     → PHM_WAIT_REGISTER_UNEQUAL(hwmgr, reg,
                         (fieldval) << PHM_FIELD_SHIFT(reg,field),
                         PHM_FIELD_MASK(reg,field))
                       → PHM_WAIT_REGISTER_UNEQUAL_GIVEN_INDEX(hwmgr, mm##reg, value, mask)
                         → phm_wait_for_register_unequal(hwmgr, index, value, mask)

smu_6_0_sh_mask.h:446   SMC_RESP_0__SMC_RESP_MASK  0xffffffffL
smu_6_0_sh_mask.h:447   SMC_RESP_0__SMC_RESP__SHIFT 0x00000000
```

Con `fieldval = 0`, `shift = 0`, `mask = 0xffffffff`:

```
predicado resuelto = (SMC_RESP_0 & 0xffffffff) != (0 & 0xffffffff)
                   =  el registro entero != 0
```

```
SMC_RESP_FIELD_IS_WHOLE_REGISTER = PROVEN
  no hay submáscara que haya que interpretar: es la palabra completa
```

## 6. El bucle de espera

```
int phm_wait_for_register_unequal(hwmgr, index, value, mask)   smu_helper.c:155
   :161   for (i = 0; i < hwmgr->usec_timeout; i++) {
   :163       cur_value = cgs_read_register(hmgr->device, index);
   :165       if ((cur_value & mask) != (value & mask)) break;
   :166       udelay(1);
          }
   :169   if (i == hmgr->usec_timeout) return -ETIME;
```

```
SMC_WAIT_MECHANISM = PROVEN
  granularidad  1 µs  (udelay)
  límite        hwmgr->usec_timeout      ← valor NO medido, no.read
  error         -ETIME
  comparación   con máscara, genérica: sirve para subcampos
```

El polling es **idéntico** al de la ruta SI (`si_smc.c:196-201`): 1 µs. Lo que
cambia es el timeout, que aquí es un campo del hwmgr y allí eran constantes
literales (1 s / 200 ms según el mensaje).

## 7. La cadena de tres niveles

```
polaris10_smumgr.c:2690   .send_msg_to_smc_with_parameter = smu7_send_msg_to_smc_with_parameter
        │
smumgr.c:155               smum_send_msg_to_smc_with_parameter(hwmgr, msg, param, resp)
   :165   mutex_lock(&hwmgr->msg_lock)
   :166   vtable → smu7_send_msg_to_smc_with_parameter
   :172   if (resp) *resp = smumgr_funcs->get_argument(hwmgr)
   :173   mutex_unlock
        │
smu7_smumgr.c:161          smu7_send_msg_to_smc_with_parameter(hwmgr, msg, param)
   :163   espera RESP != 0
   :164   cgs_write_register(mmSMC_MSG_ARG_0, param)     ◄ argumento
   :165   return smu7_send_msg_to_smc(hwmgr, msg)
        │
smu7_smumgr.c:130          smu7_send_msg_to_smc(hwmgr, msg)
   :140   cgs_write_register(mmSMC_RESP_0, 0)           ◄ armar
   :141   cgs_write_register(mmSMC_MESSAGE_0, msg)      ◄ enviar
   :142   espera RESP != 0
   :150   return 0
```

**Tres niveles**: vtable por ASIC → mutex → primitiva de bajo nivel. La función
de 040 (`amdgpu_si_send_msg_to_smc`) no tiene ninguno de los tres.

---

## 8. Estado revisado del canal SMC

```
REGISTROS     mmSMC_MESSAGE_0, mmSMC_RESP_0          PROVEN   smu_7_1_1_d.h:91-92
ARGUMENTOS    mmSMC_MSG_ARG_0..11                    PROVEN   smu_7_1_1_d.h:107-126
SENTINELA     0x00 sin resultado                     PROVEN   armed by host :140
OK            0x01                                    PROVEN   :140, :147
NO SOPORTADO  0xFE                                    PROVEN   :135, :144
ESPERA        (REG & 0xffffffff) != 0, 1 µs          PROVEN   smu_helper.c:161-166
TIMEOUT       hwmgr->usec_timeout                    PROVEN   smu_helper.c:161
ERROR         -ETIME                                  PROVEN   smu_helper.c:169
RETORNO       siempre 0                              PROVEN   smu7_smumgr.c:150
MUTEX         hwmgr->msg_lock                        PROVEN   smumgr.c:165
CONEXIÓN CON INVALIDATE  centinela → poll           PROVEN   :142, :165
```

## 9. Fallos nominales de este bloque

| # | Busqué | Realidad |
|---|---|---|
| 29º | `PHM_WAIT_FIELD_UNEQUAL` en `powerplay/inc/*.h` | está en `powerplay/hwmgr/smu_helper.h:234` |
| 30º | `smu7_send_msg_to_smc_with_parameter` definido en `smu7_smumgr.c` con `{` en la misma línea | sí, pero `smu7_send_msg_to_smc_offset` la envuelve: el nombre "offset" no es un offset |

---

## Para el driver propio

```
1. antes de enviar: esperar a que RESP != 0        (estado ocioso)
2. escribir RESP = 0                              (armar)   <- no esta en la version legacy
3. escribir el argumento en mmSMC_MSG_ARG_0
4. escribir el mensaje en mmSMC_MESSAGE_0
5. esperar a que RESP != 0
6. leer RESP: 0x01 OK / 0xFE no soportado / otro fallo
7. NO comprobar el valor de retorno: siempre es 0
8. serializar con mutex si puede haber más de un hilo
```

Los puntos 2 y 7 son los que la versión legacy de SI no tiene, y ambos son
errores silenciosos: sin el 2 el handshake puede no armar; sin el 7 un fallo de
firmware pasa por éxito.