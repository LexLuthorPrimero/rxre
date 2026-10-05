# 1189 — `tools/toolreg.py` tenía **dos programas con el mismo nombre**. El commiteado tiene 1208 líneas; el del árbol tenía 473 y **cero `def` en común**. El coste no fue un fallo: fue que `git status` lo mostraba como ` M` entre veinte otros

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=ERROR-REPORT + REPAIR
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/rxre.py  (141 -> 155 vectores, rc=0)
                              tools/huella.py  (nuevo, 27 vectores, rc=0)
CLASE=ERROR · CONTRADICTION · ESTADO=RESUELTO_Y_VIGILADO
COMMIT=0764ffe
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
```

## 0 · El error, sin adornarlo

```text
git status --short
  M tools/toolreg.py          <-- lo mio
  M tools/cap_census.py
  M revkit/cn8.py
  ... 20 ' M' mas

`M` significa "modificado respecto a HEAD".
NO significa "modificado por MI".
```

No comprobé la autoría antes de preparar el commit. Al preparar el `git diff
--stat` vi la cifra y **saltó algo que no era un número**:

```text
tools/toolreg.py | 1618 +---
```

Un fichero **más corto** que el commiteado no es una mejora de un fichero
largo: es un fichero distinto. Lo comprobé:

```text
$ git show HEAD:tools/toolreg.py | wc -l      ->  1208
$ wc -l tools/toolreg.py                      ->   473
```

Y la diferencia no era de tamaño, sino de identidad:

```python
defs solo en HEAD:   inventory, cross_reference, declarados_que_no_existen,
                     docs_index, entradas_duplicadas, tl_ownership,
                     directorios_no_declarados, run_selftests, Tool,
                     declares_read_only, parse_tool, _fixture, ...
defs solo en arbol:  matriz_completa, sondea, sonda_criptografica, resumen,
                     donde_esta, version_de, primera_version, chk, ...
comunes:             0
```

**Cero.** Dos programas distintos con el mismo nombre, y el árbol tenía el
mío.

## 1 · De quién era el bueno, y por qué importa

```text
$ grep -m1 AUTOR 06-INGENIERIA-INVERSA/findings/10{43,51,52,55,60,64,65}-*.md
  (ninguno)
$ grep -m1 AUTOR 06-INGENIERIA-INVERSA/findings/118{5,8}-*.md
  AUTOR=AGENTE-INSTR
