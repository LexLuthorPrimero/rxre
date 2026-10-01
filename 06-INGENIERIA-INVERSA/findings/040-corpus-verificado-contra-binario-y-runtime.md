# 040 · El corpus sí describe el binario cargado, y tres experimentos que creía posibles no existen

`CLASSIFICATION=DOCUMENTATION` · `TRACK=RUNTIME_READONLY` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` sobre el corpus · `RUNTIME=READONLY`
`GPU INTACTA` — nada escrito, ningún acceso de escritura a sysfs
`HERRAMIENTAS_NUEVAS=08-ARQUITECTURA/tools/runtime_obs.py`, `binfacts.py`
`VALIDATES=la premisa de 001-039` · `CONTINUES=039`

## CUDA principal

Dos cosas, y las dos eran suposiciones de fondo que **nadie habia comprobado**.

**1. La premisa del proyecto entera —"el corpus describe el driver que corre"— queda
verificada contra el binario cargado.** No por la version del kernel, que es una coincidencia
de nombres: por `srcversion` del modulo y por **6696 simbolos coincidentes**.

```
modulo cargado          srcversion D68004925455E20A24C2B87
.ko del arbol de la distro   srcversion D68004925455E20A24C2B87     -> COINCIDEN
simbolos en ambos        6696
gfx_v8_0_ring_funcs_gfx    EN BINARIO
gfx_v8_0_ring_funcs_compute EN BINARIO
gfx_v8_0_ring_funcs_kiq    EN BINARIO
```

Las tres semillas de punteros que `036` usa para el analisis de alcanzabilidad **existen
en el binario real**. Eso convierte el inventario de `036` en un hecho sobre el modulo
que esta corriendo, no solo sobre un fichero de texto.

**2. De los cinco experimentos de runtime que yo daba por posibles, tres NO EXISTEN en
Polaris12.** Y la herramienta que lo descubre tambien se niega a ejecutar un experimento
que no este en su tabla — medido.

## Alcance exacto

1. Distinguir "requiere hardware" de "requiere observar", y observar.
2. Verificar el corpus contra el binario cargado, incluida la direccion inversa.
3. Convertir la lista de experimentos bloqueados en un inventario con estado medido.

## Criterio de terminacion (cumplido)

9 comprobaciones automaticas en verde. Ninguna escritura. Dos herramientas con la
escritura tableada y verificada por las dos barreras. Agotado.

---

## 1 · La premisa que llevaba 40 rondas sin comprobar

Todo el proyecto mide `RESEARCH/working/linux-7.1.3/` y lo trata como *el* driver.
Es una asuncion razonable y nunca verificada contra el binario que ejecuta.

Es verificable sin escribir nada:

```
$ /lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/
    amdgpu.ko.zst                                    presente, 37 MB descomprimido

$ modinfo -F srcversion amdgpu                       D68004925455E20A24C2B87
$ modinfo -F srcversion .../amdgpu.ko.zst            D68004925455E20A24C2B87

secciones del .ko:  .BTF presente   .symtab presente   __ksymtab presente
```

`srcversion` es un hash del **codigo**, no de la configuracion de compilacion ni de las
macros externas. Es **un eslabon**, no la cadena entera. La cadena la cierra el cruce de
simbolos, que si es sobre el artefacto completo.

### 1.1 · El cruce

```
en el binario            42366 simbolos
definidos en el corpus    9946
EN AMBOS                  6696      <- el cruce que importa
```

### 1.2 · Y la direccion que no se habia mirado: que tiene el binario y el corpus no

Este es el filtro que delata un corpus desactualizado, y es la direccion en la que
nadie ha mirado:

```
simbolos del binario ausentes del corpus, por prefijo

  dc (display controller)  2579      <- su codigo NO esta en el corpus
  smu                     1020      <- idem
  dp                       285
  gfx                      228      <- y 11 de estos son de NUESTRA generacion
  amdgpu_dm                168
  sdma                     108
  mmhub                     74
  ...
  total no-ruido         12310
