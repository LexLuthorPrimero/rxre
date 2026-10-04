# FILTROS-MAL-FORMADOS — el censo: cuántas herramientas devuelven un conjunto vacío por un filtro que no casó, sin decirlo

```
NODE            FILTROS-MAL-FORMADOS
CLASS           auditoria-de-alcance · SOLO LECTURA del arbol
WORK_CLASS      validacion-de-instrumento
GPU             INTACTA · no se ha tocado · no se ha abierto /dev/dri/* · no se ha escrito en sysfs
ESCRITURAS      1 fichero nuevo, este. NINGUNA herramienta editada. Ningun git add, ningun commit.
MEDICION        2026-10-04T13:19:53Z · kernel 7.1.3-200.nobara.fc44.x86_64 · Python 3.14.7
HERRAMIENTAS     os.walk / open() / ast.parse / hashlib / subprocess. SIN grep. SIN internet.
CORPUS DE PRUEBA RESEARCH/kernelbuild/linux-7.1.3 (el mismo que usan las propias herramientas)
```

## 0. Veredicto en una línea

**De 56 herramientas del proyecto que aceptan un nombre escrito por una persona y lo
comparan contra un conjunto, 13 pueden quedarse vacías sin decirlo. De los 16 argumentos
que lo hacen, 15 devuelven además `rc=0` — la clase indistinguible de un resultado
bueno. Y el peor caso medido no es una tabla vacía: es `trace_path.py --root <ruta que no
existe>`, cuya salida difiere de la del caso correcto en **una** línea de ocho, la última,
y ese número es el tamaño de la población que no se ha medido.**

Las otras 39 lo hacen bien, y **cuatro de ellas lo hacen bien en un filtro y mal en
otro** (`trace_path.py`, `msg_census.py`, `reg_census.py`, `revkit/regs.py`), que es la
prueba de que no es una manía del autor sino un criterio que existe en el proyecto y se
aplica unevenly.

---

## 1. El criterio del veredicto, y por qué no es «¿falla el filtro?»

El de 1050, enunciado:

> **¿puede devolver un vacío sin que el programa diga que no ha medido nada?**

No «¿el filtro compara bien?». Un filtro que compara bien y devuelve vacío porque de
verdad no hay nada **es un resultado**. El defecto es el filtro que devuelve vacío
porque el nombre *no casó*, y el programa que no distingue esos dos vacíos.

De aquí se siguen las tres clases del enunciado, y una cuarta que resultó necesaria:

| veredicto | qué lo decide |
|---|---|
| `VACIO_SILENCIOSO` | el conjunto puede quedar vacío y el programa no dice que el nombre no casó |
| `VACIO_DECLARADO` | el programa dice que no casó, **o** lista lo que sí hay, **o** sale con rc≠0 |
| `NO_VERIFICABLE` | no se puede decidir, y se dice por qué |
| `ETIQUETA_MUERTA` *(añadida)* | el argumento se declara, se acepta, y **no entra en el cálculo**: la cifra es correcta y la etiqueta que la acompaña no se ha comprobado |

`ETIQUETA_MUERTA` no estaba en el enunciado y hace falta: `inst_closure.py:841 --asi` no
puede vaciar nada porque no filtra, pero imprime `semillas del ASIC (dce999): N` con una
`N` calculada sin mirar `dce999`. Es el mismo atributo epistémico —una afirmación sobre
un nombre que nadie validó— con otro disfraz, y sin él el censo queda incompleto.

### El caso `rc=0` merece subclase propia, y es la que se prioriza

Un `rc≠0` es un fallo visible aunque la herramienta no lo explique: quien encadena
herramientas lo nota. Un `rc=0` con un resultado vacío **es indistinguible de un
resultado bueno**, y por tanto es el único caso donde el defecto puede sobrevivir a la
revisión. Todas las medidas de §4 llevan `rc` medido.

---

## 2. RECORTE, declarado

El árbol tiene 6375 ficheros registrados. Este censo **no los recorre todos**, y dice
qué deja fuera y por qué.

**Dentro (3824 ficheros, 261 `.py`):** todo lo que no sea `.git/`, `__pycache__/`,
`.opencode/`, `.write-lock/`.

**Excluido por ser fuente ajena:**
- `RESEARCH/` — corpus del kernel y notas de otro proceso. Herramientas como `hwip.py`
  lo *leen*, pero no es suyo: un defecto de filtro aquí no es del proyecto.
- `rx550-upstream-7.2.8/` — upstream de Linux.

**Excluido por no ser puerta del proyecto** (y por tanto no tener nada que certificar):
- `03-EXPERIMENTOS/*/harness/scripts/*.py` (3 con argparse: `analyze.py`, `compare.py`,
  `governor.py`, `c1_observer.py`, `c1_isolation_automator.py`) — arneses de un
  experimento concreto, con argv propio.
- `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/cli.py` — CLI del producto en
  desarrollo, no un instrumento de medida.
- `04-IMPLEMENTACION/rx550-driver/tools/corpus_manifest_check.py` — sí usa argparse, y
  además declara correctamente (`EXIT_UNUSABLE` en `:321-325`); se excluye del recuento
  por ser del driver, no del banco.

**Lo que sí se cuenta:** `tools/` (78 con argparse), `revkit/` (24), `08-ARQUITECTURA/tools/`
(20), `01-AUDITORIA/DOCUMENTATION-ROUTER/knowledge/src_registry.py` (1).

**Población de partida, medida:** 111 ficheros `.py` contienen `add_argument`; 99 tienen
al menos un `add_argument` **que toma un valor**; 301 llamadas de esas. Las 111→99 se
deben a 12 herramientas cuyo único `add_argument` está **dentro de un comentario**
(`toalaudit.py:422` es el caso fino: `add_argument("--x") es una declaracion;` — el
regex lo contaba como argumento y no lo es). Es un recorte declarado, no un descuido:
`docs/` y los `.md` no se han abierto porque no tienen argv.

---

## 3. Cómo se ha separado «filtro» de «no filtro»

De los 301 argumentos que toman valor, son **filtro** los que cumplen una de estas dos:

1. **el valor se compara contra un conjunto que la herramienta conoce** (`==`, `in`,
   `.startswith`, `re.match` sobre un catálogo) — sea de clase (`--solo`, `--clase`),
   de concepto (`--chain`, `--vias`, `--ciego`) o de configuración (`--chip`,
   `--asic`, `--gfx`, `--bloque`);
2. **el valor es una ruta** y la no-existencia de esa ruta es un filtro que puede callar.

**No son filtro**, y quedan fuera: `--limite`, `--top`, `--n`, `--depth`, `--json`,
`--verbose`, `--selftest`, `--version`, `--escribir`, `--out`, `--dest`, `--fichero`
cuando es *salida* (`huerfanos.py:176 --fichero` es un destino JSON, no un filtro), y
los `nargs=2` de dos ficheros (`snapshot.py --diff`, que además declara, §5).

De los 301, la puerta de §8 clasifica **87** en sus cuatro clases de filtro
(`CERRADO`/`CONFIG`/`RUTA`/`ABIERTO`) y deja 214 como banderas, números o rutas de salida.
Las dos cifras no coinciden exactamente porque el criterio de la puerta es un regex sobre
el nombre del flag y el de §3 es la lectura del uso: la puerta **sobrecuenta** (coge
`--fichero` de `pm4census.py`, que sí es filtro, y `--ordered` de `smc_copy_scope.py`,
que quizá no lo sea) y **no puede** detectar un filtro cuyo flag no está en sus cuatro
familias. Por eso el 87 es la lista de trabajo de §8, no el censo, y el censo es §4–§7.

---

## 4. `VACIO_SILENCIOSO` — 16 argumentos en 13 herramientas, 15 con testigo ejecutado

Ordenados por gravedad: primero los que convierten un vacío en una **afirmación sobre el
hardware**; después los que devuelven una tabla vacía; después los que anulan la
medición entera.

### 4.0 Los tres que son peores que una tabla vacía

---

#### `tools/trace_path.py:498 --root` — el más peligroso del proyecto

