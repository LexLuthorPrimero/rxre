# Release candidate — RX 550

**Candidate ID:** `RX550-FINAL-20260925`
**Fuente:** Nobara 43/kernel 6.18.2/Mesa 25.3.2, host `1002:699f`
**Modo de validación:** `READ_ONLY/EVIDENCE` más pruebas estáticas

## Campos obligatorios

```text
PROJECT_STATUS=PARTIALLY_RESOLVED
RX550_STATUS=UNRESOLVED
KNOWN_PROBLEMS=22
UNRESOLVED_PROBLEMS=KWin/Wayland/Intel separation; GPU stability; DPM/SCLK/MCLK causality; BACO/runtime PM; VFIO; C1/ownership/recovery
VALIDATED_FIXES=PCI identity detection; per-process DRI_PRIME=1002:699f; RADV ICD isolation; M1 detector/test-mode guards; W_SMU terminology
OBSOLETE_FIXES=Kalm causal attribution; Mesa CUSTOM causal attribution
EXPERIMENTAL_ITEMS=R-11 host-upload workload; any future DPM/PM/VFIO experiment
REPRODUCIBILITY=PARTIAL
SECURITY_REVIEW=NOT_READY
READY_FOR_GITHUB=NO
```

`KNOWN_PROBLEMS=22` cuenta las filas `RX550-01` a `RX550-22` de
`PROBLEM-STATUS-FINAL.md`; no significa que todos estén presentes en el host
actual.

## Qué está demostrado

- La GPU se identifica por PCI/BDF, no por `cardN`.
- `DRI_PRIME=1002:699f` selecciona la RX550 para un proceso; `DRI_PRIME=1`
  selecciona Intel en este host.
- El ICD RADV x86_64 devuelve `0x699f`.
- El detector de journal distingue PRT, VM fault aislado, ring timeout y reset.
- Las pruebas estáticas de C1, `rx550-torneo` y M1 pasan con los límites
  documentados; `strace` permanece `NOT_AVAILABLE`.
- No se aplicaron cambios persistentes al sistema.

## Qué no está demostrado

- No hay una campaign actual que cierre E1/E3/E5, DPM/SCLK/MCLK, BACO, PM,
  reset, ring timeout, VM fault o estabilidad bajo carga.
- KWin/Wayland sigue usando la RX550 como renderer mientras la salida es Intel.
- `VK_EXT_image_drm_format_modifier` no está disponible en el dispositivo GFX8
  validado; no se ha creado un parche para ocultarlo.
- RA24 no aparece en el journal del boot, pero no se ha cerrado una prueba de
  conmutación de formatos.
- R-11 no se revalidó en la instalación actual.
- VFIO, C1, ownership y restore siguen `UNRESOLVED`.
- El árbol histórico y el trabajo preexistente contienen rutas personales y
  artefactos generados; la higiene de publicación no está cerrada.

## Pruebas de aceptación

| Prueba | Resultado |
|---|---|
| C1 unit tests | 54 OK, 1 skip |
| rx550-torneo | 64/64 |
| M1 | 110/110; `strace` `NOT_AVAILABLE` |
| Validador final | `OBSERVED`, target encontrado |
| `git diff --check` | OK en los archivos revisados |
| Benchmarks/runtime C1/VFIO | no ejecutados |

## Commit, tag y publicación

```text
COMMIT=NOT_AVAILABLE
TAG=NOT_AVAILABLE
REMOTE=NOT_AVAILABLE
PUSH=NOT_AUTHORIZED_OR_NOT_READY
```

No se inventó un remoto. No se hizo push ni se publicó una release. La
publicación queda bloqueada por `SECURITY_REVIEW=NOT_READY`, problemas
abiertos y ausencia de remoto configurado.

## Criterio para cambiar a YES

1. cerrar o documentar definitivamente la revisión de seguridad y exclusiones;
2. obtener un remoto autorizado y verificar autenticación sin exponer secretos;
3. resolver o conservar explícitamente los problemas abiertos sin convertirlos
   en resoluciones;
4. repetir las pruebas estáticas y `git diff --check` sobre el árbol exacto que
   se publicará;
5. crear commit y tag sólo después de esas comprobaciones.
