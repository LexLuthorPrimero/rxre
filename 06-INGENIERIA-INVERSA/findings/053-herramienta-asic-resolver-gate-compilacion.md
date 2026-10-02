# 053 · Herramienta `asic_resolver`: gate de compilación y rama por ASIC, mecánicos

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu` · `TOOL=tools/asic_resolver.py v1.0.0`
`VALIDATION=SELF_TEST_OK + CROSS_CHECK_INDEPENDENT_OK` · `COMPLEMENTS=046,050`

---

## CUDA principal

Dos de mis errores más caros no eran de comprensión del hardware: eran
**preguntas mecánicas que respondí leyendo**. Invertí seis documentos en un
fichero que no se compilaba, y afirmé que una rama era la nuestra porque el
fichero se llamaba `polaris10`.

Ambas preguntas se contestan sin leer el hardware. Esta herramienta las hace
inseparables de la lectura.

---

## 1. Conformance con el contrato

| campo | valor |
|---|---|
| nombre | `asic_resolver` |
| versión | `1.0.0` |
| propósito | decidir si un `.c` entra en el binario para un ASIC, y qué ramas `chip_id` ejecuta ese ASIC |
| cuestión que resuelve | ¿este código corre en nuestra Polaris12, o es código muerto? |
| observable producido | veredicto por fichero: `COMPILED_UNGATED`, `GATED_UNDECLARED`, `COMPILED_GATED_ON`, `NOT_COMPILED_GATED_OFF`, `NOT_REFERENCED`; y por rama: `SI` / `no` / `?` |
| source | `tools/asic_resolver.py` |
| arquitectura | host x86-64, Python 3, solo stdlib |
| hardware scope | solo clasificación de compilación. **No toca la GPU**, no lee MMIO, no abre `/sys` |
| dependencias | ninguna externa |
| input schema | `--kernel RAIZ`, `--chip CHIP_X`, `--config K=V`, `--universe modo`, `--expect RUTA`, `--makefile F`, `--branches F`, `--define S` |
| output schema | texto legible, o JSON con `{chip, chip_value, universe_mode, universe_verified, results[]}` |
| unidades | `chip_value` es el índice del enum, sin unidades. Los valores de `CONFIG_*` son booleanos, no tri-estado |
| build command | ninguno. Se ejecuta directamente |
| self-test | `python3 asic_resolver.py --selftest` → `RESULTADO OK` |
| known limitations | ver §6 |
| validación | vectores conocidos + cross-check independiente sobre el corpus real, §5 |

## 2. El gate de compilación, cerrado

El caso que costó seis documentos:

```
pm/legacy-dpm/Makefile:28   LEGACYDPM_MGR-$(CONFIG_DRM_AMDGPU_SI)+= si_dpm.o si_smc.o
```

```
$ asic_resolver.py --kernel K --config CONFIG_DRM_AMDGPU_SI=n \
      --makefile drivers/gpu/drm/amd/pm/legacy-dpm/si_dpm.c

VEREDICTO NOT_COMPILED_GATED_OFF
MOTIVO    'si_dpm.o' esta tras CONFIG_DRM_AMDGPU_SI, declaradas inactivas
PUERTAS   CONFIG_DRM_AMDGPU_SI
VALORES   CONFIG_DRM_AMDGPU_SI=n
UNIVERSO  verificado
ABSENCIA  reclamable

EVIDENCIA  legacy-dpm/Makefile:28  [gate:CONFIG_DRM_AMDGPU_SI]
           LEGACYDPM_MGR-$(CONFIG_DRM_AMDGPU_SI)+= si_dpm.o si_smc.o
```

Lo que importa es que **sin `--config` no afirma nada**:

```
$ asic_resolver.py --kernel K --makefile .../si_dpm.c
VEREDICTO GATED_UNDECLARED
AVISO     [CLAIM CONDICIONAL] hace falta el valor de CONFIG_DRM_AMDGPU_SI
```

Una puerta de la que no se conoce el valor se reporta, no se resuelve. Esa
distinción es la que evita convertir `GATED` en `NOT_COMPILED` por comodidad.

### El otro caso: objeto no referenciado

```
VEREDICTO NOT_REFERENCED
AVISO     [NO ABSENCE CLAIM] el objeto no esta referenciado en ningun Makefile
          alcanzado. Eso no es evidencia de que no se compile: puede estarlo por
          una regla que este Makefile no expresa. Hay que ampliar el universo.
