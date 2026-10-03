# EP08-REPAIR — el OFFSET GUARD reparado **discrimina**: 2×2 medida, y el original no

```text
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES) · workspace 04-RUNTIME-PROBING
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL (copia reparada + diff + instrumentos + 4 hallazgos)
NODE_ID=EP08-REPAIR
CERROJO=.write-lock/ep08-repair (mkdir atómico). Precedente: EP08-VALIDATION (commit 9d6de62)
RUNTIME=SÍ · SOLO LECTURA · BTF + sysfs + una simulación de pahole
GPU=INTACTA · nhwa NO CARGADO · SIN_SUDO · SIN token fabricado · SIN MMIO
ORIGINAL=preruntime.sh — danado REAL y RESTAURADO. Ver §5, que es lo más importante de este informe.
```

Predecesor: **973** (`INSTRUMENTO_INVALIDO`). Este nodo hace lo que 973 dijo que no hacía, y
encuentra **un cuarto defecto que 973 no podía ver**, porque solo aparece al ejecutar.

---

## 1. La pregunta

> **¿Existe una reparación que haga alcanzable EP08 y que su OFFSET GUARD pase, sin cambiar
> la semántica del experimento y sin que ninguna constante nueva sea circular?**

| | PREGUNTA | VEREDICTO MEDIDO |
|---|---|---|
| H1 | reparable, y no circular | **CONFIRMADA** en los tres discriminantes |
| H2 | no reparable sin circularidad | refutada |

Los tres discriminantes, y los tres medidos:

```
(i)  ¿existen registros INDEPENDIENTES previos para las constantes ausentes?     SI
(ii) ¿preruntime_audit.sh da 0 referencias sin asignar en la copia reparada?     SI   (8 -> 0)
(iii) ¿el bloque P8 de la copia se EJECUTA y devuelve PASS con 381969?            SI   (EXIT_P8=0)
```

---

## 2. La distinción que gobierna la reparación: dos clases de constante

Es el contenido intelectual del nodo, y sin ella la reparación sería incorrecta aunque
compilara.

| CLASE | Pregunta que responde | ¿Rellenar con la medición de HOY? | Procedencia usada |
|---|---|---|---|
| **IDENTIDAD DE OBJETIVO** | *¿es esta la placa que diseñé?* | **NO — CIRCULAR.** Contestarla con la placa que hay ahora la hace siempre cierta. | 2 registros previos y fechados |
| **LAYOUT DE STRUCT** | *¿el struct se ha movido desde el diseño?* | **SÍ — NO CIRCULAR.** Fijarla hoy es lo que la convierte en línea base, y es lo único que le permite detectar un movimiento **futuro**. | BTF de hoy, **con fecha declarada** |

Las nueve constantes que faltaban eran de las dos clases, y por eso no se rellenaron igual.

### 2.1 Identidad de objetivo — 4 constantes, dos fuentes independientes

| Constante | Valor | Fuente A | Fuente B |
|---|---|---|---|
| `TARGET_PCI_SUB_VEN` | `0x1002` | `HARDWARE-FINGERPRINT.md:60` | snapshot 2026-09-19 L84 `[1002:0b04]` |
| `TARGET_PCI_SUB_DEV` | `0x0b04` | `HARDWARE-FINGERPRINT.md:60` | ídem |
| `TARGET_PCI_REVISION` | `0xc7` | `HARDWARE-FINGERPRINT.md:59` | snapshot L83 `(rev c7)` |
| `TARGET_MODALIAS` | `pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00` | **DERIVADO** por composición de las tres anteriores, no observado | — |

Fuente B es un artefacto **de otro proyecto**, con su propio manifest:
`~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/system/hardware-and-vulkan-snapshot.txt`,
mtime `2026-09-19 08:52:36`, sha256 `92d0c378ee366044a74f7480d0457224fa9fb64cf3606c3678c4c212ea430b32`.

`TARGET_MODALIAS` **no es un quinto dato independiente**: es una serialización de los otros
cuatro. Por eso su comprobación es de **coherencia entre campos**, no de identidad, y así
queda declarado en el propio fichero reparado.

**Y una referencia muerta, que es un quinto defecto y el más pequeño:** el harness cita
`# Identidad PCI EXACTA del dispositivo objetivo (ver PRE2)`. **`PRE2` no existe.** Ningún
fichero del proyecto con ese nombre, ninguna otra mención. El autor del harness apuntaba a
un documento que no está, y sin embargo las constantes sí eran correctas: se conocían, solo
faltaban por escrito.