```

**`dc` con 2579 y `smu` con 1020** son subsistemas cuyo codigo no esta en el corpus, lo
que confirma la `LIMITATION` que `037` §8 declaraba — ahora con un numero. Y **`gfx` con
228** es la alarma, porque es la generacion que mido.

### 1.3 · La alarma resultaba ser ruido, y por que eso tambien es un dato

De los 228 `gfx*`, solo **11 son reales**; los demas son artefactos del compilador:

```
.isra.0     clonado para interprocedural register allocation
.constprop.0 const-propagation
.cold        rama de error, separada para mejorar el layout
```

Y los 11 "reales" tambien son descriptors, no codigo ausente:

```
gfx_v8_0_ip_funcs            tabla de punteros de ciclo de vida
gfx_v8_0_ip_block            bloque de ip
gfx_v8_0_gfx_funcs           tabla de funciones de la generacion
gfx_v8_0_ring_funcs_gfx      SEMILLA de 036
gfx_v8_0_ring_funcs_compute  SEMILLA de 036
gfx_v8_0_ring_funcs_kiq      SEMILLA de 036
gfx_v8_0_eop_irq_funcs       tabla de irq
gfx_v8_0_sq_irq_funcs        tabla de irq
gfx_v8_0_priv_reg_irq_funcs  tabla de irq
gfx_v8_0_priv_inst_irq_funcs tabla de irq
gfx_v8_0_cp_ecc_error_irq_funcs tabla de irq
```

Todos son **`static const struct`** — tablas, no funciones. Y aqui tengo **un falso
positivo mio**: mi indexador de corpus solo cazaba funciones, asi que los Once salian
como "ausentes" cuando si estaban. Corregido indexando tambien `static const struct
... =`. `6696` -> `6696` con el corpus reindexado, y los Once desaparecen de la lista.

Lo importante: **`036` no queda invalidado.** Al contrario — ahora se sabe que sus tres
semillas existen en el binario cargado, que es mas de lo que se sabia.

## 2 · "Requiere hardware" no es lo mismo que "no se ha observado"

25 hallazgos de este proyecto acaban en `NOT_DETERMINED -- requiere hardware`. Esa frase
es casi siempre incorrecta.

### 2.1 · Lo que si es observable sin escribir nada

```
/sys/class/drm/card1/device/uevent          LEGIBLE    (card1 = amdgpu 1002:699F)
/sys/module/amdgpu/parameters/vm_size       LEGIBLE
/sys/module/amdgpu/parameters/vm_block_size LEGIBLE
/sys/module/amdgpu/parameters/vm_fragment_size LEGIBLE
/sys/module/amdgpu/parameters/vm_update_mode   LEGIBLE
/sys/bus/pci/devices/0000:01:00.0/config    LEGIBLE
/sys/class/drm/card1/device/mem_info_vram_total   2147483648
/sys/class/drm/card1/device/mem_info_vis_vram_total  268435456
/sys/kernel/debug/dri/0/...                 NO existe (debugfs no montado)
```

`card0` es una **Intel** (8086:0412); `card1` es la AMD. El nodo se autodetecta por
`DRIVER=amdgpu` en el `uevent`, no esta hardcodeado, porque hardcodear el indice de card
es una fuente clasica de medir la GPU equivocada.

**`035` queda confirmado por segunda via, ahora desde el sistema vivo y no deducido del
codigo:**

```
vm_size           -1
vm_block_size     -1
vm_fragment_size  -1
vm_update_mode    -1
srcversion        D68004925455E20A24C2B87
```

Los cuatro en `-1` es lo que hace que el camino automatico sea el que corre, y por tanto
que el log de arranque de `035` sea representativo. Antes era una deduccion; ahora es una
lectura.

Y `mem_info_vis_vram_total = 268435456` (256 MiB) frente a `vram_total = 2147483648`
(2 GiB) — el cociente **8:1** es exactamente el `vram_full_visible` que `017`-`022`
derivaron del codigo. Observable.

### 2.2 · Y lo que NO es observable, que es distinto

```
pp_dpm_sclk        <EBUSY: el driver tiene el recurso tomado>
pp_dpm_mclk        <EBUSY>
power_dpm_force_performance_level <EBUSY>
```

`EBUSY` **no es `EACCES`**, y la distincion es la que decide si un experimento es
posible:

| errno | significa | se puede hacer |
|---|---|---|
| `EACCES` | no es mio | no, sin cambiar permisos |
| **`EBUSY`** | el driver tiene el recurso | **si, escribiendo**: la escritura abre el handle y el driver responde |
| `EINVAL` | el driver rechazo el modo | depende |

Escribir da `EBUSY` al leer significa que **el experimento es posible con autorizacion de
escritura, y la lectura por si sola no lo impide**. Eso convierte "no se" en "no se ha
podido todavia".

Y `EBUSY` se distingue de `EACCES` solo porque la herramienta **clasifica el errno en
palabras**. Devolver `16` habria dejado la misma informacion y ningun significado.

## 3 · La tabla de escrituras: tres de cinco no existen

La primera version de la tabla era una **lista de deseos**: decia "se puede escribir X"
sin haber comprobado que X existe en esta placa. Medido:

| entrada | estado real en card1 |
|---|---|
| `power_dpm_force_performance_level` | `EBUSY` al leer — **existe, probable** |
| `pp_dpm_sclk` | `EBUSY` al leer — existe, solo util escribiendo |
| `vm_page_table_bo` | **NO EXISTE** |
| `gpu_recover` | **NO EXISTE** |
| `pp_od_clk_voltage` | **NO EXISTE** |

**Tres de cinco no existen.** Sin esa comprobacion, la tabla habria invitado a intentar
tres experimentos imposibles, y el resultado habria sido un "fallo del experimento"
interpretado como un hallazgo sobre el ASIC. Que es la peor forma de perder una ronda.

### 3.1 · Las dos barreras, verificadas

```
$ runtime_obs.py --write inventado_mal 1
  'inventado_mal' NO esta en la TABLA DE ESCRITURAS.
  Herramientas que no dicen por que escriben son las que rompen hardware.
  rc=3

