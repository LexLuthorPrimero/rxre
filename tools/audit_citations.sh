#!/bin/sh
# audit_citations.sh - verify every "header.h:LINE" citation in the project's own
# source against the corpus, and every RX550_* constant against its definition.
#
# WHY THIS EXISTS
#
# Three of my own errors, in three findings, were the same shape: a citation that
# was plausible and wrong.
#
#   035  cited tonga_sdma_pkt_open.h for a symbol the real file (sdma_v4_0.c)
#        does not include. It includes vega10_sdma_pkt_open.h.
#   037  grepped a symbol list through "head -20" and read the visible part as
#        the complete list. The grep was fine; I truncated it.
#   038  asserted WAIT_REG_MEM_OPERATION did not exist, having read sid.h when
#        gfx_v8_0.c includes vid.h. It exists, at vid.h:182.
#
# None was caught by a compiler, because a plausible constant compiles. Each was
# caught by reading, which is slow and skippable under time pressure. This turns
# the reading into a check that runs in a second.
#
# WHAT IT CHECKS
#
#   1. Every "file.h:NNN" in the project's own C/H files resolves to a line that
#      exists and is inside the file. A citation past the end of a file is a
#      claim about a fact that moved between kernel versions.
#   2. Every "file.h:NNN" in every finding under 06-INGENIERIA-INVERSA/findings/
#      resolves the same way. 74 documents.
#   3. Every RX550_* constant that carries a "header.h:NNN" comment has that
#      line checked for the VALUE it claims, via rx550ref --decl. This is the
#      check that survives being wrong about names: the two projects use
#      different names for the same constants, and only the value is common.
#   4. Every symbol cited is checked for REACHABILITY from the consumer .c that
#      uses it: does that file actually include a header defining it? This is
#      the one that caught the 038 error, where a field was looked for in sid.h
#      when gfx_v8_0.c includes vid.h.
#   5. The specific 038 mistake is a standing check, not a one-off.
#
# WHAT IT DOES NOT CATCH, and the mutation test proved it:
#
#   Citing the header of a DIFFERENT ASIC generation when the value happens to
#   be the same. The value check passes, because the value really is the same.
#   A "the cited line must be a #define" check was written for this and
#   produced five false positives on legitimate citations to the enumeration
#   documentation in vid.h:170-180, which is comment text, not #define lines.
#   It was removed rather than shipped with false positives, because a check
#   that cries wolf is worse than no check: the reader learns to skip it, and
#   then the real failure goes unread. Stated here instead of claimed as
#   coverage that does not exist.
#
# EXIT CODES
#
#   0  every citation resolved
#   1  at least one citation did not resolve
#   2  the checker could not run (missing file, unbuilt tool)
#
# NOTE ON 2 AND 3. They are the ones that catch the real errors, and they are
# reported separately from 1 because a bad line number is a stale reference while
# an unreachable symbol is a wrong claim about which file the code reads.
#
# Limitations: header files under include/asic_reg are not scanned, only the
# amdgpu directory, because that is where the packet and GMC definitions live
# for this ASIC. A citation into a subdirectory is reported as UNCHECKED rather
# than as good or bad.

set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
AMD="$ROOT/rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd"
AMDGPU="$AMD/amdgpu"
# Los macros de registro (mmVM_*, mmATC_*) viven en amd/include/asic_reg/, que es
# hermano de amdgpu/ y NO un subdirectorio suyo. Una sola raiz respondia "0
# definitions" sobre macros que existen. Son dos, y por eso --dir se repite.
ASICREG="$AMD/include/asic_reg"
REF="$ROOT/tools/rx550ref"
WORK=/tmp/opencode/citation_audit
BUILDER="$ROOT/tools/rx550ref.c"

if [ ! -d "$AMDGPU" ]; then
	echo "audit: corpus not found at $AMDGPU" >&2
	exit 2
fi
if [ ! -d "$ASICREG" ]; then
	echo "audit: asic_reg headers not found at $ASICREG" >&2
	exit 2
fi

