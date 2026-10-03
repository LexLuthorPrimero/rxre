# 973 · El OFFSET GUARD del experimento EP08 lee el TAMAÑO del campo, no su OFFSET — y hay un `PASS` que pasa por casualidad

```text
CLASSIFICATION=ERROR+MEASUREMENT+NEGATIVE_RESULT · TRACK=TOOLING+EXPERIMENTOS
CORPUS=ninguno (fuente primaria: el propio harness auditado)
HARDWARE_SCOPE=amdgpu 1002:699f rev c7, sub 1002:0b04, modalias pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
WRITE_LOCAL=PROPIOS
MODIFICATIONS_COUNT=0
WRITE_EXECUTION=3 ficheros nuevos + este hallazgo
AUTHORIZATION=NONE (no se pide sudo, no se fabrica el token de EP08)
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
RUNTIME=READ_ONLY_SYSFS+BTF+KALLSYMS     (sin MMIO, sin debugfs, sin escritura)
GPU INTACTA · nhwa NO CARGADO · kprobe_events NO TOCADO
CERROJO=.write-lock/ep08-validate (mkdir atómico)
TARGET=03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh
     sha256 c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633
     25513 B · mtime 2026-09-29T08:21:49-03:00 · SIN MODIFICAR
ARTEFACTO=08-ARQUITECTURA/artifacts/EP08-VALIDATION/
     ep08-validation.md · preruntime_audit.sh · capture_preconditions.sh
     preconditions-live.tsv · preruntime-audit.tsv
TOOLS=preruntime_audit.sh · capture_preconditions.sh · pahole v1.30 · bash 5.x
CONTINUES=970 (mismo tipo de pregunta: un instrumento que no puede fallar cuando debe)
```

Fecha de la medicion: 2026-10-03. Kernel `7.1.3-200.nobara.fc44.x86_64`.
uid 1000, **sin privilegio**. Placa **no escrita**.

## Qué resuelve

`preruntime.sh` lleva 6 días marcado `# NO EJECUTADO. Preparado y revisado;
pendiente de autorización humana.` La pregunta de este nodo no es qué haría,
sino si **puede**:

1. ¿Alcanza siquiera su PHASE 1? **NO.** Aborta en la línea 153.
2. ¿Mide bien lo que mide cuando llegue? **NO.** Su OFFSET GUARD lee el tamaño
   del campo en vez del offset.

Y el subproducto que sobrevive a todo lo demás:

> **El diseño experimental sigue siendo válido para esta máquina.**
> `no_hw_access` está en `381969 = 0x5D411`, el valor que el harness fijó el
> 2026-09-29. El struct no se movió. Lo que está mal es el instrumento.

## Veredicto de instrumento

```
INSTRUMENTO_INVALIDO          (no DEGRADED: no llega a producir ningún dato)
  ├ ALCANZABILIDAD   NO       8 variables sin asignar, set -u las hace fatales
  ├ OFFSET GUARD     NO       lee $(NF-1) = TAMAÑO; el offset es $(NF-2)
  └ PRECONDICIONES    9 PASS / 4 FAIL / 8 INSTRUMENTO_ROTO / 2 NOT_EVALUABLE
                     / 1 PASS_POR_CASUALIDAD   (24 filas, 6 columnas)
```

## 1 · Los 8 `set -u` — el primer abort, línea 153

| Usada | Línea | Declarada como |
|---|---|---|
| `TARGET_PCI_SUB_VEN` | 153, 160 | **nunca** |
| `TARGET_PCI_SUB_DEV` | 160 | **nunca** |
| `TARGET_PCI_REVISION` | 160 | **nunca** |
| `TARGET_MODALIAS` | 156 | **nunca** |
| `NHWA_OFF_ASIC_TYPE` | 214 | `NHWA_ASIC_TYPE_OFFSET` (línea 42, otro nombre) |
| `NHWA_OFF_PCI_SUB_VEN` | 217 | **nunca** |
| `NHWA_OFF_PCI_SUB_DEV` | 218 | **nunca** |
| `NHWA_OFF_PCI_REVISION` | 219 | **nunca** |

Probado con la **línea literal del script**, constantes declaradas ya cargadas:

```
$ bash -c 'set -uo pipefail; … [ "$(cat "$d/subsystem_vendor")" = "$TARGET_PCI_SUB_VEN" ] && echo IGUAL'
bash: línea 1: TARGET_PCI_SUB_VEN: variable sin asignar
exit=127
```

**Falla cerrado**: aborta en el preflight, antes de PHASE 2 y muy antes del
`insmod` de PHASE 6. Ningún estado de hardware puede quedar cambiado por esto.

## 2 · El OFFSET GUARD lee el tamaño — `PROVEN` con pahole v1.30

