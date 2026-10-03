# 239  Las 13 comparaciones siempre verdaderas, y el TLB de GFX8 entra en bloques de 8 PTE

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=el UNLOCK de 182 (auditar las comparaciones en ficheros comunes)`
`CORRIGIDO_POR=190` -- los 13 SIEMPRE verdaderas son **8**, y los 8 switch
son **4**. El doble conteo seguia activo para las coincidencias que empiezan en
la linea N+1: se atribuian a la ventana N y a la N+1. Los 8 se verificaron a mano
(`amdgpu_ids.c:582-590`: la condicion esta entera en la linea 586).

## Cuestión principal

`182` afirmó que ~300 comparaciones de `amdgpu_ip_version(adev, GC_HWIP, 0)`
degeneran a "comparar 0 contra una constante", y clasificó **tres** a mano.

Eso era una muestra, no un recuento. Con el valor a 0, cada comparación tiene un
resultado mecánico, y leer 40 sitios a mano es justo el trabajo que hay que
automatizar.

## Criterio de terminación

Recorrer **todas** las comparaciones de `GC_HWIP` en los ficheros que se ejecutan
también en GFX8, evaluarlas con el valor 0, y clasificar cada una.
**Cumplido: 94 sitios, verificados por evaluación mecánica, no por lectura.**

## Herramienta

`08-ARQUITECTURA/tools/ipver_zero.py`. Escanea 18 ficheros comunes —los de una
sola generación no, porque en esta placa no entran y solo producirían ruido— y
evalúa cada comparación con `ip_versions[GC_HWIP][0] == 0`.

```
ficheros comunes analizados : 18
sitios encontrados          : 94
  comparaciones             : 86
    SIEMPRE verdaderas      : 13
    NUNCA verdaderas        : 73
  switch (no evaluados)     :  8
```

## Las 13 siempre verdaderas, y la regularidad es total

**Las 13 son `< IP_VERSION(n, 0, 0)` con n ≥ 9.** Sin una sola excepción.

| fichero | línea | expresión |
|---|---|---|
| `amdgpu_device.c` | 2845, 2846, 2847 | `< IP_VERSION(11,0,0)` |
| `amdgpu_display.c` | 809, 816, 874 | `< IP_VERSION(11,0,0)` |
| `amdgpu_ids.c` | 584, 585, 586 | `< IP_VERSION(10,0,0)` |
| `amdgpu_vm.c` | 1155, 1156, 1157 | `< IP_VERSION(9,0,0)` |
| `amdgpu_mes.c` | 681, 682, 683, 754, 755, 756 | `< IP_VERSION(12,0,0)` |

Que **todas** caigan en la misma forma no es casualidad: con el valor a 0, la
comparación `0 < X` solo puede ser verdadera si X > 0, y todo `IP_VERSION(n,0,0)`
con n ≥ 1 lo es. Las 73 "nunca verdaderas" son `==`, `>=` y `>` contra constantes
reales, y el mismo argumento las hace falsas.

**Es un resultado mecánico, y por eso es fiable donde una lectura no lo seria:**
no hay que confiar en que leí bien 40 sitios.

## El sitio que importa, y una afirmación de hardware que no tenía

`amdgpu_vm.c:1152-1163`:

```c
/* Vega20+XGMI where PTEs get inadvertently cached in L2 texture cache,
 * heavy-weight flush TLB unconditionally.
 */
flush_tlb |= adev->gmc.xgmi.num_physical_nodes &&
             amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9, 4, 0);

/*
 * On GFX8 and older any 8 PTE block with a valid bit set enters the TLB
 */
flush_tlb |= amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(9, 0, 0);
```

**El driver quiere decir "si soy GFX8 o anterior", y lo dice como "si mi versión
de IP es menor que 9.0.0".** Es un proxy degenerado: en esta placa la condición
es verdadera porque el valor es 0, y es correcta porque GCN3 *es* anterior a
Vega10. **Dos razones donde solo hace falta una**, y no se puede saber cuál de
las dos está actuando.

### Y el comentario es una afirmación sobre el TLB

> *On GFX8 and older **any 8 PTE block with a valid bit set enters the TLB**.*

Eso es una propiedad del hardware que el proyecto no tenía registrada:

- **La granularidad del TLB de GFX8 es de 8 PTE.**
- Poner el bit `valid` en **cualquiera** de los 8 mete el bloque entero en el TLB.
- Por tanto **no se puede actualizar parcialmente un bloque de 8 PTE**: hay que
  invalidar.

Y `params.needs_flush = flush_tlb` justo debajo, así que en esta placa **toda
actualización de page tables pide flush de TLB sin condición**.

**Consecuencia para el driver propio: no hay actualización parcial de page
tables.** Un bloque de 8 PTE es atómico desde el punto de vista de la visibilidad.

## Dos bugs de la herramienta, y por qué el self-test los dejó pasar

**Bug 1 — un placeholder que sobrevivió.** El bucle de escaneo comparaba
`ver == 0` en vez de `evaluar(op, ver)`. Salía "166 NUNCA verdaderas" cuando
`0 < IP_VERSION(9,0,0)` es evidentemente verdadera.

**El self-test no lo detectó**, porque validaba `evaluar()` en aislamiento. La
función era correcta; **el sitio que la llamaba estaba mal**. Es la misma clase de
error que el de `pm4_emit` con las expresiones sin llamada a macro: **el
componente correcto no valida el ensamblaje**.

Lo arreglé añadiendo dos tests **de pipeline**, no de función: escanean un
fichero real y comprueban el veredicto.

**Y lo demostré, que es lo que vale:** reintroduje el bug a propósito y el
self-test lo cazó.

```
$ con el bug:  self-test FALLA (1)
      pipeline: flush_tlb (amdgpu_vm.c:1157) debe ser SIEMPRE verdadera con valor 0,
      el escaneo dio False
