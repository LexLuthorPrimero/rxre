# 1572 · El data-flow de rizin y radare2 no puede cerrar la frontera WRITES: su conjunto de escrituras sale vacío para un store probable

```
CLASSIFICATION=NEGATIVE_RESULT · TRACK=RUNTIME
HARDWARE_SCOPE=NINGUNO (analisis de binario, no de hardware)
WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS=0
GPU INTACTA · fixture propio, 4728 bytes, sha256 a183f60d…
CIERRA=la clasificación de binary.dataflow en ambos backends medidos
ABRE=cual de las 24 aristas WRITES candidatas es una escritura de hardware real
```

## Qué demuestra

Ambos backends medidos producen un conjunto de lectura/escritura JSON, y en los
dos **el conjunto de escrituras sale vacío para una función que escribe**:

```json
{"reads":[{"name":"arg1","addrs":[4194304]}],
 "writes":[{"name":"arg1","addrs":[]}]}
```

La función es `campo` del fixture `rxre_min.elf`, y **escribe**. Tres producers
independientes lo confirman:

```text
objdump   400024: 67 89 97 00 00 00 d0   mov %edx,-0x30000000(%edi)
rizin ESIL 0x400024   edx,0x30000000,edi,-,=[4]      <- la coma final ES store
```

> el producer tiene producer, formato y `rc=0`, y aun así su afirmación sobre
> escrituras es falsa

## Por qué importa aquí y no es un detalle de herramienta

El proyecto tiene **24 aristas WRITES** marcadas como `observed`, todas
**candidatas por patrón de texto**, ninguna escritura de hardware demostrada.
La pregunta abierta es exactamente *cuál de ellas escribe*.

Un data-flow que devuelve cero escrituras donde hay un store demostrable, usado
para cerrar esa frontera, produciría `PROVEN_ABSENT`. Eso es la conversión
`empty → absent` que este proyecto cuenta desde el principio, y aquívestigaría
en el sitio donde más caro sale: sobre hardware real.

```
binary.dataflow NO puede cerrar la frontera WRITES
```

## La corrección de B5, que también es el hallazgo

Antes de esta medición, `binary.dataflow` figuraba como `PARTIAL` en rizin con
esta razón:

> `pdj` es desensamblado, no dataflow

**Esa razón era falsa.** `pdj` produce desensamblado y no se estaba usando como
data-flow; atribuirle un límite de formato inventaba un defecto en un producer
que no era el. El producer real es `afvxj`.

| | rizin 0.7.4 | radare2 5.9.8 |
|---|---|---|
| verbo | `afvxj` | `afvxj` |
| formato | JSON **mal formado**: `{"reads":[…],[],…}` | JSON **válido** |
| estado correcto | `PARTIAL` (formato) | `AVAILABLE` (formato) |
| conjunto de escrituras | vacío para un store | vacío para un store |

La etiqueta `PARTIAL` de rizin resultó correcta, pero **por otro motivo**. Una
razón correcta importa tanto como una etiqueta correcta: son cosas distintas y
se pueden equivocar por separado.

## El otro `empty` falso de esta iteración

```text
rizin -qc -e scr.color=0 'cmd'    ->  VACÍO, sin error
rizin -q  -e scr.color=0 -c 'cmd' ->  JSON OK
```

`-qc` consume el argumento siguiente como comando y se come el `-e`. Es la
**misma clase** que el `aa` frente a `aaa` que ya se corrigió una vez: un
`empty` por invocación incorrecta que se lee como una afirmación sobre la
herramienta.

## Reproducir

```bash
cd ~/Escritorio/RX550-INVESTIGACION
rz-bin -I -j tools/rxre/fixtures/bin/rxre_min.elf >/dev/null && \
rizin -q -N -e scr.color=0 -c 'aaa; s campo; afvxj' tools/rxre/fixtures/bin/rxre_min.elf
objdump -d --start-address=0x400017 tools/rxre/fixtures/bin/rxre_min.elf
```

## Provenance

```text
artefacto   tools/rxre/fixtures/bin/rxre_min.elf
            sha256 a183f60d67ba1787bd217db2a7cd6609a214acde1f7e9c4a2403e3d40fdb700c
producers   rizin 0.7.4 (afvxj, pdj) · radare2 5.9.8 (afvxj) · objdump · readelf
transform   desensamblado -> ESIL -> store · contraste entre 4 producers
registro    tools/rxre/backends/registry.py  (capacidades + notas + retraccion)
vector      tools/rxre/tests/test_dispatch004.py  seccion B5
limitacion  no se integro binary.dataflow como adaptador: no es seguro para WRITES
```