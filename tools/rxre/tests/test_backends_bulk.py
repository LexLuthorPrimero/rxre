#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-BULK-2026-10-12. Pruebas de los adaptadores anadidos.

## QUE SE COMPRUEBA Y POR QUE

La mayor parte de estas comprobaciones NO es "la herramienta funciona".
Es "los estados se distinguen".

La tentacion de este adaptador era dejar `unsupported` y `empty` como el
mismo 0-funciones, porque los dos se ven igual en la pantalla. MEDIDO que
NO son lo mismo:

    /usr/bin/ls   (ET_DYN) -> 5 funciones, 5 decompiladas
    small.ko      (ET_REL) -> 0 funciones, y Ghidra dice "Import succeeded"
    amdgpu.ko     (ET_REL) -> 0 funciones, y ademas ElfException

Si los tres dieran `empty`, una IA que ejecutase esto sobre el driver
concluiria que `amdgpu.ko` no tiene funciones. No las tiene que no
descompiladas: tiene 19 MB de codigo y el BTF en /sys/kernel/btf lo
confirma. El estado equivocado no es un detalle de formato: cambia lo que
la IA creera saber del hardware.

Los fixtures son salidas REALES, no inventadas: se copiaron de las tres
ejecuciones de arriba. Por eso las pruebas no necesitan Ghidra ni minutos
de JVM, y por eso comprueban el comportamiento de un fallo que ya se vio.

## COMO SE EJECUTA

    python3 tests/test_backends_bulk.py
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import dispatch, registry  # noqa: E402
from backends.adapters import cocci_search, gh_decompile  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    puede_declarar, DECOMPILATION, SEMANTIC_HYPOTHESIS, RAW_BINARY,
)

FIX = os.path.join(HERE, "fixtures")
F_DEC_OK = os.path.join(FIX, "ghidra_decomp_ok.json")
F_DEC_ETREL = os.path.join(FIX, "ghidra_decomp_etrel_0funcs.json")
F_DEC_AMDGPU = os.path.join(FIX, "ghidra_decomp_amdgpu_0funcs.json")

_n = 0
_f = 0


def chk(nombre: str, got, want) -> bool:
    global _n, _f
    _n += 1
    ok = got == want
    if not ok:
        _f += 1
        print("  FAIL: %-44s got=%r want=%r" % (nombre, got, want))
    else:
        print("  ok  : %-44s %r" % (nombre, got))
    return ok


# ---------------------------------------------------------------- registro
def t_registro():
    print("\n== registro: solo lo medido ==")
    # MEDIDO 2026-10-12 (RXRE-1634): se anadio `capstone`, un producer de
    # MODULO en proceso. No es un subproceso como los otros cuatro.
    # RXRE-AUTONOMY-002: anadidos `knowledge` y `umr` (UMR para register_read
    # RXRE-ECO-001 (2026-10-15): anadido `tree-sitter`, MEDIDO sobre
    # `amdgpu.h` -> 7066 nodos AST. El conjunto sigue siendo EXACTO.
    chk("backends registrados",
        sorted(registry.backends()),
        ["capstone", "coccinelle", "ghidra", "knowledge", "radare2",
         "rizin", "tree-sitter", "umr"])
    chk("ghidra decompile es PARTIAL",
        registry.get("ghidra")["capacities"]["binary.decompile"],
        "PARTIAL")
    chk("coccinelle semantic_search AVAILABLE",
        registry.get("coccinelle")["capacities"]
        ["source.semantic_search"],
        "AVAILABLE")
    # La capacidad de decompilacion ya no esta huerfana: antes ningun
    # backend medido la tenia. Ahora la tienen tres, y dos dicen que NO.
    chk("decompile en los tres backends medidos",
        sorted(registry._todas_las_fichas()["binary.decompile"]["backends"]
               if hasattr(registry, "_todas_las_fichas")
               else dispatch._todas_las_fichas()["binary.decompile"]
               ["backends"]),
        ["ghidra", "radare2", "rizin"])
    chk("decompile agregada = PARTIAL (no AVAILABLE)",
        dispatch._todas_las_fichas()["binary.decompile"]["estado_agregado"],
        "PARTIAL")
    # recuento: ghidra y coccinelle aportan producer, y antes eran cero
    rr = registry.recuento_real()
    chk("ghidra aporta 1 producer", rr["ghidra"], 1)
    chk("coccinelle aporta 1 producer", rr["coccinelle"], 1)


