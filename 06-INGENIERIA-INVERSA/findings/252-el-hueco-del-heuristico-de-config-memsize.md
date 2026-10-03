# 252 · El hueco del heurístico de `CONFIG_MEMSIZE`, y tres cosas que un test de contratoaxia que un comentario no

```
CLASSIFICATION=ERROR+MEASUREMENT+IMPLEMENTATION+TEST · TRACK=IMPLEMENTATION
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`201` cerró la cadena de `vram_start`. Este cierra `mc_vram_size`, que es el otro
miembro de la misma pregunta, y al hacerlo encuentra **tres defectos** en cosas que
el proyecto ya tenía escritas: un tope decorativo, un clasificador de C que no
lee C, y una predicción mía escrita a mano.

## 1 · El productor, y el hueco que tiene

```
gmc_v8_0.c:559   /* size in MB on si */
gmc_v8_0.c:560   tmp = RREG32(mmCONFIG_MEMSIZE);
gmc_v8_0.c:561   /* some boards may have garbage in the upper 16 bits */
gmc_v8_0.c:562   if (tmp & 0xffff0000) {
gmc_v8_0.c:563       drm_info(... "Probably bad vram size: 0x%08x", tmp);
gmc_v8_0.c:564       if (tmp & 0xffff)
gmc_v8_0.c:565           tmp &= 0xffff;
gmc_v8_0.c:566   }
gmc_v8_0.c:567   adev->gmc.mc_vram_size = tmp * 1024ULL * 1024ULL;
```

El comentario de la 561 dice que hay basura en los 16 bits altos. La corrección de
la 564 **solo se aplica cuando la mitad baja tiene algo**. Con la mitad baja a
cero, la condición es falsa y no se enmascara nada.

Calculado, no supuesto:

```
  CONFIG_MEMSIZE=0x00000800 ->    2048 MiB    correcto
  CONFIG_MEMSIZE=0xffff0000 -> 4294901760 MiB  <-- el caso DEL COMENTARIO, sin corregir
  CONFIG_MEMSIZE=0x00000000 ->        0 MiB    <-- y vram_end desborda por debajo
  CONFIG_MEMSIZE=0x0000ffff ->    65535 MiB   <-- sin un solo bit alto: ni aviso ni mascara
  CONFIG_MEMSIZE=0xffff0800 ->    2048 MiB    el que SI corrige
```

**Tres modos de fallo, no uno**, y el tercero es el peor porque no dispara nada:
`0x0000ffff` no tiene basura alta, así que el heurístico entero se salta y el
número absurdo se multiplica callado.

Que el campo Documentado sea de 32 bits (`bif_4_1_sh_mask.h`:
`CONFIG_MEMSIZE__CONFIG_MEMSIZE_MASK = 0xffffffff`, `__SHIFT = 0x0`) es lo que
hace razonable el comentario del driver, y es también lo que impide usar la
documentación como criterio: **la documentación declara 32 bits y el silicio, si
algo, da 16**.

## 2 · Lo implementado, y por qué la divergencia es una decisión

`07-DRIVER/kernel/rx550_mc.{h,c}`, C puro, y `tests/test_mc.c` con 23 checks.

```
  se acepta    0x800   -> 2048 MiB
  se acepta    0xffff0800 -> 2048 MiB, y se dice ENMASCARADO
  se RECHAZA   0xffff0000 -> MIEMBOS_ALTOS_SIN_SIGNAL
  se RECHAZA   0x00000000 -> TAMANO_NULO
  se RECHAZA   0x0000ffff -> TAMANO_ABSURDO