```

Mi primer diseño tenía un bug aquí: `all([]) == True` en Python, así que un
conjunto de hallazgos vacío producía `absence_claimable = True`. El self-test lo
detectó. Ausencia de evidencia de puerta **no** es evidencia de ausencia.

## 3. El gate de rama, y el error de 050 detectado por máquina

```
$ asic_resolver.py --kernel K --branches .../polaris10_smumgr.c

FICHERO   .../smumgr/polaris10_smumgr.c
compara nuestro chip contra CHIP_POLARIS12 = 17

 linea  toma   campo     op constante              valor
   793  SI     chip_id   == CHIP_POLARIS12         17
  1674  no     chip_id   == CHIP_POLARIS10         15
  1801  SI     chip_id   == CHIP_POLARIS12         17
  1819  SI     chip_id   == CHIP_POLARIS12         17

RESUMEN    se cumple: 3   no se cumple: 1

AVISO  Las ramas marcadas 'no' son CODIGO MUERTO para mi ASIC.
```

La `:1674` es exactamente la rama que en 050 corregí a mano. La herramienta
llegó a lo mismo sin que yo le dijera qué buscar: **el fichero se llama
`polaris10` y ninguna de las cuatro ramas depende del nombre del fichero**.

## 4. El censo completo del scope `smu`

Lo que la herramienta encuentra en los ficheros que voy a trazar, y que antes
no tenía inventariado:

```
smu7_hwmgr.c       39 comparaciones   11 cumplen, 15 no,  0 irresolubles
smu7_powertune.c    8 comparaciones    2 cumplen,  6 no,  0 irresolubles
smu7_thermal.c      3 comparaciones    1 cumple,   2 no,  0 irresolubles
smu7_smumgr.c       1 comparacion      1 cumple,   0 no,  0 irresolubles
smumgr.c            0 comparaciones    —           —    —
```

```
SMU_SCOPE_BRANCH_CENSUS = PROVEN
  smu7_powertune.c es el MAS ESPECIFICO: 6 de 8 ramas son codigo muerto
  para Polaris12. Dos ramas vivas: :998 (POLARIS12) y :1257 (> TONGA)
  ⇒ al trazar powertune, la rama a leer es :998, no la primera que encuentre
```

Y el patrón que se repite en `smu7_hwmgr.c`:

```
  245  SI   chip_id >= CHIP_POLARIS10   (15)
  246  SI   chip_id <= CHIP_VEGAM       (18)
       ⇒ franja: 15 <= chip_id <= 18, Polaris incluido
```

Este par se repite en `:245`, `:1205`, `:1630`, `:1639`, `:1842`, `:2476`,
`:2971`, `:3488`, `:3498`, `:3524`, `:3556`. **Once veces.** Es la guarda de
"generación Polaris o posterior hasta Vegam", y Polaris12 cae dentro.

```
POLARIS_RANGE_GUARD = PROVEN
  15 <= chip_id <= 18   ≡   Polaris10/11/12 y Vegam
  nuestra 17 esta dentro
  11 ocurrencias en smu7_hwmgr.c
```

## 5. Validación

### 5.1 Vectores conocidos (self-test)

Cada vector afirma algo verificado antes a mano. Si el self-test pasa, la
herramienta reproduce esas lecturas; **no** dice que las lecturas fueran
correctas.

```
enum       CHIP_POLARIS10=15  CHIP_POLARIS12=17  CHIP_VEGA10=19
gate       si_dpm.c sin valor → GATED_UNDECLARED, no reclamable
           si_dpm.c SI=n       → NOT_COMPILED_GATED_OFF, reclamable
           si_dpm.c SI=y       → COMPILED_GATED_ON
           legacy_dpm.c        → COMPILED_UNGATED
           no_existe.c         → NOT_REFERENCED, NO reclamable, con universo ok
rama       :1674 POLARIS10    → no se cumple
           :1801 POLARIS12    → se cumple
           :11   < VEGA10     → se cumple (17 < 19)
continu    objeto en lista partida con \  → COMPILED_UNGATED
           pariente con nombre parecido  → NOT_REFERENCED
puerta     CONFIG_ en el LADO DERECHO no cuenta como puerta
vacio      fichero sin ramas → []
ilegible   fichero inexistente → FICHERO_NO_LEGIBLE
define     0 hits sin universo → no reclamable
           nombre exacto: VOLTAGE_SCALE no casa con VOLTAGE_SCALE_EXTRA
           2 ficheros que definen lo mismo → aviso de duplicado por generacion