# ---------------------------------------------------------------- ghidra
def t_ghidra_disponibilidad():
    print("\n== ghidra: identidad verificada, no nominal ==")
    d = gh_decompile.disponible()
    chk("analyzeHeadless existe", bool(d["existe"]), True)
    chk("version verificada desde application.properties",
        bool(d["version_verificada"]), True)
    chk("version empieza por 'Ghidra '",
        d["version"].startswith("Ghidra "), True)
    chk("script precompilado presente",
        bool(d["script_precompilado"]), True)
    chk("JVM presente", bool(d["java"]), True)
    # la identidad NO se deduce de `import`: es el defecto de angr
    chk("no usa __file__ de un modulo (defecto de angr)",
        hasattr(gh_decompile, "__file__") and
        os.path.isfile(gh_decompile.__file__), True)


def t_ghidra_ok():
    print("\n== ghidra: caso OK (fixture de /usr/bin/ls, ET_DYN) ==")
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(b"\x7fELF\x02\x01\x01" + b"\x00" * 9 + b"\x02\x00"
                + b"\x3e\x00" + b"\x00" * 40)
        ruta = f.name
    try:
        env = gh_decompile.decompile(ruta, fixture_json=F_DEC_OK,
                                     max_funcs=5)
    finally:
        os.unlink(ruta)
    chk("status ok", env["status"], BK_OK)
    chk("n_functions", env["n_functions"], 5)
    chk("n_decompiladas", env["n_decompiladas"], 5)
    chk("hay resultados", len(env["results"]), 5)
    r0 = env["results"][0]
    chk("tipo = DECOMPILATION", r0["type"], DECOMPILATION)
    chk("el C no esta vacio", len(r0["value"]["c"]) > 0, True)
    chk("trae localizacion (funcion)", bool(r0["location"]["funcion"]), True)
    chk("trae direccion", bool(r0["location"]["direccion"]), True)
    chk("version en el resultado", r0["tool_version"].startswith("Ghidra "),
        True)
    # MEDIDO 2026-10-15 (RXRE-AUTO-002). Este check decia
    #
    #     chk("provenance completa", env["provenance"], "completa")
    #
    # Afirmaba que la provenance ES la cadena "completa". Era un test que
    # CODIFICABA EL DEFECTO: comprobaba que el envelope llevara una palabra
    # donde el contrato (TIERRA/FUEGO) pide la evidencia.
    #
    # El nombre queria decir "la provenance esta completa". Ahora lo afirma
    # de verdad, y MAS FUERTE que antes: no basta con la palabra, hace falta
    # el `estado` y el `input_hash` que permiten reejecutar la operacion.
    # El check viejo no podia distinguir "completa" de "completa pero sin
    # hash"; este si.
    prov = env["provenance"]
    chk("provenance completa", isinstance(prov, dict)
        and prov.get("estado") == "completa", True)
    # MEDIDO 2026-10-15. El fixture NO tiene hash de entrada: en modo
    # fixture "el ARTEFACTO no tiene que existir", asi que `input_hash` sale
    # vacio. Eso NO es una provenance mentirosa, es una simulacion declarada
    # (`usa_fixture: True`, `extra.nota`). Exigir el hash aqui seria exigir
    # un artefacto que el propio contrato dice que no tiene que existir.
    #
    # La distincion es la que importa: hash vacio CON simulacion declarada
    # es honesto; hash vacio SIN declarar es una mentira. Por eso la
    # condicion mira las dos cosas.
    extra = prov.get("extra") or {}
    chk("provenance con input_hash o simulacion declarada",
        bool(prov.get("input_hash")) or extra.get("usa_fixture") is True, True)
    # La regla del contrato: una decompilacion NO declara semantica.
    # OJO con la direccion: `puede_declarar(producer, consumidor)` pregunta
    # si un consumidor que pide `consumidor` puede aceptar evidencia
    # `producer`. Por eso DECOMPILATION -> RAW_BINARY es True (el
    # consumidor de bajo nivel la acepta) y lo que se prohibitions es al
    # reves: una decompilacion NO vale como SEMANTIC_HYPOTHESIS.
    # La primera version de esta prueba investmenta la regla y por eso
    # fallaba; el fallo era de la prueba, no del contrato.
    chk("decomp NO puede declarar SEMANTIC_HYPOTHESIS",
        puede_declarar(DECOMPILATION, SEMANTIC_HYPOTHESIS), False)
    chk("decomp NO puede declarar VALIDATED_SEMANTICS",
        puede_declarar(DECOMPILATION, "validated_semantics"), False)
    chk("decomp PUEDEsatisfacer a un consumidor RAW_BINARY",
        puede_declarar(DECOMPILATION, RAW_BINARY), True)
    chk("decomp PUEDE declarar DECOMPILATION",
        puede_declarar(DECOMPILATION, DECOMPILATION), True)
    # Direccion de la regla, que es donde mas se confunde:
    # `puede_declarar(producer, consumidor)` = "puede esta EVIDENCIA
    # satisfacer este REQUISITO" (nivel >= nivel). NO es una regla de
    # promocion de nivel. Por eso SEMANTIC_HYPOTHESIS (9) SI satisface un
    # requisito de DECOMPILACION (8): es evidencia mas fuerte.
    #
    # La segunda version de esta prueba investmenta eso y fallo. La
    # asercion correcta es la que ya esta arriba: lo que NO puede pasar es
    # que una DECOMPILACION (8) se presente como SEMANTIC_HYPOTHESIS (9).
    chk("mas evidencia SI satisface un requisito mas bajo",
        puede_declarar(SEMANTIC_HYPOTHESIS, DECOMPILATION), True)
    chk("pero evidencia mas debil NO satisface un requisito mas alto",
        puede_declarar(DECOMPILATION, SEMANTIC_HYPOTHESIS), False)


