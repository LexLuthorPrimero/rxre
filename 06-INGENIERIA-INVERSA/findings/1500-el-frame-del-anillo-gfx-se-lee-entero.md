# 1500 — El frame del anillo gfx se lee entero: 5 de sus 7 packets tienen nombre, y los tres que ya estaban identificados por separado caen en el mismo bloque de 256 dwords

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA        el opcode sin nombre que 1476 dejo abierto.  0x37 =
              PACKET3_WRITE_DATA, y con el cuerpo decodificado.
CONSOLIDA     1450 (el WRITE_DATA a 0xbcc), 1467 (la valla) y 1490 (el flush
              de HDP) en UN SOLO bloque.  No eran tres hallazgos: son tres
              paquetes del mismo frame.

DESCUBRE      0x40100000 del WRITE_DATA es WR_CONFIRM, no WR_ONE_ADDR.  El
              bit 20, no el 16.
PROVEN_ABSENT 0x3f y 0x8b NO tienen nombre en ninguna fuente disponible: ni
              cikd.h, ni las cabeceras asic_reg, ni el .reg de umr.
```

## 0 · QUÉ QUEDABA ABIERTO

`1476` §3 decodificó el frame y dejó escrito:

```text
  y el packet 0x47, que es el fence de EVENT_WRITE.
```

Pero del bloque que alli se enumero, tres quedaron sin nombre:
`0x3f`, `0x37` y `0x8b`. `1450` había identificado un `WRITE_DATA` a `0x0bcc`
por una cadena de contexto de 6 saltos, **sin saber que era uno de ellos**.

## 1 · EL FRAME, LOS 7 EN ORDEN

```text
  dword  op    nombre                count  cuerpo
  ------  ----  --------------------  -----  ---------------------------------
    3    0x22  COND_EXEC                3    0x00001080 0x000000ff 0x00000000 0x2b
    8    0x3c  WAIT_REG_MEM             5    0x00000143 0x00001537 0x00001538 0x1 0x1 0x20
   16    0x28  CONTEXT_CONTROL         1    0x80000000 0x00000000
   18    0x3f  SIN NOMBRE              2    0x00278000 0x00000001 0x07000158
   22    0x37  WRITE_DATA              3    0x40100000 0x00000bcc 0x00000000 0x1
   27    0x47  EVENT_WRITE_EOP         4    0x00038514 0x016b7000 0x200000ff 0x9bae 0x0
   33    0x8b  SIN NOMBRE              0    0x00000000
   34    ...  (resto NOP hasta 256)
```

**Cinco de siete con nombre.** Y el bloque entero son 256 dwords, uno por frame,
que es lo que `1476` §2.2 estableció.

## 2 · `0x3f` Y `0x8b` NO TIENEN NOMBRE EN NINGUNA FUENTE

```text
  cikd.h, grep PACKET3_* 0x3f  ->  (nada)
  cikd.h, grep PACKET3_* 0x8b  ->  (nada)
  TODO drivers/gpu/drm/amd/     ->  (nada)
  asic_reg/gca/gfx_8_0_sh_mask  ->  solo mascaras 0x3f de otros campos
  /usr/share/umr/.../gfx_8_0_0.reg
      -> NO define packet types.  Es un registro-por-registro, y sus entradas
         de "packet" son nombres de SEÑALES (end_of_packet, start_new_packet),
         no la tabla de opcodes de PM4.
```

```text
  PROVEN_ABSENT  0x3f y 0x8b no tienen nombre en ninguna fuente de esta maqueta.
  Y con 0x8b hay un dato extra:  count=0, cuerpo = un solo 0x00000000.
  Un PACKET3 de count=0 ocupa 2 dwords y no transporta nada.  Es un marcador
  de posicion, no trabajo.
```

## 3 · `0x37` ES `WRITE_DATA`, Y `0x40100000` NO ES LO QUE PARECÍA

`0x37 = PACKET3_WRITE_DATA` en `cikd.h`. Y el primer dword de cuerpo se decodifica
con las macros de ese mismo fichero:

```text
  WRITE_DATA_ENGINE_SEL(x)   (x) << 30
  WRITE_DATA_CACHE_POLICY(x) (x) << 25
  WR_CONFIRM                 (1 << 20)
  WR_ONE_ADDR                (1 << 16)
  WRITE_DATA_DST_SEL(x)      (x) << 8
```

```text
  0x40100000 = 0100 0000 0001 0000 ...
         ENGINE_SEL   = (>>30)&3  = 1  -> pfp
         CACHE_POLICY = (>>25)&1  = 0  -> LRU
         WR_CONFIRM   = (>>20)&1  = 1
         WR_ONE_ADDR  = (>>16)&1  = 0     <<<< NO es 1
         DST_SEL      = (>>8)&7   = 0  -> registro
```

**Mi primera lectura dijo `WR_ONE_ADDR=1` y escribi "lleva una sola direccion".**
Es `WR_CONFIRM`, el bit 20. Lo corregí al calcular los cinco campos, y el
resultado cambia la lectura del cuerpo:

```text
  WR_ONE_ADDR = 0  ->  el paquete lleva la direccion de 64 bits
  body[1] = 0x00000bcc   registro        (parte baja de la direccion)
  body[2] = 0x00000000   (parte alta: 0)
  body[3] = 0x00000001   dato = 1
