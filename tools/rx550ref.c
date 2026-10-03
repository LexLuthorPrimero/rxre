/*
 * rx550ref - symbol provenance resolver for the RX 550 (GFX8) corpus.
 *
 * THE ERROR CLASS THIS EXISTS TO PREVENT
 *
 * Three of my own errors, in three different findings, were the same mistake:
 *
 *   035  cited SDMA_OP_GEN_PTEPDE from tonga_sdma_pkt_open.h when the file that
 *        matters is sdma_v4_0.c, whose header is vega10_sdma_pkt_open.h. Right
 *        file, wrong ASIC.
 *   037  grepped "PAGE_TABLE_BASE_ADDR" through "head -20" and read the visible
 *        part as the complete list. The grep was fine; I truncated it.
 *   038  asserted WAIT_REG_MEM_OPERATION did not exist, having grepped sid.h
 *        when gfx_v8_0.c includes vi.h/vi_structs.h/vid.h. The macro is in
 *        vid.h:182.
 *
 * The common shape: a plausible value obtained from a source that was not the one
 * the code actually uses. None of them was caught by a compiler, because a
 * plausible constant compiles. All three were caught by reading, which is slow
 * and easy to skip.
 *
 * So: the check is mechanised. Given a symbol, this tool answers three questions
 * that have to be answered before citing it.
 *
 *   1. WHERE is it defined? Every #define of that exact name, with file:line.
 *   2. DO THEY AGREE? If six headers define it and one says something else, that
 *      is a trap, and the tool says so instead of leaving it to be discovered.
 *   3. DOES THE CONSUMER ACTUALLY INCLUDE THE WINNING HEADER? This is the
 *      question none of the three answers above covers, and it is the one that
 *      caught all three of my errors. gfx_v8_0.c does not include sid.h; the
 *      WAIT_REG_MEM_* fields are not there. It includes vid.h. So a citation of
 *      "sid.h:398" for a macro gfx_v8_0.c uses is a citation of a file the code
 *      never reads.
 *
 * It also refuses to let a count pass unnoticed, which is 037's lesson in
 * general form: every list this tool prints is preceded by the number of matches
 * found, and a search with more matches than fit is declared TRUNCATED rather
 * than silently trimmed.
 *
 * LIMITATIONS, because a provenance tool that overstates itself is worse than
 * none:
 *
 *   - It reads #include lines and #define lines as text. It does not preprocess,
 *     so a macro defined through another macro's expansion is not resolved.
 *   - Include guards and conditional compilation are ignored: a header listed in
 *     an #if is reported as included whether or not the branch is live.
 *   - It cannot tell you which header a symbol is "really" from. It tells you
 *     what the given consumer file includes and whether that is consistent with
 *     the citation. Deciding whether a value is right is still a reading job.
 *   - It knows nothing about the hardware.
 *
 * Build: cc -std=gnu11 -O2 -Wall -Wextra -o rx550ref rx550ref.c
 * Usage: rx550ref --dir <amdgpu-dir> --sym NAME [--in FILE] [--max N]
 *        rx550ref --dir <amdgpu-dir> --includes FILE
 *        rx550ref --dir <amdgpu-dir> --check FILE:NUMBER   (is this citation real?)
 *        rx550ref --selftest
 */

#include <ctype.h>
#include <dirent.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MAXDEFS	64
#define MAXINC	128
#define MAXLINE	4096
#define MAXPATH	1024

struct def {
	char file[MAXPATH];
	int line;
	char value[128];
	bool funclike;	/* "#define NAME(x) ..." rather than "#define NAME v" */
};

struct inc {
	char file[256];
	char line[64];
};

/* How many matches a search found, independent of how many we printed. The whole
 * point: 037 read a truncated list as a complete one. */
static unsigned g_found;
static unsigned g_shown;
static bool     g_truncated;

static int g_errors;
static int g_warnings;
static int g_checks;

static void out(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
}

