# FASE B — Probe de power cap 25/28/32/35 W (únicos writes autorizados: power1_cap)
Fecha: 2026-09-19 · RX550 stock Mesa · 28 corridas N=2 · sampler 10 Hz con cap por muestra
Protocolo: desde frío (37 C), cooldown a <=50C entre estados, orden caps 25->28->32->35, ablación,
trap de restauración al cap original (35 W). Sin aborts. Sistema verificado restaurado al final.

## Resultado por cap (mediana de ventana estable busy>=30%)
cap  W | 640p GL jelly   SCLK/pow/temp   | 640p VK phong   | 640p VK default | 1080p GL jellyfish
25 W    | 1228-1233 fps  1071/10.7W/42-44 | 404 fps 1071/11.3W/46-48 | 403-407 1071/11.2W/49-50 | 203-204 fps SCLK 1071 pow 9.6W T51-52
28 W    | 1241-1250 fps  1071/10.5-10.6W/53-54 | 409-412 1071/11.6W/55-56 | 407-411 1071/11.6W/57-58 | (no)
32 W    | 1239-1246 fps  1071/10.8W/55-56 | 409 1071/11.6W/57-58 | 411-413 1071/11.6W/59-60 | (no)
35 W    | 1245-1246 fps  1071/10.8W/55-56 | 409-413 1071/11.6W/57-58 | 408-411 1071/11.6W/59-60 | 203 fps SCLK1071 pow 9.6-9.7W T60

## Veredicto del discriminador
- **El régimen E1/E3 (25 W CLVADO / SCLK ~340-400 / 75-79 C) NO se reproduce con cap 25 W desde frío.**
  A cap 25 W hoy: SCLK 1071 MHz (boost pleno), potencia 10.7-11.6 W (nada clavada, muy por debajo del cap),
  temperatura 42-60 C, FPS idénticos a 28/32/35 W.
- La curva de cap es **PLANA para 640p**: 25->35 W no cambia SCLK, potencia ni FPS. El cap NO liga.
- A 1080p GL jellyfish los caps 25 y 35 W TAMBIÉN quedan planos (203 fps, 1071 MHz, 9.6 W) -> NO reproduce
  el comportamiento que E5 atribuyó al cap a 1080p (SCLK 390 @25W vs 600-750 @35W; P 25-31 W).
  => el workload de E5 debió ser más pesado (o estado/telemetría distinta). UNKNOWN O5 (reconciliar E5).

## Qué significa para las hipótesis
- H1 'cap liga en 640p' -> REFUTADA de plano (curva plana 25-35W).
- H4 'resolución decide si liga' -> MATIZADA/RECHAZADA para jellyfish 1080p de hoy (plano); el cap ligaba en E5
  con otro workload/estado. La resolución NO es suficiente.
- Nuevo hecho: el SMU NO baja el SCLK por un cap no alcanzado; cuando la potencia demandada (10-12 W) es
  << cap, el boost es pleno y el cap irrelevante.
- La firma E1/E3 (P==cap, SCLK bajo, T alta) NO es un efecto simple de cap; queda explicada por uno de:
  (a) SOAK térmico: la tarjeta llegó a 75-80 C sostenida (como E5, que alcanzó 88-92 C) y el SMU entró en
      regulación por objetivo de potencia con el cap de 25 W; proceso NO alcanzado en nuestros protocolos
      cortos/fríos (máx 60 C).
  (b) Anomalía de telemetría/muestreo en E1/E3 (card equivocada o estado fantasma).
  Experimento que separa (a) vs (b): EP-06 (soak térmico sostenido a cap 25 W hasta 75-80 C, luego medir).

## Corrida de validación cruzada (resultados idénticos a Fase A)
- 640p GL jelly 7 fps ~1228-1250 (Fase A: 1169-1237; E1/sweep: 1035-1187) -> banda estable ~1200.
- 640p VK phong 404-413 (Fase A: 396-400) -> consistente.
- 640p VK default 403-413 (Fase A: 403; sweep: 347-351).
- Poder de GL jelly 640p ~10.5-10.8 W; VK ~11.2-11.6 W.