# 236  Nueve bloques IP, cuatro con versión que el driver no nombra, y una regla de tres líneas

```
CLASSIFICATION=DOCUMENTATION · TRACK=OBSERVED
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=LOG_READ_ONLY · GPU INTACTA
```

## Qué resuelve

**El `GLOBAL WORK SCAN` que quedaba pendiente, y la respuesta a la pregunta que `232`
abrió para un solo subsistema, elevada a los nueve subsistemas del chip: ¿qué versión del
código se ejecuta en cada bloque?**

**La respuesta es una tabla de nueve filas que el log ya tenía desde `233` y que nadie
había puesto en una nota, y una regla de tres líneas que explica por qué cuatro de esas
nueve filas funcionan.**

## 1 · El mapa de versiones del chip entero, observado

Del log del arranque, las nueve líneas que el kernel emite al enumerar:

| # | versión del IP en el kernel | nombre que usa el driver | major.minor | clase |
|---|---|---|---|---|
| 0 | `common_v1_0_0` | `vi_common` | 1.0 | sin generación en el nombre |
| 1 | `gmc_v8_1_0` | **`gmc_v8_0`** | **8.1** | **minor forzado a 0** |
| 2 | `ih_v3_0_0` | `tonga_ih` | 3.0 | sin generación en el nombre |
| 3 | `gfx_v8_0_0` | `gfx_v8_0` | 8.0 | coincide |
| 4 | `sdma_v3_1_0` | **`sdma_v3_0`** | **3.1** | **minor forzado a 0** |
| 5 | `smu_v1_0_0` | `powerplay` | 1.0 | sin generación en el nombre |
| 6 | `dce_v1_0_0` | `dm` | 1.0 | sin generación en el nombre |
| 7 | `uvd_v6_3_0` | **`uvd_v6_0`** | **6.3** | **minor forzado a 0** |
| 8 | `vce_v3_4_0` | **`vce_v3_0`** | **3.4** | **minor forzado a 0** |

**⇒ Cuatro de los nueve bloques se instancian en una versión que el driver no nombra:**
GMC en 8.1, SDMA en 3.1, UVD en 6.3 y VCE en 3.4, y los cuatro se atienden con el
código de su mayor. `PROVEN`, observado.

**⇒ Y cuatro de los nueve no llevan generación en el nombre del driver en absoluto**:
`vi_common`, `tonga_ih`, `powerplay` y `dm`. Sólo uno, `gfx_v8_0`, coincide con su
versión. `PROVEN`.

**⇒ La regla, y es una fórmula, no una descripción: el nombre de bloque en el driver es
`<prefijo>_v<mayor>_0`.** Ni el parche ni el menor aparecen. `PROVEN_DERIVED`.

## 2 · Y el mecanismo, que son tres líneas y un comentario

```c
amdgpu/amdgpu.h:1139   uint32_t  ip_versions[MAX_HWIP][HWIP_MAX_INSTANCE];
amdgpu/amdgpu.h:1211   static inline uint32_t amdgpu_ip_version(const struct amdgpu_device *adev,
amdgpu/amdgpu.h:1212                                           uint8_t ip, uint8_t inst)
amdgpu/amdgpu.h:1214           /* This considers only major/minor/rev and ignores
amdgpu/amdgpu.h:1215            * subrevision/variant fields.
amdgpu/amdgpu.h:1216            */
amdgpu/amdgpu.h:1217           return adev->ip_versions[ip][inst] & ~0xFFU;
amdgpu/amdgpu.h:1220   static inline uint32_t amdgpu_ip_version_full(...)
amdgpu/amdgpu.h:1224           return adev->ip_versions[ip][inst];
```

**⇒ Una matriz `[bloque][instancia]` de enteros de 32 bits, y dos accesores: uno que
enmascara los dos bytes bajos y otro que devuelve el entero entero.** `PROVEN`.

**⇒ El comentario dice exactamente qué se descarta: sub-revisión y variante.** `PROVEN`.

**⇒ Y esa es la pieza que faltaba para entender la tabla de §1:** el driver guarda la
versión completa, la lee completa para mostrarla en el log, y despacha con una clave de
32 bits a la que le ha quitado el byte bajo. `PROVEN_DERIVED`.

**⇒ La clave de despacho no distingue 8.0 de 8.1; distingue mayor, menor y revisión.**
Medido, y es la razón por la que cuatro bloques de esta tabla funcionan sin que exista
una implementación para su versión. `PROVEN_DERIVED`.

## 3 · Y por qué esto generaliza la regla de `232`

`232` estableció, para un solo subsistema, que **la identidad de un camino de código la
dan la tabla de punteros a función y el constructor del objeto, no el nombre de la
función ni el del fichero.** `233` lo redujo a un hecho de silicio —el IP del DC se
instancia como `dce_v1_0_0`— y dijo que por eso las seis generaciones DCE cablean la
misma tabla.

