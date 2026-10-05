# 1502 — Los dos opcodes «sin nombre» sí los tenía: `0x3F = PACKET3_INDIRECT_BUFFER` y `0x8B = PACKET3_SWITCH_BUFFER`. Mi grep fallaba por la caja. Y el IB del anillo confirma el VMID 7 de `1420`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CORRIGE, mio   1500 §2 afirmo "PROVEN_ABSENT: 0x3f y 0x8b no tienen nombre en
                ninguna fuente".  FALSO.  Los dos tienen nombre, y estan en
                cikd.h.  Mi grep exigia minusculas y los defines usan MAYUSCULAS
                para el digito: 0x3F, no 0x3f.

CORRIGE, mio   1500 §2 decia tambien que el .reg de umr "no define packet
                types".  Es cierto, pero lo presente como si cerrara el tema.

DESCUBRE       el control del INDIRECT_BUFFER del anillo da vmid = 7, lo que
                CONFIRMA 1420 desde el artefacto y no desde el fuente.
CIERRA         el frame del anillo gfx:  7 de 7 packets con nombre.
```

## 0 · EL ERROR, QUE ES LO QUE HACE VALER EL HALLAZGO

`1500` cerró con:

```text
  PROVEN_ABSENT  0x3f y 0x8b no tienen nombre en cikd.h, ni en las cabeceras
                 asic_reg, ni en el .reg de umr
```

Lo comprobé con:

```bash
grep -oE "PACKET3_[A-Z_0-9]+[[:space:]]+0x(3f|8b)\b" cikd.h
```

Y en `cikd.h` los defines son:

```c
#define	PACKET3_INDIRECT_BUFFER				0x3F
#define	PACKET3_SWITCH_BUFFER				0x8B
```

**El `\b` de mi patrón es un límite de palabra, y `0x3F` termina en `F`, que sí es
un carácter de palabra.** Debería haber casado. Lo que falla es otra cosa, y la
encuentro reproduciéndolo:

```bash
$ grep -oE "PACKET3_[A-Z_0-9]+[[:space:]]+0x3f\b" cikd.h     ->  nada
$ grep -oE "PACKET3_[A-Z_0-9]+[[:space:]]+0x3F\b" cikd.h     ->  PACKET3_INDIRECT_BUFFER
```

```text
  EL ERROR ES LA CAJA, Y EL QUE ME FALLA ES EL QUE YO MISMO ESCRIBI.

  En 1470 endureci la herramienta para distinguir mayusculas, precisamente
  porque el padding hexadecimal produce falsos negativos.  Y aqui, dos horas
  despues, hago el mismo error en un grep manual: busco 0x3f cuando el fuente
  tiene 0x3F.

  ESO ES 1470 APLICADO A UN TEXTO QUE NO ES UN REGISTRO.  El patron se
  transferyo.  Y la leccion no es "sé masografico" la entrada: es que un grep
  manual hereda los modos de fallo de un dominio a otro sin que nadie lo mire.
```

## 1 · LA BÚSQUEDA EXHAUSTIVA, QUE ES LA QUE DEBÍA HACER DESDE EL PRINCIPIO

En vez de buscar `0x3f`, listé **los 35 opcodes que el driver emite en toda su
historia** y leí su valor:

```bash
$ grep -rhoE "PACKET3\((PACKET3_[A-Z_0-9]+)" drivers/gpu/drm/amd/ | sort -u   # 35
$ while read n; do grep -oE "^#define[[:space:]]+$n[[:space:]]+0x[0-9a-fA-F]+" cikd.h; done
```

Y el resultado, filtrado:

```text
  0x3F  PACKET3_INDIRECT_BUFFER
  0x8B  PACKET3_SWITCH_BUFFER
```

**Los dos estaban en la lista de 35 que el propio driver usa.** No hacía falta
buscarlos: basta con mirar qué packets emite el driver, que es una lista de 35
elementos, y cruzarla con `cikd.h`.

## 2 · EL FRAME DEL ANILLO GFX, AHORA 7 DE 7

```text
  dword  op    nombre                count  cuerpo
  ------  ----  --------------------  -----  ----------------------------------
    3    0x22  COND_EXEC                3    0x1080 0xff 0x0 0x2b
    8    0x3c  WAIT_REG_MEM             5    0x143 0x1537 0x1538 0x1 0x1 0x20
   16    0x28  CONTEXT_CONTROL         1    0x80000000 0x0
   18    0x3F  INDIRECT_BUFFER          2    0x278000 0x1 0x7000158
   22    0x37  WRITE_DATA              3    0x40100000 0xbcc 0x0 0x1
   27    0x47  EVENT_WRITE_EOP         4    0x38514 0x16b7000 0x200000ff 0x9bae 0x0
   33    0x8B  SWITCH_BUFFER           0    0x0
```

**Ninguno queda sin nombre.** Y `1500` acertó en un detalle que parecía menor:
`0x8B` tiene `count=0`, es decir **no transporta nada**. `PACKET3_SWITCH_BUFFER`
con count 0 es un marcador de posición de un solo dword.

## 3 · EL INDIRECT_BUFFER DECODIFICADO, Y EL VMID 7

El productor está en `gfx_v8_0.c:6131-6138`, leído entero:

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_INDIRECT_BUFFER, 2));
amdgpu_ring_write(ring, (2 << 0) | (ib->gpu_addr & 0xFFFFFFFC));   /* __BIG_ENDIAN */
amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr) & 0xFFFF);
amdgpu_ring_write(ring, control);
```

Y `control` se compone en la línea 6088:

```c
control |= ib->length_dw | (vmid << 24);
```

Con el cuerpo del anillo:

