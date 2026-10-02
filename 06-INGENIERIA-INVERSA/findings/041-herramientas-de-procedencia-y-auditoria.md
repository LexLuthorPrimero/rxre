# 041 · Dos herramientas para dejar de cometertaina clase de error a mano

`CLASSIFICATION=TOOL` · `TRACK=STATIC` · `TOOL=tools/rx550ref.c, tools/audit_citations.sh`
`GPU INTACTA` · `RUNTIME=NOT_RUN` · `MODIFICATIONS=0` en el corpus

## CUDA principal

Tres de mis últimos hallazgos eran **el mismo error**:

| finding | el error |
|---|---|
| `035` | cité `tonga_sdma_pkt_open.h` para un símbolo cuyo fichero real (`sdma_v4_0.c`) incluye `vega10_sdma_pkt_open.h` |
| `037` | hice `grep ... \| head -20` y leí la parte visible como lista completa |
| `038` | afirmé que `WAIT_REG_MEM_OPERATION` no existe, tras leer `sid.h` cuando `gfx_v8_0.c` incluye `vid.h`. Está en `vid.h:182` |

Ninguno lo detecta un compilador, porque una constante plausible compila. Los tres los paró
**leer**, que es lento y saltable bajo presión de tiempo. `031` ya había registrado el mismo
patrón con el verificador de aridad: *"errors: 0" que no significa nada*.

Esta iteración convierte esa lectura en una comprobación que corre en un segundo. Y al
construirla encontré una limitación que no había considerado, escrita abajo.

## Las dos herramientas

### `tools/rx550ref` — procedencia de un símbolo

Responde las tres preguntas que hay que responder antes de citar algo:

```
$ rx550ref --dir .../amdgpu --dir .../asic_reg --sym WAIT_REG_MEM_OPERATION --in gfx_v8_0.c
=== rx550ref: symbol WAIT_REG_MEM_OPERATION ===
    4 definition(s) across 2 root(s)
    vid.h                 :182   function    x x << 6
    soc15d.h              :191   function    x x << 6
    cikd.h                :307   function    x x << 6
    nvd.h                 :180   function    x x << 6
  ok    all definitions agree:  x x << 6
    23 include(s) in gfx_v8_0.c
  ok    gfx_v8_0.c includes exactly vid.h, which is the only one of the 4 it reaches
```

Tres cosas que la salida da y que antes dependían de leer:

1. **Dónde** está definido, con fichero y línea.
2. **Si discrepan.** Si seis cabeceras lo definen y una dice otra cosa, eso es una trampa y
   la herramienta lo dice.
3. **Si el consumidor lo incluye realmente.** Ésta es la que no cubría nada antes y es la que
   paró los tres errores. `gfx_v8_0.c` no incluye `sid.h`; los campos `WAIT_REG_MEM_*` no
   están ahí.

Modos: `--sym`, `--includes`, `--check FILE:N`, `--decl FILE:N VALOR`, `--selftest`
(11 vectores, todos verdes).

**`--decl` existe por una razón concreta.** La primera versión de la comprobación comparaba
**nombres**, y produjo veinte falsos positivos: `RX550_MM_VM_CONTEXT0_PTBA` contra
`mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` son la misma constante con dos nombres, y comparar
nombres no puede saberlo. La comparación por **valor** sí, porque ambos proyectos escriben los
números igual.

**Y normaliza la notación.** `0x51e` y `0x051E` son el mismo número y no son un
desacuerdo: `gmc_6_0_d.h` escribe uno y `gmc_8_1_d.h` el otro, y reportarlo como
desacuerdo entrena al lector a ignorar desacuerdos. Las expresiones con operador
(`(1u << 20)` contra `(1 << 20)`) se comparan como texto, y el informe **lo dice** en vez de
dejar adivinar cuán firme es un "coinciden".

### `tools/audit_citations.sh` — las citas del proyecto, todas

```
$ sh tools/audit_citations.sh
=== citation audit: does every file.h:LINE exist and say what it claims ===
rx550_pm4.c                           8 citation(s)
rx550_pm4.h                          39 citation(s)
test_pm4.c                            3 citation(s)
rx550pm4val.c                         2 citation(s)
=== findings: same check, over every .md in findings/ ===
    76 finding(s) scanned
=== reachability: every symbol cited with a consumer file ===
    16 symbol/consumer pair(s) checked
=== the specific error of 038, as a standing regression check ===
    ok  WAIT_REG_MEM_OPERATION resolves from gfx_v8_0.c
=== value: does each cited line carry the value I wrote ===
    23 value match(es), 0 mismatch(es), 5 text/unknown
RESULT: 231 citation(s) resolved, 0 skipped (subdirectory)
RESULT: all reachability checks passed
```

**231 citas comprobadas, 76 hallazgos escaneados, cero fallos.** Con tres mutaciones
inyectadas, detectadas las tres que la comprobación puede detectar:

| mutación | detectada | por qué |
|---|---|---|
| citar una línea de `vid.h` más allá del final del fichero | **SÍ** | la línea no existe |
| valor equivocado en la cabecera correcta | **SÍ** | `0x557` contra `0x50e` |
| citar la cabecera de **otra generación** con el mismo valor | **NO** | limitación, abajo |

## La limitación, y por qué la dejé escrita en vez de tapada

