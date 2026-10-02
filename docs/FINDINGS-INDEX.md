# FINDINGS-INDEX — el índice que resuelve las colisiones

> `06-INGENIERIA-INVERSA/findings/` tiene **40 índices duplicados**. El índice numérico
> no es un mecanismo de exclusión y no lo es entre sesiones que nunca se ven: se
>Aqustó dos veces el 2026-10-01 (`NR-10`). Este fichero es la respuesta: **cada
> finding se cita por su nombre completo**, que es único.
>
> `GENERADO 2026-10-01 12:15 -03:00` · `ACTUALIZADO 12:35` · método: `ls` +
> `git ls-files` + lectura de la cabecera de cada fichero. **Re-generar antes de citar**:
> el árbol crece varias veces por hora.

## Por qué este fichero y no un renombrado

Renombrar `021-a.md` y `021-b.md` a `021a` y `021b` sería la solución limpia, y es de
las sesiones que escribieron esos ficheros: son trabajo suyo, y `COORDINACION.md:184`
es *informa, no arregles*. Además, renombrar rompe las referencias `CONTINUES=` que
hay dentro de los propios findings. Un índice no rompe nada y da lo mismo.

## Cómo citar un finding

```
BIEN   021-frame-budget-gfx8-peor-caso        (completo, o el prefijo inequívoco)
MALO   "el 021"                               (hay ocho: 001, 010, 021, 023, 024,
                                                025, 026, 027 están duplicados)
```

## Los 24 índices duplicados

| Índice | Ficheros | Tema |
|---|---|---|
| `001` | `001-amdgpu-location.md` · `001-amdgpu-overview.md` | Dónde está el módulo, y qué exporta |
| `010` | `010-integration-validation.md` · `010-pgm-rsrc1-decoded.md` | Validación de integración, y un blob decodificado |
| `021` | `021-frame-budget-gfx8-peor-caso.md` · `021-write-lock-scoped-subdir-does-not-block.md` | Presupuesto del frame, y un defecto del protocolo de cerrojo |
| `023` | `023-pm4-count-convencion-medida.md` · `023-pte-productor-sdma-gfx8.md` | Convención de encoding, y el productor de PTE |
| `024` | `024-page-table-geometria-gfx8.md` · `024-pm4dw-herramienta-conteo-emision.md` | Geometría del page table, y la herramienta de conteo |
| `025` | `025-gart-invalidate-con-orden-cpu.md` · `025-vm-flush-path-gfx8-63dw.md` | La ruta GART, y la ruta de vm-flush |
| `026` | `026-pte-encoding-gfx8.md` · `026-frame-completo-gfx8-121dw.md` | Encoding del PTE, y el frame completo |
| `027` | `027-ptba-produccion-gfx8.md` · `027-write-multiple-resuelto.md` | Producción del PTBA, y el censo de `write_multiple` |
| `028` | `028-fence-completion-orden-d.md` · `028-emit-frame-size-justificado.md` | Completion del fence, y por qué 172 dw es la reserva correcta |
| `029` | `029-release-mem-y-eop-exec-muerto.md` · `029-orden-validacion-fence-no-ring.md` | `RELEASE_MEM` sin campo de número, y el orden de validación del fence |
| `030` | `030-writeback-buffer-wb-slots.md` · `030-page-walker-gfx8-2-niveles.md` | Writeback buffer, y page walker. **Se contradicen sobre `block_size`** |
| `033` | `033-protections-opaco` · `033-pm4-spec-gfx8-no-existe` · `033-mmu-vm-no-publicado` | **TRES findings con el mismo índice.** `PROTECTIONS` opaco · la spec PM4 que no existe · el bloque MMU/VM que tampoco |
| `035` | `035-block-size-tres-claims-y-un-log.md` · `035-correccion-ptepde-es-polaris12.md` | Un arbitra `block_size`; el otro lo equivoca. **Un hallazgo del proyecto contradice a otro del mismo número** |

**Son 24, y eran cuatro al empezar esta ronda.** `001 010 021 023 024 025 026 027 028 029 030 031 032 033 034` — a este ritmo la mitad del directorio comparte índice con alguien. Empeoran cada ronda mientras no se
renombre. Las dos últimas apariciones son `029-orden-validacion-fence-no-ring` y
`028-writeback-*`, ambas con posterioridad a este fichero.