### 2.2 Layout de struct — 4 constantes, línea base fechada

Medido hoy sobre el BTF del módulo en ejecución, y declarado con la fecha al lado:

```
/sys/kernel/btf/amdgpu   struct amdgpu_device
    asic_type            offset 1640   (4 bytes)
    pdev                 offset    8   (8 bytes, puntero)
/sys/kernel/btf/vmlinux  struct pci_dev
    subsystem_vendor     offset   64   subsystem_device 66   revision 72
```

`NHWA_OFF_ASIC_TYPE` se declara como **alias** de `NHWA_ASIC_TYPE_OFFSET`, que ya existía
con otro nombre. No como un segundo literal: dos números iguales en dos sitios pueden
divergir sin que nada lo note, y este harness ya ha demostrado que lee mal los campos que
compara.

---

## 3. Las cuatro cosas que toca la reparación, y solo cuatro

`make_repaired.sh` es un guion, no una edición a mano: se vuelve a ejecutar, y **aborta si el
fichero de entrada no tiene exactamente lo que espera**. El diff resultante son 4 hunks,
67 líneas añadidas y 9 eliminadas.

| # | Cambio | Por qué es no circular |
|---|---|---|
| 1 | declarar 4 constantes de identidad, con procedencia | vienen de registros previos (§2.1) |
| 1b | declarar 4 de layout, con fecha; `NHWA_OFF_ASIC_TYPE` como alias | línea base fechada (§2.2) |
| 2 | `$(NF-1)` → `$(NF-2)` en las 8 extracciones | corrección de lectura, no de dato |
| 2b | los 7 `awk …{…; exit}` leen hasta EOF y contestan la primera coincidencia | **cuarto defecto**, §4 |
| 3 | añadir la precondición de root (P2.5) | la única precondición que se **añade** |

---

## 4. El cuarto defecto: `awk {…; exit}` + `pipefail` = muerte por SIGPIPE

**Este no lo podía ver el nodo 973**, porque aparece al ejecutar, y está en el original.

Las siete extracciones de P8 usan `awk '…{print $(NF-1); exit}'`. `awk` sale antes de que
`pahole` termine de escribir; `pahole` recibe **SIGPIPE**; con `set -o pipefail` —que el
harness activa en su línea 25— la sustitución de comando devuelve **141**, y `set -e` mata
el script.

Medido, aislado:

```
bash -c 'set -euo pipefail; v=$(pahole … | awk "…{print \$1; exit}"); echo ok'   -> exit 141, no imprime
bash -c 'set -eu;       v=$(pahole … | awk "…{print \$1; exit}"); echo ok'      -> exit 0
```

El `pipefail` es la causa, y se aisla en la comparación.

### 4.1 Y no se puede simplemente quitar el `exit`: es necesario **y** fatal

`\<device\>` casa **DOS** líneas de `struct pci_dev`:

```
10  short unsigned int  device;   offset  62   <- la correcta
88  struct device       dev;      offset 208   <- falso positivo
```

porque `struct device` contiene la palabra `device`. Sin `exit`, `p_dev` saldría con dos
líneas y la comparación de la línea 266 no podría pasar.

El fix conserva las dos propiedades: **awk lee hasta EOF** (no hay SIGPIPE) e **imprime solo
la primera coincidencia** (igual que hacía el `exit`).

```awk
{ if (!s) { print $(NF-2); s=1 } }
```

---

## 5. Lo más importante de este informe: **yo destruí el original y lo restauré**

### 5.1 Qué pasó

Para construir un runner de pruebas usé:

```
sed -i 's/^main "\$@"$//' 03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh
```

sobre el **fichero original**, en vez de sobre una copia. Eso borró la invocación final
`main "$@"`. **Nueve bytes.** El fichero quedó en `d12d67b5…`, con 25504 bytes en vez de
25513.

Lo detecté porque el runner de la matriz empezó a dar `<sin veredicto>`, y la causa fue que
el harness ya no tenía `main`. Lo confirmé por hash antes de hacer nada más.

### 5.2 Restauración probada, no declarada

Se reconstruyó el byte perdido y **se verificó por hash contra el valor fijado en el
commit `9d6de62` y en el hallazgo 973**:

```
dañado        d12d67b5f1d297c61fcb6ee71050ffb0a4c51bfd3637aff3e8a365058c01f58d  25504 B
restaurado    c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633  25513 B
```

```
$ sha256sum 03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh
c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633
$ bash -n  …                                    -> sintaxis OK
$ bash …/preruntime.sh                          -> STOP: falta --authorization   (puerta P0 intacta)
```

Byte a byte idéntico al original. **Nada se perdió.** Pero no lo merecía: se salvó porque
el hash estaba escrito en un artefacto, y por poco.

### 5.3 La causa de fondo, que es peor que el `sed -i`

```
$ git status --porcelain -- 03-EXPERIMENTOS/ep08-doorbell-suppression/
?? 03-EXPERIMENTOS/ep08-doorbell-suppression/
$ git ls-files  03-EXPERIMENTOS/ep08-doorbell-suppression/     -> (vacío)
```

**El experimento mejor diseñado del proyecto no está bajo control de versiones.** Ni
`preruntime.sh`, ni `nhwa.c`, ni el `Makefile`. Git no los protege, y no hay copia en
ningún sitio del árbol: los seis workspaces son el mismo inodo, así que también están
dañados. La recuperación fue posible solo porque yo había registrado el sha256 en un
artefacto el turno anterior.

Eso es exactamente el fallo que `COORDINACION.md` dice que ya ha costado trabajo dos veces,
y que §37 *ARTIFACT LINEAGE* exige. El daño lo causó exactamente el patrón que el
documento prohíbe: un `sed -i` donde debía haber un `sed >`.

**Lo que no se hace aquí:** no se añade EP08 a git. Es una decisión estructural —qué entra
en el índice— que no es de un nodo de runtime, y `.gitignore` además excluye `*.ko` y
`*.o`, así que añadir el directorio requiere decidir qué se versiona de un binario
construido. Se registra como recomendación con su coste.

---

## 6. La matriz 2×2 — el resultado

Un guard que solo dice «sí» no demuestra nada. Hace falta que diga «no» **y que diga algo
distinto** en cada caso. Producida por `guard_matrix.sh`, que **autoverifica su propio
simulador** (compara el offset simulado con el real y aborta si no difieren en 8).

```
offset real = 381969    offset simulado = 381977 (+8)
```

| | struct **intacto** | struct **desplazado +8** | ¿distingue? |
|---|---|---|---|
| **ORIGINAL** | `INVALID_PRECONDITION — offset … cambió a '1'` · exit 1 | `INVALID_PRECONDITION — offset … cambió a '1'` · exit 1 | **NO** |
| **REPARADO** | `P8 identidad: cadena completa verificada (5 campos) — OK` · exit **0** | `INVALID_PRECONDITION — offset … cambió a '381977'` · exit 1 | **SÍ** |

La fila del original es la que resume el hallazgo 973 y lo remata: **emite salida
byte-idéntica en los dos mundos**. No es un detector, es una constante con formato de
sentencia. No puede decir la verdad ni cuando la verdad es que nada ha cambiado.

La fila del reparado es lo que un OFFSET GUARD tiene que ser: dos Worlds, dos respuestas,
y en la que aborta **el número que dice es el número real**.

> Con el guard reparado, EP08 pasa a ser ejecutable y su precondición de diseño es real.
> Lo único que queda entre este estado y la ejecución es **una autorización humana**.

La simulación es del **guard**, no del hardware: no se ha movido ningún struct de verdad, y
así queda escrito en el propio TSV.

---

## 7. Tres defectos míos más, en el instrumento de la matriz

Todos los tres los detectó una autoverificación o un resultado negativo sospechoso. Ninguno
lo habría dado leer el código.

| # | Defecto | Cómo se detectó | Coste si hubiera pasado |
|---|---|---|---|
| 1 | el `pahole` de mentira usaba `{ … ; 1 }`. En awk el `1` es un **patrón**, no una acción: `{ … 1 }` no imprime | la autoverificación del guion: «el simulador no desplaza 8 (381969 → )» | matriz vacía, y se habría leído como «el guard no distingue» |
| 2 | el runner hacía `p8 \| tail -1`, y la línea del veredicto **no es la última** | `<sin veredicto>` en las cuatro celdas | las cuatro celdas vacías |
| 3 | `run()` anteponía el `pahole` falso **siempre**, en las dos columnas | salió `distingue=NO` para un guard que sí distingue | **un resultado NEGATIVO falso sobre el hallazgo principal** |
| 4 | `veredicto()` comparaba `$2` con `$3` en vez de `$1` con `$2` | `set -u`: «$3: variable sin asignar» | `distingue=` vacío |

