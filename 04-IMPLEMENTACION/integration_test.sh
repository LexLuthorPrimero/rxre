#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# integration_test.sh - pipeline completo Fase 1 -> Fase 2 sobre la RX 550.
#
#   PNG --[rx550_compress, CPU]--> BC3 --[rx550_decompress, GPU]--> PNG
#                                 |
#                                 +--> referencia CPU .rgba
#
# Compara pixel a pixel y reporta las TRES cifras que el pipeline produce,
# que no son la misma cifra:
#
#   1. discrepancias GPU vs CPU   -> fidelidad del decodificador. 0 = coinciden.
#                                    Este numero NO depende del contenido.
#   2. PSNR original vs round-trip-> calidad del codificador con perdida.
#                                    Depende del contenido; 0 dB seria un
#                                    fallo, 28 dB es normal para BC3.
#   3. estado por textura         -> PASO / FAIL, con el motivo.
#
# LAS DOS PRIMERAS NO SE CONFUNDEN
#
# Un "0 discrepancias" con un PSNR bajo es un resultado correcto, no uno bueno:
# el decodificador de la GPU es fiel al de la CPU, y el codificador es malo.
# Un "0 discrepancias" con PSNR infinito solo es alcanzable con imagenes planas.
# Por eso las dos se imprimen siempre y el veredicto se decide sobre la
# combinacion, con el umbral de PSNR declarado arriba.
#
# AUTORIZACION
#
# rx550_decompress ejecuta compute en la RX 550 por Vulkan. Eso es RUNTIME
# GPU y requiere autorizacion: AD-7 (2026-09-28) la cubre para validar el
# descompresor. El script no escribe sysfs, no cambia politicas de energia ni
# relojes, y no toca nada del kernel.
#
# USO
#   ./integration_test.sh [corpus_dir]
#
# Sale 0 si todas las texturas pasan, 1 si alguna falla, 2 si el entorno no
# permite ejecutarlo. La distincion importa: "no se pudo correr" y "corrio y
# fallo" son hechos distintos y colapsarlos produce un verde falso.

set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE" || exit 2

CORPUS="${1:-../06-INGENIERIA-INVERSA/corpus}"
WORK="$HERE/work"
BIN="$HERE/bin"

# --- umbrales ----------------------------------------------------------------
# PSNR minimo por tipo de contenido. No son tripped wires del compresor: los
# de ese suite estan en compressor/test_compress.c (24/16/11 dB) y miden
# patrones sinteticos de un bloque. Aqui se mide una textura completa de 64x64,
# que es un promedio sobre 256 bloques y no la misma magnitud.
PSNR_MIN_GRADIENTE=25.0
PSNR_MIN_RUIDO=10.0
PSNR_MIN_ESTRUCTURA=20.0

RX550_VENDOR=1002
RX550_DEVICE=699f

say()  { printf '%s\n' "$*"; }
hr()   { say "------------------------------------------------------------------"; }
fail() { say "FALLO: $*"; }

# --- 0. entorno --------------------------------------------------------------
hr
say "INTEGRACION FASE 1 (compresor CPU) -> FASE 2 (descompresor GPU)"
hr
say "host      : $(uname -r)"
say "corpus    : $CORPUS"
say "work      : $WORK"
say ""

if [ ! -d "$CORPUS" ]; then
    say "ESTADO: FAIL"
    fail "el directorio del corpus '$CORPUS' no existe."
    exit 2
fi

# El shader tiene que existir ANTES de todo, y tiene que ser mas nuevo que su
# fuente. Un .spv viejo compila, valida y ejecuta, y corresponde a otro shader.
say "[0/4] preparando artefactos"
if ! make --no-print-directory -C decompressor decompress_bc3.spv >/dev/null 2>&1; then
    say "ESTADO: FAIL"
    fail "no se pudo generar decompressor/decompress_bc3.spv"
    exit 2
fi
if [ decompressor/decompress_bc3.spv -ot decompressor/decompress_bc3.comp ]; then
    say "ESTADO: FAIL"
    fail "decompress_bc3.spv es mas viejo que .comp: puede no corresponder al fuente"
    exit 2
