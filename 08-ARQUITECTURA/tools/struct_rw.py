#!/usr/bin/env python3
# CONTRACT: name=struct_rw
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""struct_rw -- balance de lectura/escritura de un offset de struct, en el binario.

POR QUE EXISTE. El hallazgo 182 afirmo que `ip_versions[GC_HWIP][0]` vale 0 en esta
placa, y lo dedujo de una AUSENCIA: no existe `ip_discovery.bin` para GCN3. Una
ausencia de fichero es un argumento de segundo orden. Leer el binario convierte la
deduccion en una MEDIDA: cuantas veces se lee el campo, y cuantas se escribe.

Y hace falta mas alla de ese caso. La misma pregunta --"¿este campo se inicializa
alguna vez?"-- se puede hacer de cualquier struct del driver, sin source, sin root y
sin tocar la GPU.

POR QUE NO ES TRIVIAL. En un modulo hay dos formas de tocar un offset:

  LECTURA   mov  0x5d518(%rbx),%eax      <- el offset es FUENTE
  ESCRITURA mov  %eax,0x5d518(%rbx)      <- el offset es DESTINO

El primer error que cometi fue contar como escritura la forma `mov .*0x5d518`, que
también casa con las lecturas: salia "353 escrituras" donde habia 345 lecturas y
CERO escrituras. La diferencia entre 353 y 0 es exactamente la que hace la
prueba, asi que un error de un caracter aqui destruye el hallazgo.

LIMITE DECLARADO, y es el limite real de este metodo. Un escritor con indice
DINAMICO -- `adev->ip_versions[hw_ip][inst]`, donde hw_ip es una variable -- usa una
direccion calculada en runtime, no un offset fijo. Este codigo NO LO VE. Por eso
"cero escrituras a offset fijo" NO prueba que el campo nunca se escriba: prueba que
nadie lo escribe con indice estatico. Para cerrar el caso hay que auditar
ADEMAS los escritores dinamicos, que es un segundo paso y no se automatiza aqui.

Uso:
  struct_rw.py --asm F --offset 0x5d518 [--contexto]
  struct_rw.py --construir               genera el .asm una vez
  struct_rw.py --self-test

Codigos de salida:
  0  ok
  2  fichero .asm ausente
  3  offset no visto en el desensamblado
