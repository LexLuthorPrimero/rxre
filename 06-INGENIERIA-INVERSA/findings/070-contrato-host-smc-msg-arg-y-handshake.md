# 070 · El contrato host↔SMC de Polaris12: handshake, wire format y semántica de respuesta

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

F3b declaraba abierta esta parte: *"¿Qué mensajes existen, con qué formato, en
qué SRAM, y qué respuesta da?"*. Eso no lo había cerrado nadie.

**Respuesta: el contrato no está en SRAM del host. Son tres registros MMIO y un
handshake de tres estados.** Y el `argument` está en `0xa4`, que no aparecía en
la documentación previa.

## Nota de método primero, porque casiPublish sin revisar

`polaris10_smumgr.c` **no está en `drivers/gpu/drm/amd/amdgpu/`**. Está en
`drivers/gpu/drm/amd/pm/powerplay/smumgr/`. Busqué primero en la ruta de `amdgpu/`
—que es donde vive todo lo demás que he rastreado— y concluí que el fichero no
existía. No existía en esa ruta, y la frontera lo daba por verificado.

Es la segunda vez en dos iteraciones que la ruta de búsqueda, no el contenido, me
da una ausencia falsa. La primera fue la cabecera equivocada (`mmhub` por `gmc`).
La diferencia es que aquí el fallo es de un árbol que no es el que uno está
mirando, y por eso `regdb.py` y `hdrmap.py` llevan rutas completas en su salida:
para que un `NAME_NOT_FOUND` venga con la ubicación y no sea una conclusión.

## El handshake: cómo sabe el host que el firmware vive

```
polaris10_smumgr.c:235   PHM_WAIT_VFPF_INDIRECT_FIELD_UNEQUAL(hwmgr, SMC_IND,
                                                                SMU_STATUS, SMU_DONE, 0)
polaris10_smumgr.c:237   if (1 != PHM_READ_VFPF_INDIRECT_FIELD(..., SMU_STATUS, SMU_PASS))
polaris10_smumgr.c:239       PP_ASSERT_WITH_CODE(false, "SMU Firmware start failed!", return -1);
polaris10_smumgr.c:250   PHM_WAIT_VFPF_INDIRECT_FIELD(hwmgr, SMC_IND,
                                                        FIRMWARE_FLAGS, INTERRUPTS_ENABLED, 1)
```

Tres condiciones, en orden, y cada una con su campo:

| campo | qué significa |
|---|---|
| `SMU_DONE` | el firmware terminó de arrancar. `WAIT_UNEQUAL 0` = esperar a que pase de 0. |
| `SMU_PASS` | el arranque terminó **bien**. Si no es 1, el host aborta con assert. |
| `INTERRUPTS_ENABLED` | el firmware ya accepts interrupciones. Es la condición de "listo para hablar". |

`SMU_DONE` **sólo se lee, nunca se escribe**, en las cuatro familias de ASIC que
lo tienen (`polaris10`, `tonga`, `fiji`, `vegam`), con 4 sitios y 4 lecturas. Eso
es la prueba de que la dirección es del firmware: **el host jamás puede
convencer al firmware de que está listo.**

## El wire format del mensaje

```
smu7_smumgr.c:135   PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, SMC_RESP, 0);
smu7_smumgr.c:145   cgs_write_register(hwmgr->device, mmSMC_RESP_0, 0);
smu7_smumgr.c:146   cgs_write_register(hwmgr->device, mmSMC_MESSAGE_0, msg);
smu7_smumgr.c:148   PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, SMC_RESP, 0);
smu7_smumgr.c:165   cgs_write_register(hwmgr->device, mmSMC_MSG_ARG_0, parameter);
```

Secuencia, y es un protocolo de reserva con reserva: el host espera a que el canal
esté libre, lo ocupa, y espera a que el firmware lo libere.

1. **esperar** a que `SMC_RESP` valga 0 (el SMC está libre)
2. **poner a 0** `SMC_RESP` (reclamar el canal)
3. **escribir** `SMC_MESSAGE_0` con el código de mensaje
4. **esperar** a que `SMC_RESP` vuelva a 0 (el SMC terminó)

Con parámetro (`smu7_send_msg_to_smc_with_parameter`), el parámetro se escribe
**antes**, en `mmSMC_MSG_ARG_0`, y luego se llama al envío sin parámetro.

Los offsets, de `smu_7_1_3_d.h`, la cabecera Polaris12:

```
  smu_7_1_3_d.h:97    mmSMC_MESSAGE_0    0x94     el mensaje
  smu_7_1_3_d.h:98    mmSMC_RESP_0       0x95     la respuesta
  smu_7_1_3_d.h:113   mmSMC_MSG_ARG_0    0xa4     el parámetro
```