- **`add_argument`**: `tools/trace_path.py:498`
- **filtro**: `tools/trace_path.py:507` — `root = args.root or os.path.join(kernel, "drivers/gpu/drm/amd")`, y `Index(root)` en `:514` hace `os.walk(self.root)` en `:427`
- **cómo se calla**: una ruta que no existe no da error: `os.walk` no produce nada, el índice queda con **0 funciones**, y el veredicto por símbolo pasa a ser `N_CALLERS` (`tools/trace_path.py:648`) para **todos** los símbolos. El tamaño de la población se imprime, pero en la **última línea** (`:659`).
- **tipo de comparación**: existencia de ruta → no hay comparación; el filtro es «recorrer lo que hay»

MEDIDO, con control:

```
$ python3 tools/trace_path.py --kernel $K --root NO_EXISTE_ESTA_RUTA \
      --callers-of amdgpu_gc_atomic_cmdexec ; echo "rc=$?"
  INVERSO  amdgpu_gc_atomic_cmdexec                     N_CALLERS      -

  ficheros .c indexados: 0
rc=0

$ python3 tools/trace_path.py --kernel $K --root $K/drivers/gpu/drm/amd/amdgpu \
      --callers-of amdgpu_gc_atomic_cmdexec ; echo "rc=$?"
  INVERSO  amdgpu_gc_atomic_cmdexec                     N_CALLERS      -

  ficheros .c indexados: 304
rc=0
```

Diff de las dos salidas completas: **una línea de ocho.**

```
--- root=INEXISTENTE (0 ficheros)
+++ root=correcto (304 ficheros)
@@ -8 +8 @@
-  ficheros .c indexados: 0
+  ficheros .c indexados: 304
```

Un símbolo que existe en el driver y al que **nadie llama** da el mismo `N_CALLERS` que
un símbolo que no existe en un corpus que no se ha leído. `rc=0` en los dos casos.

Y el caso inverso, **dentro de la misma herramienta**, está bien: `--from`
(`tools/trace_path.py:493`) usa `:520`, un veredicto `NO_ENCONTRADO` distinto de todos
los demás, con nota `busqueda en todo el subarbol indexado`. Y `--chip`
(`:492`) valida contra el enum en `:510-512` con rc=2. La herramienta sabe hacerlo; lo
que no sabe es que `--callers-of` y `--root` son el mismo problema.

---

#### `tools/hwip.py:803 --chip` — un vacío convertido en conclusión de hardware

- **`add_argument`**: `tools/hwip.py:803`
- **filtro**: `tools/hwip.py:887` — `hard = hardcodeados(c, args.chip)`, que busca `case <chip>:` (`:167`, `re.match(r"\s*case\s+%s\s*:" % re.escape(chip), ln)`)
- **cómo se calla**: `:895-900` convierte el vacío en una afirmación afirmativa
- **tipo de comparación**: regex contra el enum de `amd_asic_type.h`

MEDIDO. Las 33 etiquetas reales van de `CHIP_ALDEBARAN` a `CHIP_YELLOW_CARP`.

```
$ python3 tools/hwip.py --kernel $K --chip Polaris12 ; echo "rc=$?"
...
  NINGUNO. Ningun `case Polaris12:` del corpus escribe
  adev->ip_versions[] con un valor constante.

  Consecuencia directa: para esta GPU, TODAS las versiones de IP
  se leen de la tarjeta. No hay ningun atajo estatico.
rc=0
```

Idéntico con `--chip CHIP_POLARIS12`, `--chip chip_polaris12`, `--chip CHIP_POLARIS1`,
`--chip CHIP_POLARIS12X`: los cinco dan el mismo `NINGUNO` y el mismo `rc=0`. El
nombre que una persona escribe natural (`Polaris12`) es exactamente el que no casa.

Y esto **no es un vacío hipotético**: para `CHIP_POLARIS12` el resultado correcto también
es `NINGUNO`. O sea que en esta herramienta el vacío con nombre bueno y el vacío con
nombre malo son **indistinguibles por construcción**, y el texto que sale afirma algo
del hardware. La sección 5 del mismo informe sí degrada a `INCOMPLETA` cuando el chip
no existe (líneas 115-127 del diff), pero la sección 3 afirma igual, y `rc=0` en ambos.

---

#### `tools/rx550/regctx.py:376 --prefix` — la cifra no depende del filtro

- **`add_argument`**: `tools/rx550/regctx.py:376`
- **filtro**: `tools/rx550/regctx.py:205` — `accs = [a for a in accs if a["reg"] and a["reg"].startswith(prefix)]`
- **cómo se calla**: `report()` imprime `accesos totales`, `offset UNICO` y `conflicto REAL` (`:216-218`) **derivados de la lista ya filtrada**, sin ninguna declaración
- **tipo de comparación**: `.startswith`

MEDIDO:

```
$ python3 tools/rx550/regctx.py $K --prefix gfx_v8_0
regctx 2.0 — offset por GRAFO DE INCLUDES
  accesos totales  0
  offset UNICO     0   <- lo que veria el preprocesador
  conflicto REAL   0   <- >0 seria hallazgo del corpus
  ...
    cabeceras no definen el simbolo      : 51
rc=0

$ python3 tools/rx550/regctx.py $K --prefix gfx_9_0     # no existe en GFX8
  accesos totales  0
  offset UNICO     0
  conflicto REAL   0
  ...                                            rc=0
```

Las dos salidas son idénticas. Y el control sale igual: **`accesos totales 0` con el
prefijo correcto también**. Es decir: el titular de esta herramienta (`conflicto REAL 0`,
queAGENTS.md leería como «no hay conflicto de offset») no distingue «no hay conflicto» de
«no he medido nada». Es el hallazgo 1048 con otro nombre.

### 4.1 Los que devuelven tabla vacía con rc=0

---

#### `tools/fingerprint.py:513 --solo` — la puerta de verificación de target

- **`add_argument`**: `tools/fingerprint.py:513` (`metavar="CLAVE"`)
- **filtro**: `tools/fingerprint.py:533` — `filas = [f for f in r["filas"] if not a.solo or f["clave"] == a.solo]`
- **tipo de comparación**: `==` exacto
- **claves reales** (MEDIDO, las 12): `asic, bar_registro, board, cpu_model, driver, gpu_id, gpu_nombre, igpu_id, ip_gmc, ram_instalado, ram_os_total, vram`

MEDIDO:

```
$ python3 tools/fingerprint.py --solo asic            # control
  asic           journalctl (artefacto)   COINCIDE       POLARIS12
  VEREDICTO: TARGET_PARCIAL
rc=0

$ python3 tools/fingerprint.py --solo asicc           # una c de más
  campo          productor                estado         valor
  --------------------------------------------------------------------------
  VEREDICTO: TARGET_PARCIAL
  Hay campos sin observar. No es MATCH, ...
rc=0

$ python3 tools/fingerprint.py --solo gpu             # el nombre que se escribe solo
  campo          productor                estado         valor
  --------------------------------------------------------------------------
  VEREDICTO: TARGET_PARCIAL
rc=0
```

Una tabla vacía y un **veredicto de target** debajo, con `rc=0`. La herramienta que
AGENTS.md §3 y §4 mandan usar antes de medir nada es la que convierte un nombre mal
escrito en un veredicto de target. Nótese que `gpu` es un nombre razonable: la
herramienta se llama `fingerprint`, imprime `gpu_id` y `gpu_nombre`, y no tiene `gpu`.

---

#### `tools/regconst.py:395 --solo` — el mismo defecto que 1050, en la herramienta hermana

- **`add_argument`**: `tools/regconst.py:395` (`metavar="CLASE"`)
- **filtro**: `tools/regconst.py:427` — `vis = [f for f in filas if not a.solo or f["clase"] == a.solo]`
- **tipo de comparación**: `==` exacto
- **clases reales** (MEDIDO): `NO_EN_CORPUS`, `NO_ES_REGISTRO`, `PROVEN`, `PROVEN_POR_CITA`

MEDIDO:

```
$ python3 tools/regconst.py --solo NO_EN_CORPUS        # control
  NO_EN_CORPUS           RX550_MM_VM_CTX0_PTBA            0x54f      rx550_mmio.h:163
  NO_EN_CORPUS           RX550_MM_VM_CTX8_PTBA            0x50e      rx550_mmio.h:164
  NO_EN_CORPUS           RX550_MM_VM_INVALIDATE_REQ       0x51e      rx550_mmio.h:165

  35 #define con valor leidos en el driver: NO_EN_CORPUS 3, NO_ES_REGISTRO 24, PROVEN 5, PROVEN_POR_CITA 3
rc=0

$ python3 tools/regconst.py --solo no_en_corpus        # minúsculas
  [cabecera entera de :412-426, y CERO filas: el bucle de :428 no itera]
  35 #define con valor leidos en el driver: NO_EN_CORPUS 3, NO_ES_REGISTRO 24, PROVEN 5, PROVEN_POR_CITA 3
  de los cuales 11 son direcciones de registro y 24 no lo son.
rc=0
```