## Los ocho caminos de colisión, y el patrón

```
1  el índice se elige "el siguiente libre por orden"   -> dos sesiones eligen el mismo
2  el nombre del finding se elige por el tema, no por
   el índice -> dos temas distintos pueden pedir el mismo número
3  una sesión renumera sus findings y choca con los
   de otra que yaSdkhavía usado ese número                 -> caso de 022 -> 023
4  el índice no se comprueba porque git status no sirve
   como árbitro                                            -> COORDINACION.md:15-19
```

El mecanismo de exclusión del protocolo (`mkdir` sobre un directorio) protege contra
dos sesiones que compiten por **el mismo nombre de lock**, nunca contra un ancestro, y
tampoco contra dos que eligen el mismo índice dentro de un directorio que ninguna ha
bloqueado. `NR-10` tiene la reproducción.

## Corrección propuesta, y por qué no la aplico

La mínima: `mkdir .write-lock/findings` **antes** de escribir un finding, y comprobar
que no existe. Convierte el índice en turno. Con tres sesiones que escriben findings
cada pocas horas, y con las colisiones ya duplicadas, es lo que de verdad impediría la
octava.

No la aplico: `COORDINACION.md` es ley operativa y cambiarlo requiere decisión humana.
Es la frontera `F10`, y es la acción más barata de arreglar y la más cara de no
arreglar del proyecto entero.

---

# Catálogo completo

`TRACKED` = versionado en git. `UNTRACKED` = **sólo en disco**: un `git clean -x` lo
borra sin dejar rastro. Hay 9 findings sin versionar y todos sostienen afirmaciones
`PROVEN`.

