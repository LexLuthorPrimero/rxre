# EP08-VALIDATION — el instrumento experimental EP08 **no puede ejecutarse**, y su OFFSET GUARD no mide lo que dice medir

```text
AUTORIA        = AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES) · workspace 04-RUNTIME-PROBING
WORK_CLASS     = READ_ANALYSIS + WRITE_LOCAL (instrumentos + artefacto + 1 hallazgo)
NODE_ID        = EP08-VALIDATION
CERROJO        = .write-lock/ep08-validate (mkdir atómico). ROOT pertenece a
                 global-coordinator-04, mismo rol y mismo workspace: continuidad,
                 NO es LOCK_TAKEOVER. Los 19 sub-ámbitos con owner caduco se
                 declaran y NO se tocan.
RUNTIME        = SÍ, y deliberadamente SÓLO LECTURA
GPU            = INTACTA. Cero escrituras a MMIO. Cero insmod/rmmod. Cero kprobe.
SUDO           = NO solicitado. Dos precondiciones quedan NOT_EVALUABLE por eso,
                 y se declaran como tales: NOT_EVALUABLE no es PASS ni FAIL.
TOKEN          = NO fabriqué. La puerta P0 se probó SIN token; ver §3.
ESCRITURAS     = 3 ficheros nuevos bajo 08-ARQUITECTURA/artifacts/EP08-VALIDATION/
                 + 1 hallazgo nuevo. 0 ficheros modificados fuera de mi ámbito.
```

---

## 1. La pregunta, y por qué esta y no otra

El harness `03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh` lleva **6 días** con
esta etiqueta en su cabecera:

```
# NO EJECUTADO. Preparado y revisado; pendiente de autorización humana.
```

Es el experimento que ataca la pregunta con más valor para el objetivo del proyecto:
**si el ring del CP avanza sin el doorbell, el doorbell es un MMIO write evitable por
workload** — es decir, coste de envío. Y está escrito con un rigor que este proyecto no
suele tener: puerta de autorización, `A` como puerta dura con evidencia textual literal,
`no_hw_access` sin lectura directa y validación conductual, ventana de restauración
documentada, y un `OFFSET GUARD` que el propio script llama *"el guard real"*.

La pregunta de esta ronda, entonces, **no es qué haría**: es

> **¿Está este instrumento en condiciones de ejecutarse?**

Con dos mitades que se responden con oráculos distintos y ninguno necesita la placa:

| | PREGUNTA | POR QUÉ IMPORTA |
|---|---|---|
| **a)** | ¿Puede llegar siquiera a su PHASE 1? | Un harness que aborta en el preflight no es un experimento pendiente: es un experimento roto. |
| **b)** | ¿Sus precondiciones vivas se cumplen hoy? | Si (a) es que sí y (b) es que no, la autorización humana no serviría de nada. |

**Veredicto: `INSTRUMENTO_INVALIDO`. Las dos mitades fallan, y fallan de forma
independiente.** §2 y §3.

Y el motivo por el que esto no es solo una curiosidad de shell: **el modo de fallo que
encuentra es exactamente el que el propio harness dice impedir.** Su OFFSET GUARD
existe para distinguir *"el struct se movió"* de *"el ring no avanza"*. Con el `awk` que
tiene, es incapaz de distinguir eso de *"mi parser lee el campo equivocado"*. Un guard
que no puede decir por qué dispara no es un guard: es una alarma que se dispara por
motivos que ella misma no puede nombrar.

---

## 2. (a) No puede llegar a PHASE 1 — y el motivo es `set -u`, no una decisión

`preruntime.sh` abre con `set -euo pipefail`. Bajo `-u`, **una variable no asignada es
un error fatal**, no un valor vacío. El script usa 8 variables que no declara:

| Variable usada | Línea | Declarada como | Dónde se declara |
|---|---|---|---|
| `TARGET_PCI_SUB_VEN` | 153, 160 | — | **nunca** |
| `TARGET_PCI_SUB_DEV` | 160 | — | **nunca** |
| `TARGET_PCI_REVISION` | 160 | — | **nunca** |
| `TARGET_MODALIAS` | 156 | — | **nunca** |
| `NHWA_OFF_ASIC_TYPE` | 214 | `NHWA_ASIC_TYPE_OFFSET` | 42, con otro nombre |
| `NHWA_OFF_PCI_SUB_VEN` | 217 | — | **nunca** |
| `NHWA_OFF_PCI_SUB_DEV` | 218 | — | **nunca** |
| `NHWA_OFF_PCI_REVISION` | 219 | — | **nunca** |

