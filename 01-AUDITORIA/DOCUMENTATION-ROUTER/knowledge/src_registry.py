#!/usr/bin/env python3
"""Phase 1 infrastructure — SOURCE REGISTRY generator (artifact ``SRC``).

Contract implemented here (DESIGN_FROZEN B.5, B.13, D.3, and prompt E):

    SOURCE_ID -> object/file -> SHA256 -> VERSION/COMMIT when they really
    exist -> git state

Design constraints this module obeys
------------------------------------
* ``SHA256`` is the identity of the content and is always computed from the
  real object.  A caller-supplied hash is *verified*, never trusted, and a
  mismatch is rejected.  git status is never a source of truth about content.
* ``VERSION`` is never invented.  Absent a declared version the row carries
  ``NOT_DECLARED`` plus a non-empty ``VERSION_BASIS`` justification.
* ``COMMIT`` is never invented.  It is the per-file last commit when the file
  is versioned by git, otherwise ``NOT_AVAILABLE``.
* ``RETRIEVAL_DATE`` is the acquisition/verification instant, never a
  publication date.  ``RETRIEVAL_BASIS`` records how it was obtained.  A
  publication date has no column in the frozen schema and is only ever written
  into ``NOTES`` under an explicit ``PUBLICATION_DATE=`` token.
* ``TEMPORALITY`` and ``OBSOLESCENCE`` are independent axes.  ``TEMPORALITY``
  answers "when was this content valid"; ``OBSOLESCENCE`` answers "what is the
  lifecycle of this registration".  This generator determines neither, so both
  default to ``UNKNOWN`` / ``UNKNOWN_VALIDITY``.  It never infers validity from
  the existence of a file.
* The generator asserts only what it measured.  Everything else carries an
  explicit sentinel.
* Replacing a working file follows AGENTS.md:371-377: byte-for-byte copy to a
  recovery path, SHA256 recorded, candidate compared before it is applied.

Phase 1 scope
-------------
This module *can* enumerate a tree, but enumerating the project corpus is
Phase 2 (migration) and is out of scope here.  The CLI therefore requires an
explicit path list; it never walks the repository unless ``--walk`` is given
together with an explicit root, and ``--walk`` is not used by the Phase 1 test
suite.  See KNOWLEDGE-POLICY.md section 7.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Sequence

import knowledge_schema as ks

READ_CHUNK = 1 << 20


# --------------------------------------------------------------------------
# Measured facts
# --------------------------------------------------------------------------

def sha256_file(path: str) -> str:
    """SHA256 of the real bytes of ``path``.  Raises on unreadable input."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(READ_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(path: str, claimed: str) -> str:
    """Return the real SHA256, rejecting a claimed value that does not match.

    This is the enforcement point for "SHA256 must come from the real object":
    an invented hash cannot pass here.
    """
    real = sha256_file(path)
    if claimed != real:
        raise ks.SchemaError(
            "SHA256_REJECTED: claimed %s but the real object %s hashes to %s"
            % (claimed, path, real)
        )
    return real


def derive_source_id(rel_path: str) -> str:
    """``SOURCE_ID`` derived from the repository-relative path.

    DERIVED, not invented: a stable function of the path, so the same object
    always gets the same identifier without a registry lookup (B.4).
    """
    digest = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()
    return "SRC-" + digest[:12]