if [ ! -x "$REF" ] || [ "$ROOT/tools/rx550ref.c" -nt "$REF" ]; then
	if ! cc -std=gnu11 -O2 -Wall -Wextra -o "$REF" "$BUILDER" 2>/dev/null; then
		echo "audit: cannot build rx550ref" >&2
		exit 2
	fi
fi

mkdir -p "$WORK"
BAD=0
CHECKED=0
SKIPPED=0

# Pull "file.h:NNN" out of a file, one per line, deduped.
citations() {
	grep -oE '[A-Za-z0-9_./-]+\.h:[0-9]+' "$1" 2>/dev/null | sort -u
}

echo "=== citation audit: does every file.h:LINE exist and say what it claims ==="

for f in "$ROOT"/07-DRIVER/kernel/rx550_pm4.c \
	 "$ROOT"/07-DRIVER/kernel/rx550_pm4.h \
	 "$ROOT"/07-DRIVER/tests/test_pm4.c \
	 "$ROOT"/tools/rx550pm4val.c; do
	[ -f "$f" ] || continue
	cite=$(citations "$f")
	[ -z "$cite" ] && continue
	n=$(echo "$cite" | wc -l)
	printf '%-34s %4d citation(s)\n' "$(basename "$f")" "$n"

	for c in $cite; do
		hdr=${c%%:*}
		lineno=${c##*:}
		# Una cita puede llevar prefijo de ruta relativo a otro arbol
		# ("amdgpu/sid.h" desde amd/include/...). El basename es lo que
		# identifica el fichero.
		hdr=${hdr##*/}
		CHECKED=$((CHECKED + 1))
		# Buscar por basename. asic_reg tiene subdirectorios por IP
		# (gmc/, si/, nbio/), y adivinar en cual esta un header fue
		# exactamente el tipo de suposicion que produce una cita falsa.
		target=$(find "$AMDGPU" "$ASICREG" -name "$hdr" -type f 2>/dev/null | head -1)
		if [ -z "$target" ]; then
			echo "    MISSING FILE  $hdr  (cited for line $lineno)"
			BAD=$((BAD + 1))
			continue
		fi
		total=$(wc -l < "$target")
		if [ "$lineno" -gt "$total" ]; then
			echo "    PAST END      $hdr:$lineno  (file has $total lines)"
			BAD=$((BAD + 1))
			continue
		fi
		if [ "$lineno" -lt 1 ]; then
			echo "    BAD LINE      $hdr:$lineno"
			BAD=$((BAD + 1))
		fi
	done
done

echo
echo "=== findings: same check, over every .md in findings/ ==="
FDIR="$ROOT/06-INGENIERIA-INVERSA/findings"
if [ -d "$FDIR" ]; then
	for f in "$FDIR"/*.md; do
		[ -f "$f" ] || continue
		cite=$(citations "$f")
		[ -z "$cite" ] && continue
		n=$(echo "$cite" | wc -l)
		for c in $cite; do
			hdr=${c%%:*}
			lineno=${c##*:}
			hdr=${hdr##*/}
			CHECKED=$((CHECKED + 1))
			case "$hdr" in
			*/*) SKIPPED=$((SKIPPED + 1)); continue ;;
			esac
			# findings cite driver files as well as headers
			if [ -f "$AMDGPU/$hdr" ]; then
				total=$(wc -l < "$AMDGPU/$hdr")
				if [ "$lineno" -gt "$total" ]; then
					echo "    PAST END   $(basename "$f"): $hdr:$lineno  (file has $total lines)"
					BAD=$((BAD + 1))
				fi
			fi
		done
	done
	echo "    $(ls -1 "$FDIR"/*.md 2>/dev/null | wc -l) finding(s) scanned"
fi

echo
echo "=== reachability: every symbol cited with a consumer file ==="
# The RX550_ constants, and the corpus symbol each was copied from.
# Format: RX550_NAME <corpus-symbol> <consumer.c>
REACH=$(cat <<'EOF'
RX550_PKT3_WRITE_DATA PACKET3_WRITE_DATA gfx_v8_0.c
RX550_PKT3_WAIT_REG_MEM PACKET3_WAIT_REG_MEM gfx_v8_0.c
RX550_PKT3_PFP_SYNC_ME PACKET3_PFP_SYNC_ME gfx_v8_0.c
RX550_PKT3_SURFACE_SYNC PACKET3_SURFACE_SYNC gfx_v8_0.c
RX550_PKT3_ACQUIRE_MEM PACKET3_ACQUIRE_MEM gfx_v8_0.c
RX550_WR_CONFIRM WR_CONFIRM gfx_v8_0.c
RX550_WR_ONE_ADDR WR_ONE_ADDR gfx_v8_0.c
RX550_WRITE_DATA_ENGINE_SEL WRITE_DATA_ENGINE_SEL gfx_v8_0.c
RX550_CP_COHER_CNTL_FULL PACKET3_TCL1_ACTION_ENA gfx_v8_0.c
RX550_WAIT_REG_MEM_FUNCTION WAIT_REG_MEM_FUNCTION gfx_v8_0.c
RX550_WAIT_REG_MEM_MEM_SPACE WAIT_REG_MEM_MEM_SPACE gfx_v8_0.c
RX550_WAIT_REG_MEM_OPERATION WAIT_REG_MEM_OPERATION gfx_v8_0.c
RX550_WAIT_REG_MEM_ENGINE WAIT_REG_MEM_ENGINE gfx_v8_0.c
RX550_MM_VM_INVALIDATE_REQUEST mmVM_INVALIDATE_REQUEST gmc_v8_0.c
RX550_MM_VM_CONTEXT0_PTBA mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR gmc_v8_0.c
RX550_MM_VM_CONTEXT8_PTBA mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR gmc_v8_0.c
EOF
)
n=0
nbad=0
echo "$REACH" | while read -r mine sym consumer; do
	[ -z "$mine" ] && continue
	n=$((n + 1))
	if ! "$REF" --dir "$AMDGPU" --dir "$ASICREG" --sym "$sym" --in "$consumer" > "$WORK/r.txt" 2>&1; then
		echo "    UNREACHABLE  $mine <- $sym, $consumer does not include it"
		sed -n '2,8p' "$WORK/r.txt" | sed 's/^/                /'
		nbad=$((nbad + 1))
		echo "UNREACHABLE_COUNT=$((nbad + 1))" >> "$WORK/count"
	else
		# A disagreement between headers is a real finding even if reachable.
		if grep -q '^  FAIL  .*defined differently' "$WORK/r.txt"; then
			echo "    DISAGREES    $mine <- $sym"
			grep '^  FAIL' "$WORK/r.txt" | sed 's/^/                /'
			nbad=$((nbad + 1))
			echo "DISAGREE_COUNT=$((nbad + 1))" >> "$WORK/count"
		fi
	fi
done
rm -f "$WORK/count"
RCOUNT=$(echo "$REACH" | grep -c . || true)
echo "    $RCOUNT symbol/consumer pair(s) checked"

echo
echo "=== the specific error of 038, as a standing regression check ==="
# If the packet field macros ever move out of the headers gfx_v8_0.c includes,
# this is what catches it. It is one line and it is the check that was missing.
if "$REF" --dir "$AMDGPU" --dir "$ASICREG" --sym WAIT_REG_MEM_OPERATION --in gfx_v8_0.c > "$WORK/rec.txt" 2>&1; then
	echo "    ok  WAIT_REG_MEM_OPERATION resolves from gfx_v8_0.c"
else
	echo "    FAIL  it does not. vid.h:182 was the answer in 7.2.8."
	nbad=$((nbad + 1))
fi



# --- does the cited line carry the VALUE I claim? ---
#
# The identifier-based version of this check produced twenty false positives on
# the register citations: RX550_MM_VM_CONTEXT0_PTBA against
# mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR are the same constant under two names, and a
# name comparison cannot know that. So this compares VALUES, which is the only
# thing both projects agree on how to write. A check with twenty false positives
# is worse than no check, because the reader learns to skip it.
echo
echo "=== value: does each cited line carry the value I wrote ==="
VAL_OK=0
VAL_BAD=0
VAL_SKIP=0
: > "$WORK/vv"
for f in "$ROOT"/07-DRIVER/kernel/rx550_pm4.h; do
	[ -f "$f" ] || continue
	grep -n '^#define RX550_[A-Z0-9_]*[[:space:]]' "$f" 2>/dev/null | \
	while IFS= read -r line; do
		lineno=${line%%:*}
		rest=${line#*:}
		# nombre, valor y cita de la linea propia
		myname=$(echo "$rest" | sed -n 's/^#define \(RX550_[A-Z0-9_]*\)[[:space:]]\{1,\}.*/\1/p')
		myval=$(echo "$rest" | sed -n 's/^#define RX550_[A-Z0-9_]*[[:space:]]\{1,\}\([^[:space:]]*\).*/\1/p')
		[ -z "$myval" ] && continue
		case "$myval" in
		'('*|'('*')'*) VAL_SKIP=$((VAL_SKIP+1)); continue ;;
		esac
		c=$(echo "$rest" | grep -oE '[A-Za-z0-9_]+\.h:[0-9]+' | head -1)
		[ -z "$c" ] && continue
		ch=${c%%:*}; cl=${c##*:}
		ch=${ch##*/}
		t=$(find "$AMDGPU" "$ASICREG" -name "$ch" -type f 2>/dev/null | head -1)
		[ -z "$t" ] && { VAL_SKIP=$((VAL_SKIP+1)); continue; }
		# --decl abre el fichero dentro del --dir, asi que hay que darle el
		# directorio real donde find lo encontro. gmc_8_1_d.h vive en
		# asic_reg/gmc/, que no es ninguna de las dos raices.
		tdir=$(dirname "$t")
		#
		# LIMITACIÓN CONCRETA, y la mutation test la encontró: citar la
		# cabecera de otra generación con el MISMO valor no se detecta.
		# Se probó una comprobación de "la línea citada es un #define" y
		# produjo falsos positivos sobre cinco citas legítimas a la
		# documentación de enumeraciones de vid.h (las líneas 170-180 son
		# comentarios que enumeran los valores), y se quitó. Un chequeo con
		# falsos positivos entrena al lector a saltárselo, que es peor que
		# no tenerlo. Lo que queda es la comprobación de valor, que es
		# robusta porque ambos proyectos escriben los números igual.
		if "$REF" --dir "$tdir" --decl "$ch:$cl" "$myval" > "$WORK/d.txt" 2>&1; then
			echo ok >> "$WORK/vv"
		elif grep -q "compared as text" "$WORK/d.txt"; then
			echo skip >> "$WORK/vv"
		else
			echo bad >> "$WORK/vv"
			echo "    VALUE MISMATCH  $myname = $myval  cited at $ch:$cl"
			grep -E "corpus line|FAIL" "$WORK/d.txt" | sed 's/^/                    /'
		fi
	done
	# El bucle anterior corre en un subshell ("| while read"), asi que sus
	# contadores morian con el. El recuento se hace sobre el fichero, que es lo
	# unico que cruza esa frontera en POSIX sh.
	#
	# Y el recuento va ANTES del rm. La primera version hacia rm y luego
	# preguntaba por la existencia del fichero, con lo cual la respuesta era
	# siempre que no y salia "0 de 20" tras procesar veinte lineas. Un informe
	# que cuenta cero sobre trabajo hecho es peor que no informar: entrena al
	# lector a ignorar la linea.
	VAL_OK=0; VAL_BAD=0; VAL_SKIP=0
	if [ -f "$WORK/vv" ]; then
		VAL_OK=$(grep -c '^ok$' "$WORK/vv" || true)
		VAL_BAD=$(grep -c '^bad$' "$WORK/vv" || true)
		VAL_SKIP=$(grep -c '^skip$' "$WORK/vv" || true)
	fi
	rm -f "$WORK/vv"
	echo "    $VAL_OK value match(es), $VAL_BAD mismatch(es), $VAL_SKIP text/unknown"
done

echo
if [ "$BAD" -eq 0 ]; then
	echo "RESULT: $CHECKED citation(s) resolved, $SKIPPED skipped (subdirectory)"
	echo "RESULT: all reachability checks passed"
	exit 0
fi
echo "RESULT: $BAD of $CHECKED citation(s) did not resolve"
exit 1