```
^Ibool                       no_hw_access;         /* 381969     1 */
NF=6  NF-5=bool  NF-4=no_hw_access;  NF-3=/*  NF-2=381969  NF-1=1  NF-0=*/
```

`$(NF-1)` es el **tamaño**. El offset es `$(NF-2)`. Las 8 extracciones de
offset de P8 usan `$(NF-1)`.

| Precondición | offset real | tamaño | lee | esperado | qué pasaría |
|---|---|---|---|---|---|
| `no_hw_access` | **381969** ✓ | 1 | `1` | `381969` | FAIL con **diagnóstico falso** |
| `asic_type` | 1640 | 4 | `4` | sin asignar | abort |
| `pdev` | 8 | 8 | `8` | `8` | **PASS por casualidad** |
| `pci.vendor` | 60 | 2 | `2` | `60` | FAIL con diagnóstico falso |
| `pci.device` | 62 | 2 | `2` | `62` | FAIL con diagnóstico falso |
| `pci.subsystem_vendor` | 64 | 2 | `2` | sin asignar | abort |
| `pci.subsystem_device` | 66 | 2 | `2` | sin asignar | abort |
| `pci.revision` | 72 | 1 | `1` | sin asignar | abort |

### 2.1 El `PASS` por casualidad es la fila peligrosa

`pdev` es un puntero: tamaño 8, offset 8. `$(NF-1)` devuelve 8, la comparación
pasa, y **nada en P8 lo detecta**. Un guard que pasa por coincidencia de
magnitudes no ha medido nada: ha coincidido. Es el peor caso de un guard —
**verde por accidente**, en la misma función que contiene la única comprobación
que el script llama *"el guard real"*.

### 2.2 Por qué el guard es el problema y no una higiene

El OFFSET GUARD existe para decir *"el struct se movió"* y no *"el ring no
avanza"*. Leyendo el campo equivocado **no puede distinguir eso de *"mi parser
está mal"*.** Convierte el fallo en innegable y el diagnóstico en falso: el día
que `struct amdgpu_device` se mueva de verdad, este guard dirá `1` otra vez, que
es lo que ya dice hoy, y no habrá forma de diferenciar los dos casos ni con el
código fuente ni con la ejecución.

## 3 · Precondiciones vivas: 24 filas medidas

`preconditions-live.tsv`, producido por `capture_preconditions.sh`, que **usa los
awk del harness**, no equivalentes. Validado por forma (6 columnas, vocabulario
cerrado) antes de escribirse.

| veredicto | n |
|---|---|
| `PASS` | 9 |
| `INSTRUMENTO_ROTO` | 8 |
| `FAIL` | 4 |
| `NOT_EVALUABLE` (root) | 2 |
| `PASS_POR_CASUALIDAD` | 1 |

Los dos `NOT_EVALUABLE` son `amdgpu_regs` y `amdgpu_test_ib`: ambos bajo
`/sys/kernel/debug/dri/`, root-only en esta máquina (`Permiso denegado`,
medido). **No es PASS ni FAIL**, y no se cuenta como ninguno.

### 3.1 Una precondición que el harness no declara: root

```
$ grep -nE 'EUID|\bid -u\b|whoami|sudo' preruntime.sh
(sin coincidencias)
```

Y sin embargo P3–P7 leen debugfs, PHASE 6 hace `insmod`, PHASE 7 y 8 hacen
`rmmod`. **Exige root en cinco sitios y no lo comprueba en ninguno.** Sin
privilegios, el fallo es `Permiso denegado` en P4, que no lleva a nadie a la causa.

## 4 · Lo que sí está intacto, y no debe perderse por estar al lado de un defecto

- La identidad de objetivo la hace de **5 campos + modalias**, no por el ID solo,
  y el propio script razona por qué (`pci.ids` lista 5 tableros bajo `0x699f`).
- `no_hw_access` **no se lee directamente**: se valida **conductualmente**, y
  declara por escrito `DIRECT_NO_HW_ACCESS_READ = NOT_AVAILABLE`.
- La puerta A exige la **cadena literal** `ib ring tests passed.` y prohíbe usar el
  exit code como sustituto.
- PHASE 10 se autodeclara `RESTORATION_VALIDATION` y **no** un tercer brazo.

## 5 · La puerta de autorización funciona — probada, sin fabricar el token

```
$ bash ./preruntime.sh
== PHASE 0 — autorización
STOP: falta --authorization=<TOKEN>. Esta ronda NO ejecuta nada.
exit=1
```

Tras la ejecución: `logs/` no existe, `nhwa` no cargado. **No se fabricó
`RUN550-EP08`**: obtenerlo sin autorización humana habría sido autoautorización.
Por eso §1 se midió estáticamente y con la línea literal, que da el mismo
veredicto sin tocar la máquina.