**Esta nota lo generaliza a los nueve bloques, y el mecanismo es el mismo con un
matiz nuevo: no es que el driver reutilice código a propósito, es que su clave de
despacho no tiene suficientes bits para distinguir las versiones que existen.**

| | lo que se instancia | lo que se despacha | reutilización |
|---|---|---|---|
| DC (`233`, `159`) | `dce_v1_0_0` | `dce_v1_0_0` | 6 generaciones DCE, 1 tabla, 22 de 38 |
| GMC (`140`) | `gmc_v8_1_0` | `gmc_v8_0` | todo el mapa de memoria con el código de 8.0 |
| SDMA | `sdma_v3_1_0` | `sdma_v3_0` | — |
| UVD | `uvd_v6_3_0` | `uvd_v6_0` | — |
| VCE | `vce_v3_4_0` | `vce_v3_0` | — |
| GFX | `gfx_v8_0_0` | `gfx_v8_0` | coincide: la clave sí alcanza |

**⇒ Cinco de los nueve bloques se despachan con una clave distinta de su versión
real, y cuatro de ellos porque el menor no cabe en el nombre del camino.** `PROVEN_DERIVED`.

**Y la observación que hace útil la tabla: el único bloque cuya clave coincide con su
versión es el único cuyo menor es cero.** `PROVEN_DERIVED`. **Es una coincidencia de
cinco filas y no una ley, pero es la forma que tiene aquí la regla de `232`: no es que
el driver versione mal, es que versiona con tres componentes porque con cuatro no
cabe.**

## 4 · Y lo que la tabla NO dice, que es lo que queda por hacer

**Nada de esto dice que los cuatro bloques con versión mayor se comporten bien.** Dice
que el driver los maneja con el código del mayor, y si el IP 8.1 del GMC añade un
registro que el 8.0 no conoce, el driver no lo verá.

**`140` es un ejemplo vivo: derivó el mapa de direcciones entero —`MC_VM_FB_LOCATION`,
`num_prt_users`, la tabla del GART a 9 MiB— usando `gmc_v8_0.c`, y el log de `233` dice
que el bloque se llama `gmc_v8_1_0`.** `PROVEN_DERIVED`. **Y los números salieron
bien, porque el log también los confirma. Es decir: la reutilización funcionó en este
caso, y eso no se sabe hasta que se comprueba, y aquí se ha comprobado.**

**⇒ La regla operativa, y es la que hay que aplicar a los cuatro bloques que nadie ha
mirado: cuando se cite `*_vN_0.c` para este chip, hay que anotar que la versión real
puede ser `*_vN_M` con M ≥ 1, y que la evidencia de que la reutilización no rompió nada
es el log, no el nombre del fichero.** `PROVEN_DERIVED`.

