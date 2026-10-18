# Después de toda esta charla: así escalaría rxre

Una sola regla antes de la respuesta:

> **No escalás rxre. Escalás la cantidad de investigaciones difíciles que rxre resuelve correctamente sin perder trazabilidad.**

Todo lo demás es consecuencia.

---

## La secuencia

```
AUDIT A–F  →  DELIVERED  →  CHALLENGED  →  ACCEPTED
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │    ETAPA 1      │
                                    │ un plano,       │
                                    │ un test,        │
                                    │ un commit       │
                                    └────────┬────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     ▼                       ▼                       ▼
              ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
              │  ETAPA 2    │        │  ETAPA 3    │        │  ETAPA 4    │
              │ dos planos  │        │ ciclo       │        │ A vs B      │
              │ que hablan  │        │ completo    │        │ controlado  │
              └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
                     │                      │                      │
                     └──────────────────────┼──────────────────────┘
                                            ▼
                                    ┌─────────────────┐
                                    │    ETAPA 5      │
                                    │ iniciativa      │
                                    │ acotada         │
                                    └────────┬────────┘
                                             ▼
                                    ┌─────────────────┐
                                    │    ETAPA 6      │
                                    │ multi-instancia │
                                    │ sobre TIERRA    │
                                    └────────┬────────┘
                                             ▼
                                    ┌─────────────────┐
                                    │    ETAPA 7      │
                                    │ exterior real   │
                                    └─────────────────┘
```

Cada flecha es una **puerta**, no un paso. No se entra a la siguiente sin que la anterior pase su gate.

---

## Las 5 reglas que hacen que esto funcione

**1. Un plano a la vez.**
Si entran dos juntos, no sabés cuál causó el éxito. Perdés atribución causal. Es la misma regla del audit, aplicada a construir.

**2. Un test adversarial por plano, antes del comando.**
El test es el caso donde el comando **miente**. Si nunca falla, el test es cosmético. Si el comando no tiene test adversarial, no existe.

**3. El rollback es una decisión válida.**
Si una etapa cuesta más de mantener que el beneficio que da, se revierte. Documentado. Sin vergüenza. Un sistema que solo crece no escala.

**4. El audit no se reabre.**
Una vez `ACCEPTED`, las conclusiones del audit son la línea base. Si una etapa posterior contradice el audit, se investiga — pero no se reescribe el audit para acomodarlo.

**5. El banco de pruebas crece con los modos de fallo, no con las ganas.**
Nivel 1 (código) → Nivel 2 (binario) → Nivel 3 (hardware) → Nivel 4 (investigación prolongada). Se agrega un nivel nuevo solo cuando aparece un modo de fallo que los anteriores no atrapan.

---

## Cómo se mide que escala

Dos métricas primarias, no ocho:

```
1. Falsos positivos aceptados   ← debe bajar
2. Coste por hallazgo validado  ← debe bajar o mantenerse
```

Todo lo demás (claims reproducibles, hipótesis discriminadas, reutilización correcta) son **secundarias**: explican por qué las primarias se mueven, pero no las reemplazan.

Si una etapa mejora las secundarias y empeora las primarias, **no es una mejora**. Es complejidad agregada.

---

## Etapa 1, en concreto

Cuando vuelva `ACCEPTED`:

```
1. Leer claims.csv
2. Encontrar el plano con peor estado (CONTRADICTED > OPEN > UNVERIFIED)
3. Escribir SU test adversarial
4. Correrlo → falla (porque el plano no es real todavía)
5. Escribir el comando mínimo que lo haga pasar
6. Correr el test → pasa
7. Quitarlo y ver si rompe algo → si no rompe, no era un plano
8. Commit
```

Un plano. Un test. Un commit. Después el siguiente.

Ocho veces. Sin paso 9.

---

## Lo que NO haría, dicho de una vez

```
✗ Ocho carpetas con ocho clases
✗ Un README por plano antes de un test por plano
✗ "Integrar los 8 planos" como objetivo
✗ Agentes en paralelo antes de que la coordinación pruebe valer más que el conflicto
✗ Declarar éxito porque los tests pasan
✗ Escalar sobre un audit que no fue aceptado
```

---

## La respuesta en una línea

**Escalar rxre es aplicar siete veces el mismo protocolo cerrado —audit → puerta → un plano → test adversarial → rollback si falla— a superficies cada vez más grandes, midiendo siempre con falsos positivos y coste por hallazgo, y sin abrir la Etapa N+1 hasta que la N haya pasado su puerta.**

No hay ronda de diseño nueva. No hay adenda D. Hay una auditoría esperando resultados, y después ocho commits honestos.

Eso es todo.
