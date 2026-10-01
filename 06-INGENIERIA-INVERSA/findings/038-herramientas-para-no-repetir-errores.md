# 038 · Herramientas para no repetir a mano lo que ya me costó errores

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` sobre el corpus · `RUNTIME=NOT_RUN`
`GPU INTACTA`
`HERRAMIENTAS_NUEVAS=08-ARQUITECTURA/tools/doclint.py`, `corpus_guard.py`
`MEJORA=pm4_reachable.py` (deteccion de conflictos de valor)
`CONTINUES=036`, `037`

## CUDA principal

Dos herramientas que automatan lo que hacia a mano **cada ronda**, y que ya me habian
costado errores concretos:

1. **`doclint.py`** — verifica un hallazgo: intrusiones de otro idioma, citas de linea
   verificables contra el corpus, marcadores sin resolver, cabecera, y contradicciones
   numericas internas. **36 documentos, 0 errores.**
2. **`corpus_guard.py`** — envuelve una prueba de mutacion y **restaura siempre**, con
   verificacion de hash de 2787 ficheros antes y despues. Convierte una secuencia de
   cuatro pasos manuales en una linea.

Y el resultado que mas importa no es que las herramientas funcionen, sino **las cinco
veces que fallaron ellas mismas** — y una de ellas explica por que mis ultimos documentos
tenian 4 fragmentos en otro idioma que yo no veia.

## Alcance exacto

1. Automatizar las dos comprobaciones que mas tiempo consumian.
2. Que cada herramienta se valide a si misma, incluida su propia regla.
3. Lo que las herramientas revelan sobre el ASIC.

## Criterio de terminacion (cumplido)

Dos herramientas entregadas, autotest incorporado, validacion por mutacion sobre el
corpus real, y cuatro hallazgos nuevos (tres de ellos bugs de las propias
herramientas). Agotado.

---

## 1 · `doclint.py` — que comprueba y por que

Cada comprobacion corresponde a un fallo REAL mio, con su coste. No es un linter de
estilo.

| comprobacion | fallo que automatiza | frecuencia observada |
|---|---|---|
| intrusiones de otro idioma | fragmentos CJK pegados en frase castellana | **6 de 6 ultimas rondas** |
| marcadores sin resolver | `TODO`/`FIXME`/`???` en un doc que se declara cerrado | — |
| citas verificables | citar una linea que no existe o que no dice lo afirmado | `032`, `036` |
| cabecera de clasificacion | el hallazgo no declara su propio estado | — |
| contradiccion numerica interna | el mismo clave con dos valores | `035` (3 sesiones) |

### 1.1 · La intrusion de otro idioma: el defecto mas frecuente que tengo

Aparecio en `031`, `032`, `033`, `034`, `036` y `037`. Siempre un fragmento CJK dentro
de una frase en castellano, y **siempre se me paso** porque lo escribi rapido y no lo
relei. Es el fallo mas automatizable que tengo: un rango de caracteres.

El rango CJK es la red amplia. Pero los fragmentos que se me colaron **no eran todos
CJK**; algunos eran basura lexica (`fj*`, `zyj`, `annon`) que un rango no detecta. Por
eso hay una segunda comprobacion con una lista corta de intrusiones **concretas**, cada
una con su documento de origen. No es un diccionario arbitrario: cada entrada se puede
enseñar.

```bash
python3 doclint.py --self     # todos los hallazgos 020-039
```

Salida actual sobre los 36 documentos:

```
documentos: 36   errores: 0   avisos: 35
```

### 1.2 · Verificacion de citas: el fallo que produjo una afirmacion falsa

En `032` cite `gfx_v8_0.c:6231-6248` sin haberla leido. En `036` cite `6162-6178` y tuve
que comprobarlo despues. El linter resuelve cada `fichero.c:NNN` contra el corpus y avisa
si el fichero no existe o si la linea esta fuera de rango.

Y al lanzarlo aparecieron **35 citas abreviadas** en mis propios documentos:

```
ib.c:223   amdgpu_vm_flush(ring, ...)  -->  emite COND_EXEC #1  (vm.c:840)
```

`ib.c` y `vm.c` **no son resolvibles**: hay decenas de ficheros que casan con esos
nombres. Es mi estilo de cita, y es una cita que nadie puede verificar. El linter lo
detecta; corregirlo es trabajo mio.

### 1.3 · El linter tiene que distinguir redactado de citado

Los ultimos 5 "errores" que reportaba eran codigo **del kernel que yo transcribi**:

```
027  /* TODO: move that into ASIC specific code */    <- comentario del driver
031  /* XXX check if swapping is necessary on BE */    <- comentario del driver
```

Marcarlos como error habria invite a "arreglarlos", es decir, a manipular
la cita. Un hallazgo que transcribe un comentario con un `TODO` dentro **esta
transcribiendo evidencia**, no tiene un marcador sin resolver.

Asi que el linter calcula que lineas son **citadas** —bloque cercado con ```` ``` ````, o
fragmento entre acentos graves— y no audita esas lineas. Resultado: de 5 errores a 0.