def _git(repo_root: str, *args: str) -> Optional[str]:
    """Read-only git query.  Returns None when git is unavailable or fails."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def git_facts(rel_path: str, repo_root: str) -> Dict[str, str]:
    """Measure git facts for one path.  Read-only git commands only.

    Returns keys ``COMMIT`` and ``GIT_STATE``.  ``COMMIT`` is the last commit
    that touched the file, and is ``NOT_AVAILABLE`` when the file is not
    versioned by git — never a repository-wide HEAD standing in for it.
    """
    top = _git(repo_root, "rev-parse", "--show-toplevel")
    if top is None:
        return {"COMMIT": ks.S_NOT_AVAILABLE, "GIT_STATE": "NOT_A_GIT_REPO"}
    tracked = _git(repo_root, "ls-files", "--error-unmatch", "--", rel_path)
    if tracked is None:
        return {"COMMIT": ks.S_NOT_AVAILABLE, "GIT_STATE": "UNTRACKED"}
    commit = _git(repo_root, "log", "-1", "--format=%H", "--", rel_path)
    if commit is None or not ks.COMMIT_RE.match(commit):
        # tracked in the index but with no commit touching it yet
        return {"COMMIT": ks.S_NOT_AVAILABLE, "GIT_STATE": "TRACKED_CLEAN"}
    status = _git(repo_root, "status", "--porcelain", "--", rel_path)
    state = "TRACKED_CLEAN" if not status else "TRACKED_DIRTY"
    return {"COMMIT": commit, "GIT_STATE": state}


def file_mtime_utc(path: str) -> Optional[str]:
    try:
        import datetime as dt
        m = dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc)
    except OSError:
        return None
    return m.strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# Row construction
# --------------------------------------------------------------------------

def observe(
    path: str,
    repo_root: str,
    rel_path: Optional[str] = None,
    entity_class: str = "NOT_A_SOURCE",
    source_type: str = ks.S_NOT_APPLICABLE,
    version: str = ks.S_NOT_DECLARED,
    version_basis: Optional[str] = None,
    temporal: Optional[str] = None,
    obsolescence: Optional[str] = None,
    applicability: str = ks.S_NOT_DETERMINED,
    host_scope: str = ks.S_UNKNOWN,
    claimed_sha256: Optional[str] = None,
    notes: str = "",
    publication_date: Optional[str] = None,
) -> Dict[str, str]:
    """Build one SRC row from what is measurable about ``path``.

    ``entity_class`` defaults to ``NOT_A_SOURCE`` (B.13): registration is not
    promotion, and the 1880-file corpus is not classified in Phase 1.
    """
    rel = rel_path if rel_path is not None else os.path.relpath(path, repo_root)
    rel = rel.replace(os.sep, "/")
    if entity_class not in ks.ENTITY_CLASS:
        raise ks.SchemaError("ENTITY_CLASS %r not in %s" % (entity_class, list(ks.ENTITY_CLASS)))
    # Invariant DESIGN_FROZEN D.3: a non-source declares no role, and a role
    # implies the row is a source.  Enforced, not assumed.
    if entity_class == "NOT_A_SOURCE" and source_type != ks.S_NOT_APPLICABLE:
        raise ks.SchemaError(
            "ENTITY_CLASS=NOT_A_SOURCE requires SOURCE_TYPE=%s, got %r"
            % (ks.S_NOT_APPLICABLE, source_type)
        )
    if entity_class != "NOT_A_SOURCE" and source_type == ks.S_NOT_APPLICABLE:
        raise ks.SchemaError(
            "ENTITY_CLASS=%s requires a SOURCE_TYPE role, got %s"
            % (entity_class, ks.S_NOT_APPLICABLE)
        )
    # VERSION: never invented.  NOT_DECLARED demands a justification.
    if version == ks.S_NOT_DECLARED:
        basis = version_basis or ("NOT_A_SOURCE" if entity_class == "NOT_A_SOURCE"
                                  else ks.S_NOT_DETERMINED)
        if not basis:
            raise ks.SchemaError("VERSION=NOT_DECLARED requires a non-empty VERSION_BASIS")
    else:
        basis = version_basis or ks.S_NOT_DETERMINED

    exists = os.path.isfile(path)
    if exists:
        try:
            size: str = str(os.path.getsize(path))
        except OSError:
            size = ks.S_NOT_AVAILABLE
        try:
            real_hash = verify_sha256(path, claimed_sha256) if claimed_sha256 else sha256_file(path)
        except PermissionError:
            real_hash = ks.S_NOT_AVAILABLE
        access = ks.A_GRANTED if real_hash != ks.S_NOT_AVAILABLE else ks.A_DENIED
    else:
        size = ks.S_NOT_AVAILABLE
        real_hash = ks.S_NOT_AVAILABLE
        access = ks.A_SOURCE_ABSENT

    g = git_facts(rel, repo_root) if exists or os.path.exists(os.path.dirname(path) or ".") \
        else {"COMMIT": ks.S_NOT_AVAILABLE, "GIT_STATE": "NOT_A_GIT_REPO"}

    mtime = file_mtime_utc(path) if exists else None
    retrieval = mtime or ks.S_NOT_DETERMINED
    retrieval_basis = "mtime" if mtime else "UNREADABLE"
    # A mtime is a filesystem timestamp, not a recorded human acquisition date.
    # The basis says so explicitly instead of letting the date imply otherwise.

    tokens: List[str] = ["GIT_STATE=%s" % g["GIT_STATE"]]
    if publication_date is not None:
        if publication_date == retrieval:
            raise ks.SchemaError(
                "PUBLICATION_DATE must differ from RETRIEVAL_DATE; "
                "they are distinct concepts (B.5)"
            )
        tokens.append("PUBLICATION_DATE=%s" % publication_date)
    if version_basis:
        tokens.append("VERSION_BASIS=%s" % version_basis)
    if notes:
        tokens.append(notes)

    row = {
        "SOURCE_ID": derive_source_id(rel),
        "ENTITY_CLASS": entity_class,
        "SOURCE_TYPE": source_type,
        "VERSION": version,
        "VERSION_BASIS": basis,
        "COMMIT": g["COMMIT"],
        "RETRIEVAL_DATE": retrieval,
        "RETRIEVAL_BASIS": retrieval_basis,
        "PATH_OR_URL": rel,
        "SHA256": real_hash,
        "SIZE": size,
        # Two independent axes, both undetermined by the generator.
        "TEMPORALITY": temporal or ks.S_UNKNOWN,
        "OBSOLESCENCE": obsolescence or "UNKNOWN_VALIDITY",
        "APPLICABILITY": applicability,
        "HOST_SCOPE": host_scope,
        "ACCESS": access,
        "NOTES": ";".join(tokens),
    }
    ks.validate_row(ks.SRC, row)
    return row


def rows_for_paths(paths: Sequence[str], repo_root: str, **kw) -> List[Dict[str, str]]:
    return [observe(p, repo_root, **kw) for p in paths]


# --------------------------------------------------------------------------
# Evidence preservation (AGENTS.md:371-377)
# --------------------------------------------------------------------------

def preserve_before_replace(path: str, recovery_dir: str) -> Optional[Dict[str, str]]:
    """Copy a working file byte-for-byte to a recovery path before replacing it.

    Returns a record with the original path, the backup path and the SHA256 of
    both, or ``None`` when there is nothing to preserve because ``path`` does
    not exist.  A new file cannot destroy evidence, which is why HD-05 does not
    block Phase 1.
    """
    if not os.path.exists(path):
        return None
    os.makedirs(recovery_dir, exist_ok=True)
    real = sha256_file(path)
    stamp = os.path.getmtime(path)
    import datetime as dt
    ts = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = os.path.join(recovery_dir, "%s.%s.%s.bak" % (os.path.basename(path), real[:16], ts))
    shutil.copy2(path, backup)
    backup_hash = sha256_file(backup)
    if backup_hash != real:
        raise ks.SchemaError(
            "PRESERVATION_FAILED: backup %s hashes %s but original hashes %s"
            % (backup, backup_hash, real)
        )
    return {
        "ORIGINAL_PATH": os.path.abspath(path),
        "BACKUP_PATH": os.path.abspath(backup),
        "SHA256": real,
        "BACKUP_SHA256": backup_hash,
        "BYTE_IDENTICAL": "YES",
    }


def compare_candidate(path: str, candidate_sha256: str) -> bool:
    """True when the file on disk already has the candidate's content."""
    if not os.path.isfile(path):
        return False
    return sha256_file(path) == candidate_sha256


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

