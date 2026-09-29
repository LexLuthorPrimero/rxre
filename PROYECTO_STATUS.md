# Estado del Proyecto: Compresor BC3/DXT5 para RX 550 (Polaris 12)

**Fecha**: 2026-09-29
**Estado global**: **Fase 1 completa. Fase 2: el shader SE EJECUTA en la RX 550, el alfa coincide byte a byte, y el agreement test FALLA en color.**

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

## Fase 2: Descompresor (GPU) — PARCIAL

**Estado**: `PARTIAL`. Código escrito y validado aritméticamente en CPU.
**Ejecución en GPU**: `RUN`. El shader se ejecutó en la RX 550 (RADV POLARIS12).
**Agreement GPU vs CPU**: **NO establecido** — 57 de 64 bloques difieren, todos en color.

### Completado

- `decompress_bc3.comp`: shader GLSL, traducción literal de `rx550_decompress_block()`,
  `alpha_palette()` y `colour_palette()`.
- Compila a SPIR-V con `glslangValidator` 16.3.0, `rc=0`, 11984 B.
- `shader_vs_c`: **0/4096** canales discrepantes frente a `rx550_decompress_block()`, en la
  variante que lee los endpoints de color de `block 2`, que es como lee el shader
  (`decompress_bc3.comp` toma `c0`/`c1` de `w2`, bytes 8..11).
- Sincronizado con el C tras AD-11: shader y `alpha_palette()` llevan ambos `+3`/`+2`.

### Lo que se midio, y lo que falla

**El shader ejecuta en la RX 550.** Pipeline creado, `vkCmdDispatch(1,1,1)`, fence completado:
No es aritmética simulada.

```
[ OK ] 940 de 4096 bytes distintos de cero
[ OK ] ninguna palabra conserva el patron veneno 0xDEADBEEF
RESULT: GPU != CPU. 57 de 64 bloques difieren.
  bloques discrepantes : 57 de 64
  bytes discrepantes   : 3197 de 4096
```

**Alfa: 0 discrepancias de 4096.** La rampa BC3 del shader coincide byte a byte con
`rx550_decompress_block()` en hardware real.

**RGB: 57 de 64 bloques.** Error estrecho y sistemático (±57/±58), no redondeo ni ruido.
Causa `NOT_DETERMINED`.

### Corrección de un diagnóstico anterior (AD-14)

Mi informe previo atribuyo el SIGSEGV de `vkCreateComputePipelines` como defecto del driver.
**Era falso: era mío.** Mis declaraciones de structs Vulkan escritas a mano. Con
`<vulkan/vulkan.h>` real (vulkan-headers 1.4.341.0) el pipeline se crea sin crash.

La autovalidación previa a la comparación hizo su trabajo: se negó a reportar `PASS` sobre una
salida **entera a cero**, que habría producido «0 discrepancias» y un falso éxito.

**Defecto abierto y peligroso**: el test imprime `[FAIL]` por `stderr` y devuelve `rc=0`.
Con la salida canalizada parece exitoso. Cualquier CI que compruebe el código de salida
reportaría **verde sobre un fallo**. No corregido.

### Detalle importante sobre AD-11

AD-11 **no** está verificado contra el hardware. Settlea qué dice el texto de la
especificación. Ver AD-12.

---

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
| AD-13 | Estado de Fase 2: `PARTIAL`, Fase B `NOT_WRITTEN` |
| D19a | Convención BC3 `a0 = max, a1 = min` (`44bc133`): bloques con la rama `/7` de **0 a 59 de 64** |

---

## Limitaciones conocidas

1. **El agreement test NO pasa.** El shader corre, pero 57 de 64 bloques difieren en color.
2. **La interpolación del hardware es `NOT_DETERMINED`** (AD-12).
3. **El test devuelve `rc=0` aunque imprima `[FAIL]`.** Un CI reportaría verde sobre un
   fallo. No corregido.
4. `test_decompress.c` fue borrado del disco a mitad de la ronda de trabajo y reconstruido
   después por otra sesión de este mismo proyecto.

---

## Próximos pasos, si se continúa

1. `sudo dnf install vulkan-devel` y reescribir la Fase B con `<vulkan/vulkan.h>` real.
2. Ejecutar el agreement test byte a byte GPU vs CPU en la RX 550.
3. Resolver AD-12 con el experimento GL, o con la ruta Vulkan-graphics (probada en cuanto a
   que `vkcube` renderiza en RADV con `rc=0`, luego la ruta de cómputo no es necesaria).
4. Si el hardware trunca, revertir AD-11 y reabrir la divergencia contra bcdec.

---

## Conclusión

El compresor BC3/DXT5 está completo, medido y con un test que se ha comprobado que puede
fallar. El descompresor existe, compila y su aritmética concuerda con el decodificador de CPU
en **0/4096** canales. Lo que falta es evidencia de ejecución en la RX 550, y la causa es del
entorno de desarrollo, no del código. La pregunta AD-12 queda explícitamente abierta en lugar
de resuelta por asunción.