## 2 · `corpus_guard.py` — la restauracion que siempre temia olvidar

Cada prueba de mutacion era esta secuencia manual:

```
cp fichero /tmp/backup
mutar
ejecutar la herramienta
cp /tmp/opencode/backup fichero
git status --porcelain RESEARCH/     <- comprobar que VOLVI
```

El ultimo paso es el que puede fallar, y si falla **el corpus queda modificado y todas
las rondas siguientes miden codigo que yo altere**. Es la contaminacion mas dano: silenciosa
y persistente, y aparece como si fuera un hallazgo.

```bash
python3 corpus_guard.py --snapshot                       # huella: 2787 ficheros, 1.6 s
python3 corpus_guard.py --mutate FICHERO 'COMANDO'      # restaura SIEMPRE, verifica
python3 corpus_guard.py --verify                         # estado + git status
python3 corpus_guard.py --git                            # solo git status
```

`--mutate` usa `try/finally`: restaura aunque el comando falle, y despues compara la
huella completa con la referencia.

### 2.1 · La primera prueba dio justo el caso que importa

La primera mutacion que lance **fallo** —mi patron de busqueda no casaba con los tabs del
fichero— y el guard hizo lo que tiene que hacer:

```
copia de seguridad de sid.h
--- comando devuelto 1 ---
restaurado sid.h
verificacion tras restaurar: sin diferencias
corpus intacto
```

Es el caso que mas me importa: **mutacion fallida, restaurado garantizado**. Un guard que
solo restaura en el camino de exito no sirve para nada.

La segunda, con mutacion valida, dio el ciclo completo: `0x22` -> `0x23`, herramienta
ejecutada, restaurado, `sin diferencias`, `git status` vacio.

## 3 · Las cinco veces que fallaron las herramientas

Esta parte es la que mas valoro, porque es exactamente el patron de `024`/`031`/`032`/
`035`: **las herramientas fallan con los mismos modos que yo.**

### 3.1 · `\bTODO\b` con `re.I` casaba con "todo" en castellano

La primera version de la regla de marcadores era case-insensitive. En un corpus en
castellano eso produce miles de falsos positivos: `todo el ASIC`, `para todo`,
`todo lo que`. El linter habria sido inservible en dos rondas.

Lo que lo salva no fue una ejecucion: fue leer los cuatro "errores" y ver que todos
contenian la palabra **todo**. **Un linter que dispara sobre castellano no lo notas
mirando la salida: lo notas leyendo lo que dispara.**

Corregido: `TODO`/`FIXME`/`XXX`/`TBD` exigen mayusculas, que es su convencion.

### 3.2 · El autotest se debe a si mismo un caso de prueba corrupto

Al escribir el caso de prueba de `???` en el autotest, el shell lo convirtio en `¿¿¿` —
signos de interrogacion invertidos. El autotest **fallo**, porque `¿¿¿` no es `???`.

Eso es el autotest funcionando: si no llego a ejecutarse, el caso corrupto habria pasado
desapercibido y la comprobacion no habria existido. Arreglado con `chr(63) * 3`, que no
se corrompe al pasar por shell.

### 3.3 · Precedencia en un condicional: `ERROR` sin mensaje

```python
(errs if in_code else warns).append(msg + " [dentro de codigo]" if in_code else "")
```

Se evalua como `append((msg+"...") if in_code else "")`: fuera de bloque de codigo mete
**cadena vacia** en la lista de errores. El informe decia `ERROR` a secas.

Es el fallo mas perjudicial posible en un linter: **gasta el canal mas grave en un evento
intrascendente**, y entrena al lector a ignorar la palabra ERROR.

### 3.4 · El nombre del paquete era ambiguo, no inexistente

`pm4_reachable.py` resolvia valores de opcode con `setdefault` recorriendo cabeceras en
**orden alfabetico**. Si dos cabeceras dieran valores distintos, se quedaba con la
primera **y no lo decia nunca**. No da un numero falso: da un numero arbitrario sin
marcar.

Lo encontre mutando `sid.h` para cambiar `COND_EXEC` de `0x22` a `0x23`, y la
herramienta siguio diciendo `0x22`. Mi primera explicacion fue "GFX8 toma el opcode de
otra cabecera". **Era falsa**: los cinco headers de este corpus definen `COND_EXEC` como
`0x22`. El opcode es redundante, no contradictorio.

Pero la herramienta **no podia distinguir un caso del otro**, y por eso le faltaba la
comprobacion. Anadida: recoge todos los valores y declara los conflictos.

