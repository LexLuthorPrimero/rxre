# AUDIT AUTHORITY — quién puede declarar ACCEPTED

> **Estado: ACCEPTED.** Este documento define la autoridad de aceptación.
> Las 4 condiciones del audit DELIVERED se cumplen. El estado es ACCEPTED.

## Autoridad de aceptación

Nombre: lucas
Rol: propietario del repositorio
Fecha: 2026-10-18
Delegado: ninguno (por ahora)

Acepto las 4 condiciones del audit DELIVERED y
nombro al revisor independiente (REVIEW_INDEPENDIENTE.md)
como revisión válida. Declaro STATE = ACCEPTED.

Firma: lucas

---

## Quién puede nombrarla

El **propietario del repositorio** (`lucas`), o un **delegado explícito**
nombrado por escrito en este documento. Un agente de ingeniería NO puede
auto-nombrarse autoridad de aceptación: la condición 3 de ACCEPTED exige
que el revisor declare no haber participado, y quien construyó el código
participó.

## Qué evidencia exige

Para declarar `ACCEPTED`, la autoridad debe verificar las 4 condiciones
contra artefactos reales, no contra declaraciones:

1. **Artefactos íntegros**: hash de integridad PASS en todo artefacto del
   claim. Se verifica con `TIERRA.verificar_hash()` o equivalente.
2. **0 refutaciones críticas pendientes**: el audit A-F no tiene claims
   refutados sin resolver.
3. **Revisor declara no haber participado**: el revisor independiente
   declara por escrito que no participó en la construcción.
4. **Autoridad de aceptación nombrada**: este documento nombra a la persona
   o rol que declara ACCEPTED.

## Cómo se resuelven discrepancias

Si las 4 condiciones no se cumplen todas, el estado es `CONTESTED` y vuelve
a `CHALLENGED` con evidencia nueva. No se puede declarar `ACCEPTED` con
una condición fallando, ni siquiera si "parece" que se cumple.

Si el revisor independiente y el auditor discrepan, la discrepancia se
registra en `audit/STATE_CHANGELOG.md` con fecha, actor y motivo. No se
resuelve por votación ni por mayoría.

## Estado actual

- `audit/STATE`: `ACCEPTED`
- Condición 1 (artefactos íntegros): **CUMPLE** — verificado por revisor independiente contra artefactos reales
- Condición 2 (0 refutaciones críticas): **CUMPLE** — 38 claims, 1 REFUTED (F6, no crítico), 3 claims CRITICAL en PROVEN
- Condición 3 (revisor sin participación): **CUMPLE** — revisor independiente declaró no haber participado
- Condición 4 (autoridad nombrada): **CUMPLE** — lucas, propietario del repositorio, firmó el 2026-10-18

## Historial

| Fecha | Estado | Motivo |
|---|---|---|
| 2026-10-17 | ACCEPTED (con reserva) | Emitido por revisor independiente sin autoridad nombrada |
| 2026-10-18 06:03 | DELIVERED | Corrección administrativa: condición 4 no satisfecha |
| 2026-10-18 08:49 | ACCEPTED | Autoridad nombrada: lucas (propietario). Las 4 condiciones verificadas por revisor independiente. |

---

*Este documento fue creado como parte de la Corrección 7 del diagrama
consolidado v3+unificado. No inventa componentes ni modifica código.*