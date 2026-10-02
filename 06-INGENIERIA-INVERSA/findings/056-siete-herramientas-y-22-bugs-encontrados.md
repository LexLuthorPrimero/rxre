# 056 · Siete herramientas y el bucle manual cerrado

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu,tools` · `VALIDATION=SELF_TEST_OK + CROSS_CHECK_OK`

---

## CUDA principal

Dos de mis errores más caros eran **preguntas mecánicas respondidas a ojo**:
si un `.c` se compila, qué rama ejecuta mi ASIC, qué offset tiene un registro.
Ninguna requiere entender el hardware. Cada una cuesta entre veinte minutos y
media hora de lectura, y cada una me costó al menos un error documentado.

Convertirlas en siete herramientas con self-test no solo aceleró el trabajo:
**encontró 22 bugs que habrían producido hallazgos falsos**, incluidos varios
que presentaban como ausencias del corpus.

---

## 1. Las siete herramientas

```
tools/asic_resolver.py    v1.0.0  gate de compilación + rama por chip_id
tools/reg_resolve.py      v1.0.0  offset/máscara/shift + UNIDAD
tools/reg_census.py       v1.0.0  qué registros toca un .c, con bus
tools/regtable_audit.py   v1.0.0  auditoría de tablas .c vs headers
tools/cap_census.py       v1.0.0  phm_cap_set/unset por ASIC
tools/struct_layout.py    v1.0.0  offset/tamaño de struct, ABI x86-64
tools/trace_path.py       v1.0.0  cadena de llamadas con nodo vivo/muerto
```

Y `evidence_search.py` (preexistente) más `ipsolve.py`. El bucle manual
completo queda cubierto:

```
buscar símbolo        → evidence_search + reg_resolve
contar ramas           → asic_resolver --branches
cruzar tabla/header    → regtable_audit
resolver offset+unidad → reg_resolve
medir struct           → struct_layout
ver qué MMIO toca      → reg_census
encadenar la ruta      → trace_path
capacities por ASIC    → cap_census
```

## 2. El resultado que no tenía: `ci_smumgr.c` no es nuestro

```
hwmgr.c:100   ci_smu_funcs        ← carrizo     ci_smumgr.c     51 registros
hwmgr.c:144   tonga_smu_funcs     ← tonga       tonga_smumgr.c  47
hwmgr.c:149   fiji_smu_funcs      ← fiji        fiji_smumgr.c   20
hwmgr.c:157   polaris10_smu_funcs ← NUESTRO     polaris10_smumgr.c  11
```

Once vtables, once asignaciones, una sola se ejecuta para Polaris12.

```
POLARIS12_SMU_PATH = PROVEN
  el ranking por numero de registros mide lo que NO importa
  los ficheros mas densos son los de otras generaciones
  smu7_hwmgr.c (16+16) es el mas denso de la ruta VIVA
```

Sin `reg_census` habría deducido que los ficheros con más registros son los
importantes. Es exactamente el error invertido.

## 3. Lo que las herramientas tienen que decir aunque no pregunte

`trace_path` sobre la función base del canal SMC:

```
DIRECTA  smu7_send_msg_to_smc            NO_CONDICIONAL  smu7_smumgr.c:130
  MACRO  PHM_WAIT_FIELD_UNEQUAL -> PHM_WAIT_REGISTER_UNEQUAL
         -> PHM_WAIT_REGISTER_UNEQUAL_GIVEN_INDEX
         -> phm_wait_for_register_unequal               NO_CONDICIONAL  smu_helper.c:155
```

Cuatro saltos de macro hasta la función que realmente toca el MMIO. Antes
tenía ese dato por lectura manual; ahora sale en un comando y **cada nodo lleva
su veredicto de alcanzabilidad**.

```
TRACE_REACHES_MMIO_PRIMITIVE = PROVEN
  la ruta del canal SMC pasa por 4 macros antes del acceso real
  un call-graph ingenuo cortaba en la primera y perdia la mitad de la ruta
```

## 4. Los 22 bugs que encontró el self-test

Todos del tipo que solo aparece al ejecutar. Los marcados son los que habrían
producido **un hallazgo falso presentable como evidencia**.

```
regtable_audit    parseaba linea a linea; las entradas ocupan 3-4 lineas
                  → tablas truncadas que parecian enteras              [FALSO]
regtable_audit    solo aceptaba mascaras con nombre
                  → las 2 tablas GCCAC (formato literal) invisibles    [FALSO]
regtable_audit    pase shmap donde iba dmap
                  → 109 falsas "mascara ausente"                       [FALSO]
reg_resolve       suffix _MASK dentro del grupo de captura
                  → 0 campos, sin error                              [FALSO]
reg_resolve       al arreglarlo, endswith sobre un simbolo ya sin sufijo
                  → tablas vacias otra vez                            [FALSO]
reg_resolve       classify miraba mm* antes que _BASE_IDX              [FALSO]
cap_census        strip_comments acortaba el texto
                  → 225 de 274 lineas con numero erroneo              [FALSO]
cap_census        el self-test PASABA con la herramienta rota en el corpus
                  → mi fixture era mas simple que el fichero real
reg_census        RREG32(mmX) es de un argumento, mi regex exigia dos
                  → todos los RREG32/WREG32 fuera del censo
