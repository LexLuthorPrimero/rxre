#!/usr/bin/env python3
"""Phase 1 infrastructure — shared schema, controlled vocabularies and TSV I/O
for the four canonical knowledge artifacts (SRC, KB, NEG, CTR).

Provenance of this module
-------------------------
Transcription of the DESIGN_FROZEN specification of the investigation /
knowledge / provenance / learning / anti-repetition system, sections B.2-B.8,
B.12 and D.3.  The column sets below are the *named* column lists of that
specification and are authoritative.  A count stated elsewhere in the design
(`D.3`: "20 col", "33 col", "15 col") disagrees with the named lists and is
recorded as a DOCUMENTARY error; see KNOWLEDGE-POLICY.md section 3.

Frozen constraints honoured here
--------------------------------
* No column is added, removed, renamed or reordered (`C8`, `C9`).
* No taxonomy, epistemic state or provenance rule is modified.
* A field value may never contain a TAB, CR or LF: it would corrupt the row.
  Such values are rejected, never escaped and never silently truncated.
* An unavailable datum is written with an explicit sentinel.  It is never
  inferred and never left empty.
* git status is NOT a source of truth about content: SHA256 of the real
  object is the identity of the content.  git contributes COMMIT and the
  GIT_STATE token only.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from typing import Dict, Iterable, List, Sequence, Tuple

# --------------------------------------------------------------------------
# 1. Canonical artifacts: artifact key -> (filename, ordered column tuple)
# --------------------------------------------------------------------------

SRC = "SRC"
KB = "KB"
NEG = "NEG"
CTR = "CTR"

FILENAMES: Dict[str, str] = {
    SRC: "SOURCE-REGISTRY.tsv",
    KB: "KNOWLEDGE-BASE.tsv",
    NEG: "NEGATIVE-KNOWLEDGE.tsv",
    CTR: "CONTRADICTIONS.tsv",
}

COLUMNS: Dict[str, Tuple[str, ...]] = {
    SRC: (
        "SOURCE_ID", "ENTITY_CLASS", "SOURCE_TYPE", "VERSION", "VERSION_BASIS",
        "COMMIT", "RETRIEVAL_DATE", "RETRIEVAL_BASIS", "PATH_OR_URL", "SHA256",
        "SIZE", "TEMPORALITY", "OBSOLESCENCE", "APPLICABILITY", "HOST_SCOPE",
        "ACCESS", "NOTES",
    ),
    KB: (
        "KB_ID", "CLASS", "STATEMENT", "CONCEPT", "SYMBOL", "QUESTION_TYPE",
        "SCOPE", "EPISTEMIC_STATE", "OBSOLESCENCE", "SUPERSEDES",
        "SUPERSEDED_BY", "SOURCE_ID", "SRC_FILE_LINE", "APPLICABILITY",
        "DERIVATION_FROM", "ASSUMPTIONS", "FALSIFIER", "MODEL_AFFECTED",
        "HUMAN_DECISION_REF", "CODE_ID", "CODE_SHA256", "LOC_ANCHOR", "TEST_ID",
        "TEST_SHA256", "OBSERVED_IN", "ARTIFACT_SHA256", "HOST_SCOPE",
        "TEMPORALITY", "VALUE", "UNIT", "ERROR_KIND", "CAUSE", "CORRECTION",
        "PREVENTION", "RELATED_CONTRADICTION", "RELATED_NEGATIVE",
    ),
    NEG: (
        "NEG_ID", "QUERY", "SCOPE", "SOURCES_SEARCHED", "VERSION_SCOPE",
        "SEARCH_METHOD", "ACCESS", "EPISTEMIC_STATE", "WHY_NOT_FOUND",
        "LIMITATION", "RETRIEVAL_DATE", "REUSE_CONDITION", "LIFECYCLE",
        "SUPERSEDED_BY",
    ),
    CTR: (
        "CTR_ID", "CLAIM_A", "SOURCE_A", "CLAIM_B", "SOURCE_B", "KIND", "SCOPE",
        "RESOLUTION_STATE", "EVIDENCE", "FALSIFIER", "RESOLUTION",
        "RESOLUTION_BASIS", "OPEN_DECISION", "SUPERSEDED_BY",
    ),
}

# --------------------------------------------------------------------------
# 2. Sentinels for unavailable / undetermined data.
#    A sentinel is a written, machine-checkable value.  It is never a blank.
# --------------------------------------------------------------------------

S_NOT_AVAILABLE = "NOT_AVAILABLE"      # the source/object does not exist or is unreadable
S_NOT_DETERMINED = "NOT_DETERMINED"    # observation happened; does not settle the property
S_NOT_DECLARED = "NOT_DECLARED"        # the source itself declares no VERSION
S_UNKNOWN = "UNKNOWN"                  # no host declared; AGENTS.md:38-41 forbids assigning one
S_NOT_APPLICABLE = "NOT_APPLICABLE"    # the question has no valid meaning in this context

# --------------------------------------------------------------------------
# 2b. Identifier and value shapes.
#     Defined before the vocabularies because SENTINEL_PATTERNS references them.
# --------------------------------------------------------------------------

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SOURCE_ID_RE = re.compile(r"^SRC-[0-9a-f]{12}$")
KB_ID_RE = re.compile(r"^KB-[0-9a-f]{12}$")
NEG_ID_RE = re.compile(r"^NEG-[0-9a-f]{12}$")
CTR_ID_RE = re.compile(r"^CTR-[0-9a-f]{12}$")

# Fixed token prefix used inside SRC.NOTES to make the git relation explicit and
# machine-checkable without adding a column to the frozen schema.  See
# KNOWLEDGE-POLICY.md section 6 for why no GIT_STATE column was added.
GIT_STATE_TOKEN_RE = re.compile(r"GIT_STATE=(TRACKED_CLEAN|TRACKED_DIRTY|UNTRACKED|NOT_A_GIT_REPO)")

# --------------------------------------------------------------------------
# 3. Controlled vocabularies (frozen: DESIGN_FROZEN B.4, B.5, B.7, B.8, B.12)
# --------------------------------------------------------------------------

ENTITY_CLASS: Tuple[str, ...] = (
    "SOURCE", "CODE_REF", "TEST_REF", "ARTIFACT", "MODEL", "NOT_A_SOURCE",
)

SOURCE_TYPE: Tuple[str, ...] = (
    "KERNEL_SOURCE", "KERNEL_DOC", "SPECIFICATION", "PROJECT_ARTIFACT",
    "GENERATED_ARTIFACT", "WEB_PAGE",
)

OBSOLESCENCE: Tuple[str, ...] = (
    "CURRENT", "HISTORICAL", "SUPERSEDED", "CONTRADICTED", "VERSION_SPECIFIC",
    "HOST_SPECIFIC", "UNKNOWN_VALIDITY", "REFERENT_DRIFT",
)

APPLICABILITY: Tuple[str, ...] = (
    "DIRECT", "INFERENCE", S_NOT_APPLICABLE, S_NOT_DETERMINED,
)

ACCESS: Tuple[str, ...] = ("GRANTED", "DENIED", "SOURCE_ABSENT")

# Named access states.  Referenced by the generator so that both sides of the
# contract read one source of truth instead of repeating string literals.
A_GRANTED, A_DENIED, A_SOURCE_ABSENT = ACCESS

# TEMPORALITY domain is the one already in use by
# 01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-INVENTORY-ROUTING.tsv
# (measured distribution: HISTORICAL 1445, MIXED 111, CURRENT 16, UNKNOWN 4).
TEMPORALITY: Tuple[str, ...] = ("CURRENT", "HISTORICAL", "MIXED", S_UNKNOWN)

KB_CLASS: Tuple[str, ...] = (
    "FACT", "EXTRACTED_FACT", "OBSERVATION", "MEASUREMENT", "DERIVATION",
    "MODEL_CHOICE", "HUMAN_REQUIREMENT", "HUMAN_POLICY",
    "IMPLEMENTATION_HISTORY", "IMPLEMENTATION_FACT", "TEST_RESULT",
    "CONCLUSION", "HYPOTHESIS", "OPEN_QUESTION", "ASSUMPTION", "LIMITATION",
    "ERROR", "NEGATIVE_RESULT", "CONTRADICTION",
)

EPISTEMIC_STATE: Tuple[str, ...] = (
    "UNKNOWN", "NOT_INVESTIGATED", "NOT_FOUND", "NOT_OBSERVED",
    "NOT_AVAILABLE", "NOT_DETERMINED", "NOT_APPLICABLE", "PROVEN_ABSENT",
)

ERROR_KIND: Tuple[str, ...] = (
    "TOOLING", "METHODOLOGICAL", "FACTUAL", "DOCUMENTARY", "INTERPRETATION",
    "IMPLEMENTATION",
)

SEARCH_METHOD: Tuple[str, ...] = ("DIRECTED_QUERY", "SWEEP")
LIFECYCLE: Tuple[str, ...] = ("CURRENT", "STALE", "SUPERSEDED")
CTR_KIND: Tuple[str, ...] = (
    "REAL", "VERSION", "CONTEXT", "UNIT", "NOMENCLATURE", "DOC_VS_CODE",
    "SCOPE", "TEMPORAL", "DERIVATION",
)
RESOLUTION_STATE: Tuple[str, ...] = ("OPEN", "RESOLVED", "SUPERSEDED")

# artifact -> column -> allowed values.  Columns absent from this map are free
# text and are validated only for the structural rules below.
#
# A column belongs here ONLY when its value set is a closed enumeration.  A
# column whose value is "a sentinel, or a measured value of some shape" belongs
# in SENTINEL_PATTERNS instead; conflating the two would reject every real
# measurement (a numeric SIZE, a 40-hex COMMIT, a declared VERSION).
DOMAINS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    SRC: {
        "ENTITY_CLASS": ENTITY_CLASS,
        "SOURCE_TYPE": SOURCE_TYPE + (S_NOT_APPLICABLE,),
        "TEMPORALITY": TEMPORALITY,
        "OBSOLESCENCE": OBSOLESCENCE,
        "APPLICABILITY": APPLICABILITY,
        "HOST_SCOPE": (S_UNKNOWN,),
        "ACCESS": ACCESS,
    },
    KB: {
        "CLASS": KB_CLASS,
        "EPISTEMIC_STATE": EPISTEMIC_STATE,
        "OBSOLESCENCE": OBSOLESCENCE,
        "APPLICABILITY": APPLICABILITY,
        "HOST_SCOPE": (S_UNKNOWN,),
        "TEMPORALITY": TEMPORALITY,
        "ERROR_KIND": ERROR_KIND,
    },
    NEG: {
        "SEARCH_METHOD": SEARCH_METHOD,
        "ACCESS": ACCESS,
        "EPISTEMIC_STATE": EPISTEMIC_STATE,
        "LIFECYCLE": LIFECYCLE,
    },
    CTR: {
        "KIND": CTR_KIND,
        "RESOLUTION_STATE": RESOLUTION_STATE,
    },
}

# artifact -> column -> (sentinels accepted, pattern a real value must match).
# A value is valid when it is one of the sentinels or matches the pattern.
SENTINEL_PATTERNS: Dict[str, Dict[str, Tuple[Tuple[str, ...], "re.Pattern[str]"]]] = {
    SRC: {
        "VERSION": ((S_NOT_DECLARED,), re.compile(r"^\S(?:.*\S)?$")),
        "COMMIT": ((S_NOT_AVAILABLE,), COMMIT_RE),
        "SIZE": ((S_NOT_AVAILABLE,), re.compile(r"^(0|[1-9][0-9]*)$")),
        "SHA256": ((S_NOT_AVAILABLE,), SHA256_RE),
        "RETRIEVAL_DATE": ((S_NOT_DETERMINED, S_NOT_AVAILABLE),
                           re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$")),
        "RETRIEVAL_BASIS": ((S_NOT_DETERMINED,), re.compile(r"^\S(?:.*\S)?$")),
        "VERSION_BASIS": ((S_NOT_DETERMINED,), re.compile(r"^\S(?:.*\S)?$")),
        "SOURCE_ID": ((), SOURCE_ID_RE),
        "PATH_OR_URL": ((), re.compile(r"^\S(?:.*\S)?$")),
    },
    KB: {
        "KB_ID": ((), KB_ID_RE),
        "RETRIEVAL_DATE": ((S_NOT_DETERMINED,), ISO_INSTANT_RE),
    },
    NEG: {
        "NEG_ID": ((), NEG_ID_RE),
        "RETRIEVAL_DATE": ((S_NOT_DETERMINED,), ISO_INSTANT_RE),
    },
    CTR: {
        "CTR_ID": ((), CTR_ID_RE),
    },
}

# --------------------------------------------------------------------------
# 4. (identifier shapes moved to section 2b, above the vocabularies)
# --------------------------------------------------------------------------


class SchemaError(ValueError):
    """Raised when a value or a header violates the frozen schema."""


class HeaderError(SchemaError):
    """Raised when a TSV header is not exactly the frozen column sequence."""


# --------------------------------------------------------------------------
# 5. Header validation (validator subset SCHEMA; Phase 1 minimal)
# --------------------------------------------------------------------------

def header_report(actual: Sequence[str], expected: Sequence[str]) -> Dict[str, List[str]]:
    """Compare an actual header against the frozen expected header.

    Detects, separately: missing columns, extra columns, duplicated columns and
    a correct set in the wrong order.  Returns a report; never raises, so a
    caller can report every defect at once.
    """
    report: Dict[str, List[str]] = {
        "MISSING": [], "EXTRA": [], "DUPLICATE": [], "ORDER": [], "OK": [],
    }
    seen: Dict[str, int] = {}
    for col in actual:
        seen[col] = seen.get(col, 0) + 1
    for col, n in seen.items():
        if n > 1:
            report["DUPLICATE"].append("%s x%d" % (col, n))
    act = [c for c in actual if c not in expected or seen[c] == 1]
    act_once = [c for c in actual]
    dedup_preserving_order: List[str] = []
    for c in act_once:
        if c not in dedup_preserving_order:
            dedup_preserving_order.append(c)
    for col in expected:
        if col not in seen:
            report["MISSING"].append(col)
    for col in seen:
        if col not in expected:
            report["EXTRA"].append(col)
    if not (report["MISSING"] or report["EXTRA"] or report["DUPLICATE"]):
        if dedup_preserving_order != list(expected):
            first = next(
                (i for i, (a, b) in enumerate(zip(dedup_preserving_order, expected)) if a != b),
                min(len(dedup_preserving_order), len(expected)),
            )
            report["ORDER"].append(
                "first divergence at index %d: got %r, expected %r"
                % (first,
                   dedup_preserving_order[first:first + 1] or ["<end>"],
                   list(expected)[first:first + 1])
            )
        else:
            report["OK"].append("header matches frozen schema (%d columns)" % len(expected))
    return report


def validate_header(actual: Sequence[str], expected: Sequence[str]) -> None:
    rep = header_report(actual, expected)
    if rep["OK"]:
        return
    raise HeaderError(
        "header violates frozen schema: MISSING=%s EXTRA=%s DUPLICATE=%s ORDER=%s"
        % (rep["MISSING"], rep["EXTRA"], rep["DUPLICATE"], rep["ORDER"])
    )


# --------------------------------------------------------------------------
# 6. Row-level structural validation
# --------------------------------------------------------------------------

_ILLEGAL = ("\t", "\r", "\n")


def validate_value(artifact: str, column: str, value: str) -> None:
    """Reject a value that cannot be stored, or that is outside its domain."""
    if not isinstance(value, str):
        raise SchemaError("%s.%s: value must be str, got %r" % (artifact, column, type(value).__name__))
    if value == "":
        raise SchemaError(
            "%s.%s: empty value forbidden; use an explicit sentinel (%s)"
            % (artifact, column, ", ".join(sorted({S_NOT_AVAILABLE, S_NOT_DETERMINED, S_UNKNOWN, S_NOT_APPLICABLE})))
        )
    for bad in _ILLEGAL:
        if bad in value:
            raise SchemaError(
                "%s.%s: value contains %r which would corrupt the TSV row"
                % (artifact, column, bad)
            )
    domain = DOMAINS.get(artifact, {}).get(column)
    if domain is not None:
        if value not in domain:
            raise SchemaError(
                "%s.%s: %r not in frozen domain %s" % (artifact, column, value, list(domain))
            )
        return
    spec = SENTINEL_PATTERNS.get(artifact, {}).get(column)
    if spec is None:
        return
    sentinels, pattern = spec
    if value in sentinels or pattern.match(value):
        return
    raise SchemaError(
        "%s.%s: %r is neither an accepted sentinel %s nor a value matching %s"
        % (artifact, column, value, list(sentinels), pattern.pattern)
    )


def validate_row(artifact: str, row: Dict[str, str]) -> None:
    cols = COLUMNS[artifact]
    extra = [c for c in row if c not in cols]
    if extra:
        raise SchemaError("%s: unknown columns %s" % (artifact, extra))
    missing = [c for c in cols if c not in row]
    if missing:
        raise SchemaError("%s: missing columns %s" % (artifact, missing))
    for col in cols:
        validate_value(artifact, col, row[col])


# --------------------------------------------------------------------------
# 7. TSV I/O
# --------------------------------------------------------------------------

def artifact_path(directory: str, artifact: str) -> str:
    return os.path.join(directory, FILENAMES[artifact])


def write_tsv(path: str, artifact: str, rows: Iterable[Dict[str, str]]) -> str:
    """Write header + rows.  Validates the header and every value first.

    Returns the SHA256 of the bytes written.  Refuses to write a file whose
    header is not the frozen one, so a drift can never reach disk.
    """
    cols = COLUMNS[artifact]
    lines = ["\t".join(cols)]
    for i, row in enumerate(rows):
        validate_row(artifact, row)
        lines.append("\t".join(row[c] for c in cols))
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    import hashlib
    with open(path, "wb") as fh:
        fh.write(payload)
    return hashlib.sha256(payload).hexdigest()


def read_tsv(path: str, artifact: str) -> List[Dict[str, str]]:
    """Read a TSV, validating the header against the frozen schema."""
    with open(path, "r", encoding="utf-8", newline="") as fh:
        raw = fh.read()
    if not raw:
        raise HeaderError("%s: file is empty; a header row is required" % path)
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    header = lines[0].split("\t")
    validate_header(header, COLUMNS[artifact])
    rows: List[Dict[str, str]] = []
    cols = COLUMNS[artifact]
    for n, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        if len(cells) != len(cols):
            raise SchemaError(
                "%s:%d: expected %d fields, found %d" % (path, n, len(cols), len(cells))
            )
        rows.append(dict(zip(cols, cells)))
    return rows


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
