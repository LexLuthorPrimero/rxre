# 1209 — `tools/pm4_grupos.py`: el guard permanente, tres defectos de método que encontró, y **cuatro** paquetes PM3 de GFX8 determinados de una vez

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=TOOL-FACTORY + SEMANTICS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/pm4_grupos.py (nuevo,  namespace propio)
                           + correccion de METODO en 1208
CONTINUA   1207 y 1208
NUEVO      4 paquetes con layout determinado:  DMA_DATA, MAP_QUEUES,
           UNMAP_QUEUES, QUERY_STATUS.   11 grupos de dword.
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · Por qué la herramienta, y no un script de más

`1208` publicó cifras que produjo un script en `/tmp`. Esa carpeta ya se había borrado una vez
hoy por un reinicio. **Una evidencia que no se puede volver a producir no es evidencia**, es un
recuerdo (§104). El guard que|delató el error de `1208` vivía dentro de ese script de un solo
uso, así que tampoco sobrevivía.

La herramienta existe por dos razones concretas, no por completitud:

```text
  1. que la medición de 1207 y 1208 sea REPRODUCIBLE
  2. que el guard que las detectó sea PERMANENTE y no una nota de prosa
```

## 1 · Los tres defectos que encontró, y por qué la herramienta vale por sí sola

No los refractioné: los encontró ella al ejecutarse sobre el árbol entero.

### Defecto 1 · el límite de un grupo es el opcode, no el comentario

`vid.h:309 /* COMMAND */` no lo cierra ningún otro comentario, así que se tragaba tres macros de
otro paquete:

```text
  PACKET3_SET_RESOURCES_VMID_MASK      << 0
  PACKET3_SET_RESOURCES_UNMAP_LATENTY  << 16
  PACKET3_SET_RESOURCES_QUEUE_TYPE     << 29     <- CHOCA con CMD_DAIC = 1<<29
```

Un paquete tiene un opcode; el opcode es la frontera. `P_OPCODE` cierra el grupo.

### Defecto 2 · la clase de carácter corta, por quinta vez

```text
  P_GRUPO  antes   (CONTROL\\d?|COMMAND)        ->  aceptaba   9 de 14
  P_GRUPO  ahora   (CONTROL\\d*[a-z]?|COMMAND)  ->  acepta    14 de 14
```

Los 5 que no aceptaba —`CONTROL2a`, `CONTROL2b`, `CONTROL3a`, `CONTROL3b` y el `CONTROL2a` de
`QUERY_STATUS`— no fallaban: **se absorbían en el grupo anterior** y sus desplazamientos se
sumaban. Salía publicado:

```text
  PACKET3_UNMAP_QUEUES_ACTION   << 0 -> bits [-1:0] = 0 bits  min 2, holgura -2
  PACKET3_UNMAP_QUEUES_PASID    << 0 -> bits [-1:0] = 0 bits
```

`bits [-1:0]` y `holgura -2` son **veredictos imposibles**, y salían como si fueran datos.

> Es el mismo fallo que ya tenía grabado —una clase de carácter que se queda corta y deja pasar
> sin fallar— y es la quinta vez que aparece. La diferencia con las otras cuatro: aquí el
> síntoma no fue un cero ni un recuento bajo, fue un **resultado imposible publicado sin que nada
> lo marcara**. Un imposible es la señal más fuerte que existe y yo no la miraba.
>
> La defensa no es mirar la salida: es **contrastar el recuento del filtro contra el total sin
> filtro**. Eso son tres vectores permanentes, `14`, `14`, y ninguno perdido.

### Defecto 3 · la prosa colisionaba por número de dword

`p[7]` devolvía la prosa de otro paquete. Ahora la prosa se devuelve como **bloque**, y se busca
dentro por contenido (`prosa_de(p, 7, contiene="COMMAND [30:21]")`). Hay un vector que exige más
de un bloque, para que la colisión no pueda volver.

## 2 · Los cuatro paquetes, con el layout completo

`vid.h` tiene **14** comentarios de dword. Salen **11** grupos con macros; los otros 3 son
comentarios sin macros.

### `PACKET3_DMA_DATA` (opcode 0x50) — prosa: 7 dwords

