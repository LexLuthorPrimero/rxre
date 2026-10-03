# Herramientas propias de la sesión de ingeniería inversa Polaris12/GFX8

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

Ocho herramientas construidas para acelerar la investigación estática del RX550.
Cada una tiene self-test ejecutable, y todas se validaron **desde esta ubicación**,
no sólo desde el directorio temporal donde se escribieron.

```
cd /home/lucas/Escritorio/RX550-INVESTIGACION/08-ARQUITECTURA/tools
python3 <herramienta>.py --self      # debe imprimir "todos pasan"
```

## Estado

| herramienta | casos | hash (primeros 16) | qué resuelve |
|---|---|---|---|
| `citecheck.py` | 32 | `6d30a5e9b23beaff` | que cada cita `fichero:línea` apunte a algo |
| `scopeguard.py` | 14 | `206299f010f3801a` | preflight de escritura: scopes, locks, duplicados, número libre |
| `xref.py` | 32 | `6c9f787f5b7b05de` | quién LEE y quién ESCRIBE un símbolo |
| `causal.py` | 21 | `75f9292858a584f5` | grafo de llamadas con la función contenedora |
| `contradict.py` | 25 | `1d8276992282f0ee` | cifras en conflicto entre hallazgos |
| `regdb.py` | 21 | `93dd5c536a1ee141` | registro/campo contra todas las familias de cabecera |
| `hdrmap.py` | 19 | `f7016fe9fb9e7fe2` | qué familias de cabecera declara cada `.c` |
| `emisor.py` | 16 | `CONTRASTE EMISOR/CORPUS` | dword a dword contra el emisor del ASIC que corre |

**180 casos de self-test en total.** Todas pasan.

`emisor.py` se documenta aparte, en su cabecera, porque su objeto es distinto: no analiza el
corpus, lo **contrasta** con nuestro codigo. Es la pieza que `test_pm4.c` declara no tener, y su
`CN-7` ejecuta `main()` de verdad contra un fichero mutado de verdad, porque un self-test que solo
ejercita la libreria no prueba el programa.

## Por qué existen, y no por acumulación

Cada una se construyó porque una operación repetida manually consumía tiempo o
porque un error concreto del trabajo se podía mechanizar. La prueba es que
`citecheck.py` detectó 3 de 4 errores de cita propios en una sesión, y
`regdb.py` encontró los 7 registros con dirección distinta entre familias que
escribió el hallazgo 065.

Las cuatro de registro (`causal`, `regdb`, `hdrmap`, más `xref`) componen la
cadena PRODUCER → CONSUMER → REGISTRO, y **ninguna reimplementa el índice del
corpus**: todas consumen el de `doclint.py`, que además incluye el kernel
instalado en el host. `hdrmap.py` usa `include_closure.find_header()` en vez de
reimplementar el resolutor de includes.

## Límites que las herramientas declaran

Los límites están en el `docstring` de cada una, y son reales:

- `citecheck.py` verifica que la línea **existe**, no que diga lo que la cita
  afirma. Un `:2438` erróneo pasa el filtro y se ve con `--context`.
- `xref.py` y `causal.py` clasifican **textualmente**. No son un parser de C: no
  resuelven macros, no ignoran comentarios, y una mención en prosa cuenta como
  uso. Distinguen `WRITE` de `READ` por intención léxica, no por análisis de flujo.
- `regdb.py` detecta discrepancias entre familias pero **no decide** cuál
  corresponde al ASIC: eso sale del `#include`, que es evidencia, no del programa.
- `hdrmap.py` sólo lee includes **directos**. Un `.c` que herede una cabecera de
  otro `.h` aparece como "sin familia" — es un límite de la herramienta, no un
  hueco del driver.
- `contradict.py` sólo ve la forma `símbolo = entero`. Una cifra en prosa no se ve.

## Lo que NO resuelven

- **No substituyen a `causal_map.py`**, que ya construye el índice estructurado de
  afirmaciones del proyecto y detecta contradicciones y cobertura. Es una
  herramienta distinta con otro propósito: ésta trabaja sobre símbolos y
  registros del corpus, aquella sobre lo que los hallazgos *afirman*.
- **No cierran fronteras por sí solas.** Una herramienta validada da evidencia;
  convertirla en cierre es trabajo de revisión.
- **No hacen ejecución.** Nada aquí escribe en la GPU ni requiere root.

## Por qué se instalaron ahora

Estaban en `/tmp` desde que se escribieron. El scope `tools/*` estaba tomado por
otra sesión, y `COORDINACION.md:160` dice que un cerrojo abandonado **no** es
permiso para tomarlo: se informa y se espera. Cuando la otra sesión liberó el
scope, se instalaron. No se reclamó ningún cerrojo ajeno en ningún momento.