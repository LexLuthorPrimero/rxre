# 1560 — Los offsets reales del ring del IH salen del BTF del módulo que está cargado. `ih_regs.ih_rb_base` está en `adev+90680`, y con eso el bloqueo de `1534` pasa de "no existe ruta" a "solo falta adev"

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA         1556 §6:  "con las 134 cabeceras tendria los offsets".
               Y lo cierra AL REVES de lo que 1556 prometio:  las cabeceras
               NO dan offsets.  El BTF del modulo cargado, si.
TRANSFORMA     1534 §"PROVEN_ABSENT: el ring del IH no se exporta".  De eso
               queda UN hueco, con nombre:  la direccion base de adev.
PROVEN         271 structs de amdgpu con layout en bytes, leidas del .BTF del
               amdgpu.ko que esta CARGADO, sin root y sin debugfs.
CORRIGE, mio   este fichero decia 140.  Era un artefacto de pahole -C con listas
               largas:  con 279 nombres devuelve 143.  Ver §2 bis.
PROVEN         la cadena de offsets del IH es COMPLETA y CERRADA:
               adev+90680 = ih_regs.ih_rb_base, el valor del registro
               IH_RB_BASE del hardware, guardado por el driver en RAM.
ERROR, mio     uno, y es el que casi me hace perderlo:  lei el .ko.ZST con
               readelf (0 secciones debug) y sali con "el modulo no
               tiene debug info".  No lo tiene en DWARF, pero SI tiene .BTF.
               Sin descomprimir jamas lo habria visto.
```

## 0 · LA PROMESA, Y POR QUÉ NO SE CUMPLE TAL CUAL

`1556` §6, textual:

```text
  no leer mas .c del corpus, sino traer el otro mitad del arbol.  Con
  include/drm/ y el kernel tendria los offsets de struct, que es lo que
  falta para que un driver propio en C sea mas que esqueleto.
```

Eso es **falso**, y está medido:

```text
  642  includes con <> en los .c
  642  resuelven contra /usr/src/kernels/7.2.9-200.nobara.fc44.x86_64
  100,00 %

  Y de los dos problemas que 1556 decia:
      las cabeceras de kernel/DRM   RESUELTAS al 100 %   (era lo mas facil)
      los OFFSETS DE STRUCT         NO.  Una cabecera es texto:  te dice el
                                     nombre del campo, su tipo y su orden.  El
                                     OFFSET EN BYTES lo decide el COMPILADOR,
                                     con el relleno, la alineacion y el
                                     anidamiento.  Y ahi estan los 2096 bytes
                                     de struct amdgpu_irq, no en la cabecera.
```

**Las cabeceras dan la semántica; el BTF da los bytes.** Y el BTF del driver
que corre está en el `.ko` que el sistema ya tiene en disco.

## 1 · CÓMO SE LLEGA AL BTF DEL MÓDULO, Y MI ERROR

```bash
$ M=/lib/modules/$(uname -r)/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
$ readelf -S $M | grep -iE "debug|btf"
(sin salida)

$ readelf -S $M | grep -c debug_info
0
```

Ahí estuve a punto de escribir que el módulo no tiene información de tipos. **Es
falso**: `readelf` no lee dentro de un `.zst`. Descomprimido:

```bash
$ zstd -d -o amdgpu.ko $M            # 37 713 670 bytes
$ readelf -S amdgpu.ko | grep -iE "debug|btf"
    [85] .BTF              PROGBITS   ...  0000 02f5bbc
  debug_info:  0
  .BTF:        1
```

```text
  CORRIGE, mio  el modulo no tiene DWARF (.debug_info = 0) pero SI tiene BTF
               (.BTF, 3 104 956 bytes).  Los dos son formatos de tipo
               distintos y mi grep solo buscaba uno.  Es el doble fallo de
               1518 por un lado:  probe un solo patron de lo que quiero ver.
