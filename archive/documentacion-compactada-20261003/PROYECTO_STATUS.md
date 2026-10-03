# Estado del Proyecto: Compresor BC3/DXT5 para RX 550 (Polaris 12)

**Fecha**: 2026-09-29
**Estado global**: **Fase 1 completa. Fase 2 completa — el shader se ejecuta en la RX 550 y su salida coincide byte a byte con el decodificador de CPU (0/4096, 3 corridas).**

> Todas las cifras de este documento fueron **medidas en esta host el 2026-09-29** con los
> targets del `Makefile`. Las que no pude medir están marcadas como `NOT_DETERMINED`, no
> estimadas.

---

## Fase 1: Compresor (CPU) — COMPLETA

**Estado**: `COMPLETE`. Verificado, discriminado y medido.

### Características

| Aspecto | Estado | Evidencia |
|---|---|---|
| Formato | BC3/DXT5 estándar | AD-11 |
| Interpolación alfa | Redondeo `+3`/`+2` | AD-11, `test_alpha_ramp` |
| Convención de endpoints | `a0 = max, a1 = min` | D19a (`44bc133`) |
| Inset de endpoints alfa | `RX550_ALPHA_INSET_STEPS 0` | AD-10 |

### Metricas medidas

- **Checks**: **26/26 `[ OK ]`, 0 `[FAIL]`** (`make test`)
- **Resultado del decodificador**: `RESULT: all checks passed`
- **Resultado de conformidad**: `RESULT: CONFORMA con la especificacion Microsoft (AD-11, +3/+2)`
- **PSNR**: reference **28.78** dB · smooth **19.59** dB · pure noise **13.65** dB ·
  adversarial **10.90** dB
- **Throughput** (MB/s de entrada consumida): C **83.7** · AVX2 **86.0** → speedup **1.03×**
- **AVX2 bit-idéntico al C**: sí, sobre 200000 bloques

> El throughput depende de la carga de la máquina. La medición corresponde a esta host y este
> momento; no es un número portable entre equipos.

### El test discrimina (verificado, no supuesto)

Que `make test` pase no prueba nada por sí solo: un test que compara la implementación contra
una copia de sí mismo siempre pasa. El repo tiene un mutant deliberado para evitar exactamente
eso, y lo ejecuté:

```
$ make check-ramp-discriminates
  total : 65536 / 65536 pares con discrepancia
  peor error : 255 de 255
  RESULT: NO CONFORMA con la especificacion -- 65536 pares discrepan
  OK: rejected the known-wrong ramp (exit 1). The test discriminates.
  rc=0
```

El mutante se rechaza, luego la referencia de `test_alpha_ramp_independent.c` sigue siendo
independiente de la implementación y el resultado `CONFORMA` significa algo.

> Nota de procedencia: esa referencia comparaba antes contra **bcdec v0.985** (que trunca) y
> fallaba con 54300/65536 discrepancias. Ahora compara contra la especificación Microsoft
> (que redondea). El cambio de referencia es correcto dado AD-11, y la capacidad de fallar del
> test se comprobó después del cambio, no antes.

### Archivos clave

- `04-IMPLEMENTACION/compressor/rx550_compress.c`
- `04-IMPLEMENTACION/compressor/rx550_compress_avx2.s`
- `04-IMPLEMENTACION/compressor/rx550_compress.h`
- `04-IMPLEMENTACION/compressor/test_compress.c`
- `04-IMPLEMENTACION/compressor/test_alpha_ramp_independent.c`
- `04-IMPLEMENTACION/compressor/test_alpha_ramp_mutation.c`

---

## Fase 2: Descompresor (GPU) — COMPLETA

**Estado**: `COMPLETE`. El shader se ejecutó en la RX 550 y su salida coincide **byte a byte**
con el decodificador de referencia de CPU.
**Ejecución en GPU**: `RUN`, reproducible.
**Agreement GPU vs CPU**: **ESTABLECIDO** — 0 de 4096 bytes, en 3 corridas consecutivas.

### Evidencia

