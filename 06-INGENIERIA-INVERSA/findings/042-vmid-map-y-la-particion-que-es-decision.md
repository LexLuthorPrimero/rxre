# 042 · `vmid_map`: la asignación de VMID es una decisión del driver, y la geometría se comprueba sola

`CLASSIFICATION=TOOL` · `TRACK=STATIC` · `TOOL=tools/vmid_map.py` · `GPU INTACTA`
`RUNTIME=NOT_RUN` · `MODIFICATIONS=0` en el corpus

## CUDA principal

Construí la herramienta que responde la pregunta que estaba abierta desde `023` —cómo se
asigna un VMID a un proceso— y al usarla aparecieron dos cosas que no esperaba.

**La primera: la geometría de `037` se confirma sola, y con un dato que faltaba.** El
intervalo donde caería una escritura equivocada no es un hueco vacío, son **los registros de
apertura**, y la herramienta lo dice mirando el header que el código incluye de verdad:

```
tramo 0: contextos 0..7, offset 0x54f..0x556
tramo 1: contextos 8..15, offset 0x50e..0x515

VEREDICTO: NO son un array contiguo de 16.
          Un array de 16 con paso 1 desde el tramo 0 escribiría los contextos 8-15
          en 0x557..0x55e.
          Y ahí hay: mmVM_CONTEXT0_PAGE_TABLE_START_ADDR@0x557,
                    mmVM_CONTEXT1_PAGE_TABLE_START_ADDR@0x558
          El registro real del contexto 8 está en 0x50e.
```

**La segunda, y es un hallazgo: la partición en 8 no la impone el hardware, la impone el
driver.**

```
amdgpu_vmid_grab_reserved   CONTRATO: la llaman 2 fichero(s)
amdgpu_vmid_alloc_reserved  IDENTIFICADA  (visto en amdgpu_vm.c, amdgpu_ids.c, amdgpu_ids.h)
amdgpu_vmid_free_reserved   IDENTIFICADA  (visto en los mismos tres)
amdgpu_vmid_uses_reserved   IDENTIFICADA  (visto en amdgpu_cs.c, amdgpu_ids.c, amdgpu_ids.h)
amdgpu_pasid_alloc          IDENTIFICADA
```

`grab` significa **tomar un VMID reservado en vez de asignar uno libre**. Es una política de
reutilización, escrita por alguien, y el hardware no la impone. `first_kfd_vmid = 8`
(`gmc_v8_0.c:1162`) es el punto donde esa política se materializa como frontera de registro.

**Y `amdgpu_pasid_alloc` está en `amdgpu_kms.c`, no en el camino de VM.** Eso significa que
el PASID es un recurso global con su propio asignador, separado del VMID. `040` ya había
visto que `mmIH_VMID_0_LUT` mapea VMID→PASID; ahora está confirmado que son **dos asignadores
distintos**.

## Lo que la herramienta hace, y lo que no

```
vmid_map.py [--kernel RAÍZ] [--part all|topology|ptba|alloc] [--json] [--selftest]
```

Cuatro cosas, automatizadas:

1. **Topología**: cuántos contextos, cuántos vmhubs, dónde está `first_kfd_vmid`.
2. **Geometría de PTBA**: lee `gmc_v8_0.c`, ve qué header de GMC incluye, y extrae los 16
   registros de ese header. Agrupa en tramos por contigüidad. Detecta el caso no contiguo.
3. **Asignación**: busca símbolos de reserva/conversión de id, y para cada uno dice quién lo
   llama y si es **contrato** (lo llaman varios ficheros) o **decisión interna** (solo se
   llama desde donde se define).
4. **Límites**: los dice, no los esconde.

**`--part` existe porque las tres partes son independientes** y una falla no debería
silenciar a las otras dos. Es el mismo principio que el código de salida 2 del validador de
`038`.

## Tres cosas que la herramienta me hizo corregir

**El grafo de llamadas tenía que ignorar comentarios y cadenas.** Sin eso contaba llamadas
que no existen: `/* llama a foo_bar() */` es un comentario. El selftest vector 1 lo verifica,
y es la versión textual de lo que `031` estableció: leer texto no es leer código.

