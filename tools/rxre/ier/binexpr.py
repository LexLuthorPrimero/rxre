#!/usr/bin/env python3
"""ier/binexpr.py — Identidad y evidencia ELF ET_REL x86-64. IER-EVOLVE-001 · M9.

## QUE ES

Un parser ELF propio, byte-oriented, deliberadamente separado de los
adapters de backends. Su unica responsabilidad:

    ELF -> evidencia estructurada y verificable

NO decodifica instrucciones: delega en GNU objdump como proveedor
independiente (su salida es evidencia, NO verdad semantica). NO invoca
rizin, radare2 ni ningun adapter del registro. NO ejecuta los bytes.

## ALCANCE REAL (declarado, no prometido mas alla)

    Formatos:    ET_REL
    Clase:       ELF64
    Endianess:   little-endian
    Arquitectura: x86-64 (EM_X86_64 = 62)

Cualquier otro caso produce `operational_status = BLOCKED` con el motivo
exacto. NUNCA produce `EMPTY`: un artefacto no soportado no es un
resultado vacio. SHT_REL se rechaza explicitamente; SHT_NOBITS se conserva
en el inventario sin bytes; numeracion extendida SHN_XINDEX se rechaza.

## REGLAS DE LA CASA

    DIVERGENCE no implica ERROR. Un artefacto detectado divergente
    correctamente es un exito operativo del comparador.

    Nada de aqui promociona nada. La promocion es del propietario.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

MODULE_REVISION = "ier-binexpr-1"

# --- constantes ELF x86-64 -------------------------------------------------
ET_REL = 1
EM_X86_64 = 62
SHT_PROGBITS, SHT_SYMTAB, SHT_STRTAB = 1, 2, 3
SHT_RELA, SHT_NOBITS = 4, 8
SHT_REL, SHT_DYNSYM = 9, 11
SHF_WRITE, SHF_ALLOC, SHF_EXECINSTR = 0x1, 0x2, 0x4
STT_FUNC = 2
STB_LOCAL, SHN_UNDEF, SHN_XINDEX = 0, 0, 0xFFFF
ELF_HEADER_SIZE = 64
SHDR64_SIZE = 64
SYM64_SIZE = 24
RELA64_SIZE = 24

R_X86_64_PC32 = 2
R_X86_64_PLT32 = 4

# --- estados ----------------------------------------------------------------
OP_PASS, OP_BLOCKED, OP_ERROR = "PASS", "BLOCKED", "ERROR"
CMP_MATCH, CMP_DIVERGENCE, CMP_INCONCLUSIVE = "MATCH", "DIVERGENCE", "INCONCLUSIVE"
EP_PROVEN, EP_PARTIAL, EP_NOT_DETERMINED, EP_BLOCKED = (
    "PROVEN", "PARTIAL", "NOT_DETERMINED", "BLOCKED")


def sha256_de_path(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def sha256_de_obj(obj: Any) -> str:
    body = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


_VOLATILE_KEYS = {"timestamp", "duration_s", "cwd_used"}


def normalize_to_hash_inputs(obj: Any) -> Any:
    """Elimina datos volatiles de forma determinista.

    Conserva versiones, configuracion y procedencia (decoder, parsers,
    hashes). Elimina timestamps y duraciones. La clave `sha256` del
    artefacto NO se toca: es la identidad, no un timestamp.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _VOLATILE_KEYS:
                continue
            out[k] = normalize_to_hash_inputs(v)
        return out
    if isinstance(obj, list):
        return [normalize_to_hash_inputs(x) for x in obj]
    return obj


def H_artifact(path: str) -> str:
    """Huella del artefacto fisico. Identidad, no autenticidad."""
    return sha256_de_path(path)


def H_evidence(evidence: Dict[str, Any]) -> str:
    return sha256_de_obj(normalize_to_hash_inputs(evidence))


def H_report(report: Dict[str, Any]) -> str:
    return sha256_de_obj(normalize_to_hash_inputs(report))


