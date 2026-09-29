#!/usr/bin/env python3
"""Phase 1 infrastructure tests — properties, not smoke.

Covers the eighteen properties required for Phase 1 (prompt F):
header exactness, column count, column order, real SHA256 generation,
rejection of an invented SHA256, absence of invented VERSION/COMMIT,
RETRIEVAL_DATE vs publication date, TEMPORALITY vs OBSOLESCENCE, valid
ENTITY_CLASS, REFERENT_DRIFT acceptance, duplicate/missing/extra column
detection, and behaviour on nonexistent, modified, untracked and git-tracked
files, plus evidence preservation on replacement.

Every fixture is created in a temporary directory.  No test reads, writes or
enumerates the project corpus: enumeration and migration are Phase 2.

Column-count note: the named column lists of DESIGN_FROZEN B.5-B.8 give
SRC=17, KB=36, NEG=14, CTR=14.  DESIGN_FROZEN D.3 states 20/33/15/14.  The
named lists are authoritative and the D.3 counts are a DOCUMENTARY error
(AGENTS.md:212 requires the correction to be shown).  ``test_frozen_column_
counts_are_the_named_lists`` pins the authoritative numbers so the
discrepancy cannot silently return.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import knowledge_schema as ks  # noqa: E402
import src_registry as sr  # noqa: E402


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, check=True).stdout.strip()


class FrozenSchemaTest(unittest.TestCase):
    """Properties 1, 2, 3, 11, 12, 13 — header, count, order, column defects."""

    def test_frozen_column_counts_are_the_named_lists(self):
        self.assertEqual(len(ks.COLUMNS[ks.SRC]), 17)
        self.assertEqual(len(ks.COLUMNS[ks.KB]), 36)
        self.assertEqual(len(ks.COLUMNS[ks.NEG]), 14)
        self.assertEqual(len(ks.COLUMNS[ks.CTR]), 14)

    def test_no_artifact_has_a_duplicated_column(self):
        for art, cols in ks.COLUMNS.items():
            self.assertEqual(len(set(cols)), len(cols), "%s has duplicates" % art)

    def test_src_header_is_exactly_the_seventeen_frozen_columns(self):
        self.assertEqual(ks.COLUMNS[ks.SRC], (
            "SOURCE_ID", "ENTITY_CLASS", "SOURCE_TYPE", "VERSION", "VERSION_BASIS",
            "COMMIT", "RETRIEVAL_DATE", "RETRIEVAL_BASIS", "PATH_OR_URL", "SHA256",
            "SIZE", "TEMPORALITY", "OBSOLESCENCE", "APPLICABILITY", "HOST_SCOPE",
            "ACCESS", "NOTES"))

    def test_header_round_trips_through_disk(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, ks.FILENAMES[ks.SRC])
            ks.write_tsv(p, ks.SRC, [])
            with open(p, encoding="utf-8") as fh:
                header = fh.readline().rstrip("\n").split("\t")
            ks.validate_header(header, ks.COLUMNS[ks.SRC])
            self.assertEqual(header, list(ks.COLUMNS[ks.SRC]))

    def test_missing_column_is_detected(self):
        cols = list(ks.COLUMNS[ks.SRC])
        cols.remove("HOST_SCOPE")
        rep = ks.header_report(cols, ks.COLUMNS[ks.SRC])
        self.assertEqual(rep["MISSING"], ["HOST_SCOPE"])
        with self.assertRaises(ks.HeaderError):
            ks.validate_header(cols, ks.COLUMNS[ks.SRC])

    def test_extra_column_is_detected(self):
        cols = list(ks.COLUMNS[ks.SRC]) + ["GIT_STATE"]
        rep = ks.header_report(cols, ks.COLUMNS[ks.SRC])
        self.assertEqual(rep["EXTRA"], ["GIT_STATE"])
        with self.assertRaises(ks.HeaderError):
            ks.validate_header(cols, ks.COLUMNS[ks.SRC])

    def test_duplicated_column_is_detected(self):
        cols = list(ks.COLUMNS[ks.SRC])
        cols[5] = "VERSION"          # COMMIT -> VERSION, already present
        rep = ks.header_report(cols, ks.COLUMNS[ks.SRC])
        self.assertTrue(rep["DUPLICATE"], rep)
        self.assertEqual(rep["MISSING"], ["COMMIT"])

    def test_correct_set_in_wrong_order_is_detected(self):
        cols = list(ks.COLUMNS[ks.SRC])
        cols[0], cols[1] = cols[1], cols[0]
        rep = ks.header_report(cols, ks.COLUMNS[ks.SRC])
        self.assertEqual(rep["MISSING"], [])
        self.assertEqual(rep["EXTRA"], [])
        self.assertEqual(rep["DUPLICATE"], [])
        self.assertTrue(rep["ORDER"], rep)
        with self.assertRaises(ks.HeaderError):
            ks.validate_header(cols, ks.COLUMNS[ks.SRC])

    def test_writer_refuses_a_row_with_an_unknown_column(self):
        with tempfile.TemporaryDirectory() as d:
            row = self._valid_row()
            row["GIT_STATE"] = "UNTRACKED"
            with self.assertRaises(ks.SchemaError):
                ks.validate_row(ks.SRC, row)

    def test_writer_refuses_an_empty_value(self):
        with tempfile.TemporaryDirectory() as d:
            row = self._valid_row()
            row["NOTES"] = ""
            with self.assertRaises(ks.SchemaError):
                ks.validate_row(ks.SRC, row)

    def test_writer_refuses_a_value_containing_a_tab(self):
        row = self._valid_row()
        row["NOTES"] = "GIT_STATE=UNTRACKED\textra"
        with self.assertRaises(ks.SchemaError):
            ks.validate_row(ks.SRC, row)

    def test_domain_violation_is_rejected(self):
        row = self._valid_row()
        row["ACCESS"] = "MAYBE"
        with self.assertRaises(ks.SchemaError):
            ks.validate_row(ks.SRC, row)

    @staticmethod
    def _valid_row():
        return {
            "SOURCE_ID": "SRC-0123456789ab", "ENTITY_CLASS": "NOT_A_SOURCE",
            "SOURCE_TYPE": ks.S_NOT_APPLICABLE, "VERSION": ks.S_NOT_DECLARED,
            "VERSION_BASIS": "NOT_A_SOURCE", "COMMIT": ks.S_NOT_AVAILABLE,
            "RETRIEVAL_DATE": "2026-09-26T00:00:00Z", "RETRIEVAL_BASIS": "mtime",
            "PATH_OR_URL": "a/b.txt", "SHA256": "0" * 64, "SIZE": "10",
            "TEMPORALITY": ks.S_UNKNOWN, "OBSOLESCENCE": "UNKNOWN_VALIDITY",
            "APPLICABILITY": ks.S_NOT_DETERMINED, "HOST_SCOPE": ks.S_UNKNOWN,
            "ACCESS": "GRANTED", "NOTES": "GIT_STATE=UNTRACKED",
        }


class SrcObservationTest(unittest.TestCase):
    """Properties 4, 5, 6, 7, 8, 9, 10, 14 — observation semantics."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(self.repo, "sub"))
        self.f = os.path.join(self.repo, "sub", "a.txt")
        with open(self.f, "wb") as fh:
            fh.write(b"contenido-de-prueba\n")
        self.addCleanup(self.tmp.cleanup)

    def test_sha256_is_computed_from_the_real_object(self):
        row = sr.observe(self.f, self.repo)
        expected = hashlib.sha256(b"contenido-de-prueba\n").hexdigest()
        self.assertEqual(row["SHA256"], expected)
        self.assertEqual(row["SIZE"], str(len(b"contenido-de-prueba\n")))

    def test_invented_sha256_is_rejected(self):
        with self.assertRaises(ks.SchemaError) as ctx:
            sr.observe(self.f, self.repo, claimed_sha256="0" * 64)
        self.assertIn("SHA256_REJECTED", str(ctx.exception))

    def test_correct_claimed_sha256_is_accepted_and_verified(self):
        real = sr.sha256_file(self.f)
        row = sr.observe(self.f, self.repo, claimed_sha256=real)
        self.assertEqual(row["SHA256"], real)

    def test_version_is_never_invented(self):
        row = sr.observe(self.f, self.repo)
        self.assertEqual(row["VERSION"], ks.S_NOT_DECLARED)
        self.assertTrue(row["VERSION_BASIS"])
        self.assertNotRegex(row["VERSION"], r"^\d")

    def test_commit_is_never_invented_outside_git(self):
        row = sr.observe(self.f, self.repo)
        self.assertEqual(row["COMMIT"], ks.S_NOT_AVAILABLE)
        self.assertIn("GIT_STATE=NOT_A_GIT_REPO", row["NOTES"])

    def test_retrieval_date_is_not_a_publication_date(self):
        row = sr.observe(self.f, self.repo)
        self.assertEqual(row["RETRIEVAL_BASIS"], "mtime")
        self.assertNotIn("PUBLICATION_DATE=", row["NOTES"])
        # A publication date equal to the retrieval instant is refused: the two
        # are distinct concepts and conflating them is the error being tested.
        with self.assertRaises(ks.SchemaError):
            sr.observe(self.f, self.repo, publication_date=row["RETRIEVAL_DATE"])

    def test_publication_date_is_recorded_in_notes_not_in_retrieval_date(self):
        row = sr.observe(self.f, self.repo, publication_date="2013-04-30")
        self.assertEqual(row["RETRIEVAL_DATE"], sr.file_mtime_utc(self.f))
        self.assertIn("PUBLICATION_DATE=2013-04-30", row["NOTES"])
        self.assertNotIn("PUBLICATION_DATE", ks.COLUMNS[ks.SRC])

    def test_temporality_and_obsolescence_are_independent(self):
        row = sr.observe(self.f, self.repo)
        self.assertEqual(row["TEMPORALITY"], ks.S_UNKNOWN)
        self.assertEqual(row["OBSOLESCENCE"], "UNKNOWN_VALIDITY")
        a = sr.observe(self.f, self.repo, temporal="HISTORICAL")
        b = sr.observe(self.f, self.repo, obsolescence="SUPERSEDED")
        self.assertEqual(a["OBSOLESCENCE"], "UNKNOWN_VALIDITY")
        self.assertEqual(b["TEMPORALITY"], ks.S_UNKNOWN)

    def test_entity_class_domain_is_enforced(self):
        with self.assertRaises(ks.SchemaError):
            sr.observe(self.f, self.repo, entity_class="PRIMARY")

    def test_not_a_source_requires_no_role_and_a_role_forbids_not_a_source(self):
        with self.assertRaises(ks.SchemaError):
            sr.observe(self.f, self.repo, entity_class="NOT_A_SOURCE",
                       source_type="PROJECT_ARTIFACT")
        with self.assertRaises(ks.SchemaError):
            sr.observe(self.f, self.repo, entity_class="ARTIFACT",
                       source_type=ks.S_NOT_APPLICABLE)
        ok = sr.observe(self.f, self.repo, entity_class="ARTIFACT",
                        source_type="PROJECT_ARTIFACT", version_basis="DECLARED_NONE")
        self.assertEqual(ok["SOURCE_TYPE"], "PROJECT_ARTIFACT")

    def test_referent_drift_is_an_accepted_obsolescence_value(self):
        self.assertIn("REFERENT_DRIFT", ks.OBSOLESCENCE)
        row = sr.observe(self.f, self.repo, obsolescence="REFERENT_DRIFT")
        self.assertEqual(row["OBSOLESCENCE"], "REFERENT_DRIFT")
        with self.assertRaises(ks.SchemaError):
            sr.observe(self.f, self.repo, obsolescence="DRIFTED")

    def test_nonexistent_file_is_reported_not_invented(self):
        missing = os.path.join(self.repo, "sub", "no-existe.txt")
        row = sr.observe(missing, self.repo)
        self.assertEqual(row["ACCESS"], "SOURCE_ABSENT")
        self.assertEqual(row["SHA256"], ks.S_NOT_AVAILABLE)
        self.assertEqual(row["SIZE"], ks.S_NOT_AVAILABLE)
        self.assertNotEqual(row["SHA256"], "0" * 64)

    def test_unreadable_file_yields_denied_not_absent(self):
        if os.geteuid() == 0:
            self.skipTest("root bypasses permission bits; DENIED cannot be produced")
        locked = os.path.join(self.repo, "sub", "locked.txt")
        with open(locked, "wb") as fh:
            fh.write(b"x")
        os.chmod(locked, 0o000)
        self.addCleanup(os.chmod, locked, 0o644)
        row = sr.observe(locked, self.repo)
        self.assertEqual(row["ACCESS"], "DENIED")
        self.assertEqual(row["SHA256"], ks.S_NOT_AVAILABLE)

    def test_source_id_is_derived_and_stable(self):
        a = sr.observe(self.f, self.repo)
        b = sr.observe(self.f, self.repo)
        self.assertEqual(a["SOURCE_ID"], b["SOURCE_ID"])
        self.assertRegex(a["SOURCE_ID"], ks.SOURCE_ID_RE)


