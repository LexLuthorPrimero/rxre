# 1022 · T13 y T14 medían un SIGPIPE, no un símbolo: la comprobación se apagaba sola y la suite seguía en verde

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC` · `CORPUS=RESEARCH/kernelbuild/linux-7.1.3`
`WORK_CLASS=REPAIR/CONTROLLED` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=2`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## Qué se midió, y por qué se midió esto

Al meter `rx550_pdb0.o` en `rx550_drv-objs` —la capa de page tables, que hasta
entonces compilaba pero no entraba al módulo— el recuento de la auditoría
estática bajó:

```
.ko de 3 objetos:  resumen estático: 34 PASS, 0 FAIL
.ko de 4 objetos:  resumen estático: 32 PASS, 0 FAIL
```

Bajó, y **`fail` siguió en 0**. Eso ya es un defecto: dos comprobaciones
desaparecieron sin convertirse en fallos. Pero lo importante es por qué.

Las dos que desaparecieron son T13 (*init_module presente en el .ko*) y T14
(*cleanup_module presente en el .ko*). Las dos se escribieron así:

```sh
nm "$KO" 2>/dev/null | grep -q "__pfx_init_module\|init_module" && \
chk 0 T13 "init_module presente en el .ko"
```

## La causa

**Ese pipeline no mide si el símbolo está en el `.ko`.** Mide si el símbolo
aparece antes de que se vacíe el búfer de salida de `nm`, y con eso si `grep -q`
le manda `SIGPIPE` a `nm` antes de que `nm` termine.

`nm` escribe por tubería con búfer **completo** de 4096 B. Si la salida cabe en
4096, `nm` hace una sola escritura al salir y no hay `SIGPIPE` posible. Si no
cabe, `nm` escribe 4096 y el resto al salir; si `grep -q` encuentra la
coincidencia dentro de esos primeros 4096 y sale, la segunda escritura recibe
`SIGPIPE`.

Medido con el mismo binario y el mismo patrón:

| `.ko` | salida de `nm` | estado del pipe | T13/T14 |
|---|---|---|---|
| 3 objetos, 641208 B | **3945 B** | **0** | PASS |
| 4 objetos, 663832 B | **5216 B** | **141** | no se ejecutan |

Y `cleanup_module` aparece en la **línea 1** de la salida de `nm`, porque
`.exit.text` va antes que `.text`. Los símbolos `RES` que pasaban están al final
de esa misma salida. Por eso unas comprobaciones funcionaban y otras no: dependía
de la *posición* del símbolo, no de si estaba.

## Por qué el fallo era silencioso, y por qué eso es lo grave

`chk` sólo se llama si el `&&` se cumple. Con el pipe en 141:

- `chk` no se llama
- ni `pass` ni `fail` se incrementan
- el resumen sale con **0 FAIL**
- y `test_static.sh` imprime su línea de éxito: `T1-T14 + auditorías: OK`

Una comprobacion que se desactiva sola y sigue pareciendo conforme es peor que
una que falla. La que falla se ve; la que se apaga deja el hueco y avisa de que
todo está bien.

## Demostración, con el mismo input en las dos versiones

Copia del árbol en `/tmp`, símbolo sustituido por uno que **no existe** en el
`.ko`:

```
patrón VIEJO:  nm "$KO" | grep -q simbolo_inexistente && chk 0 T14 ...
               (no imprime linea T14)
               resumen estático: 33 PASS, 0 FAIL
               T1-T14 + auditorías: OK

patrón NUEVO:  grep -q simbolo_inexistente "$SYMS"; must $? T14 ...
               FAIL  T14  cleanup_module presente en el .ko (module_exit)
               resumen estático: 33 PASS, 1 FAIL
               (sin linea de éxito)
```

Mismo `.ko`, mismo símbolo inexistente, misma ejecución: el patrón viejo reporta
un falso verde de 34 comprobaciones, el nuevo reporta el fallo.

## El arreglo, en dos partes, porque una sola no basta

**1. `nm` se resuelve una vez a un fichero y se busca en el fichero.** El pipe
desaparece del camino de decisión. Se resolvió por separado con `nm -a`, que
**no** es lo mismo que `nm` y cuya salida tiene otra forma: sustituirlo por el
fichero del `nm` normal habría sido cambiar la comprobación sin querer.

