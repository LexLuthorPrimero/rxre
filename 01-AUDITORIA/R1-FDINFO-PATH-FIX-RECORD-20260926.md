# R1-FDINFO-PATH-FIX-RECORD-20260926

```text
RECORD_ID=R1-FDINFO-PATH-FIX-RECORD-20260926
CREATED_UTC=2026-09-26T04:02Z
SCOPE=scan_fds() fdinfo route + failure visibility, as authorized
WORK_CLASS=STATIC_IMPLEMENTATION
DEFECT_SCAN_FDS_FDINFO_PATH=CLOSED
R1_EXECUTED=NO
SUDO_USED=NO
```

Historical evidence is untouched. This record is new; it modifies no prior
artifact.

## 1. ROOT_CAUSE

`scan_fds()` built the fdinfo path from `fd_path.parent`, where `fd_path` is
`/proc/<pid>/fd/<n>`. `fd_path.parent` is therefore `/proc/<pid>/fd`, and the
path produced was:

```text
/proc/<pid>/fd/fdinfo/<n>      <- never exists in procfs
```

procfs places `fdinfo` as a **sibling** of `fd`, not a child:

```text
/proc/<pid>/fd/<n>             symlink to the opened file
/proc/<pid>/fdinfo/<n>         the FD's information
```

The failure was invisible twice over:

1. the path did not exist, and
2. `read_text()` is `return result.get("value", "") if result.get("status") == "OK" else ""`,
   so it discarded the error and returned `""`, which the caller consumed
   without inspecting. `error_count` was never incremented.

Net effect on R1-4: all four GPU clients were recorded with `fdinfo: ''`, while
`readlink` on the same FDs had succeeded. `fd_error_count` counted one
`readlink` failure and zero fdinfo failures.

The collector contradicted itself in the same file: `sources` declared
`"/proc/<pid>/fdinfo"` (L1517) and `CAPABILITY_MATRIX` declared
`"/proc/*/fdinfo contents (drm-client-id, drm-pdev, pasid)"` with
`"implemented": true` (L1578-1581), while the code built another path.

`PROVENANCE_OF_THE_DEFECT=UNKNOWN`. The collector has **0 commits**, is absent
from `HEAD`, and is present only in the index. `R1-PREFLIGHT-drm-identity-and-command-audit.md:255`
cites `scan_fds()` at L196; it is now at L1006. The audited version cannot be
recovered, so the defect cannot be dated or attributed.

## 2. FIX

One branch of `scan_fds()`, plus making the failure countable.

```diff
         if target in devices:
-            result["matched"].append(
-                {
-                    "fd": int(name),
-                    "target": target,
-                    "fdinfo": read_text(fd_path.parent / "fdinfo" / name, 16384),
-                }
-            )
+            fdinfo_path = fd_dir.parent / "fdinfo" / name
+            fdinfo = read_bytes(fdinfo_path, 16384)
+            if fdinfo.get("status") != "OK":
+                message = fdinfo.get("error", "FDINFO_READ_FAILED")
+                result["error_count"] += 1
+                if len(result["errors"]) < 12:
+                    result["errors"].append(
+                        {
+                            "fd": int(name),
+                            "stage": "fdinfo",
+                            "path": str(fdinfo_path),
+                            "error": message,
+                            "reason": classify_proc_error(message),
+                        }
+                    )
+            result["matched"].append(
+                {
+                    "fd": int(name),
+                    "target": target,
+                    "fdinfo": fdinfo.get("value", "") if fdinfo.get("status") == "OK" else "",
+                }
+            )
```

`read_text()` is untouched and still used elsewhere. The `matched` record keeps
its three fields and `fdinfo` stays a string, so the output shape is unchanged.

### Consequence that must not be hidden

`scan_fds()["error_count"]` feeds `root_fd_error_count` (L2073 in the pre-fix
numbering) → `coverage["fd_error_count"]` → and
`"drm_fds_enumerated": "PASS" if gpu_proven and coverage["fd_error_count"] == 0 else "FAIL"`.

Counting fdinfo failures therefore makes `drm_fds_enumerated` sensitive to them
for the first time. That is the intended and correct consequence: a DRM FD whose
fdinfo cannot be read is an incompletely enumerated DRM FD. **The scoring
expression itself was not modified.**

On a real host `/proc/<pid>/fdinfo/<n>` exists for every readable FD, so this
should introduce no new errors in practice. That is unverified without a run and
is stated as expectation, not fact.

## 3. VERIFICATION

### Behavioral test

`01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/test_fdinfo_path_behavioral.py`, 17
tests, 6 classes. It builds a synthetic `/proc` with the **real** layout — a
symlink at `<root>/<pid>/fd/<n>` and the file at `<root>/<pid>/fdinfo/<n>` — and
asserts on content that must arrive, never on the presence of a field name.

| Class | What it pins |
|---|---|
| `FdinfoContentArrivesTests` | the full fdinfo text reaches the record; `drm-driver`, `drm-client-id`, `drm-pdev`, `pasid` survive; a clean read yields no errors; several clients on two nodes all read |
| `RouteIsTheRealOneTests` | the tree never contains `fd/fdinfo`; the path recorded on failure is the sibling location and does not contain `/fd/fdinfo/` |
| `ReadFailureIsVisibleTests` | a missing fdinfo increments `error_count`, is classified, and is tagged `stage: fdinfo`; the client is still recorded; failures accumulate; an unreadable fdinfo yields `PERMISSION_DENIED`; the sample stays capped at 12 |
| `UnaffectedBranchesTests` | a device outside the set is still only listed; an unrelated file produces no record; a `readlink` failure still classifies at the `fd` stage and carries no `stage` key |
| `ShapeContractTests` | the result keeps its documented keys; the matched record keeps exactly `fd`, `target`, `fdinfo`; the 16 KiB cap still applies |

