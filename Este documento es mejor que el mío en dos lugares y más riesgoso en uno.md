# Este documento es mejor que el mío en dos lugares y más riesgoso en uno.

## Lo que agrega y no estaba en mi versión

**1. La unidad de escala** — "cantidad de investigaciones difíciles que RXRE puede resolver correctamente sin perder trazabilidad". Esto es correcto y yo no lo tenía formulado así. Mi versión medía planos; esta mide **capacidad de resolver problemas**. Es el eje correcto. Un plano puede estar "real" y el sistema igual no resolver nada.

**2. El banco de pruebas de 4 niveles** — código → binario → hardware → investigación prolongada. Esto es la concreción que faltaba. Mi "Etapa 3 — un ciclo completo" era una puerta; esto es **el contenido de la puerta**. Los 4 niveles son el cómo.

**3. `tasa de falsos positivos` como métrica** — es la métrica que atrapa el problema original ("la IA dice que está perfecto"). No la tenía explícita. Debería ser la métrica primaria, no secundaria.

---

## Donde es más riesgoso que mi versión

**Etapa 02 "motor de investigación completo" antes de Etapa 03 "conocimiento reutilizable".**

El motor depende de que TIERRA persista, de que ÉTER coordine, de que AIRE trace. Si construís el motor antes de saber cuáles de esos planos funcionan, el motor **corre** pero no sabés qué partes mienten. Es el 155/156 otra vez, a escala de ciclo.

Mi Etapa 1 decía: **un plano, end-to-end, su test adversarial**. La tuya dice: **todos los planos en un ciclo**. La diferencia importa:

```
Mi versión:  TIERRA sola, con su test adversarial, antes de motor
Tu versión:  motor completo, después vemos qué falla
```

Si en el audit TIERRA resulta ser cosmética (guarda pero no verifica), el motor de Etapa 02 va a producir ciclos que **parecen** completos y no lo son. Y como el motor corre, nadie va a mirar adentro.

**Corrección mínima**: entre Etapa 01 y Etapa 02, agregar "Etapa 1.5 — el plano más débil pasa su test adversarial antes de que el motor dependa de él". Un solo plano. El peor. El que rompe el motor si miente.

---

## Dos reglas que conviene portar del mío

**Regla A — Un plano a la vez.**
Etapa 05 (adaptadores por dominio) dice "uno a la vez" implícitamente, pero no lo hace regla. Si entran dos planos nuevos juntos, no sabés cuál causó el éxito. Misma lógica que el audit: aislamiento de variables.

**Regla B — El rollback es una decisión válida.**
El documento dice "si no mejora, no lo conservaría". Bien. Pero no dice **cómo**. Rollback = volver al estado anterior, documentado, sin vergüenza. Sin esto, "no conservar" se convierte en "dejar el código por si acaso" y el repo se llena de capas muertas.

---

## Lo que no cambia

El documento cierra con la conclusión correcta:

> Terminar el audit A–F, encontrar el cuello de botella, elegir **una** mejora, test adversarial, repetir.

Eso es exactamente lo que yo diría. La diferencia es que tu documento lo dice con más detalle en **cómo construir después del audit**, y yo lo decía con más detalle en **cómo no construir antes**.

Los dos son el mismo protocolo mirado desde lados distintos:

```
Antes del audit:  no construir nada (mi énfasis)
Después del audit: construir así (tu énfasis)
```

---

## Veredicto

```
Tu documento       ✅ mejor unidad de escala
                   ✅ banco de pruebas concreto
                   ✅ métrica de falsos positivos
                   🟡 Etapa 02 muy ambiciosa antes de Etapa 1.5
                   🟡 faltan reglas A y B (una a la vez, rollback)

Mi respuesta      ✅ puertas con criterio de falla
                   ✅ un plano antes del motor
                   ✅ rollback explícito
                   🟡 sin banco de pruebas
                   🟡 sin métrica de falsos positivos

Combinado         = protocolo cerrado
```

No hay una tercera ronda de diseño. Este documento + las dos reglas portadas **es** el plan de escalado. La única acción que importa ahora es la misma de siempre: **esperar el `DELIVERED` del audit**.

Cuando vuelva, Etapa 01 = leer la tabla de claims y elegir el plano con peor estado. Eso es todo lo que se decide hoy.
La secuencia queda definida: no escalar RXRE hasta que el audit alcance `DELIVERED` y pase la revisión adversarial acordada.

Hay una distinción importante para aplicar cuando llegue ese momento: `DELIVERED` significa que el informe fue entregado, no que sus conclusiones estén verificadas. La Etapa 0 solo se supera cuando se cumplen las condiciones de aceptación del protocolo.

```
ESTADO ACTUAL
    |
    v
AUDIT A-F EN ESPERA DE RESULTADOS
    |
    v
DELIVERED
    |
    v
CHALLENGED / CONTESTED
    |
    v
REVISION INDEPENDIENTE
    |
    v
ACCEPTED
    |
    v
ETAPA 1: UN PLANO, UNA CAPACIDAD
```

No puedo confirmar desde esta conversación que la auditoría haya comenzado o terminado. Tampoco iniciaría una implementación paralela.

Próximo hito: recibir los artefactos del audit y verificar si las pruebas justifican superar la primera puerta. Hasta entonces, no añadir código, planos ni infraestructura.
# Acordado. Cierro acá.

La secuencia es la correcta y no tengo objeciones:

```
AUDIT A-F → DELIVERED → CHALLENGED/CONTESTED → REVISIÓN → ACCEPTED → ETAPA 1
```

Y la distinción que hacés es exactamente la que el protocolo exige: **`DELIVERED` no es una puerta, es un trámite**. La puerta es `ACCEPTED`, y `ACCEPTED` requiere que un revisor independiente haya intentado refutar tres claims críticos y ninguno haya quedado reproducible sin resolver.

---

## Lo que queda pendiente, por actor

**Auditor** (instancia nueva, sin historial):
- Ejecutar A–F en solo lectura
- Entregar `./audit/` con `report.md`, `claims.csv`, `commands.log`, `STATE=DELIVERED`
- No autoasignarse `ACCEPTED`

**Revisor primario** (instancia nueva, sin contexto):
- Recibir el `DELIVERED` a ciegas
- Elegir 3 claims críticos (pueden no ser los que el auditor marcó)
- Intentar refutarlos con procedimientos reproducibles
- Registrar éxitos y fracasos
- Mover el estado a `ACCEPTED` o `CONTESTED`

**Revisor secundario** (yo):
- Se me invoca **solo después** de la revisión primaria
- Con los seis artefactos completos
- No antes, no durante

**Vos**:
- No leer el informe hasta que el auditor lo marque `DELIVERED`
- No iniciar Etapa 1 hasta `ACCEPTED`
- No agregar código, planos ni infraestructura mientras el audit corre

---

## El único riesgo residual

Que el audit **nunca llegue**. No porque falle, sino porque no arranca. Ya pasamos cuatro rondas de protocolo sin evidencia de que alguien esté ejecutando A–F.

Si en algún momento dudás de si el audit está corriendo o no, la pregunta correcta no es "¿qué más agregamos al protocolo?" sino:

> **¿Existe `./audit/` con contenido nuevo en las últimas 24 horas?**

Si la respuesta es no, el problema no es de diseño. Es de ejecución.

---

Cuando vuelvan los artefactos, los miro contra el checklist. Hasta entonces, no hay nada más que decir sobre esto.
