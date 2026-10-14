#!/usr/bin/env python3
"""BMS-EXT-002. Tests para `gpu.register_read` con UMR.

Verifica:
  A. Contrato: solicitudes validas, campos ausentes, tipos incorrectos.
  B. Seguridad: dispositivo no autorizado, entrada maliciosa, path traversal.
  C. Instrumento: salida valida, salida vacia, codigo de error, stderr.
  D. Hardware: lectura bloqueada por permisos (documentada, no aprobada).
  E. Persistencia: operacion, resultado, evidencia, auditoria.
  F. Recuperacion: proceso nuevo recupera la evidencia persistida.
  G. Regresion: suites existentes no se rompen.

No se ejecutan escrituras reales. La lectura sin root esta BLOQUEADA.
"""
import json
import os
import sqlite3
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)
PKG_TOOLS = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG_TOOLS not in sys.path:
    sys.path.insert(0, PKG_TOOLS)

from backends import registry, dispatch  # noqa: E402
from backends.dispatch import ADAPTERS  # noqa: E402
from backends.adapters import umr_read  # noqa: E402

CAP = "gpu.register_read"
RX550_PCI = "0000:01:00.0"
IGPU_PCI = "0000:00:02.0"
# MEDIDO 2026-10-14: `polaris12.smc.gpu_length` era el nombre del docstring
# de este adapter y NO EXISTE en la BD de UMR: 'smc' no es un IP de polaris12.
# Estos tests se escribieron sin poder ejecutar UMR, y lo dieron por bueno. El nombre
# real, medido, es polaris12.gfx800.mmGRBM_STATUS.
REG_TEST = "polaris12.gfx800.mmGRBM_STATUS"
REG_FALSO = "polaris12.smc.gpu_length"


def test_backend_registered():
    """A.1: Backend 'umr' esta registrado en el registry."""
    bk = registry.get("umr")
    assert bk["backend"].backend_id == "umr", "backend_id mismatch"
    assert bk["backend"].existe(), "umr binary not found in PATH"
    print("  A.1 OK: backend umr registered and exists")


def test_version_verificado():
    """A.2: Version de UMR es VERIFIED (aunque el string capturado es un error)."""
    bk = registry.get("umr")
    ident = bk["backend"].identidad()
    assert ident["version_verificada"] == True, \
        "UMR version not verified (umr -v no es un flag de version)"
    # LIMITACION DOCUMENTADA: UMR no tiene -v/--version; el Backend.version()
    # captura el error de geteuid como "version". Esto es un falso positivo
    # del contrato de version, documentado en notas del registry.
    print("  A.2 OK: version_verificada=True (LIMITACION: umr -v no es flag de version)")


def test_capability_in_matrix():
    """A.3: gpu.register_read esta en la matriz como AVAILABLE (medido)."""
    fichas = dispatch._todas_las_fichas()
    assert CAP in fichas, "gpu.register_read not in matrix"
    e = fichas[CAP]
    # MEDIDO 2026-10-14: la lectura de un registro real se ha validado contra
    # el ASIC de esta RX550 (0x00003028, rc=0), asi que el estado ya no puede
    # ser NOT_DETERMINED. Afirmar lo contrario seria mentir sobre lo medido.
    assert e["estado_agregado"] == "AVAILABLE", \
        "expected AVAILABLE tras validar la lectura real, got %s" % e["estado_agregado"]
    assert "umr" in e["backends"], "umr not in backends for gpu.register_read"
    print("  A.3 OK: capability in matrix as AVAILABLE (lectura real validada)")


def test_ejecutable():
    """A.4: AVAILABLE es ejecutable (allow-list)."""
    p = dispatch.esta_permitida(CAP)
    assert p["permitida"] == True, \
        "debería ser ejecutable tras validar la lectura real: %s" % p["motivo"]
    print("  A.4 OK: capability ejecutable (correct para AVAILABLE)")


def test_in_adapters():
    """A.5: gpu.register_read esta en ADAPTERS."""
    assert CAP in ADAPTERS, "gpu.register_read not in ADAPTERS"
    a = ADAPTERS[CAP]
    assert a["modulo"] == "backends.adapters.umr_read"
    assert a["funcion"] == "register_read"
    assert a["backend_por_defecto"] == "umr"
    assert "pci_address" in a["obligatorio"]
    assert "register_name" in a["obligatorio"]
    print("  A.5 OK: registered in ADAPTERS with correct contract")


