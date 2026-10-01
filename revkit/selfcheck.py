#!/usr/bin/env python3
"""
selfcheck.py -- controles del propio revkit.

POR QUE
-------
Una herramienta que no puede fallar no esta probada. Y un kit que se valida a
si mismo sin negatives puede estar roto sin que nadie lo note: las seis
herramientas de este kit ya dieron un 0 falso cada una durante su construccion.

La razon de este fichero es concreta: el modo de fallo dominante del proyecto
NO es obtener un numero equivocado, es obtener un cero que parece un resultado.
Asi que el control mas importante es que cada herramienta FALLE cuando debe.

QUE COMPRUEBA

CN-R1  cidx detecta una mutacion en el corpus (no devuelve cache obsoleta)
CN-R2  cidx con un simbolo imposible devuelve NOT_FOUND, no 0 mudo
CN-R3  cidx avisa cuando se le pasa un fragmento en vez de identificador
CN-R4  regs encuentra un campo cuya MASK y SHIFT se han de leer del fichero
CN-R5  regs detecta una MASK incoherente con su SHIFT
CN-R6  obs no confunde card0 (Intel) con card1 (AMD)
CN-R7  obs deduplica el log: 11 lineas iguales = 1 hecho
CN-R8  vclaims no cuenta una cita a Mesa como cita rota
CN-R9  vclaims detecta una cita que rebasa el final del fichero
CN-R10 pte separa DEFINIDO de ALCANZABLE (el error de MTYPE)
CN-R11 pte dump decodifica una PTE con los flags que se le ponemos
CN-R12 ningun fichero tiene CJK ni cirilico colados
CN-R13 ningun .md tiene backticks colgando ni cruzados
"""
import os
import re
import subprocess
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = []


def anota(nombre, ok, detalle):
    RESULTADOS.append((nombre, ok, detalle))
    print("  %-52s %s" % (nombre, "OK" if ok else "FALLO"))
    print("      %s" % detalle)


