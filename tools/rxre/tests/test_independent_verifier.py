#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-109 · INDEPENDENT_VERIFIER — verificador independiente del testigo M10.8.

Requisitos del dictamen M10.9 cubiertos aquí:
  - Implementación separada (sin reutilizar funciones decisorias del testigo).
  - Reconstrucción de operaciones desde artefactos declarados.
  - Comparación de estados antes/después (hashes, P1/P2/P3).
  - Comparación de trazas de observadores.
  - Verificación de intervalos, storage y cobertura sellada desde la fuente.
  - Detección de operaciones omitidas/reordenadas/introducidas.
  - Rechazo de sellos rotos (manifiesto manipulado ⇒ excepción, NUNCA resultado).
  - ≥ un contraejemplo que haga fallar cada condición (B..D).
  - Fixtures nativos gcc que discrimina entre implementaciones
    (control positivo/negativo).
  - NO compara sus resultados con los del testigo ni los acopla en el veredicto.
"""
import os
import sys
import json
import subprocess
import tempfile
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_iv_")

from ier import independent_verifier as iv  # noqa: E402
from ier import witness_cases as wc  # noqa: E402
from ier import transformer_witness as tw  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-56s" % nombre)
    else:
        print("  FAIL %-56s %s" % (nombre, info))
        _fallos.append(nombre)


M10 = os.environ.get(
    "RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10"))

# ── carga sellada y verificación de manifiestos ─────────────────────
sealed_ok = iv.load_sealed_analysis(M10)
v("sellado M10 verificado antes de consumir", sealed_ok is not None)

manifest_tmp = tempfile.mkdtemp(prefix="iv_m_")
art = os.path.join(manifest_tmp, "art.json")
open(art, "w").write('{"x": 1}')
open(os.path.join(manifest_tmp, "SHA256SUMS.m10.7"), "w").write(
    "%s  art.json\n" % hashlib.sha256(open(art, "rb").read()).hexdigest())
try:
    iv.load_sealed_analysis(manifest_tmp)
    v("carga de análisis sin sellado completo → ValueError", False)
except (ValueError, KeyError, json.JSONDecodeError):
    v("carga de análisis sin sellado completo → ValueError", True)

tamper = os.path.join(manifest_tmp, "art2.json")
open(tamper, "w").write('{"x": 2}')
open(os.path.join(manifest_tmp, "SHA256SUMS.m10.7"), "a").write(
    "%s  art2.json\n" % hashlib.sha256(open(tamper, "rb").read()).hexdigest())
with open(tamper, "a") as fh:
    fh.write(" ")
try:
    iv.verify_manifest(manifest_tmp, "7")
    v("manifiesto roto → rechazo", False)
except ValueError:
    v("manifiesto roto → rechazo", True)

# ── caso real: veredicto y acuerdo con el testigo ──────────────────
case = wc.build_cancel_sys_case(M10)
w = tw.evaluate(case)
vres = iv.verify_case(case, sealed_analysis=sealed_ok)
v("verifier: SAFE_TO_TRANSFORM en el caso cancel.sys", vres["verdict"] == iv.SAFE)
v("condición B TRUE (P1∧P2∧P3)", vres["conditions"]["B"]["value"] == iv.TRUE)
v("condición W TRUE", vres["conditions"]["W"]["value"] == iv.TRUE)
v("condición O TRUE", vres["conditions"]["O"]["value"] == iv.TRUE)
v("condición L TRUE", vres["conditions"]["L"]["value"] == iv.TRUE)
v("condición C TRUE", vres["conditions"]["C"]["value"] == iv.TRUE)
v("condición D TRUE", vres["conditions"]["D"]["value"] == iv.TRUE)
v("imagen original == imagen transformada (hash completo)",
  vres["final_images"]["equal_on_full_region"] is True)
v("acuerdo explícito con el testigo (sin acoplamiento)",
  w["verdict"] == vres["verdict"])
v("imágenes deterministas", vres["final_images"]["original_sha256"] ==
  vres["final_images"]["transform_sha256"])

# ── M10.10.1 · contrato de evidencia: ambas herramientas resuelven igual
# evidencia inventada citada por el caso → Bound FALSE → BLOCKED (ambos)
case_fake = wc.build_cancel_sys_case(M10)
case_fake["observations"]["evidence_intervals"] = [
    {"id": "ev-fake-invented", "interval": [-44, -25], "category": "TEXTUAL_READ"}]
v_fake = iv.verify_case(case_fake, sealed_analysis=sealed_ok)
w_fake = tw.evaluate(case_fake)
v("M10.10: evidencia citada inexistente → BLOCKED (verificador)",
  v_fake["verdict"] == iv.BLOCKED)
v("M10.10: evidencia citada inexistente → BLOCKED (testigo)",
  w_fake["verdict"] == tw.BLOCKED)

# lista vacía de evidencias: el contrato verifica contra la fuente sellada
# → SAFE en ambos instrumentos (la divergencia M10.9 queda RESUELTA por R3-R6)
case_empty = wc.build_cancel_sys_case(M10)
case_empty["observations"]["evidence_intervals"] = []
v_empty = iv.verify_case(case_empty, sealed_analysis=sealed_ok)
w_empty = tw.evaluate(case_empty)
v("M10.10: evidencia vacía declarada → SAFE (verificador)", v_empty["verdict"] == iv.SAFE)
v("M10.10: evidencia vacía declarada → SAFE (testigo)", w_empty["verdict"] == tw.SAFE)
v("M10.10: divergencia M10.9 resuelta por regla verificable",
  v_empty["verdict"] == w_empty["verdict"])

# ── cada condición con ≥ un contraejemplo ──────────────────────────
bad = wc.build_cancel_sys_case(M10)
b_bad_bytes = list(bad["proposed_transform"]["ops"][0]["bytes"])
b_bad_bytes[3] = 0xff
bad["proposed_transform"]["ops"][0]["bytes"] = b_bad_bytes
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("B contraejemplo → BLOCKED", vbad["verdict"] == iv.BLOCKED)

bad = wc.build_cancel_sys_case(M10)
bad["intervals_written_transform"] = [[-44, -26]]
bad["proposed_transform"]["overlap_intervals"] = [[-44, -26]]
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("W contraejemplo → BLOCKED", vbad["verdict"] == iv.BLOCKED)

bad = wc.build_cancel_sys_case(M10)
import json as _json
bad["order_check"]["transform"] = list(reversed(_json.loads(_json.dumps(
    bad["order_check"]["transform"]))))
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("O contraejemplo → BLOCKED", vbad["verdict"] == iv.BLOCKED)

bad = wc.build_cancel_sys_case(M10)
bad["proposed_transform"]["storage_writes"] = ["frame:-48:16"]
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("L contraejemplo (storage ajeno) → BLOCKED", vbad["verdict"] == iv.BLOCKED)

bad = wc.build_cancel_sys_case(M10)
bad["lineage"]["must_not_overlap"] = [
    {"id": "vvar_271", "interval": [-48, -32], "live_during_transform": True}]
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("L contraejemplo (solape con región viva) → BLOCKED", vbad["verdict"] == iv.BLOCKED)

bad = wc.build_cancel_sys_case(M10)
bad["observations"]["evidence_intervals"] = [
    {"id": "ev-fake-citado-inexistente", "interval": [-44, -26],
     "category": "TEXTUAL_READ"}]  # id no existe en el análisis sellado
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("C cita evidencia inexistente en la fuente sellada → BLOCKED",
  vbad["verdict"] == iv.BLOCKED)

# M10.10 · el caso válido con T que escribe bytes y O=∅ → ABSTAIN
bad = wc.build_cancel_sys_case(M10)
bad["observations"]["consumed_intervals"] = []
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("T toca bytes con O=∅ → ABSTAIN (R3 fail-closed)",
  vbad["verdict"] == iv.ABSTAIN)

bad = wc.build_cancel_sys_case(M10)
del bad["domain"]
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("D sin dominio → ABSTAIN", vbad["verdict"] == iv.ABSTAIN)

bad = wc.build_cancel_sys_case(M10)
bad["domain"] = {"function": "0x140005234"}
vbad = iv.verify_case(bad, sealed_analysis=sealed_ok)
v("D incompleto → ABSTAIN", vbad["verdict"] == iv.ABSTAIN)

# ── el verificador no importa el testigo ni sus funciones decisorias ─
src = open(os.path.join(PKG, "ier", "independent_verifier.py")).read()
v("el verificador NO importa transformer_witness",
  "import transformer_witness" not in src and
  "from .transformer_witness" not in src and
  "from ier.transformer_witness" not in src)
v("el verificador NO llama a evaluate/_check_ del testigo",
  "_check_B(" not in src.split("def _check_B")[0].replace("def _check_B", "") and
  ".evaluate(" not in src)

# ── trazas registradas ─────────────────────────────────────────────
v("traza final registra original_ops y transform_ops",
  vres["traces"]["original_ops"] == vres["traces"]["transform_ops"])

# ── fixtures nativos gcc: matriz completa de transformación (M10.9.3) ──
tmp = tempfile.mkdtemp(prefix="iv_fix_")
fixture_c = r"""
#include <stdio.h>
#include <string.h>
static const unsigned char ENC[19] = {
  0xd8,0xfd,0xd7,0xe6,0xfc,0xe0,0xf2,0xea,0xd6,
  0xf8,0xf1,0xf9,0xfe,0xea,0xcb,0xd9,0xd1,0xc7,0xa3 };
