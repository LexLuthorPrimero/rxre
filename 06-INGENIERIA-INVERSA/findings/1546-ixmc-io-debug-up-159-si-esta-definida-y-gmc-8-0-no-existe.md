# 1546 — `ixMC_IO_DEBUG_UP_159` **sí** está definida: refuto el residuo de `1539`. Y el motivo por el que no se encontraba es que **`gmc_8_0_d.h` no existe**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=RESOLUCION-DE-CONTRADICCION + AUDIT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   1539 §"y queda un residuo nombrado":  ixMC_IO_DEBUG_UP_159 se usa una
                         vez y NO ESTA DEFINIDO en ningun header del corpus
REFUTA   esa afirmacion.  Si esta definida en 3 headers,  con el mismo valor
CORRIGE   1545 me lo adjudico a lucas:  su numero,  no mio
DESRULEO EL PUNTO DE FONDO:  no era un simbolo perdido.  Era que GFX8 NO TIENE
         header de registros propio para el controlador de memoria,  y lo toma
         prestado de GFX8.1  —  y el prefijo ix va en minuscula
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · El residuo es falso: la constante está definida tres veces

```text
  include/asic_reg/gmc/gmc_6_0_d.h:393    #define ixMC_IO_DEBUG_UP_159  0x009F
  include/asic_reg/gmc/gmc_7_1_d.h:1058   #define ixMC_IO_DEBUG_UP_159  0x9f
  include/asic_reg/gmc/gmc_8_1_d.h:1162   #define ixMC_IO_DEBUG_UP_159  0x9f
```

**Mismo valor en las tres.** Y el resto del vocabulario de la sonda está igual:

```text
  mmMC_SEQ_IO_DEBUG_INDEX     gmc_6_0_d.h, gmc_7_1_d.h, gmc_8_1_d.h
  mmMC_SEQ_IO_DEBUG_DATA      gmc_6_0_d.h, gmc_7_1_d.h, gmc_8_1_d.h
```

La sonda completa, que es la de `gmc_v8_0.c:241-252`:

```c
  241  case CHIP_POLARIS12:
  242      if (ASICID_IS_P23(adev->pdev->device, adev->pdev->revision)) {
  243          chip_name = "polaris12_k";
  244      } else {
  245          WREG32(mmMC_SEQ_IO_DEBUG_INDEX, ixMC_IO_DEBUG_UP_159);
  246          /* Polaris12 32bit ASIC needs a special MC firmware */
  247          if (RREG32(mmMC_SEQ_IO_DEBUG_DATA) == 0x05b4dc40)
  248              chip_name = "polaris12_32";
  249          else
  250              chip_name = "polaris12";
  251      }
```

Las dos macros y los dos registros existen. **`1539` queda cerrado en este punto.**

## 2 · Por qué no se encontraba: no hay `gmc_8_0_d.h`

Este es el punto de fondo, y es más interesante que la constante.

```text
  include/asic_reg/gmc/    gmc_6_0_d.h   gmc_6_0_sh_mask.h
                           gmc_7_0_d.h   gmc_7_0_sh_mask.h
                           gmc_7_1_d.h   gmc_7_1_sh_mask.h
                           gmc_8_1_d.h   gmc_8_1_enum.h   gmc_8_1_sh_mask.h
                           gmc_8_2_d.h   gmc_8_2_enum.h   gmc_8_2_sh_mask.h

  NO HAY gmc_8_0_d.h.   NI gmc_8_0_sh_mask.h.   NI gmc_8_0_enum.h.
```

Y el grafo de includes —que es lo que decide, mecánicamente, qué header aplica— dice:

```text
  amdgpu/gmc_v8_0.c:35     #include "gmc/gmc_8_1_d.h"      <-- GFX8.1
  amdgpu/gfx_v8_0.c        #include "gmc/gmc_8_2_d.h"      <-- GFX8.2
```

**GFX8 no tiene header de registros propio para el controlador de memoria.** Lo toma
prestado, y lo toma **inconsistemente**: dos ficheros de la misma generación, dos headers
distintos, con una generación de diferencia.

Y no es un caso aislado. De las **39 familias** de `asic_reg`, solo **5** tienen un `_8_0_`:

```text
  CON _8_0_     athub, dce, gca, mmhub, smu
  SIN _8_0_     las otras 34,  entre ellas gmc
```

Así que el caso normal en este árbol es justo el contrario de lo quevuelve uno de GFX8: la
mayoría de las familias no tienen header propio y toman prestado el de la generación vecina.

