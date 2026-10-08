#!/usr/bin/env python3
"""evidence_search.py — búsqueda de símbolos con el universo registrado como evidencia.
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.

Por qué existe
--------------
La causa de cuatro `NOT_FOUND` falsos en este proyecto fue la misma: se buscó en un
subárbol extraído y se concluyó ausencia. El material estaba en
`RESEARCH/evidence/linux-7.1.3.tar.xz`, en el mismo repositorio.

Esta herramienta hace imposible ese error por construcción:

  * El universo de búsqueda es un **argumento explícito**, no un efecto colateral
    del `cwd`.
  * Un conjunto `--expect` declara qué **debería** contener el corpus. Lo que se
    esperaba y no estaba se reporta `UNREACHABLE`.
  * Sin hits, la clasificación por defecto es `NOT_DETERMINED` + `[NO ABSENCE
    CLAIM]`. `NOT_FOUND` solo se emite con universo **exhaustivo**, es decir,
    `UNREACHABLE` vacío.
  * Un *ledger* en JSON recuerda cada ejecución. Una búsqueda posterior sobre un
    universo mayor sabe decir qué raíz cerró el caso y por qué cambió la clasificación.

Nada de esto es una convención: es la salida por defecto.

Uso
---
    evidence_search.py --query AMDGPU_HW_IP_COMPUTE \\
        --root amd-amdgpu=RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu \\
        --root include-linux=RESEARCH/working/linux-7.1.3/include/linux \\
        --expect include-uapi-drm=linux-7.1.3/include/uapi/drm \\
        --tarball include-uapi-drm=RESEARCH/evidence/linux-7.1.3.tar.xz \\
        --ledger RESEARCH/evidence/search-ledger.jsonl

`--root` es una ruta del sistema de ficheros. `--tarball` empareja un `--expect`
con un tarball del que habría que extraerlo: se busca **dentro** del tarball sin
extraerlo, de modo que la raíz sigue siendo alcanzable.

Códigos de salida
----------------
    0  hit encontrado, o ausencia con universo exhaustivo
    2  sin hits con universo NO exhaustivo  (clasificación `NOT_DETERMINED`)
    3  error de uso
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
import tarfile
import time

TOOL = "evidence_search.py"
TOOL_VERSION = "1.0.0"

# Vocabulario de AGENTS.md. No se inveten estados nuevos.
PROVEN = "PROVEN"
OBSERVED = "OBSERVED"
NOT_FOUND = "NOT_FOUND"
NOT_DETERMINED = "NOT_DETERMINED"
CONFLICT = "CONFLICT"

SKIP_DIRS = {".git", "__pycache__", ".write-lock"}


# --------------------------------------------------------------------------- #
# Raíces
# --------------------------------------------------------------------------- #
class Root:
    """Una raíz del universo: una ruta alcanzable, o una que se esperaba y no lo está."""

    def __init__(self, name: str, spec: str, tarball: str | None = None):
        self.name = name
        self.spec = spec
        self.tarball = tarball          # ruta del tarball, si aplica
        self.inner = spec               # ruta dentro del tarball
        self.present = False
        self.reason = ""                # por qué no está
        self.n_files = 0
        self.n_bytes = 0

    def resolve(self) -> None:
        if self.tarball:
            if not os.path.isfile(self.tarball):
                self.reason = f"tarball ausente: {self.tarball}"
                return
            # Mismo criterio que probe_source() y _iter_tar(): prefijo con o sin
            # el directorio de primer nivel del archivo. Antes se usaba
            # `endswith(inner)`, que falla cuando el tarball no guarda entradas
            # de directorio: la raíz real se reportaba ausente y _iter_tar()
            # no llegaba a consultarse nunca.
            try:
                names, tops = tar_index(self.tarball)
            except (tarfile.TarError, OSError) as exc:
                self.reason = f"tarball ilegible: {exc}"
                return
            inner = self.inner.rstrip("/")
            forms = [inner] + [f"{t}/{inner}" for t in sorted(tops)]
            if any(nm.startswith(f + "/") or nm.rstrip("/") == f
                   for f in forms for nm in names):
                self.present = True
                return
            self.reason = "prefijo no observado en el tarball"
            return
        if os.path.isdir(self.spec):
            self.present = True
            return
        if os.path.isfile(self.spec):
            self.present = True
            return
        self.reason = "ruta ausente en el sistema de ficheros"

    def iter_text_files(self, exts: tuple[str, ...]):
        """Itera (nombre_lógico, lineas) sobre ficheros de texto de la raíz."""
        if not self.present:
            return
        if self.tarball:
            yield from self._iter_tar(exts)
        elif os.path.isfile(self.spec):
            yield from self._iter_one(self.spec, self.spec, exts)
        else:
            for dirpath, dirnames, filenames in os.walk(self.spec):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for fn in sorted(filenames):
                    p = os.path.join(dirpath, fn)
                    if exts and not fn.endswith(exts):
                        continue
                    logical = os.path.relpath(p, self.spec)
                    yield from self._iter_one(p, logical, exts)

    def _iter_tar(self, exts):
        try:
            names, tops = tar_index(self.tarball)
        except (tarfile.TarError, OSError):
            return
        prefix = self.inner.rstrip("/") + "/"
        # El tarball puede llevar un directorio de primer nivel ("linux-7.1.3/")
        # que la raíz interior no incluye. Se prueban ambas formas.
        forms = [prefix] + [f"{t}/{prefix}" for t in sorted(tops)]
        form = next((f for f in forms
                     if any(nm.startswith(f) or nm.rstrip("/") == f[:-1]
                            for nm in names)), None)
        if form is None:
            return
        with tarfile.open(self.tarball, "r:*") as tf:
            for m in tf:
                if not m.isfile() or not m.name.startswith(form):
                    continue
                if exts and not m.name.endswith(exts):
                    continue
                logical = m.name[len(form):]
                self.n_files += 1
                self.n_bytes += m.size
                try:
                    fobj = tf.extractfile(m)
                    if fobj is None:
                        continue
                    yield logical, fobj.read().decode("utf-8", "replace").splitlines()
                except (tarfile.TarError, OSError):
                    continue

    def _iter_one(self, path, logical, exts):
        if exts and not path.endswith(exts):
            return
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return
        if b"\0" in data[:8192]:          # binario: se cuenta pero no se lee
            self.n_files += 1
            self.n_bytes += len(data)
            return
        self.n_files += 1
        self.n_bytes += len(data)
        yield logical, data.decode("utf-8", "replace").splitlines()


# --------------------------------------------------------------------------- #
# Corpus manifest
# --------------------------------------------------------------------------- #
# El manifiesto describe el universo REALMENTE disponible: se mide, no se supone.
# Una raíz figura en él si y solo si fue localizada dentro de una fuente concreta.
# Así, incluir una fuente en el universo hace imposible la ausencia sobre las
# raíces que esa fuente aporta, y por tanto elimina la dependencia de que quien
# busca recuerde qué raíces declarar.

_TAR_INDEX: dict[str, tuple[set[str], set[str]]] = {}
# Métrica de observación del cache. No altera la semántica de búsqueda: solo
# cuenta construcción y aciertos, para que la regresión #4 compruebe una
# propiedad semántica (una lectura por fuente) sin depender de tiempo de pared.
TAR_INDEX_STATS = {"built": 0, "hits": 0, "misses": 0}


def tar_index(path: str) -> tuple[set[str], set[str]]:
    """Índice de miembros de un tarball, construido una sola vez por proceso.

    Sin esto, un corpus tarball con N key-roots abre y descomprime el archivo N
    veces: 158 MB x 7 no termina. Además un índice compartido hace que todas las
    raíces de la misma fuente vean la misma instantánea, que es lo coherente.
    """
    cached = _TAR_INDEX.get(path)
    if cached is not None:
        TAR_INDEX_STATS["hits"] += 1
        return cached
    TAR_INDEX_STATS["misses"] += 1
    names: set[str] = set()
    tops: set[str] = set()
    with tarfile.open(path, "r:*") as tf:
        for m in tf:
            names.add(m.name)
            parts = m.name.split("/", 1)
            if len(parts) == 2 and parts[1]:
                tops.add(parts[0])
    _TAR_INDEX[path] = (names, tops)
    TAR_INDEX_STATS["built"] += 1
    return names, tops


def tar_index_reset() -> None:
    """Limpia índice y métrica. Solo para pruebas: no forma parte de la búsqueda."""
    _TAR_INDEX.clear()
    for k in TAR_INDEX_STATS:
        TAR_INDEX_STATS[k] = 0


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def source_identity(path: str, kind: str) -> dict:
    """Identidad verificable de una fuente. Es lo que permite saber si el
    manifiesto sigue describiendo el material que hay en disco hoy."""
    if kind == "tarball":
        if not os.path.isfile(path):
            return {"present": False, "reason": "fichero ausente"}
        st = os.stat(path)
        return {
            "present": True,
            "kind": "tarball",
            "path": path,
            "size_bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
            "sha256": sha256_file(path),
        }
    if os.path.isdir(path):
        n_files = n_dirs = n_bytes = 0
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            n_dirs += 1
            for fn in filenames:
                n_files += 1
                try:
                    n_bytes += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    pass
        return {
            "present": True,
            "kind": "dir",
            "path": path,
            "n_files": n_files,
            "n_dirs": n_dirs,
            "size_bytes": n_bytes,
        }
    return {"present": False, "reason": "ruta ausente"}


def probe_source(path: str, kind: str, key_roots: list[str]) -> dict[str, dict]:
    """Responde TODOS los key-roots en una sola pasada sobre la fuente.

    Un key-root está presente si y solo si fue observado dentro de la fuente.
    Nunca se infiere: si no se observó, no está.
    """
    result: dict[str, dict] = {k: {"present": False} for k in key_roots}
    if kind == "tarball":
        if not os.path.isfile(path):
            for k in key_roots:
                result[k] = {"present": False, "reason": "tarball ausente"}
            return result
        # Una pasada: se recogen los nombres de miembro y los directorios de
        # primer nivel. Un tarball del kernel lleva prefijo ("linux-7.1.3/…"),
        # así que una key-root sin él no casaría nunca y la fuente aparecería con
        # coverage 0 siendo completa. Por eso se prueban ambas formas y se
        # registra cuál se usó.
        try:
            names, tops = tar_index(path)
        except (tarfile.TarError, OSError) as exc:
            for k in key_roots:
                result[k] = {"present": False, "reason": f"tarball ilegible: {exc}"}
            return result

        for k in key_roots:
            k = k.rstrip("/")
            forms = [k] + [f"{t}/{k}" for t in sorted(tops)]
            matched, n = None, 0
            for form in forms:
                cnt = sum(1 for nm in names
                          if nm.startswith(form + "/") or nm.rstrip("/") == form)
                if cnt:
                    matched, n = form, cnt
                    break
            if matched:
                result[k] = {"present": True, "n_entries": n,
                             "example": matched + "/", "matched_form": matched,
                             "reason": ""}
            else:
                result[k] = {"present": False, "n_entries": 0,
                             "tried_forms": forms[:5],
                             "reason": "prefijo no observado en el tarball"}
        return result

    if os.path.isdir(path):
        for k in key_roots:
            p = os.path.join(path, k)
            if os.path.isdir(p):
                try:
                    n = len(os.listdir(p))
                except OSError:
                    n = 0
                result[k] = {"present": True, "n_entries": n, "example": p, "reason": ""}
            else:
                result[k] = {"present": False, "reason": "ruta ausente bajo la fuente"}
        return result

    for k in key_roots:
        result[k] = {"present": False, "reason": "fuente ausente"}
    return result


DEFAULT_KEY_ROOTS = [
    "drivers/gpu/drm/amd/amdgpu",
    "drivers/gpu/drm/amd/include",
    "drivers/gpu/drm/scheduler",
    "drivers/gpu/drm",
    "include/uapi/drm",
    "include/drm",
    "include/linux",
]


def cmd_manifest(args) -> int:
    sources = []
    for spec in args.source:
        if "=" not in spec:
            print(f"ERROR: --source espera NAME=KIND:PATH, recibí {spec!r}", file=sys.stderr)
            return 3
        name, rest = spec.split("=", 1)
        kind, _, path = rest.partition(":")
        if kind not in ("dir", "tarball"):
            print(f"ERROR: KIND debe ser dir|tarball, recibí {kind!r}", file=sys.stderr)
            return 3
        sources.append((name, kind, path))

    key_roots = args.key_root or DEFAULT_KEY_ROOTS
    manifest = {
        "schema": "corpus-manifest/1",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "key_roots": key_roots,
        "sources": {},
    }
    for name, kind, path in sources:
        ident = source_identity(path, kind)
        entry = {"identity": ident}
        if ident.get("present"):
            entry["covers"] = probe_source(path, kind, key_roots)
            present = sum(1 for v in entry["covers"].values() if v["present"])
            entry["n_key_roots_present"] = present
            entry["n_key_roots_absent"] = len(key_roots) - present
        else:
            entry["covers"] = {k: {"present": False, "reason": "fuente ausente"}
                               for k in key_roots}
            entry["n_key_roots_present"] = 0
            entry["n_key_roots_absent"] = len(key_roots)
        manifest["sources"][name] = entry

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"MANIFEST escrito en {args.out}")
        print()
        print("CORPUS")
        for name, e in manifest["sources"].items():
            ident = e["identity"]
            if not ident.get("present"):
                print(f"  ✗ {name:<14} {ident.get('reason')}")
                continue
            bits = []
            if ident["kind"] == "tarball":
                bits.append(f"{ident['size_bytes']} B")
                bits.append(f"sha256 {ident['sha256'][:16]}…")
            else:
                bits.append(f"{ident['n_files']} ficheros")
                bits.append(f"{ident['size_bytes']} B")
            print(f"  ✓ {name:<14} {ident['path']}  ({', '.join(bits)})")
            print(f"      key-roots presentes: {e['n_key_roots_present']}/{len(key_roots)}")
        print()
        print("KEY-ROOT COVERAGE")
        head = "  " + " " * 34 + "".join(f"{n[:12]:<14}" for n in manifest["sources"])
        print(head)
        for k in key_roots:
            row = f"  {k:<34}"
            for n in manifest["sources"]:
                v = manifest["sources"][n]["covers"].get(k, {})
                row += f"{'✓' if v.get('present') else '✗':<14}"
            print(row)
    return 0


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #
def load_ledger(path: str) -> dict:
    """Carga el histórico por query. Una línea JSON por ejecución."""
    hist: dict[str, list[dict]] = {}
    if not os.path.isfile(path):
        return hist
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            hist.setdefault(rec.get("query", "?"), []).append(rec)
    return hist


def append_ledger(path: str, rec: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def universe_fingerprint(universe: dict) -> str:
    """Huella estable del universo: nombres + qué raíz aportó cada hit."""
    parts = [f"{name}={int(info['present'])}" for name, info in sorted(universe.items())]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Búsqueda
# --------------------------------------------------------------------------- #
def build_pattern(query: str, exact_word: bool) -> re.Pattern:
    """Compila el patrón de búsqueda.

    `\\b` solo se aplica donde el carácter adyacente de la consulta es un carácter
    de palabra. Sin esta condición, una consulta que empieza por `#`, `_` o un
    dígito queda emparejada por `\\b` contra un límite que no puede existir, y la
    búsqueda devuelve cero hits con universo exhaustivo: un `NOT_FOUND` falso,
    que es exactamente el fallo que esta herramienta existe para impedir.
    """
    body = re.escape(query)
    if not exact_word:
        return re.compile(body)
    prefix = r"\b" if query[:1].isalnum() or query[:1] == "_" else ""
    suffix = r"\b" if query[-1:].isalnum() or query[-1:] == "_" else ""
    return re.compile(prefix + body + suffix)




def _fast_word_matcher(query: str, exact_word: bool):
    """FAST PATH A (SEARCH-OPT-003): literal + exact_word=True -> str.find.

    Gate de elegibilidad explícito:
      · `exact_word is True` (la consulta se interpreta con límites de palabra).
      · La literalidad es siempre por construcción: el backend ESCAPA la query
        (build_pattern usa re.escape), luego re.escape(query) matchea la cadena
        literal query; str.find(query) encuentra exactamente esa cadena. Son
        equivalentes para toda query, incluidos metacaracteres (^, $, (?=...),
        (?:...), \\1, a+b) que el backend trata como literales (SEARCH-OPT-001 §3
        pattern_classes: las clases "regex" del corpus son LITERALES escapadas).

    El único matiz semántico de exact_word es el \\b condicional, que este
    matcher replica manualmente: \\b se exige en un lado sólo si el carácter
    adyacente de la query es \\w (isalnum() or "_"), igual que build_pattern.
    \\w de Python = char alfanumérico Unicode o '_'; el límite falla si el
    carácter previo/siguiente es eso mismo, no-\\w o fin de línea lo satisface.

    Devuelve `None` cuando el fast path NO es elegible: el llamador usa
    build_pattern (backend actual, sin cambio de comportamiento).
    """
    if not exact_word:
        return None
    prefix_b = bool(query[:1].isalnum() or query[:1] == "_")
    suffix_b = bool(query[-1:].isalnum() or query[-1:] == "_")
    n = len(query)

    def matches(text: str) -> bool:
        start = 0
        while True:
            pos = text.find(query, start)
            if pos < 0:
                return False
            if prefix_b and pos > 0 and (text[pos - 1].isalnum() or text[pos - 1] == "_"):
                start = pos + 1
                continue
            if suffix_b and pos + n < len(text) and (text[pos + n].isalnum() or text[pos + n] == "_"):
                start = pos + 1
                continue
            return True

    return matches


def search(query: str, roots: list[Root], exact_word: bool,
           include: str | None, match_name: bool = False) -> tuple[list[dict], dict]:
    """Busca en el contenido, o en el nombre del fichero si `match_name`.

    El modo nombre cubre un caso distinto y tan frecuente como el de las
    definiciones: preguntar si un fichero existe. `gmc_v8_1.c`, `amdgpu_main.c`
    y `drivers/gpu/drm/scheduler/` se resolvieron alguna vez mirando el
    contenido cuando lo que se comprobaba era la existencia del fichero.
    """
    filt = re.compile(include) if include else None
    # SEARCH-OPT-003: fast path A. `_fast_word_matcher` devuelve un matcher
    # str.find+boundary si la consulta es elegible (literal + exact_word=True),
    # y None si no: en ese caso se usa build_pattern, el backend de siempre.
    fast = _fast_word_matcher(query, exact_word)
    pat = None if fast is not None else build_pattern(query, exact_word)
    hits: list[dict] = []
    universe: dict[str, dict] = {}

    def matches(text: str) -> bool:
        """Matcher real por línea: fast path A o regex del backend (fallback)."""
        return fast(text) if fast is not None else pat.search(text) is not None

    for root in roots:
        root.resolve()
        universe[root.name] = {
            "present": root.present,
            "spec": root.spec,
            "tarball": root.tarball,
            "reason": root.reason,
        }
        if not root.present:
            continue
        for logical, lines in root.iter_text_files((".c", ".h", ".txt", ".json", ".md")):
            if filt and not filt.search(logical):
                continue
            if match_name:
                if matches(logical):
                    hits.append({
                        "root": root.name,
                        "file": logical,
                        "line": 0,
                        "text": "fichero presente",
                    })
                continue
            for n, line in enumerate(lines, 1):
                if matches(line):
                    hits.append({
                        "root": root.name,
                        "file": logical,
                        "line": n,
                        "text": line.strip()[:200],
                    })
    return hits, universe


def classify(hits: list[dict], universe: dict) -> tuple[str, list[str]]:
    """Regla central. Devuelve (clasificación, reasons)."""
    unreachable = [n for n, u in universe.items() if not u["present"]]
    reasons: list[str] = []
    if hits:
        if unreachable:
            reasons.append(
                f"universo NO exhaustivo: {len(unreachable)} raíz/raíces "
                f"UNREACHABLE ({', '.join(sorted(unreachable))})"
            )
            reasons.append("la clasificación no puede superar OBSERVED")
            return OBSERVED, reasons
        reasons.append("universo exhaustivo y con hits")
        return PROVEN, reasons
    if unreachable:
        reasons.append(
            f"universo NO exhaustivo: {len(unreachable)} raíz/raíces "
            f"UNREACHABLE ({', '.join(sorted(unreachable))})"
        )
        reasons.append("NO se emite ausencia: la raíz que falta puede contener la definición")
        return NOT_DETERMINED, reasons
    reasons.append("universo exhaustivo, sin hits")
    return NOT_FOUND, reasons


def supersedes(query: str, hist: dict, universe: dict, classification: str) -> list[str]:
    """Compara contra ejecuciones anteriores del mismo query."""
    prev = hist.get(query, [])
    if not prev:
        return []
    last = prev[-1]
    out = []
    pcls = last.get("classification")
    if pcls == classification:
        return []
    prev_univ = last.get("universe", {})
    new_roots = sorted(set(universe) - set(prev_univ))
    out.append(f"cambio de clasificación: {pcls} -> {classification}")
    if pcls == NOT_DETERMINED and classification in (PROVEN, OBSERVED):
        closed = [
            n for n, u in universe.items()
            if u["present"] and not prev_univ.get(n, {}).get("present")
        ]
        if closed:
            out.append(f"raíz añadida que cierra el caso: {', '.join(closed)}")
    elif new_roots:
        out.append(f"raíces nuevas respecto a la ejecución anterior: {', '.join(new_roots)}")
    if last.get("universe_fingerprint") and last["universe_fingerprint"] != universe_fingerprint(universe):
        out.append("huella de universo distinta: el alcance de la búsqueda cambió")
    return out


# --------------------------------------------------------------------------- #
# Salida
# --------------------------------------------------------------------------- #
def emit(args, query, hits, universe, classification, reasons, notes,
         manifest_info=None) -> None:
    if args.json:
        print(json.dumps({
            "query": query,
            "classification": classification,
            "reasons": reasons,
            "notes": notes,
            "manifest": manifest_info,
            "universe": universe,
            "universe_fingerprint": universe_fingerprint(universe),
            "hits": hits,
        }, ensure_ascii=False, indent=2))
        return

    print("QUERY")
    print(f"  {query}")
    print()
    print("SEARCH UNIVERSE")
    for name, u in sorted(universe.items()):
        mark = "✓" if u["present"] else "✗"
        if u["present"]:
            where = u["tarball"] or u["spec"]
            print(f"  {mark} {name:<28} {where}")
        else:
            tail = "  ← faltaba" if name not in u.get("_expected", ()) else "  ← faltaba"
            print(f"  {mark} {name:<28} {u['spec']}   {u['reason']}")
    print()
    if hits:
        print("RESULT")
        for h in hits[: args.max_hits]:
            print(f"  {h['root']}:{h['file']}:{h['line']}")
            print(f"      {h['text']}")
        if len(hits) > args.max_hits:
            print(f"  … {len(hits) - args.max_hits} más (--max-hits)")
    else:
        print("RESULT")
        print("  sin coincidencias en el universo declarado")
    print()
    print("CLASSIFICATION")
    print(f"  {classification}")
    if classification == NOT_DETERMINED:
        print("  [NO ABSENCE CLAIM]")
    for r in reasons:
        print(f"  - {r}")
    for n in notes:
        print(f"  * {n}")
    print()
    print(f"  universe_fingerprint = {universe_fingerprint(universe)}")
    if manifest_info:
        m = manifest_info
        print(f"  manifest = {m['file']} · corpus = {m['corpus']} · "
              f"key-roots {m['key_roots_present']}/{m['key_roots_declared']} presentes")


def _fixture_tarball(path: str, members: list[tuple[str, str]]) -> str:
    """Crea un tarball mínimo con los miembros dados. Devuelve su ruta."""
    with tarfile.open(path, "w:gz") as tf:
        for name, content in members:
            data = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            import io
            tf.addfile(info, io.BytesIO(data))
    return path


def regression_2_tarball_prefix(tmp: str) -> list[str]:
    """#2 — los key-roots de un tarball llevan prefijo propio (`linux-7.1.3/`).

    Defecto: las raíces se comparaban contra `m.name.startswith(key_root)` sin
    tener en cuenta el directorio de primer nivel del archivo, de modo que un
    tarball completo del kernel aparecía con coverage 0/7.

    Con el defecto: `n_key_roots_present` = 0 y `matched_form` ausente.
    Corregido: la raíz se localiza y se registra `matched_form`.
    """
    fails = []
    tb = _fixture_tarball(os.path.join(tmp, "r2.tar.gz"), [
        ("linux-7.1.3/drivers/gpu/drm/scheduler/sched_main.c", "x\n"),
        ("linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_ring.c", "y\n"),
        ("linux-7.1.3/README", "z\n"),
    ])
    key_roots = ["drivers/gpu/drm/scheduler", "drivers/gpu/drm/amd/amdgpu",
                 "include/uapi/drm"]
    tar_index_reset()
    cov = probe_source(tb, "tarball", key_roots)

    if not cov["drivers/gpu/drm/scheduler"]["present"]:
        fails.append("#2 scheduler: presente en el tarball, reportado ausente")
    if not cov["drivers/gpu/drm/amd/amdgpu"]["present"]:
        fails.append("#2 amdgpu: presente en el tarball, reportado ausente")
    n_present = sum(1 for v in cov.values() if v["present"])
    if n_present == 0:
        fails.append(f"#2 coverage = 0/3 pese a que la fuente contiene 2 de 3")
    if n_present != 2:
        fails.append(f"#2 coverage = {n_present}/3, esperaba 2/3")
    mf = cov["drivers/gpu/drm/scheduler"].get("matched_form")
    if mf != "linux-7.1.3/drivers/gpu/drm/scheduler":
        fails.append(f"#2 matched_form = {mf!r}, esperaba el prefijo con linux-7.1.3/")
    # caso negativo: una raíz ausente NO debe convertirse en MATCH
    if cov["include/uapi/drm"]["present"]:
        fails.append("#2 include/uapi/drm: ausente en el tarball, reportado presente")
    if cov["include/uapi/drm"].get("n_entries", 0) != 0:
        fails.append("#2 include/uapi/drm: n_entries != 0 para una raíz ausente")
    return fails


def regression_3_manifest_composition(tmp: str) -> list[str]:
    """#3 — las raíces del manifiesto se componen con la ruta de la fuente.

    Defecto: se creaban las raíces con la ruta relativa del key-root tal cual, de
    modo que `drivers/gpu/drm/amd/amdgpu` se resolvía contra el cwd y se
    reportaba ausente aunque la fuente la contuviera.

    Con el defecto: 7/7 raíces `ruta ausente`.
    Corregido: la raíz del manifiesto apunta a <fuente>/<key-root>.
    """
    fails = []
    src = os.path.join(tmp, "corpus-X")
    inner = os.path.join(src, "A", "B", "C")
    os.makedirs(inner, exist_ok=True)
    with open(os.path.join(inner, "alfa.h"), "w", encoding="utf-8") as fh:
        fh.write("#define MARCADOR_UNICO 1\n")

    man_path = os.path.join(tmp, "r3-manifest.json")
    manifest = {
        "schema": "corpus-manifest/1",
        "key_roots": ["A/B/C"],
        "sources": {
            "X": {
                "identity": {"present": True, "kind": "dir", "path": src,
                             "n_files": 1},
                "covers": {"A/B/C": {"present": True, "n_entries": 1,
                                     "example": inner, "reason": ""}},
                "n_key_roots_present": 1,
                "n_key_roots_absent": 0,
            }
        },
    }
    with open(man_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)

    # Reproduce exactamente la composición que hace main() con --manifest.
    entry = manifest["sources"]["X"]
    ident = entry["identity"]
    roots = []
    for k, cov in entry["covers"].items():
        is_tar = ident["kind"] == "tarball"
        if is_tar:
            roots.append(Root(f"X:{k}", k, tarball=ident["path"]))
        else:
            roots.append(Root(f"X:{k}", os.path.join(ident["path"], k)))
    r = roots[0]
    r.resolve()

    if not r.present:
        fails.append(f"#3 la raíz del manifiesto no resolvió: {r.spec} -> {r.reason}")
    if os.path.normpath(r.spec) != os.path.normpath(inner):
        fails.append(f"#3 spec = {r.spec!r}, esperaba {inner!r} (fuente + key-root)")
    if os.path.isabs(r.spec) is not True:
        fails.append("#3 spec no es una ruta absoluta composed desde la fuente")

    # Y el resultado observable: la búsqueda debe encontrar el marcador.
    hits, _ = search("MARCADOR_UNICO", roots, True, None)
    if not hits:
        fails.append("#3 la búsqueda no encontró el fichero del key-root del manifiesto")
    return fails


def regression_4_tarball_cache(tmp: str) -> list[str]:
    """#4 — N key-roots sobre una misma fuente ⇒ una sola construcción del índice.

    Defecto: `tar_index` se llamaba por raíz, así que 7 raícesTrigger 7
    descompresiones completas de 158 MB y la operación no terminaba.

    Se comprueba una propiedad SEMÁNTICA mediante la métrica `TAR_INDEX_STATS`
    (built / hits / misses), no tiempo de pared ni umbrales.
    """
    fails = []
    tb = _fixture_tarball(os.path.join(tmp, "r4.tar.gz"), [
        (f"linux-7.1.3/raiz{i}/f{i}.c", "z\n") for i in range(7)
    ])
    key_roots = [f"raiz{i}" for i in range(7)]
    # Propiedad semántica: una fuente ⇒ una construcción del índice, sea cual
    # sea el número de key-roots. Se mide con TAR_INDEX_STATS, no con tiempo.
    tar_index_reset()
    if TAR_INDEX_STATS["built"] != 0:
        fails.append("#4 la metrica no arranca a cero")

    cov = probe_source(tb, "tarball", key_roots)
    if TAR_INDEX_STATS["built"] != 1:
        fails.append(f"#4 probe_source con 7 raices construyo el indice "
                     f"{TAR_INDEX_STATS['built']} veces, esperaba 1")
    n_present = sum(1 for v in cov.values() if v["present"])
    if n_present != 7:
        fails.append(f"#4 las 7 raices deberian estar presentes, hay {n_present}")

    # Segunda pasada sobre la MISMA fuente: debe ser acierto de cache, no
    # reconstruccion. Esta es la asercion que distingue el defecto.
    built_before = TAR_INDEX_STATS["built"]
    hits_before = TAR_INDEX_STATS["hits"]
    probe_source(tb, "tarball", key_roots)
    if TAR_INDEX_STATS["built"] != built_before:
        fails.append(f"#4 la segunda pasada reconstruyo el indice "
                     f"({built_before} -> {TAR_INDEX_STATS['built']})")
    if TAR_INDEX_STATS["hits"] <= hits_before:
        fails.append("#4 la segunda pasada no registro un acierto de cache")

    # Y por la via de busqueda, que es donde se observo el sintoma original:
    # 7 raices de la misma fuente no pueden sumar 7 construcciones.
    roots = [Root(f"tb:raiz{i}", f"raiz{i}", tarball=tb) for i in range(7)]
    search("z", roots, False, None)
    if TAR_INDEX_STATS["built"] != 1:
        fails.append(f"#4 search() con 7 raices sobre una fuente dejo "
                     f"{TAR_INDEX_STATS['built']} construcciones, esperaba 1")
    for r in roots:
        if not r.present:
            fails.append(f"#4 la raiz {r.inner} no se resolvio presente")
    return fails


def regression_5_manifest_info_reaches_emit(tmp: str) -> list[str]:
    """#5 — `manifest_info` debe llegar a `emit()` sin NameError.

    Defecto: `emit()` leía `manifest_info` sin que nadie se lo pasara, y con
    `--manifest` toda invocación terminaba en NameError.

    Se comprueba el resultado observable en ambos caminos: con manifiesto y sin
    manifiesto.
    """
    fails = []

    class A:
        query = "Q"
        json = False
        max_hits = 5
        name = False

    with_manifest = {
        "file": "/tmp/r5.json", "corpus": "X",
        "identity": {"present": True, "kind": "dir", "path": "/tmp/corpus-X",
                     "n_files": 1},
        "key_roots_declared": 1, "key_roots_present": 1,
    }
    import io as _io
    import contextlib as _ctx

    # Camino con manifiesto: no debe lanzar y debe emitir la línea del manifiesto.
    buf = _io.StringIO()
    try:
        with _ctx.redirect_stdout(buf):
            emit(A(), "Q", [], {}, NOT_DETERMINED, ["razon"], [], with_manifest)
    except NameError as exc:
        fails.append(f"#5 NameError con manifest_info: {exc}")
        return fails
    out = buf.getvalue()
    if "manifest =" not in out:
        fails.append("#5 la salida no refleja manifest_info")
    if "/tmp/r5.json" not in out:
        fails.append("#5 la salida no nombra el fichero de manifiesto")

    # Camino sin manifiesto: no debe lanzar y no debe emitir la línea.
    buf2 = _io.StringIO()
    try:
        with _ctx.redirect_stdout(buf2):
            emit(A(), "Q", [], {}, NOT_DETERMINED, ["razon"], [], None)
    except NameError as exc:
        fails.append(f"#5 NameError con manifest_info=None: {exc}")
        return fails
    out2 = buf2.getvalue()
    if "manifest =" in out2:
        fails.append("#5 emitió línea de manifiesto sin manifiesto")

    # Y la serialización JSON, que también lo consume.
    buf3 = _io.StringIO()
    try:
        with _ctx.redirect_stdout(buf3):
            A.json = True
            emit(A(), "Q", [], {}, NOT_DETERMINED, ["razon"], [], with_manifest)
            A.json = False
    except NameError as exc:
        fails.append(f"#5 NameError en la salida JSON: {exc}")
        return fails
    try:
        doc = json.loads(buf3.getvalue())
    except json.JSONDecodeError as exc:
        fails.append(f"#5 la salida JSON no es parseable: {exc}")
        return fails
    if doc.get("manifest") != with_manifest:
        fails.append("#5 el JSON no conserva manifest_info")
    return fails


def selftest() -> int:
    """Garantías que esta herramienta promete. Si alguna falla, la herramienta miente.

    Cada aserción corresponde a un modo de fallo observado en este proyecto.
    """
    fails: list[str] = []
    total = 0

    def check(name, got, want):
        nonlocal total
        total += 1
        if got != want:
            fails.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    # --- #1: patrones que no producen NOT_FOUND falso -----------------------
    check("#1 patrón #define casa",
          bool(build_pattern("#define AMDGPU_HW_IP_COMPUTE", True)
               .search("#define AMDGPU_HW_IP_COMPUTE      1")), True)
    check("#1 patrón #define NO casa con prefijo distinto",
          bool(build_pattern("#define AMDGPU_HW_IP_COMPUTE", True)
               .search("#define AMDGPU_HW_IP_GFX          0")), False)
    check("#1 patrón con guion bajo inicial",
          bool(build_pattern("_foo", True).search("x _foo y")), True)
    check("#1 patrón respeta límites de palabra",
          bool(build_pattern("foo", True).search("foobar")), False)
    check("#1 patrón subword no respeta límites",
          bool(build_pattern("foo", False).search("foobar")), True)

    # --- Clasificación: la regla central -----------------------------------
    pres = {"r": {"present": True, "spec": "/x", "tarball": None, "reason": ""}}
    unre = {"r": {"present": True, "spec": "/x", "tarball": None, "reason": ""},
            "q": {"present": False, "spec": "/y", "tarball": None, "reason": "ausente"}}
    check("clasificación: sin hits, universo exhaustivo -> NOT_FOUND",
          classify([], pres)[0], NOT_FOUND)
    check("clasificación: sin hits, universo incompleto -> NOT_DETERMINED",
          classify([], unre)[0], NOT_DETERMINED)
    check("clasificación: con hits, universo incompleto -> OBSERVED",
          classify([{"x": 1}], unre)[0], OBSERVED)
    check("clasificación: con hits, universo exhaustivo -> PROVEN",
          classify([{"x": 1}], pres)[0], PROVEN)
    check("clasificación: sin hits nunca devuelve PROVEN",
          classify([], pres)[0] == PROVEN, False)
    check("clasificación: universo incompleto razona el hueco",
          any("UNREACHABLE" in r for r in classify([], unre)[1]), True)

    # --- Regresiones #2–#5 --------------------------------------------------
    import tempfile
    with tempfile.TemporaryDirectory(prefix="evidence_search-selftest-") as tmp:
        for label, fn in (("#2", regression_2_tarball_prefix),
                          ("#3", regression_3_manifest_composition),
                          ("#4", regression_4_tarball_cache),
                          ("#5", regression_5_manifest_info_reaches_emit)):
            before = len(fails)
            try:
                fails.extend(fn(tmp))
            except Exception as exc:                     # noqa: BLE001
                fails.append(f"{label} la regresión lanzó {type(exc).__name__}: {exc}")
            total += 1
            if len(fails) == before:
                print(f"  {label} PASS")

    if fails:
        print("SELFTEST FALLIDO")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"SELFTEST OK — {total} garantías verificadas")
    print("  · los patrones no producen NOT_FOUND falso")
    print("  · la ausencia exige universo exhaustivo")
    print("  · un universo incompleto degrada PROVEN a OBSERVED")
    print("  · las key-roots de un tarball se localizan bajo su prefijo propio")
    print("  · las raíces del manifiesto se componen con la fuente")
    print("  · un tarball se indexa una vez, no una vez por raíz")
    print("  · manifest_info llega a emit() con y sin manifiesto")
    return 0


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "manifest":
        m = argparse.ArgumentParser(prog=f"{TOOL} manifest",
                                    description="Medir el universo realmente "
                                                "disponible y escribir el manifiesto.")
        m.add_argument("--source", action="append", default=[], required=True,
                       metavar="NAME=KIND:PATH",
                       help="fuente real: dir:PATH o tarball:PATH (repetible)")
        m.add_argument("--key-root", action="append", default=[], metavar="PATH",
                       help="raíz clave que debe quedar cubierta (repetible)")
        m.add_argument("--out", required=True, help="fichero JSON de salida")
        m.add_argument("--json", action="store_true")
        return cmd_manifest(m.parse_args(argv[1:]))
    if "--selftest" in argv:
        return selftest()

    ap = argparse.ArgumentParser(
        description="Búsqueda de símbolos con el universo de búsqueda como evidencia.",
    )
    ap.add_argument("--selftest", action="store_true",
                    help="verificar las garantías internas y salir")
    ap.add_argument("--query", required=True,
                    help="texto buscado, LITERAL (se escapa internamente; "
                         "no es una expresión regular)")
    ap.add_argument("--root", action="append", default=[], metavar="NAME=PATH",
                    help="raíz alcanzable del sistema de ficheros (repetible)")
    ap.add_argument("--expect", action="append", default=[], metavar="NAME=PATH",
                    help="raíz que el corpus DEBERÍA contener (repetible)")
    ap.add_argument("--tarball", action="append", default=[], metavar="NAME=ARCHIVE",
                    help="tarball del que extraer un --expect, buscando dentro sin extraer")
    ap.add_argument("--include", help="regex de ficheros a considerar dentro de cada raíz")
    ap.add_argument("--subword", action="store_true",
                    help="no exigir límites de palabra")
    ap.add_argument("--name", action="store_true",
                    help="coincidir con el nombre del fichero, no con su contenido")
    ap.add_argument("--manifest", help="manifest de corpus; con --corpus, las "
                                        "raíces se derivan del manifiesto en vez "
                                        "de declararse a mano")
    ap.add_argument("--corpus", help="nombre de la fuente dentro del manifiesto a "
                                     "usar como universo")
    ap.add_argument("--ledger", help="JSONL donde anotar cada ejecución")
    ap.add_argument("--max-hits", type=int, default=25)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    tarballs = {}
    for spec in args.tarball:
        if "=" not in spec:
            ap.error(f"--tarball espera NAME=ARCHIVE, recibí {spec!r}")
        name, arch = spec.split("=", 1)
        tarballs[name] = arch

    roots: list[Root] = []
    for spec in args.root:
        if "=" not in spec:
            ap.error(f"--root espera NAME=PATH, recibí {spec!r}")
        name, path = spec.split("=", 1)
        roots.append(Root(name, path))

    expected_names = []
    for spec in args.expect:
        if "=" not in spec:
            ap.error(f"--expect espera NAME=PATH, recibí {spec!r}")
        name, path = spec.split("=", 1)
        expected_names.append(name)
        roots.append(Root(name, path, tarball=tarballs.get(name)))

    # El manifiesto sustituye a la memoria: si se nombra un corpus, TODAS las
    # key-roots que esa fuente aporta entran en el universo, estén o no
    # presentes. Una key-root ausente convierte la ausencia en
    # NOT_DETERMINED, que es lo que impide el falso NOT_FOUND.
    manifest_info = None
    if args.manifest:
        if not os.path.isfile(args.manifest):
            ap.error(f"--manifest no existe: {args.manifest}")
        with open(args.manifest, encoding="utf-8") as fh:
            manifest = json.load(fh)
        if manifest.get("schema") != "corpus-manifest/1":
            ap.error(f"schema de manifiesto no soportado: {manifest.get('schema')!r}")
        if args.corpus:
            if args.corpus not in manifest["sources"]:
                ap.error(
                    f"corpus {args.corpus!r} no está en el manifiesto; "
                    f"disponibles: {', '.join(sorted(manifest['sources']))}"
                )
            entry = manifest["sources"][args.corpus]
            ident = entry["identity"]
            if not ident.get("present"):
                ap.error(f"la fuente del corpus {args.corpus!r} no está presente")
            src = ident["path"]
            is_tar = ident["kind"] == "tarball"
            for k, cov in entry["covers"].items():
                rname = f"{args.corpus}:{k}"
                if rname in {r.name for r in roots}:
                    continue
                # Para un tarball, `spec` es la ruta DENTRO del archivo; para un
                # directorio, hay que componerla con la raíz de la fuente, o la
                # raíz se resuelve contra el cwd y aparece como ausente.
                if is_tar:
                    roots.append(Root(rname, k, tarball=src))
                else:
                    roots.append(Root(rname, os.path.join(src, k)))
                expected_names.append(rname)
            manifest_info = {
                "file": args.manifest,
                "corpus": args.corpus,
                "identity": ident,
                "key_roots_declared": len(entry["covers"]),
                "key_roots_present": entry["n_key_roots_present"],
            }

    # Una raíz declarada y presente no es una ausencia; una declarada y ausente
    # es un hueco del universo y por tanto impide emitir NOT_FOUND.
    hits, universe = search(args.query, roots, not args.subword, args.include,
                           match_name=args.name)
    for name in expected_names:
        if name in universe:
            universe[name]["expected"] = True
    classification, reasons = classify(hits, universe)

    hist = load_ledger(args.ledger) if args.ledger else {}
    notes = supersedes(args.query, hist, universe, classification)

    emit(args, args.query, hits, universe, classification, reasons, notes,
         manifest_info)

    if args.ledger:
        append_ledger(args.ledger, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "tool": TOOL,
            "tool_version": TOOL_VERSION,
            "query": args.query,
            "classification": classification,
            "reasons": reasons,
            "notes": notes,
            "universe": {k: {kk: vv for kk, vv in v.items()} for k, v in universe.items()},
            "universe_fingerprint": universe_fingerprint(universe),
            "n_hits": len(hits),
            "mode": "name" if args.name else "content",
            "manifest": manifest_info,
            "cwd": os.getcwd(),
        })
        print(f"  ledger += {args.ledger}")

    if classification == NOT_DETERMINED:
        return 2
    return 0


# --------------------------------------------------------------------------- #
# Limitación conocida, medida — no la minimizar
# --------------------------------------------------------------------------- #
# Esta herramienta NO puede saber qué raíz se olvidó declarar.
#
# Medido: buscando `#define AMDGPU_HW_IP_COMPUTE` sobre el subárbol
# `amd/amdgpu` y declarando SOLO esa raíz, emite `NOT_FOUND`. Y es un
# `NOT_FOUND` real: esa raíz no contiene la definición. Pero la definición
# estaba en `include/uapi/drm/amdgpu_drm.h:934`, en el mismo repositorio.
#
# Es decir: los cuatro fallos de ausencia de este proyecto fueron todos
# «se olvidó declarar una raíz», que es exactamente el fallo que la
# herramienta no detecta por sí sola.
#
# Lo que sí hace, y está medido:
#   · hace el universo declarado VISIBLE y PERSISTIDO, de modo que un
#     universo de una sola raíz se ve como tal en la salida;
#   · `--expect` permite declarar lo que debería estar, y entonces la
#     ausencia pasa a `NOT_DETERMINED` con rc=2, aunque no haya hits;
#   · el ledger registra la transición cuando la raíz llega después;
#   · `--selftest` impide que un fallo interno produzca `NOT_FOUND` falso.
#
# Endurecimiento pendiente, no implementado: un manifiesto del corpus
# completo del kernel, del que derivar `--expect` en vez de recordarlo. Sin
# manifiesto, la disciplina de declarar sigue recayendo en quien busca.


if __name__ == "__main__":
    sys.exit(main())
