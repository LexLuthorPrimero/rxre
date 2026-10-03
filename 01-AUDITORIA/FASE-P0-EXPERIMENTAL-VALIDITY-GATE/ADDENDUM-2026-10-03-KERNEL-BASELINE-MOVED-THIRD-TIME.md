# ADDENDUM 2026-10-03 — La línea base se movió por tercera vez, y el registro experimental no la acompaña

**Addendum a**: `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` (el original **no** se modifica: son 366 líneas intactas y lo seguirá siendo).

**Quién**: sesión `opencode`, ámbito `kernel-coverage`.
**Modo**: READ-ONLY sobre toda la evidencia. Este fichero es lo único creado.
**Por qué aquí y no en otro sitio**: este gate ya es el lugar canónico de la
validez del registro experimental, y su tabla §6 (línea 65 del original) ya
registra el desajuste de kernel. Una segunda nota sobre el mismo asunto en otro
fichero sería la duplicación que el índice no admite.
**Por qué fichero aparte y no dentro**: el gate es un informe fechado. Añadirle
secciones lo reescribiría, y los informes históricos no se reescriben. Estar en
la misma carpeta hace que no se puedan separar por accidente.

---

## A1. Qué dispara esto

Una auditoría del universo externo al proyecto —árboles hermanos en
`~/Escritorio`— encontró un snapshot de sistema de 2026-09-18 que declara su
propio entorno:

```
Linux lex-luthor 7.2.4-201.nobara.fc44.x86_64
```

Fuente: lectura directa de
`~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/system/hardware-and-vulkan-snapshot.txt`.

Ese árbol **no** es una copia de este proyecto. Es el proyecto hermano «RX 550
Modo Torneo» (runner, power-cap sweep, `kalm-gpu`), con su propio `manifest/`,
su propio `SHA256SUMS-critical` y sus propias instrucciones para IA. Se
clasifica `SIBLING_PROJECT__SEPARATE_SCOPE`. No se copia nada de él a esta raíz;
se cita, con su ruta.

---

## A2. La línea temporal del kernel, con la fuente de cada afirmación

