# 1528 — la fila mide 4 KB, los otros dos campos no significan nada, y mi hipótesis del 2 KB era falsa por la razón correcta

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM (una sola) · FASE=2 (geometria)
CLASSIFICATION=SEMANTICA-DERIVADA-DEL-DRIVER + REFUTACION-DE-HIPOTESIS-PROPIA + PROVEN_ABSENT
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1522 (le da la semantica que dejo abierta) y mi propia aritmetica del turno anterior
ESTADO=PROBADO · NOOFCOLS tiene formula escrita: fila = 4 KB en esta placa
       · NOOFBANK y NOOFRANKS se guardan CRUDOS y NADIE los convierte en cuenta, en todo el arbol
       · el ilog2(num_banks) que parece resolverlo opera sobre OTRO campo con otro encoding
       · la geometria la declara el ROM y no la decodifica nadie
       · MI FORMULA UNIFORME ERA FALSA, y se refuta por una causa concreta y util
```

## 1. De donde salio el 2 KB, y por que estaba mal

En el turno anterior calcule la geometria con una suposicion mia: que `NOOFBANK`, `NOOFROWS` y
`NOOFCOLS` fueran **todos exponentes del mismo encoding**. Salio 2 KB contra los 2 GB de la placa, y
lo declare sin cerrar.

La suposicion era falsa. **Y la causa de que sea falsa es el hallazgo**, no un obstaculo: los tres
campos no comparten encoding, y ademas uno de ellos tiene formula escrita en el driver.

## 2. `NOOFCOLS` tiene semantica, y esta escrita

No hay que deducirla. Esta en `gfx_v8_0.c:1818-1821`, en la rama de GPU **discreta** (la `else` del
`if (adev->flags & AMD_IS_APU)`):

```c
  1818   tmp = REG_GET_FIELD(mc_arb_ramcfg, MC_ARB_RAMCFG, NOOFCOLS);
  1819   adev->gfx.config.mem_row_size_in_kb = (4 * (1 << (8 + tmp))) / 1024;
  1820   if (adev->gfx.config.mem_row_size_in_kb > 4)
  1821           adev->gfx.config.mem_row_size_in_kb = 4;
```

Con el valor medido en el ROM, `NOOFCOLS = 2`:

```text
  (4 * (1 << (8 + 2))) / 1024  =  (4 * 1024) / 1024  =  4 KB
  y el capping de la 1820 no muerde: 4 no es mayor que 4
```

> **PROBADO por la formula del propio driver:** `mem_row_size_in_kb = 4` en esta placa. Con el
> mismo registro, un `NOOFCOLS` de 3 daria 8 KB y lo recortaria a 4: **el capping oculta el valor
> real en cuanto `NOOFCOLS >= 3`**, y en esta placa no muerde, asi que aqui el 4 es el valor
> calculado y no un recorte.

**La fila de esta memoria mide 4 KB.** Ese es un hecho de la tarjeta derivado de una formula del
driver aplicada a un valor del ROM, sin tocar hardware.

Y la formula tambien dice **elUnits**: el `4 *` inicial es el ancho, y el `/1024` es KB. No es un
numero de filas: es un **tamaño de fila**, y por eso mi cuenta de "2 KB" estaba mal planteada desde
el principio — estaba multiplicando un numero de filas por un exponente de columnas y llamando a eso
capacidad.

## 3. Los otros dos campos: crudos, y sin consumidor

```c
  1784   adev->gfx.config.num_banks = REG_GET_FIELD(mc_arb_ramcfg, MC_ARB_RAMCFG, NOOFBANK);
  1786   adev->gfx.config.num_ranks = REG_GET_FIELD(mc_arb_ramcfg, MC_ARB_RAMCFG, NOOFRANKS);
```

Sin `1 <<`. Sin `ilog2`. **Valor crudo, tal cual.** Con lo medido:

```text
  config.num_banks  = 2
  config.num_ranks  = 0
```

Y aqui esta el dato que cierra el tema. Consumidores de esos dos campos en todo el arbol:

| consumidor | que hace |
|---|---|
| `amdgpu_amdkfd_gpuvm.c:3234-3235` | copiaverbatim a `config` de KFD. Comentario literal: *"Those values are not set from GFX9 onwards"* |
| `amdgpu_debugfs.c:1005` | expone `mem_row_size_in_kb`, **no** banks ni ranks |

**No hay un tercer consumidor.** En gfx8, `config.num_banks` y `config.num_ranks` no los usa nada de
la ruta grafica. Se leen del hardware, se guardan, se copian a KFD, y se quedan.

> **PROVEN_ABSENT, con el alcance declarado:** en este corpus de amdgpu, nadie convierte
> `NOOFBANK` ni `NOOFRANKS` de exponente a cantidad. El nombre del campo dice `num_` —una cuenta—
> y el valor que se guarda es el exponent cruda. **Si el campo es un exponente, el nombre miente;
> y no hay nada en el arbol que lo resuelva.**

## 4. La trampa del homonimo, que es lo que casi me hace seguir mintiendo

Existe en el arbol un sitio que **si** aplica `ilog2` a un `num_banks`:

```c
  amdgpu_display.c:851   ... ilog2(adev->gfx.config.gb_addr_config_fields.num_banks)