def _sha256_texto(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _leer_cstr(blob: bytes, off: int) -> str:
    if off < 0 or off >= len(blob):
        return ""
    fin = blob.find(b"\x00", off)
    if fin < 0:
        return ""
    return blob[off:fin].decode("utf-8", errors="replace")


def _precondition(path: str, max_bytes: int):
    """Devuelve (None, meta) o (motivo, meta). Nunca lanza."""
    if not isinstance(path, str) or not path:
        return "ruta vacia", {}
    if not os.path.isfile(path):
        return "artefacto no existe o no es un archivo: %s" % path, {}
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return "no se pudo medir el artefacto: %s" % exc, {}
    if size <= 0:
        return "artefacto vacio", {}
    if size > max_bytes:
        return "artefacto excede max_bytes (%d > %d)" % (size, max_bytes), {}
    return None, {"artifact_size": size}


def _validar_elf64(data: bytes):
    """Cabecera. Devuelve (header, None) o (None, motivo)."""
    if len(data) < ELF_HEADER_SIZE:
        return None, "ELF no alcanza el tamano de cabecera"
    if data[:4] != b"\x7fELF":
        return None, "no es un ELF (magic)"
    if data[4] != 2:
        return None, "no es ELF64 (clase=%d)" % data[4]
    if data[5] != 1:
        return None, "no es little-endian"
    e_type, e_machine = struct.unpack_from("<H H", data, 16)
    if e_machine != EM_X86_64:
        return None, "arquitectura no soportada: e_machine=%d" % e_machine
    if e_type != ET_REL:
        if e_type in (2, 3, 4):
            return None, ("formato no soportado en esta fase: e_type=%d "
                          "(solo ET_REL)" % e_type)
        return None, "e_type desconocido: %d" % e_type
    (e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize,
     e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = \
        struct.unpack_from("<I Q Q Q I H H H H H H", data, 20)
    if e_ehsize != ELF_HEADER_SIZE:
        return None, "e_ehsize inesperado: %d" % e_ehsize
    return {
        "e_type": e_type, "e_machine": e_machine, "e_version": e_version,
        "e_entry": e_entry, "e_phoff": e_phoff, "e_shoff": e_shoff,
        "e_flags": e_flags, "e_ehsize": e_ehsize, "e_phentsize": e_phentsize,
        "e_phnum": e_phnum, "e_shentsize": e_shentsize, "e_shnum": e_shnum,
        "e_shstrndx": e_shstrndx,
    }, None


def _validar_shoff(data: bytes, header: Dict[str, Any]):
    n = header["e_shnum"]
    if n == 0:
        return (None, "numeracion extendida (e_shnum=0, SHN_XINDEX) "
                      "no soportada")
    if header["e_shentsize"] != SHDR64_SIZE:
        return None, "e_shentsize inesperado: %d" % header["e_shentsize"]
    if header["e_shstrndx"] == SHN_XINDEX:
        return None, "SHN_XINDEX en e_shstrndx: no soportado"
    fin = header["e_shoff"] + header["e_shentsize"] * n
    if header["e_shoff"] <= 0 or fin > len(data):
        return None, ("e_shoff + e_shentsize*e_shnum fuera del "
                      "artefacto (%d > %d)" % (fin, len(data)))
    return list(range(n)), None


def identify_evidence(path: str, max_bytes: int = 64 * 1024 * 1024) -> Dict[str, Any]:
    """Identifica el artefacto y produce evidencia estructurada.

    Nunca ejecuta los bytes. Nunca consulta un adapter. Un artefacto
    fuera de alcance es BLOCKED, no EMPTY.
    """
    motivo, meta = _precondition(path, max_bytes)
    base = {
        "operational_status": OP_BLOCKED if motivo else OP_PASS,
        "epistemic_status": EP_BLOCKED if motivo else EP_NOT_DETERMINED,
        "comparison_status": CMP_INCONCLUSIVE,
        "limitations": [],
    }
    if motivo:
        base.update(operational_status=OP_BLOCKED, epistemic_status=EP_BLOCKED,
                    limitations=[motivo])
        return base
    try:
        data = open(path, "rb").read()
    except OSError as exc:
        base.update(operational_status=OP_ERROR, epistemic_status=EP_NOT_DETERMINED,
                    limitations=["lectura del artefacto fallo: %s" % exc])
        return base

    base["artifact_sha256"] = sha256_de_path(path)
    base["artifact_size"] = len(data)

    header, motivo = _validar_elf64(data)
    if motivo:
        base.update(operational_status=OP_BLOCKED, epistemic_status=EP_BLOCKED,
                    limitations=[motivo])
        return base
    base["elf_header"] = dict(header)

    indices, motivo = _validar_shoff(data, header)
    if motivo:
        base.update(operational_status=OP_BLOCKED, epistemic_status=EP_BLOCKED,
                    limitations=[motivo])
        return base

    # --- secciones ------------------------------------------------------
    sections = []
    for i in indices:
        off = header["e_shoff"] + i * header["e_shentsize"]
        vals = struct.unpack_from("<I I Q Q Q Q I I Q Q", data, off)
        (sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size,
         sh_link, sh_info, sh_addralign, sh_entsize) = vals
        sections.append({
            "index": i, "sh_name_raw": sh_name, "sh_type": sh_type,
            "sh_addr": sh_addr, "sh_offset": sh_offset, "sh_size": sh_size,
            "sh_entsize": sh_entsize, "sh_link": sh_link, "sh_info": sh_info,
            "sh_flags": {"write": bool(sh_flags & SHF_WRITE),
                         "alloc": bool(sh_flags & SHF_ALLOC),
                         "execinstr": bool(sh_flags & SHF_EXECINSTR)},
            "align": sh_addralign,
        })

    # --- shstrtab: nombres de seccion -----------------------------------
    shstr = header["e_shstrndx"]
    if shstr >= len(sections):
        base.update(operational_status=OP_BLOCKED,
                    limitations=["e_shstrndx fuera de rango (%d)" % shstr])
        return base
    nombre_off, nombre_size = sections[shstr]["sh_offset"], sections[shstr]["sh_size"]
    if SHT_PROGBITS != sections[shstr]["sh_type"] and sections[shstr]["sh_type"] != SHT_STRTAB:
        pass  # shstrtab es STRTAB en la practica; se intenta leer igual
    if nombre_off + nombre_size > len(data):
        base.update(operational_status=OP_BLOCKED,
                    limitations=["shstrtab fuera del artefacto"])
        return base
    shstrtab = data[nombre_off:nombre_off + nombre_size]
    for sec in sections:
        sec["name"] = _leer_cstr(shstrtab, sec["sh_name_raw"])
        sec.pop("sh_name_raw")

    # --- contenido/limites por seccion ----------------------------------
    for sec in sections:
        if sec["sh_type"] == SHT_NOBITS:
            sec["has_bytes"] = False
            continue
        if sec["sh_offset"] + sec["sh_size"] > len(data):
            base.update(operational_status=OP_BLOCKED,
                        limitations=["seccion %r fuera del artefacto "
                                     "(offset+size)" % sec["name"]])
            return base
        sec["has_bytes"] = True

    # --- simbolos ---------------------------------------------------------
    symbols = []
    for sec in sections:
        if sec["sh_type"] not in (SHT_SYMTAB, SHT_DYNSYM):
            continue
        if sec["sh_entsize"] != SYM64_SIZE:
            base.update(operational_status=OP_BLOCKED,
                        limitations=["st_entsize inesperado en %r" % sec["name"]])
            return base
        if not sec["has_bytes"]:
            base.update(operational_status=OP_BLOCKED,
                        limitations=["tabla de simbolos NOBITS: %r" % sec["name"]])
            return base
        link = sec["sh_link"]
        if link >= len(sections):
            base.update(operational_status=OP_BLOCKED,
                        limitations=["sh_link de la tabla de simbolos fuera de "
                                     "rango (%r)" % sec["name"]])
            return base
        strsec = sections[link]
        if strsec["sh_offset"] + strsec["sh_size"] > len(data):
            base.update(operational_status=OP_BLOCKED,
                        limitations=["strtab fuera del artefacto (tabla %r)"
                                     % sec["name"]])
            return base
        strtab = data[strsec["sh_offset"]:strsec["sh_offset"] + strsec["sh_size"]]
        n = sec["sh_size"] // SYM64_SIZE
        for j in range(n):
            off = sec["sh_offset"] + j * SYM64_SIZE
            st_name, st_info, st_other, st_shndx, st_value, st_size = \
                struct.unpack_from("<I B B H Q Q", data, off)
            if st_shndx == SHN_XINDEX:
                base.update(operational_status=OP_BLOCKED,
                            limitations=["SHN_XINDEX en la tabla %r: no soportado"
                                         % sec["name"]])
                return base
            symbols.append({
                "index": j, "name": _leer_cstr(strtab, st_name),
                "st_info": st_info, "st_other": st_other,
                "st_shndx": st_shndx, "st_value": st_value,
                "st_size": st_size,
                "type": {0: "STT_NOTYPE", 1: "STT_OBJECT", 2: "STT_FUNC",
                         3: "STT_SECTION", 4: "STT_FILE"}.get(st_info & 0xF,
                                                              "STT_%d" % (st_info & 0xF)),
                "bind": {0: "LOCAL", 1: "GLOBAL", 2: "WEAK"}.get(st_info >> 4,
                                                                 "BIND_%d" % (st_info >> 4)),
                "symbol_table": "symtab" if sec["sh_type"] == SHT_SYMTAB else "dynsym",
                "symbol_source_section": sec["index"],
            })

    # --- relocations (RELA; REL rechazado) ---------------------------------
    relocations = []
    for sec in sections:
        if sec["sh_type"] == SHT_REL:
            base.update(operational_status=OP_BLOCKED,
                        limitations=["SHT_REL no soportado en %r: "
                                     "se exige RELA o rechazo explicito"
                                     % sec["name"]])
            return base
        if sec["sh_type"] != SHT_RELA:
            continue
        if sec["sh_entsize"] != RELA64_SIZE or not sec["has_bytes"]:
            base.update(operational_status=OP_BLOCKED,
                        limitations=["entradas RELA invalidas en %r"
                                     % sec["name"]])
            return base
        link = sec["sh_link"]
        if link >= len(sections):
            base.update(operational_status=OP_BLOCKED,
                        limitations=["sh_link de relocations fuera de rango"])
            return base
        target_idx = sec["sh_info"]
        if target_idx >= len(sections) or target_idx < 0:
            base.update(operational_status=OP_BLOCKED,
                        limitations=["sh_info de relocations fuera de rango"])
            return base
        tsec = sections[target_idx]
        n = sec["sh_size"] // RELA64_SIZE
        for j in range(n):
            off = sec["sh_offset"] + j * RELA64_SIZE
            r_offset, r_info, r_addend = struct.unpack_from("<Q Q q", data, off)
            r_sym = r_info >> 32
            r_type = r_info & 0xFFFFFFFF
            if tsec["has_bytes"] and r_offset + 8 > tsec["sh_size"] + 8:
                pass  # r_offset protege contenido del target: verificado abajo
            if tsec["has_bytes"] and r_offset > tsec["sh_size"]:
                base.update(operational_status=OP_BLOCKED,
                            limitations=["relocation con r_offset=%#x excede "
                                         "la seccion objetivo %r (size %#x)"
                                         % (r_offset, tsec["name"], tsec["sh_size"])])
                return base
            relocations.append({
                "source_section_index": sec["index"],
                "source_section_name": sec["name"],
                "target_section_index": target_idx,
                "target_section_name": tsec["name"],
                "r_offset": r_offset, "r_info": r_info, "r_type": r_type,
                "r_sym": r_sym, "r_addend": r_addend,
            })

    base["sections"] = sections
    base["symbols"] = symbols
    base["relocations"] = relocations

    # --- decodificacion (GNU objdump, proveedor independiente) ------------
    code_ranges = [
        {"section": s["index"], "section_name": s["name"],
         "start": 0, "end": s["sh_size"],
         "evidence": ["shf_execinstr"]}
        for s in sections if s["sh_flags"]["execinstr"] and s["sh_size"] > 0
    ]
    if not code_ranges:
        # ET_REL valido sin rangos de codigo (p.ej. objeto vacio): no es un
        # fallo del decodificador ni un artefacto no soportado.
        base["instructions"] = []
        insn_out = {"ok": True, "instructions": [],
                    "decoder": None, "decoder_version": None,
                    "sin_rangos_codigo": True}
        base["limitations"] = base.get("limitations", []) + [
            "artefacto sin rangos de codigo declarados: nada que decodificar"]
        decoded = []
        base["instruction_coverage"] = {
            "declared_code_ranges": [], "decoded_ranges": [],
            "undecoded_ranges": [],
            "data_ranges": [
                {"section": s["index"], "section_name": s["name"],
                 "start": 0, "end": s["sh_size"],
                 "evidence": ["no-shf_execinstr"]}
                for s in sections if not s["sh_flags"]["execinstr"] and s["sh_size"] > 0
            ],
            "unknown_ranges": [], "coverage_ratio": None,
        }
    else:
        insn_out = decode_with_objdump(path)
    if insn_out["ok"]:
        insns = _attach_bytes_and_sizes(data, sections, insn_out["instructions"])
        base["instructions"] = insns
        decoded = _union_ranges([
            {"section": i["section"], "start": i["offset"],
             "end": i["offset"] + i["size"]} for i in insns
        ])
    else:
        base.update(operational_status=OP_ERROR,
                    limitations=base.get("limitations", []) + [insn_out["motivo"]])
        base["instructions"] = []
        decoded = []

    declared_union = _union_ranges([
        {"section": r["section"], "start": r["start"], "end": r["end"]}
        for r in code_ranges])
    deco = _range_intersect_subtract(decoded, declared_union)
    ratio = _coverage_ratio(_range_intersect(decoded, declared_union), declared_union)
    base["instruction_coverage"] = {
        "declared_code_ranges": code_ranges,
        "decoded_ranges": _clip_to(decoded, declared_union),
        "undecoded_ranges": deco,
        "data_ranges": [
            {"section": s["index"], "section_name": s["name"],
             "start": 0, "end": s["sh_size"],
             "evidence": ["no-shf_execinstr"]}
            for s in sections if not s["sh_flags"]["execinstr"] and s["sh_size"] > 0
        ],
        "unknown_ranges": [],
        "coverage_ratio": ratio,
    }
    if not insn_out["ok"]:
        base["limitations"].append(
            "instrucciones no decodificadas: cobertura no computable")

    base["provenance"] = {
        "artifact_sha256": base["artifact_sha256"],
        "artifact_size": base["artifact_size"],
        "parser": "binexpr-internal",
        "parser_revision": MODULE_REVISION,
        "decoder": insn_out.get("decoder"),
        "decoder_version": insn_out.get("decoder_version"),
        "executable_hash": insn_out.get("executable_hash"),
        "created_by": "ier/binexpr.py %s" % MODULE_REVISION,
    }
    base["hash"] = {
        "H_artifact": H_artifact(path),
        "H_evidence": H_evidence({k: v for k, v in base.items()
                                  if k not in ("provenance", "hash")}),
    }
    return base


def is_supported(path: str) -> bool:
    return identify_evidence(path)["operational_status"] == OP_PASS


# --- decodificacion objdump -------------------------------------------------
_INSN_START_RE = re.compile(
    r"^\s*([0-9a-fA-F]+):\t((?:[0-9a-fA-F]{2}[ \t]*)+)(?:\t(\S+)\s*(.*))?$")


def _objdump_bin() -> Optional[str]:
    for d in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(d, "objdump")
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _objdump_version(exe: str) -> str:
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True,
                           timeout=30)
        m = re.search(r"\d+\.\d+(?:\.\d+)?", (p.stdout or p.stderr or ""))
        return m.group(0) if m else "unknown"
    except Exception:
        return "unknown"


def decode_with_objdump(path: str) -> Dict[str, Any]:
    """Mnemonics/operandos/offsets via objdump. NO impone size ni bytes.

    objdump envuelve la columna de bytes cuando una instruccion ocupa mas
    de 7 bytes (p.ej. `mov 0x0(,%rax,8),%rax`): los bytes finales quedan
    en una linea-sin-mnemonico. Este parser acumula esas continuaciones y
    entrega `byte_count` por instruccion (suma real de bytes mostrados),
    sin confundirlas con instrucciones nuevas. El TAMANO definitivo se
    calcula por delta entre offsets en identify_evidence: los bytes se
    leen del ELF propio (fuente de verdad), no de la salida del decodificador.
    """
    exe = _objdump_bin()
    if not exe:
        return {"ok": False, "motivo": "binexpr: objdump no disponible en PATH"}
    env = dict(os.environ, LC_ALL="C")
    try:
        p = subprocess.run([exe, "-d", path], capture_output=True, text=True,
                           timeout=120, env=env)
    except subprocess.TimeoutExpired:
        return {"ok": False, "motivo": "binexpr: objdump timeout"}
    except OSError as exc:
        return {"ok": False, "motivo": "binexpr: objdump fallo: %s" % exc}
    out = (p.stdout or "")
    version = _objdump_version(exe)
    instructions = []
    cur_section_name = None
    # estado del acumulador de instruccion abierta
    pend_offset = None
    pend_bytes = ""
    pend_mnemonic = None
    pend_operands = None

    def flush():
        nonlocal pend_offset, pend_bytes, pend_mnemonic, pend_operands
        if pend_offset is not None:
            instructions.append({
                "section_name": cur_section_name or ".text",
                "offset": pend_offset,
                "objdump_byte_count": len(pend_bytes) // 2,
                "mnemonic": (pend_mnemonic or "").lower(),
                "operands": (pend_operands or "").strip(),
                "decoded_by": "GNU objdump %s" % version,
                "decoder_version": version,
            })
        pend_offset, pend_bytes = None, ""
        pend_mnemonic, pend_operands = None, None

    for line in out.splitlines():
        msec = re.match(r"^(?:Disassembly|desensamblado) of (?:section|la sección)\s*\.?(\S+):$",
                        line.strip(), re.IGNORECASE)
        if msec:
            flush()
            cur_section_name = msec.group(1).rstrip(":")
            continue
        m = _INSN_START_RE.match(line)
        if not m:
            continue
        off_s, bytes_s, mnemonic, operands = m.groups()
        off = int(off_s, 16)
        raw = re.sub(r"\s+", "", bytes_s).lower()
        if mnemonic is not None:
            # nueva instruccion: cerrar la anterior
            flush()
            pend_offset, pend_bytes = off, raw
            pend_mnemonic, pend_operands = mnemonic, operands
        else:
            # linea-continuacion de bytes de la instruccion abierta
            if pend_offset is None or off != pend_offset + len(pend_bytes) // 2:
                # hueco inesperado: no podemos atribuir
                flush()
                continue
            pend_bytes += raw
    flush()

    if not instructions:
        return {"ok": False, "motivo": "binexpr: objdump no produjo instrucciones",
                "decoder": "objdump", "decoder_version": version,
                "executable_hash": H_artifact(exe)}
    return {"ok": True, "instructions": _assign_section_indices(path, instructions),
            "decoder": "GNU objdump", "decoder_version": version,
            "executable_hash": H_artifact(exe)}


def _attach_bytes_and_sizes(data: bytes, sections: List[Dict[str, Any]],
                            instructions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Asigna size y bytes definitivos desde el ELF (fuente de verdad).

    size_i = offset_{i+1} - offset_i (misma seccion); ultima insn de la
    seccion: size = sh_size - offset_i. bytes = slice real del fichero.
    Si el contador de bytes de objdump no cuadra con el delta, la
    instruccion se marca `bytes_mismatch` (desnivel) sin alterar el size
    computado: la cobertura se calcula sobre bytes reales del fichero.
    """
    by_sec: Dict[int, List[Dict[str, Any]]] = {}
    for ins in instructions:
        by_sec.setdefault(ins["section"], []).append(ins)
    sec_map = {s["index"]: s for s in sections}
    for sec_index, lst in by_sec.items():
        lst.sort(key=lambda i: i["offset"])
        sec = sec_map.get(sec_index)
        sec_size = sec["sh_size"] if sec else 0
        sec_file_off = sec["sh_offset"] if sec else 0
        for i, ins in enumerate(lst):
            if i + 1 < len(lst):
                size = lst[i + 1]["offset"] - ins["offset"]
            else:
                size = sec_size - ins["offset"]
            ins = dict(ins)
            ins["size"] = max(size, 0)
            ins["bytes"] = data[sec_file_off + ins["offset"]:
                                sec_file_off + ins["offset"] + ins["size"]].hex() \
                if ins["size"] > 0 else ""
            ob = ins.get("objdump_byte_count")
            if ob is not None and ob != ins["size"]:
                ins["decoder_note"] = ("objdump mostro %d bytes pero el delta es %d; "
                                       "se computa sobre el ELF" % (ob, ins["size"]))
            ins.pop("objdump_byte_count", None)
            lst[i] = ins
    return [ins for lst in by_sec.values() for ins in lst]


def _assign_section_indices(path: str, instructions: List[Dict[str, Any]]):
    """Asigna indice de seccion a cada instruccion leida del propio ELF."""
    _ = instructions
    ev = _raw_section_map(path)
    out = []
    for insn in instructions:
        name = insn.get("section_name") or ".text"
        idx = ev.get("." + name if not name.startswith(".") else name,
                     ev.get(name, ev.get(".text")))
        insn = dict(insn)
        insn["section"] = idx
        out.append(insn)
    return out


def _raw_section_map(path: str) -> Dict[str, int]:
    data = open(path, "rb").read()
    header, motivo = _validar_elf64(data)
    if motivo:
        return {".text": 0}
    n = header["e_shnum"]
    mapping: Dict[str, int] = {}
    secs = []
    for i in range(n):
        off = header["e_shoff"] + i * SHDR64_SIZE
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, \
            sh_link, sh_info, sh_addralign, sh_entsize = \
            struct.unpack_from("<I I Q Q Q Q I I Q Q", data, off)
        secs.append((i, sh_name, sh_type, sh_offset, sh_size))
    shstr = header["e_shstrndx"]
    if shstr < len(secs):
        sh_off, sh_size = secs[shstr][3], secs[shstr][4]
        shstrtab = data[sh_off:sh_off + sh_size]
        for i, sh_name, _t, _o, _s in secs:
            mapping[_leer_cstr(shstrtab, sh_name)] = i
    return mapping or {".text": 0}


# --- rangos -----------------------------------------------------------------
def _union_ranges(dom):
    por_seccion: Dict[int, List[Tuple[int, int]]] = {}
    for r in dom:
        por_seccion.setdefault(r["section"], []).append((r["start"], r["end"]))
    out = []
    for sec, rngs in por_seccion.items():
        rngs.sort()
        cur_s, cur_e = None, None
        for s, e in rngs:
            if cur_s is None:
                cur_s, cur_e = s, e
                continue
            if s <= cur_e:
                cur_e = max(cur_e, e)
            else:
                out.append({"section": sec, "start": cur_s, "end": cur_e})
                cur_s, cur_e = s, e
        if cur_s is not None:
            out.append({"section": sec, "start": cur_s, "end": cur_e})
    return out


def _range_intersect(a, b):
    out = []
    por_sec_b: Dict[int, List[Tuple[int, int]]] = {}
    for r in b:
        por_sec_b.setdefault(r["section"], []).append((r["start"], r["end"]))
    for ra in a:
        for sb, eb in por_sec_b.get(ra["section"], []):
            s, e = max(ra["start"], sb), min(ra["end"], eb)
            if s < e:
                out.append({"section": ra["section"], "start": s, "end": e})
    return out


def _range_intersect_subtract(decoded, declared):
    """declared menos decoded: rangos sin decodificar."""
    out = []
    dec_flat: Dict[int, List[Tuple[int, int]]] = {}
    for r in decoded:
        dec_flat.setdefault(r["section"], []).append((r["start"], r["end"]))
    for rd in declared:
        sec = rd["section"]
        piezas = [(rd["start"], rd["end"])]
        for s, e in dec_flat.get(sec, []):
            nuevas = []
            for ps, pe in piezas:
                if e <= ps or s >= pe:
                    nuevas.append((ps, pe))
                    continue
                if ps < s:
                    nuevas.append((ps, s))
                if pe > e:
                    nuevas.append((e, pe))
            piezas = nuevas
        for ps, pe in piezas:
            out.append({"section": sec, "start": ps, "end": pe,
                        "reason": "sin bytes decodificados"})
    return out


def _clip_to(decoded, declared):
    return _range_intersect(decoded, declared)


def _coverage_ratio(intersection, declared) -> Optional[float]:
    total = sum(r["end"] - r["start"] for r in declared)
    if total == 0:
        return None
    cub = sum(r["end"] - r["start"] for r in intersection)
    return round(cub / total, 6)
