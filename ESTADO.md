# ESTADO — RX 550 Polaris12 / GFX8

Documento único de estado. Consolida seis documentos que se declaraban "estado
final" y competían entre sí. Los originales están en
`archive/documentacion-compactada-20261003/` y en git; aquí no se resume nada que
no estuviera medido en su fuente.

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=consolidacion-documental
GENERADO=A MANO por global-coordinator-01 el 2026-10-03
FUENTES=6 documentos, 3 ventanas temporales distintas (2026-09-19, 09-25, 09-29)
REGLA=las cifras se citan con su fuente y su fecha. Si dos fuentes discrepan, se
      declaran las dos; no se promedian ni se elige la más reciente.
```

## Por qué estos seis eran uno

No se contradicen: son tres cierres sucesivos sobre el mismo objeto, y la
divergencia de fechas es lo que los hacía parecer documentos distintos.

| Fuente | Fecha | Objeto |
|---|---|---|
| `00-INDICE/FINAL-RESEARCH-STATUS.md` | 2026-09-19 | cierre de la sesión de investigación |
| `RELEASE-CANDIDATE.md`, `FINAL-RELEASE-REPORT.md`, `RELEASE-EXCLUSIONS.md` | 2026-09-25 | candidato a publicación |
| `PROYECTO_STATUS.md`, `CIERRE_PROYECTO.md` | 2026-09-29 | cierre del compresor/descompresor |

`00-INDICE/README.md` ya declaraba canónico a `MASTER-RESEARCH-STATUS.md` y
histórico a `FINAL-RESEARCH-STATUS.md`. Este documento no sustituye al primero:
lo complementa con la capa de driver, que el maestro no cubre.

---

## 1 · Estado vigente — 2026-09-29

**`PROYECTO_STATUS.md`, `CIERRE_PROYECTO.md`**

```
Estado global   Fase 1 completa. Fase 2 completa.
Tag             v1.0-fase2-completa
Estado          COMPLETO con evidencia de hardware
```

### Qué es cierto y cómo se comprobó

El descompresor **se ejecuta en la RX 550** y su salida coincide **byte a byte**
con el decodificador de CPU: **0 discrepancias sobre 4096 bloques, 3 corridas**.

El test **discrimina**, y eso se demonstrated, no supuesto: la referencia
`test_alpha_ramp_independent.c` se comparó contra la especificación Microsoft
(que redondea), no contra `bcdec v0.985` (que trunca). Con la referencia nueva se
insertó el mutante deliberado y el mutante fue rechazado:

```
$ make check-ramp-discriminates
  total : 65536 / 65536 pares con discrepancia
  peor error : 255 de 255
  RESULT: NO CONFORMA con la especificacion -- 65536 pares discrepan
  OK: rejected the known-wrong ramp (exit 1). The test discriminates.
```

Un test que compara la implementación contra sí mismo siempre pasa. Este no.

### Cifras medidas (host y momento concretos; no portables entre equipos)

| Métrica | Valor |
|---|---|
| Checks del compresor | **26/26 `[ OK ]`**, 0 `[FAIL]` |
| Conformidad con la especificación Microsoft | `CONFORMA`, rampa alfa `+3`/`+2` |
| Convenciones de endpoint | `a0 = max`, `a1 = min` (D19a, commit `44bc133`) |
| Inset de endpoints alfa | `RX550_ALPHA_INSET_STEPS 0` (AD-10) |
| PSNR | reference **28.78** dB · smooth **19.59** · pure noise **13.65** · adversarial **10.90** |
| Throughput | C **83.7** MB/s · AVX2 **86.0** MB/s → speedup **1.03×** |
| AVX2 bit-idéntico al C | sí, sobre 200000 bloques |

El throughput depende de la carga de la máquina. Es un número de esta host en
este momento, no una propiedad del código.

### Decisiones que gobiernan lo anterior

- **AD-8** — BC3/DXT5 estándar confirmado; `RX550_BC4X` descartado.
- **AD-9** — BC3 usa truncamiento puro; los offsets `+3`/`+2` quedan **retirados**.
- **AD-10** — la búsqueda de inset alfa cuesta **2,8×** y no compra calidad medida.
- **AD-11** — divergencia entre la especificación Microsoft y `bcdec v0.985`.

### Lo que este estado NO establece

- El shader no es el sampler. Adjuntar la textura DXT5 como color attachment de un
  FBO y leer con `glReadPixels` **sigue sin ejecutarse**.
- La validación de esquema SPIR-V sigue `NOT_AVAILABLE` sin `spirv-val`.
- **Un dispatch no mide throughput.** No hay cifra de rendimiento del descompresor
  en GPU.
- El corpus es determinista y sintético: es guarda de regresión en hardware real,
  no prueba sobre todos los bloques posibles.

---

## 2 · Estado de publicación — 2026-09-25

**`RELEASE-CANDIDATE.md`, `FINAL-RELEASE-REPORT.md`, `RELEASE-EXCLUSIONS.md`**

```
Candidate ID          RX550-FINAL-20260925
Fuente                Nobara 43 · kernel 6.18.2 · Mesa 25.3.2 · host 1002:699f
Modo de validación    READ_ONLY/EVIDENCE + pruebas estáticas