```

Y con `WR_CONFIRM=1`, ese `1` final es además una confirmación de escritura.

## 4 · `DST_SEL`, Y CIERRA UNA PREGUNTA DE 1459

`1459` cerró, con el oráculo de `umr`, que `DST_SEL` está en los **bits 8–10** de
este mismo registro, y que hay un tercer campo que el driver nunca escribe. Aquí:

```text
  DST_SEL = 0  ->  "0 - register", segun el comentario de cikd.h
```

Y coincide con lo que `1459` demostro: este paquete escribe **a un registro**, no a
memoria. `DST_SEL=0` es el caso documentado.

```text
  CONFIRMA  1459 §2: DST_SEL=0 significa registro, y el driver lo usa asi.
```

## 5 · LA CONSOLIDACIÓN, Y ES EL VALOR REAL DE ESTE HALLAZGO

```text
  1450  "el WRITE_DATA a 0x0bcc es mmHDP_DEBUG0, valor 1, cadena de 6 saltos"
  1467  "la valla es EVENT_WRITE_EOP con los 4 flags EOP"
  1490  "el WAIT_REG_MEM es el flush de HDP sobre 0x1537/0x1538, mask=1"

  LOS TRES SON PAQUETES CONSECUTIVOS DEL MISMO BLOQUE DE 256 DWORDS.

  Eso significa que los tres hallazgos no estaban describiendo tres cosas:
  estaban describiendo tres trozos del mismo objeto, sin saber que era el
  mismo.  Y el bloque de 256 dwords es UN FRAME.

  Y AHORA SE LEE DE PRINCIPIO A FIN:
    1. COND_EXEC      gobierna si el resto se ejecuta
    2. WAIT_REG_MEM   espera a que el HDP termine el flush
    3. CONTEXT_CONTROL
    4. 0x3f           sin nombre
    5. WRITE_DATA     escribe en mmHDP_DEBUG0 (0xbcc) el valor 1
    6. EVENT_WRITE_EOP   la valla, con los flags EOP y el fence
    7. 0x8b           marcador sin carga

  QUE ORDEN TIENE:  espera al HDP, escribe el debug, y despues mete la valla.
  Es la secuencia de un frame que se asegura de que el HDP esta limpio antes
  de terminar.
```

## 6 · LO QUE SIGUE SIN RESOLVER, Y ES POCO

```text
NOT_DETERMINED  que son 0x3f (cuerpo 0x278000, 1, 0x07000158) y 0x8b.
                Sin nombre en ninguna fuente.  Y sin mas oraculo que buscar:
                el de umr no tiene tabla de packets, y el corpus no lo tiene.

ABIERTO, y con criterio    0x3f tiene cuerpo de 3 dwords con 0x00278000 y
                           0x07000158, y NINGUNO de los dos aparece en una
                           cabecera asic_reg.  Eso no los hace registros: los
                           dos probablemente NO son direcciones.  0x07000158 tiene
                           forma de mascara de bits (tres campos de un byte).
                           NOT_DETERMINED, y no lo voy a suponer.

CIERRA          el "opcode sin nombre" de 1476 §3, en lo que se refiere a 0x37
CIERRA          la ambiguedad de 0x3f y 0x8b: NO es que no se mire, es que no
                hay donde mirar.  Eso es PROVEN_ABSENT y no NOT_FOUND.
```

## 7 · ESTADO

```text
PROVEN          0x37 = PACKET3_WRITE_DATA (cikd.h)
PROVEN          0x40100000 = ENGINE_SEL(pfp) + WR_CONFIRM, con DST_SEL=0
PROVEN          WR_ONE_ADDR=0, no 1.  Mi primera lectura fue WR_ONE_ADDR y
                cambia la interpretacion del cuerpo.
CONFIRMA        1459: DST_SEL=0 = registro, y el driver lo usa asi
CONSOLIDA       1450, 1467 y 1490 son tres paquetes del MISMO frame de 256
                dwords, no tres hallazgos independientes

PROVEN_ABSENT   0x3f y 0x8b no tienen nombre en cikd.h, ni en las cabeceras
                asic_reg, ni en el .reg de umr (que no define packet types)
PROVEN          0x8b tiene count=0: ocupa 2 dwords y no transporta nada

ERROR PROPIO    leí WR_ONE_ADDR en el bit 16 cuando el flag puesto era WR_CONFIRM
                del bit 20.  Decir "lleva una sola dirección" era falso.

NOT_DETERMINED  que son 0x3f y 0x8b.  Sin fuente disponible.
```

## 8 · LA LECCION, QUE ES LA DE `1473` UNA VEZ MAS

`1450` identificó `0x0bcc` traversing una cadena de 6 saltos de contexto, porque
el primer `grep` del opcode no dio un nombre. **Ese era el mismo problema de
`1470`**: el número de opcode no identifica el packet, igual que la dirección no
identifica el registro.

La diferencia es que ahora tengo la herramienta que lo resuelve en una línea:

```text
  grep -oE "PACKET3_[A-Z_0-9]+[[:space:]]+0x37" cikd.h
```

**Tardé 50 hallazgos en hacer esa pregunta.** `1450` dio con la respuesta correcta
por un camino que costaba 6 pasos, y la respuesta directa estaba en un fichero
que ya tenía abierto.
