# DRAFT — Convocatoria ciega de verificación — issue #1 `rxre-cleanroom` (propuesta v1.3.0)

(Borrador privado; no publicado. Publicación solo tras aprobación escrita del propietario.)

Título sugerido: `Blind review wanted (v1.3.0): two commands, 15 minutes, zero trust in the author`

---

**English**

`rxre-cleanroom` and `rxre-engine` now ship `v1.3.0` with a single-command,
fail-closed verifier. This is a request for the one thing this project cannot
produce on its own: an independent confirmation (or refutation) from a machine
the author has never touched.

What you do:

```sh
git clone https://github.com/LexLuthorPrimero/rxre-cleanroom
cd rxre-cleanroom
./verify.sh
```

or, with the packaged zips (SHA-256):

- cleanroom: `rxre-cleanroom-1.3.0.zip` — `6274fa72b8a40b0bed319effc757f1955c99f524494ea821c4f547804d6bd22a`
- engine: [`rxre-engine-1.3.0.zip`](https://github.com/LexLuthorPrimero/rxre-engine/releases/tag/v1.3.0) — `8c67df83a38c4888461be4a002f50742b58c967b9241ccc1d6fdae6c6a4ab882`

Expected: `VERIFY: all steps passed` (cleanroom) — both generations byte-exact,
challenge corpus 3,100 + 3,241, locale invariance, i18n black-box, 11 `wc`
corpora. On the engine side the README states the actual pytest count (23 passed,
2 honestly skipped without the author's private DB).

Fail-closed by design: if your host's `/usr/bin/ls` or `/usr/bin/wc` do not match
the sealed hashes, the verifier refuses to proceed — that is the control working,
not a bug. Identities: `ls` `54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c` ·
`wc` `81d614595c717be908fce809713702efd35ce5a56f5ab7cbc497d1a61eb1a38f`.

What we ask:

- Confirm (`VERIFIED_BY_THIRD`), refute (`NO_REPRODUCE`), or report resource/
  environment impossibility (`INSUFFICIENT`). Any of the three is an asset.
- Refutations are best as **minimal counterexamples**: the exact entry
  (pair of names / line of corpus), expected vs observed, 3× repeat. Template:
  [`reviewer-kit/CONTRAEJEMPLO.md`](https://github.com/LexLuthorPrimero/rxre-engine/blob/main/reviewer-kit/CONTRAEJEMPLO.md).
- That is the whole contribution. No install, no account, no cost.

What you get: nothing but being right. Your dictamen lands as a comment here;
if it refutes the claim, the milestone is reopened and fixed in the open.

**Español (resumen)**

Dos paquetes, un comando, cero confianza en el autor. Clona, ejecuta
`./verify.sh`, pega tu entorno (distro, hashes de `/usr/bin/ls` y `/usr/bin/wc`,
salida completa) y tu dictamen: `VERIFICADO_POR_TERCERO`, `NO_REPRODUCE` o
`INSUFFICIENTE`. Un contraejemplo minimizado vale más que diez auditorías
amables.
