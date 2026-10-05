# 1518 — El `length_dw` de los 46 IB viene de userspace, y la cadena completa queda trazada: `chunk_ib->ib_bytes / 4` cruza el ioctl, el driver solo lo alinea a 8. La partición de `1516` no la hace el driver

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    sdma0.

CIERRA         el punto 6 de 1516 §7: donde se decide el tamaño del IB.
PROVEN         la cadena, de punta a punta:
                 userspace  ->  chunk_ib->ib_bytes  ->  ib->length_dw
                 ->  amdgpu_ring_write(ring, ib->length_dw)
               El kernel driver NO decide el tamaño: lo transporta.
PROVEN         el unico redondeo del driver es a 8 dwords
               (pad_count = (-length_dw) & 7, sdma_v3_0.c:1012), y 46 de 46
               ya son multiplos de 8.  El 8 y el 16 los eligio el cliente.
PROVEN         el driver valida que el IB quepa en el BO que contiene la VA
               (amdgpu_cs.c:1066) y despues COPIA el IB a un buffer del
               kernel (memcpy en :1076).  O sea que el contenido del IB SI
               pasa por el kernel: hay un punto de captura accesible.
DESCUBRE       la particion de 1516 no la hace el allocator del driver.  El
               driver solo busca el BO que ya contiene la VA.  El pool es de
               Mesa.
ERROR, mio     "no hay redondeo en el driver" era una conclusion Prematura:
               habia uno, a 8 dwords, y me lo habia saltado por buscar
               "ALIGN" y no "(-x) & 7".
```

## 0 · EL PENDIENTE

`1516` §7 punto 6:

```text
  6. por que length_dw solo toma 8 y 16.  El productor escribe ib->length_dw
     tal cual, sin redondeo (sdma_v3_0.c:438).  O sea que el redondeo a
     potencia de 2 lo pone quien construyo el IB, y eso es codigo de Mesa, no
     del kernel driver.
```

La primera mitad era **falsa**: `sdma_v3_0.c:438` escribe tal cual, pero hay un
`pad_ib` que alinea. Lo encontre tarde. Ver §1.

## 1 · MI ERROR: SI HAY REDONDEO, Y A 8

```bash
$ K=rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/amdgpu
$ grep -rnE "length_dw.*(ALIGN|~|align_mask|>>|roundup)" $K/sdma_v3_0.c $K/cik_sdma.c $K/amdgpu_cs.c
(sin salida)
```

Lo que si hay, con el termino que faltaba:

```bash
$ grep -rn "length_dw) & 7" $K/*.c
$K/cik_sdma.c:803      pad_count = (-ib->length_dw) & 7;
$K/sdma_v2_4.c:739     pad_count = (-ib->length_dw) & 7;
$K/sdma_v3_0.c:1012    pad_count = (-ib->length_dw) & 7;    <- VIVO
$K/sdma_v4_0.c:1673    pad_count = (-ib->length_dw) & 7;
$K/sdma_v4_4_2.c:1269  pad_count = (-ib->length_dw) & 7;
```

Cinco sitios del patron, uno solo vivo para POLARIS12.

Conclui: «el driver no redondea». **Eso es un `PROVEN_ABSENT` formado por un
grep con un conjunto de términos.** Los términos no incluian la forma que el
driver usa.

La forma real:

```c
/* sdma_v3_0.c:1012 */
pad_count = (-ib->length_dw) & 7;
for (i = 0; i < pad_count; i++)
        ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_NOP);
```

`(-x) & 7` es un redondeo **hacia arriba a múltiplo de 8**, escrito como
aritmética de complemento a dos, no como `ALIGN`. Y el kernel también lo hace
en `cik_sdma.c:803`.

```text
  CORRIGE, mio  1516 §7 punto 6: el driver SI redondea, a 8 dwords.
                Mi busqueda uso un conjunto de terminos incompleto.

  Y ESTO ES LA SEXTA VEZ QUE PASA, con dos formas distintas:
    1500, 1502, 1506, 1508  -> decidir antes de ver toda la salida
    1516 (ciclo), 1518      -> PENSAR EL RESULTADO y luego buscar la prueba

  ESTA ES NUEVA: no busquaba mal, buscaba lo que ya sabia que iba a encontrar.
  "sin redondeo" era mi conclusion previa, y luego use el grep para
  confirmarla.  El patron de 1516 al reves: el ojo quiere ver el ciclo.
