# 1225 — Los nueve que no pude clasificar, clasificados: **8 cuadran** con `count = payload − 1`, y `NOP` no es un paquete en un flujo. Y el CONTROL **no está siempre en el dword 2**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSE-OUT · SEMANTICS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/pm4_grupos.py  (modo --clase,  +4 vectores)
CIERRA   1213 §5 y 1223:  los 9 paquetes cuya clase dije que no tenia
                          discriminante.  Si lo tenia:  el count de la cabecera
VALIDA   count = payload - 1  en 8 paquetes mas:  11 en total con 11 aciertos
DESRULEO NO SE PUEDE ASUMIR QUE EL CONTROL SEA EL DWORD 2
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · El discriminante que no buscaba

En `1213` escribí de estos nueve:

> no los clasifico porque no tengo un discriminante para separarlos, y un
> `SIN ESTRUCTURA` sin probar sería repetir el error de `1210`

El discriminante estaba en el propio driver y es mecánico: **el `count` de la cabecera dice
cuántos dwords de payload se escriben, y se cuenta contra las escrituras reales.**

## 1 · Los nueve, con la regla aplicada

```text
  REGLA  count de la cabecera  ==  (escrituras que siguen)  -  1

  paquete                   count   payload  escrituras  veredicto
  NOP                       16383   16384        --      ASIGNACION a miembro de
                                                          struct,  no es un paquete
  DISPATCH_DIRECT           3         4          4       CUADRA
  CONTEXT_CONTROL           1         2          2       CUADRA
  CLEAR_STATE               0         1          1       CUADRA
  COND_EXEC                 3         4          4       CUADRA
  INDIRECT_BUFFER_CONST     2         3          3       CUADRA
  COPY_DATA                 4         5          5       CUADRA
  PFP_SYNC_ME               0         1          1       CUADRA
  SWITCH_BUFFER             0         1          1       CUADRA

  8 cuadran,  1 no aplica
```

## 2 · `NOP`: por qué no es una excepción, sino otra cosa

```c
   6873  		.nop = PACKET3(PACKET3_NOP, 0x3FFF),
```

Eso es una **entrada de la tabla de funciones del anillo**, `gfx_ring_funcs.nop`, que guarda el
comando de sincronización. No está en un flujo de paquetes: no hay `amdgpu_ring_write` detrás, y
`0x3FFF` no es un count de payload sino el payload del propio NOP.

Así que `count = payload − 1` no se le aplica **porque no le aplica a nada**: no es un paquete
emitido, es un valor de tabla. Y eso lo hace `NOT_APPLICABLE`, no un fallo de la regla.

## 3 · Lo que de verdad aporta: el CONTROL no está siempre en el dword 2

Fue lo que salió al mirar qué escribe cada uno. Los cuatro con payload compuesto:

```text
  COPY_DATA          count=4  ->  5 payload
      dword 2   0 | (5 << 8) | (1 << 20)     <- CONTROL: SRC_SEL, DST_SEL, WR_CONFIRM
      dword 3   reg                            SRC address
      dword 4   0                              (destino)
      dword 5   lower_32_bits(...)             ADDR_LO
      dword 6   upper_32_bits(...)             ADDR_HI
      =>  EL CONTROL VA PRIMERO

  INDIRECT_BUFFER_CONST   count=2  ->  3 payload
      6092   (2 << 0) | (ib->gpu_addr & 0xFFFFFFFC)      ADDR_LO
      6097   upper_32_bits(ib->gpu_addr) & 0xFFFF        ADDR_HI
      6098   control = ib->length_dw | (vmid << 24)      CONTROL,  AL FINAL

  COND_EXEC          count=3  ->  4 payload
      6322   lower_32_bits(addr)      ADDR_LO
      6323   upper_32_bits(addr)      ADDR_HI
      6325   0                        COND_EXEC_GPU_ADDR  (se parchea luego)
      6328   0                        COND_EXEC_CPU_ADDR  (se parchea luego)
      =>  DIRECCIONES PRIMERO

  DISPATCH_DIRECT    count=3  ->  4 payload
      1542   8     /* x */
      1543   1     /* y */
      1544   1     /* z */
      1545   REG_SET_FIELD(0, COMPUTE_DISPATCH_INITIATOR, ...)   CONTROL,  AL FINAL
      =>  COORDENADAS PRIMERO
```

**En uno de los cuatro el control va primero; en los otros tres va al final.** No hay convención,
y para un decodificador eso significa que la posición del dword de control **tiene que determinarse
por paquete**, nunca por suposición.

Eso también explica por qué el método de `1207` —«el inicio del campo siguiente acota el
anterior»— solo funciona **dentro de un grupo de dwords declarado**. Un grupo de macros no dice en
qué dword está el control; solo dice qué bits ocupa *donde esté*. Por eso `1218` daba cotas y
no anchos, y por eso eso no se arregla con mas de lectura.

## 4 · La validación que se acumula

```text
  1199   count = payload - 1,  con 3 puntos de emision  y  .emit_ib_size = 7
  1225   el mismo invariante,  en 8 paquetes mas

  total  11 comprobaciones,  11 aciertos,  0 fallos
```

Y la regla no se pierde: los cuatro vectores nuevos están en `pm4_grupos.py --selftest`, que sube de
53 a **57 vectores**. El guard global de recuento sigue obligated a que el número ejecutado
concurre con el declarado.

## 5 · Procedimiento

```text
PREGUNTA   ¿hay discriminante para clasificar los 9 paquetes sin clase?
HERRAMIENTA  tools/pm4_grupos.py --clase   (nuevo)   +4 vectores
FUENTES     gfx_v8_0.c,  los nueve puntos de emision leidos con linea
MEDIDO      8 de 9 cuadran con count = payload - 1
            NOP:  ASIGNACION a miembro de struct,  no paquete en un flujo
            COPY_DATA lleva el CONTROL primero;  DISPATCH_DIRECT,  COND_EXEC e
            INDIRECT_BUFFER_CONST lo llevan al final
AUTOCORR.  tres fallos mios al construir la herramienta,  todos visibles:
  (a) ventana de 12 lineas que no paraba en la linea en blanco,  y se comia el
      cuerpo de un bucle posterior:  CONTEXT_CONTROL daba 4 escrituras contra 2
      de payload y salia NO CUADRA siendo correcto.
  (b) en la forma por asignacion la escritura de la CABECERA es una escritura
      distinta de la del literal  (literal en 6078,  cabecera escrita en 6091),
      y la contaba:  INDIRECT_BUFFER_CONST daba 4 contra 3.
  (c) las dos formas de asignacion se trataban como una:  hay que separar
      "var = PACKET3(.) y luego ring_write(var)"  — que es un paquete de
      verdad —  de ".campo = PACKET3(.) en un inicializador de struct",  que no
      lo es.  El discriminante es si la variable aparece despues en un
      ring_write.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - la posicion del dword de control,  paquete por paquete,  es ahora la fila mas
    grande que queda de este frente:  8 de 9 ya tienen el numero de payload
    exacto  y  3 de 4 medidos tienen la posicion del control medida
  - NOP:  el valor 0x3FFF que el driver guarda en gfx_ring_funcs.nop  merece su
    propio hallazgo,  porque es el mecanismo de sincronizacion del KIQ
```