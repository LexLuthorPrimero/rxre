# 104 · §C: `VM_INVALIDATE_REQUEST` y `RESPONSE` son 16 bits cada uno, con layout idéntico

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`103` cerró que la lectura existe pero **no qué devuelve**. Esto dice qué
devuelve: **un acuse por dominio, de 16 bits, que el driver descarta**.

## Los dos registros

```
gmc_8_1_d.h:615   #define mmVM_INVALIDATE_REQUEST    0x51e
gmc_8_1_d.h:616   #define mmVM_INVALIDATE_RESPONSE   0x51f
```

Y en `gmc_8_2_d.h`, los mismos dos valores. **Son dos registros distintos,
adyacentes**, con layouts de bits idénticos:

| bit | REQUEST (write) | máscara | RESPONSE (read) | máscara |
|---|---|---|---|---|
| 0 | `INVALIDATE_DOMAIN_0` | `0x1` | `DOMAIN_INVALIDATED_0` | `0x1` |
| 1 | `INVALIDATE_DOMAIN_1` | `0x2` | `DOMAIN_INVALIDATED_1` | `0x2` |
| … | … | … | … | … |
| 15 | `INVALIDATE_DOMAIN_15` | `0x8000` | `DOMAIN_INVALIDATED_15` | `0x8000` |

**16 de 16 con máscara idéntica**, y la unión ocupa `0xffff`: 16 bits contiguos
desde el 0, sin huecos.

**Es una pareja petición/acuse con granularidad de dominio.** Escribes qué
dominios quieres invalidar; el hardware responde qué invalidó.

## Y el driver no mira la respuesta

```
gmc_v8_0.c:640   WREG32(mmVM_INVALIDATE_REQUEST, mask);
gmc_v8_0.c:641   RREG32(mmVM_INVALIDATE_RESPONSE);
```

`RREG32` como expresión de sentencia. **El valor se descarta.** No hay `if`, no
hay máscara, no hay comparación con lo que se pidió.

Verificado que no hay ningún consumidor del valor: los dos `RREG32` del driver son
sentencias sueltas y no hay ninguna otra lectura de `mmVM_INVALIDATE_RESPONSE`
en todo el árbol.

**Eso no significa que el valor no sirva.** Significa que **amdgpu no lo
comprueba**, y eso es una decisión de diseño que un driver propio puede no
copiar.

## Es una convención de todas las generaciones, no de GFX8

```
gmc_6_0_sh_mask.h    16 campos RESPONSE
gmc_7_0_sh_mask.h    16 campos RESPONSE
gmc_8_1_sh_mask.h    16 campos RESPONSE
gmc_8_2_sh_mask.h    16 campos RESPONSE
```

**Los cuatro headers de GMC que tengo traen los mismos 16.** El acuse por
dominio lleva desde GFX6. No es una rareza de esta generación, es la interfaz
del hardware para invalidación, y un driver propio la hereda entera.

## Y el vecindario lo hace más interesante: PRT está a 12 bytes

```
0x506-0x50d   VM_CONTEXT0..7_PAGE_TABLE_BASE_ADDR
0x50e-0x515   VM_CONTEXT8..15_PAGE_TABLE_BASE_ADDR
0x51e         VM_INVALIDATE_REQUEST
0x51f         VM_INVALIDATE_RESPONSE
0x52c-0x52f   VM_PRT_APERTURE0..3_LOW_ADDR
```

**`VM_PRT_APERTURE0..3_LOW_ADDR` está 13 bytes después de RESPONSE**, y es lo que
escribe `gmc_v8_0_set_prt` (`gmc_v8_0.c:798-800`).

Conecta con `099`: la invalidación y el PRT —que **desactiva siete mecanismos de
error** incluyendo `MASK_PDE0_FAULT`— están en la misma página de registros, a
13 bytes de distancia.

**Para un driver propio: invalidación y PRT no son subsistemas separados.** Viven
juntos en el mismo bloque de VM, y lo que PRT hace es exactamente lo contrario
que RESPONSE: uno silencia errores, el otro los acusa. Entender el uno sin el
otro es leer la mitad.

## Y el CONTEXT0-7 / CONTEXT8-15 explica el salto de `064`

`064` vio siete registros con offset distinto en dos rangos, sin saber por qué.
La respuesta está en `gmc_v8_0.c:673-676`:

```
gmc_v8_0.c:673   if (vmid < 8)
gmc_v8_0.c:674       reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
gmc_v8_0.c:675   else
gmc_v8_0.c:676       reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
```

