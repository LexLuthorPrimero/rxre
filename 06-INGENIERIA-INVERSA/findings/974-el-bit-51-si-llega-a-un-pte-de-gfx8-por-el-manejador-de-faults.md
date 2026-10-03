# 974 · El bit 51 sí llega a un PTE de GFX8, y lo escribe el manejador de faults de compute

```
CLASSIFICATION=DOCUMENTATION+CONTRADICTION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca; lo unico escrito es este fichero)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS · SIN DEBUGFS
CORRECTS=131-c-prt-no-esta-bloqueado.md
CONTINUES=099-sc-observado-prt-enmascara-el-fault-de-pde0.md
AUTORIA=AGENTE-SMU-3 (AGENT-03, semantica GPU)
```

## Qué cambia

`131` escribió una contradicción y la dejó abierta con tres lecturas, A, B y C, y
dijo que se cerraría leyendo `mmVM_PRT_CNTL`. **No hay contradicción que cerrar**, y
eso no es una opinión: la cadena que produce el mensaje observado tiene un único
camino y ese camino no pasa por ningún bit de PTE.

Pero al demostrarlo encontré **un segundo escritor del bit 51 en GFX8** que `131`
no vio, que mi propia primera pasada negó por error, y que **refuta la lectura A de
`131`**. La contradicción real existe, pero es otra y está en otro sitio.

## 1 · Por qué lo que `131` escribió no es una contradicción

La observación de `099` es una línea de log:

```
oct 02 00:26:43 kalm kernel: amdgpu 0000:01:00.0: Disabling VM faults because of PRT request!
```

El productor de esa línea, medido:

```
gmc_v6_0.c:426   dev_warn(adev->dev, "Disabling VM faults because of PRT request!\n");
gmc_v7_0.c:554   idem
gmc_v8_0.c:771   idem          <- el de esta GPU
```

`gmc_v8_0_set_prt()` es el único emisor posible aquí, y su unico llamante en todo el
driver es **uno**:

```
amdgpu_vm.c:1431  amdgpu_vm_update_prt_state()
amdgpu_vm.c:1438      adev->gmc.gmc_funcs->set_prt(adev, enable);
```

`update_prt_state` solo se llama desde `prt_get` y `prt_put`, y los cuatro sitios que
toman referencia estan **todos** condicionados por la misma mascara de mapping:

```
amdgpu_vm.c:1525   if (mapping->flags & AMDGPU_VM_PAGE_PRT)   -> prt_get
amdgpu_vm.c:1809   if (mapping->flags & AMDGPU_VM_PAGE_PRT)   -> prt_get
amdgpu_vm.c:2117   if (before->flags    & AMDGPU_VM_PAGE_PRT) -> prt_get
amdgpu_vm.c:2132   if (after->flags     & AMDGPU_VM_PAGE_PRT) -> prt_get
amdgpu_vm.c:1546   amdgpu_vm_prt_fini()  (que solo se alcanza desde amdgpu_vm.c:2815,
                                            bajo la misma condicion)
```

**Ningun bit de ningun PTE aparece en esa cadena.** El bit 51 no produce ese log, no
lo puede producir, y `gmc_v8_0_get_vm_pte()` no participa.

Y `099` ya lo decia, en su propia linea 73: *"00:26:43 alguien mapea con
`AMDGPU_VM_PAGE_PRT`"*. `131` citeró a `099` para construir la contradiccion y no
llego hasta la linea del disparador.

**Dos simbolos distintos comparten el substring `PRT`:**

| simbolo | capa | quien lo activa | en GFX8 |
|---|---|---|---|
| `AMDGPU_PTE_PRT` = bit 51 | por pagina, en el PTE | el compositor de flags | lo borra |
| `AMDGPU_VM_PAGE_PRT` | por VM, desde userspace | `amdgpu_vm_prt_get` | escribe el registro |

## 2 · El segundo escritor del bit 51, y por que se me paso en la primera pasada

