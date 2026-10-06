# 1580 — Ítem 6 cerrado: `PACKET3_WAIT_REG_MEM` **no era un pendiente** — el opcode existe, tiene sus 4 campos documentados, y los 4 dwords de payload quedan identificados por uso. Y uno de sus tres usos en GFX8 es la vía de entrada a GPUVM, que yo tenía declarada bloqueada

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSEOUT · SEMANTICA-DE-PAQUETES
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CÓDIGO+REFUTACIÓN-DE-NOTA-PROPIA
MODIFICATIONS=1230 §pendientes (uno de los 8: RETIRADO por ser falso)
MODIFICATIONS=1580-segun-place · 1225 (invariante del count, 12ª comprobación)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el sexto hueco de riesgo cero,  y RETIRA un pendiente de 1230
REFUTA   dos afirmaciones mias propias sobre este opcode
ABRE     un discriminador concreto para la frontera GPUVM,  que decia bloqueada
```

## 0 · Lo que yo tenía escrito, y por qué las dos cosas eran falsas

En mi lista de huecos, el ítem 6 decía:

```text
  "CP_WAIT_REG_MEM declara cero campos.  El registro existe y el driver lo
   emite 3 veces con count=5.  Los otros linajes (soc15d.h, nvd.h) pueden
   tener las máscaras.  Cierra uno de los 8 pendientes de 1230."
```

Y al ir a buscarlo escribí `grep CP_WAIT_REG_MEM` sobre `gfx_v8_0.c` y **no salió
nada**. Dos conclusiones posibles —"no se emite" o"me equivoqué de token"— y la
regla del proyecto es no elegir la que me resulta más cómoda. Fui a mirar la lista
de opcodes.

**Las dos partes de mi nota eran falsas, y por razones distintas.**

```text
  "declara cero campos"          FALSO.  Tiene 4 macros de campo,  y ademas con
                                      las enumeraciones de valores escritas debajo.
  "el driver lo emite 3 veces"   CIERTO, pero por busqueda con OTRO token.
```

**Lo que confundí:** `CP_WAIT_REG_MEM` **no es el opcode**. El opcode es
`PACKET3_WAIT_REG_MEM`. Y `CP_WAIT_REG_MEM_TIMEOUT` **sí existe**, pero es otra cosa
enteramente: un **registro MMIO**, `mmCP_WAIT_REG_MEM_TIMEOUT = 0xc074` en
`gca/gfx_8_0_d.h:498`. Busqué el nombre del registro donde debía buscar el del
paquete, y el hueco que abrí era un **error de nomenclatura mío**, no una laguna en
el driver.

## 1 · El opcode, con sus cuatro campos, y la dirección de cada uno

```text
  amdgpu/vid.h:168   #define PACKET3_WAIT_REG_MEM      0x3C
```

Y los cuatro, con la enumeración de valores que AMD escribió al lado:

```text
  vid.h:169   WAIT_REG_MEM_FUNCTION(x)   (x << 0)    0 always  1 <  2 <=  3 ==
                                                     4 !=  5 >=  6 >
  vid.h:178   WAIT_REG_MEM_MEM_SPACE(x)  (x << 4)    0 reg    1 mem
  vid.h:182   WAIT_REG_MEM_OPERATION(x)  (x << 6)    0 wait_reg_mem  1 wr_wait_wr_reg
  vid.h:186   WAIT_REG_MEM_ENGINE(x)     (x << 8)    0 me     1 pfp
```

**Los bits documentados son solo el 0-9.** Del dword de control no se declara nada por
encima del bit 9. Ese es el residuo real, y es pequeño.

## 2 · Los cuatro dwords de payload, deducidos de los usos, no de la prosa

Aquí está lo útil. Los macros no cubren el payload, pero **los tres usos en GFX8 lo
llenan con valores que no dejan otra lectura**:

```text
  dword 0   cabecera     PACKET3(PACKET3_WAIT_REG_MEM, 5)
  dword 1   control      FUNCTION | MEM_SPACE<<4 | OPERATION<<6 | ENGINE<<8
  dword 2   direccion    registro  ->  mmXXX          |  memoria -> addr[31:0]
  dword 3   dir alta     0 si es un registro          |  memoria -> addr[63:32]
  dword 4   ref          valor con el que se compara
  dword 5   mask         que bits cuentan
  dword 6   poll interval  base de tiempo del bucle de sondeo
