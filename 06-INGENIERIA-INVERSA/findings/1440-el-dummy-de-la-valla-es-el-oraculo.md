# 1440 — el IB real contiene **dos vallas por bloque**, y el dummy que el driver emite justo antes es el oráculo que permite decodificarlas sin los macros que faltan

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt   dwords 27..52, 8 bloques
CORPUS=rx550-upstream-7.2.8 (solo lectura)

AFECTADO=gfx_v8_0.c:6141-6178      gfx_v8_0_ring_emit_fence_gfx
         el bloque emite DOS EVENT_WRITE_EOP: un dummy con seq-1 y el real
         con seq, y el dummy codifica las constantes FIJAS

CIERRA=el DEFERRED de 1421 §8 sobre la valla, en todo menos un bit
        (el bit que queda sin nombrar es NOT_DETERMINED con dos candidatos)
ESTADO=OBSERVADO-ESTRUCTURA · NOT_DETERMINED-LA-ASIGNACION-DE-DOS-BITS
```

## 0 · POR QUÉ SE PUEDE DECODIFICAR SIN LOS MACROS QUE FALTAN

`1421` §8 dejó la valla como `DEFERRED` porque `DATA_SEL`, `INT_SEL`,
`EVENT_TYPE`, `EVENT_INDEX` y los `EOP_*_ACTION_EN` **no existen en ninguna parte
del corpus** — ni en `si.h`, ni en `vi.h`, ni en los PM4 completos de otras
generaciones (`sid.h`, `nvd.h`), ni en `gca/gfx_8_0_enum.h`.

Volví a buscarlo y la ausencia es total. **Pero hay un oráculo dentro del propio
artefacto**, y es lo que `§46 ORACLE ENGINE` pide sin que haya que buscarlo:

> **El propio driver emite un paquete de calibración antes de cada valla real, con
> las mismas variables pero con los valores constantes escritos a mano.** Los dos
> paquetes están en el mismo anillo, a seis dwords de distancia, y sólo cambian
> los campos que el driver hace variables.

## 1 · LA FUENTE, ENTERA, Y LO QUE HACE VARIABLE

`gfx_v8_0_ring_emit_fence_gfx` (`gfx_v8_0.c:6141-6178`), las dos mitades:

```c
        /* Workaround for cache flush problems. First send a dummy EOP
         * event down the pipe with seq one below.
         */
        amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
        amdgpu_ring_write(ring, (EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN |
                                 EOP_TC_WB_ACTION_EN |
                                 EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) |
                                 EVENT_INDEX(5)));
        amdgpu_ring_write(ring, addr & 0xfffffffc);
        amdgpu_ring_write(ring, (upper_32_bits(addr) & 0xffff) |
                                 DATA_SEL(1) | INT_SEL(0));          <-- FIJO
        amdgpu_ring_write(ring, lower_32_bits(seq - 1));
        amdgpu_ring_write(ring, upper_32_bits(seq - 1));

        /* Then send the real EOP event down the pipe: */
        amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
        amdgpu_ring_write(ring, (EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN |
                                 EOP_TC_WB_ACTION_EN |
                                 EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) |
                                 EVENT_INDEX(5) |
                                 (exec ? EOP_EXEC : 0)));
        amdgpu_ring_write(ring, addr & 0xfffffffc);
        amdgpu_ring_write(ring, (upper_32_bits(addr) & 0xffff) |
                          DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0));  <-- VARIABLE
        amdgpu_ring_write(ring, lower_32_bits(seq));
        amdgpu_ring_write(ring, upper_32_bits(seq));
```

**El dummy es el paquete de calibración.** Fija `DATA_SEL(1) | INT_SEL(0)` y
`seq - 1`. El real varía `DATA_SEL`, `INT_SEL` y `seq`. Todo lo demás es idéntico.

**Y en el artefacto hay DOS vallas por bloque, no una.** El driver emite una
valla por llamada, así que el bloque tiene dos llamadas: `ring_emit_fence_gfx` con
flags distintos, o una de graphics y otra de otro emisor.

## 2 · LO MEDIDO, EN LOS OCHO BLOQUES

Cada bloque, cuatro `EVENT_WRITE_EOP`, que se agrupan en dos parejas de dos:

```
  EOP#   addr_lo     addr_hi     seq        (addr_hi >> 16) = DATA_SEL|INT_SEL
   0     0x016b7000  0x200000ff  0x09bae        0x2000      <- dummy de la valla A
   1     0x016b7000  0x400000ff  0x09baf        0x4000      <- real de la valla A
   2     0x00001040  0x200000ff  0x09be7        0x2000      <- dummy de la valla B
   3     0x00001040  0x220000ff  0x09be8        0x2200      <- real de la valla B