**El primer punto de-aborto es la línea 153**, dentro de P2 — la identidad PCI. Todo lo
anterior pasa: P1 (kernel) se evalúa bien.

### 2.1 Demostrado, no deducido

Se evaluó **la línea literal del script**, con las constantes que el script sí declara
ya cargadas, bajo `set -u`:

```
$ bash -c 'set -uo pipefail; d=$1; TARGET_PCI_VENDOR="0x1002"; TARGET_PCI_DEVICE="0x699f";
           [ "$(cat "$d/vendor")" = "$TARGET_PCI_VENDOR" ] &&
           [ "$(cat "$d/device")" = "$TARGET_PCI_DEVICE" ] &&
           [ "$(cat "$d/subsystem_vendor")" = "$TARGET_PCI_SUB_VEN" ] && echo IGUAL'
bash: línea 1: TARGET_PCI_SUB_VEN: variable sin asignar
exit=127
```

La línea 214 (`$NHWA_OFF_ASIC_TYPE`, en P8) falla por la misma razón, y queda
confirmada por captura propia.

### 2.2 Consecuencia que importa

El fallo es **fail-closed**: aborta en el preflight, antes de PHASE 2 y mucho antes de
PHASE 6 (`insmod`). **Ningún estado de hardware puede quedar cambiado por este defecto.**
La placa está a salvo; el experimento no.

---

## 3. La puerta de autorización: existe y funciona

Probada de verdad, **sin token**, sin GPU y sin escribir nada:

```
$ bash ./preruntime.sh
== PHASE 0 — autorización
STOP: falta --authorization=<TOKEN>. Esta ronda NO ejecuta nada.
exit=1
```

Comprobado tras la ejecución: `logs/` **no existe**, `nhwa` **no cargado**. La puerta es
real y cierra antes de PHASE 1.

**No se fabricó el token.** `RUN550-EP08` está escrito en el propio fichero, y obtenerlo
sin autorización humana habría sido autoautorización: exactamente lo que el proyecto
prohíbe. Por eso la mitad (a) se midió estáticamente y con la línea literal, que es lo
que permite llegar al mismo veredicto sin tocar la máquina.

---

## 4. (b) El OFFSET GUARD lee el TAMAÑO, no el OFFSET

Este es el hallazgo grande, y **no lo habría dado ningún test de ejecución**, porque el
harness aborta antes de llegar ahí.

`pahole v1.30` emite el offset y el tamaño en los dos últimos campos de la línea, y la
línea **termina en `*/`**:

```
^Ibool                       no_hw_access;         /* 381969     1 */
```

Tokenizada:

```
NF=6    NF-5=bool   NF-4=no_hw_access;   NF-3=/*   NF-2=381969   NF-1=1   NF-0=*/
```

Es decir: **`$(NF-1)` es el tamaño (1). El offset es `$(NF-2)`.** El harness usa
`$(NF-1)` en las ocho extracciones de offset de P8.

### 4.1 Qué haría P8 si llegara a ejecutarse

Medido con los awk **del harness**, no con otros:

| Precondición | offset real | tamaño | devuelve `$(NF-1)` | esperado por el harness | qué pasaría |
|---|---|---|---|---|---|
| `no_hw_access` | **381969** ✓ | 1 | `1` | `381969` | **FAIL con diagnóstico FALSO**: "el offset cambió a 1" |
| `asic_type` | 1640 | 4 | `4` | `$NHWA_OFF_ASIC_TYPE` sin asignar | abort |
| `pdev` | 8 | 8 | `8` | `8` | **PASS por casualidad** |
| `pci.vendor` | 60 | 2 | `2` | `60` | FAIL con diagnóstico falso |
| `pci.device` | 62 | 2 | `2` | `62` | FAIL con diagnóstico falso |
| `pci.subsystem_vendor` | 64 | 2 | `2` | sin asignar | abort |
| `pci.subsystem_device` | 66 | 2 | 2 | sin asignar | abort |
| `pci.revision` | 72 | 1 | `1` | sin asignar | abort |

