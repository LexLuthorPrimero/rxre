# 04-IMPLEMENTACION — Fase 1 (compresor CPU) y Fase 2 (descompresor GPU)

Pipeline cerrado y verificado sobre la RX 550: **PNG → BC3 en CPU → decodificación
BC3 en la GPU → PNG**, con comparación byte a pixel.

## Los tres comandos

```sh
# 1. Construir los dos binarios del pipeline
make -C 04-IMPLEMENTACION

# 2. Ejecutar el pipeline completo sobre el corpus (requiere la RX 550)
./04-IMPLEMENTACION/integration_test.sh

# 3. Comprobar el codec de la Fase 1 por separado
make -C 04-IMPLEMENTACION/compressor test
```

El segundo comando debe terminar con `3/3 texturas: ESTADO: PASO` y código de
salida 0.

## Qué produce

| Artefacto | Qué es |
|---|---|
| `bin/rx550_compress` | PNG → BC3. CPU. |
| `bin/rx550_decompress` | BC3 → PNG. Vulkan compute sobre `1002:699f`. |
| `common/png_rw.[ch]` | Lector y escritor PNG de 8 bits, sin interlazado. |
| `integration_test.sh` | El pipeline, con su veredicto. |

`bin/` y `work/` están en `.gitignore`: son artefactos de compilación y de
corrida, no fuentes.

## Uso de las herramientas por separado

```sh
# Fase 1
bin/rx550_compress entrada.png salida.bc3 referencia.rgba

# Fase 2 — se ejecuta desde decompressor/ porque el shader se carga por ruta
cd decompressor
../bin/rx550_decompress ../salida.bc3 ../salida.png ../referencia.rgba
```

El `cd` no es cosmético: `rx550_decompress` abre
`../decompressor/decompress_bc3.spv` relativo a su directorio de trabajo. Copiar
el `.spv` a otro sitio produciría un módulo que nadie valida.

## Las tres cifras que imprime el pipeline

No son la misma cifra y no deben resumirse en una:

| Cifra | Qué mide | Por qué no basta sola |
|---|---|---|
| `0/16384 discrepancias` | Fidelidad del **decodificador**: GPU vs CPU, byte a byte | Es 0 con cualquier contenido, incluso con basura. No dice nada de la calidad. |
| `XX dB PSNR` | Calidad del **codificador** con pérdida: original vs round-trip | Depende del contenido. Un decodificador fiel con un codificador malo da PSNR bajo y 0 discrepancias. |
| `GPUVSCPU 0` en orden de imagen | Que el **PNG escrito** conserva ese orden | Detecta un reordenamiento de bloques silencioso, que la comparación de bytes no ve. |

## Tres defectos que este pipeline encontró, y que un test de bloques no habría visto

Los tres son el mismo patrón: un número correcto en cada lado y una comparación
entre cosas distintas.

1. **Orden de bloque frente a orden de imagen.** La GPU escribe el bloque `b`,
   píxel `p` en `b*64 + p*4`; la imagen lo quiere en
   `(by*4+py)*stride + (bx*4+px)*4`. Para el primer bloque coinciden. Después
   no. Compararlos daba ~13 000 discrepancias falsas con ambos lados correctos.

2. **Un factor 4 en el destino.** Al reordenar, `dst` multiplicaba por 4 el
   término de columna pero no el de fila: desplazamiento en píxeles para uno y
   en bytes para el otro. Escribía correctamente la primera fila y el resto
   en otro sitio. Una imagen plausible arriba y corrupta debajo.

3. **`-v p=` en vez de `$1` en awk.** El PSNR llegaba por `stdin` y la
   comparación se hacía en `BEGIN`, que no lee `stdin`. `$1` estaba vacío, así
   que toda textura comparaba `0 >= suelo` y fallaba. El `pipe` era decoración.

Los dos primeros los detectó la comparación pixel a pixel, no la de bytes. Por
eso están las tres: la de bytes sola habría dado un verde falso.

## Lo que este pipeline NO demuestra

- **Que el códec cumpla BC3.** El decodificador de la GPU coincide con
  `rx550_compress_block()`, que es la especificación aritmética de este
  proyecto. Que ambos coincidan no prueba que la rampa alfa sea la de la
  especificación Microsoft. Eso lo comprueba
  `compressor/test_alpha_ramp_independent.c`, contra una transcripción
  independiente, y es un test distinto.
- **Que la GPU es hardware y no llvmpipe.** El dispositivo se selecciona por
  identidad PCI `1002:699f`, no por índice de enumeración, así que no es
  llvmpipe. Que el *resultado* no se haya calculado en software es otra
  pregunta, y es P-9 / AD-12, no esto.
- **Rendimiento.** Un dispatch de 256 bloques no mide throughput.
- **Que el módulo `rx550.ko` cargue.** `CONFIG_SECURITY_LOCKDOWN_LSM=y` rechaza
  módulos sin firmar en este host. Nada de esto corre en el kernel.

## Autorización

`rx550_decompress` ejecuta compute en la RX 550. Eso es `RUNTIME_GPU` y está
cubierto por **AD-7** (2026-09-28), para validar el descompresor. El pipeline no
escribe sysfs, no cambia políticas de energía ni relojes, no toca IRQ y no
modifica el kernel.
