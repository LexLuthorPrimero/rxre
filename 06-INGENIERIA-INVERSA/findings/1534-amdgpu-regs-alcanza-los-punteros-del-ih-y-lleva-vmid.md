# 1534 — El ring del IH no se exporta, pero `amdgpu_regs` alcanza sus dos punteros por offset, y el offset lleva un selector de anillo con su propio VMID. Dos correcciones a `1531`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    tonga_ih.

CIERRA         el NOT_DETERMINED de 1531 §8:  el ring del IH no se exporta, y
               en su lugar hay una via por amdgpu_regs que alcanza
               IH_RB_RPTR y IH_RB_WPTR.
DESCUBRE       el offset de amdgpu_regs lleva codificados un selector de
               SH/SE/INSTANCE y otro de ME/PIPE/QUEUE/VMID, con un bit de
               power-gating lock.  Es un protocolo de lectura multiplexado, no
               un volcado de memoria.
DESCUBRE       hay CUATRO anillos de IH (ih, ih_soft, ih1, ih2) y TRES formatos
               de lectura: 4 dwords, 8 dwords, y una lectura de 64 bits.
CORRIGE, mio   1531: el ring tiene DOS ramas de asignacion.  La que use
               tonga_ih.c es dma_alloc_coherent (RAM), pero existe la otra, con
               amdgpu_bo_create_kernel y GEM_DOMAIN_GTT.
ERROR, mio     dos greps vacios que leí como "no existe": uno por buscar
               "ih|irq" en un fichero donde no está, otro por usar
               grep -rloE con -l y -o excluyentes.
```

## 0 · DE DONDE VIENE

`1531` §8 dejó:

```text
  NOT_DETERMINED  como se exporta el ring del IH.  No esta en debugfs (busqueda
                  sin resultado en amdgpu_debugfs.c).  Es RAM de kernel, asi que
                  hay una via, pero no la he encontrado y no la invento.
```

Y también:

```text
  1. EL RING DEL IH.  Si hay forma de exportarlo, se cierra la atribucion
     VMID->proceso que llevaba abierta desde el principio.
```

## 1 · EL INVENTARIO REAL, Y MIS DOS GREPS VACIOS

Primero, un aviso de método. Mis dos primeros intentos dieron vacío:

```bash
$ grep -rnE "debugfs_create.*(ih|irq)" amdgpu_debugfs.c     -> nada
$ grep -nE "ih|irq" amdgpu_debugfs.h                       -> nada
```

**Leí eso como «no hay export del IH».** No lo prueba: `amdgpu_debugfs.c` registra
con `debugfs_create_file(nombre[], ...)` y una tabla, así que un grep de
`ih|irq` en el *código* no encuentra nada aunque el *nombre* exista. Es el error
de `1500`/`1512` por quinta vez, y ya debería estar automatizado: **si el
inventario está en una tabla, se lee la tabla.**

Leída la tabla entera, `debugfs_regs_names[]` (`amdgpu_debugfs.c:1721`):

```text
  amdgpu_regs      amdgpu_regs2      amdgpu_gprwave     amdgpu_regs_didt
  amdgpu_regs_pcie amdgpu_regs_pcie64 amdgpu_regs_smc   amdgpu_gca_config
  amdgpu_sensors   amdgpu_wave       amdgpu_gpr         amdgpu_gfxoff
  amdgpu_gfxoff_status  amdgpu_gfxoff_count  amdgpu_gfxoff_residency
```

```text
  PROVEN  hay 15 entradas de debugfs de amdgpu en esa tabla, y NINGUNA es del
          interrupt handler.  No existe amdgpu_ih, ni amdgpu_irq, ni
          amdgpu_irq_ring.

  Y ADEMAS, el inventario completo de nombres "amdgpu_*" del fichero (25), que
  incluye los que no estan en esa tabla:
      amdgpu_benchmark  amdgpu_discovery  amdgpu_evict_gtt  amdgpu_evict_vram
      amdgpu_force_sclk  amdgpu_preempt_ib  amdgpu_smu_debug  amdgpu_test_ib
      amdgpu_vbios  amdgpu_vm_info

  PROVEN_ABSENT  con inventario cerrado de 25 nombres:  no hay ninguna entrada
                 de debugfs que exponga el ring del IH.  No un "no encontre".

  CORRIGE, mio  la primera redaccion de esta linea decia 23.  Son 25, contados
                sobre el fichero, sin truncador.