```text
  CONTROL  (vid.h:280)
      ENGINE            << 0   -> bits [12:0 ] = 13 bits  enum 0,1     min 1, holgura 12
      SRC_CACHE_POLICY  << 13  -> bits [14:13] =  2 bits  enum 0,1,2   EXACTO
      SRC_VOLATILE      = 1<<15                       FLAG 1 bit
      DST_SEL           << 20  -> bits [24:20] =  5 bits  enum 0,1,3   min 2, holgura 3
      DST_CACHE_POLICY  << 25  -> bits [26:25] =  2 bits  enum 0,1,2   EXACTO
      DST_VOLATILE      = 1<<27                       FLAG 1 bit
      SRC_SEL           << 29  -> bits [30:29] =  2 bits  enum 0,1,2,3 EXACTO
      CP_SYNC           = 1<<31                       FLAG 1 bit
      cubiertos 27/32    huecos: bits [16:19], bits [28]

  COMMAND  (vid.h:309)
      DIS_WC = 1<<21, CMD_SRC_SWAP <<22 [23:22] EXACTO, CMD_DST_SWAP <<24 [25:24] EXACTO,
      CMD_SAS = 1<<26, CMD_DAS = 1<<27, CMD_SAIC = 1<<28, CMD_DAIC = 1<<29,
      CMD_RAW_WAIT = 1<<30
      cubiertos por macros: bits [21:30]        la prosa dice [30:21]  -> COINCIDE
```

### `PACKET3_MAP_QUEUES` — prosa: 7 dwords

```text
  CONTROL   (vid.h:393)   6 macros   cubiertos 28/32   hueco bits [0:3]
  CONTROL2  (vid.h:400)   5 macros   cubiertos 31/32   hueco bits [0]
```

### `PACKET3_UNMAP_QUEUES` — prosa: 6 dwords, y es el único con **tiling completo**

```text
  CONTROL   (vid.h:414)
      ACTION      << 0  -> bits [ 3:0 ] =  4 bits  enum 0,1,2,3  min 2, holgura 2
      QUEUE_SEL   << 4  -> bits [25:4 ] = 22 bits
      ENGINE_SEL  << 26 -> bits [28:26] =  3 bits
      NUM_QUEUES  << 29 -> bits [31:29] =  3 bits
      cubiertos 32/32    huecos: NINGUNO

  CONTROL2a (vid.h:424)  PASID            << 0   bits [31:0 ] = 32 bits   32/32
  CONTROL2b (vid.h:426)  DOORBELL_OFFSET0 << 2  bits [31:2 ] = 30 bits   hueco [0:1]
  CONTROL3a (vid.h:428)  DOORBELL_OFFSET1 << 2  bits [31:2 ] = 30 bits   hueco [0:1]
  CONTROL3b (vid.h:430)  RB_WPTR          << 0   bits [31:0 ] = 32 bits   32/32
  CONTROL4  (vid.h:432)  DOORBELL_OFFSET2 << 2  bits [31:2 ] = 30 bits   hueco [0:1]
  CONTROL5  (vid.h:434)  DOORBELL_OFFSET3 << 2  bits [31:2 ] = 30 bits   hueco [0:1]
```

`UNMAP_QUEUES` reparte un mismo desplazamiento entre varios dwords porque `DOORBELL_OFFSET`
está partido en cuatro trozos de 30 bits: 4 × 30 = 120 bits de offset, repartidos. Eso **no** es
un error de layout, es el campo partido, y el nombre lo dice (`_0` a `_3`).

### `PACKET3_QUERY_STATUS` (opcode 0xA4)

```text
  CONTROL   (vid.h:445)
      CONTEXT_ID    << 0  -> bits [27:0 ] = 28 bits
      INTERRUPT_SEL << 28 -> bits [29:28] =  2 bits
      COMMAND       << 30 -> bits [31:30] =  2 bits
      cubiertos 32/32    huecos: NINGUNO

  CONTROL2a (vid.h:449)  PASID           << 0   bits [31:0 ] = 32 bits  32/32
  CONTROL2b (vid.h:451)  DOORBELL_OFFSET << 2   bits [24:2 ] = 23 bits  hueco [0:1]
                          ENG_SEL         << 25  bits [31:25] =  7 bits
```

## 2-bis · El fallo más grave de todos, y lo cometió el selftest

Escribí el selftest, dio **17 vectores OK**, y lo di por bueno. No lo era.

```text
  g.items()  entrega  (linea_del_comentario, (nombre, campos))
  yo escribí  for n, cs in dd   ->  n = NUMERO DE LINEA
  luego        if n == "CONTROL" ->  compara un entero con una cadena
```

Siempre falso. `ctrl` y `cmd` salían **vacíos**, y los **nueve vectores de `DMA_DATA`** —justo
los que reproduzco el hallazgo central— **no se ejecutaban**. El selftest contaba 17 de un total
de 26 y lo reporté como 17 de 17: `total` era el número de vectores **ejecutados**, así que un
bloque saltado en silencio se cuenta como cobertura, no como ausencia.