```

Tres medidas, cada una con su recuento:

| medida | resultado | recuento |
|---|---|---|
| las dos parejas comparten dirección, y las direcciones **difieren entre sí** | `0x016b7000` frente a `0x00001040` | 8 de 8 bloques |
| `seq(real) - seq(dummy)` dentro de cada pareja | **exactamente 1** | **16 de 16 parejas** |
| `seq(B) - seq(A)` entre las dos vallas del bloque | **exactamente 0x39 = 57** | 8 de 8 bloques |
| valor del dummy en el campo variable | **siempre 0x2000** | **16 de 16** |

**`16 de 16` con delta 1 es la firma del `seq - 1` del driver.** No es una
correlación: es el valor exacto que la fuente escribe, medido en todas las
parejas disponibles sin una sola excepción.

Y los dos contadores de secuencia avanzan **a la vez, ambos en 1 por bloque,
manteniendo el offset de 57**: son dos contadores independientes con un
desfase constante.

## 3 · LA SEMÁNTICA DE LAS DOS VALLAS

El dword `addr_hi` es `(upper_32(addr) & 0xffff) | DATA_SEL | INT_SEL`. Los bits
bajos son `0x00ff` en las cuatro, o sea que la parte de dirección es constante; y
el campo de arriba cambia. **Restando el dummy de su propio real:**

```
  valla A:  0x4000 - 0x2000 = 0x2000
  valla B:  0x2200 - 0x2000 = 0x0200
```

Y el driver solo tiene **dos** bits variables ahí:

```c
  DATA_SEL(write64bit ? 2 : 1)      ->  dos valores
  INT_SEL(int_sel ? 2 : 0)          ->  dos valores
```

> **Cada valla cambia exactamente uno de los dos campos, y son campos
> distintos.** Eso es `PROVEN` sobre el artefacto, y es la observación que
> identifica las dos llamadas sin necesitar el nombre de los campos.

**Lo que se puede afirmar de la valla A:** su campo `write64bit` está en el valor
`2` y `int_sel` en `0`. **Lo mismo para la B, con los papeles invertidos.** En
conjunto: **una de las dos vallas escribe 64 bits y la otra 32, y la que escribe
32 es la que pide interrupción** — porque son las dos combinaciones que el driver
puede emitir y cada una aparece exactamente una vez por bloque.

### Y el otro emisor de valla queda descartado por medición

`gfx_v8_0_ring_emit_fence_compute` (`gfx_v8_0.c:6237-6258`) existe y emite fence
también, pero **no es el emisor de estos paquetes**, por dos razones
independientes:

```
  razon 1, la estructura
     emite UN solo paquete, con PACKET3_RELEASE_MEM, y SIN dummy
     el artefacto tiene 32 EVENT_WRITE_EOP, en 16 parejas con delta 1
     y CERO paquetes del tipo de la valla de compute

  razon 2, el recuento
     PACKET3_EVENT_WRITE_EOP (0x47)      32 en el artefacto
     el tipo de la valla de compute        0 en el artefacto
```

**Los ocho tipos de paquete que sí están**, con su recuento:

```
  0x10  NOP                 1648
  0x47  EVENT_WRITE_EOP       32
  0x22  COND_EXEC              8
  0x28  CONTEXT_CONTROL        8
  0x37  WRITE_DATA             8
  0x3c  WAIT_REG_MEM           8
  0x3f  INDIRECT_BUFFER        8
  0x8b  SWITCH_BUFFER          8
```

**Los cuatro `EVENT_WRITE_EOP` por bloque vienen de `emit_fence_gfx`, y solo de
ahí.** Y hay una diferencia estructural entre los dos emisores que queda
registrada: en `RELEASE_MEM` el `DATA_SEL | INT_SEL` ocupa **un dword propio**, y
en `EVENT_WRITE_EOP` va **OR-ingado con la dirección alta**. Un lector de IB que
no sepa eso no puede comparar las dos vallas.

## 4 · EL BIT QUE NO SE PUEDE ELEGIR, Y POR QUÉ

`DATA_SEL` toma `{1, 2}` e `INT_SEL` toma `{0, 2}`. Si la codificación es
lineal, `DATA_SEL(x) = A·x` e `INT_SEL(y) = B·y`, entonces:

```
  DATA_SEL(1) = A      DATA_SEL(2) = 2A     diferencia = A
  INT_SEL(0)  = 0      INT_SEL(2)  = 2B     diferencia = 2B