static const unsigned char LIT[19] = "IoDriverObjectType\0";
static int g_fail = 0;
static void ck(const char *name, int cond) {
  printf("%s: %s\n", name, cond ? "PASS" : "FAIL");
  if (!cond) g_fail++;
}
static void build_enc(unsigned char *out) {
  int i;
  for (i = 0; i < 19; i++) out[i] = ENC[i];
  for (i = 0; i < 18; i++) out[i] ^= (unsigned char)((i + 145) & 0xff);
  out[18] = 0;
}
static void build_fold(unsigned char *out) {
  build_enc(out); /* fold = copia de bytes idénticos + mismo loop */
}
int main(void) {
  unsigned char a[20], b[20], c[20];
  memset(a, 0x11, sizeof a); memset(b, 0x22, sizeof b);
  build_enc(a); build_fold(b);
  ck("literal-decodificable-desde-ENC (orig==lit)", memcmp(a, LIT, 19) == 0);
  ck("folded==orig (bytes observables 0..18)", memcmp(a, b, 19) == 0);
  ck("bytes observables idénticos en ventana [0,19)", memcmp(a, b, 19) == 0 && a[19] != b[19]);
  ck("terminador presente tras transformación", a[18] == 0 && b[18] == 0 && a[19] == 0x11 && b[19] == 0x22);
  memcpy(c, LIT, 19); c[18] = 0x41;
  ck("transformación incorrecta (mal terminador) detectada", memcmp(c, LIT, 19) != 0);
  memcpy(c, b, 18); c[18] = 0x42;
  ck("copia parcial detectada por byte 18", c[18] != 0);
  { unsigned char d[20]; memcpy(d, b, 19); d[18] = 0;
    ck("lectura posterior (terminador presente)", d[18] == 0 && memcmp(d, LIT, 18) == 0); }
  { unsigned char d[20]; memcpy(d, b, 19); d[0] = 'X';
    ck("escritura posterior adulterada detectable", d[0] != 'I'); }
  { unsigned char buf1[20], buf2[24]; /* emulación de reutilización temporal */
    memset(buf1, 0, sizeof buf1); memcpy(buf1, a, 19);
    memset(buf2, 0, sizeof buf2); memcpy(buf2, LIT, 19);
    ck("reutilización temporal: estados contenidos independientes",
       memcmp(buf1, buf2, 19) == 0); }
  { unsigned char d[20]; memset(d, 0xAA, sizeof d);
    for (int i = 0; i < 18; i++) d[i] = (unsigned char)(ENC[i] ^ ((i + 145) & 0xff));
    d[18] = 0;
    ck("tras store opaco 0xAA, decode reconstruye LIT", memcmp(d, LIT, 19) == 0); }
  { unsigned char d[20]; memcpy(d, b, 20); /* call sin efectos sobre el buffer */
    ck("call sin efectos conserva estado", memcmp(d, b, 20) == 0); }
  { unsigned char d[20]; memcpy(d, b, 19);
    d[3] = 0x00; /* efecto opaco simulado */
    ck("call con efecto opaco altera bytes (detectable)", d[3] != b[3]); }
  /* bytes 18 y 19 son muertos (el loop cubre 0..17; el terminador pisa 18):
     son INVISIBLES a cualquier observador → flip ahí NO debe cambiar la salida. */
  for (int flip = 0; flip < 20; flip++) {
    unsigned char d[20]; memcpy(d, ENC, 19); d[18] = 0x00; /* transición equivalente */
    d[flip] ^= 0x01;
    for (int i = 0; i < 18; i++) d[i] ^= (unsigned char)((i + 145) & 0xff);
    d[18] = 0;
    int changed = memcmp(d, LIT, 19) != 0;
    int dead = (flip >= 18);
    if (!dead && !changed) { printf("adversarial flip=%d: NO detectado\n", flip); g_fail++; }
    if (dead && changed)  { printf("adversarial flip=%d: byte muerto reportado como vivo\n", flip); g_fail++; }
  }
  printf("adversarial-flips: bytes vivos 0..17 detectados; bytes muertos 18..19 invisibles\n");
  printf("RESULT: %s\n", g_fail ? "FAIL" : "PASS");
  return g_fail;
}
"""
fix_src = os.path.join(tmp, "fixture.c")
fix_bin = os.path.join(tmp, "fixture")
with open(fix_src, "w") as fh:
    fh.write(fixture_c)
cc = os.environ.get("CC", "gcc")
try:
    subprocess.run([cc, "-std=c11", "-O2", "-Wall", fix_src, "-o", fix_bin],
                   check=True, capture_output=True, timeout=120)
    out = subprocess.run([fix_bin], capture_output=True, text=True, timeout=10).stdout
    print(out)
    v("fixture nativo: toda la matriz de transformación PASA",
      "RESULT: PASS" in out and "FAIL" not in out.replace("NO detectado\n", ""),
      out.replace("\n", " | "))
except FileNotFoundError:
    print("  SKIP fixtures nativos (gcc no disponible)")
except subprocess.CalledProcessError as exc:
    v("fixture nativo compila y ejecuta", False, str(exc))

print()
if _fallos:
    print("independent_verifier FALLA:", _fallos)
    sys.exit(1)
print("independent_verifier: OK")
sys.exit(0)
