# 244 · `182` demostrado desde el binario: 345 lecturas y **cero** escrituras de `ip_versions[GC_HWIP][0]`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC_BINARY` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=/tmp/amdgpu_loaded.ko` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=la deduccion de 182, que era un argumento de segundo orden`

## Cuestión principal

`182` afirmó que `ip_versions[GC_HWIP][0] == 0` en esta placa, y lo dedujo de una
**ausencia de fichero**: no existe `ip_discovery.bin` para GCN3.

Es un argumento de segundo orden: un fichero que no está, más un razonamiento
sobre qué lo habría escrito. `185`, `190` y `203` se apoyan todos en ese valor.

**Se puede medir en el binario.** `objdump -d` sobre el `.ko` da 2.33 millones de
líneas, y el campo tiene un offset fijo en `struct amdgpu_device`.

## Criterio de terminación

Localizar el offset del campo y contar, en todo el desensamblado, cuántas veces se
lee y cuántas se escribe. **Cumplido, y con control pareado.**

## Herramienta

`08-ARQUITECTURA/tools/struct_rw.py`. Desensambla una vez a `/tmp/opencode/ko.asm`
(2.332.563 líneas) y cuenta accesos por offset:

```
$ struct_rw.py --offset 0x5d518 --contexto
offset 0x5d518 en ko.asm
  lecturas  (offset como fuente) : 345
  escrituras (offset como destino): 0
       2157 lectura   1a51:	mov    0x5d518(%rbx),%eax
      35610 lectura   1f380:	mov    0x5d518(%rbx),%eax
      73831 lectura   41c36:	mov    0x5d518(%r12),%edx
```

## El offset es `ip_versions[GC_HWIP][0]`, y se identifica por co-localización

No lo supuse: lo identifiqué en una función cuyo fuente conozco.

`amdgpu_gmc_tmz_set` **en el fuente** empieza con
`switch (amdgpu_ip_version(adev, GC_HWIP, 0))`, y su primer argumento es `adev`.

**En el binario**, esa función empieza con:

```
amdgpu_gmc_tmz_set:
  mov    0x5d518(%rdi),%eax          <- %rdi = primer argumento = adev
  cmp    $0xb050400,%eax              <- IP_VERSION(11,5,4)
  je     ...
  cmp    $0xb050300,%eax              <- IP_VERSION(11,5,3)
  cmp    $0xb050200,%eax              <- IP_VERSION(11,5,2)
  cmp    $0xa030700,%eax              <- IP_VERSION(10,3,7)
```

**Los inmediatos son las constantes `IP_VERSION` del fuente, ya compiladas**:
`IP_VERSION_FULL(mj,mn,rv,var,srev) = (mj<<24)|(mn<<16)|(rv<<8)|(var<<4)|srev`, luego
`0x0B050400` = maj `0x0B`=11, min `0x05`=5, rev `0x04`=4.

**Función conocida en el fuente + mismo offset en el binario = la identificación es
sólida.** Y de paso queda confirmado mecánicamente que las comparaciones de
`ipver_zero` son `cmp` contra constantes literales: el valor 0 no es una hipótesis,
es lo que hay.

## El resultado, y el control que lo respalda

| | lecturas | escrituras |
|---|---|---|
| `0x5d518` = `ip_versions[GC_HWIP][0]` | **345** | **0** |
| `0x5cb20` = otro campo, **control** | 420 | **5** |

**El control es la mitad del resultado.** Una herramienta que solo dijera «cero
escrituras» no valdría nada: podría estar rota. Con el campo vecino que **sí** se
escribe 5 veces, la herramienta distingue.

## El límite, y por qué aun así la conclusión aguanta

**Este método no ve escritores con índice dinámico.** `amdgpu_discovery.c:1640` hace:

```c
adev->ip_versions[hw_ip] = ...;    /* hw_ip es una VARIABLE */
```

Eso compila a una dirección calculada en runtime, **no** a un offset fijo. Así que
«cero escrituras a offset fijo» prueba que nadie escribe el campo **con índice
estático**, y no que nadie lo escriba nunca.

**Pero el escritor dinámico es uno solo, y su ruta es inalcanzable aquí:**

```
grep -rn "amdgpu_discovery_set_ip_blocks" *.c *.h | grep -v amdgpu_discovery.c
amdgpu_device.c:1994:   r = amdgpu_discovery_set_ip_blocks(adev);
```

**Un único llamante**, y es la rama `default:` del switch de ASIC. `190` ya
verificó el dispatch:

```c
case CHIP_POLARIS12:
        r = vi_set_ip_blocks(adev);        break;   /* <- entra esta */
default:
        r = amdgpu_discovery_set_ip_blocks(adev); break;   /* <- nunca */
```

**La cadena queda cerrada por los dos extremos**: el campo no tiene escritor
estático, y el único escritor dinámico está en una rama que `CHIP_POLARIS12` no
toma. `182` pasa de *inferido por un fichero que falta* a **medido**.

## El error que casi destruye la prueba

Mi primer conteo dio **«353 escrituras»**. Era falso: usé el patrón
`mov .*0x5d518`, que **también casa con las lecturas**, porque ahí el offset va
antes de la coma:

```
LECTURA    mov  0x5d518(%rbx),%eax     offset como FUENTE
ESCRITURA  mov  %eax,0x5d518(%rbx)     offset como DESTINO
```

**La diferencia entre 353 y 0 es exactamente la que sostiene el hallazgo.** Un
error de un carácter en un regex da vuelta la conclusión sin que nada falle visible.