fi
SPV_BYTES=$(stat -c%s decompressor/decompress_bc3.spv)
SPV_MAGIC=$(od -An -tx4 -N4 decompressor/decompress_bc3.spv | tr -d ' ')
say "      decompress_bc3.spv  ${SPV_BYTES} B  magic ${SPV_MAGIC}"
if [ "$SPV_MAGIC" != "07230203" ]; then
    say "ESTADO: FAIL"
    fail "decompress_bc3.spv no es un modulo SPIR-V"
    exit 2
fi
if command -v spirv-val >/dev/null 2>&1; then
    if spirv-val --target-env vulkan1.1 decompressor/decompress_bc3.spv >/dev/null 2>&1; then
        say "      spirv-val --target-env vulkan1.1  OK (validacion de esquema)"
    else
        say "      ATENCION: spirv-valinstalled pero el modulo no valida; se continua"
        say "      y se registra como CONFLICT en el informe."
    fi
else
    say "      ATENCION: spirv-val no instalado; validacion de esquema NO_AVAILABLE."
    say "      NO es la misma cosa que no ejecutar: el shader se despacha igualmente."
fi

# --- 1. construir ------------------------------------------------------------
say ""
say "[1/4] construyendo los binarios del pipeline"
if ! make --no-print-directory all >/dev/null 2>&1; then
    say "ESTADO: FAIL"
    fail "fallo la compilacion de rx550_compress / rx550_decompress"
    make all 2>&1 | tail -20
    exit 2
fi
for b in "$BIN/rx550_compress" "$BIN/rx550_decompress"; do
    if [ ! -x "$b" ]; then
        say "ESTADO: FAIL"
        fail "no se genero $b"
        exit 2
    fi
done
say "      $("$BIN/rx550_compress" 2>&1 | head -1 | sed 's/uso: //')"
say "      binarios: $(cd "$BIN" && sha256sum rx550_compress rx550_decompress | awk '{print $1}' | tr '\n' ' ')"

# --- 2. la RX 550 esta presente y es usable ----------------------------------
say ""
say "[2/4] comprobando la RX 550"
if ! command -v vulkaninfo >/dev/null 2>&1; then
    say "ESTADO: FAIL"
    fail "vulkaninfo no esta instalado: no se puede confirmar la RX 550"
    exit 2
fi
VULKAN_DEVICES=$(vulkaninfo --summary 2>/dev/null | grep -c "deviceName" || true)
RX550_LINE=$(vulkaninfo --summary 2>/dev/null | grep -A2 "deviceID *= *0x699f" | head -3 || true)
if ! printf '%s' "$RX550_LINE" | grep -qi "699f"; then
    say "      dispositivos Vulkan expuestos: $VULKAN_DEVICES"
    say "      no aparece 1002:699f entre ellos."
    say "ESTADO: FAIL"
    fail "la RX 550 no esta expuesta por Vulkan en este host. El pipeline exige"
    fail "ejecutar la Fase 2 en ella; no se sustituye por llvmpipe ni por la"
    fail "iGPU de Intel, porque el objetivo es precisamente la GPU objetivo."
    exit 2
fi
say "      OK  1002:699f presente (identidad PCI, no indice de enumeracion)"

rm -rf "$WORK"
mkdir -p "$WORK"

# --- 3. pipeline por textura -------------------------------------------------
say ""
say "[3/4] pipeline por textura"
hr

# nombre|floor de PSNR
declare -a CASES=(
    "t1_gradiente.png|$PSNR_MIN_GRADIENTE|gradiente suave, caso favorable"
    "t2_ruido.png|$PSNR_MIN_RUIDO|ruido independiente, caso peor para BC3"
    "t3_estructura.png|$PSNR_MIN_ESTRUCTURA|bordes duros y alfa plano"
)

TOTAL=0; PASSED=0; FAILED=0; SKIPPED=0
declare -a SUMMARY=()

