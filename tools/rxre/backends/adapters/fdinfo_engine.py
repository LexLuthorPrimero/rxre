#!/usr/bin/env python3
"""RXRE-FDINFO-ENGINE-OBSERVATION-022 / 024.
Adaptador de solo lectura que obtiene contadores drm-engine-* desde
/proc/<pid>/fdinfo/<fd> para RX 550 Polaris12 (0000:01:00.0).

CONTRATO DE SEGURIDAD:
- Solo lectura de /proc (rw-r--r--, mismo usuario, sin escalado).
- No sudo; no DEBUGFS; no MMIO; no escritura.
- No modifica DB/mechanismo/MMR / PUBLISHED_VERIFIED / .rxre / informes cerrados.
- Si el dispositivo no coincide (drm-pdev) → bloqueo explícito, NO atribución.
- Si el FD no existe o es inaccesible → bloqueo/error según caso.
- Si los contadores faltan → partial con limitaciones declaradas.
- Baseline opcional permite distinguir incremento / sin incremento.

USO DEL CONCEPTO artefacto (024):
- `artefacto=/proc/<pid>/fdinfo/<fd>` es una referencia verificable al recurso
  observado; el adapter lo valida (leer, drm-pdev, contadores) antes de producir.
- `machine.procesar_linea` valida la misma referencia en precheck.
"""
from __future__ import annotations
import hashlib, json, os, re, time

ALLOW_PCI = "0000:01:00.0"
RENDER_DEV = "/dev/dri/renderD128"
PROC_ROOT = "/proc"   # permiten pruebas sintéticas mediante monkeypatch

