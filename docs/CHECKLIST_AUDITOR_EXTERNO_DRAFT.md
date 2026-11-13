# DRAFT — Checklist para el primer auditor externo (15 minutos)

(Borrador privado; no publicado. Versiona como Anexo del issue #1 o del kit.)

## A. Antes de ejecutar (preflight — anotar todo esto)

- [ ] `date -u`, `uname -a`, `cat /etc/os-release | head -3`
- [ ] `gcc --version | head -1`, `python3 --version`
- [ ] `sha256sum /usr/bin/ls /usr/bin/wc` (si difieren del sello → el diferencial no valida ESE oráculo; documentar y decide: parar o continuar solo como chequeo de integridad)
- [ ] `locale -a | grep -E '^(C|es_AR\.utf8)$'`
- [ ] Ordenador/entorno aislado (máquina personal o VM descartable; sin credenciales del autor)
- [ ] Elegir canal: (a) clon GitHub `git clone`, (b) zip del release + `sha256sum -c`

## B. Ejecución (≤15 min)

- [ ] `sha256sum -c SHA256SUMS` (clone o zip descomprimido) → todas `OK`
- [ ] `./verify.sh` (cleanroom) o `sh evidence/r3/verify.sh` (engine)
- [ ] Observar el fail-closed: identidad nativa pasa antes de cualquier salto
- [ ] Capturar salida completa (no truncada) — archivo `auditor_<fecha>.log`
- [ ] Engine solamente: observar `23 passed, 2 skipped` (los skips son los 2 tests que exigen la DB privada del autor, deliberadamente no distribuida)
- [ ] Si algo diverge → ir a D (triage)

## C. Cierre (dictamen)

- [ ] Veredicto: `REPRODUCE` / `NO_REPRODUCE` / `PARCIAL` (justificación) / `INSUFFICIENT` (no pudo ejecutar — p. ej. mismatch de hashes nativos)
- [ ] Entorno + veredicto + log + contraejemplo (si aplica) como comentario en issue #1
- [ ] Archivar localmente el `.log` con los hashes del paquete usado

## D. Triage si algo diverge (orden estricto)

1. ¿Es la identidad nativa (paso 2)? → Imposible vs este oráculo; dictamen `INSUFFICIENT` o redo con binarios correctos. **No** es un fallo del paquete.
2. ¿Falla un sello de `SHA256SUMS`? → Posible corrupción del zip/clone: redescargar; si persiste, reportar.
3. ¿Mismatch en un caso? → Minimizar a entrada mínima (2 nombres / 1 línea de corpus), repetir 3×, reportar con plantilla `CONTRAEJEMPLO.md`. NO especular sobre la causa.
4. ¿Timeout/ambiente? → Documentar recursos (RAM, CPU), considerar `INSUFFICIENT` honesto.

## E. Qué NO debe hacer el auditor

- [ ] No ejecutar binarios fuera de los verificadores del paquete
- [ ] No modificar corpus, matrices ni sellos
- [ ] No reportar un veredicto sin el log completo
- [ ] No prometer PASS de terceros por el proyecto: el dictamen vale para el entorno del auditor, en su fecha

## F. Qué significa cada resultado (para la puerta)

| Resultado del auditor | Efecto sobre PUERTA condición 3 |
|---|---|
| REPRODUCE (limpio) | Dato externo a favor; el propietario decide etiquetas |
| NO_REPRODUCE + contraejemplo válido | Reabre el hito; fix documentado; sellado nuevo |
| PARCIAL | Nuevo dictamen no promoción; se documenta la limitación |
| INSUFFICIENT | Sin efecto; se agradece la transparencia |

Ningún resultado convierte el proyecto en general: cada veredicto cubre únicamente el dominio sellado (GNU coreutils 9.10 `filenvercmp`/`wc`).