class GitRelationTest(unittest.TestCase):
    """Properties 15, 16, 17 — untracked, modified and git-tracked files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@example.invalid")
        _git(self.repo, "config", "user.name", "test")
        _git(self.repo, "config", "commit.gpgsign", "false")
        self.tracked = os.path.join(self.repo, "tracked.txt")
        with open(self.tracked, "wb") as fh:
            fh.write(b"v1\n")
        _git(self.repo, "add", "tracked.txt")
        _git(self.repo, "commit", "-q", "-m", "add tracked")
        self.addCleanup(self.tmp.cleanup)

    def test_git_tracked_file_carries_its_own_commit(self):
        row = sr.observe(self.tracked, self.repo)
        head = _git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(row["COMMIT"], head)
        self.assertRegex(row["COMMIT"], ks.COMMIT_RE)
        self.assertIn("GIT_STATE=TRACKED_CLEAN", row["NOTES"])

    def test_modified_file_is_dirty_but_hash_tracks_the_working_tree(self):
        with open(self.tracked, "wb") as fh:
            fh.write(b"v2-modificado\n")
        row = sr.observe(self.tracked, self.repo)
        self.assertIn("GIT_STATE=TRACKED_DIRTY", row["NOTES"])
        # git status is not the identity of the content: the working-tree
        # bytes decide the hash, and the file is still read.
        self.assertEqual(row["SHA256"], hashlib.sha256(b"v2-modificado\n").hexdigest())
        self.assertNotEqual(row["SHA256"], hashlib.sha256(b"v1\n").hexdigest())
        self.assertEqual(row["ACCESS"], "GRANTED")
        # COMMIT stays the last commit that touched the path, unmodified.
        self.assertEqual(row["COMMIT"], _git(self.repo, "rev-parse", "HEAD"))

    def test_untracked_file_has_no_commit(self):
        new = os.path.join(self.repo, "nuevo.txt")
        with open(new, "wb") as fh:
            fh.write(b"nuevo\n")
        row = sr.observe(new, self.repo)
        self.assertEqual(row["COMMIT"], ks.S_NOT_AVAILABLE)
        self.assertIn("GIT_STATE=UNTRACKED", row["NOTES"])
        self.assertRegex(row["SHA256"], ks.SHA256_RE)

    def test_git_state_token_is_machine_readable(self):
        row = sr.observe(self.tracked, self.repo)
        m = ks.GIT_STATE_TOKEN_RE.search(row["NOTES"])
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "TRACKED_CLEAN")

    def test_commit_is_per_file_not_repository_head(self):
        other = os.path.join(self.repo, "otro.txt")
        with open(other, "wb") as fh:
            fh.write(b"otro\n")
        _git(self.repo, "add", "otro.txt")
        _git(self.repo, "commit", "-q", "-m", "second")
        row = sr.observe(self.tracked, self.repo)
        self.assertNotEqual(row["COMMIT"], _git(self.repo, "rev-parse", "HEAD"))


class EvidencePreservationTest(unittest.TestCase):
    """Property 18 — preservation before an intentional replacement."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self.tmp.name, "out")
        self.rec = os.path.join(self.tmp.name, "recovery")
        os.makedirs(self.dir)
        self.addCleanup(self.tmp.cleanup)

    def test_new_file_needs_no_preservation(self):
        rec = sr.preserve_before_replace(
            os.path.join(self.dir, "inexistente.tsv"), self.rec)
        self.assertIsNone(rec)

    def test_preservation_is_byte_identical_and_records_sha256(self):
        target = os.path.join(self.dir, ks.FILENAMES[ks.SRC])
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("contenido original\n")
        original = sr.sha256_file(target)
        rec = sr.preserve_before_replace(target, self.rec)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["SHA256"], original)
        self.assertEqual(rec["BACKUP_SHA256"], original)
        self.assertEqual(rec["BYTE_IDENTICAL"], "YES")
        self.assertTrue(os.path.isfile(rec["BACKUP_PATH"]))
        with open(rec["BACKUP_PATH"], "rb") as fh:
            self.assertEqual(fh.read(), b"contenido original\n")

    def test_replacement_without_recovery_dir_is_refused(self):
        target = os.path.join(self.dir, ks.FILENAMES[ks.SRC])
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("contenido original\n")
        before = sr.sha256_file(target)
        with self.assertRaises(ks.SchemaError) as ctx:
            sr.write_registry(self.dir, [])
        self.assertIn("REFUSED", str(ctx.exception))
        # refusal must leave the evidence untouched
        self.assertEqual(sr.sha256_file(target), before)

    def test_replacement_with_recovery_dir_preserves_then_applies(self):
        target = os.path.join(self.dir, ks.FILENAMES[ks.SRC])
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("contenido original\n")
        before = sr.sha256_file(target)
        info = sr.write_registry(self.dir, [], self.rec)
        self.assertIn("PRESERVED", info)
        self.assertEqual(info["PRESERVED_SHA256"], before)
        backup = info["PRESERVED"]
        self.assertTrue(os.path.isfile(backup))
        with open(backup, "rb") as fh:
            self.assertEqual(fh.read(), b"contenido original\n")
        # the candidate was applied and is the frozen header
        with open(target, encoding="utf-8") as fh:
            self.assertEqual(fh.readline().rstrip("\n").split("\t"),
                             list(ks.COLUMNS[ks.SRC]))
        self.assertNotEqual(sr.sha256_file(target), before)

    def test_candidate_comparison_detects_identical_content(self):
        target = os.path.join(self.dir, "x.txt")
        with open(target, "wb") as fh:
            fh.write(b"igual\n")
        digest = sr.sha256_file(target)
        self.assertTrue(sr.compare_candidate(target, digest))
        self.assertFalse(sr.compare_candidate(target, "0" * 64))
        self.assertFalse(sr.compare_candidate(os.path.join(self.dir, "nope"), digest))


