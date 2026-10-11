# fixture `rxre_min`

Artefacto de entrada para `binary.inspect`. **4728 bytes, ELF64 x86-64,
estatico, no stripped.**

No es codigo de driver. No abre ni escribe la RX550 ni la iGPU. Solo contiene
la constante `0xD0000000` como **dato**, para que un backend tenga algo que
encontrar.

## Por que existe

Un mock de backend (`{"functions": []}`) verifica el normalizador, no el
productor. Este fixture pasa por el camino completo y verificable:

```
rxre_min.c
  -> gcc -Os -nostdlib -ffreestanding
  -> ld.bfd (script minimo, sin libc ni crt)
  -> rxre_min.elf        sha256 a183f60d...
  -> rz-bin -I -j        producer real
  -> json.loads
  -> _normalizar()
  -> result_id + provenance
```

## Reproducibilidad

```bash
gcc -Os -fno-pie -no-pie -nostdlib -ffreestanding -c rxre_min.c -o rxre_min.o
gcc -Os -fno-pie -no-pie -nostdlib -ffreestanding \
    -Wl,--build-id=none -Wl,-T,rxre_min.ld rxre_min.o -o rxre_min.elf
sha256sum rxre_min.elf    # debe ser a183f60d67ba1787bd217db2a7cd6609a...
```

**MEDIDO:** dos compilaciones consecutivas con un `touch` entre medias dan
byte-identicos. El hash no depende de la hora ni del path.

Si el hash no coincide, el artefacto esta comprometido y el test que lo use
falla. No se "reconstruye" el manifiesto para que cuadre.

## Ground truth

Las cuatro funciones estan en el fuente, asi que el numero de funciones que
encuentre un backend es un dato comprobable y no una cifra que se acepta:

| simbolo | vaddr | patron |
|---|---|---|
| `mmio` | `0x400000` | devuelve un puntero |
| `escribir_registro` | `0x400007` | store directo |
| `leer_registro` | `0x40000f` | load directo |
| `campo` | `0x400017` | load + ALU + store (RMW) |

La distincion util es `escribir_registro` frente a `campo`. Es exactamente la
pregunta que el proyecto tiene abierta sobre las 24 aristas WRITES candidatas:
**cual de ellas es de hecho una escritura.** Aqui la respuesta esta en el
fuente y ningun backend puede deducirla, asi que el fixture discrimina.

## Lo que este fixture NO demuestra

Que exista un patron de acceso a registro en un binario **no** demuestra que el
hardware hace lo que el patron sugiere. Un `store` a un MMIO es un `store` a un
MMIO. La semantica la aporta la evidencia del lado del hardware, y no esta
aqui. `binary.inspect` es `RAW_BINARY`: una DECLARACION.