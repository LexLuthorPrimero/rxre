# R-2.21 — R2-DEPENDENCY-GRAPH — Grafo de Dependencias del Ecosistema

> **Archivo:** `R2-DEPENDENCY-GRAPH.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.21)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [DISEÑADO]. Cada arista lleva marca de fuerza: CONFIRMADA / PROBABLE / POTENCIAL.
> **Reconciliación 2026-09-24:** las aristas de *coordinación* entre Orquestador y
> F/G/K/L/M/O/P/Q no son dependencias de orden; el grafo de ejecución se considera
> acíclico. Ninguna arista autoriza programación o escritura.

---

## 1. Nodos del grafo

- **Base:** R-0 (External Knowledge Recovery), R-1 (Reconciliation), WORKLOAD-SINTETICO, rx550-torneo,
  FASE D (contadores auditados), POLARIS12-MAP, M1, R-14/Superposition.
- **Diseñadas en R-2:** E (real-game), F (geometry), G (memoria), H (workaround), I (PowerPlay),
  J (matriz), K (lab), L (tuner), M (contadores) con N (ecosistema) , O (gestores), P (FG/upscale),
  Q (Mesa). Protege projects: Ghost, Ghost-Cache, BERRETA, RX-Compression-Engine, Orquestador.

## 2. Grafo (DFS desde base)

```
R-0 (event IDs, powerplay, arch, workarounds, tools)   [VERIFICADO source-level]
  ├──► R-1 (reconciliación GFX8)  [COMPLETADA]  ──► M (estado del catálogo) [PARTIALLY_RECONCILED]
  ├──► FASE D et.3 (contadores programados) [NO AUTORIZADO; el catálogo NO habilita]   [BLOQUEADO]
  └──► FASE M (PolarisLens etc.)   [PARTIALLY_RECONCILED]  ──► GHOST (hit-rate caché, si medible) [POTENCIAL]

WORKLOAD-SINTETICO (E-01..E-03, ES-01, F2, DESIGN-GRAPHICS)
  ├──► R-2.9 synthetic workload design  [CONFIRMADA]
  ├──► F (GEO-01..08)   [CONFIRMADA: requiere workload gráfico + pipeline stats]
  ├──► G (M1..M5)       [CONFIRMADA: G-M1/M5 usan el sintético]
  └──► H (H-1..H-7)     [PROBABLE: interpreta resultados existentes]

E (real-game)        [CONFIRMADA dep: autorización de instalación; refinída]
  ├──► FASE E vs Superposition (not comparable)   [CONFIRMADA]
  └──► G (comparativa de memoria en juego)        [POTENCIAL]

F ──► J (priority matrix)   [CONFIRMADA]
G ──► J ──► K (runner)      [CONFIRMADA]
H ──► F (interpretación GEO-05/07)   [POTENCIAL]
H ──► Q (candidata de código)        [POTENCIAL]
I ──► L (tuner; contratos/interfaces) y J (riesgo) [CONFIRMADA para diseño]
I ──► L: cualquier write pertenece a un frame L futuro, no crea dependencia inversa

K (lab) ──► L (runner A/B), M (mediciones)   [CONFIRMADA]
K (lab) · Orquestador: coordinación bidireccional, no dependencia de orden [COORDINACIÓN]
L (tuner) ──► rx550-torneo (evalúa, NO reemplaza)         [CONFIRMADA]
L ──► I (feedback/interfaces; no orden), G-M3 (riesgo)       [COORDINACIÓN]

G ──► GHOST (prefetch/localidad)   [POTENCIAL → solo si G-M1/G-M5 dan señal]
G ──► RX-Compression-Engine (bandwidth)   [POTENCIAL → solo si G-M2/G-M4]
F/H/I ──► BERRETA (async NEED confirm con ASY-01) [POTENCIAL]
P (FG/upscale) ──► E (juego real: la capa se evalúa sobre el mismo) [PROBABLE]
O (gestores) ──► Orquestador (tabla cap-habilidad) [PROBABLE]
Q (Mesa) ──► L/M/Orquestador (observaciones) [PROBABLE]

Orquestador (R-2.17) ──► K, L, M, O, P, Q   [COORDINACIÓN; no es orden]
```

## 3. Tabla de aristas con fuerza

| Origen | Destino | Fuerza | Justificación |
|---|---|---|---|
| R-0 | M | PARTIALLY_RECONCILED | M cita el catálogo R-0/R-1; no habilita programación |
| R-0/R-1 | FASE D et.3 | BLOQUEADO | catálogo + reconciliación no autorizan programming; falta tupla ASIC/autorización |
| M | GHOST hit-rate | POTENCIAL | Ghost necesita contadores para validar mecanismo |
| WORKLOAD | R-2.9 (diseño) | CONFIRMADA | reusa main/main-graphics |
| WORKLOAD | F | CONFIRMADA | GEO necesita el workload gráfico |
| WORKLOAD | G | CONFIRMADA | G-M1/M5 usan sintético |
| WORKLOAD | H | PROBABLE | H-1 interpreta E3/E5 cocientes |
| E | G | POTENCIAL | si un juego real valida el modelo de memoria |
| F | J | CONFIRMADA | fichas entran a matriz |
| G | J | CONFIRMADA | ídem (G-Mx) |
| G | GHOST | POTENCIAL | el proyecto GHOST depende de señal de G-M1/M5 |
| G | RX-Compression-Engine | POTENCIAL | idem G-M2/M4 |
| H | Q | POTENCIAL | H-5/6/7 = observación de código para Q |
| I | L | CONFIRMADA (diseño) | L usa contratos/interfaces de I; no habilita I→L→I |
| L | I | COORDINACIÓN | feedback de interfaces; no dependencia de orden |
| J | K | CONFIRMADA | prioridad guía qué ejecuta K |
| K | L | CONFIRMADA | L usa runner/validación de K |
| K | M | CONFIRMADA | M mide con runner K |
| L | rx550-torneo | CONFIRMADA | evalúa, no reemplaza (R1-8) |
| L | G-M3 | PROBABLE | riesgo OOM de G-M3 debe entrar al frame de autorización |
| F/H/I | BERRETA | POTENCIAL | BERRETA requiere validar overlap (ASY-01) y sistema power-limited |
| P | E | PROBABLE | FG/upscale se evalúa sobre el mismo workload real |
| O | Orquestador | PROBABLE | tabla de capacidades de gestores para decisión |
| Q | Orquestador | PROBABLE | observaciones de Mesa alimentan decisión |
| K/L/M/O/P/Q | Orquestador | COORDINACIÓN | Orquestador coordina; no es una dependencia de orden |

## 4. Lecturas clave del grafo
- **Coordinación ≠ ciclo:** Orquestador puede recibir estado de F/G/K/L/M/O/P/Q y
  devolver coordinación, pero eso no crea una dependencia de orden inversa.
- **El cuello para la ejecución** es `WORKLOAD→F/G` y `K→L/M`: hay que implementar el launcher sintético
  (futuro) y el Lab antes de las cosas de mayor riesgo (L/M).
- **Ghost y RX-Compression-Engine** NO tienen aún camino CONFIRMADO hacia la ejecución: dependen de que
  G-M1/G-M5 (y G-M2/G-M4) den señal. Son **POTENCIAL** genuinamente bloqueados por evidencia.
- **BERRETA** depende de validar ASY-01 y del régimen power-limited (E3/E5) → potencia de baja prioridad
  hasta I/L.
- **Ninguna arista concede autorización de ejecución**: el grafo es de conocimiento, no de permiso.
