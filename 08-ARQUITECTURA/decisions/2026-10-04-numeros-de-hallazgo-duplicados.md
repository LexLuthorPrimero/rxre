# DEC-2026-10-04 — Los números de hallazgo duplicados: qué se repara y qué no

**Estado**: `ACCEPTED` · decide, no propone.
**Fecha**: 2026-10-04 · **Nodo**: `NUM-UNIQUE-GATE`
**Ámbito**: `06-INGENIERIA-INVERSA/findings/`, `FINDINGS-RENUMERACIONES.md`,
`docs/FINDINGS-INDEX.md` · **Modo**: `READ_ONLY` sobre el árbol. Ni un renombrado,
ni una cita reescrita, ni un byte del driver tocado.
**Puerta que la hace ejecutable**: `tools/check_num_unico.py`

---

## 0. POR QUÉ ESTE DOCUMENTO EXISTE

Porque el árbol tenía **dos reglas opuestas y ninguna entrada de DECISION LOG que
dijera cuál obedece**. Medido, no interpretado:

- `tools/nextnum.py:32-35` — «No renumera. Renombrar 64 numeros y sus 87
  ambiguedades rompe todas las citas a la vez, y las citas son la evidencia […] 048
  dice exactamente esto y el proyecto no lo ha ejecutado.»
- `08-ARQUITECTURA/tools/num_collision.py:49-51` — «No renumera. Renumerar 126
  documentos rompe todas las citas a la vez.»
- `08-ARQUITECTURA/tools/num_collision.py:245-246` — «Esto mide el alcance del
  problema. NO PROPONE renumerar».

Y en dirección contraria, en el mismo árbol:

- `FINDINGS-RENUMERACIONES.md` **ya registra 43 renumeraciones ejecutadas**, 42 de
  ellas marcadas `REASIGNADO: SI`. El renumerado no es una propuesta: es un hecho
  consumado, y las 1033 referencias que dejó colgando son su precio ya cobrado.
- `tools/dupenum.py` tiene un modo `--aplicar` **escrito y funcional** que
  renumera. Si la política fuera «no renumerar», ese código es código muerto que
  además se ofrece como camino.
- `06-INGENIERIA-INVERSA/findings/400-el-resumen-y-el-aviso-tienen-vector.md:243`
  — «renombrar **los míos** no rompe nada suyo: desambigua las citas que ya».

**Censo de posiciones escritas.** 20 líneas que dicen «no renumerar» en 12
ficheros (`tools/nextnum.py`, `tools/dupenum.py`,
`08-ARQUITECTURA/tools/num_collision.py`, y 8 hallazgos: `048`, `073`, `074`,
`077`, `197`, `274`, `400`, `943`, `944`, `999`), y al menos 3 que dicen lo
contrario. Sin esta entrada, un agente que lea `nextnum.py` y otro que lea
`dupenum.py --aplicar` llegan a conclusiones opuestas y ambos pueden citar la fuente.

**Esta entrada cierra la contradicción. La política que gana es la de reparar
adelante, y su alcance exacto es §1.**

---

## 1. DECISIÓN

**Se adopta M1: el índice `NNN → [ficheros]` generado es el mecanismo de
desambiguación, y `tools/check_num_unico.py` es su puerta.**

En concreto, cuatro reglas, cada una con su por qué medido:

**D1 — El número de hallazgo NO es clave primaria y no se cita nunca por número
desnudo.** Se cita por nombre de fichero. Motivo: los 540 nombres de
`findings/` son únicos —medido: `len(listdir)` = 540 ficheros, 540 nombres
distintos, 0 colisiones de nombre—, luego el nombre **sí** identifica. El número
no: hay 74 números que identifican 2 o 3 hallazgos distintos. Una cita por
nombre puede estar COLGADA (no resolver a nada), que es un defecto distinto y
detectable; una cita por número duplicado es AMBIGUA, que no lo es.

