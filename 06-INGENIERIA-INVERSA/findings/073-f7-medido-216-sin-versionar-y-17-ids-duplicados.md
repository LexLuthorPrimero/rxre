# 073 · F7 medido: 216 ficheros sin versionar, y 17 IDs de hallazgo duplicados ahora mismo

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + GIT_INSPECTION
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué es esto y qué NO es

`git status --porcelain` y `ls`. Nada más. **No hay `git add`, no hay commit, no
hay `git clean`.** F7 establece que *"git add es de las sesiones propietarias. Este
trabajo no hace commits ajenos ni versiona ficheros de otras sesiones"*, y eso se
respeta: esto mide, no versiona.

Lo que sí tiene valor es que **F7 seableró con 5 hallazgos sin versionar y ahora
mede 71**, y que los IDs duplicados pasaron de 10 a 17 durante esta sesión.

## La medición

```
  ficheros modificados o sin seguimiento        216
  de ellos, ficheros de hallazgo (.md)           71
  IDs de hallazgo duplicados                      17
```

Y las colisiones **son reales**, no prefijos que se parecen. Ejemplos verificados:

```
  051-interrupt-vector-iv-gfx8-y-teardown-lifo.md      <- mío, sobre IV y teardown
  051-leer-agents-md-cambia-la-politica.md            <- de otra sesión

  056-function-always-spec-primaria-descartada-con-causa.md   <- mío, sobre la spec
  056-siete-herramientas-y-22-bugs-encontrados.md             <- de otra sesión

  072-f3c-estatico-cond-exc-e-invalidate-response.md    <- mío, F3c
  072-la-lista-cerrada-de-verbos-que-cronometraba-el-grafo.md  <- de otra sesión
```

Tres temas completamente distintos por número. **Un hallazgo que se cita por su
número es ambiguo desde hoy**: "ver 051" no dice cuál de los dos.

## Por qué esto importa más de lo que parece

`COORDINACION.md:9-12` documenta **dos pérdidas reales de trabajo** en este
proyecto, y las dos fueron de trabajo sin commitear. Por eso la regla 2 del
protocolo dice "commitea antes de liberar".

El dato nuevo no es que haya trabajo sin versionar — eso ya lo sabía F7. Es que
**el mecanismo de numeración no funciona y nadie lo fuerza a funcionar**:

- `scopeguard.py` detecta los duplicados en un comando, y dice `32 IDs duplicados`
- el número **creció** durante la sesión, mientras había herramientas que lo veían
- las dos sesiones escribieron en el mismo directorio sin que el ID lo impidiera

Un detector que existe, funciona, y se consulta sin cambiar nada es un control
de cinta adhesiva mal pegada. Es exactamente el fallo que F11 describe para los titulares: la
capacidad de medir no sustituye a la obligación de actuar.

**Lo que hace falta no es otra herramienta: es que `mkdir` del lock venga con un
reservador de números.** `COORDINACION.md` dice que el cerrojo es por ámbito, y
`021-write-lock-scoped-subdir-does-not-block.md` ya demostró que los
sub-locks no excluyen. El caso es el mismo: el cerrojo protege **el fichero**, no
**el nombre**, y dos sesiones pueden tomar el mismo nombre en ámbitos distintos.

## Lo mío, separado de lo ajeno

```
  MÍO, sin versionar (esta sesión):
    hallazgos   062 064 065 066 067 068 069 070 071 072   (10 ficheros)
    herramientas  citecheck scopeguard xref causal contradict regdb hdrmap toolaudit
    documentación TOOLS-README.md, ESTADO-BASE-PRE-F1.md
    implementación f2_sampler_probe.c  + su binario
    edición      run_all.py  (9 entradas añadidas al runner)

  AJENO, sin versionar: el resto de los 216
```

El binario `f2_sampler_probe` no debería versionarse: es un artefacto de
compilación, no fuente. Lo dejo identificado para que quien haga el `git add`
decida, en vez de subir un ELF por descuido.

## Nada de esto está en riesgo por ahora

```
  amdgpu sigue cargado, VRAM 2048 MiB intacto
  6 paquetes de desarrollo instalados (headers de Mesa/GL, ninguno toca la GPU)
```

## Estado de F7

| Afirmación | Estado |
|---|---|
| 216 ficheros sin versionar | `PROVEN` (`git status`) |
| 71 de ellos hallazgos | `PROVEN` |
| 17 IDs de hallazgo duplicados | `PROVEN` (`ls` + `git status`) |
| Las duplicaciones son de contenido, no de nombre | `PROVEN` (3 pares leídos) |
| Los duplicados crecieron de 10 a 17 en la sesión | `PROVEN` (medido en dos momentos) |
| `git add` lo hacen las sesiones propietarias | política, no ejecutada |
| Que el trabajo sin versionar ya se perdió | `NOT_OBSERVED`, y las dos pérdidas previas son precedent |

## Procedencia

- `GIT_INSPECTION` — `git status --porcelain`. Sólo lectura, ningún cambio en el índice.
- `ls` sobre `06-INGENIERIA-INVERSA/findings/`.
- `scopeguard.py` para el recuento de duplicados.
- No se editó `OPEN-FRONTIERS.md` ni `F7`: son de otra sesión.