Peor que un vacío: **la salida se contradice a sí misma**. La línea de resumen (`:436`,
que cuenta `filas`, la lista **sin filtrar**) anuncia `NO_EN_CORPUS 3` y debajo no hay
ninguna. Quien lee el resumen cree que hay tres y no ve ninguno. El guardia de vacío de
esta herramienta (`:444-449`, `if not filas:`) comprueba la lista **sin filtrar**, así que
no dispara con `--solo`.

Es el mismo defecto que `lint.py:925-926`, y `lint.py` **ya está arreglado**
(`tools/lint.py:961-967`) mientras que `regconst.py` —que es el mismo archivo de ideas:
mismo `metavar="CLASE"`, mismo `==`, mismo `if not filas:` al final— no lo está.

---

#### `revkit/dires.py:112 --bloque` — la herramienta que diagnostica el defecto y lo tiene

- **`add_argument`**: `revkit/dires.py:112`
- **filtro**: `revkit/dires.py:196` — `if a.bloque and bloque != a.bloque: continue`
- **tipo de comparación**: `!=` con `continue`

MEDIDO:

```
$ python3 revkit/dires.py 0x1537 --bloque bif         # control
0x1537 ->
  mmGPU_HDP_FLUSH_REQ              bif      bif/bif_4_1_d.h:72
  mmGPU_HDP_FLUSH_REQ              bif      bif/bif_5_0_d.h:78
  mmGPU_HDP_FLUSH_REQ              bif      bif/bif_5_1_d.h:70
rc=0

$ python3 revkit/dires.py 0x1537 --bloque BIF         # mayúsculas: no existe
0x1537 ->
rc=0
```

Lo relevante no es el vacío: es que **el propio fichero describe esta clase de defecto
y la arregla a una función de distancia**. `revkit/dires.py:149-153`:

```
# AUTOCOMPROBACION en cada ejecucion. ... el fallo que corrigio esto (SUFIJOS_DIR
# con ".d.h" en vez de "_d.h") no daba error: devolvia una lista vacia para BIF, el
# bloque que hace falta en esta GPU, y eso parece un resultado legitimo.
# Un filtro mal escrito no avisa de que lo este.
```

La autocomprobación de `:160-176` valida el índice contra `0x1537`/`0x1538` en BIF
4.1 — pero valida el **índice**, no el `--bloque`. El diagnóstico es correcto y la
reparación incompleta.

---

#### `revkit/regs.py:304 --asic` — el vacío con una NOTA que lo justifica

- **`add_argument`**: `revkit/regs.py:304`
- **filtro**: `revkit/regs.py:429-430` — `mask = [x for x in mask if a.asic in x[1]]`, `shift = [...]`
- **tipo de comparación**: `in` (subcadena sobre el nombre del fichero)
- **agravante**: `:442` itera `for (mv, mf, ml) in mask:` sobre la lista ya vacía, y `:473-476` imprime una NOTA de boilerplate que **explica el vacío como si fuera intencionado**

MEDIDO:

```
$ python3 revkit/regs.py CC_GC_SHADER_ARRAY_CONFIG INACTIVE_CUS --asic gfx_8_0
CC_GC_SHADER_ARRAY_CONFIG.INACTIVE_CUS
------------------------------------------------------------
  gfx_8_0          MASK=0xffff0000 SHIFT=16  -> 16 bits @ 16   gfx_8_0_sh_mask.h:17713

NOTA: el mismo campo tiene valores distintos por ASIC.
Un unico valor sin decir de que ASIC es una respuesta ambigua.
rc=0

$ python3 revkit/regs.py CC_GC_SHADER_ARRAY_CONFIG INACTIVE_CUS --asic gfx_9_0
CC_GC_SHADER_ARRAY_CONFIG.INACTIVE_CUS
------------------------------------------------------------

NOTA: el mismo campo tiene valores distintos por ASIC.
Un unico valor sin decir de que ASIC es una respuesta ambigua.
rc=0
```

`gfx_9_0` es un nombre natural: la generación **es** gfx9. Y el fichero se llama
`gfx_9_0` en unos sitios y `gc_9_0` en otros, así que el nombre que casi se escribe
tampoco casa. La NOTA final dice «un único valor sin decir de qué ASIC es una respuesta
ambigua» sobre una salida donde no hay ni un valor: el texto trabaja en contra.

---

#### `tools/uninit_copy.py:756 --clase`

- **`add_argument`**: `tools/uninit_copy.py:756` (`action="append"`)
- **filtro**: `tools/uninit_copy.py:810` — `sel = [h for h in todos if h.clase in clases_filtro]`
- **tipo de comparación**: `in` contra lista
- **salida**: `:812-814` cuenta; `:822` `if sel:` imprime el RESUMEN; `:827` `return 1 if sel else 0`

MEDIDO (625 ficheros, 16 candidatos reales):

```
$ python3 tools/uninit_copy.py $D --clase TYPE_MISMATC      # falta la H
uninit_copy 1.0.0 · 625 ficheros leidos · 16 candidatos · 0 en las clases pedidas
rc=0

$ python3 tools/uninit_copy.py $D --clase TYPE_MISMATCH     # control
  ... 11 hallazgos ...
  RESUMEN por clase:
    TYPE_MISMATCH       11   la copia usa sizeof() de un tipo distinto al de la variable
rc=1
```

La línea de cabecera **dice los dos números**: 16 candidatos medidos, 0 seleccionados. Y
sale con `rc=0`. Es la forma más limpia de ver el defecto: la herramienta mide la
población, mide el filtro, y no dice que el segundo número sea por un nombre que no
existe.

Con dos filtros, uno bueno y uno mal:

```
$ python3 tools/uninit_copy.py $D --clase TYPE_MISMATCH --clase FULL_SIZE_COPPY
  RESUMEN por clase:
    TYPE_MISMATCH       11   la copia usa sizeof() de un tipo distinto al de la variable
    FULL_SIZE_COPPY      0   ?
rc=1
```

El `?` de `CLASES.get(c, "?")` (`:826`) es la **única** señal, y solo aparece porque la
otra clase tuvo hallazgos. Con dos nombres mal escritos no sale ni eso.

---

#### `tools/cap_census.py:258 --cap` — y en `--json` el filtro no existe

- **`add_argument`**: `tools/cap_census.py:258`
- **filtro**: `tools/cap_census.py:240` — `if only and only not in str(r["cap"]): continue`
- **tipo de comparación**: `in` (subcadena)

MEDIDO:

```
$ python3 tools/cap_census.py --kernel $K --cap PHM_TYPOXX ; echo rc=$?
cap_census 1.0.0
  UN SET sin unset posterior no prueba que la capability este activa.
  ...
  capability                                      set  unset  ficheros
  ------------------------------------------------------------------------------------------------
rc=0

$ python3 tools/cap_census.py --kernel $K --cap PHM_TYPOXX --json | python3 -c ...
rows en --json: 66
¿aparece alguna fila con PHM_TYPOXX? False
primera cap: PHM_PlatformCaps_ABM
```

**Defecto adicional, y es más grave**: en modo `--json` el filtro **no se aplica**.
`tools/cap_census.py:288` construye `"rows": [{k: v for k, v in r.items() if k != "hits"} for r in rows]`
sobre `rows`, que es la lista **sin filtrar** (`:279`). El camino `--json` de `render()`
no existe: `render()` solo se llama en modo texto. O sea: la misma invocación da 0 filas
en un modo y 66 en el otro. Un consumidor automático que pase `--cap` y `--json` recibe
el censo completo y no se entera.

---

#### `tools/msg_census.py:630 --msg`

- **`add_argument`**: `tools/msg_census.py:630`
- **filtro**: `tools/msg_census.py:478` — `if only and only not in str(m["symbol"]): continue`
- **tipo de comparación**: `in` (subcadena)

