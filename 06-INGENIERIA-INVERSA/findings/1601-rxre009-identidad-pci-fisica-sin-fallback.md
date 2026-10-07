# 1601 — RXRE-009: la identidad física no puede salir del primer AMD ni de un fallback

```text
CLASSIFICATION=ERROR_REPRODUCIDO+REPARACION_VALIDADA_EN_FIXTURE
WORK_CLASS=RXRE-009-DOGFOODING
AUTOR=AGENTE_RXRE009 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f · rev c7 · subsystem 1002:0b04
WRITE_EXECUTION=SOLO_FICHEROS_DE_HERRAMIENTA_Y_TEST_EN_/home/lucas/Escritorio/rxre
MODIFICATIONS=tools/rxre/core/target.py; tools/rxre/tests/test_target_identity009.py;
              tools/rxre/tests/mutate_target_identity009.py; este hallazgo
RUNTIME=LECTURA_SYSFS_DE_0000:01:00.0; NO_GPU_MMIO; NO_INTEL; NO_DRIVER_BIND
```

## Pregunta y discriminante

¿`get_current_target()` observa la función PCI y revisión de esta RX550, o rellena la identidad desde un supuesto cuando falla la detección? Si falta el nodo PCI, **None**, no RX550 c7; con otro AMD presente, el único nodo elegible es `0000:01:00.0`; con `revision` ausente, `unknown` explícito y sin routing físico.

PRECONDITION: árbol de evolución `/home/lucas/Escritorio/rxre`, fuente `tools/rxre/core/target.py` SHA256 inicial `356c253b258736584145205452957b8a45d16be995b8e19438fa087bf14998c1`, snapshot externo no modificado. ACTION: ejecutar API real de RXRE, inspeccionar productor y prueba P1, añadir oráculo con sysfs falso, reparar ese productor, ejecutar tests y mutaciones aisladas. ACCEPT: BDF/revisión observados, fallo de detección sin identidad sintética, fixture verde, mutantes válidos muertos. FAIL: distinto valor o un superviviente. INVALID: suite no se importa, test solo valida su propia lógica, o mutación no importa. NEXT STATE: `TARGET_FINGERPRINT` deja de aceptar fallback; integración en CLI queda abierta.

## Evidencia antes del cambio

- `tools/rxre/core/target.py` leía `os.listdir('/sys/bus/pci/devices')`, seleccionaba el primer vendor `0x1002`, ponía `revision='unknown'` y `get_current_target()` devolvía RX550 `c7` fabricada si la detección fallaba. `TargetIdentity` no tenía BDF ni subsystem.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B` importando `core.target`: en esta máquina devolvió `1002:699F`, `revision=unknown`, `is_unknown=True`; al forzar `_get_target_from_pci -> None`, devolvió `1002:699F`, `revision=c7`, `is_unknown=False`, con provenance etiquetada `FALLBACK`.
- Oráculo independiente: lectura de `/sys/bus/pci/devices/0000:01:00.0/{vendor,device,revision,subsystem_vendor,subsystem_device}` dio `0x1002,0x699f,0xc7,0x1002,0x0b04`. No se leyó ni escribió el dispositivo Intel.
- `test_p004.py` pasaba con `PYTHONPATH=tools/rxre` antes de reparar, aunque no comprobaba BDF/revisión. Invocarlo sin esa variable falló en import `core`: fallo del harness registrado, no una prueba de que el target fuese incorrecto.

## Reparación y límites

`_get_target_from_pci(root)` ahora lee exclusivamente `root/0000:01:00.0` y los cinco campos del dispositivo. Si falta función o divergen vendor/device/revisión/subsystem conocidos, retorna `None`. Si se leen vendor/device pero faltan revisión o subsystem, conserva `unknown` en `TargetIdentity`, registra `NOT_OBSERVED` con ruta sysfs y no habilita capacidades físicas. `get_current_target(root)` ya no devuelve una RX550 fabricada; BDF y subsystem forman parte del dato. Las identidades sintéticas sin BDF que usan tests de routing estático continúan posibles, pero **no autorizan hardware**.

Este cambio prueba identidad **PCI en sysfs**, no que la GPU ejecute semántica GFX8; `Polaris12/gfx_8_0` sigue siendo un mapping de código, no una lectura de IP hardware. La API `core.target` aún no aparece como consumidor en `api/machine.py` ni en `cli.py` (búsqueda de símbolo restringida a `tools/rxre/**/*.py` encontró solo los tests): **HUECO_DE_CONEXIÓN** para query pública, no debe anunciarse el routing de toda RXRE como corregido.

## Validación / contraejemplos

- `test_target_identity009.py`: 5 pruebas con nodos sysfs falsos en `/tmp/opencode`; cubren AMD anterior, BDF correcto, revisión observada, detección ausente, revisión incorrecta/ausente y subsystem incorrecto. Antes del parche: un FAIL de fallback y tres TypeError por interfaz sin root inyectable. Después: 5/5 verdes.
- `test_p004.py` con `PYTHONPATH=tools/rxre`: seis grupos verdes antes y después; su verde previo **no** era evidencia suficiente de fingerprint.
- `PYTHONPATH=tools/rxre python3 -B -m core.target`: `TARGET SELF-TEST PASSED` sobre esta host. La invocación directa por ruta falla por relative import; no usarla como resultado.
- `mutate_target_identity009.py`: baseline verde; seis mutaciones AST válidas/importables, ejecutadas en copias temporales, seis con fallo de aserción y **cero supervivientes**: fallback, BDF erróneo, revisión inventada, provenance de faltante omitida, subsystem ignorado y routing de identidad parcial. El antiguo `tools/mutate_target.py` contiene `RAIZ` del snapshot anterior y escribe en su target: **no fue ejecutado**.
- Reuso de la API real: `TargetIdentity(bdf='0000:01:00.0', vendor='1002', device='699f', revision='c7', subsystem='1002:0b04', provenance de cinco ficheros sysfs); is_unknown=False; get_capabilities_for_target` devolvió 11 candidatos. Son capacidades **relevantes estáticamente**, no comportamiento de hardware validado.

## Estado y próxima acción

BUG de selección/fallback y provenance física: reproducido y reparado para la API local; `RELATION/RXRE_PUBLIC_ROUTING`: `PARTIAL`, porque ningún consumidor de CLI/machine usa aún `get_current_target`. La siguiente pregunta causal RX550 será **qué índice representa `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR` y cómo llega al flush de VMID8**. Primero invocar `RXRE register`, después comparar literalmente `gmc_8_1_d.h`, `gmc_v8_0.c`, `findings/1588` y `findings/1600` de ESTE árbol. Nada de MMIO, display, fb0, i915 ni reset.