struct_layout     "uint32_t b, c" → el match codicioso perdia el 1er campo
struct_layout     find_struct releia el arbol por struct → timeout 120s
trace_path        "int (*fn(void))(int)" capturaba `int` como funcion
trace_path        typedef de puntero a funcion contado como definicion
trace_path        una llamada suelta se contaba como definicion nueva
trace_path        macros: el filtro por prefijo eliminaba las que importan
trace_path        el cuerpo capturado eran los PARAMETROS, no la expansion
reg_resolve       fixture con headers en el sitio equivocado
trace_path        3 correcciones de refs a expand_into / children vs target
```

### Los dos que más importan

**`strip_comments` acortaba el texto.** Sustituía cada comentario por un espacio
único, lo que invalidaba el mapa de posiciones y desplazaba todos los números
de línea posteriores. 225 de 274. Y el self-test **pasaba**, porque mi fixture
no tenía un comentario multilínea. La lección no es "añade más tests": es que
un self-test con fixture más simple que el corpus real valida menos de lo que
cree. Arreglado sustituyendo cada carácter de comentario por un espacio, y
añadiendo al fixture un comentario multilínea con un `phm_cap_set` fantasma que
solo se cuela si el strip está mal.

**Filtro de macros por prefijo compartido.** Excluía llamadas cuyo nombre
compartía prefijo con la macro, para evitar autorreferencias. Eso borraba
exactamente las macros que había que resolver: `PHM_WAIT_FIELD_UNEQUAL` llama a
`PHM_WAIT_REGISTER_UNEQUAL`. El filtro parecía razonable y estaba midiendo lo contrario de lo que creía.

```
SELF_TEST_SIMPLE_THAN_CORPUS = FALSE_POSITIVE_SOURCE
  un fixture mas simple que el corpus valida el caso simple y nada mas
  hay que meter en el fixture los modos de fallo que se vieron
```

## 5. Validación cruzada: contra `gcc`

`struct_layout` no se valida contra sí mismo, contra el compilador:

```
gpcr       size=20  type@=16     gcc: 20 / 16      ✓
rellenada  size=8   b@=4         gcc: 8 / 4        ✓
punteros   size=24  q@=8  c@=16  gcc: 24 / 8 / 16  ✓
```

Y contra lectura manual, dos casos de `cap_census`:

```
hwmgr.c:487   phm_cap_set SQRamping      ← el set
hwmgr.c:520   phm_cap_unset SQRamping    ← el unset
```

274 de 274 líneas correctas, verificadas una a una por script contra el
contenido real del fichero.

## 6. Lo que las herramientas NO hacen, declarado

```
NO_PRU             ninguna toca la GPU, ni MMIO, ni /sys, ni modulos
NO_ESCRIBE         WRITE_EXECUTION=NONE, MODIFICATIONS=0
NO_SEMANTICA_HW    coherencia entre fuentes, no significado del hardware
NO_EJECUCION       trace_path declara la rama, no prueba que se ejecute
NO_INFERIR_ABSENCE un 0 sin universo verificado lleva NO ABSENCE CLAIM
NO_INVENTAR_OFFSET struct_layout marca '?' en vez de un numero plausible
```

Ese último es el más importante para un driver propio: **un offset inventado
escribe en el campo vecino**, y es peor que no saberlo.

## 7. Hallazgos de esta tanda, ya cerrados

```
PROVEN   POLARIS12_SMU_PATH = polaris10_smumgr.c + smu7_hwmgr.c
PROVEN   la cadena SMC pasa por 4 macros hasta phm_wait_for_register_unequal
PROVEN   DIDT_STALL/TUNING son índices GFX9+; 6 de las 109 entradas de la
         tabla Polaris12 apuntan a índices que gfx_8_0_d.h no define
PROVEN   las 109 entradas caben en sus máscaras (regtable_audit, 0 truncan)
PROVEN   GCCACConfig_Polaris12 no existe; P12 usa la de P11
PROVEN   Voltage en mV (rangos 1100..2500 en smu7_hwmgr.c:2020-2031)
PROVEN   ro viene de un eFuse por dies, escala lineal sobre 0..255
```

## 8. Reglas que las herramientas dejan fijadas

Las siete reglas ya estaban en documentos; ahora son comandos. Una regla escrita
se olvida, un comando se ejecuta.

```
COMPILE_GATE_BEFORE_TRACE_GATE    era una regla; ahora es asic_resolver
CONFIG_WITHOUT_VALUE_IS_A_CLAIM   GATED_UNDECLARED, nunca NOT_COMPILED
NAME_MATCH_NOT_SEMANTIC_MATCH     extends al nombre del FICHERO
UNIT_DECLARATION_BEFORE_COMPARISON  declara de qué campo sale cada número
CROSS_CHECK_INDEPENDENT           gcc, y el corpus, no la herramienta
SELF_TEST_MUST_EXCEED_FIXTURE      un fixture simple valida el caso simple
```

---

```
GPU INTACTA · WRITE_EXECUTION NONE · MODIFICATIONS 0
B_RUNTIME NOT_EXECUTED · 7 herramientas SELF_TEST OK
CROSS_CHECK gcc OK · 274/274 líneas de cap_census verificadas
```