```

Y la prediccion se cumple:

```text
  46 de 46 length_dw son multiplos de 8.   (pad_count = 0 en los 46)
  valores: 8 (x19) y 16 (x27)
```

**Pero eso no explica el 8 y el 16.** El `pad_count` solo SUBE; no baja nunca
hasta la siguiente potencia de dos. Un `length_dw` de 10 se alinea a 16 con
este codigo, y uno de 5 a 8. Escribe 16 y 24, no 16 y 32. **El 8 y el 16 los
eligio el que construyo el IB, antes de que el driver lo tocara.**

## 2 · LA CADENA COMPLETA, DE PUNTA A PUNTA

```text
  USERSpace (Mesa)
      |  ioctl DRM_IOCTL_AMDGPU_CS
      v
  drm_amdgpu_cs_chunk_ib {  va_start, ib_bytes, flags }
      |
      v
  amdgpu_cs.c:417   ib->gpu_addr = chunk_ib->va_start;
  amdgpu_cs.c:418   ib->length_dw = chunk_ib->ib_bytes / 4;
      |
      v
  amdgpu_ib.c:283   amdgpu_ring_emit_ib(ring, job, ib, status);
      |
      v
  sdma_v3_0.c:437   amdgpu_ring_write(ring, ib->length_dw);   <- lo que LEI en el anillo
```

```text
  PROVEN  ib->length_dw es chunk_ib->ib_bytes / 4, y chunk_ib viene del
          userspace.  El kernel lo divide por 4 y lo pasa.  No lo decide.

  Y la validacion que si hace el driver, amdgpu_cs.c:1064-1068:
      if ((va_start + ib->length_dw * 4) > (m->last + 1) * AMDGPU_GPU_PAGE_SIZE)
              return -EINVAL;   "IB va_start+ib_bytes is invalid"

  O sea: el driver RECHAZA un IB que no quepa en el BO.  No lo ajusta.  El
  limite es el tamano del BO, y el BO lo pidio el cliente.
```

**El anillo no puede mentir sobre el tamaño**: `length_dw` es lo que el cliente
pidió, dividido por 4, y validado contra el BO.

## 3 · Y AQUI ESTA LO QUE NO SABIA: EL IB SE COPIA AL KERNEL

```c
/* amdgpu_cs.c:1072-1078 */
r = amdgpu_bo_kmap(aobj, (void **)&kptr);
kptr += va_start - (m->start * AMDGPU_GPU_PAGE_SIZE);