**2. `must()` es el único camino para comprobar algo, y `&& chk` desaparece.**
`&& chk` es exactamente la construcción que permite que una comprobación no se
ejecute. Existía en cinco sitios del fichero; los que tocaban `nm` se
convirtieron, y los que leen ficheros con `grep` sobre disco no tienen el
problema porque no hay tubería en el medio.

## Estado después, en los dos tamaños

```
.ko de 3 objetos:  34 PASS, 0 FAIL, con T13 y T14 presentes
.ko de 4 objetos:  34 PASS, 0 FAIL, con T13 y T14 presentes
```

El conteo ya no depende del tamaño del `.ko`. Eso es la propiedad que importa: el
número de comprobaciones ejecutadas es ahora una constante del script, no una
función del binario.

## Lo que además cambió, y por qué

`rx550_pdb0.o` entra en `rx550_drv-objs`. Motivo y alcance exactos:

- **Lo que se midió**: el enlace. `rx550_pdb0.c` compila bajo las opciones reales
  de kbuild (no bajo las de un `gcc` cualquiera), y el `.ko` enlaza, genera BTF y
  pasa la auditoría estática. Estado `NOT_DETERMINED → OBSERVED`.
- **Lo que NO se afirma**: que la capa esté usada. `rx550_pdb0.c` expone 16
  funciones (`rx550_pdb0_init`, `_alloc`, `_open`, `_map_va`, `_lookup`,
  `_unmap_index`, `_destroy`, `_encode`, `_entry_valid`, `_entry_addr`,
  `_index_in_range`, `_index_for_va`, `_tables_for`, …) y, MEDIDO sobre el árbol,
  **cero llamadas** fuera de su propio `test_pdb0`. Entrar en el binario no es lo
  mismo que estar en el camino de `probe()`.

`probe()` sigue siendo lo que se lee en `rx550_target.c:125-278`: matching de
cinco campos, `kzalloc`, descubrir BARs, adquirir BAR5, `pci_iomap`, `rx550_mmio_attach`,
`pci_set_drvdata`, y una sonda opt-in de `mmGRBM_STATUS2`. No hay GPUVM, ni GART,
ni VMID, ni fence, ni submission. Eso es otra frontera y tiene su propia medida.

La diferencia observable del `.ko`: 641208 → 663832 bytes, y 28 símbolos con
`pdb0` en el nombre. Definidos: 0 sin resolver nuevos (`nm -u` sigue con 18, los
mismos 18 del kernel).

## Lo que este hallazgo no dice

- No dice que la capa de page tables funcione. Dice que **enlaza**. Su corrección
  funcional la miden `test_pdb0` (75), `test_vmid1_pgt` (610) y
  `test_vmid1_pgt_backing` (1238), que son modelos de software, no hardware.
- No dice que el `.ko` se pueda cargar. No se intentó: `amdgpu` posee el
  dispositivo (`-EBUSY` es el resultado esperado de `target_res_claim_regions`),
  y tomar la GPU es una decisión con precondiciones propias (§90), no un efecto
  secundario de una repairs de script.
- No dice que la auditoría estática sea suficiente. Dice que una parte de ella
  estaba midiendo otra cosa, y que ahora mide lo que dice.

## La lección, que es la misma de tres veces

`exit 0 ≠ resultado válido`, pero hay una forma mas breve: **una
comprobación que se salta a sí misma y no incrementa ningún contador**. El
resumen seguirá diciendo «34 PASS, 0 FAIL» y nadie lo mirará, porque los dos
números que la gente lee son exactamente los que no se enteran.

La regla que sale de aquí y que ya estaba escrita en el proyecto
(`08-ARQUITECTURA/tools/toolkit.py`, §28) es que una comprobación debe tener un
camino de ejecución que no dependa de que otro comando termine bien. Por eso
`must()` existe, y por eso `&& chk` no.

## Trazabilidad

- Fichero reparado: `04-IMPLEMENTACION/rx550-driver/tests/test_static.sh`
- Medida que lo disparó: `tools/tu_compila.sh` + enlace con `rx550_pdb0.o`
- Verificación de contratos tras el cambio: `tools/contratos.sh`, 17 invocadas,
  0 problemas
- Discriminante de la geometría: finding 1021
- Prefijo de numeración: 1022, reservado antes de escribir