MEDIDO:

```
$ python3 tools/msg_census.py --kernel $K --chip CHIP_POLARIS12 --msg NoExisteMsg
  simbolos sin resolver (217): None, PPSMC_MSG_ACPPowerOFF, PPSMC_MSG_ACPPowerON, ...
  valor por cabecera: el numero se particiona por generacion.
  mensaje                                  valor(es)            hdr                usos payload
  --------------------------------------------------------------------------------------------------------
rc=0

$ ... --msg _ActiveProcessNotify          # control
  PPSMC_MSG_ActiveProcessNotify            ?                    rv                    1 SIMBOLO
rc=0
```

La cabecera con las cifras reales (`llamadas de envio`, `mensajes distintos`,
`reparto de payload`) se imprime siempre, calculada **sin** filtrar (`:456-458`), y
debajo la tabla vacía. Salida autocontradictoria, `rc=0`.

**Contraste dentro de la misma herramienta**: `--chip` **sí** se valida —
`tools/msg_census.py:643-645` da `ERROR {chip} no esta en el enum` con `rc=2`
(MEDIDO). El mismo fichero, dos convenciones, y la que falla es la del filtro de texto.

---

#### `tools/assert_contract.py:524 --fichero`

- **`add_argument`**: `tools/assert_contract.py:524`
- **filtro**: `tools/assert_contract.py:254` — `ev = escanear(raiz, solo)`, subcadena sobre el nombre
- **salida**: `:262` `ocurrencias: %d`, `:265-268` la tabla de reparto, `:270-271` el párrafo «LECTURA»

MEDIDO, con control:

```
$ python3 tools/assert_contract.py --kernel $K --fichero hwmgr        # control
  ocurrencias: 678
    ABORTA            545   80.4%  ########################################

$ python3 tools/assert_contract.py --kernel $K --fichero NO_EXISTE_XYZ
  assert_contract 1.0.0
  raiz: .../powerplay
  ocurrencias: 0

  CONTRATO DE ERROR (que hace el tercer argumento del macro)
    ABORTA              0    0.0%
    SALTA               0    0.0%
    REGISTRA_Y_SIGUE    0    0.0%
    PR_WARN_PURO        0    0.0%
    OTRO                0    0.0%

  LECTURA: ABORTA es el unico que detiene. REGISTRA_Y_SIGUE acumula el fallo y
  continua; 125 Counts quince de esos y devuelve 0. AVISA no hace nada.
rc=0
```

El párrafo `LECTURA` es una **conclusión sobre el driver** —«ABORTA es el único que
detiene, REGISTRA_Y_SIGUE acumula el fallo y continúa, 125 cuenta quince de esos y
devuelve 0»— y se imprime con cinco ceros detrás. `125` viene del comentario, no de la
medición de esta invocación. Éste es el patrón exacto de `hwip.py`: el vacío más un
texto interpretativo no condicionado.

---

#### `tools/citegen.py:385 --fichero`

- **`add_argument`**: `tools/citegen.py:385`
- **filtro**: `tools/citegen.py:410` — `citas = [x for x in citas if args.fichero in str(x["en"])]`
- **tipo de comparación**: `in` (subcadena)
- **salida**: `:440` `citas %d`, `:458-460` el recuento por clase, `:433` `return 1 if sospechosos else 0`

MEDIDO:

```
$ python3 tools/citegen.py --fichero NO_EXISTE_XXX ; echo rc=$?
  citas       0  (ficheros .md/.c/.h/.sh/.py, corpus excluido)
  RECUENTO POR CLASE
  [y aqui no hay NI UNA linea de clase: el bucle de :458-460 no itera nada]
rc=0

$ python3 tools/citegen.py --fichero NEGATIVE-RESULTS.md   # control
  citas       37
  RECUENTO POR CLASE
    EN_DISPATCH           14
    ...
    OTRO_ASIC              4  <-- SOSPECHOSO
    NO_EN_DISPATCH         2  <-- SOSPECHOSO
rc=1
```

Un censo de citas dudosas sobre esta GPU que sale con **0 citas, 0 clases, rc=0**. Sin
fichero que filtrar y con un fichero inexistente la salida es la misma.

### 4.2 El que anula la medición sin tabla

---

#### `tools/msg_census.py:629 --root`

- **`add_argument`**: `tools/msg_census.py:629`
- **uso**: `tools/msg_census.py:140` — `for root in roots:` → `os.walk(root)` en `:143`
- **tipo de comparación**: existencia de ruta

MEDIDO:

```
$ python3 tools/msg_census.py --kernel $K --chip CHIP_POLARIS12 --root NO_EXISTE ; echo rc=$?
msg_census 1.0.0
  MAPA_DE_BITS = el host pasa un OR de mascaras. NO demuestra que el
  firmware lo trate como flags: solo que le llega un numero.

  llamadas de envio: 0
  mensajes distintos: 0
  reparto de payload: {}
rc=0
```

Un censo entero con **0 de 0 de {}**, `rc=0`, y ninguna palabra sobre que no se ha
leído nada. Con `--root` correcto el mismo comando da cientos de mensajes. Es el
hallazgo 1048 (`ppt_validate` lee un `.c` que el filtro excluye) con un `--root`
mal escrito encima.

### 4.3 Veredicto estático, sin ejecución

---

#### `tools/reg_census.py:240 --gfx`

- **`add_argument`**: `tools/reg_census.py:240`
- **uso**: `tools/reg_census.py:256` — `resolve = lambda s: RR.resolve_reg(amd_root, args.gfx, s)`, solo con `--resolve`
- **cadena**: `tools/reg_resolve.py:224-226` — si `gfx8_d.h` no existe, `order` pasa a ser *todos* los headers cuyo nombre empieza por `gfx`; con un `gfx` equivocado la lista queda vacía, `in_target` queda vacía (`:228`) y el veredicto pasa a `DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO` (`:250`), que se imprime como `... (otra gen)` en `tools/reg_census.py:193-194`
- **por qué no se ejecutó**: con `--gfx gfx_9_0` la resolución no terminó en 180 s (MEDIDO: `timeout 180` → sin salida). El veredicto está derivado de la lectura, no medido: **`VACIO_SILENCIOSO` por lectura estática, `NO_VERIFICABLE` por ejecución.** Se queda como el único `VACIO_SILENCIOSO` sin testigo ejecutado, y por tanto el único que puede resultar ser un falso positivo.

Lo que sí está medido de esta cadena es el lado del símbolo, que no depende de `--gfx`:
`tools/reg_census.py --kernel $K --resolve --gfx gfx_8_0 --file .../gmc_v8_0.c` imprime
cuatro registros con `... (otra gen)` (MEDIDO), o sea que el veredicto
`DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO` es el que se emite en la operación
diaria de esta herramienta, y con un `--gfx` equivocado **todos** los registros caen en
ese veredicto sin que ninguna salida lo marque como sospechoso.

---

## 5. `VACIO_DECLARADO` — los que lo hacen bien, y por qué son la especificación

No es una lista de perdedores. Es **la especificación del arreglo**, escrita en código
existente. Los cuatro patrones:

### Patrón A — `choices=` en argparse (17 sitios, gratis)

```
tools/docscan.py:1060        --fail-on  {defect,stale,review,none}
tools/ppt_validate.py:765    --frontera {ppt,smu,ambas}
tools/vmid_map.py:836        --part     {all,topology,ptba,alloc}
tools/round.py:758           --only     {scan,new,claims,arbitrate,conflicts}
tools/asic_resolver.py:819   --universe {pm-subtree,includes,both,explicit}
tools/check_num_unico.py:1416 --alcance  {propio,todo}
```

MEDIDO:

```
$ python3 tools/docscan.py --repo . --only taxonomy --fail-on defect_typo ; echo rc=$?
usage: docscan [-h] ... [--fail-on {defect,stale,review,none}] ...
docscan: error: argument --fail-on: invalid choice: 'defect_typo' (choose from 'defect', 'stale', 'review', 'none')
rc=2

$ python3 tools/vmid_map.py --kernel $K --part topologie ; echo rc=$?
... invalid choice: 'topologie' ...
rc=2
```

### Patrón B — el conjunto se calcula y se imprime, y se sale con rc≠0

Es lo que hizo el arreglo de `lint.py` (`tools/lint.py:961-967`). Los que ya lo hacen:

