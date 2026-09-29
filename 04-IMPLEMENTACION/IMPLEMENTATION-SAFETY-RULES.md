# IMPLEMENTATION-SAFETY-RULES.md — Reglas de seguridad de implementación

**Ubicación canónica:** `04-IMPLEMENTACION/`
**Estado:** reglas documentales; no otorgan autorización de escritura.

## Frontera absoluta

No se modifica, escribe ni restaura por iniciativa propia ninguno de estos elementos:

- `power1_cap`, DPM, SCLK/MCLK, `pp_power_profile_mode`, `ppfeaturemask` o sysfs equivalente.
- Kalm (`kalmd`, `kalm-lite`, `kalm-gpu.service`) o configuración de servicios.
- Mesa del sistema, `/opt/mesa-*`, kernel, GRUB, DRM/AMDKMS, BIOS/VBIOS o firmware.
- `WORKLOAD-SINTETICO`, sus shaders, Makefile, workloads o resultados congelados.
- Set H, sus scripts, hashes, contenido o mtimes.
- Logs, manifiestos, JSON de corrida, `frozen.sha256` y artefactos de los 388 power sweeps.

## Selección de dispositivo Vulkan

La evidencia local es divergente: `MESA_VK_DEVICE_SELECT=1002:699f` no se acepta como
prueba de selección. Usar ICD RADV y verificar explícitamente `0x699f` en cada corrida;
el selector numérico es opcional y solo puede conservarse si esa verificación pasa.

## Antes de cualquier acción futura autorizada

1. Identificar la fase, el objetivo, la variable independiente y el criterio de éxito.
2. Localizar la evidencia fuente y los hashes de precondición.
3. Hacer snapshot **read-only** del estado que se vaya a observar.
4. Definir rollback, readback y condición de abort.
5. Confirmar que la acción no altera Set H ni los elementos congelados.
6. Pedir autorización explícita para la acción concreta; este documento no la concede.

## Clasificación de acciones

| Clase | Ejemplo | Estado |
|---|---|---|
| R | Lectura de estado, telemetría y análisis de artefactos existentes | Permitida solo dentro del alcance autorizado |
| D | Diseño/documentación sin ejecutar | Separada de toda escritura |
| W | Escritura en sysfs, Mesa, firmware, counters o servicios | **NO AUTORIZADA** por este documento |
| X | Ejecución de scripts, benchmarks o código descargado | **NO AUTORIZADA** por este documento |

## Abort y preservación

- Si aparece una desviación inesperada, una parada, un reset, un error de ownership o una
  pérdida de hash: no reintentar; conservar el estado y registrar el incidente.
- No borrar ni renombrar evidencia para simplificar una auditoría.
- No sustituir una ruta histórica por una ruta inventada; marcarla como
  **HISTÓRICO / NO VERIFICABLE** cuando corresponda.
- No reconstruir artefactos temporales perdidos de `/tmp`.
- No elevar un resultado a `VALIDADO` o `SUPPORTED` sin la muestra y los gates definidos.

## R-4B

R-4B v2.3 queda **INCONCLUSO / INCONCLUSIVE**: S1-v2.3 se ejecutó/completó y S2-v2.3
quedó PARADA D antes de Phase 2. No se reintenta S2, no se reconstruye telemetría temporal
y no se declara `SUPPORTED`. T9 (`/tmp/opencode/ep06_base.txt`) pertenece a Set H y no se
toca bajo ninguna circunstancia.

## H12

H12 permanece `REQUIRES CAPABILITY AUDIT`; no se diseña ni ejecuta hasta confirmar WSI,
present timing, extensions, queues y telemetría local en una fase documental separada.

## Referencias

- `IMPLEMENTATION-ROADMAP.md` (misma carpeta).
- `00-INDICE/MASTER-RESEARCH-STATUS.md` (estado vivo).
- `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-READINESS-AUDIT.md` (auditoría;
  sus documentos auxiliares canónicos están en esta carpeta).
