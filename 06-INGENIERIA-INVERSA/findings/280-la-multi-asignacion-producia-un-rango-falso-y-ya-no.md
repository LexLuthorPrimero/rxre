# 280 · La multi-asignación producía un rango falso, y ya no

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 1 (`tools/smc_copy_scope.py`)

> ## Resultado
>
> `smc_copy_scope` 1.2.0 → **1.3.0**. El punto de uso manda sobre el nombre:
> `graphics_level_address` en `:149`, `:157` y `:166` devuelve **236**, **708** y
> **1592**. Antes devolvía 1592, 1592 y 1592, y uno de esos tres era un rango
> inventado.

## El criterio de cierre, cumplido

Declarado en `278`: `graphics_level_address` debe dar 236, 708 y 1592, en orden.

| línea | 1.2.0 | 1.3.0 | veredicto |
|---|---|---|---|
| `:149` | `?..?` | `?..?` | destino ya correcto; falta el tamaño (hueco aparte) |
| `:157` | **`1592..1615`** | **`708..731`** | **el falso, corregido** |
| `:166` | `1592..1593` | `1592..1593` | correcto, **ahora por diseño y no por suerte** |

`:166` merecía nota en `278`: acertaba porque era la última asignación, que es
justo la que sobrevivía en el mapa. Con el orden de asignaciones invertido
habría fallado también. Ya no depende del orden.

## El cambio, en tres sitios

**1. `ctx` guarda la historia, no solo la última.**

```python
ctx.setdefault(nombre, []).append((off, base, a))
```

con `a` = posición de la sentencia. Antes era `ctx[nombre] = (off, base)`, que
sobrescribía en cada asignación.

**2. `resuelve_destino` recibe `pos` y elige la vigente antes del uso.**

```python
previas = [x for x in v if x[2] < pos]
if not previas:
    return None, "variable local " + e + " asignada DESPUES de su uso", ""
return previas[-1][0], "variable local " + e, previas[-1][1]
```

Con `pos is None` se conserva el comportamiento viejo, para no romper a quien
llame sin posición.

**3. Los dos puntos de uso pasan `a`.** El de la escritura y el que resuelve el
lado derecho de una asignación. Este segundo importa: si la base es otra variable
local que se reasigna después, el valor correcto es el que estaba vigente al
ejecutar *esta*, no el último.

## La validación

**Los 21 vectores anteriores NO detectaban el defecto.** Comprobado
introduciendo el fallo a mano:

```
los 21 vectores con el defecto reintroducido:  exit=0   lineas FALLO: 0
```

Es `SELF_TEST_MUST_EXCEED_FIXTURE` incumplido por segunda vez, igual que en
`260`. El fixture no cubría el comportamiento que se iba a cambiar.

**Añadido el caso L**, que reproduce la forma real: un mismo nombre con tres
asignaciones y un uso entre cada par.

```c
direccion = base + offsetof(T, A);   write(...)   -> 10
direccion = base + offsetof(T, B);   write(...)   -> 20
direccion = base + offsetof(T, C);   write(...)   -> 30
```

Con el defecto reintroducido desde el fichero **actual**:

```
exit=3
SELFTEST FALLO: casoL: se esperaban los inicios 10,20,30 y se obtuvieron [30, 30, 30]
```

`[30, 30, 30]` es exactamente el fallo de `polaris10_smumgr.c`. 22 vectores,
`RESULTADO OK`.

**Recuento final sobre el fichero real, leído en crudo:**

```
8 correctos   0 falsos   4 sin resolver
```

De los 4 sin resolver, **3 son `PROVEN_ABSENT`** (`:654`, `:1872`, `:1881`:
direcciones que decide el firmware). Queda **1 hueco real**, y no es del destino.

## El hueco que queda, y por qué — `SEMANTIC_MISSING` del mapa de contadores

`:149` sigue sin tamaño. Y la causa no es el destino, que ya se resuelve bien:

```c
126:  uint32_t graphics_level_address, vr_config_address, graphics_level_size;
128:  graphics_level_size = sizeof(avfs_graphics_level_polaris10);
151:      graphics_level_size, 0x40000),
```

`graphics_level_size` solo aparece en esas tres líneas de todo el fichero.
`:128` **no entra** en el mapa de contadores por dos razones encadenadas:

1. El patrón de `:745` solo reconoce `sizeof(T) * CONSTANTE`. `:128` es un
   `sizeof` a secas, así que no casa.
2. Al caer a `RE_LOCAL_ADDR` —que sí acepta `:128`, porque el tipo es
   opcional— `resuelve_destino("sizeof(...)")` devuelve `off=None`, y eso va a
   `ctx`, que es el mapa de **destinos**, no a `__contadores__`, que es el de
   **tamaños**.