```

Y `pahole` directo sobre el `.ko` falla:

```bash
$ pahole -C amdgpu_irq_src amdgpu.ko
libbpf: Malformed BTF string section, did you forget to provide base BTF?
```

**Es BTF partido (split BTF)**: el módulo no lleva la tabla de strings completa,
la hereda de `vmlinux`. Y la opción existe:

```bash
$ pahole --help | grep btf_base
      --btf_base=PATH        Path to the base BTF file

$ pahole --btf_base=/sys/kernel/btf/vmlinux -C amdgpu_irq_src amdgpu.ko
struct amdgpu_irq_src {
        unsigned int               num_types;            /*     0     4 */
        atomic_t *                 enabled_types;        /*     8     8 */
        const struct amdgpu_irq_src_funcs  * funcs;      /*    16     8 */
        /* size: 24, cachelines: 1, members: 3 */
};
```

```text
  PROVEN  con vmlinux como base, el BTF del modulo da layout en bytes.

  Y OJO QUE ESTO ES LA DOCENA VEZ con "no mire como se usa el instrumento":
  probe el instrumento (pahole) sin leer su ayuda (--btf_base).  Dos
  minutos de "no funciona" por no leer el --help.
```

## 2 · EL ALCANCE: 271 DE 279

```bash
$ grep -ohE "^struct amdgpu_[a-z0-9_]+ \{" amdgpu/*.h | sed 's/^struct //;s/ {//' | sort -u > hdr
279
$ while read s; do
    pahole --btf_base=/sys/kernel/btf/vmlinux -C $s amdgpu.ko | grep -q "^struct $s {" && echo $s >> ok
  done < hdr
271 de 279
```

```text
  PROVEN  271 de las 279 structs de amdgpu definidas en las cabeceras estan en
          el BTF del modulo cargado, con layout en bytes completo.
          El corpus da los NOMBRES; el BTF da los BYTES.  Los dos juntos.

  LAS 8 QUE NO ESTAN, inventario cerrado:

    amdgpu_mes_ctx_data          amdgpu_mes_ctx_meta_data
    amdgpu_mes_gang              amdgpu_mes_gang_properties
    amdgpu_mes_queue             amdgpu_mes_queue_properties
    amdgpu_mst_connector         amdgpu_wb_slot

  Y CADA UNA ESTA FUERA POR UNA RAZON CONCRETA:
      las 6 amdgpu_mes_*   son de MES, el microcontrolador de Arcturus/MI300.
                            No hay Arcturus en esta placa.
      amdgpu_mst_connector  es de DisplayPort MST.  La RX550 no lo usa, y el
                            DC esta vetado por la frontera dura de todos modos.
      amdgpu_wb_slot       es de writeback.  Es de MI generacion, pero no lo
                            compila el modulo:  es una funcion que se elimina
                            en el enlace, asi que no hay tipo que emitir.

  PROVEN_ABSENT  con inventario cerrado, una llamada por struct:  esas 8 no
                 estan en el BTF del modulo.  Cero de gfx, sdma, gmc, ih, vm,
                 vmid, ring, vce, uvd.

  PROVEN  LA RUTA DE POLARIS12 ESTA COMPLETA EN EL BTF.  De los 9 ip_blocks,
          los 7 que estan en el corpus (vi, gmc, tonga_ih, gfx, sdma, uvd, vce)
          tienen todas sus structs con offset medido, incluidos gfx_ring,
          amdgpu_ring, amdgpu_ring_funcs, amdgpu_sdma, amdgpu_vm, amdgpu_vmid,
          amdgpu_sched, sdma_v3_0_ip_block, gfx_v8_0_ip_funcs,
          gmc_v8_0_ip_funcs, tonga_ih_ip_funcs.  Comprobado uno por uno.

  Y LO QUE NO HAY, y no es instrumento:  struct amdgpu_ih NO EXISTE en 7.2.9,
  y eso no lo dice el BTF, lo dice el codigo.  amdgpu_ih.h define solo
  amdgpu_ih_regs, amdgpu_ih_ring y amdgpu_ih_funcs;  el estado del IH vive
  dentro de struct amdgpu_irq.  El BTF lo confirma...
```

## 2 bis · MI ERROR, Y EL INSTRUMENTO QUE MIENTE

La primera versión de esta sección decía:

```text
  $ pahole --btf_base=... -C <279 nombres> amdgpu.ko | grep -c "^struct ... {"
  140
```

**140 estaba mal. El número real es 271.** Y no fue un error de lectura: fue
el instrumento.

```bash
$ para n en 3 10 25 279:
    pahole --btf_base=... -C "<n nombres>" amdgpu.ko | grep -c "^struct .. {"
  lote de 3    ->   3
  lote de 10   ->  10
  lote de 25   ->  25
  lote de 279  -> 143        <<< aqui
```

```text
  PROVEN  pahole -C pierde nombres a partir de alguna longitud de lista.
          Con 25 acierta, con 279 se queda en la mitad.

  Y MI PRIMER INTENTO, el de 140, no fue un lote de 25:  fue un lote de 279,
  y por eso salio el numero mas pequeno.

  Y COMO LO DESCUBRI:  la lista "139 que faltan" contenia amdgpu_ring,
  amdgpu_sdma, amdgpu_vm y amdgpu_sched.  Esas cuatro las habia visto ENCONTRADAS
  en una prueba anterior del mismo fichero.  Dos mediciones del mismo
  instrumento, con el mismo fichero, discrepantes.  MEDIDO UNA TERCERA VEZ,
  nombre por nombre, y ahi estaban.

  CORRIGE, mio  140 -> 271.  Y la cifra de 143 del lote de 279 explica el 140
               que cerre antes:  el limite esta en el rango, no es exacto.
               Mi numero inicial era en realidad el numero del instrumento
               saturado, y lo presente como el numero del objeto.

  ESTA ES LA DECIMOTERCERA VEZ con la misma forma, y es la segunda vez que se
  da de dos maneras:
      1518  probe un solo patron de lo que queria ver ("align_mask") y el
            driver usaba (-x)&7.
      1556  use "cuantos includes no resuelven" para medir un recorte.
      1560  use "279 nombres en una llamada" para contar structs.

  LA REGLA, y es la que se queda:
      ANTES DE CREER UNA CIFRA NEGATIVA, PROBAR EL INSTRUMENTO CON UN CASO QUE
      SE QUE ES POSITIVO.  Un cero de un instrumento que no ha sido probado
      con un uno no es informacion.

  Y "amdgpu_ring no esta" era la senal.  Tuve la contradICCION en las manos y
  la persegui, que es lo que habia que hacer.
```

## 3 · `struct amdgpu_irq`: 2096 BYTES, Y EL VIRQ[256] QUE CIERRA 1550

```c
struct amdgpu_irq {                                /* size 2096 */
        bool                       installed;     /*     0     1 */
        unsigned int               irq;           /*     4     4 */
        spinlock_t                 lock;          /*     8     4 */
        struct amdgpu_irq_client   client[32];    /*    16   256 */  <- 32 x 8
        bool                       msi_enabled;   /*   272     1 */
        struct amdgpu_ih_ring      ih;            /*   280   160 */
        struct amdgpu_ih_ring      ih1;           /*   440   160 */
        struct amdgpu_ih_ring      ih2;           /*   600   160 */
        struct amdgpu_ih_ring      ih_soft;       /*   760   160 */
        const struct amdgpu_ih_funcs  * ih_funcs; /*   920     8 */
        struct work_struct         ih1_work;     /*   928    32 */
        struct work_struct         ih2_work;     /*   960    32 */
        struct work_struct         ih_soft_work; /*   992    32 */
        struct amdgpu_irq_src      self_irq;      /*  1024    24 */
        struct irq_domain *        domain;        /*  1048     8 */
        unsigned int               virq[256];     /*  1056  1024 */  <- 256 x 4
        uint32_t                   srbm_soft_reset;      /*  2080     4 */
        u32                        retry_cam_doorbell_index; /* 2084  4 */
        bool                       retry_cam_enabled;    /* 2088     1 */
};
```

```text
  CONFIRMA, con offset  virq[256] = 1024 bytes = 256 x 4.  El 256 de
                                AMDGPU_MAX_IRQ_SRC_ID (1550 §1) no es un
                                #define arbitrario:  es el TAMAÑO REAL de la
                                tabla, leido del binario.  1550 lo dedujo del
                                codigo;  esto lo confirma desde el artefacto.

  Y client[32] = 256 bytes / 8 = 32 entradas.  O SEA:  AMDGPU_IRQ_CLIENTID_MAX
  == 32, aunque 1550 §1 no pudo resolverlo porque SOC15_IH_CLIENTID_MAX no esta
  en ninguna cabecera del corpus (PROVEN_ABSENT con inventario cerrado).  El
  BTF lo da aunque el numero no este escrito en ningun sitio.

  Y ESO PARECE UNA CONTRADICCION, y hay que decirla:
      1550 §1 dijo que client_id es SIEMPRE 0 (AMDGPU_IRQ_CLIENTID_LEGACY),
      y §1 concluyo que "la tabla efectiva es de UNA dimension".
      El BTF dice que hay 32 clientes.
      LAS DOS SON VERDADERAS:  el ARRAY tiene 32, y para los producers de
      1531 el indice que se usa es 0.  1550 no mintio; leyo la mitad.
      El otro occupant es el cliente KFD/PSP, que no toca la tabla de gfx.