| # | Finding | Tema | Estado | Sostiene |
|---|---|---|---|---|
| 001 | `001-amdgpu-location.md` | Ubicación del módulo en el árbol | TRACKED | — |
| 001 | `001-amdgpu-overview.md` | Vista general del módulo | TRACKED | — |
| 002 | `002-module-sections.md` | Secciones del .ko | TRACKED | — |
| 003 | `003-exported-symbols.md` | Símbolos exportados | TRACKED | — |
| 005 | `005-cs-ioctl-analysis.md` | Análisis del ioctl | TRACKED | — |
| 006 | `006-lsdma-packets.md` | Paquetes LSDMA | TRACKED | — |
| 007 | `007-gfx8-pm4-format.md` | Formato PM4 en GFX8 | TRACKED | — |
| 008 | `008-firmware-blob.md` | Blob de firmware | TRACKED | — |
| 009 | `009-blockers-status.md` | Estado de bloqueos | TRACKED | — |
| 010 | `010-integration-validation.md` | Validación de integración | TRACKED | — |
| 010 | `010-pgm-rsrc1-decoded.md` | `pgm_rsrc1` decodificado | TRACKED | — |
| 011 | `011-compute-submit-path.md` | Ruta de submit de compute | TRACKED | — |
| 012 | `012-edc-gpr-workaround-carrizo.md` | Workaround EDC/GPR | TRACKED | — |
| 013 | `013-real-submit-path-polaris12.md` | Ruta de submit real | TRACKED | — |
| 014 | `014-mesa-bc3-cpu-decoder-verification.md` | Verificación del decodificador BC3 en Mesa | TRACKED | RE-30 |
| 015 | `015-llvmpipe-discriminating-pairs.md` | Pares discriminantes en llvmpipe | TRACKED | — |
| 016 | `016-q5-static-preregistration.md` | Preregistro de Q-5 | TRACKED | — |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | `FUNCTION(0)=always` no prueba completion | **UNTRACKED** | RE-01, RE-02, **C-002** |
| 018 | `018-execution-order-invalidacion-gfx8.md` | La espera de completion es `NOT_IMPLEMENTABLE` | **UNTRACKED** | RE-02 |
| 019 | `019-atc-l2-invalidation-gfx8.md` | ATC sin granularidad en GFX8 | **UNTRACKED** | RE-03 |
| 020 | `020-vmflush-dword-budget-gfx8.md` | Sobre-reserva de 5 dw en el vm-flush | TRACKED | RE-07 |
| 021 | `021-frame-budget-gfx8-peor-caso.md` | `emit_frame_size` reserva el peor caso | TRACKED | RE-06, **RE-23** |
| 021 | `021-write-lock-scoped-subdir-does-not-block.md` | El cerrojo de ámbito no excluye a la raíz | **UNTRACKED** | NR-10, **C-008** |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | `COND_EXEC` inerte en GFX8 | TRACKED | RE-09 |
| 023 | `023-pm4-count-convencion-medida.md` | `n = payload − 1`, medida | TRACKED | RE-08 |
| 023 | `023-pte-productor-sdma-gfx8.md` | El productor de PTE es `SDMA_OP_GEN_PTEPDE` | **UNTRACKED** | **RE-04, RE-05** |
| 024 | `024-page-table-geometria-gfx8.md` | Geometría del page table | TRACKED | RE-10, RE-11, RE-12, **C-003** |
| 024 | `024-pm4dw-herramienta-conteo-emision.md` | La herramienta de conteo de emisión | **UNTRACKED** | TL-02 |
| 025 | `025-gart-invalidate-con-orden-cpu.md` | La ruta GART tiene completion por CPU | TRACKED | RE-13 |
| 025 | `025-vm-flush-path-gfx8-63dw.md` | La ruta de vm-flush son 63 dw, alcanzable | TRACKED | RE-14, RE-22 |
| 026 | `026-pte-encoding-gfx8.md` | El PTE de GFX8: 40 bits de PA por tres vías | TRACKED | RE-20 |
| 026 | `026-frame-completo-gfx8-121dw.md` | El frame son 121 dw; la reserva son dos sumandos | TRACKED | RE-16, RE-17, **NR-07c** |
| 027 | `027-ptba-produccion-gfx8.md` | El PTBA: una sola aritmética | TRACKED | RE-19 |
| 027 | `027-write-multiple-resuelto.md` | `write_multiple` deja de ser una bandera | TRACKED | **RE-23** |
| 028 | `028-fence-completion-orden-d.md` | El fence sí tiene completion | TRACKED | RE-18 |
| 028 | `028-emit-frame-size-justificado.md` | Por qué 172 dw es la reserva correcta | TRACKED | complemento de RE-06 |
| 029 | `029-release-mem-y-eop-exec-muerto.md` | Por qué `RELEASE_MEM` no necesita `seq − 1` | **UNTRACKED** | RE-21 |
| 029 | `029-orden-validacion-fence-no-ring.md` | Orden de validación del fence, sin el ring | **UNVERIFIED** | — |
| 030 | `030-writeback-buffer-wb-slots.md` | El writeback buffer: 5 slots, uno se fuga | TRACKED | P23 |
| 030 | `030-page-walker-gfx8-2-niveles.md` | Page walker de 2 niveles. **`block_size = 22` REFUTADO** | **UNTRACKED** | **C-009**: contradice el `dev_info` del kernel en ejecución. Sobrevive `RE-28` (no huge pages) |
| 031 | `031-rptr-wptr-tres-dominios.md` | Tres dominios de memoria, sin `mb()` | TRACKED | P26, **RE-25** (su §4 cerrado por 032) |
| 032 | `032-fence-lectura-coherente-por-pin.md` | La lectura del fence es normal; la garantía está en el `pin` | TRACKED | **RE-25** |
| 033 | `033-protections-opaco-en-el-camino-gpuvm.md` | `PROTECTIONS` es opaco en GPUVM | **UNTRACKED** | **RE-24**, degrada la base del layout del PTE |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | **La spec PM4 de GFX8 no existe.** Cierra el `−1` de RE-08; refuta una aserción de freedreno | **UNTRACKED** | **RE-29, RE-30, RE-31**, `C-010` |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | **La spec PM4 de GFX8 no existe.** Cierre el `−1` de RE-08; refuta una aserción de freedreno | **UNTRACKED** | **RE-29, RE-30, RE-31**, `C-010` |
| 042 | `042-at-wire-format-inversion-cg-r-l.md` | Formato del bus AT, y la inversión CG/R/L | **UNTRACKED** | — línea nueva, acceso a registros |
| 043 | `043-pll-bsp-asi-pasi.md` | PLL / BSP / ASI / PA-SI | **UNTRACKED** | — el árbol de relojes. Complementa RE-27 |
| 031 | `031-aridad-no-entregada.md` | El verificador de aridad **NO** se entregó, con evidencia | **UNTRACKED** | `NEGATIVE_RESULT` + una compuerta de cobertura |
| 032 | `032-pte-invalido-no-existe.md` | "Inválido" no es `VALID=0`: es un PTE válido que apunta a 0 | **UNTRACKED** | cierra el hueco estático de page tables |
| 033 | `033-mmu-vm-no-publicado.md` | El bloque MMU/VM de GFX8 **no está publicado** por AMD | **UNTRACKED** | **RE-34**. `NOT_PUBLISHED`, no `NOT_DETERMINED` |
| 035 | `035-block-size-tres-claims-y-un-log.md` | Tres cifras para `block_size`, y el log que las zanja | **UNTRACKED** | **RE-35**: corrobora `C-009` con el mismo árbitro |
| 035 | `035-correccion-ptepde-es-polaris12.md` | Corrige `023`: dice `sdma_v4_0` y `count - 1` | **UNTRACKED** | **REFUTADO en `C-011`**. El ASIC usa `sdma_v3_0` |
| 036 | `036-correccion-023-implementada-ptepde.md` | Implementa 035 en `rx550_pm4.c` | **UNTRACKED** | **el error está compilado** en `rx550_pm4.c:277`. Frontera `F3d` |
| 037 | `037-ptba-dos-tramos-y-vm-flush.md` | PTBA en dos tramos, y el vm-flush | **UNTRACKED** | declara la circularidad del test propio |
| 036 | `036-vocabulario-pm4-vivo-polaris12.md` | Vocabulario PM4 vivo en Polaris12 | **UNTRACKED** | — |
| 038 | `038-validador-flujo-y-regla-del-count.md` | Validador de flujo, y la regla `count = payload − 1` | **UNTRACKED** | **RE-37**: confirma la circularidad desde dentro; **RE-38**: su evidencia ya caducó |
| 039 | `039-coherencia-ib-si-existe.md` | Coherencia del IB, si el buffer existe | **UNTRACKED** | — |
| 052 | `052-srcid-de-fault-gfx8-y-tabla-de-iv-no-catalogada.md` | Los dos SRCID de fault de GFX8, y **112 vectores sin catalogar** | **UNTRACKED** | completa el IV de `RE-36`: `src_id` dice **qué**, `vmid`/`pasid` dicen **quién**, `src_data[0]` dice **dónde** |
| 053 | `053-herramienta-asic-resolver-gate-compilacion.md` | **`asic_resolver`**: gate de compilación y rama por ASIC, mecánicos | **UNTRACKED** | **`RE-39`, `TL-10`**. Verificado por mí: `--selftest` OK, rc=0 |
| 046 | `046-correccion-smu-ruta-no-compilada-para-polaris12.md` | **`si_dpm.c`/`si_smc.c` no compilan para Polaris12** | **UNTRACKED** | **refuta 040-045**. `P38`, reencuadra `F3b` |
| 047 | `047-ruta-real-polaris12-canal-smc-argumento-vtable.md` | La ruta real, y el argumento de la vtable | **UNTRACKED** | — |
| 048 | `048-protocolo-smc-polaris-armado-y-retorno-siempre-cero.md` | El protocolo SMC armado, y retorno siempre cero | **UNTRACKED** | — |
| 049 | `049-modelo-voltaje-smio-polaris12.md` | El modelo de voltaje de SMIO en Polaris12 | **UNTRACKED** | — |
| 050 | `050-correccion-chip-id-y-clock-stretcher.md` | Corrige su propio turno: `CHIP_POLARIS12 = 17`, no 10 | **UNTRACKED** | autocomputadora de la línea H |
| 051 | `051-interrupt-vector-iv-gfx8-y-teardown-lifo.md` | El vector de interrupción de GFX8 y el teardown LIFO del GMC | **UNTRACKED** | **RE-36, P40, P41** |
| 040 | `040-smu-canal-mensajes-gfx8.md` | El canal de mensajes al SMU | TRACKED | **RE-27**, degradada por `046` |
| 041 | `041-curva-at-histeresis-dvfs-gfx8.md` | La banda de histéresis `[t_l, t_h]` del firmware SMU | **UNTRACKED** | complementa RE-27 |
> **Filas añadidas mecánicamente el 2026-10-02**, por `docscan.py --index`. Cada fila transcribe el título que el propio hallazgo escribe y su estado en git. **Ninguna ha sido leída**, y por eso la columna dice `NO LEIDA`: un título transcrito no es una afirmación sobre el hallazgo. Están aquí para que el índice no esté viejo respecto al árbol, que crece varias veces por hora.