Las tres filas con ✓, y las marcadas como tales, son el dato que sobrevive a todo lo demás:

> **El diseño experimental de EP08 sigue siendo válido para esta máquina.**
> `no_hw_access` está en `0x5D411` = 381969, el valor que el harness fijó el 2026-09-29.
> El struct **no se movió**. El kernel que corre es exactamente el que fijó:
> `7.1.3-200.nobara.fc44.x86_64`, y el `.ko` tiene el vermagic correspondiente.

Lo que está mal es el **instrumento**, no el hardware ni el diseño.

### 4.2 El `PASS` por casualidad es la fila peligrosa

`pdev` es un puntero: tamaño 8, offset 8. `$(NF-1)` devuelve 8 y la comparación contra
`NHWA_OFF_PDEV=8` **pasa**. Pasa leyendo el campo equivocado, y no hay nada en P8 que lo
detecte. Un guard que pasa por una coincidencia de magnitudes no ha medido nada; ha
coincidido. Es el peor caso posible de un guard: **verde por accidente**, en la misma
función que contiene la única comprobación que el script llama "el guard real".

### 4.3 Por qué importa para el objetivo, y no solo por higiene

EP08 discrimina entre dos respuestas al resultado de B (`preruntime.sh` §PHASE 12):

- `B1_CONSUMED_WITHOUT_EFFECT` → **el doorbell es necesario** → el MMIO write es
  irreducible, y el techo de rendimiento de envío está donde está.
- `B3_EXECUTION_WITHOUT_DOORBELL` → **el doorbell es evitable** → se puede publicar el
  WPTR y ahorrar un MMIO write por paquete en la ruta caliente del ring.

Esa distinción **no la puede resolver el propio B con su instrumentación actual**: con
`RESULT_CLASS` basado en el código de salida del test, el fallo por precondición
inválida y el resultado físico se mezclan en la misma rama de clasificación. El
`abort condition` está escrito; **la evidencia que lo distinguiría no está medida**.

---

## 5. Tabla completa de precondiciones vivas

Producida por `capture_preconditions.sh`, que **usa los awk del harness**, no otros.
24 filas, 6 columnas, vocabulario cerrado de veredictos, validadas por forma antes de
escribirse.

| veredicto | n | qué significa |
|---|---|---|
| `PASS` | 9 | se cumple |
| `INSTRUMENTO_ROTO` | 8 | el harness no puede ni intentarlo: constante sin declarar |
| `FAIL` | 4 | se incumple, o el harness mediría mal |
| `NOT_EVALUABLE` | 2 | requiere root; **no es PASS ni FAIL** |
| `PASS_POR_CASUALIDAD` | 1 | pasa leyendo el campo equivocado |

Detalle fila a fila: `preconditions-live.tsv`. Los dos `NOT_EVALUABLE` son
`amdgpu_regs` y `amdgpu_test_ib`, ambos bajo `/sys/kernel/debug/dri/`, que en esta
máquina es root-only (`Permiso denegado`, medido).

### 5.1 Una precondición que el harness no declara: root

```
$ grep -nE 'EUID|\bid -u\b|whoami|sudo' preruntime.sh
(sin coincidencias)
```

Y sin embargo: P3–P7 leen debugfs, que es root-only; PHASE 6 hace `insmod`, PHASE 7 y 8
hacen `rmmod`. **El script exige root en cinco sitios y no lo comprueba en ninguno.** Con
un usuario sin privilegios falla con `Permiso denegado` en P4, que es un mensaje que
nunca lleva a nadie a la causa. Tabla: fila `P_raiz` = `FAIL`.

### 5.2 Lo que SÍ está intacto, y conviene que conste

`preruntime.sh` acierta en cosas que otros ficheros de este proyecto no aciertan, y no
deben perderse por estar al lado de un defecto:

- La identidad de objetivo la hace de **5 campos + modalias**, no por el ID solo. El
  propio script razona por qué (`device 0x699f` no basta: `pci.ids` lista 5 tableros).
  Coincide con lo que el **finding 120** ya había Registrado sobre la tabla de DPM.
