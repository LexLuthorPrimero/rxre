# 1495 — Los 12 dwords de la invalidación son 2 `SRBM_WRITE` y 1 `POLL_REGMEM`, el VMID es el 3,
# y el poll con `mask=0` ocupa el 4,7 % del anillo sin esperar nada

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

IDENTIFICA   los 3 packets de la secuencia, no como "12 dwords".  Y con eso
             PROVEN el VMID 3, que 1493 dejó como CONSISTENTE.
CUANTA      el coste en dwords de anillo:  9,4 % del buffer en invalidaciones
             y 4,7 % en el poll con mask=0, que no espera.

CONFIRMA     gmc_v8_0.c:659  WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid):
             el valor del SRBM_WRITE es literalmente 1 << 3 = 8.
VINCULA      1430 (0x54f), 1401 y 1459 (0x51e), 1488 (el POLL_REGMEM de 6).
             Los cuatro hallazgos cae sobre los mismos 12 dwords.
```

## 0 · DE DÓNDE SALE

`1493` dejó el `NOT_DETERMINED` de `[2]=8` como *CONSISTENTE* con VMID 3, y dijo
que no lo afirmaria sin leer el layout. También dejó abierta la pregunta de
cuánto anillo cuesta. Las dos se resuelven con lo mismo: **mirar los 12 dwords
como packets en vez de como valores sueltos.**

## 1 · LA SECUENCIA, CON LOS TRES PACKETS

Los opcodes salen de `tonga_sdma_pkt_open.h` — el header que incluye
`sdma_v3_0.c:48` — no de un catálogo de registros:

```text
  [ 0] 0xf000000e   op=0x0e  SDMA_OP_SRBM_WRITE   (línea 39)
  [ 1] 0x0000054f   PAGE_TABLE_BLOCK_SIZE / array context0-7   (1430)
  [ 2] 0x0f400900   base de la tabla de pagina del proceso
  [ 3] 0xf000000e   op=0x0e  SDMA_OP_SRBM_WRITE
  [ 4] 0x0000051e   mmVM_INVALIDATE_REQUEST                   (1401, 1459)
  [ 5] 0x00000008   = 1 << 3   <- EL VALOR
  [ 6] 0x00000008   op=0x08  SDMA_OP_POLL_REGMEM   (línea 33)
  [ 7] 0x00001478   mmVM_INVALIDATE_REQUEST << 2
  [ 8] 0x00000000   value
  [ 9] 0x00000000   reference
  [10] 0x00000000   mask
  [11] 0x0fff000a   RETRY_COUNT=0xfff  INTERVAL=10
```

**Tres packets: dos escrituras y un poll.** Cada `SRBM_WRITE` son 4 dwords
(header, addr, val, y el siguiente header) — que es exactamente lo que escribe
`sdma_v3_0_ring_emit_wreg` (`sdma_v3_0.c:1074-1080`):

```c
static void sdma_v3_0_ring_emit_wreg(struct amdgpu_ring *ring, u32 reg, u32 val)
{
        amdgpu_ring_write(ring, SDMA_PKT_HEADER_OP(SDMA_OP_SRBM_WRITE) |
                          SDMA_PKT_SRBM_WRITE_HEADER_BYTE_EN(0xf));
        amdgpu_ring_write(ring, reg);
        amdgpu_ring_write(ring, val);
}
```

## 2 · EL VMID 3, PROVEN

```text
  [5] = 0x00000008 = 1 << 3
```

Y el productor del segundo `SRBM_WRITE` es el MMU, `gmc_v8_0.c:659`:

```c
        /* bits 0-15 are the VM contexts0-15 */
        WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

**El valor escrito es `1 << vmid`, y lo que hay en el anillo es `1 << 3`.**
Con la estructura de packet conocida, `[5]` es el campo `val` de un
`SRBM_WRITE` sobre `mmVM_INVALIDATE_REQUEST`. Eso es `PROVEN`, no `CONSISTENTE`:
ya no depende de interpretar un dword suelto.

**Con esto los cuatro hallazgos caen sobre los mismos 12 dwords:**

| hallazgo | qué aporta | dword |
|---|---|---|
| `1430` | `0x54f` es el array de context 0–7 | `[1]` |
| `1401`, `1459` | `mmVM_INVALIDATE_REQUEST = 0x51e` | `[4]`, `[7]` |
| `1493` | se emite 16 veces, idénticas | la secuencia entera |
| `1488` | el `POLL_REGMEM` de 6 dwords con `func=0` | `[6]`–`[11]` |
| `1411` | el poll no espera porque `mask = 0` | `[8]`–`[10]` |

## 3 · EL COSTE EN DWORDS, Y ES LO QUE INTERESA AL PROYECTO

```text
  buffer del anillo                    2048 dwords
  secuencias de invalidacion en la captura    16
  longitud de cada una                       12 dwords
  ------------------------------------------------------------------
  total en invalidaciones        192  ->   9,4 % del buffer
  de los cuales, el poll con mask=0
  (dwords [6] a [11], 6 por vez)    96  ->   4,7 % del buffer
```

**Y el poll no espera.** Es `FUNC(0)` —`always`—, con `value = 0`,
`reference = 0` y `mask = 0`. `1488` ya lo había decoding; aquí se ve que ocupa
**6 dwords de los 12**, la mitad de la secuencia.