```

La divergencia está en **un solo caso**: `0xffff0000`. Los otros se aceptan igual
que upstream. Y el motivo por el que se acepta el que upstream acepta, en vez de
divergir en todo, es que **la diferencia entre aceptar y rechazar tiene que ser
una decisión y no una estética**: aquí es «aceptamos lo que el otro acepta y
rechazamos lo que el otro no sabe interpretar».

Que el hueco sea de upstream y no esté observado en esta placa también se dice:
el log da `VRAM: 2048M`, o sea que aquí no apareció basura. Lo que se ha medido es
una propiedad del **código**, no del silicio.

## 3 · El vector que hace la comparación falsable

El test **lleva dentro la función de `gmc_v8_0.c` copiada**, y para cada valor
calcula las dos respuestas:

```
     CONFIG_MEMSIZE   nombre                             amdgpu        este
     0x00000800       2048 MiB, real de esta placa       2048MiB      2048
     0xffff0000       el caso del comentario             4294901760MiB  RECHAZA
     0xffff0800       bits altos Y senal abajo           2048MiB      2048
     0x00000000       cero                               0MiB         RECHAZA
     0x0000ffff       65535 MiB, sin un bit alto         65535MiB     RECHAZA
     0xffff00ff       255 MiB, enmascarado a algo        255MiB       255
                                        que PARECE razonable
```

La divergencia no está escrita en un comentario: está **calculada al lado**, y
cambia si el código de referencia cambia. Es el mismo criterio que se usó para
las máscaras de opcode en `147`.

## 4 · Defecto 1: un tope que no podía rechazar nada

La primera versión del tope era **64 GiB = 65536 MiB**. El campo que llega ahí
tiene 16 bits y viene enmascarado, así que lo único que puede expresar es
`0..65535 MiB`.

Un tope de 65536 MiB **no puede rechazar nada que el campo sea capaz de
representar**. Y no es inofensivo: un check que no puede fallar da la impresión
de que hay un filtro donde no lo hay. Eso es `241` aplicado a una constante.

```
  el tope tiene que estar ESTRICTAMENTE por debajo del maximo del campo
  16 GiB = 16384 MiB   por debajo de 65535      y por encima de la VRAM real
                                              mas grande de esta generacion
                                              (Polaris11 llega a 8 GB, y aqui
                                               el tope es el doble)
  el log de esta placa dice 2048 MiB: 32 veces por debajo
```

Es un `MODEL_CHOICE` y está declarado como tal en la cabecera.

## 5 · Defecto 2: el clasificador de C no leía el C del proyecto

`drvchain.py` noATED `MC / VRAM` como `IMPLEMENTADO` con seis funciones que tienen
cuerpo. Dos motivos, y los dos son del clasificador:

**No veía la forma del kernel.** `definido()` exigía tipo de retorno y nombre en
la **misma línea**:

```
  int
  rx550_mc_vram_desde_registros(__u32 fb_location, ...)
```

que es exactamente como escribe el kernel y como escribe el driver de este
proyecto desde `rx550_pm4.c` en adelante. El patrón no casaba, y la función se
graduaba `DECLARADO` aunque tuviera el cuerpo delante.

**Y miraba solo la primera coincidencia.** Al concatenar cabecera y `.c`, la
primera coincidencia de un símbolo es su **prototipo en el `.h`**, que acaba en
`;`. `definido()` devolvía `False` ahí y se quedaba: nunca llegaba a mirar la
definición, que estaba tres ficheros más abajo.

Esto no es un caso raro: es **el caso normal de cualquier módulo con cabecera
propia**. Y ningún vector lo cazaba, porque todos usaban la forma de una línea.

La solución no fue añadir un segundo patrón —eso deja la combinación
`prototipo con el tipo suelto` + `definición con el tipo en línea` sin cubrir— sino
**un solo escáner** con regla de predominio:

```
  si CUALQUIER coincidencia acaba en LLAVE  -> hay cuerpo
  si alguna acaba en PUNTO Y COMA y ninguna en LLAVE -> prototipo
  si ninguna coincide -> NINGUNA