| 034 | `034-corpus-autoconsistente-layouts-pm4.md` | El kernel se autoconsistency-check: 28/28 sobre layouts documentados | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 037 | `037-mapa-registros-mosaico-y-60-escrituras.md` | El mapa de registros es un mosaico de seis familias, y 60 escrituras p | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 038 | `038-herramientas-para-no-repetir-errores.md` | Herramientas para no repetir a mano lo que ya me costó errores | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 039 | `039-cierre-de-includes-resolucion-real.md` | El cierre de includes, y por qué la resolución alfabética era falsa | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 040 | `040-corpus-verificado-contra-binario-y-runtime.md` | El corpus sí describe el binario cargado, y tres experimentos que creí | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 040 | `040-wptr-doorbell-y-tres-productores-de-ib.md` | wptr y doorbell reconstruidos — y hay tres productores de referencia-a | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 041 | `041-grafo-y-detector-contradicciones.md` | Grafo de conocimiento y detector de contradicciones, automático | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 041 | `041-herramientas-de-procedencia-y-auditoria.md` | Dos herramientas para dejar de cometertaina clase de error a mano | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 042 | `042-mapa-causal-y-mecanismo-hqd-mqd.md` | El mapa causalFlechas encuentra 64 registros que nadie había mirado | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 042 | `042-vmid-map-y-la-particion-que-es-decision.md` | vmid_map: la asignación de VMID es una decisión del driver, y la geome | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 043 | `043-asercion-struct-mqd-contra-offsets.md` | El driver tiene una aserción sobre el hardware que nunca se comprobó,  | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 043 | `043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md` | Vuelta atrás: 035 y 036 estaban equivocados, y la herramienta lo encon | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 044 | `044-asercion-corroborada-y-regla-propias-ajenas.md` | Cuatro sitios indexan el mismo bloque, y el control de contratos neces | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 044 | `044-correccion-implementada-y-por-que-make-no-vio-el-cambio.md` | La corrección de 043 aplicada, y por qué make no vio el cambio | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 044 | `044-xclk-fuentes-y-constantes-legacy.md` | xclk: cinco caminos de reloj, dos leídos del hardware, y dos constante | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 045 | `045-fronteras-obsoletas-y-cuatro-formas-de-mentir.md` | Hay 29 fronteras que otro documento ya cerró, y cuatro formas de que u | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 045 | `045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md` | La convención de count nunca se midió en el ASIC de esta GPU, y dos he | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 045 | `045-smu-cadena-completa-y-cierre-de-scope.md` | Cadena cerrada: del BIOS y del hardware al reloj de GFX8 | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 046 | `046-auto-referencia-y-la-jerarquia-de-fuentes.md` | Una herramienta se cita a sí misma, y eso obliga a jerarquizar las fue | TRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 046 | `046-la-version-de-ip-que-nunca-se-consulta.md` | La versión de IP que nunca se consulta, y por qué 043 preguntó lo que  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 047 | `047-los-diez-selectores-y-el-limite-del-claim.md` | Ninguno de los 10 selectores de IP es alcanzable, y por qué el claim f | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 048 | `048-claims-y-lo-que-el-proyecto-realmente-cita.md` | El proyecto se audita, pero casi no se cita: 114 de 388 afirmaciones t | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 049 | `049-los-497-respaldos-en-codigo-resueltos.md` | Los 497 respaldos en código, resueltos contra el corpus: cero errores  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 050 | `050-la-frontera-ordenada-por-su-via-de-cierre.md` | (sin titulo) | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 051 | `051-leer-agents-md-cambia-la-politica.md` | Leer AGENTS.md cambia la política: la frontera era un formulario, no u | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 054 | `054-dos-mascaras-mc-y-pte-y-reproduccion-de-gart.md` | Las dos máscaras de dirección MC y PTE, y la reproducción exacta de lo | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 055 | `055-didt-indirecto-unidad-dword-y-protocolo-soc15.md` | DIDT de Polaris12: bus indirecto, y la unidad del offset resuelta por  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 056 | `056-function-always-spec-primaria-descartada-con-causa.md` | FUNCTION=always: la spec primaria existe, es de shaders, y nunca hubo  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 056 | `056-siete-herramientas-y-22-bugs-encontrados.md` | Siete herramientas y el bucle manual cerrado | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 057 | `057-vias-de-lectura-gpuvm-y-por-que-no-hay-discriminante-read-only.md` | Las vías de lectura de estado de GPUVM que existen, y por qué no hay d | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 058 | `058-tabla-iv-gfx8-112-nombres-73-valores.md` | La tabla de IV de GFX8: 112 nombres, 73 valores, y 8 alias que el hard | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 059 | `059-srcdata-no-es-payload-es-el-wptr-del-ring.md` | src_data[0] no lleva el payload del evento: es el WPTR del propio ring | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 060 | `060-srcdata-es-el-subtipo-y-el-decodificador-esta-en-dce.md` | src_data[0] sí es el payload: el decodificador de display está en dce_ | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 061 | `061-srcdata-dos-valores-constante-por-derivacion.md` | src_data[0] tiene exactamente dos valores válidos, y es constante por  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 062 | `062-citas-de-c-009-desplazadas-y-tabla-de-030-invertida.md` | La cita que arbitra block_size está desplazada 2 líneas, y la tabla de | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | MEMORIA · sesión smu — estado persistente al 2026-10-01 | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 064 | `064-bitmap-vm-context-cntl-gfx8-f3-y-faults.md` | El mapa de bits completo de VM_CONTEXT_CNTL en GFX8: dónde cae F3 y dó | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 065 | `065-offset-gmc-vs-mmhub-siete-registros.md` | Siete registros de GMC tienen direcciones distintas en MMHUB, y el #in | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 066 | `066-mapa-familias-por-fichero-c.md` | Cada .c declara sus familias de cabecera, y eso acota dónde puede esta | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 067 | `067-cadena-gart-256m-y-tabla-en-vram.md` | La cadena GART de punta a punta: 256 MiB por default, y la tabla es un | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 068 | `068-orden-emision-ptba-invalidate-wait-pfp.md` | La cadena de emisión de §D está entera en 26 líneas, y su aritmética c | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 069 | `069-f11-medido-y-ad12-discriminante-verificado.md` | F11 medido (27 de 34 herramientas citadas) y AD-12 verificado hoy con  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 070 | `070-contrato-host-smc-msg-arg-y-handshake.md` | El contrato host↔SMC de Polaris12: handshake, wire format y semántica  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 071 | `071-el-except-que-devuelve-stub-y-el-flag-que-desactiva-la-auditoria.md` | El except que devuelve un stub, el flag que desactiva la auditoría, y  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 071 | `071-f2-ejecutado-bloqueado-por-saturacion-gpu.md` | F2 ejecutado y bloqueado por saturación de la GPU, no por hardware: el | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 072 | `072-f3c-estatico-cond-exc-e-invalidate-response.md` | F3c estático: COND_EXEC es idéntico en GFX8, y VM_INVALIDATE_RESPONSE  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 072 | `072-la-lista-cerrada-de-verbos-que-cronometraba-el-grafo.md` | La lista cerrada de verbos que cronometraba el grafo de findings | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 073 | `073-f7-medido-216-sin-versionar-y-17-ids-duplicados.md` | F7 medido: 216 ficheros sin versionar, y 17 IDs de hallazgo duplicados | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 074 | `074-f2b-el-hardware-compone-el-pte.md` | F2b: el host NO compone el PTE — lo compone el hardware a partir de ad | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
> **Filas añadidas mecánicamente el 2026-10-02**, por `docscan.py --index`. Cada fila transcribe el título que el propio hallazgo escribe y su estado en git. **Ninguna ha sido leída**, y por eso la columna dice `NO LEIDA`: un título transcrito no es una afirmación sobre el hallazgo. Están aquí para que el índice no esté viejo respecto al árbol, que crece varias veces por hora.

