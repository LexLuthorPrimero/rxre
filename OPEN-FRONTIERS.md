# OPEN-FRONTIERS

<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Los 1083 huecos abiertos de 286 findings, y por donde se cierran.

**Generado desde la salida de `tools/frontier.py --json`**, no reimplementando su clasificacion. Dos recuentos del mismo conjunto divergen sin que nadie lo note.

## Via de cierre

| via | huecos | que significa |
|---|---|---|
| `SPEC_NO_PUBLICADO` | 358 | falta documentacion que no existe (033) |
| `RUNTIME_ACTIVO` | 290 | solo se cierra observando comportamiento |
| `POR_DEFINICION` | 137 | es una convencion que se elige, no se descubre |
| `UN_REGISTRO` | 123 | se cierra leyendo un registro de la tarjeta |
| `SIN_PISTAS` | 107 | el texto no dice que haria falta para cerrarlo |
| `DIFERENCIAL` | 68 | se cierra repitiendo con un parametro y comparando |

**Total: 1083 huecos.**
`SIN_PISTAS` son los unicos que ningun texto del proyecto dice como cerrar.

## Los huecos

| finding | fichero | linea | clase | via | fuerza | marca | registros |
|---|---|---|---|---|---|---|---|
| 001 | `001-amdgpu-overview.md` | 213 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 001 | `001-amdgpu-overview.md` | 254 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 003 | `003-exported-symbols.md` | 141 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 005 | `005-cs-ioctl-analysis.md` | 90 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 005 | `005-cs-ioctl-analysis.md` | 202 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 006 | `006-lsdma-packets.md` | 245 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 006 | `006-lsdma-packets.md` | 290 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 007 | `007-gfx8-pm4-format.md` | 78 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 007 | `007-gfx8-pm4-format.md` | 214 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 008 | `008-firmware-blob.md` | 103 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 008 | `008-firmware-blob.md` | 127 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 008 | `008-firmware-blob.md` | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 009 | `009-blockers-status.md` | 68 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | `009-blockers-status.md` | 73 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | `009-blockers-status.md` | 145 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | `009-blockers-status.md` | 190 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | `009-blockers-status.md` | 191 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | `009-blockers-status.md` | 205 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 010 | `010-integration-validation.md` | 515 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | `010-integration-validation.md` | 524 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | `010-pgm-rsrc1-decoded.md` | 5 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | `010-pgm-rsrc1-decoded.md` | 140 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 010 | `010-pgm-rsrc1-decoded.md` | 174 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | `010-pgm-rsrc1-decoded.md` | 175 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 011 | `011-compute-submit-path.md` | 265 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 011 | `011-compute-submit-path.md` | 301 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 012 | `012-edc-gpr-workaround-carrizo.md` | 76 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 012 | `012-edc-gpr-workaround-carrizo.md` | 272 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 012 | `012-edc-gpr-workaround-carrizo.md` | 282 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 013 | `013-real-submit-path-polaris12.md` | 211 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | `013-real-submit-path-polaris12.md` | 228 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | `013-real-submit-path-polaris12.md` | 229 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | `013-real-submit-path-polaris12.md` | 230 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | `013-real-submit-path-polaris12.md` | 231 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 18 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 23 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 26 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 30 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 113 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 116 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 121 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 130 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 131 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 285 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: comportamiento real | - |
| 015 | `015-llvmpipe-discriminating-pairs.md` | 498 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 016 | `016-q5-static-preregistration.md` | 138 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 016 | `016-q5-static-preregistration.md` | 171 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | 144 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | 145 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Efecto real | - |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | 159 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | 176 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 017 | `017-vm-invalidate-gfx8-function-always.md` | 196 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 018 | `018-execution-order-invalidacion-gfx8.md` | 29 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 018 | `018-execution-order-invalidacion-gfx8.md` | 90 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 018 | `018-execution-order-invalidacion-gfx8.md` | 206 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 018 | `018-execution-order-invalidacion-gfx8.md` | 227 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 018 | `018-execution-order-invalidacion-gfx8.md` | 236 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: REQUIREMENT | - |
| 018 | `018-execution-order-invalidacion-gfx8.md` | 251 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 019 | `019-atc-l2-invalidation-gfx8.md` | 163 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 019 | `019-atc-l2-invalidation-gfx8.md` | 164 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 019 | `019-atc-l2-invalidation-gfx8.md` | 190 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 020 | `020-vmflush-dword-budget-gfx8.md` | 131 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 020 | `020-vmflush-dword-budget-gfx8.md` | 132 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 020 | `020-vmflush-dword-budget-gfx8.md` | 133 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 020 | `020-vmflush-dword-budget-gfx8.md` | 172 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 021 | `021-frame-budget-gfx8-peor-caso.md` | 166 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 021 | `021-frame-budget-gfx8-peor-caso.md` | 167 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 021 | `021-frame-budget-gfx8-peor-caso.md` | 203 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 021 | `021-frame-budget-gfx8-peor-caso.md` | 214 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | 246 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | 258 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: MODEL_CHOICE | - |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | 283 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | 284 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | 285 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | 289 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | `022-cond-exec-inerte-en-gfx8.md` | 310 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: REQUIREMENT | - |
| 023 | `023-pm4-count-convencion-medida.md` | 75 | `UNKNOWN` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 175 | `UNKNOWN` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 200 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 205 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 212 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 215 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 233 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 245 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 023 | `023-pm4-count-convencion-medida.md` | 246 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 023 | `023-pm4-count-convencion-medida.md` | 256 | `UNKNOWN` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | `023-pm4-count-convencion-medida.md` | 287 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: hardware interpreta | - |
| 024 | `024-page-table-geometria-gfx8.md` | 213 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 024 | `024-page-table-geometria-gfx8.md` | 287 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 024 | `024-pm4dw-herramienta-conteo-emision.md` | 176 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 025 | `025-gart-invalidate-con-orden-cpu.md` | 91 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 025 | `025-gart-invalidate-con-orden-cpu.md` | 112 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 025 | `025-gart-invalidate-con-orden-cpu.md` | 182 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 025 | `025-gart-invalidate-con-orden-cpu.md` | 184 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 025 | `025-vm-flush-path-gfx8-63dw.md` | 123 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 025 | `025-vm-flush-path-gfx8-63dw.md` | 168 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 025 | `025-vm-flush-path-gfx8-63dw.md` | 170 | `UNKNOWN` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 026 | `026-frame-completo-gfx8-121dw.md` | 9 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | `026-frame-completo-gfx8-121dw.md` | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | `026-frame-completo-gfx8-121dw.md` | 159 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | `026-pte-encoding-gfx8.md` | 220 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | `026-pte-encoding-gfx8.md` | 237 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | `026-pte-encoding-gfx8.md` | 238 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | `026-pte-encoding-gfx8.md` | 239 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | `026-pte-encoding-gfx8.md` | 257 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 027 | `027-ptba-produccion-gfx8.md` | 271 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 028 | `028-fence-completion-orden-d.md` | 116 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | `028-fence-completion-orden-d.md` | 275 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | `028-fence-completion-orden-d.md` | 291 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | `028-fence-completion-orden-d.md` | 296 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | `028-fence-completion-orden-d.md` | 315 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 029 | `029-orden-validacion-fence-no-ring.md` | 123 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 029 | `029-orden-validacion-fence-no-ring.md` | 131 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 029 | `029-orden-validacion-fence-no-ring.md` | 171 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 029 | `029-release-mem-y-eop-exec-muerto.md` | 99 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 029 | `029-release-mem-y-eop-exec-muerto.md` | 232 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 029 | `029-release-mem-y-eop-exec-muerto.md` | 244 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 030 | `030-page-walker-gfx8-2-niveles.md` | 93 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: arquitectura d | - |
| 030 | `030-writeback-buffer-wb-slots.md` | 171 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: arquitectura d | - |
| 030 | `030-writeback-buffer-wb-slots.md` | 216 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: arquitectura d | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 25 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 277 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 278 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 288 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 304 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 314 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 346 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | `031-rptr-wptr-tres-dominios.md` | 426 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 032 | `032-fence-lectura-coherente-por-pin.md` | 38 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | `032-fence-lectura-coherente-por-pin.md` | 202 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | `032-fence-lectura-coherente-por-pin.md` | 212 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: visible para | - |
| 032 | `032-fence-lectura-coherente-por-pin.md` | 213 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: visible para | - |
| 032 | `032-fence-lectura-coherente-por-pin.md` | 245 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | `032-fence-lectura-coherente-por-pin.md` | 270 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | `032-fence-lectura-coherente-por-pin.md` | 282 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 032 | `032-pte-invalido-no-existe.md` | 92 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 032 | `032-pte-invalido-no-existe.md` | 93 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 032 | `032-pte-invalido-no-existe.md` | 94 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 032 | `032-pte-invalido-no-existe.md` | 100 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 033 | `033-mmu-vm-no-publicado.md` | 1 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: NOT_PUBLISHED | - |
| 033 | `033-mmu-vm-no-publicado.md` | 13 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | `033-mmu-vm-no-publicado.md` | 15 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | `033-mmu-vm-no-publicado.md` | 47 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: NOT_PUBLISHED | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 32 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 98 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 99 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 101 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convencion | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 102 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convencion | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 280 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 396 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 399 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 435 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 033 | `033-pm4-spec-gfx8-no-existe-y-el-encuadre.md` | 452 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 034 | `034-corpus-autoconsistente-layouts-pm4.md` | 206 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 034 | `034-corpus-autoconsistente-layouts-pm4.md` | 264 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 034 | `034-corpus-autoconsistente-layouts-pm4.md` | 289 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 034 | `034-corpus-autoconsistente-layouts-pm4.md` | 329 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 035 | `035-block-size-tres-claims-y-un-log.md` | 157 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 035 | `035-block-size-tres-claims-y-un-log.md` | 262 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 036 | `036-vocabulario-pm4-vivo-polaris12.md` | 254 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 036 | `036-vocabulario-pm4-vivo-polaris12.md` | 264 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 036 | `036-vocabulario-pm4-vivo-polaris12.md` | 310 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 037 | `037-mapa-registros-mosaico-y-60-escrituras.md` | 266 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 037 | `037-mapa-registros-mosaico-y-60-escrituras.md` | 275 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 037 | `037-mapa-registros-mosaico-y-60-escrituras.md` | 283 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | `mmCP_HQD_PQ_RPTR` |
| 037 | `037-ptba-dos-tramos-y-vm-flush.md` | 83 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 037 | `037-ptba-dos-tramos-y-vm-flush.md` | 85 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 037 | `037-ptba-dos-tramos-y-vm-flush.md` | 86 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 038 | `038-herramientas-para-no-repetir-errores.md` | 267 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 038 | `038-validador-flujo-y-regla-del-count.md` | 8 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 038 | `038-validador-flujo-y-regla-del-count.md` | 164 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 039 | `039-coherencia-ib-si-existe.md` | 73 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 039 | `039-coherencia-ib-si-existe.md` | 174 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 039 | `039-coherencia-ib-si-existe.md` | 175 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 039 | `039-coherencia-ib-si-existe.md` | 176 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 040 | `040-corpus-verificado-contra-binario-y-runtime.md` | 249 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | `040-corpus-verificado-contra-binario-y-runtime.md` | 285 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 040 | `040-wptr-doorbell-y-tres-productores-de-ib.md` | 38 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | `040-wptr-doorbell-y-tres-productores-de-ib.md` | 183 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | `040-wptr-doorbell-y-tres-productores-de-ib.md` | 184 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | `040-wptr-doorbell-y-tres-productores-de-ib.md` | 185 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | `040-wptr-doorbell-y-tres-productores-de-ib.md` | 187 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 041 | `041-grafo-y-detector-contradicciones.md` | 62 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 041 | `041-grafo-y-detector-contradicciones.md` | 89 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 041 | `041-grafo-y-detector-contradicciones.md` | 185 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 041 | `041-grafo-y-detector-contradicciones.md` | 188 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 042 | `042-mapa-causal-y-mecanismo-hqd-mqd.md` | 162 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 042 | `042-mapa-causal-y-mecanismo-hqd-mqd.md` | 224 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no hay documentaci | - |
| 042 | `042-mapa-causal-y-mecanismo-hqd-mqd.md` | 242 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 042 | `042-mapa-causal-y-mecanismo-hqd-mqd.md` | 245 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 042 | `042-vmid-map-y-la-particion-que-es-decision.md` | 93 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 042 | `042-vmid-map-y-la-particion-que-es-decision.md` | 94 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 043 | `043-asercion-struct-mqd-contra-offsets.md` | 145 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 043 | `043-asercion-struct-mqd-contra-offsets.md` | 210 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 043 | `043-asercion-struct-mqd-contra-offsets.md` | 212 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 044 | `044-asercion-corroborada-y-regla-propias-ajenas.md` | 184 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 044 | `044-asercion-corroborada-y-regla-propias-ajenas.md` | 187 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 044 | `044-correccion-implementada-y-por-que-make-no-vio-el-cambio.md` | 118 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 045 | `045-fronteras-obsoletas-y-cuatro-formas-de-mentir.md` | 12 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | `045-fronteras-obsoletas-y-cuatro-formas-de-mentir.md` | 22 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | `045-fronteras-obsoletas-y-cuatro-formas-de-mentir.md` | 60 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | `045-fronteras-obsoletas-y-cuatro-formas-de-mentir.md` | 75 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | `045-fronteras-obsoletas-y-cuatro-formas-de-mentir.md` | 111 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | `045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md` | 129 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | `045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md` | 150 | `NOT_DETERMINED` | `UN_REGISTRO` | 3 | frase: un registro | - |
| 046 | `046-auto-referencia-y-la-jerarquia-de-fuentes.md` | 73 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 046 | `046-auto-referencia-y-la-jerarquia-de-fuentes.md` | 74 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 046 | `046-auto-referencia-y-la-jerarquia-de-fuentes.md` | 203 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 046 | `046-la-version-de-ip-que-nunca-se-consulta.md` | 74 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 046 | `046-la-version-de-ip-que-nunca-se-consulta.md` | 145 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 047 | `047-el-handler-si-lee-src-data.md` | 109 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_CONTEXT1_PROTECT | - |
| 047 | `047-el-handler-si-lee-src-data.md` | 110 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_CONTEXT1_PROTECT | - |
| 047 | `047-el-handler-si-lee-src-data.md` | 147 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 047 | `047-el-handler-si-lee-src-data.md` | 148 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 047 | `047-los-diez-selectores-y-el-limite-del-claim.md` | 201 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_CONTEXT1_PROTECT | - |
| 048 | `048-numeros-de-hallazgo-no-identifican.md` | 122 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 048 | `048-numeros-de-hallazgo-no-identifican.md` | 123 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 050 | `050-correccion-chip-id-y-clock-stretcher.md` | 106 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | `050-frontera-de-corpus-no-de-hardware.md` | 10 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | `050-frontera-de-corpus-no-de-hardware.md` | 22 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | `050-frontera-de-corpus-no-de-hardware.md` | 122 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | `050-frontera-de-corpus-no-de-hardware.md` | 123 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 051 | `051-asic-id-desde-pci-config.md` | 109 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 051 | `051-asic-id-desde-pci-config.md` | 116 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 051 | `051-asic-id-desde-pci-config.md` | 150 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 056 | `056-function-always-spec-primaria-descartada-con-causa.md` | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 056 | `056-function-always-spec-primaria-descartada-con-causa.md` | 153 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 056 | `056-function-always-spec-primaria-descartada-con-causa.md` | 180 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 057 | `057-vias-de-lectura-gpuvm-y-por-que-no-hay-discriminante-read-only.md` | 10 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 057 | `057-vias-de-lectura-gpuvm-y-por-que-no-hay-discriminante-read-only.md` | 133 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 058 | `058-tabla-iv-gfx8-112-nombres-73-valores.md` | 77 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 059 | `059-srcdata-no-es-payload-es-el-wptr-del-ring.md` | 35 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 059 | `059-srcdata-no-es-payload-es-el-wptr-del-ring.md` | 104 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 059 | `059-srcdata-no-es-payload-es-el-wptr-del-ring.md` | 105 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 061 | `061-srcdata-dos-valores-constante-por-derivacion.md` | 98 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 062 | `062-citas-de-c-009-desplazadas-y-tabla-de-030-invertida.md` | 109 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 062 | `062-citas-de-c-009-desplazadas-y-tabla-de-030-invertida.md` | 112 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 525 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 1576 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 2099 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 2216 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 2582 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 2638 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 2854 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 3331 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 4378 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | `063-memoria-sesion-smu-estado-persistente.md` | 4549 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 064 | `064-bitmap-vm-context-cntl-gfx8-f3-y-faults.md` | 11 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 064 | `064-bitmap-vm-context-cntl-gfx8-f3-y-faults.md` | 62 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 064 | `064-bitmap-vm-context-cntl-gfx8-f3-y-faults.md` | 155 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: hardware interpreta | - |
| 064 | `064-bitmap-vm-context-cntl-gfx8-f3-y-faults.md` | 171 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 064 | `064-bitmap-vm-context-cntl-gfx8-f3-y-faults.md` | 172 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 064 | `064-bitmap-vm-context-cntl-gfx8-f3-y-faults.md` | 176 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 065 | `065-offset-gmc-vs-mmhub-siete-registros.md` | 79 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 065 | `065-offset-gmc-vs-mmhub-siete-registros.md` | 137 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 065 | `065-offset-gmc-vs-mmhub-siete-registros.md` | 138 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 066 | `066-mapa-familias-por-fichero-c.md` | 117 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 068 | `068-orden-emision-ptba-invalidate-wait-pfp.md` | 89 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: Orden | - |
| 068 | `068-orden-emision-ptba-invalidate-wait-pfp.md` | 109 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: Orden | - |
| 068 | `068-orden-emision-ptba-invalidate-wait-pfp.md` | 110 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 068 | `068-orden-emision-ptba-invalidate-wait-pfp.md` | 111 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 069 | `069-f11-medido-y-ad12-discriminante-verificado.md` | 10 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 069 | `069-f11-medido-y-ad12-discriminante-verificado.md` | 145 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 070 | `070-contrato-host-smc-msg-arg-y-handshake.md` | 145 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 070 | `070-contrato-host-smc-msg-arg-y-handshake.md` | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 071 | `071-f2-ejecutado-bloqueado-por-saturacion-gpu.md` | 144 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 072 | `072-f3c-estatico-cond-exc-e-invalidate-response.md` | 103 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 072 | `072-f3c-estatico-cond-exc-e-invalidate-response.md` | 107 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 072 | `072-f3c-estatico-cond-exc-e-invalidate-response.md` | 121 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 072 | `072-f3c-estatico-cond-exc-e-invalidate-response.md` | 122 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 074 | `074-f2b-el-hardware-compone-el-pte.md` | 87 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 074 | `074-f2b-el-hardware-compone-el-pte.md` | 88 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 074 | `074-f2b-el-hardware-compone-el-pte.md` | 89 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 074 | `074-f2b-el-hardware-compone-el-pte.md` | 90 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 074 | `074-f2b-el-hardware-compone-el-pte.md` | 91 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 075 | `075-mapa-flags-pte-y-bifurcacion-host.md` | 161 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 081 | `081-la-tabla-dpm-son-1884-bytes-no-1120.md` | 89 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 081 | `081-system-access-mode-3-es-not-in-sys.md` | 152 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 081 | `081-system-access-mode-3-es-not-in-sys.md` | 162 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 082 | `082-el-acceso-no-mapeado-pide-pagina-prt.md` | 182 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 082 | `082-el-acceso-no-mapeado-pide-pagina-prt.md` | 183 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 083 | `083-sg-cache-coherency-l1-l2-y-asimetria.md` | 119 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 083 | `083-sg-cache-coherency-l1-l2-y-asimetria.md` | 138 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 084 | `084-mecanismo-de-copia-al-smc-y-assert-de-rango.md` | 32 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 084 | `084-mecanismo-de-copia-al-smc-y-assert-de-rango.md` | 34 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 084 | `084-se-packet-consumption-y-granularidad.md` | 121 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 084 | `084-se-packet-consumption-y-granularidad.md` | 123 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 085 | `085-sb-page-walker-invalidate-siempre-obligatorio.md` | 134 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | `085-sb-page-walker-invalidate-siempre-obligatorio.md` | 135 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | `085-sb-page-walker-invalidate-siempre-obligatorio.md` | 136 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | `085-sb-page-walker-invalidate-siempre-obligatorio.md` | 137 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | `085-sb-page-walker-invalidate-siempre-obligatorio.md` | 142 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 086 | `086-sf-vram-256m-visibles-y-la-bar.md` | 148 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 086 | `086-sf-vram-256m-visibles-y-la-bar.md` | 149 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 087 | `087-sf-gmc-8-1-nombre-no-predice-generacion.md` | 12 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | `087-sf-gmc-8-1-nombre-no-predice-generacion.md` | 168 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | `087-sf-gmc-8-1-nombre-no-predice-generacion.md` | 169 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | `087-sf-gmc-8-1-nombre-no-predice-generacion.md` | 174 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | `087-vm-fault-stop-0-y-ip-block-mask-confirma-047.md` | 123 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | `087-vm-fault-stop-0-y-ip-block-mask-confirma-047.md` | 186 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 088 | `088-pte-system-es-la-otra-mitad-de-system-access-mode.md` | 183 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NO esta | - |
| 089 | `089-gc-hwip-bloqueado-por-capacidad-y-resuelto-estaticamente.md` | 116 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 089 | `089-gc-hwip-bloqueado-por-capacidad-y-resuelto-estaticamente.md` | 198 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 090 | `090-sg-l1-l2-constantes-fijas-y-grano-de-2mib.md` | 170 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: POLICY | - |
| 090 | `090-sg-l1-l2-constantes-fijas-y-grano-de-2mib.md` | 171 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: POLICY | - |
| 090 | `090-sg-l1-l2-constantes-fijas-y-grano-de-2mib.md` | 172 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: POLICY | - |
| 092 | `092-sc-7-tipos-de-fault-y-3-enables-cada-uno.md` | 202 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | `092-sc-7-tipos-de-fault-y-3-enables-cada-uno.md` | 203 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | `092-sc-7-tipos-de-fault-y-3-enables-cada-uno.md` | 204 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | `092-sc-7-tipos-de-fault-y-3-enables-cada-uno.md` | 205 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | `092-sc-7-tipos-de-fault-y-3-enables-cada-uno.md` | 208 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 094 | `094-sd-presupuesto-del-frame-dos-cifras-viejas.md` | 175 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 094 | `094-sd-presupuesto-del-frame-dos-cifras-viejas.md` | 176 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 094 | `094-sd-presupuesto-del-frame-dos-cifras-viejas.md` | 177 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 095 | `095-camino-termico-y-un-assert-inerte.md` | 127 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | `095-los-5-sin-medir-y-los-2-limite-reconcilian.md` | 148 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 095 | `095-los-5-sin-medir-y-los-2-limite-reconcilian.md` | 151 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 095 | `095-se-pfp-me-ce-tres-motores-tres-icache.md` | 12 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | `095-se-pfp-me-ce-tres-motores-tres-icache.md` | 151 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | `095-se-pfp-me-ce-tres-motores-tres-icache.md` | 152 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | `095-se-pfp-me-ce-tres-motores-tres-icache.md` | 153 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | `095-se-pfp-me-ce-tres-motores-tres-icache.md` | 154 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | `095-se-pfp-me-ce-tres-motores-tres-icache.md` | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: hardware hace | - |
| 095 | `095-se-pfp-me-ce-tres-motores-tres-icache.md` | 174 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 096 | `096-se-mecanismo-de-fence-completo.md` | 44 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 096 | `096-se-mecanismo-de-fence-completo.md` | 232 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 096 | `096-se-mecanismo-de-fence-completo.md` | 233 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 096 | `096-se-mecanismo-de-fence-completo.md` | 234 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 096 | `096-se-mecanismo-de-fence-completo.md` | 235 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 096 | `096-se-mecanismo-de-fence-completo.md` | 236 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 096 | `096-se-mecanismo-de-fence-completo.md` | 238 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 166 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 186 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 187 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 188 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 189 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | `097-se-observado-24-de-24-pares-eop-delta-1.md` | 190 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 098 | `098-prt-funciona-al-reves-en-gfx9.md` | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 098 | `098-se-observado-retraso-fence-0-a-4.md` | 104 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 098 | `098-se-observado-retraso-fence-0-a-4.md` | 105 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 099 | `099-sc-observado-prt-enmascara-el-fault-de-pde0.md` | 159 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 099 | `099-sc-observado-prt-enmascara-el-fault-de-pde0.md` | 160 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 099 | `099-sc-observado-prt-enmascara-el-fault-de-pde0.md` | 161 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 099 | `099-sc-observado-prt-enmascara-el-fault-de-pde0.md` | 162 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 100 | `100-el-limite-de-la-sram-del-smc-es-el-doble-de-la-sram-declarada.md` | 7 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `100-el-limite-de-la-sram-del-smc-es-el-doble-de-la-sram-declarada.md` | 17 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `100-el-limite-de-la-sram-del-smc-es-el-doble-de-la-sram-declarada.md` | 195 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `100-sf-observado-gart-65536-y-el-sysfs-que-no-lo-dice.md` | 113 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `100-sf-observado-gart-65536-y-el-sysfs-que-no-lo-dice.md` | 127 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1000-de-pci-enumeration-a-gpu-ready-la-secuencia-completa.md` | 300 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 100 | `1002-correccion-a-105-el-1024-no-es-el-anillo-de-interrupcion-y-el-real-tiene-4096.md` | 275 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 313 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 314 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 315 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 316 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 317 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 369 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 375 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-mandato-no-es-el-que-existe.md` | 563 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 172 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 224 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 265 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 274 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 275 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 276 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 276 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 277 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 278 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 278 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 306 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 100 | `1004-eng-invalidate-es-gfx9-y-no-gfx8.md` | 309 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 101 | `101-gfx8-decodifica-el-tipo-de-fault-y-nadie-lo-lee.md` | 44 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `101-gfx8-decodifica-el-tipo-de-fault-y-nadie-lo-lee.md` | 118 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 17 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 45 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 48 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 181 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 190 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 192 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 205 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 207 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 325 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 346 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1010-el-limite-de-paginas-de-ttm-que-amdgpu-imprime-como-5907m.md` | 349 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1011-el-grep-de-ad8-no-puede-distinguir-y-el-isa-si.md` | 184 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1011-el-grep-de-ad8-no-puede-distinguir-y-el-isa-si.md` | 185 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | `1011-el-grep-de-ad8-no-puede-distinguir-y-el-isa-si.md` | 185 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 102 | `102-sa-despacho-cpu-vs-sdma-y-la-rama-que-no-existe.md` | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `102-sa-despacho-cpu-vs-sdma-y-la-rama-que-no-existe.md` | 161 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `102-sa-despacho-cpu-vs-sdma-y-la-rama-que-no-existe.md` | 162 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md` | 25 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md` | 102 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md` | 142 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md` | 168 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md` | 229 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | `1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md` | 230 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 104 | `104-once-usos-de-dpm-table-start-y-el-hueco-de-108.md` | 5 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 104 | `104-once-usos-de-dpm-table-start-y-el-hueco-de-108.md` | 19 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 105 | `105-se-ih-y-el-camino-real-de-los-faults.md` | 178 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 105 | `105-se-ih-y-el-camino-real-de-los-faults.md` | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 106 | `106-funcion-no-existe-y-el-trigger-es-software.md` | 33 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 106 | `106-funcion-no-existe-y-el-trigger-es-software.md` | 80 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 106 | `106-funcion-no-existe-y-el-trigger-es-software.md` | 153 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 107 | `107-el-reset-vacia-tlb-sin-request.md` | 117 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: compa | - |
| 107 | `107-sc-function-always-2-de-7-y-el-ring-usa-1.md` | 151 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: compa | - |
| 107 | `107-sc-function-always-2-de-7-y-el-ring-usa-1.md` | 152 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: compa | - |
| 108 | `108-el-determinante-del-desfase-y-lo-que-no-se-puede-cerrar.md` | 85 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | `108-el-determinante-del-desfase-y-lo-que-no-se-puede-cerrar.md` | 112 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | `108-sd-pfp-escribe-me-espera-punto-de-visibilidad.md` | 145 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | `108-sd-pfp-escribe-me-espera-punto-de-visibilidad.md` | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | `108-sd-pfp-escribe-me-espera-punto-de-visibilidad.md` | 151 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 109 | `109-sd-un-anillo-dos-motores-tres-esperas.md` | 134 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 109 | `109-sd-un-anillo-dos-motores-tres-esperas.md` | 135 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 109 | `109-sd-un-anillo-dos-motores-tres-esperas.md` | 136 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 110 | `110-funcion-es-de-wait-reg-mem-no-del-invalidate.md` | 194 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 111 | `111-sd-next-ib-el-pfp-lo-busca.md` | 137 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 111 | `111-sd-next-ib-el-pfp-lo-busca.md` | 138 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 111 | `111-sd-next-ib-el-pfp-lo-busca.md` | 139 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 112 | `112-registros-del-walker-en-gmc-8-1-y-las-7-familias.md` | 276 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no documentad | - |
| 112 | `112-registros-del-walker-en-gmc-8-1-y-las-7-familias.md` | 289 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no documentad | - |
| 113 | `113-dpm-table-start-es-la-base-literal-y-los-once-usos-son-correctos.md` | 12 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 113 | `113-dpm-table-start-es-la-base-literal-y-los-once-usos-son-correctos.md` | 19 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 18 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 43 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 94 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 181 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 199 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 237 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 276 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 280 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 325 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | `114-implgate-cinco-bugs-propios-y-una-afirmacion-falsa.md` | 328 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 115 | `115-firmware-smc-si-en-el-corpus.md` | 270 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 115 | `115-sd-cuando-hay-invalidate-regla-por-vmid.md` | 188 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 115 | `115-sd-cuando-hay-invalidate-regla-por-vmid.md` | 189 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 116 | `116-sd-use-cpu-nunca-dispara-geometria.md` | 13 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | `116-sd-use-cpu-nunca-dispara-geometria.md` | 205 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | `116-sd-use-cpu-nunca-dispara-geometria.md` | 206 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | `116-sd-use-cpu-nunca-dispara-geometria.md` | 209 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | `116-sd-use-cpu-nunca-dispara-geometria.md` | 211 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 117 | `117-doclint-no-se-mira-el-80.md` | 167 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 118 | `118-toolaudit-no-ve-el-denominador.md` | 194 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 119 | `119-el-fichero-que-si-corre-esta-a-una-tabla.md` | 99 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 119 | `119-el-fichero-que-si-corre-esta-a-una-tabla.md` | 100 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 119 | `119-el-fichero-que-si-corre-esta-a-una-tabla.md` | 101 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 119 | `119-el-fichero-que-si-corre-esta-a-una-tabla.md` | 103 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 120 | `120-las-325-referencias-rotas-no-san-325.md` | 126 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 120 | `120-las-325-referencias-rotas-no-san-325.md` | 127 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 121 | `121-la-deuda-de-340-no-se-limpa-se-evita.md` | 103 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | `121-la-deuda-de-340-no-se-limpa-se-evita.md` | 106 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | `121-pm4-estatico-y-la-contabilidad-cuadra.md` | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 121 | `121-pm4-estatico-y-la-contabilidad-cuadra.md` | 222 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 121 | `121-tabla-de-relojes-dpm-reconstruida.md` | 5 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | `121-tabla-de-relojes-dpm-reconstruida.md` | 55 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | `121-tabla-de-relojes-dpm-reconstruida.md` | 120 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 122 | `122-e-los-10-wait-reg-mem-son-hdp-flush.md` | 181 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 122 | `122-e-los-10-wait-reg-mem-son-hdp-flush.md` | 182 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 122 | `122-e-los-10-wait-reg-mem-son-hdp-flush.md` | 183 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 122 | `122-para-que-el-encuadre-de-dos-fuentes-resulte-honesto.md` | 125 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 123 | `123-e-cuadra-cuando-se-llama-hdp-flush.md` | 209 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 123 | `123-e-cuadra-cuando-se-llama-hdp-flush.md` | 260 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 124 | `124-g-coherencia-page-tables-por-orden.md` | 100 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 124 | `124-g-coherencia-page-tables-por-orden.md` | 101 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 124 | `124-g-coherencia-page-tables-por-orden.md` | 129 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 124 | `124-g-coherencia-page-tables-por-orden.md` | 130 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 124 | `124-g-coherencia-page-tables-por-orden.md` | 131 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 125 | `125-casi-la-mitad-de-las-multiplicidades-no-son-corrobora.md` | 112 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: speci | - |
| 125 | `125-casi-la-mitad-de-las-multiplicidades-no-son-corrobora.md` | 115 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: speci | - |
| 126 | `126-g-el-precio-de-la-coherencia.md` | 128 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 126 | `126-g-el-precio-de-la-coherencia.md` | 129 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 127 | `127-align-mask-no-se-opone-a-emit-ib-size.md` | 120 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 127 | `127-g-hay-una-cache-l2-de-fragmentos.md` | 148 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 127 | `127-g-hay-una-cache-l2-de-fragmentos.md` | 149 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 127 | `127-g-hay-una-cache-l2-de-fragmentos.md` | 151 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 128 | `128-c-dos-mecanismos-de-invalidate.md` | 88 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | `128-c-dos-mecanismos-de-invalidate.md` | 167 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | `128-c-dos-mecanismos-de-invalidate.md` | 168 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | `128-c-dos-mecanismos-de-invalidate.md` | 169 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | `128-c-dos-mecanismos-de-invalidate.md` | 170 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 129 | `129-a-translate-further-y-fragment-size.md` | 139 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 129 | `129-a-translate-further-y-fragment-size.md` | 140 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 130 | `130-ab-el-l1-guarda-un-pte-por-fragmento.md` | 164 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | `130-ab-el-l1-guarda-un-pte-por-fragmento.md` | 165 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | `130-ab-el-l1-guarda-un-pte-por-fragmento.md` | 166 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | `130-ab-el-l1-guarda-un-pte-por-fragmento.md` | 202 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | `130-la-clase-count-menos-n-barrida.md` | 7 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 130 | `130-la-clase-count-menos-n-barrida.md` | 208 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | `130-pm4-contrastado-contra-el-codigo-del-ko.md` | 186 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 131 | `131-c-prt-no-esta-bloqueado.md` | 12 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | `131-c-prt-no-esta-bloqueado.md` | 159 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | `131-c-prt-no-esta-bloqueado.md` | 160 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | `131-c-prt-no-esta-bloqueado.md` | 165 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | `131-c-prt-no-esta-bloqueado.md` | 168 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | `131-c-prt-no-esta-bloqueado.md` | 179 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | `131-los-26-count-valen-uno-y-esta-medido.md` | 5 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | `131-los-26-count-valen-uno-y-esta-medido.md` | 226 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 132 | `132-a-flags-de-pte-frag-y-tf.md` | 207 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 132 | `132-a-flags-de-pte-frag-y-tf.md` | 208 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 132 | `132-a-flags-de-pte-frag-y-tf.md` | 209 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 133 | `133-g-el-mtype-no-existe-en-gfx8.md` | 106 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 133 | `133-g-el-mtype-no-existe-en-gfx8.md` | 147 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 135 | `135-packet3-clasificados-por-quien-los-usa.md` | 163 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 135 | `135-packet3-clasificados-por-quien-los-usa.md` | 164 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 135 | `135-packet3-clasificados-por-quien-los-usa.md` | 201 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 136 | `136-g-la-cadena-de-coherencia-cerrada.md` | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 136 | `136-g-la-cadena-de-coherencia-cerrada.md` | 144 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 137 | `137-c-configuracion-tlb-l2-gfx8.md` | 129 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | `137-c-configuracion-tlb-l2-gfx8.md` | 130 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | `137-c-configuracion-tlb-l2-gfx8.md` | 131 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | `137-c-configuracion-tlb-l2-gfx8.md` | 132 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | `137-c-configuracion-tlb-l2-gfx8.md` | 134 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 138 | `138-c-protection-faults-y-la-geometria.md` | 17 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | `138-c-protection-faults-y-la-geometria.md` | 260 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | `138-c-protection-faults-y-la-geometria.md` | 261 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | `138-c-protection-faults-y-la-geometria.md` | 262 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | `138-c-protection-faults-y-la-geometria.md` | 269 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | `138-c-protection-faults-y-la-geometria.md` | 281 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 300 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 349 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 350 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 351 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 352 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 357 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 372 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | `139-formato-del-pte-y-del-pde-y-la-homonimia-prt.md` | 393 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 140 | `140-f-mapa-de-direcciones-observado.md` | 19 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | `140-f-mapa-de-direcciones-observado.md` | 264 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | `140-f-mapa-de-direcciones-observado.md` | 265 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | `140-f-mapa-de-direcciones-observado.md` | 266 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | `140-f-mapa-de-direcciones-observado.md` | 267 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 142 | `142-f-agp-vacia-y-bloque-hdp-sin-nombre.md` | 252 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | mmHDP_ | `mmHDP_` |
| 142 | `142-f-agp-vacia-y-bloque-hdp-sin-nombre.md` | 255 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmHDP_ | - |
| 142 | `142-f-agp-vacia-y-bloque-hdp-sin-nombre.md` | 260 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmHDP_ | - |
| 143 | `143-c-registros-golden-y-ciclo-del-prt.md` | 178 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 143 | `143-c-registros-golden-y-ciclo-del-prt.md` | 238 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 143 | `143-c-registros-golden-y-ciclo-del-prt.md` | 240 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 143 | `143-c-registros-golden-y-ciclo-del-prt.md` | 241 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 143 | `143-c-registros-golden-y-ciclo-del-prt.md` | 243 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 144 | `144-prt-cierra-y-el-corpus-no-tiene-uapi.md` | 226 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 144 | `144-prt-cierra-y-el-corpus-no-tiene-uapi.md` | 260 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 145 | `145-el-99-del-corpus-es-amd.md` | 160 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 146 | `146-el-makefile-no-es-un-manifiesto.md` | 111 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 147 | `147-display-modelo-de-programacion-dce100.md` | 197 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 147 | `147-display-modelo-de-programacion-dce100.md` | 198 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: timing | - |
| 147 | `147-display-modelo-de-programacion-dce100.md` | 199 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: timing | - |
| 147 | `147-display-modelo-de-programacion-dce100.md` | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: timing | - |
| 148 | `148-display-sink-generico-y-un-bit-de-salida.md` | 203 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: timing | - |
| 148 | `148-display-sink-generico-y-un-bit-de-salida.md` | 222 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 148 | `148-display-sink-generico-y-un-bit-de-salida.md` | 223 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 148 | `148-display-sink-generico-y-un-bit-de-salida.md` | 224 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 149 | `149-display-la-frontera-dm-dc.md` | 207 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 149 | `149-display-la-frontera-dm-dc.md` | 208 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 150 | `150-display-signal-type-mascara-o-enum.md` | 198 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 150 | `150-display-signal-type-mascara-o-enum.md` | 199 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 150 | `150-display-signal-type-mascara-o-enum.md` | 200 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 151 | `151-display-dml1-vs-dml2-medido.md` | 134 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 151 | `151-display-dml1-vs-dml2-medido.md` | 156 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 151 | `151-display-dml1-vs-dml2-medido.md` | 157 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 151 | `151-display-dml1-vs-dml2-medido.md` | 177 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 152 | `152-display-dc-link-la-tercera-pieza.md` | 193 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | `152-display-dc-link-la-tercera-pieza.md` | 194 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | `152-display-dc-link-la-tercera-pieza.md` | 195 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | `152-display-dc-link-la-tercera-pieza.md` | 196 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | `152-display-dc-link-la-tercera-pieza.md` | 220 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 153 | `153-display-ddi-y-el-identificador-de-objeto.md` | 219 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | `153-display-ddi-y-el-identificador-de-objeto.md` | 220 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | `153-display-ddi-y-el-identificador-de-objeto.md` | 221 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | `153-display-ddi-y-el-identificador-de-objeto.md` | 230 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | `153-display-ddi-y-el-identificador-de-objeto.md` | 254 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | `153-display-ddi-y-el-identificador-de-objeto.md` | 282 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 154 | `154-display-donde-se-decide-la-senal.md` | 12 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | `154-display-donde-se-decide-la-senal.md` | 67 | `UNKNOWN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | `154-display-donde-se-decide-la-senal.md` | 199 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | `154-display-donde-se-decide-la-senal.md` | 200 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | `154-display-donde-se-decide-la-senal.md` | 202 | `UNKNOWN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | `154-display-donde-se-decide-la-senal.md` | 203 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | `154-display-donde-se-decide-la-senal.md` | 232 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 155 | `155-el-dc-de-esta-maquina-es-dce-11-2.md` | 182 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | `155-el-dc-de-esta-maquina-es-dce-11-2.md` | 194 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | `155-el-dc-de-esta-maquina-es-dce-11-2.md` | 218 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | `155-el-dc-de-esta-maquina-es-dce-11-2.md` | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | `155-el-dc-de-esta-maquina-es-dce-11-2.md` | 220 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | `155-el-dc-de-esta-maquina-es-dce-11-2.md` | 221 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | `155-el-dc-de-esta-maquina-es-dce-11-2.md` | 243 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 156 | `156-la-identidad-de-un-camino-de-codigo.md` | 165 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | `156-la-identidad-de-un-camino-de-codigo.md` | 166 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | `156-la-identidad-de-un-camino-de-codigo.md` | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | `156-la-identidad-de-un-camino-de-codigo.md` | 168 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | `156-la-identidad-de-un-camino-de-codigo.md` | 195 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 157 | `157-display-16-null-y-dos-mecanismos.md` | 182 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 157 | `157-display-16-null-y-dos-mecanismos.md` | 183 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 157 | `157-display-16-null-y-dos-mecanismos.md` | 185 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 158 | `158-el-par-struct-tabla-y-no-el-chip.md` | 182 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 158 | `158-el-par-struct-tabla-y-no-el-chip.md` | 183 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 158 | `158-el-par-struct-tabla-y-no-el-chip.md` | 184 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 158 | `158-el-par-struct-tabla-y-no-el-chip.md` | 212 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 159 | `159-dce112-52-funciones-21-por-ciento-de-dce110.md` | 165 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 159 | `159-dce112-52-funciones-21-por-ciento-de-dce110.md` | 166 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 159 | `159-dce112-52-funciones-21-por-ciento-de-dce110.md` | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 160 | `160-dp-4-carriles-hbr3-32-gbps.md` | 117 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | `160-dp-4-carriles-hbr3-32-gbps.md` | 238 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | `160-dp-4-carriles-hbr3-32-gbps.md` | 244 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | `160-dp-4-carriles-hbr3-32-gbps.md` | 246 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | `160-dp-4-carriles-hbr3-32-gbps.md` | 315 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 161 | `161-reloj-600-mhz-y-el-bios.md` | 210 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 161 | `161-reloj-600-mhz-y-el-bios.md` | 211 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 161 | `161-reloj-600-mhz-y-el-bios.md` | 212 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 162 | `162-seis-tuberias-y-el-bomb-de-interrupciones.md` | 237 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: TIMIN | - |
| 162 | `162-seis-tuberias-y-el-bomb-de-interrupciones.md` | 238 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: TIMIN | - |
| 162 | `162-seis-tuberias-y-el-bomb-de-interrupciones.md` | 239 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: TIMIN | - |
| 163 | `163-log-observado-polaris12-y-cero-crtc.md` | 13 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | `163-log-observado-polaris12-y-cero-crtc.md` | 180 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | `163-log-observado-polaris12-y-cero-crtc.md` | 222 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | `163-log-observado-polaris12-y-cero-crtc.md` | 223 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | `163-log-observado-polaris12-y-cero-crtc.md` | 224 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | `163-log-observado-polaris12-y-cero-crtc.md` | 225 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | `163-log-observado-polaris12-y-cero-crtc.md` | 254 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 164 | `164-lexa-pro-y-el-gart-fija-mc-mask.md` | 172 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 164 | `164-lexa-pro-y-el-gart-fija-mc-mask.md` | 173 | `NOT_DETERMINED` | `UN_REGISTRO` | 3 | frase: un registro | - |
| 164 | `164-lexa-pro-y-el-gart-fija-mc-mask.md` | 174 | `NOT_DETERMINED` | `UN_REGISTRO` | 3 | frase: un registro | - |
| 164 | `164-lexa-pro-y-el-gart-fija-mc-mask.md` | 205 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 164 | `164-lexa-pro-y-el-gart-fija-mc-mask.md` | 234 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 165 | `165-cuanto-de-display-es-generico.md` | 154 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 165 | `165-cuanto-de-display-es-generico.md` | 155 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 95 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 163 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 177 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 183 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 184 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 185 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | `166-dos-conectores-dvi-y-hdmi.md` | 248 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 167 | `167-los-dos-conectores-dvi-y-hdmi-en-registros.md` | 243 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 167 | `167-los-dos-conectores-dvi-y-hdmi-en-registros.md` | 244 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 167 | `167-los-dos-conectores-dvi-y-hdmi-en-registros.md` | 245 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 167 | `167-los-dos-conectores-dvi-y-hdmi-en-registros.md` | 250 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 170 | `170-no-existe-codigo-que-reutilizar.md` | 12 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | `170-no-existe-codigo-que-reutilizar.md` | 139 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | `170-no-existe-codigo-que-reutilizar.md` | 140 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | `170-no-existe-codigo-que-reutilizar.md` | 141 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | `170-no-existe-codigo-que-reutilizar.md` | 142 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | `170-no-existe-codigo-que-reutilizar.md` | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convención | - |
| 170 | `170-no-existe-codigo-que-reutilizar.md` | 187 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 172 | `172-la-capa-generica-y-un-69-que-era-falso.md` | 175 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 172 | `172-la-capa-generica-y-un-69-que-era-falso.md` | 176 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 172 | `172-la-capa-generica-y-un-69-que-era-falso.md` | 177 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 173 | `173-el-secuenciador-es-un-interprete.md` | 163 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 173 | `173-el-secuenciador-es-un-interprete.md` | 164 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 173 | `173-el-secuenciador-es-un-interprete.md` | 165 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 173 | `173-el-secuenciador-es-un-interprete.md` | 166 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 174 | `174-el-87-por-ciento-son-llamadas-directas.md` | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 174 | `174-el-87-por-ciento-son-llamadas-directas.md` | 120 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 174 | `174-el-87-por-ciento-son-llamadas-directas.md` | 121 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | `175-para-otra-gpu-entre-24-y-75.md` | 76 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | `175-para-otra-gpu-entre-24-y-75.md` | 149 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | `175-para-otra-gpu-entre-24-y-75.md` | 150 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | `175-para-otra-gpu-entre-24-y-75.md` | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | `175-para-otra-gpu-entre-24-y-75.md` | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 176 | `176-longitudes-de-bar-sin-root-y-mapa-de-bloques-fuera-de-todo-corpus.md` | 28 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 177 | `177-res-cpu-visible-cierra-secF.md` | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 177 | `177-res-cpu-visible-cierra-secF.md` | 214 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 178 | `178-los-dos-canales-son-disjuntos.md` | 176 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | `178-los-dos-canales-son-disjuntos.md` | 177 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | `178-los-dos-canales-son-disjuntos.md` | 178 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | `178-los-dos-canales-son-disjuntos.md` | 179 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | `178-los-dos-canales-son-disjuntos.md` | 187 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 179 | `179-cuatro-clases-y-dos-por-ciento-9.md` | 144 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 179 | `179-cuatro-clases-y-dos-por-ciento-9.md` | 145 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 179 | `179-cuatro-clases-y-dos-por-ciento-9.md` | 146 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 179 | `179-cuatro-clases-y-dos-por-ciento-9.md` | 150 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 168 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 169 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 170 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 171 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 176 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | `181-de-443839-lineas-123571-alcanzables.md` | 180 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 183 | `183-dos-formatos-de-iv-y-la-version-del-bloque-que-decide.md` | 13 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 183 | `183-dos-formatos-de-iv-y-la-version-del-bloque-que-decide.md` | 135 | `NOT_PROVEN` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 184 | `184-veintiuna-guardas-y-la-cadena-de-identidad.md` | 174 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 184 | `184-veintiuna-guardas-y-la-cadena-de-identidad.md` | 175 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 184 | `184-veintiuna-guardas-y-la-cadena-de-identidad.md` | 179 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | `185-siete-raices-y-el-motor-no-es-dml.md` | 133 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | `185-siete-raices-y-el-motor-no-es-dml.md` | 151 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | `185-siete-raices-y-el-motor-no-es-dml.md` | 152 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | `185-siete-raices-y-el-motor-no-es-dml.md` | 153 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | `185-siete-raices-y-el-motor-no-es-dml.md` | 154 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | `185-siete-raices-y-el-motor-no-es-dml.md` | 158 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | `185-siete-raices-y-el-motor-no-es-dml.md` | 164 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 186 | `186-685-afirmaciones-abiertas-no-era-un-resultado.md` | 37 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 187 | `187-dos-caracteres-en-un-patron.md` | 109 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | `187-dos-caracteres-en-un-patron.md` | 121 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | `187-dos-caracteres-en-un-patron.md` | 122 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | `187-dos-caracteres-en-un-patron.md` | 123 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | `187-dos-caracteres-en-un-patron.md` | 126 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 188 | `188-el-nombre-del-op-12-y-la-cita-equivocada.md` | 178 | `NOT_PROVEN` | `POR_DEFINICION` | 2 | frase: convención | - |
| 190 | `190-dos-registros-de-version-ip-y-tmz-confirmado-en-runtime.md` | 222 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 193 | `193-tabla-de-asic-desde-el-binario.md` | 59 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 193 | `193-tabla-de-asic-desde-el-binario.md` | 119 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 198 | `198-tres-correcciones-de-la-poda.md` | 124 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 198 | `198-tres-correcciones-de-la-poda.md` | 125 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 198 | `198-tres-correcciones-de-la-poda.md` | 126 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 198 | `198-tres-correcciones-de-la-poda.md` | 131 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 198 | `198-tres-correcciones-de-la-poda.md` | 134 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 199 | `199-seccion-f-la-base-de-vram-y-el-agujero.md` | 135 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: Un solo regist | - |
| 199 | `199-seccion-f-la-base-de-vram-y-el-agujero.md` | 152 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: Un solo registro | - |
| 199 | `199-seccion-f-la-base-de-vram-y-el-agujero.md` | 153 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: Un solo registro | - |
| 199 | `199-seccion-f-la-base-de-vram-y-el-agujero.md` | 163 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: Un solo regist | - |
| 203 | `203-los-headers-son-vocabulario-no-mapa-de-uso.md` | 111 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 204 | `204-los-256-mib-del-gart-son-semantica.md` | 138 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 204 | `204-los-256-mib-del-gart-son-semantica.md` | 144 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 208 | `208-lut-de-voltaje-del-smc.md` | 161 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 209 | `209-siete-campos-de-pmfuses-se-suben-a-cero.md` | 100 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 210 | `210-sc-handshake-de-completacion-existe-y-072-se-equivoco.md` | 48 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: inmediat | - |
| 210 | `210-sc-handshake-de-completacion-existe-y-072-se-equivoco.md` | 163 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 210 | `210-sc-handshake-de-completacion-existe-y-072-se-equivoco.md` | 164 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 210 | `210-sc-handshake-de-completacion-existe-y-072-se-equivoco.md` | 165 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 210 | `210-sc-handshake-de-completacion-existe-y-072-se-equivoco.md` | 168 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: inmediat | - |
| 210 | `210-sc-handshake-de-completacion-existe-y-072-se-equivoco.md` | 203 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: inmediat | - |
| 211 | `211-sc-invalidate-request-response-16-bits.md` | 150 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | `211-sc-invalidate-request-response-16-bits.md` | 151 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | `211-sc-invalidate-request-response-16-bits.md` | 152 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | `211-sc-invalidate-request-response-16-bits.md` | 153 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | `211-sc-invalidate-request-response-16-bits.md` | 155 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 218 | `218-sd-el-vm-flush-lo-pide-el-scheduler.md` | 138 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 218 | `218-sd-el-vm-flush-lo-pide-el-scheduler.md` | 139 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 218 | `218-sd-el-vm-flush-lo-pide-el-scheduler.md` | 149 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 218 | `218-sd-el-vm-flush-lo-pide-el-scheduler.md` | 171 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 223 | `223-resultado-negativo-estados-ppt-sin-relojes.md` | 99 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 224 | `224-dpm-levels-8-contra-una-cuenta-solo-validada-con-ge-1.md` | 49 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 231 | `231-ip-version-del-firmware-cierra-gfx-hwip.md` | 26 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 231 | `231-ip-version-del-firmware-cierra-gfx-hwip.md` | 177 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 231 | `231-ip-version-del-firmware-cierra-gfx-hwip.md` | 180 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 232 | `232-coherencia-cpu-gpu-tres-mecanismos.md` | 196 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | `mmHDP_DEBUG0` |
| 233 | `233-escritor-cpu-desactivado-por-dos-razones.md` | 168 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 235 | `235-los-600mhz-son-el-techo-de-hdmi-2-0.md` | 13 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | `235-los-600mhz-son-el-techo-de-hdmi-2-0.md` | 127 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | `235-los-600mhz-son-el-techo-de-hdmi-2-0.md` | 158 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | `235-los-600mhz-son-el-techo-de-hdmi-2-0.md` | 159 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | `235-los-600mhz-son-el-techo-de-hdmi-2-0.md` | 160 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 236 | `236-los-nueve-bloques-ip.md` | 141 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | `236-los-nueve-bloques-ip.md` | 142 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | `236-los-nueve-bloques-ip.md` | 143 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | `236-los-nueve-bloques-ip.md` | 144 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | `236-los-nueve-bloques-ip.md` | 145 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | `236-los-nueve-bloques-ip.md` | 177 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 237 | `237-la-densidad-de-delegacion.md` | 128 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 237 | `237-la-densidad-de-delegacion.md` | 129 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 237 | `237-la-densidad-de-delegacion.md` | 130 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 237 | `237-la-densidad-de-delegacion.md` | 131 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 238 | `238-la-densidad-clasifica-el-fichero.md` | 134 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 238 | `238-la-densidad-clasifica-el-fichero.md` | 135 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 238 | `238-la-densidad-clasifica-el-fichero.md` | 136 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 238 | `238-la-densidad-clasifica-el-fichero.md` | 137 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 240 | `240-la-cadena-de-identidad-observada.md` | 128 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convención | - |
| 240 | `240-la-cadena-de-identidad-observada.md` | 129 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convención | - |
| 240 | `240-la-cadena-de-identidad-observada.md` | 138 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convención | - |
| 241 | `241-el-eslabon-que-faltaba-era-un-literal.md` | 82 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 241 | `241-el-eslabon-que-faltaba-era-un-literal.md` | 83 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 241 | `241-el-eslabon-que-faltaba-era-un-literal.md` | 137 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 242 | `242-los-registros-caben-en-bar5-con-4x-de-holgura.md` | 280 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convención | `mmSDMA_`, `mmSRBM_` |
| 243 | `243-los-5907-mib-de-gtt-es-la-mitad-de-la-ram.md` | 137 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 244 | `244-182-demostrado-desde-el-binario-cero-escrituras.md` | 148 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 246 | `246-la-coherencia-de-gfx8-son-tres-registros-y-ninguno-de-cache.md` | 180 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmDB_RMI_L2_CACHE_CON | - |
| 246 | `246-la-coherencia-de-gfx8-son-tres-registros-y-ninguno-de-cache.md` | 180 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmDB_RMI_L2_CACHE_CON | - |
| 246 | `246-la-coherencia-de-gfx8-son-tres-registros-y-ninguno-de-cache.md` | 182 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmDB_RMI_L2_CACHE_CON | - |
| 246 | `246-la-coherencia-de-gfx8-son-tres-registros-y-ninguno-de-cache.md` | 225 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no hay documentaci | - |
| 246 | `246-la-coherencia-de-gfx8-son-tres-registros-y-ninguno-de-cache.md` | 227 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no hay documentaci | - |
| 251 | `251-leer-la-temperatura-no-es-leer-un-registro.md` | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 251 | `251-leer-la-temperatura-no-es-leer-un-registro.md` | 178 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 16 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 168 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 171 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 200 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 203 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 211 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 214 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | `253-edge-sale-de-gfxtemperature-y-hotspot-de-soctemperature.md` | 223 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | `254-la-cabecera-de-los-20-firmware-valida-20-de-20.md` | 193 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | `254-la-cabecera-de-los-20-firmware-valida-20-de-20.md` | 195 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | `254-la-cabecera-de-los-20-firmware-valida-20-de-20.md` | 197 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | `254-la-cabecera-de-los-20-firmware-valida-20-de-20.md` | 199 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | `254-la-cabecera-de-los-20-firmware-valida-20-de-20.md` | 201 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | `254-la-cabecera-de-los-20-firmware-valida-20-de-20.md` | 203 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | `254-la-cabecera-de-los-20-firmware-valida-20-de-20.md` | 204 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 255 | `255-las-tres-contradicciones-son-el-mismo-intermedio.md` | 212 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 255 | `255-las-tres-contradicciones-son-el-mismo-intermedio.md` | 215 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 256 | `256-la-tabla-de-spread-spectrum-que-si-alcanza-mi-asic.md` | 111 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Inmed | - |
| 256 | `256-la-tabla-de-spread-spectrum-que-si-alcanza-mi-asic.md` | 138 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Inmed | - |
| 256 | `256-la-tabla-de-spread-spectrum-que-si-alcanza-mi-asic.md` | 195 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Inmed | - |
| 257 | `257-sched-hw-submission-2-y-el-anillo-gfx-son-2048-dwords.md` | 160 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 257 | `257-sched-hw-submission-2-y-el-anillo-gfx-son-2048-dwords.md` | 162 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 257 | `257-sched-hw-submission-2-y-el-anillo-gfx-son-2048-dwords.md` | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 257 | `257-sched-hw-submission-2-y-el-anillo-gfx-son-2048-dwords.md` | 179 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | `258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md` | 209 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | `258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md` | 211 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | `258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md` | 235 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | `258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md` | 237 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | `258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md` | 250 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | `258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md` | 251 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 259 | `259-la-clave-primaria-de-findings-no-es-unica.md` | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 259 | `259-la-clave-primaria-de-findings-no-es-unica.md` | 120 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 261 | `261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md` | 193 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | `261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md` | 196 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | `261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md` | 199 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | `261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md` | 211 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | `261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md` | 221 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | `261-banco-de-pruebas-de-computo-y-el-bug-que-lo-invalido.md` | 221 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 262 | `262-dos-escritores-en-la-misma-ram-del-smc.md` | 32 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | `262-dos-escritores-en-la-misma-ram-del-smc.md` | 113 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 262 | `262-dos-escritores-en-la-misma-ram-del-smc.md` | 117 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | `262-dos-escritores-en-la-misma-ram-del-smc.md` | 159 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 262 | `262-el-control-tardo-tres-versiones-en-ser-un-control.md` | 138 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | `262-el-control-tardo-tres-versiones-en-ser-un-control.md` | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | `262-el-control-tardo-tres-versiones-en-ser-un-control.md` | 157 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 263 | `263-el-avfs-se-sobrescribe-y-mi-hipotesis-era-invertida.md` | 7 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 263 | `263-el-avfs-se-sobrescribe-y-mi-hipotesis-era-invertida.md` | 95 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 263 | `263-el-avfs-se-sobrescribe-y-mi-hipotesis-era-invertida.md` | 131 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 263 | `263-el-avfs-se-sobrescribe-y-mi-hipotesis-era-invertida.md` | 133 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 265 | `265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md` | 12 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 265 | `265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md` | 137 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 265 | `265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md` | 139 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 265 | `265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md` | 157 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 265 | `265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md` | 157 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 266 | `266-la-codificacion-del-voltaje-no-es-un-float-y-el-avfs-la-incumple.md` | 78 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 269 | `269-el-techo-de-reloj-no-viene-de-la-tabla-de-voltajes.md` | 190 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 269 | `269-el-techo-de-reloj-no-viene-de-la-tabla-de-voltajes.md` | 199 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 270 | `270-el-banco-media-la-copia-pcie-no-el-kernel.md` | 142 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 271 | `271-el-kernel-de-cache-mide-la-tasa-de-emision.md` | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 271 | `271-el-kernel-de-cache-mide-la-tasa-de-emision.md` | 130 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 272 | `272-cg-mask-y-cu-mask-son-categorias-distintas.md` | 190 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 272 | `272-cg-mask-y-cu-mask-son-categorias-distintas.md` | 190 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 272 | `272-cg-mask-y-cu-mask-son-categorias-distintas.md` | 209 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 273 | `273-no-hay-layout-para-la-revision-7.md` | 84 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 273 | `273-no-hay-layout-para-la-revision-7.md` | 97 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 273 | `273-no-hay-layout-para-la-revision-7.md` | 120 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 274 | `274-la-poblacion-de-herramientas-era-112-y-contamos-31.md` | 54 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 275 | `275-los-9-no-resuelto-eran-7-del-mismo-patron.md` | 209 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 277 | `277-la-cadena-dependiente-no-expone-la-memoria-aunque-valide.md` | 121 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 277 | `277-la-cadena-dependiente-no-expone-la-memoria-aunque-valide.md` | 123 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 277 | `277-la-cadena-dependiente-no-expone-la-memoria-aunque-valide.md` | 139 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: latencia | - |
| 277 | `277-la-cadena-dependiente-no-expone-la-memoria-aunque-valide.md` | 141 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: latencia | - |
| 278 | `278-el-recuento-de-cobertura-de-polaris10-por-fin.md` | 117 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 278 | `278-el-recuento-de-cobertura-de-polaris10-por-fin.md` | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 279 | `279-rx550-mc-config-memsize-no-es-un-registro.md` | 129 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | mmMC_VM_FB_LOCATION | `mmMC_VM_FB_LOCATION` |
| 280 | `280-la-multi-asignacion-producia-un-rango-falso-y-ya-no.md` | 157 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 281 | `281-el-bucle-si-se-ejecuta-pero-alinea-90-veces.md` | 135 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 281 | `281-el-bucle-si-se-ejecuta-pero-alinea-90-veces.md` | 139 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 281 | `281-el-bucle-si-se-ejecuta-pero-alinea-90-veces.md` | 156 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 281 | `281-el-bucle-si-se-ejecuta-pero-alinea-90-veces.md` | 159 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 282 | `282-el-shader-no-distingue-vram-de-ram.md` | 72 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | `282-el-shader-no-distingue-vram-de-ram.md` | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | `282-el-shader-no-distingue-vram-de-ram.md` | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | `282-el-shader-no-distingue-vram-de-ram.md` | 189 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | `282-el-shader-no-distingue-vram-de-ram.md` | 191 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 283 | `283-la-carrera-eliminada-40-de-40-donde-fallaba-0-de-40.md` | 137 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 283 | `283-la-carrera-eliminada-40-de-40-donde-fallaba-0-de-40.md` | 139 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 284 | `284-el-enlace-esta-en-2-gbs-y-la-tarjeta-admite-7877.md` | 78 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | `284-el-enlace-esta-en-2-gbs-y-la-tarjeta-admite-7877.md` | 80 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | `284-el-enlace-esta-en-2-gbs-y-la-tarjeta-admite-7877.md` | 117 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | `284-el-enlace-esta-en-2-gbs-y-la-tarjeta-admite-7877.md` | 120 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | `284-el-enlace-esta-en-2-gbs-y-la-tarjeta-admite-7877.md` | 122 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | `284-el-enlace-esta-en-2-gbs-y-la-tarjeta-admite-7877.md` | 139 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 285 | `285-el-enlace-lo-limita-el-puerto-que-se-autolimita-a-gen2.md` | 23 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | `285-el-enlace-lo-limita-el-puerto-que-se-autolimita-a-gen2.md` | 76 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | `285-el-enlace-lo-limita-el-puerto-que-se-autolimita-a-gen2.md` | 80 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | `285-el-enlace-lo-limita-el-puerto-que-se-autolimita-a-gen2.md` | 103 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | `285-el-enlace-lo-limita-el-puerto-que-se-autolimita-a-gen2.md` | 104 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | `285-el-enlace-lo-limita-el-puerto-que-se-autolimita-a-gen2.md` | 131 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | `285-el-enlace-lo-limita-el-puerto-que-se-autolimita-a-gen2.md` | 131 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 286 | `286-el-ancho-de-banda-del-enlace-medido-1377-gbs.md` | 136 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 286 | `286-el-ancho-de-banda-del-enlace-medido-1377-gbs.md` | 139 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 287 | `287-la-lectura-si-costaba-su-latencia-443-ciclos.md` | 166 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 287 | `287-la-lectura-si-costaba-su-latencia-443-ciclos.md` | 168 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | `288-el-barrido-tiene-dos-codos-y-ninguno-mide-cache.md` | 26 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | `288-el-barrido-tiene-dos-codos-y-ninguno-mide-cache.md` | 27 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | `288-el-barrido-tiene-dos-codos-y-ninguno-mide-cache.md` | 124 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | `288-el-barrido-tiene-dos-codos-y-ninguno-mide-cache.md` | 125 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 289 | `289-la-cache-retiene-entre-256-y-320-kib.md` | 128 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 289 | `289-la-cache-retiene-entre-256-y-320-kib.md` | 130 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 290 | `290-el-codo-no-depende-del-reparto-entre-vias.md` | 104 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 290 | `290-el-codo-no-depende-del-reparto-entre-vias.md` | 108 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 290 | `290-el-codo-no-depende-del-reparto-entre-vias.md` | 117 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 290 | `290-el-codo-no-depende-del-reparto-entre-vias.md` | 119 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 291 | `291-doce-cifras-de-poblacion-diez-sin-fecha-y-ninguna-commiteada.md` | 423 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 292 | `292-citas-a-ficheros-que-esta-gpu-no-ejecuta.md` | 130 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 292 | `292-citas-a-ficheros-que-esta-gpu-no-ejecuta.md` | 203 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 292 | `292-citas-a-ficheros-que-esta-gpu-no-ejecuta.md` | 210 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 293 | `293-tres-vocabitarios-de-estado-vivos-y-uno-sin-declaracion.md` | 188 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 305 | `305-el-mapa-bar-estaba-en-el-sysfs.md` | 247 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 306 | `306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md` | 236 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: MODEL_CHOICE | - |
| 306 | `306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md` | 307 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: MODEL_CHOICE | - |
| 306 | `306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md` | 324 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | mmCONFIG_MEMSIZE | `mmCONFIG_MEMSIZE` |
| 306 | `306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md` | 325 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: MODEL_CHOICE | - |
| 306 | `306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md` | 326 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: MODEL_CHOICE | - |
| 306 | `306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md` | 328 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: MODEL_CHOICE | - |
| 307 | `307-63-numeros-citados-que-no-son-hallazgos.md` | 170 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 308 | `308-setenta-y-cuatro-numeros-colisionan-y-1739-citas-no-saben-a-cual.md` | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 308 | `308-setenta-y-cuatro-numeros-colisionan-y-1739-citas-no-saben-a-cual.md` | 164 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 310 | `310-dos-herramientas-declaran-readonly-y-abren-el-nodo-drm-en-lectura-escritura.md` | 115 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 401 | `401-doclint-no-indexaba-07-driver.md` | 207 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 401 | `401-doclint-no-indexaba-07-driver.md` | 224 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 402 | `402-tapada-0-no-era-un-resultado-y-ya-no-lo-es.md` | 126 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 403 | `403-el-orden-entre-las-escrituras-avfs-y-la-copia.md` | 142 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 403 | `403-el-orden-entre-las-escrituras-avfs-y-la-copia.md` | 161 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 403 | `403-el-orden-entre-las-escrituras-avfs-y-la-copia.md` | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 500 | `500-el-shadow-de-los-contadores-y-el-mensaje-que-acusa.md` | 164 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 501 | `501-el-hueco-de-la-forma-c-es-real-y-no-es-de-mi-asic.md` | 151 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 502 | `502-quien-escribe-cada-byte-de-los-1776.md` | 274 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 503 | `503-srcdata-como-discriminante-sobrevive-pero-la-cita-no.md` | 113 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 503 | `503-srcdata-como-discriminante-sobrevive-pero-la-cita-no.md` | 133 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 504 | `504-los-nueve-locks-los-sostienen-procesos-muertos.md` | 135 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 504 | `504-los-nueve-locks-los-sostienen-procesos-muertos.md` | 242 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 505 | `505-el-cap-de-clock-stretcher-si-esta-activo.md` | 7 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 506 | `506-la-puerta-de-2095-el-divisor-dfs-escribe.md` | 15 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 550 | `550-la-tabla-pcie-esta-empaquetada-y-el-struct-no.md` | 148 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 550 | `550-la-tabla-pcie-esta-empaquetada-y-el-struct-no.md` | 184 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: cambia el resultado | - |
| 551 | `551-toolkit-audita-solo-su-directorio.md` | 121 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 551 | `551-toolkit-audita-solo-su-directorio.md` | 259 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 551 | `551-toolkit-audita-solo-su-directorio.md` | 271 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 551 | `551-toolkit-audita-solo-su-directorio.md` | 357 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 551 | `551-toolkit-audita-solo-su-directorio.md` | 374 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 601 | `601-la-tabla-pcie-del-vbios-esta-empaquetada-y-el.md` | 177 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | `602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md` | 25 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | `602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md` | 98 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | `602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md` | 101 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | `602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md` | 233 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | `602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md` | 238 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | `602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md` | 283 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | `602-la-cadena-colapsa-y-el-techo-de-vram-estaba-en-la-mitad.md` | 284 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 604 | `604-una-contradiccion-y-una-premisa-sin-verificar.md` | 15 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | `604-una-contradiccion-y-una-premisa-sin-verificar.md` | 102 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | `604-una-contradiccion-y-una-premisa-sin-verificar.md` | 138 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | `604-una-contradiccion-y-una-premisa-sin-verificar.md` | 152 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | `604-una-contradiccion-y-una-premisa-sin-verificar.md` | 202 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 605 | `605-la-ruta-legacy-si-es-la-viva-por-agotamiento.md` | 8 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: mmRCC_CONFIG | - |
| 605 | `605-la-ruta-legacy-si-es-la-viva-por-agotamiento.md` | 143 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: mmRCC_CONFIG | - |
| 605 | `605-la-ruta-legacy-si-es-la-viva-por-agotamiento.md` | 211 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmRCC_CONFIG | - |
| 606 | `606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md` | 113 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | `606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md` | 116 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | `606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md` | 152 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | `606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md` | 154 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | `606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md` | 166 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | `606-el-acantonado-del-bar-a-256-mib-y-un-flag-muerto.md` | 168 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 607 | `607-el-control-que-le-faltaba-al-banco.md` | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 607 | `607-el-control-que-le-faltaba-al-banco.md` | 148 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 607 | `607-el-control-que-le-faltaba-al-banco.md` | 157 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 607 | `607-el-control-que-le-faltaba-al-banco.md` | 159 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 608 | `608-el-cap-esta-activo-y-mi-herramienta-de-offsets.md` | 30 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 608 | `608-el-cap-esta-activo-y-mi-herramienta-de-offsets.md` | 199 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 608 | `608-el-cap-esta-activo-y-mi-herramienta-de-offsets.md` | 200 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 27 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 29 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 117 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 117 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 136 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 140 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 142 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | `609-no-es-un-coste-por-envio-se-paga-una-vez.md` | 146 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 901 | `901-la-base-queda-proven-y-este-arbol-no-es-el-que.md` | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 901 | `901-la-base-queda-proven-y-este-arbol-no-es-el-que.md` | 161 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 901 | `901-la-base-queda-proven-y-este-arbol-no-es-el-que.md` | 178 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 902 | `902-reserva-y-separacion-son-dos-ejes.md` | 132 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 902 | `902-reserva-y-separacion-son-dos-ejes.md` | 133 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 902 | `902-reserva-y-separacion-son-dos-ejes.md` | 148 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 902 | `902-reserva-y-separacion-son-dos-ejes.md` | 150 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 903 | `903-banco-de-mediciones-con-contrato.md` | 148 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | `903-banco-de-mediciones-con-contrato.md` | 149 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | `903-banco-de-mediciones-con-contrato.md` | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | `903-banco-de-mediciones-con-contrato.md` | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | `903-banco-de-mediciones-con-contrato.md` | 156 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | `903-banco-de-mediciones-con-contrato.md` | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 905 | `905-el-pago-sigue-a-las-paginas-y-la-rama-se-satura.md` | 64 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 905 | `905-el-pago-sigue-a-las-paginas-y-la-rama-se-satura.md` | 64 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 905 | `905-el-pago-sigue-a-las-paginas-y-la-rama-se-satura.md` | 133 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 905 | `905-el-pago-sigue-a-las-paginas-y-la-rama-se-satura.md` | 135 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 908 | `908-vram-bit-width-dice-64-y-la-medicion-dice-128.md` | 96 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | `908-vram-bit-width-dice-64-y-la-medicion-dice-128.md` | 96 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | `908-vram-bit-width-dice-64-y-la-medicion-dice-128.md` | 129 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | `908-vram-bit-width-dice-64-y-la-medicion-dice-128.md` | 130 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | `908-vram-bit-width-dice-64-y-la-medicion-dice-128.md` | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | `908-vram-bit-width-dice-64-y-la-medicion-dice-128.md` | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 909 | `909-el-bus-es-de-64-bits-y-el-multiplicador-es-4.md` | 66 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 909 | `909-el-bus-es-de-64-bits-y-el-multiplicador-es-4.md` | 67 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 909 | `909-el-bus-es-de-64-bits-y-el-multiplicador-es-4.md` | 141 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 909 | `909-el-bus-es-de-64-bits-y-el-multiplicador-es-4.md` | 142 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 911 | `911-el-vbios-dice-128-y-el-driver-informa-64.md` | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 911 | `911-el-vbios-dice-128-y-el-driver-informa-64.md` | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 911 | `911-el-vbios-dice-128-y-el-driver-informa-64.md` | 125 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 911 | `911-el-vbios-dice-128-y-el-driver-informa-64.md` | 127 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 922 | `922-avfs-lo-que-de-verdad-se-sube-al-smc.md` | 136 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 922 | `922-avfs-lo-que-de-verdad-se-sube-al-smc.md` | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 923 | `923-vram-width-dos-rutas-ninguna-lectura-ucmembuswidth.md` | 3 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 923 | `923-vram-width-dos-rutas-ninguna-lectura-ucmembuswidth.md` | 53 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 923 | `923-vram-width-dos-rutas-ninguna-lectura-ucmembuswidth.md` | 61 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 923 | `923-vram-width-dos-rutas-ninguna-lectura-ucmembuswidth.md` | 73 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 924 | `924-read-mmr-reg-no-observa-mc-ni-vm.md` | 58 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 925 | `925-son-coeficientes-y-923-estaba-equivocado.md` | 47 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 925 | `925-son-coeficientes-y-923-estaba-equivocado.md` | 77 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 925 | `925-son-coeficientes-y-923-estaba-equivocado.md` | 80 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 925 | `925-son-coeficientes-y-923-estaba-equivocado.md` | 140 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 926 | `926-el-driver-sobrescribe-avfs-con-los-mismos-valores.md` | 105 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 931 | `931-la-unidad-es-10-khz-y-no-habria-parecido.md` | 181 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 932 | `932-bench-declara-writes-gpu-y-no-escribe.md` | 103 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 932 | `932-bench-declara-writes-gpu-y-no-escribe.md` | 124 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | `932-bench-declara-writes-gpu-y-no-escribe.md` | 253 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | `932-bench-declara-writes-gpu-y-no-escribe.md` | 263 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | `932-bench-declara-writes-gpu-y-no-escribe.md` | 318 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | `932-bench-declara-writes-gpu-y-no-escribe.md` | 379 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | `932-bench-declara-writes-gpu-y-no-escribe.md` | 434 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 933 | `933-282-discriminante-ejecutado-no-separa-y-mem2-no-funciona.md` | 83 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 934 | `934-marcas-de-tiempo-refutan-el-envio-fallido-en-mem2.md` | 78 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: visible para | - |
| 938 | `938-techo-de-envio-38us-y-por-debajo-de-60us-el-banco-es-envio.md` | 46 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 939 | `939-de-7-ganancias-mi-vbios-solo-puede-entregar-2.md` | 170 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 939 | `939-de-7-ganancias-mi-vbios-solo-puede-entregar-2.md` | 203 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 939 | `939-de-7-ganancias-mi-vbios-solo-puede-entregar-2.md` | 241 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 940 | `940-el-control-no-ve-que-falten-despachos.md` | 3 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: cambi | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 18 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 155 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 186 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 187 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 188 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 189 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 234 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | `941-usTjMax-93-la-rama-de-limites-si-corren.md` | 237 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 942 | `942-282-2-cerrada-en-283-y-arrastrada-en-cinco-notas.md` | 122 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 945 | `945-la-revision-nunca-se-midio-y-pstate-sclk-confirma-el-nivel-0.md` | 141 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: no se | - |
| 951 | `951-los-997-mhz-estaban-medidos-con-el-compositor-corriendo.md` | 41 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 952 | `952-271-1-ejecutado-misma-forma-sin-codo-de-cache.md` | 4 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: LATEN | - |
| 952 | `952-271-1-ejecutado-misma-forma-sin-codo-de-cache.md` | 95 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: LATEN | - |
| 952 | `952-271-1-ejecutado-misma-forma-sin-codo-de-cache.md` | 146 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: LATEN | - |
| 954 | `954-average-graphics-activity-en-el-byte-60.md` | 167 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 954 | `954-average-graphics-activity-en-el-byte-60.md` | 168 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 954 | `954-average-graphics-activity-en-el-byte-60.md` | 169 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 954 | `954-average-graphics-activity-en-el-byte-60.md` | 170 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 958 | `958-la-huella-no-se-satura-la-hipotesis-refutada.md` | 4 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 970 | `970-runtime-obs-falla-en-silencio-cinco-defectos.md` | 305 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | `970-runtime-obs-falla-en-silencio-cinco-defectos.md` | 362 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | `970-runtime-obs-falla-en-silencio-cinco-defectos.md` | 436 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | `970-runtime-obs-falla-en-silencio-cinco-defectos.md` | 439 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | `970-runtime-obs-falla-en-silencio-cinco-defectos.md` | 466 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 974 | `974-el-bit-51-si-llega-a-un-pte-de-gfx8-por-el-manejador-de-faults.md` | 200 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 974 | `974-el-bit-51-si-llega-a-un-pte-de-gfx8-por-el-manejador-de-faults.md` | 201 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 974 | `974-el-bit-51-si-llega-a-un-pte-de-gfx8-por-el-manejador-de-faults.md` | 202 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 974 | `974-el-bit-51-si-llega-a-un-pte-de-gfx8-por-el-manejador-de-faults.md` | 203 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 976 | `976-corregcion-a-974-el-escritor-del-bit-51-es-inalcanzable-en-gfx8.md` | 147 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 976 | `976-corregcion-a-974-el-escritor-del-bit-51-es-inalcanzable-en-gfx8.md` | 148 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 978 | `978-el-iv-de-gfx8-no-es-el-de-8-dwords.md` | 63 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 978 | `978-el-iv-de-gfx8-no-es-el-de-8-dwords.md` | 142 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 978 | `978-el-iv-de-gfx8-no-es-el-de-8-dwords.md` | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 981 | `981-el-backend-de-color-y-profundidad-tiene-cero-cobertura.md` | 153 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 981 | `981-el-backend-de-color-y-profundidad-tiene-cero-cobertura.md` | 154 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 981 | `981-el-backend-de-color-y-profundidad-tiene-cero-cobertura.md` | 155 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 981 | `981-el-backend-de-color-y-profundidad-tiene-cero-cobertura.md` | 156 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 986 | `986-los-headers-de-cb-db-no-estan-ausentes-del-corpus.md` | 111 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 991 | `991-el-isa-de-gfx8-si-tiene-fuente-primaria-publicada.md` | 53 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 991 | `991-el-isa-de-gfx8-si-tiene-fuente-primaria-publicada.md` | 150 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 991 | `991-el-isa-de-gfx8-si-tiene-fuente-primaria-publicada.md` | 189 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 992 | `992-la-tabla-de-opcodes-de-gfx8-coincide-con-un-codificador.md` | 103 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 3 | frase: No esta | - |
| 992 | `992-la-tabla-de-opcodes-de-gfx8-coincide-con-un-codificador.md` | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 992 | `992-la-tabla-de-opcodes-de-gfx8-coincide-con-un-codificador.md` | 115 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 993 | `993-siete-huecos-y-un-igual-que-no-era-un-defecto.md` | 255 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 993 | `993-siete-huecos-y-un-igual-que-no-era-un-defecto.md` | 270 | `NOT_PROVEN` | `SIN_PISTAS` | 0 |  | - |
| 999 | `999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md` | 55 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md` | 136 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md` | 202 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md` | 215 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md` | 216 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-corpus-de-definiciones-de-registro-es-identico-en-los-dos-arboles.md` | 218 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 256 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 257 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 258 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 259 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 264 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 297 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 307 | `NOT_DETERMINED` | `UN_REGISTRO` | 3 | frase: un registro | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 353 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 999 | `999-el-fetch-del-anillo-es-un-bloque-de-registros-cp-rb-y-no-un-paquete.md` | 356 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |

Obsoletos declarados por el propio findings: 44.