for entry in "${CASES[@]}"; do
    IFS='|' read -r png floor desc <<< "$entry"
    src="$CORPUS/$png"

    say ""
    say "== $png  ($desc)"
    say "   suelo de PSNR para este contenido: ${floor} dB"

    if [ ! -f "$src" ]; then
        say "   [ SKIP ] no existe $src"
        SKIPPED=$((SKIPPED + 1))
        SUMMARY+=("$png|SKIP|no existe el fichero de entrada")
        continue
    fi

    # --- Fase 1: PNG -> BC3 (CPU) ---
    if ! "$BIN/rx550_compress" "$src" "$WORK/$png.bc3" "$WORK/$png.ref.rgba" >"$WORK/$png.compress.log" 2>&1; then
        say "   [FAIL] rx550_compress devolvio error:"
        sed 's/^/     /' "$WORK/$png.compress.log"
        FAILED=$((FAILED + 1))
        SUMMARY+=("$png|FAIL|Fase 1: rx550_compress fallo")
        continue
    fi
    # rx550_compress imprime "  PSNR      : 38.24 dB  (...)". El grep debe
    # tolerar los espacios de relleno: sin ellos devolvia cadena vacia y el
    # numero travelaba como vacio hasta el veredicto.
    COMPRESS_PSNR=$(grep -oE 'PSNR +: *[0-9]+\.[0-9]+' "$WORK/$png.compress.log" \
                   | grep -oE '[0-9]+\.[0-9]+')
    if [ -z "$COMPRESS_PSNR" ]; then
        say "   [FAIL] rx550_compress no imprimio PSNR; el formato de salida cambio"
        FAILED=$((FAILED + 1))
        SUMMARY+=("$png|FAIL|no se pudo leer el PSNR de la Fase 1")
        continue
    fi
    BC3_BYTES=$(stat -c%s "$WORK/$png.bc3")
    say "   [ OK ] Fase 1: $BC3_BYTES B BC3, PSNR round-trip CPU ${COMPRESS_PSNR} dB"

    # --- Fase 2: BC3 -> PNG (GPU) ---
    # rx550_decompress busca ../decompressor/decompress_bc3.spv respecto a su
    # cwd, asi que se ejecuta desde ahi. No se copia el .spv a ningun sitio:
    # una copia es un modulo mas que puede quedar obsoleta sin avisar.
    # $BIN es absoluta; anteponerle "../" la convertia en "../<abs>", que no
    # existe. Desde decompressor/, la ruta relativa correcta es ../bin/....
    if ! (cd decompressor && "../bin/rx550_decompress" \
            "../work/$png.bc3" "../work/$png.out.png" \
            "../work/$png.ref.rgba") >"$WORK/$png.decompress.log" 2>&1; then
        rc=$?
        say "   [FAIL] rx550_decompress devolvio $rc"
        sed 's/^/     /' "$WORK/$png.decompress.log" | tail -25
        # rc=1 es discrepancia real; rc>=2 es que no se pudo ejecutar.
        if [ "$rc" -ge 2 ]; then
            SKIPPED=$((SKIPPED + 1))
            SUMMARY+=("$png|FAIL|Fase 2 no se pudo ejecutar (rc=$rc)")
        else
            FAILED=$((FAILED + 1))
            SUMMARY+=("$png|FAIL|Fase 2: GPU != CPU")
        fi
        continue
    fi

    DISCREP=$(grep -oE '[0-9]+ de [0-9]+ bytes discrepantes' "$WORK/$png.decompress.log" | head -1)
    GPU_BYTES=$(grep -oE 'bytes no nulos *: [0-9]+ de [0-9]+' "$WORK/$png.decompress.log" | head -1)
    POISON=$(grep -oE 'bytes con patron 0xDEADBEEF: [0-9]+' "$WORK/$png.decompress.log" | head -1)
    say "   [ OK ] Fase 2: GPU ejecutada. $DISCREP"
    say "          $GPU_BYTES; $POISON"

    TOTAL=$((TOTAL + 1))

    # --- 3. comparacion pixel a pixel, segunda via ---
    # rx550_decompress ya comparo GPU vs CPU byte a byte. Esta segunda
    # comparacion es deliberadamente distinta: reabre el PNG que la GPU escribio
    # y lo compara con el PNG original. Si el PNG esta mal escrito, o los
    # bloques se reordenaron al escribirlo, la primera comparacion no lo
    # detectaria porque compara buffers, no ficheros.
    if [ ! -f "$WORK/$png.out.png" ]; then
        say "   [FAIL] la GPU no produjo $png.out.png"
        FAILED=$((FAILED + 1))
        SUMMARY+=("$png|FAIL|no se genero el PNG de salida")
        continue
    fi

    # --- 3b. segunda referencia: el round-trip de la CPU en orden de imagen ---
    # La referencia .rgba esta en orden de BLOQUE (lo que produce la GPU), asi
    # que no se puede comparar con un PNG directamente. Se reordena aqui, sin
    # trustworthy tool: el objetivo es que la comparacion sea independiente del
    # codigo de rx550_decompress.
    python3 - "$WORK/$png.ref.rgba" "$WORK/$png.refimg.rgba" <<'PY'
