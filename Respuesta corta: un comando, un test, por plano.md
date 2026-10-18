# Respuesta corta: un comando, un test, por plano.

Después de todo esto, mi respuesta cambió. Al principio te hubiera dado una lista de features. Ahora te doy **una cosa por plano** que se puede probar adversarialmente. Si no pasa el test, no es un plano — es una función con nombre poético.

Y una regla que sale de todo lo que discutimos: **no construyo ninguno hasta que el audit muestre que falta**. Puede que rxre ya lo tenga. Puede que lo tenga a medias.

---

## El criterio

Un plano es real si:

```
1. Existe UN comando que hace algo que el agente no puede hacer sin él
2. Existe UN test adversarial que falla si el comando miente
3. Quitarlo rompe una capacidad, no solo un módulo
```

Si no cumple las tres, es cosmético. Se arregla o se borra.

---

## Los 8, con su test

| Plano | Comando mínimo | Test adversarial | Qué prueba |
|---|---|---|---|
| **CUERPO** | `rxre cuerpo hash <file>` | Modificar 1 byte, el hash cambia | Que lee el mundo real, no un cache |
| **TIERRA** | `rxre tierra verify --chain <dir>` | Corromper 1 artefacto, el chain se rompe | Que la integridad es real, no decorativa |
| **ÉTER** | `rxre eter loop --max N` | Pedir loop infinito, corta en N | Que el techo existe, no es sugerencia |
| **AIRE** | `rxre aire ask --model X` | Modelo caído → error tipado, no cuelgue | Que alcanza algo externo, no simula |
| **MENTE** | `rxre mente plan --persist` | Matar proceso, `plan show` recupera el plan | Que persiste, no vive en el JSON de respuesta |
| **AGUA** | `rxre agua forget --topic X` | `recall X` devuelve vacío después | Que olvida de verdad, no filtra en lectura |
| **FUEGO** | `rxre fuego apply --sandbox` | Aplicar, rollback, `diff` da 0 bytes | Que modifica y puede deshacer |
| **ALMA** | `rxre alma refuse --value X` | Dos sesiones, mismo pedido, mismo rechazo | Que la identidad persiste entre sesiones |

Cada test es **el caso donde el comando falla**. Si el test pasa, el comando es real. Si el test nunca falla, el test es cosmético.

---

## El orden en que los daría

No todos a la vez. Este orden respeta dependencias:

```
1. TIERRA     ← sin persistencia, todo lo demás es efímero
2. ÉTER       ← sin bus, los planos no se hablan
3. CUERPO     ← sin sensores/actuadores, no hay mundo
4. AIRE       ← sin canales, el agente está solo
5. MENTE      ← usa TIERRA para persistir planes
6. AGUA       ← usa TIERRA para olvidar/recordar
7. FUEGO      ← usa CUERPO + TIERRA para actuar y deshacer
8. ALMA       ← lo último, porque identidad es lo más difícil de testear
```

**ALMA al final es a propósito.** "Identidad persistente" es lo más fácil de fingir con un YAML. Es lo que menos se puede verificar con un test. Por eso va último: cuando todo lo demás esté probado, recién ahí tiene sentido preguntar si el agente "sigue siendo el mismo".

---

## Lo que NO haría

```
✗ Ocho archivos con ocho clases abstractas
✗ Una carpeta por plano antes de tener un comando por plano
✗ Un README de cada plano antes de un test de cada plano
✗ "Integrar el modelo de 8 planos" como objetivo
✗ Un plano que sea "el que junta los otros" (ÉTER no es un cajón)
```

Todo eso es cosmética disfrazada de arquitectura.

---

## La única cosa que importa

El audit que el amigo va a correr responde **cuáles de estos 8 ya existen** en rxre, **cuáles son cosméticos** y **cuáles faltan**. Mi trabajo no es darte los 8 ahora. Mi trabajo es darte la vara para saber cuáles son reales.

Cuando vuelva `DELIVERED`, mirás la tabla de claims y por cada plano te preguntás:

```
¿Tiene su comando?        → si no, es idea
¿Tiene su test?           → si no, es fe
¿Pasa el test adversarial? → si no, es bug
¿Quitarlo rompe algo?     → si no, es decoración
```

Los que pasen las 4, se quedan. Los que no, se arreglan o se borran. **Eso es darle los 8 planos a rxre.** No es escribir código. Es no dejar entrar nada que no pase la vara.

---