def _hash_texto(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _parse_fdinfo(texto: str) -> dict:
    pdev = None
    gfx = None
    compute = None
    for line in texto.splitlines():
        line = line.strip()
        if line.startswith("drm-pdev:"):
            pdev = line.split(":", 1)[1].strip()
        elif line.startswith("drm-engine-gfx:"):
            gfx = int(line.split(":", 1)[1].split()[0])
        elif line.startswith("drm-engine-compute:"):
            compute = int(line.split(":", 1)[1].split()[0])
    return {"pdev": pdev, "gfx": gfx, "compute": compute}

def observe_engine(**params) -> dict:
    t0 = time.time()
    pci = params.get("pci_address") or params.get("pci")
    artefacto_path = params.get("artefacto") or params.get("artifact")
    pid_target = params.get("pid")
    fd_target = params.get("fd")
    baseline = params.get("baseline") or {}

    if pci != ALLOW_PCI:
        return {"status": "invalid_input", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "pci_address no coincide con allow-list (solo %s)" % ALLOW_PCI,
                "results": [], "limitations": ["pci_address=%s" % pci],
                "precheck": {"ok": False, "motivo": "pci_address invalido"}}

    # Resolver referencia de artefacto / fdinfo
    fdinfo_path = None
    pid = None
    fd = None
    artefacto_root = None
    try:
        if artefacto_path:
            # contrato artefacto: <root>/<pid>/fdinfo/<fd>
            # En produccion <root> es /proc. Se acepta otra raiz solo para
            # pruebas sinteticas; si no es /proc, se DECLARA como limitacion.
            m = re.match(r"^(?P<root>.*)/(?P<pid>\d+)/fdinfo/(?P<fd>\d+)$",
                         artefacto_path)
            if m:
                pid = int(m.group("pid"))
                fd = m.group("fd")
                fdinfo_path = artefacto_path
                if not m.group("root").rstrip("/").endswith("proc"):
                    artefacto_root = m.group("root")
                else:
                    artefacto_root = None
            else:
                return {"status": "invalid_input", "op": "rxre.observation_engine",
                        "capability": "rxre.observation_engine",
                        "motivo": "artefacto no sigue <root>/<pid>/fdinfo/<fd>",
                        "results": [], "limitations": ["artefacto=%s" % artefacto_path],
                        "precheck": {"ok": False}}
        elif pid_target is not None and fd_target is not None:
            pid = int(pid_target)
            fd = str(fd_target)
            fdinfo_path = os.path.join(PROC_ROOT, str(pid), "fdinfo", fd)
        else:
            # búsqueda de todas las tareas (solo lectura; sin sudo)
            for entry in os.listdir(PROC_ROOT):
                if not entry.isdigit():
                    continue
                if pid_target is not None and int(entry) != int(pid_target):
                    continue
                proc_fd_dir = os.path.join(PROC_ROOT, entry, "fd")
                if not os.path.isdir(proc_fd_dir):
                    continue
                try:
                    fds = os.listdir(proc_fd_dir)
                except OSError:
                    continue
                for f in fds:
                    try:
                        target = os.readlink(os.path.join(proc_fd_dir, f))
                    except OSError:
                        continue
                    if target == RENDER_DEV:
                        info_path = os.path.join(PROC_ROOT, entry, "fdinfo", f)
                        try:
                            with open(info_path) as fh:
                                txt = fh.read()
                        except OSError:
                            continue
                        parsed = _parse_fdinfo(txt)
                        if parsed["pdev"] == ALLOW_PCI:
                            pid = int(entry)
                            fd = f
                            fdinfo_path = info_path
                            break
                if pid is not None:
                    break
    except Exception as exc:
        return {"status": "error", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "excepcion en resolucion de referencia: %s" % exc,
                "results": [], "limitations": ["excepcion en busqueda: %s" % str(exc)],
                "precheck": {"ok": False, "motivo": "error de resolucion"}}

    if fdinfo_path is None or pid is None or fd is None:
        return {"status": "blocked", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "no se encontro fd de renderD128 con drm-pdev=%s" % ALLOW_PCI,
                "results": [], "limitations": ["pid/fd no encontrado o inaccesible"],
                "precheck": {"ok": False, "motivo": "recurso no encontrado"}}

    # Leer fdinfo (artefacto real observado)
    try:
        with open(fdinfo_path) as fh:
            fdinfo_text = fh.read()
    except FileNotFoundError:
        return {"status": "blocked", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "artefacto no existe (proceso terminado o FD cerrado): %s" % fdinfo_path,
                "results": [], "limitations": ["artefacto inexistente: %s" % fdinfo_path],
                "precheck": {"ok": False, "motivo": "artefacto inexistente"}}
    except PermissionError:
        return {"status": "blocked", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "permiso denegado al leer %s" % fdinfo_path,
                "results": [], "limitations": ["permiso denegado"],
                "precheck": {"ok": False, "motivo": "permiso denegado"}}
    except Exception as exc:
        return {"status": "error", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "error leyendo fdinfo: %s" % exc,
                "results": [], "limitations": ["fdinfo inaccesible", str(exc)],
                "precheck": {"ok": False, "motivo": "error de lectura"}}

    parsed = _parse_fdinfo(fdinfo_text)
    # Verificar dispositivo observado
    if parsed["pdev"] is None:
        return {"status": "blocked", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "formato invalido: drm-pdev ausente en %s" % fdinfo_path,
                "results": [], "limitations": ["formato invalido: drm-pdev ausente"],
                "precheck": {"ok": False, "motivo": "formato invalido"}}
    if parsed["pdev"] != ALLOW_PCI:
        return {"status": "invalid_input", "op": "rxre.observation_engine",
                "capability": "rxre.observation_engine",
                "motivo": "dispositivo incorrecto: drm-pdev=%s (esperado %s)" % (parsed["pdev"], ALLOW_PCI),
                "results": [], "limitations": ["dispositivo incorrecto: drm-pdev=%s" % parsed["pdev"]],
                "precheck": {"ok": False, "motivo": "dispositivo incorrecto"}}

    gfx_ns = parsed["gfx"]
    compute_ns = parsed["compute"]
    artifact_hash = hashlib.sha256(fdinfo_text.encode("utf-8")).hexdigest()

    # Estado de resultado según disponibilidad
    if gfx_ns is not None and compute_ns is not None:
        res_status = "observed"
    else:
        res_status = "partial"

    # Delta / baseline (024: distinguir incremento / ausencia / sin incremento)
    delta_state = {}
    if isinstance(baseline, dict):
        b_gfx = baseline.get("gfx") or baseline.get("drm_engine_gfx_ns")
        b_comp = baseline.get("compute") or baseline.get("drm_engine_compute_ns")
        if gfx_ns is not None:
            delta_state["gfx"] = "sin_incremento" if (b_gfx is not None and gfx_ns == b_gfx) else ("con_incremento" if (b_gfx is not None and gfx_ns > b_gfx) else "sin_baseline")
        else:
            delta_state["gfx"] = "contador_ausente"
        if compute_ns is not None:
            delta_state["compute"] = "sin_incremento" if (b_comp is not None and compute_ns == b_comp) else ("con_incremento" if (b_comp is not None and compute_ns > b_comp) else "sin_baseline")
        else:
            delta_state["compute"] = "contador_ausente"
    else:
        delta_state = {"gfx": "sin_baseline", "compute": "sin_baseline"}

    # Limitaciones declaradas (MENTE / CUERPO / AGUA requieren limitaciones)
    limitations_env = [
        "Solo GFX/COMPUTE observados; SC/SDMA/VIDEO/DEC no expuestos en fdinfo de esta version de kernel",
        "DEBUGFS bloqueado (requiere root) para etapas adicionales",
        "Contadores acumulativos; delta requiere lectura previa (t0); observacion de instante, no de ejecucion continua.",
        "Observacion realizada con solo lectura; sin MMIO ni escritura; sin sudo.",
    ]
    if gfx_ns is None or compute_ns is None:
        limitations_env.append("Contador parcial o ausente: no demuestra inactividad (solo ausencia de exposicion por el kernel o FD).")
    if isinstance(baseline, dict):
        limitations_env.append("Baseline aplicado (%s); delta calculado contra lectura t0." % str(baseline))
    if artefacto_root:
        limitations_env.append("El artefacto no esta bajo /proc (raiz %s): referencia sintetica, no una lectura real de /proc." % artefacto_root)

    result_id = "res_fdinfo_024_%d_%s_%s" % (pid, fd, artifact_hash[:12])
    result = {
        "result_id": result_id,
        "type": "OBSERVATION",
        "value": {"gfx_ns": gfx_ns, "compute_ns": compute_ns, "delta_state": delta_state},
        "source": "rxre.adapters.fdinfo_engine",
        "artifact": "fdinfo:%s:%s" % (ALLOW_PCI, fdinfo_path),
        "location": {"file": fdinfo_path, "line": 0},
        "file": fdinfo_path,
        "line": 0,
        "scope": ALLOW_PCI,
        "tool": "fdinfo_engine",
        "tool_version": "024",
        "status": res_status,
        "artifact_hash": artifact_hash,
        "limitations": limitations_env,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "raw": {
            "pid": pid, "fd": fd, "fdinfo_path": fdinfo_path,
            "drm_pdev": ALLOW_PCI, "device": "AMD Radeon RX 550 / 550 Series (Polaris12)",
            "method": "fdinfo_engine_observation",
            "metrics": {"drm_engine_gfx_ns": gfx_ns, "drm_engine_compute_ns": compute_ns},
            "delta_state": delta_state,
            "baseline_applied": bool(isinstance(baseline, dict) and baseline),
        },
    }
    duration_s = round(time.time() - t0, 4)
    precheck = {
        "ok": True,
        "artefacto": fdinfo_path,
        "dispositivo_verificado": ALLOW_PCI,
        "drm_pdev_leido": ALLOW_PCI,
        "lectura": "solo-lectura /proc/<pid>/fdinfo/<fd>",
        "escritura": False,
        "root_requerido": False,
        "verificaciones": ["drm-pdev coincide con allow-list",
                            "fdinfo legible sin elevar privilegios",
                            "contadores extraidos (si presentes)",
                            "artefacto verificado (si proporcionado)"],
    }
    argv = ["observe_engine", "--pci_address=%s" % ALLOW_PCI]
    if pid is not None:
        argv.append("--pid=%s" % pid)
    if fd is not None:
        argv.append("--fd=%s" % fd)
    if params.get("artefacto"):
        argv.append("--artefacto=%s" % params.get("artefacto"))
    if isinstance(baseline, dict) and baseline:
        argv.append("--baseline=%s" % json.dumps(baseline))
    ejec = {
        "command_or_api": "rxre.observation_engine",
        "argv": argv,
        "exit_status": 0,
        "duration_s": duration_s,
    }
    provenance = {
        "adapter": "fdinfo_engine",
        "pci_address": ALLOW_PCI,
        "pid": pid,
        "fd": fd,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "estado": "completa",
        "input_hash": _hash_texto("%s|%s|%s|%s" % (ALLOW_PCI, pid, fd, fdinfo_path)),
        "transformacion": "extraccion de contadores drm-engine-gfx/compute desde fdinfo",
        "normalizador": "backends.adapters.fdinfo_engine",
        "source_path": fdinfo_path,
        "drm_pdev_observed": ALLOW_PCI,
        "method": "fdinfo_engine_observation",
    }
    return {
        "status": "ok",
        "op": "rxre.observation_engine",
        "capability": "rxre.observation_engine",
        "results": [result],
        "precheck": precheck,
        "ejecucion": ejec,
        "provenance": provenance,
        "limitations": limitations_env,
    }
