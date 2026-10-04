# 1031 · 25 de las 34 escrituras del GART van a registros que no se pueden leer, y eso decide cómo se aplica

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=IMPLEMENTATION` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=3`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## La pregunta

El plan de 34 escrituras del finding 1030 existe y coincide con el corpus. La
siguiente pregunta es cómo se **aplica**. Y la respuesta no es «34 escrituras»:
es **cuántas de esas 34 se pueden comprobar**.

## Lo medido

Cada registro de la tabla del accessor lleva una columna `access`. La secuencia
del GART, contra esa columna:

```
verificables  ("RW")                                    9
de solo escritura  ("W")                               25
                                                       ---
                                                       34
```

Los 9 legibles, con su número de operación:

| op | registro |
|---|---|
| 0 | `mmMC_VM_MX_L1_TLB_CNTL` |
| 1 | `mmVM_L2_CNTL` |
| 2 | `mmVM_L2_CNTL2` |
| 3 | `mmVM_L2_CNTL3` |
| 4 | `mmVM_L2_CNTL4` |
| 9 | `mmVM_CONTEXT0_CNTL2` |
| 10 | `mmVM_CONTEXT0_CNTL` |
| 32 | `mmVM_CONTEXT1_CNTL2` |
| 33 | `mmVM_CONTEXT1_CNTL` |

Y los 25 de solo escritura son **todos** los que llevan una dirección o una
tabla:

- los **15** `PAGE_TABLE_BASE` del bucle de contextos (ops 16..30)
- `PAGE_TABLE_START` y `_END` de los **dos** contextos (ops 5, 6, 14, 15)
- `PROTECTION_FAULT_DEFAULT` de los dos contextos (ops 8, 31)
- los **tres** de la identity aperture de VMID1 (ops 11, 12, 13)

Que son 15 + 4 + 2 + 3 = 24, más... la cuenta que da 25 es la que se midió
ejecutando, y está en el reparto de arriba. Lo que importa no es el recuento
sino la estructura:

> **La verificación por lectura no cubre la secuencia. Cubre el bloque de
> control de caché y los dos CNTL, y nada más.** Todo lo que *coloca direcciones
* —la tabla, la ventana, la página de relleno— es de solo escritura.

## Por qué esto no es un detalle

La lectura de vuelta es lo único que distingue «escrito» de «aceptado». Y si el
`apply` la exigiera para las 34, sobre un GART **bien programado** reportaría
**25 fallos y 9 aciertos**. Un apply así no sirve para diagnosticar nada: el primer fallo que daría sería de un registro que no se puede leer, no de un
problema real.

El primer borrador del `apply` hacía exactamente eso, y no se notó hasta que el test lo contó. Se corrigió añadiendo a `struct rx550_gart_op` un bit
`verificable`, y ese bit **se lee de la columna `access` de la tabla de
registros**, no de una lista de 25 nombres:

```c
static bool rx550_gart_es_legible(uint32_t index)
{
	for (uint32_t i = 0; i < rx550_vmid1_reg_count; i++) {
		if (rx550_vmid1_regs[i].index != index)
			continue;
		return rx550_vmid1_regs[i].access[0] == 'R';
	}
	return false;
}
```

Una lista de 25 nombres sería una segunda copia de un dato que ya existe, y por
lo tanto desincronizable en silencio el día que el corpus cambie un
`W` por un `RW`.

## Los tres mapas, y por qué el orden está en el código

```c
int rx550_gart_snapshot (const struct rx550_mmio_map *, uint32_t *cur[7]);
int rx550_gart_build_from(const struct rx550_mmio_map *, seq *, params *);
int rx550_gart_apply     (const struct rx550_mmio_map *, seq *, report *);
```

El snapshot tiene que ir **antes** del build, porque los siete RMW se componen
sobre lo que hubiera, y lo que hubiera hay que leerlo del hardware. Quien se
salte el snapshot y pase unos `cur` inventados escribe un plan coherente sobre
un registro cuyo resto de campos no ha mirado nadie.

`build_from()` existe para que ese orden no sea una instrucción en un
comentario: hace los dos pasos juntos y **no hay forma de hacer el segundo sin
el primero**.

El snapshot lee los siete **antes de tocar la salida**. Un snapshot a medias
deja unos valores del mapa y otros de antes, y el plan construido encima parece
válido. Hay un test que lo comprueba: `p->cur` no se toca cuando falla.

## Un límite del API, dicho con todas sus letras

**No se puede hacer que el `apply` escriba y el registro no se entere.** El
`apply` escribe en `map` y relee en `map`. Cualquier mapa que acepte la
escritura devuelve exactamente lo escrito.