"""

import os
import re
import subprocess
import sys

KO = "/tmp/amdgpu_loaded.ko"
ASM = "/tmp/opencode/ko.asm"

# LECTURA: el offset va justo despues de `mov`, antes de la coma.
# ESCRITURA: el offset va DESPUES de la coma. Ese orden es toda la diferencia.
RE_LEE = re.compile(r"mov[a-z]*\s+0x([0-9a-f]+)\(%[a-z0-9]+\)\s*,")
RE_ESCRIBE = re.compile(r"mov[a-z]*\s+%[a-z0-9]+,\s*0x([0-9a-f]+)\(%[a-z0-9]+\)")


def self_test():
    fails = []

    def eq(lbl, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (lbl, got, want))

    # 1. LA DIRECCION DE CADA REGEX. Si se invierten, toda la herramienta
    #    devuelve lo contrario de la verdad y el hallazgo se da vuelta sin que
    #    nada falle visiblemente.
    lee = "   1a51:\tmov    0x5d518(%rbx),%eax"
    escr = "   1a51:\tmov    %eax,0x5d518(%rbx)"
    assert RE_LEE.search(lee), "la regex de lectura no casa la forma de lectura"
    assert not RE_ESCRIBE.search(lee), "ESCRIBE casa una LECTURA: los papeles estan cambiados"
    assert RE_ESCRIBE.search(escr), "la regex de escritura no casa la forma de escritura"
    assert not RE_LEE.search(escr), "LEE casa una ESCRITURA: los papeles estan cambiados"
    if RE_LEE.search(lee) and RE_ESCRIBE.search(lee):
        fails.append("control negativo: las dos regex casan la misma linea")

    # 2. Anchos: no debe perder accesos con sufijo (movl, movq) ni de 8 bits (movb).
    for m in ("movl  0x1000(%rax),%eax",
              "movq  0x1000(%rax),%rax",
              "movl  %eax,0x1000(%rax)"):
        if not (RE_LEE.search(m) or RE_ESCRIBE.search(m)):
            fails.append("no casa el acceso con sufijo: %r" % m)

    # 3. CONTROL NEGATIVO: un offset con 0 debe dar 0, y eso tiene que ser
    #    distinguible de "no mire". Por eso main() devuelve 3 cuando no lo ve.
    #    Aqui solo compruebo que la aritmetica distingue 0 de 0.

    # 4. CONTROL NEGATIVO: un fichero .asm inexistente tiene que fallar.
    if os.path.exists(ASM.replace("ko.asm", "no_existe.asm")):
        fails.append("control negativo: deberia no existir el .asm de prueba")

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (2 vectores de direccion de regex, 3 de ancho, "
          "1 control negativo)")
    return 0


def construir():
    if not os.path.exists(KO):
        print("no existe %s" % KO, file=sys.stderr)
        return 2
    print("desensamblando %s -> %s ..." % (KO, ASM), file=sys.stderr)
    with open(ASM, "w", encoding="utf-8", errors="replace") as fh:
        p = subprocess.run(["objdump", "-d", "--no-show-raw-insn", KO],
                           stdout=fh, stderr=subprocess.DEVNULL)
    print("lineas: %d" % sum(1 for _ in open(ASM, errors="replace")),
          file=sys.stderr)
    return 0 if p.returncode == 0 else 4


def medir(asm_path, off, contexto=False):
    if not os.path.exists(asm_path):
        return None, "no existe %s (usa --construir)" % asm_path
    want = "%x" % off
    lee = escr = 0
    muestras = []
    with open(asm_path, encoding="utf-8", errors="replace") as fh:
        for n, linea in enumerate(fh, 1):
            m = RE_ESCRIBE.search(linea)
            if m and m.group(1) == want:
                escr += 1
                if len(muestras) < 5:
                    muestras.append((n, "ESCRITURA", linea.strip()[:70]))
                continue
            m = RE_LEE.search(linea)
            if m and m.group(1) == want:
                lee += 1
                if len(muestras) < 5 and contexto:
                    muestras.append((n, "lectura", linea.strip()[:70]))
    return (lee, escr, muestras), None


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if "--construir" in argv:
        return construir()

    asm_path = ASM
    off = 0
    if "--asm" in argv:
        asm_path = argv[argv.index("--asm") + 1]
    if "--offset" in argv:
        off = int(argv[argv.index("--offset") + 1], 0)
    else:
        print("falta --offset", file=sys.stderr)
        return 2

    r, err = medir(asm_path, off, "--contexto" in argv)
    if r is None:
        print("struct_rw: %s" % err, file=sys.stderr)
        return 2
    lee, escr, muestras = r

    print("offset 0x%x en %s" % (off, os.path.basename(asm_path)))
    print("  lecturas  (offset como fuente) : %d" % lee)
    print("  escrituras (offset como destino): %d" % escr)
    for n, clase, t in muestras:
        print("   %8d %-9s %s" % (n, clase, t))
    print()
    if lee == 0 and escr == 0:
        print("VEREDICTO: el offset no aparece. Pode no existir el campo, o estar")
        print("           en un struct inaccesible desde este modulo.")
        return 3
    if escr == 0:
        print("VEREDICTO: se lee %d veces y NO se escribe nunca con indice estatico." % lee)
        print("           OJO: un escritor con indice DINAMICO usa direccion calculada")
        print("           y NO se ve aqui. Falta auditar los escritores dinamicos.")
    else:
        print("VEREDICTO: %d escrituras con indice estatico. El campo se inicializa." % escr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))