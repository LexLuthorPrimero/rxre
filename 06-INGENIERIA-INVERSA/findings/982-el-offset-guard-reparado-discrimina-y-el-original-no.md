# 982 · Reparado, el OFFSET GUARD de EP08 **discrimina**; el original no — matriz 2×2 medida

```text
CLASSIFICATION=MEASUREMENT+IMPLEMENTATION · TRACK=EXPERIMENTOS+TOOLING
CORPUS=ninguno (fuentes primarias: HARDWARE-FINGERPRINT.md, snapshot hermano 2026-09-19)
HARDWARE_SCOPE=amdgpu 1002:699f rev c7, sub 1002:0b04
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
MODIFICATIONS_COUNT=0 sobre el original (copia reparada aparte)
AUTHORIZATION=NONE (sin sudo, sin token, sin MMIO)
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
RUNTIME=READ_ONLY_BTF+SYSFS + simulacion de pahole
GPU INTACTA · nhwa NO CARGADO
CERROJO=.write-lock/ep08-repair
CONTINUES=973 (que declaró INSTRUMENTO_INVALIDO sin intentar la reparación)
ARTEFACTO=08-ARQUITECTURA/artifacts/EP08-VALIDATION/ep08-repair.md
         preruntime.sh.repaired · preruntime.patch · guard-matrix.tsv
         guard_matrix.sh · make_repaired.sh
HERRAMIENTAS=preruntime_audit.sh (de 973) · pahole v1.30
```

Kernel `7.1.3-200.nobara.fc44.x86_64`, 2026-10-03. uid 1000, sin privilegio. Placa no escrita.

## Qué resuelve

973 hairdijo que EP08 no puede ejecutarse. La pregunta de este nodo es si eso tiene arreglo
**sin que la reparación mienta**:

> **¿Existe una reparación que lo haga alcanzable y que su OFFSET GUARD pase, sin cambiar
> la semántica del experimento y sin que ninguna constante nueva sea circular?**

**Sí. Y el guard reparado discrimina; el original no.** Medido, no reorganizationando.

```
(i)  registros independientes previos para las constantes ausentes    SI
(ii) preruntime_audit.sh: referencias sin asignar                     8 -> 0
(iii) el bloque P8 se EJECUTA y devuelve PASS con 381969                EXIT_P8=0
```

## La matriz 2×2, que es el resultado

Un guard que solo dice «sí» no demuestra nada: hace falta que diga «no» **y que diga algo
distinto** en cada caso.

```
offset real 381969 · offset simulado 381977 (+8)
```

| | struct **intacto** | struct **desplazado +8** | ¿distingue? |
|---|---|---|---|
| **ORIGINAL** | `cambió a '1'` · exit 1 | `cambió a '1'` · exit 1 | **NO** |
| **REPARADO** | `cadena completa verificada (5 campos) — OK` · exit **0** | `cambió a '381977'` · exit 1 | **SÍ** |

**El original emite salida byte-idéntica en los dos mundos.** No es un detector: es una
constante con formato de sentencia. No puede decir la verdad ni cuando la verdad es que
nada ha cambiado.

## La reparación: 4 hunks, 67 líneas añadidas, 9 eliminadas

| # | Cambio |
|---|---|
| 1 | declarar 4 constantes de **identidad de objetivo**, con procedencia (2 registros previos) |
| 1b | declarar 4 de **layout de struct**, con fecha; `NHWA_OFF_ASIC_TYPE` como alias |
| 2 | `$(NF-1)` → `$(NF-2)` en las 8 extracciones de offset |
| 2b | los 7 `awk {…; exit}` leen hasta EOF y contestan la primera coincidencia → ver 983 |
| 3 | añadir la precondición de root (P2.5), que no existía |

`make_repaired.sh` es un guion que **aborta si la entrada no tiene exactamente lo que
espera** (8 ocurrencias de `$(NF-1)`, 7 de `; exit`). No es una edición a mano.

## El contenido que hace que la reparación sea correcta

Dos clases de constante, dos respuestas distintas a "¿puedo rellenarla con lo que mido hoy?":

| CLASE | Pregunta | ¿Rellenar con HOY? |
|---|---|---|
| **IDENTIDAD DE OBJETIVO** | ¿es esta la placa que diseñé? | **NO — CIRCULAR.** Contestarla con la placa actual la hace siempre cierta. |
| **LAYOUT DE STRUCT** | ¿el struct se ha movido? | **SÍ.** Fijarla hoy es lo que la convierte en línea base y le permite detectar un movimiento **futuro**. |

Ver **985** para el desarrollo. Aquí lo que importa es que la reparación no se habríapodido
hacer bien sin esa distinción: las nueve constantes que faltaban eran de las dos clases.

## Un quinto defecto, el más pequeño y el más triste

```
# Identidad PCI EXACTA del dispositivo objetivo (ver PRE2).
```

**`PRE2` no existe.** Ningún fichero con ese nombre, ninguna otra mención en el proyecto. El
autor apuntaba a un documento que no está — y las constantes eran correctas, porque se
conocían: faltaban por escrito.

## Un defecto mío, en el mismo turno, y la parte que más cuesta

Usé `sed -i` sobre el **original** para construir un runner. Borró `main "$@"` — nueve
bytes. Detectado por hash, y **restaurado con el hash verificado** contra el valor fijado en
`9d6de62`:

```
dañado      d12d67b5…1f58d  25504 B
restaurado  c0349f7f…26633  25513 B   == el original, byte a byte
```

Nada se perdió. Se salvó porque el sha256 estaba escrito en un artefacto del turno
anterior. La causa de fondo es peor que el `sed -i`: **EP08 no está bajo control de
versiones**. Ver **984**.

## Estado

```
EP08-REPAIR        RESOLVED · REPARABLE_Y_NO_CIRCULAR
EP08-EJECUCION     DESBLOQUEADA TECNICAMENTE · pendiente SOLO de autorización humana
preruntime.sh      INTACTO, sha c0349f7f…26633, verificado dos veces
GPU / MMIO / nhwa  INTACTOS
```

- **No autoriza ni ejecuta el experimento.** El diff es un paso; aplicarlo y correrlo
  exige el token humano y una escritura en placa.
- **No sobrescribe el original.** Se entrega copia + diff. El original es la prueba.
- **No afirma nada del ASIC.** Todo es del módulo que corre y de su BTF.
- La simulación +8 es del **guard**, no del hardware: no se movió ningún struct real.

```
LIMITACION 1  P4/P5 siguen NOT_EVALUABLE sin root. No se pidió sudo.
LIMITACION 2  PHASE 1 COMPLETA no se ejecutó: exige root y token. Se ejecutó el bloque P8.
LIMITACION 3  La matriz simula el mundo con un pahole de mentira que se autoverifica.
```