# 1490 — El `WAIT_REG_MEM` del anillo real NO es el de `1411`: es el flush de HDP con `mask=1`, y sus siete dwords cuadran uno a uno con una función que no había leído

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CORRIGE, por via indirecta  1411 y 1441 afirmaban que el WAIT_REG_MEM del anillo
                            gfx espera con mask=0 y por tanto no espera.  En el
                            anillo real hay 8 WAIT_REG_MEM y TODOS tienen
                            mask=1, reg=0x1537, ref=0x1538.  No son el del
                            vm_flush:  son el flush de HDP.

DESCUBRE       0x1537 = mmGPU_HDP_FLUSH_REQ y 0x1538 = mmGPU_HDP_FLUSH_DONE, en
               el bloque bif.  Los emite gfx_v8_0_ring_emit_hdp_flush, que NO es
               la funcion que 1411 leyo.
CONFIRMA       los 8 son identicos y hay uno por cada bloque de 256 dwords.
CIERRA         con aritmetica el valor de ref_and_mask, que en el fuente es una
               VARIABLE:  aqui vale 1, y es GPU_HDP_FLUSH_DONE__CP0_MASK.
PERFECCIONA    1476.  Los 7 dwords del paquete cuadran EXACTAMENTE, incluido el
               poll interval 0x20 que un primer recuento dio por distinto.
```

## 0 · QUÉ SE PREGUNTÓ

`1411` dice que el `WAIT_REG_MEM` del flush de VM espera con `mask = 0` y que por
tanto **no espera**. `1441` contó 3 de esos paquetes en el IB.

Eso nunca se contrastó contra el anillo real. Ahora sí.

## 1 · LO QUE HAY EN EL ANILLO

Opcodes PACKET3 en `amdgpu_ring_gfx.txt`, leídos con el layout de `1476`:

```text
  0x10  NOP                 x1648
  0x47  EVENT_WRITE_EOP     x32     <- la valla, 1467
  0x22  COND_EXEC           x8      <- 1442
  0x3c  WAIT_REG_MEM        x8      <- ESTE
  0x28  CONTEXT_CONTROL     x8
  0x3f  (no en cikd.h)      x8
  0x37  (no en cikd.h)      x8
  0x8b  (no en cikd.h)      x8
```

**Ocho `WAIT_REG_MEM`, uno en cada bloque de 256 dwords** (posiciones 8, 264,
520, 776, 1032, 1288, 1544, 1800 — exactamente los inicios de bloque que
`1476` §2.2 estableció). Los ocho, byte a byte, con los campos declarados en
`cikd.h:294-311` (`FUNCTION` en `[2:0]`, `OPERATION` en `[7:6]`, `ENGINE` en
`[9:8]`):

```text
  hdr      0xc0053c00   type=3  count=5  opcode=0x3c
  body0    0x00000143   ENGINE=1  OPERATION=1  FUNCTION=3
  body1    0x00001537
  body2    0x00001538
  body3    0x00000001
  body4    0x00000001
  body5    0x00000020
  siguiente 0xc0012800   type=3  count=1  opcode=0x28  (CONTEXT_CONTROL)
```

`OPERATION=1` y `FUNCTION=3` son literalmente el comentario del driver:
`WAIT_REG_MEM_OPERATION(1) | /* write, wait, write */` y
`WAIT_REG_MEM_FUNCTION(3) | /* == */`.

## 2 · QUÉ REGISTROS SON

Ni `0x1537` ni `0x1538` son `mmVM_INVALIDATE_REQUEST` (`0x51e`, según `1401` y
`1459`). Resueltos con `regalias.py` (1470), de 4 bloques posibles:

```text
  0x1537  [bif]  mmGPU_HDP_FLUSH_REQ      <- el que sirve
  0x1538  [bif]  mmGPU_HDP_FLUSH_DONE     <- el que sirve