**D2 — El índice de colisiones se genera y se verifica contra el FS, y la
verificación compara CONJUNTOS, no recuentos.** Motivo medido, y es el motivo de
que esta decisión no pueda ser la de "solo comparar recuentos":

```
findings/*.md por os.listdir                    : 540
`Ficheros en findings/` que declara el índice    : 509     (31 viejo)
números con colisión por el FS                  : 74
números con colisión que declara el índice      : 74      ← COINCIDE
filas en la tabla de colisiones del índice      : 74      ← COINCIDE
  … y el conjunto NO coincide:
    en el FS y SIN fila en el índice             : 1011
    con fila y SIN colisión en el FS            : 998
```

El recuento da 74 = 74 y el conjunto es otro. Una puerta que comparase recuentos
pasaría **en verde hoy, con el defecto presente**. Mecanismo, por mtime:

```
FINDINGS-RENUMERACIONES.md   generado 2026-10-03T15:59:03
1011-el-grep-de-ad8...md     creado    2026-10-03T16:06:21   (+7 min)
1011-la-regla-de-shell..md   creado    2026-10-03T16:06:37   (+8 min)
ficheros de findings/ más nuevos que el índice : 196 de 540
```

Los dos errores se compensan y el número sale bien. Por eso el índice se
comprueba por conjuntos. Este es el defecto que la puerta existe para que no
vuelva a pasar: **nadie comparó el número del informe contra el disco.**

**D3 — Las 20 posiciones que dicen «no renumerar» quedan CLASIFICADAS, no
borradas.** No se tocan esos ficheros. Se reescriben para que apunten a esta
entrada, que es lo que evita que la contradicción reaparezca. Ninguna de las 20
 dice hoy «no renumeres nunca»: todas dicen «renumerar rompe citas», y eso es una
afirmación sobre el **método**, no sobre el **destino**. Medido: la afirmación es
cierta para renumerar sin más (43 renumeraciones dejaron 1033 referencias
colgando) y falsa como prohibición, porque `dupenum.py --aplicar` tiene una regla
que libera **solo** lo que no está citado, y hoy eso es exactamente 1 de 74
grupos.

**D4 — M1 NO puede devolver 0, y se dice antes de que nadie lo espere.** Medido
sobre una copia del árbol real, con el generador real:

| estado | código | códigos que se disparan |
|---|---|---|
| estado real de hoy | **5** | `[5, 3, 4]` |
| índice regenerado desde el FS | **4** | `[4]` |
| regenerado + fila de la 1011 borrada a mano | **5** | `[5, 3, 4]` |
| regenerado + 3 citas por número a la 033 | **4** | `[4]` |
| sin colisiones + índice al día | **0** | `[]` |

Los códigos 5 y 3 **se van juntos** al regenerar: sobre un índice generado, «todo
número duplicado tiene fila» y «la tabla es el conjunto de colisiones del FS» son
la **misma proposición** — si falta una fila, sobra otra. Lo que queda después de
arreglar el índice son **2148 citas por número que apuntan a un número duplicado**.
Eso es lo que M1 no arregla, y es lo que convierte a M1 en *medible* y no en
*suficiente*.

LA CIFRA DE CITAS ES UNA INSTANTANEA, Y EL ARBOL ESTA VIVO. Medido con
`python3 tools/check_num_unico.py --json` sobre el árbol real:

```
2026-10-04T02:57Z   540 ficheros   74 grupos   2148 citas ambiguas   [5,3,4]  codigo 5
2026-10-04T03:1xZ   540 ficheros   74 grupos   2154 citas ambiguas   [5,3,4]  codigo 5
```

El número de **grupos** no se movió (74) y el de **citas** sí, +6 en quince
minutos, porque otro nodo estaba escribiendo hallazgos al mismo tiempo. Por eso
aquí se citan los dos juntos: el código de salida depende de si hay colisiones, y
74 no ha cambiado; el recuento de daño es una foto y hay que fecharla para
citarla.

---

## 2. POR QUÉ M1 Y NO M2 NI M3

