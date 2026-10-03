# RX550-INVESTIGACION

Investigación reproducible de una AMD Radeon RX 550 Polaris12/GFX8
(`1002:699f`, `amdgpu`) en un host Nobara/KDE. El proyecto separa evidencia,
hipótesis, correcciones de código, workarounds y estado de publicación.

## Estado actual

**Estado de consolidación:** `PARTIALLY_RESOLVED`
**Estado de la RX550:** `UNRESOLVED` para estabilidad y causalidad de DPM/PM.
**Publicación:** `READY_FOR_GITHUB=NO`.

> **HOST ACTUALIZADO 2026-10-01 — este bloque estaba obsoleto.** Describe la instalación
> validada el 2026-09-25, que ya no es la de esta máquina. Verificado por lectura directa
> el 2026-10-01 11:0x: el host pasó a **Nobara Linux 44**, kernel
> **`7.1.3-200.nobara.fc44.x86_64`**, Mesa **`26.2.3`**. La RX550 sigue en
> `0000:01:00.0` pero es **`card1`**, no `card2`; `renderD129` y `hwmon1` sí coinciden.
> Los "43 / 6.18.2 / 25.3.2 / card2" de abajo son `HISTÓRICO`. Estado vigente y su
> evidencia: [`docs/CURRENT-STATE.md`](docs/CURRENT-STATE.md).

La instalación validada es Nobara Linux 43, kernel
`6.18.2-200.nobara.fc43.x86_64`, Mesa `25.3.2`, LLVM `21.1.7`, libdrm `2.4.128`
y firmware `20251125`. La RX550 se identifica por PCI/BDF; en ese host es
`card2`, `renderD129` y `hwmon1`, pero esos números no son portables.

No se aplicaron cambios persistentes al sistema. No se ejecutaron benchmarks,
A/B, power-cap writes, C1 runtime, SMART, scrub, Btrfs write, VFIO, reset ni
servicio start/stop.

## Navegación documental

### Estado actual del proyecto: [`docs/`](docs/MASTER-RESEARCH-STATUS.md)

**Empieza por ahí, no por el resto de este fichero.** El `README.md` describe la
línea de investigación de septiembre (telemetría DPM/PM, C1, publication). `docs/`
describe la línea que se está trabajando ahora: reconstrucción del hardware GFX8 y
driver propio.

```
docs/MASTER-RESEARCH-STATUS.md   índice. Qué está probado, qué no, qué está bloqueado
docs/CURRENT-STATE.md             el estado verificable de HOY, con su evidencia
docs/EVIDENCE-MATRIX.md           claim → fichero:línea → quién lo sostiene
docs/FINDINGS-INDEX.md            los 38 findings, con estado de versionado
docs/OPEN-FRONTIERS.md            11 fronteras con test discriminante
docs/CONTRADICTIONS.md            dos versiones del mismo hecho, y cuál manda
docs/NEGATIVE-RESULTS.md          qué se descartó y qué NO descarta
docs/TOOLS-STATUS.md              qué herramienta está validada y cuál no
docs/IMPLEMENTATION-STATUS.md    escrito ≠ compila ≠ ejecutado ≠ validado
docs/EXPERIMENTS.md               qué se ejecutó y qué no se debe repetir
docs/DECISIONS.md                 decisiones con motivo y reversibilidad
docs/CHANGELOG-RESEARCH.md        cambios de conocimiento, no de comandos
```

> El README de abajo y `00-INDICE/MASTER-RESEARCH-STATUS.md` conservan el historial
> R-4B/D6 de septiembre. No son estado actual y no se borran.

**[DOCUMENTATION-ROUTER.md](01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md)** es el
punto de entrada para cualquier pregunta sobre la documentación de esa línea. Clasifica la consulta y da
la fuente primaria de los 68 temas, con su temporalidad y su host. Un índice histórico de este
repositorio tiene 1576 entradas y solo 16 son actuales: el router existe para no tener que
recorrerlo entero.

## Documentos finales

- [PATCH-REGISTRY-FINAL.md](PATCH-REGISTRY-FINAL.md): registro de correcciones,
  procedimientos, hashes, validación y rollback.
- [PROBLEM-STATUS-FINAL.md](PROBLEM-STATUS-FINAL.md): matriz de problemas y
  estados permitidos.
- [INSTALL.md](INSTALL.md): requisitos, paquetes, selectores y límites.
- [ROLLBACK.md](ROLLBACK.md): rollback y recuperación sin cambios persistentes.
- [TESTING.md](TESTING.md): pruebas estáticas y criterios de aceptación.
- [ESTADO.md](ESTADO.md): **documento único de estado**. Incluye los gates de
  publicación (`READY_FOR_GITHUB=NO`, `SECURITY_REVIEW=NOT_READY`), el informe de
  release, los bloqueos actuales y los artefactos excluidos del árbol publicable.
  Consolida los que antes eran `RELEASE-CANDIDATE.md`, `FINAL-RELEASE-REPORT.md` y
  `RELEASE-EXCLUSIONS.md`, movidos a `archive/documentacion-compactada-20261003/`.
- [Captura JSON](01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json)
  y [informe legible](01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.md).

## Estructura

```text
00-INDICE/          índices, estados y decisiones
01-AUDITORIA/       auditorías, gates, VFIO, C1 y validación final
02-ARQUITECTURA/    arquitectura, hardware y conocimiento
03-EXPERIMENTOS/    experimentos, resultados y R-11
04-IMPLEMENTACION/  herramientas, C1 y rx550-torneo
05-FUENTES-EXTERNAS/ fuentes, Mesa y referencias
tools/              utilidades read-only y validación
```

El índice histórico permanece en [00-INDICE/README.md](00-INDICE/README.md) y
[00-INDICE/MASTER-RESEARCH-STATUS.md](00-INDICE/MASTER-RESEARCH-STATUS.md). Las
referencias a backups, `cardN` y antiguos kernels son provenance histórica, no
instrucciones operativas.

## Reproducir la validación

Desde la raíz, sin privilegios y sin cambiar el sistema:

```bash
python3 tools/validate_rx550_final.py
PYTHONDONTWRITEBYTECODE=1 python3 04-IMPLEMENTACION/rx550-torneo/tests/run_tests.py
PYTHONDONTWRITEBYTECODE=1 python3 04-IMPLEMENTACION/rx550-torneo/tests/run_tests_m1.py
python3 -m unittest discover -s 04-IMPLEMENTACION/tests -p 'test_*.py'
```

Resultados de la consolidación: C1 `54` tests OK con `1` skip; rx550-torneo
`64/64`; M1 `110/110` con `strace` `NOT_AVAILABLE`. La ausencia de `strace` no
se cuenta como PASS.

## Reglas de seguridad

- No usar `sudo` para diagnóstico.
- No escribir `/sys`, PM, DPM, power cap, governors, IRQ, scheduler o
  almacenamiento.
- No modificar GRUB, initramfs, udev, módulos, servicios, firmware o VBIOS.
- No ejecutar C1, `run_c1()`, benchmarks o A/B sin autorización runtime
  separada.
- No declarar `RESOLVED` un problema por el hecho de que el escritorio
  arranque.
- No publicar secretos, cookies, logs personales, rutas privadas, binarios ni
  dumps innecesarios.

## Git

La rama observada es `main`. No hay remoto configurado, no se inventó una URL y
no se hizo push. El commit/tag final permanece `NOT_AVAILABLE` hasta cerrar la
revisión de seguridad, el árbol publicable y los problemas abiertos. Consulte
`ESTADO.md` antes de cualquier operación GitHub.
