#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-013 — la cobertura GFX8 tiene que medir ESTE arbol, con su unidad declarada.

La corrida de `artifacts/rxre_cobertura_gfx8.jsonl` (2633/2633 ok) la produjo un
script cuya RAIZ era una constante absoluta: /home/lucas/Escritorio/
RX550-INVESTIGACION.  Ese arbol tiene OTRO RXRE.  La medicion era de un arbol
que no es el que contiene la herramienta que la produce.

Este test fija las tres cosas que una medicion tiene que declarar:  el arbol,
la unidad y el registro de procedencia.

ORACLE INTERNO : el contrato del propio script (RAIZ derivada de __file__,
                  verificacion de que el 'cli' importado vive bajo RAIZ,
                  relacion byte_offset = valor * 4 por registro).
ORACLE EXTERNO : el arbol de destino.  Si el 'cli' importado es de fuera de
                  RAIZ, la medicion es de otro arbol aunque todo lo demas pase.
                  Y la semantica del productor:  el reg_resolve de RAIZ tiene
                  que usar * 4 y no puede tener >> 2.  Si vuelve la unidad
                  invertida, el artefacto vuelve a mentir aunque las cifras
                  coincidan.

Y una regla que este test aprende por el camino:  un artefacto en el que no
ha salido NINGUN valor no demuestra nada sobre la unidad.  Por eso la
transformacion se comprueba tambien en proceso,  sobre un valor inyectado,  y
no solo sobre lo que la corrida haya tengas la suerte de producir.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
TOOL = os.path.join(RAIZ, "tools", "rxre_cobertura_gfx8.py")
DICC_REL = ("RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/"
            "gca/gfx_8_0_d.h")

FALLOS = []
V = []


def v(nombre, ok, detalle=""):
    print("  [%s] %s" % ("OK " if ok else "NO ", nombre))
    V.append(nombre)
    if not ok:
        if detalle:
            print("        %s" % str(detalle)[:400])
        FALLOS.append(nombre)


def ejecuta(argv, cwd=RAIZ, env=None):
    return subprocess.run([sys.executable, "-B"] + argv, cwd=cwd,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                                   **(env or {})),
                          capture_output=True, text=True, timeout=900)