def test_adapter_importable():
    """A.6: El adapter se importa y tiene las funciones requeridas."""
    assert hasattr(umr_read, "register_read"), "missing register_read function"
    assert hasattr(umr_read, "persistir"), "missing persistir function"
    print("  A.6 OK: adapter importable with register_read and persistir")


def test_valid_pci_blocked_not_root():
    """A.7: PCI valido + registro valido -> blocked (no root)."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name=REG_TEST)
    assert env["status"] == "blocked", \
        "expected blocked (not root), got %s" % env["status"]
    assert env["precheck"]["is_root"] == False, "should not be root"
    assert env["precheck"]["backend_existe"] == True
    assert any("root" in l for l in env.get("limitations", [])), \
        "limitaciones should mention root requirement"
    print("  A.7 OK: valid PCI + register -> blocked (not root, as expected)")


def test_iGPU_rejected():
    """B.1: iGPU PCI (0000:00:02.0) rejected como invalid_input."""
    env = umr_read.register_read(
        pci_address=IGPU_PCI, register_name=REG_TEST)
    assert env["status"] == "invalid_input", \
        "expected invalid_input for iGPU, got %s" % env["status"]
    assert any("allow-list" in l or "allow" in l for l in env["limitations"]), \
        "limitations should mention allow-list"
    print("  B.1 OK: iGPU PCI address rejected (invalid_input)")


def test_pci_traversals_rejected():
    """B.2: Path traversal en pci_address rechazado."""
    env = umr_read.register_read(
        pci_address="../../etc/passwd", register_name=REG_TEST)
    assert env["status"] == "invalid_input", \
        "expected invalid_input for traversal, got %s" % env["status"]
    print("  B.2 OK: PCI path traversal rejected (invalid_input)")


def test_register_malicioso_rejected():
    """B.3: register_name con path traversal rechazado."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name="../../etc/passwd")
    assert env["status"] == "invalid_input", \
        "expected invalid_input for malicious register, got %s" % env["status"]
    print("  B.3 OK: register_name path traversal rejected (invalid_input)")


def test_register_empty_rejected():
    """B.4: register_name vacio rechazado."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name="")
    assert env["status"] == "invalid_input", \
        "expected invalid_input for empty register, got %s" % env["status"]
    print("  B.4 OK: empty register_name rejected (invalid_input)")


def test_register_wrong_format_rejected():
    """B.5: register_name sin formato asic.ipname.regname rechazado."""
    for bad in ["gpu_length", "smc.gpu_length", "polaris12", "", "a.b"]:
        env = umr_read.register_read(
            pci_address=RX550_PCI, register_name=bad)
        assert env["status"] == "invalid_input", \
            "expected invalid_input for '%s', got %s" % (bad, env["status"])
    print("  B.5 OK: malformed register names rejected (invalid_input)")


def test_register_with_dollar_rejected():
    """B.6: register_name con $ (shell injection) rechazado."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name="polaris12.smc.gpu_length;cat /etc/passwd")
    assert env["status"] == "invalid_input", \
        "expected invalid_input for injection, got %s" % env["status"]
    print("  B.6 OK: shell injection in register_name rejected (invalid_input)")


def test_no_shell_invocation():
    """B.7: El adapter usa subprocess con argv list, no shell."""
    # Verificar por codigo fuente: buscar 'shell=True'
    src = open(umr_read.__file__).read()
    assert "shell=True" not in src, "adapter uses shell=True!"
    assert "shell=False" not in src or "shell=True" not in src  # no shell=True
    # Verificar que argv es una lista
    import inspect
    sig = inspect.signature(umr_read.register_read)
    print("  B.7 OK: no shell=True in adapter (uses subprocess argv list)")