```
[0] 1002:699f  AMD Radeon RX 550 / 550 Series (RADV POLARIS12)   <- objetivo, por PCI identity
[2] 10005:0000 llvmpipe                                           <- presente, NO seleccionado
[ OK ] vkCreateDevice, familia de colas compute 0
[ OK ] vkCreateShaderModule -- el driver aceptó el módulo
[ OK ] vkCmdDispatch(4,1,1), submit y fence completados
[ OK ] 4005 de 4096 bytes distintos de cero
[ OK ] ninguna palabra conserva el patrón veneno 0xDEADBEEF
  bloques discrepantes : 0 de 64
  bytes discrepantes   : 0 de 4096
RESULT: GPU == CPU.          rc=0
```

Alfa y color coinciden por igual: la comparación es sobre los 4096 bytes completos, no sólo
sobre un canal. La cobertura del corpus se mide y se imprime — 5 bloques en el modo de 6 valores
de la rampa alfa, 59 en el de 8.

### Los tres defectos que lo bloqueaban

Ninguno era visible desde el lado CPU. `shader_vs_c` dio **0/4096** con los tres presentes.

1. **Índice de color** (`decompress_bc3.comp`): `& 0xFFu` donde el C lee 2 bits; el `& 3u`
   posterior recortaba a los dos bits **altos** del byte. Los píxeles 2 y 3 de cada grupo de 4
  tomaban el índice de otro píxel — de ahí los pares transpuestos con diferencia constante ±58.
   Además la rama `else` leía fuera del bloque para `p = 8..15`: `c_idx` son 4 bytes, una sola
   palabra, no dos como el array de 6 bytes del alfa.
2. **Faltaba `vkCmdPushConstants`**: el shader acotaba el dispatch con `params.num_blocks` leído
   de memoria no inicializada. Con basura grande no escribía nada; con basura pequeña se ejecutaba
   por suerte. La primera corrida (3197 bytes erróneos) fue una ejecución afortunada, no un
   resultado reproducible.
3. **`DISPATCHES` mal calculado**: `ceil(64/256) = 1` cuando el shader mapea una invocación a un
   **píxel**, no a un bloque — un workgroup de 256 cubre 16 bloques. Hacían falta 4. Los bloques
   16..63 nunca se escribieron.

Ver AD-13 en `DECISIONS.md` para el detalle y para lo que este test **no** establece.

### Límites

- `GFX_HWIP` sigue `NOT_DETERMINED`: este test no consulta la generación gfx ni la infiere.
- Validación de esquema SPIR-V: **CORREGIDO** — `spirv-val` **sí** está instalado
  (`/usr/bin/spirv-val`, SPIRV-Tools v2026.1) y valida `decompress_bc3.spv` con `rc=0`.
    Escribí que faltaba; era falso. Queda pendiente únicamente que el driver acepte el
    módulo, que es evidencia sobre ese driver.
- El corpus es determinista y sintético: es una guarda de regresión, no una prueba exhaustiva.
- Un dispatch no mide rendimiento.

## AD-12: comportamiento del hardware — `NOT_DETERMINED`

**Pregunta abierta**: ¿el sampler del Polaris 12 decodifica la rampa alfa de BC3 con
truncamiento o con redondeo `+3`/`+2`?

**Por qué no es un detalle**. Este proyecto entrega un **encoder**, y el consumidor del encoder
es el hardware. Si el sampler trunca, `rx550_compress.c` emitiría bloques que la RX 550
decodifica distinto de como predice `rx550_decompress_block()`. El error no aparecería en un
informe: viajaría **dentro del payload del bloque**, de forma sistemática, en el 82.9 % de los
pares de endpoints. Un round-trip contra el decodificador propio lo ocultaría por construcción.

**Método preparado**: adjuntar una textura DXT5 directamente como color attachment de un FBO y
leer con `glReadPixels`. Sin shader, sin quad, sin dibujar. Evita por diseño la ruta de cómputo
Vulkan que no funciona. Cobertura: los 65536 pares de endpoints × 8 índices = 1048576
observaciones. Con autovalidación en 4 puntos, el último de los cuales es que los índices 0 y 1
decodifiquen exactamente a `a0`/`a1` — que no interpolan y por tanto prueban el camino, no la
rampa.

**Mientras tanto**: el redondeo se mantiene por coherencia interna entre encoder y shader,
marcado como **no validado contra el hardware objetivo**.

---

## Decisiones arquitectónicas

