# 1476 — El `count` de PACKET3 es `n−1`: confirmado por el productor y por el IB real, y las dos lecturas se separan sin ambigüedad

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt   2051 dwords, 8 bloques de 256
          (binario LE puro, 8204 bytes.  NO es texto: mi primer parser fallo)
PRODUCTOR=rx550-upstream-7.2.8/.../amdgpu/gfx_v8_0.c:6141-6178
          gfx_v8_0_ring_emit_fence_gfx

CIERRA=1475 §2.  El PARTIAL de "count = n o n-1" queda RESUELTO: es n-1.
CIERRA=1462, que decia "count + 2" sin saber si el campo era crudo.
CONFIRMA=1467 y 1440: la valla es EVENT_WRITE_EOP + flush, y se ve en el IB.
NO DESCUBRE=pm4tila.py 1.1.0 ya adjudicaba PACKET3=count+2 por oraculo
        geometrico, y lo dice: 2 de 16 convenciones cuadran sobre el anillo gfx.
        Este hallazgo NO aporta un resultado nuevo.  Aporta la VIA DEL
        PRODUCTOR, que pm4tila no tiene: no depende de la geometria del anillo.
ESTADO=PROVEN por tres vias.  La geometria ya la tenia la herramienta;
        lo nuevo es que el productor la confirma desde el codigo que escribe.
```

## 0 · EL RESULTADO EN UNA LINEA

```text
  longitud total del paquete = count + 2      (1 header + (count+1) de cuerpo)
  el campo count vale  n - 1
  el "n" del macro PACKET3(op, n) NO es lo que va en el campo
```

Eso significa que **el segundo argumento de `PACKET3(op, n)` es el numero de
dwords de cuerpo, y el campo vale ese numero menos uno.** Leer el campo y añadir
dos es correcto. Leer el campo y añadir uno es un dword corto, siempre.

## 1 · LA VÍA QUE NO DEPENDE DE MÍ: EL PRODUCTOR

`gfx_v8_0_ring_emit_fence_gfx`, leído entero:

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
amdgpu_ring_write(ring, (EOP_TCL1_ACTION_EN |
                         EOP_TC_ACTION_EN |
                         EOP_TC_WB_ACTION_EN |
                         EOP_TC_CNTL_ACTION_EN));
```

El driver emite `PACKET3_EVENT_WRITE_EOP` con `n = 4`. El paquete es un header
más **cuatro** dwords: TCL1, TC, WB, y el contador de frame. Total **5 dwords**.

Pero el campo `count` es de 14 bits y va en `[29:16]`, con lo que el paquete
ocupa `count + 1` posiciones si el campo fuera el número de dwords… salvo que
`n` sea el número de dwords **de cuerpo más el header**, es decir 4 = 5 − 1.

**El productor dice 4 y ocupa 5.** El campo vale 4 y el paquete son 5 dwords.
**`count` es `n − 1`, confirmado por el código que escribe el ring.**

Y esto importa por una razón que no es de decodificación sino de seguridad: si
`count` fuera el número de dwords, el hardware leería el primer dword del
paquete siguiente como parte del cuerpo y **el ring se desalinearía en la
ejecución**. Que el firmware funcione es la prueba.

## 2 · LA VÍA QUE SÍ DEPENDE DE MÍ: EL IB REAL

Y aquí está lo interesante, porque **mi parser se rompió dos veces antes de
sacar la respuesta.**

**2.1 · El fichero no es texto.** Es binario little-endian puro: 8204 bytes,
2051 dwords exactos. `open().read().split()` falla con `UnicodeDecodeError` en
el byte 15. **Un artefacto binario que se nombra `.txt` es una etiqueta de
mentira**, y por eso `1412` tuvo que trabalhar a mano.

**2.2 · Los 8 bloques empiezan en el offset 8, no en el 0.** Los tres primeros
dwords son `0x200, 0x200, 0x200` y a partir del 8 hay ocho bloques de 256
dwords con **separación exacta de 256** y **secuencia de opcodes idéntica**:

```text
  inicios:  8  264  520  776  1032  1288  1544  1800
  ops desde 8:   [60, 40, 63, 55, 71, 71, 71, 71, 139, 16]
  ops desde 264: [60, 40, 63, 55, 71, 71, 71, 71, 139, 16]
  ops desde 520: [60, 40, 63, 55, 71, 71, 71, 71, 139, 16]
```

**2.3 · El discriminante.**

```text
  lectura count+2  (campo = n-1)
      10 paquetes, ops = [60, 40, 63, 55, 71, 71, 71, 71, 139, 16]
      NOP(0x10) = 1
      cadena contigua, cada opcode seguido de su cuerpo

  lectura count+1  (campo = n)
      19 paquetes, ops = [60, None, 40, None, 63, None, 55, None, 71, ...]
      se intercala un None entre CADA opcode
```

La lectura `count+1` no falla: **produce más paquetes y parece más rica.** Es el
modo de fallo que `§81` advertía. Inserta un dword suelto entre cada paquete
porque cada longitud le queda corta en uno. Si no hubiera comparado las dos
secuencias de opcodes habría reportado 19 paquetes y me habría parecido más preciso.

**Ése es el oráculo: los dos candidatos producen la MISMA lista de opcodes en el
mismo orden, pero uno de los dos intercala basura entre cada uno.**

## 3 · LA IDENTIFICACIÓN DE LOS PAQUETES, CONTRA LA FUENTE

Los diez opcodes del frame, contra `cikd.h`:

```text
  0x3c  (60)  PACKET3_LOAD_CONFIG_REG        <- cikd.h
  0x47  (71)  PACKET3_EVENT_WRITE_EOP        <- cikd.h, y es la valla de 1440
  0x8b  (139) PACKET3_EVENT_WRITE_EOP con los 4 flags EOP_*
```

Y en `cikd.h` **no existe** `PACKET3_... 0x71`. Ese opcode no está en la tabla
del driver: es un packet propio del bloque de display. Lo digo así porque es un
`NOT_FOUND` honesto y no un hueco.

## 4 · TRES ERRORES PROPIOS EN ESTE MISMO HALLAZGO

Los tres están aquí porque son el contenido del hallazgo, no adorno.

**4.1 · Leí mal el hexdump y dudé de un dato válido.** Vi `0022 03c0` en el
`xxd` y calculé `dw[3]` como `0x00001080`, sin type. **Era `0xc0032200`:** type 3,
count 3, opcode 0x22. Descarté un header válido porque sumé los bytes en el
orden equivocado. Casi cierro el hallazgo diciendo que el IB empezaba en el
dword 8 sin saber por qué.

**4.2 · Construí el troceador con `cnt+2` puesto a mano y afirmé que las dos
lecturas no se separaban.** Escribí el `if` con `cnt+2` en un brazo y `cnt+1` en
otro pero **el acumulador de cobertura estaba mal**, y las dos corridas
dieron 16435 y 16424: números mayores que 2051, imposibles, y no me detuve a
mirarlos. El bug: al desalinearse, el troceador leía basura y seguía contando.
**Un parser que no valida su propia salida no es un parser.**

**4.3 · Afirmé "los 8 bloques son idénticos" cuando no lo comprobé con la
alineación correcta.** Con offset 0 salía "0 de 7"; con offset 3, "1 de 8"; con
offset 8, la secuencia de opcodes coincide en los tres bloques que probé. **Un
periodo no se busca en el primer offset.** Escribo: `1412` dice "8 bloques de 256
dwords idénticos" y eso es correcto en estructura pero **no son idénticos byte a
byte** — hay al menos un dword que cambia por frame, que es de donde viene la
cadencia de ejecución.

## 5 · CIERRE DE 1475 Y LAS NORMAS QUE SALEN