```

Confirmado en `bif_5_0_d.h:78-79` — que es la cabecera que `gfx_v8_0.c:47`
incluye — y también en `bif_4_1_d.h`.

**Es un flush de HDP, no una invalidación de VM.** Y por eso `mask = 1` y no 0:
el paquete espera a que un registro **cambie** a un valor concreto, que es lo
único que un flush necesita.

## 3 · LA FUNCIÓN QUE EMITE ESTO

```c
/* gfx_v8_0.c:6042-6062, LEIDA ENTERA */
static void gfx_v8_0_ring_emit_hdp_flush(struct amdgpu_ring *ring)
{
        u32 ref_and_mask, reg_mem_engine;

        if (!adev->gfx.funcs->get_hdp_flush_mask) { ...return; }

        adev->gfx.funcs->get_hdp_flush_mask(ring, &ref_and_mask, &reg_mem_engine);
        amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
        amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(1) |
                                 WAIT_REG_MEM_FUNCTION(3) |
                                 reg_mem_engine));
        amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_REQ);
        amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_DONE);
        amdgpu_ring_write(ring, ref_and_mask);
        amdgpu_ring_write(ring, ref_and_mask);
        amdgpu_ring_write(ring, 0x20); /* poll interval */
}
```

Y el valor de las dos variables (`gfx_v8_0_get_hdp_flush_mask`, línea 5229):

```c
} else {                                          /* anillo GFX, no compute/kiq */
        *ref_and_mask  = GPU_HDP_FLUSH_DONE__CP0_MASK;
        *reg_mem_engine = WAIT_REG_MEM_ENGINE(1);      /* pfp */
}
```

## 4 · LOS DWORDS, UNO A UNO

```text
  dword  fuente                                    anillo       ?
  ------  ---------------------------------------   ----------   --------
  hdr     PACKET3(PACKET3_WAIT_REG_MEM, 5)         0xc0053c00    SI
  body0   OPERATION(1)|FUNCTION(3)|ENGINE(1)        0x00000143    SI
  body1   mmGPU_HDP_FLUSH_REQ                       0x00001537    SI
  body2   mmGPU_HDP_FLUSH_DONE                      0x00001538    SI
  body3   ref_and_mask = CP0_MASK                   0x00000001    SI
  body4   ref_and_mask = CP0_MASK                   0x00000001    SI
  body5   0x20                                       0x00000020    SI
```

**Siete de siete.** Y `body0 = 0x143` se explica con aritmética, sin mirar el
oráculo de registros:

```text
  OPERATION(1) << 6  = 0x40
  FUNCTION(3)        = 0x03
  ENGINE(1)     << 8 = 0x100
  ------------------------
                      0x143    exacto
```

**Y con esto `1476` queda confirmado por completo**: el layout `count+2` de §0 de
ese hallazgo dice que un `PACKET3` con `count=5` ocupa 7 dwords. Aquí ocupa 7, y
el séptimo es `0xc0012800`, un `PACKET3_CONTEXT_CONTROL` con `count=1`. **Ni un
dword de más ni uno de menos, en los ocho paquetes.**

## 5 · EL ERROR, Y POR QUÉ LO ESCRIBE

En el primer recuento leí seis dwords a partir del header y obtuve `body5 = 1`
en el anillo frente a `0x20` en el fuente. Casi lo escribo como discrepancia
fuente/hardware.

**No lo era: conté mal.** `count = 5` son cinco dwords de cuerpo, no seis. Mi
lectura por indice tomaba el sexto cuerpo, que en realidad es el **siguiente
paquete**.

```text
  LA REGLA, y es la segunda vez esta sesion que la incumplo:
    un paquete tiene una longitud DECLARADA, y leerlo por posicion sin
    respetarla produce un valor plausible que pertenece a otra cosa.

  Aqui el valor de mas (0x1) era identico a body3 y body4, de modo que
  "mask=1" y "interval=1" parecian una lectura coherente.  Un error de indice
  que produce una coincidencia con el campo vecino.

  Y POR QUE LO DETECTE:  me hizo dudar de que el que el header del paquete siguiente
  (0xc0012800) es un header PLAUSIBLE.  Un header plausible justo despues del
  cuerpo es la senal de que el cuerpo termino antes.  Si no lo hubiera mirado,
  1490 afirmaria una discrepancia que no existe.
