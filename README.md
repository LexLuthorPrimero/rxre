# RXRE — Reverse Engineering Engine

RXRE is a reverse-engineering engine that lets an AI investigate an
unfamiliar target with traceability and epistemic rigor. It speaks
JSON Lines: one JSON request per line, one response (an "envelope")
per line, in the same order.

The AMD Radeon RX 550 (Polaris12 / GFX8) against the Linux 7.1.3
sources is the current validation field, not the architectural limit:
RXRE dispatches to capabilities and normalizes whatever the backing
tool emits, so a new target is a new corpus, not a new engine.

## Layout

    tools/rxre/            the engine (API, core, commands, backends)
    tools/*.py             the backing tools the engine dispatches to
    docs/TOOLS-STATUS.md   tool registry status (read by toolreg.py)
    RESEARCH/working/      the corpus RXRE investigates (Linux 7.1.3)

## Run it

    echo '{"op":"ops"}' | python3 tools/rxre/api/machine.py
    echo '{"op":"query","target":"0000:01:00.0",
           "question":"who writes VM_CONTEXT0_CNTL"}' \
      | python3 tools/rxre/api/machine.py

## Documentation for an unfamiliar AI

    tools/rxre/docs/AI_QUICKSTART.md        how to drive RXRE (read first)
    tools/rxre/docs/RXRE_PUBLIC_CONTRACT.md  the exact request/response contract

Both are the only documents needed to operate RXRE.

## License

GPL-2.0 (see LICENSE). The engine declares SPDX-License-Identifier:
GPL-2.0 in its sources. The corpus is the Linux kernel source tree
(Linux 7.1.3), also GPL-2.0, redistributed here unmodified as the
investigation corpus.

## Target scope

Operations are target-scoped by whitelist. The PCI target
0000:01:00.0 (the RX 550) is the only authorized GPU target.
0000:00:02.0 (the processor integrated GPU) is out of scope and is
blocked before any execution: RXRE returns "blocked" for it and
runs nothing.
