# 1459 — el database de `umr` cierra la última ambigüedad del IB real: `DATA_SEL` está en los bits 29–31 e `INT_SEL` en los 24–26, y hay un tercer campo que el driver nunca escribe

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST

ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt   dwords 4-7 y 28-52
ORACLE NUEVO=/usr/share/umr/database/ip/gfx_8_0_0.reg   (umr 1.0.11)
           /usr/share/umr/database/ip/gmc_8_1_0.reg
           /usr/share/umr/database/polaris12.asic

CIERRA=1440 §4, el NOT_DETERMINED de cual de las dos diferencias es DATA_SEL y
        cual es INT_SEL.  Dos candidatas, y un tercer campo que nadie habia visto.
VALIDA=1401 y 1404, con cuatro offsets GMC medidos desde la fuente del driver y
        confirmados por una fuente sin relacion
ESTADO=PROVEN, y el campo nunca escrito es NOT_DETERMINED
```

## 0 · DE DÓNDE SALE EL ORACLE

La regla `1430` §7 dice: *antes de escribir `NOT_DETERMINED`, mira donde nadie ha
mirado*. Nadie había mirado `/usr/share/umr/database/`, que existe porque `umr`
está instalado (`umr-1.0.11-2.fc44`), y que es **una descripción de ASIC
independiente de la fuente del driver**.

```
  /usr/share/umr/database/polaris12.asic        273 bytes, el mapa de familias
  /usr/share/umr/database/ip/gfx_8_0_0.reg      los registros de GFX8
  /usr/share/umr/database/ip/gmc_8_1_0.reg      los de GMC 8.1
```

Y `polaris12.asic` **confirma por fuera** dos cosas que este nodo había medido
desde el driver:

```
  gmc810  -> ip/gmc_8_1_0.reg      GFX8 es GC 8.1
  gfx800  -> ip/gfx_8_0_0.reg      y el bloque de gráficos es 8.0
  y NO existe polaris12.soc15       porque GFX8 es anterior a SOC15
```

Lo último es **lo mismo que dice `1421` §3** — que la ventana de gráficos de GFX8
no publica ningún registro de VM porque GFX8 no es una parte SOC15. **Dos fuentes
sin relación, la misma conclusión.**

## 1 · VALIDACIÓN CRUZADA DE LO QUE YA TENÍA MEDIDO

Antes de usar un oráculo nuevo hay que validarlo contra algo conocido. MEDIDO:

| registro | fuente del driver (`1401`, `1404`) | `umr` `gmc_8_1_0.reg` | |
|---|---|---|---|
| `mmVM_CONTEXT0_CNTL` | `0x504` | `0x504` | coincide |
| `mmVM_CONTEXT1_CNTL` | `0x505` | `0x505` | coincide |
| `mmVM_INVALIDATE_REQUEST` | `0x51e` | `0x51e` | coincide |
| `mmVM_INVALIDATE_RESPONSE` | `0x51f` | `0x51f` | coincide |

**Cuatro de cuatro.** El oráculo sirve, y por tanto lo que diga de los campos de
la valla se puede tomar en serio.

## 2 · LA RESPUESTA, Y ESTÁ EN `gfx_8_0_0.reg`

`1440` §4 dejó esto:

```
  valla A:  0x4000 - 0x2000 = 0x2000
  valla B:  0x2200 - 0x2000 = 0x0200
  dos asignaciones aritméticamente válidas, y nada las separa
```

MEDIDO, el registro al que escribe el driver. `gfx_v8_0.c:6174` escribe

```c
        amdgpu_ring_write(ring, (upper_32_bits(addr) & 0xffff) |
                          DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0));
```

y en `gfx_8_0_0.reg`:

```
  mmCP_EOP_DONE_DATA_CNTL 0 0xc0d6 4 0 4294967295
        CNTX_ID   0 15
        DST_SEL  16 17
        INT_SEL  24 26
        DATA_SEL 29 31
