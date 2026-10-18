#!/usr/bin/env python3
# CONTRACT: name=rxre_register_fields
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
"""
rxre_register_fields.py — extrai todos os campos de um registro a partir de
*_sh_mask.h, selecionados com base na IDENTIDADE RESOLVIDA do registro.

Por que existe
--------------
O registro `reg_resolve.py` resolve um mm* para sua identidade fisica: token,
bloqueio IP, deslocamento e geracao (ex.: mmVM_CONTEXT0_CNTL → offset 0x504,
bloqueio GMC, geracao GFX8, definido em `gmc/gmc_8_1_d.h`).

Mas `rxre_register_fields` nunca usava essa identidade: varria **todos** os
arquivos *_sh_mask.h e pegava o PRIMEIRO que continha o registro. Como varias
geracoes definem o mesmo registro (ex.: gmc/gmc_8_1_sh_mask.h e
gmc/gmc_8_2_sh_mask.h definem VM_CONTEXT0_CNTL), isso podia selecionar campos
de uma geracao INCOMPATIVEL — 304 campos misturados de 15 cabeceras.

Este script corrige isso: ele aceita o contexto da identidade resolta e escolhe
o _sh_mask.h correspondente (mesmo bloqueio IP + mesma versao) em vez de
varrer tudo.

Como funciona a RELACAO registro → schema de campos
----------------------------------------------------
O kernel AMD define o layout de bits de um registro em `*_d.h` (definições do
registro) e as máscaras/deslocamentos dos campos em um _sh_mask.h da MESMA
versao e do MESMO bloco IP:

    drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c inclui:
        #include "gmc/gmc_8_1_d.h"
        #include "gmc/gmc_8_1_sh_mask.h"

Relação derivada da evidencia do corpus:
    gmc/gmc_8_1_d.h      →  gmc/gmc_8_1_sh_mask.h
    gca/gfx_8_0_d.h      →  gca/gfx_8_0_sh_mask.h
    gc/gfx_9_4_3_d.h     →  gc/gfx_9_4_3_sh_mask.h

A derivacao é feita a partir do nome do arquivo do _d.h escolhido (mesma
versao, mesma pasta, substituindo _d.h por _sh_mask.h), NAO por substituir
terminacao de string cega nem por buscare deslocamento numerico.

Uso
---
    # Sem contexto: comportamento antigo (fallback amplo, pode ser ambiguo)
    rxre_register_fields.py --kernel RAIZ --reg VM_CONTEXT0_CNTL --gfx gfx_8_0

    # Com resolucao de identidade (recomendado):
    rxre_register_fields.py --kernel RAIZ --reg VM_CONTEXT0_CNTL --gfx gfx_8_0
        --ip-block GMC --ip-version 8_1
    rxre_register_fields.py --kernel RAIZ --reg VM_CONTEXT0_CNTL --gfx gfx_8_0
        --resolved-header drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_8_1_d.h
    rxre_register_fields.py --kernel RAIZ --reg VM_CONTEXT0_CNTL --gfx gfx_8_0
        --resolved-json <(cat /tmp/vmcontext0_identity.json)
    rxre_register_fields.py --selftest

CONTRATO DE SAIDA (mantido; campos adicionais quando identico fornecida):
    {tool, version, register, gfx, fields: [...], field_count: int}
    Cada campo: field_name, mask, mask_value, shift, low_bit, high_bit,
    width, mask_is_positioned, mask_is_contiguous, header_file,
    field_line_mask, field_line_shift, field_macro_mask, field_macro_shift.
    Adicional (apenas quando identidade fornecida): identity_status,
    identity_ip_block, identity_generation, identity_chosen_header,
    identity_selection_evidence.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
Não abre /sys, não escreve em arquivos, não toca na GPU nem no sistema de arquivos.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence

NAME = "rxre_register_fields"
VERSION = "0.1.1"

ASIC_REG_DIR = os.path.join("include", "asic_reg")

# Mapeamento IP_BLOCK → diretório raiz de include/asic_reg (evidencia: o
# kernel coloca gca/{gfx}_*, gc/{gfx}_* e gmc/gmc_*_d.h + gmc/gmc_*_sh_mask.h).
IP_BLOCK_DIR = {
    "GCA": "gca",
    "GC": "gc",
    "GMC": "gmc",
    "MMHUB": "mmhub",
    "SDMA": "sdma",
}

# IP_BLOCK → prefixo de nome do arquivo de cabeca (evidencia: gca/gfx_8_0_d.h,
# gc/gfx_9_4_3_d.h, gmc/gmc_8_1_d.h). Usado para derivar o arquivo _sh_mask.h
# a partir de um ip_version como "8_1".
IP_BLOCK_GFX_PREFIX = {
    "GCA": "gfx",
    "GC": "gfx",
    "GMC": "gmc",
    "MMHUB": "mmhub",
    "SDMA": "sdma",
}

# Token → bloco IP quando o contexto nao determina o bloco IP.
TOKEN_IP_BLOCK_HINT = {
    # VM_CONTEXT* e GART* pertencem ao bloco GMC.
    "VM_CONTEXT0_CNTL": "GMC",
    "VM_CONTEXT0_CNTL2": "GMC",
    "VM_CONTEXT1_CNTL": "GMC",
    "VM_CONTEXT1_CNTL2": "GMC",
    "VM_CONTEXT0_PDE0_BASE": "GMC",
}

_define_re = re.compile(
    r"#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(0[xX][0-9a-fA-F]+|\d+)[uUlL]*\s*$"
)


def parse_int(tok: str) -> int:
    return int(tok, 16) if tok.lower().startswith("0x") else int(tok)


# ---------------------------------------------------------------------------
# Derivacao da cabecera _sh_mask.h a partir da identidade resolta.
# ---------------------------------------------------------------------------

def derive_sh_mask_header(resolved_d_header: str) -> Optional[str]:
    """Deriva o caminho do _sh_mask.h correspondente ao _d.h resolvido.

    Relacao evidenciada no corpus: gmc/gmc_8_1_d.h → gmc/gmc_8_1_sh_mask.h,
    gca/gfx_8_0_d.h → gca/gfx_8_0_sh_mask.h, etc.

    So faz a substituicao quando o nome do arquivo tem o padrao
    <prefixo>_<versao>_d.h e existe o arquivo homonimo com _sh_mask.h na
    mesma pasta. Se nao houver cabeca resolvida ou a cabeca de campos nao
    existir, devolve None.
    """
    if not resolved_d_header:
        return None

    d_path = resolved_d_header
    # Converter caminho relativo para absoluto.
    # Se for relativo, assumir que esta baseado no root do corpus RXRE.
    if not os.path.isabs(d_path):
        # Raiz do projeto: /home/lucas/Escritorio/rxre
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        d_path = os.path.normpath(os.path.join(project_root, d_path))

    filename = os.path.basename(d_path)
    if not filename.endswith("_d.h"):
        # Nem todo _d.h tem _sh_mask.h correspondente (offset.h nao tem).
        return None

    # Extrai prefixo e versao: gmc_8_1_d.h → prefixo=gmc, versao=8_1
    m = re.match(r"^([A-Za-z0-9_]+)_([A-Za-z0-9_]+)_d\.h$", filename)
    if not m:
        return None

    prefix = m.group(1)
    version = m.group(2)

    parent = os.path.dirname(d_path)
    mask_candidate = os.path.join(parent, f"{prefix}_{version}_sh_mask.h")
    if os.path.isfile(mask_candidate):
        return mask_candidate

    return None


def derive_sh_mask_by_ipblock(
    ip_block: str, ip_version: str, amd_root: str
) -> Optional[str]:
    """Deriva o _sh_mask.h a partir de ip_block + versao do IP.

    ip_block = "GMC", ip_version = "8_1"  →  .../asic_reg/gmc/gmc_8_1_sh_mask.h
    ip_block = "GCA", ip_version = "gfx_8_0" → .../asic_reg/gca/gfx_8_0_sh_mask.h
    """
    dirn = IP_BLOCK_DIR.get(ip_block.upper())
    if not dirn:
        return None

    # Determina o prefixo correto do nome do arquivo (evidencia: gca/gfx_8_0_*,
    # gc/gfx_9_4_3_*, gmc/gmc_8_1_*). GCA/GC usam "gfx", GMC/MMHUB/SDMA usam
    # o nome do bloco IP em minusculo.
    file_prefix = IP_BLOCK_GFX_PREFIX.get(ip_block.upper(), dirn.lower())

    if "_" in ip_version:
        # Ex: ip_version = "8_1" → prefix=gmc, versao=8_1 → gmc_8_1_sh_mask.h
        # Ex: ip_version = "gfx_8_0" → prefix=gfx, versao=8_0 → gfx_8_0_sh_mask.h
        parts = ip_version.split("_", 1)
        version = f"{parts[0]}_{parts[1]}"
    else:
        version = ip_version

    # Para GCA/GC, o prefixo ja esta no ip_version (ex: gfx_8_0), entao nao
    # duplica. Para GMC, o ip_version e "8_1" e o prefixo e "gmc".
    if ip_version.startswith(f"{file_prefix}_"):
        # ip_version ja contem o prefixo (ex: gfx_8_0)
        filename = f"{ip_version}_sh_mask.h"
    else:
        # ip_version nao contem prefixo (ex: 8_1)
        filename = f"{file_prefix}_{ip_version}_sh_mask.h"

    mask_candidate = os.path.join(amd_root, ASIC_REG_DIR, dirn, filename)
    if os.path.isfile(mask_candidate):
        return mask_candidate
    return None


def find_sh_mask_by_identity(
    amd_root: str, resolved_d_header: Optional[str],
    ip_block: Optional[str], ip_version: Optional[str]
) -> Optional[str]:
    """Seleciona o unico _sh_mask.h compativel com a identidade, ou None."""
    if resolved_d_header:
        derived = derive_sh_mask_header(resolved_d_header)
        if derived and os.path.isfile(derived):
            return derived

    if ip_block and ip_version:
        derived = derive_sh_mask_by_ipblock(ip_block, ip_version, amd_root)
        if derived and os.path.isfile(derived):
            return derived

    return None


def _list_sh_mask_files(base: str) -> List[str]:
    """Retorna todos os arquivos *_sh_mask.h no arvore base, incluindo subdiretorios."""
    out: List[str] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith("_sh_mask.h"):
                out.append(os.path.join(root, f))
    return out


def find_sh_mask_candidates(
    amd_root: str, gfx: str,
    ip_block: Optional[str] = None,
    ip_version: Optional[str] = None
) -> List[str]:
    """Encontra todos os candidatos *_sh_mask.h para um determinado gfx.

    Quando identidade fornecida (ip_block, ip_version), filtra os candidatos
    para APENAS os headers compatíveis com o bloco IP e versao.
    Quando identidade não fornecida, usa o fallback amplo (comportamento legado).
    """
    candidates: List[str] = []
    base = os.path.join(amd_root, ASIC_REG_DIR)
    seen: set = set()

    def _add(path: str) -> None:
        rp = os.path.realpath(path)
        if rp not in seen and os.path.isfile(path):
            seen.add(rp)
            candidates.append(path)

    if ip_block and ip_version:
        # FILTRADO: APENAS headers compatíveis com o bloco IP e versao
        dirn = IP_BLOCK_DIR.get(ip_block.upper())
        if not dirn:
            return []  # bloco IP desconhecido

        # Construir o padrao esperado: <prefixo>_<versao>_sh_mask.h
        if "_" in ip_version:
            # gmc_8_1 : prefixo = gmc, versao = 8_1
            parts = ip_version.split("_", 1)
            prefix = f"{dirn.lower()}_{parts[0]}"
            version = f"{parts[0]}_{parts[1]}"
        else:
            prefix = f"{dirn.lower()}_{ip_version}"
            version = ip_version

        expected_pattern = f"{prefix}_{version}_sh_mask.h"

        # Procurar o arquivo específico
        specific_path = os.path.join(base, dirn, expected_pattern)
        if os.path.isfile(specific_path):
            _add(specific_path)
        return candidates  # retorna apenas o header específico ou lista vazia

    # FALLBACK: comportamento legado (varrer todos)
    # 1) Localizacoes ordenadas de preferencia para este gfx.
    for pattern in (
        os.path.join("gca", "{gfx}_sh_mask.h"),
        os.path.join("gc", "{gfx}_sh_mask.h"),
        os.path.join("gmc", "{gfx}_sh_mask.h"),
    ):
        _add(os.path.join(base, pattern.format(gfx=gfx)))

    # 2) Qualquer {gfx}_sh_mask.h em qualquer subdiretorio.
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.startswith(f"{gfx}_") and f.endswith("_sh_mask.h"):
                _add(os.path.join(root, f))

    # 3) Headers GMC para este gfx (necessarios para registros MMIO GFX8/9).
    # GMC usa nomenclatura como gmc_8_1_sh_mask.h, gmc_8_2_sh_mask.h, etc.
    for f in _list_sh_mask_files(base):
        if "gmc" in f and (gfx in os.path.basename(f) or re.search(r"8_", os.path.basename(f))):
            _add(f)

    # 4) Todos os *_sh_mask.h restantes (fallback amplo).
    for f in _list_sh_mask_files(base):
        _add(f)

    return candidates


def scan_sh_mask_defines(path: str) -> Dict[str, Dict[str, Any]]:
    """Varre um arquivo *sh_mask.h e extrai todas as macros #define numericas."""
    defines: Dict[str, Dict[str, Any]] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line_num, line in enumerate(fh, 1):
                m = _define_re.match(line)
                if m:
                    name = m.group(1)
                    val = parse_int(m.group(2))
                    defines[name] = {"value": val, "line": line_num}
    except Exception:
        pass
    return defines