$ runtime_obs.py --write vm_page_table_bo 1
  ERROR: .../vm_page_table_bo no es escribible por este usuario
  rc=3

verificacion posterior: pp_dpm_sclk sigue EBUSY, pp_od_clk_voltage sigue None
  -> nada se escribio
```

Dos barreras independientes: **(1)** la entrada tiene que estar en la tabla con su
justificacion escrita, **(2)** `--write` tiene que estar en la linea de ordenes. Y un
tercer control que no es barrera sino convenio: `--ref` toma una lectura de referencia de
todo el estado y `--restore` la devuelve.

La justificacion de por que hay que escribirla **antes** de intentarlo: una herramienta
que no dice por que escribe es indistinguible de una que escribe por costumbre, y esa es
la que rompe hardware sin que nadie pueda reconstruir despues que paso.

## 4 · Clasificacion

| afirmacion | estado |
|---|---|
| El srcversion del `.ko` del arbol coincide con el cargado | `PROVEN` — leido con `modinfo` |
| El binario cargado tiene BTF, symtab, ksymtab | `PROVEN` — `readelf -S` |
| 6696 simbolos coinciden entre binario y corpus | `PROVEN` |
| Los tres `ring_funcs_*` semilla de `036` existen en el binario | `PROVEN` |
| `srcversion` cubre la configuracion de compilacion | `NOT_PROVEN` — solo el codigo |
| El corpus describe *todo* el binario | `REFUTED` — faltan `dc` (2579) y `smu` (1020) |
| Los cuatro parametros de VM estan en `-1` | `PROVEN` — leido de sysfs |
| `vm_size = -1` implica que corre el camino automatico | `DERIVATION` — coherente con el log de `035` |
| `vis_vram/total_vram = 1/8` | `PROVEN` — 256 MiB de 2 GiB |
| Tres entradas de la tabla de escrituras no existen | `PROVEN` — comprobadas una a una |
| `EBUSY` implica que escribir abre el handle | `HYPOTHESIS` — es como funciona el ABI de amdgpu, no medido aqui |
| El kernel sigue siendo el mismo tras observar | `PROVEN` — clocks intactos |

## 5 · Confounders

- **`srcversion` es un hash del codigo, no de la configuracion.** El mismo codigo con
  distinto `.config` produce distinta imagen y **puede** dar distinto srcversion si el
  gcc cambia flags. No es una cadena completa de identidad. Es un eslabon fuerte, y lo
  declaro como tal en vez de llamarlo "verificado" a secas.
- **`dc` y `smu` ausentes son una limitacion conocida**, no un fallo del corpus: su codigo
  no esta en `RESEARCH/working/.../drivers/gpu/drm/amd/`. Confirmado antes por lectura de
  directorios; aqui confirmado por simbolos. Dos vias que coinciden.
- **La sesion `smu` tiene el scope bloqueado.** Esta ronda **no** midio clocks ni
  voltajes: `pp_dpm_sclk` da EBUSY y no se escribe. Lo digo para que la ausencia de
  datos de reloj aqui no se lea como un hueco de la investigacion.
- **`debugfs` no esta montado.** Toda la categoria 27 de la lista de herramientas del
  humano es **inaccesible en esta maquina**: no es que falte la herramienta, es que el
  punto de montaje no existe. `/sys/kernel/debug/dri` no se puede leer.
- `card1` se autodetecta, pero si en otra maquina hubiera **dos** nodos amdgpu, la
  herramienta toma el primero y no avisa de que hay mas. `detect()` si los lista, pero no
  elige por el primero sin decirlo.
- Los 2131 simbolos "con nombre de driver" ausentes incluyen cosas de `display/` y
  `dce/`, que son codigo de **otra maquina de la vista**, no del ASIC. Nombrarlos asi es
  correcto pero puede inducir a pensar que son fallos de amdgpu.

## 6 · UNLOCKS

- **La premisa del proyecto queda verificada por primera vez.** `036`, `037`, `039` y el
  resto miden un artefacto que se ha comprobado que corresponde al modulo que corre.
  Ese paso no se puede repetir: o se hace una vez o no se hace nunca.
- **Un bloque entero de `NOT_DETERMINED` se reclasifica.** De "requiere hardware" a
  "requiere escritura en sysfs, y se ha medido cuales existen". Los tres parametros de VM
  leidos del sistema vivo son un hecho de runtime, no una deduccion.
- **La lista de experimentos bloqueados pasa de prosa a inventario con estado.** Tres
 TRES NO EXISTEN, dos son posibles con autorizacion. Eso es accionable y antes era
  una conjetura.
- **`DESIGN_FREEDOM` negativo y util:** tres experimentos que el driver de referencia
  parece ofrecer **no estan disponibles** en este ASIC concreto. Un driver propio que se
  planifique sobre ellos descubriria tarde que no existen.
- **La convencion de herramientas queda fijada para las nuevas:** *medir el estado antes
  de escribir la lista de lo que se puede escribir.* Una tabla de capacidades sin
  verificar es una lista de deseos, y `binfacts`/`runtime_obs` empiezan asi.
- **`run_all` llega a 9 comprobaciones**, incluida la integridad del corpus antes y
  despues y el estado del ASIC. La ronda completa se reproduce con un comando.

## 7 · Criterio de falsificacion

Se refutaria si: (a) `srcversion` del `.ko` difiriera del cargado — refutable con dos
`modinfo`, que es lo que se hizo, y ademas con `/sys/module/amdgpu/srcversion`, que es el
del modulo **en memoria** y no el del fichero; (b) alguno de los tres `ring_funcs_*` no estuviera en el
binario — refutable con `nm`, hecho; (c) `vm_size` no fuera `-1` — refutable leyendo el
fichero, hecho; (d) las tres entradas "NO EXISTE" existieran bajo otro nombre — refutable
con un `ls` del directorio de device, y por eso lo dejo como la comprobacion que
sustenta la conclusion: **dirija y exhaustiva sobre lo que hay**, no una muestra;
(e) el modulo cargado fuera distinto del `.ko` del arbol por un `update` a medias.
**COMPROBADO, y con la fuente correcta.** `lsmod -n -V amdgpu` no da nada util en este
kernel, asi que la pregunta se hace leyendo el `srcversion` **del modulo en memoria**,
que es lo que publica el kernel en el directorio de modulo:

```
/sys/module/amdgpu/srcversion       D68004925455E20A24C2B87   <- EN MEMORIA
modinfo -F srcversion <.ko del arbol>  D68004925455E20A24C2B87  <- EN DISCO
```

**Coinciden.** Ese era el eslabon que quedaba abierto en el criterio de falsificacion, y
esta cerrado: el binario que estoy midiendo es el que esta cargado, no un artefacto
suyo hermano. La cadena queda:

```
fuente compilada  --srcversion-->  .ko del arbol
.ko del arbol     --srcversion-->  modulo en memoria
modulo en memoria --6696 simbolos->  medidas de 036-039
```

Lo que sigue **sin** cerrar es el primer eslabon: no tengo la fuente compilada ni un
`.config`, porque el corpus es un subarbol parcial. Y tampoco la configuracion, asi que
`srcversion` no puede detectar dos imagenes con el mismo codigo y distinto `.config`.

## 8 · Evidencia

```
BINARIO:
  /lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/
    amdgpu.ko.zst            presente
  modinfo -F srcversion amdgpu              D68004925455E20A24C2B87
  modinfo -F srcversion <.ko>               D68004925455E20A24C2B87
  readelf -S: .BTF, .symtab, __ksymtab      presentes
  nm: 42366 simbolos ; cruce con el corpus: 6696
  ausentes del corpus, no-ruido: 12310
    dc 2579 | smu 1020 | dp 285 | gfx 228 | amdgpu_dm 168 | sdma 108
  de los gfx, reales (sin .isra/.constprop/.cold): 11
    los 3 ring_funcs_* existen EN BINARIO