F3b ya tenía `0x94` y `0x95` verificados. **`0xa4` no estaba**, y es la pieza que
falta para usar el canal: sin él no se puede enviar un mensaje con argumento, y
`smu7_send_msg_to_smc_offset` lo usa precisamente así.

## La semántica de la respuesta

```
smu7_smumgr.c:139   if (ret == 0xFE)      "last message was not supported"
smu7_smumgr.c:141   else if (ret != 1)     "last message was failed ret is %d"
smu7_smumgr.c:152   if (ret == 0xFE)      "message %x was not supported"
smu7_smumgr.c:154   else if (ret != 1)     "failed to send message %x ret is %d"
```

**Tres estados, no dos:**

| `SMC_RESP` | significado |
|---|---|
| `1` | éxito |
| `0xFE` | **el firmware no conoce ese mensaje**. No es un fallo: es un mensaje inválido para esta versión de firmware. |
| otro | fallo real del mensaje |

`0xFE` es lo que hace que el canal sea **extensible sin cambiar el host**: un
firmware nuevo puede reconocer mensajes que un host nuevo le manda, y ambos
lados toleran que el otro no conozca un código. Es un protocolo con
versionado implícito por respuesta.

Y hay una asimetría que importa: **`smu7_send_msg_to_smc` devuelve 0 siempre**
(`smumgr/smu7_smumgr.c:158`). El fallo se registra con `dev_dbg`/`dev_info` pero **no
propaga**. El único punto que aborta de verdad es el handshake de arranque
(`smumgr/polaris10_smumgr.c:239`), y ése es el único `PP_ASSERT`.

**Consecuencia para un driver propio**: un mensaje de reloj que el firmware
rechace no devuelve error. Se registra y se sigue, y el valor de reloj aplicado
será el anterior. Sin leer `SMC_RESP` explícitamente, un driver propio no puede
saber si su petición surtió efecto.

## El juego de mensajes

```
  48 códigos PPSMC_MSG_ distintos en el árbol
```

`PPSMC_MSG_Test` es el primero que usa la función de handshake
(`smumgr/smu7_smumgr.c:177`), con parámetro `0x20000`.

**El enum completo no lo transcribo aquí.** 48 entradas serían 48 líneas de dato
que una herramienta debe producir, no un hallazgo escrito a mano: es exactamente
lo que hace `toolaudit.py` con los titulares. Queda como pendiente de
extracción, no como neglecto.

## Lo que esto NO cierra

| Afirmación | Estado |
|---|---|
| Los 3 registros y sus offsets | `PROVEN` (`smu/smu_7_1_3_d.h:97`) |
| El handshake de 3 campos del arranque | `PROVEN` (`polaris10_smumgr.c:235-250`) |
| `SMU_DONE`/`SMU_PASS` sólo se leen | `PROVEN` (4 familias, 4 lecturas, 0 escrituras) |
| El wire format en 4 pasos | `PROVEN` (`smu7_smumgr.c:135-148`) |
| `0xFE` = mensaje no soportado | `PROVEN` (`smumgr/smu7_smumgr.c:139, :152`) |
| El envío no propaga error | `PROVEN` (`return 0` en L158) |
| Los 48 códigos de mensaje | `PROVEN` (existen) |
| Qué **hace** el firmware con cada mensaje | `NOT_DETERMINED` — es firmware |
| Qué reloj aplica cada mensaje | `NOT_DETERMINED` — está en el blob |

Y sigue en pie lo que 046 ya établir: el modelo real son **tablas de voltaje por
dominio** (`populate_smc_{mvdd,vddc,vddci}_table`, `smumgr/polaris10_smumgr.c:664`),
no curvas de histéresis con histeresis. Esta nota no cambia eso: describe el
**canal**, no la política de voltaje que viaja por él.

## Procedencia

- `CORPUS` — `pm/powerplay/smumgr/{smu7_smumgr,polaris10_smumgr}.c`,
  `include/asic_reg/smu/smu_7_1_3_d.h`.
- Herramientas: `xref.py` (4 sitios de `SMU_DONE`, todos lectura), `regdb.py`
  (cabecera y línea), `hdrmap.py` (que el fichero es de la ruta `pm/powerplay`).
- Sin `RUNTIME`, sin lectura de la GPU, sin escrituras.
- No se editó `OPEN-FRONTIERS.md` ni `046`: son de otras sesiones
  (`COORDINACION.md:184`). Se informa.