# 031 · Verificador de aridad: NO ENTREGADO, con la evidencia de por qué

`CLASSIFICATION=DOCUMENTATION` · `NEGATIVE_RESULT` · `TOOL=tools/pm4dw.c --check-arity`
`CORPUS=rx550-upstream-7.2.8/linux-7.2.8` · `RUNTIME=NOT_RUN` · `GPU INTACTA`

## CUDA principal

Intenté construir el verificador de aridad que `030` justificaba. **No funciona**, y lo
dejo escrito con la evidencia en vez de entregarlo como si funcionara.

Lo que sí queda y vale: **una compuerta de cobertura** que impide que un análisis con
cobertura baja reporte un pass. Sin ella, el verificador habría devuelto
`0 mismatches` sobre 2 llamadas en 63 definiciones, y eso se lee como "el código es
consistente".

## Por qué se intentó

En `030` publiqué `block_size = 13/14/15` cuando es `22/23/24`, por pasar `vm_size` donde el
código pasa `tmp`. Fue un fallo de leer el nombre del parámetro en vez de leer la llamada.
`AGENTS.md` §"PRE-EXECUTION CONTRACT CHECK" pide exactamente lo contrario —"verificar que
campos y parámetros existen"— y un fallo de esa clase produce un número plausible y
equivocado, que es peor que un fallo visible.

## Lo que falla

El verificador cruza cada nombre de función contra el cuerpo de cada definición y compara
el número de argumentos de la llamada con el de la firma. En la práctica:

```
$ pm4dw --check-arity gmc_v8_0.c
# call arity check (definitions parsed in this run only)
FUNCTION                                    DECL    CALL  STATUS
!                                              0       1  ARITY MISMATCH
2 call(s) checked against 63 parsed definition(s); 1 mismatch(es)
pm4dw: NOT_COVERAGE -- only 2 call(s) resolved across 63 definitions;
        the parser did not see the tree, so '0 mismatches' is NOT a pass
```

**2 llamadas resueltas sobre 63 definiciones.** El parser de `pm4dw` está diseñado para el
camino de emisión de PM4, donde cada función es un `static void f(args)\n{`. El resto del
árbol de llamadas —macros, punteros de función, funciones declaradas en otro fichero,
`static inline`— no encaja en ese modelo y el scanner no los ve.

Intenté dos arreglos y ninguno fue suficiente:

| arreglo | efecto |
|---|---|
| rechazar líneas que empiezan por `#` | `!` desaparece como definición… y sigue apareciendo |
| exigir que el identificador empiece por letra o `_` | tampoco: el residuo persiste |

El residuo `!` viene del camino inverso de `decl_name`: cuando el carácter anterior al `(` no
es alfanumérico, el retroceso se detiene en el propio `(`, y `is_definition_name` recibe esa
posición. Mi filtro debería rechazarla y no lo hace en ese camino.

## Por qué no lo entrego

Un verificador de aridad que sólo ve el 3 % del árbol no verifica aridad: verifica que
3 llamadas casan. Reportarlo como funcional sería exactamente el fallo que
`AGENTS.md` §"A test that inspects source text, or asserts that a name is present, cannot
detect a behavioural defect" describe, y que §"A name is not a measurement" profetiza: el
nombre del modo dice "check" y el resultado no significa nada.

**`NEGATIVE_RESULT` registrado**: la verificación de contratos de llamada sobre el árbol
completo de amdgpu **no está hecha**, y este intento no la resuelve. La razón es de
alcance del parser, no de concepto.

## Lo que sí se entrega

### La compuerta de cobertura

Añadida al propio programa, y aplica a cualquier modo futuro:

```c
if (calls < ndefs) {
        fprintf(stderr, "pm4dw: NOT_COVERAGE -- only %d call(s) resolved across "
                "%d definitions; the parser did not see the tree, so "
                "'0 mismatches' is NOT a pass\n", calls, ndefs);
        return 1;
}
```

Un análisis que no vio el árbol no puede pasar. Es la misma disciplina que
`AGENTS.md` §"Absence is not one state": *no observado* no es *ausente*, y *sin cobertura*
no es *sin discrepancias*.

## UNLOCKS

- La verificación de aridad queda como hueco conocido, con el motivo. Reintentarlo exige un
  parser que maneje macros y punteros de función, que es otro programa.
- `PRE-EXECUTION CONTRACT CHECK` sigue sin herramienta. La alternativa inmediata es
  manual y dirigida: para cada función del camino que importe, abrir su definición y su
  llamada y contarlas. Hecho para `get_block_size` al detectar el error, y funcionó.
- `pm4dw` sigue siendo útil para lo que fue construido: conteo de emisión, rutas, tamaños
  de struct y sitios de `write_multiple`. `--check-arity` no lo está, y ahora lo dice.

## Criterio de falsación

Este hallazgo se refutaría si una implementación de aridad sobre el mismo corpus reportara
una fracción de llamadas resueltas alta —digamos > 50 % de las definiciones con al menos
una llamada— sin falsos positivos en un fichero con un desajuste inyectado. Eso demostraría
que el parser sí puede cubrir el árbol y el fallo es de implementación, no de modelo.

## Evidencia

```
herramienta:  tools/pm4dw.c, modo --check-arity, compuerta NOT_COVERAGE
salida:       "2 call(s) checked against 63 parsed definition(s)"
corpus:       12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)
relacionado:  030 §"La corrección" (el error que motivó el intento)
```

Ningún registro leído de MMIO. `RUNTIME=NOT_RUN`. `MODIFICATIONS=0` en el corpus.