| herramienta | `add_argument` | declaración | rc |
|---|---|---|---|
| `08-ARQ/tools/causal.py` | `:349 --chain` | `:372-374` `tema %r sin nodos conocidos. Temas: page_table, invalidate, vram` | 1 |
| `08-ARQ/tools/contradict.py` | `:322 --sym` | `:361-364` `%r: no aparece con ninguna cifra en %s` + `Comprueba el nombre antes de concluir que no existe` | 1 |
| `08-ARQ/tools/xref.py` | `:395 --sym` | `:435-453` `NINGUN sitio con ese NOMBRE EXACTO` + **diagnóstico de subcadena** que dice `Usa --sym <nombre>` | 1 |
| `08-ARQ/tools/smumsg.py` | `:263 --msg` | `:285-287` `ningun mensaje contiene %r` | 1 |
| `08-ARQ/tools/hdrmap.py` | `:239 --file` | `:253-258` `no nombra ninguna cabecera de forma DIRECTA` + por qué no implica ausencia | 1 |
| `08-ARQ/tools/scopeguard.py` | `:305 --check` | `:358-367` `TEMA %r` + `LIBRE. nadie lo ha escrito.` | 0/2 |
| `tools/mutate.py` | `:379 --run` | `:398-400` `mutante desconocido: %s` | 2 |
| `revkit/captura.py` | `:142 --solo` | `:185` `%r no esta en el plan de captura` | — |
| `revkit/regs.py` | `:297 reg` / `:298 field` / `:299 --find` | `:396` `el registro %r no existe en los headers` + **registros parecidos**; `:419` `campo %s.%s no encontrado` + campos parecidos; `:381-384` `NINGUN registro, campo ni fichero casa con el patron` + `Eso es NOT_FOUND, no PROVEN_ABSENT` | 1 |
| `tools/citations.py` | `:921 --show` | `:948-950` `UNRESOLVED  ningun fichero con ese nombre en este repositorio` | 1 |
| `tools/artifacts.py` | `:1329 --solo` | `:1348-1350` `artifacts: no conozco %s` | 2 |
| `tools/docscan.py` | `:1068 --only` | `:1143-1146` `docscan: unknown check(s): %s` | 2 |
| `tools/snapshot.py` | `:972 --diff` | `:991-993` captura `OSError` y lo dice | 2 |
| `tools/toolcheck.py` | `:323 --dir` | `:333-335` `ERROR  no existe %s` | 2 |
| `tools/contradict.py` | `:412 --findings` | `:422-424` `ERROR  no existe %s` | 2 |
| `08-ARQ/tools/reenvio_gate.py` | `:834 --find` | `:309-311` `G0: no existe %s` | 2 |
| `tools/reservas_gate.py` | `:1952 --ledger` | `:423-426` (docstring) → C2 falla nombrando el ledger | 1 |
| `tools/unreach.py` | `:669 --chip` | `:716-718` `*** case %s NO ENCONTRADO ***` + `No se puede afirmar nada` | 2 |
| `tools/trace_path.py` | `:492 --chip` | `:510-512` `ERROR %s no esta en amd_asic_type.h` | 2 |
| `tools/trace_path.py` | `:493 --from` | `:520-522` veredicto `NO_ENCONTRADO` **distinto** de los demás | 0 |
| `tools/msg_census.py` | `:628 --chip` | `:643-645` `ERROR %s no esta en el enum` | 2 |
| `tools/pipeline.py` | `:559 --root` | `:596` `ERROR  no encuentro la definicion de %s` | — |
| `tools/reg_resolve.py` | `:491 --gfx`, `:492 --reg`, `:493 --field` | `:181` `SH_MASK_NO_ENCONTRADO`; `:193` `MASK_NO_DEFINIDA` + `defines_leidos`; `:239` `PROVEN_ABSENT_EN_ASIC_REG` + nota | 0 |
| `tools/reg_census.py` | `:236 --file` | `:178-179` `ERROR NO_LEGIBLE: %s` | 0 |
| `tools/regtable_audit.py` | `:558 --gfx`, `:562 --table` | `:582-584` `ERROR %s no encontrado`; `:591-600` `Tablas disponibles: ...` | 2 |
| `tools/struct_layout.py` | `:1586 --struct` | `:1618-1622` `PROVEN_ABSENT_EN_CORPUS` + `busqueda exhaustiva` | 0 |
| `tools/smc_layout.py` | `:1263 --type` | `:1392-1396` `PROVEN_ABSENT_EN_CORPUS (%d usos)` | 0 |
| `tools/gccverify.py` | `:267 --struct` | `CLASIFICACION: NO_COMPARABLE (no se inventa ningun numero)` | 2 |
| `tools/evidence_search.py` | `:976/978/980/987/990` | `:1031-1036` `corpus %r no está en el manifiesto; disponibles: ...` | 2 |
| `tools/ipsolve.py` | `:1118 --chip` | `:1091-1092` `NOT_DISPATCHED_FOR_CHIP` está en `UNRESOLVED_VERDICTS` → `_exit_code` da 3; `:1213` `%d of %d did not resolve` | 3 |
| `revkit/huerfanos.py` | `:175 --raiz` | `:199-205` `NINGUNA de las raices existe` + `Un recorrido de 0 ficheros NO es 'no hay huecos'` | 2 |
| `revkit/btfsnap.py` | `:221 --structs` | `:254-261` `--structs se dio pero no queda ningun nombre` + explica por qué no cae a la lista por defecto | 5 |
| `tools/xref.py` | `:499 --file` | `:517-530` `AST INCOMPLETO` + `Se sale con codigo 3 en vez de devolver un analisis vacio, que pareceria un resultado sin referencias` | 3 |

Tres de estos merecen que se les apunte el motivo, porque son el **contrato exacto** del
arreglo de 1050 escrito por el propio proyecto:

- `tools/xref.py:528-529` — *"Se sale con codigo 3 en vez de devolver un analisis vacio,
  que pareceria un resultado sin referencias."*
- `revkit/huerfanos.py:203-204` — *"Un recorrido de 0 ficheros NO es 'no hay huecos'.
  Es 'no se ha mirado nada', y se distingue porque se imprime aqui."*
- `revkit/btfsnap.py:255-258` — *"Caer a la lista por defecto seria una sustitucion
  silenciosa: el usuario pide una cosa y recibe otra, sin que nada lo diga. Se rechaza
  en vez de adivinar."*

### Los que fallan ruidosamente (constan por completitud)

| herramienta | `add_argument` | qué hace | rc |
|---|---|---|---|
| `revkit/scan.py` | `:274 --solo` | `:281-283` `{"...": f}[a.solo]()` → `KeyError` con traza | 1 |
| `tools/constmap.py` | `:649 --header` | `:277` `open(header)` sin cerrar → traza | 120 |

Ruidoso no es bueno: `constmap.py` debería decir `ERROR no encuentro <header>` y salir
con 2, como hacen sus pares de §5. Pero un `rc=120` es un fallo que se ve, y el
presupuesto de esta auditoría es el silencio.

---

## 6. `ETIQUETA_MUERTA` — argumentos que no filtran

Un caso, y merece nombre propio porque es el único donde la cifra es **correcta** y la
etiqueta **no**:

| herramienta | `add_argument` | hecho |
|---|---|---|
| `08-ARQ/tools/inst_closure.py` | `:841 --asi` (`default="dce112"`) | `a.asi` aparece en **una** línea del `main`: `:868`, y es dentro de un `print`. El cálculo de `:864-865` itera `ASIC_CONSTRUCTORS` |

Y hay un segundo defecto en la misma línea, que la medición destapa: **`ASIC_CONSTRUCTORS`
es la lista vacía en el fuente** (`08-ARQUITECTURA/tools/inst_closure.py:83`).

MEDIDO, ejecutado:

```
$ python3 08-ARQUITECTURA/tools/inst_closure.py --asi dce999
  BASE = .../RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/display
  ...
  funciones indexadas: 7892
  semillas del ASIC (dce999): 0 de []
  semillas genericas: 1
rc=0

$ python3 08-ARQUITECTURA/tools/inst_closure.py          # el default, sin --asi
  semillas del ASIC (dce112): 0 de []
  semillas genericas: 1
rc=0
```