| 073 | `073-el-indice-por-numero-descarta-y-el-grafo-pierde-aristas.md` | El índice por número se queda con el primero, y el grafo pierde 53 ari | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 074 | `074-25-aristas-que-existian-y-44-findings-sin-relacion.md` | 25 aristas que existían y no se contaban, y 44 findings que no se decl | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 075 | `075-mapa-flags-pte-y-bifurcacion-host.md` | El mapa completo de flags de PTE, y una bifurcación que 074 no vio | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 076 | `076-catalogo-276-mensajes-smu-y-codigos-retirados.md` | Los 276 mensajes del firmware SMU para Polaris12, y 297 códigos que ya | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
> **Filas añadidas mecánicamente el 2026-10-02**, por `docscan.py --index`. Cada fila transcribe el título que el propio hallazgo escribe y su estado en git. **Ninguna ha sido leída**, y por eso la columna dice `NO LEIDA`: un título transcrito no es una afirmación sobre el hallazgo. Están aquí para que el índice no esté viejo respecto al árbol, que crece varias veces por hora.

| 047 | `047-el-handler-si-lee-src-data.md` | El handler de faults sí lee src_data[0] — y lo imprime | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 077 | `077-141-citas-que-eran-rangos-y-10-omisiones-reales.md` | 141 citas que eran rangos de líneas, y 10 omisiones que sí son reales | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 078 | `078-de-las-89-aristas-85-tienen-respaldo-en-el-cuerpo.md` | De las 89 aristas, 85 tienen respaldo en el cuerpo del origen y 4 son  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
> **Filas añadidas mecánicamente el 2026-10-02**, por `docscan.py --index`. Cada fila transcribe el título que el propio hallazgo escribe y su estado en git. **Ninguna ha sido leída**, y por eso la columna dice `NO LEIDA`: un título transcrito no es una afirmación sobre el hallazgo. Están aquí para que el índice no esté viejo respecto al árbol, que crece varias veces por hora.