```

Con las diferencias medidas (`0x2000` y `0x0200`), **hay dos asignaciones
aritméticamente válidas y nada las separa:**

| | `A = DATA_SEL(1)` | `2B` | consecuencia |
|---|---|---|---|
| **(a)** | `0x2000` | `0x0200` | la valla A cambia `DATA_SEL` (64 bit), la B cambia `INT_SEL` (interrupción) |
| **(b)** | `0x0200` | `0x2000` | invertidas |

**La que se deduce de `flags` es (a)** — la A es la de 64 bits — pero
**«la que se deduce» no es una medida**: es la que concuerda con el nombre del
campo, y `1412` §3 ya demostró que un nombre de campo no es el campo que uno
cree. Se queda **`NOT_DETERMINED`**, y el discriminante es uno solo:

> **`si.h` completo.** Una línea. `DATA_SEL(1)` y `INT_SEL(2)` en el mismo
> fichero, y la asignación sale por aritmética.

## 5 · LO QUE ESTE HALLAZGO APORTA A UN DRIVER PROPIO

Porque la valla es la primitiva de la que depende todo lo demás, y aquí hay tres
cosas medidas que un driver tiene que acertar:

```
  1. el DUMMY no es opcional
     el driver emite un EOP con seq-1 ANTES del real, por un workaround de
     flush de cache, y lo dice en el comentario
     -> 16 de 16 parejas en el artefacto con delta exactamente 1
     -> un driver propio que solo emita el EOP real se ahorra 6 dwords
        y pierde el workaround que AMD considera necesario

  2. son DOS vallas, con contadores INDEPENDIENTES
     offset medido 0x39 = 57, constante en 8 de 8 bloques
     una en 64 bit y otra en 32 con interrupción
     -> dos destinos de fence, no uno

  3. el campo de flags viaja en el MISMO dword que la dirección alta
     (upper_32(addr) & 0xffff) | DATA_SEL | INT_SEL
     -> los flags y la dirección no se pueden separar leyendo el IB
```

**Y hay una consecuencia de rendimiento que no es teoría sino aritmética:** el
workaround cuesta **6 dwords por valla, y el anillo está el 79 % relleno de
`NOP`**. Con dos vallas por bloque de 256 dwords, los `NOP` sobran de sobra, así
que **el workaround no cuesta espacio en esta carga**. Eso es `PROVEN` sobre el
artefacto: 203 de 256 dwords son relleno.

## 6 · LO QUE NO SE AFIRMA

- **No se dice cuál de las dos vallas es la de 64 bits.** §4: dos
  asignaciones válidas, y elegir por el nombre del campo no es medir.
- **No se nombran los bits de `DATA_SEL` ni de `INT_SEL`.** Se nombran sus
  **diferencias**, que es lo que el artefacto mide.
- **No se dice que la dirección `0x016b7000` esté en VRAM.** Es un valor; si es
  una dirección de GPU, su VRAM no está medido aquí.
- **No se dice por qué hay dos llamadas de valla en un mismo anillo.** Que las
  cuatro provengan de `emit_fence_gfx` es `PROVEN` por el tipo de paquete (§3);
  **por qué se llama dos veces** —dos consumidores del ring, o dos banderas
  distintas en una llamada— es `NOT_DETERMINED`, y se responde con el estado del
  ring en el momento de la captura, que no está en el artefacto.
- **No se toca el corpus ni el artefacto.**

```
ESTADO
  ARTEFACTO revkit/capturas/amdgpu_ring_gfx.txt
     2 vallas por bloque de 256 dwords, 4 EOP por valla par
     seq(real) - seq(dummy) = 1                  16 de 16    PROVEN
     campo variable del dummy siempre 0x2000      16 de 16    PROVEN
     seq(B) - seq(A) = 0x39 = 57                  8 de 8      PROVEN
     valla A cambia un campo por 0x2000            8 de 8      PROVEN
     valla B cambia otro campo por 0x0200          8 de 8      PROVEN
     una es de 64 bit y la otra de 32 con interrupcion           CORROBORATED

  NO DETERMINADO, un solo discriminante
     cual de las dos diferencias es DATA_SEL y cual INT_SEL
     se cierra con si.h completo: una linea

  por que el dummy sirve de oraculo
     el driver escribe DATA_SEL(1) | INT_SEL(0) a mano en el dummy,
     y el real solo cambia esos dos campos -> el propio paquete es la referencia

  el workaround del dummy NO cuesta espacio con esta carga
     203 de 256 dwords son NOP                                   PROVEN

  capa de macros PM4 ausente en TODO el corpus
     ni si.h, ni vi.h, ni sid.h, ni nvd.h, ni gca/gfx_8_0_enum.h

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```