def write_registry(directory: str, rows: Iterable[Dict[str, str]],
                   recovery_dir: Optional[str] = None) -> Dict[str, str]:
    """Write SOURCE-REGISTRY.tsv, preserving any existing file first.

    Refuses to overwrite an existing registry when ``recovery_dir`` is not
    supplied: an intentional replacement requires the preservation step, and
    the replacement is a deletion of evidence otherwise (AGENTS.md:379-382).
    """
    target = ks.artifact_path(directory, ks.SRC)
    record = None
    if os.path.exists(target):
        if not recovery_dir:
            raise ks.SchemaError(
                "REFUSED: %s already exists and no recovery_dir was given; "
                "an unpreserved replacement is evidence destruction" % target
            )
        record = preserve_before_replace(target, recovery_dir)
    digest = ks.write_tsv(target, ks.SRC, rows)
    out = {"PATH": os.path.abspath(target), "SHA256": digest}
    if record:
        out["PRESERVED"] = record["BACKUP_PATH"]
        out["PRESERVED_SHA256"] = record["SHA256"]
    return out


def create_empty_registry(directory: str) -> Dict[str, str]:
    """Create the registry with the frozen header and zero data rows."""
    return write_registry(directory, [])


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="SRC registry generator (Phase 1).")
    ap.add_argument("--repo-root", required=True, help="repository root for relative paths")
    ap.add_argument("--out-dir", required=True, help="directory receiving SOURCE-REGISTRY.tsv")
    ap.add_argument("--path", action="append", default=[],
                    help="explicit file to observe; repeatable. No implicit walk.")
    ap.add_argument("--recovery-dir", default=None,
                    help="required if the target registry already exists")
    ap.add_argument("--print-header-only", action="store_true",
                    help="print the frozen header and exit without writing")
    args = ap.parse_args(argv)

    if args.print_header_only:
        print("\t".join(ks.COLUMNS[ks.SRC]))
        return 0

    repo_root = os.path.abspath(args.repo_root)
    if not args.path:
        # Phase 1: refuse to enumerate the corpus. Enumeration is Phase 2.
        create_empty_registry(args.out_dir)
        print("created empty registry: %s" % ks.artifact_path(args.out_dir, ks.SRC))
        return 0
    rows = [observe(os.path.join(repo_root, p), repo_root) for p in args.path]
    info = write_registry(args.out_dir, rows, args.recovery_dir)
    for k, v in info.items():
        print("%s=%s" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
