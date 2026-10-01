/*
 * gfx8vmgeom -- extraccion de constantes y modelo. Ver gfx8vmgeom.h.
 *
 * Nota sobre el diseño: la extraccion es deliberadamente dumb. No interpreta
 * C; busca un ancla literal y lee numeros. El unico requisito es que el ancla
 * exista, y si no existe la herramienta falla en vez de devolver un cero que
 * luego se propaga como si fuera una propiedad del hardware.
 */
#include "gfx8vmgeom.h"

#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

/* --------------------------------------------------------------------- */
/* extraccion                                                             */
/* --------------------------------------------------------------------- */

bool gg_read_file(const char *path, char **out, size_t *out_len)
{
	FILE *f;
	long n;
	char *buf;
	size_t got;

	*out = NULL;
	if (out_len)
		*out_len = 0;

	f = fopen(path, "rb");
	if (!f)
		return false;
	if (fseek(f, 0, SEEK_END) != 0) {
		fclose(f);
		return false;
	}
	n = ftell(f);
	if (n < 0) {
		fclose(f);
		return false;
	}
	rewind(f);

	buf = malloc((size_t)n + 1);
	if (!buf) {
		fclose(f);
		return false;
	}
	got = fread(buf, 1, (size_t)n, f);
	fclose(f);
	buf[got] = '\0';
	*out = buf;
	if (out_len)
		*out_len = got;
	return true;
}

/*
 * Busca `anchor` y aplica `fmt` con sscanf sobre lo que hay justo despues.
 * `fmt` lo escribe quien llama y describe la forma real del texto; esta
 * funcion no lo reinterpreta. Devuelve true solo si la conversion completa
 * tiene exito, que es lo que impide el "scanf se comio la mitad".
 */
bool gg_extract_after(const char *text, const char *anchor, const char *fmt,
		      unsigned *out, unsigned count)
{
	const char *p;
	unsigned tmp[4];
	int rc;

	if (!text || !anchor || !fmt || !out)
		return false;
	if (count == 0 || count > 4)
		return false;

	p = strstr(text, anchor);
	if (!p)
		return false;
	p += strlen(anchor);

	switch (count) {
	case 1: rc = sscanf(p, fmt, &tmp[0]); break;
	case 2: rc = sscanf(p, fmt, &tmp[0], &tmp[1]); break;
	case 3: rc = sscanf(p, fmt, &tmp[0], &tmp[1], &tmp[2]); break;
	default: rc = sscanf(p, fmt, &tmp[0], &tmp[1], &tmp[2], &tmp[3]); break;
	}
	if (rc != (int)count)
		return false;

	memcpy(out, tmp, count * sizeof(*out));
	return true;
}

bool gg_extract_u64_after(const char *text, const char *anchor, uint64_t *out)
{
	const char *p;
	unsigned long long v;

	if (!text || !anchor || !out)
		return false;
	p = strstr(text, anchor);
	if (!p)
		return false;
	p += strlen(anchor);
	/*
	 * sscanf exige que los literales del formato coincidan caracter a
	 * caracter; solo se salta el espacio en blanco de las directivas de
	 * conversion. Sin este salto, "0x%llx" falla contra " 0x..." y el
	 * fallo se manifestaria como "no se localizo pte_addr_mask", que es
	 * un diagnostico falso: el numero si estaba ahi.
	 */
	while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
		p++;
	if (sscanf(p, "0x%llx", &v) != 1)
		return false;
	*out = (uint64_t)v;
	return true;
}

/*
 * Recorre el enumeradorBuscando `token` y devuelve su posicion. El recorrido
 * empieza tras "enum <anchor> {" y termina en el primer "};", de modo que un
 * token homonimo fuera del enumerador no se cuenta.
 */