```

Los hallazgos `1043`, `1051`, `1052`, `1055`, `1060`, `1064` y `1065` **no
llevan `AUTOR`**: no son míos. Y son precisamente los que citan `toolreg`. El
programa de 1208 líneas con `TOOL_DIRS` de 7 entradas, `run_selftests`, cobertura
contra `docs/TOOLS-STATUS.md` y 14 checks es **de otra sesión**, con su propio
razonamiento escrito en sus docstrings:

> *"la primera versión de este fichero escaneaba solo `tools/`; después se
> añadió `08-ARQUITECTURA/tools/` … y un TERCER directorio apareció —
> `rx550-driver/tools/` — y nadie lo añadió, porque nada comparaba el árbol con
> la tupla."*

Yo lo sobrescribí a las **22:03** de hoy. Su trabajo seguía vivo en `HEAD` porque
nadie lo había commiteado desde la 10:10.

**El daño real fue evitado por una regla que yo mismo escribí antes**: no
commiteé `toolreg.py`. Lo vi en el `--stat`, lo dudé, y fui a mirar. Si hubiera
commiteado a ciegas, un instrumento con 14 checks y puerta de directorios habría
sido sustituido por otro de 22 vectores, y el hallazgo `1064` —"seis opciones
documentadas que no existen"— habría empezado a ser mentira sin que nada lo
notara.

## 2 · Lo que el resolutor nuevo destapó (y que llevaba meses oculto)

Al dejar de depender de `matriz_completa` y resolver contra la interfaz real,
aparecieron tres cosas:

### 2.1 `dynamic_debug` no es un binario

```text
estado_de("dynamic_debug")  ->  AUSENTE        (con el resolutor viejo)
```

Falso. No es un ejecutable de `PATH`: es `/sys/kernel/debug/dynamic_debug/control`,
que sin privilegios da **`EACCES`, no `ENOENT`**. Es decir: existe, pide
privilegio y se revierte. Está declarado como

```text
ESCRIBE en el kernel: activa printk. Se puede reactivar
```

Es la **RUNTIME_TRACE más barata y más reversible que existe**, y mi tabla la
reportaba como inexistente. Un instrumento reportado como ausente no se planifica.

### 2.2 `spatch` estaba duplicada

Dos filas: `[FIND_DEF, FIND_WRITER, FIND_READER, REWRITE]` y
`[FIND_WRITER, REWRITE]`. La segunda es un **subconjunto estricto** de la
primera. Con la columna cruda, el enrutado tiene dos respuestas para lo mismo y
gana la que esté antes en el fichero. Es la misma clase de defecto que el
`radeontop` duplicado que ya había encontrado una vez — y lo había encontrado en
**otra** herramienta, lo cual demuestra que buscarlo una vez no es buscarlo.

### 2.3 El que más caro habría sido

```text
('llvm-mc', ['ISA_ENCODE'],  ...  "ENSAMBLA pero NO desensambla")
('llvm-mc', ['ISA_DECODE'],  ...  "PROBADO QUE NO SIRVE para decodificar")
```

Las dos filas son **ciertas**. El problema es que la segunda está en la columna
de capacidades, y eso la hace **enrutable**:

```text
antes:  candidatos_para(["ISA_DECODE"])
        -> llvm-objdump, clrxdisasm, rga, llvm-mc      <-- llvm-mc entra
        -> el plan sale OK con pasos que no pueden funcionar
```

> Un resultado negativo escrito como capacidad es un plan que se contradice.

Y era peor de lo que parece: el hallazgo `1185`, mío, de esta misma sesión, ya
había medido que `llvm-mc` no desensambla. **La tabla afirmaba lo contrario de
lo que yo mismo había medido, y nada lo confrontaba.**

## 3 · La reparación, y por qué no es "borrar la fila"

Borrar el par refutado habría perdido la medición. Lo que se hizo fue
**separar la evidencia de lo que se enruta**:

```python
CAP_REFUTADA = {
    ("llvm-mc", "ISA_DECODE"):
        "MEDIDO 1185: llvm-mc ensambla y responde 'not yet supported' al "
        "desensamblar. Cubre ISA_ENCODE y nada mas",
    ("llvm-objdump", "ISA_DECODE_DESDE_BYTES"):
        "MEDIDO 1185: decodifica SOLO sobre un objeto ELF. Sobre bytes sueltos "
        "no hay formato, y por eso sigue faltando un desensamblador GFX8 real",
    (DD_CONTROL, "FIND_DEF"):
        "MEDIDO: es una interfaz de traza del kernel, no un indice de codigo",
}
```

- La **fila** sigue completa, con su nota. Nada de evidencia se borra.
- `capacidades_ruteables(h)` es lo que el planificador consume: lo declarado
  menos lo probadamente imposible.
- Cada motivo **cita su medición**, para que se pueda auditar en vez de creerlo.

Y el efecto lateral valió más que el arreglo:

```text
$ rxre huecos
  ISA_ANALYZE              candidatas=rga          ninguna viva
  ISA_DECODE_DESDE_BYTES   candidatas=llvm-objdump  PROBADA IMPOSIBLE: ...
  RUNTIME_CLOCK            candidatas=rocm-smi     ninguna viva
  RUNTIME_INSPECT          candidatas=drgn         ninguna viva
  STRUCT_OFFSET_LIVE       candidatas=drgn         ninguna viva
