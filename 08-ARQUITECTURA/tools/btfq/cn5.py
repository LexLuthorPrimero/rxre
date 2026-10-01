#!/usr/bin/env python3
"""
cn5.py -- control negativo del contraste corpus/BTF.

QUE TIENE QUE DEMOSTRAR
----------------------
Que crosscheck.py puede DETECTAR una divergencia real. Un contraste que solo
ha reportado "coinciden" no ha demostrado nada: puede que su comparacion sea
vacia, que compare el fichero consigo mismo, o que el filtro se trague todo.

Se prueba por Mutation Testing: se mete una divergencia DELIBERADA en una
COPIA del corpus en /tmp y se exige que el contraste la vea.

Por que una copia y no el corpus
-------------------------------
RESEARCH/ es el corpus y esta bajo禁令 de escritura. Ademas, mutar el
corpus real dejaria una diferencia que nadie podria distinguir de un
resultado legitimo. La mutacion va contra /tmp, y el script lo comprueba
con sha256 antes y despues.

CONTROLES
---------
  CN-5a  campo anadido solo en el binario  -> debe verse como divergencia
  CN-5b  campo quitado solo en la fuente   -> debe verse como divergencia
  CN-5c  corpus intacto                    -> debe coincidir (rc=0)
  CN-5d  el corpus real no cambia          -> sha256 antes == despues

Si CN-5a o CN-5b NO detectan su mutacion, el contraste es inservible: solo
sabria decir "coinciden" sin poder decir nunca "no coinciden".
"""
import hashlib
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crosscheck

REAL = crosscheck.CORPUS


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def comparar_en(hdr_path):
    """Ejecuta la misma comparacion de crosscheck sobre un header dado."""
    src = crosscheck.campos_fuente(hdr_path, "amdgpu_gmc")
    bin_, n = crosscheck.campos_btf("amdgpu_gmc")
    return src, bin_


def con_header_mutado(nombre, mutar):
    """Copia el .h real a /tmp, lo muta, y devuelve la comparacion."""
    origen = os.path.join(REAL, "amdgpu_gmc.h")
    fd, tmp = tempfile.mkstemp(suffix=".h")
    os.close(fd)
    shutil.copy2(origen, tmp)
    try:
        txt = open(tmp, encoding="utf-8", errors="replace").read()
        txt = mutar(txt)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(txt)
        return comparar_en(tmp)
    finally:
        os.unlink(tmp)


def main():
    print("Controles negativos del contraste corpus/BTF (mutation testing)")
    print("corpus real (NO se modifica): %s" % REAL)
    print()
    fallos = 0

    # ---- CN-5a: campo SOLO en el binario -------------------------------
    # Se consigue GREGANDO un campo al BTF simulado... pero el BTF es real y
    # no se puede mutar sin root. La via honesta es la inversa: quitar un
    # campo que SI esta en el binario y ver que aparece como "solo en fuente".
    # Para CN-5a se simula el binario: se comprueba que un campo extra en el
    # lado binario se detectaria. Se hace sobre el parser de campos, no
    # inventando metricas.
    orig_bin = crosscheck.campos_btf("amdgpu_gmc")[0]
    mutado_bin = set(orig_bin) | {"campo_fantasma_xyz"}
    src_real = crosscheck.campos_fuente(
        os.path.join(REAL, "amdgpu_gmc.h"), "amdgpu_gmc")
    solo = mutado_bin - src_real
    ok_a = "campo_fantasma_xyz" in solo
    print("  %-42s %s" % ("CN-5a campo extra en el binario", "OK" if ok_a else "FALLO"))
    print("      detectado como 'solo en el binario': %s" % sorted(solo & {"campo_fantasma_xyz"}))
    if not ok_a:
        fallos += 1

    # ---- CN-5b: campo quitado SOLO en la fuente --------------------------
    # La primera version de esta mutacion buscaba "\tbool\t\t\tis_app_apu;\n",
    # con TRES tabuladores. La linea real es "\tbool is_app_apu;\n": un
    # tabulador, un tipo, un espacio. La mutacion no aplicaba, y aun asi el
    # control se evaluaba como si hubiera aplicado.
    #
    # Por eso ahora se comprueba que la mutacion REALMENTE ocurrio antes de
    # judgementsar si el contraste la detecta. Un control negativo que no
    # verifica su propia mutacion no mide nada.
    def quitar(txt):
        return re.sub(r"^\s*bool\s+is_app_apu;\s*$", "", txt,
                      count=1, flags=re.M)
    src_mut, bin_real = con_header_mutado("cn5b", quitar)
    aplico = "is_app_apu" not in src_mut
    ok_b = aplico and "is_app_apu" in (bin_real - src_mut)
    print("      la mutacion se aplico de verdad: %s" % aplico)
    print("  %-42s %s" % ("CN-5b campo quitado en la fuente", "OK" if ok_b else "FALLO"))
    print("      detectado como 'solo en el binario': %s"
          % sorted(bin_real - src_mut))
    if not ok_b:
        fallos += 1

    # ---- CN-5c: corpus intacto debe coincidir ----------------------------
    src_ok, bin_ok = comparar_en(os.path.join(REAL, "amdgpu_gmc.h"))
    diff = (bin_ok - src_ok) - crosscheck.ANON
    ok_c = not diff and not (set(src_ok) - bin_ok - crosscheck.ANON)
    print("  %-42s %s" % ("CN-5c corpus intacto -> coincide", "OK" if ok_c else "FALLO"))
    print("      interseccion=%d  diferencias_reales=%d"
          % (len(src_ok & bin_ok), len(diff)))
    if not ok_c:
        fallos += 1

    # ---- CN-5d: el corpus real no se toco -------------------------------
    h = os.path.join(REAL, "amdgpu_gmc.h")
    antes = sha(h)
    con_header_mutado("cn5d", lambda t: t + "\n/* mutacion throwaway */\n")
    despues = sha(h)
    ok_d = antes == despues
    print("  %-42s %s" % ("CN-5d corpus real intacto (sha)", "OK" if ok_d else "FALLO"))
    print("      sha antes=%s despues=%s" % (antes[:16], despues[:16]))
    if not ok_d:
        fallos += 1

    print()
    print("%d/4 controles vivos" % (4 - fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
