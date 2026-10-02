#!/usr/bin/env python3
"""
cn8.py -- controles de atomrom.py: firmware, VRAM y el contraste de unidades.

POR QUE UN FICHERO APARTE Y NO MAS LINEAS EN cn7
-------------------------------------------------
Porque cn7 es de pm4dec. Los controles de una herramienta que decodifica
PM4 y los de una que decodifica el VBIOS no se mezclan: si fallan, hay que
saber cual de las dos esta mal, y un unico "algo de atomrom fallo" obliga a
buscar.

QUE COMPRUEBA, Y POR QUE CADA CASO
----------------------------------
1. El autotest basico de atomrom (se delega, no se reimplementa).
2. Que la unidad de los clocks se detecta como CORRECTA con el VBIOS real.
3. CASO NEGATIVO DE LA UNIDAD: un VBIOS con los mismos numeros crudos pero
   leidos con un factor equivocado tiene que DIFIERE. Esto es lo que
   convierte el contraste en un control y no en una decoracion: si el factor
   se puede cambiar sin que nadie se entere, el contraste no contrasta nada.
4. Que la VRAM del VBIOS coincide con la que ve el kernel.
5. CASO NEGATIVO DE LA VRAM: un VBIOS sintetico que declara 1024 MB cuando
   el kernel ve 2048 tiene que salir con "NO COINCIDEN" y codigo 5.
6. Que sin los ficheros de contraste el codigo de salida NO es 0. Un
   codigo 0 cuando no se ha podido comprobar es el fallo mas caro: parece
   una corroboracion y no es una.
"""
import os
import struct
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atomrom as A  # noqa: E402

FALLOS = []


def chk(nombre, cond, detalle=""):
    if cond:
        print("  OK    %s" % nombre)
    else:
        print("  FALLA %s %s" % (nombre, detalle))
        FALLOS.append(nombre)


def main():
    vbios = os.path.join(AQUI, "capturas", "amdgpu_vbios.txt")
    if not os.path.exists(vbios):
        print("OMITIDO: no esta el VBIOS capturado.")
        print("Se obtiene con: RX550_SUDO_PASS=... captura.py")
        print("Los controles de contraste necesitan la maquina real.")
        return 2
    d = open(vbios, "rb").read()

    print("controles de atomrom.py")
    print("-" * 66)

    # 1. el autotest propio, delegado
    r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                        "autotest"], capture_output=True, text=True)
    chk("atomrom autotest (ROM sintetico)", r.returncode == 0,
        "(rc=%d)" % r.returncode)

    # 2. la unidad correcta se reconoce
    r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                        "firmware", vbios], capture_output=True, text=True)
    chk("unidad de los clocks CORROBORATED con el VBIOS real",
        r.returncode == 0 and "COINCIDE" in r.stdout,
        "(rc=%d)" % r.returncode)

    # 3. CASO NEGATIVO: la unidad se comprueba de verdad.
    #
    # Se reescribe atomrom.py en una copia con el factor a MHz cambiado de
    # 100 a 10, y se exige que el contraste falle. Si el contraste no depende
    # del factor, esto pasaria igual y el control no serviria para nada.
    with tempfile.TemporaryDirectory() as td:
        copia = os.path.join(td, "atomrom_malo.py")
        src = open(os.path.join(AQUI, "atomrom.py")).read()
        # se cambia SOLO el factor del calculo del contraste
        malo = src.replace("mhz = CRUDO[nombre] / 100.0",
                           "mhz = CRUDO[nombre] / 10.0")
        chk("el mutante cambia de verdad el factor", malo != src)
        open(copia, "w").write(malo)
        # se ejecuta desde el directorio de revkit para que encuentre capturas
        r = subprocess.run([sys.executable, copia, "firmware", vbios],
                           capture_output=True, text=True, cwd=AQUI)
        chk("CASO NEGATIVO: unidad equivocada -> DIFIERE y rc=5",
            r.returncode == 5 and "DIFIERE" in r.stdout,
            "(rc=%d)" % r.returncode)

        # 4-5. VRAM: la correcta coincide, y una sintetica que no, falla
        r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                            "vram", vbios], capture_output=True, text=True,
                           cwd=AQUI)
        chk("VRAM del VBIOS coincide con la del kernel",
            r.returncode == 0 and "COINCIDEN" in r.stdout,
            "(rc=%d)" % r.returncode)

        # VBIOS sintetico con usMemorySize = 1024 en vez de 2048.
        # Se parchea sobre una copia del VBIOS real, que mantiene validas
        # las firmas, y solo se cambia ese campo.
        rom2 = bytearray(d)
        v = A.valida(bytes(rom2))
        mt = v["data_table"]
        vram_off = A.u16(rom2, mt + A.HEADER_COMUN + 2 * 28)
        mod = vram_off + 4 + 12 + 4
        struct.pack_into("<H", rom2, mod + 20, 1024)   # usMemorySize
        f2 = os.path.join(td, "vbios_1024.bin")
        open(f2, "wb").write(bytes(rom2))
        r = subprocess.run([sys.executable, os.path.join(AQUI, "atomrom.py"),
                            "vram", f2], capture_output=True, text=True,
                           cwd=AQUI)
        chk("CASO NEGATIVO: VRAM de 1024 contra kernel de 2048 -> NO COINCIDEN",
            r.returncode == 5 and "NO COINCIDEN" in r.stdout,
            "(rc=%d)" % r.returncode)

    # 6. Sin los ficheros de contraste el rc NO puede ser 0.
    #
    # Un codigo 0 cuando no se ha podido comprobar es el fallo mas caro de
    # esta herramienta: parece una corroboracion y no es una. Se comprueba
    # moviendo el fichero de verdad, porque el comando lo busca SIEMPRE en
    # capturas/ y no acepta otra ruta: si lo quise accepting una, el
    # contraste se podria esquivar.
    pm = os.path.join(AQUI, "capturas", "amdgpu_pm_info.txt")
    vm = os.path.join(AQUI, "capturas", "amdgpu_vram_mm.txt")
    for fichero, arg, etiqueta in ((pm, "firmware", "amdgpu_pm_info"),
                                   (vm, "vram", "amdgpu_vram_mm")):
        if not os.path.exists(fichero):
            print("  OMIT  sin %s no se puede probar el caso 6" % etiqueta)
            continue
        guard = fichero + ".cn8.bak"
        os.rename(fichero, guard)
        try:
            r = subprocess.run([sys.executable,
                                os.path.join(AQUI, "atomrom.py"), arg, vbios],
                               capture_output=True, text=True, cwd=AQUI)
            chk("sin %s: avisa y NO sale con rc=0" % etiqueta,
                r.returncode == 4, "(rc=%d)" % r.returncode)
        finally:
            os.rename(guard, fichero)

    print("-" * 66)
    if FALLOS:
        print("%d control(es) FALLAN. atomrom NO es autoridad hasta"
              % len(FALLOS))
        print("que se arreglen.")
        return 1
    print("todos los controles pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
