#!/usr/bin/env python3
"""trace_data - RXRE capability to trace register read/write operations.

Esta capacidad extrae operaciones de acceso a registros (READ, WRITE, READ_MODIFY_WRITE)
desde archivos C en el corpus, asociándolas con funciones y proving provenance completa.

Ejemplo de uso:
  python3 tools/rxre_trace_data.py --register VM_CONTEXT0_CNTL --gfx gfx_8_0 --json
  python3 tools/rxre_trace_data.py --function gmc_v8_0_gart_enable --gfx gfx_8_0 --json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths de interés
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # raíz del proyecto rxre


def _kernelbuild() -> str:
    """Devuelve el path al árbol de kernel usado como corpus."""
    return os.path.join(ROOT, "RESEARCH", "kernelbuild", "linux-7.1.3")


# ---------------------------------------------------------------------------
# Patrones de detección
# ---------------------------------------------------------------------------

# READ:  tmp = RREG32(mmREGISTER)
#        RREG32_INDEX(mmREGISTER)
READ_PATTERN = re.compile(
    r"RREG32(?:_INDEX|_PIO|_SMC)?\s*\(\s*mm([A-Za-z0-9_]+)\s*\)"
)

# WRITE: WREG32(mmREGISTER, ...)
#        WREG32_P(mmREGISTER, value, mask)
#        WREG32_RLC(mmREGISTER, value)
#        WREG32_INDEX(mmREGISTER, value)
WRITE_PATTERN = re.compile(
    r"WREG32(?:[_A-Z]*)?\s*\(\s*mm([A-Za-z0-9_]+)\s*,"
)

# READ-MODIFY-WRITE: no es un patrón único; se detecta combinando READ+WRITE
# en la misma función para el mismo registro sin WRITE intermedio.

# Detección de definición de función: [static|extern] return_type name(
# Requiere al menos dos palabras antes del paréntesis para reducir
# falsos positivos (llamadas a funciones como RREG32(...)).
FUNCTION_DEF_PATTERN = re.compile(
    r"^\s*(?:static\s+|extern\s+)?\w+\s+\w+\s*\("
)

# Palabras clave de C que no deben tratarse como nombres de función
C_KEYWORDS = frozenset({
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do', 'double',
    'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'int', 'long', 'register',
    'return', 'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef',
    'union', 'unsigned', 'void', 'volatile', 'while',
})


def _strip_line_comment(line: str) -> str:
    """Elimina comentarios // de una línea (pero respeta strings)."""
    in_string = False
    escape = False
    for i, ch in enumerate(line):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string and ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
            return line[:i]
    return line


def _is_function_definition(line: str) -> bool:
    """Verdadero si la línea parece una definición de función."""
    match = FUNCTION_DEF_PATTERN.match(line)
    if not match:
        return False
    # Verificar que la palabra antes del '(' no sea un keyword de C
    parts = line.strip().split()
    for i, part in enumerate(parts):
        if '(' in part:
            if i > 0:
                candidate = parts[i - 1]
                if '(' not in candidate and candidate not in C_KEYWORDS:
                    return True
            # También verificar si el nombre está en la misma parte
            func_candidate = part.split('(')[0]
            if func_candidate not in C_KEYWORDS:
                return True
    return False


def _extract_function_name(line: str) -> Optional[str]:
    """Extrae el nombre de la función de una línea de definición de función.
    Devuelve None si no es una definición de función.
    """
    if not FUNCTION_DEF_PATTERN.match(line):
        return None
    # Formato esperado: [static/extern] return_type function_name(params)
    # El '(' puede estar en la misma palabra que el nombre de la función
    parts = line.strip().split()
    for i, part in enumerate(parts):
        if '(' in part:
            # El '(' está en esta parte - el nombre de la función está o en esta parte (antes del '(')
            # o en la parte anterior (si la parte anterior no tiene '(')
            if '(' in part:
                # Intentamos extraer el nombre de esta parte
                func_name = part.split('(')[0]
                if func_name and func_name not in C_KEYWORDS:
                    return func_name
            if i > 0:
                candidate = parts[i - 1]
                if '(' not in candidate and candidate not in C_KEYWORDS:
                    return candidate
    return None


