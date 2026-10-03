# 201 · `MC_VM_FB_LOCATION`, los dos prefijos del mismo registro, y por qué el driver se lo cree a medias

```
CLASSIFICATION=MEASUREMENT+DERIVATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

La cadena completa de `vram_start` en GFX8, de principio a fin, con la línea que
la produce y la línea que la consume. Y dos cosas que salieron por el camino y que
son la mitad del valor de este hallazgo:

1. El registro tiene **dos nombres distintos**, y el que se busca primero no está.
2. El driver **escribe** ese registro solo en el camino de SR-IOV VF, y con un
   `/* XXX double check these! */` del propio upstream.

## 1 · El ASIC de esta GPU, verificado y no supuesto

Antes de leer un registro hay que saber de qué bloque sale. No se supone:

```
vi.c:2107        case CHIP_POLARIS12:
vi.c:2110          amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);
vi.c:2111          amdgpu_device_ip_block_add(adev, &tonga_ih_ip_block);
vi.c:2126        case CHIP_CARRIZO:  ->  &gmc_v8_0_ip_block   (el otro)
```

`CHIP_POLARIS12` comparte `case` con `POLARIS10`, `POLARIS11` y `VEGAM`: los
cuatro usan GMC **8.1**. Es decir, GMC 8.1 no es un rasgo de Polaris12 sino del
grupo, y Polaris12 se distingue de Carrizo precisamente en estos dos bloques.

Corroborado con `183`, que llega a lo mismo por el lado del IH.

## 2 · El registro, y el prefijo que casi lo esconde

```
gmc_8_1_d.h:281    #define mmMC_VM_FB_LOCATION    0x809
sid.h:84           #define MC_VM_FB_LOCATION      0x809
```

El **mismo offset**, dos nombres. La documentación del ASIC usa el prefijo `mm`
(`mmMC_CONFIG`, `mmMC_ARB_ATOMIC`, `mmMC_VM_FB_OFFSET`…), y el identificador de
software usa `MC_` a secas. En el código de lectura se llama además con `reg` por
delante: `regMMMC_VM_FB_LOCATION_BASE` (`mmhub_v3_0_1.c:507`).

Medido: `grep "^#define MC_VM_FB_LOCATION" gmc/gmc_8_1_d.h` → **0 resultados**,
y `gmc_8_1_d.h` tiene **0 macros `MC_`** de 1681. Buscar el nombre de software
en el header de hardware da un negativo perfecto y sin motivo.

Ésta es la misma forma del error que este proyecto ya ha pagado en `170` y en
`regconst.py`: **el prefijo decide el resultado del grep, y no lo decide el
sentido**. Un negativo así no es `NOT_FOUND`, es una pregunta mal escrita.

```
0x809 < 0x200000   cabe en la ventana de 2 MiB medida por 176
0x809 < 0x2e00     muy por debajo de los registros MM_COMPUTE de 180
```

## 3 · La representación: dos mitades de 16 bits

El lector, GFX8 y solo no-VF:

```
gmc_v8_0.c:416   if (!amdgpu_sriov_vf(adev))
gmc_v8_0.c:417       base = RREG32(mmMC_VM_FB_LOCATION) & 0xFFFF;
gmc_v8_0.c:418       base <<= 24;
gmc_v8_0.c:421   amdgpu_gmc_vram_location(adev, mc, base);
```

El consumidor final:

```
amdgpu_gmc.c:220   mc->vram_start = base;
amdgpu_gmc.c:221   mc->vram_end   = mc->vram_start + mc->mc_vram_size - 1;
amdgpu_gmc.c:232   mc->fb_start   = mc->vram_start;
```

### DERIVATION

```
vram_start = (RREG32(0x809) & 0xFFFF) << 24
```

Consecuencia que **no** es un supuesto: los **16 bits bajos** de `vram_start` y
los 16 siguientes son **cero siempre** en esta ruta. El registro no guarda una
dirección, guarda **los bits 24..39** de una dirección de 40 bits, y el hardware
pone el resto a cero.

Eso explica por separado lo que el estado del proyecto tenía anotado como
`vram_base_offset = 0` para la ruta Polaris12: no es una constante de compilación,
es la forma que tiene la representación.

## 4 · La asimetría: quién lee, quién escribe

```
LEE   gmc_v8_0.c:417    si NO soy VF           -> base = (reg & 0xFFFF) << 24
ESCRIBE gmc_v8_0.c:478  si SOY VF              -> las DOS mitades
        gmc_v8_0.c:479    /* XXX double check these! */
        gmc_v8_0.c:480    WREG32(mmHDP_NONSURFACE_BASE, vram_start >> 8)