```

## 4 · `struct amdgpu_ih_ring`: AQUÍ ESTÁ EL HALLAZGO

```c
struct amdgpu_ih_ring {                             /* size 160 */
        unsigned int               ring_size;       /*     0     4 */
        uint32_t                   ptr_mask;        /*     4     4 */
        u32                        doorbell_index;  /*     8     4 */
        bool                       use_doorbell;    /*    12     1 */
        bool                       use_bus_addr;    /*    13     1 */
        struct amdgpu_bo *         ring_obj;        /*    16     8 */
        uint32_t *                 ring;            /*    24     8 */
        uint64_t                   gpu_addr;        /*    32     8 */
        uint64_t                   wptr_addr;       /*    40     8 */
        uint32_t *                 wptr_cpu;        /*    48     8 */
        uint64_t                   rptr_addr;       /*    56     8 */
        uint32_t *                 rptr_cpu;        /*    64     8 */
        bool                       enabled;         /*    72     1 */
        unsigned int               rptr;            /*    76     4 */
        struct amdgpu_ih_regs      ih_regs;         /*    80    36 */
        wait_queue_head_t          wait_process;    /*   120    24 */
        uint64_t                   processed_timestamp; /*  144     8 */
        bool                       overflow;        /*   152     1 */
};

struct amdgpu_ih_regs {                             /* size 36 */
        uint32_t                   ih_rb_base;        /*     0     4 */
        uint32_t                   ih_rb_base_hi;     /*     4     4 */
        uint32_t                   ih_rb_cntl;        /*     8     4 */
        uint32_t                   ih_rb_wptr;        /*    12     4 */
        uint32_t                   ih_rb_rptr;        /*    16     4 */
        uint32_t                   ih_doorbell_rptr;  /*    20     4 */
        uint32_t                   ih_rb_wptr_addr_lo;/*    24     4 */
        uint32_t                   ih_rb_wptr_addr_hi;/*    28     4 */
        uint32_t                   psp_reg_id;        /*    32     4 */
};
```

**`ih_regs` es la sombra en RAM de los registros MMIO del IH.** `ih_rb_base` es
el valor que el driver leyo de `IH_RB_BASE` (el offset `0xF80` que `1534`
mencionaba). Ese valor es **la direccion GPU-visible del ring del IH**, la que
`1534` dio por inalcanzable.

## 5 · LA CADENA DE OFFSETS, CERRADA

Con `A` = direccion base de `struct amdgpu_device`:

```text
  A+32      &adev->ddev                  (struct drm_device, 1560 bytes)
  A+90320   &adev->irq                   (struct amdgpu_irq, 2096 bytes)
  A+90336   &adev->irq.client[0]
  A+90600   &adev->irq.ih
  A+90624     .ring                      (puntero CPU al ring)
  A+90648     .wptr_cpu
  A+90664     .rptr_cpu
  A+90676     .rptr
  A+90680     .ih_regs
  A+90680       .ih_rb_base              <<< el objetivo de 1534
  A+90684       .ih_rb_base_hi
  A+90688       .ih_rb_cntl
  A+90692       .ih_rb_wptr
  A+90696       .ih_rb_rptr
  A+90700       .ih_doorbell_rptr
  A+90752     .overflow
  A+91376   &adev->irq.virq[0]
