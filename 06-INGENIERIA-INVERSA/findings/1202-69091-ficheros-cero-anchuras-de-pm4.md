# 1202 — Barrido de **69 091 ficheros**: el árbol no declara **ni una** anchura de campo PM4, para ningún ASIC. Y el cero está autovalidado, que es lo que lo hace un dato

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=PM4-SEMANTICS + NEGATIVE_RESULT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/campos_pm4.py  (--arborme; 28 -> 31 vectores)
CLASE=NEGATIVE_RESULT · GAP · ESTADO=MEDIDO_Y_AUTOVALIDADO
CIERRA 1201 (que solo barrio vid.h)  ·  1200 (que dedujo lo deducible)
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · Por qué `1201` no era la pregunta completa

`1201` contó 38 campos de PM3 con `<<` en `vid.h` y **0** con máscara, frente a 17 máscaras
de registro del mismo fichero. Su conclusión era "el GFX8 no declara anchuras".

La pregunta completa es más grande:

```text
¿LOS DECLARA ALGUN SITIO DEL ARBOL?
```

Porque si no los declara ni el kernel que los emite, el problema no es del GFX8: es del
material de partida, y eso cambia lo que hay que hacer.

## 1 · El barrido

```text
$ campos_pm4.py --arborme

  BARRIDO DEL ARBOL  69091 ficheros
    campos de PM3 que declaran anchura: 0
    el patron VE un positivo conocido:  True

    Ni una.  En TODO el arbol.  La anchura de un campo de PM4
    no se puede leer de aqui,  para NINGUN ASIC.
```

Qué cubre el barrido:

```text
  RESEARCH/working/linux-7.1.3/     la copia de trabajo,  con vid.h, soc15d.h,
                                    nvd.h y gfx_v12_1_pkt.h
  RESEARCH/baseline/linux-7.1.3/    la otra copia del mismo kernel
  RESEARCH/kernelref/               167 cabeceras
  RESEARCH/polaris12xl/             18 cabeceras
```

Y el patrón que busca es la forma completa, con la máscara pegada al desplazamiento:

```python
  define PACKET3_<CAMPO>(x)  ... << N ... & (u32) 0xM
```

## 2 · Los dos únicos candidatos, y por qué son falsos positivos

Los 24 resultados de una búsqueda más laxa sobre `PACKET3_.*_MASK` son dos cosas
distintas:

```c
  #define PACKET3_SET_RESOURCES_VMID_MASK(x)  ((x) << 0)
```

`VMID_MASK` es el **nombre de un campo** —el valor de máscara que se le pasa a
`SET_RESOURCES`—, no la declaración de una anchura. Su valor es un argumento.

```c
  #define PACKET3_WAIT_REG_MEM__MASK(x)  ((unsigned)(x))
```

Es un **accesor**: devuelve el campo. Los dos firmados con `(x)` e `_MASK` en el nombre, y
ninguno declara un ancho.

> Un nombre que contiene `MASK` no es una máscara. Es la clase de coincidencia que hace
> que una búsqueda con `grep` produzca un positivo y no advierte de que no es lo que se
> buscaba.

## 3 · Lo que hace que este cero sea un dato y no una herramienta rota

Esta herramienta lleva **tres regex que devolvieron cero en silencio**, y las tres
produciron cifras verosímiles y falsas:

| Vector | Síntoma | Causa |
|---|---|---|
| `[A-Z0-9_]+` | los 7 sub-bloques colapsaban en 1 | no casa con la `a` de `CONTROL2a` |
| `RE_GRUPO` sin `re.M` | los sub-bloques mal agrupados | `^` sólo casa al principio del texto entero |
| `RE_MASCARA` sin `re.M` | "0 campos, 0 máscaras" | ídem, en un barrido de 69 091 ficheros |

Un cuarto ya está en la categoría correcta: este mismo barrido, que **antes de dar su
cero se prueba contra un caso positivo conocido**:

```text
  el patron VE un positivo conocido:  True
```

y si eso fuera `False`, el instrumento sale con `rc=2` y dice que su cero **no es un
dato**:

```text
  EL BARRIDO NO ES FIABLE:  no encuentra ni el caso de prueba.
  Su cero no es un dato.
```

> Un negativo que no se ha validado contra un positivo no es un resultado: es una
> herramienta rota con buena pinta.

## 4 · Consecuencias, y son de nivel de proyecto

```text
1. La anchura de un campo PM4 NO se puede leer de este arbol,  para ningun ASIC.
   No es una carencia del GFX8 ni de vid.h:  es del material de partida.

2. De 15 grupos de vid.h,  la deduccion por huecos cierra 1  (UNMAP_QUEUES_ACTION,
   corroborado por los 4 valores del comentario).  Los otros 14 quedan abiertos.

3. Cualquier lectura de un campo PM3 hecha desde este arbol es una ADIVINANZA sin
   donde comprobarse sin hardware.

4. Las dos vias honestas siguen siendo las de 1201:
      - traer la especificacion del ASIC,  externa
      - medirla por lectura de hardware tras emitir el paquete

5. Y hay una tercera que este hallazgo sugiere y no se ha explorado:  para un campo
   concreto,  el conjunto de VALORES que el driver le pasa a lo largo del arbol es una
   cota inferior de la anchura.  Si el driver solo pasa 0..3,  la anchura es al menos 2
   bits,  y eso es medible con lo que hay.
```

El punto 5 es el que conviene: **es la única vía que queda dentro del árbol**, y no
necesita hardware ni especificación. No se ha medido todavía.

## 5 · Procedimiento

```text
MEDIDO     campos de PM3 que declaran anchura, en 69091 ficheros de RESEARCH/:
           CERO
MEDIDO     los 24 candidatos de una busqueda laxa:  1 es un campo LLAMADO
           VMID_MASK y 1 es un ACCESOR;  ninguno declara un ancho
MEDIDO     vid.h:  38 campos de PM3 con <<, 0 con mascara, 17 mascaras de registro
MEDIDO     kernelref: 167 cabeceras, 0 definiciones de paquetes PM3
AÑADIDO    --arborme, con autocomprobacion:  el patron debe ver un positivo
           conocido,  y si no,  rc=2 y "su cero no es un dato"
           campos_pm4  28 -> 31 vectores rc=0
NO HECHO   la cota inferior desde el conjunto de valores que el driver pasa.  Es la
           unica via que queda dentro del arbol,  y no necesita hardware
NO HECHO   traer la especificacion del ASIC:  externa,  y la API de GitHub desde
           aqui responde 404,  o sea NO_ACCESS y no ausencia
runtime    RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```