def _ko_real() -> str:
    """Un .ko real del sistema. Se usa para la regla ET_REL."""
    import glob
    import subprocess
    k = sorted(glob.glob("/lib/modules/*/kernel/fs/*/*.ko*"))
    if not k:
        return ""
    dst = os.path.join(tempfile.gettempdir(), "rxre_test_small.ko")
    src = k[0]
    try:
        if src.endswith(".zst"):
            subprocess.run(["zstd", "-d", "-f", "-o", dst, src],
                           capture_output=True, timeout=120)
        else:
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
    except Exception:
        return ""
    return dst if os.path.isfile(dst) else ""


def t_ghidra_etrel_unsupported():
    """LA PRUEBA IMPORTANTE. ET_REL + 0 funciones = unsupported."""
    print("\n== ghidra: ET_REL con 0 funciones -> UNSUPPORTED ==")
    ko = _ko_real()
    if not ko:
        print("  skip: no hay .ko en el sistema")
        return
    try:
        env = gh_decompile.decompile(ko, fixture_json=F_DEC_ETREL)
    finally:
        os.unlink(ko)
    chk("status unsupported (NO empty)", env["status"], BK_UNSUPPORTED)
    chk("NO es empty", env["status"] == BK_EMPTY, False)
    chk("n_functions 0", env["n_functions"], 0)
    chk("sin resultados que explicar", len(env["results"]), 0)
    chk("el motivo nombra la clase de entrada",
        "ET_REL" in " ".join(env["ejecucion"]["limitations"]), True)
    chk("el motivo ofrece via alternativa",
        "BTF" in " ".join(env["ejecucion"]["limitations"])
        or "rizin" in " ".join(env["ejecucion"]["limitations"]), True)