```

Derivación, cada peldaño con su fuente:

```text
  adev->irq          = 90320     pahole amdgpu_device
  + ih               = 280       pahole amdgpu_irq
  + ih_regs          = 80        pahole amdgpu_ih_ring
  + ih_rb_base       = 0         pahole amdgpu_ih_regs
  ---------------------------------------------
                     = 90680     suma, verificada en python
```

```text
  PROVEN_DERIVED  la direccion del IH_RB_BASE guardado en RAM del sistema es
                  adev + 90680.  Sin root para leerla, pero con la direccion
                  exacta.

  Y ADEMAS, sin ningun dato del hardware:
      adev + 90624  = puntero CPU al ring del IH   (dwords, RAM del sistema)
      adev + 90664  = puntero CPU a la sombra de rptr
      adev + 90676  = rptr en bytes, en el propio adev, en una variable normal

  EL rptr esta en adev+90676, o sea que es un campo ORDINARIO de una struct
  que el kernel tiene asignada.  No es un registro MMIO, no necesita
  amdgpu_regs, no necesita debugfs:  es memoria de kernel normal.  Lo unico
  que falta es poder leer memoria de kernel.
```

## 6 · QUÉ CAMBIA Y QUÉ NO

```text
  1534 decia:  "PROVEN_ABSENT:  el ring del IH no se exporta por ningun
                debugfs.  Y no hay otra via sin privilege."
  ESO SIGUE SIENDO VERDAD en la parte de la VIA.  No hay debugfs, no hay
  modulo nuestro.  No se ha inventado una via.

  Y LO QUE CAMBIA, que es el punto:
      antes  la razon de que no se pudiera era "no se donde esta".
      ahora  se sabe donde esta, al byte, y se sabe que es memoria normal.

  EL BLOQUIO AHORA TIENE NOMBRE Y TAMANO:
      falta UNA variable:  la direccion base de adev.

  Y ESO ES MENOS DE LO QUE PARECIA, por dos razones medidas:
      1. adev->ddev esta en A+32, y struct drm_device SI esta en el BTF de
         vmlinux (87 lineas de layout, leidas y medidas).  Asi que la
         estructura que amdgpu usa para negociar con DRM ya tiene offsets
         PROPIOS, sin depender del modulo.
      2. drm_device tiene una entrada conocida por el espacio de usuario:
         el struct file de /dev/dri/cardN.  Si alguna vez hay una lectura, el
         puntero se resuelve desde ahi, no desde una busqueda.

  LO QUE NO PUEDO DECIR:
      que adev este en un sitio que yo pueda leer sin root.  /proc/kcore y
      /dev/mem requieren privilege, y 1538 ya midio que el unico camino sin
      privilege es /proc/interrupts.  No lo he cambiado y no lo voy a
      cambiar por sorpresa.