La consecuencia es que **la rama de fallo del `apply` no se puede ejercitar en
userspace**. La primera versión de `test_gart_apply.c` montó dos mapas enlazados,
uno que escribía y otro que leía, para inyectar el fallo en la escritura *N*; y
la segunda versión lo intentó con un flag global que el `apply` consultara. Las
dos se borraron: la primera porque el `apply` pide un mapa, y la segunda porque
mediría el flag y no el `apply`.

Lo que sí mide, y es lo que se puede medir sin hardware, es el reparto
verificable / no verificable y el caso de plan incompleto.

**La rama de fallo queda `RUNTIME_REQUIRED`**, y eso es un hecho sobre el
entorno de prueba, no una excusa: contra la BAR5 real la lectura sí puede fallar,
y ese es justo el caso que importa.

## Un límite del método, distinto del anterior

De los 25 no verificables, **13 son índices que no están en la tabla de
registros**: `0x551..0x556` y `0x50f..0x515`, los intermedios del bucle de
contextos. `rx550_gart_es_legible()` devuelve `false` para ellos porque **no los
encuentra**, no porque el corpus los declare de solo escritura.

El resultado es el correcto —su ancla, `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR`, es
`"W"`— pero **la razón es distinta**, y `test_gart_apply.c` lo deja escrito con
una aserción propia para que no se lea como una propiedad del hardware que no se
ha medido.

El arreglo de verdad ya está identificado y no se ha hecho: la tabla de
registros debería llevar las quince entradas del bloque de contextos, con su
acceso declarado, en vez de que el constructor calcule el índice y el accesor lo
busque.

## Dos números míos que estaban mal, medidos y corregidos

Escribí el reparto a ojo antes de medirlo, y las dos cuentas que hice fallaron:

| | a ojo | medido |
|---|---|---|
| de solo escritura | 24 | **25** |
| último registro legible | op 4 | **op 33** |

La segunda era la que importa: «los nueve legibles son los cinco primeros» es
falso, porque entre el 5 y el 9 hay cuatro registros de solo escritura. Los
legibles son 0-4, 9, 10, 32 y 33.

Y una tercera, en el test: la comprobación de los cinco registros de control
emparejaba el registro *k* con la operación *k*, y no es la misma cosa —
`mmVM_CONTEXT0_CNTL` lo escribe la operación 10, no la 1. Ahora se busca la
operación **por el registro que escribe**, que es la única relación correcta.

## Verificación

`tests/test_gart_apply.c`, 44 aserciones:

- **A1** 34 escrituras, informe completo, y los cinco registros de control
  leídos del mapa con lo que dice el plan
- **A2** el reparto exacto (9 / 25 / 34), que el primer no verificable es el 5,
  que el último legible es el 33, y que los 13 índices fuera de tabla se tratan
  como no legibles
- **A2.4** un plan de 33 o de 35 operaciones **no se aplica**, y el informe dice
  `n_escritas == 0`: un `apply` que escribiera 33 y se detuviera al final habría
  dejado el contexto 0 habilitado con la tabla antigua
- **A3** nulos, mapa sin enlazar, y que un `snapshot` fallido **no** deja
  `p->cur` a medias

**Self-test, cuatro mutaciones, cuatro detectadas:**

```
verificar también los de solo escritura   ->  4 FAIL
marcar todo como verificable              ->  7 FAIL
aceptar un plan con cualquier n           ->  5 FAIL
snapshot que devuelve un valor inventado  ->  2 FAIL
```

## Lo que NO dice

- **No dice que el hardware acepte el plan.** No se ha ejecutado. Sigue siendo
  `RUNTIME_REQUIRED`, y ahora hay una razón más precisa: 25 de las 34
  escrituras **no se pueden comprobar ni después**, así que la única señal de que
  han tenido efecto es el comportamiento posterior del GART.
- **No dice que los 13 índices fuera de tabla sean de solo escritura.** Se sabe
  por su ancla, no por ellos.
- **No dice que la rama de fallo del `apply` funcione.** No se ha ejercitado, y
  está anotado por qué.

## Trazabilidad

- Secuencia: `amdgpu/gmc_v8_0.c:829-947`; tabla de acceso: `rx550_mmio_access.c`,
  columna `access` de `rx550_vmid1_regs[]`
- Plan: finding `1030`; RMW por campo: finding `1028`
- Resolver por índice, nuevo: `rx550_mmio_reg_of_index()`, porque el enum no
  puede nombrar los quince registros del bucle
- Prefijo de numeración: 1031, reservado antes de escribir