# 170 · Ninguna de las cuatro versiones tiene código propio: no hay nada que reutilizar

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**Las cuatro `NOT_DETERMINED` que dejó `169`, cerradas en un paso, y no midiendo lo que
`169` proponía.** Se iba a contar qué registros nombra el fichero de la generación nueva
y no el de la vieja; resulta que **el fichero de la generación nueva no existe**, y por
tanto no hay nada que comparar.

**⇒ `gmc_v8_1.c`, `sdma_v3_1.c`, `uvd_v6_3.c` y `vce_v3_4.c` no están en el árbol.** `PROVEN_ABSENT`.

**⇒ El driver no está reutilizando código por comodidad ni por una clave de despacho
demasiado corta: está usando la única implementación que existe.** `PROVEN_DERIVED`.

## 1 · Los cuatro casos, uno a uno

| bloque | IP real | implementación usada | ¿existe la propia? | menores que sí existen en ese mayor | veredicto |
|---|---|---|---|---|---|
| GMC | `v8.1` | `gmc_v8_0` | **no** | v8.0 | reutilización sin alternativa |
| SDMA | `v3.1` | `sdma_v3_0` | **no** | v3.0 | reutilización sin alternativa |
| UVD | `v6.3` | `uvd_v6_0` | **no** | v6.0 | reutilización sin alternativa |
| VCE | `v3.4` | `vce_v3_0` | **no** | v3.0 | reutilización sin alternativa |

**Y el inventario completo de cada bloque, que es lo que da contexto:**

```
gmc   -> v6.0  v7.0  v8.0  v9.0  v10.0  v11.0  v12.0  v12.1
sdma  -> v2.4  v3.0  v4.0  v4.4  v5.0  v5.2  v6.0  v7.0  v7.1
uvd   -> v3.1  v4.2  v5.0  v6.0  v7.0
vce   -> v1.0  v2.0  v3.0  v4.0
gfx   -> v6.0  v7.0  v8.0  v9.0  v9.4  v10.0  v11.0  v12.0  v12.1
```

**⇒ El salto mayor de menor entre dos implementaciones que existen es el de VCE, de 3.0
a 4.0, y el de UVD, de 4.2 a 5.0.** En ninguna serie de bloques de esta lista hay dos
implementaciones consecutivas con el mismo mayor y distinto menor, **salvo el caso
`gfx_v9_4` y `gmc_v12_1`, que sí existen como fichero propio.** `PROVEN_DERIVED`.

**⇒ Y ese es el contraejemplo que importa: cuando un menor necesitó código propio, lo
tuvo.** `gmc_v12_1.c` y `gfx_v9_4.c` existen, y `gfx_v12_1.c` también. `PROVEN_DERIVED`.

## 2 · Y la regla, que no era la que `169` decía

`169` afirmó que la regla era «el nombre del driver es `<prefijo>_v<mayor>_0`». **Medido
sobre los 121 ficheros de versión de `amdgpu/`, esa regla es falsa como regla y cierta
como tendencia:**

| | ficheros |
|---|---|
| con menor `0` en el nombre | **74** |
| con menor distinto de `0` | **47** |
| total de versiones nombradas como fichero | **121** |

**⇒ 47 de 121 llevan un menor distinto de cero.** `PROVEN`. Ejemplos: `gmc_v12_1.c`,
`gfx_v9_4.c`, `sdma_v7_1.c`, `sdma_v5_2.c`, `sdma_v4_4.c`, `uvd_v3_1.c`, `uvd_v4_2.c`,
`ih_v6_1.c`, `umc_v8_14.c`, `nbio_v7_11.c`, `mes_v12_1.c`, `gfxhub_v12_1.c`.

**⇒ La regla real, y es la forma honesta de `156`:**

> **amdgpu nombra un fichero después de la versión que necesitó código propio, y reutiliza
> cuando una versión nueva no lo necesitó.**

**No es una convención de nombres ni una limitación de la clave de despacho: es un hecho
sobre qué versiones existen como código.** `PROVEN_DERIVED`.

**⇒ Y esto corrige la explicación que `169` dio del caso del DC.** `169` dijo que las seis
generaciones DCE cablean la misma tabla «porque la clave de despacho tiene tres
componentes». **Eso explica por qué el DC 11.2 no tiene su propia tabla, pero no explica
por qué `gmc_v8_1` no tiene su propio fichero — y la respuesta es distinta: no hay
`dce_11_2` como fichero, del mismo modo que no hay `gmc_v8_1`.** `PROVEN_DERIVED`.

**⇒ Las dos razones son distintas y ambas certain, y `169` las confundió:**
- **El DC**: la clave de despacho del DC es la versión del IP, `1.0.0`, común a toda la
  familia, así que un 11.2 no puede tener su propia ruta aunque quisiera.
