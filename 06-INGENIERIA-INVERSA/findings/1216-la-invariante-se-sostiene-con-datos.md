# 1216 — La invariante se sostiene con datos: el desplazamiento **nunca subestima** y sobrestima 3 de 4. Pero el bloqueo de `1215` era real, por otra razón

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=METHOD-VALIDATION · CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el bloqueo que 1215 nombro:  los limites de dword de soc15d.h y
         nvd.h.  La respuesta es:  existen,  pero NO particionan de forma
         fiable,  y por eso el test sale con solo 4 comparaciones limpias
VALIDA   el metodo por desplazamiento contra máscaras reales
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta

`1215` dejó 132 máscaras y un test sin hacer:
```text
  132 campos con máscara,  en 19 paquetes
  300 pares de campos con rangos solapados
```
y di sin medir que "los 300 son entre dwords distintos". Eso era una afirmación sin medir: lo dije
porque `SRC_SEL` y `SRC_32B_ADDR_LO` claramente lo son,  y me quedé ahi.  La pregunta correcta es:
**¿existen las fronteras de dword que hacen falta?**

## 1 · Sí existen, y no particionan

```text
  soc15d.h   8 comentarios de dword:  CONTROL(355) COMMAND(380) CONTROL(493)
              CONTROL2(503) CONTROL(514) CONTROL4(532) CONTROL5(534) CONTROL(545)
  nvd.h      8 + GFX11:  CONTROL(406) COMMAND(431) CONTROL(604) CONTROL2(614)
              CONTROL(625) CONTROL4(643) CONTROL5(645) CONTROL(656)
```

La misma convención que `vid.h`. Y hay máscaras **dentro** de esa región: **9** en `soc15d.h` y
**8** en `nvd.h`. Ese es el único sitio donde las dos clases de información coexisten, y por eso
el test es pequeño.

## 2 · El test, y su resultado

Sólo sobre los campos que tienen **máscara y vecino siguiente dentro del mismo grupo**:

```text
  soc15d.h
    COMMAND  PACKET3_SET_SH_REG
        REG_OFFSET    bit  0   máscara 16 bits   despl 23    SOBRESTIMA en 7
        VMID_SHIFT    bit 23   máscara  5 bits   despl  5    EXACTO
        INDEX         bit 28   máscara  4 bits              (ultimo, sin vecino)

  nvd.h      identico, campo por campo

  y desde 1215,  via los comentarios de vid.h,  que si particionan:
    WRITE_DATA_DST_SEL        bit  8   máscara 4 bits   despl 8   SOBRESTIMA en 4
    WR_CONFIRM                bit 20   máscara 1 bit    despl 5   SOBRESTIMA en 4
    WRITE_DATA_CACHE_POLICY   bit 25   máscara 2 bits   despl 5   SOBRESTIMA en 3
```

**Las cuatro comparaciones limpias dan:**

```text
  subestima            0 de 4      <- la invariante se sostiene
  exactas              1 de 4      <- VMID_SHIFT
  sobrestimadas        3 de 4
```

Y la distribución del error, que es lo que hace el resultado utilizable:

```text
  campo                  despl   máscara   error
  VMID_SHIFT                5        5        0
  WRITE_DATA_CACHE_POLICY   5        2        3
  WRITE_DATA_DST_SEL        8        4        4
  WR_CONFIRM                5        1        4
  SET_SH_REG REG_OFFSET    23       16        7
```

El error no es aleatorio: es **la distancia al siguiente campo declarado**, y cuando el header
declara un campo que el campo anterior no necesita, la diferencia se come el hueco entero. Por eso
`WR_CONFIRM` con máscara de 1 bit se come 4 bits de hueco, y `REG_OFFSET` con 16 se come 7.

> Eso convierte el desplazamiento en una cota utilizable **con error acotable por el hueco**, lo
> cual es más de lo que tenía. No es el ancho. Es el ancho más el hueco hasta el siguiente.

## 3 · Por qué el test sale con 4 comparaciones y no con 132

Porque `/* COMMAND */` **no es una frontera de dword** en esas cabeceras. El caso medido:

```text
  COMMAND  PACKET3_ACQUIRE_MEM
      COHER_BASE_HI        bit  0   máscara 24 bits
      COHER_SIZE_HI        bit  0   máscara  8 bits
      COHER_SIZE_HI_VG10   bit  0   máscara 24 bits
      GCR_CNTL             bit  0   máscara 11 bits
      POLL_INTERVAL        bit  0   máscara 16 bits
```