| 079 | `079-el-76-de-respaldo-es-contra-un-numero-que-no-identifica.md` | El 76% de respaldo textual es contra un número que no identifica un fi | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
> **Filas añadidas mecánicamente el 2026-10-02**, por `docscan.py --index`. Cada fila transcribe el título que el propio hallazgo escribe y su estado en git. **Ninguna ha sido leída**, y por eso la columna dice `NO LEIDA`: un título transcrito no es una afirmación sobre el hallazgo. Están aquí para que el índice no esté viejo respecto al árbol, que crece varias veces por hora.

| 048 | `048-numeros-de-hallazgo-no-identifican.md` | Los números de hallazgo no identifican un hallazgo: 37 de 82 están dup | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 080 | `080-un-criterio-automatico-para-las-58-aristas-ambiguas.md` | Un criterio automático para las 58 aristas ambiguas, y por qué no se p | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 081 | `081-la-tabla-dpm-son-1884-bytes-no-1120.md` | SMU74_Discrete_DpmTable son 1884 bytes, no 1120: una CORRECCION | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 081 | `081-system-access-mode-3-es-not-in-sys.md` | SYSTEM_ACCESS_MODE = 3 es NOT_IN_SYS, y cierra la mitad de la frontera | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 082 | `082-el-acceso-no-mapeado-pide-pagina-prt.md` | El acceso no mapeado no pasa de paso: pide página. Y set_prt está en l | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 082 | `082-ocho-fallos-de-layout-que-producen-numeros-plausibles-y-falsos.md` | Ocho fallos de layout que producen numeros plausibles y falsos | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 083 | `083-auditoria-de-las-110-copias-a-la-ram-del-smc.md` | Auditoria de las 110 copias a la RAM del SMC: ninguna truncada, todas  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 083 | `083-en-gfx8-el-prt-se-puede-activar-y-no-hay-quien-lo-atienda.md` | En GFX8 el PRT se puede activar y no hay quien lo atienda | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 083 | `083-sg-cache-coherency-l1-l2-y-asimetria.md` | §G por primera vez: la cadena enable/disable de las cachés de traducci | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 084 | `084-mecanismo-de-copia-al-smc-y-assert-de-rango.md` | El mecanismo de copia al SMC: dword a dword, MSB primero, con assert d | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 084 | `084-se-packet-consumption-y-granularidad.md` | §E por primera vez: packet consumption es un contrato declarado, y el  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 085 | `085-sb-page-walker-invalidate-siempre-obligatorio.md` | §B: en GFX8 el invalidate es SIEMPRE obligatorio, y el comentario que  | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 086 | `086-sf-vram-256m-visibles-y-la-bar.md` | §F VRAM: por qué hay 256 MiB visibles de 2048, y por qué no es por par | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |
| 087 | `087-vm-fault-stop-0-y-ip-block-mask-confirma-047.md` | vm_fault_stop = 0 en esta placa: los faults no se desactivan, y ip_blo | UNTRACKED | NO LEIDA — transcripción, nadie lo ha leído |