### 3.5 · `pm4_reachable` resolvia cabeceras por alfabeto en vez de por includes

El defecto de fondo de 3.4. La respuesta correcta —que opcode ve realmente GFX8— la da
el preprocesador, y lo intente:

```
gcc -E -P -I$K/include -I$K/arch/x86/include -I$K/arch/x86/include/generated ...
60391 lineas preprocesadas
fatal error: dm_services_types.h: No existe el fichero o el directorio
```

`dm_services_types.h` **no existe en el sistema**. Es un header que el
`dm_pp_interface.h` del corpus espera y que las cabeceras del kernel instalado no
traen. El preprocesado se detiene ahi.

`LIMITATION` declarada: **no se puede resolver el cierre de includes con el preprocesador
en esta maquina.** Y la consecuencia util es que la resolucion por orden alfabetico se
queda como aproximacion, y ahora **declara sus conflictos en vez de ocultarlos**.

## 4 · Los cuatro conflictos que declara

Con la comprobacion nueva:

```
PACKET3_INDIRECT_BUFFER_CONST   0x31 en sid.h   |  0x33 en cikd,soc15d,vid
PACKET3_LOAD_CONFIG_REG         0x5F en sid.h   |  0x60 en cikd,v12_1,nvd,soc15d,vid
PACKET3_LOAD_CONTEXT_REG        0x60 en sid.h   |  0x61 en cikd,v12_1,nvd,soc15d,vid
PACKET3_LOAD_SH_REG             0x5F en cikd,v12_1,nvd,soc15d,vid  |  0x61 en sid.h
```

**Cuatro paquetes fueron renumerados entre generaciones.** `LOAD_SH_REG` es `0x5F` en
cuatro headers y `0x61` en `sid.h`; `LOAD_CONTEXT_REG` es justo al reves. Copiar una
constante de opcode del header equivocado emite **el paquete equivocado**, y no hay
ningun sintoma hasta que el hardware hace otra cosa.

### 4.1 · Y la pregunta que si importa: ningun vivo esta afectado

```
ninguno de los 21 opcodes de la categoria A aparece en la lista de conflictos
```

Comprobado, no supuesto. Los cuatro conflictivos —`LOAD_SH_REG`, `LOAD_CONFIG_REG`,
`LOAD_CONTEXT_REG`, `INDIRECT_BUFFER_CONST`— son construcciones de **Mesa** para escribir
registros desde memoria; amdgpu no los usa en GFX8.

Asi que el defecto es real pero **no afecta al inventario de `036`**. Lo digo
explicitamente para que no se lea como una contaminacion del resultado anterior.

## 5 · Clasificacion

| afirmacion | estado |
|---|---|
| `doclint.py` pasa su propio autotest antes de usarse | `PROVEN` — 6 casos de marcador, 2 de CJK, intrusiones |
| 36 hallazgos, 0 errores | `PROVEN` |
| Las intrusiones CJK aparecieron en 6 de 6 rondas previas | `OBSERVATION` de mi propio historial |
| `corpus_guard.py` restaura aunque el comando falle | `PROVEN` — primera prueba |
| La huella cubre 2787 ficheros y tarda 1,6 s | `PROVEN` |
| El corpus quedo intacto tras 2 mutaciones | `PROVEN` — `git status` vacio |
| `\bTODO\b` con `re.I` casa "todo" en castellano | `PROVEN` |
| `PACKET3_COND_EXEC` es 0x22 en los 5 headers | `PROVEN` |
| 4 opcodes tienen valor distinto en distintas cabeceras | `PROVEN` |
| Ninguno de los 21 opcodes vivos esta entre esos 4 | `PROVEN` |
| Que valor ve **realmente** el preprocesador | `NOT_DETERMINED` — `dm_services_types.h` ausente |
| Las 35 citas abreviadas (`ib.c`, `vm.c`) son mias | `PROVEN` — 021, 022, 024 |

## 6 · Confounders

- **`dm_services_types.h` ausente.** No es un problema de Flags: el header no existe en
  ninguna parte del sistema. El corpus `dm_pp_interface.h` es mas nuevo que las
  cabeceras del kernel instalado, o estas estan incompletas. Esto **impide usar el
  preprocesador como verdad**, que era el objetivo. `LIMITATION`, no bug mio.
- **El rango CJK tiene falsos positivos legitimos:** codigo de terceros citados. Se
  separan en un bucket de "citado" que no se audita. Un fragmento CJK **dentro de codigo
  que yo escribo** pasaria como correcto; no se distingue "codigo mio" de "codigo
  citado" mas alla de los acentos graves y los bloques cercados.
- **La lista de intrusiones lexicales es corta a proposito.** Es una lista de fallos
  reales observados, no un detector de basura. Ampliarla sin un caso real que la justifique
  es anadir ruido.
