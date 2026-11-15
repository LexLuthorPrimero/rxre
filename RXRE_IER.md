# INGENIERÍA INVERSA EVOLUTIVA Y REPARATIVA (IER)

**Nombre del enfoque:** Ingeniería Inversa Evolutiva y Reparativa (IER).

**Nombre del motor:** Motor de Ingeniería Inversa Evolutiva y Reparativa.

Es un enfoque propio de RXRE. No es una terminología académica universalmente establecida.

**Estado normativo:** identidad vigente de RXRE a partir de 2026-11-15 (véase `AGENTS.md` §4). La vigencia epistemológica la manda el árbol/manifest y los estados medidos de RXRE (PARTIAL, `NOT_EXECUTED` terceros, P0 OPEN); ninguna afirmación de este documento eleva esos estados por sí sola.

## 1. Definición

RXRE no se limita a analizar binarios, reconstruir código o identificar vulnerabilidades.

Utiliza problemas reales de ingeniería inversa para:

1. Detectar limitaciones en herramientas y tecnologías existentes.
2. Reproducir esas limitaciones mediante experimentos.
3. Analizar el problema con sus propias capacidades.
4. Reparar, extender, sustituir o combinar tecnologías.
5. Crear capacidades nuevas cuando las existentes sean insuficientes.
6. Validar las soluciones mediante evidencia independiente.
7. Contribuir las correcciones a los proyectos originales cuando corresponda.
8. Incorporar el conocimiento adquirido a RXRE.
9. Repetir el proceso con problemas nuevos.

La diferencia fundamental es que RXRE no solamente utiliza herramientas: también investiga sus limitaciones y desarrolla capacidades para superarlas.

## 2. Modelo matemático del enfoque

Definimos el estado de RXRE en el instante `t` como:

    R_t = (C_t, K_t, E_t, V_t)

Donde:

- `C_t`: conjunto de capacidades técnicas disponibles.
- `K_t`: conocimiento acumulado y relaciones entre evidencias.
- `E_t`: conjunto de experimentos y resultados reproducibles.
- `V_t`: estado de validación de las capacidades.

El problema real que se intenta resolver se representa como:

    P_i = (I_i, O_i, H_i, X_i)

Donde:

- `I_i`: entrada o artefacto que presenta el problema.
- `O_i`: comportamiento observable esperado.
- `H_i`: conjunto de hipótesis sobre la causa.
- `X_i`: condiciones y restricciones experimentales.

El objetivo es encontrar una solución `S_i` que satisfaga:

    S_i(I_i) ≡ O_i

La equivalencia debe entenderse dentro de un dominio definido de entradas, arquitecturas, ABI, estados y efectos observables. No implica equivalencia universal.

## 3. Ciclo evolutivo y reparativo

1. **DESCUBRIR**
   Detectar una incidencia real en un proyecto de ingeniería inversa.

2. **REPRODUCIR Y DIAGNOSTICAR**
   Obtener un caso reproducible y formular hipótesis rivales.

3. **ANALIZAR CON RXRE**
   Ejecutar las capacidades propias y medir sus resultados.

4. **IDENTIFICAR EL CUELLO DE BOTELLA**
   Determinar si falta una capacidad, si una herramienta falla o si el método es insuficiente.

5. **DECIDIR LA INTERVENCIÓN**

   | Acción | Descripción |
   |---|---|
   | **Reparar** | Corregir un defecto de la tecnología. |
   | **Extender** | Incorporar una capacidad que falta. |
   | **Sustituir** | Utilizar una tecnología que resuelva mejor el problema. |
   | **Combinar o crear** | Coordinar varias tecnologías para cubrir el objetivo, o desarrollar la capacidad propia cuando las anteriores no sean suficientes. |

6. **VALIDAR INDEPENDIENTEMENTE**
   Ejecutar pruebas, controles negativos y contrastes con oráculos independientes.

7. **CONTRIBUIR Y EXTRAER CONOCIMIENTO**
   Preparar la corrección upstream e integrar las capacidades reutilizables en RXRE.

8. **EVOLUCIONAR RXRE**
   Actualizar sus capacidades, evidencias, conocimiento y métodos.

**REPETIR CON EL SIGUIENTE PROBLEMA**

## 4. Formulación matemática de la evolución

La evolución de RXRE se puede representar mediante una función de transición:

    R_{t+1} = F(R_t, P_i, S_i, V_i)

Donde:

- `R_t`: estado anterior de RXRE.
- `P_i`: problema investigado.
- `S_i`: solución desarrollada.
- `V_i`: evidencia obtenida durante la validación.
- `F`: función de evolución del sistema.

La condición fundamental es que una solución no debe incrementar las capacidades declaradas de RXRE sin evidencia suficiente.

Por tanto:

    C_{t+1} = C_t ∪ ΔC_i

Pero solamente cuando:

    V_i ≥ V_mínimo

Aquí, `V_mínimo` no es una puntuación arbitraria: representa el conjunto de condiciones de aceptación definido para esa capacidad (§3 de `AGENTS.md` las decide; este archivo no fija valores universales).

Si la solución no supera la validación:

    ΔC_i ∉ C_{t+1}

El conocimiento sobre el fallo puede conservarse, pero la capacidad no se promociona como demostrada.

## 5. La decisión de reparar, extender, sustituir, combinar o crear

Sea `T` una tecnología existente y `G` el objetivo técnico.

