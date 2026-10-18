# SPDX-License-Identifier: GPL-2.0
"""`binary.disassemble` y `binary.disassemble_func` sobre Capstone. RXRE-1634.

## POR QUE UN PRODUCTOR EN PROCESO Y NO UN SUBCOLECTO

MEDIDO 2026-10-12 sobre /usr/bin/rizin, rizin 0.7.4:

    `aa; pdj 8 @ main`   -> JSON con 8 instrucciones   FUNCIONA
    `aa; pdfj @ main`    -> NO emite JSON              FALLA

El JSON existe para un rango corto y no para una funcion entera. Es
justo el caso que hace falta para analizar algo: un CFG, un descompilado
manual, una busqueda de accesos a un registro.

Capstone 5.0.7 esta YA INSTALADO en este sistema
(`/home/lucas/.local/lib/python3.14/site-packages/capstone`), asi que
adquirir esta capacidad costo cero. MEDIDO: 158 000 instrucciones/s con
`detail=True` sobre x86-64, y en proceso evita el coste de arrancar un
subproceso y el parseo de su JSON.

## LA COBERTURA ES EL DATO IMPORTANTE, NO EL RECUENTO

MEDIDO 2026-10-12: si se pide el rango que declara el productor,
Capstone cubre el 100 % de una funcion `sym` de 909 bytes (228
instrucciones). Pero sobre una entrada `type:"fcn"` con `size` 137 solo
cubrio el 9,5 %: **Capstone se detiene en el primer byte que no puede
decodificar y no dice donde**.

Por eso este adapter NO devuelve "N instrucciones". Devuelve, por
funcion:

    bytes_declarados, bytes_descubiertos, instrucciones, cobertura_pct,
   primer_hueco

Un recuento sin cobertura es una afirmacion que no se sostiene: 4
instrucciones pueden ser una funcion corta o el principio de una larga
con datos en medio. Quien consume necesita saber cual de las dos.

## LO QUE ESTO NO ES

Un desensamblado NO es un descompilado. No hay estructura de control, ni
nombres, ni tipos. `DISASSEMBLY` esta por debajo de `FUNCTION_CANDIDATE`
en la escalera de confianza del contrato, y `puede_declarar` lo impide
promoverlo a nada mas.

Tampoco es un Capstone para la GPU. Capstone 5.0.7 no cubre GFX8; esta
capacidad es para codigo x86-64, que es lo que necesita el modulo del
kernel (`amdgpu.ko` es un objeto x86-64 ET_REL). Para GFX8 haria falta
otro producer, y no se declara aqui.
"""
from __future__ import annotations

import os
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    DISASSEMBLY, sha256_de, sha256_texto, estado_firma,
)
from . import provenance as _prov

#: MEDIDO 2026-10-12 en este host.
CAPSTONE_MEDIDO = {
    "fecha": "2026-10-12",
    "version": "5.0.7", "cs_version": "5, 0, 1280",
    "rendimiento": "~158000 instr/s en x86-64 con detail=True",
    "instalado_en": "/home/lucas/.local/lib/python3.14/site-packages/"
                    "capstone",
    "nota": "ya instalado antes de este lote: adquirir la capacidad costo 0",
}

GRUPOS = {
    1: "JUMP", 2: "CALL", 3: "RET", 4: "INT", 5: "IRET", 6: "PRIVILEGE",
    7: "BRANCH_RELATIVE",
}

try:
    import capstone as _cs
    CAPSTONE_DISPONIBLE = True
except ImportError:
    _cs = None
    CAPSTONE_DISPONIBLE = False


def _elf_tipo(ruta: str) -> str:
    try:
        with open(ruta, "rb") as fh:
            h = fh.read(20)
    except OSError:
        return ""
    if len(h) < 18 or h[:4] != b"\x7fELF":
        return ""
    fmt = "<H" if h[5] == 1 else ">H"
    (e_type,) = struct.unpack_from(fmt, h, 16)
    return {1: "ET_REL", 2: "ET_EXEC", 3: "ET_DYN",
            4: "ET_CORE"}.get(e_type, "ET_%d" % e_type)