- `no_hw_access` **no se lee directamente**: se valida **conductualmente**, porque ningún
  debugfs ni registro la expone. Y declara por escrito
  `DIRECT_NO_HW_ACCESS_READ = NOT_AVAILABLE`. Eso es `NOT_AVAILABLE` correcto, usado bien.
- La puerta A exige la **cadena literal** `ib ring tests passed.` y prohíbe usar el exit
  code como sustituto. Es la regla de este proyecto aplicada a sí mismo.
- PHASE 10 se autodeclara `RESTORATION_VALIDATION` y **no** un tercer brazo
  experimental, precisamente para no contarse como evidencia física.

---

## 6. Dos instrumentos, y los dos se validaron en las dos direcciones

Se construyeron en lugar de hacerlo a mano, para que repetir esto sea un comando
(`RESEARCH_INSTRUMENT`; §99 *no tool theater*: sin ellos esto no sería reproducible).

### 6.1 `preruntime_audit.sh` — separa "mecánicamente muerto" de "medidor roto"

| control | resultado |
|---|---|
| **negativo**: harness sano → debe dar 0 sin asignar | `PASS`, 0. **Cero falsos positivos.** |
| **positivo 1**: declarar `TARGET_PCI_SUB_VEN` en una copia | 8 → 7. Desaparece. |
| **positivo 2**: añadir `$VAR_INVENTADA` sin asignar | 7 → 8. Aparece. |
| **suelo**: el harness real | 8, y **coinciden exactamente** con el `comm` manual independiente |

Sin el control negativo, «8 referencias sin asignar» habría sido un número sin
significado. Con él, es un detector que se sabe detectar.

### 6.2 `capture_preconditions.sh` — mide con los comandos del harness

Valida **la forma de su propio artefacto** antes de dar por bueno el resultado: 6 columnas
por fila y vocabulario cerrado de veredictos, si no, `exit 2`.

| control | resultado |
|---|---|
| TSV intacto | `exit 0` |
| fila de 3 campos inyectada | `FORMA_ROTA` + `exit 1` |

`exit 0` de este instrumento significa *auditado*, no *sano*. Está escrito en su salida,
porque es el mismo error que el harness evita en su puerta A.

### 6.3 Dos defectos propios, registrados porque son del mismo tipo que el encontrado

1. **Murió en silencio.** `set -e` + `pipefail` + un `grep` sin coincidencias (buscaba
   `${X:=`, que un harness sano no tiene) abortaba el instrumento con salida vacía. Se
   vio **solo porque se comprobó el exit code**. Es exactamente la clase de fallo que el
   **finding 109** ya había detectado en un tool anterior del proyecto.
2. **Falso positivo por precedencia de operadores.** `grep X || true | sed Y` se parsea
   como `grep X || (true | sed Y)`: `|` liga más fuerte que `||`. El `sed` no corría
   nunca, los `for k in` llegaban sin transformar, y las **variables de bucle de un
   harness sano se reportaban como no asignadas**. Se detectó al ver que el control
   negativo de §6.1 daba 3 falsos positivos (`a`, `d`, `k`). Fix: desactivar `errexit`
   en la sección de extracción, no parchear el operador.

Ninguno de los dos se habría visto por leer el código con atención: se vieron por
**ejecutar el control negativo**, que es lo que los distingue de una hipótesis.

---

## 7. Estado que cambia, y estado que no

