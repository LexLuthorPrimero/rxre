# 264 · El documento rector cambió y las convenciones se quedaron sin declarar

```
CLASSIFICATION=CONTRADICTION+MEASUREMENT+POLICY · TRACK=VERIFICATION
CORPUS=NINGUNO (todo del proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`AGENTS.md` es el documento rector del proyecto. Puso de 1101 líneas a 3736: se
sustituyó por el MASTER PROMPT V6. Y el V6 **no declara** ninguna de las
convenciones que el proyecto construyó durante meses.

No es un problema de redacción. Es que **tres herramientas están validando un
formato que nada exige**, y una validación verde no distingue "el formato es
correcto" de "el texto cumple una forma".

## 1 · Lo medido

```
  AGENTS.md ahora: 3736 lineas, 117 secciones

  FORMATOS que las herramientas imponen:
    PENDIENTE=             routeaudit, implgate, lint      NO DECLARADO
    ALCANZABLE_SIN_ROOT=   routeaudit, lint                NO DECLARADO
    CITA=                  citeambig                        NO DECLARADO
    TERMINO=               citeambig                        NO DECLARADO
    ROL=                   citeambig                        NO DECLARADO

  CITAS por nombre de seccion, en los hallazgos:
    7 NO_RESUELVEN   §RESULTADO OBLIGATORIO, §AUTOMATIZACIÓN DE DOCUMENTACIÓN,
                     §DOCUMENTACIÓN EXTERNA, §F MEMORY SYSTEM,
                     §IMPLEMENTATION_GATE, §LA CITA QUE SE SOSTIENE,
                     §OBJETIVO FINAL
    10 marcadores §A/§B/§C, que eran de bisección semántica, sin documento
    26 citas por número de línea   INCOMPARABLES

  157 ficheros de hallazgo CITAN AGENTS.md
```

Y el peso de las herramientas afectadas:

```
  routeaudit.py   8 comprobaciones, 24 referencias a los formatos
  lint.py        30 vectores,       27
  citeambig.py   25 vectores,       47
```

## 2 · Lo que se puede comprobar exacto y lo que no

`tools/govcheck.py` separa las dos cosas, porque confundirlas sería el mismo error
que el proyecto viene pagando en otra forma:

| clase | ¿comprobable? | cómo |
|---|---|---|
| sección por nombre | **sí, exacto** | el nombre es un encabezado que existe o no |
| formato declarado | **sí, exacto** | la cadena está o no está en el documento |
| línea `AGENTS.md:118` | **no** | el número existe y ya no significa lo que significaba |

Una cita por línea **no se audita con este método**, y se declara
`INCOMPARABLE` en vez de inventar un criterio que la "resuelva". Para hacerlo
habría que comparar el contenido de esa línea con lo que el hallazgo afirma de
ella, que es una lectura, no una regla.

```
  un instrumento que declara lo que no sabe, mide mejor que uno que inventa
```

## 3 · La decisión, y de quién es

Se propuso al usuario **añadir** las convenciones al documento rector. La
respuesta fue: **"no tocar agents.md"**.

Así que el documento no se toca, y la declaración va en las herramientas, que sí
son de este proyecto. Las tres llevan ahora, en su cabecera, un bloque que dice:

```
  - qué formato imponen y que AGENTS.md ya no lo declara
  - que sus comprobaciones pueden pasar porque el formato es correcto Y tambien
    pasarian si el formato fuera cualquiera
  - que siguen sirviendo para normalizar y para detectar las 11 lineas
    PENDIENTE= que hay
  - lo que NO pueden hacer es justificar su propia existencia
  - la fecha y la respuesta textual del usuario
  - que govcheck.py queda como auditor permanente de ese estado
```

Es un estadoquo documentado, y es peor que las otras dos opciones: tres
herramientas validadas validan algo que nada exige. La ventaja es que ahora
**está escrito en las tres**, y no es un accidente silencioso.

## 4 · CORRECCION: el permission model NO cambió, y yo dije que sí

La primera versión de esta sección afirmaba que el modelo de permisos había
cambiado y que había una CONTRADICCIÓN sin registrar. **Es falso, y lo comprobé
leyendo los dos textos.**

Lo que dicen los hallazgos, que es lo que había dado por supuesto:

```
  `insmod` es NIVEL 4 y requiere autorización humana explícita
  NIVEL 4 — GPU reset, insmod/bind/unbind del driver del sistema
  `root` NO implica autorización NIVEL 4
```

Y lo que dice el §71, texto íntegro:

```
  No bloquear automáticamente: sudo / su / root
  Evaluar efecto real.
  Permitir cuando sean necesarios para: diagnosis, observation, measurement,
                                    tracing, hardware inspection
  Mayor cautela para: kernel deletion, partitioning, destructive firmware,
                      irreversible destructive actions