def find_register_fields(
    amd_root: str, register_name: str, gfx: str,
    resolved_header: Optional[str] = None,
    ip_block: Optional[str] = None,
    ip_version: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extrai todos os campos para um registro mm*.

    Com identidade fornecida (resolved_header, ip_block e/ou ip_version):
        Usa EXATAMENTE o _sh_mask.h derivado da identidade. Nao pesquisa
        outros arquivos. Se o _sh_mask.h derivado nao existir, devolve [] e
        o envelope de saida informa "fields_status": "NO_SCHEMA".

    Sem identidade: fallback ao comportamento antigo (varrer *_sh_mask.h).
    """
    selected_header = find_sh_mask_by_identity(amd_root, resolved_header, ip_block, ip_version)

    if selected_header:
        defines = scan_sh_mask_defines(selected_header)
        return _scan_for_register(
            amd_root, register_name, selected_header, defines
        )

    # Fallback: varrer todos os candidatos (comportamento legado).
    candidates = find_sh_mask_candidates(amd_root, gfx, ip_block, ip_version)
    if not candidates:
        return []

    results: List[Dict[str, Any]] = []
    for sh_path in candidates:
        defines = scan_sh_mask_defines(sh_path)
        if not defines:
            continue
        results.extend(_scan_for_register(amd_root, register_name, sh_path, defines))
    return results


def _scan_for_register(
    amd_root: str, register_name: str, sh_path: str,
    defines: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Varre defines de um unico arquivo e devolve os campos do registro."""
    results: List[Dict[str, Any]] = []

    pattern = re.compile(
        r"^" + re.escape(register_name) + r"__([A-Za-z0-9_]+)_MASK$"
    )

    for name, mask_info in defines.items():
        m = pattern.match(name)
        if not m:
            continue

        field_name = m.group(1)
        mask_val = mask_info["value"]
        mask_line = mask_info["line"]

        shift_name = f"{register_name}__{field_name}__SHIFT"
        shift_info = defines.get(shift_name)
        if not shift_info:
            continue

        shift_val = shift_info["value"]
        shift_line = shift_info["line"]

        low_bit = shift_val
        low_bits_mask = (1 << shift_val) - 1
        if (mask_val & low_bits_mask) != 0:
            continue

        masked = mask_val >> shift_val
        width = bin(masked).count("1")
        high_bit = low_bit + width - 1 if width > 0 else shift_val

        is_contiguous = (masked == ((1 << width) - 1)) if width > 0 else True

        results.append({
            "register": register_name,
            "field_name": field_name,
            "mask": hex(mask_val),
            "mask_value": mask_val,
            "shift": shift_val,
            "low_bit": low_bit,
            "high_bit": high_bit,
            "width": width,
            "mask_is_positioned": (mask_val >> shift_val) != 0,
            "mask_is_contiguous": is_contiguous,
            "header_file": os.path.relpath(sh_path, amd_root),
            "field_line_mask": mask_line,
            "field_line_shift": shift_line,
            "field_macro_mask": f"{register_name}__{field_name}_MASK",
            "field_macro_shift": f"{register_name}__{field_name}__SHIFT",
        })

    return results


# ---------------------------------------------------------------------------
# self-test (com vetores discriminantes: identidade, ambiguidade,
# geracoes incompativeis).
# ---------------------------------------------------------------------------

def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtive {got!r}, esperava {want!r}")

    # -----------------------------------------------------------------------
    # Teste A: autodescoberta (fallback, sem identidade) - compatibilidade
    # com o comportamento anterior.
    # -----------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        amd_root = os.path.join(td, "amd")
        base = os.path.join(amd_root, ASIC_REG_DIR, "gca")
        os.makedirs(base, exist_ok=True)
        sh = os.path.join(base, "gfx_8_0_sh_mask.h")
        with open(sh, "w", encoding="utf-8") as fh:
            fh.write("#define VM_CONTEXT0_CNTL__ENABLE_CONTEXT_MASK 0x1\n")
            fh.write("#define VM_CONTEXT0_CNTL__ENABLE_CONTEXT__SHIFT 0x0\n")
            fh.write("#define VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH_MASK 0x6\n")
            fh.write("#define VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH__SHIFT 0x1\n")

        fields = find_register_fields(amd_root, "VM_CONTEXT0_CNTL", "gfx_8_0")
        check("A.count", len(fields), 2)
        if len(fields) >= 2:
            fields_dict = {f["field_name"]: f for f in fields}
            check("A.ENABLE_CONTEXT.mask", fields_dict["ENABLE_CONTEXT"]["mask"], "0x1")
            check("A.ENABLE_CONTEXT.shift", fields_dict["ENABLE_CONTEXT"]["shift"], 0)
            check("A.ENABLE_CONTEXT.width", fields_dict["ENABLE_CONTEXT"]["width"], 1)
            check("A.PAGE_TABLE_DEPTH.mask", fields_dict["PAGE_TABLE_DEPTH"]["mask"], "0x6")
            check("A.PAGE_TABLE_DEPTH.shift", fields_dict["PAGE_TABLE_DEPTH"]["shift"], 1)
            check("A.PAGE_TABLE_DEPTH.width", fields_dict["PAGE_TABLE_DEPTH"]["width"], 2)

    # -----------------------------------------------------------------------
    # Teste B: identidade derivada de resolved_header → seleciona EXATAMENTE
    # um _sh_mask.h. Sem este contexto, um segundo arquivo define o mesmo
    # registro com um schema de campos INCOMPATIVEL; o teste verifica que
    # os campos do arquivo errado NAO aparecem.
    # -----------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        amd_root = os.path.join(td, "amd")
        d81 = os.path.join(amd_root, ASIC_REG_DIR, "gmc", "gmc_8_1_d.h")
        sh81 = os.path.join(amd_root, ASIC_REG_DIR, "gmc", "gmc_8_1_sh_mask.h")
        sh82 = os.path.join(amd_root, ASIC_REG_DIR, "gmc", "gmc_8_2_sh_mask.h")
        os.makedirs(os.path.dirname(d81), exist_ok=True)
        os.makedirs(os.path.dirname(sh81), exist_ok=True)
        os.makedirs(os.path.dirname(sh82), exist_ok=True)

        with open(d81, "w", encoding="utf-8") as fh:
            fh.write("#define mmVM_CONTEXT0_CNTL 0x504\n")

        with open(sh81, "w", encoding="utf-8") as fh:
            # Schema da geracao 8.1: habilita, profundidade PT, protecao INT
            fh.write("#define VM_CONTEXT0_CNTL__ENABLE_CONTEXT_MASK 0x1\n")
            fh.write("#define VM_CONTEXT0_CNTL__ENABLE_CONTEXT__SHIFT 0x0\n")
            fh.write("#define VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH_MASK 0x6\n")
            fh.write("#define VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH__SHIFT 0x1\n")

        with open(sh82, "w", encoding="utf-8") as fh:
            # Schema da geracao 8.2: DIFERENTE (novo campo, mascara distinta)
            fh.write("#define VM_CONTEXT0_CNTL__ENABLE_CONTEXT_MASK 0x2\n")
            fh.write("#define VM_CONTEXT0_CNTL__ENABLE_CONTEXT__SHIFT 0x1\n")
            fh.write("#define VM_CONTEXT0_CNTL__NEW_FEATURE_MASK 0x4\n")
            fh.write("#define VM_CONTEXT0_CNTL__NEW_FEATURE__SHIFT 0x2\n")

        resolved_header = d81
        fields = find_register_fields(
            amd_root, "VM_CONTEXT0_CNTL", "gfx_8_0",
            resolved_header=resolved_header
        )

        # Sem contexto, o fallback pega o primeiro arquivo que encontra o registro.
        fallback_fields = find_register_fields(amd_root, "VM_CONTEXT0_CNTL", "gfx_8_0")

        check("B.count_with_identity", len(fields), 2)
        check("B.ENABLE_CONTEXT.mask", fields[0]["mask"], "0x1")
        check("B.ENABLE_CONTEXT.shift", fields[0]["shift"], 0)
        check("B.ENABLE_CONTEXT.header", os.path.basename(fields[0]["header_file"]), "gmc_8_1_sh_mask.h")
        check("B.header_file", fields[0]["header_file"], "include/asic_reg/gmc/gmc_8_1_sh_mask.h")

        # O campo NEW_FEATURE da geracao 8.2 NAO deve aparecer.
        field_names = {f["field_name"]: f for f in fields}
        check("B.no_wrong_gen", "NEW_FEATURE" not in field_names, True)
        # PAGE_TABLE_DEPTH existe na 8.1 (a correta) — so verifica que vem do header certo.
        check("B.uses_gen81", "PAGE_TABLE_DEPTH" in field_names, True)
        check("B.page_table_depth.header",
              any(f["field_name"] == "PAGE_TABLE_DEPTH" and "gmc_8_1" in f["header_file"] for f in fields), True)

        # O fallback (sem contexto) pega campos de AMBAS geracoes: demonstra a ambiguidade.
        check("B.fallback_count", len(fallback_fields), 4)

    # -----------------------------------------------------------------------
    # Teste C: ip_block + ip_version → selecao sem arquivo _d.h resolvido.
    # -----------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        amd_root = os.path.join(td, "amd")
        sh_gca_80 = os.path.join(amd_root, ASIC_REG_DIR, "gca", "gfx_8_0_sh_mask.h")
        sh_gca_81 = os.path.join(amd_root, ASIC_REG_DIR, "gca", "gfx_8_1_sh_mask.h")
        os.makedirs(os.path.dirname(sh_gca_80), exist_ok=True)
        os.makedirs(os.path.dirname(sh_gca_81), exist_ok=True)

        with open(sh_gca_80, "w", encoding="utf-8") as fh:
            fh.write("#define GCA_80_REG__F1_MASK 0x1\n")
            fh.write("#define GCA_80_REG__F1__SHIFT 0x0\n")
        with open(sh_gca_81, "w", encoding="utf-8") as fh:
            fh.write("#define GCA_81_REG__F1_MASK 0x4\n")
            fh.write("#define GCA_81_REG__F1__SHIFT 0x2\n")

        fields = find_register_fields(
            amd_root, "GCA_80_REG", "gfx_8_0",
            ip_block="GCA", ip_version="8_0"
        )
        check("C.count", len(fields), 1)
        check("C.shift", fields[0]["shift"], 0)
        check("C.header", os.path.basename(fields[0]["header_file"]), "gfx_8_0_sh_mask.h")

        # Teste C2: GMC com ip_version "8_1" (sem prefixo)
        sh_gmc_81 = os.path.join(amd_root, ASIC_REG_DIR, "gmc", "gmc_8_1_sh_mask.h")
        os.makedirs(os.path.dirname(sh_gmc_81), exist_ok=True)
        with open(sh_gmc_81, "w", encoding="utf-8") as fh:
            fh.write("#define GMC_81_REG__F1_MASK 0x1\n")
            fh.write("#define GMC_81_REG__F1__SHIFT 0x0\n")

        fields_c2 = find_register_fields(
            amd_root, "GMC_81_REG", "gfx_8_0",
            ip_block="GMC", ip_version="8_1"
        )
        check("C2.count", len(fields_c2), 1)
        check("C2.shift", fields_c2[0]["shift"], 0)
        check("C2.header", os.path.basename(fields_c2[0]["header_file"]), "gmc_8_1_sh_mask.h")

    # -----------------------------------------------------------------------
    # Teste D: contexto insuficiente com multiplas cabeceras homonimas → o
    # fallback varre os 3, mas o modo com identidade seleciona 1 (ou 0 se a
    # cabeca derivada nao existir). Verifica que a derivacao de cabeca
    # inexistente nao produz campos inventados.
    # -----------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        amd_root = os.path.join(td, "amd")
        d_nonexistent = os.path.join(amd_root, ASIC_REG_DIR, "gmc", "gmc_9_9_d.h")
        fields = find_register_fields(
            amd_root, "MMHUB_SOME_REG", "gfx_8_0",
            resolved_header=d_nonexistent
        )
        check("D.no_schema_count", len(fields), 0)

    # -----------------------------------------------------------------------
    # Teste E: registro inexistente → 0 campos (compatibilidade).
    # -----------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        amd_root = os.path.join(td, "amd")
        none_fields = find_register_fields(amd_root, "MM_INVALID", "gfx_8_0")
        check("E.not_found", len(none_fields), 0)

    if failures:
        print(f"{NAME} {VERSION} · self-test FALHOU ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"{NAME} {VERSION} · self-test OK")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog=NAME,
        description="Extrai todos os campos de um registro MMIO a partir do "
                    "_sh_mask.h derivado da identidade do registro."
    )
    ap.add_argument("--selftest", action="store_true",
                    help="executa o auto-teste unitário")
    ap.add_argument("--kernel", help="raiz do kernel AMD (contém drivers/gpu/drm/amd)")
    ap.add_argument("--reg", help="nome do registro MMIO (por exemplo, VM_CONTEXT0_CNTL)")
    ap.add_argument("--gfx", default="gfx_8_0", help="target gfx generation (padrão: gfx_8_0)")
    ap.add_argument("--ip-block", dest="ip_block",
                    help="bloqueio IP da identidade do registro (GMC, GCA, GC, MMHUB, SDMA)")
    ap.add_argument("--ip-version", dest="ip_version",
                    help="versao do bloco IP (8_1, 8_2, 9_4_3, gfx_8_0, etc.)")
    ap.add_argument("--resolved-header", dest="resolved_header",
                    help="caminho da cabeca _d.h resolvida (ex: .../gmc_8_1_d.h)")
    ap.add_argument("--resolved-json", dest="resolved_json",
                    help="arquivo JSON com a saida de reg_resolve (campos chosen/definition)")
    ap.add_argument("--json", action="store_true", help="emite JSON")

    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.kernel:
        ap.error("--kernel é obrigatório (salvo com --selftest)")
    if not args.reg:
        ap.error("--reg é obrigatório (salvo com --selftest)")

    kernel_path = os.path.abspath(args.kernel)
    amd_root = os.path.join(kernel_path, "drivers/gpu/drm/amd")
    if not os.path.isdir(amd_root):
        ap.error("--kernel deve conter drivers/gpu/drm/amd")

    # Determina a identidade a partir das opcoes.
    resolved_header = args.resolved_header
    ip_block = args.ip_block
    ip_version = args.ip_version

    if args.resolved_json:
        try:
            with open(args.resolved_json, "r", encoding="utf-8") as fh:
                identity = json.load(fh)
            chosen = identity.get("chosen")
            if isinstance(chosen, dict):
                resolved_header = chosen.get("file")
                definition = identity.get("definition")
                if definition and isinstance(definition, dict):
                    ip_version = definition.get("ip_version") or definition.get("generation")
                    ip_block = definition.get("ip_block")
            else:
                # Evidencia: sem cabeca escolhida, nao ha geracao certa para
                # derivar o schema de campos.
                resolved_header = None
        except Exception as exc:
            ap.error(f"--resolved-json nao pôde ser lido: {exc}")

    fields = find_register_fields(
        amd_root, args.reg, args.gfx,
        resolved_header=resolved_header,
        ip_block=ip_block,
        ip_version=ip_version,
    )

    out = {
        "tool": NAME,
        "version": VERSION,
        "register": args.reg,
        "gfx": args.gfx,
        "fields": fields,
        "field_count": len(fields),
    }
    if resolved_header:
        out["identity_status"] = "RESOLVED"
        out["identity_chosen_header"] = resolved_header
        out["identity_ip_block"] = ip_block
        out["identity_generation"] = ip_version
    elif ip_block and ip_version:
        out["identity_status"] = "RESOLVED_BY_IPBLOCK"
        out["identity_ip_block"] = ip_block
        out["identity_generation"] = ip_version
    else:
        out["identity_status"] = "UNRESOLVED"
        out["identity_selection_evidence"] = (
            "fallback: sem identidade, foi varrido *_sh_mask.h; se houver "
            "multiplas cabeceras homonimas, a geracao do schema pode estar "
            "ambigua."
        )

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print(f"{NAME} {VERSION} · registro {args.reg}, gfx={args.gfx} · "
          f"WORK_CLASS=READ_ONLY")
    if not fields:
        print(f"  Nenhum campo encontrado para '{args.reg}' (0 resultados).")
    else:
        print(f"  Campos extraídos: {len(fields)}")
        for f in fields:
            print(f"    - {f['field_name']}: mask={f['mask']}, shift={f['shift']}, "
                  f"width={f['width']} [origem {f['header_file']}:{f['field_line_mask']}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