bool gg_enum_ordinal(const char *text, const char *enum_anchor, const char *token,
		     long *out)
{
	const char *open_brace, *end, *p;
	long idx = 0;
	size_t tlen;

	if (!text || !enum_anchor || !token || !out)
		return false;
	open_brace = strstr(text, enum_anchor);
	if (!open_brace)
		return false;
	/*
	 * El conteo arranca DESPUES de la llave de apertura. Empezar en el
	 * propio "enum amd_asic_type" contaria dos identificadores de mas y
	 * desplazaria todos los ordinales en 2 -- que es exactamente lo que
	 * paso: CHIP_POLARIS12 salia 19 en lugar de 17, y la asercion fallo.
	 * El fallo era del extractor, no del corpus.
	 */
	open_brace = strchr(open_brace, '{');
	if (!open_brace)
		return false;
	end = strstr(open_brace, "};");
	if (!end || end <= open_brace)
		return false;

	tlen = strlen(token);
	p = open_brace;

	while (p < end) {
		/* avanzar al siguiente identificador */
		while (p < end && !(isalpha((unsigned char)*p) || *p == '_'))
			p++;
		if (p >= end)
			break;

		if (strncmp(p, token, tlen) == 0) {
			char after = p[tlen];
			if (!isalnum((unsigned char)after) && after != '_') {
				*out = idx;
				return true;
			}
		}

		/* saltar el identificador completo */
		while (p < end && (isalnum((unsigned char)*p) || *p == '_'))
			p++;
		idx++;
	}
	return false;
}

bool gg_macro_shift(const char *text, const char *macro, unsigned *out)
{
	const char *def, *sh;

	if (!text || !macro || !out)
		return false;
	def = strstr(text, macro);
	if (!def)
		return false;
	sh = strstr(def, "<<");
	if (!sh)
		return false;
	sh += 2;
	while (*sh == ' ' || *sh == '\t')
		sh++;
	if (sscanf(sh, "%u", out) != 1)
		return false;
	return true;
}

/* Primer literal hexadecimal que aparece tras la definicion del macro. */
bool gg_macro_mask(const char *text, const char *macro, uint64_t *out)
{
	const char *p;
	unsigned long long v;

	if (!text || !macro || !out)
		return false;
	p = strstr(text, macro);
	if (!p)
		return false;
	while (*p && !(p[0] == '0' && (p[1] == 'x' || p[1] == 'X')))
		p++;
	if (!*p)
		return false;
	if (sscanf(p, "0x%llx", &v) != 1)
		return false;
	*out = (uint64_t)v;
	return true;
}

/* --------------------------------------------------------------------- */
/* sha256, para que "es el fichero del tarball" sea un hecho y no una nota */
/* --------------------------------------------------------------------- */

/*
 * Implementacion propia en lugar de invocar sha256sum: la herramienta no
 * debe depender de un binario externo para decidir si su corpus es el que
 * cree. Es el mismo criterio que el guard de rx550-mem, que audita el
 * binario y no solo el fuente.
 */

struct gg_sha256 {
	uint32_t h[8];
	uint64_t len;
	unsigned char buf[64];
	size_t n;
};

static uint32_t gg_rotr(uint32_t x, unsigned n)
{
	return (x >> n) | (x << (32 - n));
}