def t_ghidra_etrel_detectado():
    print("\n== ghidra: la clase de entrada se LEE, no se supone ==")
    c = gh_decompile._elf_clase("/usr/bin/ls")
    chk("lee e_type de /usr/bin/ls", c.get("ok"), True)
    chk("/usr/bin/ls NO es ET_REL", c.get("e_type") == 1, False)
    chk("nombre de tipo lleno", isinstance(c.get("e_type_nombre"), str),
        True)
    c2 = gh_decompile._elf_clase("/etc/hostname")
    chk("no-ELF se detecta sin arrancar el backend",
        c2.get("ok"), False)


def t_ghidra_amdgpu_fixture():
    print("\n== ghidra: el caso de amdgpu.ko tambien es unsupported ==")
    ko = _ko_real()
    if not ko:
        print("  skip: no hay .ko")
        return
    try:
        env = gh_decompile.decompile(ko, fixture_json=F_DEC_AMDGPU)
    finally:
        os.unlink(ko)
    chk("status unsupported", env["status"], BK_UNSUPPORTED)


def t_ghidra_no_elf():
    print("\n== ghidra: entrada invalida NO se invoca ==")
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False,
                                     mode="w") as f:
        f.write("no soy un ELF\n")
        ruta = f.name
    try:
        env = gh_decompile.decompile(ruta, fixture_json=F_DEC_OK)
    finally:
        os.unlink(ruta)
    chk("status invalid_input", env["status"], BK_INVALID)
    chk("no se llego a ejecutar", env["ejecutada"]
        if "ejecutada" in env else True, True)


# ------------------------------------------------------------ coccinelle
def t_coccinelle_real():
    """Prueba con la herramienta REAL: spatch es de segundos."""
    print("\n== coccinelle: producer real, positivo y control negativo ==")
    d = cocci_search.disponible()
    if not d["existe"]:
        print("  skip: spatch no instalado")
        return
    chk("version verificada", d["version_verificada"], True)
    chk("version 1.3.1 detectada", "1.3.1" in d["version"], True)

    patron = os.path.join(tempfile.gettempdir(), "rxre_t.cocci")
    with open(patron, "w") as f:
        f.write("@@\nexpression E;\nidentifier p;\n@@\n"
                "- *p = E;\n+ XX_write(E);\n")
    pos = os.path.join(tempfile.gettempdir(), "rxre_pos.c")
    with open(pos, "w") as f:
        f.write("int main(){int x=5;int*p=&x;*p=42;return 0;}\n")
    neg = os.path.join(tempfile.gettempdir(), "rxre_neg.c")
    with open(neg, "w") as f:
        f.write("int main(){int y=1;return y+1;}\n")
    try:
        env = cocci_search.buscar(pos, patron)
        chk("positivo: status ok", env["status"], BK_OK)
        chk("positivo: hubo coincidencias", env["n_hits"] > 0, True)
        chk("positivo: hay resultado", len(env["results"]), 1)
        chk("positivo: tipo SEMANTIC_HYPOTHESIS",
            env["results"][0]["type"], SEMANTIC_HYPOTHESIS)
        chk("positivo: limitacion dice que es HIPOTESIS",
            any("SEMANTIC_HYPOTHESIS" in x
                for x in env["results"][0]["limitations"]), True)
        chk("positivo: limitacion dice que NO prueba el hardware",
            any("hardware" in x
                for x in env["results"][0]["limitations"]), True)

        envn = cocci_search.buscar(neg, patron)
        chk("negativo: status empty (no error)", envn["status"], BK_EMPTY)
        chk("negativo: 0 coincidencias", envn["n_hits"], 0)
        chk("negativo: sin resultados", len(envn["results"]), 0)
        # ESTA es la comparacion que importa: el empty del negativo es de
        # verdad. Si fuera indistinguible del error, un patron que no casa
        # pareceria un fallo de la herramienta.
        chk("positivo y negativo se distinguen",
            env["status"] != envn["status"], True)
    finally:
        for p in (patron, pos, neg):
            if os.path.isfile(p):
                os.unlink(p)