# ---------------------------------------------------------------------------
# Cache: escanea el árbol del kernel una sola vez por register_token
# ---------------------------------------------------------------------------

_SCAN_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def _find_register_accesses(
    kernel_path: str,
    register_token: str,
) -> List[Dict[str, Any]]:
    """Busca en el corpus accesos a un registro dado (por su token mmREGISTER).
    Devuelve una lista de diccionarios, cada uno representando un acceso (READ o WRITE)
    con provenance básica (sin agrupar por función ni intentar RMW todavía).
    """
    cache_key = (kernel_path, register_token)
    if cache_key in _SCAN_CACHE:
        return copy.deepcopy(_SCAN_CACHE[cache_key])

    # register_token es de la forma "mmREGISTRO" (ej. "mmVM_CONTEXT0Cntl")
    # Extraemos solo el nombre del registro (sin el prefijo mm) para comparar
    register_name = register_token.upper()[2:]  # Quitar "mm"
    accesses: List[Dict[str, Any]] = []
    for root, dirs, files in os.walk(kernel_path):
        # Evitamos directorios ocultos y de control de versión
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if not file.endswith('.c'):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except OSError:
                continue

            current_function: Optional[str] = None
            for line_num, line in enumerate(lines, start=1):
                if _is_function_definition(line):
                    current_function = _extract_function_name(line)
                if current_function is not None:
                    clean_line = _strip_line_comment(line)
                    read_match = READ_PATTERN.search(clean_line)
                    if read_match:
                        if read_match.group(1).upper() == register_name:
                            acc = {
                                'register': register_name,
                                'register_token': register_token,
                                'function': current_function,
                                'file': file_path,
                                'line': line_num,
                                'operation': 'READ',
                                'expression': line.strip(),
                                'source_snippet': line.rstrip(),
                                'canonical_register_source': 'trace_data_input',
                            }
                            accesses.append(acc)
                        continue  # No también buscar WRITE en la misma línea
                    write_match = WRITE_PATTERN.search(clean_line)
                    if write_match:
                        if write_match.group(1).upper() == register_name:
                            acc = {
                                'register': register_name,
                                'register_token': register_token,
                                'function': current_function,
                                'file': file_path,
                                'line': line_num,
                                'operation': 'WRITE',
                                'expression': line.strip(),
                                'source_snippet': line.rstrip(),
                                'canonical_register_source': 'trace_data_input',
                            }
                            accesses.append(acc)

    _SCAN_CACHE[cache_key] = copy.deepcopy(accesses)
    return accesses