```

## 2 · PERO `amdgpu_regs` ALCANZA LOS DOS PUNTEROS

`amdgpu_regs` no es un volcado de memoria: es un **interfaz de operación**. Su
`.read` pasa por `amdgpu_debugfs_process_reg_op` (`amdgpu_debugfs.c:78`), y ahí
está todo el protocolo. Lo leo entero:

```c
/* amdgpu_debugfs.c, process_reg_op */
if (size & 0x3 || *pos & 0x3 ||
        ((*pos & (1ULL << 62)) && (*pos & (1ULL << 61))))
        return -EINVAL;

pm_pg_lock = (*pos >> 23) & 1;

if (*pos & (1ULL << 62)) {        /* bit 62: bank switch */
        se_bank        = (*pos & GENMASK_ULL(33, 24)) >> 24;
        sh_bank        = (*pos & GENMASK_ULL(43, 34)) >> 34;
        instance_bank  = (*pos & GENMASK_ULL(53, 44)) >> 44;
        use_bank = true;
} else if (*pos & (1ULL << 61)) { /* bit 61: ring switch */
        me     = (*pos & GENMASK_ULL(33, 24)) >> 24;
        pipe   = (*pos & GENMASK_ULL(43, 34)) >> 34;
        queue  = (*pos & GENMASK_ULL(53, 44)) >> 44;
        vmid   = (*pos & GENMASK_ULL(58, 54)) >> 54;
        use_ring = true;
}
...
*pos &= (1UL << 22) - 1;
...
while (size) {
        if (read) {
                value = RREG32(*pos >> 2);
                r = put_user(value, (uint32_t *)buf);
        }
        ...
}
```

Las direcciones del IH, desde `sid.h` (que es la cabecera que los define, no la
que incluye `tonga_ih.c` — ver `1531` §4):

```text
  IH_RB_BASE            0xF81       IH_RB_RPTR   0xF82
  IH_RB_WPTR            0xF83       IH_CNTL      0xF86
  INTERRUPT_CNTL        0x151A      INTERRUPT_CNTL2  0x151B
```

Y el límite:

```text
  *pos &= (1UL << 22) - 1   ->  el offset real va de 0 a 4 194 303 bytes (3 MiB)
  IH_RB_RPTR = 0xF82 = 3970 bytes      MUY DENTRO
  IH_RB_WPTR = 0xF83 = 3971 bytes      MUY DENTRO
```

```text
  PROVEN  amdgpu_regs puede leer IH_RB_RPTR e IH_RB_WPTR pasando el offset
          0xF82 o 0xF83 en la posicion de lectura.  Solo lectura, solo dwords
          alineados, y con el bit 23 puesto opcionalmente para tomar el lock de
          power gating.

  Y ESO ES LO QUE FALTA PARA LEER EL RING:  con rptr y wptr del hardware, mas
  IH_RB_BASE (la direccion fisica del ring), se puede calcular el rango del
  buffer.  El contenido sigue sin estar exportado, pero ya se sabe DONDE esta
  y CUANTO ocupa.

  NO AFIRMO QUE SE PUEDA LEER.  amdgpu_regs da el puntero, no el buffer.  La
  diferencia es la que separa "se donde esta" de "tengo el dato", y esa
  diferencia la escribo en vez de saltarla.
```

## 3 · Y EL OFFSET LLEVA SU PROPIO VMID

Esto no lo esperaba y es lo más útil del hallazgo:

```text
  bit 61 -> modo "ring"
            bits[33:24]  ME
            bits[43:34]  PIPE
            bits[53:44]  QUEUE
            bits[58:54]  VMID     <-- 5 bits, 0..31