```

Y `es_declaracion()` tuvo que delegar en el mismo escáner, porque al añadir el
patrón nuevo un prototipo partido en dos líneas pasó a graduarse `INVOCA`: la
clase `INVOCA` se comprueba **antes** que `DECLARADO`, y esa forma no la
reconocía nadie.

```
  antes   MC / VRAM  AUSENTE     19 eslabones: PROBADO 3, AUSENTE 10
  ahora   MC / VRAM  PROBADO     19 eslabones: PROBADO 4, AUSENTE 9
                                los dos juntos: 7 de 19  (37%)
```

## 6 · Defecto 3: una predicción mía escrita a mano, mal

`242` decía que `mmMC_VM_FB_LOCATION` tiene que leer `0x00000F40`. Es
**incorrecto**: produce `0x000F40000000`, y el log dice `0x000000F400000000`.

```
  registro correcto    0xF400
  el que se escribio    0x0F40     produce 16 veces menos
```

Es un **desplazamiento de cuatro bits de nibble**, el error más difícil de ver en
un hexadecimal porque el resultado sigue siendo plausible.

Y hay una razón por la que no se vio: **era una predicción, no una medida**, y una
predicción no se revisa con el mismo cuidado. El sitio donde un error se propaga
solo es el código; aquí era el hallazgo, que es peor, porque el hallazgo es la
evidencia.

`test_mc` lleva ahora un vector que multiplica la cadena entera contra los dos
números del log, y que no habría podido pasar con `0x0F40` puesto. La corrección
está escrita en `242` con el cálculo a la vista.

## 7 · El coste del `#include`, que no era gratis

`rx550_mc.c` se incluye en `rx550_drv.c` en vez de enlazarse aparte, porque el
`.o` del módulo no puede ser miembro de sus propios `-objs`. La contrapartida es
que los dos ficheros caen en la **misma unidad de traducción**, y la primera
versión de la tabla de motivos se llamaba `motivos`, igual que la de
`rx550_mmio.c`:

```
rx550_mc.c:39:26: error: redefinicion de 'motivos'
```

**Un `static` no es invisible al linker dentro de un mismo `.o`.** Es la única
colisión que introduce el patrón, y por eso los dos ficheros llevan el sufijo.
Queda escrito en `rx550_mc.c` para que el próximo que lo intente lo encuentre
antes de compilar.

## 8 · Lo que NO se establece

```
  que los registros valgan 0xF400 y 0x800   NO MEDIDO: exige el mapa, y el
    mapa sigue retenido por el bloque<->BAR (NOT_IN_CORPUS, 176 §3)
  que 2048 MiB sea el del chip                OBSERVADO de ESTA placa, con su
    VBIOS. Un ASIC es una cosa y una placa es otra
  que el hardware pueda dar 0xffff0000       NO MEDIDO. Que upstream no lo
    contemple es una OBSERVACION sobre el codigo, no una medida del silicio
  el layout de bits de MC_VM_FB_LOCATION     NOT_IN_CORPUS: el header no lo
    declara (201 §5). Solo se sabe que 16 bits van en 24..39
  la relacion entre CONFIG_MEMSIZE y el VRAM
    que declara el SMU                     DESCONOCIDA: el VBIOS puede
    recortarla. Este hallazgo no la toca
```

## 9 · Trazabilidad

```
  07-DRIVER/kernel/rx550_mc.h    el contrato, el MODEL_CHOICE del tope, la prediccion
  07-DRIVER/kernel/rx550_mc.c    la aritmetica y los rechazos, con la divergencia escrita
  07-DRIVER/tests/test_mc.c      23 checks, con la referencia de amdgpu COPIADA dentro
  tools/drvchain.py              forma(): un escaner con predominio, 18 vectores
  gmc_v8_0.c:559-568             el productor y su hueco
  bif_4_1_d.h:33 / _sh_mask.h    CONFIG_MEMSIZE: 0x150a, MASK 0xffffffff, SHIFT 0
  amdgpu_gmc.c:220-221            el consumidor
  findings/201 / 202             vram_start, y la prediccion corregida
```