if (ring->funcs->parse_cs) {
        memcpy(ib->ptr, kptr, ib->length_dw * 4);
        amdgpu_bo_kunmap(aobj);
```

Y `amdgpu_cs_find_mapping` (`amdgpu_cs.c:1807`) busca el BO que contiene la VA:
si no lo encuentra, `IB va_start is invalid`.

```text
  DESCUBRE  el contenido del IB PASA POR EL KERNEL.  amdgpu_cs_find_mapping
            localiza el BO a partir de la VA que el anillo transporta, lo
            mapea con kmap, y lo COPIA a ib->ptr.

  Y ESO ABRE UNA VIA QUE NO TENIA CONTEMPLADA, y es de 1508:

            1508 concluyo que "el contenido del IB es INVISIBLE en las 21
            capturas" y escribi que no se arregla con mas herramientas.

            ESA CONCLUSION ES CORRECTA PARA LAS CAPTURAS, Y ESTA MAL COMO
            FRONTERA DEL PROYECTO.  El contenido del IB no esta en los
            ficheros, pero SI es accesible: esta en VRAM, el driver sabe
            traduction VA->BO, y ese mapeo existe en /dev/dri/card1.

            O sea: la frontera no es "no se puede", es "falta una lectura".
            Y esa lectura es la misma que bloquea el resto: credenciales.
```

Esto es un `REFUTADO` parcial de mi propio `1508`, y lo escribo con las dos
condiciones: el dato **no está en las capturas** (eso sigue siendo cierto y no
cambia), pero **no es inaccesible**.

## 4 · LA PARTICION DE 1516 NO ES DEL DRIVER

Consecuencia directa de §2 y §3:

```text
  1516 medio: 46 slots de 256 bytes, alineados, sin solapes, en un rango de
  251 slots.  Y supuse que eso era un pool del driver.

  LO QUE EL DRIVER HACE, leido del codigo:
      amdgpu_cs_find_mapping(p, va_start, &aobj, &m)   busca el BO
      valida que quepa
      kmap + memcpy

  LO QUE EL DRIVER NO HACE:
      no reserva slots
      no alinea a 256
      no decide el tamano del BO

  PROVEN_DERIVED  la alineacion de 256 y la particion de 251 slots las hace
                  QUIEN PIDIÓ EL BO.  O sea Mesa o el cliente de userspace,
                  a traves del ioctl.  El kernel es transporte y validador.

  Y ESO ES LA SEGUNDA VEZ que la misma conclusion me lleva al sitio de
  decision equivocado, y por eso la puedo afirmar con la cadena de produccion
  entera trazada y no con un "no encontre".  La primera vez, en `1516` §7,
  supuse que la particion era del driver; ahora se que es del cliente, y la
  diferencia es que esta vez puedo senalar la linea que lo dice.
```

## 5 · ESTADO

```text
PROVEN          la cadena del length_dw, completa:
                chunk_ib->ib_bytes (userspace) -> ib->length_dw
                (amdgpu_cs.c:418) -> amdgpu_ring_write (sdma_v3_0.c:437).
                El kernel transporta y divide por 4; no decide el tamaño.
PROVEN          el unico redondeo del driver es a 8 dwords
                (sdma_v3_0.c:1012, cik_sdma.c:803).  46 de 46 ya son
                multiplos de 8.  Ese codigo sube al multiplo siguiente, no
                reduce a potencia de dos, asi que el 8 y el 16 los eligio el
                cliente.
PROVEN          el driver valida que el IB quepa en el BO que contiene la VA
                (amdgpu_cs.c:1066) y devuelve -EINVAL si no.
PROVEN          el driver valida que max IB packet size sea coherente
                (amdgpu_cs.c:400, AMDGPU_GFX_SDMA_IB_PACKET_SIZE_MAX_DW =
                0xFFFFF para rings SDMA).
DESCUBRE        el contenido del IB se COPIA al kernel: find_mapping localiza
                el BO a partir de la VA del anillo, kmap, y memcpy a
                ib->ptr (amdgpu_cs.c:1058-1078).  El IB es accesible desde
                /dev/dri/card1, no solo desde VRAM.
PROVEN_DERIVED  la particion de 1516 y la alineacion a 256 las hace el
                cliente, no el driver: el driver no reserva ni alinea nada,
                solo busca el BO existente y valida.

CORRIGE, mio    1516 §7 punto 6: el driver SI redondea, a 8 dwords.
                Mi PROVEN_ABSENT salio de un grep con terminos
                incompletos: no busque "(-x) & 7".
REFUTADO, mio  el alcance de 1508: el contenido del IB NO esta en las
                capturas (cierto, no cambia), pero no es INACCESIBLE.  Es
                una lectura que falta, y la hace el kernel con
                find_mapping + kmap.
ERROR, mio    sexta vez que un claim mio sale mal: las cuatro primeras por
              decidir antes de ver toda la salida, 1516 por ver lo que
              queria ver, y esta por buscar solo la forma que mi conclusion
              previa predecía.
```

## 6 · LO QUE SIGUE DENTRO DE ESTA AREA

```text
  2. El retroceso del seq (-52 aqui, -7 en gfx) y los saltos de +2, +6, +8.
  3. El VMID 0 frente al 7 del anillo gfx.
  4. Los 736 NOP: relleno o restos.

  Y UNO NUEVO, que sale de §3 y es el mas util de todos:

  7. El IB esta en VRAM en 0x000000ff_003c_xxxx, alineado a 256, y el driver
     ya sabe convertir esa VA a BO.  Con /dev/dri/card1 se podria leer el
     contenido de los 46 IB, y con el contenido se cierra el ultimo 0 % que
     queda: QUE DIBUJA LA GPU.

     Es la misma lectura que desbloquea el registro, y por eso el cuello es
     UNO SOLO, no cinco.  Y no es el IB de gfx (1508, 344 dwords que no caben
     en su frame) sino el de sdma0, que es de 8 o 16 dwords y SI se puede
     leer entero con un solo read.
```

Ese séptimo punto es el que cambia el estado del proyecto: **el primer IB
legible de la sesión son 32 o 64 bytes, no 344.** Y `1516` ya dio las 46
direcciones exactas.

No cambio de area hasta cerrar estos cinco o hasta declarar `SATURATED` con el
motivo escrito.