def disponible() -> Dict[str, Any]:
    """El producer existe y.VERSION medida. Distinto de 'esta integrado'."""
    d = {"existe": CAPSTONE_DISPONIBLE, "modulo": "capstone",
         "version": "", "cs_version": "", "cs_modes_disponibles": []}
    if not CAPSTONE_DISPONIBLE:
        d["motivo"] = ("capstone no esta importable desde este "
                       "interpretor. Un checkout NO es una instalacion.")
        return d
    d["version"] = getattr(_cs, "__version__", "?")
    try:
        d["cs_version"] = ".".join(str(x) for x in _cs.cs_version())
    except Exception:
        pass
    d["cs_modes_disponibles"] = [n for n in dir(_cs)
                                 if n.startswith("CS_MODE_")]
    return d


def _operandos(ins, cs) -> List[Dict[str, Any]]:
    """Operando con su TIPO, no solo su texto.

    MEDIDO: `op_str` es texto y no permite saber si un `0x10` es un
    inmediato o el desplazamiento de un acceso a memoria. Esa
    distincion es la que separa "mover un valor" de "leer/escribir en
    una direccion", y sin ella el consumidor tiene que adivinar.
    """
    out = []
    try:
        ops = ins.operands
    except Exception:
        return out
    for o in ops:
        t = o.type
        if t == cs.x86.X86_OP_REG:
            out.append({"tipo": "reg", "reg": ins.reg_name(o.reg)})
        elif t == cs.x86.X86_OP_IMM:
            out.append({"tipo": "imm", "valor": o.imm})
        elif t == cs.x86.X86_OP_MEM:
            out.append({"tipo": "mem",
                        "base": (ins.reg_name(o.mem.base)
                                 if o.mem.base else ""),
                        "indice": (ins.reg_name(o.mem.index)
                                   if o.mem.index else ""),
                        "desplazamiento": o.mem.disp,
                        "escala": o.mem.scale,
                        "segmento": o.mem.segment})
        else:
            out.append({"tipo": "tipo%d" % t})
    return out


def _grupos(ins) -> List[str]:
    """Clase de la instruccion: salto, llamada, retorno, interrupcion.

    Es lo que permite construir un CFG sin depender de un productor que
    no emita JSON. MEDIDO 2026-10-12: `agCj` y `agf` no dan JSON en rizin
    ni en radare2, asi que esta es la via disponible.
    """
    try:
        g = ins.groups_count
    except Exception:
        return []
    return [GRUPOS.get(x, "grupo%d" % x)
            for x in (ins.groups or [])]


