# AGENT RE/TOOLING — REGLAS DE OPERACION Y CADENCIA DE INFORME

<!-- PROPIEDAD DE: AGENT RE/TOOLING (rol instrumental).
     NO lo edita ningun otro nodo.  Si este fichero lo cambia alguien, ese
     alguien ha cambiado el rol, y eso se dice en el commit.
     Fichero NUEVO.  No toca AGENTS.md (lo posee AGENT-05 COORDINACION) ni
     promp.md (que es el prompt del GLOBAL COORDINATOR, de otro rol). -->

```
ROL          INGENIERIA INVERSA + TOOLING.  No soy el agente principal del
             driver.  Mi producto es CAPACIDAD DE RE SOBRE ESTA RX550.
ARBOL        ~/Escritorio/RX550-INVESTIGACION
GPU          INTACTA salvo peticion expresa.  sin sudo por defecto.
ESCRITURA    solo ficheros NUEVOS, salvo que el dueno del fichero sea mio.
```

## 1 · CICLOS CERRADOS

Un ciclo se cuenta cuando la acción tiene **PASS, FAIL e INVALID definidos** y
el artefacto está escrito con su procedencia verificada. No se cuenta una
exploración, ni un `--selftest` que pasa, ni un hallazgo sin artefacto.

| # | ciclo | artefacto | hallazgos | estado |
|---|---|---|---|---|
| 1 | `R5a-PROSA` — el contrato en prosa no se falsificaba; 6 opciones documentadas que no existen | `08-ARQUITECTURA/artifacts/R5a-PROSA/` | 1064, 1065, 1066 | CERRADO |
| 2 | `R6-PM4TILA` — la longitud de un paquete PM4 estaba contestada de 3 maneras; `count+2` es la única que embaldosa el anillo real | `08-ARQUITECTURA/artifacts/R6-PM4TILA/` | 1062, 1063, 1067, 1068 | CERRADO |

**CONTADOR DE ESTE ROL: 2 ciclos, 7 hallazgos (1062–1068).**

### El contador del árbol es COMPARTIDO, y por eso van separados

MEDIDO: hay otra sesión escribiendo en este árbol y reserva números en lotes.
El contador de la directiva sube también por su trabajo, así que **presentar
el número más alto como "trabajo mío" sería robarle la medida**.

```
trabajo acumulado en el árbol        573 hallazgos en 472 números   (MEDIDO)
número más alto                      1073 reservado, 1074 libre    (MEDIDO)
de los cuales, hallazgos de este rol    7   (1062..1068)
```

Y una consecuencia operativa que ya costó un número: **`--check` y luego
`--reservar` NO es atómico.** MEDIDO: `--reservar 1062` devolvió `OCUPADO`
porque la otra sesión escribió el fichero en el intervalo. La única forma
lícita de tomar número es **`--reservar`**, y si falla se toma el siguiente.
Comprobar antes y reservar después abre una ventana de carrera.

## 2 · INFORME AL HUMANO

### MEDIDO, y con un número

```
ciclos cerrados            2
herramientas nuevas         2   prosa.py, pm4tila.py
ficheros nuevos             6   (2 herramientas + 2 artefactos .json/.txt + 2 HALLAZGOS.md)
ficheros EXISTENTES         0   modificados.  Ninguno.
GPU                         INTACTA
sudo                        NO usado
commits                     NINGUNO
selftest                    51 vectores en total, 0 fallos
                             prosa.py   28
                             pm4tila.py 23
reproducibilidad            ambos artefactos: hash identico en 2 corridas
procedencia                 6 de 6 hashes de encabezado verificados contra el fichero
```

### LOS HALLAZGOS, en orden de peso

**1. Seis herramientas documentan opciones que no existen.** `claim.py
--coverage`, `msg_census.py --list-unknown`, `reg_resolve.py
--across-headers`, `struct_layout.py --fields`, `xref.py --declares`,
`contradict.py --with-code`. Están en su propio bloque de opciones, son ejemplos
de uso, y no funcionan. Las cinco primeras están marcadas `TOOL_VALIDATED`.

> **Por qué no lo vio nadie:** el registro mide que la herramienta *funciona*
> (su `--selftest` pasa). No mide que su *documentación* sea ejecutable. Una
> herramienta cuyo docstring da una orden que sale con error está validada y
> equivocada a la vez, y nada en el registro actual distingue esos dos estados.

**2. `count + 1` es la convención de longitud de paquete PM4 que usa el código,
y no puede ser.** Tres sitios del proyecto dan tres respuestas
(`pm4dec.py:29` docstring, `pm4dec.py:442` código, `pm4_codec.py:25`), y el
propio `pm4dec.py` imprime una cuarta contradictoria en su línea 1008.

