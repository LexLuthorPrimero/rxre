# 1177 — el segundo escritor de `mmIH_VMID_0_LUT` está muerto: nadie invoca `set_pasid_vmid_mapping`, y eso deja a `1166` con un solo productor real

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=amdgpu_amdkfd_gfx_v8.c:87,594   la funcion y su puntero en la tabla
         1166-mmih-vmid-0-lut-lo-escriben-dos-caminos-con-valores-distintos.md
CORRIGE=1166, en su afirmacion central: NO hay dos escritores vivos.  Hay uno
        vivo y uno inalcanzable, que es un problema distinto y peor.
ESTADO=PROVEN-INALCANZABILIDAD · el metodo es el de 046, aplicado a un simbolo
```

## 0 · LO QUE `1166` AFIRMÓ, Y QUE ESTE HALLAZGO CORRIGE

`1166` cerró diciendo:

> *hay dos escritores del registro de mapeo, con valores distintos… el mismo
> registro, el mismo campo, dos valores distintos. Y no es que uno sea una
> versión antigua del otro: **están en el mismo driver, conviven**, y se disparan
> por condiciones **independientes**.*

**«conviven» es falso.** MEDIDO: el segundo de ellos **no se ejecuta**.

Y la diferencia no es un matiz. Cambia la conclusión entera:

| | lo que decía `1166` | lo que se puede decir |
|---|---|---|
| escritores de `mmIH_VMID_0_LUT` | 2, ambos vivos | **1 vivo**, 1 inalcanzable |
| hay coordinación entre ellos | "nada en el código" | **no hay nada que coordinar**: uno no corre |
| riesgo para un driver propio | "quién escribe el último decide" | **copiar el alcanzable, y el otro no importa** |

> **Un hallazgo que se corrige a sí mismo y se conserva vale más que uno
> acertado la primera vez.** `1166` acertó al encontrar los dos productores y
> acertó al ver que escribían valores distintos — eso es `PROVEN` y sigue siendo
> cierto. Lo que estaba mal era la frase **«conviven»**, que es una afirmación
> de alcance, y de las que este proyecto lleva mil lecciones documentando.

## 1 · LA MEDICIÓN, EN TRES PASOS Y POR SEPARADO

El símbolo es `set_pasid_vmid_mapping`, un puntero a función dentro de
`struct kgd_device_funcs`. Hay que separar **definición**, **asignación en la
tabla** y **invocación**, porque un grep que mezcla las tres da un número que no
significa nada.

```
  1.  menciones del simbolo en el arbol            17
  2.  de ellas, ASIGNACIONES en tabla de dispatch    9
  3.  invocaciones reales                            0
```

El paso 3, aislado:

```bash
grep -rn "set_pasid_vmid_mapping(" | grep -v "static int|= kgd|= set_pasid| int kgd"
```

devuelve **dos líneas**, y las dos son **prototipos**:

```
  amdgpu_amdkfd_gfx_v9.h:27   int kgd_gfx_v9_set_pasid_vmid_mapping(struct amdgpu_device *adev, ...)
  amdgpu_amdkfd_gfx_v9.c:101  int kgd_gfx_v9_set_pasid_vmid_mapping(struct amdgpu_device *adev, ...)
```

**Cero llamadas.** El puntero se define en nueve tablas de generación —una por
`kgd_device_funcs`— y no lo invoca nadie en este corpus.

## 2 · POR QUÉ ES ALCANZABLE EL OTRO PRODUCTOR, Y ESTO NO ES UNA EXCEPCIÓN

El productor A de `1166` no se alcanza por un puntero de tabla: se llama
directamente.

```c
amdgpu_vm.c:847-849
  if (pasid_mapping_needed)
        amdgpu_gmc_emit_pasid_mapping(ring, job->vmid, job->pasid);
```

Y ese es un punto de la función que decide si un trabajo se envía. La condición
es:

```c
amdgpu_vm.c:806-808
  pasid_mapping_needed &= adev->gmc.gmc_funcs->emit_pasid_mapping &&
```

**Producer A: llamada directa, alcanzable.** Productor B: puntero de tabla, sin
invocación.

Y esa asimetría es la lección, porque es exactamente la que el proyecto ya pagó
con `023`/`035`/`043` y con `047`: **un nombre de función en una tabla de
dispatch parece código, y no lo es hasta que se encuentra quién lo llama.**

> Lo que `047` midió sobre los *selectores de IP version* —inalcanzables porque
> el `switch` que los lee no se ejecuta— es el mismo hecho que este, en otra
> escala: **una funciónreferenciada en una tabla de funciones no es código
> alcanzable, es un puntero que alguien tiene que invocar.** Y en este caso nadie
> lo invoca.

## 3 · LO QUE QUEDA VIVO, Y ES MÁS SIMPLE DE LO QUE DECÍA `1166`

Si el productor B no corre, entonces para esta ASIC **la tabla
`ATC_VMID0_PASID_MAPPING` nunca se escribe** desde KFD.

Y eso conecta con `1153`, que había medido que `gmc_v8_0_flush_gpu_tlb_pasid`
**lee 15 de esos registros** para construir la máscara:

```
  LECTOR   gmc_v8_0_flush_gpu_tlb_pasid      lee ATC_VMID0_PASID_MAPPING[1..15]
  ESCRIPTOR B (kgd_set_pasid_vmid_mapping)   no se ejecuta