```

## 7 · ESTADO

```text
PROVEN          el sistema tiene /usr/src/kernels/7.2.9-200.nobara.fc44.x86_64,
                el arbol EXACTO del kernel que corre (UTS_RELEASE medido), y
                las 642 includes <> del driver resuelven al 100 % contra el.
PROVEN          el amdgpu.ko cargado trae .BTF (3 104 956 bytes) y NO trae
                DWARF.  Con --btf_base=vmlinux, pahole da layout en bytes de
                271 de las 279 structs de amdgpu declaradas en las cabeceras.
                Las 8 ausentes son 6 de MES (Arcturus), 1 de DP MST y 1 de
                writeback:  ninguna de la ruta de POLARIS12.
PROVEN          pahole -C pierde nombres con listas largas:  con 25 nombres
                acierta, con 279 devuelve 143.  Toda cifra negativa de esta
                herramienta exige un control con un caso POSITIVO conocido.
PROVEN          struct amdgpu_irq mide 2096 bytes.  client[32] de 8 bytes.
                virq[256] de 4 bytes = 1024, en el offset 1056.
PROVEN          struct amdgpu_ih_ring mide 160 bytes, con ring en +24,
                rptr_cpu en +64, rptr en +76 e ih_regs en +80.
PROVEN          struct amdgpu_ih_regs guarda ih_rb_base, ih_rb_cntl,
                ih_rb_wptr, ih_rb_rptr e ih_doorbell_rptr:  la sombra en RAM
                de los registros MMIO del IH.