```

Y el §72 RUNTIME TAKEOVER pide, antes de tomar control exclusivo: hardware
identity, driver ownership, GPU state, process state, preconditions,
observability, rollback, recovery, abort condition, y una pregunta discriminante
concreta.

**Los tres coinciden:**

| |Model anterior| V6 |
|---|---|---|
| root para observar | permitido (NIVEL 2) | permitido (§71) |
| root no autoriza takeover | `root` NO implica NIVEL 4 | §71 no lo concede |
| takeover exige más | autorización humana explícita | §72: precondiciones y discriminante |
| lo irreversible | NIVEL 4 | §71: "mayor cautela" |

Lo que cambió es **el vocabulario**, no la sustancia: `NIVEL 2` → §71,
`NIVEL 4` → §72. Un hallazgo que dice "esto es NIVEL 4" sigue diciendo la verdad,
aunque el número no exista ya en el documento rector.

```
  un cambio de vocabulario no es un cambio de decision
```

Así que el defecto real es más pequeño de lo que seemed, y es el mismo que ya
estaba en §1: **las citas no resuelven**. 16 hallazgos citan NIVEL 4 y 24 citan
insmod; ninguno de esos números señala ya una sección. Lo que falta no es
re-decidir nada: es que la referencia dangling.

Y la trampa de esta sección era exactamente la que este proyecto lleva media
sesión evitando: **afirmar una contradicción desde una impresión en vez de leer
las dos frases**. La impresión venía de que §71 "dice lo contrario", y no lo dice:
§71 habla de *no bloquear el acceso*, y el nivel 4 nunca fue sobre el acceso,
sino sobre el takeover. Se leyeron las dos mitades de la misma regla como si
fueran dos reglas.

## 4 bis · Y la versión que citan 157 hallazgos NO está en git

Esto se comprobó después de escribir §1, y es el hecho que le da toda la
gravedad al asunto.

```
  version de AGENTS.md en el historial        lineas   "LA CITA QUE SOSTIENE"
  6fb9113  (la mayor)                          1060          NO
  daec702                                      984          NO
  1bb4115                                      333          NO
  4a437ac                                      302          NO
  6fe40b2                                      277          NO
  54b3ea8                                      256          NO
  .....................................................
  la version que rigio durante la sesion      1101          SI
  V6, la que hay ahora                          3736          NO
```

**Ninguna versión commiteada tuvo nunca `LA CITA QUE SE SOSTIENE`.** La de 1101
líneas, contra la que escribieron 157 hallazgos, estaba **solo en el árbol de
trabajo**: nunca se commiteó, y el pegado de V6 la sobrescribió.

Consecuencias, y son de dos clases:

```
  1  las convenciones CITA=/TERMINO=/ROL=  NO SON RECUPERABLES del repositorio.
     Su unico registro escrito ahora mismo son las cabeceras de las tres
     herramientas y los hallazgos que las usan. Eso es lo que se decidio
     conservar cuando la respuesta fue "no tocar agents.md", y sin those
     declaraciones no habria quedado NADA escrito de ellas.

  2  las citas por numero de linea ya NO SON INCOMPARABLES, porque git conserva
     6 versiones de referencia. Se pueden resolver contra la version vigente
     cuando se escribieron. Lo que no se puede es saber CUAL era: hay seis
     candidatas y ningun sello de tiempo en la cita que las distinga.
     Eso no es INCOMPARABLE, es AMBIGUO, y es un estado distinto con una
     herramienta distinta.
```

La segunda convierte la limitacion que `govcheck` declara en una `
AMBIGUO`, y eso es una mejora pendiente real: `git log -- AGENTS.md` da seis
versiones y una cita `AGENTS.md:118` tiene que declararse contra una de ellas o
contra ninguna.

Lo que **no** se puede recuperar es el texto exacto. Y eso no se arregla con una
herramienta: se arregla commitando el documento rector, que es justo lo que el
V6 no hizo al sustituirlo.

## 5 · Un error mío, y de la clase que este proyecto vigila

La primera medición de `govcheck` dio **1** sección rota. El recuento correcto es
**7**. Mi regex:

```
  no-greedy + terminadores SIN espacio  -> se para en la palabra más corta
                                            seguida de espacio: "OBJETIVO"
  greedy + terminadores SIN espacio     -> se come un espacio de más y falla
```

Las dos cosas a la vez: **greedy, con el espacio dentro del lookahead**. El
retroceso de un carácter del greedy es lo que hace que "LA CITA QUE SE SOSTIENE"
cas complete.

```
  un instrumento que cuenta de menos no es uno conservador: es uno que miente
  con menos ruido
```

Tres vectores fallaron a la vez y el síntoma común era el mismo nombre truncado,
así que se veía rápido. Lo que no se veía era el subconteo: **un número
demasiado bajo no dispara ninguna alarma**, igual que uno demasiado alto.

## 6 · El estado de los números duplicados ha empeorado

`dupenum` se escribió en esta misma sesión para resolver las colisiones de
numeración entre agentes paralelos. Aplicó 42 renumeraciones y bajó de 100
duplicados a 57. Ahora:

```
  ficheros de hallazgo   352
  numeros distintos      259
  numeros duplicados      66
    de ellos SEGURO        0
    de ellos AMBIGUO      66
