# Escalar no es construir más. Es aplicar el mismo método a una superficie más grande.

El protocolo ya está cerrado. Escalar **no es agregar diseño**. Es tomar la misma vara —comando, test adversarial, quitar y ver si rompe— y aplicarla a superficies cada vez más grandes.

Lo que escala es la **superficie de lo probado**, no la ambición de lo construido.

---

## La regla que no cambia

```
Cada etapa es una PUERTA, no un paso.

No se entra a la etapa N+1 hasta que:
  [ ] la etapa N pasó su gate
  [ ] se documentó qué se aprendió
  [ ] se midió el costo de mantener lo agregado
  [ ] el audit previo sigue vigente
```

Si saltás una puerta, el sistema crece en superficie de falla más rápido que en capacidad. Eso es lo que pasó con los proyectos que se ven bien y se rompen a los 6 meses.

---

## Las 7 etapas

### Etapa 0 — Audit entregado y verificado

```
Superficie:  el repo tal como está
Gate:        DELIVERED → CHALLENGED → ACCEPTED
             (con el protocolo que ya acordamos)
Falla si:    nadie intenta refutar 3 claims
Costo:       0 (no se toca código)
```

**Sin esta etapa no hay escalada.** Escalar sobre una arquitectura que no entendés es duplicar lo que ya existe.

---

### Etapa 1 — Un plano, end-to-end

```
Superficie:  el plano con peor estado en el audit
Gate:        su test adversarial pasa
             + su comando es invocable desde `rxre`
             + su estado aparece en `rxre status`
Falla si:    el test pasa pero el comando no se usa en el flujo real
Costo:       1 archivo, 1 test, 1 línea en el mapa
```

Elegís **uno solo**. El peor. No el más fácil ni el más divertido. El que más rompe si está mal.

---

### Etapa 2 — Dos planos que se hablan

```
Superficie:  el plano 1 + el plano con el que naturalmente interactúa
             (TIERRA↔CUERPO, MENTE↔AGUA, FUEGO↔TIERRA, etc.)
Gate:        un evento del plano A produce un efecto observable en B
             + el efecto se registra en ÉTER con `--trace`
             + se puede reproducir desde `commands.log`
Falla si:    el efecto depende de estado global mutable
             (señal de que el bus no existe)
Costo:       refactor de uno de los dos, no de ambos
```

**Regla**: si los dos planos comparten estado global, no están hablando por el bus. Están acoplados. Se arregla antes de pasar.

---

### Etapa 3 — Un ciclo completo

```
Superficie:  los 8 planos, en un solo ciclo acotado
Gate:        un problema real, con artefacto real, con hash
             + el ciclo termina en ≤ N pasos (N definido antes)
             + se puede cortar con `rxre eter panic`
             + se puede reanudar si se mata el proceso
             + queda un informe reproducible
Falla si:    el ciclo nunca termina, o termina por timeout sin reportar
Costo:       el primer `rxre eter loop` de verdad
```

**Esta es la etapa que separa "modelo conceptual" de "modelo operativo".** Todo lo anterior era preparación.

---

### Etapa 4 — La comparación controlada

```
Superficie:  A (flujo actual) vs B (8 planos explícitos)
             sobre el MISMO problema, MISMO artefacto, MISMO presupuesto
Gate:        A y B aislados (sesiones separadas, semilla registrada)
             + métricas primarias medidas
             + resultado puede ser INCONCLUSIVE
             + si B no mejora, la hipótesis se descarta o se corrige
Falla si:    A y B comparten contexto
             o el orden de corrida correlaciona con el resultado
Costo:       2 corridas completas + análisis
```

**Esta etapa es la única que puede decir si los 8 planos sirven.** Sin ella, todo lo anterior es fe.

---

### Etapa 5 — Iniciativa acotada

```
Superficie:  el agente puede iniciar sin prompt humano
Gate:        presupuesto duro (tokens, tiempo, acciones)
             + kill switch probado (matar y verificar que para)
             + auditoría de cada decisión iniciada
             + un humano puede ver el estado en cualquier momento
Falla si:    el agente gasta sin techo, o no se puede interrumpir limpiamente
Costo:       el primer `rxre eter schedule` real
```

**Acá se rompe el patrón de "el agente espera".** Es la etapa más peligrosa. No se entra sin las cuatro condiciones.

---

### Etapa 6 — Múltiples instancias sobre TIERRA

```
Superficie:  dos agentes, misma DB, mismo repo
Gate:        lock probado (o esquema de concurrencia explícito)
             + corrupción inyectada → recuperación verificada
             + event sourcing consistente entre instancias
             + un agente no puede pisar el ciclo del otro
Falla si:    se corrompe la DB en la primera hora
Costo:       el primer esquema con concurrencia real
```

**Esta es la etapa que la mayoría de proyectos salta.** Y es la que rompe todo en producción.

---

### Etapa 7 — Alcanzar el exterior

```
Superficie:  hardware real, APIs, otros agentes
Gate:        cada canal externo tiene:
             - sandbox o límite de efecto
             - error tipado (no cuelgue)
             - auditoría de lo enviado/recibido
             - forma de deshacer si es acción con consecuencia
Falla si:    una llamada externa deja el sistema en estado inconsistente
Costo:       el adaptador más caro de mantener
```

**AIRE y FUEGO se vuelven reales acá.** Antes eran internos. Ahora tocan el mundo.

---

## La regla meta

```
ESCALÁS UN PLANO A LA VEZ.
NUNCA DOS.

Si dos planos nuevos entran en la misma etapa,
no sabés cuál causó el éxito o el fracaso.
Perdés la atribución causal.
```

Esto es lo mismo que pide el protocolo de audit: aislamiento de variables. Escalar es aplicar la misma disciplina a la construcción.

---

## Qué hacer cuando una etapa falla

```
FALLA EN EL GATE:
  → no se avanza
  → se documenta qué falló y por qué
  → se arregla SOLO eso
  → se vuelve a correr el gate

FALLA POR COSTO:
  → se mide cuánto costó mantener lo agregado
  → si el costo > el beneficio, se ROLLBACK
  → el rollback es una decisión válida, no un fracaso

FALLA POR INCONCLUSIVE:
  → no se declara éxito
  → no se declara fracaso
  → se rediseña el experimento, no el sistema
```

**El rollback es parte del escalado.** Un sistema que solo crece no escala. Un sistema que crece, mide y a veces retrocede, sí.

---

## El estado final, si todo pasa

```
rxre escala cuando:
  [ ] los 8 planos tienen su test adversarial
  [ ] cada uno puede quitarse sin romper los otros 7
  [ ] el ciclo completo corre con techo, kill switch y reanudación
  [ ] A vs B se midió al menos una vez y B no empeoró
  [ ] dos instancias conviven sin corromper TIERRA
  [ ] al menos un canal externo tiene sandbox y auditoría
  [ ] el informe de cualquier ciclo se puede reproducir por un tercero

No escala cuando:
  ✗ tiene más comandos
  ✗ tiene más planos
  ✗ tiene más métricas
  ✗ tiene más documentación
  ✗ "está perfecto"
```

---

## La respuesta en una línea

**Escalar rxre es aplicar siete veces el mismo protocolo cerrado a superficies cada vez más grandes, sabiendo que cada etapa puede fallar y que el rollback es una decisión válida.**

No es un roadmap. Es una secuencia de puertas con criterios de falla explícitos. El método no cambia. La superficie sí.

Y el único paso que importa ahora es el mismo de siempre: **esperar el `DELIVERED` del audit**. Sin eso, no hay Etapa 0. Sin Etapa 0, no hay escalada. Solo hay features.