| Cuándo | Kernel | Qué lo afirma |
|---|---|---|
| 2026-09-09 | `7.2.4-201.nobara.fc44` | banner `uname` del snapshot hermano, fechado 2026-09-18 |
| 2026-09-19 | `7.2.4-201.nobara.fc44` | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/`, `fase-b-cap-probe-20260919-122038/` |
| 2026-09-24 | `7.2.6-201.nobara.fc44` | §6 del gate original, campo «Kernel», método `uname -a` |
| 2026-09-25 | `7.2.4-201.nobara.fc44` | `FASE-D-COUNTERS-AUDIT.md:4`, campo «Entorno» |
| 2026-10-03 | `7.1.3-200.nobara.fc44` | `uname -r`, medido hoy |

**Lo que este addendum añade.** El gate del día 24 ya decía que la línea base no
era el kernel histórico y lo marcaba como *«No sabemos qué cambios exactos hay»*.
Eso sigue vigente. Lo que faltaba es que el movimiento **no se ha parado ahí**:
hoy el kernel es `7.1.3-200`, que es **anterior** a los dos anteriores. La
secuencia es `7.2.4 → 7.2.6 → 7.1.3`, y el último tramo es un **descenso de
versión**, no un ascenso.

Eso no está anotado en ningún documento del índice. La única mención de
`7.1.3-200` en texto de informe es la **versión del paquete `perf`**
(linux-tools) en `FASE-D-COUNTERS-AUDIT.md:43`, que es un hecho distinto: los
linux-tools pueden estar instalados junto a un kernel distinto del suyo, y por
eso su presencia no registra ninguna transición.

**Estado**: `OBSERVADO`, y la ausencia de anotación es `PROVEN_ABSENT` por
enumeración sobre `docs/`, `*.md` de raíz y `01-AUDITORIA/`.

---

## A3. Cuánta evidencia existe en cada kernel

Cuenta por rutas cuyo contenido contiene la cadena de versión.

| Dónde | Kernel | Ficheros | Naturaleza |
|---|---|---|---|
| `03-EXPERIMENTOS/` | `7.2.4-201` | 193 | registro en ejecución, repartido en ~126 carpetas |
| `03-EXPERIMENTOS/` | `7.2.6-201` | 0 | el gate declara 7.2.6 pero no lo escribe en los datos |
| `03-EXPERIMENTOS/` | `7.1.3-200` | 39 | **artefactos de compilación** (`.o`, `.ko`, `.cmd`) |
| `03-EXPERIMENTOS/` | `7.1.3-200` | 1 | texto de informe, y es la versión de `perf` |

Los 39 artefactos de compilación están en `03-EXPERIMENTOS/sandbox/` y
`03-EXPERIMENTOS/ep08-doorbell-suppression/`. Llevan la versión porque el
`Makefile` de kbuild la graba en los `.cmd` y en las cadenas del `.ko`. **No son
evidencia de ejecución**: nadie ejecutó un `.o`.

---

## A4. Lo que este recuento NO establece

Cuenta cadenas de versión dentro de ficheros. Eso establece **qué ficheros
declaran** qué kernel. No establece que los demás no se ejecutaran en el kernel
actual: un fichero de runtime puede no registrar el kernel en absoluto.

La formulación correcta, y es la diferencia entre esto y exagerarlo:

- **PROVEN por enumeración**: 193 ficheros declaran `7.2.4-201`.
- **PROVEN por enumeración**: **ningún** fichero de `03-EXPERIMENTOS/` declara
  `7.1.3-200` en texto de runtime.
- **NOT_DETERMINED**: si algún experimento llegó a ejecutarse sobre `7.1.3-200`.
  Un recuento de cadenas no puede responder eso. Responderlo exige el registro de
  cada ejecución, que no existe como tal.

Lo que sí se puede afirmar sin exagerar: **todo el registro experimental
ejecutable que declara su kernel es de un kernel que ya no está en la máquina.**

---

## A5. Consecuencia para el corpus

`RESEARCH/kernelbuild/` contiene **un solo** árbol: `linux-7.1.3`. Medido.

- Para trabajo **hacia adelante** está bien: el corpus coincide con el kernel en
  ejecución, que es contra el que compila `check-drivers` y se construye
  `rx550_drv.ko` (`modinfo` en el propio gate original).
- Para **re-derivar** cualquier conclusión histórica **no sirve**: no hay corpus
  de `7.2.4` ni de `7.2.6` en este árbol. Si una medición de `fase-a` o `fase-b`
  necesita re-derivarse contra el kernel que la produjo, hoy no se puede.

Esto es una **limitación de capacidad**, no una conclusión sobre las mediciones.
Las mediciones no se refutan: se acotan.

---

## A6. Mesa también se movió

| Cuándo | Mesa | Fuente |
|---|---|---|
| 2026-09-18 | `26.2.2-1.fc44` | `manifest/system-packages-rpm.txt` del snapshot hermano |
| 2026-09-24 | `26.2.2` system | `FASE-D-COUNTERS-AUDIT.md:4` |
| 2026-10-03 | `26.2.3-1.fc44` | `rpm -q mesa-dri-drivers`, medido hoy |

La pila de userspace que aporta el ICD Vulkan (`radeon_icd.x86_64.json`) ha
cambiado de versión entre las mediciones históricas y el estado actual. Toda
comparación que atraviese esa frontera tiene un confounder de versión de Mesa que
el gate ya exigía registrar y que hasta ahora no estaba registrado en ningún
sitio.

---

## A7. Lo que NO se hace aquí

- **No se corrige** ninguna conclusión previa. Un kernel distinto no refuta una
  medición: la acota.
- **No se reetiqueta** `fase-a` ni `fase-b` como inválidas. Son observaciones en
  un kernel que ya no está, y su valor sigue siendo lo que se midió entonces.
- **No se mueve** el árbol hermano. Clasificado
  `SIBLING_PROJECT__SEPARATE_SCOPE`, tiene su propia raíz, su propio manifest y
  su propio ciclo. No es un archivo de este proyecto, así que no viola la regla
  de un solo árbol activo: es otro proyecto, con su propia regla.
- **No se toca** el original de este gate.

---

## A8. La acción siguiente, y por qué esta

Volver a medir en el kernel actual cualquier cifra que se vaya a reutilizar como
línea base. Es barato, es discriminante, y **deshace** el confounder en lugar de
documentarlo por cuarta vez.

La alternativa —seguir anotando qué kernel era cada cosa— tiene valor de
trazabilidad y ninguno de capacidad: deja el mismo número utilizable en el mismo
nuevo contexto.

---

## A9. Procedencia de este addendum

| Campo | Valor |
|---|---|
| Producer | sesión `opencode` |
| Ámbito | `kernel-coverage` |
| Fecha | 2026-10-03 |
| Modo | READ-ONLY sobre evidencia; un fichero creado |
| Herramientas | `scopeguard.py --locks`, `grep -rl` por cadena, `rpm -q`, `uname -r`, `ls`, `find` |
| Fichero modificado | ninguno |
| Ficheros creados | este |
| States usados | `PROVEN` (enumeración), `OBSERVADO` (línea temporal), `NOT_DETERMINED` (A4), `PROVEN_ABSENT` (A2) |
| Limitación principal | A4: la enumeración de cadenas no puede afirmar que algo no se ejecutó |
---

# CORRECCION 2026-10-03 — A3 tenía un reparto equivocado

**Autocorrección, detectada recontando, no por revisión.**

## Qué estaba mal

En A3, al pie de la tabla, escribí:

> Los 39 artefactos de compilación están en `03-EXPERIMENTOS/sandbox/` y
> `03-EXPERIMENTOS/ep08-doorbell-suppression/`.

Iba en la fila de `7.2.4-201`, y era **falso**: los 193 ficheros que declaran
`7.2.4-201` son **los 193** texto de runtime. Ninguno es un `.o`, `.ko` ni `.cmd`.
Los 39 artefactos de compilación pertenecen a la fila de `7.1.3-200`, que es
donde estaban, y el error fue mío al escribir el pie bajo la fila equivocada.

Comprobación que lo detecta, y que es la que hay que repetir:

```
ficheros que contienen 7.2.4-201                        193
de ellos, con extension .o/.ko/.cmd                      0
```

## Y el reparto de los 45 con `7.1.3-200` era más sencillo de lo puesto

Desglose real por extensión:

| Extensión | Ficheros | Qué son |
|---|---|---|
| `.cmd` | 21 | artefactos de kbuild |
| `.o` | 15 | artefactos de compilación |
| `.ko` | 3 | módulo construido |
| `.c` | 4 | **fuente del proyecto**, no artefacto |
| `.sh` | 1 | script de precondición |
| `.md` | 1 | informe, y es la versión de `perf` |

Los cuatro `.c` son `control/pci_resource.c`, `control/rx550_target.c` y sus dos
copias en `sandbox/`. **No los había visto**: los conté como artefactos porque
estaban en el mismo recuento. Un `.c` que menciona la versión del kernel es
fuente del proyecto que afirma una condición sobre el kernel, y eso pertenece a
otro sitio del índice, no a este addendum.

El `.sh` es `ep08-doorbell-suppression/preruntime.sh`, que por el nombre es una
precondición de ejecución y probablemente comprueba el kernel antes de correr.
Eso explicaría por qué el único directorio con rastro de `7.1.3` fuera también
el único con una precondición de kernel: **alguien ya se preocupó de esto** y es un
sitio donde esa preocupación está escrita. No se ha leído; queda como
`NOT_AUDITED`.

## Lo que no cambia

Ni A2, ni A4, ni A5, ni A6. La conclusión central —todo el registro experimental
ejecutable que declara su kernel es de un kernel que ya no está— se sostiene
igual, porque se apoyaba en los 193, que eran correctos desde el principio.

## La lección, que es lo único que esto añade

Escribí el pie de una tabla antes de tener el desglose por extensión, y lo
escribí junto al número que ya tenía en la cabeza. Un número total correcto
`(193) convive happily con un reparto de sus partes que es inventado, y el
conjunto no se nota por los totales: se nota por el reparto.