- **Los otros cuatro**: la versión del IP cambió (`8.1`, `3.1`, `6.3`, `3.4`) y aun así no
  hay fichero, porque **el cambio no necesitó código propio**.

**Un caso es «la versión no distingue» y el otro es «la versión no ha cambiado lo
suficiente», y ninguno de los dos es un fallo del driver.** `PROVEN_DERIVED`.

## 3 · Y por qué esto importa para un driver propio

**La pregunta «¿qué parte de este driver tengo que reescribir para otra GPU?» tiene ahora
una respuesta que no es un porcentaje sino un inventario: se listan las versiones que
tienen fichero, y se sabe que las que no lo tienen no lo necesitan.**

| | |
|---|---|
| versiones con fichero propio | **121** |
| versiones de IP de esta máquina sin fichero propio | **4 de 9 bloques** |
| bloques cuya versión de IP no aparece en su nombre | **4 de 9** (`vi_common`, `tonga_ih`, `powerplay`, `dm`) |

**⇒ Para una GPU nueva, el trabajo es: para cada bloque, ver si su versión de IP está en
la lista de 121.** Si está, ese fichero hay que reescribirlo. Si no está, no hay nada que
reescribir, porque la generación anterior cubre el caso. **Y para esta máquina, cinco de
sus nueve bloques están en el segundo caso.** `PROVEN_DERIVED`.

**⇒ Que el clave de despacho del DC sea `1.0.0` para toda la familia es lo que hace que
el trabajo de display sea 52 funciones (`159`) en vez de 252.** Y que el DC no tenga
fichero `dce_11_2` es lo que hace que su tabla de swizzle tenga 91 de 130 campos y no
130. `PROVEN_DERIVED`.

## 4 · Y el caso del GMC, que es el que tiene evidencia independiente

`140` derivó el mapa de direcciones completo —`MC_VM_FB_LOCATION`, el hueco de 42 GiB,
`num_prt_users` 65536, la tabla del GART a 9 MiB— **usando `gmc_v8_0.c`, que es la
implementación del 8.0, para un bloque que se llama 8.1.** `PROVEN_DERIVED`.

**Y `163` confirmó los cuatro números con el log, y `164` añadió el quinto por
aritmética inversa.** `PROVEN`.

**⇒ Es el único caso del bloque entero en que la reutilización está comprobada de las dos
formas: por derivación en el código y por observación en el log.** `PROVEN_DERIVED`.

