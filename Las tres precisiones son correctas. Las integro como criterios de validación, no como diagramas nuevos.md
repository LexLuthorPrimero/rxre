# Las tres precisiones son correctas. Las integro como criterios de validación, no como diagramas nuevos.

No hace falta otra ronda de diagramas. Estas tres precisiones son **condiciones de aceptación** de los tres fixes, no un cuarto nivel.

---

## Precisión 1 — Independencia de ÉTER: se verifica, no se asume

Agregado al Fix 1, como test obligatorio antes de declarar la arquitectura válida:

```
TEST DE INDEPENDENCIA DE ÉTER

  1. Deshabilitar ÉTER (matar proceso / bloquear puerto / flag off).
  2. Ejecutar una interacción directa MENTE <-> CUERPO.
  3. Registrar: resultado, latencia, eventos perdidos.
  4. Restaurar ÉTER.
  5. Verificar recuperación de observabilidad.

PASS:
  [ ] la interacción directa funciona sin ÉTER
  [ ] la pérdida de eventos está identificada (cuáles, cuántos)
  [ ] la recuperación no inventa eventos ni duplica efectos
  [ ] la latencia sin ÉTER no degrada más de X% (X se define antes)

FAIL:
  - la llamada directa depende de ÉTER sin saberlo
  - la publicación de eventos bloquea la operación principal
  - tras restaurar, hay eventos duplicados o fantasma
```

Hasta que este test pase, "ÉTER no media" es **hipótesis arquitectónica**, no propiedad verificada. El audit decide qué contratos son síncronos; el test decide si la independencia es real.

---

## Precisión 2 — `ACCEPTED` es una conjunción, no una acumulación

El diagrama del Fix 2 muestra las condiciones por claim. Falta la condición **global**. La agrego como fórmula:

```
ACCEPTED(exhaustivo) =
      3 claims críticos seleccionados
  AND cada intento de refutación fue válido y reproducible
  AND cada evidencia original fue reproducible por el revisor
  AND ninguna refutación crítica reproducible quedó sin resolver

ACCEPTED(válido pero limitado) =
      3 claims críticos seleccionados
  AND cada intento válido
  AND cada evidencia reproducible
  AND no quedan refutaciones sin resolver
  BUT el alcance del ACCEPTED es solo esos 3 claims
      (no se extrapola a los demás)
```

La segunda forma es válida pero explícita: **no dice "el informe es correcto", dice "estos tres claims resistieron"**. Si el auditor quiere que `ACCEPTED` cubra más, tiene que declararlo y el revisor tiene que intentar refutar más claims.

**Regla operativa nueva**: el `ACCEPTED` debe declarar **cuántos claims cubre y cuáles**. Sin eso, el estado es ambiguo.

---

## Precisión 3 — "No se puede arreglar sin el plano" se reemplaza por procedimiento

La imposibilidad absoluta no es demostrable. Se reemplaza por esta secuencia acotada:

```
PROCEDIMIENTO DE CAPACIDAD GENUINA

  1. IDENTIFICAR   la capacidad concreta que falla al quitar el plano.
                   (no "algo se rompe" — qué exactamente)

  2. REPRODUCIR    el fallo al retirar el plano, N veces.
                   (si no se reproduce, el fallo era ruido)

  3. REPARAR       con un cambio acotado que NO toque el plano.
                   (si no se puede reparar sin el plano → paso 5)
                   (si se puede reparar → el fallo era acoplamiento)

  4. REPETIR       la retirada tras la reparación.
                   (si ahora no falla → el plano no era real)

  5. EVIDENCIAR    la diferencia entre las dos ejecuciones
                   (con plano / sin plano), con hash y comando.

  COMMIT del plano solo si:
    [ ] el fallo se reproduce N veces
    [ ] la reparación acotada no fue suficiente
    [ ] la diferencia está evidenciada
```

**Si la reparación requiere tocar otro plano**: el commit del plano nuevo y el fix del otro plano van juntos, **con dos tests que distingan la contribución de cada uno**. Si no se pueden distinguir, no se sabe cuál era necesario, y el commit es especulativo.

---

## Estado operativo (sin cambios)

```
AUDIT A-F:      esperando artefactos
STATE:          no confirmado como iniciado
ETAPA 1:        BLOQUEADA
IMPLEMENTACION: NO AUTORIZADA
```

Estas tres precisiones **no abren** nada. Suben la vara de lo que `ACCEPTED` tiene que significar y de lo que "plano real" tiene que probar. La secuencia sigue igual.

---

## Lo único que agrego a la especificación existente

Tres líneas nuevas en el checklist del revisor, para cuando llegue el `DELIVERED`:

```
[ ] ¿El ACCEPTED declara cuántos claims cubre y cuáles?
[ ] ¿El test de independencia de ÉTER se corrió o está agendado?
[ ] ¿Cada "plano real" tiene evidencia de capacidad genuina,
    no solo de "quitar rompe"?
```

Con eso, la especificación está cerrada. No hay adenda D. No hay diagrama 4. Hay tres criterios más que el informe tiene que satisfacer para que `ACCEPTED` valga lo que dice.

**El audit sigue esperando.**