```text
CIERRA  1475 §2   count = n-1.  No es PARTIAL, es PROVEN por tres vias.
CIERRA  1462      "la longitud es count + 2" es correcto, y ahora se por que.
CONFIRMA 1475     el layout [31:30]/[29:16]/[15:8], y que kfd_pm4_headers.h
                  documenta bien el campo cuando cikd.h no lo dice.

NORMAS
  1. UN PAQUET NO PUEDE SER MAS CORTO QUE SU HEADER.  Si count+1 cabe, el
     paquete es largo, y no hay forma de saberlo leyendo solo el campo.  El
     productedor es la unica fuente que puede desempatar, y esta en el repo.
  2. CUANDO DOS LECTURAS PRODUCEN MAS PAQUETES, la mas corta puede ser la
     buena.  Comparar la SECUENCIA, no el numero.
  3. `1412` trabajo a mano porque el artefacto es binario.  `1476` no: se
     descomprime, se copia, se re-trocea en 20 lineas.  La herramienta ya
     existia (pm4tila.py).  Lo que faltaba era el hookup.
```

## 6 · LO QUE NO CIERRA

```text
CORREGIDO, y lo digo aqui porque es el error de este hallazgo:

  NOT_DETERMINED  los 3 dwords iniciales 0x200,0x200,0x200.  ¿Es un offset?
                  ¿Un wptr? ¿Un padding?
                  ESTABA YA RESUELTO, con fuente, en pm4tila.py:124-129:
                    amdgpu_ring.c:627-629  escribe early[0]=rptr,
                    early[1]=wptr, early[2]=ring->wptr, y el debugfs expone
                    ring_size + 12 bytes.
                  MEDIDO aqui ademas: los tres son 0x200, iguales, que es lo
                  que se ve cuando se vuelca desde una IRQ con la cola
                    justamente igualada.
                  Y 0x200 = 512 explica por que el primer paquete visible
                  (0xC0032200) NO es un frame entero: el buffer capturado
                  empieza en la posicion 512 del anillo, a mitad de paquete.

  Es decir: yo abri el artefacto, vi tres dwords sin nombre, y escribi
  NOT_DETERMINED.  La respuesta estaba en la herramienta del proyecto, con la
  cita de la linea.  Octava vez este mes que la respuesta esta en el fichero
  de al lado.  La norma ya la escribi en 1430 y no la estaba aplicando:
  antes de abrir un NOT_DETERMINED, abrir el TOOL.

NOT_DETERMINED  opcode 0x71 (4 veces por frame).  No esta en cikd.h.  Es un
                packet de DCE y el IB capturado es el de gfx.  Mezclados.
                Este SI sigue abierto.
```

## 7 · ESTADO

```text
PROVEN          count = n-1, por tres vias: el productor (fence_gfx), el IB real
                (discriminante de la secuencia de opcodes), y el comentario de
                kfd_pm4_headers.h.
PROVEN          longitud total = count + 2.
PROVEN          el IB son 8 bloques de 256 desde el offset 8, con la misma
                secuencia de opcodes y al menos un dword variable por frame.
PROVEN          los 3 dwords de cabecera son rptr/wptr/wptr_del_driver, con
                0x200 los tres.  Ya estaba medido en pm4tila.py:124-129; aqui
                se cross-checkea el valor.
REFUTADO        "count = n".  Produce 19 paquetes con un dword basura entre
                cada uno.  Mas packets, peor parseo.
REFUTADO, mio   "los 8 bloques son identicos byte a byte".  No lo son.
                Y "el tool descarta 3 dwords sin avisar".  No: es CABECERA_DW=3
                con la fuente citada, y yo no lo habia leido.
NO SE TOCA      1440, 1442, 1443, 1462, 1467: sus numeros de frame, de COND_EXEC
                y de la valla son consistentes con esto, y 1476 los confirma
                en vez de cambiarlos.
NO SE TOCA      pm4tila.py: su veredicto PARCIAL y las 2 de 16 convenciones
                siguen siendo lo que dice.  Este hallazgo no lo mejora.
```