def desensamblar(artefacto: str, inicio: int = 0, longitud: int = 0,
                 arquitectura: str = "x86_64",
                 timeout: int = 0,
                 fixture_bin: str = "",
                 backend_id: str = "capstone") -> Dict[str, Any]:
    """Desensambla un rango del fichero y DECLARA lo que cubrio.

    `backend_id` lo inyecta el dispatch con el `backend_por_defecto` de la
    capacidad. Se ACEPTA y se COMPRUEBA en vez de ignorarse: si alguien
    invoca esta capacidad pidiendo `backend_id="rizin"`, esta no es su
    producer y la respuesta tiene que decirlo, no devolver un resultado de
    Capstone etiquetado como si fuera de otro. Es el mismo principio que
    en `rz_functions`: el envelope declara QUE producer produjo el
    resultado, y aqui ademas que el pedido coincide con el.
    """
    if backend_id != "capstone":
        return {"status": BK_INVALID,
                "precheck": {"ok": False, "backend_id": backend_id},
                "limitations": [
                    "backend %r no puede servir esta capacidad: su unico "
                    "producer es `capstone` (modulo en proceso). Pedir %r "
                    "devolveria un resultado de Capstone con la etiqueta "
                    "equivocada." % (backend_id, backend_id)]}
    if not CAPSTONE_DISPONIBLE:
        return {"status": BK_BLOCKED,
                "limitations": ["capstone no esta importable: %s"
                                % disponible().get("motivo", "")]}

    d = disponible()
    pre = {"input_existe": os.path.isfile(artefacto) or bool(fixture_bin),
           "elf_tipo": "", "input_hash": "", "capstone": d,
           "ok": False}

    ruta = fixture_bin or artefacto
    if not pre["input_existe"]:
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": ["la entrada no existe: %s" % ruta]}
    if not fixture_bin:
        if os.path.isfile(artefacto) and estado_firma(artefacto) == "no_legible":
            pre["elf_tipo"] = ""
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [
                        "la entrada EXISTE pero no es legible "
                        "(permiso o E/S): %s" % artefacto,
                        "no se pudo leer la firma: NO se sabe si es ELF",
                        "no se desensamblo: se leen bytes, pero el rango "
                        "que se pide debe viene de un analisis previo"]}
        pre["elf_tipo"] = _elf_tipo(artefacto)
        if not pre["elf_tipo"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [
                        "la entrada no es un ELF: %s" % artefacto,
                        "no se desensamblo: se leen bytes, pero el rango "
                        "que se pide debe viene de un analisis previo"]}
    try:
        with open(ruta, "rb") as fh:
            total = os.fstat(fh.fileno()).st_size
            fh.seek(inicio)
            bruto = fh.read(longitud) if longitud else fh.read()
    except OSError as exc:
        return {"status": BK_ERROR, "precheck": pre,
                "limitations": ["no se pudo leer: %s" % exc]}

    if not bruto:
        return {"status": BK_EMPTY, "precheck": pre,
                "limitations": ["el rango pedido esta vacio (offset %d, "
                                "longitud %d, fichero de %d bytes)"
                                % (inicio, longitud, total)]}
    pre["input_hash"] = sha256_de(ruta)
    pre["ok"] = True

    if arquitectura == "x86_64":
        arch, mode = _cs.CS_ARCH_X86, _cs.CS_MODE_64
    elif arquitectura == "x86":
        arch, mode = _cs.CS_ARCH_X86, _cs.CS_MODE_32
    elif arquitectura == "arm64":
        arch, mode = _cs.CS_ARCH_ARM64, _cs.CS_MODE_ARM
    else:
        # `unsupported` y no `error`: el adapter funciona, lo que no se
        # soporta es ESTA arquitectura. Es justo la distincion que el
        # contrato exige y que se confunde en el otro sentido - decir
        # `error` implicaria que algo fallo.
        return {"status": BK_UNSUPPORTED,
                "precheck": pre,
                "limitations": [
                    "arquitectura no soportada por este adapter: %r" % arquitectura,
                    "este adapter cubre x86, x86_64 y arm64. Añadir otra "
                    "arquitectura es trabajo propio, no un parametro: "
                    "cambia como se decodifican operandos y nombres."]}

    md = _cs.Cs(arch, mode)
    md.detail = True
    t0 = time.time()
    insns = list(md.disasm(bruto, inicio))
    dur = round(time.time() - t0, 6)

    n = len(insns)
    cubiertos = sum(i.size for i in insns)
    declarados = len(bruto)
    # El hueco: Capstone para en el primer byte indecodificable y no lo
    # dice. Se localiza por el hueco entre la ultima instruccion y el fin.
    primer_hueco = None
    if insns:
        fin_ultimo = insns[-1].address + insns[-1].size
        if cubiertos < declarados:
            primer_hueco = fin_ultimo
    # Y los huecos INTERNOS: el consumidor los necesita porque un CFG no
    # puede tener una arista que atraviese un hueco sin saberlo.
    huecos = []
    prev = inicio
    for i in insns:
        if i.address > prev:
            huecos.append({"desde": prev, "hasta": i.address,
                           "bytes": i.address - prev})
        prev = i.address + i.size
    if prev < inicio + declarados:
        huecos.append({"desde": prev, "hasta": inicio + declarados,
                       "bytes": inicio + declarados - prev})

    pct = round(100.0 * cubiertos / declarados, 2) if declarados else 0.0
    instr = [{
        "direccion": i.address, "tam": i.size, "mnemonico": i.mnemonic,
        "op_str": i.op_str, "id": i.id,
        "operandos": _operandos(i, _cs),
        "grupos": _grupos(i),
        "crudo": {"bytes": i.bytes.hex()},
    } for i in insns]

    lim = [
        "un desensamblado NO es un descompilado: no hay estructura de "
        "control, ni nombres, ni tipos. El tipo del contrato lo separa "
        "(DISASSEMBLY esta por debajo de FUNCTION_CANDIDATE y `puede_declarar` "
        "no lo deja ascender).",
        "COBERTURA %0.2f%% (%d de %d bytes). Capstone se detiene en el "
        "primer byte que no decodifica y NO dice cual es: por eso se "
        "declaran `huecos` y `primer_hueco`, y por eso un recuento de "
        "instrucciones sin cobertura no es un resultado." % (pct, cubiertos,
                                                             declarados),
        "Capstone 5.0.7 no cubre GFX8. Esta capacidad es para x86-64, que "
        "es lo que necesita un modulo de kernel (`amdgpu.ko` es ET_REL "
        "x86-64). Para la GPU haria falta otro producer.",
        "el rango lo elige quien llama: este adapter NO descubre funciones. "
        "Combinar con `binary.functions` (aflj) para obtener los offsets.",
        "MEDIDO: %s." % d["version"],
    ]
    if not insns:
        lim.append("0 instrucciones sobre un rango NO vacio. Eso NO prueba "
                   "que no haya codigo: el rango puede estar en datos, o "
                   "ser una arquitectura distinta. El rango y su Tamano "
                   "los decidio quien llama.")
        ejec = {"operation": "binary.disassemble", "backend_id": "capstone",
                "command_or_api": "capstone (en proceso, sin subproceso)",
                "argv": [], "exit_status": 0, "duration_s": dur,
                "timeout": False, "stderr": ""}
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "results": [], "n_instrucciones": 0, "cobertura": {
                    "bytes_declarados": declarados, "bytes_descubiertos": 0,
                    "cobertura_pct": 0.0, "huecos": huecos,
                    "primer_hueco": inicio},
                "limitations": lim, "provenance": _prov.desde_precheck(pre, transformacion='capstone -> desensamblado lineal; bytes_descubiertos contra bytes_declarados -> cobertura_pct', normalizador='backends.adapters.cs_disasm.desensamblar'),
                "capstone_medido": CAPSTONE_MEDIDO}

    ref = ruta
    res = {
        "result_id": "res_disasm_" + sha256_texto(
            "%s|%d|%d|%s" % (ref, inicio, declarados, arquitectura))[:12],
        "type": DISASSEMBLY,
        "value": {"arquitectura": arquitectura, "offset_inicio": inicio,
                  "n_instrucciones": n,
                  "cobertura": {"bytes_declarados": declarados,
                                "bytes_descubiertos": cubiertos,
                                "cobertura_pct": pct,
                                "huecos": huecos[:200],
                                "primer_hueco": primer_hueco},
                  "instrucciones": instr[:4000]},
        "completitud": {"completo": len(instr) <= 4000,
                        "omitidos": max(0, len(instr) - 4000),
                        "limite": 4000,
                        "elemento": "instrucciones"},
        "completitud_anidada": {"huecos": {"completo": len(huecos) <= 200,
                                           "omitidos": max(0, len(huecos) - 200),
                                           "limite": 200}},
        "source": ref, "location": {"file": os.path.basename(ref)},
        "scope": "binary", "tool": "capstone",
        "tool_version": d["version"],
        "input": {"path": ref, "sha256": pre["input_hash"]},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": ref, "artifact_hash": pre["input_hash"],
        "status": "declared", "limitations": lim, "duration_s": dur,
    }
    ejec = {"operation": "binary.disassemble", "backend_id": "capstone",
            "command_or_api": "capstone (en proceso, sin subproceso)",
            "argv": [], "exit_status": 0, "duration_s": dur,
            "timeout": False, "stderr": "",
            "nota": "producer EN PROCESO: por eso argv va vacio y no hay "
                    "subproceso que medir"}
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "results": [res], "n_instrucciones": n,
            "cobertura": res["value"]["cobertura"],
            "limitations": lim, "provenance": _prov.desde_precheck(pre, transformacion='capstone -> desensamblado lineal; bytes_descubiertos contra bytes_declarados -> cobertura_pct', normalizador='backends.adapters.cs_disasm.desensamblar'),
            "capstone_medido": CAPSTONE_MEDIDO}