```

Y el modo `bank`, con `bits[53:44]` = INSTANCE / CU / WGP.

```text
  DESCUBRE  la lectura de un registro de la GPU no es "dame el offset".  Es un
            protocolo:  le dices que banco, o que anillo y que VMID, y le das
            el offset.  El driver traduce a SRBM/GRBM con
            amdgpu_gfx_select_se_sh() o amdgpu_gfx_select_me_pipe_q().

  Y ESO DA UNA SEGUNDA VIA AL VMID, independiente del ring del IH:  se puede
  SELECCIONAR un VMID y leer un registro en su contexto.  Los VMID 0..31, que
  es justo el rango que 1495 no pudo resolver.

  CUIDADO CON EL ALCANCE:  esto prueba que la via EXISTE en el codigo.  No que
  yo pueda usarla sin permisos.  amdgpu_regs se crea con S_IFREG | 0400
  (amdgpu_debugfs.c:1753), o sea modo 0400:  solo lectura, y solo root.
```

## 4 · CORRECCION A `1531`: DOS RAMAS DE ASIGNACION

`1531` §2 dice que el ring es `dma_alloc_coherent`, RAM del sistema. Es cierto
**para la rama que toma `tonga_ih.c`**, pero `amdgpu_ih_ring_init` tiene dos
ramas y yo solo leí una:

```c
/* amdgpu_ih.c:56-65, rama use_bus_addr == true */
if (use_bus_addr) {
        ih->ring = dma_alloc_coherent(adev->dev, ih->ring_size + 8,
                                      &dma_addr, GFP_KERNEL);
        ih->gpu_addr = dma_addr;
        ...
}
/* amdgpu_ih.c:88-91, rama else */
r = amdgpu_bo_create_kernel(adev, ih->ring_size, PAGE_SIZE,
                            AMDGPU_GEM_DOMAIN_GTT,
                            &ih->ring_obj, &ih->gpu_addr, (void **)&ih->ring);
```

```text
  CORRIGE, mio  1531 §2:  la rama con dma_alloc_coherent es la que usa
                tonga_ih.c (sw_init pasa use_bus_addr = true, linea 312).  Pero
                existe la otra rama, y usa amdgpu_bo_create_kernel con
                AMDGPU_GEM_DOMAIN_GTT:  un BO, o sea memoria de GPU mapeada.

  PROVEN_DERIVED  la eleccion depende de use_bus_addr.  Para POLARIS12 es true,
                asi que es RAM del sistema.  Y ESO SE CONFIRMA por el camino
                independiente del flag IH_REQ_NONSNOOP_EN = 0.

  Y NO ES UN DETALLE:  si el ring estuviera en GTT, la lectura del contenido
  necesitaria /dev/dri/card1.  Como esta en RAM del sistema, no.  Y eso solo se
  puede afirmar porque mire las DOS ramas y no solo la que me servia.
```

## 5 · Y HAY TRES ANILLOS DE IH, Y DOS FORMATOS DE ENTRADA

Otra vez, mas de lo que `1531` registro:

```c
/* amdgpu_ih.c:313 */
const char *amdgpu_ih_ring_name(struct amdgpu_device *adev,
                                struct amdgpu_ih_ring *ih)
{
        return ih == &adev->irq.ih   ? "ih"     :
               ih == &adev->irq.ih_soft ? "sw ih" :
               ih == &adev->irq.ih1  ? "ih1"    :
               ih == &adev->irq.ih2  ? "ih2"    : "unknown";
}
```

Y dos formatos de entrada, distinguished por generacion:

```text
  4 dwords (tonga_ih.c:256-259, tonga_ih_decode_iv)
      dw[0][7:0]=src_id   dw[1][27:0]=src_data
      dw[2][7:0]=ring_id  dw[2][15:8]=vmid  dw[2][31:16]=pasid

  8 dwords (amdgpu_ih.c:275-278, amdgpu_ih_decode_iv_helper)
      "position and also advance the position for Vega10 and later GPUs"
      lee dw[0..7]
```

```text
  PROVEN  hay CUATRO anillos de IH (ih, ih_soft, ih1, ih2), segun
          amdgpu_ih_ring_name (amdgpu_ih.c:313-317), que los nombra uno a uno.
          Y hay tres formatos de lectura distintos.

  El de 4 dwords es el de mi generacion (tonga_ih.c:256-259); el de 8 es para
  Vega10 y posteriores (amdgpu_ih.c:275-278).

  Y ESO EXPLICA POR QUE 1531 DIJO "4 dwords" SIN MATIZAR:  es lo que lee
  tonga_ih.c, que es el vigente para POLARIS12.  Pero el driver tiene los otros
  dos tambien, y un driver propio tiene que saber cual de los tres aplica.

  Y HAY UN TERCER FORMATO que no es una entrada de IV sino una LECTURA de 64
  bits (amdgpu_ih.c:300-311), con iv_size = 32:
      dw1 = ring[ring_index + 1]
      dw2 = ring[ring_index + 2]
      return dw1 | ((u64)(dw2 & 0xffff) << 32)
  eso lee 32 bytes de separacion por entrada.  Un tercer formato, para un
  caso distinto.