**⇒ Y los otros tres —SDMA, UVD, VCE— no tienen esa comprobación, pero se sigue sin
poder necesitar.** La evidencia que los cubriría es la misma que la del GMC: que el
kernel anuncie el bloque y el driver no proteste. Y en esta máquina anunciar los cuatro y
no protestar de ninguno es lo que hace el log de `163`. `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `gmc_v8_1.c`, `sdma_v3_1.c`, `uvd_v6_3.c`, `vce_v3_4.c` no existen | `PROVEN_ABSENT` |
| Los cuatro usan la única implementación que existe | `PROVEN_DERIVED` |
| El inventario de versiones de cada uno de los cinco bloques | `PROVEN` |
| 74 con menor 0 y 47 con menor distinto, de 121 | `PROVEN` |
| La regla es «fichero tras la versión que necesitó código» | `PROVEN_DERIVED` |
| `gfx_v9_4.c`, `gmc_v12_1.c` existen: el contraejemplo | `PROVEN_DERIVED` |
| `169`: la clave de tres componentes explica el DC | `CORREGIDO` — es una de dos razones |
| `140` acertó usando el fichero del 8.0 para un bloque 8.1 | `PROVEN` — derivado y observado |
| Si el 8.1 del GMC añadió algún registro que el 8.0 no usa | **`NOT_DETERMINED`** |
| Si el 3.4 del VCE añadió algún campo | **`NOT_DETERMINED`** |
| Si el log del arranque de otra placa delataría un bloque reutilizado mal | **`NOT_DETERMINED`** |
| Cuántas instancias de cada bloque hay activas | **`NOT_DETERMINED`** |

**Las tres primeras abiertas ya no son «qué diferencias hay», que era la pregunta
equivocada: ahora son «¿el firmware de otra placa podría pedir un campo que la
implementación reutilizada no escribe?», y eso es un `RREG32` o un caso de campo
reclamado.** Son nivel 4, y son la frontera correcta del bloque.

## Procedencia

- `STATIC` -- el inventario de `amdgpu/`: los 304 ficheros `.c` del directorio, de los
  cuales 121 casan con `^(\w+)_v(\d+)_(\d+)\.c$` y se agrupan por prefijo y por
  (mayor, menor); la existencia o no de los cuatro ficheros concretos
  `gmc_v8_1.c`, `sdma_v3_1.c`, `uvd_v6_3.c`, `vce_v3_4.c`, comprobada con `os.path.exists`;
  `amdgpu/gmc_v8_0.c` (el fichero que `140` usó, y que es la única implementación del 8.x
  del GMC); `amdgpu/amdgpu.h:1139` `:1211-1225` (la matriz de versiones y los dos
  accesores, de `169`).
- Medición por programa: **los cuatro casos, con su veredicto impreso uno a uno**; el
  inventario de los cinco bloques; **el reparto 74 / 47 / 121**; y la comprobación de que
  `gfx_v9_4.c`, `gmc_v12_1.c` y `gfx_v12_1.c` sí existen, que es el contraejemplo que
  convierte la regla en regla y no en convención.
- **Dos errores de script propios, ambos de formato y ambos antes de escribir:** (1) usé
  `"%d.%d"%s` sobre un generador que cedía un entero en vez de una tupla, y `TypeError`;
  (2) el mismo error en la lista de menores. **Los dos son la misma causa: un programa que
  formatea necesita que el dato tenga la forma que el formato espera, y si no la tiene el
  programa se cae en vez de avisar.** *Es la versión de código de la regla (c) de la
  tanda: un número que decide una conclusión tiene que imprimirlo un programa, y un
  programa que se cae no ha impreso nada.*
- **Y una corrección de `169` que es de fondo y no de cifra: `169` dio una sola razón para
  un caso que tiene dos, y esta nota las separa.** El DC no tiene fichero propio porque
  su clave de despacho es común a la familia; GMC, SDMA, UVD y VCE no lo tienen porque su
  IP cambió sin que el cambio necesitara código. **La primera razón es de diseño del
  despacho y la segunda es un hecho sobre el árbol, y confundirlas hace que la segunda
  parezca una limitación de la primera.**
- Encadenada con `169` (**las cuatro `NOT_DETERMINED` de esta nota, y su explicación
  corregida**), `163` (**el log que anuncia los nueve bloques y no protesta de ninguno**),
  `164` (la aritmética inversa que confirmó el mapa del GMC), `156` (la regla de la tabla
  y el constructor, en su forma honesta), `159` (52 funciones propias de DCE 11.2 y el
  21% del coste de una generación), `155` (DCE 11.2 y la lista de 91 de 130),
  `153` (los siete paths), `150` (los cuatro `cntl.signal`), `145` (`PROVEN_ABSENT` con
  causa, y el hueco de la uAPI), `140` (**el mapa entero derivado con un fichero de la
  generación anterior**), `136`, `132`, `130`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Las cuatro `NOT_DETERMINED` de `169` se cerraron sin hacer lo que `169` decía, y el
descubrimiento es que la pregunta estaba mal planteada en su segunda mitad.**

*`169` propuso: «contar los registros que el fichero de la generación nueva nombra y el
de la vieja no».* **Ese recuento es imposible si el fichero de la generación nueva no
existe, y no existe.** *Y el paso que faltaba no era una medición sino una comprobación
previa de existencia, que es más barata que cualquier medición y que se hace en una
línea.* **La regla es la que ya estaba en la lista desde el principio de la tanda bajo la
forma de "cuestiones de suposición": antes de medir una diferencia, comprobar que hay dos
cosas que comparar.**

**Y el resultado segundo es más valioso que el cierre: la regla que `169`fatigaba —«el
nombre es `<mayor>_0`»— es falsa como regla.** *47 de 121 ficheros llevan un menor
distinto de cero, y entre ellos `gmc_v12_1.c` y `gfx_v9_4.c`, que existen precisamente
porque ese menor necesitó código propio.* **La regla real es «se nombra un fichero
después de la versión que necesitó código», y eso no es una convención de nombres sino
un inventario: hay 121 versiones en el árbol, se cuentan, y ese es el número que un
driver propio necesita.**

**Y la corrección de fondo es de método y es la más útil de la tanda:** *`169` dio una
sola razón para un caso que tiene dos, y una de las dos no era una razón sino una
coincidencia de forma.* **El DC no tiene fichero propio porque su clave de despacho es
`1.0.0` para toda la familia — eso es diseño. GMC, SDMA, UVD y VCE no lo tienen porque
su versión de IP cambió y el cambio no necesitó código — eso es un hecho del árbol.**
**Y confundirlas hace que la segunda parezca una limitación de la primera, que es una
conclusión mucho más fuerte y mucho más difícil de refutar. Cuando dos cosas tienen
causas distintas, decir una de ellas es un error aunque la que digas sea cierta.**