Las dos salidas son idénticas salvo la etiqueta. Y el `0 de []` dice las dos cosas de una
vez: el número es cero, y **la lista que debería producirlo está vacía**. La herramienta
no ha medido ninguna semilla de ASIC, y su titular dice «semillas del ASIC (...)». Con
`--asi dce999` el titular es además una etiqueta que nadie ha comprobado.

No es un caso aislado: es lo que le pasa a cualquier herramienta cuya constante de
catálogo se queda vacía por edición y cuyo `--help` no la exige. La puerta de §8 no lo
detecta porque no hay ningún filtro que esté mal; haría falta una comprobación de
**catálogo no vacío**, que es otra puerta y no la de este nodo.

Y dos filtros **aceptados y nunca aplicados**, verificados por ausencia del `dest` en
todo el fichero:

| herramienta | `add_argument` | `dest` searched |
|---|---|---|
| `tools/claims.py` | `:762 --solo-clase` | `solo_clase` aparece en 1 línea del fichero: la propia declaración |
| `tools/frontier.py` | `:467 --vias` | `vias` aparece en 2 líneas: `:467` (declaración) y `:695` (`"vias": VIAS`, la constante, sin relación) |

MEDIDO sobre `claims.py --solo-clase`: la salida es la del censo completo. Un filtro que
no filtra no puede vaciar nada, pero **afirma** que filtra, y quien lo usa cree que está
viendo un subconjunto.

---

## 7. `NO_VERIFICABLE` — y por qué

| elemento | por qué |
|---|---|
| `revkit/klog.py:167 --patron` | lee `journalctl`/`dmesg`. El encargo prohíbe `dmesg`/`journalctl`, así que **no se ha ejecutado**. Estáticamente: `cmd_lineas(a)` filtra por subcadena; no hay conjunto cerrado, así que el vacío es una verdad sobre la consulta. Riesgo: **no determinado** |
| `revkit/obs.py:124 --filtro` | idem, `log_amdgpu()` en `:95` ya declara el log vacío (`:96-98` dice `NO es evidencia de que no haya log`). El `--filtro` de `:101` es regex sobre esas líneas; un regex que no casa → lista vacía, y el comportamiento del consumidor **no se ha leído** |
| `08-ARQ/tools/citecheck.py:530 --dir` | `glob.glob(os.path.join(a.dir, "**", "*.md"))` en `:547`. Si `--dir` no casa, `targets` queda con lo positional; si no hay positional, `:548-550` imprime ayuda con rc=2. Con positional + `--dir` malo, el vacío **no es observable en la salida**. No ejecutado |
| `tools/reg_census.py:240 --gfx` | ver §4.3: lectura estática sí, medición no (`>180 s`) |
| `01-AUDITORIA/.../src_registry.py:338-342` | cuatro rutas (`--repo-root --out-dir --path --recovery-dir`). `:358` las recorre; `observe()` devuelve filas por ruta. No ejecutado: escribe en `--out-dir`, y este nodo no escribe |

---

## 8. LA PUERTA

### 8.1 Qué tiene que poder fallar

> **«Ninguna herramienta de este proyecto devuelve un conjunto vacío por un filtro que
> no casó sin decirlo.»**

Formulado como predicado sobre `(herramienta, argumento, valor)`, no sobre el código: se
puede falsar con un vector, no con una opinión sobre el estilo.

### 8.2 Las dos capas, y por qué dos

**Capa A — estática, de rastreo. NO es un veredicto.**

Recorre las 99 herramientas con `add_argument` que toma valor (`:301` argumentos),
localiza el uso de cada `dest`, lo clasifica en `CERRADO` / `CONFIG` / `RUTA` /
`ABIERTO` / `NO_ES_FILTRO`, y produce la lista de **candidatos a adjudicar**.

MEDIDO con el prototipo (`/tmp/opencode/puerta_filtros.py`, Capa A, ejecutada):

```json
{ "capa": "A", "filtros": 87, "sin_declaracion": 69 }
```

**Y ese 69 no es un recuento de defectos.** Es un recuento de *«la heurística no ha
encontrado una declaración»*, y la heurística es limitada por construcción: busca
`if ... <dest> ...: return [1-9]` en una ventana de 600 caracteres, y por eso **no ve**
que `msg_census.py:643` valida `--chip` (la comprobación es `if chip_val is None:` sobre
una variable intermedia, no sobre `args.chip`). Una capa que no puede ver no puede
declarar `PASS`: declara `NOT_DETERMINED` y que Capa B la resuelva. Por eso Capa A no
computa la puerta; **computa la lista de la puerta**.

**Capa B — dinámica, de falsación. ES el veredicto.**

Para cada filtro de las cuatro clases, un vector con el valor mal formado y una condición
de paso **estrecha**:

```
ok  :=  rc != 0
   ó  existe una línea que diga que EL VALOR PEDIDO no está en el conjunto válido
```

La segunda disyunción tiene que estar **anclada al valor**, no al informe entero. MEDIDO:
la primera versión del oráculo aceptaba cualquier `NO ENCONTRADO` en la salida, y eso
hacía que `hwip.py --chip Polaris12` pasara la puerta — cuando esa herramienta imprime
`NO ENCONTRADO` en su sección 5 y **afirma igual** en la sección 3 que no hay atajo
estático. Oráculo correcto:

```python
DECLARA = re.compile(
    r"no es ninguna (clase|clave)|clases que SI existen|"
    r"no esta en el enum|no conozco|"
    r"no aparece con ninguna cifra|"
    r"temas? .* sin nodos|"
    r"no esta en el plan de captura|"
    r"mutante desconocido|"
    r"unknown check", re.I)
```

### 8.3 Capa B ejecutada — y el control negativo

MEDIDO, 10 vectores negativos (los diez son **`VACIO_SILENCIOSO` de §4**; ninguno
es un vector de control *positivo*, por diseño: son el control negativo de la puerta):

```json
{ "capa": "B", "vectores": 10, "que_callan": 9 }
```

```
  OK    rc=2    tools/lint.py          ERROR: --solo CLASE_QUE_NO_EXISTE no es ninguna clase de este informe.
  FALLA rc=0    tools/regconst.py
  FALLA rc=0    tools/fingerprint.py
  FALLA rc=0    tools/uninit_copy.py     uninit_copy 1.0.0 · 1 ficheros leidos · 0 candidatos · 0 en las clases pedidas
  FALLA rc=0    tools/assert_contract.py assert_contract 1.0.0
  FALLA rc=0    revkit/dires.py          direcciones indexadas : 641231
  FALLA rc=0    tools/trace_path.py      trace_path 1.0.0 · chip=CHIP_POLARIS12 valor=17
  FALLA rc=0    tools/msg_census.py      msg_census 1.0.0
  FALLA rc=0    tools/hwip.py
  FALLA rc=0    revkit/regs.py           CC_GC_SHADER_ARRAY_CONFIG.INACTIVE_CUS
```

**`que_callan: 9` sobre 10 vectores es el resultado de la puerta, y es un FALLO de la
puerta.** La puerta no está escrita: no existe `tools/puerta_filtros.py`, y no se ha
escrito porque el encargo de este nodo es un único fichero nuevo y ninguna herramienta
editada. El prototipo vivió en `/tmp/opencode/` y **no se ha instalado**.

### 8.3-bis El oráculo de la puerta también se ha falsado, y ha fallado

La primera versión de la Capa B usaba un oráculo **anchado**: `ok := rc != 0 ó la salida
contiene "NO ENCONTRADO" / "no existe" / "no encuentro"` en cualquier parte. Con ese
oráculo, MEDIDO:

```
{ "capa": "B", "vectores": 10, "que_callan": 8 }
  OK    rc=0    tools/hwip.py          <-- FALSO OK
```

`hwip.py --chip Polaris12` **pasa** la puerta con un oráculo ancho, y no debe pasarla:
la herramienta imprime `NO ENCONTRADO` en su sección 5 (`amdgpu_drv.c:2041 ... NO
ENCONTRADO`) y, en la sección 3, **afirma igual** que para esta GPU todas las versiones
de IP se leen de la tarjeta. La frase que el oráculo tomaba por declaración pertenece a
otra sección del informe.

Con el oráculo **anclado al valor** (§8.2) el mismo vector da `FALLA`, que es lo
correcto, y `que_callan` sube de 8 a 9.