```

El camino que se ejecuta en **esta GPU** —que no es un VF— es el que **lee**. El
que escribe va precedido de un `XXX double check these!` del propio upstream, en
la misma línea.

Tres cosas que salen de ahí y que no se sabían:

```
  1  Si amdgpu_sriov_vf(adev), base = 0 y NO se lee el registro:
     el driver asume que la VRAM empieza en 0. Es una RAMDIFICACIÓN
     controlable por software, no una lectura.

  2  En el camino de escritura el >> es 24 (gmc_v8_0.c:476-477), y en la
     lectura tambien, pero para OTRO campo:
        SYSTEM_APERTURE_LOW_ADDR   recibe vram_start >> 12   (:469)
        SYSTEM_APERTURE_HIGH_ADDR  recibe vram_end   >> 12   (:471)
        MC_VM_FB_LOCATION          recibe vram_end   >> 24   (:476)
     Un >> no significa nada fuera del campo al que pertenece.

  3  HDP_NONSURFACE_BASE recibe >> 8 y va en la misma frase que el XXX.
     HDP es el header para el display, no el controlador de memoria: es el
     mismo problema de frontera hardware/software con otro nombre encima.
```

## 5 · Lo que NO se establece

```
  el valor real de vram_start en esta placa    NO MEDIDO: requiere leer 0x809,
                                               que exige el mapa, que exige el
                                               bloque<->BAR (NOT_IN_CORPUS, 176 §3)
  la anchura TOTAL del campo de 40 bits        DERIVATION de >>24 y &0xFFFF.
                                               El header no declara el layout
                                               de bits de este campo: las
                                               mascaras mmMC_VM_FB_LOCATION_BASE__
                                               NO estan en gmc_8_1_sh_mask.h
  mc_vram_size de esta placa                   NOT_DETERMINED: sale de SMU y de
                                               la tabla de GTT, no de MC
  que >>24 sea la escala correcta              CORROBORADO por el par lectura/
                                               escritura y por >>12 en los
                                               aperture, NO por hardware
```

La ausencia de las máscaras en `gmc_8_1_sh_mask.h` no es un hueco de lectura:
`grep mmMC_VM_FB_LOCATION_BASE__ ...` devuelve 0 en ese fichero, y ese campo sí
aparece en `mmhub_1_0_sh_mask.h`. Los bloques **nombran distinto** el mismo campo
según la generación. Igual que el registro.

## 6 · Para el driver propio

```
  el registro que hay que leer para saber donde empieza la VRAM
      offset 0x809, 16 bits en [15:0], escalados por 24

  y el mapa de MMIO lo respalda por primera vez con una razon de mas:
      ya no es "una ventana de 2 MiB porque si". Es "una ventana de 2 MiB que
      tiene dentro, en 0x809, el primer byte de la informacion que decide
      donde vive la VRAM". El orden de la cadena de 171 empieza a tener
      contenido y no solo longitud.
```

## 7 · Trazabilidad

```
  vi.c:2107, :2110            POLARIS12 -> gmc_v8_1_ip_block
  include/asic_reg/gmc/gmc_8_1_d.h:281      mmMC_VM_FB_LOCATION 0x809
  amdgpu/sid.h:84                           MC_VM_FB_LOCATION   0x809
  gmc_v8_0.c:416-418                        lector, rama no-VF
  gmc_v8_0.c:469, :471, :476-480            escritores, rama VF
  amdgpu_gmc.c:220, :221, :232             consumidores
  mmhub_v3_0_1.c:507                        el otro bloque, mismo campo
  findings/183                              el mismo razonamiento por el IH
```

```
CITA=gmc_8_1_d.h | TERMINO=mmMC_VM_FB_LOCATION | ROL=el offset del registro,
    con el prefijo mm que el grep sin prefijo no encuentra
```