## 6 · Instrumentos, validados en las dos direcciones

`preruntime_audit.sh` separa "mecánicamente muerto" de "medidor roto":

| control | resultado |
|---|---|
| negativo (harness sano) | `PASS`, 0 — **cero falsos positivos** |
| positivo 1 (declarar una) | 8 → 7 |
| positivo 2 (añadir `$VAR_INVENTADA`) | 7 → 8 |
| suelo (el harness real) | 8, idéntico al `comm` manual independiente |

`capture_preconditions.sh` valida la forma de su propio artefacto: TSV de 3
campos inyectado → `FORMA_ROTA` + `exit 1`; intacto → `exit 0`.

### 6.1 Dos defectos míos, del mismo tipo que el encontrado

1. **Murió en silencio.** `set -e` + `pipefail` + un `grep` sin coincidencias
   (buscaba `${X:=`, que un harness sano no tiene) abortaba el instrumento con
   salida vacía. Se vio **solo porque se comprobó el exit code**. Es la clase
   que el **finding 109** ya había detectado en otro tool del proyecto.
2. **Falso positivo por precedencia de operadores.** `grep X || true | sed Y` se
   parsea como `grep X || (true | sed Y)`: `|` liga más fuerte que `||`. El `sed`
   no corría nunca, los `for k in` llegaban sin transformar, y las **variables de
   bucle de un harness sano se reportaban como no asignadas**. Lo delató el
   control negativo dando 3 falsos positivos (`a`, `d`, `k`).

Ninguno se habría visto leyendo el código con atención: se vieron por **ejecutar
el control negativo**, que es lo que los separa de una hipótesis.

## 7 · Qué queda abierto, y qué NO se hace aquí

```
EP08-VALIDATION        RESOLVED · INSTRUMENTO_INVALIDO
DISEÑO EP08            VIGENTE · CORROBORADO   (no_hw_access = 0x5D411, sin movimiento)
EP08-DOORBELL          DEFERRED · BLOQUEADO, y NO por el hardware ni por la placa
  Desbloquea: (1) declarar las 8 constantes, (2) $(NF-1) -> $(NF-2),
              (3) declarar la precondición de root,
              (4) autorización humana para escribir.
              (1)-(3) son de quien escribió el harness. (4) es del humano.
preruntime.sh          INTACTO, sha c0349f7f…26633
GPU / MMIO / nhwa      INTACTOS
```

- **No se corrige `preruntime.sh`.** El defecto está medido y probado; repararlo es
  otra acción, de otro turno. Aquí preservar es lo correcto: el valor del fichero
  es ser la prueba.
- **No se ejecuta el experimento.** Las escrituras sobre hardware las exige una
  autorización humana, y no se pide aquí.
- **No se declara inválida ninguna medición previa.** Nada se ha medido con este
  harness: no hay resultados que acotar.
- **No afirma nada del ASIC.** `no_hw_access` en 381969 es un hecho del **struct
  del módulo que corre**, leído por BTF.
- **No cierra** `CONTRAD-Q5-GFX8-ES-GCN3` ni ninguna otra: son de otro nodo.
- **No toca** `CURRENT-STATE.md` ni los regenerados por `tools/artifacts.py`: son
  globales y hay otro nodo escribiéndolos.

## 8 · Procedencia

```
HEAD                3d89682195b03f0244a5a2945f2a9567dff704eb
preruntime.sh       c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633  INTACTO
nhwa.c              b06d8952214a0063f95c9a38fa347aa3efe59e730ae003d4067310620c0def3f  INTACTO
nhwa.ko             c537efbeeded4b8617a352ab3b5a128dafcb3f3c196caea535c28d92c75ff012  NO CARGADO
pahole              v1.30           (fija el layout de columnas: es la version load-bearing)
kernel vivo         7.1.3-200.nobara.fc44.x86_64
btf/amdgpu          3882770 B, legible sin sudo        btf/vmlinux  6357197 B
kallsyms            amdgpu_mm_wdoorbell: 2 ocurrencias
reserva de numero   973, atomica, tools/nextnum.py --reservar 973
concurrencia        AGENT-03 en Q5-MEM-TABLES/, AGENT-06 bajo drv-q8/: ambitos disjuntos.
                    El lock findnum tenia owner 201683 MUERTO: usado bajo reserva, no forfeit.
LIMITACION 1        2 precondiciones NOT_EVALUABLE por root. No es evidencia de ausencia.
LIMITACION 2        El veredicto sobre P8 es LO QUE HARIA el harness, obtenido
                    estaticamente, porque nunca puede alcanzarlo en ejecucion.
```