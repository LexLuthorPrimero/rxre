# 1430 — el comentario del driver dice literalmente `/* enable context1-15 */`: `mmVM_CONTEXT1_CNTL` cubre los contextos 1 a 15, y eso cierra `1404` y `1128` sin hardware

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
TARGET=CHIP_POLARIS12

AFECTADO=gmc_v8_0.c:913-929      el bloque, con su comentario
         gmc_8_1_sh_mask.h        PAGE_TABLE_BLOCK_SIZE__MASK 0xf000000
                                 PAGE_TABLE_BLOCK_SIZE__SHIFT 0x18

CIERRA=1404 §5 (los contextos 2-15 no tienen escritor alcanzable)
        1128 (mmVM_CONTEXT0_CNTL.PAGE_TABLE_BLOCK_SIZE, que mandaba a runtime)
        1420 §3 (el despacho observado en VMID 7 deja de ser un misterio)

CORRIGE=1421 §5, que dijo que H3 «se cae».  H3 es la buena: la confirma un
        comentario del propio driver, que yo no habia leido.
        Y corrige 1404 §3, que listaba dos campos escritos y son nueve.
ESTADO=PROVEN sobre el codigo · el valor de reset de CONTEXT0 sigue sin medirse
```

## 0 · EL ERROR, EN ORDEN

Esta cadena de cuatro hallazgos viene acumulando correcciones y yo he sido el
que más se ha equivocado. El orden importa, así que va primero:

| hallazgo | lo que afirmé | lo que era |
|---|---|---|
| `1404` §3 | «solo se escriben `ENABLE_CONTEXT` y `PAGE_TABLE_DEPTH`» | **nueve campos**, y uno es `PAGE_TABLE_BLOCK_SIZE` |
| `1404` §5 | quien configura los contextos 2–15: `NOT_DETERMINED`, tres hipótesis | **el driver lo dice en un comentario** |
| `1421` §5 | «H3 se cae: el sh_mask no publica campo de rango» | **H3 es la buena**, y mi razón era inválida |
| `1128` | `PAGE_TABLE_BLOCK_SIZE` necesita runtime | **posición y escritor son estáticos** |

> **Los cuatro estaban mal en la misma dirección: afirmar que algo no se puede
> leer, sin haber leído el fichero entero.** `1404` §3 leyó las líneas 887-891 y
> 917-919, que es donde yo miré, y no las 913-930, que es donde estaba el resto.
> **`1129`, `1144`, `1153`, `1412` y `1420` ya me lo habían cobrado cinco veces y
> aquí lo hice una sexta.**

## 1 · EL BLOQUE, ENTERO, CON SU COMENTARIO

`gmc_v8_0.c:913-929`, literal:

```c
	/* enable context1-15 */
	WREG32(mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR,
	       (u32)(adev->dummy_page_addr >> 12));
	WREG32(mmVM_CONTEXT1_CNTL2, 4);
	tmp = RREG32(mmVM_CONTEXT1_CNTL);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, ENABLE_CONTEXT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_DEPTH, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, DUMMY_PAGE_FAULT_ENABLE_DEFAULT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PDE0_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, VALID_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, READ_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, WRITE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
	tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_BLOCK_SIZE,
			    adev->vm_manager.block_size - 9);
	WREG32(mmVM_CONTEXT1_CNTL, tmp);
```

**`/* enable context1-15 */`.**

Ocho registros y un solo `WREG32` de `CNTIL`. Y el comentario no es una
sospecha: es la intención del autor, escrita a una línea del código.

## 2 · POR QUÉ MI ARGUMENTO CONTRA H3 ERA INVÁLIDO

`1421` §5 escribió que H3 —«`mmVM_CONTEXT1_CNTL` cubre un rango»— se caía
porque `gmc_8_1_sh_mask.h` no publica ningún campo de rango.

**La premisa era correcta y la conclusión estaba mal.**

MEDIDO, lo que sí publica el sh_mask para `mmVM_CONTEXT1_CNTL`: **22 campos**
(44 entradas contando `_MASK` y `_SHIFT`), y los únicos con `RANGE` en el nombre
son:

```
  VM_CONTEXT1_CNTL__RANGE_PROTECTION_FAULT_ENABLE_DEFAULT
  VM_CONTEXT1_CNTL__RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT
```

Esos son **faults de rango de la tabla de páginas**, no un rango de VMID. Correcto.

**Pero de ahí no sale H3.** Sale lo contrario:

> **Un registro cuyo comentario dice «habilita los contextos 1 a 15» no necesita
> un campo de rango para hacerlo: necesita un bit, y el bit es `ENABLE_CONTEXT`.**
> El rango está en el **sentido del bit**, no en el layout del registro. Los dos
> son cosas distintas y yo las confundí.

Es la misma clase de error que `1412` §3 con los bits del paquete: **un campo con
nombre no es el campo que creo que es.**

## 3 · LAS TRES HIPÓTESIS DE `1404`, CON SU ESTADO REAL

`1404` §5 dejó tres. Con todo lo medido:

| | hipótesis | estado |
|---|---|---|
| **H1** | el reset deja `ENABLE_CONTEXT = 1` en 2–15 | **DESCARTADA**: si fuera así, no haría falta escribir el registro, y el driver lo escribe |
| **H2** | otro escritor en el árbol configura 2–15 | **DESCARTADA**: `1404` §3 ya lo había medido — no hay segundo escritor, y `1421` §3 mostró que los símbolos no existen para esta ASIC |
| **H3** | `mmVM_CONTEXT1_CNTL` cubre 1–15 | **CONFIRMADA** por el comentario, `gmc_v8_0.c:913` |

**Y hay una cuarta fuente que la corrobora sin ser el comentario:** `1420`
midió en el IB real un despacho sobre el **VMID 7**. Si `CONTEXT1_CNTIL` solo
habilitara el contexto 1, ese despacho no habría podido convertirse en trabajo.

> **La fuente independiente es la que pesa:** el comentario dice que
> el driver pretende 1-15; el anillo demuestra que el 7 funciona. **Las dos juntas
> convierten H3 en `CORROBORATED`.**

## 4 · LO QUE CIERRA DE `1128`, Y QUÉ QUEDA

`1128` había dejado `mmVM_CONTEXT0_CNTL.PAGE_TABLE_BLOCK_SIZE` como pregunta de
runtime. Ahora, estáticamente:

```
  PAGE_TABLE_BLOCK_SIZE
     MASK   0xf000000        4 bits
     SHIFT  0x18 = 24        bits 24..27
     en mmVM_CONTEXT0_CNTL y en mmVM_CONTEXT1_CNTL, mismo sitio
     ocurrencias en 24 ficheros .c del arbol  30
     el UNICO de GFX8 alcanzable   gmc_v8_0.c:927
     valor que escribe          adev->vm_manager.block_size - 9
```

Y `block_size` viene de `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)` con
`fragment_size_default = 9` (`1404`), así que:

```
  PAGE_TABLE_BLOCK_SIZE que escribe GFX8  =  block_size - 9
  y ese -9 es el MISMO 9 que `1126` ya había medido
  y que la rama muerta de gfxhub_v1_0.c:262 hacia block_size
```

**Cierra (`PROVEN`):** posición del campo, autor único en GFX8, y fórmula del valor.

**Queda `NOT_DETERMINED`, y es una sola cosa:** el valor de reset de ese campo en
`mmVM_CONTEXT0_CNTL`. El driver **no lo escribe para el contexto 0** — solo para
el 1 — así que el contexto del GART depende de lo que haga el reset. **Una
lectura MMIO de `mmVM_CONTEXT0_CNTL` lo cierra**, y es la misma lectura que
`1404` y `1421` necesitan para las otras preguntas. **Un viaje, cuatro
respuestas.**

## 5 · POR QUÉ ESTO ES MÁS ÚTIL QUE LA CUADRILLA DE HALLAZGOS QUE CIERRA

Porque `1404` §6 tenía una lista de «trampas» para un driver propio, y una de
ellas era exactamente esto:

```
  lo que 1404 temia:  "no hay escritor para VMID 2-15"
  lo que es:          "un solo escritor los cubre todos, y lo dice arriba"