**Y además hay un shadow silencioso que se come la entrada por línea de órdenes:**

```python
739:  local = ctx.setdefault("__contadores__", {})       # se crea aunque quede VACIA
813:  ctx_cont = ctx_amb.get("__contadores__", contadores)  # si existe, el global no se mira
```

`--contador graphics_level_size=448` **lo pasé** y no tuvo efecto, porque en
cuanto una función tiene cualquier sentencia reconocida la clave existe, y el
`.get` con valor por defecto ya nunca llega a mirar `contadores`.

Esto no es un bug de entrada perdida: es un **shadow que no avisa**. La
herramienta acepta el argumento, no avisa de que lo ignora, y sale un
`NO_RESUELTO` que parece un límite del corpus. Es de la misma familia que el
número falso: **lo que parece un dato del mundo es en realidad un dato mío**.

## Tres errores míos en la verificación, y los tres en la herramienta

Al comprobar el arreglo escribí un script de contraste y **falló tres veces,
siempre en mi contra**:

| intento | qué dijo | realidad |
|---|---|---|
| 1 | `:2398` sin resolver | el destino ocupa **dos líneas**; mi regex no cruzó |
| 2 | `:149` da `708..731`, falso | `:149` no tiene `tam=` propio; el regex corrió hasta `:157` |
| 3 | 7 correctos, 1 falso | el recuento real es 8 correctos, 0 falsos |

En los tres, `smc_copy_scope` tenía razón y mi comprobación mintió. Dos causes:
normalizar la salida con `\n\s+ → espacio` **fusiona líneas que la herramienta
delimita deliberadamente**, y un `re.search` con `.*?` no tiene solución cuando
el campo buscado falta en esa línea: se fuga a la siguiente.

**La lección**: una herramienta que tiene un campo ausente y un script que no lo
distingue del siguiente producen un veredicto falso, no una ausencia. Cuando el
contraste y la herramienta discrepan, **antes de acusar a la herramienta hay que
comprobar que el contraste está leyendo lo que dice leer**. Por eso la
verificación definitiva está en la salida literal del fichero, línea a línea, sin
regex.

## Lo que NO afirmo

- **NO** afirmo que `:2118` se ejecute en mi placa. `B_RUNTIME = NOT_EXECUTED`,
  sigue haciendo falta `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** afirmo el orden entre `:2398` y `:2118`. Sigue `NOT_DETERMINED`.
- **NO** he tocado `artifacts.py` ni `atomrom.py`. Son del otro agente.
- **NO** he medido hardware, ni escrito en `/sys`, ni cargado módulos.

## Estado de la herramienta

`smc_copy_scope` 1.3.0 — **`VALIDATED`**, 22 vectores, `exit=0`, y con el
defecto reintroducido `exit=3`.

Sobre el fichero real, con las entradas completas de gcc: **8 rangos correctos,
0 falsos, 4 sin resolver de los que 3 son `PROVEN_ABSENT`**.

Con 1.2.0 el mismo comando daba **1 falso**. El arreglo no solo subió el recuento
de `VIVA`: **quitó el número inventado**, que era lo que podía contaminar una
conclusión sin que nadie lo notara.

## Frontier siguiente

**El shadow de `:813`, y el `sizeof` a secas de `:745`.** Son dos líneas y el
criterio de cierre es limpio: `:149` debe dar `236..683 448B` **sin** que haya que
pasar `--contador graphics_level_size`, porque el valor está en `:128` y una
herramienta que no lo ve está leyendo menos de lo que el fichero dice.

Tres formas de cerrarlo, y solo dos son defendibles:

- Que `:128` entre en `__contadores__` cuando `sizeof(...)` resuelva en `sizes`.
  Es lo correcto: el dato está en el fichero.
- Que `:813` **fusione** en vez de sustituir:
  `{**contadores, **ctx_amb.get("__contadores__", {})}`. Los locales ganan, que
  es lo que dice el comentario de `:742`, y los globales siguen visibles.

La tercera, que es la que hice para cerrar `:157`, sería **no arreglar el shadow
y documentarlo**. Eso convierte un defecto en un requisito de uso, y es
precisamente lo que `278`LKWarn criticaba: una herramienta a la que hay que
alimentarle cada hueco.

**Y hay una comprobacion que falta en el fixture y que es la que de verdad
importa**: que **ningún** `--contador` pasado por línea de órdenes se pierda en
silencio. Hoy ninguno se pierde sin avisar, pero tampoco hay nada que lo
compruebe.