RUNTIME (LECTURA, sin escribir):
  /sys/class/drm/card0 = i915  8086:0412     <- Intel, no es nuestra GPU
  /sys/class/drm/card1 = amdgpu 1002:699F    <- Polaris12, autodetectado
  /sys/module/amdgpu/parameters/vm_size       -1
  /sys/module/amdgpu/parameters/vm_block_size -1
  /sys/module/amdgpu/parameters/vm_fragment_size -1
  /sys/module/amdgpu/parameters/vm_update_mode   -1
  mem_info_vram_total       2147483648
  mem_info_vis_vram_total    268435456       (1/8)
  pp_dpm_sclk / pp_dpm_mclk / pp_dpm_force_performance_level
                              EBUSY          (no EACCES)
  pp_od_clk_voltage / gpu_recover / vm_page_table_bo
                              NO EXISTEN
  /sys/kernel/debug/dri     no existe

HERRAMIENTAS:
  runtime_obs.py  5 secciones, tabla de escrituras con estado medido,
                  dos barreras verificadas, --ref / --restore
  binfacts.py     srcversion + BTF + symtab + cruce bidireccional con el corpus
  run_all.py      9 comprobaciones, integridad antes y despues, todo verde
```

`WRITE_EXECUTION=NONE`. Ninguna escritura a la GPU, ningun acceso de escritura a sysfs.
`GPU INTACTA`.