## 3 · Lo que la inconsistencia cuesta, medido

```text
  gmc_8_1_d.h   1680 defines
  gmc_8_2_d.h    882 defines
  comunes        841
  con VALOR DISTINTO entre 8.1 y 8.2      1

      mmMC_CG_DATAPORT      8.1 = 0xa21      8.2 = 0xa32

  solo en 8.1    839
  solo en 8.2     41
```

Tres cosas, y las tres importan:

```text
  a)  UN REGISTRO SE MUEVE.  mmMC_CG_DATAPORT esta en 0xa21 segun 8.1 y en 0xa32
      segun 8.2.  Es el UNICO de los 841 comunes que cambia de valor.  Código que
      lea ese registro a traves de 8.1 y que calcule otra cosa a traves de 8.2
      esta hablando con dos registros distintos.

  b)  839 REGISTROS SOLO ESTAN EN 8.1.  Y entre ellos, TODO el vocabulario de la
      sonda:
          ixMC_IO_DEBUG_UP_159        8.1=0x9f    8.2=  no existe
          mmMC_SEQ_IO_DEBUG_INDEX     8.1=0xa91   8.2=  no existe
          mmMC_SEQ_IO_DEBUG_DATA      8.1=0xa92   8.2=  no existe
      O sea:  gfx_v8_0.c,  que incluye gmc_8_2_d.h,  NO PUEDE ver los registros
      que usa la sonda de memoria.  Las dos vistas son disjuntas.

  c)  41 REGISTROS SOLO ESTAN EN 8.2.  O sea:  gmc_v8_0.c,  que incluye 8.1,  no
      puede ver 41 registros que si ve el otro fichero.
```

**Consecuencia operativa, y es la que hay que escribir:** para trabajar sobre GFX8, el header
correcto del controlador de memoria es **`gmc_8_1_d.h`**, no un `gmc_8_0_d.h` que no existe, y
no `gmc_8_2_d.h` que le faltan 839 registros. Y si alguna vez se usa `gfx_v8_0.c` para
mirar memoria, hay que cambiar su include o saber que está mirando otra cosa.

## 4 · La asimetría completa de GFX8: nativo en el shader, prestado en la memoria

```text
  bloque        header propio de GFX8?     cual
  ----------------------------------------------------------------------
  SOMBRA (gca)  SI                           gfx_8_0_d.h
                                             gfx_8_0_enum.h
                                             gfx_8_0_sh_mask.h
  PAQUETES      SI                           amdgpu/vid.h
  MEMORIA (gmc) NO                           prestado de gmc_8_1_d.h
```

Las tres primeras filas de la tabla de arriba. **GFX8 es nativo para el shading —son los 9196
campos de `gfx_8_0_sh_mask.h` que he estado usando toda la sesión— y prestado para la
memoria.**

Eso explica por qué esta sesión pudo cerrar tanto del frente PM4 (el header de GFX8 es propio
y está completo) y en cambio la línea de GPUVM lleva `033` y `057` como muro: **la parte
de memoria es la que el driver no tiene declarada para esta generación.**

## 5 · El error mío, y era de una clase que ya había pagado cinco veces

Buscando esto escribí un regex que devolvió **cero** definiciones para un archivo que tiene
1683. El motivo, medido:

```text
  linea 1162, 84 caracteres:
      #define ixMC_IO_DEBUG_UP_159                          0x9f

  regex  #\s*define\s+([A-Za-z_][A-Z0-9_]*)\s+(\S+)     ->  NO MATCHEA
  regex  #define\s+(\S+)\s+(\S+)                        ->  ('ixMC_IO_DEBUG_UP_159','0x9f')
```

**`[A-Z0-9_]` es case-sensitive y `ixMC_IO_DEBUG_UP_159` empieza por `ix` en minúscula.** El
`[A-Za-z_]` del primer carácter acepta la `i`, y a continuación `[A-Z0-9_]` se estrella con la
`x`. Se come exactamente la familia completa sin avisar.

Octava vez en esta tanda que un regex devuelve un número verosímil y equivocado —aquí un
cero, que es la forma más silenciosa de hacerlo—. Y esta vez el número no era inventado: era
un parser que no veía 524 líneas de un archivo.

**La defensa que funcionó:** reescribir sin regex, troceando la línea. El parser sin regex dio
1680 y 882, y con eso apareció el resultado de verdad.

## 6 · La auditoría: qué de lo publicado queda tocado