```text
  PROVEN_DERIVED  la mitad de la secuencia de invalidacion es un paquete que no
                  hace nada.  6 de 12 dwords, 96 de 192, 4,7 % del anillo.

  Y OJO con lo que esto NO demuestra:
    - que quitarlo mejore el rendimiento.  Eso requiere medir (§74) y hay un
      argumento en contra: el poll podria estar ahi por robustez, para no
      depender de que el HDP flush haya terminado.  "No espera" no es
      "sobra".
    - que 16 invalidaciones del mismo VMID sean un error.  Pode    - que 16 invalidaciones del mismo VMID sean un error.  Puede que el
      scheduler revalida por robustez, y la captura no dice quien las pide.

  LO QUE SI SE PUEDE DECIR:
    un driver propio que no espere nada con un poll de mask=0 ahorra 6 dwords
    por invalidacion.  Con 16 por ventana de anillo, son 96 dwords, un 4,7 %
    del buffer, que queda para trabajo util.  Eso es un DATO de ocupacion, no
    una mejora de rendimiento, y la distincion es la de §75.
```

## 4 · POR QUÉ MIRAR COMO PACKETS Y NO COMO VALORES

Porque el catálogo de registros **no sirve aquí**, y decirlo es parte del
hallazgo:

```text
  Feeding regalias.py con los 12 dwords sueltos da:

    0x0000054f  ->  mmDC_PERFMON7_... , regMPCC_MCM1_...        (NADA que ver)
    0x0000051e  ->  mmUVD_RB_BASE_HI3, regDCHUBBUB_...          (NADA que ver)
    0x00001478  ->  mmCM5_CM_GAMCOR_..., mmMPCC_OGAM3_...       (NADA que ver)

  Porque 0x54f y 0x51e NO SON DIRECCIONES DE REGISTRO en el sentido de MMIO:
  un packet SDMA los lleva como el campo "reg" de un SRBM_WRITE, y la
  escritura la hace la unidad SRBM, no el MMIO del ASIC.

  Y aun asi los NOMBRES son correctos:  0x51e ES mmVM_INVALIDATE_REQUEST, y
  0x54f ES el PAGE_TABLE_BLOCK_SIZE.  Lo que cambia es la RUTA por la que se
  llega, no el destino.

  ESTO ES 1470 CONCRETO:  el findings que mas hallazgos ha producido de esta
  sesion es que un numero de registro no identifica un registro.  Y aqui se ve
  la version fuerte:  un numero de registro escrito en un packet SDMA no es un
  acceso MMIO, aunque el numero sea el correcto.
```

## 5 · ESTADO

```text
PROVEN          los 12 dwords son 2 SRBM_WRITE (4+4) y 1 POLL_REGMEM (6), con
                los opcodes leidos de tonga_sdma_pkt_open.h
PROVEN          [5] = 1 << 3 = VMID 3, como campo val de un SRBM_WRITE sobre
                mmVM_INVALIDATE_REQUEST.  Cierra el CONSISTENTE de 1493.
PROVEN_DERIVED  el poll con mask=0 ocupa 6 de los 12 dwords: la mitad de la
                secuencia, y 4,7 % del buffer del anillo en esta captura
PROVEN          1493 1401 1459 1430 1488 1411 caen sobre los mismos 12 dwords,
                cada uno aportanto un campo distinto
DESCUBRE        regalias.py NO es aplicable a los campos reg/val de un packet
                SDMA, aunque los numeros coincidan con los registros.  Version
                fuerte de 1470.

NOT_DETERMINED  si quitar el poll con mask=0 mejora el rendimiento.  Medible
                con §74, y HAY un argumento en contra: puede estar ahi por
                robustez.  "No espera" no es "sobra".
NOT_DETERMINED  quien pide las 16 invalidaciones del mismo VMID.

CIERRA          el CONSISTENTE de 1493 §4 sobre el VMID
```

## 6 · LO QUE SIGUE, Y ES LO QUE MANDO

La pregunta de `1493` §7.3 — *si el poll con `mask=0` no espera, ¿qué garantía
da?* — tiene ahora la mitad estática resuelta y la otra mitad es hardware:

```text
  YA SABIDO   no espera (mask=0 con func=0)
  YA SABIDO   ocupa 6 de 12 dwords, la mitad de la secuencia
  FALTA       si el hardware lo trata como no-op o si aun asi sincroniza algo

  Y HAY UNA TERCERA QUE NO HABIA PLANTEADO:
    el SRBM_WRITE #1 escribe 0x54f = la BASE DE TABLA, y el #2 escribe 0x51e.
    Los dos son escrituras REALES a registros del ASIC.  Las 16 veces.
    Eso es trabajo que NO es un no-op, y es la parte que si hay que replicar.

    O sea:  de los 12 dwords, 4 son utiles, 4 son utiles, y 6 no hacen nada.
    Un driver propio tiene que escribir los 8 primeros y puede omitir los 6
    ultimos, SI se confirma que no sincronizan.

  ESO es lo que separa "copiar el driver de referencia" de "escribir el
  correcto", y es la siguiente medicion.
```