### Discrimination

The pre-fix collector was reconstructed by reversing the patch and hashing the
result: it reproduced `HASH_BEFORE` **byte for byte**.

```text
pre-fix  (HASH_BEFORE fb515882…)  Ran 17  FAILED (failures=9)
post-fix (HASH_AFTER  fe0b740c…)  Ran 17  OK
```

The 8 that pass in both are the invariant guards by design: they assert the
`drm_nodes_any` branch, the `readlink` classification, and the shape contract,
none of which this fix touches.

### Suites

```text
directly affected:
  test_medium_fixes.py                   Ran 27  OK
  test_collector_failure_modes.py        Ran 35  OK
  test_med_review_classifications.py     Ran 26  OK
  test_privileged_read_collector.py      Ran 43  OK
  test_r1_defects.py                     Ran 23  OK

complete:  Ran 245 tests   OK   exit 0
```

`245 = 228` pre-existing `+ 17` new. No regressions.

## 4. HASHES

```text
HASH_BEFORE=fb515882707e2bfd36131772a895230d432d4e83f65dedb8e8921eb7317f4d78
HASH_AFTER =fe0b740c19c1557e779005d43e606348a62e28365cfcc1ad05f91f76aa40db2e
```

Both verified with `sha256sum` and `hashlib`; they agree.

```text
FILE=01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py
SHA256=fe0b740c19c1557e779005d43e606348a62e28365cfcc1ad05f91f76aa40db2e
BYTES=117403  LINES=2915   (2892 -> 2915)

FILE=01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/test_fdinfo_path_behavioral.py
SHA256=a33e2f86428a0a05c188507148aaa50a1eb9360a03c64623d31a4d87966cd5aa
BYTES=11575  LINES=271
```

## 5. SCOPE HELD

```text
CLIENTS_PASID_ATTRIBUTABLE=UNCHANGED
  OWNERSHIP_CRITERION_ROWS = 11 rows, same order
  its state decision expression is byte-identical
DRM_FDS_ENUMERATED_SEMANTICS=UNCHANGED
  its scoring expression was not modified; only what feeds fd_error_count changed
READ_TEXT=UNCHANGED (still 1 definition, still used elsewhere)
R1_EXECUTED=NO   SUDO_USED=NO   COMMITS=0
FILES_TOUCHED=2 (1 modified, 1 created) + this record
```

Evidence re-verified intact: `R1-20260926T030435Z.json` `8806311b8f19a6f6…`,
`R1-20260926T024340Z.json` `04be7bc4…`, `R1-20260926T005434Z.json` `aa388953…`.

## 6. UNRESOLVED HOST EVENT — not caused by this fix, cause unknown

While verifying that no system state changed, the sysfs fingerprint moved.

`find /sys/class/drm/card1 -maxdepth 2` does not follow the symlink, so the
fingerprint is that of the symlink's own mtime. It read `2ab1d083e52dd3fa` at
the R1-4 pre-run and post-run, and `761336900080d886` afterwards.

```text
/sys/class/drm/card1     mtime 2026-09-26T04:00:10Z   <- moved
/sys/class/drm/card0     mtime 2026-09-26T00:05:07Z   unchanged
/sys/class/drm/renderD129 mtime 2026-09-26T00:05:07Z  unchanged
/sys/class/drm/renderD128 mtime 2026-09-26T00:05:07Z  unchanged
/sys/bus/pci/devices/0000:01:00.0 mtime 2026-09-26T00:05:07Z  unchanged
```

Only `card1` moved, and it moved 13 s before the first of three samples taken 2 s
apart, which then agreed. The device is still bound to `amdgpu`, `/dev/dri/card1`
is still `e2:1` with its original mtime, and `amdgpu` is still in
`/proc/modules`.

```text
CAUSE=UNKNOWN
DMSG=NOT_AVAILABLE (kernel buffer read denied without privilege)
ATTRIBUTED_TO_THIS_FIX=NO
  the only writes performed were to two files inside the repository;
  every /proc path used by the tests points at a temporary directory
R1_4_IMPACT=NONE — R1-4 ran 03:04–03:07Z, before this event
```

`SYSFS_CHANGES` is therefore **not** claimed as 0. It is `UNKNOWN`, pending an
explanation for the `card1` re-probe.

## 7. SEPARATE FINDING — not fixed here

```text
FINDING_ID=DRM_FDS_ENUMERATED_DOES_NOT_VALIDATE_CLIENT_ID
STATUS=OPEN
ROOT_CAUSE=drm_fds_enumerated is described as "DRM file descriptors enumerated
  with drm-client-id/pasid" but is scored solely on coverage["fd_error_count"] == 0.
  It never inspects whether drm-client-id or pasid was actually present.
IMPACT=the row can read PASS while the fields it names were never captured
SCOPE=explicitly excluded from this fix by the authorization
```

With the fdinfo route repaired, this row can now be given its intended
meaning, but that is a separate decision.

## 8. STATE

```text
DEFECT_SCAN_FDS_FDINFO_PATH=CLOSED
FDINFO_ROUTE=/proc/<pid>/fdinfo/<n>   VERIFIED by test
FDINFO_CONTENT_REACHES_SCAN_FDS=YES  VERIFIED by test
READ_FAILURE_NO_LONGER_SILENT=YES    VERIFIED by test
REGRESSION_PROOF=9/17 fail on the bit-identical pre-fix collector
R1_RUN_5=NOT_AUTHORIZED
```