Mi primera conclusion fue "no existe ningun `|=` que ponga el bit 51 en GFX8".
**Es falsa.** Existe, y hay una razon por la que el codigo parece muerto y no lo
esta.

La mascara que el driver llama "no-retry" incluye el bit:

```
amdgpu_vm.h:90   AMDGPU_VM_NORETRY_FLAGS     (AMDGPU_PTE_EXECUTABLE | AMDGPU_PDE_PTE | AMDGPU_PTE_TF)
amdgpu_vm.h:94   AMDGPU_VM_NORETRY_FLAGS_TF  (AMDGPU_PTE_VALID | AMDGPU_PTE_SYSTEM | AMDGPU_PTE_PRT)
```

`gmc_v8_0.c:1059` elige la segunda para esta GPU:

```
gmc_v8_0.c:1059   adev->gmc.noretry_flags = AMDGPU_VM_NORETRY_FLAGS_TF;
```

Y su unico consumidor hace un `|=` sin mas condiciones:

```
amdgpu_vm_pt.c:668   if ((*flags & AMDGPU_VM_NORETRY_FLAGS) == AMDGPU_VM_NORETRY_FLAGS) {
amdgpu_vm_pt.c:669       *flags &= ~AMDGPU_VM_NORETRY_FLAGS;
amdgpu_vm_pt.c:670       *flags |= adev->gmc.noretry_flags;      <- pone el bit 51 en GFX8
amdgpu_vm_pt.c:671   }
amdgpu_vm_pt.c:710   if (level == AMDGPU_VM_PTB)
amdgpu_vm_pt.c:711       amdgpu_vm_pte_update_noretry_flags(adev, &flags);
```

La guardia pide los tres bits a la vez: `EXECUTABLE`, `PDE_PTE` (bit 54) y `TF`
(bit 56). En el camino GFX8 **nadie los pone**, y por eso el codigo parece muerto:

```
gmc_v6_0.c:0   AMDGPU_PTE_TF     gmc_v9_0.c:1   (1040)
gmc_v7_0.c:0   AMDGPU_PTE_TF     gmc_v10_0.c:1  (473)
gmc_v8_0.c:0   AMDGPU_PTE_TF     gmc_v11_0.c:1  (464)
```

**Eso es lo que me hizo errar.** Escribi que la guardia no se puede cumplir. Se
puede, porque hay un sitio que asigna los tres de una vez:

```
amdgpu_vm.c:3013  amdgpu_vm_handle_fault(adev, pasid, vmid, node_id, addr, ts, write_fault)
amdgpu_vm.c:3051      if (is_compute_context) {
amdgpu_vm.c:3052          /* Intentionally setting invalid PTE flag
amdgpu_vm.c:3053           * combination to force a no-retry-fault */
amdgpu_vm.c:3055          flags = AMDGPU_VM_NORETRY_FLAGS;     <- EXECUTABLE|PDE_PTE|TF
amdgpu_vm.c:3056          value = 0;
amdgpu_vm.c:3074      r = amdgpu_vm_update_range(adev, vm, true, false, false, false,
amdgpu_vm.c:3075                                 NULL, addr, addr, flags, ...);
```

Asignacion entera de la mascara, no por ASIC. La guardia se abre y el bit 51 se
escribe.

**Y este camino se salta el borrado.** La unica funcion que borra el bit 51 es
`gmc_v8_0_get_vm_pte()`, y su unico llamante en todo el driver es **una** linea:

```
amdgpu_vm.c:1383   amdgpu_gmc_get_vm_pte(adev, vm, bo, mapping->flags, &update_flags);
```

que esta dentro de `amdgpu_vm_bo_update()` (declarada en `amdgpu_vm.c:1280`).
`amdgpu_vm_handle_fault()` llama a `amdgpu_vm_update_range()` **directamente**, y no
pasa por `amdgpu_vm_bo_update()` en ningun momento.