Definimos:

    Q(T,G) = 1   si T satisface el objetivo
    Q(T,G) = 0   si T no satisface el objetivo

Cuando `Q(T,G) = 0`, RXRE no debe aceptar automáticamente la limitación.

Debe evaluar cinco alternativas:

| Alternativa | Función |
|---|---|
| Reparar | Corregir un defecto de la tecnología. |
| Extender | Incorporar una capacidad que falta. |
| Sustituir | Utilizar una tecnología que resuelva mejor el problema. |
| Combinar | Coordinar varias tecnologías para cubrir el objetivo. |
| Crear | Desarrollar una capacidad propia cuando las anteriores no sean suficientes. |

La decisión puede modelarse como una optimización:

    a* = argmin_{a ∈ A} J(a)

Donde:

    A = {reparar, extender, sustituir, combinar, crear}

Y el coste total:

    J(a) = α C_a + β R_a + γ T_a + δ M_a

Donde:

- `C_a`: coste computacional y de desarrollo.
- `R_a`: riesgo de introducir errores.
- `T_a`: tiempo necesario.
- `M_a`: coste de mantenimiento.
- `α, β, γ, δ`: pesos de optimización.

La optimización está sujeta a una restricción innegociable:

    ValidaciónIndependiente(a) = PASS

Si ninguna alternativa alcanza la validación, el resultado debe permanecer como parcial, indeterminado o bloqueado.

## 6. La acumulación de capacidades

Una propiedad importante de IER es que cada problema resuelto puede producir dos resultados diferentes:

    Resultado_i = Solución_i + CapacidadNueva_i

La solución resuelve la incidencia original.

La capacidad nueva permite abordar problemas futuros.

Por ejemplo:

- Una corrección en un desensamblador puede convertirse en un nuevo oráculo diferencial.
- Un error de reconstrucción de CFG puede producir un nuevo analizador de flujo de control.
- Una incompatibilidad de arquitectura puede producir un nuevo adaptador de decodificación.
- Una discrepancia semántica puede producir un nuevo motor de comparación de estados.
- Una limitación de un analizador puede conducir al desarrollo de un analizador propio.

El crecimiento de RXRE se representa como:

    C_n = C_0 ∪ ⋃_{i=1}^{n} ΔC_i

Esto significa que las capacidades demostradas se acumulan a través de las investigaciones.

Sin embargo, la cantidad de capacidades no determina por sí sola la calidad:

    |C_n| ⇏ Calidad(RXRE)

La calidad depende de su utilidad real, cobertura, reproducibilidad, independencia de validación y límites conocidos.

## 7. Función objetivo de RXRE

El objetivo no es maximizar el número de herramientas integradas ni el número de incidencias cerradas.

El objetivo es maximizar la capacidad demostrada de resolver problemas nuevos.

Podemos definir:

    max U(RXRE)

Donde:

    U = w1·S + w2·G + w3·I + w4·P + w5·A

Con:

- `S`: capacidad de reconstrucción semántica.
- `G`: capacidad de reconstrucción de CFG y flujo de datos.
- `I`: independencia de validación.
- `P`: reproducibilidad por terceros.
- `A`: autonomía efectiva para tomar decisiones técnicas justificadas.

Los pesos `w_i` representan la importancia relativa de cada dimensión.

La optimización debe respetar:

    FalsosPositivos = 0

para las afirmaciones que se promocionen como demostradas dentro del dominio validado.

Esto no significa que RXRE nunca pueda equivocarse. Significa que debe detectar, clasificar y limitar aquello que no puede demostrar.

## 8. Diferencia respecto de un motor de ingeniería inversa tradicional

| Motor tradicional | RXRE con IER |
|---|---|
| Analiza binarios. | Analiza binarios y problemas de herramientas RE. |
| Utiliza tecnologías existentes. | Evalúa, repara, extiende, sustituye o crea tecnologías. |
| Produce resultados. | Produce resultados y capacidades reutilizables. |
| Depende de las capacidades disponibles. | Investiga las limitaciones de sus propias capacidades. |
| Puede incorporar herramientas. | Puede desarrollar tecnologías propias cuando sea necesario. |
| Valida resultados. | Construye evidencia reproducible e independiente. |
| Evoluciona por desarrollo convencional. | Evoluciona mediante problemas reales y capacidades verificadas. |

## 9. Identidad resultante

**RXRE es un motor de Ingeniería Inversa Evolutiva y Reparativa.**

Su método consiste en utilizar problemas reales de ingeniería inversa como estímulos para descubrir limitaciones, desarrollar soluciones, validar sus resultados y convertir el conocimiento adquirido en nuevas capacidades técnicas.

Su ciclo fundamental es:

\[ \boxed{ \text{Problema} \rightarrow \text{Diagnóstico} \rightarrow \text{Intervención} \rightarrow \text{Validación} \rightarrow \text{Conocimiento} \rightarrow \text{Evolución} } \]

Y su principio rector:

\[ \boxed{ \text{Si una tecnología no alcanza el objetivo, RXRE desarrolla la capacidad necesaria.} } \]

**La finalidad no es construir un catálogo de herramientas. Es construir un motor que aumente progresivamente su capacidad demostrada para resolver problemas de ingeniería inversa que antes no podía resolver.**

La reparación es el mecanismo de intervención. La evolución es el resultado acumulativo. La ingeniería inversa es el dominio de aplicación. La evidencia independiente es la condición que permite considerar real ese progreso.