**El intervalo de colisión va en la dirección correcta.** Mi primer cálculo producía
`[1362, 1293]`, un intervalo vacío, porque escribí el hueco como ascendente cuando el segundo
tramo está **más abajo** que el primero. Y el "hueco entre tramos" tampoco es lo
interesante: lo interesante es **dónde caería la escritura equivocada**, que es
`t0.primer_offset + 8 .. + 15` = `0x557..0x55e`. Dos confusiones distintas, ambas de
suposición sobre la geometría, y ambas por no haber mirado qué dice el dato.

**La lista de candidatos era demasiado estrecha y luego demasiado ancha.** La versión
buscaba `amdgpu_id_*reserve*` y no encontraba nada: en 7.2.8 la reserva se llama
`amdgpu_vmid_grab_reserved`. Luego la ensanché a `(reserve|acquire|alloc)` y capturó
`amdgpu_acpi_set_uma_allocation_size`, que no tiene nada que ver con VMID. La versión final
exige que el nombre contenga `vmid`, `id` o `pasid` **y** el verbo.

Esa secuencia —nada, demasiado, demasiado— es la razón por la que la herramienta ahora
imprime `0` ficheros leídos y `631` como universo: **si no encuentra nada, no dice "no
existe", dice "mis patrones no lo encontraron"**, y obliga a ampliar la herramienta antes de
concluir algo sobre el hardware.

## Lo que NO hace

- **No cierra ningún `NOT_DETERMINED`.** Que el driver asigne el VMID 3 no dice qué hace el
  hardware con el bit que escribe. Eso sigue siendo `NOT_DETERMINED`, y `033` ya estableció que la especificación de GFX8 no está publicada.
- **El grafo de llamadas es textual.** No preprocesa, así que una llamada a través de un
  macro de función, o un puntero a función invocado indirectamente, no aparece. Un
  `SIN LLAMADAS VISIBLES` puede ser código muerto o código invisible.
- **No sabe qué función ejecuta para `CHIP_POLARIS12`.** Eso lo hace `ipsolve.py`, que ya
  existe y funciona. Le complementary: `ipsolve` dice *qué fichero*, `vmid_map` dice *qué
  geometría*.

## Falsación

- La geometría se refuta si el header que `gmc_v8_0.c` incluye deja de ser `gmc_8_1_d.h`, o
  si los offsets de `mmVM_CONTEXT0/8_PAGE_TABLE_BASE_ADDR` cambian. La herramienta lo lee, no
  lo supone: `includes_de_gmc_v8_0_c` aparece en la salida.
- La conclusión de "decisión del driver" se refuta si existiera una razón de hardware para la
  partición en 8. Buscaría en la especificación, que no está publicada, así que aquí es
  `PROVEN_DERIVED` y no más.
- La herramienta se refuta si el selftest deja de dar 4/4, o si una mutación del corpus
  cambia su veredicto sin que cambie el dato.

## UNLOCKS

- La pregunta de la iteración anterior está **respondida en su parte estructural**: hay 16
  contextos, el 0 es el GART, la partición 8/8 es una política, y la geometría de registros
  está verificada por lectura automática. Falta la parte que depende de la especificación.
- Un driver propio puede elegir su propia política de asignación. Nada en el hardware obliga
  a reservar en vez de asignar libre, y eso es una decisión de diseño, no una restricción.
- La herramienta es el patrón para las demás: automatizar la **recolección**, dejar el
  **juicio** a quien lee, y acotar toda ausencia con un número de universo.

## Evidencia

```
tools/vmid_map.py         4 vectores de selftest, todos verdes
salida real               631 ficheros .c/.h en amdgpu/; 16 registros; 2 tramos
modificaciones:           solo en tools/; corpus intacto
suite del driver:         22 + 12 + 196 = 230 checks, 0 fallos
herramientas existentes:  asic_resolver, ipsolve, reg_resolve, reg_census, regtable_audit,
                          cap_census, struct_layout, rx550ref, rx550pm4val, pm4dw
corpus:                   MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