La tercera mutación pasa. Citar `nvd.h:106` (que es `PACKET3_WRITE_DATA = 0x37`) en lugar de
`vid.h:201` (que es `PACKET3_SURFACE_SYNC = 0x43`) **no lo detecta** la comparación de valor,
porque si hubiera escrito el valor correcto el valor sería el mismo.

Escribí una comprobación para eso —"la línea citada tiene que ser un `#define`"— y **la
quité**: produjo cinco falsos positivos sobre citas legítimas a la documentación de
enumeraciones de `vid.h:170-180`, que es texto de comentario, no líneas de `#define`.

**Un chequeo con falsos positivos es peor que no tener chequeo**: entrena al lector a
saltárselo, y entonces el fallo real pasa sin que nadie lo mire. Es el mismo argumento que
sostiene el código de salida 2 del validador de `038`, y el mismo que hizo que dejara el
verificador de aridad de `031` con su compuerta de cobertura en vez de entregarlo mintiendo.

Lo que sí distingue los casos es el **nombre** del macro, y comparar nombres entre dos
proyectos con esquemas distintos fue justo lo que produjo los veinte falsos positivos. No
hay aquí una comparación correcta y barata, y decirlo es más útil que un chequeo que a
veces miente.

## Tres decisiones de diseño que la mutation test obligó a cambiar

**El recuento es el valor de retorno, nunca la longitud del array.** `037` leyó una lista
truncada como completa. Aquí `find_defs` devuelve el número encontrado aunque el array esté
lleno, y `--max` declara `TRUNCATED` en vez de recortar en silencio. Un vector del selftest
comprueba exactamente eso con 3 definiciones y `max=1`.

**Comparar por valor, no por texto.** Sin eso, `0x51e` contra `0x051E` es un desacuerdo
falso, y con eso el `0x051E` de `gmc_6_0_d.h:1252` aparecía como conflicto con las otras
cuatro cabeceras del mismo registro.

**El `--dir` se repite, y son dos raíces.** Los macros de paquete (`vid.h`, `sid.h`,
`vega10_sdma_pkt_open.h`) están en `amdgpu/`. Los de registro (`mmVM_*`, `mmATC_*`) están en
`amd/include/asic_reg/`, que es **hermano** de `amdgpu/`, no un subdirectorio. Con una sola
raíz la herramienta respondía `0 definitions` sobre macros que existen — y por eso
`audit_citations.sh` reportó tres registros como inalcanzables en su primera ejecución.

## Lo que esto acelera a partir de ahora

Cada iteración hasta ahora empezaba con lectura manual para establecer de dónde viene un
símbolo y si el fichero que cito lo incluye. Eso son dos o tres lecturas por símbolo, y es
justo el paso que me salteé dos veces. Ahora es un comando:

```
$ rx550ref --dir .../amdgpu --dir .../asic_reg --sym SDMA_OP_PTEPDE --in sdma_v4_0.c
```

que responde las tres preguntas a la vez, y si la respuesta es "no incluido" o "las
cabeceras discrepan", salta antes de escribir una afirmación.

Y `audit_citations.sh` se puede correr **antes de cada hallazgo**, no después: si una cita no
resuelve, se corrige en el momento en que se escribe, en lugar de tres findings después.

## UNLOCKS

- La verificación de contratos de llamada de `031` sigue sin herramienta, y queda
  demostrado por qué: el problema era de cobertura del parser, no de comprobación. Lo que sí
  hay ahora es la verificación de **procedencia** de símbolos, que es la que evita la mitad de
  los errores.
- Los tres errores listados arriba son ahora categorías nombradas, no incidentes:
  *alcance de línea*, *truncado silencioso*, *cabecera no incluida*. Las tres tienen
  comprobación.
- La limitación documentada (cabecera de otra generación con el mismo valor) es un hueco
  concreto: exigiría un mapa `nombre_por_constante` mantenido a mano, que es trabajo
  periódico que se pudriría. `NOT_ATTEMPTED` con el motivo.

## Falsación

- `audit_citations.sh` se refuta si una de las tres mutaciones deja de detectarse, o si
  `rx550ref --selftest` deja de dar 11/11. Ambos se comprueban en un segundo.
- La limitación de "cabecera de otra generación" se cierra si aparece un mutante que la
  detecte. La mutation test es la que la encontró y la puede volver a encontrar.
- La comparación por valor se refuta si dos cabeceras del mismo ASIC escriben el mismo
  registro con valores numéricamente distintos. `mmVM_INVALIDATE_REQUEST` sale
  `0x51e` en cinco cabeceras, incluida la de GCN1 con `0x051E`, y eso no es un desacuerdo.
  Eso lo verificó la herramienta sola, y es el tipo de cosa que yo no habría mirado.

## Evidencia

```
tools/rx550ref.c            1 Tool, C11, sin warnings, 11/11 selftest
tools/audit_citations.sh    231 citas, 76 hallazgos, 3 mutaciones (2 detectadas, 1 documentada)
herramientas previas:        rx550pm4val (038), pm4dw (031, parcial)
modificaciones:              solo en tools/ y 07-DRIVER/; corpus intacto
suite del driver:            22 + 12 + 196 = 230 checks, 0 fallos
corpus:                      MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