---

# CORRECCION 2 — 94 carpetas, no 126; y la precondición de kernel ya existía

## C2.1 El número de carpetas estaba mal

A3 dice «~126 carpetas». Medido con la definición natural —directorios distintos
que contienen al menos un fichero con la cadena— son **94**.

De dónde salió 126: una variante del comando que quitaba un único segmento final
del path en vez de agrupar por directorio de experimento. Dos definiciones de
«carpeta» dan dos cifras, y escribí la que tenía en la cabeza sin declararla.
`193` y `94` son los valores con definición explícita; «~126» no lo era.

## C2.2 La precondición de kernel ya existía, y yo la marquer como NO_AUDITED

Había escrito que el `.sh` de `ep08` era «probablemente una precondición de
kernel» y lo dejé en `NOT_AUDITED`. Leído:

```
03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh:28
    KVER_EXPECTED="7.1.3-200.nobara.fc44.x86_64"
```

**Es exactamente eso.** El proyecto tiene ya un mecanismo que declara el kernel
esperado y, por nombre de variable, obliga a comprobarlo antes de ejecutar. Y los
cuatro `.c` que portan la versión son fuentes que **apuntan al `/usr/src/kernels/`
de ese mismo kernel**, o sea que el código fuente también está fijado a 7.1.3.

Consecuencia para A2: el proyecto **no** está ignorando el kernel. Tiene la
precondición escrita y ejecutándose. Lo que no tiene es el registro de qué se
ejecutó antes de que el preflight existiera, y por eso A4 sigue siendo
`NOT_DETERMINED` y no por descuido.

## C2.3 A8 cambia, y por eso se corrige en vez de añadirse

A8 proponía «volver a medir en el kernel actual». Sigue siendo la acción correcta,
pero **ya existe el mecanismo que la hace mecánica**: `KVER_EXPECTED` en
`preruntime.sh` es exactamente la puerta que un banco de pruebas necesita.

La acción siguiente no es, por tanto, designing un preflight nuevo. Es **usar el
que ya hay**: extender `preruntime.sh` como precondición estándar para cualquier
medición que se vaya a reutilizar como línea base, para que el kernel se registre
por construcción y no por memoria de quien lee el fichero después.

Eso es una mejora de reutilización de una automatización existente, no un
invento. Y tiene una propiedad que importa: hace imposible el error que este
addendum documenta.

## C2.4 Lo que sigue sin cambiar

A1, A4 y A5. Y el veredicto central, que nunca dependió del número de carpetas.
