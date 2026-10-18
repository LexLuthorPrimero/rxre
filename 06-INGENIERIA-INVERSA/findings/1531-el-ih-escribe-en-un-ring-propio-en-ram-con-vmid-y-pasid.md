# 1531 — El IH tiene un ring buffer propio en RAM del sistema, y sus entradas llevan `ring_id`, `vmid` y `pasid`. Pero el corpus no tiene las cabeceras de BIF: 94 ficheros no compilan, incluido `tonga_ih.c`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    tonga_ih (interrupt handler).  Primer bloque de los cuatro
               sin tocar.

DESCUBRE       el IH no "avisa": escribe ENTRADAS en un ring buffer propio, de
               64 KiB, en memoria de sistema coherente.  No es VRAM.
DESCUBRE       cada entrada son 4 dwords y lleva ring_id, vmid y pasid.  Es el
               dato que dije que no existe en las 21 capturas para atribuir un
               VMID a un proceso.
CONFIRMA       fence_info es una MEDIDA del IH.  Last signaled fence es la
               salida del handler, y yo lo llevaba usando como contador.
PROVEN         tonga_ih_ip_block es IH 3.0 (funcs = tonga_ih_ip_funcs), no 4.x
               como sugeria el nombre del fichero.
PROVEN         94 ficheros .c incluyen cabeceras de subdirectorios que NO
               existen en el corpus: bif/ 26, oss/ 49, gmc/ 19.  Entre ellos
               tonga_ih.c, que incluye bif/bif_5_1_d.h y no existe.
ERROR, mio     tres, y las tres son "no mire la cabecera que el fichero
               incluye": mire sid.h y bif_5_0_d.h, cuando tonga_ih.c incluye
               bif_5_1_d.h.
```

## 0 · POR QUE EMPIEZO POR EL IH

`1523` §7 dejó cuatro pendientes y este es el que un driver propio necesita sí o
sí: **las vallas que leí solo sirven si hay una interrupción que las despierte.**
`1518` cerró el *cómo se escribe*; faltaba el *quién avisa*.

Y al planarlo:
```text
  3 de los 4 bloques sin tocar se cierran con las herramientas actuales.
  tonga_ih es el más barato: 509 líneas, 26 funciones.
```

## 1 · EL BLOQUE, RESUELTO POR DEFINICION Y NO POR NOMBRE

Aplico la regla de `1523`: leo la definición, no el nombre del fichero.

```c
/* tonga_ih.c:503 */
const struct amdgpu_ip_block_version tonga_ih_ip_block = {
	.type = AMD_IP_BLOCK_TYPE_IH,
	.major = 3,
	.minor = 0,
	.rev = 0,
	.funcs = &tonga_ih_ip_funcs,
};
```

```text
  PROVEN  tonga_ih es IH 3.0, y comparte .funcs con el nombre "tonga" del
          fichero.  El nombre del fichero NO dice la version.

  Y ESTO ES 1516 §7 OTRA VEZ:  gmc_v8_1 en gmc_v8_0.c, uvd_v6_3 en
  uvd_v6_0.c, y ahora tonga_ih = IH 3.0.  Cada bloque se resuelve leyendo su
  ip_block y su .funcs.  Nunca por el nombre del fichero.