```

Ese es `gb_addr_config_fields.num_banks`, **otro campo**, no `config.num_banks`. Y en gfx9 ese otro
campo se construye con shift:

```c
  gfx_v9_0.c:2125    adev->gfx.config.gb_addr_config_fields.num_banks = 1 << ...
  gfx_v9_4_3.c:942   adev->gfx.config.gb_addr_config_fields.num_banks = 1 << ...
```

O sea: **hay dos `num_banks` con dos encodings distintos**, y el que usa `ilog2` es el de gfx9, no el
que viene de `MC_ARB_RAMCFG`. En gfx8 el de `GB_ADDR_CONFIG` sale de una constante golden
(`TONGA_GB_ADDR_CONFIG_GOLDEN` y compañía), no del registro de memoria.

Si uno lee `display.c:851` y llega a `MC_ARB_RAMCFG`, concluye que banks es exponente. **No lo es en
ningun consumidor de gfx8.** Es el mismo tipo de homonimia que el `139`Thy ya registro con `prt`.

## 5. Lo que esto deja, y lo que deja abierto

```text
PROBADO     mem_row_size_in_kb = 4.  Derivado de la formula del driver sobre el valor del ROM.
PROBADO     config.num_banks = 2 y config.num_ranks = 0, crudos, sin convertir, sin consumidor
            en la ruta grafica de gfx8.
PROBADO     el ilog2 que apparentemente resolveria la ambiguedad es de otro campo y otro ASIC.
PROBADO     dos campos llamados num_banks con encodings distintos conviven en la misma struct.
NOT_DETERMINED  si NOOFBANK=2 son 2 banks o 2^2=4.  No hay consumidor que lo decida en este
            corpus.  KFD recibe el numero pero no lo convierte en lo que le llega desde aqui, y
            el uso de KFD de ese campo no es trazable desde amdgpu.
NOT_DETERMINED  si NOOFRANKS=0 es 0 ranks (imposible) o 2^0=1 rank.  El 0 hace sospechar que es
            exponente, pero "sospechar" no es medir.
ABIERTO     reconciliar los 2048 MB con la fila de 4 KB.  NO lo fuerzo: para hacerlo falta saber
            el numero de filas, y el numero de filas no esta en ningun campo que yo sepa leer.
LIMITE      el artefacto que llevaria el valor ya decodificado por el driver es
            /sys/kernel/debug/dri/0/amdgpu_gc_info, que expone mem_row_size_in_kb
            (amdgpu_debugfs.c:1005).  NO ESTA en revkit/capturas/.  Es una laguna de custodia
            concreta y con nombre, y se cierra sola cuando se permita leer debugfs.
RIESGO      ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
```

## 6. Lo que esto cambia para la parte 1

El item 2 de la definicion de cierre —la geometria de VRAM— no es un hueco de un dato. Es esto:

```text
  la fila            4 KB            PROBADO, por la formula del driver
  el mapa de canales mmMC_SHARED_CHREMAP   declarado en el ROM, 0x00000010
  los bancos/ranks   crudos, sin usar  PROBADO que no se usan
  el numero de filas desconocido        NOT_DETERMINED, y con nombre
  la capacidad       2048 MB, del ROM, con 4 oraculos de alineacion
```

**La tarjeta declara su geometria y el driver se la pasa entera sin montarla.** Eso no es un fallo del
proyecto: es una caracteristica de gfx8, y para escribir un driver propio es exactamente el dato que
hay que reconstruir a mano. Que aqui `num_banks` valga 2 sin saber si son 2 o 4 es el ejemplo
concreto.

## 7. Decision log (§103)

```text
DECISION    dejar el reparto 2048 MB / 4 KB sin reconciliar, y no buscar el numero de filas por
            prueba y error
WHY         exigiria inventar una semantica de filas que ninguna fuente del corpus declara.
            §63: no se implementa una semantica critica sin cadena.  Aqui no hay cadena.
ALTERNATIVA  probar filas hasta que cuadre.  Descartada: siempre cuadra algo, y un numero que
            cuadra porque se busco no es evidencia.  Seria el mismo error que el 1494/1496/1498.
DISCriminante  la fuente que falta esta nombrada: amdgpu_gc_info, que el driver escribe con su
            propio valor ya decodificado.  Un solo fichero la cierra.
CONSECUENCIA  el item 2 queda con 4 de 9 subpuntos probados y 1 con nombre.  Es el estado honesto.
REVERSIBLE  si aparece la semantica de filas, la fila de 4 KB no cambia: viene de una formula.
```

## 8. La regla que aplico a partir de ahora, y que casi me hace fallar aqui

Me puse a multiplicar exponentes para que salieran los 2 GB. **Eso es buscar la respuesta, no
derivarla**, y el 1522 ya habria avisado si lo hubiera releido antes de calcular.

Lo que funciono fue buscar la **formula** en el driver antes de calcular nada, y ahi estaba escrita,
en cuatro lineas, con su unidad y su capping. Y lasHipotesis wrong no fallo por falta de datos:
falló por una razon concreta y con nombre —los tres campos no comparten encoding— y esa razon es
informacion.

> Cuando un calculo no cuadre, el siguiente paso es **buscar la formula del productor**, no ampliar
> el espacio de hipotesis. `NOOFCOLS` la tenia el driver, escrita, con su capping. Yo la resolvi
> solo despues de fallar el calculo, y la habria resuelto antes si hubieramirado quien consume el
> registro en vez de quien lo escribe.