```

Los tres sitios, con su función:

```text
  gfx_v8_0.c:6047   gfx_v8_0_ring_emit_hdp_flush
      control   OPERATION(1)=write,wait,write   FUNCTION(3)==   ENGINE del anillo
      dword2    mmGPU_HDP_FLUSH_REQ
      dword3    mmGPU_HDP_FLUSH_DONE
      dword4    ref_and_mask
      dword5    ref_and_mask
      dword6    0x20      "poll interval"

  gfx_v8_0.c:6180   gfx_v8_0_ring_emit_pipeline_sync
      control   MEM_SPACE(1)=memoria   FUNCTION(3)==   ENGINE(usepfp)
      dword2    addr & 0xfffffffc              <-- 64 bits,  partido en dos dwords
      dword3    upper_32_bits(addr)
      dword4    seq = ring->fence_drv.sync_seq
      dword5    0xffffffff                     <-- mascara: todos los 32 bits
      dword6    4        "poll interval"

  gfx_v8_0.c:6199   gfx_v8_0_ring_emit_vm_flush
      control   OPERATION(0)=wait   FUNCTION(0)=always   ENGINE(0)=me
      dword2    mmVM_INVALIDATE_REQUEST
      dword3    0
      dword4    0     "ref"
      dword5    0     "mask"
      dword6    0x20  "poll interval"
```

**El segundo sitio es el que cierra la decodificación**, porque es el único que pasa
una dirección de 64 bits de verdad: `dword2`/`dword3` son `addr & 0xfffffffc` y
`upper_32_bits(addr)`, `dword4` es el valor a comparar y `dword5` es `0xffffffff`.
Eso fija por uso qué es cada cosa. La masking `& 0xfffffffc` además confirma el
requisito de alineación a 4 que ya imponía `smu7_set_smc_sram_address:40` en el otro
lado del driver.

** twelfth confirmation del invariante de `1225`:** payload de 6 dwords, `count = 5`.
La regla `count = payload − 1` aguanta otro caso, y este con el payload más largo que
he encontrado.

## 3 · El productor varía, y eso no es trivial: el ENGINE sale del tipo de anillo

`get_hdp_flush_mask` de GFX8 (`:5231-5247`) decide los dos campos que no son
constantes:

```text
  anillo GFX (graphics)  ->  ENGINE = WAIT_REG_MEM_ENGINE(1) = PFP
                            ref_and_mask = GPU_HDP_FLUSH_DONE__CP0_MASK
  anillo COMPUTE o KIQ   ->  ENGINE = 0 = ME
                            ref_and_mask = GPU_HDP_FLUSH_DONE__CP2_MASK << pipe
                                         o   GPU_HDP_FLUSH_DONE__CP6_MASK << pipe
```

**El mismo paquete apunta a un motor distinto según el anillo que lo emite**, y la
máscara se desplaza por tubería. Para el anillo de gráficos —que es el que
interesa para el modo de escritorio— es `CP0` y `ENGINE = PFP`.

Y hay una corroboración lateral con `1228`: **`gfx_v12_1.c:246` no pasa
`WAIT_REG_MEM_ENGINE` en absoluto.** Es el mismo patrón que el `ENG_SEL` que se mueve
de `<<25` a `<<28` solo en GFX12.1. Los dos cambios de GFX12.1 son del mismo tipo: la
selección de motor deja de ser un campo del paquete.

## 4 · Y lo que de verdad me importa: el tercer uso ES la frontera GPUVM

Este es el hallazgo de la ronda. El tercer sitio es `gfx_v8_0_ring_emit_vm_flush`, y su
primera línea es:

```c
  gfx_v8_0.c:6196   amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);
  gfx_v8_0.c:6198   /* wait for the invalidate to complete */
```

**`vmid` y `pd_addr`.** Eso es GPUVM: identificador de espacio de direcciones y
dirección de la tabla de página. Y `tengo declarada esa frontera como bloqueada:

```text
  "GPUVM / PTE / GART:  033 (AMD no publica el bloque de gestion de memoria de
   GFX8),  057 (sin discriminante de solo lectura),  07-DRIVER/ no implementa VM.
   Muro declarado;  ninguna capacidad de RXRE lo resuelve."
```

**El muro sigue en pie en cuanto a la especificación del hardware** —sigo sin saber
qué significa un bit de la PTE—. **Pero la premisa "no hay discriminante" era
demasiado amplia**, por dos razones que salen de aquí:

**Una: la sincronización de la invalidación no se comprueba, se espera por tiempo.**
El control es `FUNCTION(0) = always`, con `ref = 0`, `mask = 0` y `poll interval =
0x20`. O sea: **no hay bit de "invalidación completada" que consultar**; el paquete
espera un número de intervals y sigue. Eso es un hecho semántico sobre cómo se
serializa una invalidación de TLB en GFX8, y **es observable en el anillo**, sin
entrar en la PTE.

**Dos: hay una segunda primitiva inmediatamente después, y es condicional.**

```c
  gfx_v8_0.c:6209   /* compute doesn't have PFP */
  gfx_v8_0.c:6210   if (usepfp) {
  gfx_v8_0.c:6211       /* sync PFP to ME, otherwise we might get invalid PFP reads */
  gfx_v8_0.c:6212       amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
  gfx_v8_0.c:6214   }
```