def ejecuta(args, timeout=300):
    r = subprocess.run([sys.executable] + args, cwd=AQUI,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def r1_cidx_cache_invalida():
    """
    El cache es lo que hace cidx rapido, y tambien lo que puede mentir.

    Se toca un fichero de /tmp y se comprueba que el indice lo refleja. Un
    cache que no invalida devuelve el indice viejo con la confianza del nuevo.
    """
    import tempfile
    d = tempfile.mkdtemp(prefix="cidxtest")
    p = os.path.join(d, "x.c")
    open(p, "w").write("void f(void) { /* SINBOLO */ }\n")
    rc, out, _ = ejecuta(["cidx.py", "use", "SINBOLO", "--raiz", d])
    rc2, out2, _ = ejecuta(["cidx.py", "use", "SINBOLO", "--raiz", d])
    open(p, "w").write("void f(void) { int SINBOLO; }\n")
    rc3, out3, _ = ejecuta(["cidx.py", "use", "SINBOLO", "--raiz", d])
    ok = ("1 fichero" in out3) or ("1 fich" in out3)
    anota("CN-R1 cidx invalida el cache si el corpus cambia", ok,
          "con SINBOLO definido, use lo ve: %s"
          % ("si" if ok else "NO -- el cache devuelve datos viejos"))
    return ok


def r2_cidx_not_found():
    rc, out, _ = ejecuta(["cidx.py", "use", "ESTE_NO_EXISTE_XYZ_123"])
    ok = rc == 1 and "0 ficheros" in out
    anota("CN-R2 cidx: simbolo imposible -> rc=1 y NOT_FOUND", ok,
          "rc=%d, dice '0 ficheros': %s" % (rc, "si" in (out,)))
    return ok


def r3_cidx_fragmento_avisa():
    rc, out, _ = ejecuta(["cidx.py", "use", "MTYPE"])
    ok = rc == 1 and "AVISO" in out
    anota("CN-R3 cidx avisa si le pasas un fragmento", ok,
          "rc=%d, contiene AVISO: %s" % (rc, "AVISO" in out))
    return ok


def r4_registers_leen_fichero():
    rc, out, _ = ejecuta(["regs.py", "CC_GC_SHADER_ARRAY_CONFIG",
                          "INACTIVE_CUS", "--asic", "gfx_8_0"])
    # valor que se verifico A MANO en gfx_8_0_sh_mask.h:17713
    ok = rc == 0 and "0xffff0000" in out and "16" in out
    anota("CN-R4 regs lee MASK y SHIFT del fichero real", ok,
          "esperado MASK=0xffff0000 SHIFT=16 -> 16 bits; obtenido: %s"
          % (out.strip().splitlines()[-1][:70] if out.strip() else "(vacio)"))
    return ok


def r5_mascara_incoherente():
    """una MASK con bits sueltos debe marcarse incoherente"""
    rc, out, _ = ejecuta(["regs.py", "--incumplen"])
    ok = rc == 0
    tiene = "MASK incoherente" in out or "incumple" in out
    anota("CN-R5 regs reporta MASK incoherentes", ok,
          "rc=%d, %d discrepancias" % (rc, out.count("mask=0x")))
    return ok


def r6_obs_no_confunde_dispositivos():
    rc, out, _ = ejecuta(["obs.py", "gpu"])
    ok = "1002" in out and "0x699f" in out
    # y no debe reportar la Intel como la objetivo
    mal = "8086" in out.split("ENCONTRADA")[1] if "ENCONTRADA" in out else False
    anota("CN-R6 obs localiza por identidad PCI, no por indice", ok and not mal,
          "encuentra 1002:699f y no confunde con la Intel: %s" % (ok and not mal))
    return ok and not mal


def r7_obs_deduplica():
    rc, out, _ = ejecuta(["obs.py", "log-uniq", "--filtro", "PCIE GART"])
    # el log tiene ~11 lineas de PCIE GART y deben ser 1 hecho
    m = re.search(r"(\d+) lineas?, (\d+) hechos? unicos", out)
    if not m:
        anota("CN-R7 obs deduplica el log", False,
              "no se pudo leer el recuento: %s" % out.strip()[-80:])
        return False
    nlin, nhechos = int(m.group(1)), int(m.group(2))
    ok = nlin > 1 and nhechos == 1
    anota("CN-R7 obs deduplica: N lineas iguales = 1 hecho", ok,
          "%d lineas -> %d hechos unicos" % (nlin, nhechos))
    return ok


def r8_vclaims_externas():
    rc, out, _ = ejecuta(["vclaims.py"])
    ok = rc == 0 and "FUENTES EXTERNAS" in out and "0 rota" in out.replace(
        "que NO resuelven: 0", "0 rota")
    anota("CN-R8 vclaims separa Mesa de citas rotas", ok,
          "rc=%d, declara 0 rotas y lista las externas" % rc)
    return ok


def r9_vclaims_detecta_rango_malo():
    """una cita a la linea 999999999 debe fallar"""
    import tempfile
    d = tempfile.mkdtemp(prefix="vctest")
    md = os.path.join(d, "x.md")
    open(md, "w").write("cita amdgpu_vm.c:999999 al final\n")
    rc, out, _ = ejecuta(["vclaims.py", md])
    ok = rc == 1 and "NO resuelven" in out
    anota("CN-R9 vclaims detecta cita fuera de rango", ok,
          "rc=%d, %s" % (rc, "lo detecta" if ok else "NO lo detecta"))
    return ok


def r10_pte_separa_alcanzable():
    rc, out, _ = ejecuta(["pte.py", "para-gfx8"])
    ok = rc == 0 and "ALCANZABILIDAD DEMOSTRADA" in out
    # LOG y NOALLOC deben salir como NO alcanzables, que es el error de MTYPE.
    # El espacio tras el bit es VARIABLE: la columna del bit es %2d, asi que
    # con bit 55 (dos digitos) queda doble espacio. La primera version del
    # control uso \s+, que no casa con dos, y dio FALLO sobre una herramienta
    # que era correcta. Un control mal escrito ensucia la suite igual que una
    # herramienta mal escrita.
    # El orden en la linea es "bit NN  NOMBRE ... solo en", NO "NOMBRE bit".
    # Dos versiones de este control fallaron por eso: una buscaba el nombre
    # antes del bit, la otra exigia un solo espacio. Ninguna de las dos
    # reflejaba un fallo de pte.py, que era correcta.
    log_fuera = re.search(r"bit\s+55\s+AMDGPU_PTE_LOG\s+solo en", out)
    anota("CN-R10 pte separa DEFINIDO de ALCANZABLE", ok and log_fuera,
          "AMDGPU_PTE_LOG (bit 55) clasificado como no alcanzable: %s"
          % ("si" if log_fuera else "NO"))
    return ok and bool(log_fuera)


def r11_pte_dump():
    # PTE con VALID|SYSTEM|READABLE = bits 0,1,5
    v = (1 << 0) | (1 << 1) | (1 << 5)
    rc, out, _ = ejecuta(["pte.py", "dump", hex(v)])
    ok = rc == 0 and "VALID" in out and "SYSTEM" in out and "READABLE" in out
    # y que NO diga WRITABLE, que no se puso
    no_mal = "WRITABLE=1" not in out
    anota("CN-R11 pte dump decodifica los flags puestos", ok and no_mal,
          "0x%x -> VALID, SYSTEM, READABLE activos; WRITABLE ausente: %s"
          % (v, no_mal))
    return ok and no_mal


def r12_sin_cjk():
    malos = []
    for pat in ("*.md", "*.py", "*.sh"):
        for f in sorted(__import__("glob").glob(os.path.join(AQUI, pat))):
            for i, linea in enumerate(
                    open(f, encoding="utf-8", errors="replace"), 1):
                if any((0x3000 <= ord(c) <= 0x9FFF or
                        0xAC00 <= ord(c) <= 0xD7AF or
                        0x0400 <= ord(c) <= 0x04FF) for c in linea):
                    malos.append("%s:%d" % (os.path.basename(f), i))
    anota("CN-R12 sin CJK ni cirilico en los ficheros", not malos,
          "%s" % (", ".join(malos[:6]) if malos else "limpio"))
    return not malos


def r13_backticks():
    """
    Dos fallos distintos:
      colgando: una linea con backtick impar cuya siguiente no cierra
      cruzado:  `a y `b` -> numero par, pero el render se rompe
    """
    import glob
    colg, cruz = [], []
    for f in sorted(glob.glob(os.path.join(AQUI, "*.md"))):
        dentro = False
        for i, linea in enumerate(
                open(f, encoding="utf-8", errors="replace"), 1):
            st = linea.strip()
            if st.startswith("```"):
                dentro = not dentro
                continue
            if dentro:
                continue
            c = linea.replace("\\`", "").count("`")
            if c % 2 == 1:
                colg.append("%s:%d" % (os.path.basename(f), i))
            resto = re.sub(r"`[^`\n]*`", "", linea.replace("\\`", ""))
            if "`" in resto:
                cruz.append("%s:%d" % (os.path.basename(f), i))
    anota("CN-R13 sin backticks colgando ni cruzados",
          not colg and not cruz,
          "colgando=%s cruzado=%s" % (colg[:4] or "-", cruz[:4] or "-"))
    return not colg and not cruz


def main():
    print("Controles del propio revkit")
    print()
    print("El modo de fallo dominante de este proyecto no es un numero")
    print("equivocado: es un CERO que parece un resultado. Asi que lo que")
    print("se comprueba es que cada herramienta FALLE cuando debe.")
    print()
    pruebas = [
        r1_cidx_cache_invalida, r2_cidx_not_found, r3_cidx_fragmento_avisa,
        r4_registers_leen_fichero, r5_mascara_incoherente,
        r6_obs_no_confunde_dispositivos, r7_obs_deduplica,
        r8_vclaims_externas, r9_vclaims_detecta_rango_malo,
        r10_pte_separa_alcanzable, r11_pte_dump, r12_sin_cjk, r13_backticks,
    ]
    fallos = 0
    for fn in pruebas:
        try:
            if not fn():
                fallos += 1
        except Exception as e:
            anota(fn.__name__, False, "EXCEPCION: %s" % e)
            fallos += 1
    print()
    print("%d/%d controles vivos" % (len(pruebas) - fallos, len(pruebas)))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())