```

**`DATA_SEL` es el bit 29, e `INT_SEL` el 25.** Y las diferencias medidas eran
`0x2000` (bit 13 del nibble alto, que es bit 29 del dword) y `0x0200` (bit 25).

> **La asignación que `1440` no pudo decidir está decided, y la guess que hice
> era la correcta:** `0x2000` es `DATA_SEL`, `0x0200` es `INT_SEL`. **Y no lo
> decidí por el nombre del campo**, que es exactamente el error que
> `1421` §5 cometió — lo decidí porque el oráculo dice en qué bit está cada uno.

## 3 · LOS CUATRO PAQUETES, DECODIFICADOS

Con los bits del oráculo, los cuatro `EVENT_WRITE_EOP` del bloque 0:

```
  paquete     dword     CNTX_ID  DST_SEL  INT_SEL  DATA_SEL
  A dummy   0x200000ff   0x00ff     0       0        1
  A real    0x400000ff   0x00ff     0       0        2
  B dummy   0x200000ff   0x00ff     0       0        1
  B real    0x220000ff   0x00ff     0       2        1
```

Y el driver (`gfx_v8_0.c:6159` el dummy con valores fijos, `6174` el real):

```
  DATA_SEL(1) -> campo 1        DATA_SEL(2) -> campo 2
  INT_SEL(0)  -> campo 0        INT_SEL(2) -> campo 2
```

**Los cuatro casan exactamente.** Y de ahí, sin ambigüedad:

| valla | `DATA_SEL` | `INT_SEL` | se traduce en |
|---|---|---|---|
| **A** | 1 → **2** | 0 → 0 | `write64bit = 1`, `int_sel = 0` |
| **B** | 1 → 1 | 0 → **2** | `write64bit = 0`, `int_sel = 1` |

> **Es exactamente lo que `1440` §3 afirmaba, y ahora es `PROVEN` en vez de
> inferido:** una valla escribe **64 bits sin interrupción**, la otra **32 bits
> con interrupción**. La correspondencia con `write64bit` e `int_sel` es directa
> porque el dummy fijo del driver **es el cero de los dos campos**, y eso es lo
> que hace el cálculo unquestionable.

## 4 · EL TERCER CAMPO: `DST_SEL`, QUE EL DRIVER NUNCA ESCRIBE

El oráculo muestra **tres** campos, y el driver solo pone dos:

```
  mmCP_EOP_DONE_DATA_CNTL
        CNTX_ID   0 15      el driver pone la direccion, bits 0-15
        DST_SEL  16 17      <-- NUNCA LO PONE
        INT_SEL  24 26      lo pone
        DATA_SEL 29 31      lo pone
```

Y MEDIDO: `DST_SEL = 0` en los cuatro paquetes, o sea **en el IB real**.

**Eso es un campo muerto en esta ruta.** No es un error del driver — es que el
camino del anillo de gráficos no lo necesita. Pero es un dato que un driver
propio tiene que saber: **si escribe algo de la valla y quiere el mismo
comportamiento, `DST_SEL` se queda en 0.**

*Y por qué existe el campo es `NOT_DETERMINED`:* en el database de la familia
`gfx_v8_0_0.reg` está el mismo `mmCP_EOP_DONE_DATA_CNTL` para las rutas que sí
lo usan, y la semántica del campo no la publica este fichero.

## 5 · POR QUÉ EL ORACLE ES LA HERRAMIENTA QUE FALTABA

Porque es **lo contrario** a todo lo que el corpus podía dar:

```
  el corpus del driver   dice COMO se escribe, nunca que bit es cada cosa
                         porque los macros que lo dicen estan en si.h, que en
                         este corpus es un stub de 2 defines (1421 §6)
  el database de umr     dice QUE BIT es cada cosa, y no dice nada de como se
                         escribe nunca