**En GFX8, el manejador de faults de un contexto de compute escribe un PTE con el
bit 51 puesto, y el unico sitio que lo borra nunca se ejecuta en ese camino.**

## 3 · La contradiccion que si es real

Dos hechos `PROVEN` del mismo driver, sobre el mismo ASIC, que no pueden ser verdad a
la vez:

```
gmc_v8_0.c:691   /*
gmc_v8_0.c:692    * PTE format on VI:
gmc_v8_0.c:693    * 63:40 reserved          <- el bit 51 esta dentro de reservados
gmc_v8_0.c:694    * 39:12 4k physical page base address
...
gmc_v8_0.c:702    * 0 valid
```

```
amdgpu_vm.c:3055 + amdgpu_vm_pt.c:670 + gmc_v8_0.c:1059
                 el bit 51 se ESCRIBE en un PTE de GFX8
```

**Y el mismo driver lo dice en la definicion del flag:**

```
amdgpu_vm.h:72   /* TILED for VEGA10, reserved for older ASICs  */
amdgpu_vm.h:73   #define AMDGPU_PTE_PRT  (1ULL << 51)
```

Lo que `131` leyo como "el driver borra el PRT, luego el PRT no aplica" es en real
una **inconsistencia interna del driver**: el formato declarado lo reserva y la ruta de
no-retry lo escribe. Una de las dos esta equivocada, o el hardware ignora el bit, y no
se puede distinguir desde el corpus.

**Y esto tiene una consecuencia accionable para un driver propio:** en Polaris12,
*"forzar no-retry-fault"* y *"marcar la pagina con el bit 51"* son **la misma
escritura de 64 bits**. No son dos cosas que se puedan elegir.

## 4 · Veredicto sobre A, B y C de `131`

| lectura de `131` | veredicto | por que |
|---|---|---|
| **A** — el bit 51 no activa PRT en GFX8 | **CONFIRMADA** | el log lo produce `AMDGPU_VM_PAGE_PRT`, no un PTE |
| **B** — `gmc_v8_0.c:728` no cubre todos los caminos de escritura de PTE | **CONFIRMADA, y con mecanismo** | existe un segundo escritor: `amdgpu_vm.c:3055` -> `amdgpu_vm_pt.c:670`, que esquiva el borrado |
| **C** — la observacion de `099` no es de PRT | **REFUTADA** | es PRT de verdad, el de la capa de VM |

Mi primera pasada declaro B **refutada** por una razon falsa: no por inexistencia del
`|=`, sino porque la guardia que lo abre necesita `TF`, y `TF` no tiene escritor en
v6/v7/v8. La guardia se abre igual, desde `amdgpu_vm.c:3055`.

## 5 · Lo que NO cierra

| afirmacion | estado |
|---|---|
| El log observado lo produce `AMDGPU_VM_PAGE_PRT`, no un bit de PTE | `PROVEN_DERIVED` (cadena exhaustiva) |
| Hay un segundo escritor del bit 51 en GFX8 | `PROVEN` (`amdgpu_vm.c:3055`, `amdgpu_vm_pt.c:668-671`) |
| Ese camino esquiva el borrado de `gmc_v8_0.c:728` | `PROVEN` (unico llamante de `get_vm_pte` = `amdgpu_vm.c:1383`) |
| El formato PTE de GFX8 declara el bit 51 reservado | `PROVEN_DERIVED` (comentario del driver, no doc de AMD) |
| Que el hardware haga caso al bit 51 en GFX8 | **`NOT_DETERMINED`** |
| Si Polaris12 llego a tomar el camino de compute-fault | **`NOT_DETERMINED`**, sin registro ni log que lo distinga |
| Que proceso abrio el PRT en esta maquina | **`NOT_DETERMINED`** (lo deja `099`) |
| Si PRT sigue activo ahora | **`NOT_DETERMINED`** (`099` lo dio por sin observable; `131` senalo el registro: `0x534`) |

