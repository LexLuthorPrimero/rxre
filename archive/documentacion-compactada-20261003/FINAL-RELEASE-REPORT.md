# Informe final de release — RX 550

**Candidate:** `RX550-FINAL-20260925`
**Fecha:** 2026-09-25
**Modo:** consolidación documental y validación read-only
**Estado Git observado:** rama `main`, sin remoto, commit base
`c6146788e0d4fb12d9b0ec1209fa2840692de0c5`.

Este informe no declara una release final. `READY_FOR_GITHUB=NO`.

## Respuestas requeridas

### 1. ¿Está todo el trabajo histórico consolidado y trazable?

Sí, para la documentación disponible: los problemas y estados están en
`PATCH-REGISTRY-FINAL.md` y `PROBLEM-STATUS-FINAL.md`; la captura actual está
en `01-AUDITORIA/FINAL-VALIDATION/`. La evidencia que no existe o no tiene
fuente suficiente queda `NOT_AVAILABLE`, `UNKNOWN` o `UNRESOLVED`.

### 2. ¿Qué correcciones eran necesarias y se han migrado?

- Detección de RX550 por PCI/BDF y pruebas sin `cardN` fijo.
- Selector GL por `DRI_PRIME=1002:699f` en el proceso, sin fallback a `1`.
- ICD RADV x86_64 y limpieza de selectores heredados en M1.
- Guardas y detector de journal más conservador.
- Documentación de la corrección R-11 como workaround de workload.

No se aplicó una corrección de kernel, firmware, DPM, PM, KWin, VFIO o C1.

### 3. ¿Qué correcciones históricas eran necesarias pero no se migraron?

La build Mesa CUSTOM y el parche RADV de logging no se migraron al sistema:
no eran necesarios para arrancar y no resolvieron el régimen histórico. Los
workarounds Mesa ya incorporados upstream no se duplican localmente. VFIO,
C1, BACO, DPM y RA24 no se implementaron por falta de validación o hardware.

### 4. ¿La instalación actual tiene las correcciones y sus pruebas?

La instalación actual tiene paquetes de distribución y los procedimientos
documentados. Las pruebas estáticas pasan: C1 `54` (1 skip), `rx550-torneo`
`64/64`, M1 `110/110` (`strace` `NOT_AVAILABLE`). Eso demuestra el contrato de
herramientas, no una reparación física del controlador.

### 5. ¿Qué problemas quedan abiertos o sin verificar?

Quedan abiertos la estabilidad bajo carga, reset/ring timeout/VM fault bajo
carga, DPM/SCLK/MCLK y sus causas, BACO/runtime PM, separación KWin/Wayland/Intel,
RA24 bajo una prueba específica, R-11 en Mesa actual, VFIO, C1/ownership/recovery,
salud HDD/Btrfs y la disponibilidad de `VK_EXT_image_drm_format_modifier` para
el caso que motivó la búsqueda.

### 6. ¿Hay algún cambio persistente aplicado al sistema?

No. No se usaron `sudo`, no se escribieron nodos `/sys`, no se cambiaron
servicios, GRUB, initramfs, udev, Mesa, firmware, VBIOS, DPM, PM, power cap,
Kalm, autopilot, C1, VFIO ni almacenamiento.

### 7. ¿Hay algo instalado que convenga eliminar?

La instalación actual no contiene Mesa CUSTOM bajo `/opt`; no se quitó ningún
paquete del sistema. En el repositorio hay un instalador de benchmark de
193 MB y una descarga parcial de 34 MB que no son necesarios para publicar y
quedan señalados para exclusión. No se eliminaron automáticamente para no
destruir evidencia local.

### 8. ¿Hay commits sin documentar o cambios pendientes?

El árbol tenía 135 archivos modificados y numerosos artefactos sin trackear
antes de esta consolidación. La nueva validación registra `worktree_entries`
sin publicar nombres. La lista exacta y la exclusión de logs/build artefacts
deben revisarse antes de un commit público. No se hizo un commit final.

### 9. ¿Se detectó algún secreto, token, cookie o clave privada?

No se encontraron claves privadas, tokens GitHub/GitLab, claves AWS ni
asignaciones de contraseña en la revisión de alta confianza. Sí hay rutas
personales, logs históricos, manifiestos y datos generados; por eso
`SECURITY_REVIEW=NOT_READY` y `READY_FOR_GITHUB=NO`.

### 10. ¿Se eliminaron datos personales innecesarios?

No de forma destructiva. Se preservó la evidencia local y el historial. Se
documentaron la exclusión de dumps, binarios, logs con rutas y artefactos de
build para una siguiente limpieza de publicación. No se deben subir archivos
con rutas personales o logs completos.

### 11. ¿Se revisaron los archivos grandes y `.gitignore`?

Sí: se identificaron `GravityMark_1.89.run` (193 MB) y
`Unigine_Superposition-1.1.run.partial` (34 MB), además de logs y builds. La
`.gitignore` y `RELEASE-EXCLUSIONS.md` los excluyen del árbol publicable; la
limpieza del índice conservando la evidencia local fue aplicada, pero el
historial baseline conserva los artefactos.

### 12. ¿`git diff --check` está limpio?

`git diff --check` pasó para los archivos modificados revisados en esta fase.
Debe repetirse sobre el árbol exacto que se decida publicar después de limpiar
o clasificar los artefactos pendientes.

### 13. ¿Qué pruebas se ejecutaron y qué resultado tuvieron?

- `python3 -m unittest discover -s 04-IMPLEMENTACION/tests -p 'test_*.py'`:
  54 OK, 1 skip.
- `04-IMPLEMENTACION/rx550-torneo/tests/run_tests.py`: 64/64.
- `run_tests_m1.py`: 110/110; `strace` `NOT_AVAILABLE`.
- `python3 -m py_compile` de los módulos modificados: OK.
- `tools/validate_rx550_final.py`: target `1002:699f` encontrado, sin escrituras.
- No se ejecutaron benchmarks, A/B, C1 runtime, SMART, scrub, Btrfs write, reset
  ni pruebas invasivas.

### 14. ¿Cuál es el estado de preparación para GitHub y por qué?

`READY_FOR_GITHUB=NO`. La razón principal es la seguridad/higiene del árbol y
la ausencia de un remoto configurado; además, hay problemas abiertos que sólo
pueden publicarse como `UNRESOLVED`, no como resoluciones. No se inventó una
URL ni se hizo push.

### 15. ¿Qué commit representa el estado final y existe tag?

Actualmente no hay commit final ni tag de release: `COMMIT=NOT_AVAILABLE` y
`TAG=NOT_AVAILABLE`. El commit base observado es
`c6146788e0d4fb12d9b0ec1209fa2840692de0c5`. Si se supera el gate de seguridad y
se autoriza un remoto, se puede crear un commit y un tag RC; no se debe
publicar una release `v1.0.0-rx550-final` mientras el gate siga en `NO`.

## Resumen ejecutivo

La parte más importante de esta migración es negativa: la instalación nueva
arranca con Mesa/kernel de distribución y la identidad de RX550 puede
comprobarse, pero no hay evidencia para declarar resueltos el régimen histórico,
la estabilidad, DPM/PM, KWin/Wayland, VFIO o C1. El JSON histórico
`resultados_etapa2.json` se excluyó del árbol publicable porque mezcla JSON y
texto y no valida como JSON. La documentación y las herramientas sí quedan
listas para que una persona autorizada continúe con limpieza, pruebas runtime y
publicación.
