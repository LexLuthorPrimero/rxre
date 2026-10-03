# OPEN-FRONTIERS

<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Los 1016 huecos abiertos de 281 findings, y por donde se cierran.

**Generado desde la salida de `tools/frontier.py --json`**, no reimplementando su clasificacion. Dos recuentos del mismo conjunto divergen sin que nadie lo note.

## Via de cierre

| via | huecos | que significa |
|---|---|---|
| `SPEC_NO_PUBLICADO` | 339 | falta documentacion que no existe (033) |
| `RUNTIME_ACTIVO` | 276 | solo se cierra observando comportamiento |
| `POR_DEFINICION` | 132 | es una convencion que se elige, no se descubre |
| `UN_REGISTRO` | 108 | se cierra leyendo un registro de la tarjeta |
| `SIN_PISTAS` | 93 | el texto no dice que haria falta para cerrarlo |
| `DIFERENCIAL` | 68 | se cierra repitiendo con un parametro y comparando |

**Total: 1016 huecos.**
`SIN_PISTAS` son los unicos que ningun texto del proyecto dice como cerrar.

## Los huecos

| finding | linea | clase | via | fuerza | marca | registros |
|---|---|---|---|---|---|---|
| 001 | 213 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 001 | 253 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 003 | 140 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 005 | 85 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 005 | 200 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 006 | 243 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 006 | 281 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 007 | 75 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 007 | 213 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 008 | 103 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 008 | 127 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 008 | 149 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 009 | 67 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | 73 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | 145 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | 187 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | 187 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 009 | 203 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 010 | 3 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | 137 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 010 | 171 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | 171 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | 508 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 010 | 524 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 011 | 264 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 011 | 296 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 012 | 76 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 012 | 266 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 012 | 280 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 013 | 209 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | 225 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | 225 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | 225 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 013 | 225 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmGDS_COMPUT | - |
| 015 | 16 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 16 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 25 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 25 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 112 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 112 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 120 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 124 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 124 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 015 | 279 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: comportamiento real | - |
| 015 | 494 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 016 | 138 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 016 | 168 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 017 | 140 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 017 | 140 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 017 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Efecto real | - |
| 017 | 140 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 017 | 155 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 017 | 175 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 017 | 191 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 018 | 28 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 018 | 86 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 018 | 200 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 018 | 224 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 018 | 233 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: REQUIREMENT | - |
| 018 | 246 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 019 | 156 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 019 | 156 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 019 | 183 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 020 | 125 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 020 | 125 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 020 | 125 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 020 | 166 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 021 | 160 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 021 | 160 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 021 | 191 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 021 | 208 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 022 | 244 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | 252 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: MODEL_CHOICE | - |
| 022 | 272 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | 272 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | 272 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | 287 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 022 | 307 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: REQUIREMENT | - |
| 023 | 71 | `UNKNOWN` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | 173 | `UNKNOWN` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | 199 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | 205 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | 209 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | 215 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | 232 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convencion | - |
| 023 | 238 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 023 | 238 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 023 | 255 | `UNKNOWN` | `POR_DEFINICION` | 1 | seccion: frase: convencion | - |
| 023 | 281 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: hardware interpreta | - |
| 024 | 172 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 024 | 211 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 024 | 273 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 025 | 88 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 025 | 112 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 025 | 121 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 025 | 165 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 025 | 165 | `UNKNOWN` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 025 | 175 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 025 | 175 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 026 | 9 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | 220 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | 226 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | 226 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | 226 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 026 | 249 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 027 | 266 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 028 | 110 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | 272 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | 289 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | 294 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: MODEL | - |
| 028 | 300 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 029 | 99 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 029 | 121 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 029 | 127 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 029 | 167 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 029 | 231 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 029 | 237 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 030 | 88 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: arquitectura d | - |
| 030 | 171 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: arquitectura d | - |
| 030 | 203 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: arquitectura d | - |
| 031 | 24 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | 264 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | 264 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | 288 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | 294 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 031 | 308 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 031 | 338 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 031 | 426 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 032 | 35 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | 89 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 032 | 89 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 032 | 89 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 032 | 96 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | 202 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | 206 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: visible para | - |
| 032 | 206 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: visible para | - |
| 032 | 235 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | 261 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 032 | 275 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 033 | 1 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: NOT_PUBLISHED | - |
| 033 | 12 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | 12 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | 28 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | 47 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: NOT_PUBLISHED | - |
| 033 | 96 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 033 | 96 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 033 | 96 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convencion | - |
| 033 | 96 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convencion | - |
| 033 | 279 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | 382 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | 382 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 033 | 425 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 033 | 447 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 034 | 206 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 034 | 263 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 034 | 277 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 034 | 317 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convencion | - |
| 035 | 155 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 035 | 250 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 036 | 245 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 036 | 259 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 036 | 305 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 037 | 83 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 037 | 83 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 037 | 83 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 037 | 256 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 037 | 271 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 037 | 271 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | `mmCP_HQD_PQ_RPTR` |
| 038 | 8 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 038 | 164 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 038 | 255 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 039 | 71 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 039 | 169 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 039 | 169 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 039 | 169 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 040 | 36 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | 181 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | 181 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | 181 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | 181 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | 243 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 040 | 282 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 041 | 56 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 041 | 88 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 041 | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 041 | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 042 | 93 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 042 | 93 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 042 | 159 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 042 | 215 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no hay documentaci | - |
| 042 | 229 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 042 | 229 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 043 | 142 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 043 | 201 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 043 | 201 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 044 | 118 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 044 | 175 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 044 | 175 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 045 | 10 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | 22 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | 59 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | 73 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | 110 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | 129 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 045 | 142 | `NOT_DETERMINED` | `UN_REGISTRO` | 3 | frase: un registro | - |
| 046 | 72 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 046 | 72 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 046 | 73 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 046 | 145 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 046 | 192 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 047 | 107 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_CONTEXT1_PROTECT | - |
| 047 | 107 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_CONTEXT1_PROTECT | - |
| 047 | 134 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 047 | 134 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 047 | 201 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_CONTEXT1_PROTECT | - |
| 048 | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 048 | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 050 | 10 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | 20 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | 105 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | 110 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 050 | 110 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 051 | 105 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 051 | 114 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 051 | 139 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 056 | 120 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 056 | 153 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 056 | 178 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 057 | 10 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 057 | 133 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 058 | 77 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 059 | 34 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 059 | 98 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 059 | 98 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 061 | 95 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 062 | 104 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 062 | 111 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 063 | 523 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 1573 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 2098 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 2210 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 2582 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 2637 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 2854 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 3330 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 4376 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 063 | 4549 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 064 | 11 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 064 | 61 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: spec | - |
| 064 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: hardware interpreta | - |
| 064 | 166 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 064 | 166 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 064 | 166 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 065 | 78 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 065 | 130 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 065 | 130 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 066 | 109 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 068 | 88 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: Orden | - |
| 068 | 100 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: Orden | - |
| 068 | 100 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 068 | 100 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 069 | 10 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 069 | 137 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: spec | - |
| 070 | 136 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 070 | 136 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 071 | 135 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 072 | 103 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 072 | 103 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 072 | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 072 | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 074 | 85 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 074 | 85 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 074 | 85 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 074 | 85 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 074 | 85 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 075 | 150 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 081 | 88 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 081 | 151 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 081 | 159 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 082 | 174 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 082 | 174 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 083 | 114 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 083 | 138 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 084 | 30 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 084 | 34 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 084 | 113 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 084 | 113 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 085 | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 085 | 139 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 086 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 086 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 087 | 12 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | 123 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | 161 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | 161 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | 171 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 087 | 182 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 088 | 175 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NO esta | - |
| 089 | 111 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 089 | 189 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 090 | 160 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: POLICY | - |
| 090 | 160 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: POLICY | - |
| 090 | 160 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: POLICY | - |
| 092 | 192 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | 192 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | 192 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | 192 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 092 | 207 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 094 | 166 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 094 | 166 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 094 | 166 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 095 | 12 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | 124 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 095 | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | - |
| 095 | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: spec | - |
| 095 | 156 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: hardware hace | - |
| 095 | 169 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 096 | 43 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 096 | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 096 | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 096 | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 096 | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 096 | 219 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 096 | 238 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 097 | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 097 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 098 | 98 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 098 | 98 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 098 | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 099 | 150 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 099 | 150 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 099 | 150 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 099 | 150 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 100 | 5 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | 5 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | 111 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | 117 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 100 | 192 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmSMC_IND_DA | - |
| 101 | 44 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 101 | 117 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 102 | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 102 | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: inmed | - |
| 104 | 3 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 104 | 3 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 105 | 165 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 105 | 165 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 106 | 33 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 106 | 79 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 106 | 143 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_INVALID | - |
| 107 | 109 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: compa | - |
| 107 | 139 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: compa | - |
| 107 | 139 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: compa | - |
| 108 | 81 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | 109 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | 134 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | 134 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 108 | 148 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 109 | 124 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 109 | 124 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 109 | 124 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 110 | 181 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: Orden | - |
| 111 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 111 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 111 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 112 | 261 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no documentad | - |
| 112 | 282 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no documentad | - |
| 113 | 10 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 113 | 16 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 114 | 17 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 41 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 93 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 198 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 236 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 273 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 278 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 320 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 114 | 320 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: REQUI | - |
| 115 | 177 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 115 | 177 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 115 | 270 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Timin | - |
| 116 | 12 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | 193 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | 193 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | 208 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 116 | 208 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 117 | 163 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 118 | 184 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 119 | 92 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 119 | 92 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 119 | 92 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 119 | 92 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 120 | 119 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 120 | 119 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 121 | 5 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | 55 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | 98 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | 98 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 121 | 117 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 121 | 209 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 121 | 209 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 122 | 116 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 122 | 171 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 122 | 171 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 122 | 171 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmGPU_HDP_FLUSH_REQ | - |
| 123 | 203 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 123 | 260 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 124 | 98 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 124 | 98 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 124 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 124 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 124 | 119 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 125 | 106 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: speci | - |
| 125 | 106 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: speci | - |
| 126 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 126 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 127 | 110 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 127 | 136 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 127 | 136 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 127 | 151 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 128 | 87 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | 158 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | 158 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | 158 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 128 | 158 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 129 | 127 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 129 | 127 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 130 | 5 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 130 | 152 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | 152 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | 152 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 130 | 202 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 130 | 207 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 131 | 5 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | 12 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | 151 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | 151 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | 165 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | 165 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | 172 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 131 | 226 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmVM_PRT_CNTL | - |
| 132 | 195 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 132 | 195 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 132 | 195 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 133 | 104 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 133 | 137 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 135 | 155 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 135 | 155 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 135 | 195 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 136 | 132 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 136 | 132 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 137 | 122 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | 122 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | 122 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | 122 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 137 | 134 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_MX_L1_TLB_CNT | - |
| 138 | 14 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | 246 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | 246 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | 246 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | 264 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 138 | 274 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 139 | 300 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | 329 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | 329 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | 329 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | 329 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | 354 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | 363 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 139 | 389 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmVM_CONTEXT | - |
| 140 | 18 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | 249 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | 249 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | 249 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 140 | 249 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 142 | 237 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | mmHDP_ | `mmHDP_` |
| 142 | 237 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | seccion: mmHDP_ | - |
| 142 | 257 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmHDP_ | - |
| 143 | 175 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 143 | 226 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 143 | 226 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 143 | 226 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 143 | 226 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 144 | 226 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 144 | 246 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 145 | 147 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 146 | 102 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 147 | 185 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 147 | 185 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: timing | - |
| 147 | 185 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: timing | - |
| 147 | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: timing | - |
| 148 | 203 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: timing | - |
| 148 | 210 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 148 | 210 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 148 | 210 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 149 | 192 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 149 | 192 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: timing | - |
| 150 | 185 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 150 | 185 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 150 | 185 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 151 | 133 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 151 | 144 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 151 | 144 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 151 | 166 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 152 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | 179 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 152 | 204 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 153 | 202 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | 202 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | 202 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | 226 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | 235 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 153 | 282 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 154 | 12 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | 65 | `UNKNOWN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | 184 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | 184 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | 184 | `UNKNOWN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | 184 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 154 | 215 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 155 | 182 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | 193 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 155 | 230 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: TIMING | - |
| 156 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 156 | 176 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: TIMING | - |
| 157 | 169 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 157 | 169 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 157 | 169 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 158 | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 158 | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 158 | 167 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 158 | 192 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 159 | 153 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 159 | 153 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 159 | 153 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 160 | 117 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | 230 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | 230 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | 230 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 160 | 315 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: polic | - |
| 161 | 195 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 161 | 195 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 161 | 195 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 162 | 220 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: TIMIN | - |
| 162 | 220 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: TIMIN | - |
| 162 | 220 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: TIMIN | - |
| 163 | 12 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | 210 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | 210 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | 210 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | 210 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 163 | 234 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 164 | 158 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 164 | 158 | `NOT_DETERMINED` | `UN_REGISTRO` | 3 | frase: un registro | - |
| 164 | 158 | `NOT_DETERMINED` | `UN_REGISTRO` | 3 | frase: un registro | - |
| 164 | 183 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 164 | 234 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 165 | 141 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 165 | 141 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 166 | 95 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | 163 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 166 | 170 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | 170 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | 170 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | 170 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | 170 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 166 | 247 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 167 | 225 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 167 | 225 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 167 | 225 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 167 | 247 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 170 | 12 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | 129 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | 129 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | 129 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | 129 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 170 | 151 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convención | - |
| 170 | 187 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 172 | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 172 | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 172 | 160 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 173 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 173 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 173 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 173 | 152 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 174 | 108 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 174 | 108 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 174 | 108 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | 73 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 175 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 176 | 25 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 177 | 190 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 177 | 206 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 178 | 164 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | 164 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | 164 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | 164 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 178 | 181 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 179 | 136 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 179 | 136 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 179 | 136 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 179 | 148 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: diferencia ent | - |
| 181 | 149 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | 158 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | 173 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 181 | 178 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: timin | - |
| 183 | 12 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: frase: un re | - |
| 183 | 134 | `NOT_PROVEN` | `UN_REGISTRO` | 2 | parrafo: un registro | - |
| 184 | 163 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 184 | 163 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 184 | 177 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | 131 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | 143 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | 143 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | 143 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | 143 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | 156 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 185 | 162 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 186 | 36 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 187 | 106 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | 113 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | 113 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | 113 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 187 | 125 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 188 | 176 | `NOT_PROVEN` | `POR_DEFINICION` | 2 | frase: convención | - |
| 190 | 206 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 193 | 59 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 193 | 110 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 198 | 115 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 198 | 115 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 198 | 115 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 198 | 128 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 198 | 133 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 199 | 131 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: Un solo regist | - |
| 199 | 140 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: Un solo registro | - |
| 199 | 140 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | parrafo: Un solo registro | - |
| 199 | 160 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: Un solo regist | - |
| 203 | 101 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 204 | 129 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 204 | 142 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmMC_VM_FB_LOCATION | - |
| 208 | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 209 | 100 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 210 | 46 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: inmediat | - |
| 210 | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 210 | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 210 | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 210 | 168 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: inmediat | - |
| 210 | 201 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: inmediat | - |
| 211 | 141 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | 141 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | 141 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | 141 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 211 | 155 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 218 | 128 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 218 | 128 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 218 | 145 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 218 | 171 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 223 | 96 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 224 | 49 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 231 | 24 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 231 | 169 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 231 | 169 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 232 | 186 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: spec | `mmHDP_DEBUG0` |
| 233 | 157 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 235 | 12 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | 127 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | 144 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | 144 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 235 | 144 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 236 | 128 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | 128 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | 128 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | 128 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | 128 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 236 | 155 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 237 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 237 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 237 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 237 | 119 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 238 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 238 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 238 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 238 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 240 | 119 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convención | - |
| 240 | 119 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | seccion: frase: convención | - |
| 240 | 137 | `NOT_DETERMINED` | `POR_DEFINICION` | 2 | frase: convención | - |
| 241 | 78 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 241 | 78 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 241 | 126 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 242 | 268 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | parrafo: convención | `mmSDMA_`, `mmSRBM_` |
| 243 | 134 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 244 | 138 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 246 | 179 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmDB_RMI_L2_CACHE_CON | - |
| 246 | 179 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmDB_RMI_L2_CACHE_CON | - |
| 246 | 182 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | seccion: mmDB_RMI_L2_CACHE_CON | - |
| 246 | 225 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no hay documentaci | - |
| 246 | 225 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no hay documentaci | - |
| 251 | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 251 | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 16 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 168 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 168 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 200 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 200 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 211 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 211 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 253 | 223 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | 193 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | 193 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | 197 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | 197 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | 201 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | 201 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 254 | 201 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 255 | 212 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 255 | 212 | `NOT_DETERMINED` | `DIFERENCIAL` | 3 | frase: diferencia entre | - |
| 256 | 106 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Inmed | - |
| 256 | 136 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Inmed | - |
| 256 | 193 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: Inmed | - |
| 257 | 160 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 257 | 160 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 257 | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 257 | 175 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | 209 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | 209 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | 235 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | 235 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | 250 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 258 | 250 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: Conve | - |
| 259 | 110 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 259 | 110 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 261 | 193 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | 193 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | 198 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | 211 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | 221 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 261 | 221 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 262 | 29 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | 111 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 262 | 117 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | 138 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | 138 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | 154 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 262 | 156 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 263 | 5 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 263 | 92 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 263 | 131 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 263 | 131 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 265 | 12 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 265 | 137 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 265 | 137 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 265 | 156 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 265 | 156 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 266 | 76 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 269 | 184 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 269 | 196 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 270 | 141 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 271 | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 271 | 128 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 272 | 190 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 272 | 190 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 272 | 207 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 273 | 84 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 273 | 90 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 273 | 119 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 274 | 52 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 275 | 205 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 277 | 121 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 277 | 121 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 277 | 139 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: latencia | - |
| 277 | 139 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: latencia | - |
| 278 | 117 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 278 | 149 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 279 | 120 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | mmMC_VM_FB_LOCATION | `mmMC_VM_FB_LOCATION` |
| 280 | 155 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 281 | 135 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 281 | 135 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 281 | 156 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 281 | 156 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 282 | 59 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | 179 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | 189 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 282 | 189 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 283 | 137 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 283 | 137 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 284 | 78 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | 78 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | 115 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | 120 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | 120 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 284 | 139 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 285 | 21 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | 76 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | 76 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | 102 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | 102 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | 131 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 285 | 131 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 286 | 136 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 286 | 136 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 287 | 166 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 287 | 166 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | 26 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | 26 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | 124 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 288 | 124 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: latencia | - |
| 289 | 128 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 289 | 128 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 290 | 104 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 290 | 104 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 290 | 117 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 290 | 117 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 291 | 421 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 292 | 130 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 292 | 197 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 292 | 197 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 293 | 188 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 305 | 246 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 401 | 195 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 401 | 211 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 402 | 126 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 403 | 134 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 403 | 159 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 403 | 215 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: orden | - |
| 500 | 162 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 2 | frase: orden | - |
| 501 | 149 | `NOT_PROVEN` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 502 | 273 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 503 | 110 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 503 | 123 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 504 | 126 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 504 | 242 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 505 | 5 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 506 | 5 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 550 | 148 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: conve | - |
| 550 | 184 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: cambia el resultado | - |
| 551 | 120 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 551 | 252 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 551 | 264 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | parrafo: diferencia entre | - |
| 551 | 351 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 551 | 364 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO ES | - |
| 601 | 177 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | 12 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | 98 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | 98 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | 233 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | 233 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | 283 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 602 | 283 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 604 | 5 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | 100 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | 138 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | 146 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 604 | 200 | `NOT_PROVEN` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 605 | 5 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: mmRCC_CONFIG | - |
| 605 | 141 | `NOT_PROVEN` | `UN_REGISTRO` | 1 | documento entero: mmRCC_CONFIG | - |
| 605 | 210 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: mmRCC_CONFIG | - |
| 606 | 113 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | 113 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | 152 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | 152 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | 166 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 606 | 166 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 607 | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 607 | 146 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 607 | 157 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 607 | 157 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 608 | 30 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 608 | 192 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 608 | 192 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 609 | 27 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | 27 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | 117 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | 117 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | 136 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | 136 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | 142 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 609 | 142 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 901 | 153 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 901 | 153 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 901 | 178 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 902 | 132 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 902 | 132 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 902 | 148 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 902 | 148 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: difer | - |
| 903 | 148 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | 148 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | 151 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | 156 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 903 | 156 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: laten | - |
| 905 | 64 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 905 | 64 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 905 | 133 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 905 | 133 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 908 | 96 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | 96 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | 129 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | 129 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 908 | 143 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 909 | 66 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 909 | 66 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 909 | 141 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 909 | 141 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 911 | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 911 | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 911 | 125 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 911 | 125 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NO es | - |
| 922 | 134 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 922 | 140 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | seccion: frase: orden | - |
| 923 | 3 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 923 | 51 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 923 | 61 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 923 | 73 | `NOT_DETERMINED` | `POR_DEFINICION` | 1 | documento entero: frase: decis | - |
| 924 | 55 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: inmediat | - |
| 925 | 47 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 925 | 75 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 925 | 80 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 925 | 139 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 926 | 104 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 931 | 181 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | parrafo: no esta | - |
| 932 | 100 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 932 | 114 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | 249 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | 263 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | 314 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | 376 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 932 | 431 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 933 | 83 | `NOT_DETERMINED` | `DIFERENCIAL` | 2 | seccion: frase: cambia con el | - |
| 934 | 78 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | parrafo: visible para | - |
| 938 | 42 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 939 | 170 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 939 | 197 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 939 | 238 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 940 | 3 | `NOT_DETERMINED` | `DIFERENCIAL` | 1 | documento entero: frase: cambi | - |
| 941 | 18 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | 152 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | 186 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | 186 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | 186 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | 186 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | 234 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 941 | 234 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 942 | 122 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: No es | - |
| 945 | 141 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: no se | - |
| 951 | 41 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: no esta | - |
| 952 | 4 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: LATEN | - |
| 952 | 94 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: LATEN | - |
| 952 | 142 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: LATEN | - |
| 954 | 167 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 954 | 167 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 954 | 167 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 954 | 167 | `UNKNOWN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 958 | 4 | `NOT_DETERMINED` | `RUNTIME_ACTIVO` | 1 | documento entero: frase: orden | - |
| 970 | 303 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | 362 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | 425 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | 425 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 970 | 458 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 3 | frase: no esta | - |
| 974 | 194 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 974 | 194 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 974 | 194 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 974 | 194 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 2 | seccion: frase: NOT_PUBLISHED | - |
| 976 | 140 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 976 | 140 | `NOT_DETERMINED` | `UN_REGISTRO` | 2 | seccion: frase: un registro | - |
| 978 | 63 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 978 | 133 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 978 | 133 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 981 | 150 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 981 | 150 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 981 | 150 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 981 | 150 | `NOT_DETERMINED` | `UN_REGISTRO` | 1 | documento entero: frase: un so | - |
| 986 | 111 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 991 | 49 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 991 | 146 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 991 | 186 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: NOT_P | - |
| 992 | 98 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 3 | frase: No esta | - |
| 992 | 108 | `NOT_DETERMINED` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 992 | 108 | `NOT_PROVEN` | `SPEC_NO_PUBLICADO` | 1 | documento entero: frase: no es | - |
| 993 | 254 | `NOT_DETERMINED` | `SIN_PISTAS` | 0 |  | - |
| 993 | 260 | `NOT_PROVEN` | `SIN_PISTAS` | 0 |  | - |

Obsoletos declarados por el propio findings: 43.