```
EP08-VALIDATION                 RESOLVED · INSTRUMENTO_INVALIDO          NUEVO
  ├ a) alcanzable a PHASE 1     NO · 8 variables sin asignar bajo set -u · PROVEN
  ├ b) OFFSET GUARD operativo   NO · lee $(NF-1)=tamaño; offset es $(NF-2) · PROVEN
  ├ b) precondiciones vivas      9 PASS / 4 FAIL / 8 INSTRUMENTO_ROTO /
  │                             2 NOT_EVALUABLE (root) / 1 PASS_POR_CASUALIDAD
  ├ puerta de autorización       FUNCIONA · PROVEN por ejecución sin token
  └ precondición de root         AUSENTE en el harness · PROVEN por enumeración

DISENO EXPERIMENTAL EP08        VIGENTE · CORROBORADO
  no_hw_access sigue en 381969 = 0x5D411. El struct NO se movió.
  El kernel vivo es el que el .ko fijó. El experimento sigue siendo hacible.

EP08-DOORBELL                   DEFERRED · BLOQUEADO, no por el hardware
  Requisitos para desbloquear: (1) declarar las 8 constantes, (2) $(NF-1) -> $(NF-2),
  (3) declarar la precondición de root, (4) autorización humana para escribir en la placa.
  Ninguno de los cuatro es mío. (1)-(3) son de quien escribió el harness.

preruntime.sh                   INTACTO · sha c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633
  NO SE MODIFICA. Un instrumento con un defecto medido vale más como evidencia
  —de qué protege y de qué NO protege— que arreglado en silencio. Arreglarlo es
  otra acción, de otro turno, y es de otro rol.

GPU / MMIO / modulo nhwa        INTACTOS. Cero escrituras. Cero sudo. Cero token fabricado.
preruntime.sh en el arbol       0 modifications
```

---

## 8. Lo que este nodo NO hace, escrito para que no se lea de más

- **No corrige `preruntime.sh`.** El defecto está medido y probado; repararlo sería
  otra acción. §79 *repair over preservation* va en el sentido contrario: aquí preservar
  es lo correcto, porque el valor del fichero es ser la prueba.
- **No ejecuta el experimento.** Requiere autorización humana, y las escrituras sobre
  hardware las exige. No se pide aquí.
- **No declara inválida ninguna medición previa.** Nada se ha medido con este harness:
  no hay resultados que acotar.
- **No afirma nada del ASIC.** `no_hw_access` en 381969 es un hecho del **struct del
  módulo que corre**, leído por BTF. No es un hecho del silicio.
- **No cierra `CONTRAD-Q5-GFX8-ES-GCN3` ni ninguna otra contradicción.** Son de otro
  nodo; se listan aquí para que no se confundan con esto.
- **No toca** `CURRENT-STATE.md`, `KNOWLEDGE-GRAPH.md` ni ningún regenerado por
  `tools/artifacts.py`: son globales y hay otro nodo escribiéndolos ahora mismo.

---

## 9. Procedencia

| campo | valor |
|---|---|
| HEAD al empezar | `3d89682195b03f0244a5a2945f2a9567dff704eb` |
| `preruntime.sh` | `c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633` 25513 B — **sin modificar** |
| `nhwa.c` | `b06d8952214a0063f95c9a38fa347aa3efe59e730ae003d4067310620c0def3f` — sin modificar |
| `nhwa.ko` | `c537efbeeded4b8617a352ab3b5a128dafcb3f3c196caea535c28d92c75ff012` — sin cargar |
| `pahole` | **v1.30** (fija el layout de columnas; O3 del auditor) |
| kernel vivo | `7.1.3-200.nobara.fc44.x86_64` |
| objetivo | `1002:699f rev c7` · sub `1002:0b04` · modalias `pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00` |
| `/sys/kernel/btf/amdgpu` | 3882770 B, legible sin sudo |
| `/sys/kernel/btf/vmlinux` | 6357197 B |
| ficheros creados | `preruntime_audit.sh`, `capture_preconditions.sh`, `preconditions-live.tsv`, `preruntime-audit.tsv`, este informe |
| ficheros modificados | 0 fuera de mi ámbito |
| hash de reservation | hallazgo **973**, tomado con `tools/nextnum.py --reservar 973` (atómico) |
| concurrencia | AGENT-03 escribía `Q5-MEM-TABLES/`; AGENT-06 escribía bajo `drv-q8`. Ámbitos disjuntos, sin solape de ficheros. `findnum` estaba con owner `201683` **MUERTO**: usado bajo reserva, no forfeit. |
| limitaciones | (1) 2 precondiciones `NOT_EVALUABLE` por root, no por fallo; (2) el veredicto sobre P8 es *lo que haría* el harness, obtenido estáticamente, porque nunca puede alcanzarlo; (3) `2` `NOT_EVALUABLE` no es evidencia de ausencia |