```text
  defines ix* en include/asic_reg/                         83.722
  (524 solo en gmc_8_1_d.h)

  HERRAMIENTAS QUE LEEN asic_reg Y USAN [A-Z0-9_] SIN IGNORECASE:
    claims.py          [A-Z][A-Z0-9_]{2,}   en identificadores entre acentos graves
    ibref.py           prefijos IT_ / PACKET3_,  y el formato de su propio fixture
    regtable_audit.py  solo GPU_CONFIGREG_*

  EXPOSICION,  uno a uno:
    pm4_grupos.py   SIN EXPOSICION.  Trabaja sobre amdgpu/vid.h,  que tiene
                    0 defines ix*  y 219 de 219 con nombre todo-mayusculas.
                    Los 12 hallazgos de esta sesion no se tocan.
    regtable_audit.py  SIN EXPOSICION.  Su unico patron es GPU_CONFIGREG_*.
    ibref.py           SIN EXPOSICION.  Sus dos patrones sin prefijo  (  :1916,
                       :1918  )  parsean  SU PROPIO formato de fixture  (NOMBRE =
                       0xNNN  en mayusculas por construccion  ).
    claims.py          EXPOSICION REAL Y ACOTADA:  un identificador que empiece por
                       minuscula  no se registra.  Una linea de hallazgo que citar
                       ixMC_IO_DEBUG_UP_159  entre acentos graves no cuenta como
                       identificador.  Afecta a la familia  ix*,  y solo a esa.
```

**Lo que hay que arreglar es una cosa, y es de una línea:** `claims.py` debe aceptar minúscula
inicial, porque en la nomenclatura de AMD los prefijos `ix` y `mm`conviven con los demás y el
`ix` es el único que va en minúscula. No lo he tocado porque el encargo es findings y
`claims.py` no está en la lista de ficheros intocables, pero **es un arreglo pendiente y lo
digo en vez de callarlo**.

Y una nota que no es mío: **`1545` ya estaba ocupado.** Lointenté primero y el contador
compartido lo tenía. Tomo `1546`. Que quede escrito, porque el número no identifica al autor
del trabajo y `1224`/`1054`/`1056` ya lo dejaron dicho.

## 7 · Procedimiento

```text
PREGUNTA   ¿esta ixMC_IO_DEBUG_UP_159 definida en algun header del corpus?
FUENTES    grep sobre todo RESEARCH/  (working, baseline, kernelbuild)
           el grafo de includes de gmc_v8_0.c  y de gfx_v8_0.c
           los 39 directorios de include/asic_reg/
           conteo de defines  ix*  en el arbol
           dos formas de parsear gmc_8_1_d.h y gmc_8_2_d.h,  con regex y sin regex
MEDIDO     definida en gmc_6_0_d.h, gmc_7_1_d.h y gmc_8_1_d.h,  valor 0x9f en las tres
           NO existe gmc_8_0_d.h ni gmc_8_0_sh_mask.h
           gmc_v8_0.c:35 incluye gmc_8_1_d.h;  gfx_v8_0.c incluye gmc_8_2_d.h
           5 de 39 familias tienen header _8_0_;  gmc no esta entre ellas
           gmc_8_1_d.h 1680 defines,  gmc_8_2_d.h 882,  841 comunes,
           1 con valor distinto (mmMC_CG_DATAPORT 0xa21 -> 0xa32),
           839 solo en 8.1,  41 solo en 8.2
           el vocabulario de la sonda existe solo en 8.1
           83.722 defines ix* en asic_reg
           vid.h: 0 defines ix*,  219 de 219 en mayusculas  -> pm4_grupos.py intacto
CIERRA   1539 §residuo nombrado
PARCIAL   la correccion de 1539 queda en un punto  (el residuo),  no en el resto
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto,  no se escribio nada
RUNTIME      NOT_RUN
LO QUE SIGUE
  - el arreglo de UNA LINEA en claims.py:  aceptar minuscula inicial en el patron
    de identificadores,  porque ix  es el unico prefijo que va en minuscula y
    arrastra 83.722 defines
  - gmc_8_1_d.h  es el header de memoria que aplica a GFX8.  Cualquier trabajo
    sobre UMC/GART/GPUVM tiene que apoyarse en el,  no en un gmc_8_0_* que no
    existe  ni en gmc_8_2_d.h  al que le faltan 839 registros
  - el lado del shader de GFX8 si es nativo y completo:  gfx_8_0_d.h y
    gfx_8_0_sh_mask.h existen.  Los dos lados no tienen la misma calidad,  y esa
    asimetria explica por que el frente PM4 se cerro y el de GPUVM no
```