# 1569 · `exit 0` con el ejecutable equivocado: `rizin -qc -I -j` responde 0 y(stdout es su banner

```
CLASSIFICATION=ERROR · TRACK=RUNTIME
HARDWARE_SCOPE=NINGUNO · WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS=0
GPU INTACTA
CIERRA=el fallo "silencioso mas caro" de la vertical binary.inspect
ABRE=el patron "rc=0 con stdout que no es el pedido" en el resto de producers
```

## Qué pasó

El adapter de `binary.inspect` construyó su comando con el ejecutable del
registro (`rizin`, que es el de análisis) en vez del binario propio del producer
(`rz-bin`):

```text
argv  =  ['rizin', '-qc', '-I', '-j', '/bin/ls']
rc    =  0
stdout=  -- You can use registers in math expressions. For example: 'wx 1234 @ esp - 2'
         [0x00003910]>
         [0x00003910]>
```

`rc=0`, salida no vacía, ningún error. Y el resultado fue `error` — pero sólo
porque la normalizaciónosomaló a fallar al parsear. Si el normalizador hubiera
sido tolerante, habría devuelto un `ok` con el banner como contenido.

## Por qué es el fallo más caro de esta clase

```
exit 0 != resultado válido
```

§26 lo exige, y este caso lo demuestra con una sutileza: **`rc=0` no es un
resultado, pero tampoco delata el error**. Un pipeline con `set -e` habría
continuado. Lo único que lo delató fue el contenido.

Los otros dos detalles que trouxe el mismo fallo:

- `rz-bin -j` **a secas** imprime el `usage` y sale. `-j` es modificador, no
  modo: hay que combinarlo (`-Ij`, `-Sj`, `-sj`, `-ij`, `-Ej`).
- `stdout` trae ANSI y `\r` por defecto. Sin `-e scr.color=0` el JSON no parsea,
  y eso es `error` sobre una salida perfectamente válida. El contrato lo
  declara en un campo `limpieza` con `{aplicada, caracteres_quitados}`.

## La reparación, y por qué la mutación se llama así

El registro declara `exe="rizin"` porque el análisis lo produce rizin; la
inspección estática la produce **`rz-bin`**, que es otro binario. La allow-list de
backends no contiene la noción de "producer ≠ entrypoint", y ahí estaba el hueco.

Se añadió la mutación **`el adapter usa el ejecutable equivocado (exit 0 + banner)`**,
que reproduce exactamente esto. Si no la detecta un vector, `exit 0` vuelve a
ser sinónimo de resultado válido.

## Reproducir

```bash
rizin -qc -I -j /bin/ls ; echo "rc=$?"     # banner + prompt, rc=0
rz-bin -I -j /bin/ls | head -c 60          # JSON correcto
```

## Provenance

```text
artefacto   /bin/ls  sha256 54e936d37decdad9…
producers   rizin 0.7.4 (mal invocado) · rz-bin 0.7.4 (bien invocado)
transform   argv -> subprocess -> rc + stdout -> limpieza -> json.loads
adapter     backends/adapters/rz_inspect.py  _exe_de()
vector      test_backends004.py  seccion 6  (argv[0] == 'rz-bin')
mutacion    "el adapter usa el ejecutable equivocado"   DETECTADA
limitacion  el vector comprueba el argv Y que la salida sea un dict con 'info';
            comprobar solo el rc habria pasado con el banner
```