static void gg_sha256_block(struct gg_sha256 *s, const unsigned char *p)
{
	static const uint32_t K[64] = {
		0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,
		0x59f111f1u,0x923f82a4u,0xab1c5ed5u,0xd807aa98u,0x12835b01u,
		0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,
		0xc19bf174u,0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,
		0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,0x983e5152u,
		0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,
		0x06ca6351u,0x14292967u,0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,
		0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
		0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,
		0xd6990624u,0xf40e3585u,0x106aa070u,0x19a4c116u,0x1e376c08u,
		0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,
		0x682e6ff3u,0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,
		0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
	};
	uint32_t w[64];
	uint32_t a, b, cc, d, e, f, g, hh;
	unsigned i;

	for (i = 0; i < 16; i++)
		w[i] = ((uint32_t)p[i * 4 + 0] << 24) |
		       ((uint32_t)p[i * 4 + 1] << 16) |
		       ((uint32_t)p[i * 4 + 2] << 8) |
		       ((uint32_t)p[i * 4 + 3]);
	for (i = 16; i < 64; i++) {
		uint32_t s0 = gg_rotr(w[i - 15], 7) ^ gg_rotr(w[i - 15], 18) ^
			      (w[i - 15] >> 3);
		uint32_t s1 = gg_rotr(w[i - 2], 17) ^ gg_rotr(w[i - 2], 19) ^
			      (w[i - 2] >> 10);
		w[i] = w[i - 16] + s0 + w[i - 7] + s1;
	}

	a = s->h[0]; b = s->h[1]; cc = s->h[2]; d = s->h[3];
	e = s->h[4]; f = s->h[5]; g = s->h[6]; hh = s->h[7];

	for (i = 0; i < 64; i++) {
		uint32_t S1 = gg_rotr(e, 6) ^ gg_rotr(e, 11) ^ gg_rotr(e, 25);
		uint32_t ch = (e & f) ^ ((~e) & g);
		uint32_t t1 = hh + S1 + ch + K[i] + w[i];
		uint32_t S0 = gg_rotr(a, 2) ^ gg_rotr(a, 13) ^ gg_rotr(a, 22);
		uint32_t mj = (a & b) ^ (a & cc) ^ (b & cc);
		uint32_t t2 = S0 + mj;
		hh = g; g = f; f = e; e = d + t1;
		d = cc; cc = b; b = a; a = t1 + t2;
	}

	s->h[0] += a; s->h[1] += b; s->h[2] += cc; s->h[3] += d;
	s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += hh;
}

static void gg_sha256_init(struct gg_sha256 *s)
{
	s->h[0] = 0x6a09e667u; s->h[1] = 0xbb67ae85u;
	s->h[2] = 0x3c6ef372u; s->h[3] = 0xa54ff53au;
	s->h[4] = 0x510e527fu; s->h[5] = 0x9b05688cu;
	s->h[6] = 0x1f83d9abu; s->h[7] = 0x5be0cd19u;
	s->len = 0;
	s->n = 0;
}

static void gg_sha256_update(struct gg_sha256 *s, const unsigned char *p, size_t n)
{
	s->len += (uint64_t)n;
	while (n) {
		size_t take = 64 - s->n;
		if (take > n)
			take = n;
		memcpy(s->buf + s->n, p, take);
		s->n += take;
		p += take;
		n -= take;
		if (s->n == 64) {
			gg_sha256_block(s, s->buf);
			s->n = 0;
		}
	}
}

static void gg_sha256_final(struct gg_sha256 *s, char out[65])
{
	uint64_t bits = s->len * 8u;
	unsigned char pad[72];
	size_t padlen;
	unsigned i;

	memset(pad, 0, sizeof(pad));
	pad[0] = 0x80;
	/* se rellena hasta que el bloque final quede a 56 mod 64 */
	padlen = (s->n < 56) ? (56 - s->n) : (120 - s->n);
	for (i = 0; i < 8; i++)
		pad[padlen + i] = (unsigned char)((bits >> (56 - 8 * i)) & 0xffu);
	gg_sha256_update(s, pad, padlen + 8);

	for (i = 0; i < 8; i++)
		snprintf(out + i * 8, 9, "%08x", s->h[i]);
	out[64] = '\0';
}

bool gg_file_sha256(const char *path, char out[65])
{
	struct gg_sha256 s;
	unsigned char chunk[4096];
	FILE *f;
	size_t got;

	f = fopen(path, "rb");
	if (!f)
		return false;
	gg_sha256_init(&s);
	while ((got = fread(chunk, 1, sizeof(chunk), f)) > 0)
		gg_sha256_update(&s, chunk, got);
	if (ferror(f)) {
		fclose(f);
		return false;
	}
	fclose(f);
	gg_sha256_final(&s, out);
	return true;
}

const char *const GG_ASIC_TYPE_SHA256_7_1_3 =
	"cea577df48a684246ef00d887350d42b9fa5048b9135ae5e8e93dc9eb94a7809";

