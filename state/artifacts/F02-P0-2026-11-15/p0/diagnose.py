"""Diagnóstico estructurado para F-02 (H1 demostrada; H2..H4 disputadas)."""
def diagnosticar(evidence, src_sha):
    missing = evidence.get("missing", {})
    total_missing = sum(len(v) for v in missing.values())
    return {
        "case": "F-02",
        "causa": "Esquema SQLite persistido incompatible con contrato de escritura de store.registrar() (faltan columnas M281).",
        "evidencias": [
            {"id": "EV-1", "fuente": "PRIME_SRC_SHA256", "valor": src_sha, "validez": "inmutable_en_reporte"},
            {"id": "EV-2", "fuente": "PRAGMA table_info(operations)", "valor": evidence["columns"]["operations"], "validez": "static"},
            {"id": "EV-3", "fuente": "PRAGMA table_info(results)", "valor": evidence["columns"]["results"], "validez": "static"},
            {"id": "EV-4", "fuente": "counts_pre", "valor": evidence["counts"], "validez": "static"},
            {"id": "EV-5", "fuente": "integrity_check", "valor": evidence["integrity"], "validez": "static"},
        ],
        "hipotesis": [
            {"id": "H1", "descripcion": "Esquema pre-M281 incompatible con contrato actual", "estado": "CONFIRMADA", "discriminante": "PRAGMA table_info"},
            {"id": "H2", "descripcion": "Base equivocada / ruta incorrecta", "estado": "RECHAZADA", "discriminante": "sha256(src) igual a esperado"},
            {"id": "H3", "descripcion": "Corrupción del archivo", "estado": "NO_DETERMINADA", "discriminante": "integrity_check antes=ok, tras añadir columnas=ok -> no demuestra antes; queda abierta"},
            {"id": "H4", "descripcion": "INSERT mal formado en registrar()", "estado": "DESCARTADA", "discriminante": "registrar() sobre copia migrada escribe op_* correctamente"},
        ],
        "limitaciones": [
            "Candidato reparado sobre copia; DB protegida nunca tocada",
            "Terceros NO verificaron este diagnóstico",
            "H3 sigue abierta: no se ejecutó PRAGMA integrity sobre la DB original (acceder a protegida no estaba autorizado)"
        ],
        "recomendacion": "REPARAR_COLUMNAS_ALTER",
    }
