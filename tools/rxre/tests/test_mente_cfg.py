#!/usr/bin/env python3
"""MENTE-3 adversarial."""
import sys, os, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rxre.core.mente_cfg import MenteCFG

fails = []
n = 0
def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    m_no_disp = MenteCFG(os.path.join(td, "cfg_no.db"), dispatcher=None)
    try:
        m_no_disp.construir("/fake", "main")
        v("M3.1 requiere dispatcher", False, "no falló")
    except ValueError as e:
        v("M3.1 requiere dispatcher", "dispatcher" in str(e).lower() or "backend" in str(e).lower(), str(e)[:40])

    m = MenteCFG(os.path.join(td, "cfg.db"))
    import sqlite3, uuid
    from datetime import datetime
    cfg_id = f"cfg-{uuid.uuid4().hex[:8]}"
    with sqlite3.connect(m.db_path) as c:
        c.execute(
            "INSERT INTO mente_cfg (cfg_id, artifact_hash, funcion, bloques, aristas, entry_block, exit_blocks, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cfg_id, "hash", "main",
             '["B0","B1","B2","B3"]',
             '[["B0","B1"],["B1","B2"],["B2","B3"],["B0","B3"]]',
             "B0", '["B3"]', datetime.utcnow().isoformat())
        )
    v("M3.2 alcanzable", m.alcanzable(cfg_id, "B0", "B3") is True)
    v("M3.3 no alcanzable (B3->B0, no hay arista inversa)", m.alcanzable(cfg_id, "B3", "B0") is False)
    paths = m.caminos(cfg_id, "B0", "B3")
    v("M3.4 caminos", len(paths) >= 2, "len=%d" % len(paths))

print("PASS: %d/%d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