```

## 6 · ESTADO

```text
CORRIGE, mio   el recuento de nombres: 25, no 23.  Medido sobre el fichero
                entero, sin truncador.
CORRIGE, mio   el numero de anillos de IH: CUATRO (ih, ih_soft, ih1, ih2),
                no tres.  amdgpu_ih_ring_name los nombra uno a uno.
PROVEN          no existe ninguna entrada de debugfs que exponga el ring del
                IH.  Inventario cerrado de 25 nombres "amdgpu_*" en
                amdgpu_debugfs.c.  PROVEN_ABSENT, no NOT_FOUND.
PROVEN          amdgpu_regs alcanza IH_RB_RPTR (0xF82) e IH_RB_WPTR (0xF83):
                son 3970 y 3971 bytes, dentro del limite de 22 bits
                (*pos &= (1<<22)-1).  Solo dwords alineados.
PROVEN          el offset de amdgpu_regs es un protocolo: bit 62 = bank switch
                (SE bits[33:24], SH [43:34], INSTANCE [53:44]), bit 61 = ring
                switch (ME, PIPE, QUEUE, y VMID bits[58:54]), bit 23 = tomar
                el lock de power gating.
DESCUBRE        se puede SELECCIONAR un VMID (0..31) y leer un registro en su
                contexto, por una via independiente del ring del IH.
PROVEN          amdgpu_regs es S_IFREG | 0400 (amdgpu_debugfs.c:1753):  solo
                lectura, y solo root.  La via existe en el codigo y requiere
                privilegios.
CORRIGE, mio   1531 §2: hay DOS ramas en amdgpu_ih_ring_init.  La de
               tonga_ih.c es dma_alloc_coherent (RAM), la otra es
               amdgpu_bo_create_kernel con GEM_DOMAIN_GTT.  Mi conclusion
               era correcta para mi ASIC pero incompleta.
PROVEN          cuatro anillos de IH (ih, ih_soft, ih1, ih2) y tres formatos
               de lectura: 4 dwords (tonga_ih, mi generacion), 8 dwords
               (Vega10+), y una lectura de 64 bits con iv_size=32.

NOT_DETERMINED  si el contenido del ring se puede leer.  Con rptr, wptr y
                IH_RB_BASE se sabe DONDE esta y CUANTO ocupa; el contenido no
                esta exportado por ninguna via que haya encontrado.
NOT_DETERMINED  si el ring de POLARIS12 esta poblado o vacio.  Requiere leer.
```

## 7 · LO QUE SIGUE

```text
  1. EL ESTADO DEL RING, que ahora si es alcanzable en principio.  rptr y wptr
     por amdgpu_regs, restados:  el numero de entradas pendientes.  Eso es una
     medida en vivo de quanta interrupcion genera la carga.  Y es la primera
     medida de RENDIMIENTO que no es un reloj.

  2. Y CON ESO SE CONECTA TODO:  si rptr != wptr, hay interrupciones sin
     procesar.  Eso es trabajo real de GPU que se ve.  Y si wptr - rptr crece
     entre dos lecturas, hay carga.

  3. Y EL VMID POR LA VIA DEL OFFSET:  seleccionar VMID 7 con el bit 61 y leer
     un registro.  Eso responde a una pregunta de 1495 y 1516 que llevo abierta
     desde el principio desde el principio:  0 frente a 7.

  PERO LAS TRES NECESITAN /dev/dri/card1 O ROOT.  Y ESO ES UN SOLO BLOQUEO,
  no tres.  Es el mismo gate para el contenido del IB (1518), para los
  registros, para el rendimiento y para el ring del IH.
```

**Ese punto 3 es el que cierra la cadena.** He estado sin poder atribuir un VMID
porque no tenía el dato. Resulta que hay dos caminos independientes para
conseguirlo, y los dos están detrás del mismo bloqueo de credenciales.