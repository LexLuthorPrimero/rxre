# 1201 — El árbol **no declara ni una** anchura de campo PM4 para el GFX8, mientras el mismo `vid.h` sí declara 17 máscaras para sus registros. No es su estilo: son dos convenciones, y la que falta es la de los paquetes

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=PM4-SEMANTICS + GAP-AUDIT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/campos_pm4.py  (--convenciones; 20 -> 28 vectores)
CLASE=MEASUREMENT · GAP · ESTADO=MEDIDO
CORPUS=RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/vid.h
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · Lo que `1200` dejaba abierto, y la pregunta que lo cierra

`1200` medió que **los desplazamientos de `vid.h` no determinan una partición** en 15 de 15
grupos. Dejaba una vía: buscar un segundo header del GFX8 que declarase anchuras.

```text
  drivers/gpu/drm/amd/amdgpu/*_pkt.h
  -> solo existe  gfx_v12_1_pkt.h      (Navi 12)

  drivers/gpu/drm/amd/amdgpu/gfx_v8*.h
  -> solo existe  gfx_v8_0.h           (sin _pkt.h)
```

**El GFX8 no tiene header de paquetes en este árbol.** Sus macros de campo viven en
`vid.h`, y en `vid.h` no hay ni una anchura.

## 1 · La medición

```text
$ campos_pm4.py --convenciones

  campos de PM3 declarada con << : 38
  de esos, con mascara declarada  : 0
  mascaras de registro del mismo header: 17
```

Las 17 máscaras del mismo fichero son de **registros de hardware**:

```c
  #define RB_MAP_PKR0_MASK      (0x3 << 0)
  #define RB_MAP_PKR1_MASK      (0x3 << 2)
  #define MC_SEQ_MISC0__MT__MASK 0xf0000000
```

Es decir, **`vid.h` declara desplazamiento *y* máscara para sus registros, y desplazamiento
*solo* para sus 38 campos de PM3.** Mismo fichero, misma familia de campos, dos
convenciones.

> No es que el header no sea explícito: es explícito con todo menos con los paquetes. Y esa
> asimetría es un hecho del fichero, no una impresión mía, porque se cuenta.

## 2 · Por qué importa para el driver propio

```text
PARA LEER UN CAMPO DE PM4 HAY QUE CONOCER SU ANCHURA, y el arbol no la da.

  lo que si esta:   el desplazamiento
  lo que no esta:   la anchura, la mascara, y el valor por defecto

  PACKET2 si la declara:   PACKET2_PAD_SHIFT / PACKET2_PAD_MASK / REG_SET
                           y esta junto a PACKET3, a veinte lineas

  es decir: el paquete ANTERIOR si usa la convencion completa
```

Consecuencias, en orden de urgencia:

1. **Cualquier lectura de un campo PM4 hecha desde el árbol es una adivinanza.** No hay
   dónde comprobarla sin hardware.
2. La deducción por huecos (`1200`) funciona para 1 campo de 15 grupos —`UNMAP_QUEUES_ACTION`,
   corroborado por los cuatro valores que lista el comentario— y **falla en los otros 14**.
   No es una estrategia generalizable.
3. Un driver propio tiene dos caminos honestos: traer la anchura de la especificación del
   ASIC, que es externa, o medirla por lectura de hardware tras emitir el paquete.

## 3 · Lo único que se deduce de forma fiable, y con dos corroboraciones

```text
  PACKET3_UNMAP_QUEUES / CONTROL
    UNMAP_QUEUES_ACTION   shift 0   [3:0]   4 bits

  vid.h:416-419
    /* 0 - PREEMPT_QUEUES
     * 1 - RESET_QUEUES
     * 2 - DISABLE_PROCESS_QUEUES
     * 3 - PREEMPT_QUEUES_NO_UNMAP
     */
  cuatro valores, cuatro bits
```

Dos fuentes independientes del mismo árbol dan lo mismo. Y hay una tercera del mismo
género que la de `RB_MAP_PKR0_MASK (0x3 << 0)`: **si el campo siguiera la convención de los
registros del mismo fichero, sería un `& 0xF`**.

## 4 · Y el tercer regex de este fichero que no encontraba nada

`RE_MASCARA` y `RE_SHIFT_MACRO` no llevaban `re.M`. Sin `re.MULTILINE`, `^` sólo casa al
principio del **texto entero**, no al principio de cada línea, y `findall` sobre un header
devolvía lista vacía sin excepción. El síntoma era:

```text
  campos de PM3 declarada con << : 0
  mascaras de registro del mismo header: 0
```

Un **cero verosímil y falso**, y la Medicion que iba a escribir era "el header no declara
nada", cuando declara 17 máscaras.

Es la **tercera** vez que un regex de esta herramienta falla en silencio por una causa
tipográfica (`[A-Z0-9_]` sin la `a` de `CONTROL2a`, `RE_GRUPO` sin `re.M`, y ahora esto).

El guard que lo evita es el más barato posible, y no prueba que el regex encuentre lo
correcto:

```python
  for nombre, rx in (("RE_MACRO", RE_MACRO), ...):
      chk("regex %s: encuentra algo en vid.h, o no casa con nada" % nombre,
          len(rx.findall(vid)) > 0, "0 coincidencias:  ¿le falta re.M?")
```

> Un regex que no encuentra nada **no falla**: devuelve cero. Y el cero se parece mucho a
> un resultado.

## 5 · Procedimiento

```text
MEDIDO     campos de PM3 declarados con << en vid.h:        38
           de esos, con mascara declarada:                   0
           mascaras de registro del MISMO header:            17
           ficheros *_pkt.h en el arbol:  solo gfx_v12_1_pkt.h  (Navi)
           ficheros gfx_v8*.h:            solo gfx_v8_0.h     (sin _pkt.h)
MEDIDO     UNMAP_QUEUES_ACTION deduce [3:0] = 4 bits,  y el comentario del
           header lista 4 valores:  dos fuentes, mismo numero
CORREGIDO  RE_MASCARA y RE_SHIFT_MACRO sin re.M:  devolvian cero
ANADIDO    --convenciones
ANADIDO    guard que exige a cada regex del fichero que encuentre algo
           campos_pm4  20 -> 28 vectores rc=0
NO HECHO   traer la especificacion del ASIC para cerrar los 14 grupos que la
           deduccion no cierra:  es la unica via que queda,  y es externa
runtime    RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
