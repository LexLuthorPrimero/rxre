# RX COMPRESSION ENGINE — Documento de Diseño del Proyecto

> **Archivo:** `projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.16)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [IDEA]. **PROVISIONAL RESEARCH PROJECT** — hipótesis de optimización de memoria.
> **Estado global:** **IDEA**. No se ejecutó ni se escribió código.

---

## 1. OBJETIVO

Evaluar si **comprimir datos en la ruta de memoria** (texturas, buffers, datos intermedios) puede
**aumentar el ancho de banda efectivo** (más datos útiles por byte transferido por VRAM/GTT/PCIe) en
Polaris12, y en qué casos el coste de descompresión **no compensa**. Es una pregunta de **bandwidth vs
latency vs coste de CPU/ALU**, no un motor a implementar ya.

## 2. ÁREAS DE APLICACIÓN (diseño conceptual)

| Área | Dónde vive | Ahorro potencial | Coste |
|---|---|---|---|
| **Texturas** | VRAM/L2 (sample texture) | menos bytes/transferencia, mejor hit L2 | descompresión en muestreo (HW ya lo hace con formatos comprimidos nativos como BC/ASTC) |
| **Buffers/vertex** | GTT/VRAM/PCIe (fetch) | menos PCIe si vía GTT | descompresión en vertex fetch; paralelismo de CU vs fetch |
| **Datos intermedios** (render target/RO) | VRAM (CB writes) | DCC ya existe en HW — la compresión SW de RO suele perder | complejidad alta, poco margen |
| **GTT/system RAM** | host + PCIe | si el working set cabe comprimido en GTT | latencia extra de descomprimir en la GPU |

## 3. CASOS EN QUE PODRÍA AYUDAR / NO AYUDAR (hipótesis revisables)
- **PODRÍA AYUDAR:** datos read-heavy con baja entropía (texturas tipo cache de sprites), WHERE la GPU
  ya pierde BW por fetch (F2) y el trabajo de descompresión es menor que la latencia ahorrada.
- **NO AYUDA:** datos write-heavy / de alta entropía (resultados de ALU), o con descompresión en camino
  crítico que añada latencia > ahorro; y en nuestro caso power-limited (E3), el extra de SCLK del trabajo
  de descompresión puede superar el ahorro.

## 4. CÓMO SE MEDIRÍA (diseño de experimento)
- A/B sobre el mismo workload (FETCH/texturas): comprimido (BC/ASTC nativo) vs sin comprimir, midiendo:
  `mem_busy`, frametime p50/p99, power, **y supra (si D-3 autorizado) tráfico VRAM/GTT**.
- La métrica decisiva: **FPS/frametime frente a MB transferidos**, con definición exacta del "MB"
  (NO usar mem_busy como BW, METRICS-DEFINITIONS).
- Verificar que la descompresión NO sobrecarga CU de tal modo que `shader_busy` suba con power.

## 5. WORKLOADS
- Sintético TEXTURE (modo de R-2.9) con texturas nativas (BC) vs UNORM; y FETCH con buffer comprimido en
  shader (descompresión en CU). Ambos ya existen conceptualmente en el diseño del sintético.

## 6. GPU vs CPU tradeoff
- La compresión SW en CPU (antes del upload) ahorra BW GPU pero cuesta CPU (i7-4790) → medir el delta en
  la cola gráfica (frametime) y el CPU (IPC). Si la CPU no da abasto, no se recomienda esa vía.

## 7. CONFOUNDERS
- DCC existente en HW (no confundir con nuestra compresión SW).
- Migración TTM (GTT/VRAM) puede degradar la comparación → fijar alojamiento (G-M1).
- Potencia/hermó (E3/E5) puede enmascarar; usar rangos "steady".

## 8. DEPENDENCIAS
FASE G (modelo de memoria, G-M2/G-M4), FASE K (runner), design del workload sintético (módulo TEXTURE).
Si requeriera contadores → FASE M. **Nada se implementa aquí.**

## 9. CONCLUSIÓN
RX Compression Engine es **IDEA, PROVISIONAL**, con diseño conceptual de áreas, mécase de medición y
confounders. **No se ejecutó ningún experimento ni se afirma beneficio.** Su viabilidad depende
exclusivamente de las mediciones de FASE G y del gate de la Matriz J.