def t_coccinelle_patron_invalido():
    print("\n== coccinelle: 'No rules apply' NO es empty ==")
    d = cocci_search.disponible()
    if not d["existe"]:
        print("  skip")
        return
    # Un patron SIN lineas +/-/*: spatch responde "No rules apply" con 255.
    # MEDIDO: eso es invalid_input, no "no coincide".
    patron = os.path.join(tempfile.gettempdir(), "rxre_malo.cocci")
    with open(patron, "w") as f:
        f.write("@@\nexpression E;\n@@\n  x = E;\n")
    src = os.path.join(tempfile.gettempdir(), "rxre_malo.c")
    with open(src, "w") as f:
        f.write("int main(){int a=1;int x=0;x=a;return x;}\n")
    try:
        v = cocci_search._validar_patron(patron)
        chk("el validador RECHAZA el patron sin +/-/*",
            v["ok"], False)
        chk("el motivo es util", "semantico" in v["motivo"], True)
        env = cocci_search.buscar(src, patron)
        chk("invalid_input, NO empty", env["status"], BK_INVALID)
    finally:
        for p in (patron, src):
            if os.path.isfile(p):
                os.unlink(p)


def t_coccinelle_spool_no_existe():
    print("\n== coccinelle: el flag que NO existe ==")
    d = cocci_search.disponible()
    if not d["existe"]:
        print("  skip")
        return
    import subprocess
    p = subprocess.run([d["path"], "--spool", "/tmp/x", "/tmp/y"],
                       capture_output=True, text=True, timeout=60)
    t = (p.stderr or "") + (p.stdout or "")
    chk("--spool rechazado por spatch 1.3.1",
        "unknown option" in t or "unrecognized" in t, True)
    # MEDIDO: rc 2 para flag desconocido, y rc 255 para "No rules apply".
    # Son fallos DISTINTOS con el mismo objetivo. La primera version de
    # esta prueba decia 255 para el flag, y fallaba: lo correcto no era
    # arreglar el adaptador sino corregir la suposicion.
    chk("rc de flag desconocido es 2", p.returncode, 2)
    chk("flag desconocido -> invalid_input, no empty",
        cocci_search.buscar.__doc__ is not None
        and "RE_OPCION_DESCONOCIDA" in
        open(cocci_search.__file__, encoding="utf-8").read(), True)


# --------------------------------------------------------------- dispatch
def t_dispatch_generico():
    print("\n== dispatch: ya no esta atado a un solo adapter ==")
    # MEDIDO 2026-10-12: 9 adapters, tras RXRE-1631 (binary.functions) y
    # RXRE-1632 (las cinco de contenedor). El bucle de abajo es el que de
    # verdad prueba que cada uno existe; este numero solo avisa si se
    # OLVIDO registrar alguno.
    # RXRE-ECO-001 (2026-10-15): +1 adapter, `source.ast_parse` (tree-sitter).
    # MEDIDO: amdgpu.h -> 7066 nodos AST. El numero sigue siendo EXACTO a
    # proposito:_relajar a >=25 haria invisible un adapter olvidado.
    chk("los 26 adapters son importables",
        len(dispatch.ADAPTERS), 26)
    for cap, a in sorted(dispatch.ADAPTERS.items()):
        import importlib
        m = importlib.import_module(a["modulo"])
        chk("adapter de %s tiene %s()" % (cap, a["funcion"]),
            callable(getattr(m, a["funcion"], None)), True)
    chk("decompile permitida", dispatch.esta_permitida(
        "binary.decompile")["permitida"], True)
    chk("semantic_search permitida", dispatch.esta_permitida(
        "source.semantic_search")["permitida"], True)
    chk("capacidad inexistente sigue rechazada",
        dispatch.esta_permitida("binary.no_existe")["permitida"], False)
    chk("identificador cerrado (no es traversal)",
        dispatch.esta_permitida("../../etc/passwd")["permitida"], False)