bool gg_header_sha256_ok(const char *hdr_root)
{
	char path[2 * GG_MAX_PATH];
	char got[65];
	int n;

	n = snprintf(path, sizeof(path), "%s/include/drm/amd_asic_type.h", hdr_root);
	if (n < 0 || (size_t)n >= sizeof(path))
		return false;
	if (!gg_file_sha256(path, got))
		return false;
	return strcmp(got, GG_ASIC_TYPE_SHA256_7_1_3) == 0;
}

/*
 * La rama que decide block_size. Se afirma la FORMA, no el numero de linea,
 * porque el numero de linea cambia entre versiones y una cita por linea seria
 * justo el tipo de acoplamiento que este repo ya sufrio.
 */
enum gg_branch_shape gg_check_block_size_branch(const char *src_root)
{
	char path[2 * GG_MAX_PATH];
	char *txt = NULL;
	const char *gate, *nine, *alt;
	enum gg_branch_shape shape = GG_BRANCH_UNKNOWN;
	int n;

	n = snprintf(path, sizeof(path), "%s/drivers/gpu/drm/amd/amdgpu/amdgpu_vm.c",
		     src_root);
	if (n < 0 || (size_t)n >= sizeof(path))
		return GG_BRANCH_UNKNOWN;
	if (!gg_read_file(path, &txt, NULL))
		return GG_BRANCH_UNKNOWN;

	gate = strstr(txt, "num_level > 1)");
	if (!gate)
		goto out;
	nine = strstr(gate, "block_size = 9;");
	if (!nine)
		goto out;
	alt = strstr(nine, "amdgpu_vm_get_block_size(tmp)");
	if (!alt) {
		shape = GG_BRANCH_OTHER;
		goto out;
	}
	/* el else tiene que pasar tmp, no vm_size: es el nucleo del hallazgo */
	if (strstr(alt, "amdgpu_vm_get_block_size(vm_size)") == NULL)
		shape = GG_BRANCH_NUMLEVEL_GT1;
	else
		shape = GG_BRANCH_OTHER;

out:
	free(txt);
	return shape;
}

/* --------------------------------------------------------------------- */
/* corpus                                                                 */
/* --------------------------------------------------------------------- */

#define FAIL(...)                                                            \
	do {                                                                  \
		snprintf(why, why_len, __VA_ARGS__);                          \
		goto out;                                                       \
	} while (0)

