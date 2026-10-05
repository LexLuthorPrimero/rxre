# 1221 — `vid.h` **nombra el registro** que copia. `vid.h:479` dice `/* mmPA_SC_RASTER_CONFIG mask */`, y los 17 campos cuadran 17 de 17. Cierra la pregunta abierta de `1214`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   1214 §"cual de los 31 macros PACKET3_ pertenece a que paquete vecino"  y
         su §"por que vid.h no separa el bloque compartido"
NUEVO    una regla buscable:  los comentarios '/* mmX mask */' de un header de
         paquetes son COPIAS LITERALES de los campos de un registro.  En todo el
         arbol solo hay 4 bloques de ese tipo,  y 2 estan en vid.h
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · Lo que el header dice de sí mismo

No hubo que deducir nada. `vid.h` lo escribe:

```c
   479  /* mmPA_SC_RASTER_CONFIG mask */
   480  #define RB_MAP_PKR0(x)				((x) << 0)
   481  #define RB_MAP_PKR0_MASK			(0x3 << 0)
   482  #define RB_MAP_PKR1(x)				((x) << 2)
   483  #define RB_MAP_PKR1_MASK			(0x3 << 2)
   ...
   507  /* mmPA_SC_RASTER_CONFIG_1 mask */
   508  #define SE_PAIR_MAP(x)				((x) << 0)
   509  #define SE_PAIR_MAP_MASK			(0x3 << 0)
```

Es una **copia literal de los campos de `PA_SC_RASTER_CONFIG` y `PA_SC_RASTER_CONFIG_1`**, con sus
máscaras, pegada dentro del header de paquetes. Eso explica de una vez las tres cosas que `1214`
dejó sin resolver, y lo hace por declaración propia del archivo en lugar de por inferencia mía.

## 1 · El cuadre, campo a campo

```text
  campo          vid.h        registro PA_SC_RASTER_CONFIG   veredicto
  RB_MAP_PKR0    [ 1:0 ]      [ 1:0 ]                      igual
  RB_MAP_PKR1    [ 3:2 ]      [ 3:2 ]                      igual
  RB_XSEL2       [ 5:4 ]      [ 5:4 ]                      igual
  RB_XSEL        [ 6:6 ]      [ 6:6 ]                      igual
  RB_YSEL        [ 7:7 ]      [ 7:7 ]                      igual
  PKR_MAP        [ 9:8 ]      [ 9:8 ]                      igual
  PKR_XSEL       [11:10]      [11:10]                      igual
  PKR_YSEL       [13:12]      [13:12]                      igual
  SC_MAP         [17:16]      [17:16]                      igual
  SC_XSEL        [19:18]      [19:18]                      igual
  SC_YSEL        [21:20]      [21:20]                      igual
  SE_MAP         [25:24]      [25:24]                      igual
  SE_XSEL        [27:26]      [27:26]                      igual
  SE_YSEL        [29:28]      [29:28]                      igual

  PA_SC_RASTER_CONFIG_1
  SE_PAIR_MAP    [ 1:0 ]      [ 1:0 ]                      igual
  SE_PAIR_XSEL   [ 3:2 ]      [ 3:2 ]                      igual
  SE_PAIR_YSEL   [ 5:4 ]      [ 5:4 ]                      igual

  TOTAL  17 macros en vid.h,  18 campos en el registro,  17 en el mismo bit
         y con el mismo ancho
```

Y **el registro tiene un campo que `vid.h` no trae**:

```text
  PKR_XSEL2    PA_SC_RASTER_CONFIG bits [15:14]    ausente de vid.h
```

Cae en el hueco limpio que dejan `PKR_YSEL` en `[13:12]` y `SC_MAP` en `[17:16]`. O sea que la
copia de `vid.h` está **incompleta**: 14 de los 15 campos del primer registro, 3 de 3 del segundo.

## 2 · Qué cierra, de `1214`

`1214` §5 dejó estos tres abiertos:

```text
  ABIERTO en 1214                                      ESTADO AHORA
  ---------------------------------------------------------------------------
  por que vid.h no separa el bloque compartido      →  el bloque esta marcado
    de 99 macros                                        como copia de un registro,
                                                        en un comentario que lo dice
  cual de los 31 macros PACKET3_ pertenece a que     →  los 17 RB_/PKR_/SC_/SE_/
    paquete vecino                                      SE_PAIR_ no son campos de
                                                        paquete:  son campos de
                                                        PA_SC_RASTER_CONFIG,  y
                                                        cuadran 17 de 17
  si NOP y CLEAR_STATE tienen estructura             →  sigue sin decidirse,  y es
                                                        un caso distinto
```

Y añade un dato que no buscaba: **`vid.h` está incompleto respecto al registro que copia.** Eso
es un hecho sobre el header, no una limite mio, y es de la clase que `§121` exige registrar.

## 3 · La regla, y su censo

```text
  REGLA   un bloque que empieza con el comentario  /* mm<REGISTRO> mask */
          es una copia literal de los campos de ese registro,  con su mascara.
          Es buscable,  y por tanto verificable.

  CENSO en todo el arbol del driver:
      vid.h    2 bloques     mmPA_SC_RASTER_CONFIG,  mmPA_SC_RASTER_CONFIG_1
      cikd.h   2 bloques
      (los otros cuatro headers de paquete no tienen ninguno)

  o sea que vid.h es practicamente el unico header de PAQUETES que mete
  definiciones de REGISTRO dentro.  Eso es una rareza del archivo,  no una
  convencion del proyecto,  y explica por que 1214 los encontro como
  "macros sin nombre de paquete":  no son campos de paquete.
```

`cikd.h` tiene 2 bloques más. No los he cotejado todavía: es el siguiente ítem, no este.

## 4 · El límite del método por nombre, dicho antes de que se confunda con el del §1

El censo que me trajo hasta aquí buscó campos de paquete **por nombre** en el header de registros,
y produjo dos falsos positivos:

```text
  EVENT_WRITE.EVENT_TYPE  << 0   casa con VGT_EVENT_INITIATOR[5:0]
  SET_BASE.PACKET3_BASE_INDEX     casa con SQ_M0_GPR_IDX_WORD[7:0]
```

`INDEX` y `EVENT_TYPE` son nombres de campo de registro muy comunes, y que coincidan no significa
que sean el mismo campo. **Un nombre coincidente no es una identidad.** El caso de §1 no depende de
eso: el comentario nombra el registro, y encima cuadran 17 de 17 en bit y ancho. Eso es
identificación por declaración, no por parecido de nombre.

## 5 · Procedimiento

```text
PREGUNTA   ¿los macros sin nombre de paquete de vid.h son de otro lenguaje,  y
            puedo decirlo con un mecanismo y no con una conjetura?
FUENTES    vid.h:476-515,  leido con numero de linea
           asic_reg/gca/gfx_8_0_sh_mask.h  (PA_SC_RASTER_CONFIG  y  _1)
           asic_reg/gca/gfx_8_0_d.h:  mmPA_SC_RASTER_CONFIG = 0xa0d4
           censo grep de '/* mmX mask */' en los seis headers de paquete
MEDIDO     17 de 17 en el mismo bit y con el mismo ancho
           1 campo del registro ausente de vid.h  (PKR_XSEL2,  bits [15:14])
           4 bloques '/* mmX mask */' en todo el arbol,  2 en vid.h  y 2 en cikd.h
NEGATIVOS  el metodo por nombre produce falsos positivos:  INDEX  y EVENT_TYPE
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - cotejar los 2 bloques de cikd.h con sus registros:  mismo metodo,  mismo
    riesgo de que la copia este incompleta
  - si hay mas copias de registro en vid.h  que no esten marcadas con '/* mmX mask */'
  - NOP y CLEAR_STATE siguen sin clase
```