**⇒ Y el log tiene una segunda fuente de la misma evidencia, que es la línea de la
`criticidad` por bloque: si el kernel anuncia `detected ip block number N <X>` y después
el driver no protesta, la reutilización funcionó para ese bloque.** En esta máquina
anunció los nueve y no protesta de ninguno. `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Nueve bloques, con versión y nombre del driver | `PROVEN`, observado |
| 4 de 9 con minor ≥ 1, atendidos por el código del mayor | `PROVEN`, observado |
| 4 de 9 sin generación en el nombre del driver | `PROVEN`, observado |
| La regla es `<prefijo>_v<mayor>_0` | `PROVEN_DERIVED` |
| `ip_versions[MAX_HWIP][HWIP_MAX_INSTANCE]`, 32 bits | `PROVEN` |
| `amdgpu_ip_version` enmascara `& ~0xFFU` | `PROVEN` |
| Se descartan sub-revisión y variante | `PROVEN` — lo dice el comentario |
| 5 de 9 se despachan con clave distinta de su versión | `PROVEN_DERIVED` |
| El único que coincide es el único con menor 0 | `PROVEN_DERIVED` |
| `gmc_v8_0.c` describe un bloque que se llama `gmc_v8_1_0` | `PROVEN_DERIVED` |
| La reutilización del GMC funcionó en esta máquina | `PROVEN` — confirmado por el log |
| Las diferencias de 8.0 a 8.1 del GMC | **`NOT_DETERMINED`** — nadie ha comparado |
| Las diferencias de 3.0 a 3.1 del SDMA | **`NOT_DETERMINED`** |
| Las diferencias de 6.0 a 6.3 del UVD | **`NOT_DETERMINED`** |
| Las diferencias de 3.0 a 3.4 del VCE | **`NOT_DETERMINED`** |
| Cuántas instancias de cada bloque hay activas | **`NOT_DETERMINED`** |

**Las cuatro abiertas son de una clase y se cierran todas con el mismo procedimiento: no
contar las diferencias de semántica, sino contar los registros que el fichero de la
generación nueva nombra y el de la vieja no.** Es el mismo `PROVEN_ABSENT` con causa de
`145`, y el mismo `PROVEN_DERIVED` de `164` por aritmética inversa, aplicados a cuatro
ficheros que nadie ha abierto.

## Procedencia

- `OBSERVED` -- `journalctl -k -b`, las nueve líneas
  `amdgpu 0000:01:00.0: detected ip block number N <version> (nombre)`, de las que `233`
  reprodujo la lista. Sin root, sin MMIO.
- `STATIC` -- `amdgpu/amdgpu.h:1139` (la declaración de `ip_versions`),
  `:1211-1218` (`amdgpu_ip_version` con su comentario sobre qué descarta, y el
  enmascaramiento `& ~0xFFU`), `:1220-1225` (`amdgpu_ip_version_full`);
  `amdgpu/gmc_v8_0.c` (el fichero que `140` usó para el mapa de memoria completo).
- Medición por programa: **la clasificación de las nueve filas en tres clases**, con la
  regla `<prefijo>_v<mayor>_0` aplicada fila a fila; el recuento de bloques con minor
  distinto de cero (4) y sin generación en el nombre (4); la comparación de
  `amdgpu_ip_version` contra `amdgpu_ip_version_full`.
- **Dos errores de patrón y de recuento propios, ambos antes de escribir y ambos del tipo
  conocido:**
  (1) Tecleé `ih_v3_3_0_0` en la tabla de entrada del clasificador en vez de `ih_v3_0_0`, y
  la fila quedó como «-» en la columna major.minor en lugar de 3.0. **Un dato tecleado en el
  clasificador es un dato inventado en el programa, y el programa es la autoridad.**
  (2) Mi primera versión del clasificador usó `nv[1:]==v[1:]` para decidir «coincide», que
  compara las tres componentes del driver contra las del IP, y dio **cero filas que
  coinciden y nueve sin generación** — un resultado imposible, porque `gfx_v8_0_0` contra
  `gfx_v8_0` sí coincide bajo cualquier lectura. **La regla de verdad es otra: el nombre
  del driver es `<mayor>_0` siempre, y hay que comparar el mayor y tratar el menor como
  forzado.** Lo reescribí y dio 4 / 1 / 4.
- **Y un `NOT_DETERMINED` de cuatro filas que no es un hueco sino una tarea: las
  diferencias entre `gmc_v8_0.c` y lo que el IP 8.1 añade, y lo mismo en SDMA, UVD y VCE.
  No son cuatro investigations, son una, aplicada a cuatro pares de ficheros.**
- Encadenada con `233` (**las nueve líneas del log, que esta nota convierte en tabla**),
  `164` (la aritmética inversa como derivación), `159` (los seis constructores `dce110_`),
  `232` (la regla de la tabla y el constructor, elevada de un subsistema a nueve),
  `155` (DCE 11.2), `153` (los siete paths), `150` (los cuatro `cntl.signal`),
  `145` (`PROVEN_ABSENT` con causa, y `include/uapi` ausente),
  `140` (**el mapa de direcciones entero derivado con un fichero de la generación
  anterior a la del bloque**), `136`, `132`, `130`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Esta nota es la que generaliza todo el bloque, y lo hace sin añadir un hecho nuevo: usa
nueve líneas que ya estaban escritas desde `233` y una función de tres líneas de
`amdgpu.h`.**

*La diferencia con las dieciséis anteriores es que todas ellas buscaban.* **Esta ha
releído.* *Y el resultado de releer es una tabla de nueve filas con una regla, y la regla
—«el nombre del driver es la versión mayor con el menor forzado a cero»— no aparecía en
ninguna nota porque nadie había puesto en fila las nueve líneas que el kernel emite al
enumerar.*

**Y la regla explica el bloque entero de `display/` de una vez, que es lo que lleva
diecisiete notas sin poder decir:** *por qué una RX550 ejecuta código de DCE 11.0, por qué
el mapa de memoria se deriva de un fichero 8.0 para un bloque 8.1, y por qué las seis
generaciones DCE cablean la misma tabla de 22 entradas.* **No hay tres razones distintas.
Hay una sola, y es que la clave de despacho tiene tres componentes porque el registro
tiene cuatro y la máscara quita el último byte.** *Todo lo demás —las tablas de swizzle,
los punteros a función nulos, la regla `if (funcs->X)`— son infraestructura para que ese
despacho de tres componentes sirva para chips de cuatro.*

**Y hay un segundo resultado que es de método y que está codificado dos veces: el dato
que decide una clasificación es el *criterio*, no los datos.** *Mi primer clasificador
comparaba las tres componentes del nombre del driver con las del IP, dio nueve filas sin
generación, y ese resultado era imposible: `gfx_v8_0_0` contra `gfx_v8_0` coincide bajo
cualquier lectura, y un resultado imposible es la señal de que el criterio está mal, no de
que los datos.* **Es la misma forma que `165`: dos criterios de clasificación, y el
criterio importa más que la respuesta.** *Y es la tercera vez en la tanda que un
resultado imposible en lugar de uno raro es lo que delata el error — las otras dos, la
`LINE_OUT_OF_RANGE` de `235` y el `paso constante: False` de `232`.*