```

**Una trampa que se ve en el propio `grep` del campo es una trampa que un driver
propio no copia por error**, porque para verla hay que abrir el fichero. Y una
que hace falta hardware para detectarla es una que se copia.

El orden de valor es el inverso del que parece:

| lo que cuesta verlo | lo que cuesta consecuencias |
|---|---|
| leer el fichero entero | bajo — se ve al escribir el driver |
| hacer un experimento | alto — se ve en producción |

> **El proyecto lleva mil hallazgos midiendo lo segundo y muchas veces no ha
> medido lo primero.** `1404` fue a la sh_mask a buscar un campo de rango en vez
> de leer las siete líneas de debajo del comentario que lo decía todo.

## 6 · LO QUE NO SE AFIRMA

- **No se dice que `ENABLE_CONTEXT = 1` en `CONTEXT1_CNTIL` cubra 1–15 en el
  hardware.** Se dice que el driver **lo pretende**, que es observable en el
  código, y que el despacho observado en VMID 7 **corrobora** que para el 7
  funciona. Que funcione para los 15 es `CORROBORATED`, no `PROVEN`.
- **No se dice nada del valor de reset de `PAGE_TABLE_BLOCK_SIZE` para el
  contexto 0.** Sigue sin medirse, y es un viaje de una lectura.
- **No se corrige el resto de `1404`.** Lo demás de ese hallazgo se sostiene: el
  array de bases partido, `max_level = 1`, la profundidad 0 frente a 1.
- **No se toca el corpus.**

## 7 · EL MANTEL QUE HAY QUE PONERLE A TODO ESTO

Cinco hallazgos consecutivos en la misma línea de investigación, y en cuatro de
ellos **yo affirmaba algo que el fichero ya decía a tres líneas del sitio donde
miraba**. Los cinco:

```
  1404 §3   campos escritos, leidas 4 de 18 lineas
  1404 §5   "NOT_DETERMINED", con el comentario a una linea
  1421 §5   "H3 se cae", por un campo que no era el relevante
  1412 §3   bits [23:16] en vez de [15:8]
  1420      atribucion de un IB sin comprobar el bit discriminante
```

**Y los cinco errores eran detectables porque siempre había un segundo
sitio donde mirar:**

| error | el segundo sitio |
|---|---|
| `1412` §3 | un paquete real con un campo con nombre |
| `1420` | un bit del propio dato |
| `1404` §5 | el comentario del propio driver |
| `1421` §5 | `1404` §3, que ya decía «nueve campos» |
| — | **el mismo del fichero, siempre** |

> **La regla, y es la más accionable de esta tanda:**
> **antes de escribir `NOT_DETERMINED`, abrir el fichero y leer las N líneas
> antes y las N líneas después del hallazgo, y mirar los comentarios.**
> Un `NOT_DETERMINED` es la afirmación más cara del proyecto: cuesta un
> viaje al nodo de runtime, y estos cinco han costado cero viajes y
> cero lecturas de hardware, cuando la respuesta estaba en el texto.

```
ESTADO
  mmVM_CONTEXT1_CNTL en GFX8
     habilita contextos 1-15      PROVEN   (gmc_v8_0.c:913, comentario)
     corroborado por un despacho real en VMID 7    OBSERVADO  (1420)
     escriben 9 campos, no 2      PROVEN   corrige 1404 §3
     unico escritor alcanzable    gmc_v8_0_gart_enable

  PAGE_TABLE_BLOCK_SIZE
     bits 24..27, mask 0xf000000, shift 0x18       PROVEN
     autor unico en GFX8          gmc_v8_0.c:927
     valor                        block_size - 9
     escrito solo para CONTEXT1
     valor de reset de CONTEXT0    NO MEDIDO -> 1 lectura MMIO

  1404 §5 H1, H2  DESCARTADAS   H3 CONFIRMADA
  1128            cierra la posicion y el autor; queda el reset de CONTEXT0
  1421 §5         CORREGIDO por este hallazgo, el argumento era invalido

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```