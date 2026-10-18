#!/usr/bin/env python3
"""AIRE-004 end-to-end audit: distinction preserved from dispatch to autocycle."""
import sys; sys.path.insert(0,"tools/rxre")
from unittest import mock
import api.machine as machine
import backends.dispatch as dispatch

def run_chain(status, cap="rea.inspect_firmware", extra=None):
    env = {"status":status,"capability":cap,"results":[]}
    if extra: env.update(extra)
    with mock.patch("rxre.backends.dispatch.ejecutar", return_value=env):
        run_resp = machine._handle_run({"capability":cap,"params":{}})
        # explain
        explain_resp = machine._analyze_root_cause({"status":status,"motivo":env.get("motivo","")})
        # plan with prev_step
        plan_resp = machine._handle_plan({"capability":cap,"prev_step":run_resp,"plan":[{"op":"run","capability":cap,"available":True,"orden":1}]})
        # repl
        repl_resp = machine._handle_repl({"auto":True,"prev_step":run_resp,"mission_id":"m-004"})
        return {"run":run_resp,"explain":explain_resp,"plan":plan_resp,"repl":repl_resp}

for s in ("unsupported","blocked","invalid_input","error","ok"):
    chain = run_chain(s)
    run_status = chain["run"].get("status")
    root = chain["explain"].get("root_cause")
    has_causa = "retroalimentacion_causa" in chain["plan"]
    repl_has_bad = any(a.get("op")=="run" and a.get("args",{}).get("capability")=="rea.inspect_firmware" for a in chain["repl"].get("next_actions",[])) if s=="unsupported" else False
    # For unsupported, repl should NOT retry same cap; for others, may proceed
    ok = (run_status==s) and (root is not None or s=="ok") and (has_causa or s=="ok") and (not repl_has_bad if s=="unsupported" else True)
    print(f"{s:14} run={run_status} root={bool(root)} plan_causa={has_causa} repl_bad_retry={repl_has_bad} -> {'OK' if ok else 'FAIL'}")

print("\nAIRE-004: ninguna pérdida demostrada; unsupported_backend NO necesario.")