Adjudicado por **teselación exacta** del anillo real (16 convenciones, 2
sobreviven, coinciden en `count + 2`) y corroborado por **129 constructores del
driver contra 0**.

**3. El modo de fallo importa más que el número.** `pm4dec.py` reporta 1808
paquetes donde hay **1728**; cada longitud va un dword corta y el dword sobrante
se cuenta como fila `PKT0(dato)`. **La suma total da 2048 exacto.**

> El error sistemático y su compensación se anulan. **Un decodificador cuya suma
> cuadra no está validado: cuadra *a pesar de* estar mal.** Eso no lo detectaba
> ningún control del proyecto.

**4. La afirmación más pesada del decodificador PM4 no es falsable con
análisis de prosa.** El docstring de `pm4dec.py` declara `sid.h` cuando su
código usa `vid.h` por grafo de includes. Un grep lo marca *correcto*, porque
`sid.h` aparece en el código: lo nombra para excluirlo. La verdad la da el
cierre de includes, no un verificador de prosa.

### MIS ERRORES, que son la parte que hace válido lo anterior

| error | lo cazó |
|---|---|
| **el docstring contaba como código**: `ast.walk` ve el docstring como cualquier cadena, así que toda declaración salía `SUSTENTADA` | el selftest: 9 de 18 vectores fallaron |
| **inventé 11 votos** contra la convención correcta, contando payload de constructores que no usan `amdgpu_ring_write` | la contradicción 129 vs 11 |
| **35 falsos positivos** de un total de 35 filas FLAG, por guiones parentéticos y flags de otros programas | adjudiqué 8 a mano: 4 falsos |
| **dos vectores de selftest míos** afirmaban `UNICA` con `count = 0`, donde `count+2` y `2·count+2` son indistinguibles | fallaron; la herramienta acertó |
| **hermetismo recursivo**: el vector comprobaba el cwd lanzando `--selftest`, que lo relanzaba | 120 s de timeout, sin imprimir |

El patrón: **cinco de esos cinco los cazó una comprobación, no la lectura.**

### LO QUE NO HICE, y por qué

- **No corregí `pm4dec.py:442`.** Es una línea (`i + 1 + cnt` → `i + 2 + cnt`),
  pero `revkit/` estaba modificado sin commitear por otro nodo. Dejar el
  arreglo como `OBSERVATION_FOR_MAIN_AGENT` cuesta un informe; escribir encima
  del trabajo de otro cuesta un conflicto.
- **No regeneré `TOOLS-STATUS.md`.** Lo genera `tools/artifacts.py`, que otro
  nodo tenía modificado. Habría escrito sobre su trabajo.
- **No decidí qué opcode es el bueno para GFX8**, ni si el residuo del anillo
  describe una carga real. Es semántica de hardware: no es mío.

### LO QUE SIGUE ABIERTO, y es lo que más me importa

1. `PACKET2 = NOT_DETERMINED`. El anillo GFX no tiene ningún PACKET2 con cuenta
   ≠ 0, así que **el dato no existe**. Se necesita captura nueva: es del nodo
   de runtime, no mío.
2. 69 de 198 constructores del driver quedan `fuera_de_alcance` (los que
   escriben por `ib.ptr[...]` o buffer de CPU). Cubrirlos sube la corroboración
   de 129 a ~198.
3. `prosa.py` solo cubre `.py`. Los 32 `.c`/`.sh` son `NO_CLASIFICABLE`: su
   prosa vive en comentarios, y `ast` no la da. Requiere otro oráculo.
4. `SOLO_EN_LISTA` no es falsable con prosa. Necesita el resolvedor de grafo de
   includes que R2 ya tiene a medias.

## 3 · CADENCIA DE INFORME — LA REGLA

> **Cada 1000 ciclos cerrados, el agente RE/TOOLING entrega al humano su
> informe.**

Regla como la pidió el humano, literal, sin reinterpretar. Vive en §3 y el
contador que la dispara está en §1.

### Y una observación sobre por qué no dispara, medida

`cada 1000 ciclos` es, hoy, **una regla que no se dispara nunca**:

```
ciclos cerrados MEDIDOS           2   (en una sesion)
hallazgos numerados del proyecto  ~1000, pero son HALLAZGOS, no ciclos
```

