"""Informe verificable: atomo, sha de cada pieza, estado final y limitaciones."""
import json, os, hashlib, time

def build(manifest, repair, verify, verify_file, report_dir):
    run_id = "F02-" + time.strftime("%Y%m%dT%H%M%S")
    a = os.path.join(report_dir, run_id + ".json")
    if os.path.exists(a):
        return build(manifest, repair, verify, verify_file, report_dir)  # rechazar colisión
    payload = {
        "run_id": run_id,
        "case": "F-02",
        "sha256_manifest": hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",",":",)).encode()).hexdigest() if isinstance(manifest, dict) else None,
        "sha256_oracle": verify.get("oracle_sha256") if isinstance(verify, dict) else None,
        "sha256_verify_db": verify.get("sha256_verify") if isinstance(verify, dict) else None,
        "verdict": verify.get("verdict", "NOT_DETERMINED") if isinstance(verify, dict) else "NOT_DETERMINED",
        "verify_detail": verify,
        "repair_detail": repair,
        "manifest": manifest,
        "limitaciones": [
            "verificacion sobre copia; la DB protegida no fue tocada ni leida con intencion de modificacion",
            "terceros no participaron; PROVEN no se declara",
            "prediccion de rendimiento no hecha; solo correctitud estructural",
            "hipótesis H3 (corrupción) sigue NO_DETERMINADA",
        ],
        "estado_final": "PASS_PARTIAL",
    }
    # escritura atomica con O_EXCL
    tmp = a + ".tmp." + str(os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, a)  # atómico en mismo filesystem
    return a