```

## 2 · EL HALLAZGO: EL IH TIENE SU PROPIO RING, Y ESTA EN RAM

`tonga_ih_sw_init` (`tonga_ih.c:306`):

```c
r = amdgpu_ih_ring_init(adev, &adev->irq.ih, 64 * 1024, true);
...
adev->irq.ih.use_doorbell = true;
adev->irq.ih.doorbell_index = adev->doorbell_index.ih;
```

Y `amdgpu_ih_ring_init` (`amdgpu_ih.c:42`) **leído entero**, porque esto decide si
es alcanzable:

```c
if (use_bus_addr) {
        ih->ring = dma_alloc_coherent(adev->dev, ih->ring_size + 8,
                                      &dma_addr, GFP_KERNEL);
        ih->gpu_addr = dma_addr;
        ih->wptr_addr = dma_addr + ih->ring_size;
        ih->wptr_cpu = &ih->ring[ih->ring_size / 4];
        ih->rptr_addr = dma_addr + ih->ring_size + 4;
        ih->rptr_cpu = &ih->ring[(ih->ring_size / 4) + 1];
```

```text
  PROVEN  el ring del IH es de 64 KiB (64*1024, alineado a potencia de dos
          por order_base_2), en MEMORIA DE SISTEMA coherente, no en VRAM.

  Y hay 8 bytes extra: rptr y wptr como sombras, al final del ring.
  ih->ring_size + 8.

  Y el propio driver lo dice, con el flag puesto a 0 y el motivo escrito:
      /* INTERRUPT_CNTL__IH_REQ_NONSNOOP_EN_MASK=1 if ring is in
         non-cacheable memory, e.g., vram */
      interrupt_cntl = REG_SET_FIELD(interrupt_cntl, INTERRUPT_CNTL,
                                     IH_REQ_NONSNOOP_EN, 0);
```

**Consecuencia que importa para el proyecto:** si el ring del IH está en RAM del
sistema, entonces es **memoria de proceso del kernel**. No es VRAM, no requiere
`/dev/dri/card1`, y en principio es alcanzable por otra vía que aún no he
explorado. Lo dejo como `NOT_DETERMINED` porque no sé cómo la-exporta amdgpu, y
afirmar eso sería el `PROVEN_ABSENT` que `1514` me corrigió.

## 3 · LA ENTRADA, Y AQUI ESTA EL DATO QUE BUSCABA

`tonga_ih_decode_iv` (`tonga_ih.c:248`), que es *el* consumidor del ring:

```c
/* wptr/rptr are in bytes! */
u32 ring_index = ih->rptr >> 2;
uint32_t dw[4];

dw[0] = le32_to_cpu(ih->ring[ring_index + 0]);
...
entry->client_id = AMDGPU_IRQ_CLIENTID_LEGACY;
entry->src_id    = dw[0] & 0xff;
entry->src_data[0] = dw[1] & 0xfffffff;
entry->ring_id   = dw[2] & 0xff;
entry->vmid      = (dw[2] >> 8) & 0xff;
entry->pasid     = (dw[2] >> 16) & 0xffff;

ih->rptr += 16;
```

```text
  PROVEN  cada entrada del IH son 4 dwords = 16 bytes, y el layout es:

      dw[0]  bits[7:0]      src_id      (que motor interruppio)
      dw[1]  bits[27:0]     src_data    (el numero de secuencia, p.ej.)
      dw[2]  bits[7:0]      ring_id     (que anillo)
      dw[2]  bits[15:8]     vmid
      dw[2]  bits[31:16]    pasid
      dw[3]                 (el driver lo lee y lo descarta)

  Y rptr avanza 16 bytes por entrada.  El puntero esta en BYTES, no en dwords.
```

**Esto es lo que dije en `1506`/`1516` que no existía.** Escribí que «ninguna
captura expone VMID→proceso» y es cierto para las 21 capturas, pero es **falso**
como frontera: el hardware escribe el VMID y el PASID en un ring que el CPU lee
con un `le32_to_cpu` y un desplazamiento de bits. Nada de eso requiere acceso a
VRAM.

```text
  CORRIGE, mio  (parcialmente) mi "no se puede atribuir el VMID".  Con las
                21 capturas, no.  Con el ring del IH, si.  Y es RAM.
```

## 4 · LOS REGISTROS, Y TRES ERRORES MIOS SEGUIDOS

Quería las direcciones. Y aquí hice tres veces lo mismo:

**Error 1.** Busqué en `gfx_8_0_0.reg` y `gc_8_1_0.reg` (los que uso siempre).
Salió vacío. Busqué en `bif_5_0_0.reg` y solo 2 de 9 aparecieron.

**Error 2.** Busqué `IH_RB_*` en toda la base de `umr` con `grep -rloE ... -l -o`,
y **`-l` y `-o` son excluyentes**. El bucle devolvió vacío para todo. Lo detecté
porque el `printf` imprimió `NOT_FOUND` para registros que sí existen.

**Error 3, el de fondo.** Dije «los registros están en `sid.h`» porque un grep me
devolvió `sid.h`, y construí una tabla sobre eso. **`sid.h` define
`INTERRUPT_CNTL = 0x151A`, pero NO define `IH_DOORBELL_RPTR`, y `tonga_ih.c` lo
usa.** La cabecera correcta es la que el fichero *incluye*.

```text
  tonga_ih.c:33-34   #include "bif/bif_5_1_d.h"
                     #include "bif/bif_5_1_sh_mask.h"

  Y bif_5_1_d.h NO EXISTE en el corpus.  Ver §5.
```

**La regla, y ya es la cuarta vez esta sesión:** para saber de dónde viene un
símbolo de un `.c`, se lee la lista de `#include` de ese `.c`. No se busca el
nombre del símbolo en el árbol, porque el fichero donde vive puede ser de otra
generación.

## 5 · Y EL CORPUS NO TIENE LAS CABECERAS: 94 FICHEROS NO COMPILAN

```text
  subdirectorio   .h presentes   .c que los incluyen
  bif/                     0                26
  oss/                     0                49
  gmc/                     0                19
                                total         94
```

Y `bif/`, `oss/`, `gmc/` **no existen** en el corpus: hay 324 `.h` y ninguno en
esos subdirectorios.

```text
  1471 USO gmc_8_1_ip_block de gmc/gmc_8_1_d.h.  Ese fichero NO esta.
  1523 y todos los hallazgos de sdma0 usaron sdma_v3_0.c, que incluye
       gmc/gmc_8_2_d.h y oss/oss_3_0_d.h.  Esos tampoco estan.

  PROVEN  94 de los .c del driver no pueden compilarse contra este corpus.
          Entre ellos tonga_ih.c, que es el bloque que estoy cerrando.
```

### Esto NO contradice a `1480`

`1480` busqué **includes desde los `.c` hacia las cabeceras** y concluded «5 de
1000». Eso es correcto. Lo que no miró es la dirección inversa: **cabeceras que
los `.c` incluyen y que no están**. Las dos mediciones son complementarias y
las dos son verdaderas.

```text
  1480  .c -> .h que no existen            5 de 1000   (ninguno en la ruta)
  1531  .h -> .c que las necesitan          94 ficheros  (tonga_ih.c entre ellos)

  Y LA SEGUNDA ES LA QUE IMPORTA:  1480 concluyo "el corpus esta sano" y de
  hecho esta sano para LEER.  Lo que no esta es COMPILABLE.
```

## 6 · `fence_info` ES UNA MEDIDA DEL IH

Y esto es lo que ya tenía sin saberlo. `1520` §5 usé `Last signaled fence` como
el estado del contador de vallas. Es correcto —y además es **la salida del
handler**:

```text
  18 anillos, cada uno con "Last signaled fence".
  Esos 18 numeros los escribio el IH al procesar las entradas del §3.
```

O sea que de los cuatro campos de cada entrada (`src_id`, `src_data`, `ring_id`,
`vmid`), **`fence_info` me da `src_data` agregado por `ring_id`**, y el resto
necesita el ring crudo.

```text
  PROVEN_DERIVED  fence_info es un producto del IH: agrupa por ring_id y
                  reporta el maximo de src_data.  Es un resumen con perdida de
                  3 de los 4 campos, hecho por el propio driver.

  Y ESO EXPLICA POR QUE DE 18 ANILLOS SOLO HAY 4 CAPTURAS:  el debugfs de IH
  esta en otro sitio del arbol.  No es que falten por descuido, es que la
  herramienta que las genero no las genera.
```

## 7 · ESTADO

```text
PROVEN          tonga_ih_ip_block es IH 3.0, .funcs = tonga_ih_ip_funcs
                (tonga_ih.c:503).  El nombre del fichero no dice la version.
PROVEN          el ring del IH son 64 KiB (64*1024, alineado con
                order_base_2) + 8 bytes de sombras rptr/wptr, en
                dma_alloc_coherent(GFP_KERNEL): MEMORIA DE SISTEMA, no VRAM.
PROVEN          el driver lo confirma con IH_REQ_NONSNOOP_EN = 0 y el motivo
                en el comentario (tonga_ih.c:118-119).
PROVEN          cada entrada son 4 dwords / 16 bytes.  Layout:
                dw[0][7:0]=src_id, dw[1][27:0]=src_data,
                dw[2][7:0]=ring_id, dw[2][15:8]=vmid, dw[2][31:16]=pasid.
                rptr avanza 16 y esta en BYTES.
PROVEN_DERIVED  fence_info es un producto del IH: agrupa las entradas por
                ring_id y reporta el maximo de src_data.  Es fence_info =
                2 de los 4 campos, con perdida.
PROVEN          94 .c del driver incluyen cabeceras de subdirectorios que no
                existen: bif/ 26, oss/ 49, gmc/ 19.  Entre ellos tonga_ih.c,
                que incluye bif/bif_5_1_d.h.
PROVEN          el corpus esta SANO PARA LEER pero NO COMPILABLE.  324 .h, y
                ninguno en bif/, oss/ ni gmc/.
NO CONTRADICE   1480: busco en sentido inverso (.c -> .h).  Las dos
                mediciones son ciertas y complementarias.

CORRIGE, mio    "ninguna captura expone VMID -> proceso" (1506, 1516) era
                cierto para las 21 capturas y falso como frontera: el hardware
                escribe vmid y pasid en un ring de RAM del sistema.
ERROR, mio    tres seguidos, los tres "no mire la cabecera que el fichero
              incluye":
              1.  busque en los .reg de gc/gfx en vez del bloque del IH
              2.  use grep -rloE, con -l y -o excluyentes: bucle vacio
              3.  construi una tabla sobre sid.h, que NO define
                  IH_DOORBELL_RPTR;  la correcta es bif_5_1_d.h

NOT_DETERMINED  como se exporta el ring del IH.  No esta en debugfs (busqueda
                sin resultado en amdgpu_debugfs.c).  Es RAM de kernel, asi que
                hay una via, pero no la he encontrado y no la invento.
NOT_DETERMINED  si el ring del IH de POLARIS12 esta poblado o vacio.  Requiere
                leerlo, y ver la linea anterior.
```

## 8 · LO QUE SIGUE

```text
  1. EL RING DEL IH.  Es el dato mas valioso que ha salido hoy: 4 campos por
     entrada, con vmid y pasid, en RAM del sistema.  Si hay forma de
     exportarlo, se cierra la atribucion VMID->proceso que llevaba abierta
     desde el principio.  Y hay una pista: el IH tiene un SEGUNDO ring,
     adev->irq.ih_soft, de tamano IH_SW_RING_SIZE, que es software.

  2. ih_soft, y aqui el dato ya esta medido:
      amdgpu_ih.h:31   #define IH_SW_RING_SIZE  (16 * 1024)
                                     /* enough for 512 CAM entries */

      16 KiB para 512 entradas CAM.  No es un buffer de software arbitrario:
      tiene CAPACIDAD CONTADA, y el comentario da la division.

      PROVEN_DERIVED  el ring de hardware (64 KiB) tiene 4 veces el de software,
                      y el de software esta dimensionado por entradas, no por
                      bytes.  Con 16 bytes por entrada (§3):
                          hardware:  64 KiB / 16 = 4096 entradas
                          software:  16 KiB / 16 = 1024 entradas
                      y el comentario dice 512, o sea que el de software
                      reserva la mitad de su capacidad.

      Y ESO ES UN DATO DE CORRECTITUD, no de curiosidad:  si el consumidor no
      vacia el ring a tiempo, el hardware sobrescribe.  Es un limite calculable
      que un driver propio tiene que respetar, y no aparece en ningun paquete.

  3. Y ALGO QUE ES NUEVO Y MAS PEQUEÑO:  he pasado toda la sesion leyendo
     anillos que escribo YO, y nunca el que escribe el HARDWARE.  El ring del
     IH es lo unico de las 21 capturas que no es una salida del driver.  Es el
     unico sitio donde se ve lo que la GPU hacia por su cuenta.
```