**Y el árbol siguió creciendo después de la última actualización de este fichero**:
`042-at-wire-format-inversion-cg-r-l` y `043-pll-bsp-asi-pasi`. No registrados: no se
han leído. El primero es territorio nuevo (acceso a registros por bus AT) y el segundo
toca el árbol de relojes, que es la línea H que `040` acaba de abrir.

**Hay huecos en la numeración**: faltan `004`, `038` y `039`. O se numeraron y no se commitearon, o el índice numérico ya no es
consecutivo porque las sesiones disjuntas eligen números por su cuenta. Es el mismo
problema de `NR-10`, y en este caso con una síntoma nuevo: **huecos en la
numeración**.

**Un hallazgo marcado `UNVERIFIED`** porque apareció con este fichero y no se ha leído:
`029-orden-validacion-fence-no-ring`. Su nombre sugiere que **cuestiona la premisa de
`028`** —"sin el ring"— y eso sería una contradicción con `RE-18`. **No se registra
ningún claim sobre él.** Es exactamente lo que hay que hacer: la contradicción es
*plausible*, no `PROVEN`. Leerlo es la acción más barata de esta ronda, y si el nombre
describe lo que el título insinúa, es la de mayor valor: cerraría o refutaría el único
punto del path de submit donde el hardware confirma que el trabajo terminó.