def main():
    fuente = open(TOOL, encoding="utf-8").read()

    # ══ 1 · el arbol ═════════════════════════════════════════════════════
    v("la herramienta NO fija una ruta absoluta de arbol como RAIZ",
      'RAIZ = "/home' not in fuente)
    v("RAIZ se deriva de __file__",
      "os.path.dirname(os.path.dirname(os.path.abspath(__file__)))" in fuente)
    v("el diccionario existe bajo ESE RAIZ",
      os.path.isfile(os.path.join(RAIZ, DICC_REL)),
      "falta %s bajo %s" % (DICC_REL, RAIZ))

    # ══ 2 · la verificacion de que el RXRE medido es el de RAIZ ═════════
    v("el script verifica donde se importo 'cli'",
      "verifica_arbol" in fuente and "INVALID_TREE" in fuente)
    v("la verificacion compara rutas ABSOLUTAS, no subcadenas",
      "os.path.abspath(cli.__file__)" in fuente
      and "os.path.abspath(os.path.join(RAIZ" in fuente)

    # ══ 3 · la unidad, oraculo externo ══════════════════════════════════
    reg = open(os.path.join(RAIZ, "tools/reg_resolve.py"), encoding="utf-8").read()
    v("el reg_resolve de RAIZ calcula byte_offset = valor * 4",
      'out["byte_offset"] = hex(val * 4)' in reg)
    v("el reg_resolve de RAIZ NO divide por 4", "val >> 2" not in reg)
    v("la herramienta declara la unidad y la derivacion",
      'UNIDAD = "dword_register_index"' in fuente
      and 'DERIVACION_BYTE = "byte_offset = valor * 4"' in fuente)

    # ══ 4 · una corrida real, pequena, con procedencia ═══════════════════
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13-") as tmp:
        sal = os.path.join(tmp, "c.jsonl")
        met = os.path.join(tmp, "c.meta.json")
        p = ejecuta([TOOL, "--muestra=3", "--salida=" + sal, "--meta=" + met])
        v("la corrida termina sin error", p.returncode == 0, p.stderr[-500:])

        if not os.path.isfile(sal) or not os.path.isfile(met):
            v("produce artefacto y procedencia", False,
              "faltan %s / %s" % (sal, met))
            return 1

        filas = [json.loads(x) for x in open(sal, encoding="utf-8") if x.strip()]
        v("el artefacto tiene una linea por registro de la muestra",
          len(filas) == 3, "len=%d" % len(filas))
        v("cada linea declara la unidad",
          all(f.get("unidad") == "dword_register_index" for f in filas))
        con_valor = [f for f in filas if isinstance(f.get("elegido"), int)]
        v("si hay valor, el byte offset sale de valor * 4 y NUNCA de >> 2",
          all(f.get("byte_offset_derivado") == f["elegido"] * 4
              and f.get("byte_offset_derivado") != f["elegido"] >> 2
              for f in con_valor),
          "con_valor=%d de %d" % (len(con_valor), len(filas)))

        m = json.load(open(met, encoding="utf-8"))
        for clave in ("source_root", "source_root_origen", "source_git_head",
                      "reg_resolve_path", "reg_resolve_sha256",
                      "producer_sha256", "unit_semantics", "generation",
                      "timestamp", "producer_command", "denominador",
                      "reparto", "fallback_byte_offset", "rxre_importado"):
            v("la procedencia declara %s" % clave, clave in m)
        v("la procedencia dice que arbol se midio",
          m.get("source_root") == RAIZ,
          "source_root=%s, esperado %s" % (m.get("source_root"), RAIZ))
        v("la procedencia dice que RXRE se importo",
          os.path.abspath(m.get("rxre_importado", "")) ==
          os.path.join(RAIZ, "tools/rxre/cli.py"),
          "rxre_importado=%s" % m.get("rxre_importado"))
        v("el sha256 de reg_resolve corresponde al fichero de RAIZ",
          m.get("reg_resolve_sha256") == hashlib.sha256(
              open(os.path.join(RAIZ, "tools/reg_resolve.py"), "rb")
              .read()).hexdigest())
        v("el sha256 del productor corresponde a la herramienta de RAIZ",
          m.get("producer_sha256") == hashlib.sha256(
              open(TOOL, "rb").read()).hexdigest())
        v("la unidad declarada es indice dword, con la conversion * 4",
          m["unit_semantics"]["valor_#define"] == "dword_register_index"
          and "* 4" in m["unit_semantics"]["byte_offset"])
        v("la procedencia prohibe explicitamente >> 2",
          ">>" in m["unit_semantics"]["prohibido"])
        v("la procedencia acota el alcance: derivado, no observado",
          "no observado" in m["unit_semantics"]["alcance"])
        v("el denominador lo declara el diccionario, con su entrada",
          m["denominador"]["entradas"] == 2633,
          "entradas=%s" % m["denominador"].get("entradas"))

        # ── el fallback muerto es una MEDICION, no una lectura ────────────
        fb = m["fallback_byte_offset"]
        v("el fallback byte_offset se declara DEAD / NOT_REACHED",
          fb["runtime_path"] == "DEAD / NOT_REACHED")
        v("el fallback NO se disparo en la corrida",
          fb["disparado"] == 0, "disparado=%s" % fb.get("disparado"))

    # ══ 5 · la unidad, contra el PRODUCTOR ═════════════════════════════
    kern = os.path.join(RAIZ, "RESEARCH/working/linux-7.1.3")
    amd = os.path.join(kern, "drivers/gpu/drm/amd")
    vistos = {}
    for sym, idx, byte in (("mmSMC_IND_INDEX_11", 0x1AC, 0x6B0),
                           ("mmSMC_IND_DATA_11", 0x1AD, 0x6B4)):
        p = ejecuta([os.path.join(RAIZ, "tools/reg_resolve.py"),
                     "--kernel", kern, "--amd-root", amd,
                     "--gfx", "gfx_8_0", "--reg", sym, "--json"])
        if p.returncode != 0 or not p.stdout.strip():
            v("reg_resolve responde para %s" % sym, False, p.stderr[-300:])
            continue
        r = json.loads(p.stdout)["results"][0]
        vistos[sym] = r
        v("%s se clasifica como indice dword" % sym,
          r.get("symbol_class") == "dword_index_de_mm",
          str(r.get("symbol_class")))
        v("%s declara la unidad como indice dword" % sym,
          "dword register index" in (r.get("unit") or ""))
        v("%s: value ES el indice dword, no el byte offset" % sym,
          r.get("value") is not None
          and int(r["value"], 16) == int(r["dword_index"], 16) == idx,
          "value=%s dword_index=%s" % (r.get("value"), r.get("dword_index")))
        v("%s: byte_offset = indice * 4" % sym,
          int(r["byte_offset"], 16) == int(r["dword_index"], 16) * 4 == byte,
          "byte_offset=%s" % r.get("byte_offset"))
        v("%s: byte_offset DISTINTO del indice (la unidad se distingue)" % sym,
          r.get("byte_offset") != r.get("dword_index"))
        v("%s: el byte offset NO sale de >> 2" % sym,
          int(r["byte_offset"], 16) != int(r["value"], 16) >> 2)
    if len(vistos) == 2:
        a, b = vistos["mmSMC_IND_INDEX_11"], vistos["mmSMC_IND_DATA_11"]
        v("los dos registros siguen siendo DISTINTOS en las dos unidades",
          a["dword_index"] != b["dword_index"]
          and a["byte_offset"] != b["byte_offset"])
        v("y >> 2 los habria fundido en uno solo (por eso esta prohibido)",
          (int(a["value"], 16) >> 2) == (int(b["value"], 16) >> 2))

    # ══ 6 · la herramienta en proceso: la transformacion, sin depender ══
    # ══    de que ningun registro haya salido con valor                  ══
    spec = importlib.util.spec_from_file_location("cob13_tool", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.RAZ = RAIZ
    CONSULTA_REAL = mod.consulta_rxre

    mod.consulta_rxre = lambda n: (0x1AD, 3, "ok", "")
    fila = mod.veredicto("mmSMC_IND_DATA_11", 0x1AD)
    v("veredicto declara la unidad por registro",
      fila.get("unidad") == "dword_register_index")
    v("veredicto deriva el byte offset del valor ELEGIDO por * 4",
      fila.get("byte_offset_derivado") == 0x1AD * 4,
      "byte_offset_derivado=%s" % fila.get("byte_offset_derivado"))
    v("veredicto NO deriva el byte offset por >> 2",
      fila.get("byte_offset_derivado") != 0x1AD >> 2)

    # El productor elige 0x6B (el error de unidad de 1589).  El byte offset
    # tiene que derivarse de ELEGIDO, no de esperado:  si se derivara de
    # esperado, un valor equivocado daria un byte offset plausible.
    mod.consulta_rxre = lambda n: (0x6B, 3, "ok", "")
    fila = mod.veredicto("mmSMC_IND_DATA_11", 0x1AD)
    v("con el valor equivocado, el veredicto DIVERGE",
      fila.get("estado") == "DIVERGE" and fila.get("delta") == 0x6B - 0x1AD,
      "estado=%s delta=%s" % (fila.get("estado"), fila.get("delta")))
    v("el byte offset se deriva de ELEGIDO, no de esperado",
      fila.get("byte_offset_derivado") == 0x6B * 4,
      "byte_offset_derivado=%s (esperado %d si saliera de ELEGIDO)"
      % (fila.get("byte_offset_derivado"), 0x6B * 4))

    # ══ 7 · el contador del fallback muerto ═════════════════════════════
    # No basta con leer el codigo y decir "esa rama no se ejecuta".  Se le
    # inyecta un 'cli' cuyo chosen NO trae 'value' —  la unica forma de que
    # la rama se alcance —  y se exige que el contador LO CUENTE.
    class _CliFalso:
        @staticmethod
        def main(argv=None):
            print(json.dumps({"status": "ok", "results": [
                {"definitions": [], "chosen": {"file": "x", "rel": "x"}}]}))
    antes = mod.FALLBACK_DEAD["disparado"]
    guardado = sys.modules.get("cli")
    sys.modules["cli"] = _CliFalso
    try:
        CONSULTA_REAL("mmSMC_IND_DATA_11")
    finally:
        if guardado is None:
            sys.modules.pop("cli", None)
        else:
            sys.modules["cli"] = guardado
    v("el contador CUENTA las ejecuciones de la rama muerta",
      mod.FALLBACK_DEAD["disparado"] == antes + 1,
      "antes=%d despues=%d" % (antes, mod.FALLBACK_DEAD["disparado"]))
    v("y la rama devuelve el byte_offset ausente, sin inventarlo",
      mod.FALLBACK_DEAD["registros"] >= 1)

    # ══ 8 · los tres candados del arbol, uno por caso ═════════════════
    # Cada caso aisla UN candado:  todo lo demas esta presente.  Si un caso
    # dejara pasar al mutante que suprime ESE candado,  es porque otro
    # candado lo tapaba y este no prueba nada.
    def _arbol(tmp, dicc=False, cli=False, regres=False):
        os.makedirs(os.path.join(tmp, "tools"), exist_ok=True)
        open(os.path.join(tmp, "tools/rxre_cobertura_gfx8.py"), "w",
             encoding="utf-8").write(fuente)
        if dicc:
            d = os.path.join(tmp, DICC_REL)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            open(d, "w", encoding="utf-8").write("")
        if cli:
            os.makedirs(os.path.join(tmp, "tools/rxre"), exist_ok=True)
            open(os.path.join(tmp, "tools/rxre/cli.py"), "w",
                 encoding="utf-8").write("def main(argv=None):\n    pass\n")
        if regres:
            shutil.copy(RAIZ + "/tools/reg_resolve.py",
                        os.path.join(tmp, "tools/reg_resolve.py"))
        return os.path.join(tmp, "tools/rxre_cobertura_gfx8.py")

    # 8a · sin RXRE:  dictionary y reg_resolve presentes,  cli.py ausente.
    #     Solo el candado de cli.py puede negarse.
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13b-") as tmp:
        copia = _arbol(tmp, dicc=True, cli=False, regres=True)
        p = ejecuta([copia, "--muestra=1", "--raiz=" + tmp], cwd=tmp)
        v("[8a] sin tools/rxre/cli.py se niega con INVALID_TREE",
          p.returncode != 0 and "INVALID_TREE" in (p.stderr + p.stdout),
          "rc=%s err=%s" % (p.returncode, (p.stderr + p.stdout)[-300:]))

    # 8b · sin diccionario:  RXRE y reg_resolve presentes.  Solo el candado
    #     del diccionario puede negarse.
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13d-") as tmp:
        copia = _arbol(tmp, dicc=False, cli=True, regres=True)
        p = ejecuta([copia, "--muestra=1", "--raiz=" + tmp], cwd=tmp)
        v("[8b] sin diccionario se niega con INVALID_TREE",
          p.returncode != 0 and "INVALID_TREE" in (p.stderr + p.stdout),
          "rc=%s err=%s" % (p.returncode, (p.stderr + p.stdout)[-300:]))

    # 8c · sin el productor:  diccionario y cli.py presentes,  reg_resolve
    #     ausente.  Solo el candado del productor puede negarse.
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13g-") as tmp:
        copia = _arbol(tmp, dicc=True, cli=True, regres=False)
        p = ejecuta([copia, "--muestra=1", "--raiz=" + tmp], cwd=tmp)
        v("[8c] sin tools/reg_resolve.py se niega con INVALID_TREE",
          p.returncode != 0 and "INVALID_TREE" in (p.stderr + p.stdout),
          "rc=%s err=%s" % (p.returncode, (p.stderr + p.stdout)[-300:]))

    # 8d · arbol vacio del todo:  tiene que negarse tambien,  no importar
    #     nada de otra parte.
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13h-") as tmp:
        copia = _arbol(tmp, dicc=False, cli=False, regres=False)
        p = ejecuta([copia, "--muestra=1", "--raiz=" + tmp], cwd=tmp)
        v("[8d] un arbol sin nada se niega con INVALID_TREE",
          p.returncode != 0 and "INVALID_TREE" in (p.stderr + p.stdout),
          "rc=%s err=%s" % (p.returncode, (p.stderr + p.stdout)[-300:]))

    # ══ 9 · el guard de arbol tiene que ser NECESARIO, no decorativo ═══
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13c-") as tmp:
        falso = os.path.join(tmp, "ajeno")
        os.makedirs(falso)
        open(os.path.join(falso, "cli.py"), "w", encoding="utf-8").write(
            "def main(argv=None):\n"
            "    import json\n"
            "    print(json.dumps({'status': 'ok', 'results': ["
            "{'definitions': [], 'chosen': {'value': 999999}}]}))\n")
        debil = fuente.replace(
            'sys.path.insert(0, RAIZ + "/tools/rxre")',
            'sys.path.append(RAIZ + "/tools/rxre")')
        v("el candado que se quita para esta prueba existe de verdad",
          debil != fuente)
        copia = os.path.join(tmp, "debil.py")
        open(copia, "w", encoding="utf-8").write(debil)
        p = ejecuta([copia, "--muestra=1", "--raiz=" + RAIZ],
                    env={"PYTHONPATH": falso})
        v("con el otro candado quitado, verifica_arbol detecta el cli ajeno",
          p.returncode != 0 and "INVALID_TREE" in (p.stderr + p.stdout),
          "rc=%s err=%s" % (p.returncode, (p.stderr + p.stdout)[-300:]))
        v("y no llega a escribir ningun veredicto con el valor falso",
          "999999" not in p.stdout)

    # ══ 10 · el override de RAIZ tiene que FUNCIONAR ════════════════════
    # Un override que no existe no se distingue de uno roto:  por eso se
    # ejecuta contra un arbol completo y se mira que se midio ESE.
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13e-") as tmp:
        dst = tmp
        shutil.copytree(RAIZ + "/tools/rxre", dst + "/tools/rxre",
                        ignore=shutil.ignore_patterns("__pycache__", "github",
                                                      "storage"),
                        dirs_exist_ok=True)
        shutil.copy(RAIZ + "/tools/reg_resolve.py",
                    dst + "/tools/reg_resolve.py")
        os.makedirs(dst + "/tools", exist_ok=True)
        open(dst + "/tools/rxre_cobertura_gfx8.py", "w",
             encoding="utf-8").write(fuente)
        os.symlink(RAIZ + "/RESEARCH", dst + "/RESEARCH")
        sal = os.path.join(tmp, "o.jsonl")
        met = os.path.join(tmp, "o.meta.json")
        p = ejecuta([dst + "/tools/rxre_cobertura_gfx8.py", "--muestra=2",
                     "--salida=" + sal, "--meta=" + met, "--raiz=" + dst],
                    cwd=dst)
        v("con --raiz= contra otro arbol completo, la corrida arranca",
          p.returncode == 0, p.stderr[-400:])
        if os.path.isfile(met):
            mo = json.load(open(met, encoding="utf-8"))
            v("--raiz= cambia de verdad el arbol medido",
              os.path.realpath(mo.get("source_root", "")) ==
              os.path.realpath(dst),
              "source_root=%s" % mo.get("source_root"))
            v("y lo declara como coming de argv, no de __file__",
              mo.get("source_root_origen") == "argv:--raiz",
              "origen=%s" % mo.get("source_root_origen"))
            v("y el RXRE importado es el de ESE arbol",
              os.path.realpath(mo.get("rxre_importado", "")) ==
              os.path.realpath(dst + "/tools/rxre/cli.py"))
        else:
            v("--raiz= produce procedencia", False, "no hay %s" % met)

        sal2 = os.path.join(tmp, "e.jsonl")
        met2 = os.path.join(tmp, "e.meta.json")
        p = ejecuta([dst + "/tools/rxre_cobertura_gfx8.py", "--muestra=2",
                     "--salida=" + sal2, "--meta=" + met2],
                    cwd=dst, env={"RXRE_ROOT": dst})
        v("con RXRE_ROOT contra otro arbol completo, la corrida arranca",
          p.returncode == 0, p.stderr[-400:])
        if os.path.isfile(met2):
            me = json.load(open(met2, encoding="utf-8"))
            v("RXRE_ROOT cambia de verdad el arbol medido",
              os.path.realpath(me.get("source_root", "")) ==
              os.path.realpath(dst),
              "source_root=%s" % me.get("source_root"))
            v("y lo declara como coming de env",
              me.get("source_root_origen") == "env:RXRE_ROOT",
              "origen=%s" % me.get("source_root_origen"))
        else:
            v("RXRE_ROOT produce procedencia", False, "no hay %s" % met2)

    # ══ 11 · el contador del fallback, de extremo a extremo ════════════
    # Un 'cli' que SI esta en el sitio correcto —asi que pasa el candado— pero
    # devuelve un chosen SIN 'value'.  Es la unica forma real de alcanzar la
    # rama.  Y alterna:  el primer registro trae 'value',  los siguientes no.
    # Asregistros != disparado,  que es lo que separa un contador de una
    # etiqueta.
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="cob13f-") as tmp:
        shutil.copytree(RAIZ + "/tools/rxre", os.path.join(tmp, "tools/rxre"),
                        ignore=shutil.ignore_patterns("__pycache__", "github",
                                                      "storage"),
                        dirs_exist_ok=True)
        open(os.path.join(tmp, "tools/rxre/cli.py"), "w", encoding="utf-8").write(
            "_n = [0]\n"
            "def main(argv=None):\n"
            "    import json\n"
            "    _n[0] += 1\n"
            "    ch = {'file': 'x', 'rel': 'x'}\n"
            "    if _n[0] == 1:\n"
            "        ch['value'] = 9451\n"
            "    print(json.dumps({'status': 'ok', 'results': ["
            "{'definitions': [], 'chosen': ch}]}))\n")
        open(os.path.join(tmp, "tools/rxre_cobertura_gfx8.py"), "w",
             encoding="utf-8").write(fuente)
        shutil.copy(RAIZ + "/tools/reg_resolve.py",
                    os.path.join(tmp, "tools/reg_resolve.py"))
        os.symlink(RAIZ + "/RESEARCH", os.path.join(tmp, "RESEARCH"))
        sal = os.path.join(tmp, "f.jsonl")
        met = os.path.join(tmp, "f.meta.json")
        p = ejecuta([os.path.join(tmp, "tools/rxre_cobertura_gfx8.py"),
                     "--muestra=4", "--salida=" + sal, "--meta=" + met,
                     "--raiz=" + tmp], cwd=tmp)
        v("con un chosen sin 'value' la corrida NO se rompe", p.returncode == 0,
          p.stderr[-300:])
        if os.path.isfile(met):
            fb2 = json.load(open(met, encoding="utf-8"))["fallback_byte_offset"]
            v("el fallback se CUENTA, no se declara muerto a priori",
              fb2["disparado"] == 3,
              "disparado=%s de %s" % (fb2.get("disparado"),
                                      fb2.get("registros_con_chosen_dict")))
            v("y disparos != registros: el contador distingue, no copia",
              fb2["registros_con_chosen_dict"] == 4 and fb2["disparado"] == 3,
              "registros=%s disparos=%s" % (fb2.get("registros_con_chosen_dict"),
                                            fb2.get("disparado")))
        else:
            v("el caso hostil produce procedencia", False, "no hay %s" % met)

    if FALLOS:
        print("\n%d/%d FALLOS: %s" % (len(FALLOS), len(V),
                                      ", ".join(FALLOS[:6])))
        return 1
    print("\n%d checks · TODO VERDE" % len(V))
    return 0


if __name__ == "__main__":
    sys.exit(main())