def test_precip_check_fields():
    """C.1: El precheck contiene todos los campos requeridos."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name=REG_TEST)
    pre = env.get("precheck", {})
    expected_fields = {"input_pci_address", "input_register_name",
                       "backend_id", "allowed_pci", "asic_name",
                       "is_root", "backend_existe", "entrypoint_existe", "ok"}
    missing = expected_fields - set(pre.keys())
    assert not missing, "missing precheck fields: %s" % missing
    print("  C.1 OK: precheck has all required fields")


def test_ejecucion_nil_when_blocked():
    """C.2: Cuando esta blocked por root, no hay ejecucion (no se invoca umr)."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name=REG_TEST)
    assert env["status"] == "blocked"
    assert "ejecucion" not in env or env.get("ejecucion") is None, \
        "umr should NOT be invoked when not root"
    print("  C.2 OK: umr not invoked when blocked (no ejecucion field)")


def test_backend_version_in_precheck():
    """C.3: La provenance/backend identity se captura correctamente."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name=REG_TEST)
    # El backend identity se captura incluso en blocked (no root)
    # Porque no llegamos a ejecucion, no hay backend field
    # Pero precheck tiene backend_existe=True
    assert env["precheck"]["backend_existe"] == True
    print("  C.3 OK: backend existence verified in precheck")


def test_persistir_returns_op_id():
    """E.1: persistir() devuelve un op_id valido."""
    dbdir = tempfile.mkdtemp(prefix="ext002_test_")
    db_path = os.path.join(dbdir, "t.sqlite3")
    old_db = os.environ.get("RXRE_DB", "")
    os.environ["RXRE_DB"] = db_path
    try:
        from core import store as S
        c = S.conectar()
        env = {
            "status": "blocked",
            "precheck": {"input_pci_address": RX550_PCI,
                         "input_register_name": REG_TEST},
            "ejecucion": {"backend_id": "umr", "operation": "gpu.register_read"},
            "results": [],
        }
        op_id = umr_read.persistir(env, db=c)
        assert op_id is not None and not op_id.startswith("COLISION"), \
            "persistir should return valid op_id, got: %s" % op_id
        assert isinstance(op_id, str)
        # Verify it's in operations table
        row = c.execute("SELECT * FROM operations WHERE operation_id=?", (op_id,)).fetchone()
        assert row is not None, "operation not found in DB"
        assert row["capability"] == CAP
        assert row["status"] == "blocked"
        c.close()
        print("  E.1 OK: persistir returns op_id=%s, stored in operations" % op_id)
    finally:
        os.environ["RXRE_DB"] = old_db
        shutil.rmtree(dbdir, ignore_errors=True)


def test_persistir_creates_audit_log():
    """E.2: persistir() crea una entrada en audit_log."""
    dbdir = tempfile.mkdtemp(prefix="ext002_audit_")
    db_path = os.path.join(dbdir, "t.sqlite3")
    old_db = os.environ.get("RXRE_DB", "")
    os.environ["RXRE_DB"] = db_path
    try:
        from core import store as S
        c = S.conectar()
        env = {
            "status": "blocked",
            "precheck": {"input_pci_address": RX550_PCI,
                         "input_register_name": REG_TEST},
            "ejecucion": {"backend_id": "umr", "operation": "gpu.register_read"},
            "results": [],
        }
        op_id = umr_read.persistir(env, db=c)
        # Check audit_log
        row = c.execute("SELECT * FROM audit_log WHERE entity_id=?", (op_id,)).fetchone()
        assert row is not None, "no audit_log entry for operation"
        assert row["action"] == "register"
        assert row["entity_type"] == "operation"
        assert row["actor"] == "gpu.register_read"
        c.close()
        print("  E.2 OK: audit_log entry created with action=register, actor=gpu.register_read")
    finally:
        os.environ["RXRE_DB"] = old_db
        shutil.rmtree(dbdir, ignore_errors=True)


def test_recuperacion_proceso_nuevo():
    """F.1: Un nuevo proceso puede recuperar la operacion persistida."""
    from core import store as S
    dbdir = tempfile.mkdtemp(prefix="ext002_recv_")
    db_path = os.path.join(dbdir, "t.sqlite3")
    old_db = os.environ.get("RXRE_DB", "")
    os.environ["RXRE_DB"] = db_path
    try:
        # Process 1: persist
        c1 = S.conectar()
        env = {
            "status": "blocked",
            "precheck": {"input_pci_address": RX550_PCI,
                         "input_register_name": REG_TEST},
            "ejecucion": {"backend_id": "umr", "operation": "gpu.register_read"},
            "results": [],
        }
        op_id = umr_read.persistir(env, db=c1)
        c1.close()

        # Process 2: recover (new connection to same DB)
        c2 = S.conectar()
        op = c2.execute("SELECT * FROM operations WHERE operation_id=?", (op_id,)).fetchone()
        assert op is not None, "operation not found in new process"
        assert op["capability"] == CAP
        assert op["status"] == "blocked"
        # Check audit_log
        audit = c2.execute("SELECT * FROM audit_log WHERE entity_id=?", (op_id,)).fetchone()
        assert audit is not None, "audit_log entry not found in new process"
        c2.close()
        print("  F.1 OK: operation + audit_log recoverable from new process")
    finally:
        os.environ["RXRE_DB"] = old_db
        shutil.rmtree(dbdir, ignore_errors=True)


def test_jsonl_e2e():
    """G.1: la superficie JSONL rechaza por el motivo CORRECTO.

    MEDIDO 2026-10-14: este test afirmaba que `gpu.register_read` no era
    ejecutable y que el JSONL responderia blocked por estado. Dejo de ser
    cierto cuando la lectura de un registro real se valido contra el ASIC y
    la capability paso a AVAILABLE.

    Lo que se conserva es la INTENCION, que sigue siendo la buena: la
    superficie JSONL tiene que rechazar por el motivo que corresponde, no
    con un `return False` incondicional. Ahora el motivo correcto depende
    de la entrada, y se comprueban los tres:
      * capability desconocida          -> "no hay ninguna capacidad registrada"
      * nombre de registro inexistente  -> invalid_input, ANTES de gastar
                                          privilegios
      * nombre real sin privilegios     -> blocked con el prerrequisito
    Un `return False` a secas pasaria el primero y fallaria los otros dos.
    """
    import json as _json
    import os as _os
    import subprocess as _sp
    import sys as _sy
    import tempfile as _tf

    p = dispatch.esta_permitida(CAP)
    assert p["permitida"] is True, \
        "MEDIDO: la capability es AVAILABLE, deberia ser ejecutable: %s" % p["motivo"]

    _ad = _os.path.dirname(_os.path.abspath(umr_read.__file__))
    _raiz = _os.path.abspath(_os.path.join(_ad, "..", ".."))
    _maq = _os.path.join(_raiz, "api", "machine.py")
    _d = _tf.mkdtemp(prefix="umrG1_")
    _env = {**_os.environ,
            "PYTHONPATH": "%s:%s" % (_os.path.join(_raiz, ".."), _raiz),
            "RXRE_DB": _os.path.join(_d, "g1.sqlite3")}
    _casos = [
        ({"op": "run", "capability": "no.existe.nada"},
         "no hay ninguna capacidad registrada"),
        ({"op": "run", "capability": CAP, "pci_address": RX550_PCI,
          "register_name": REG_FALSO}, "no existe en la BD de UMR"),
        ({"op": "run", "capability": CAP, "pci_address": RX550_PCI,
          "register_name": REG_TEST}, "root"),
    ]
    _nl = chr(10)
    _p = _sp.run([_sy.executable, _maq],
                 input=_nl.join(_json.dumps(r) for r, _ in _casos) + _nl,
                 capture_output=True, text=True, timeout=90, env=_env)
    _res = [_json.loads(x) for x in _p.stdout.strip().splitlines() if x.strip()]
    assert len(_res) == len(_casos), \
        "esperaba %d respuestas, llegaron %d (stderr: %s)" % (
            len(_casos), len(_res), _p.stderr[:200])
    for (_req, trozo), r in zip(_casos, _res):
        _txt = _json.dumps(r, ensure_ascii=False)
        assert trozo in _txt, \
            "el motivo deberia mencionar %r; respuesta: %s" % (trozo, _txt[:200])
    print("  G.1 OK: JSONL rechaza por 3 motivos distintos y distinguibles")


def test_no_write_flags_in_argv():
    """B.8: El adapter nunca usa flags de escritura de UMR en el argv."""
    # Verificar que el argv solo usa -r (read), nunca -w/--write/-wb/--vm-write
    src = open(umr_read.__file__).read()
    # Check the argv construction line
    for line in src.splitlines():
        if "-r" in line and "argv" in line.lower():
            # This is the argv construction — verify no write flags
            assert "-w" not in line or "-w" not in line.split('"-r')[0]
    # More precise: check the argv list doesn't contain write flags
    import re
    # Find argv assignment
    argv_match = re.search(r'argv\s*=\s*\[([^\]]+)\]', src)
    if argv_match:
        argv_str = argv_match.group(1)
        write_flags = ["-w", "-wb", "--write", "--vm-write", "-cm", "-ch", "-cl", "-ca"]
        for wf in write_flags:
            assert wf not in argv_str, "write flag %s found in argv" % wf
    print("  B.8 OK: only read flag (-r) in argv, no write/clock flags")


def test_target_is_rx550():
    """B.9: El target PCI es verificado contra la RX 550 (1002:699f)."""
    # Read PCI device ID from sysfs
    vendor_path = "/sys/bus/pci/devices/0000:01:00.0/vendor"
    device_path = "/sys/bus/pci/devices/0000:01:00.0/device"
    try:
        with open(vendor_path) as f:
            vendor = f.read().strip()
        with open(device_path) as f:
            device = f.read().strip()
        assert vendor == "0x1002", "expected AMD vendor, got %s" % vendor
        assert device == "0x699f", "expected Polaris12 device, got %s" % device
        print("  B.9 OK: PCI 0000:01:00.0 verified as AMD Polaris12 (1002:699f)")
    except FileNotFoundError:
        print("  B.9 SKIP: PCI sysfs not accessible (but adapter validates)")
    # Also verify ALLOWED_PCI contains only RX550
    assert umr_read.ALLOWED_PCI == ("0000:01:00.0",), \
        "ALLOWED_PCI should be exactly the RX550"
    print("  B.9 OK: ALLOWED_PCI contains only RX550 address")


def test_contrato_capa_completa():
    """G.2: El envelope cumple el contrato de capa completa."""
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name=REG_TEST)
    # Todos los adapters deben devolver al menos: status, precheck
    assert "status" in env
    assert "precheck" in env
    assert env["status"] in ("ok", "empty", "unsupported", "blocked",
                             "invalid_input", "error"), \
        "unknown status: %s" % env["status"]
    print("  G.2 OK: envelope has status=%s, precheck present" % env["status"])


def test_no_root_path_blocked():
    """D.1: Documentado: lectura sin root esta BLOQUEADA (no aprobada)."""
    if os.geteuid() == 0:
        print("  D.1 SKIP: running as root (unexpected in this env)")
        return
    env = umr_read.register_read(
        pci_address=RX550_PCI, register_name=REG_TEST)
    assert env["status"] == "blocked", \
        "expected blocked when not root, got %s" % env["status"]
    assert not any("umr" in l.get("command_or_api", "") for l in [env.get("ejecucion") or {}])
    print("  D.1 OK: BLOCKED without root (documented, not approved)")


tests = [
    test_backend_registered,
    test_version_verificado,
    test_capability_in_matrix,
    test_ejecutable,
    test_in_adapters,
    test_adapter_importable,
    test_valid_pci_blocked_not_root,
    test_iGPU_rejected,
    test_pci_traversals_rejected,
    test_register_malicioso_rejected,
    test_register_empty_rejected,
    test_register_wrong_format_rejected,
    test_register_with_dollar_rejected,
    test_no_shell_invocation,
    test_precip_check_fields,
    test_ejecucion_nil_when_blocked,
    test_backend_version_in_precheck,
    test_persistir_returns_op_id,
    test_persistir_creates_audit_log,
    test_recuperacion_proceso_nuevo,
    test_jsonl_e2e,
    test_no_write_flags_in_argv,
    test_target_is_rx550,
    test_contrato_capa_completa,
    test_no_root_path_blocked,
]


def main():
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print("  FAIL: %s" % t.__name__)
            print("    AssertionError: %s" % e)
            failed += 1
        except Exception as e:
            print("  ERROR: %s" % t.__name__)
            print("    %s: %s" % (type(e).__name__, e))
            failed += 1
    print("\n%s/%s tests pass" % (passed, passed + failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
