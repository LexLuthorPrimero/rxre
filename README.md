# RX550-INVESTIGACION

Investigación reproducible de una AMD Radeon RX 550 Polaris12/GFX8
(`1002:699f`, `amdgpu`) en un host Nobara/KDE. El proyecto separa evidencia,
hipótesis, correcciones de código, workarounds y estado de publicación.

## Estado actual

**Estado de consolidación:** `PARTIALLY_RESOLVED`
**Estado de la RX550:** `UNRESOLVED` para estabilidad y causalidad de DPM/PM.
**Publicación:** `READY_FOR_GITHUB=NO`.

La instalación validada es Nobara Linux 43, kernel
`6.18.2-200.nobara.fc43.x86_64`, Mesa `25.3.2`, LLVM `21.1.7`, libdrm `2.4.128`
y firmware `20251125`. La RX550 se identifica por PCI/BDF; en ese host es
`card2`, `renderD129` y `hwmon1`, pero esos números no son portables.

No se aplicaron cambios persistentes al sistema. No se ejecutaron benchmarks,
A/B, power-cap writes, C1 runtime, SMART, scrub, Btrfs write, VFIO, reset ni
servicio start/stop.

## Navegación documental

**[DOCUMENTATION-ROUTER.md](01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md)** es el
punto de entrada para cualquier pregunta sobre la documentación. Clasifica la consulta y da
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
- [RELEASE-CANDIDATE.md](RELEASE-CANDIDATE.md): gates de publicación.
- [FINAL-RELEASE-REPORT.md](FINAL-RELEASE-REPORT.md): informe de release y
  bloqueos actuales.
- [RELEASE-EXCLUSIONS.md](RELEASE-EXCLUSIONS.md): artefactos excluidos del árbol
  publicable y regla de preservación.
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
`RELEASE-CANDIDATE.md` antes de cualquier operación GitHub.