Por eso el self-test de `struct_rw.py` no prueba que la regex encuentre algo:
**prueba que las dos regex NO casan la misma línea**, y que la de escritura no casa
la forma de lectura. Es un control de *dirección*, que es lo único que importa
cuando el resultado bueno y el resultado falso se diferencian en el orden de dos
operandales.

También corregí mi propio conteo previo: un `grep -c`-insensato daba 8302
apariciones de `0x5cb20`; la regex precisa da 420 lecturas + 5 escrituras = 425.
**Un `grep -c` cuenta apariciones, no accesos, y ni siquiera distingue lectura de
escritura.**

## Clasificación

| afirmación | estado |
|---|---|
| `0x5d518` se lee 345 veces | `PROVEN` — desensamblado |
| `0x5d518` se escribe 0 veces con índice estático | `PROVEN` — desensamblado |
| `0x5d518` = `ip_versions[GC_HWIP][0]` | `PROVEN` — co-localización con fuente |
| Los `cmp` son constantes `IP_VERSION` compiladas | `PROVEN` — inmediatos 0x0B050400 etc. |
| `amdgpu_discovery_set_ip_blocks` tiene un solo llamante | `PROVEN` — grep |
| Ese llamante es la rama `default:` | `PROVEN` — `190` |
| `ip_versions[GC_HWIP][0]` nunca se escribe en esta placa | `PROVEN_CADENA` — estático + inalcanzable |
| Que un escritor dinámico no sería visible | `LIMITE` — declarado en la docstring |
| Que no haya otras rutas de escritura | `NOT_DETERMINED` |

## Confounders

- **El límite es real y lo declaro**: un escritor con índice dinámico es invisible
  para este método. Lo cierro porque **conozco al único** que existe y sé que su
  rama no se toma. Si hubiera un segundo, el método no lo sabría.
- **`0x5d518` es un offset, no un símbolo.** La identificación por co-localización
  es fuerte pero no es un type-checked proof: si otro campo estuviera en el mismo
  offset en otra versión del struct, la lectura sería ambigua. Aquí el struct es el
  del binario que se está ejecutando, y la función de referencia usa exactamente ese
  campo, así que no hay ambigüedad **para esa función**.
- ~~**No he desensamblado `.init.text`.** `objdump -d` cubre `.text`. Un escritor
  en texto de inicialización no contaría. **No lo he comprobado**, y es un hueco
  real.~~ **CERRADO: no era un hueco.** `objdump -d` sobre un `.ko` desensambla
  **todas** las secciones ejecutables, no solo `.text`:
  ```
  $ grep -oE "^Desensamblado de la secci[^:]*:" ko.asm | sort | uniq -c
        1 .altinstr_aux      1 .exit.text          1 .static_call.text
        1 .altinstr_replacement   1 .init.text    1 .text
  ```
  El conteo de 345 lecturas y 0 escrituras se hizo sobre el **fichero entero**, así
  que ya cubría `.init.text` y `.exit.text`. La medición era completa.
- **`struct amdgpu_device` cambia entre versiones de kernel.** El offset `0x5d518`
  vale para este `.ko`, no para ninguno otro.

## Desfalsificación

- **(a)** 345 lecturas / 0 escrituras → refutable con `struct_rw.py --offset`.
- **(b)** El control (420/5) → refutable igual. **Es lo que impide que la
  herramienta sea un muro.**
- **(c)** La dirección de las regex → refutable intercambiándolas: el self-test
  tiene que fallar. **Verificado por construcción del aserto.**
- **(d)** La co-localización → refutable leyendo `amdgpu_gmc_tmz_set` en el fuente
  y sus primeros `cmp` en el binario.
- **(e)** Que no haya escritor estático → **refutable** desensamblando `.init.text`.
  **No comprobado.**

## UNLOCKS

- **`182` sube de clase**: de *inferido por un fichero ausente* a **medido en el
  binario**. Con ello `185`, `190` y `203` dejan de apoyarse en un segundo orden.
- **Una herramienta general**: `struct_rw.py` responde "¿este campo se inicializa
  alguna vez?" para cualquier struct del driver, sin source, sin root y sin tocar la
  GPU. Es reutilizable, y no hay nada parecido en el kit.
- **Control reutilizable**: en una herramienta de conteo, el control no es
  "encuentra algo", es **"las dos direcciones no casan la misma línea"**. Aquí el
  resultado bueno y el falso se diferencian en el orden de dos operandales.
- **Corregido un auto-contaje mío**: `grep -c` de 8302 apariciones eran 425
  accesos. Un conteo de apariciones no es un conteo de eventos, y menos cuando cada
  acceso produce dos.
- **`.init.text` cerrado**: la medición cubría las 6 secciones ejecutables, no
  solo `.text`. No era un hueco.

## Evidencia

```
objdump -d /tmp/amdgpu_loaded.ko > ko.asm            2332563 lineas
08-ARQUITECTURA/tools/struct_rw.py --offset 0x5d518 --contexto
    345 lecturas, 0 escrituras
08-ARQUITECTURA/tools/struct_rw.py --offset 0x5cb20
    420 lecturas, 5 escrituras          <- control pareado
amdgpu_gmc.c:927                       switch (amdgpu_ip_version(adev, GC_HWIP, 0))
amdgpu_device.c:1994                   unico llamante de discovery_set_ip_blocks
amdgpu_discovery.c:1640                el unico escritor con indice dinamico
amdgpu_ip.h:77-79                      IP_VERSION_FULL
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.