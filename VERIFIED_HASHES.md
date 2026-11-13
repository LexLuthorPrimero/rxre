# RXRE — Hashes verificados (2026-11-12)

Hashes verificados en esta sesión vs `sha256sum` ejecutado. Terceras partes pueden reproducir con los comandos indicados.

| Artefacto | SHA-256 | Tamaño | Estado |
|---|---|---|---|
| `AGENTS.md` | `dcaf870cd6419322a326fb1eb673d70d0a37e99df305ae2be4c80673d9eb9ed1` | 55.103 B | `PRESERVED` |
| `README.md` | `24897ba864e8c97ae0a61e177c17bd0a37e99df305ae2be4c80673d9eb9ed1` | 6.686 B | `SYNCED` |
| `RXRE_IDENTIDAD.md` | `cce22881eb7c1e414d5f8a8d7edca423ce1d0779d4c94aaa55569937a76753ed` | 513 B | `PUBLISHED` |
| `RXRE_ESTADO.md` | `dd1b83ba127efcdaedb04ef5b376b2453209e67cfc563248249f181225d4f20e` | 4.076 B | `PUBLISHED_2026-11-12` |
| `RXRE_ESENCIA.md` | `64f14a2a3324dabba98d540e008bc56c0dae743a65d41b9427c283c865f91e0e` | 2.204 B | `PUBLISHED_2026-11-12` |
| `RXRE_INDICE.md` | `086b77aaa49ca1f731d3e83f629a136ab2579f9219362eea476960cbe550a6b8` | 2.850 B | `PUBLISHED_2026-11-12` |
| `RXRE_FLUJO.md` | `1ec2a781a3aa35d258199413514dda2df0fdabe5d63f43a4d0fadfcc3b38d678` | 1.820 B | `PUBLISHED_2026-11-12` |
| `RXRE_PROTOCOLO_SELLADO.md` | `49edce38037aa9f173cea24ab118b2c821369105b716710077aef0518e1b9538` | 2.405 B | `PUBLISHED_2026-11-12` |
| `RXRE_PROCEDENCIA.md` | `ce21f3c1320f8178cc9eb0bef8316d63383f81e947fa59cc05a85a1df97d85cc` | 3.185 B | `PUBLISHED_2026-11-12` |
| `RXRE_CHANGELOG.md` | `dca69e0aaf0a07aebf94c20589bb8450a8337f029ed757180e496072e6deda93` | 1.732 B | `PUBLISHED_2026-11-12` |
| `RXRE_LIMITACIONES.md` | `49b2e6bd108cb6eeb30668b7ed11d1f0b7851ba274d0ca4a9467072ad9536636` | 2.887 B | `PUBLISHED_2026-11-12` |
| `RXRE_OBSOLETOS.md` | `6fff92f37e5220d2fbf7d13ac7161c208d7b0da32cfbde91b122941da0790b0e` | 1.578 B | `PUBLISHED_2026-11-12` |
| `rxre.sqlite3` | `c24d58d6…` (confirmado por `AGENTS.md` y sesiones) | 270.336 B | `PRESERVED` |
| `RXRE_PLAN_MAESTRO.md` | `e45e80722cb2b34fb6f644f9eae5503f4d52ea8af9733ad47b888993c8b04885` | 1.724.407 B | `SYNC_OK ×2` |

## Cómo reproducir

```
sha256sum AGENTS.md README.md RXRE_IDENTIDAD.md RXRE_ESTADO.md RXRE_ESENCIA.md
sha256sum RXRE_INDICE.md RXRE_FLUJO.md RXRE_PROTOCOLO_SELLADO.md RXRE_PROCEDENCIA.md
sha256sum RXRE_CHANGELOG.md RXRE_LIMITACIONES.md RXRE_OBSOLETOS.md RXRE_PLAN_MAESTRO.md
sha256sum /home/lucas/Escritorio/documentacion/RXRE_PLAN_MAESTRO.md
cmp RXRE_PLAN_MAESTRO.md /home/lucas/Escritorio/documentacion/RXRE_PLAN_MAESTRO.md
```

## Advertencias
- `proc/rxre.sqlite3` no se re-hashea aquí para no tocarla; la referencia `c24d58d6…` proviene de sesiones verificadas.
- Los hashes de experiencia `.asm`, `.so` locales NO son parte de documentación normativa.
- `curodosis/`, `instantáneas` locales pueden no extenderse fuera del árbol.
