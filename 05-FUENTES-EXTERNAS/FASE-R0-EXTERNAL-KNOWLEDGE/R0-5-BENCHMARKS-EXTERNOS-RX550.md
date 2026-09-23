# R0-5 — Benchmarks externos RX 550 (Polaris12) y contexto de rendimiento

> **Archivo:** `R0-5-BENCHMARKS-EXTERNOS-RX550.md`
> **Fase:** FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [VERIFICADO] (reviews técnicas publicadas con datos; cifras concretas origen del
> propio review, no del proyecto — no representan medición en la unidad del usuario)

---

## 1. Ficha de partida (definición del SKU benchmarkeado)

- Tom's Hardware (2017-04-27): "AMD Radeon RX 550 2GB review", GPU de referencia **512 SP /
  1183 MHz boost / 128-bit / 2 GB GDDR5**, 50 W TDP, sin conector auxiliar.
- Propósito declarado: esports/1080p medio. Posición: el RX 460 (Polaris11) era claramente más
  rápido en su mismo rango de precio.

## 2. Datos publicados relevantes (referencia de rendimiento y potencia)

| Métrica | Valor publicado | Fuente |
|---|---|---|
| Rendimiento gaming 1080p | esports jugables; AAA mainstream solo a 720p/bajos | TH |
| Posición de mercado | RX 460 > RX 550 en rendimiento bruto; Necesita minoristas | TH |
| Potencia gaming (peor caso) | ~47 W (juego) | TH / Igor'sLAB |
| VCore/boost en carga | boost ~1141–1164 MHz en bucle de juego (max boost real < 1183) | Igor'sLAB |
| Power virus | ~820 MHz promedio estrés sostenido (thermal/APU) | Igor'sLAB |

Cifras de rendimiento puro (FPS) en juegos concretos NO se transcriben aquí por dos motivos:
1. No son comparables 1:1 con la unidad del proyecto (cap 35 W, drivers Linux/Mesa, refrigeración,
   VRAM 4 GB vs 2 GB según modelo).
2. El proyecto ya tiene mediciones locales propias (Superposition score 804, GravityMark, etc.)
   que son la referencia operacional.

## 3. Contexto para el proyecto

- Externamente el "régimen de referencia" del RX550 (50 W, boost alto) está lejos del régimen
  observado en la unidad (cap 35 W, SCLK 1071, draw ~13 W actual): el proyecto NO mide problemas
  de potencia sino una configuracion muy restringida.
- VCore/boost externo (1141–1164 MHz gaming, bajas a 820 MHz en pila de estrés) explica parte de
  por qué el draw máximo medido en Superposition (23.7 W pico) es sensiblemente menor al TDP
  nominal (50 W): es el mismo ASIC con throttling térmico/eléctrico y política DPM de fábrica.
- No se identifica contradicción entre estos datos y las hipótesis R-07 (MCLK) ni con FASE C
  (Superposition) → compatibilidad documental lograda.

## 4. Fuentes

1. Tom's Hardware — Radeon RX 550 2GB Review (2017-04-27):
   https://www.tomshardware.com/reviews/amd-radeon-rx-550-2gb,5034.html
2. Igor'sLAB — RX 550 (datos de potencia/boost del ASIC de referencia):
   https://www.igorslab.de/ (review RX 550; búsqueda específica disponible)
3. VideoCardz — Lexa PRO spec database:
   https://videocardz.net/amd-radeon-rx-550
4. TechPowerUp — GPU database RX 550:
   https://www.techpowerup.com/gpu-specs/radeon-rx-550.c2905

## 5. Confianza y límites

- [VERIFICADO] existencia y rangos de las cifras citadas (fuentes consultadas).
- Los números exactos de temperatura/fan/FPS dependen del modelo de tarjeta; no forman parte del
  marco de conclusiones del proyecto, solo de contexto.
- Nada de lo anterior modifica hipótesis locales; se documenta como conocimiento externo de
  referencia (objetivo de la FASE R-0).