READY_FOR_GITHUB      NO
SECURITY_REVIEW       NOT_READY
```

La publicación está bloqueada por higiene y seguridad del árbol, no por el
compresor. `RELEASE-EXCLUSIONS.md` conserva la lista de lo que queda fuera y la
razón de cada exclusión. Las exclusiones **no borran**: la evidencia permanece en
el árbol local y en el commit baseline.

El informe final declara explícitamente que **no** declara una release final.

---

## 3 · Estado del host y la instalación — 2026-09-19, reconciliado 2026-09-24

**`00-INDICE/FINAL-RESEARCH-STATUS.md`**, **`PROBLEM-STATUS-FINAL.md`**

Este cierre es el que声响 más, y el que más se malinterpreta:

```
Gate P0 (2026-09-24)   B. CONTAMINATED_REQUIRES_ISOLATION
Cap vigente            35 W, DPM automático
Autores activos        kalm, kalm-gpu, system-autopilot, otros; hay clientes de la RX550
Display                Intel HD 4600
GPU objetivo           RX 550 1002:699f, secundaria, sin salida de vídeo en el snapshot
```

`1002:699f` es **la identidad PCI**, y `amdgpu` la asignó a `card1`. Eso no la
convierte en `card0`. Cualquier lectura que la dé por `card0` está equivocada.

### La medición que no discrimina

```
power1_input @35 W = 12.27 W  ->  compuerta <27 W activada  ->  NO DISCRIMINATIVO
```

El cap no se separates del suelo del sensor. Un valor por debajo del umbral **no
demuestra** que el cap actuara. Y `power1_input` es un **estimador del SMU**, no
un vatímetro independiente: hoy reporta valores reales donde antes reportaba un
plano, lo que significa que **el sensor cambió de comportamiento**, no que la
medición nueva sea más buena.

### Los ocho estados que admite la matriz de problemas

`RESOLVED`, `PARTIALLY_RESOLVED`, `UNRESOLVED`, `OBSOLETE`,
`ALREADY_FIXED_UPSTREAM`, `NOT_REPRODUCED`, `UNKNOWN`, `NOT_AVAILABLE`.

`NOT_REPRODUCED` significa que el síntoma no apareció en la comprobación actual.
**No** significa que su causa histórica esté resuelta. Un hecho observado no se
convierte en causalidad.

---

## 4 · Lo que sigue abierto

```
Sobre el compresor      fuera de laYC3: rendimiento en GPU sin medir, sampler sin ejecutar
Sobre publicación      SECURITY_REVIEW=NOT_READY, READY_FOR_GITHUB=NO
Sobre el host          Gate P0 en B: contaminated_requires_isolation, sin tuning autorizado
Sobre el proyecto      1003 huecos abiertos en 276 findings
                        (OPEN-FRONTIERS.md, vista generada el 2026-10-03 14:57:47)
                        vía: SPEC_NO_PUBLICADO 332 · RUNTIME_ACTIVO 276 · POR_DEFINICION 132
                             UN_REGISTRO 104 · SIN_PISTAS 91 · DIFERENCIAL 68

                        El registro tiene 504 findings en disco. La vista generada
                        cuenta 276 porque solo cuenta los que_ports relaciones; los
                        228 restantes aparecen sin aristas en KNOWLEDGE-GRAPH.md.
                        La cifra se mueve entre regeneraciones: 989 a las 14:51,
                        1003 a las 14:57.
```

`SIN_PISTAS` son los únicos 91 para los que ningún texto del proyecto dice cómo
cerrarlos.

## 5 · Dónde está la evidencia, no el estado

Este documento es estado. La evidencia no está aquí:

- **504 findings** en `06-INGENIERIA-INVERSA/findings/` — fuente primaria.
  `KNOWLEDGE-GRAPH.md` mide 96 de sus aristas con destino ambiguo porque el
  número no identifica a un finding. **Para citar, usar el nombre del fichero.**
- **9 vistas generadas** en la raíz por `tools/artifacts.py`. Declaran
  `NO EDITAR A MANO`; su desfase respecto al disco es esperado, no error.
- **Índice canónico**: `00-INDICE/README.md`.
- **Protocolo**: `COORDINACION.md`. **Autoridad del prompt**: `AGENTS.md`.