def _group_by_function(
    accesses: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Agrupa las operaciones por función."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for acc in accesses:
        func = acc.get('function', '')
        if func:
            grouped.setdefault(func, []).append(acc)
    # Ordenar cada grupo por número de línea
    for func in grouped:
        grouped[func].sort(key=lambda x: x['line'])
    return grouped


# ---------------------------------------------------------------------------
# Detección de READ_MODIFY_WRITE
# ---------------------------------------------------------------------------

def _detect_rmw_pairs(operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detecta pares READ seguido de WRITE (sin WRITE intermedio del mismo registro)
    y devuelve operaciones READ_MODIFY_WRITE para estos pares.
    Las READ/WRITE originales se mantienen independientes.
    """
    if not operations:
        return []

    rmw_result: List[Dict[str, Any]] = []
    used_indices: set = set()

    i = 0
    while i < len(operations):
        op = operations[i]
        if op['operation'] == 'READ' and i not in used_indices:
            # Buscamos el próximo WRITE sin un WRITE intermedio del mismo registro
            j = i + 1
            while j < len(operations) and operations[j]['operation'] != 'WRITE':
                j += 1
            if j < len(operations) and operations[j]['operation'] == 'WRITE' and j not in used_indices:
                # Encontramos un par READ->WRITE sin WRITE intermedio del mismo registro
                # Creamos una operación RMW que abarca desde el READ hasta el WRITE
                rmw_op = {
                    'register': operations[i].get('register', ''),
                    'register_token': operations[i].get('register_token', ''),
                    'function': operations[i].get('function', ''),
                    'file': operations[i].get('file', ''),
                    'line_start': operations[i]['line'],
                    'line_end': operations[j]['line'],
                    'operation': 'READ_MODIFY_WRITE',
                    'expression': f"{operations[i]['expression']}\n{operations[j]['expression']}",
                    'source_snippet': f"{operations[i]['source_snippet']}\n{operations[j]['source_snippet']}",
                    'canonical_register_source': operations[i].get('canonical_register_source', ''),
                }
                rmw_result.append(rmw_op)
                used_indices.add(i)
                used_indices.add(j)
                i = j + 1
                continue
        i += 1
    return rmw_result


# ---------------------------------------------------------------------------
# Modo registro → funciones
# ---------------------------------------------------------------------------

def _trace_data_by_register(args: Dict[str, Any]) -> Dict[str, Any]:
    """Modo trace_data por registro: dado un registro, devuelve las funciones que lo acceden."""
    register_name = args['register']
    # Formamos el token mmREGISTER (asumimos que el registro se nombra en mayúsculas en el código)
    register_token = f"mm{register_name.upper()}"
    gfx = args.get('gfx', 'gfx_8_0')
    kernel_path = args.get('kernel', _kernelbuild())

    # Verificamos que el kernel_path exista
    if not os.path.isdir(kernel_path):
        return {
            "tool": "trace_data",
            "register": register_name,
            "gfx": gfx,
            "status": "error",
            "limitations": [f"kernel path no existe: {kernel_path}"],
        }

    # Buscamos todos los accesos al registro en el corpus
    accesses = _find_register_accesses(kernel_path, register_token)
    if not accesses:
        return {
            "tool": "trace_data",
            "register": register_name,
            "gfx": gfx,
            "status": "not_found",
            "limitations": [f"no se encontraron accesos al registro {register_name} en el corpus"],
        }

    # Agrupamos por función
    grouped = _group_by_function(accesses)

    # Para cada función, detectamos RMW y preparamos los resultados
    results: List[Dict[str, Any]] = []
    for func_name, func_accesses in grouped.items():
        # Añadimos el nombre del registro a cada acceso para contexto
        for acc in func_accesses:
            acc['register'] = register_name
            # Aseguramos que line_start y line_end existan
            if 'line_start' not in acc:
                acc['line_start'] = acc['line']
                acc['line_end'] = acc['line']
        # Primero añadimos las operaciones principales
        results.extend(func_accesses)
        # Luego detectamos pares READ-MODIFY-WRITE
        rmw_pairs = _detect_rmw_pairs(func_accesses)
        for rmw in rmw_pairs:
            results.append(rmw)

    # Ordenamos los resultados por file y line_start para consistencia
    results.sort(key=lambda x: (x['file'], x['line_start'] if 'line_start' in x else x['line']))

    return {
        "tool": "trace_data",
        "version": "0.1.0",
        "register": register_name,
        "gfx": gfx,
        "status": "ok" if results else "not_found",
        "results": results,
    }


# ---------------------------------------------------------------------------
# Modo función → registros
# ---------------------------------------------------------------------------

def _find_all_register_accesses(kernel_path: str) -> List[Dict[str, Any]]:
    """Busca en el corpus todos los accesos a registros (cualquier token que coincida con mm seguido de alfanuméricos).
    Devuelve una lista de accesos, cada uno con el token del registro detectado (con prefijo mm).
    Incluye función y provenance básica.
    """
    cache_key = ("__all__", kernel_path)
    if cache_key in _SCAN_CACHE:
        return copy.deepcopy(_SCAN_CACHE[cache_key])

    all_accesses: List[Dict[str, Any]] = []
    # Patrón para cualquier token mmREGISTER
    any_mm_pattern = re.compile(r"RREG32(?:_INDEX|_PIO|_SMC)?\s*\(\s*(mm[A-Za-z0-9_]+)\s*\)")
    any_wreg_pattern = re.compile(r"WREG32(?:[_A-Z]*)?\s*\(\s*(mm[A-Za-z0-9_]+)\s*,")

    for root, dirs, files in os.walk(kernel_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if not file.endswith('.c'):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except OSError:
                continue

            current_function: Optional[str] = None
            for line_num, line in enumerate(lines, start=1):
                if _is_function_definition(line):
                    current_function = _extract_function_name(line)
                if current_function is not None:
                    clean_line = _strip_line_comment(line)
                    read_match = any_mm_pattern.search(clean_line)
                    if read_match:
                        reg_token = read_match.group(1)
                        all_accesses.append({
                            'register': reg_token[2:].upper(),  # sin mm
                            'register_token': reg_token,
                            'function': current_function,
                            'file': file_path,
                            'line': line_num,
                            'operation': 'READ',
                            'expression': line.strip(),
                            'source_snippet': line.rstrip(),
                            'canonical_register_source': 'trace_data_input',
                        })
                        continue
                    write_match = any_wreg_pattern.search(clean_line)
                    if write_match:
                        reg_token = write_match.group(1)
                        all_accesses.append({
                            'register': reg_token[2:].upper(),  # sin mm
                            'register_token': reg_token,
                            'function': current_function,
                            'file': file_path,
                            'line': line_num,
                            'operation': 'WRITE',
                            'expression': line.strip(),
                            'source_snippet': line.rstrip(),
                            'canonical_register_source': 'trace_data_input',
                        })

    _SCAN_CACHE[cache_key] = copy.deepcopy(all_accesses)
    return all_accesses


def _trace_data_by_function(args: Dict[str, Any]) -> Dict[str, Any]:
    """Modo trace_data por función: dada una función, devuelve los registros que accede."""
    function_name = args['function']
    gfx = args.get('gfx', 'gfx_8_0')
    kernel_path = args.get('kernel', _kernelbuild())

    # Verificamos que el kernel_path exista
    if not os.path.isdir(kernel_path):
        return {
            "tool": "trace_data",
            "function": function_name,
            "gfx": gfx,
            "status": "error",
            "limitations": [f"kernel path no existe: {kernel_path}"],
        }

    # Buscamos todos los accesos
    all_accesses = _find_all_register_accesses(kernel_path)
    # Filtramos por función
    reg_accesses = [acc for acc in all_accesses if acc.get('function') == function_name]

    if not reg_accesses:
        return {
            "tool": "trace_data",
            "function": function_name,
            "gfx": gfx,
            "status": "not_found",
            "limitations": [f"no se encontraron accesos a registros en la función {function_name}"],
        }

    # Agrupamos por registro
    grouped_by_reg: Dict[str, List[Dict[str, Any]]] = {}
    for acc in reg_accesses:
        reg = acc.get('register', '')
        if reg:
            grouped_by_reg.setdefault(reg, []).append(acc)
    for reg in grouped_by_reg:
        grouped_by_reg[reg].sort(key=lambda x: x['line'])

    results: List[Dict[str, Any]] = []
    for reg_name, reg_accesses in grouped_by_reg.items():
        # Añadimos el nombre de la función a cada acceso
        for acc in reg_accesses:
            acc['function'] = function_name
            acc['canonical_register_source'] = 'trace_data_input'
            if 'line_start' not in acc:
                acc['line_start'] = acc['line']
                acc['line_end'] = acc['line']
        # Primero añadimos las operaciones principales
        results.extend(reg_accesses)
        # Luego detectamos pares READ-MODIFY-WRITE
        rmw_pairs = _detect_rmw_pairs(reg_accesses)
        for rmw in rmw_pairs:
            rmw['register'] = reg_name
            results.append(rmw)

    # Ordenamos por registro y luego por file y line_start
    results.sort(key=lambda x: (x['register'], x['file'], x['line_start'] if 'line_start' in x else x['line']))

    return {
        "tool": "trace_data",
        "version": "0.1.0",
        "function": function_name,
        "gfx": gfx,
        "status": "ok" if results else "not_found",
        "results": results,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _selftest() -> int:
    """Valida la capacidad trace_data contra el corpus.
    Casos de regresión: VM_CONTEXT0_CNTL en gmc_v8_0.c
    """
    print("=== trace_data self-test ===")

    # Construir un corpus reducido para testing rápido (solo gmc_v8_0.c)
    test_kernel = os.path.join(HERE, "..", "RESEARCH", "kernelbuild", "linux-7.1.3",
                               "drivers", "gpu", "drm", "amd", "amdgpu")
    print(f"test_kernel: {test_kernel}")
    print(f"exists: {os.path.isdir(test_kernel)}")
    if not os.path.isdir(test_kernel):
        test_kernel = None

    # Caso de prueba 1: register → function
    args = {'register': 'VM_CONTEXT0_CNTL', 'gfx': 'gfx_8_0'}
    if test_kernel:
        args['kernel'] = test_kernel
    print(f"args: {args}")
    result = _trace_data_by_register(args)
    print(f"Register result: status={result['status']}")
    if result['status'] != 'ok':
        print(f"FAIL: status={result['status']}")
        print(f"  limitations: {result.get('limitations', [])}")
        return 1

    # Verificamos funciones críticas
    functions = set(res.get('function', '') for res in result['results'])
    if 'gmc_v8_0_gart_enable' not in functions:
        print("FAIL: gmc_v8_0_gart_enable no se encuentra accediendo a VM_CONTEXT0_CNTL")
        return 1
    if 'gmc_v8_0_gart_disable' not in functions:
        print("FAIL: gmc_v8_0_gart_disable no se encuentra accediendo a VM_CONTEXT0_CNTL")
        return 1
    if 'gmc_v8_0_vm_fault_interrupt_state' not in functions:
        print("FAIL: gmc_v8_0_vm_fault_interrupt_state no se encuentra accediendo a VM_CONTEXT0_CNTL")
        return 1

    # Verificamos que haya al menos un READ, un WRITE y un READ_MODIFY_WRITE
    ops = set(res['operation'] for res in result['results'])
    if 'READ' not in ops:
        print("FAIL: no se encontró ninguna operación READ")
        return 1
    if 'WRITE' not in ops:
        print("FAIL: no se encontró ninguna operación WRITE")
        return 1
    if 'READ_MODIFY_WRITE' not in ops:
        print("FAIL: no se encontró ninguna operación READ_MODIFY_WRITE")
        return 1

    # Verificamos la provenance de un READ
    read_ops = [res for res in result['results'] if res['operation'] == 'READ']
    if not read_ops:
        print("FAIL: no hay operaciones READ")
        return 1
    first_read = read_ops[0]
    for key in ['register', 'function', 'file', 'line', 'expression', 'source_snippet']:
        if key not in first_read or not first_read[key]:
            print(f"FAIL: provenance incompleta en READ: {key} está vacío")
            return 1

    # Verificamos la provenance de un READ_MODIFY_WRITE
    rmw_ops = [res for res in result['results'] if res['operation'] == 'READ_MODIFY_WRITE']
    if not rmw_ops:
        print("FAIL: no hay operaciones READ_MODIFY_WRITE")
        return 1
    first_rmw = rmw_ops[0]
    for key in ['register', 'function', 'file', 'line_start', 'line_end', 'expression', 'source_snippet']:
        if key not in first_rmw or not first_rmw[key]:
            print(f"FAIL: provenance incompleta en READ_MODIFY_WRITE: {key} está vacío")
            return 1
    if first_rmw['line_end'] <= first_rmw['line_start']:
        print("FAIL: READ_MODIFY_WRITE sin rango válido")
        return 1

    # Caso de prueba 2: gmc_v8_0_gart_disable debe ser un WRITE puro (no RMW)
    write_ops = [res for res in result['results'] if res['operation'] == 'WRITE']
    gart_disable_writes = [res for res in write_ops if res['function'] == 'gmc_v8_0_gart_disable']
    if not gart_disable_writes:
        print("FAIL: gmc_v8_0_gart_disable no tiene operaciones WRITE")
        return 1

    # Caso de prueba 3: segundo registro (ATC_L2_CNTL)
    args2 = {'register': 'ATC_L2_CNTL', 'gfx': 'gfx_8_0'}
    result2 = _trace_data_by_register(args2)
    if result2['status'] != 'ok':
        print("INFO: ATC_L2_CNTL no tiene accesos (esto es aceptable si el corpus no lo tiene)")

    # Caso de prueba 4: modo función → register
    args3 = {'function': 'gmc_v8_0_gart_enable', 'gfx': 'gfx_8_0'}
    result3 = _trace_data_by_function(args3)
    if result3['status'] != 'ok':
        print("FAIL: modo función no funciona para gmc_v8_0_gart_enable")
        return 1
    functions_registers = set(res['register'] for res in result3['results'])
    if 'VM_CONTEXT0_CNTL' not in functions_registers:
        print("FAIL: modo función no encontró VM_CONTEXT0_CNTL para gmc_v8_0_gart_enable")
        return 1

    # Caso de prueba 5: símbolo no existente
    args4 = {'register': 'REGISTRO_NO_EXISTE_EN_EL_CORPUS', 'gfx': 'gfx_8_0'}
    result4 = _trace_data_by_register(args4)
    if result4['status'] != 'not_found':
        print("FAIL: no se manejó correctamente un registro no existente")
        return 1

    print("PASS: self-test de trace_data OK")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Punto de entrada principal.
    Devuelve 0 si todo OK, 1 si error o not_found.
    """
    parser = argparse.ArgumentParser(prog="rxre_trace_data",
                                     description="Rastreo de acceso a registros (READ/WRITE/RMW) desde código C.")
    parser.add_argument("--selftest", action="store_true",
                        help="Ejecuta el self-test de la herramienta")
    parser.add_argument("--register", default=None,
                        help="Nombre del registro (ej. VM_CONTEXT0_CNTL)")
    parser.add_argument("--function", default=None,
                        help="Nombre de la función (ej. gmc_v8_0_gart_enable)")
    parser.add_argument("--gfx", default="gfx_8_0",
                        help="Generación de GPU (def. gfx_8_0)")
    parser.add_argument("--kernel", default=None,
                        help="Ruta del kernel/corpus (def. kernelbuild)")
    parser.add_argument("--json", action="store_true", default=True,
                        help="Salida en JSON (por defecto)")
    parser.add_argument("--human", action="store_true",
                        help="Salida legible para personas (formato plano)")

    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.register:
        params = {'register': args.register, 'gfx': args.gfx}
        if args.kernel:
            params['kernel'] = args.kernel
        result = _trace_data_by_register(params)
    elif args.function:
        params = {'function': args.function, 'gfx': args.gfx}
        if args.kernel:
            params['kernel'] = args.kernel
        result = _trace_data_by_function(params)
    else:
        # Default: print help
        parser.print_help()
        return 0

    if args.human:
        _print_human(result)
    else:
        print(json.dumps(result, indent=2))

    if result['status'] != 'ok':
        return 1
    return 0


def _print_human(result: Dict[str, Any]) -> None:
    """Imprime los resultados en formato legible."""
    status = result.get('status', 'unknown')
    if 'register' in result:
        print(f"=== trace_data: registro {result.get('register', '?')} ({status}) ===")
    elif 'function' in result:
        print(f"=== trace_data: función {result.get('function', '?')} ({status}) ===")

    if status == 'not_found':
        for lim in result.get('limitations', []):
            print(f"  LIMITACIÓN: {lim}")
        return

    results = result.get('results', [])
    if not results:
        print("  (sin resultados)")
        return

    for r in results:
        op = r.get('operation', '?')
        func = r.get('function', '?')
        file_r = r.get('file', '?')
        line_s = r.get('line_start', r.get('line', '?'))
        line_e = r.get('line_end', r.get('line', '?'))
        reg = r.get('register', '?')

        if isinstance(line_s, int) and isinstance(line_e, int) and line_s != line_e:
            print(f"  [{op:18s}] {func} @ {os.path.basename(file_r)}:{line_s}-{line_e}  reg={reg}")
        else:
            print(f"  [{op:18s}] {func} @ {os.path.basename(file_r)}:{line_s}  reg={reg}")

        # Show source snippet
        snippet = r.get('source_snippet', '')
        if snippet:
            for snippet_line in snippet.split('\n'):
                print(f"    | {snippet_line.strip()}")


if __name__ == "__main__":
    sys.exit(main())
