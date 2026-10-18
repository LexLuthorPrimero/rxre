# 1629 — CATÁLOGO DE MUTATE_TARGET OBSOLETO: 2 DE 4 MUTANTES NO APLICABLES — CORREGIDO

```text
CLASSIFICATION=ERROR_CORRECTED
WORK_CLASS=RXRE-CLI-UNIFICATION-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Los 4 mutantes del catálogo se aplican al código actual de target.py?
STATE=REFUTED_THEN_CORRECTED
```

## QUE SE AFIRMABA

El catálogo de `tools/mutate_target.py` declara 4 mutantes sobre
`tools/rxre/core/target.py`, todos `esperado="CAER"`.

## QUE SE MEDIO

`./rxre mutate` produce:

```text
[FATAL] M1_elimino_asic_match: busqueda_no_encuentra: return MAPPING.get((vendor.upper(), device.upper()
[FATAL] M3_sin_provenance: busqueda_no_encuentra: f"PCI vendor:{vendor} device:{device}"
```

**2 de 4 mutantes no se aplican.** El harness los marcaba `FATAL` y los
contaba como fallo, así que el run terminaba con `rc=1`.

## CAUSA: EL CATÁLOGO ESTÁ ESCRITO CONTRA UNA VERSIÓN ANTERIOR

Las cadenas buscadas no existen en el código actual:

| Mutante | Cadena buscada (catálogo) | Realidad en `target.py` |
|---|---|---|
| M1 | `MAPPING.get((vendor.upper(), device.upper()), (None, None))` | `return _MAPA_PCI.get("%s:%s" % (vendor, device))` (línea 124) |
| M3 | `f"PCI vendor:{vendor} device:{device}"` | `"PCI %s: vendor=%s device=%s rev=%s" % (bdf, vendor, device, revision),` (línea 151) |

Dos Derivas, ambas coherentes con una reescritura posterior del módulo:

1. **El mapa se renombró**: `MAPPING` → `_MAPA_PCI`.
2. **El formato de provenance cambió** de f-string a `%`-formatting, y se le
   añadió el campo `rev`.

M2 y M5 sí aplicaban: `"Polaris12", "gfx_8_0"),` y
`    _initialize_capability_mapping()` siguen presentes.

## POR QUÉ ESTO NO ERA SIMPLEMENTE "UN TEST ROTO"

Un `FATAL` por mutante no aplicable **degrada el resultado sin anunciarlo**.
El resumen decía "mutantes 2 / 4 con comportamiento esperado" como si dos
mutantes hubieran sobrevivido y otros dos fallen honestamente. No: dos nunca
se intentaron.

Es el mismo patrón que §82 en negativo: `NO_RESULT` presentado como
`NEGATIVE_RESULT`. Un mutante que no se aplica no es un mutante que sobrevive.

Además, el catálogo.codificaba el estado del código como si fuera **evidencia
actual** (§86 HISTORICAL EVIDENCE). Era evidencia histórica presentada como
observación vigente.

## REPARACIÓN

Las tres cadenas se reescribieron contra el código actual:

```python
dict(nombre="M1_elimino_asic_match",
     buscar='    return _MAPA_PCI.get("%s:%s" % (vendor, device))',
     cambio='    return None', ...)

dict(nombre="M3_sin_provenance_pci",
     buscar='        "PCI %s: vendor=%s device=%s rev=%s" % (bdf, vendor, device, revision),',
     cambio='        "PCI redacted",', ...)
```

M1 pasa a mutar a `return None`, que es la eliminación del lookup que el
nombre del mutante describe.

Tras la reparación (y la reclasificación de M3 documentada en el hallazgo
1628):

```text
=== mutate_reg_resolve ===   mutantes 4 / 4 con comportamiento esperado
=== mutate_relations ===     mutantes 4 / 4 con comportamiento esperado
=== mutate_target ===        mutantes 4 / 4 con comportamiento esperado
```

`./rxre mutate` → `rc=0`. `target.py` verificado intacto después del run
(`git status` vacío, hash `1eaf88ceae0a9a5c2687907c80b8359f9fa04f3f7d92b934bf42bb9d661b0739`).

## HALLAZGO ADICIONAL: RAIZ DERIVADO DE `__file__`

`mutate_target.py` tenía la raíz **hardcodeada**:

```python
RAIZ = "/home/lucas/Escritorio/rxre"     # antes
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ahora
```

Sin este arreglo, el mutador habría editado el fichero del path absoluto
aunque el árbol se moviera de sitio — es decir, habría mutado un archivo que
no es el del repositorio en curso, sin avisar. El path hardcodeado convertía
la prueba en no reproducible y potencialmente destructiva.

Coberto por `cli.mutate.sin_raiz_hardcodeada`.

## RIESGO RESIDUAL MEDIDO

`mutate_target.py` escribe `target.py` **in-place**. El backup/restore existe
pero **no es atómico**: si el proceso muere entre la escritura del mutante y el
restore, el fichero queda mutado.

Mitigación actual: el backup sobrevive en
`/tmp/opencode/mutate-target-scratch/target.py.bak`, así que la recuperación es
posible. No se ha implementado un `try/finally` en el propio script.

Estado: riesgo **conocido y no mitigado**. `NOT_DETERMINED` si ocurre en la
práctica. `git checkout` es la recuperación de referencia mientras el fichero
esté versionado.

## ALCANCE DE LA INTERVENCIÓN

Escritura sobre `tools/rxre/core/target.py` in-place, con backup y restore
verificados por hash. Sin acceso a GPU. `0000:00:02.0` no tocado.

## ESTADO

```text
CLAIM=Los 4 mutantes del catálogo se aplican al código actual
STATE=REFUTED (2 de 4 no aplicables)
CLAIM=Los 4 mutantes se aplican tras actualizar las cadenas
STATE=PROVEN (4/4 comportamiento esperado, rc=0)
```

## LO QUE NO SE HIZO

- **No se añadió** un test que verifique que el catálogo sigue siendo
  aplicable al código actual. Hoy el fallo se manifiesta como `FATAL` en
  runtime, no como test rojo. Un guard de aplicabilidad habría convertido un
  error silencioso en un fallo visible antes de mutar nada.
  Estado: `OPEN_FRONTIER`, no implementado.
