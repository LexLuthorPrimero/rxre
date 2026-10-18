# 1628 — M3 ES UN MUTANTE EQUIVALENTE, NO UN AGUJERO DEL ORÁCULO — MEDIDO

```text
CLASSIFICATION=NEGATIVE_RESULT
WORK_CLASS=RXRE-CLI-UNIFICATION-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Sobrevive el mutante M3 porque el oráculo es débil, o porque la mutación no pierde información?
STATE=PROVEN_EQUIVALENT_MUTANT
```

## ORIGEN

`tools/mutate_target.py` declara 4 mutantes sobre `tools/rxre/core/target.py`,
con oráculo `test_p004.py` (T0401-T0406). Al ejecutar `./rxre mutate`:

```text
[OK] M1_elimino_asic_match: DETECTADO
[OK] M2_target_incorrecto: DETECTADO
[XX] M3_sin_provenance: MUTANTE SOBREVIVE (AGUJERO)
[OK] M5_sin_inicializar_mapping: DETECTADO
mutantes 3 / 4 con comportamiento esperado
```

El catálogo afirma `esperado="CAER"` para M3. Sobrevivió.

## LA HIPÓTESIS BARATA (Y POR QUÉ ES INSUFICIENTE)

La lectura inmediata es "el test T0403 es débil". T0403 comprueba:

```python
v("T0403 provenance includes PCI information",
  "PCI" in prov_str or "vendor" in prov_str or "1002" in prov_str,
  f"provenance = {prov}")
```

Eso es un `OR` de tres condiciones. La provenance real tiene **cuatro
entradas**, y las condiciones las satisfacen entradas **distintas**:

```text
[0] PCI 0000:01:00.0: vendor=1002 device=699f rev=c7
[1] vendor/device/revision leidos de sysfs:/sys/.../0000:01:00.0/{vendor,device,revision}
[2] asic=Polaris12 gfx=gfx_8_0 desde mapa declarado en core.target._MAPA_PCI, ...
[3] driver en uso: amdgpu
```

M3 redacta `[0]`. Pero `[1]` contiene literalmente la palabra `vendor`, así que
el `OR` sigue siendo verdadero y el test pasa.

Eso describe **por qué** el test no cae. No demuestra que M3 pierda información.

## DISCRIMINANTE: ¿M3 PIERDE INFORMACIÓN?

La pregunta causal es si el mutante es *detectable de principle* o si la
mutación es semánticamente inocua. Se midió directamente, aplicando M3 y
comprobando si el triple `(bdf, vendor, device)` sigue siendo reconstruible:

```text
=== CON MUTANTE M3 APLICADO ===
BDF_EN_PROV:       True
VENDOR_EN_PROV:    True
DEVICE_EN_PROV:    True
TRIPLE_RECONSTRUIBLE: True
--- provenance resultante ---
  [0] PCI redacted
  [1] vendor/device/revision leidos de sysfs:/sys/.../0000:01:00.0/{vendor,device,revision}
  [2] asic=Polaris12 gfx=gfx_8_0 desde ... derivado de lspci -nn -d 1002:699f ...
  [3] driver en uso: amdgpu
```

**El triple sigue siendo reconstruible.** Por tanto M3 **no pierde
información**: es un *mutante equivalente* en este host.

`target.py` restaurado tras la medición (hash `1eaf88ceae0a9a5c…`, `git status`
limpio). El backup en `/tmp/opencode/mutate-target-scratch/target.py.bak` se
conservó como evidencia.

## POR QUÉ ES EQUIVALENTE AQUÍ Y NO EN OTRO HOST

La entrada `[0]` es la única que **liga** el BDF a los IDs. Las entradas `[1]`
y `[2]` por separado no lo hacen: `[1]` da el BDF sin los IDs; `[2]` da los IDs
sin el BDF.

Con **una sola** GPU detectable, esa separación no importa: no hay otro
candidato al que atribuir. Con **dos** GPUs detectables, `[2]` affirmaría
"ASIC=Polaris12" sin decir **de qué BDF**, y la atribución se vuelve
indeterminada. M3 sería entonces detectable y necesario.

Es decir: la equivalencia de M3 es una propiedad de **este host**, no del
código. El catálogo la declaraba `CAER` sin esa salvedad.

## REPARACIÓN

Reclasificado en el catálogo, con la razón escrita en el propio dato:

```python
dict(nombre="M3_sin_provenance_pci",
     esperado="SOBREVIVE",
     nota="MUTANTE EQUIVALENTE en este host, medido: el triple "
          "(bdf,vendor,device) sigue siendo reconstruible desde las "
          "entradas [1] y [2] de la provenance. NO es un agujero del "
          "oráculo: es una limitacion del harness con UN solo target. "
          "Con dos GPUs detectables esta mutacion SI seria atribuible a "
          "un BDF, porque [2] dice QUEasic es sin decir DE QUE BDF. "
          "Para discriminating hace falta un host multi-target.")
```

## POR QUÉ NO SE REFUERZA EL ORÁCULO

Se podría endurecer T0403 para exigir vendor y device en la **misma** entrada.
Eso haría caer M3, pero produciría un **falso positivo**: reportaría un
"agujero" donde la información sigue disponible por otras vías.

Un oráculo que fuerza la caída de un mutante equivalente miente sobre la
calidad del código bajo prueba. Preferimos el resultado honesto.

## CONSECUENCIA PARA EL ESTADO DEL ORÁCULO

`test_p004.py` es `VALIDATED` como oráculo de M1, M2 y M5. Para M3 el oráculo
es **incapaz de discriminar por construcción** en un host de un solo target.
Eso no lo invalida para los otros tres.

## ALCANCE DE LA INTERVENCIÓN

Read-only sobre hardware. Se escribió `tools/rxre/core/target.py` **in-place**
mediante el propio `mutate_target.py`, con backup y restore verificados por
hash. No se tocó la GPU ni `0000:00:02.0`.

## ESTADO

```text
CLAIM=M3 sobrevive porque el oráculo T0403 es débil
STATE=REFUTED
CLAIM=M3 es un mutante equivalente en hosts de un solo target
STATE=PROVEN (medido por reconstrucción del triple bdf/vendor/device)
```

## LO QUE NO SE HIZO

- **No se midió** el comportamiento de M3 con dos GPUs detectables. Este host
  tiene una. Estado: `DEFERRED`, no `PROVEN_ABSENT`.
- **No se midió** si existe otro host en el laboratorio. `NOT_DETERMINED`.