- **El linter solo mira hallazgos `02x` y `03x`.** Los de otras sesiones (`040`+) y los
  del diseno (`08-ARQUITECTURA/designs/`) tienen otro esquema y no se auditan.
- La comprobacion de cabecera es **aviso, no error**, porque otras sesiones usan otro
  esquema de cabecera. Imponer el mio como error seria ruido de una regla ajena.
- `corpus_guard` protege `RESEARCH/working/linux-7.1.3`. **No protege** `04-IMPLEMENTACION`
  ni `07-DRIVER`, que son donde otras sesiones construyen. Anadirlos haria la
  comprobacion de integridad mas cara sin benefitio para esta ronda.

## 7 · UNLOCKS

- **La comprobacion de calidad pasa de ritual a comando.** Un solo `doclint.py --self`
  sustituye la pasada manual de releer y grep que hacia cada ronda, y encuentra en
  segundos lo que a mi se me pasa en seis.
- **La prueba de mutacion deja de ser una secuencia de cuatro pasos** y pasa a ser una
  linea con restaurado garantizado. Eso elimina la contaminacion silenciosa del corpus,
  que es el peor modo de fallo posible en un proyecto de ingenieria inversa.
- **Una resolucion que antes era silenciosa ahora declara sus conflictos**, y ha
  encontrado cuatro renumeraciones de opcode entre generaciones que eran invisibles.
- **`DESIGN_FREEDOM` sobre el metodo, no sobre el hardware:** las cinco veces que fallaron
  estas herramientas fallaron con los mismos modos que yo (buscar el primer indicio,
  asumir equivalencia entre lo similar, no distinguir lo citado de lo redactado,
  dejar un arbitrario sin marcar). Automatizar **reproduce** los errores si no se
  auditan las reglas.
- Queda una herramenta que **si** hace falta y no existe: un resolutor del cierre de
  includes que no dependa del preprocesador. Es el hueco conocido de esta ronda.

## 8 · Criterio de falsificacion

Se refutaria si: (a) el autotest pasara con una regla que no dispara sobre una intrusion
real — refutable metiendo un CJK en un documento temporal y viendo que el linter lo ve,
que es lo que hace el propio autotest; (b) `corpus_guard` no restaurara un fichero
modificado — refutable con `--mutate` sobre un fichero real, que es lo que se ha hecho
dos veces; (c) el rango CJK no detectara un ideograma — refutable, y esta en el autotest;
(d) el rango CJK detectara castellano — refutable, y tambien esta en el autotest con
"el campo de bytes"; (e) `dm_services_types.h` apareciese y el preprocesador cerrara —
refutable en un segundo con `find /`; (f) alguno de los 21 opcodes vivos tuviera
conflicto de valor — refutable cruzando las dos listas de la salida, que es lo que se
hizo.

## 9 · Evidencia

```
HERRAMIENTAS NUEVAS:
  08-ARQUITECTURA/tools/doclint.py
    autotest: 6 casos de marcador, 2 de CJK, intrusiones lexicales
    resultado sobre 36 documentos: 0 errores, 35 avisos
    avisos que quedan: cabecera de otro esquema (otras sesiones)
                        y 35 citas abreviadas propias (ib.c, vm.c)
  08-ARQUITECTURA/tools/corpus_guard.py
    huella: 2787 ficheros bajo RESEARCH/working/linux-7.1.3, 1.57 s
    --mutate con try/finally: restaura aunque el comando falle
    prueba 1: mutacion fallida (patron mal escrito) -> restaurado, sin diferencias
    prueba 2: mutacion valida 0x22 -> 0x23       -> restaurado, sin diferencias
    --verify: sin diferencias, git status vacio

MEJORA:
  08-ARQUITECTURA/tools/pm4_reachable.py
    opcode_values() ahora devuelve tambien los CONFLICTOS de valor
    4 conflictos declarados: INDIRECT_BUFFER_CONST, LOAD_CONFIG_REG,
                             LOAD_CONTEXT_REG, LOAD_SH_REG
    0 de los 21 opcodes vivos afectado

LIMITACION INVESTIGADA:
  gcc -E sobre gfx_v8_0.c: 60391 lineas, luego
  fatal: dm_services_types.h no existe en el sistema
  => el preprocesador no puede ser la verdad del cierre de includes aqui

BLOQUES QUE YA FUNCIONABAN (6 de 7 herramientas con validacion negativa):
  pm4_count_census.py    mutante
  pm4_layout_audit.py    mutante
  pm4_reachable.py       mutante + ahora autocomprueba el resolutor de opcode
  gmmio_inventory.py     2 mutantes, uno valida el validador
  doclint.py             autotest
  corpus_guard.py        2 mutaciones reales sobre el corpus
```

`WRITE_EXECUTION=NONE`. Ninguna escritura a la GPU. `GPU INTACTA`.