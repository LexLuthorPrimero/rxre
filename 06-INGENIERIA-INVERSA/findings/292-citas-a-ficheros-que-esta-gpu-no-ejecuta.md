# 292 · 164 citas apuntan a ficheros que esta GPU no ejecuta, y `dce_v8_0.c` es código muerto

`CLASSIFICATION=EVIDENCE` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0` (por clase+vendor, nunca por índice)

## Cuestión principal

De las citas del proyecto, **cuántas apuntan a un fichero que esta GPU no
ejecuta**. No es una pregunta retórica: si la respuesta fuera alta, el corpus
tendría material de GCN1…GCN12 mezclado y citar un fichero de Vega sería un
error de alcance, no de forma. Hay que medirlo antes de afirmarlo.

## Criterio de terminación

Contar, clasificar y **decidir si el número es alto o bajo**. También comprobar
que la herramienta que cuenta no sea la fuente de un error propio. **Cumplido.**

## Herramienta: `tools/citegen.py`, validada antes de usarla

```
=== citegen selftest ===
  OK   gmc_v8_0.c     EN_DISPATCH     el case anade gmc_v8_1_ip_block, definido en este fichero
  OK   sdma_v4_0.c    EN_RUTA_IP      nadie lo anade por case, pero discovery lo enruta por version
  OK   sdma_v3_0.c    EN_DISPATCH     el chip anade sdma_v3_1_ip_block, definido en este fichero
  OK   gfx_v7_0.c     NO_EN_DISPATCH   declara 3 bloques, codigo compartido
  OK   gmc_7_0_d.h    FUERA_DE_AMDGPU   es asic_reg, no amdgpu/
  OK   una cita sin numero de linea se clasifica igual
RESULT: PASS (6 vectores)
```

Con **controles negativos** (`gfx_v7_0.c` → `NO_EN_DISPATCH`,
`gmc_7_0_d.h` → `FUERA_DE_AMDGPU`). Es decir: la herramienta sabe decir "no".
Sin eso, un recuento no dice nada.

## El recuento

```
citas 3956   (ficheros .md/.c/.h/.sh/.py, corpus excluido)
  EN_DISPATCH         2923      (73,8%)
  EN_RUTA_IP           530      (13,4%)
  FUERA_DE_AMDGPU      339      ( 8,6%)
  NO_EN_DISPATCH        91      <-- SOSPECHOSO
  OTRO_ASIC             73      <-- SOSPECHOSO
                     ─────
                     164 / 3956 = 4,1%