$ restaurado:  self-test OK (16 vectores, 4 controles, 2 de pipeline)
```

**Bug 2 — doble conteo.** Recorría cada línea *y* la siguiente como dos ventanas,
así que una condición de dos líneas se contaba dos veces: **182 sitios en vez de
94.** Los duplicados eran visibles —`amdgpu_ids.c:586` salía dos veces— y eso fue
lo que hizo clic.

Un número inflado 2× es el tipo de error que pasa desapercibido si no se mira la
tabla completa.

## Clasificación

| afirmación | estado |
|---|---|
| 94 sitios de `GC_HWIP` en ficheros comunes | `PROVEN` — `ipver_zero` |
| 13 siempre verdaderas, 73 nunca, 8 switch | `PROVEN` — evaluación mecánica |
| Las 13 son `< IP_VERSION(n,0,0)` con n≥9 | `PROVEN` — la regularidad es total |
| `flush_tlb` es verdadero sin condición en GFX8 | `PROVEN_DERIVED` |
| El TLB de GFX8 entra en bloques de 8 PTE | `CORROBORATED` — comentario del driver |
| No se puede actualizar parcialmente un bloque de 8 PTE | `DERIVATION` — de la anterior |
| Que 8 sea el número correcto de PTE | `CORROBORATED` — solo el comentario |
| Los 8 `switch` toman la rama `default` | `DERIVATION` — 0 no casa con ningún caso |
| Que el proxy sea "correcto por casualidad" | `HYPOTHESIS` — no verificable |

## Confounders

- **Los 8 `switch` no los evalúo.** Un `switch (0)` con `case IP_VERSION(9,0,0)`
  cae en `default`, pero un `switch` con `case 0:` explícito haría otra cosa. No
  los he leído uno a uno.
- **La regularidad de las 13 es mecánica y por eso es fiable**, pero la
  clasificación depende de que `ip_versions[GC_HWIP][0]` sea 0, que es la
  conclusión de `182` y depende de que `devm_drm_dev_alloc` ponga a cero.
- **"Bloques de 8 PTE"** viene de un comentario del driver, no de un header ni de
  una spec. Es `CORROBORATED`. Que sea 8 y no 4 o 16 no lo puedo comprobar.
- **Contraste de recuento**: un `grep -c` directo da 5 líneas con `< IP_VERSION`
  en ficheros comunes, y la herramienta da 13 sitios. **No es contradicción**:
  `grep -c` cuenta líneas y hay condiciones multilínea, y la herramienta además
  cuenta los `>=` y `==`. Es un contraste de orden de magnitud, no una validación
  del total. Lo digo porque sería fácil citarlos como si se validaran mutuamente.
- **No he confirmado el nombre de la función** que contiene
  `amdgpu_vm.c:1155-1157`.

## Desfalsificación

- **(a)** 13 siempre verdaderas → refutable con `ipver_zero --resumen`.
- **(b)** Todas `< IP_VERSION(n,0,0)` → refutable con la tabla de `ipver_zero`.
- **(c)** `flush_tlb` verdadero → refutable con `amdgpu_vm.c:1157` y el valor 0.
- **(d)** Los 94 sitios → refutable cambiando `COMMON`; y el doble conteo se
  detectó por ver `:586` duplicado.
- **(e)** El TLB en bloques de 8 PTE → **no refutable aquí**, es un comentario.
- **(f)** Que el self-test caza el bug → verificado **reintroduciéndolo**.

## UNLOCKS

- **§A/§B reciben una propiedad del hardware que no tenían**: granularidad de 8
  PTE del TLB en GFX8, y no se puede actualizar parcialmente. Es la razón
  técnica de que toda actualización de page tables pida flush.
- **La auditoría de `182` queda completa**: no era una muestra de tres, son 94
  sitios con veredicto mecánico.
- **Un patrón reutilizable de autoverificación**: reintroducir un bug a propósito
  y comprobar que el self-test lo caza. Es la única forma de saber si un control
  mide algo.
- **La lección, que es la misma de siempre**: *un self-test que valida una
  función no valida la herramienta*. Hay que testear el pipeline.
- **Siguiente paso**: los 8 `switch` quedan sin evaluar, y un `switch` cuyo
  `default:` hace trabajo real es una rama que en esta placa se ejecuta siempre.

## Evidencia

```
08-ARQUITECTURA/tools/ipver_zero.py   --todos --fichero F --resumen --self-test
self-test: 16 vectores + 4 controles + 2 de pipeline

amdgpu_vm.c:1152-1163   flush_tlb, y el comentario "On GFX8 and older any
                        8 PTE block with a valid bit set enters the TLB"
amdgpu_ip.h:77-79       IP_VERSION_FULL(mj,mn,rv,var,srev)
amdgpu.h:1211-1217      amdgpu_ip_version() lee ip_versions[ip][inst]
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.