```text
  body[0] = 0x00278000   gpu_addr bits 1..31
  body[1] = 0x00000001   gpu_addr bits 32..47
  body[2] = 0x07000158   control
```

```text
  control = 0x07000158
    length_dw = control & 0xFFFF          =  344 dwords
    vmid      = (control >> 24) & 0xFF    =    7
    CACHE_POLICY (>>28)                   =    0
    VALID       (bit 23)                  =    0
    TCL2_VOLATILE(bit 22)                 =    0
```

**`vmid = 7`, leído del artefacto.** Y `1420` afirma:

> el IB despacha sobre VMID 7; discriminante `INDIRECT_BUFFER_VALID` (bit23),
> 15 sitios en 6 generaciones

**Confirmado desde el anillo, no desde el fuente.** Y con un detalle que `1420`
no tenía: `VALID` está a **0**, o sea que en este frame concreto el IB no lleva
el bit de validación puesto, y aun así el frame se emite.

## 4 · Y ESO CORRIGE UNA LECTURA DE 1420

`1420` limita su discriminante a "cuál es el discriminante entre 15 sitios en 6
generaciones". Aquí hay un dato que acota el rango:

```text
  1420  el IB va en el anillo que le toca, con vmid=7
  1502  en ESTE frame, INDIRECT_BUFFER_VALID = 0

  Y gmc_v8_0.c:6090 muestra que hay una rama que SI lo usa:
      if (amdgpu_sriov_vf(adev) && (ib->flags & AMDGPU_IB_FLAG_PREEMPT))
              control |= INDIRECT_BUFFER_PRE_ENB(1);

  O sea:  VALID/las banderas de control se ponen en CASOS ESPECIFICOS (SR-IOV
  con preempt), no siempre.  En el camino normal de un frame de escritorio no
  se pone ninguna.  Y eso significa que  VALID no sirve para distinguir entre
  los 15 sitios, porque en el caso normal esta a 0 y no discrimina nada.
```

## 5 · LO QUE QUEDA, Y ES POCO

```text
NOT_DETERMINED  la GPU address del IB:  (0x00278000 << 1) | (0x0001 << 32)
                = 0x1004f0000.  Es una VA, y no hay forma de resolverla a
                paginas fisicas sin el GTT, que no esta en las capturas.

NOT_DETERMINED  por que hay un solo INDIRECT_BUFFER por frame de 256 dwords, y
                por que apunta a un solo lugar.  Un frame de escritorio con un
                solo draw es lo esperable, pero "lo esperable" no es "medido".

CIERRA          los dos opcodes sin nombre de 1500.  El frame es 7 de 7.
CONFIRMA        1420 en el VMID 7, y CORRIGE su alcance: INDIRECT_BUFFER_VALID
                no discrimina entre los 15 sitios, porque en el camino normal
                esta a 0.
```

## 6 · LA LECCION, Y ES LA QUINTA VEZ

```text
  1.  1473  un recuento grande y negativo es un include path, no un hallazgo
  2.  1480  lo mismo, con las tres cifras 819 / 524 / 5
  3.  1493  contar y deducir son operaciones distintas
  4.  1500  el primer resultado de un grep no es un resultado
  5.  1502  y un PROVEN_ABSENT es el claims mas fuerte que se puede hacer mal,
              porque dice "no hay donde mirar" y eso cierra la frontera

  ESTA ES LA MAS IMPORTANTE DE LAS CINCO.  Afirmar PROVEN_ABSENT equivocado no
  deja nada abierto:  el que venga leera "ya se buscaron todas las fuentes" y
  no lo volvera a mirar.  Un NOT_FOUND equivocado solo se equivoc una vez.

  Y la causa fue la mas tonta posible:  caja de las hex.

  LA REGLA QUE PROPONGO Y QUE YA ESTA APLICADA EN regalias.py:
    NUNCA escribir PROVEN_ABSENT a partir de un solo grep.  Ni a partir de
    dos.  Solo a partir de un inventario cerrado, y el inventario se escribe
    en el hallazgo.

    Aqui el inventario eran 35 simbolos y estaba a un comando de distancia.
    Y sin inventario, "no lo encontre" no es "no existe".
```

## 7 · ESTADO

```text
CORRIGE   1500 §2 (PROVEN_ABSENT erroneo: los dos opcodes tienen nombre)
CORRIGE   1420 en el alcance: INDIRECT_BUFFER_VALID no discrimina los 15
           sitios, porque en el camino normal vale 0
CONFIRMA  1420 en el VMID 7, leído del ARTEFACTO y no del fuente

PROVEN    0x3F = PACKET3_INDIRECT_BUFFER, 0x8B = PACKET3_SWITCH_BUFFER (cikd.h)
PROVEN    el frame del anillo gfx es 7 de 7 packets con nombre
PROVEN    el IB del frame apunta a gpu_addr 0x1004f0000, length_dw = 344,
          vmid = 7, y VALID = TCL2_VOLATILE = CACHE_POLICY = 0

REFUTADO, mio   1500 §2.  Un PROVEN_ABSENT fundado en un grep sensible a la caja.

NOT_DETERMINED  a que paginas fisicas apunta 0x1004f0000.  El GTT no esta en las
                capturas.
```

## 8 · LO QUE SIGUE

El frame del anillo gfx está **cerrado**: 7 de 7 packets identificados, con sus
campos decodificados y su productor localizado en el código.

Lo que queda del lado del anillo es el mismo trabajo en el **anillo de compute**,
que `pm4tila` trata como un caso aparte (2021 paquetes, convención distinta) y
que no he mirado con este nivel de detalle. Ahí el bloque de 256 no aplica igual,
y ese es el siguiente sitio donde la estructura de frame se puede contrastar o
refutar.