```

`rc=1` cuando hay sospechosas. Código de salida distinto de cero, como debe.

## Mi hipótesis era FALSA, y eso es el resultado

Yo esperaba un número alto. **4,1% no es alto.** La disciplina de alcance de las
citas del proyecto es buena, y la hipótesis queda **REFUTADA**, no "revisada".

## Dónde están las 164, y por qué casi todas son benignas

| directorio | citas | |
|---|---|---|
| `06-INGENIERIA-INVERSA` (findings) | **84** | la mitad |
| `docs` | 32 | |
| `revkit` | 14 | |
| `08-ARQUITECTURA` | 9 | |
| `02-ARQUITECTURA` | 8 | |
| `tools` | 7 | |
| `04-IMPLEMENTACION` | 6 | |
| `05-FUENTES-EXTERNAS` | 3 | |
| `07-DRIVER` | 1 | |

La mitad están en los hallazgos, que es donde viven los claims, así que ahí
habría que mirar. Y al mirarlas, **los títulos declaran el alcance ellos
mismos**:

```
045-la-convencion-de-count-nunca-se-midio-en-mi-asic.md   ← "en mi ASIC"
098-prt-funciona-al-reves-en-gfx9.md                      ← "en GFX9"
133-g-el-mtype-no-existe-en-gfx8.md                       ← "en GFX8"
```

Eso son **comparaciones entre generaciones, etiquetadas**. Y la comparación de
generaciones **es evidencia**: es lo que permite decir "esto sí funciona aquí y
esto no". El peligro es citarla **sin decirlo**, y aquí se dice.

**La distribución es la opuesta del problema que temía**: las citas a otros ASIC
se concentran en los hallazgos que más claramente declaran el alcance.

## Los ficheros más citados como sospechosos

```
gmc_v7_0.c   25      gmc_v6_0.c   22      gfx_v7_0.c   18
gfx_v6_0.c   12      sdma_v2_4.c  10      dce_v8_0.c    6
```

Los cuatro primeros son material de **GCN1/GCN2/GCN3** (`gmc_v6_0` = Tonga,
`gfx_v6_0` = GCN1). Es coherente con que se citen al comparar generaciones.

## Y el hallazgo de fondo: `dce_v8_0.c` NO lo ejecuta nadie

El quinto, `dce_v8_0.c`, **no** es lo mismo que los otros, y `citegen` tiene
razón al marcarlo:

```
dce_v8_0.c:3560   const struct amdgpu_ip_block_version dce_v8_0_ip_block = {
```

**Definido, y no lo añade nadie.** No hay ningún
`amdgpu_device_ip_block_add(adev, &dce_v8_0_ip_block)` en todo `amdgpu/`, ni
aparece en `amdgpu_discovery.c`. Y tampoco se llama desde fuera:

| símbolo | referencias fuera de `dce_v8_0.c` |
|---|---|
| `dce_v8_0_atomic_enable` | ninguna |
| `dce_v8_0_early_init` | ninguna |
| `dce_v8_0_sw_init` | ninguna |
| `dce_v8_0_irq_set` | ninguna |

**Es un fichero que parece el driver de display de GFX8 y no está conectado a
nada.** El DC de GFX8 entra por otro camino (`dm_ip_block`, condicionado a
`CONFIG_DRM_AMD_DC` y a `amdgpu_device_has_dc_support()`), que es justo lo que
la decisión de diseño del switch deja ver.

Y esto importa porque existe un hallazgo que dice literalmente
`el-decodificador-esta-en-dce`: **`060` apoya su localizar en un fichero que no
se ejecuta.** Eso no lo hace falso por sí solo — el fichero puede *contener* el
código aunque su bloque no se añada — pero **no puede citarse como prueba de lo
que el hardware hace**, solo como texto.

### El alcance de esta afirmación, acotado

- He comprobado **4 símbolos** de los muchos del fichero. `NOT_DETERMINED` si
  algún otro se referencia.
- No he comprobado `dce_v8_0.hwseq` ni las cabeceras.
- No he mirado si algún módulo fuera de `amdgpu/` lo referencia.
- **No he construido nada ni ejecutado nada.** Es `PROVEN` sobre el texto.

## Un aviso de la herramienta que NO era un problema

`citegen` avisa de que un `case` no se cerró con `break` en 60 líneas
(`vi.c:1344`). Fui a mirarlo, esperando un hueco en el grafo de despacho, y
**tenía yo la idea equivocada**: `vi.c:1344` es el `case CHIP_POLARIS12:` de la
función de **contadores de rendimiento**, con `case CHIP_TOPAZ:` detrás. Es un
`case` repetido 8 veces en `vi.c`, y el escáner cogió uno que no era el del
despacho.

El caso del despacho es un **grupo de fallthrough**, y `CHIP_POLARIS12` es la
**tercera** etiqueta:

```c
case CHIP_POLARIS10:
case CHIP_POLARIS11:
case CHIP_POLARIS12:
case CHIP_VEGAM:
        amdgpu_device_ip_block_add(adev, &vi_common_ip_block);
        ...
        break;
```

Son 8 incondicionales + 2 condicionales = **10 bloques**, que es exactamente lo
que dice la herramienta. **`citegen` acertó y yo sospeché de ella.** Casi
registro como defecto suyo un acierto suyo.

## Cuatro aliasing corroborados en un solo `case`

Ese mismo `case` muestra, de una vez, cuatro de los aliasing que ya tení­a
registrados, y uno que **no**:

| bloque añadido | versión del bloque | versión del código |
|---|---|---|
| `gmc_v8_1_ip_block` | GMC **8.1** | `gmc_v8_0` |
| `sdma_v3_1_ip_block` | SDMA **3.1** | `sdma_v3_0` |
| `uvd_v6_3_ip_block` | UVD **6.3** | `uvd_v6_0` |
| `vce_v3_4_ip_block` | VCE **3.4** | `vce_v3_0` |
| `tonga_ih_ip_block` | **Tonga** | — |

**Nuevo:** Polaris12 es **Baffin**, y usa el bloque de interrupciones de **Tonga**.
No es una versión nueva del IH, es el de otro ASIC reutilizado. Es el **quinto**
caso de aliasing, y el primero que no es "mismo número de familia, distinto
sub-número": es un ASIC distinto cuyo bloque se comparte entero.

## Confounders

- **`citegen` no cubre** citas sin número de línea, ni a funciones, ni a
  registros. Solo citas con nombre de fichero de ASIC. El 4,1% es del subconjunto
  que la tool covers, **no del total de citas del proyecto**.
- `FUERA_DE_AMDGPU` (339) no significa suspicious: son cabeceras de `asic_reg`,
  que **sí** son las de esta placa. La herramienta lo distingue y con razón.
- El grafo se construye leyendo el `case`; los bloques que añade una función
  con otra forma dan `NO_EN_DISPATCH`. Es un `NEGATIVE_RESULT` **acotado**.
- No he revisado **una por una** las 84 citas de los hallazgos: he mirado los
  títulos de los 8 primeros. Que 3 de 3 declaren alcance **no prueba** que los
  81 restantes lo hagan.
- `revkit` (14) y `05-FUENTES-EXTERNAS` (3) son contenido externo; sus citas
  tienen otro contrato.

## Clasificación

| afirmación | estado |
|---|---|
| 164 de 3956 citas apuntan a ficheros no ejecutados por esta GPU | `PROVEN` — `citegen`, self-test PASS |
| `citegen` tiene 6 vectores conocidos y 2 controles negativos | `PROVEN` |
| el 87,2% de las citas está en ruta de ejecución o de IP | `PROVEN` |
| las 3 primeras con más citas declaran su alcance en el título | `OBSERVED` — lectura de 3 títulos |
| las 84 restantes también lo declaran | **`NOT_DETERMINED`** |
| `dce_v8_0_ip_block` no lo añade nadie | `PROVEN` — grep en todo `amdgpu/` |
| 4 símbolos de `dce_v8_0.c` no se referencian fuera | `PROVEN` |
| `dce_v8_0.c` entero es inalcanzable | `PARTIAL` — 4 de N símbolos |
| Polaris12 añade 10 bloques en el `case` de `vi.c:2107` | `PROVEN` |
| el aviso de `vi.c:1344` es un artefacto, no un hueco | `PROVEN` — el `case` es de perf counters |
| Baffin usa `tonga_ih_ip_block` | `OBSERVED` — `vi.c:2112` |
| ese IH es "el mismo" que el de Tonga en comportamiento | `NOT_DETERMINED` |
| mi hipótesis de contaminación alta | `REFUTED` |

## Desfalsificación

- **(a)** 164 sospechosas → refutable ejecutando `citegen.py --kernel
  RESEARCH/working/linux-7.1.3`. **Verificado.**
- **(b)** `citegen` sabe decir que no → refutable con sus vectores
  `gfx_v7_0.c` y `gmc_7_0_d.h`. **Verificado.**
- **(c)** el aviso de `vi.c:1344` es inofensivo → refutable leyendo `vi.c:1344`
  y `vi.c:2107`. **Verificado.**
- **(d)** `dce_v8_0_ip_block` no se usa → refutable grepeando
  `amdgpu_device_ip_block_add` en `amdgpu/`. **Verificado: 0.**
- **(e)** Baffin usa el IH de Tonga → refutable leyendo `vi.c:2107-2124`.
  **Verificado.**
- **(f)** las 84 citas de hallazgos son benignas → **NO comprobado.** Es la
  límite de este hallazgo.

## UNLOCKS

- **El proyecto tiene buena disciplina de alcance de citas**, y ahora está
  medido en vez de supuesto. 87,2% en ruta de ejecución.
- **`dce_v8_0.c` es un señuelo**: parece el driver de display de GFX8 y no está
  conectado a nada. Un fichero puede *contener* la respuesta y no *ejecutarse*:
  son dos cosas, y citarlas como prueba de hardware confunde una con otra.
- **Un quinto aliasing**: Baffin reutiliza el bloque de interrupciones de
  Tonga entero. No es "misma familia, otro sub-número" como los otros cuatro.
- **`citegen` es TOOL_VALIDATED y se le puede dar el número.** Casi lo retiro
  por un aviso que era sobre otro `case`.
- **Siguiente paso, y es el que queda de este hallazgo**: `060` apoya la
  localización del decodificador en `dce_v8_0.c`. Si ese fichero no se ejecuta,
  el hallazgo necesita otro apoyo, o necesita decir que su evidencia es
  textual y no de ejecución. Es una comprobación de **una** afirmación
  concreta, no un juicio sobre las 84.

## Evidencia

```
python3 tools/citegen.py --selftest                      PASS (6 vectores)
python3 tools/citegen.py --kernel RESEARCH/working/linux-7.1.3    rc=1
  EN_DISPATCH 2923 · EN_RUTA_IP 530 · FUERA 339 · NO_EN_DISPATCH 91 · OTRO_ASIC 73
grep -rn "dce_v8_0_ip_block" amdgpu/*.c        solo la definicion, dce_v8_0.c:3560
grep -rn "dce_v8_0_sw_init\|dce_v8_0_atomic_enable" amdgpu/  fuera de su fichero: nada
vi.c:2105-2124   case POLARIS10/POLARIS11/POLARIS12/VEGAM -> 10 bloques
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.