**Los PTBA están partidos en dos bloques de ocho**: `CONTEXT0-7` a partir de
`0x506`, y `CONTEXT8-15` a partir de `0x50e`. No es arbitrario ni un bug: es
que el espacio de registro se organiza en bloques, y el código tiene que
saltar entre ellos.

**Y explica `102`/`103` por qué `emit_flush_gpu_tlb` reescribe el PTBA antes de
invalidar**: son dos registros del mismo bloque, a 24 bytes de distancia, y se
escriben seguidos en el ring.

## El error que casi publico

Mi primera lectura de los offsets fue:

```
615:#define mmVM_INVALIDATE_REQUEST    0x51
616:#define mmVM_INVALIDATE_RESPONSE   0x51
```

Y saqué la conclusión: *"son el mismo registro con dos nombres semánticos"*.

**Es falso.** Los valores son `0x51e` y `0x51f`. Lo que pasó es que mi comando
**truncó la línea a 88 columnas y se comió el último carácter**, así que leí
`0x51` dos veces, coincidían, y construí encima una interpretación entera.

**Un resultado que coincide con lo que yo esperaba, obtenido de una salida
truncada, es el peor tipo de resultado.** Y lo peligroso es que era
plausible: "un registro, dos nombres" suena a diseño ingenioso, y casi lo
publico.

Lo que lo cazó fue volver a pedir el campo **sin `cut`**, y ver el dígito que
faltaba.

**Ésta es la segunda vez hoy que un `cut` mal puesto me da un dato falso**, y las
dos veces el número "falso" era más sencillo que el real — que es exactamente la
forma en que un error pasa inadvertido.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| Son dos registros distintos, `0x51e` y `0x51f` | `PROVEN` (`gmc_8_1_d.h:615-616`) |
| Cada uno tiene 16 bits con máscaras idénticas | `PROVEN` (16/16) |
| Los bits son `INVALIDATE_DOMAIN_N` / `DOMAIN_INVALIDATED_N` | `PROVEN` |
| El layout es el mismo desde GFX6 | `PROVEN` (4 headers) |
| El driver descarta el valor de la respuesta | `PROVEN` (sentencia suelta) |
| PRT está 13 bytes después | `PROVEN` (`0x51f` → `0x52c`) |
| Los PTBA van en dos bloques de 8 | `PROVEN_DERIVED` (`gmc_v8_0.c:673-676`) |
| **Si el hardware pone todos los bits que se piden** | **`NOT_DETERMINED`** |
| Si un bit se queda a 0 significa fallo o "no aplicable" | `NOT_DETERMINED` |
| Cuánto tarda el hardware en llenar los bits | `NOT_DETERMINED` |
| Si la lectura fuerza completión o sólo informa | `NOT_DETERMINED` |

**Las dos primeras `NOT_DETERMINED` son el nudo que queda, y son
`software behaviour ≠ hardware semantics` en estado puro.**

El driver escribe 16 bits posibles y no comprueba ninguno. **Eso sólo es
defensible si el hardware garantiza que todos los bits pedidos se ponds.** No lo
comprueba porque confía en ello, o porque leerlos no le serviría, o porque el
coste de comprobar en el camino caliente no compensa.

**Un driver propio tiene que elegir, y las tres opciones son defendibles:**
comprobar los bits y reintentar, comprobar y avisar, o no comprobar como
amdgpu. Lo que no se puede es no elegir: el registro existe y devuelve algo.

## Procedencia

- `STATIC` — `gmc_8_1_d.h:615-616`, `gmc_8_2_d.h` (mismos valores),
  `gmc_8_1_sh_mask.h` (16 campos REQUEST y 16 RESPONSE), `gmc_6_0_sh_mask.h` y
  `gmc_7_0_sh_mask.h` (conteo), `gmc_v8_0.c:625-683` y `:673-680` y `:798-800`.
- Sin `RUNTIME`. Sin escrituras.
- Encadenada con `103` (la lectura existe), `099` (PRT), `102` (los dos
  escritores), `068` y `085` (orden de emisión), `064` (los dos bloques de PTBA).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método, que es la misma del error.**

Ya había escrito, tras el error de `amdgpu_page_table_update`, que "nombrar
cosas sin verificar cuesta un grep de un segundo". Esta vez no fue un nombre:
fue un **valor numérico truncado**, y el mismo tipo de error —*algo que no
comprobé*— con una máscara distinta.

**La regla no era "verifica los nombres". Era "verifica lo que no has visto con
tus propios ojos".** Y un `cut -c1-88` sobre una línea de 95 columnas es una de
las formas más fáciles de no verlo.

**Concreto para lo que viene: si un valor numérico decide una conclusión,
se imprime entero o se comprueba el ancho de la línea antes de recortarla.**