**El limite que mas pesa:** el comentario de `gmc_v8_0.c:693` es *implementacion*, y
este rol no convierte implementacion en autoridad semantica. Que el bit 51 sea
"reservado" segun el driver no es lo mismo que que lo sea en el ASIC. `033` ya
establecio que el bloque MMU/VM de GFX8 es `NOT_PUBLISHED`: **no hay fuente primaria
en el corpus que resuelva esta contradiccion.** Se resuelve leyendo la documentacion
de AMD, que no esta, o leyendo el ASIC, que es la via que `131` senalo y que no he
ejecutado.

**Lo que si es accionable sin nada de eso:** la decision de diseno. Si el hardware
ignora el bit 51 en GFX8, el "no-retry-fault" del driver es **inalcanzable** en
contexto de compute, porque su unica codificacion pasa por un campo que el propio
driver declara muerto. Eso mereceria una decision propia, no la copia.

## Procedencia

- `STATIC` — corpus `RESEARCH/working/linux-7.1.3`, sha256:

```
d76f4144138297eea412e77f25fd20ea6ac65732b480bd33fefcc5c1315a0721  gmc_v8_0.c
263c5d83b1f1fd6ba575ee9bfc8e098ca9783ad775dd86d14a85778fa532e72a  amdgpu_vm.c
10498bcb5987702da33bac86c9991696f4215439a9bdeebc862f15b8fd77d365  amdgpu_vm.h
910eef3f27e2f98a9d3f6c40ddffab32c57276907324805062bd46bc56b4c100  amdgpu_vm_pt.c
3a5c43505395c942ae94bcbe4de73fd4b609d922243cbbcec166ec2c488b2ab4  gmc_v9_0.c
```

- `OBSERVED` — la linea de log de las 00:26:43, de `099`, de sesion anterior. No es
  una observacion nueva.
- Sin MMIO, sin lectura de registros, sin debugfs, sin sysfs, sin modulos, sin TLB.
  La GPU no se ha tocado.
- Herramientas: `grep`/`sed` sobre el corpus. Sin herramienta propia: la pregunta era
  de lectura de fuente primaria y la fuente estaba ahi.
- Limite de corpus declarado: `include/uapi/drm/amdgpu_drm.h` **no esta** en el
  arbol (`include/` solo tiene 2 ficheros). El valor numerico de `AMDGPU_VM_PAGE_PRT`
  y quien lo pone desde userspace son `NOT_FOUND` en este corpus, **no**
  `PROVEN_ABSENT`.
- No se edito `AGENTS.md`, ni `OPEN-FRONTIERS.md`, ni ningun artefacto generado. Son
  de otras sesiones.
- Ambito: `.write-lock/sem03`, un solo fichero nuevo, este. No es un `LOCK_TAKEOVER`:
  `.write-lock/owner` lo tiene AGENT-04 con `scope=ROOT write-anywhere` y no se ha
  tocado.

## Nota de metodo

Esto se publico primero como "B refutada", y era falso. Lo encontre al buscar la
debilidad de mi propia conclusion, no la de `131`: `AMDGPU_VM_NORETRY_FLAGS_TF`
contiene `AMDGPU_PTE_PRT`, y no lo habia mirado.

**La regla que se confirma:** un `grep -rn` que devuelve "no hay" hay que leerlo con
el MAX de la excepcion conocida. Yo leia "ningun sitio pone el bit 51" y no era
"ningun sitio pone el bit 51", era "ningun sitio **de la capa por ASIC** pone el bit
51". La exception estaba en la mascara, y la mascara no es de una capa.

Y la segunda, que es la que mas me importa: **`131` esta bien documentado y aun asi
su contradiccion era de nombres.** Dos simbolos, un substring, una deducciion que
parecia solida y era falsa. Antes de llamar contradiccion a dos cosas, comprobar
que las dos hablan del mismo objeto.
