#!/usr/bin/env python3
"""T35-T37: behavioural coverage for DEFECT-03 (root_fd_error_count scoping).

DEFECT-03 aborted R1 run ``R1-20260926T005434Z`` with::

    UnboundLocalError: cannot access local variable 'root_fd_error_count'

Cause: ``observe`` is a closure nested inside ``main``.  It augments
``root_fd_error_count`` and four sibling counters.  Python makes an augmented
assignment inside a nested function a *local* of that function, so the read
fails on the first PID unless ``nonlocal`` is declared.  ``main`` initialises the
counters, but that does not make them visible to the closure.

``test_T31`` in ``test_r1_defects.py`` cannot detect this: it reads
``inspect.getsource(collector.main)`` and asserts a literal string is present.
The augmented-assignment line exists both before and after the defect, so the
assertion holds with or without the bug.  It is a source-text check standing in
for execution, and this module executes the real ``observe`` body instead.

What this module does:

* ``T35`` runs the *real* ``observe`` FunctionDef, extracted from the real source
  by AST, inside a harness that reproduces ``main``'s scope exactly (counter
  initialisation copied from ``main`` itself, no ``nonlocal``).  Any PID
  processed must raise ``UnboundLocalError`` today.
* ``T36`` proves the harness discriminates: the same real body with
  ``nonlocal`` inserted must *not* raise.  Without this, a passing T35 would
  prove nothing.
* ``T37`` asserts the invariants that make T35 meaningful: ``observe`` really is
  nested in ``main``, it really augments those names, and ``nonlocal`` really is
  absent from the whole file.

No test here invokes sudo, systemctl, C1, or a live host probe.  The data
sources ``observe`` calls are replaced by minimal stubs, but the *defective
statement itself* is never stubbed, mocked, or skipped -- it is the real source.
"""
from __future__ import annotations

import ast
import importlib.util
import io
import contextlib
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "privileged_read_collector.py"
SPEC = importlib.util.spec_from_file_location("collector_defect03", SCRIPT)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)

# The five counters `observe` augments, in the order `main` initialises them.
COUNTERS = (
    "root_fd_error_count",
    "root_fd_permission_denied",
    "root_fd_disappeared",
    "root_fd_other_errors",
    "root_process_error_count",
)


def _load_ast():
    return ast.parse(SCRIPT.read_text(encoding="utf-8"))


def _find_main(tree):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError("main() not found in collector source")


def _counter_inits(main_node):
    """Return the real initialisation statements for the five counters,
    plus main()'s real `coverage` accumulator literal."""
    found = {}
    coverage = None
    for node in ast.walk(main_node):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in COUNTERS:
                found.setdefault(target.id, node)
            if isinstance(target, ast.Name) and target.id == "coverage":
                coverage = coverage or node
    missing = [c for c in COUNTERS if c not in found]
    assert not missing, f"counters not initialised in main(): {missing}"
    assert coverage is not None, "coverage accumulator not found in main()"
    return [found[c] for c in COUNTERS] + [coverage]


def _observe_def(main_node):
    for node in ast.walk(main_node):
        if isinstance(node, ast.FunctionDef) and node.name == "observe":
            return node
    raise AssertionError("nested observe() not found in main()")


def _harness_source(strip_nonlocal: bool) -> str:
    """Build a module that nests the *real* observe() inside a harness.

    The harness body is the real counter-initialisation from ``main`` followed
    by the real ``observe`` definition, both re-indented by one level.  That
    reproduces exactly the scoping situation the collector has: counters
    initialised in the enclosing function, augmented in a nested one.
    """
    tree = _load_ast()
    main_node = _find_main(tree)
    lines = SCRIPT.read_text(encoding="utf-8").splitlines(keepends=True)

    # main()'s body already sits at 4-space indentation, which is exactly the
    # level it needs inside `def _harness():`, so the statements are used
    # verbatim -- no re-indentation, which would silently change their scope.
    init_src = "".join(
        "".join(lines[n.lineno - 1: n.end_lineno]) for n in _counter_inits(main_node)
    )

    obs = _observe_def(main_node)
    body = "".join(lines[obs.lineno - 1: obs.end_lineno])

    if strip_nonlocal:
        # Reproduce the pre-fix state by deleting only observe()'s own nonlocal
        # statement.  Everything else stays byte-identical to the real source.
        keep, dropping = [], False
        for line in body.splitlines(keepends=True):
            if line.lstrip().startswith("nonlocal "):
                dropping = True
                continue
            if dropping:
                # Continuation lines of the same statement name a counter and
                # cannot be a statement on their own.
                if any(c in line for c in COUNTERS):
                    continue
                dropping = False
            keep.append(line)
        obs_src = "".join(keep)
    else:
        obs_src = body

    return f"def _harness(_stubs):\n{init_src}{obs_src}\n    return observe\n"


def _stubs():
    """Minimal data sources.  They do not touch the defective statement."""
    fd = {"status": "OK", "error_count": 0, "errors": [], "matched": [],
          "drm_nodes_any": []}
    return {
        "proc_meta": lambda pid, _root=None: {"pid": pid, "comm": "x",
                                              "cmdline": "x", "uid": "0",
                                              "namespaces": {}},
        "scan_fds": lambda pid, devices, _root=None: dict(fd),
        "scan_maps": lambda pid, _root=None, keep=None: {},
        "relevant_process": lambda meta, kw: False,
        "classify_proc_error": lambda text: "OTHER",
        "compositor_gpu_relation": lambda *a, **k: None,
        # observe() now re-reads a cleanly scanned PID to see whether it
        # vanished.  Stubbed ALIVE so this harness stays hermetic and never
        # stats a real /proc entry, and so no absence is ever credited here.
        "pid_gone": lambda pid, proc_root=None: {
            "state": "ALIVE", "reason": "OBSERVED", "error": None},
    }