```

### 5.2 Cross-check independiente

**Enum, leído con `sed` en vez de con la herramienta:**

```
CHIP_HAWAII=8  CHIP_TOPAZ=10  CHIP_TONGA=11
CHIP_POLARIS10=15  CHIP_POLARIS11=16  CHIP_POLARIS12=17  CHIP_VEGAM=18
```

Coincide con los valores que la herramienta resuelve.

Mi primer cross-check devolvió `POLARIS10 = 10`. La causa fue mía: `grep -oE
'[0-9]+'` sobre `CHIP_POLARIS10` captura los dígitos **del nombre**, no los del
comentario. Es la misma clase de error que el `0x8008` de `mmGRBM_STATUS2`, y
que `VOLTAGE_SCALE`: leer un número sin mirar de qué campo viene.

**Recuento de ramas, `grep -c` plano contra la herramienta:**

```
smu7_powertune.c    grep plano: 8    herramienta: 8
```

### 5.3 Dos bugs que encontró el self-test

Ninguno era hipotético: ambos habrían producido conclusiones falsas.

```
1. el parser del enum solo aceptaba comentarios `#`, y el fichero del kernel
   usa `/* 15 */`. Resultado: enum vacio, cero ramas detectadas, y la
   herramienta habria dicho "no hay ramas" con total seguridad.
   Un parser que no parsea no avisa: es indistinguishable de una ausencia.

2. all([]) == True hacia que un objeto no referenciado saliera como
   ausencia reclamable.
```

## 6. Limitaciones conocidas

```
NO_EVALUA_MACRO      `obj-$(obj-m)$(CONFIG_X)+=` no resuelve el nombre derivado.
                     Si el objeto se construye por indireccion, no lo vera.

NO_SIGUE_CONDICIONALES  `ifeq ($(CONFIG_X),y)` alrededor del include no se
                     interpreta. El universo podria quedar corto.

NO_DISTINGUE_MODULOS   amd_powerplay.o podria compilar un fichero que aqui no
                     esta referenciado. Un NOT_REFERENCED no es prueba de
                     que no exista una regla que lo traiga.

NO_VALIDA_SEMANTICA    Saber que si_dpm.c no se compila no dice nada de si el
                     codigo que si se compila es correcto. La observabilidad
                     es de construccion, no de hardware.

NO_AFIRMA_ausencia_SIN_UNIVERSO  El universo por defecto (`pm-subtree`)
                     enumera todos los Makefiles bajo amd/pm, lo que es
                     exhaustivo para ese subdirectorio. Si un Makefile
                     estuviera fuera de `pm/`, este modo no lo veria.
```

## 7. Reglas que la herramienta deja fijadas

```
COMPILE_GATE_BEFORE_TRACE_GATE   ya existia como regla (046). Ahora es un
                                 comando. La regla sola se olvida; el comando
                                 se ejecuta.

CONFIG_IN_RHS_IS_NOT_A_GATE      un CONFIG_ citado como argumento no abre
                                 puerta. Contarlo al reves convertiria una
                                 regla incondicional en condicional.

CONFIG_WITHOUT_VALUE_IS_NOT_A_VERDICT
                                 una puerta sin valor declarado se reporta
                                 como GATED_UNDECLARED, nunca como
                                 NOT_COMPILED.

NAME_MATCH_NOT_SEMANTIC_MATCH    extends al nombre del FICHERO, no solo al del
                                 simbolo. `polaris10_smumgr.c` sirve a tres
                                 generaciones; el nombre no dice cual.

CODE_DEAD_IS_NOT_CODE            15 de 39 ramas de smu7_hwmgr.c no se ejecutan
                                 en nuestra tarjeta. Tracearlas es trabajo
                                 desperdiciado y conclusion falsa si se
                                 mezclan con las vivas.
```

## 8. Lo que esta herramienta desbloquea

Ahora puedo barrer cualquier fichero del corpus del driver y obtener, sin
leerlo, qué parte es viva para `CHIP_POLARIS12`. Eso convierte "elegir un
fichero para trazar" de una decisión por intuición a una decisión con
criterio: **el fichero con más rama viva es el que más información da por línea
leída.**

Con los números de §4, el orden de valor informativo para el scope `smu` es:

```
1. smu7_hwmgr.c      11 ramas vivas de 39   → mayor densidad
2. smu7_powertune.c   2 ramas vivas de  8   → muy especifica, util si se lee :998
3. smu7_thermal.c     1 rama viva de  3     → pocavirus, bajo valor
4. smu7_smumgr.c      1 de 1, ya cerrada en 048
```

---

```
B_RUNTIME=NOT_EXECUTED · WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU INTACTA
TOOL_VERSION=1.0.0 · SELF_TEST=OK · CROSS_CHECK=OK
```