| ID | Decisión |
|---|---|
  | AD-10 | `RX550_ALPHA_INSET_STEPS 0` — mismo PSNR (±0.01 dB), 2.8× más rápido |
| AD-11 | Interpolación BC3 con redondeo `+3`/`+2` según especificación Microsoft D3D9 |
| AD-12 | Rampa del hardware Polaris 12: `NOT_DETERMINED` |
| AD-13 | Fase 2 `COMPLETE`: agreement test GPU==CPU, 0/4096, tres defectos corregidos |
| D19a | Convención BC3 `a0 = max, a1 = min` (`44bc133`): bloques con la rama `/7` de **0 a 59 de 64** |

---

## Limitaciones conocidas

> **RECONCILIADO 2026-10-01 (docs/).** Los cuatro puntos siguientes se escribieron
> entre `b8294b1` y `b7ed0c1` (2026-09-29 00:44–01:10), **antes** de que `7ed1eca`
> (01:17) elevara la Fase 2 a `COMPLETE`. El punto 1 quedó sin corregir y pasó a
> contradecir la cabecera del propio fichero. Se conservan con su estado histórico
> y se marcan; el estado vigente es `PASS` — ver §Fase 2 y `docs/CONTRADICTIONS.md`
> (`C-001`).
>
> 1. **`SUPERSEDED` — ya no aplica.** El agreement test **pasa**: 0 de 64 bloques,
>    0 de 4096 bytes, en 3 corridas. El "57 de 64" era el estado previo a la
>    corrección de los tres defectos de AD-13. No volver a contarlo como vigente.
> 2. **VIGENTE.** La interpolación del hardware es `NOT_DETERMINED` (AD-12).
> 3. **VIGENTE, no comprobado.** El test devuelve `rc=0` aunque imprima `[FAIL]`.
>    Escrito por `b7ed0c1` el 2026-09-29; **no se ha vuelto a verificar**. El
>    estado correcto es `NOT_RECHECKED`, no `VIGENTE`.
> 4. **VIGENTE como incidente.** `test_decompress.c` fue borrado del disco a mitad
>    de ronda y reconstruido por otra sesión.

---

## Próximos pasos, si se continúa

> **RECONCILIADO 2026-10-01.** Los puntos 1 y 2 quedaron obsoletos el 2026-09-29 01:17
> (`7ed1eca`): `vulkan-devel` ya no hace falta — `test_decompress.c` usa las cabeceras
> reales de Vulkan — y el agreement test **ya se ejecutó** en la RX 550.

1. ~~`sudo dnf install vulkan-devel`~~ — `SUPERSEDED`, ya instalado y usado.
2. ~~Ejecutar el agreement test byte a byte GPU vs CPU en la RX 550.~~ — `SUPERSEDED`,
   ejecutado: 0 de 4096 bytes, 3 corridas (`7ed1eca`).
3. Resolver AD-12 con el experimento GL, o con la ruta Vulkan-graphics (probada en cuanto a
   que `vkcube` renderiza en RADV con `rc=0`, luego la ruta de cómputo no es necesaria).
4. Si el hardware trunca, revertir AD-11 y reabrir la divergencia contra bcdec.

---

## Conclusión

> **RECONCILIADO 2026-10-01.** La última frase ("lo que falta es evidencia de ejecución
> en la RX 550") era **falsa** al escribirse y quedó sin corregir: la ejecución en la
> RX 550 está acreditada desde el 2026-09-29 01:17 (`7ed1eca`). Texto original conservado
> abajo.

El compresor BC3/DXT5 está completo, medido y con un test que se ha comprobado que puede
fallar. El descompresor existe, compila y su aritmética concuerda con el decodificador de CPU
en **0/4096** canales. ~~Lo que falta es evidencia de ejecución en la RX 550, y la causa es del
entorno de desarrollo, no del código.~~ La pregunta AD-12 queda explícitamente abierta en lugar
de resuelta por asunción.

**Estado vigente de la conclusión**: Fase 1 `COMPLETE`. Fase 2 `COMPLETE` con ejecución
real en la RX 550. Lo único que sigue abierto del lado BC3 es **AD-12** — si el sampler
del Polaris 12 decodifica la rampa alfa con truncamiento o con redondeo `+3`/`+2`.
Todo lo demás que este fichero.listaba como pendiente se cerró o está `SUPERSEDED`
arriba.
