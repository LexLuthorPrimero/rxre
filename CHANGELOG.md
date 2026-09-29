# Changelog

## 2026-09-25 — consolidación final de la migración

### Documentación

- Añadidos `PATCH-REGISTRY-FINAL.md` y `PROBLEM-STATUS-FINAL.md` con una
  entrada por problema y estados explícitos.
- Añadidos `INSTALL.md`, `ROLLBACK.md`, `TESTING.md`, `RELEASE-CANDIDATE.md` y
  `FINAL-RELEASE-REPORT.md`.
- Añadida la instantánea read-only
  `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.{json,md}`.
- Documentado que el host actual es Nobara 43/kernel 6.18.2/Mesa 25.3.2 y que
  el backup histórico corresponde a otro entorno.

### Implementación estática

- `rx550-torneo` deja de usar fallback a `DRI_PRIME=1` para seleccionar la
  RX550; usa `vendor:device` y, si hace falta, BDF.
- Las pruebas de Fase 1 dejan de asumir `card0`, `card1`, `renderD129` o
  `hwmon2`.
- El runner M1 limpia `MESA_VK_DEVICE_SELECT` y `VK_DRIVER_FILES` heredados y
  fuerza el ICD RADV x86_64.
- El modo de prueba M1 usa estados auxiliares sintéticos, por lo que no depende
  de que el host tenga `power/control=on`.
- El detector de journal separa PRT, VM fault aislado, ring timeout y reset.
- Añadida `tools/validate_rx550_final.py`, que sólo lee y no ejecuta workloads.

### Pruebas

- C1: 54 tests OK, 1 skip.
- `rx550-torneo` Phase1: 64/64 checks.
- M1: 110/110 checks; `strace` quedó `NOT_AVAILABLE` y no se instaló.

### Estado

- No se aplicaron cambios de sistema, kernel, firmware, Mesa, servicios, udev,
  GRUB, VFIO, C1, DPM, PM o power cap.
- No se declaró una corrección de estabilidad, DPM causal, VFIO, C1, Kalm,
  RA24 o `VK_EXT_image_drm_format_modifier`.
- El release permanece condicionado a la revisión de seguridad, unresolved
  gates y autorización de remoto.
## [FECHA] - [VERSIÓN O TAG]
### Añadido
- [archivo]: [descripción breve de lo que se añadió]

### Cambiado
- [archivo]: [qué se cambió y por qué]

### Eliminado
- [archivo]: [qué se eliminó y por qué]

### Corregido
- [archivo]: [qué bug se corrigió]
## 2026-09-29 - v0.1.0-compresor
### Añadido
- 04-IMPLEMENTACION/compressor/: Librería de compresión de texturas en C + ASM x86_64
  - rx550_compress.h: Estructuras y prototipos
  - rx550_compress.c: Implementación en C puro
  - rx550_compress_avx2.s: Implementación en ensamblador AVX2
  - test_compress.c: Pruebas y benchmark
  - Makefile: Sistema de compilación
  - README.md: Documentación