Es la **sexta** vez que aparece la clase, y la más difícil de ver: el síntoma no fue un cero ni
un número raro, fue **verde**.

La defensa permanente, y verificada por mutación:

```python
VECTORES_ESPERADOS = 30
...
if total != VECTORES_ESPERADOS:
    fallos.append(("se ejecutaron %d vectores de %d declarados" % ..., "..."))
```

Probado **roturando la herramienta a propósito**, no afirmándolo:

```text
  cambio  ctrl = [cs ... if nom == "CONTROLXX"]
  resultado
      FALLA las guardas de los bloques DMA_DATA son ciertas   ctrl=0 cmd=1
      FALLA se ejecutaron 25 vectores de 30 declarados
      SELFTEST: 23 de 25
  restaurado
      SELFTEST OK: 30 vectores
```

Sin ese guard, esta herramienta habría publicado durante un rato un selftest verde que no
probaba el 30% de lo que dice probar. **Un recuento que se calcula sobre lo ejecutado no puede
detectar lo que no se ejecuta.** Por eso `total` se contrasta contra una constante declarada, no
contra el número de llamadas a `chk`.

## 3 · Lo que la herramienta NO hace, y por qué está escrito

```text
  NO lee la GPU.                    RUNTIME=NOT_RUN,  siempre.
  NO da el ancho por EXTRACCION.    No hay codigo en el arbol que extraiga
                                    estos campos,  y no lo va a haber sin
                                    escribir un decodificador.
  NO inventa el ancho de un FLAG.   "(1 << n)" es un valor constante:  su
                                    ancho es 1 por construccion,  no por
                                    deduccion,  y la herramienta lo dice
                                    como FLAG y no como campo.
  NO afirma que "EXACTO" sea el ancho real.  EXACTO = el ancho calculado por
                                    desplazamiento coincide con el minimo que
                                    exige la enumeracion.  Que el hardware lo
                                    interprete asi es otro claim,  no medido.
  NO confunde NOT_FOUND con PROVEN_ABSENT.  Los huecos son NOT_FOUND:  ningun
                                    macro los nombra,  no consta que no
                                    pertenezcan a nada.
  NO escribe en el arbol.           Solo lectura.
```

## 4 · Clasificación epistémica

```text
  layout de 4 paquetes / 11 grupos  CORROBORATED   fuente primaria
  coherencia prosa-macros           OBSERVED        2 paquetes,  y coincide
  PIPE = 2 bits                     CORROBORATED   5 vias,  la 5a primaria
  ME = 1 bit                        CORROBORATED
  EN el ASIC leido                  NOT_OBSERVED
```

`1207` y `1208` affirmed los mismos layouts **con un método que tenía tres defectos**. Que
`1209` los reproduzca con un método corregido y vectores que los fijan no los degrada: los
**confirma** por una vía independiente (el recuento sin filtro, y el contraste de prosa).
Es lo contrario de `IMPLEMENTATION_IS_NOT_AUTHORITY`: dos implementaciones del mismo cálculo que
coinciden strengthens el dato, siempre que no compartan el mismo error.

## 5 · Procedimiento

```text
HERRAMIENTA  tools/pm4_grupos.py    30 vectores,  0 fallos
VECTORES     el guard global: 30 ejecutados de 30 declarados
             el guard de autovalidacion ve el positivo de vid.h:282
             un bloque que abre pegado al margen se sigue viendo
             23 bloques de enumeracion  /  78 valores,  no 55
             el enum {0,1,3} existe
             vid.h declara 14 comentarios de dword
             el filtro de grupos no pierde ninguno de los 14
             ningun nombre de dword se queda fuera de un grupo
             MAP_QUEUES/CONTROL2: PIPE [30:29], ME bit 31, DOORBELL 24 bits
             MAP_QUEUES/CONTROL2: el unico hueco es el bit 0
             DMA_DATA/CONTROL: 27/32, huecos [16:19] y [28]
             DMA_DATA/COMMAND: bits [21:30], 8 macros, 2 EXACTO
             ningun grupo se traga macros de otro paquete      <- REGRESION
             la prosa y los macros coinciden sobre COMMAND
             la prosa no se pisa entre paquetes
             no existe macro para BYTE_COUNT
             las guardas de los bloques DMA_DATA son ciertas      <- por el fallo
             los inicios de COMMAND son 8 y distintos
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
```