```

`ISA_DECODE_DESDE_BYTES` es **la pregunta real** del frente GFX8: *¿desensambla
estos bytes sueltos?*. Antes no salía porque nadie la declaraba —sólo la
refutábamos—, y una refutación guardada y no consultable es lo mismo que no
haberla medido. Ahora sale como hueco **con la prueba de que el hueco existe**,
que es la forma más fuerte de hueco que hay.

## 4 · La regla que sale, y que ya era conocido

```text
UNA HERRAMIENTA TIENE UN NOMBRE, NO UNA IDENTIDAD.
Y `git status` DICE QUE HAY UNA DIFERENCIA, NO QUIEN LA HIZO.
```

Tres reglas ejecutables que salían de esto:

| Regla | Mecanismo | Vectores |
|---|---|---|
| Dos filas iguales no enrutan dos veces | `filas_duplicadas()` con `(herramienta, capacidades)` en la clave | 2 |
| Un par `(herramienta, capacidad)` se declara una vez | `CAP_REFUTADA` + `capacidades_ruteables()` | 9 |
| Una dependencia se declara por **interfaz**, no por nombre de función | `TOOLREG_INTERFAZ` + `_toolreg_interfaz_ok()` | 3 |

La tercera es la que habría atrapado esto a la primera: `rxre` ya no llama
`matriz_completa`, llama tres nombres que **comprueba** y, si faltan, dice
cuáles en vez de reventar con `AttributeError` dentro de un selftest.

```text
vector: la que rxre necesita esta TODAY en el registro commiteado   PASA
vector: y el registro commiteado NO tiene la que rxre uso por error PASA
vector: rxre NO depende de ninguna funcion propia del registro       PASA
```

## 5 · El dato que faltaba en el informe de `1188`

`1188` afirmaba que el registro único de herramientas era `toolreg` y que `rxre`
lo consultaba sin duplicarlo. **Era verdad y a la vez falso**: `rxre` consultaba
*una versión de `toolreg` que solo existía en mi árbol de trabajo*. La afirmación
era correcta sobre el papel y falsa sobre el árbol, y no había forma de notarlo
porque `git status` mostraba `M`.

```text
MEDIDO   rxre            141 -> 155 vectores rc=0
         toolreg         14 checks, 0 failures (fichero COMMITEADO, 1208 lineas)
         layoutcross     79 vectores
         mmio            48 vectores
         oraculo ibref   116 vectores
         ibref.py        77 de 116
         verif           DERIVA 11 -> 5 de 51
```

`verif` es la corroboración independiente de que el `toolreg` pisado **no era
equivalente**: seis de las once derivas desaparecieron al restaurar el bueno. No
era un fichero parecido, era peor, y el motor de deriva lo sabía sin que yo lo
escuchara.

## 6 · Procedimiento

```text
detectado    git diff --stat dio 1618 en toolreg.py; un fichero mas corto no
             puede ser una mejora de uno largo.  Idoneidad: nombre.
comprobado   1208 vs 473 lineas; 0 defs comunes; 14 checks vs 22 vectores
autoria      los hallazgos que citan toolreg (1043-1065) no llevan AUTOR; los
             mios (1185, 1188) si
reparado     git checkout tools/toolreg.py -> intacto en HEAD, 14 checks 0
             toolreg.py NO commiteado.  El commit 0764ffe no lo toca
adaptado     rxre estado_de(): 3 universos (EN_ARBOL / EN_PATH / AUSENTE)
             + TOOLREG_INTERFAZ comprobada, no llamada a ciegas
arreglado    spatch duplicada fuera; dynamic_debug con su ruta real;
             CAP_REFUTADA + capacidades_ruteables + filas_duplicadas;
             _caps_totales suma lo solo-refutado
medido       rxre 155 rc=0; huecos 4 -> 5 con la nueva razon; verif 11 -> 5
no hecho    no se audito si OTROS ficheros de tools/ con el mismo nombre tienen
            el mismo problema.  El caso esta cerrado; la clase, no.
escrituras   1 commit propio (0764ffe).  0 ficheros de otras sesiones
runtime      RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  DRIVER=i915 intacto
```