A dos ciclos por sesión, 1000 ciclos son ~500 sesiones. La regla pediría un
informe dentro de un plazo que no existe, y una puerta que no se dispara no
protege nada — es el fallo espejo del que el propio proyecto ya escribió en
`toolreg.py`: *"an interlock that cries wolf gets ignored, and then it protects
nothing"*, pero en su versión silenciosa.

**No he cambiado el número.** La regla de arriba es la del humano y está escrita
como la pidió. Lo que dejo debajo es una cadencia de trabajo que sí se dispara,
en una sola línea y fácil de borrar:

> **Línea de trabajo (borrable):** además del hito de 1000, entregar informe
> al humano **cada 10 ciclos cerrados**, y **siempre** que un ciclo produzca un
> hallazgo que refute un claiming previo del proyecto.

Si el humano prefiere solo el hito, se borra esa línea y no cambia nada más.

## 3 bis · CONDICIÓN DE PARADA — 1000 MEJORAS MÍNIMO PARA ENTREGAR INFORME

```text
DIRECTIVA=PROPIETARIO DEL ARBOL · 2026-10-04
PARADA=No entregar informe por encima de 1000 mejoras.
       El informe se entrega AL LLEGAR a 1000, no antes.
PENDIENTE=el humano no confirmó cuál de las dos unidades; se adopta la (2)
          porque es la más exigente y la que no se puede cumplir con relleno.
```

### Por qué la unidad está definida, y no es burocracia

`§99 NO TOOL THEATER` dice: *«No crear herramientas para poder decir que
existen herramientas».* Una cuota de "1000 mejoras" sin definir la unidad **manda
hacer exactamente eso**, y el árbol ya paga el coste de tener muchas: 194
herramientas con 63 `TOOL_UNVALIDATED`.

MEDIDO al escribir esta regla:

| lectura de "mejora" | objetivo | veredicto |
|---|---|---|
| herramienta nueva | 1000 | **prohibida por §99** — tengo 2, y el problema del árbol no es que falten |
| hallazgo con transición de estado | 1000 | coherente con la directiva de 3106 |

### LAS DOS CONDICIONES, y las dos hacen falta

Una unidad cuenta como **1 mejora** si cumple **AMBAS**:

**1 · Cambio de estado justificado.** Produce una transición verificable:
`PROVEN` · `CORROBORATED` · `REFUTED` · una herramienta pasa a `VALIDATED`.

> **NO cuenta**: un fichero nuevo sin evidencia · una reformulación de algo ya
> dicho · una exploración sin veredicto · un número de hallazgo nuevo sin más ·
> una cifra que ya estaba en otro documento.

**2 · Trazabilidad hasta la RX550.** La unidad tiene que ser una medida **sobre
el ASIC**, **sobre el corpus de esta ASIC**, o **sobre un instrumento cuyo oráculo
se validó contra el ASIC**.

> Sin la condición 2, una cuota se cumple con trabajo de método. Con ella, se
> cumple con RE.

### El contador de la regla NO es el número de hallazgo

MEDIDO, y es la razón por la que esto está escrito:

```
  hallazgos en el arbol                621
  numeros duplicados                  74  -> 102 ficheros de mas, sin trabajo
  mejoras CONTABILIZADAS de este rol  20
```

El **número más alto no mide mejoras**: gasta números. `1122-reservar-funciona-y-
aun-asi-mi-numero-quedo-ocupado.md` mide por qué —`--reservar` garantiza
exclusividad sobre *el ledger*, no sobre el *filesystem*, y entre el arbitro y el
detector no hay nada que impida la colisión.

> **Por eso el objetivo son 1000 mejoras CONTABILIZADAS por §3 bis y no 1000
> números de hallazgo.** Con el número se puede "llegar" sin haber hecho nada, que
> es exactamente lo que la directiva de trabajo advierte cuando dice que el
> contador sobrestima.

### Las tres salidas de §3 bis, y solo una es el objetivo

```
  REGLA.   1. 1000 mejoras por §3 bis  ->  la-condition de parada
  LINEA.   2. 10 ciclos cerrados        ->  cadencia de trabajo, borrable
  SUPUESTO 3. 1000 ciclos cerrados      ->  se cumple solo si 2 llega a 1000
```

## 4 · LO QUE NO CAMBIA

- Un ciclo sigue siendo una acción con PASS, FAIL e INVALID definidos.
- `NO_RESULT` no es `ZERO_EFFECT`. Un ciclo que no produce nada no se cuenta
  como avance, y se dice.
- Toda cifra de este fichero se mide ejecutando, no se escribe de memoria.
- Los hashes de procedencia se verifican contra el fichero **después** de la
  última edición del encabezado.