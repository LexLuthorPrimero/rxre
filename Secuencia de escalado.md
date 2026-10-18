Escalaría RXRE mediante expansión progresiva de la superficie verificada, manteniendo constantes el método, los criterios de evidencia y la posibilidad de rollback.

La conversación deja una decisión central: no diseñar otra arquitectura ahora. El protocolo A-F ya existe; lo que falta es evidencia de su ejecución.

## Secuencia de escalado

## 00

Auditoría y aceptación

Ejecutar A-F en solo lectura, entregar los artefactos, intentar refutar tres claims críticos y resolver cualquier refutación reproducible.

Gate: `STATE=ACCEPTED` por revisión independiente.

## 01

Un plano end-to-end

Elegir el plano con el peor estado demostrado por el audit. Implementar únicamente la capacidad mínima necesaria.

Gate: comando invocable, test adversarial, estado observable en `rxre status` y uso probado en un flujo real.

## 02

Integración de dos planos

Conectar el plano validado con su dependencia natural. Comprobar el efecto causal, su traza y su reproducción.

Gate: evento, efecto observable y traza reproducible sin acoplamiento accidental mediante estado global mutable.

## 03

Ciclo completo

Ejecutar una investigación real sobre un artefacto identificado por hash.

Gate: presupuesto de pasos definido de antemano, interrupción, reanudación tras matar el proceso e informe reproducible.

## 04

Comparación A/B

Comparar el flujo actual con el flujo de ocho planos explícitos sobre el mismo problema, con sesiones aisladas y presupuestos comparables.

Gate: métricas primarias registradas y resultado interpretable. Si es inconcluso, no se declara mejora.

## 05

Iniciativa autónoma acotada

Permitir que RXRE inicie investigaciones sin un prompt humano inmediato.

Gate: presupuesto duro, kill switch probado, auditoría de decisiones y supervisión visible del estado.

## 06

Concurrencia

Permitir dos instancias sobre el repositorio y la base de evidencia compartidos.

Gate: coordinación o bloqueo demostrado, recuperación ante corrupción inyectada y aislamiento entre investigaciones.

## 07

Interacción con el exterior

Ampliar el alcance a hardware, APIs y otros agentes.

Gate: aislamiento, errores tipados, auditoría de entradas y salidas y reversión cuando la acción lo permita.

## La regla de cada puerta

Ninguna etapa se supera solo porque sus tests pasan.

Antes de avanzar, exigiría:

1. Capacidad: existe y se utiliza en el flujo real.
2. Refutación: una prueba adversarial puede detectar cuándo falla.
3. Aislamiento: quitar la capacidad no rompe otras capacidades independientes ni revela dependencias ocultas.
4. Evidencia: los resultados pueden reconstruirse sin depender de la memoria del agente.
5. Economía: el beneficio justifica el coste de implementación y mantenimiento.
6. Reversibilidad: existe un rollback cuando el cambio no aporta valor.

Cada etapa modifica una sola capacidad nueva. Si falla, se corrige esa causa y se repite el gate; si el coste supera el beneficio, se revierte.

## Qué mediría en toda la secuencia

| Métrica                     | Pregunta que responde                                           |
| --------------------------- | --------------------------------------------------------------- |
| Exactitud                   | ¿Las conclusiones son correctas?                                |
| Reproducibilidad            | ¿Un tercero puede verificar los resultados?                     |
| Poder discriminante         | ¿Las pruebas distinguen causas rivales?                         |
| Reutilización               | ¿RXRE aprovecha hallazgos anteriores sin contaminar su certeza? |
| Recuperación                | ¿Puede reanudar una investigación interrumpida?                 |
| Coste por hallazgo validado | ¿La mejora compensa sus recursos?                               |
| Regresiones                 | ¿La nueva capacidad perjudica lo que ya funcionaba?             |

El objetivo final no es tener ocho nombres, más comandos o más agentes. Es que RXRE pueda investigar problemas más complejos manteniendo la exactitud, la procedencia y el control operativo.

## La decisión inmediata

No tocaría el código todavía. Primero comprobaría que el audit A-F existe y ha producido artefactos nuevos. Si no existe, resolvería el bloqueo de ejecución en lugar de seguir ampliando el protocolo.

El primer cambio de código solo se elegiría después de `ACCEPTED`, basándose en el mapa real de capacidades y en el defecto de mayor impacto demostrado por la auditoría.

Ese es el escalado que aplicaría: una capacidad, una prueba adversarial, una validación independiente y una puerta superada antes de ampliar la superficie.