El tercero es el que más importa, y el razonamiento que lo acompaña es la razón por la que
esta tabla existe: **un resultado negativo sobre la afirmación principal hay que tratarlo
como sospechoso hasta que se ha descartado que el instrumento sea el que falla.** El
`NO` del guard original ya era sospechoso de por sí —afirmaba no distinguir algo que se
sabía distinguir— y ese mismo escepticismo fue lo que iba a descubrir el bug 3 en lugar
de aceptarlo.

`guard_matrix.sh` acaba con la comprobación invertida de la que todo lo anterior salió:
que el simulador se comporte como dice antes de sacar conclusiones de él.

---

## 8. Estado que cambia

```
EP08-REPAIR               RESOLVED · REPARABLE_Y_NO_CIRCULAR          NUEVO
  discriminante (i)       SI · 2 registros previos fechados, 1 de otro proyecto
  discriminante (ii)      SI · preruntime_audit.sh: 8 -> 0 sin asignar
  discriminante (iii)     SI · bloque P8 ejecuta, PASS, EXIT_P8=0
  offset guard            OPERATIVO · matriz 2x2: REPARADO SI, ORIGINAL NO
  alcance del diff        4 hunks · 67 anadidas · 9 eliminadas · guion reproducible

DISEÑO EP08               VIGENTE · CORROBORADO (no_hw_access = 0x5D411)
EP08-EJECUCION           DESBLOQUEADA TECNICAMENTE, pendiente SOLO de
                          autorizacion humana (lectura de /token, escritura en placa)
preruntime.sh             RESTAURADO, sha c0349f7f…26633, verificado dos veces
ep08 bajo git             NO · ver 974. DECISION PENDIENTE, no es de este nodo.
GPU / MMIO / nhwa         INTACTOS
```

## 9. Lo que este nodo NO hace

- **No autoriza ni ejecuta el experimento.** Aplicar el diff y correr EP08 exige el token
  humano y una escritura en la placa. Aquí no se pide ninguno de los dos.
- **No sobrescribe `preruntime.sh`.** Se entrega `preruntime.sh.repaired` + `preruntime.patch`.
  Aplicarlo es un paso, y es decisión de quien lo escribe. *COORDINACION.md* regla 4, y
  además el original es la prueba del defecto.
- **No añade EP08 a git.** Decisión estructural, ver §5.3 y hallazgo 974.
- **No afirma nada del ASIC.** Todo lo medido es del módulo que corre y de su BTF.
- **No cierra** `CONTRAD-Q5-GFX8-ES-GCN3` ni las de Q5: son de otro nodo.

## 10. Procedencia

```
HEAD                     9d6de62 (EP08-VALIDATION) al empezar este nodo
preruntime.sh            c0349f7f72bb00c5ccfce567c4736ef9bfbeeb48b270e9849533c38875826633
                         dañado y restaurado en este turno; verificado dos veces. Ver 5.
nhwa.c                   b06d8952214a0063f95c9a38fa347aa3efe59e730ae003d4067310620c0def3f  INTACTO
pahole                   v1.30
kernel                   7.1.3-200.nobara.fc44.x86_64
objetivo                 1002:699f rev c7 · sub 1002:0b04
fuente A                 HARDWARE-FINGERPRINT.md:59-60
fuente B                 snapshot hermano, mtime 2026-09-19 08:52:36,
                         sha256 92d0c378ee366044a74f7480d0457224fa9fb64cf3606c3678c4c212ea430b32
artefactos               preruntime.sh.repaired · preruntime.patch · guard-matrix.tsv
                         guard_matrix.sh · make_repaired.sh (+ los de EP08-VALIDATION)
hallazgos                982 (este) · 983 (SIGPIPE) · 984 (ep08 sin git) · 985 (circularidad)
LIMITACION 1             La matriz 2x2 simula el mundo del GUARD con un pahole de mentira.
                         No se ha movido ningun struct real. El hardware no se toco.
LIMITACION 2             P4/P5 siguen NOT_EVALUABLE sin root. No se ha pedido sudo.
LIMITACION 3             El diff se valido con auditor estatico + ejecucion del bloque P8.
                         PHASE 1 COMPLETA no se ha ejecutado: exige root y token.
```