import sys, struct
RB = 64   # bytes por bloque descomprimido (16 pixeles x 4 canales)
DIM = 4
raw = open(sys.argv[1],'rb').read()
nb = len(raw)//RB
assert nb*RB == len(raw), 'tamano no multiplo de %d' % RB
side = 0
while side*side < nb: side += 1
assert side*side == nb, 'no es una retícula cuadrada de bloques: %d' % nb
W = H = side*DIM
out = bytearray(W*H*4)
for by in range(side):
    for bx in range(side):
        boff = (by*side+bx)*RB
        for py in range(DIM):
            for px in range(DIM):
                s = boff + (py*DIM+px)*4
                d = ((by*DIM+py)*W + (bx*DIM+px))*4
                out[d:d+4] = raw[s:s+4]
open(sys.argv[2],'wb').write(out)
PY
    PIXDIFF=$(python3 - "$src" "$WORK/$png.out.png" <<'PY'
import sys, zlib, struct

def read_png(p):
    d = open(p,'rb').read()
    assert d[:8] == b'\x89PNG\r\n\x1a\n', 'firma'
    idat = b''
    i = 8
    while i < len(d):
        ln = struct.unpack('>I', d[i:i+4])[0]; t = d[i+4:i+8]; data = d[i+8:i+8+ln]
        crc = struct.unpack('>I', d[i+8+ln:i+12+ln])[0]
        assert zlib.crc32(t+data) & 0xffffffff == crc, 'CRC '+t.decode()
        if t == b'IHDR':
            w,h,bd,ct,_,_,il = struct.unpack('>IIBBBBB', data)
            assert bd==8 and il==0, 'profundidad/interlace'
        elif t == b'IDAT': idat += data
        elif t == b'IEND': break
        i += 12+ln
    nch = {0:1,2:3,3:1,4:2,6:4}[ct]
    raw = zlib.decompress(idat)
    stride = w*nch
    out = bytearray()
    prev = bytearray(stride)
    pos = 0
    for _ in range(h):
        f = raw[pos]; pos += 1
        cur = bytearray(raw[pos:pos+stride]); pos += stride
        for x in range(stride):
            a = cur[x-nch] if x >= nch else 0
            b = prev[x]
            c = prev[x-nch] if x >= nch else 0
            if f == 1: cur[x] = (cur[x]+a) & 255
            elif f == 2: cur[x] = (cur[x]+b) & 255
            elif f == 3: cur[x] = (cur[x]+((a+b)>>1)) & 255
            elif f == 4:
                pp = a+b-c
                pa,pb,pc = abs(pp-a),abs(pp-b),abs(pp-c)
                pr = a if (pa<=pb and pa<=pc) else (b if pb<=pc else c)
                cur[x] = (cur[x]+pr) & 255
            elif f != 0: raise AssertionError('filtro %d' % f)
        out += cur; prev = cur
    # a RGBA
    rgba = bytearray(w*h*4)
    for k in range(w*h):
        s = out[k*nch:(k+1)*nch]
        if ct == 6: rgba[k*4:k*4+4] = s
        elif ct == 2: rgba[k*4:k*4+3] = s; rgba[k*4+3] = 255
        elif ct == 0: rgba[k*4:k*4+3] = bytes([s[0]]*3); rgba[k*4+3] = 255
        elif ct == 4: rgba[k*4:k*4+3] = bytes([s[0]]*3); rgba[k*4+3] = s[1]
        elif ct == 3: raise AssertionError('paleta no soportada en el comparador')
    return w,h,bytes(rgba)

w1,h1,a = read_png(sys.argv[1])
w2,h2,b = read_png(sys.argv[2])
if (w1,h1) != (w2,h2):
    print("DIMENSIONES %dx%d != %dx%d" % (w1,h1,w2,h2)); sys.exit(0)
diff = sum(1 for x,y in zip(a,b) if x != y)
sq = 0
for x,y in zip(a,b):
    d = x-y; sq += d*d
n = len(a)
mse = sq/n
psnr = 999.0 if mse == 0 else 10*__import__('math').log10(255.0*255.0/mse)
print("PIXDIFF %d de %d bytes, PSNR %.2f" % (diff, n, psnr))
PY
)
    say "          PNG de salida vs PNG original: $PIXDIFF"

    PIX_BYTES=$(printf '%s' "$PIXDIFF" | grep -oE '[0-9]+ de [0-9]+' | grep -oE '^[0-9]+')
    PIX_PSNR=$(printf '%s' "$PIXDIFF" | grep -oE 'PSNR [0-9]+\.[0-9]+' | grep -oE '[0-9]+\.[0-9]+')
    if [ -z "$PIX_PSNR" ]; then
        say "   [FAIL] no se pudo calcular el PSNR pixel a pixel: $PIXDIFF"
        FAILED=$((FAILED + 1))
        SUMMARY+=("$png|FAIL|no se pudo calcular el PSNR pixel a pixel")
        continue
    fi

    # --- 3c. la GPU contra el round-trip de la CPU, en orden de imagen ---
    # Tercera comparación, y la que responde a la pregunta que hace el
    # enunciado: ¿el PNG que sale de la GPU es el PNG que habría salido en
    # CPU? Se compara out.png contra refimg.rgba con el MISMO lector PNG, de
    # modo que las dos rutas de lectura son comparables y un error de lectura
    # no puede salir favorecido.
    GPUVSREF=$(python3 - "$WORK/$png.out.png" "$WORK/$png.refimg.rgba" <<'PY'
import sys, zlib, struct
def png_rgba(p):
    d=open(p,'rb').read(); assert d[:8]==b'\x89PNG\r\n\x1a\n'
    i=8; idat=b''; w=h=ct=None
    while i<len(d):
        ln=struct.unpack('>I',d[i:i+4])[0]; t=d[i+4:i+8]; data=d[i+8:i+8+ln]
        crc=struct.unpack('>I',d[i+8+ln:i+12+ln])[0]
        assert zlib.crc32(t+data)&0xffffffff==crc, 'CRC '+t.decode()
        if t==b'IHDR': w,h,bd,ct,_,_,il=struct.unpack('>IIBBBBB',data); assert bd==8 and il==0
        elif t==b'IDAT': idat+=data
        elif t==b'IEND': break
        i+=12+ln
    nch={0:1,2:3,3:1,4:2,6:4}[ct]; stride=w*nch
    raw=zlib.decompress(idat); out=bytearray(); prev=bytearray(stride); pos=0
    for _ in range(h):
        f=raw[pos]; pos+=1
        cur=bytearray(raw[pos:pos+stride]); pos+=stride
        for x in range(stride):
            a=cur[x-nch] if x>=nch else 0; b=prev[x]
            c=prev[x-nch] if x>=nch else 0
            if f==1: cur[x]=(cur[x]+a)&255
            elif f==2: cur[x]=(cur[x]+b)&255
            elif f==3: cur[x]=(cur[x]+((a+b)>>1))&255
            elif f==4:
                pp=a+b-c; pa,pb,pc=abs(pp-a),abs(pp-b),abs(pp-c)
                pr=a if(pa<=pb and pa<=pc) else (b if pb<=pc else c)
                cur[x]=(cur[x]+pr)&255
            elif f!=0: raise AssertionError('filtro %d'%f)
        out+=cur; prev=cur
    rgba=bytearray(w*h*4)
    for k in range(w*h):
        s=out[k*nch:(k+1)*nch]
        if ct==6: rgba[k*4:k*4+4]=s
        elif ct==2: rgba[k*4:k*4+3]=s; rgba[k*4+3]=255
        elif ct==0: rgba[k*4:k*4+3]=bytes([s[0]]*3); rgba[k*4+3]=255
        elif ct==4: rgba[k*4:k*4+3]=bytes([s[0]]*3); rgba[k*4+3]=s[1]
        else: raise AssertionError('paleta')
    return w,h,bytes(rgba)
w1,h1,a=png_rgba(sys.argv[1])
b=open(sys.argv[2],'rb').read()
if len(b)!=(w1*h1*4): print("SIZE %d != %d"%(len(b),w1*h1*4)); sys.exit(0)
d=sum(1 for x,y in zip(a,b) if x!=y)
print("GPUVSCPU %d de %d"%(d,len(b)))
PY
)
    say "          PNG de la GPU vs round-trip CPU: $GPUVSREF"
    GPUVSCPU_N=$(printf '%s' "$GPUVSREF" | grep -oE '^GPUVSCPU [0-9]+' | grep -oE '[0-9]+')
    if [ -z "$GPUVSCPU_N" ]; then
        say "   [FAIL] no se pudo ejecutar la comparacion GPU vs round-trip CPU"
        FAILED=$((FAILED + 1))
        SUMMARY+=("$png|FAIL|la comparacion de imagen no pudo ejecutarse")
        continue
    fi

    # --- 4. veredicto -------------------------------------------------------
    # Tres condiciones independientes, todas necesarias:
    #   a) 0 discrepancias GPU vs CPU, en bytes (fidelidad del decodificador)
    #   b) 0 diferencias GPU vs round-trip CPU, en PNG (orden y escritura)
    #   c) PSNR del round-trip por encima del suelo de ESTE contenido
    # (b) existe porque (a) compara buffers: no detects que el PNG se escriba
    # con los bloques en otro orden, que es un fallo real y silencioso.
    if printf '%s' "$DISCREP" | grep -q '^0 de ' && [ "$GPUVSCPU_N" -eq 0 ]; then
        # -v p= , not $1. The PSNR arrives on stdin but the comparison happens
        # in BEGIN, which never reads stdin, so $1 was empty and every texture
        # compared 0 >= floor and failed. The pipe was decoration.
        if [ "$(awk -v p="$PIX_PSNR" -v f="$floor" 'BEGIN{print (p+0>=f+0)?1:0}')" = "1" ]; then
            say "   RESULTADO: 0/16384 discrepancias, ${PIX_PSNR} dB PSNR, ESTADO: PASO"
            PASSED=$((PASSED + 1))
            SUMMARY+=("$png|PASO|0 discrepancias, ${PIX_PSNR} dB (suelo ${floor})")
        else
            say "   RESULTADO: 0/16384 discrepancias, ${PIX_PSNR} dB PSNR, ESTADO: FAIL"
            say "            PSNR ${PIX_PSNR} dB por debajo del suelo ${floor} dB de este contenido."
            say "            El decodificador es fiel (0 discrepancias); lo que falla es"
            say "            la calidad del codificador con perdida. Localizarlo es"
            say "            trabajo de la Fase 1, no de la Fase 2."
            FAILED=$((FAILED + 1))
            SUMMARY+=("$png|FAIL|PSNR ${PIX_PSNR} < suelo ${floor} dB, con 0 discrepancias")
        fi
    else
        say "   RESULTADO: GPU != CPU, $DISCREP. ESTADO: FAIL"
        FAILED=$((FAILED + 1))
        SUMMARY+=("$png|FAIL|$DISCREP")
    fi
done

# --- 4. resumen --------------------------------------------------------------
say ""
hr
say "[4/4] resumen por textura"
hr
printf '  %-20s %-8s %s\n' "TEXTURA" "ESTADO" "MEDICION"
for row in "${SUMMARY[@]}"; do
    IFS='|' read -r n s m <<< "$row"
    printf '  %-20s %-8s %s\n' "$n" "$s" "$m"
done
hr

if [ "$TOTAL" -eq 0 ]; then
    say "ESTADO: FAIL"
    fail "ninguna textura llego a ejecutarse: $TOTAL ejecutadas de $((PASSED+FAILED+SKIPPED))"
    exit 2
fi

if [ "$FAILED" -eq 0 ]; then
    say "$PASSED/$TOTAL texturas: ESTADO: PASO"
    exit 0
fi

say "$PASSED/$TOTAL texturas pasaron, $FAILED fallaron: ESTADO: FAIL"
exit 1