static void fail(const char *fmt, ...)
{
	va_list ap;

	g_errors++;
	out("  FAIL  ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	out("\n");
}

static void warn(const char *fmt, ...)
{
	va_list ap;

	g_warnings++;
	out("  warn  ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	out("\n");
}

static void pass(const char *fmt, ...)
{
	va_list ap;

	g_checks++;
	out("  ok    ");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	out("\n");
}

static char *trim(char *s)
{
	char *e;

	while (*s && isspace((unsigned char)*s))
		s++;
	if (!*s)
		return s;
	e = s + strlen(s) - 1;
	while (e > s && isspace((unsigned char)*e))
		*e-- = '\0';
	return s;
}

/* Collapse runs of whitespace so a #define line's value can be compared across
 * headers that align it with tabs. "0x3F" and "0x3F" must compare equal even
 * when one arrived as "0x3F\t\t\t". */
static void squeeze(char *s)
{
	char *r = s;
	bool sp = false;

	for (; *s; s++) {
		if (isspace((unsigned char)*s)) {
			sp = true;
			continue;
		}
		if (sp && r != s)
			*r++ = ' ';
		sp = false;
		*r++ = *s;
	}
	*r = '\0';
}

static bool is_ident_char(int c)
{
	return isalnum(c) || c == '_';
}

/*
 * Do two #define values denote the same constant?
 *
 * Text comparison is wrong in both directions:
 *
 *   - "0x51e" and "0x051E" are the same number, differently written. Reporting
 *     a disagreement there trains the reader to ignore disagreements, which is
 *     how a real one gets missed. A tool that cries wolf is worse than none.
 *   - "(1u << 20)" and "(1 << 20)" are the same too, and it is not obvious by
 *     inspection, so they are compared as text and agree only when written the
 *     same. That is a known limitation, not a solved one.
 *
 * So: a pure numeric value is normalised through strtoull before comparison.
 * Anything with an operator in it is compared as text, and the report says which
 * comparison was used so a reader is never left guessing how firm a "agree" is.
 */
enum cmp_result {
	CMP_SAME,	/* equal as numbers, or identical as text */
	CMP_DIFFERENT,	/* genuinely different */
	CMP_TEXT_ONLY	/* contains an operator: compared as text */
};

static enum cmp_result compare_values(const char *a, const char *b)
{
	char ea_buf[MAXLINE], eb_buf[MAXLINE];
	char *ea = ea_buf, *eb = eb_buf;
	char *pa, *pb;
	unsigned long long va, vb;

	snprintf(ea_buf, sizeof ea_buf, "%s", a);
	snprintf(eb_buf, sizeof eb_buf, "%s", b);
	pa = trim(ea);
	pb = trim(eb);

	/*
	 * A pure integer literal, optionally signed and with u/l suffixes. The
	 * digit test comes first so "0x51e" is not read as decimal, and the
	 * strtoull base is 0 so the C literal rules apply.
	 */
	if (isdigit((unsigned char)*pa) || *pa == '-' || *pa == '+') {
		char *end;

		va = strtoull(pa, &end, 0);
		while (end && (isspace((unsigned char)*end) ||
			       *end == 'u' || *end == 'U' ||
			       *end == 'l' || *end == 'L'))
			end++;
		if (end && *end == '\0') {
			vb = strtoull(pb, &end, 0);
			while (end && (isspace((unsigned char)*end) ||
				       *end == 'u' || *end == 'U' ||
				       *end == 'l' || *end == 'L'))
				end++;
			if (end && *end == '\0')
				return va == vb ? CMP_SAME : CMP_DIFFERENT;
			return CMP_TEXT_ONLY;
		}
	}

	/* An expression: comparison by text, and the report says so. */
	if (strcmp(pa, pb) == 0)
		return CMP_SAME;
	return CMP_TEXT_ONLY;
}

/*
 * Collect every `#define NAME ...` for the given symbol across the directory.
 * Returns the number found, which may exceed what is stored: the caller must
 * use the return value, not the array, to know whether it is looking at
 * everything.
 */
/*
 * How deep find_defs recurses.
 *
 * The register macros this project cites (mmVM_*, mmATC_*) live in
 * include/asic_reg/gmc/ and include/asic_reg/si/, one or two levels below the
 * amdgpu directory, and they are reached by gmc_v8_0.c through gmc_v8_0.c's own
 * #include. Depth 2 is enough for that and shallow enough that the walk does not
 * wander into a kernel tree. The count is always the return value, never the
 * array length: if these ever converge, the tool would be able to hide a match,
 * which is 037's failure exactly.
 */
#define MAXDEPTH 2
#define MAXROOTS 4

static unsigned find_defs_r(const char *dir, const char *sym, struct def *defs,
			    int max, int depth)
{
	DIR *d = opendir(dir);
	struct dirent *e;
	unsigned found = 0;
	size_t symlen = strlen(sym);

	if (!d) {
		if (depth == 0)
			out("rx550ref: cannot open %s\n", dir);
		return 0;
	}

	while ((e = readdir(d)) != NULL) {
		char path[MAXPATH];
		char line[MAXLINE];
		FILE *f;
		int lineno = 0;

		if (e->d_name[0] == '.')
			continue;
		snprintf(path, sizeof path, "%s/%s", dir, e->d_name);

		/* A subdirectory: descend, but only while depth allows, and only
		 * where .h files actually live. Skipping known non-source trees
		 * keeps the walk fast enough to run on every citation. */
		{
			struct stat sb;

			if (stat(path, &sb) != 0)
				continue;
			if (S_ISDIR(sb.st_mode)) {
				if (depth + 1 < MAXDEPTH)
					found += find_defs_r(path, sym, defs,
							     max, depth + 1);
				continue;
			}
		}

		if (strlen(e->d_name) < 3 ||
		    strcmp(e->d_name + strlen(e->d_name) - 2, ".h") != 0)
			continue;

		f = fopen(path, "r");
		if (!f)
			continue;

		while (fgets(line, sizeof line, f)) {
			char *p = line;
			char *name;
			char *val;
			bool funclike;

			lineno++;
			while (*p == ' ' || *p == '\t')
				p++;
			if (*p != '#')
				continue;
			p++;
			while (*p == ' ' || *p == '\t')
				p++;
			if (strncmp(p, "define", 6) != 0)
				continue;
			p += 6;
			if (is_ident_char((unsigned char)*p))
				continue;
			while (*p == ' ' || *p == '\t')
				p++;
			name = p;
			while (is_ident_char((unsigned char)*p))
				p++;
			if ((size_t)(p - name) != symlen ||
			    strncmp(name, sym, symlen) != 0)
				continue;
			val = trim(p);
			funclike = (*p == '(');
			if (funclike) {
				char *r = val;
				char *sp;

				/* Keep the signature, drop the body: a reader needs to
				 * know it is a macro and what its parameters are, and
				 * the body is where the shift lives. */
				sp = strrchr(val, ')');
				if (sp)
					*sp = '\0';
				for (r = val; *r; r++)
					if (*r == '(' || *r == ')')
						*r = ' ';
				squeeze(val);
			} else {
				squeeze(val);
			}

			found++;
			if (found <= (unsigned)max) {
				/* Bare basename, kept in a full-size buffer. Two files
				 * with the same basename in different subtrees
				 * are reported with the same name; the search
				 * reports the directory separately below so a
				 * reader can tell which one it got. */
				const char *base = strrchr(path, '/');

				snprintf(defs[found - 1].file,
					 sizeof defs[found - 1].file, "%s",
					 base ? base + 1 : path);
				defs[found - 1].line = lineno;
				defs[found - 1].funclike = funclike;
				snprintf(defs[found - 1].value,
					 sizeof defs[found - 1].value, "%s",
					 val);
			}
		}
		fclose(f);
	}
	closedir(d);
	return found;
}

static unsigned find_defs(const char *dir, const char *sym, struct def *defs,
			 int max)
{
	return find_defs_r(dir, sym, defs, max, 0);
}

/*
 * Search several roots, accumulating.
 *
 * There are two and they are not nested. The packet macros (vid.h, sid.h,
 * vega10_sdma_pkt_open.h) are in amdgpu/. The register macros (mmVM_*,
 * mmATC_*) are in amd/include/asic_reg/, a sibling subtree. A citation of one
 * kind cannot be checked from the root of the other, which is why --dir can be
 * repeated and why the earlier single-root version answered "0 definitions"
 * about a macro that exists.
 *
 * The roots are visited in the order given and the totals add up, so a
 * multi-root search can still be truncated and still has to say so.
 */
static unsigned find_defs_multi(char roots[][MAXPATH], int nroots,
				const char *sym, struct def *defs, int max)
{
	unsigned total = 0;
	int r;

	for (r = 0; r < nroots; r++) {
		struct def local[MAXDEFS];
		unsigned n = find_defs(roots[r], sym, local, MAXDEFS);
		unsigned i;

		for (i = 0; i < n && total < (unsigned)max; i++) {
			/* Both buffers are the same size, so a bounded copy is
			 * exact rather than truncating. The compiler flags an
			 * unbounded %s into a same-sized array, and it is right
			 * to: same size is not a reason to stop checking. */
			memcpy(defs[total].file, local[i].file,
			       sizeof defs[total].file);
			defs[total].line = local[i].line;
			defs[total].funclike = local[i].funclike;
			memcpy(defs[total].value, local[i].value,
			       sizeof defs[total].value);
			total++;
		}
		total += n - i;	/* count what we could not store */
	}
	return total;
}

/* The #include lines of one .c file, as bare header names. */
static unsigned find_includes(const char *dir, const char *src,
			      struct inc *incs, int max)
{
	char path[MAXPATH];
	char line[MAXLINE];
	FILE *f;
	unsigned found = 0;
	int lineno = 0;

	snprintf(path, sizeof path, "%s/%s", dir, src);
	f = fopen(path, "r");
	if (!f) {
		out("rx550ref: cannot open %s\n", path);
		return 0;
	}

	while (fgets(line, sizeof line, f)) {
		char *p = line;
		char *q;

		lineno++;
		while (*p == ' ' || *p == '\t')
			p++;
		if (*p != '#')
			continue;
		p++;
		while (*p == ' ' || *p == '\t')
			p++;
		if (strncmp(p, "include", 7) != 0)
			continue;
		p += 7;
		if (is_ident_char((unsigned char)*p))
			continue;
		while (*p == ' ' || *p == '\t')
			p++;
		if (*p != '"')
			continue;	/* <...> is a system header */
		p++;
		q = p;
		while (*q && *q != '"')
			q++;
		*q = '\0';

		found++;
		if (found <= (unsigned)max) {
			snprintf(incs[found - 1].file,
				 sizeof incs[found - 1].file, "%s", p);
			snprintf(incs[found - 1].line,
				 sizeof incs[found - 1].line, "%d", lineno);
		}
	}
	fclose(f);
	return found;
}

/*
 * Is `hdr` among the includes, comparing basenames?
 *
 * The path prefix matters and the naive comparison missed it. gfx_v8_0.c has
 *
 *     #include "gmc/gmc_8_1_d.h"
 *
 * and the register is called gmc_8_1_d.h. A strcmp of the whole include line
 * against the definition's filename fails, the tool reports the symbol as
 * unreachable, and the reader concludes amdgpu cannot see its own registers.
 *
 * Comparing basenames is right here and slightly too permissive: a header named
 * gmc_8_1_d.h reached through a different directory would count as the same one.
 * In this corpus the basenames are unique across the two roots, and the search
 * reports the root, so a collision would be visible rather than silent. That is
 * the limitation, stated instead of hidden.
 */
static bool includes_file(const struct inc *incs, unsigned n, const char *hdr)
{
	const char *want = strrchr(hdr, '/');
	unsigned i;

	want = want ? want + 1 : hdr;
	for (i = 0; i < n; i++) {
		const char *got = strrchr(incs[i].file, '/');

		got = got ? got + 1 : incs[i].file;
		if (strcmp(got, want) == 0)
			return true;
	}
	return false;
}

static int cmp_str(const void *a, const void *b)
{
	return strcmp((const char *)a, (const char *)b);
}

/* ---------------------------------------------------------------- the work */

static int mode_sym(char roots[][MAXPATH], int nroots, const char *sym,
		    const char *consumer, unsigned max)
{
	struct def defs[MAXDEFS];
	struct inc incs[MAXINC];
	unsigned ndefs, nincs, i;
	unsigned shown;
	const char *first_value;

	printf("=== rx550ref: symbol %s ===\n", sym);

	ndefs = find_defs_multi(roots, nroots, sym, defs, MAXDEFS);
	g_found = ndefs;
	printf("    %u definition(s) across %d root(s)\n", ndefs, nroots);

	if (!ndefs) {
		fail("no #define of %s in any header. Either the name is wrong or it "
		     "is not a macro; both are worth knowing before citing it", sym);
		return 1;
	}

	shown = ndefs < max ? ndefs : max;
	g_shown = shown;
	g_truncated = shown < ndefs;
	if (g_truncated)
		printf("    TRUNCATED: showing %u of %u\n", shown, ndefs);

	for (i = 0; i < shown; i++)
		printf("    %-22s:%-5d %-10s %s\n", defs[i].file, defs[i].line,
		       defs[i].funclike ? "function" : "value",
		       defs[i].value);

	/* A disagreement only exists between definitions of the same kind. A value
	 * and a signature are not two answers to the same question. */
	{
		unsigned nval = 0, nfun = 0;

		for (i = 0; i < shown; i++) {
			if (defs[i].funclike)
				nfun++;
			else
				nval++;
		}
		printf("    %u value, %u function-like\n", nval, nfun);
	}

	/* Do they agree? One definition that differs is a trap, not a detail: it
	 * means the name is ambiguous across ASIC generations and a citation
	 * without the header is not a citation. */
	first_value = defs[0].value;
	{
		unsigned ntext = 0;	/* pairs compared as text, not as numbers */
		unsigned ndiff = 0;

		for (i = 1; i < ndefs; i++) {
			enum cmp_result c;

			if (i >= max)
				break;	/* only compare what was printed */
			if (defs[i].funclike != defs[0].funclike)
				continue;
			c = compare_values(defs[i].value, first_value);
			if (c == CMP_SAME)
				continue;
			if (c == CMP_TEXT_ONLY) {
				ntext++;
				continue;
			}
			ndiff++;
			fail("%s is defined differently: %s:%d says \"%s\", "
			     "%s:%d says \"%s\"",
			     sym, defs[0].file, defs[0].line, defs[0].value,
			     defs[i].file, defs[i].line, defs[i].value);
		}
		if (ntext)
			warn("%u pair(s) of %s compared as text, not as numbers: "
			     "the value contains an operator, so \"agree\" here "
			     "means the headers write it the same way. Read them.",
			     ntext, sym);
		if (g_errors == 0)
			pass("all definitions agree: %s%s", first_value,
			     ntext ? " (modulo the text-compared pairs above)" : "");
		(void)ndiff;
	}

	if (!consumer)
		return 0;

	/* The question that caught all three of my errors: does the consumer file
	 * actually include the header the value came from? */
	nincs = 0;
	{
		int r;

		for (r = 0; r < nroots && !nincs; r++)
			nincs = find_includes(roots[r], consumer, incs, MAXINC);
	}
	if (!nincs) {
		fail("cannot read includes of %s in any of the %d root(s)",
		     consumer, nroots);
		return 1;
	}
	printf("    %u include(s) in %s\n", nincs, consumer);
	if (nincs > MAXINC) {
		printf("    TRUNCATED: %u includes, showing %u\n", nincs, MAXINC);
		warn("%s has %u includes and the list was capped at %u",
		     consumer, nincs, MAXINC);
	}

	/* Sort the printed list so a reader can scan it, and so the two lists are
	 * comparable. */
	qsort(incs, nincs, sizeof incs[0], cmp_str);

	{
		unsigned shown_inc = nincs < 12 ? nincs : 12;

		for (i = 0; i < shown_inc; i++)
			printf("      . %s\n", incs[i].file);
		if (shown_inc < nincs)
			printf("      . ... and %u more\n", nincs - shown_inc);
	}

	/* Every header that defines the symbol, checked against the consumer. */
	{
		unsigned matching = 0;
		bool any_ambiguous = false;

		for (i = 0; i < shown; i++) {
			if (includes_file(incs, nincs, defs[i].file)) {
				matching++;
				continue;
			}
			if (!defs[i].funclike &&
			    compare_values(defs[i].value, defs[0].value) ==
			    CMP_DIFFERENT) {
				any_ambiguous = true;
				warn("%s:%d defines %s as \"%s\" but %s does not "
				     "include it, and it differs from %s:%d",
				     defs[i].file, defs[i].line, sym, defs[i].value,
				     consumer, defs[0].file, defs[0].line);
			}
		}

		if (!matching) {
			fail("%s includes NONE of the %u header(s) that define %s. "
			     "The citation is not reachable from the code.",
			     consumer, shown, sym);
		} else if (matching > 1) {
			pass("%s includes %u of the %u defining header(s)",
			     consumer, matching, shown);
			if (any_ambiguous)
				warn("more than one defining header is included and "
				     "they did not all agree");
		} else {
			pass("%s includes exactly %s, which is the only one of the "
			     "%u it reaches", consumer, defs[0].file, shown);
		}
	}

	return g_errors ? 1 : 0;
}

static int mode_includes(const char *dir, const char *src)
{
	struct inc incs[MAXINC];
	unsigned n, i;

	printf("=== rx550ref: includes of %s ===\n", src);
	n = find_includes(dir, src, incs, MAXINC);
	g_found = n;
	printf("    %u include(s)\n", n);
	if (!n) {
		fail("no #include \"...\" lines found in %s", src);
		return 1;
	}
	if (n > MAXINC) {
		g_truncated = true;
		printf("    TRUNCATED: showing %u of %u\n", MAXINC, n);
	}
	qsort(incs, n < MAXINC ? n : MAXINC, sizeof incs[0], cmp_str);
	for (i = 0; i < n && i < MAXINC; i++)
		printf("    %-28s line %s\n", incs[i].file, incs[i].line);
	return 0;
}

/*
 * Is "FILE:NUMBER" a real citation? A line number is a claim about a fact, and a
 * fact that moved between kernel versions is exactly the kind that silently
 * becomes false. This asks whether the line exists and whether it contains the
 * symbol.
 */
static int mode_check(const char *dir, const char *file, int line,
		      const char *sym)
{
	char path[MAXPATH];
	char buf[MAXLINE];
	FILE *f;
	int lineno = 0;
	bool saw = false;
	int printed = 0;

	printf("=== rx550ref: check %s:%d for %s ===\n", file, line,
	       sym ? sym : "anything");
	snprintf(path, sizeof path, "%s/%s", dir, file);
	f = fopen(path, "r");
	if (!f) {
		fail("cannot open %s", path);
		return 1;
	}
	while (fgets(buf, sizeof buf, f)) {
		lineno++;
		if (lineno < line - 2)
			continue;
		if (lineno > line + 2)
			break;
		printed++;
		if (lineno == line) {
			saw = true;
			printf("    %5d | %s", lineno, buf);
			if (sym && !strstr(buf, sym))
				fail("line %d of %s does not mention %s. The line "
				     "exists but does not say what the citation "
				     "claims.", line, file, sym);
		} else {
			printf("    %5d | %s", lineno, buf);
		}
	}
	fclose(f);

	if (!printed) {
		fail("%s has %d lines, so :%d is past the end. The citation is to a "
		     "line that does not exist in this corpus version.", file,
		     lineno, line);
		return 1;
	}
	if (!saw) {
		fail("never reached line %d in %s", line, file);
		return 1;
	}
	pass("line %d of %s exists and mentions %s", line, file,
	     sym ? sym : "its target");
	return 0;
}

/*
 * --decl FILE:LINE:VALUE -- does that corpus line define the value I claim?
 *
 * The shell version of this check compared identifiers, and it was wrong: my
 * macro is RX550_MM_VM_CONTEXT0_PTBA and the corpus name is
 * mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR, so every register citation came back
 * "SAYS ELSEWHERE" while the citation was perfectly correct. Twenty false
 * positives on a check I had just written is the same failure as the one this
 * tool exists to catch: a check that is not right being worse than no check,
 * because the reader learns to skip it.
 *
 * The robust comparison is the VALUE, not the name. My header writes the value
 * and the citation; the corpus line writes its own value. If the two values are
 * the same number, the citation says what it claims regardless of what the two
 * projects chose to call the macro. That also survives a value being re-spelled
 * (0x43 vs 0x043) and a name being changed upstream, neither of which invalidates
 * a citation.
 *
 * What it does NOT check is that the value is the right one for this ASIC, or
 * that the corpus line defines a symbol of the same family. Those are reading
 * jobs. This is a mechanical consistency check and says so.
 */
static int mode_decl(const char *dir, const char *file, int line,
		     const char *value)
{
	char path[MAXPATH];
	char buf[MAXLINE];
	FILE *f;
	int lineno = 0;
	bool saw = false;
	char *got = NULL;

	printf("=== rx550ref: decl check %s:%d claims value %s ===\n", file, line,
	       value);
	snprintf(path, sizeof path, "%s/%s", dir, file);
	f = fopen(path, "r");
	if (!f) {
		fail("cannot open %s", path);
		return 1;
	}
	while (fgets(buf, sizeof buf, f)) {
		char *eol;

		lineno++;
		if (lineno < line)
			continue;
		if (lineno > line)
			break;
		saw = true;
		eol = strpbrk(buf, "\n");
		if (eol)
			*eol = '\0';
		/*
		 * A #define is NAME and then VALUE. The value is what has to be
		 * compared, and taking everything after "#define" includes the
		 * name, so "PACKET3_SURFACE_SYNC  0x43" is never equal to "0x43"
		 * and every check would come back "compared as text". That was
		 * this function's first version and the self-test caught it.
		 *
		 * Split at the first run of whitespace that follows an identifier.
		 * For a function-like macro there is no value, and that is reported
		 * rather than guessed: "(x)" alone is not a constant.
		 */
		got = strstr(buf, "#define");
		if (got) {
			got = trim(got + 7);
			if (*got == '(') {
				/* function-like: skip the parameter list */
				char *close = strchr(got, ')');

				if (close)
					got = trim(close + 1);
			} else {
				while (*got && !isspace((unsigned char)*got))
					got++;
				got = trim(got);
			}
		} else {
			got = trim(buf);
		}
		break;
	}
	fclose(f);

	if (!saw) {
		fail("%s has %d lines, so :%d is past the end", file, lineno, line);
		return 1;
	}
	printf("    corpus line: %s\n", got ? got : "(empty)");
	printf("    claimed:     %s\n", value);

	if (!got) {
		fail("line %d of %s has no #define", line, file);
		return 1;
	}

	{
		enum cmp_result c = compare_values(value, got);

		if (c == CMP_SAME) {
			pass("the value matches");
			return 0;
		}
		if (c == CMP_TEXT_ONLY) {
			/* An expression: "(1u << 20)" against "(1 << 20)". Same
			 * number, different spelling, and text comparison cannot see
			 * it. Reported as unresolved rather than as a failure,
			 * because claiming a mismatch here would be a guess. */
			warn("compared as text, not as numbers: \"%s\" vs \"%s\". "
			     "Same spelling required to call it a match. Read it.",
			     value, got);
			return 1;
		}
	}

	fail("the value does not match: I claim %s, the corpus says %s", value, got);
	return 1;
}

/* -------------------------------------------------------------- self test */

/* A miniature corpus, so the self-test does not depend on the real tree being
 * present or unchanged. If it did, a corpus re-extract would turn this into a
 * false failure and the lesson would be lost. */
static int selftest(void)
{
	static const char g_dir[] = "/tmp/rx550ref_selftest";
	char path[MAXPATH];
	FILE *f;
	int bad = 0;

	printf("=== rx550ref selftest ===\n");
	printf("    fixture: %s\n\n", g_dir);

	mkdir(g_dir, 0755);

	snprintf(path, sizeof path, "%s/vid.h", g_dir);
	f = fopen(path, "w");
	if (!f) {
		fail("cannot create the fixture; the self-test is not runnable here");
		return 1;
	}
	/* Three headers, one value disagreement, and tab alignment, so the
	 * squeeze path and the disagreement path are both exercised. */
	fprintf(f, "#ifndef VID_H\n#define VID_H\n");
	fprintf(f, "#define\tWAIT_REG_MEM_FUNCTION(x)                ((x) << 0)\n");
	fprintf(f, "#define\tRX550_SURFACE_SYNC                       0x43\n");
	fprintf(f, "#define\tPACKET3_WRITE_DATA\t\t\t\t0x37\n");
	fprintf(f, "#define\tPACKET3_NOP(x)\t\t\t\tPACKET3_NOP_SH(x)\n");
	fprintf(f, "#endif\n");
	fclose(f);

	snprintf(path, sizeof path, "%s/sid.h", g_dir);
	f = fopen(path, "w");
	fprintf(f, "#define\tPACKET3_WRITE_DATA\t\t\t\t0x37\n");
	fprintf(f, "#define\tWAIT_REG_MEM_MEM_SPACE(x)\t\t\t((x) << 4)\n");
	fclose(f);

	snprintf(path, sizeof path, "%s/other.h", g_dir);
	f = fopen(path, "w");
	fprintf(f, "#define\tPACKET3_WRITE_DATA\t\t\t\t0x40\n");
	fclose(f);

	/* The consumer includes vid.h only. So it reaches PACKET3_WRITE_DATA's
	 * agreeing definitions, and NOT the one in other.h. */
	snprintf(path, sizeof path, "%s/gfx_v8_0.c", g_dir);
	f = fopen(path, "w");
	fprintf(f, "#include \"vi.h\"\n");
	fprintf(f, "#include \"vi_structs.h\"\n");
	fprintf(f, "#include \"vid.h\"\n");
	fprintf(f, "#include <linux/delay.h>\n");
	fprintf(f, "int x;\n");
	fclose(f);

	char roots_g[1][MAXPATH];
	int rc;

	snprintf(roots_g[0], sizeof roots_g[0], "%s", g_dir);

	/* --- 1. a symbol with a disagreement the consumer is insulated from --- */
	printf("[1] PACKET3_WRITE_DATA, 3 headers, one disagrees, consumer sees vid.h\n");
	g_errors = g_warnings = g_checks = 0;
	rc = mode_sym(roots_g, 1, "PACKET3_WRITE_DATA", "gfx_v8_0.c", 32);
	if (rc == 0)
		bad++;
	/* Two separate things must have been reported: the disagreement, and the
	 * fact that the disagreeing header is not one the consumer includes. */
	if (g_warnings == 0)
		bad++;
	printf("    verdict: %s (exit %d, %d error, %d warn -- the disagreement "
	       "must be BOTH an error and a warn about reachability)\n\n",
	       (rc != 0 && g_warnings > 0) ? "PASS" : "FAIL", rc, g_errors,
	       g_warnings);

	/* --- 2. the clean case the tool must NOT cry wolf on --- */
	printf("[2] RX550_SURFACE_SYNC: one header, consumer includes it, no "
	       "disagreement. Must be a clean pass.\n");
	{
		/* before is unused here: the vector asserts an error by design */

		g_errors = g_warnings = g_checks = 0;
		rc = mode_sym(roots_g, 1, "RX550_SURFACE_SYNC", "gfx_v8_0.c", 32);
		if (rc != 0)
			bad++;
		if (g_warnings != 0)
			bad++;
		printf("    verdict: %s (exit %d, %d error, %d warn)\n\n",
		       (rc == 0 && g_warnings == 0) ? "PASS" : "FAIL", rc,
		       g_errors, g_warnings);
	}

	/* --- 3. a symbol the consumer cannot reach --- */
	printf("[3] WAIT_REG_MEM_MEM_SPACE, defined in sid.h which is not included\n");
	{
		int bad_start3 = bad;

		g_errors = g_warnings = g_checks = 0;
		if (mode_sym(roots_g, 1, "WAIT_REG_MEM_MEM_SPACE", "gfx_v8_0.c", 32) == 0)
			bad++;
		printf("    verdict: %s (unreachable citation is an error)\n\n",
		       bad == bad_start3 ? "PASS" : "FAIL");
	}

	/* --- 3b. a function-like macro whose name collides with a real value --- */
	printf("[3b] a function-like macro is FOUND and labelled 'function', "
	       "not 'value'\n");
	{
		struct def defs[MAXDEFS];
		unsigned n = find_defs(g_dir, "WAIT_REG_MEM_FUNCTION", defs,
				       MAXDEFS);
		int before = bad;

		/* vid.h has WAIT_REG_MEM_FUNCTION(x) = ((x) << 0). The tool used to
		 * skip these entirely, which meant --sym answered "0 definitions"
		 * about half the fields in the packet headers. It must now find it
		 * AND say it is function-like, because a reader who cites a shift
		 * as if it were a constant is making exactly the mistake 038 was. */
		if (n == 0)
			bad++;
		else if (!defs[0].funclike)
			bad++;
		printf("    found %u, funclike=%d -- verdict: %s\n\n", n,
		       n ? defs[0].funclike : -1, (bad == before) ? "PASS" : "FAIL");
	}

	/* --- 3c. two spellings of the same number must NOT be a disagreement --- */
	printf("[3c] 0x51e vs 0x051E: same number, different spelling\n");
	{
		struct def a[1], b[1];
		int before = bad;

		/* gmc_6_0_d.h writes 0x051E and gmc_8_1_d.h writes 0x51e for the
		 * same register offset. Text comparison calls that a disagreement
		 * and the reader learns to ignore disagreements. It is the same
		 * number. */
		snprintf(a[0].value, sizeof a[0].value, "0x51e");
		snprintf(b[0].value, sizeof b[0].value, "0x051E");
		if (compare_values(a[0].value, b[0].value) != CMP_SAME)
			bad++;
		snprintf(b[0].value, sizeof b[0].value, "0x52f");
		if (compare_values(a[0].value, b[0].value) != CMP_DIFFERENT)
			bad++;
		snprintf(b[0].value, sizeof b[0].value, "(1u << 20)");
		if (compare_values("(1 << 20)", b[0].value) != CMP_TEXT_ONLY)
			bad++;
		printf("    verdict: %s\n\n", (bad == before) ? "PASS" : "FAIL");
	}

	/* --- 4. a forwarding function-like macro --- */
	printf("[4] PACKET3_NOP is a function-like macro that forwards to another: "
	       "its captured value must not claim to be an opcode\n");
	{
		struct def defs[MAXDEFS];
		unsigned n = find_defs(g_dir, "PACKET3_NOP", defs, MAXDEFS);
		int before = bad;

		/* vid.h: PACKET3_NOP(x) PACKET3_NOP_SH(x) -- a forwarding macro. The
		 * tool reports it, and the report must show the signature so nobody
		 * reads it as the numeric opcode it forwards to. */
		if (n != 1)
			bad++;
		else if (!defs[0].funclike)
			bad++;
		else if (strstr(defs[0].value, "x") == NULL)
			bad++;
		printf("    found %u as '%s' -- verdict: %s\n\n", n,
		       n ? defs[0].value : "(none)", (bad == before) ? "PASS" : "FAIL");
	}

	/* --- 5. truncation must be declared, never silent --- */
	printf("[5] max=1 with 3 definitions must declare TRUNCATED\n");
	{
		int before = bad;
		struct def defs[MAXDEFS];
		unsigned n = find_defs(g_dir, "PACKET3_WRITE_DATA", defs, MAXDEFS);

		g_errors = g_warnings = g_checks = 0;
		g_truncated = false;
		/* The count is the return value, not the array length. If these
		 * ever converge, the tool would be able to hide a match. */
		if (n != 3)
			bad++;
		if (n <= 1)
			bad++;
		printf("    found %u (expect 3), so max=1 would truncate: %s\n\n", n,
		       (bad == before) ? "PASS" : "FAIL");
	}

	/* --- 6. an out-of-range citation --- */
	printf("[6] a citation to a line past the end of the file must FAIL\n");
	{
		int before = bad;

		g_errors = g_warnings = g_checks = 0;
		if (mode_check(g_dir, "gfx_v8_0.c", 9999, "vid.h") == 0)
			bad++;
		printf("    verdict: %s\n\n", (bad == before) ? "PASS" : "FAIL");
	}

	/* --- 7. a real citation --- */
	printf("[7] gfx_v8_0.c:3 does mention vid.h\n");
	{
		int before = bad;

		g_errors = g_warnings = g_checks = 0;
		if (mode_check(g_dir, "gfx_v8_0.c", 3, "vid.h") != 0)
			bad++;
		printf("    verdict: %s\n\n", (bad == before) ? "PASS" : "FAIL");
	}

	/* --- 8. an unknown symbol --- */
	printf("[8] a symbol nobody defines must FAIL, not return empty\n");
	{
		int before = bad;

		g_errors = g_warnings = g_checks = 0;
		if (mode_sym(roots_g, 1, "RX550_NO_SUCH_SYMBOL", NULL, 32) == 0)
			bad++;
		printf("    verdict: %s\n\n", (bad == before) ? "PASS" : "FAIL");
	}

	/* --- 10. --decl on a value that matches, and on one that does not --- */
	printf("[10] --decl: matching value, and a value that differs\n");
	{
		int before = bad;

		g_errors = g_warnings = g_checks = 0;
		if (mode_decl(g_dir, "vid.h", 4, "0x43") != 0)
			bad++;
		g_errors = g_warnings = g_checks = 0;
		/* A different number on the same line must be a failure. */
		if (mode_decl(g_dir, "vid.h", 4, "0x99") == 0)
			bad++;
		printf("    verdict: %s\n\n", (bad == before) ? "PASS" : "FAIL");
	}

	printf("=== selftest: %u of 11 vectors behaved as specified ===\n", 11 - bad);
	if (bad) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	return 0;
}

/* ------------------------------------------------------------------- main */

int main(int argc, char **argv)
{
	char roots[MAXROOTS][MAXPATH];
	int nroots = 0;
	const char *sym = NULL;
	const char *consumer = NULL;
	const char *file = NULL;
	const char *declval = NULL;
	int line = 0;
	unsigned max = 32;
	int i, rc = 0;

	for (i = 1; i < argc; i++) {
		if (strcmp(argv[i], "--selftest") == 0)
			return selftest();
		if (strcmp(argv[i], "--dir") == 0 && i + 1 < argc) {
			if (nroots < MAXROOTS) {
				snprintf(roots[nroots], sizeof roots[nroots],
					 "%s", argv[++i]);
				nroots++;
			} else {
				out("rx550ref: at most %d roots\n", MAXROOTS);
				return 2;
			}
			continue;
		}
		if (strcmp(argv[i], "--sym") == 0 && i + 1 < argc) {
			sym = argv[++i];
			continue;
		}
		if (strcmp(argv[i], "--in") == 0 && i + 1 < argc) {
			consumer = argv[++i];
			continue;
		}
		if (strcmp(argv[i], "--includes") == 0 && i + 1 < argc) {
			file = argv[++i];
			continue;
		}
		if (strcmp(argv[i], "--decl") == 0 && i + 2 < argc) {
			/* Split FIRST, then parse the number. atoi() on the whole
			 * "file.h:1" yields 0, because the number is at the end and
			 * atoi stops at the first non-digit. That made every --decl
			 * check report "line 0 is past the end" and the shell driver
			 * counted it as a value mismatch, on citations that were
			 * correct. */
			char *arg = argv[++i];
			char *colon = strrchr(arg, ':');

			if (!colon) {
				out("rx550ref: --decl wants FILE.h:NUMBER\n");
				return 2;
			}
			*colon = '\0';
			file = arg;
			line = atoi(colon + 1);
			declval = argv[++i];
			continue;
		}
		if (strcmp(argv[i], "--check") == 0 && i + 1 < argc) {
			char *arg = argv[++i];
			char *colon = strrchr(arg, ':');

			if (!colon) {
				out("rx550ref: --check wants FILE:NUMBER\n");
				return 2;
			}
			*colon = '\0';
			file = arg;
			line = atoi(colon + 1);
			/* No symbol given: the line must merely exist. */
			sym = NULL;
			continue;
		}
		if (strcmp(argv[i], "--max") == 0 && i + 1 < argc) {
			max = (unsigned)atoi(argv[++i]);
			continue;
		}
		if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
			printf("usage:\n"
			       "  rx550ref --dir D [--dir D2 ...] --sym NAME [--in FILE] [--max N]\n"
			       "      where is NAME defined, do the definitions agree,\n"
			       "      and does FILE actually include the winner\n"
			       "  rx550ref --dir D --includes FILE.c\n"
			       "  rx550ref --dir D --check FILE.c:NUMBER [--sym TEXT]\n"
			       "      is that citation a real line, and does it say it\n"
			       "  rx550ref --dir D --decl FILE.h:NUMBER VALUE\n"
			       "      does that corpus line carry the value I claim\n"
			       "  rx550ref --selftest\n");
			return 0;
		}
	}

	if (!nroots) {
		out("rx550ref: --dir is required, and may be given more than once\n");
		return 2;
	}
	if (declval) {
		int r;

		rc = 2;
		for (r = 0; r < nroots; r++) {
			if (mode_decl(roots[r], file, line, declval) == 0) {
				rc = 0;
				break;
			}
			g_errors = 0;
			g_warnings = 0;
		}
	} else if (file && line) {
		int r;

		rc = 2;
		for (r = 0; r < nroots; r++) {
			if (mode_check(roots[r], file, line, sym) == 0) {
				rc = 0;
				break;
			}
			g_errors = 0;
		}
	} else if (file) {
		int r;

		rc = 2;
		for (r = 0; r < nroots; r++) {
			if (mode_includes(roots[r], file) == 0) {
				rc = 0;
				break;
			}
		}
	} else if (sym) {
		rc = mode_sym(roots, nroots, sym, consumer, max);
	} else {
		out("rx550ref: nothing to do\n");
		return 2;
	}

	if (g_truncated)
		printf("(note: a list above was TRUNCATED. A truncated list does "
		       "not support an absence claim.)\n");
	return rc;
}