Queda dicho porque es el mismo defecto que se está auditando, una capa arriba: un patrón
que casa con algo que no es lo que se busca, y una puerta que por eso da verde. Una
puerta que solo se valida contra herramientas que ya pasan no vale nada; esta se valida
contra las que fallan.

**Lo que esto cuesta en el sitio donde se está mirando:** a `hwip.py` nadie lo detecta no
porque su filtro esté callado, sino porque otra sección del mismo informe dice
`NO ENCONTRADO` y el ojo se queda ahí. Un oráculo de puerta ancho habría repetido el
error desde dentro de la puerta, y eso habría sido peor que no tener puerta: habría
autorizado en verde los ocho reparos que este documento propone.

### 8.4 El control negativo, y por qué esta puerta es falsable de verdad

La puerta **no puede pasar hoy**, porque sus propios vectores de prueba son herramientas
del proyecto con el defecto. Eso no es un defecto del diseño de la puerta: es lo que la
hace falsable.

- **Control negativo 1 — el que ya existe y se ejecutó**: `--solo CLASE_QUE_NO_EXISTE`
  sobre `tools/lint.py` → `rc=2` + `ERROR: --solo ... no es ninguna clase de este
  informe.` + lista de las 4 clases que sí existen. **La puerta pasa ese vector.** Es el
  arreglo de 1050, y funciona.
- **Control negativo 2 — el mismo vector contra la herramienta hermana**:
  `tools/regconst.py --solo CLASE_QUE_NO_EXISTE` → `rc=0` y salida completa. **La puerta
  falla ese vector.** Mismo `metavar="CLASE"`, mismo `==`, misma forma de código: la
  diferencia entre el vector que pasa y el que falla es un commit.
- **Control negativo 3 — el que exige que la puerta crezca**: cuando se repare
  `regconst.py`, `fingerprint.py`, `trace_path.py --root`, `dires.py`, `regs.py`,
  `assert_contract.py`, `uninit_copy.py`, `msg_census.py` y `hwip.py`, la puerta debe
  subir de 9 a 0. **Si `que_callan` no baja al reparar, la puerta está mal escrita** y
  hay que arreglarla antes que a las herramientas. Ese es el uso de la puerta: obligar a
  que cada arreglo venga con su vector.

### 8.5-bis Capa C — la que este nodo no ha escrito, y por qué importa más que B

La Capa B verifica una propiedad de la **salida**: «con un nombre mal escrito, esto no
calla». Hay una segunda, más fuerte y más barata de verificar, sobre el **código**:

> **Si el conjunto de valores válidos es calculable, la herramienta tiene que calcularlo
> y usarlo para rechazar el valor antes de filtrar.**

`tools/lint.py:959` — `clases_presentes = sorted({r["clase"] for r in rows})` — es
exactamente eso, y por eso `--solo` ya no puede callar. Aplicado a `regconst.py` el arreglo
son **siete líneas**, y el texto que tiene que imprimir ya existe literalmente en el
fichero hermano (`tools/lint.py:962-967`).

El motivo de no haberla escrito: Capa C es un detector de cambios sobre el árbol, y este
nodo tenía prohibido tocar herramientas. Se deja enunciada porque es la que convierte
esta lista de 14 en un invariante mantenido.

### 8.6 Los dos vectores que la puerta tiene que añadir y este nodo no ejecutó