Los tres con su coste medido, sobre el árbol de hoy (**540 ficheros, 74 grupos,
175 implicados, 101 copias sobrantes; 47 grupos de 2, 27 de 3**).

### M2 — sufijo por duplicado (`1031`, `1031b`) — RECHAZADA, no diferida

| coste | medida |
|---|---|
| ficheros a renombrar | **101** (47 grupos de 2 → 1 mueve; 27 de 3 → 2 mueven) |
| referencias por nombre que hay que reescribir, escritas a mano | **671**, en **110 documentos** |
| referencias por nombre, incluyendo 3 artefactos generados | 6371, en 113 documentos |
| `dupenum.py --aplicar` puede aplicar hoy | **1 de 74 grupos** |

El último renglón es el que decide. M2 exige reescribir 671 referencias escritas a
mano, y la única herramienta del proyecto que puede hacerlo sin criterio —
`dupenum.py --aplicar` solo puede aplicarla a **un** grupo, porque 73 de 74 tienen
**todos** sus ficheros citados. M2 como política general está agotada, y su coste
no es de ejecución sino de criterio: elegir qué numero se queda es una decisión
de contenido que ninguna herramienta puede tomar.

Y el daño de M2 no es el renombrado: es que **el número deja de ser histórico**.
`num_collision.py` observa que las citas tienen forma `033:397`, y 033 era la
«ronda 33». M2 destruye esa agrupación para resolver un problema que el índice
resuelve sin destruir nada.

### M3 — marca de cabecera en los duplicados más recientes — RECHAZADA

| coste | medida |
|---|---|
| cabeceras a editar | **101** |
| criterios verificables desde el FS | **0** |

M3 es el más barato de aplicar y el más caro de verificar, y esa asimetría es el
motivo entero del rechazo: «el más reciente» es un hecho de `mtime`, y `mtime` no
sobrevive a un `git checkout`, ni a un `cp`, ni a un `tar` sin `-p`. Una marca que
la puerta no puede comprobar desde el FS es una **afirmación**, y una afirmación
no es una puerta. El criterio que M3 quiere —«el segundo 999 no se renumeró por
política»— ya está escrito y es durable: `findings/999:219` lo dice, y un texto
dentro del fichero sobrevive al `mtime`.

### M1 — índice generado + puerta — ELEGIDA

| coste | medida |
|---|---|
| ficheros a renombrar | **0** |
| citas a reescribir | **0** |
| cabeceras a editar | **0** |
| regenerar el índice | `08-ARQUITECTURA/tools/findings_index.py` (ya existe) |
| ejecutar la puerta | **1.6 s**, 31 MB de RSS, 2496 ficheros leídos |
| autocomprobación | la cuenta la hace el FS: `tools/check_num_unico.py --selftest`, 23 comprobaciones, 0 fallos |

---

## 3. CONSECUENCIA

1. **`tools/check_num_unico.py` es la puerta del proyecto para esta propiedad.**
   Returna **5** hoy, con `[5, 3, 4]`. Los códigos son 0/2/3/4/5; el 1 no se usa
   porque se confunde con un linter. Precedencia declarada: 2 > 5 > 3 > 4, y se
   imprimen **todos** los que se disparan, porque un código que oculta a los otros
   es un contador y no una puerta.
2. **`tools/dupenum.py` deja de devolver 0 con el defecto presente.** Era la única
   de las tres herramientas del tema que pasaba en verde con 74 colisiones
   delante. Ahora: `0` sin duplicados, `2` sin medir, `3` todos reparables, `4` con
   al menos un AMBIGUO. `--json` sigue imprime JSON válido aunque salga 4: el
   veredicto es el código, no el stdout. Verificado sobre el árbol real: sale 4.
3. **El índice se regenera antes de cualquier análisis que lo cite.** El código 5
   dice exactamente eso, y sale antes que 3 y 4 porque A2 y A3 se miden *contra* el
   índice: si el índice no regenera idéntico, la comparación se hace contra una
   medida equivocada y un 3 emitido ahí sería un hallazgo sobre un fichero
   desactualizado, no sobre el árbol.