PROVEN_DERIVED  adev+90680 = &adev->irq.ih.ih_regs.ih_rb_base.  Cadena cerrada
                por suma de cuatro offsets medidos, cada uno con su struct.
PROVEN          struct amdgpu_ih NO EXISTE en 7.2.9.  El estado del IH esta en
                struct amdgpu_irq.  amdgpu_ih.h solo define amdgpu_ih_regs,
                amdgpu_ih_ring y amdgpu_ih_funcs.

CONFIRMA        1550 §1:  AMDGPU_MAX_IRQ_SRC_ID = 0x100 no es arbitrario,  es
                el tamaño medido de virq[256] = 1024 bytes.
CORRIGE, mio    1550 §6:  "con las 134 cabeceras tendria los offsets".  Falso.
                Las cabeceras dan semantica, no bytes.  Los offsets salen del
                BTF del modulo cargado, que ya estaba en disco.
CORRIGE, mio    1550 §1 "la tabla efectiva es de una dimension":  el array
                tiene 32 clientes.  Para mis producers el indice es 0;  el
                BTF dice que el array es de 32.  Las dos cosas son ciertas.
CORRIGE, mio    este hallazgo decia 140 structs y son 271.  La cifra 140
                era el limite del instrumento, no el numero del objeto.
CORRIGE, mio    error mio de esta sesion:  le el .ko.ZST con readelf y
                conclui que no habia informacion de tipos.  Hay .BTF,  dentro
                del archivo comprimido.  Cita a proposito:  rc=0, sin salida.

TRANSFORMA      1534 PROVEN_ABSENT.  El bloque no se levanta, pero pasa de
                "no hay via" a "la via existe y es adev+90680;  falta la base
                de adev, y sigue faltando privilege para leer kernel".

NOT_DETERMINED  la direccion base de adev en tiempo de ejecucion.  No medible
                sin leer memoria de kernel.
```

## 8 · LO QUE SIGUE, Y POR QUÉ NO ES MÁS DE LO QUE ES

```text
  1. EL RESTO DE LA CADENA SIGUE ABIERTO por el mismo motivo.  rptr en
     adev+90676 es legible en cuanto haya una lectura de memoria de kernel, y
     entonces rptr+wptr (91376, 1024 bytes) dan la tabla de src_id VIVA, que
     es lo que 1550 solo pudo dar como codigo.

  2. Y CON ESA MISMA LECTURA, amdgpu_device (que es enorme) me da en una sola
     pasada los rptr/wptr de los 18 anillos de gfx y sdma, y sus
     processed_timestamp.  O sea: 1538 y 1543 dejan de depender de una foto.

  3. LO QUE ESTO NO HACE, y lo digo porque seria facil Exagerar:
     no he leido nada de la GPU.  No he tocado el hardware.  He leido la
     FORMA de un binario que el kernel ya habia cargado.  Es mejor que un
     .h porque no puede mentir, y es peor que una lectura porque no dice
     NADA del estado actual.

  4. Y SIGUE SIENDO PRIORIDAD MENOR que leer el ring de verdad.  Esto no
     sustituye a 1538;  le quita la dificultad matematica.  Si el portil de root
     llega, el trabajo pasa de "buscar donde esta" a "leer dos direcciones".
     Ese es todo el cambio.
```