- `tools/hwip.py` tiene dos secciones con requisitos distintos. La sección 5 degrada a
  `INCOMPLETA` cuando el chip no existe; la sección 3 afirma. Con el oráculo anclado al
  valor la puerta **ya lo detecta** (MEDIDO: `FALLA rc=0`). Lo que falta es el vector
  más fuerte: «la sección 3 dice NINGUNO **y** el chip no está en el enum`, y la puerta
  tiene que fallar por la **sección 3**, no por el `rc`. Hoy pasan las dos cosas y la
  puerta acierta por un motivo que no es el que importa.
- `tools/cap_census.py --cap X --json` devuelve el censo **sin filtrar**. Ningún oráculo
  de rc lo detecta porque la salida es válida y completa. El vector que falta es de
  **equivalencia de modos**: `--cap X` en texto y `--cap X --json` deben seleccionar el
  mismo conjunto, y hoy no lo hacen (MEDIDO: 0 filas y 66 filas para el mismo valor).

### 8.7 Lo que la puerta NO puede cubrir, y hay que decir

- Los filtros de clase ABIERTA (`--msg`, `--fichero`, `--patron`, `--find`): no tienen
  conjunto cerrado, así que «no casó» no es un error de escritura sino una verdad sobre
  la consulta. La puerta **no puede** exigirles nada, y por eso su fallo en ellos no es
  un descuido de la puerta sino una limitación del argumento. Para ésos el requisito
  correcto es distinto y más fuerte: **la salida tiene que decir cuántas filas había
  antes del filtro**, que es justo lo que `uninit_copy.py:812-814` ya hace (y por eso
  su `VACIO_SILENCIOSO` es visible) y lo que `msg_census.py`, `cap_census.py` y
  `hwip.py` no hacen.
- `trace_path.py --root` no es un filtro de valor sino de **población**. La puerta tiene
  que exigir que el tamaño de la población se imprima **antes** del primer veredicto, no
  después. Hoy se imprime después (`:659`).

---

## 9. Recuento, con veredicto

**56 herramientas examinadas**, de las 99 del proyecto que tienen al menos un
`add_argument` que toma valor (§2). El número bruto sin clasificación es el que no
sirve:

| veredicto | herramientas | argumentos | con `rc=0` en el caso mal formado |
|---|---|---|---|
| `VACIO_SILENCIOSO` | **13** | **16** | **15** de 16 (el 16.º es `reg_census --gfx`, sin ejecutar) |
| `VACIO_DECLARADO` | 39 | 45 | 5 declaran pero en `rc=0`: `reg_resolve`, `reg_census --file`, `smc_layout`, `struct_layout`, `trace_path --from` |
| etiqueta muerta (`--asi`) | 1 | 1 | 1 (`inst_closure.py --asi dce999`: `rc=0`, etiqueta sin comprobar) |
| filtro muerto (acepta y no filtra) | 2 | 2 | 0 |
| `NO_VERIFICABLE` | 4 | 5 | — |
| **unión, sin doble conteo** | **56** | — | — |

**Las 39 `VACIO_DECLARADO` y las 13 `VACIO_SILENCIOSO` se solapan en 4 herramientas**
(`tools/trace_path.py`, `tools/msg_census.py`, `tools/reg_census.py`, `revkit/regs.py`):
cada una declara correctamente un filtro y deja otro mudo. Por eso `13 + 39 + 1 + 2 + 4`
son 59 y la unión son 56. Un filtro por herramienta no habría detectado ninguna de las
cuatro; el defecto es **por argumento**, no por fichero.

Los 16 argumentos `VACIO_SILENCIOSO`, por herramienta:

1. `tools/trace_path.py` — `--root` (§4.0), `--callers-of`
2. `tools/hwip.py` — `--chip` (§4.0)
3. `tools/rx550/regctx.py` — `--prefix` (§4.0)
4. `tools/fingerprint.py` — `--solo` (§4.1)
5. `tools/regconst.py` — `--solo` (§4.1)
6. `revkit/dires.py` — `--bloque` (§4.1)
7. `revkit/regs.py` — `--asic` (§4.1)
8. `tools/uninit_copy.py` — `--clase` (§4.1)
9. `tools/cap_census.py` — `--cap` (§4.1), `--chip` (`:257`; `chip_value: null` en `--json`, texto idéntico al correcto — MEDIDO)
10. `tools/msg_census.py` — `--msg` (§4.1), `--root` (§4.2)
11. `tools/assert_contract.py` — `--fichero` (§4.1)
12. `tools/citegen.py` — `--fichero` (§4.1)
13. `tools/reg_census.py` — `--gfx` (§4.3, **sin ejecutar**)

---

## 10. Lo que queda abierto, sin adornos

1. **`tools/reg_census.py:240 --gfx`** es el único `VACIO_SILENCIOSO` sin testigo
   ejecutado. `NOT_VERIFIED`: la resolución con `--gfx gfx_9_0` no terminó en 180 s
   (MEDIDO: `timeout 180`, sin salida). La clasificación viene de la lectura de
   `tools/reg_resolve.py:224-226` → `:250`, y puede ser un falso positivo.
2. **La Capa A de la puerta deja 69 candidatos sin adjudicar** y este nodo no los abrió:
   los `--repo`/`--docs`/`--amd-root`/`--root-dir`/`--source` de 20 herramientas, más
   `--include` de `evidence_search.py`, `--mapa` de `reenvio_gate.py`, `--key-root`,
   `--ledger`, `--btf`, `--compare`, `--offsets-from`, `--lectura-defines` de
   `smc_copy_scope.py`. **Ninguno se ha declarado `VACIO_DECLARADO` por suposición, y
   ninguno se ha declarado `VACIO_SILENCIOSO` sin abrirlo.** El 69 es «no mirado», que es
   un estado, no un veredicto.
3. **`revkit/klog.py` y `revkit/obs.py` siguen sin verificar**, y no se pueden verificar
   dentro del encargo: leen `journalctl`/`dmesg`, y el encargo lo prohíbe.
4. **La puerta no está escrita.** El prototipo midió 9 de 10 vectores mudos, y su oráculo
   tuvo que arreglarse una vez (§8.3-bis) antes de decir la verdad sobre `hwip.py`.
   Escribirla es otro nodo, y §8 es su contrato.
5. **El arreglo de `lint.py:961-967` no se ha propagado** a `regconst.py`, que es el mismo
   archivo de ideas con el mismo `metavar="CLASE"` y el mismo `==`. Es el arreglo de menor
   coste de toda la lista: siete líneas, y el texto de error que tiene que imprimir ya
   existe literalmente en el fichero hermano.
6. **`tools/cap_census.py --cap` no filtra en `--json`.** No es un `VACIO_SILENCIOSO`: es
   un filtro que en un modo no filtra y en el otro sí, con la misma invocación. Va en la
   lista porque la puerta tiene que cubrirlo y porque el arreglo (aplicar el filtro antes
   de `:288`) es de una línea.

---

## Apéndice A — Cómo se citan las líneas, y hash de las herramientas que más pesan

Toda afirmación de este documento cita `fichero:línea` **contra el contenido actual**, y
las 121 citas se verificaron programáticamente (121 verificadas, 0 errores). El
inventario de `add_argument` se hizo **eliminando comentarios antes de analizar**, porque
sin eso `toalaudit.py:422` (`add_argument("--x") es una declaracion;`, dentro de un
comentario) cuenta como argumento y no lo es: 111 → 99 herramientas, 305 → 301
argumentos. Y las líneas se cuentan sobre el fichero **original**, no sobre el
descomentado; una versión intermedia daba números desplazados y se descartó.

### Hash de las herramientas que más pesan

| fichero | sha256[:16] | líneas |
|---|---|---|
| `tools/trace_path.py` | `88da33bec82e7eb9` | 781 |
| `tools/fingerprint.py` | `aa26c787fb23364c` | 551 |
| `tools/regconst.py` | `d96d1cd5014b8ac1` | 455 |
| `tools/lint.py` | `de07fd1c73a023ce` | 1021 |
| `tools/hwip.py` | `e52b6b9500f3abc9` | 1017 |
| `revkit/dires.py` | `63070f7997e92754` | 204 |
| `revkit/regs.py` | `1903c3da3b154838` | 480 |
| `tools/uninit_copy.py` | `60ae8d7a5fe666bd` | 832 |
| `tools/assert_contract.py` | `b203942237ae5ab8` | 555 |
| `tools/cap_census.py` | `86d153a17176a1e2` | 389 |
| `tools/msg_census.py` | `f00166daee637707` | 669 |
| `tools/mutscore.py` | `884028f47d4684b4` | 905 |
| `tools/citegen.py` | `e4d729dca12b8f82` | 511 |
| `tools/rx550/regctx.py` | `3d77ea372a51db35` | 388 |

### `DRIFT_DETECTED` — un fichero que cito lo está cambiando otra sesión

`git status` muestra **`revkit/huerfanos.py` como `M`, con 61 inserciones**, y no lo he
escrito yo: este nodo no ha editado ninguna herramienta. También hay 17 ficheros `M` en
`04-IMPLEMENTACION/rx550-driver/` y un directorio nuevo sin seguimiento,
`03-EXPERIMENTOS/ATOMBIOS-DECODER/`, de otra sesión.

Verificado explícitamente, porque el hallazgo 1048 enseña lo que pasa si no se verifica:
las seis líneas que cito de ese fichero siguen diciendo lo que cito.

```
revkit/huerfanos.py:175  ap.add_argument("--raiz", action="append", default=None)
revkit/huerfanos.py:197  existentes = [r for r in raices if os.path.isdir(r)]
revkit/huerfanos.py:199      print("NINGUNA de las raices existe. Se han probado:")
revkit/huerfanos.py:203      print("Un recorrido de 0 ficheros NO es 'no hay huecos'. Es 'no se")
revkit/huerfanos.py:204      print("ha mirado nada', y se distingue porque se imprime aqui.")
revkit/huerfanos.py:205      return 2
```

**Lo que este nodo ha creado es exactamente un fichero**,
`08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md`, sin seguimiento, y no ha hecho `git add` ni
`git commit`.

## Apéndice B — Lo que se ejecutó y lo que no

**Ejecutado** (solo lectura, sin banderas de escritura, sin `/dev/dri`, sin sysfs, sin
`dmesg`/`journalctl`, sin internet): `tools/lint.py`, `tools/regconst.py`,
`tools/fingerprint.py`, `tools/hwip.py`, `tools/trace_path.py`, `revkit/dires.py`,
`revkit/regs.py`, `tools/uninit_copy.py`, `tools/cap_census.py`, `tools/msg_census.py`,
`tools/assert_contract.py`, `tools/citegen.py`, `tools/rx550/regctx.py`,
`tools/mutscore.py`, `tools/artifacts.py`, `revkit/captura.py`, `revkit/scan.py`,
`08-ARQ/smumsg.py`, `08-ARQ/causal.py`, `08-ARQ/xref.py`, `08-ARQ/inst_closure.py`,
`tools/docscan.py`, `tools/vmid_map.py`, `tools/round.py`, `tools/mutate.py`,
`08-ARQ/hdrmap.py`, `tools/gccverify.py`, `tools/struct_layout.py`, `tools/smc_layout.py`,
`tools/reg_resolve.py`, `tools/reg_census.py`, `tools/toolcheck.py`,
`tools/reservas_gate.py`, `tools/constmap.py`, `tools/xref.py`, `revkit/huerfanos.py`,
`revkit/btfsnap.py`, `tools/citations.py`, `tools/contradict.py`,
`08-ARQ/tools/regdb.py` (sólo `--help`).

**Leído, NO ejecutado**, y declarado como tal en el cuerpo: `tools/ipsolve.py` (>180 s),
`tools/reg_census.py --resolve --gfx gfx_9_0` (>180 s), `tools/pipeline.py`,
`tools/evidence_search.py`, `08-ARQ/tools/citecheck.py`,
`08-ARQ/tools/reenvio_gate.py`, `08-ARQ/tools/scopeguard.py`,
`tools/claims.py` y `tools/frontier.py` (ambos por **ausencia del `dest`**, que es una
prueba de lectura, no de ejecución), `01-AUDITORIA/.../src_registry.py` (escribe en
`--out-dir`).

**No ejecutado por prohibición explícita del encargo:** `revkit/klog.py`,
`revkit/obs.py` — leen `journalctl`/`dmesg`.

**No pertenece a este nodo:** `04-IMPLEMENTACION/**` y `03-EXPERIMENTOS/**`, excluidos en
§2 y no contados en ninguna tabla.

## Apéndice C — Lo que este nodo NO ha hecho

- **No ha arreglado nada.** Ni una línea de ninguna herramienta. La lista es el
  entregable y repararla es otro nodo, con la lista completa delante.
- **No ha escrito la puerta.** §8 es su contrato, no su código.
- **No ha renumerado nada**, ni ha tocado hallazgos, ni `FINDINGS-RENUMERACIONES.md`.
- **No ha abierto `/dev/dri/*`**, ni ha escrito en sysfs, ni ha leído `dmesg` ni
  `journalctl`, ni ha descargado nada.
- **No ha hecho `git add` ni `git commit`.**