4. **`docs/FINDINGS-INDEX.md` queda superado por `FINDINGS-RENUMERACIONES.md`.**
   Motivo medido: el primero es de escritura manual, mtime `2026-10-02T01:20`, su
   cabecera dice «40 índices duplicados», su sección se titula «Los 24 índices
   duplicados», y su tabla tiene **13** filas. Hay 74. Tres cifras distintas en el
   mismo fichero. Dos índices del mismo objeto con cifras distintas y ninguno
   verificado contra el disco: el peor de los dos casos, porque un lector no
   sabe cuál de los dos leer.
5. **Lo que sigue abierto y NO lo arregla esta decisión**: las ~2150 citas por
   número que apuntan a un número duplicado. M1 las hace *visibles* y contadas;
   hacerlas *correctas* es reescritura de texto, y eso es otro nodo.

---

## 4. ALTERNATIVAS DESCARTADAS, con el motivo

| alternativa | por qué se descarta |
|---|---|
| Renumerar los 74 grupos de golpe (M2 sin criterio) | 73 de 74 tienen todos sus ficheros citados; `dupenum --aplicar` solo puede liberar 1. No hay criterio mecánico para elegir qué número se queda. |
| Dejar el estado como está y solo documentarlo | Es lo que ha pasado: el índice lleva 196 ficheros de retraso y nadie lo notó porque nadie lo comparó contra el disco. Documentar sin puerta no produce un cambio de estado. |
| Comparar solo recuentos en la puerta | Medido: hoy el recuento de colisiones coincide (74 = 74) y el conjunto no. Esa puerta pasaría en verde con el defecto presente. |
| Que la puerta afirme solo A1 (números únicos) | A1 sola no ve el índice viejo: con 74 colisiones, el codigo 5 sale hoy solo por las cifras, y al regenerar el índice A1 seguiría diciendo «74 colisiones» sin que nada lo detecte. Se necesitan las tres afirmaciones. |
| Que `check_num_unico.py` regenere el índice | Lo haría WRITE. La puerta tiene que poder fallar sin tocar nada, o el fallo deja rastro en el árbol y el siguiente run ya no ve el defecto. |
| Usar `git ls-files` como fuente del FS | Medido: `git ls-files 06-INGENIERIA-INVERSA/findings` devuelve **544** frente a **540** de `os.listdir`. La diferencia son 5 stubs de reserva en `findings/_reservas/` **más un hallazgo sin commitear**: `1035-las-tres-anomalias-del-corpus...md`, escrito a las 02:38:34 por otro nodo mientras este corría. El índice del proyecto ya va un fichero por detrás del árbol. `os.listdir` es lo que la puerta puede regenerar y comparar sin depender de un commit. |

---

## 5. REVERSIBILIDAD

**Total, y con coste cero.** Los cambios de este nodo son:

- `tools/check_num_unico.py` — fichero **nuevo**. Borrarlo devuelve el árbol a su
  estado. No lo referencia nada más.
- `tools/dupenum.py` — cambio de **código de salida**, no de medida. Verificado:
  el `--json` antes y después produce el mismo conjunto de 74 grupos con el mismo
  conjunto de ficheros en cada uno, y la misma clasificación SEGURO/AMBIGUO. La
  única diferencia en el artefacto es `total_ficheros` 539 → 540, y es porque
  **otro nodo escribió `1035-las-tres-anomalias-del-corpus...md` a las 02:38:34
  mientras este corría**. Revertir es `git checkout tools/dupenum.py`.
  Reutilizadores afectados: ninguno. Ningún fichero del proyecto mira el código de
  salida de `dupenum.py` (medido: las 13 menciones de `dupenum` en el árbol son
  documentación, un `.tsv` de validación y un comprobador de resolución de
  nombres en `toolaudit.py`; ninguno hace `returncode`).

**Lo que NO es reversible, y por que no se aplica:** renombrar 101 ficheros.
Por eso M2 queda rechazada y no aplicada.