Cinco campos, **todos en el bit 0**, dentro de un único `/* COMMAND */`. Son cinco dwords distintos
—`COHER_BASE_HI` y `POLL_INTERVAL` no pueden estar en el mismo sitio— y el comentario no los separa.
Esos 4 «subestimaciones» que aparecieron en la primera pasada no son subestimaciones: son
intervalos de ancho cero porque dos campos empiezan en el mismo bit, o sea que **están en dwords
distintos**.

Y hay una divergencia entre las dos cabeceras que confirma que no es un accidente:

```text
  soc15d.h   COHER_SIZE_HI_VG10   máscara 24 bits   (VG10 = Vega10,  ASIC distinto)
  nvd.h      (no existe)
  soc15d.h   GCR_CNTL             máscara 11 bits
  nvd.h                            máscara 19 bits
```

`GCR_CNTL` mide 11 bits en GFX9 y 19 en GFX10. **El campo cambió de ancho entre generaciones.**
Eso es lo que §69 advertía, medido.

## 4 · Estado corregido de la evidencia

```text
  LA INVARIANTE                          PROVEN dentro del alcance medido
                                         (4 comparaciones, 0 subestimaciones).
                                         NO es prueba universal:  4 comparaciones
                                         es poco,  y hay que decirlo asi.

  EL DESPLAZAMIENTO ES COTA POR ARRIBA    CORROBORATED,  ahora con 3 casos de
                                         sobrestimacion medida  y un exacto.

  "EXACTO" DE 1209                        NO es el ancho real.  Sigue siendo
                                         "coincide con el minimo por
                                         enumeracion".  Con máscara real,  el
                                         unico caso limpio  (VMID_SHIFT)  si
                                         coincide  — por casualidad del
                                         empaquetado,  no por el metodo.

  PIPE = 2 bits                           NO SE MUEVE.  Ninguna de las 132
                                         máscaras lo contradice  y  no hay
                                         ninguna para el GFX8.

  MASCARAS DE OTRAS GENERACIONES          NO TRANSFERIBLES.  Y ahora con una
                                         prueba de que cambian:
                                         GCR_CNTL  11 bits en GFX9,
                                                   19 bits en GFX10.
```

## 5 · Lo que sigue sin poder medirse, y por qué

```text
  FALTA  las fronteras de dword de los paquetes de comando multi-dword en
         soc15d.h y nvd.h. vid.h las resuelve con la prosa de cabecera
         ("7. COMMAND [30:21] | BYTE_COUNT [20:0]"),  y en 1213 se vio que
         esa prosa COINCIDE con los macros.  Las cabeceras nuevas no tienen
         prosa equivalente.  Sin ella,  el metodo no puede pasar de cota.

  FALTA  una máscara de GFX8.  vid.h tiene 0.  Ninguna de las 132 es de esta
         generacion,  y §69 dice que no se transferiran.

  FALTA  un caso donde el desplazamiento y la máscara coincidan Y el hueco
         sea distinto de cero,  para comprobar que "exacto" significa algo.
         De momento solo hay uno,  y con hueco cero.
```

## 6 · Procedimiento

```text
PREGUNTA   ¿existen las fronteras de dword que hacen falta para validar el
            metodo por desplazamiento contra las 132 máscaras?
FUENTES    soc15d.h  (588 lineas, 8 comentarios de dword, 139 macros de campo)
           nvd.h     (678 lineas, 8+1 comentarios, 201 macros de campo)
           vid.h:141-161  (los comentarios de grupo, que si particionan)
MEDIDO     máscaras dentro de la region de comentarios: 9 en soc15d, 8 en nvd
           comparaciones limpias: 4
           subestima 0  exactas 1  sobrestima 3
           ACQUIRE_MEM: 5 campos los cinco en el bit 0  dentro de un solo
                         /* COMMAND */,  o sea cinco dwords distintos
           GCR_CNTL: 11 bits en soc15d  (GFX9),  19 bits en nvd  (GFX10)
LO QUE SE CORRIGE
   1215  decia "los 300 solapes son entre dwords distintos"  sin haberlo
         medido.  Ahora si:  y el motivo es que /* COMMAND */ no es una
         frontera de dword.  El bloqueo era real,  pero por otra razon que
         la que escribi  (no es que falten los comentarios:  es que no
         particionan).
AUTOCORR.  la primera pasada de este test dio 4 subestimaciones.  No lo eran:
   eran intervalos de ancho cero porque dos campos empiezan en el mismo bit.
   Los entregué como subestimaciones durante un rato  y  de ahi salio la
   conclusion erronea.  Un "subestima" de 24 bits contra un campo de 24 es
   una pista de que el agrupamiento esta mal,  no de que el metodo falle.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
```