## Los nueve sin versionar, y qué se pierde si se borran

```
017  sin él no existe la evidencia de que FUNCTION(0)=always con mask=0 no compara.
     RE-01 y RE-02 dependen sólo de él.
018  sin él, "esperar completion es NOT_IMPLEMENTABLE" no tiene Basis escrito.
019  sin él, la afirmación de que flush_type y vmhub son parámetros muertos queda sin
     el barrido que la sostiene.
021-lock  sin él, la reproducción de NR-10 y la propuesta de F10 desaparecen. Y es el
     único documento que explica por qué dos sesiones pueden escribir a la vez.
023-pte  sin él, RE-04 y RE-05 desaparecen. Son la afirmación más accionable de la
     línea A: el driver propio emite un paquete SDMA, no escribe memoria.
024-pm4dw  sin él, TL-02 queda sin fuente y RE-14/RE-16/RE-23 pierden su productor.
025-vm-flush  sin él, los 63 dw y el descubrimiento de emit_cleaner_shader nulo.
026-frame  sin él, los 121 dw y la fórmula de dos sumandos (NR-07c).
029  sin él, RE-21 y la explicación estructural de por qué GFX8 no necesita seq−1
```

Ocho de los nueve son de la **línea A**, la que está avanzando. `COORDINACION.md:9-12`
documenta dos pérdidas reales de trabajo en este proyecto y ambas fueron de material
sin commitear. La frontera `F7` es esto, y sigue siendo lo más caro que no se arregla.

## Reproducir este índice

```bash
cd /home/lucas/Escritorio/RX550-INVESTIGACION
# colisiones de índice
ls 06-INGENIERIA-INVERSA/findings/ | sed 's/-.*//' | sort | uniq -d
# sin versionar
for f in 06-INGENIERIA-INVERSA/findings/*.md; do
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 || echo "UNTRACKED $f"
done
# total
ls 06-INGENIERIA-INVERSA/findings/*.md | wc -l
```

Un índice de findings que hay que re-generar a mano es un índice que se queda viejo.
Los tres comandos de arriba son el índice real; este fichero es la versión legible.