```

## 6 · LO QUE CIERRA Y LO QUE ABRE

```text
CORRIGE, por via indirecta
  1411   el "WAIT_REG_MEM con mask=0 que no espera" sigue siendo cierto para el
         flush de VM (gfx_v8_0.c:6205-6213), PERO ese paquete NO ESTA en la
         captura.  Los 8 que estan son del flush de HDP.
  1441   los "3 WAIT_REG_MEM con FUNCION 0" que contó en el IB no son estos.
         Estos tienen FUNCTION=3.  Son paquetes distintos.

  LO QUE NO SE CORRIGE, y es importante:  1411 sigue siendo valido como
  afirmacion sobre EL CODIGO.  Lo que se cae es la idea de que esos son los
  paquetes del anillo capturado.

ABRE, y es la pregunta de 1411 con el dato que faltaba
  1411 dice que el flush de VM espera con mask=0 y no espera.  Eso es una
  afirmacion sobre lo que el driver ESCRIBE.  Si el paquete no aparece en el
  anillo capturado, la afirmacion sigue siendo valida pero el ARTEFACTO no la
  contiene.

  Y HAY UNA EXPLICACION POSIBLE, medible:  1476 §6 marco el IB como el frame de
  un context, y este anillo es de un frame de ese tipo.  Si este frame NO
  invalida VM porque su VMID no cambio, entonces el flush de VM no se emite.
  Eso no es un bug: es que no hacia falta.

  NOT_DETERMINED  si el flush de VM se emite cuando el VMID cambia.  Medible:
  buscar INVALIDATE_REQUEST en el anillo cuando hay un cambio de page table.
  No lo he hecho.

CONFIRMA, por segunda via
  1488  los 16 POLL_REGMEM con func=0 en SDMA.  Ese es el camino del flush de
        VM en el anillo SDMA.  El del anillo GFX no esta en la captura, y el
        de HDP si.  Que sean coherentes es la conclusion.
```

## 7 · ESTADO

```text
PROVEN          8 WAIT_REG_MEM en el anillo gfx, identicos, uno por bloque de
                256 dwords, en las posiciones de inicio de bloque de 1476
PROVEN          sus 7 dwords cuadran EXACTAMENTE con gfx_v8_0.c:6042-6062
PROVEN          0x1537 = mmGPU_HDP_FLUSH_REQ, 0x1538 = mmGPU_HDP_FLUSH_DONE
                (bloque bif, bif_5_0_d.h:78-79)
PROVEN_DERIVED  ref_and_mask = 1 = GPU_HDP_FLUSH_DONE__CP0_MASK, por la rama
                del anillo GFX de gfx_v8_0_get_hdp_flush_mask
PROVEN          body0 = 0x143 = OPERATION(1)<<6 | FUNCTION(3) | ENGINE(1)<<8
PERFECCIONA     1476: count+2 confirmado en un paquete con nombre, con el
                septimo dword siendo un header del paquete siguiente
CORRIGE          1411 y 1441 en el alcance: sus WAIT_REG_MEM no son estos

REFUTADO, mio    leí 6 dwords de cuerpo donde hay 5, y el valor de mas
                coincidia con el campo vecino, de modo que parecia una lectura
                coherente.  Un header plausible justo despues del cuerpo es lo
                que lo delata.

NOT_DETERMINED  si el flush de VM se emite cuando el VMID cambia.  El paquete
                no esta en la captura, y eso puede ser porque no hacia falta.
```