**Reapertura:** `NEW_EVIDENCE` (que `dupenum --aplicar` con una regla mejor libere
más de 1 grupo), `NEW_REQUIREMENT` (que aparezca un consumidor que necesite el
número como clave), o `NEW_COUNTEREXAMPLE` (que el índice se vuelva a desincronizar
tras regenerarlo, lo que invalidaría D2 y obligaría a M3 o a un índice en git).

---

## 6. CONTRADICCIONES QUE ESTA ENTRADA NO RESUELVE

Se registran, no se cierran:

- **20 posiciones escritas dicen «no renumerar»** y 3 dicen lo contrario (§0). Esta
  entrada decide; reescribir esas 20 líneas es trabajo de otro nodo y es
  `REPAIR_OVER_PRESERVATION` con criterio editorial, no mecánico.
- **`943-setenta-numeros-de-nota-duplicados.md:90` y
  `944-el-mecanismo-existe-y-429-notas-no-lo-usan.md:108` Instance: cifras que no
  reconcilio**: ambos hablan de «167 notas colisionadas» y «3840 citas
  entrantes». Hoy hay 74 grupos y ~2150 citas por número (fotografadas arriba).
  Sus cifras son de una
  fotografía anterior y no he podido determinar con qué alcance se midieron:
  `NOT_DETERMINED`, motivo: no hay en el árbol el artefacto que las produzca con su
  alcance declarado, y reconstruirlas exigiría volver a medir con una definición
  de «cita entrante» que esos dos documentos no fijan.
- **El enunciado del nodo dice «0 citas ambiguas en `07-DRIVER/`». NO se
  reproduce: hay 9**, las 9 de la forma `NNN:LL` en `07-DRIVER/kernel/rx550_pm4.c`
  (líneas 600, 601, 604, 668 y 4 más), apuntando a `039:` (2 ficheros) y `040:`
  (3 ficheros), ambos duplicados. Con el alcance declarado por la puerta
  (`--alcance propio`, que excluye `RESEARCH/` y `rx550-upstream-7.2.8/`). No sé
  con qué alcance se midió el 0; `NOT_DETERMINED`.

---

## 7. ARTEFACTOS Y PROCEDENCIA

| artefacto | estado | sha256 (completo en el informe del nodo) |
|---|---|---|
| `tools/check_num_unico.py` | NUEVO, 1.0.0, `WORK_CLASS=READ_ONLY` | ver informe |
| `tools/dupenum.py` | MODIFICADO, 1.0.0 → 1.1.0, solo códigos de salida | ver informe |
| `08-ARQUITECTURA/decisions/2026-10-04-numeros-de-hallazgo-duplicados.md` | NUEVO, este fichero | ver informe |
| `FINDINGS-RENUMERACIONES.md` | **NO MODIFICADO**, aunque D4 implica regenerarlo | `946219b4cd9a170c4cfe85a8210452c12c7d6e913560b6aa40364077d36f211f` |
| `docs/FINDINGS-INDEX.md` | **NO MODIFICADO** | `fc3793ee34115746e2e22f79faad9ed30088d0881b3637c3a829f979d8ed7f8c` |
| `/tmp/opencode/cnu-demo/discriminacion.json` | tabla de discriminación, sobre COPIA del árbol | ver informe |

`FINDINGS-RENUMERACIONES.md` sigue declarando `509` ficheros y por eso la puerta
sigue dando 5. **Regenerarlo es lo que hace salir el 5, y este nodo no lo hace**:
su contrato es `READ_ONLY` sobre el árbol, y una puerta que arregla lo que mide
no puede usarse para medir si lo que mide se reparó. La regeneración es una
acción de otro nodo, con su propia verificación, y la puerta está lista para
comprobarla: en cuanto el índice diga 540, el 5 desaparece y solo queda el 4.

`WORK_CLASS=READ_ONLY` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` ·
`RUNTIME=NOT_RUN` · `GPU INTACTA` — ninguna herramienta de este nodo toca hardware,
sysfs, registros, `dmesg` ni la GPU.