El comentario del driver dice algo que no es evidente: **sin `PFP_SYNC_ME`, el PFP
puede leer inválido.** Eso es un requisito de ordenación real entre el processor de
instrucciones de píxeles y el motor de comandos, y es exactamente el tipo de
restricción que un driver propio tiene que respetar y que hoy no está escrita en
ningún sitio de este proyecto.

**Lo que esto abre, con honestidad sobre su límite:** `PACKET3_PFP_SYNC_ME` no estaba
en mi inventario. Lo he encontrado **por la vía de un pendiente que era falso**. Eso
deja una línea de trabajo concreta y de riesgo cero: enumerar los paquetes de
sincronización entre PFP y ME y su condición de emisión, porque son primitivas que un
driver propio necesita invocar y cuyo orden no es opcional. Sigue **sin** resolverse qué
significa la PTE — eso no lo abre nadie sin la especificación.

## 5 · Procedimiento y alcance

```text
PREGUNTA   que declara y que significa PACKET3_WAIT_REG_MEM,  y si es de los
           8 pendientes de 1230
FUENTES    la seccion de opcodes PACKET3 de amdgpu/vid.h:112-455,  leida
           grep de PACKET3_WAIT_REG_MEM en TODO el arbol .c   (14 emisiones)
           grep de CP_WAIT_REG_MEM en TODO el arbol            (solo registros MMIO)
           los 3 sitios de GFX8 con contexto,  y el productor get_hdp_flush_mask
MEDIDO     PACKET3_WAIT_REG_MEM = 0x3C,  en vid.h:168
     4 macros de campo,  con enumeraciones de valores,  en vid.h:169-189
     los macros cubren solo los bits 0-9 del dword de control
     14 emisiones en el arbol;  3 en gfx_v8_0.c  (:6047, :6180, :6199)
     las 3 pasan count=5 con payload de 6 dwords  -> invariante de 1225,  12a vez
     payload decodificado por uso:  dir[31:0] · dir[63:32] · ref · mask · poll
     la direccion de 64 bits partida en dos dwords la fija el sitio :6184-6185
     ENGINE sale del tipo de anillo:  PFP para GFX,  ME para COMPUTE/KIQ
     gfx_v12_1.c no pasa ENGINE,  coherente con 1228
     el sitio :6199 llama a amdgpu_gmc_emit_flush_gpu_tlb(vmid, pd_addr)
     y lo sigue con PACKET3_PFP_SYNC_ME si usepfp
DESVIO MIO  dos,  y las dos del mismo tipo
     · confundi  CP_WAIT_REG_MEM  (registro MMIO, 0xc074)  con
       PACKET3_WAIT_REG_MEM  (el opcode).  Busqué el nombre del registro
     · de ese error deduje "el driver no lo emite",  y la realidad es que
       lo emite 3 veces.  Debí comprobar el token ANTES de concluir el negativo
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

## 6 · Sobre el patrón de error, que ya es una medida

Esta es la **tercera vez** en el día que una nota que yo arrastraba resulta falsa por
un nombre, no por un hecho:

```text
  1578   "36 bytes de diferencia"  ->  comparaba discrete contra fusion,  no
                                      contra smu74,  que es el de nuestra placa
  1579   "el SMC no autoincrementa"  ->  cierto a medias:  hay un segundo camino
  1580   "CP_WAIT_REG_MEM declara cero campos"  ->  es el nombre del REGISTRO,
                                                   no el del opcode
```

**Las tres son de la misma clase: un nombre que yo escribí una vez y que seafarió de
la realidad sin que nadie lo volviera a comprobar.** La defensa que funciona es la
misma que ya usé en `1576`: cuando una afirmación mía es el objeto de la
investigación, **buscar el token y contar, no citar la nota**. Y cuando el grep no
devuelve nada, eso es `NOT_FOUND` sobre una búsqueda, no `PROVEN_ABSENT` sobre el
código.

## 7 · Lo que sigue

```text
  huecos de riesgo cero:  4 · 5 · 7     (1, 2, 3 y 6, cerrados)
  1230 §pendientes:  uno RETIRADO por falso.  Quedan 7,  con motivo nombrado
  nuevo,  y con valor real:
    enumerar las primitivas de sincronizacion PFP<->ME y su condicion de
    emision.  PACKET3_PFP_SYNC_ME ha aparecido por un pendiente falso,  lo que
    sugiere que hay mas en esa vecindad.  Es de riesgo cero y un driver propio
    necesita su orden
  y sigue en pie lo unico que cierra soft_regs_start:  el valor de
    SMC_RAM[0x20030].  Con la receta del driver (1579),  las dos direcciones
    confirmadas en los tres linajes,  y pendiente de tu OK
```