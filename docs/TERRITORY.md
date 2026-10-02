
TERRITORY.md -- what this session writes, what it reads, and what it never touches.

WHY THIS FILE EXISTS, AND WHY IT IS SHORT
-----------------------------------------
Several sessions share this tree.  The division of labour that keeps that
workable is not "whoever is more confident".  It is: **each session writes its
own files and nobody else's**, and says so where the next one will read it.

This file is that statement for the documentation session, and it is deliberately
short.  A territory document that explains itself at length is a document nobody
reads before doing the thing it forbids.

THE THREE PARTS
---------------
  ESCRIVO    exactly two places.  Nothing else, ever.
  LEO        anything.  Reading another session's work is not touching it.
  NO TOCO    the enumerated list, which is the whole point of having this file

WHY "EVER", AND NOT "BY DEFAULT"
--------------------------------
Because the interesting failure is not a decision to edit somebody's file.  It is
a tool that gains a `--write` flag, or a patch that grows one extra path, or a
refactor that moves a constant and takes a directory with it.  Those are all
small, all reasonable, and none of them feel like crossing a line.

So the rule is enforced rather than promised: `drift.py --territory` reads every
source file this session owns and resolves every write path it can find, and
reports anything that lands outside these two directories.  A new write that
appears in a new place is then a thing the next run NAMES, instead of a thing
nobody notices until two sessions have edited the same file.

WHAT IS NOT FORBIDDEN, and would be easy to get wrong
-----------------------------------------------------
  · READING anything, including other sessions' code and documentation.  `F3d` was
    closed by reading `rx550_pm4.c`, which belongs to another session, and by
    answering a question `revkit/PTEPDE-GFX8.md` had left written down.  Both are
    reading.  Neither is touching.
  · DOCUMENTING another session's artefacts.  `TOOLS-STATUS.md` describes 115
    tools, most of them written by others, and describing something is how the
    next session finds it.  What is forbidden is changing it.
  · RECORDING a defect in another session's file.  `C-012` names two operational
    indices with the same basename and says which line is missing where.  It does
    not edit the TSV.
  · ANSWERING the question a colleague left open, and saying in my own files that
    the answer is there for them to pick up.
  · TAKING A LOCK.  `.write-lock/` exists so two sessions do not write the same
    file at once.  Using it is not ownership.

WHAT IS FORBIDDEN
-----------------
  · editing, moving, renaming or deleting a file outside `docs/` and `tools/`
  · adding a write path to one of my own tools that resolves outside those two
    directories and outside an ephemeral temporary directory
  · committing, staging, or reverting anything of another session's

HOW IT IS CHECKED, AND WHAT THE CHECK DOES NOT PROVE
----------------------------------------------------
  `drift.py --territory` resolves write paths statically.  A path it cannot
  resolve is reported as UNRESOLVED and not counted as safe, because a static
  resolver that guessed would be asserting something it did not read.

  And the honest limit: a static check sees `open(...)` calls.  It does not see a
  write performed through a library, a subprocess, or a variable assigned three
  functions away.  So this check raises the cost of crossing the line; it does not
  make crossing it impossible.  Saying otherwise would be exactly the class of
  overclaim this project keeps correcting in itself.