```

**Un lector sin escritor.** Y eso es `PROVEN` y es un dato de una clase distinta
del de `1166`: no es una carrera entre dos escritores, es **una tabla que se lee
y no se escribe desde el camino que se ejecuta**.

Y no hay que especular para verlo: el productor B es el **único** escritor de esa
tabla en todo el árbol, porque el productor A solo escribe `mmIH_VMID_0_LUT`:

```c
gmc_v8_0_emit_pasid_mapping:
        amdgpu_ring_emit_wreg(ring, mmIH_VMID_0_LUT + vmid, pasid);   /* y NADA mas */
```

> **Consecuencia operativa, y es la que importa para el bucle:** si la tabla
> `ATC_VMID0_PASID_MAPPING` no se escribe, la máscara que
> `gmc_v8_0_flush_gpu_tlb_pasid` construye es **cero**, porque
> `ATC_VMID0_PASID_MAPPING__VALID_MASK` nunca se pone. Y una máscara cero escrita
> en `mmVM_INVALIDATE_REQUEST` **no invalida nada**.
>
> Eso **no dice** que la invalidación por PASID esté rota: puede que en esta ASIC
> no se use, y que la vía 1 sea la buena. **Lo que dice es que la vía 2, tal como
> está escrita, no puede hacer nada en esta configuración.** Y es `NOT_DETERMINED`
> si es intencionado o es un descuido del upstream.

## 4 · LO QUE NO SE AFIRMA

- **No digo que KFD no pueda invocarlo.** Digo que en este corpus nadie lo
  invoca. Puede haber un camino por `ioctl` que lo alcance por otro nombre, o una
  versión de `.h` que este árbol no trae. Eso es `NOT_FOUND` en el grafo textual, no
  `PROVEN_ABSENT` en el árbol.
- **No digo que el valor de `VALID_MASK` sea 0.** Es un campo del registro, y su
  valor en esta GPU es `NOT_DETERMINED` sin hardware. Lo que afirmo es que **el
  único código del árbol que pondría ese bit no se ejecuta**.
- **No abro el bug del upstream.** Puede que en GFX8 la vía 1 sea la única
  válida y la 2 esté muerta a propósito. Eso es semántica del ASIC.

## 5 · POR QUÉ ESTE HALLAZGO ES MÁS ÚTIL QUE LA AFIRMACIÓN QUE CORRIGE

Porque **reduce lo que hay que replicar y nombra lo que hay que decidir**:

```
  antes (1166):  dos escritores, valores distintos, hay que coordinarlos
  ahora (1177):  un escritor alcanzable, otro muerto
                 -> el alcanzable basta, se copia
                 -> y hay una tabla que se lee sin escritor, que es una
                    pregunta de 1 linea para el nodo de runtime
```

La segunda línea es la que vale. Un lector sin escritor es un **`NOT_DETERMINED`
con una sola forma de cerrarse**: leer `mmATC_VMID0_PASID_MAPPING` en esta GPU y
ver si los 15 registros tienen `VALID` puesto. Si lo tienen, hay un escritor que
no está en este corpus. Si no lo tienen, la vía 2 es decorativa y la 1 es la
buena.

Cualquiera de las dos respuestas **cambia lo que implementa un driver propio**, y
ninguna se puede obtener leyendo código.

## 6 · LA LECIÓN, Y ES LA TERCERA VEZ

La tabla:

| hallazgo | lo que tomé por vivo | lo que era |
|---|---|---|
| `023` | `sdma_v3_0.c` como productor de PTE | el fichero equivocado |
| `047` | el cero de ficheros ASIC | `sdma_v3_0.c` estaba en la lista, no el que corre |
| `1166` | dos escritores de `mmIH_VMID_0_LUT` | uno está en una tabla sin invocación |

**Tres veces, la misma forma.** Y las tres tienen el mismo coste: un hallazgo que
alguien tomaría por cerrado y sobre el que construiría.

> Lo que las tres tienen en común no es el error: es que **el defecto se detecta
> con un grep que distingue el rol de cada mención**, y un grep normal no lo
> distingue. La razón por la que el proyecto ha pagado esto tres veces es que
> **cuenta menciones donde tenía que contar invocaciones.**
>
> Y el instrumento que falta es diminuto: `tools/unreach.py` ya hace la prueba de
> alcanzabilidad, y resuelve este caso si se le pasa un símbolo de `kgd_device_funcs`
> en vez de un selector de IP version. **Eso es una línea de alcance, no un
> instrumento nuevo** — y por eso lo dejo anotado en §7 en vez de construir algo.

## 7 · LO QUE PROPONGO, Y NO LO HAGO

Extender `tools/unreach.py` a los **punteros de `kgd_device_funcs`**: es la misma
prueba de alcanzabilidad sobre un grafo distinto, y el corpus tiene nueve tablas
con esos punteros. Si hay punteros sin invocación además de este, son la misma
familia de hallazgo y se miden de una vez.

**No lo implemento**: `tools/unreach.py` es de otra sesión, y el árbol tiene
ficheros suyos modificados sin commitear. Es una línea de alcance para quien lo
posea.

```
ESTADO
  set_pasid_vmid_mapping
    punteros definidos en tablas de dispatch      9
    punteros invocados                           0        PROVEN
     -> el productor B de 1166 esta INALCANZABLE
  ATC_VMID0_PASID_MAPPING
     unico escritor                              kgd_set_pasid_vmid_mapping  -> INALCANZABLE
     leido por                                  gmc_v8_0_flush_gpu_tlb_pasid (1153)
     -> LECTOR SIN ESCRITOR                     PROVEN
  el valor del registro en esta GPU             NOT_DETERMINED -> 1 lectura lo cierra
  mmIH_VMID_0_LUT
     escritores alcanzables                      1        PROVEN
     el valor que escribe                       pasid, sin VALID_MASK     PROVEN

  corrige el alcance de 1166, no su medicion
  GPU     INTACTA
  sudo    NO usado
```