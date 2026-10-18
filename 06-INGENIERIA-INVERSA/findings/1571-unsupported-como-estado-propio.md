# 1571 · `unsupported` como estado propio: un ELF con `e_machine` desconocido sale `rc=0` con contenido y sin arquitectura

```
CLASSIFICATION=FACT · TRACK=RUNTIME
HARDWARE_SCOPE=NINGUNO (binario de fichero) · WORK_CLASS=READ_ONLY
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU INTACTA
CIERRA=la distincion entre "no hay nada que mirar" y "nadie ha identificado esto"
ABRE=que otros producers tendran la misma forma de falsehood
```

## Qué demuestra

Un ELF con `e_machine` desconocido (`0xFFFF`) **pasa** el precheck de firma,
el backend responde **`rc=0`** y devuelve `info` **con contenido**:

```text
rizin    arch=None                     machine='<unknown>: 0xffff'
radare2  arch='Unknown or unsupported arch'
/bin/ls  arch='x86'
```

Reducido a la forma del contrato (`rc` + contenido + parseable) esto sería `ok`
con `arch: null`. Y una IA leería `arquitectura: null` como si el binario **no
tuviera arquitectura**.

No la tiene. Es que **nadie la ha identificado**.

```
no saber qué arquitectura es  ≠  no haber nada que mirar
```

## Por qué obliga a un estado más

RXRE-001 tenía cuatro estados: `ok`, `empty`, `blocked`, `error`. Con ellos,
este caso sólo puede reportingarse como `ok` incompleto o como `error`, y los
dos mienten:

- `ok` afirma que se sabe la arquitectura. No se sabe.
- `error` afirma que el backend falló. No falló.

La sexta forma es `unsupported` con `rc=4`, y **lleva el motivo y el verbo que
faltó**, para que una IA pueda intentar por otro camino en vez de rendirse.

```
unsupported  →  empty   PROHIBIDO
blocked      →  empty   PROHIBIDO
error        →  empty   PROHIBIDO
```

## Y no se deduce del texto

`machine` dice `<unknown>: 0xffff`. Convertirlo en un nombre de arquitectura
sería inventar un dato que **ningún producer emitió**. La arquitectura se pide
al producer; si no la da, queda `unsupported`.

## Reproducir

```bash
cd /tmp && cp /bin/ls elf_desc.elf && python3 -c "
import struct
b=bytearray(open('elf_desc.elf','rb').read())
struct.pack_into('<H', b, 0x12, 0xFFFF)
open('elf_desc.elf','wb').write(bytes(b))"
rz-bin -I -j elf_desc.elf | python3 -m json.tool | head -5
```

## Provenance

```text
artefacto   /bin/ls con e_machine parcheado a 0xFFFF
producers   rz-bin 0.7.4 · radare2 5.9.8  (corroboracion independiente)
transform   ELF valido -> e_machine desconocido -> info sin clave arch
adapter     tools/rxre/backends/adapters/rz_inspect.py  rama `sin_arch`
mutaciones  "una arquitectura sin identificar se declara soportada"  DETECTADA
            "la arquitectura se deduce del texto machine"            DETECTADA
limitacion  no se integro un productor de "formatos soportados": el backend
            no lo expone y declararlo seria inventar
```