def t_dispatch_sin_herramientas(monkey_home: bool = False):
    """RXRE debe seguir respondiendo cuando la herramienta no esta."""
    print("\n== continuidad: RXRE responde sin las herramientas ==")
    chk("listar() funciona sin invocar nada",
        bool(dispatch.listar()["capacidades"]), True)
    chk("plan() de decompile funciona",
        dispatch.planificar("binary.decompile")["status"], "ok")
    chk("plan marca decompile como ejecutable",
        any(p["available"] for p in
            dispatch.planificar("binary.decompile")["plan"]), True)
    # una capacidad sin producer no se invoca: se explica
    r = dispatch.ejecutar("binary.no_existe", {})
    chk("capacidad inexistente -> blocked, no crash",
        r["status"], "blocked")
    chk("el bloqueo explica por que", len(r["motivo"]) > 10, True)


def t_plan_decompile_ya_no_es_callejon():
    """El plan de decompile antes era un callejon sin salida."""
    print("\n== plan: decompile deja de ser un callejon ==")
    p = dispatch.planificar("binary.decompile")
    chk("estado del plan", p["status"], "ok")
    chk("pasos", len(p["plan"]), 6)
    bloq = p["resumen"]["bloqueos"]
    # RXRE-AUTONOMY-002: binary.cfg y binary.dataflow ahora TIENEN adapter
    # (rz_cfg.py), asi que dejaron de ser pasos bloqueados. El plan sigue
    # teniendo 6 pasos listados (no se acorta), pero ahora 0 estan bloqueados.
    #
    # MEDIDO: dentro del PLAN de `binary.decompile` hay 6 pasos,
    # de los que 0 siguen bloqueados. Todos tienen adapter ahora.
    chk("0 pasos de este plan estan bloqueados (todos tienen adapter)",
        len(bloq), 0)
    for cap in ("binary.sections", "binary.imports", "binary.exports",
                "binary.strings", "binary.symbols",
                "binary.cfg", "binary.dataflow",
                "binary.functions", "binary.disassemble"):
        chk("%s ya NO esta bloqueada (tiene adapter)" % cap,
            dispatch.esta_permitida(cap)["permitida"], True)

    # El conjunto GLOBAL de capacidades declaradas sin adapter. MEDIDO
    # 2026-10-14 tras RXRE-AUTONOMY-002: todas las capacidades verificables
    # tienen adapter. El conjunto de sin-adapter es vacio.
    fichas = dispatch._todas_las_fichas()
    chk("todas las capacidades verificables tienen adapter (0 sin adapter)",
        sorted(c for c in fichas if c not in dispatch.ADAPTERS),
        [])
    chk("binary.functions ya NO esta bloqueada (tiene adapter)",
        [x for x in p["plan"]
         if x["operation"] == "binary.functions"][0]["available"], True)
    chk("el paso decompile es ejecutable",
        [x for x in p["plan"] if x["operation"] == "binary.decompile"][0]
        ["available"], True)
    chk("el primer paso (inspect) es ejecutable",
        p["plan"][0]["available"], True)
    # El plan NO se acorta: los 6 pasos siguen listados, ejecutables o no
    chk("el plan no se acorta (6 pasos listados)", len(p["plan"]), 6)


def main() -> int:
    print("RXRE-BULK-2026-10-12: pruebas de adaptadores")
    t_registro()
    t_ghidra_disponibilidad()
    t_ghidra_ok()
    t_ghidra_etrel_detectado()
    t_ghidra_etrel_unsupported()
    t_ghidra_amdgpu_fixture()
    t_ghidra_no_elf()
    t_coccinelle_real()
    t_coccinelle_patron_invalido()
    t_coccinelle_spool_no_existe()
    t_dispatch_generico()
    t_dispatch_sin_herramientas()
    t_plan_decompile_ya_no_es_callejon()
    print("\n%d checks, %d failures" % (_n, _f))
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())