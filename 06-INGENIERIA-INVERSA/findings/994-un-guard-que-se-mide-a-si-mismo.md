# 994 · Un guard que se mide a sí mismo: 19 instrumentos SIN RED, y el primero era el propio guard

```text
CLASSIFICATION=MEASUREMENT+IMPLEMENTATION+AUTOMATION · TRACK=TOOLING
CORPUS=directo
HARDWARE_SCOPE=ninguno: no toca la placa
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
MODIFICATIONS_COUNT=0 sobre instrumentos existentes
AUTHORIZATION=NONE · GPU INTACTA · RUNTIME=NOT_RUN
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
CONTINUES=988 y el mismo numero 991, que quedo ocupado por otro hallazgo
         mientras este se escribia: se renumero a 994.
         CONTINUES=988, que dio 34 sin red contando "versionado sí/no".
         Este NO cuenta lo mismo: cuenta RECUPERABILIDAD, que tiene tres estados.
TOOL=08-ARQUITECTURA/tools/recovery_preflight.sh   (NUEVO, este nodo)
     git add + classification propia: VERSIONADO
ARTEFACTO=recovery-preflight.tsv
```

## Por qué esto no es el mismo número que 34

988 contaba una propiedad binaria: *¿git lo tiene?* La pregunta que importa cuando vas a
romper algo es otra:

> **Si lo rompo ahora, ¿qué puedo recuperar?**

Eso tiene **tres** respuestas, no dos, y la tercera es la que 988 no podía ver:

| estado | qué significa | cómo se recupera |
|---|---|---|
| `VERSIONADO` | git tiene el fichero | `git checkout` |
| `CON_HASH` | git **no** lo tiene, pero su sha256 está escrito en un artefacto **que sí está versionado** | reconstruyendo el byte y verificando el hash |
| `SIN_RED` | ninguna de las dos | **no** |

`CON_HASH` es la clase que el incidente de 984 produjo sin querer. `preruntime.sh` está
**sin versionar y con su hash escrito en dos artefactos commiteados**. Antes de este turno,
si ese `sed -i` no hubiera sido detectado por hash, se habría perdido. No por una propiedad
del sistema: por una coincidencia de procedimiento.

## El número

```
VERSIONADO   44
CON_HASH     14
SIN_RED      19
```

De los 34 que 988 contó como "sin red en git", **14 de ellos sí eran recuperables**,
porque su hash estaba escrito. Y `SIN_RED` bajó de 34 a 19 — no porque se versionara nada,
sino porque el criterio era más fino.

## La parte que no programé: el guard se mide a sí mismo primero

La primera fila del TSV es la propia herramienta, clasificada por ella misma:

```
   PRIMERA EJECUCION (sin git add)
   estado=SIN_RED   08-ARQUITECTURA/tools/recovery_preflight.sh

   tras git add
   estado=VERSIONADO
```

Es la única forma de que la afirmación sea verificable por quien la lee, y tiene una
consecuencia práctica: **esta herramienta no podía vivir en `tools/`**. El censo de 988
muestra que `tools/` es el árbol sin red — casi todos sus instrumentos son `SIN_RED` o
`CON_HASH`. Un guard de recuperación guardado donde no hay recuperación es peor que no
tenerlo, porque se lee como si alguien lo hubiera pensado y no lo ha pensado.

Por eso vive en `08-ARQUITECTURA/tools/`, que tiene 75 ficheros versionados.

## Controles, que es lo que lo hace creíble

| control | esperado | medido |
|---|---|---|
| fichero trackeado conocido | `VERSIONADO` | `VERSIONADO` |
| `preruntime.sh` (sin git, con hash en 988) | `CON_HASH` | `CON_HASH` |
| `tools/assert_contract.py` (ni git ni hash) | `SIN_RED` | `SIN_RED` |
| la herramienta antes de `git add` | `SIN_RED` | `SIN_RED` |
| la herramienta después | `VERSIONADO` | `VERSIONADO` |
| vocabulario del TSV | solo los 3 estados | solo los 3, `exit 2` si no |
| terceros en el censo | `ABORTO exit 2` | implementado (patrón `\t` del 988) |

**Los tres estados se han visto funcionar.** Un clasificador al que solo se le ha visto
devolver `VERSIONADO` no está probado: está probado un tercio.

## Contrato de coste, medido

```
wall 53.20 s   cpu 50.46 s   maxrss 14.6 MB
```

**Lento, y hay que decirlo.** El coste viene de indexar los hashes: recorre los 1495
ficheros versionados buscando cadenas de 64 hex. Es un coste **determinista y cacheable** —
los hashes de ficheros versionados solo cambian cuando cambia el commit, que es
exactamente lo que cachea `git ls-files`. Con `HEAD` como clave de caché, esto baja a
milisegundos. **No se ha implementado la caché**, porque instrumentar el caché sin medir si
compensa es el error antes de medirlo. Se declara como pendiente, no como hecho.

## Los 19 SIN_RED, que son el objetivo

```
tools/assert_contract.py      tools/claims.py           tools/frontier.py
tools/citeambig.py            tools/drift.py            tools/docscan.py
tools/rx550/regla.py          tools/rx550/contract.py   tools/rx550/alcance.py
tools/rx550/revierte.py       tools/rx550/mandato.py     tools/rx550/conflicto.py
tools/rx550/bits.py           tools/rx550/transiciones.py
tools/rx550/run-all.sh        07-DRIVER/driver/test_rx550_pciid.sh
04-IMPLEMENTACION/rx550-mem/mutate.sh
03-EXPERIMENTOS/{control,sandbox}/tests/test_static.sh
06-INGENIERIA-INVERSA/agents/astext.py
```

`assert_contract.py` y `run-all.sh` son los dos que más precondiciones declaran. **Si el
validador de contratos cambia y cambia bien, no hay forma de saber qué cambió ni de volver
atrás.** No es una pérdida: es la ausencia del mecanismo que la haría posible.

## Lo que NO se hace aquí

- **No se añade nada a git.** Los 19 son decisión estructural. Lo único que se ha añadido es
  la propia herramienta, porque **tenía que ser recuperable para poder hablar de
  recuperabilidad**, y eso no es una excepción sino la condición de uso.
- **No se arregla el `assert_contract.py` ni se audita su corrección.** Que tenga precondiciones
  no dice nada de si son correctas ni de si son circulares en el sentido de 985.
- **No se convierte en gate de la suite todavía.** Es un artefacto y una medición. Convertirlo
  en puerta es la acción siguiente, y tiene su propio coste.

```
LIMITACION  CON_HASH prueba que el hash está escrito en un artefacto versionado. NO prueba
            que ese hash sea el del fichero que hay ahora. Para eso hay que comparar, y un
            CON_HASH cuyo sha difiere del registrado es la señal de alarma más fuerte que
            tiene esta herramienta. NO se ha implementado esa comparación: es el siguiente
            paso y es un discriminante real, porque distingue "sin red" de "cambiado".
```