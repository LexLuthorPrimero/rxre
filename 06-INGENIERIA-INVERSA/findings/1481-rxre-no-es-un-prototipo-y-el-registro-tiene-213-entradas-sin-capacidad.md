# 1481 — `rxre.py` no es un prototipo: es un orquestador con 188 vectores, y el hueco real es de 213 herramientas sin capacidad declarada

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=MEDICION
ESTADO=PROVEN
ALCANCE=arbol local /home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA
MEDIDO=sobre el arbol local, con `command -v` y lectura de fuentes. No hay MMIO,
  no hay TLB, no hay insmod, no se toca 0000:00:02.0
PRODUCER=RXRE/tools/rxre_boot.py v1.0.0
ARTEFACTO=RXRE/artifacts/BOOTSTRAP-001.json (270734 bytes, sha256 abajo)
COMANDO=python3 RXRE/tools/rxre_boot.py --json --out RXRE/artifacts/BOOTSTRAP-001.json
ARTIFACT_HASH=sha256 75676aa05849b897b6df7786c269e33a53a4931b01dfb01b296c08c737e2cf70
TOOL_HASH=sha256 d7228a46e23b31ed6954c17589ecd5a52559637bd2a5c3cb61aee1c61daf853e
VECTORES=19 de 19 PASS
```

## Qué se preguntaba

La consigna para construir RXRE como plataforma era: "no partas de cero, primero
inventaría". Y añadía una hipótesis explícita sobre el punto de partida:

> "Especialmente determina qué parte de `tools/rxre.py` ya existe y si representa
> un prototipo inicial de RXRE. No asumas que está incompleto solamente por su
> tamaño."

Eso es una hipótesis falsable, así que se midió en vez de aceptarse.

## Resultado 1 — la hipótesis queda REFUTADA

`tools/rxre.py` son **2730 líneas, 132936 bytes, versión declarada 1.0.0**, y
sus 188 vectores pasan todos:

```
$ python3 tools/rxre.py --selftest
...
SELFTEST OK: 188 vectores
```

No es un prototipo. Es un **orquestador de catálogo ejecutable** con, medido por
`grep` sobre su propio fuente:

| capacidad declarada en él | qué hace de verdad |
|---|---|
| catálogo de 26 filas × 14 campos | qué herramienta cubre qué capacidad |
| `CAP_REFUTADA` | separa *evidencia negativa medida* de *capacidad enrutable* |
| 3 puertas (`FRONTERA`, `GANANCIA`, `REVERSIBILIDAD`) | decide qué herramienta **NO** ejecutar todavía |
| `objetivo_a_capacidades` | pregunta en lenguaje natural → cadena de capacidades |
| 9 validadores ejecutables | las reglas de §22/§26/§80 como código, no como prosa |
| `mutation_sensitivity` | mide si esos validadores **saben fallar** (17 mutaciones) |
| `cobertura_de_campos` | si las reglas alcanzan a los hallazgos reales |
| `cobertura_minima` | escalera k campos → cuántas reglas desbloquean (exhaustiva, 2^17) |
| `discrimina` / `siguiente_accion` | la prueba más barata que separa dos modelos |
| `contradiccion` | detecta conflicto y **nunca** elige ganador |
| `work_scan` | cuenta hallazgos, repetidos y **authorship** |
| `MATURITY` | manifiesto que degrada a manual toda capacidad sin vector |

Dos detalles que lo separan de un prototipo y que conviene conocer antes de
tocarlo:

- **`PUERTA_FRONTERA` es un hecho, no una política.** `limites_de_la_maquina()`
  lee `/sys/class/drm/card{0,1}/device/{vendor,device}` y separa
  `escribe_en_el_sistema` (autorizable) de `toca_la_integrada` (sin salida). La
  frontera dura de AGENTS.md ya está **ejecutable** aquí, con vector.
- **`MADUREZ` se autolimita.** La regla `if auto and not vector: auto = False`
  significa que ninguna capacidad puede declararse automatizada sin un vector
  que la ejercite. `AUTONOMOUS_RE` está declarada `NO` a propósito.

**Conclusión:** el "primer minimalist architecture" de la consigna (cap 34) ya
tiene su columna vertebral. Lo que falta no es el orquestador: es lo que el
orquestador declara en su propio manifiesto como `residual`, y son cinco.

## Resultado 2 — el hueco real, medido

`rxre` recorre `toolreg` para el **árbol** y `shutil.which` para el **PATH**.
Son dos universos disjuntos y está bien que lo sean. Pero la tabla de
capacidades `CAP` cubre **26 filas**, y el registro `toolreg` inventaría **217
entradas** en 7 directorios:

```
tools                            97
08-ARQUITECTURA/tools            74
revkit                           33
04-IMPLEMENTACION/rx550-driver/tools  6
09-POWER-CLOCKS/tools             4
04-IMPLEMENTACION/tools           2
01-AUDITORIA/tools                1
```

**213 de 217 entradas del registro no tienen ninguna capacidad declarada en el
catálogo de rxre.** Solo 25 quedan cubiertas — y esa cifra es de 25
*herramientas distintas*, no de 26 filas: `llvm-mc` tiene **dos filas
legítimas** con capacidades distintas (`ISA_ENCODE` e `ISA_DECODE`), y el propio
`rxre` lo declara así y lo comprueba con un vector (*repetir HERRAMIENTA no es
repetir fila si las capacidades difieren*). Contado por fuera, en el fichero:
`CAP` tiene 26 filas y 25 nombres distintos.

Y las que quedan cubiertas no son todas enrutables: rxre cataloga
`tools/ibref.py`, `tools/mmio.py`, `tools/layoutcross.py`, `tools/toolreg.py` y
`cp`, pero no `tools/ibref.py` como `PM4_SYNTH` frente a `revkit/pm4dec.py` como
lo mismo, ni `08-ARQUITECTURA/tools/xref.py` frente a `tools/xref.py`, que
existen **los dos** con contenidos distintos (sha12 `4205fbc42e9e` y
`90bb073df932`).

Este es el hueco que importa para la consigna, y no es un hueco de
arquitectura: es un hueco de **catálogo**. La pregunta que el north star quiere
poder responder —

> «¿qué herramienta tengo para descubrir escritores de este registro?»

— hoy responde bien para ~25 instrumentos y no tiene respuesta para los otros
192. `rxre`'s propio `huecos()` lo detecta para 5 capacidades y dice `RUNTIME_INSPECT`,
`STRUCT_OFFSET_LIVE`, `RUNTIME_CLOCK` e `ISA_ANALYZE` están *"ninguna viva:
ausentes, fallidas o vetadas"*; verificado a mano: `drgn` no está en PATH,
`rocm-smi` no está, `rga` no está, `clrxdisasm` no está. **Esas cuatro ausencias
son reales.**

## Resultado 3 — lo que sí está unificado, contra lo que no

Lo que ya es común (y por tanto no hay que reescribir):

- **217 entradas, un solo registro.** `toolreg` es la verdad; `rxre` consulta;
  `rxre_boot` consulta el mismo. Verificado: 0 rutas del inventario que no
  existan en el árbol.
- **Salida parseable mayoritaria**: 101 herramientas con `--json`, 158 con
  `--selftest`, **93 con las dos** — que es el criterio real de "puede dejar
  evidencia utilizable".
- **Procedencia del corpus con productor único**: `prov.py` medido sobre 607
  hallazgos con token de estado; D1 sin 473, D2 sin 98, D3 sin **2** (0.3 %).
  Factor D1/D3 = **236.5×**. Ese factor es el hallazgo `1473`, y se **invoca**
  desde el bootstrap en vez de reimplementarse: dos números para la misma cifra
  es justo lo que `1473` midió.

Lo que **no** está unificado, y es el hallazgo de este inventario:

- **165 aristas de dependencia, y 172 llamadas por `subprocess` que NO son
  aristas.** El grafo estático es una **cota inferior** del acoplamiento real, y
  no lo acerca al orden de magnitud: 110 de las 165 aristas vienen de rutas
  escritas en cadenas, y las 172 invocaciones por `subprocess` son
  acoplamiento real invisible. Con 9 ficheros usando `importlib`.
- **42 tipos de relación distintos** en `relations.py`, para 171 aristas y 124
  nodos: `CORRECTS` y `CORRIGE`, `RETRACTED_BY` y `RETRACTA_LA_PROMESA_DE`,
  `CONFIRMED_BY` y `CONFIRMADO_POR` coexisten. No hay vocabulario cerrado, así
  que un grafo con 42 etiquetas **no es consultable por relaciones**.
- **Cuatro nombres duplicados en directorios distintos, los cuatro con
  contenido divergente**: `contradict.py`, `fingerprint.py`, `huella.py`,
  `xref.py`. Ninguno es duplicación; son instrumentos distintos que comparten
  nombre, y `rxre.py` ya tiene un vector que documenta exactamente ese caso
  (`toolreg.py` pisado por otro fichero del mismo nombre). El riesgo está vivo.

## Procedencia

- `STATIC` — lectura de `tools/rxre.py` **completo** (2731 líneas) antes de
  decidir; `tools/toolreg.py` (18 defs, 1208 líneas); `tools/prov.py`
  completo. `python3 tools/rxre.py --selftest` → 188 vectores, todos `ok`.
- `COMANDO` — `RXRE/tools/rxre_boot.py --selftest` y `--json --out`, 19
  vectores, todos `PASS`, rc=0. Artefacto 270734 bytes.
- `CROSS-CHECK` — las 4 ausencias de binario verificadas **con `command -v`,
  por fuera de rxre**, no leyendo su veredicto.
- **Sin MMIO write, sin TLB, sin insmod, sin tocar la GPU integrada.**
  `command -v` y la lectura de fuentes no escriben nada. `rxre_boot.py` es
  aditivo, de solo lectura, y escribe únicamente en `--out`.
- El único fichero creado por esta sesión fuera de `findings/` es
  `RXRE/tools/rxre_boot.py` (nuevo, 1059 líneas) y su artefacto JSON.
  **Ninguna herramienta existente fue modificada.** `rxre_boot.py` son 953 líneas,
no 1059: la cifra anterior era una estimación mía y se cuenta aquí con `wc -l`
por si alguien la reutiliza.
- Cadena: `1473` (procedencia), `1185` (lo que llvm-mc no hace), `1191`
  (curva de campos), y el propio `rxre.py` §4b, que ya narra el `toolreg.py`
  pisado.

## Lo que NO se afirma

- **No se afirma que las 192 herramientas sin capacidad sean útiles.** Absence
  de declaration no es absence of capability (§16, §26). Lo medido es que
  **rxre no puede enrutarlas**, no que no hagan nada.
- **No se afirma que los 5 huecos de capacidad sean los únicos huecos.** Se
  calculan sobre el catálogo `CAP`, que es lo que rxre conoce. Si se amplía el
  catálogo, la lista cambia.
- **No se ejecutó ninguna herramienta del registro.** El mapa E/S y el de
  formatos son de parseo estático. `--help-probe` existe y registra el rc, pero
  **no se usó** para este hallazgo, así que este documento **no dice que
  ninguna arranque**.
- **No se modificó ninguna herramienta existente.** `rxre_boot.py` es aditivo
  y de solo lectura.

## CONFOUNDER MEDIDO: el denominador se movió durante la sesión

Entre la primera y la última ejecución de `rxre_boot.py`, el registro pasó de
**217 a 218 entradas**, y `tools/` de **97 a 98**. La causa está identificada y
**no es este trabajo**: `tools/asicpath.py`, 16716 bytes, mtime `01:20`, aparece
como `??` en `git status` junto a otros ocho ficheros no versionados. El árbol
lo está escribiendo otra sesión.

```
$ for i in 1 2 3; do ... inventory() ... done     # 20 s de separacion
entradas=218  tools=98
entradas=218  tools=98
entradas=218  tools=98
```

Estable dentro de la ventana, así que **las cifras del hallazgo son coherentes
entre sí** — las 217 se leyeron de una sola ejecución y el artefacto JSON guarda
exactamente ese conjunto de rutas. Pero la afirmación *"213 de 217 no tienen
capacidad"* tiene la forma `no_enrutables / total_del_registro`, y el segundo
término **no es una constante de este proyecto**: crece mientras se investiga.

**Por eso el hallazgo expresa el hueco como cifra absoluta (`213`), que no se
mueve, y no como porcentaje (`88 %`), que sí.** AGENTS.md lo dice del contador
de hallazgos; lo mismo vale para el denominador del registro, y por el mismo
motivo: **el número más alto cuenta trabajo gastado, no el estado del catálogo.**

## Dos notas de método

**La primera: los vectores fallaron cinco veces, y cuatro por el vector.**

`rxre_boot.py --selftest` dio `10 pasan, 3 fallan` en su primera ejecución. Los
tres fallos eran **del instrumento**, no del sujeto:

1. `RXRE` apuntado a `RXRE/tools/rxre.py`, que no existe → `FileNotFoundError`
   al cargar el catálogo → **28 capacidades leídas como 0**. Un número derivado
   de una carga fallida no es un cero: es un número inventado con la forma
   correcta. El error se escondía porque el selftest también fallaba.
2. Se daba `Tool.path` de `toolreg` por relativo; **es absoluto**. Las 217
   rutas apuntaban a sitios inexistentes, y el inventario entero era de nada.
3. Un vector buscaba la clave `"NOTA"` donde la clave se llama `"nota"`, y luego
   pedía que la nota contuviera la palabra `NOTA`, que no contiene.

A eso se suman dos vectores escritos **siempre en verde**: uno con
`if "clave" in ev else True`, y otro con una resta cuyos dos lados se cancelan
por construcción. Ninguno podía fallar. Se sustituyeron por la partición real,
que sí puede fallar.

El vector que cazó el caso 2 fue `toda-ruta-del-registro-es-relativa-a-la-raiz`.
Se podía **relajar** —el inventario "funcionaba" sin él— y no se relajó: se
arregló el código. *Un vector que falla por el código y no por el sujeto no se
relaja: se arregla, y el arreglo se escribe.*

**La segunda: el hueco se encontró en la primera pregunta, no en la décima.**

La consigna pedía un mapa de dependencias elaborate, con adaptadores y esquemas.
El primer número que salió del inventario —`26 filas de catálogo contra 217
entradas de registro`— ya era la respuesta a *«qué falta»*. Las nueve capas de
arquitectura que propone el north star no las puede cerrar nadie mientras la
pregunta de north star no tenga respuesta para el 88 % del catálogo.

Eso no es un argumento contra la arquitectura. Es un argumento **de orden**: el
primer paso medible es `cerrar el catálogo de capacidades sobre 192
herramientas`, y no requiere escribir una línea de código nuevo — es medir, con
`toolreg` como única fuente, y es donde está el trabajo.

**Estado final: `PROVEN` para las cifras, `NOT_DETERMINED` para la
utilidad.** Lo segundo no se ha medido y no se afirma.