```

Los dos son necesarios y no se sustituyen. Y el hecho de que el corpus no pueda
dar los bits **ya lo sabía este nodo**: `1440` §4 terminó con «el discriminante
es una línea de `si.h` completo», y `si.h` completo no está aquí.

**Pero el oráculo está en la máquina.** Y con esto hay una vía para las
preguntas que siguen abiertas, sin hardware:

| pregunta abierta | qué la respondería |
|---|---|
| ¿qué hace el campo `DST_SEL`? | otro `.reg` de otra generación, o un `.asic` con más detalle |
| los campos de `WAIT_REG_MEM_FUNCTION` | `gfx_8_0_0.reg` o el `.reg` del bloque que lo declara |
| `mmVM_INVALIDATE_REQUEST`: ¿`DOMAIN_INVALIDATED` es W1C? | el sh_mask de umr, si existe |
| el valor de `PAGE_TABLE_BLOCK_SIZE` tras reset | **esto sí necesita hardware** |

**La primera fila es la que importa: `1411` §3 fijó el idioma de `WAIT_REG_MEM`
leyendo los otros dos usos del driver, y el oráculo puede decir los bits
directamente.** Eso convierte una inferencia en una medida, y sin GPU.

## 6 · LO QUE NO SE AFIRMA

- **No se dice que el campo `DATA_SEL` sea `(x) << 29` exactamente.** Se dice que
  el campo **está en los bits 29–31** y que los valores observados 1 y 2
  corresponden a los argumentos 1 y 2 del driver. La fórmula exacta del macro es
  `NOT_DETERMINED` sin el `.h` del driver, porque la codificación del argumento
  podria ser directa o con un desplazamiento.
- **No se dice qué hace `DST_SEL`.** Se dice que existe, que el driver no lo
  escribe, y que vale 0 en el IB real.
- **No se generaliza a otras generaciones.** El registro `mmCP_EOP_DONE_DATA_CNTL`
  existe en la familia, pero los bits pueden variar, y no se ha comprobado en
  `gfx_9_*` ni en `gfx_10_*`.

## 7 · ESTADO

```
  ORACLE NUEVO
     /usr/share/umr/database/ip/{gfx_8_0_0,gmc_8_1_0}.reg
     de umr 1.0.11, instalado en la maquina, legible sin privilegios
     validado: 4 de 4 offsets GMC coinciden con los del driver

  polaris12.asic
     gmc810  gfx800  oss300  bif510  smu713  dce1120
     NO hay polaris12.soc15 -> GFX8 anterior a SOC15
     confirma 1421 §3 por una segunda fuente

  CIERRA 1440 §4
     DATA_SEL  bits 29-31, observado 1 en el dummy y 2 en la valla A
     INT_SEL   bits 24-26, observado 0 en el dummy y 2 en la valla B
     valla A   write64bit=1  int_sel=0     64 bit, sin interrupcion
     valla B   write64bit=0  int_sel=1     32 bit, con interrupcion
     4 de 4 paquetes casan exactamente

  NUEVO DATO
     mmCP_EOP_DONE_DATA_CNTL tiene TERCER campo DST_SEL en 16-17
     el driver no lo escribe, y vale 0 en el IB real
     su semantica es NOT_DETERMINED

  lo que el oráculo NO puede, y es lo que queda para el hardware
     el valor de reset de un registro
     si un campo es W1C
     si la mascara de un poll con mask=0 la tolera el silicio
     la subagente 1452 encontró el mismo defecto de mask=0 en el motor SDMA,
     asi que el patron aparece en AMBOS motores: eso es una pista de silicio, no
     de codigo, y no se resuelve leyendo ningun fichero

  1452 (subagente, SDMA) llega a la misma conclusion por otra via
     el patron "poll con mask=0 que no espera" aparece en PM4 y en SDMA
     y la causa, si la hay, es del silicio: 1459 no lo puede cerrar

  la tabla de 1440 queda completa
     la cuenta del COND_EXEC   0x2b = 43, y es el parche (1442)
     los dos pares de vallas    A y B, con su semantica ahora conocida (este)
     el campo sin nombre       mmHDP_DEBUG0 = 0xbcc (1450)
     el relleno                0xffff1000 = PACKET3(NOP, 0x3FFF) (1441)
     el switch buffer          2 dwords (1441)
     y el IB no tiene ningun campo sin decodificar

  NOTA DE ALCANCE
     el oráculo no sustituye al hardware: el valor de reset de un registro, o el
     estado real de la GPU, solo se median en la maquina

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
```