bool gg_corpus_load(struct gg_corpus *c, const char *src_root,
		    const char *hdr_root, char *why, size_t why_len)
{
	char *vmh = NULL, *gmcc = NULL, *ptc = NULL, *gart_h = NULL;
	char *soc = NULL, *gfx = NULL;
	bool ok = false;
	unsigned v[4];
	uint64_t mask;
	const char *p;
	size_t i;
	char path[2 * GG_MAX_PATH];
	int n;

	if (!c || !src_root || !hdr_root || !why) {
		if (why && why_len)
			snprintf(why, why_len, "argumento nulo");
		return false;
	}
	memset(c, 0, sizeof(*c));
	why[0] = '\0';

	snprintf(c->src_root, sizeof(c->src_root), "%s", src_root);
	snprintf(c->hdr_root, sizeof(c->hdr_root), "%s", hdr_root);
	snprintf(c->amdgpu, sizeof(c->amdgpu),
		 "%s/drivers/gpu/drm/amd/amdgpu", src_root);
	snprintf(c->asic, sizeof(c->asic), "%s/include/drm/amd_asic_type.h",
		 hdr_root);

	/* La cabecera viene de un arbol distinto del de las fuentes, porque el
	 * corpus de este repo esta partido: working/baseline traen
	 * include/linux y nada mas. Se exige que la cabecera sea la de 7.1.3
	 * por hash, porque mezclarla sin comprobar seria repetir el fallo que
	 * este repo ya registro dos veces con arboles instrumentados. */
	if (!gg_header_sha256_ok(hdr_root))
		FAIL("amd_asic_type.h de %s no coincide con el sha256 de 7.1.3",
		     hdr_root);

/* Una ruta truncada se lee como un fichero que no existe, y el error seria
 * "no se pudo leer" en lugar de "la ruta no cabe". Se distingue aqui. */
#define LOAD(field, fname, label)                                           \
	do {                                                                  \
		n = snprintf(path, sizeof(path), "%s/%s", c->amdgpu, fname);  \
		if (n < 0 || (size_t)n >= sizeof(path))                       \
			FAIL("ruta truncada para %s", label);                 \
		if (!gg_read_file(path, &field, NULL))                          \
			FAIL("no se pudo leer %s (%s)", label, path);         \
	} while (0)

	if (!gg_read_file(c->asic, &soc, NULL))
		FAIL("no se pudo leer %s", c->asic);
	LOAD(vmh, "amdgpu_vm.h", "amdgpu_vm.h");
	LOAD(gmcc, "gmc_v8_0.c", "gmc_v8_0.c");
	LOAD(ptc, "amdgpu_vm_pt.c", "amdgpu_vm_pt.c");
	LOAD(gart_h, "amdgpu_gart.h", "amdgpu_gart.h");
	LOAD(gfx, "gfx_v8_0.c", "gfx_v8_0.c");

#undef LOAD

	/* --- la llamada que Polaris12 ejecuta de verdad ------------------- */
	/* gmc_v8_0.c: amdgpu_vm_adjust_size(adev, 64, 9, 1, 40) */
	if (!gg_extract_after(gmcc, "amdgpu_vm_adjust_size(adev,", "%u, %u, %u, %u",
			     v, 4))
		FAIL("ancla 'amdgpu_vm_adjust_size(adev,' no localizada en gmc_v8_0.c");
	c->min_vm_size_gb = v[0];
	c->fragment_size_default = v[1];
	c->max_level = v[2];
	c->max_bits = v[3];

	if (c->max_level != 1)
		FAIL("max_level=%u: este modelo solo cubre max_level==1 (GFX8)",
		     c->max_level);

	/* gmc_v8_0.c: adev->gmc.pte_addr_mask = 0x000000FFFFFFF000ULL */
	if (!gg_extract_u64_after(gmcc, "pte_addr_mask =", &c->pte_addr_mask))
		FAIL("no se localizo pte_addr_mask en gmc_v8_0.c");
	if ((c->pte_addr_mask & 0xfffULL) != 0)
		FAIL("pte_addr_mask no esta alineado a pagina: 0x%llx",
		     (unsigned long long)c->pte_addr_mask);
	c->pa_bits = 0;
	for (mask = c->pte_addr_mask; mask; mask >>= 1)
		c->pa_bits++;

	/* --- posiciones de bit, todas de amdgpu_vm.h --------------------- */
	{
		static const struct { const char *macro; size_t off; } bits[] = {
			{ "#define AMDGPU_PTE_VALID", offsetof(struct gg_corpus, bit_valid) },
			{ "#define AMDGPU_PTE_SYSTEM", offsetof(struct gg_corpus, bit_system) },
			{ "#define AMDGPU_PTE_SNOOPED", offsetof(struct gg_corpus, bit_snooped) },
			{ "#define AMDGPU_PTE_TMZ", offsetof(struct gg_corpus, bit_tmz) },
			{ "#define AMDGPU_PTE_EXECUTABLE", offsetof(struct gg_corpus, bit_executable) },
			{ "#define AMDGPU_PTE_READABLE", offsetof(struct gg_corpus, bit_readable) },
			{ "#define AMDGPU_PTE_WRITEABLE", offsetof(struct gg_corpus, bit_writeable) },
			{ "#define AMDGPU_PDE_PTE\t", offsetof(struct gg_corpus, bit_pde_pte) },
			{ "#define AMDGPU_PTE_PRT\t", offsetof(struct gg_corpus, bit_prt) },
			{ "#define AMDGPU_PTE_LOG", offsetof(struct gg_corpus, bit_log) },
			{ "#define AMDGPU_PTE_TF", offsetof(struct gg_corpus, bit_tf) },
			{ "#define AMDGPU_PTE_NOALLOC", offsetof(struct gg_corpus, bit_noalloc) },
			{ "#define AMDGPU_PDE_BFS", offsetof(struct gg_corpus, bit_bfs) },
		};
		for (i = 0; i < sizeof(bits) / sizeof(bits[0]); i++) {
			unsigned *slot = (unsigned *)((char *)c + bits[i].off);
			if (!gg_macro_shift(vmh, bits[i].macro, slot))
				FAIL("no se localizo el shift de '%s' en amdgpu_vm.h",
				     bits[i].macro);
			if (*slot >= 64)
				FAIL("shift >= 64 para '%s'", bits[i].macro);
		}
	}

	/* fragmento: ((x & 0x1fULL) << 7) -> shift y ancho */
	if (!gg_macro_shift(vmh, "#define AMDGPU_PTE_FRAG", &c->frag_shift))
		FAIL("no se localizo el shift de AMDGPU_PTE_FRAG");
	if (!gg_macro_mask(vmh, "#define AMDGPU_PTE_FRAG", &mask))
		FAIL("no se localizo la mascara de AMDGPU_PTE_FRAG");
	c->frag_width = 0;
	for (mask = mask; mask; mask >>= 1)
		c->frag_width += (unsigned)(mask & 1u);
	if (c->frag_shift + c->frag_width > 64)
		FAIL("el campo FRAG se sale de la palabra de 64 bits");

	/* --- generacion de GFX, que decide PDE_PTE_FLAG ------------------ */
	p = strstr(gfx, "gfx_v8_0_ip_block =");
	if (!p)
		FAIL("no se localizo gfx_v8_0_ip_block = en gfx_v8_0.c");
	if (sscanf(p, "gfx_v8_0_ip_block = "
		       "{ .type = AMD_IP_BLOCK_TYPE_GFX, "
		       ".major = %u, .minor = %u, .rev = %u",
		   &c->gfx_major, &c->gfx_minor, &c->gfx_rev) != 3)
		FAIL("no se pudo leer major/minor/rev de gfx_v8_0_ip_block");

	/* --- orden de ASIC: el gate de todas las ramas >= CHIP_VEGA10 ---- */
	if (!gg_enum_ordinal(soc, "enum amd_asic_type", "CHIP_POLARIS12",
			     &c->ord_polaris12))
		FAIL("CHIP_POLARIS12 no esta en amd_asic_type.h");
	if (!gg_enum_ordinal(soc, "enum amd_asic_type", "CHIP_VEGA10",
			     &c->ord_vega10))
		FAIL("CHIP_VEGA10 no esta en amd_asic_type.h");
	c->polaris12_before_vega10 = c->ord_polaris12 < c->ord_vega10;
	c->ord_vega12 = -1;
	(void)gg_enum_ordinal(soc, "enum amd_asic_type", "CHIP_VEGA12",
			      &c->ord_vega12);

	/* AMDGPU_PDE_PTE_FLAG selecciona >= IP_VERSION(12,0,0) */
	c->gfx_before_gfx12 = (c->gfx_major < 12);

	/* --- anclas que sostienen el modelo ----------------------------- */
	if (!strstr(ptc, "9 * (AMDGPU_VM_PDB0 - level)"))
		FAIL("la aritmetica de amdgpu_vm_pt_level_shift() cambio de forma");
	if (!strstr(ptc, "return AMDGPU_VM_PTE_COUNT(adev);"))
		FAIL("amdgpu_vm_pt_num_entries() no devuelve PTE_COUNT en la hoja");
	if (!strstr(gart_h, "#define AMDGPU_GPU_PAGE_SIZE 4096"))
		FAIL("AMDGPU_GPU_PAGE_SIZE no es 4096 en este corpus");

	ok = true;
out:
	free(vmh);
	free(gmcc);
	free(ptc);
	free(gart_h);
	free(soc);
	free(gfx);
	return ok;
}

#undef FAIL