```

**Ninguno reparable.** Cada grupo tiene sus dos miembros citados, y la regla que
escribí —renumerar solo si nadie cita— correctamente se niega a actuar.

```
  el ritmo de colisiones nuevas supera al de resolucion
```

Esto no es un fallo de la herramienta: es la herramienta funcionando. Lo que
significa es que la ventana de la corrección masiva **se cerró**, y que a partir
de aquí cada duplicado se resuelve leyendo los dos hallazgos y decidiendo, que no
es automatizable.

Los grupos 258 y 261 son los de esta sesión: `258` lo comparten un hallazgo de
ancho de banda de VRAM y el del fingerprint; `261`, uno sobre bancos de pruebas y
este. Los dos pares están citados y quedan `AMBIGUO`.

## 7 · Lo que NO se establece

```
  que las convenciones esten ABANDONADAS    NO. Nadie lo ha decidido. Se sabe
    que no estan declaradas; si se mantienen o se retiran es una decision abierta
  que las 7 secciones citadas significen todavia algo   NO_RESUELVE dice que el
    encabezado no esta, no que la idea se haya perdido
  el permission model vigente               CORROBORADO: §71 y §72 coinciden con
    lo que el nivel 4 exigia. Solo cambia el vocabulario
  las 26 citas por linea                     INCOMPARABLE con este metodo, y
    hacerlo mal seria peor que no hacerlo
```

## 8 · Trazabilidad

```
  tools/govcheck.py                    la auditoria, 10 comprobaciones, --json
  tools/routeaudit.py                  bloque de declaracion anadido
  tools/lint.py                        bloque de declaracion anadido
  tools/citeambig.py                   bloque de declaracion anadido
  tools/dupenum.py                     el estado de duplicados, 0 SEGURO
  AGENTS.md                            NO MODIFICADO, por decision del usuario
  findings/245                         la herramienta de duplicados
  findings/250                         el instruments que decia 22 y decia 0
```
---

## 10 · REMEDICIÓN 2026-10-03 — la deriva ocurrió dos veces

Este hallazgo se escribió cuando `AGENTS.md` pasó de 1101 a 3736 líneas. Desde
entonces el fichero rector ha vuelto a cambiar, y la re-medición con la misma
herramienta da lo mismo:

```
declarado en este hallazgo   AGENTS.md: 3736 lineas  (MASTER PROMPT V6)
medido hoy                   AGENTS.md: 4001 lineas  (AGENTS V11)
delta                        +265 lineas

FORMATOS que las herramientas imponen, con V11 vigente:
  PENDIENTE=             routeaudit, implgate, lint   NO DECLARADO
  ALCANZABLE_SIN_ROOT=   routeaudit, lint             NO DECLARADO
  CITA=                  citeambig                    NO DECLARADO
  TERMINO=               citeambig                    NO DECLARADO
  ROL=                   citeambig                    NO DECLARADO

CITAS por nombre de seccion, con V11 vigente:
  7 NO_RESUELVEN   §RESULTADO OBLIGATORIO, §AUTOMATIZACIÓN DE DOCUMENTACIÓN,
                   §DOCUMENTACIÓN EXTERNA, §F MEMORY SYSTEM,
                   §IMPLEMENTATION_GATE, §LA CITA QUE SE SOSTIENE,
                   §OBJETIVO FINAL

poblacion afectada:  157 ficheros de hallazgo CITABAN AGENTS.md
                     171 lo citan hoy        (+14)
```

**Lo que cambia respecto a la primera medición:** nada en la conclusión, todo
en la alcance. Los mismos 5 formatos, las mismas 7 secciones muertas, y la
población afectada ha crecido 14 ficheros.

**Lo que esto añade y no estaba:** que la deriva **es una propiedad de cómo
cambia la gobernanza de este proyecto, no un incidente**. El documento rector
cambió dos veces (1101 → 3736 → 4001) y en las dos el proyecto se quedó
referenciando al anterior. Un solo caso se corrige migrando; dos casos
aparejados indican que hace falta un mecanismo, y el hallazgo 968 ya lo propone para los
formatos: la regla se declara, el valor se mide.

Este hallazgo **sigue abierto**. Su estado no mejora con el cambio de versión:
las cinco convenciones que las herramientas imponen continúan sin declarar en el
documento rector vigente, y decidir si se mantienen o se retiran es decisión
del usuario, no de este proyecto.

**Herramienta:** `tools/govcheck.py`, `--selftest` en `PASS` con 24
comprobaciones antes de consumir su salida.

**Alcance de hardware:** ninguno. Lecturas de fichero. GPU intacta.