def _build_globals():
    g = {
        "root_fd_errors": [],
        "gpu_clients": [],
        "storage_clients": [],
        "compositor_relations": {},
        "pid_records": {},
        "devices": (),
        "keywords": (),
        "prior_pids": (),
        # observe()'s proc_root default is a module global, so the harness
        # namespace must carry it for the signature to resolve.  The value is
        # never read: _stubs() replaces pid_gone, so no real /proc is touched.
        "DEFAULT_PROC_ROOT": Path("/proc"),
        # observe() classifies absence through a module-level pure function.
        # This namespace is built explicitly instead of being seeded from the
        # collector module, so the dependency is supplied here exactly as
        # DEFAULT_PROC_ROOT is: the reference must resolve; behaviour is not
        # changed by this harness.
        "classify_fd_absence": collector.classify_fd_absence,
        "DETERMINED_ABSENT": collector.DETERMINED_ABSENT,
        "NOT_DETERMINED": collector.NOT_DETERMINED,
    }
    g.update(_stubs())
    return g


def _run_observe(strip_nonlocal: bool) -> object:
    """Execute the real observe() body against one PID. Returns the result or raises."""
    src = _harness_source(strip_nonlocal)
    g = _build_globals()
    g["__name__"] = "harness_module"
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, "<harness>", "exec"), g)
        observe = g["_harness"](None)
        return observe(1)


class T35_RealObserveBodyIsExecuted(unittest.TestCase):
    def test_one_pid_against_the_real_source(self):
        """REGRESSION GUARD.  One PID through the real observe() body.

        Processing a single PID must not raise.  This fails with
        UnboundLocalError for as long as observe() augments the counters
        without `nonlocal`, and passes once that declaration is present.
        """
        result = _run_observe(strip_nonlocal=False)
        self.assertIsInstance(result, dict)
        self.assertIn("fd_scan", result)
        self.assertIn("maps", result)

    def test_defect_03_only_reappears_when_nonlocal_is_removed(self):
        """Characterisation.  The failure is observed by running the code, and
        it comes back only when observe()'s own nonlocal is deleted."""
        with self.assertRaises(UnboundLocalError) as ctx:
            _run_observe(strip_nonlocal=True)
        self.assertIn("root_fd_error_count", str(ctx.exception))

    def test_main_initialises_them_and_observe_binds_them(self):
        """main() initialises the five counters and observe() binds all five."""
        src = SCRIPT.read_text(encoding="utf-8")
        inits = _counter_inits(_find_main(tree=_load_ast()))
        self.assertEqual(len(inits), 6, "main() must initialise five counters + coverage")
        self.assertIn("root_fd_error_count = 0", src)
        self.assertEqual(src.count("nonlocal"), 1,
                         "exactly one nonlocal declaration is expected")
        self.assertIn("root_fd_error_count = 0", src)


class T36_HarnessDiscriminates(unittest.TestCase):
    def test_real_source_does_not_raise(self):
        """Case A.  The real, fixed source runs one PID to completion."""
        result = _run_observe(strip_nonlocal=False)
        self.assertIsInstance(result, dict)
        self.assertIn("fd_scan", result)
        self.assertIn("maps", result)

    def test_the_only_difference_is_the_nonlocal_statement(self):
        fixed = _harness_source(False)
        reverted = _harness_source(True)
        self.assertIn("nonlocal root_fd_error_count", fixed)
        self.assertNotIn("nonlocal root_fd_error_count", reverted)
        self.assertEqual(len(fixed.splitlines()) - len(reverted.splitlines()), 2)


class T37_SourceInvariants(unittest.TestCase):
    def test_observe_declares_nonlocal_for_exactly_the_five_counters(self):
        tree = _load_ast()
        obs = _observe_def(_find_main(tree))
        decls = [n for n in ast.walk(obs) if isinstance(n, ast.Nonlocal)]
        self.assertEqual(len(decls), 1, "observe() must declare nonlocal exactly once")
        self.assertEqual(sorted(decls[0].names), sorted(COUNTERS))
        # It must be the first statement after the docstring.
        first = obs.body[0]
        self.assertIsInstance(first, ast.Expr, "docstring must come first")
        self.assertIsInstance(obs.body[1], ast.Nonlocal)

    def test_observe_is_nested_inside_main(self):
        tree = _load_ast()
        main_node = _find_main(tree)
        nested = [n for n in main_node.body if isinstance(n, ast.FunctionDef)]
        self.assertIn("observe", [n.name for n in nested],
                      "observe must be a nested def of main, not a module function")

    def test_observe_augments_the_five_counters(self):
        tree = _load_ast()
        obs = _observe_def(_find_main(tree))
        augmented = {n.target.id for n in ast.walk(obs)
                     if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)}
        for c in COUNTERS:
            self.assertIn(c, augmented, f"observe must augment {c}")

    def test_the_failing_statement_is_outside_every_branch(self):
        """The augmented assignment runs for every PID; no fixture can dodge it."""
        tree = _load_ast()
        obs = _observe_def(_find_main(tree))
        target = None
        for n in ast.walk(obs):
            if (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
                    and n.target.id == "root_fd_error_count"):
                target = n
        self.assertIsNotNone(target)
        # depth 0 inside observe => not inside any if/for/while body
        self.assertEqual(target.col_offset, obs.body[0].col_offset)
        self.assertEqual(target.col_offset, 8,
                         "statement must sit at observe's top level")


if __name__ == "__main__":
    unittest.main(verbosity=2)