class FourArtifactsTest(unittest.TestCase):
    """The four canonical artifacts exist with the frozen header and zero rows."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self.tmp.name, "out")
        os.makedirs(self.dir)
        self.addCleanup(self.tmp.cleanup)

    def test_all_four_headers_are_exact_and_data_free(self):
        for art in (ks.SRC, ks.KB, ks.NEG, ks.CTR):
            path = ks.artifact_path(self.dir, art)
            ks.write_tsv(path, art, [])
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            self.assertTrue(raw.endswith("\n"))
            lines = raw.rstrip("\n").split("\n")
            self.assertEqual(len(lines), 1, "%s must have zero data rows" % art)
            self.assertEqual(lines[0].split("\t"), list(ks.COLUMNS[art]))
            self.assertEqual(ks.read_tsv(path, art), [])

    def test_taxonomy_and_state_vocabularies_are_disjoint(self):
        self.assertEqual(set(ks.KB_CLASS) & set(ks.EPISTEMIC_STATE), set())
        for st in ks.EPISTEMIC_STATE:
            self.assertNotIn(st, ks.KB_CLASS)

    def test_filenames_are_the_frozen_four(self):
        self.assertEqual(ks.FILENAMES, {
            "SRC": "SOURCE-REGISTRY.tsv", "KB": "KNOWLEDGE-BASE.tsv",
            "NEG": "NEGATIVE-KNOWLEDGE.tsv", "CTR": "CONTRADICTIONS.tsv"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
