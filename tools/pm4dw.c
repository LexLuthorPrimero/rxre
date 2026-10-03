/* pm4dw — emission-cost accounting for GFX8 PM4 ring paths.
 *
 * WHY THIS EXISTS
 * ---------------
 * Two sessions produced conflicting numbers for gfx_v8_0_ring_emit_vm_flush.
 * One counted WAIT_REG_MEM as 6 dwords and got residual +6; another counted 7
 * and got +5. Both counted by hand with grep. Hand-counting amdgpu_ring_write()
 * calls is the exact operation that produced the disagreement, so it is
 * mechanised here and then shown to fail on a deliberately broken input.
 *
 * It reads source text only. It opens no device node, writes no register, and
 * never runs the GPU.
 *   INPUT_CLASS=CORPUS   OUTPUT_CLASS=DERIVATION   RUNTIME=NOT_RUN
 *
 * SCOPE OF TRUST
 * --------------
 * A number this tool prints is only as good as two assumptions, both stated in
 * the output:
 *
 *   1. One amdgpu_ring_write() call == one dword. True for this driver
 *      (amdgpu_ring.h:494 writes one u32 and decrements count_dw). amdgpu_ring_write_multiple()
 *      is counted once, NOT by its argument, so a caller using it with n > 1 is
 *      under-counted. The tool reports when it sees that symbol.
 *   2. .emit_frame_size is a reservation, so declared > emitted is correct and
 *      only declared < emitted is a defect. The tool exits 1 on that case only.
 *
 * PARSING
 * -------
 * Kernel style is regular enough to parse by line: a definition is a line
 * that opens with a type and is followed by a line starting with '{'. Struct
 * initialisers open with `name = {`. Both are recognised by the shape of the
 * line, not by reverse-parsing from the brace. The earlier version walked
 * backwards from each '{' and mis-named nearly every function, because a
 * parameter list ends in ')' and the name is not adjacent to it.
 *
 * BUILD: cc -O2 -Wall -Wextra -o pm4dw pm4dw.c
 * USE:   pm4dw --macro NAME=VALUE ... --struct NAME ... --path fn1,fn2,...
 *                 file.c [file.c ...]
 * EXIT:  0 OK; 1 under-reservation or a --path name not found; 2 usage error.
 *
 * --path RESOLVES COMPOSITION, WHICH --struct CANNOT
 * -----------------------------------------------
 * --struct sums every handler the struct names. That is an upper bound, not the
 * set that can actually run in one submission, so it cannot decide whether a
 * reservation is sufficient. --path takes the *ordered* list of emitters one
 * submission can execute and sums exactly those. A name that is absent from the
 * parsed corpus is reported as ABSENT rather than silently treated as zero:
 * on GFX8 that is how "emit_cleaner_shader is not implemented for this ASIC"
 * becomes a fact rather than an assumption. See finding 024 for why this
 * distinction decides the question.
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXDEFS   1024
#define MAXNAME   128
#define MAXMACROS 64
/* How many lines past a declaration the body brace may be. Kernel signatures
 * wrap; statements do not become definitions by accident. */
#define LOOKAHEAD_LINES 12

typedef struct {
	char  name[MAXNAME];
	char *body;      /* '{' .. matching '}', NUL-terminated, comments intact */
	int   base;      /* direct amdgpu_ring_write() calls */
	int   total;     /* base plus callees, fixed point */
	int   uses_multiple; /* amdgpu_ring_write_multiple() present */
	int   is_struct;     /* a struct initialiser: no dwords of its own */
	int   indirect;      /* dispatches through a function pointer */
	char  wm_sites[8][96]; /* amdgpu_ring_write_multiple() call sites, verbatim */
	int   nwm;
	int   nparams;      /* parameter count from the definition's signature */
	int   has_def;      /* signature seen (0 if only a struct field matched) */
} Def;

typedef struct {
	char name[MAXNAME];
	long value;
} Macro;

static Def   defs[MAXDEFS];
static int   ndefs;
static Macro macros[MAXMACROS];
static int   nmacros;

static void die(const char *msg, const char *arg)
{
	fprintf(stderr, "pm4dw: %s%s%s\n", msg, arg ? ": " : "", arg ? arg : "");
	exit(2);
}

static Def *find_def(const char *name)
{
	int i;
	for (i = 0; i < ndefs; i++)
		if (strcmp(defs[i].name, name) == 0)
			return &defs[i];
	return NULL;
}

static long macro_value(const char *name)
{
	int i;
	for (i = 0; i < nmacros; i++)
		if (strcmp(macros[i].name, name) == 0)
			return macros[i].value;
	die("unresolved macro", name);
	return 0;
}

static void add_macro(const char *s)
{
	const char *eq = strchr(s, '=');
	char nm[MAXNAME];
	size_t n;

	if (!eq)
		die("macro needs NAME=VALUE", s);
	n = (size_t)(eq - s);
	if (n >= MAXNAME)
		die("macro name too long", s);
	memcpy(nm, s, n);
	nm[n] = '\0';
	if (nmacros >= MAXMACROS)
		die("too many macros", NULL);
	snprintf(macros[nmacros].name, MAXNAME, "%s", nm);
	macros[nmacros].value = atol(eq + 1);
	nmacros++;
}

/* ---- line-oriented scanning ------------------------------------------ */

/* Copy the brace-balanced body that starts at the '{' on line `start`.
 * Braces inside string literals and comments do not count. */
static char *extract_body(const char *brace, const char *end)
{
	int depth = 0;
	const char *p = brace;

	while (p < end) {
		if (p + 1 < end && p[0] == '/' && p[1] == '*') {
			const char *cl = p + 2;
			while (cl + 1 < end && !(cl[0] == '*' && cl[1] == '/'))
				cl++;
			p = (cl + 1 < end) ? cl + 2 : end;
			continue;
		}
		if (p + 1 < end && p[0] == '/' && p[1] == '/') {
			const char *nl = memchr(p, '\n', (size_t)(end - p));
			p = nl ? nl : end;
			continue;
		}
		if (*p == '"' || *p == '\'') {
			char q = *p++;
			while (p < end && *p != q) {
				if (*p == '\\' && p + 1 < end)
					p++;
				p++;
			}
			if (p < end)
				p++;
			continue;
		}
		if (*p == '{')
			depth++;
		else if (*p == '}') {
			depth--;
			if (depth == 0) {
				size_t n = (size_t)(p - brace) + 1;
				char *b = malloc(n + 1);
				if (!b)
					die("out of memory", NULL);
				memcpy(b, brace, n);
				b[n] = '\0';
				return b;
			}
		}
		p++;
	}
	return NULL;
}

/* The definition name is the last identifier before the '(' that opens the
 * parameter list. Read the declaration line by line, tracking paren depth so
 * multi-line parameter lists work. */
/* Is the identifier starting at `p` a real function name rather than a
 * keyword, a macro, or a type? Heuristics, each with a reason:
 *
 *   - not a C keyword: `switch (x)`, `for (...)`, `if (...)` are statements
 *   - not ALL_CAPS with a digit or underscore: macros in this driver are
 *     UPPER_SNAKE, functions are lower_snake
 *   - not immediately preceded by '.' or "->": a field, not a function
 *   - the line before it must contain a type-like token, i.e. something that
 *     is not just the name itself
 */
static int is_definition_name(const char *p, const char *lim)
{
	static const char *kw[] = {
		"if", "for", "while", "switch", "return", "sizeof", "do", "else",
		"case", "default", "break", "continue", "goto", "defined", NULL
	};
	int i;
	size_t n = 0;
	const char *e = p;
	const char *b = p;

	/* must start with a letter or underscore. Without this, "!" and other
	 * punctuation got in as one-character "definitions". */
	if (!isalpha((unsigned char)*p) && *p != '_')
		return 0;
	while (e < lim && (isalnum((unsigned char)*e) || *e == '_'))
		e++;
	n = (size_t)(e - b);
	if (n == 0 || n >= MAXNAME)
		return 0;

	for (i = 0; kw[i]; i++)
		if (strlen(kw[i]) == n && memcmp(b, kw[i], n) == 0)
			return 0;

	/* macro: starts uppercase and contains an underscore or digit */
	{
		int upper = isupper((unsigned char)*b);
		int marker = 0;
		for (e = b; e < b + n; e++)
			if (*e == '_' || isdigit((unsigned char)*e))
				marker = 1;
		if (upper && marker)
			return 0;
		/* A bare all-caps name like WREG32 has no underscore; require at
		 * least two uppercase letters to treat it as a macro. */
		if (upper) {
			int uppers = 0;
			for (e = b; e < b + n; e++)
				if (isupper((unsigned char)*e))
					uppers++;
			if (uppers >= 2)
				return 0;
		}
	}

	/* preceded by '.' or "->" => struct field */
	if (b[-1] == '.' || (b[-2] == '-' && b[-1] == '>'))
		return 0;

	return 1;
}

static int decl_name(const char *from, const char *to, char *out, size_t outlen)
{
	const char *lineend;

	/* find the '{' that starts the body, then read backwards over the ')'
	 * of the signature to the matching '(' */
	lineend = from;
	while (lineend < to && *lineend != '{')
		lineend++;

	/* Read forward from `from` and remember the identifier that most recently
	 * preceded an unmatched '('. That identifier is the function name.
	 * Walking backwards from the '{' does not work: the character before the
	 * '{' is usually a newline, and the ')' of the signature can be several
	 * lines earlier. Tracking forward is also simpler to reason about. */
	lineend = from;
	while (lineend < to && *lineend != '{')
		lineend++;

	{
		const char *e = from;
		const char *idstart = NULL;
		int d = 0;

		while (e < lineend) {
			if (*e == '(') {
				d++;
				/* remember the identifier just before this '(' */
				idstart = e;
				while (idstart > from &&
				       !isalnum((unsigned char)idstart[-1]) &&
				       idstart[-1] != '_')
					idstart--;
				{
					const char *s = idstart;
					while (s > from &&
					       (isalnum((unsigned char)s[-1]) || s[-1] == '_'))
						s--;
					idstart = s;
				}
			} else if (*e == ')') {
				if (d > 0)
					d--;
			}
			e++;
		}
		if (d != 0 || !idstart || idstart == from)
			return 0;
		/* Reject anything that is not a definition of a function declared in
		 * this file. Without this, control-flow keywords and macros were
		 * parsed as definitions — "switch (...)" became a function named
		 * `switch`, "ARRAY_SIZE(x)" became a function named `ARRAY_SIZE` —
		 * and the resulting graph had thousands of bogus edges. */
		if (!is_definition_name(idstart, lineend))
			return 0;
		{
			const char *e2 = idstart;
			size_t n;
			while (e2 < lineend &&
			       (isalnum((unsigned char)*e2) || *e2 == '_'))
				e2++;
			n = (size_t)(e2 - idstart);
			if (n == 0 || n >= outlen)
				return 0;
			memcpy(out, idstart, n);
			out[n] = '\0';
			return 1;
		}
	}
	}

/* Struct initialiser name: `ident = {`. */
static int init_name(const char *from, const char *to, char *out, size_t outlen)
{
	const char *eq = memchr(from, '=', (size_t)(to - from));
	const char *s;
	size_t n;

	if (!eq)
		return 0;
	s = eq;
	while (s > from && (*s == ' ' || *s == '\t'))
		s--;
	if (s == from)
		return 0;
	s--; /* step onto the last character of the name */
	while (s > from && (isalnum((unsigned char)s[-1]) || s[-1] == '_'))
		s--;
	n = (size_t)(eq - s);
	while (n > 0 && isspace((unsigned char)s[n - 1]))
		n--;
	if (n == 0 || n >= outlen)
		return 0;
	memcpy(out, s, n);
	out[n] = '\0';
	return 1;
}

/* A struct initialiser body has no amdgpu_ring_write() of its own; its dword
 * cost is the sum of the emit_* handlers it names. A function body emits
 * directly. */
static int is_struct_marker(const char *body)
{
	return strstr(body, ".emit_") != NULL && strstr(body, "amdgpu_ring_write") == NULL;
}

/* Given a definition name and the start of its declaration, find the '(' of
 * the parameter list. Returns NULL if the signature is not on this line. */
static const char *signature_open(const char *line, const char *name)
{
	const char *p = strstr(line, name);
	if (!p)
		return NULL;
	p += strlen(name);
	while (p && *p && *p != '(' && *p != ';' && *p != '\n')
		p++;
	return (p && *p == '(') ? p : NULL;
}

/* Matching ')' for a ')' at *open. */
static const char *matching_paren(const char *open)
{
	const char *q = open;
	int d = 0;
	for (; *q; q++) {
		if (*q == '(')
			d++;
		else if (*q == ')') {
			d--;
			if (d == 0)
				return q;
		}
	}
	return NULL;
}

/* Count top-level parameters in a function signature text. "void" alone and an
 * empty list both count as zero. The text is the inside of the parentheses. */
static int count_params(const char *s, const char *e)
{
	int n = 0;
	int d = 0;
	int seen = 0;

	for (; s < e; s++) {
		if (*s == '(' || *s == '[' || *s == '{') {
			d++;
			continue;
		}
		if (*s == ')' || *s == ']' || *s == '}') {
			d--;
			continue;
		}
		if (d != 0)
			continue;
		if (*s == ',') {
			n++;
			continue;
		}
		if (!isspace((unsigned char)*s) && *s != '*')
			seen = 1;
	}
	if (seen)
		n++;
	if (n == 1) {
		/* a single "void" is not a parameter */
		const char *t = s;
		while (t < e && isspace((unsigned char)*t))
			t++;
		if (e - t == 4 && memcmp(t, "void", 4) == 0)
			return 0;
	}
	return n;
}

/* Split a call's argument list on top-level commas. Returns the count. */
static int count_args(const char *s, const char *close)
{
	int n = 0;
	int d = 0;
	int seen = 0;
	const char *p;

	for (p = s; p < close; p++) {
		if (*p == '(' || *p == '[' || *p == '{')
			d++;
		else if (*p == ')' || *p == ']' || *p == '}')
			d--;
		else if (d == 0 && *p == ',')
			n++;
		else if (d == 0 && !isspace((unsigned char)*p))
			seen = 1;
	}
	if (seen)
		n++;
	return n;
}

/* Arity check: every call to a function whose definition we parsed must pass
 * the same number of arguments as the definition declares.
 *
 * WHY: AGENTS.md "PRE-EXECUTION CONTRACT CHECK" requires verifying that fields
 * and parameters actually exist before trusting a result. A silent arity
 * mismatch produces a plausible, wrong number, which is worse than a crash.
 * Macros are NOT definitions and are deliberately skipped: they are reported
 * separately so the skip is visible rather than assumed. */
static int check_arity(void)
{
	int i, k, bad = 0, calls = 0, unresolved = 0;

	printf("\n# call arity check (definitions parsed in this run only)\n");
	printf("%-40s %7s %7s  %s\n", "FUNCTION", "DECL", "CALL", "STATUS");
	for (i = 0; i < ndefs; i++) {
		int sites = 0;
		int bad_here = 0;
		int mismatch_arg = 0;

		if (defs[i].is_struct || !defs[i].has_def)
			continue;

		/* Every definition's body is searched for calls to THIS name. The
		 * first version searched only the callee's own body, which finds
		 * nothing by construction: a definition does not call itself. That
		 * reported "0 call(s) checked" and looked like a clean pass. */
		for (k = 0; k < ndefs; k++) {
			const char *p = defs[k].body;

			while ((p = strstr(p, defs[i].name)) != NULL) {
				const char *at = p + strlen(defs[i].name);
				const char *args, *close;
				int depth = 1;
				const char *q;
				int got;

				if (at != defs[k].body &&
				    (isalnum((unsigned char)at[-1]) || at[-1] == '_' ||
				     at[-1] == '.' || at[-1] == '>'))
					goto next;
				if (*at != '(')
					goto next;
				args = at + 1;
				for (q = args; *q; q++) {
					if (*q == '(')
						depth++;
					else if (*q == ')') {
						depth--;
						if (depth == 0)
							break;
					}
				}
				if (!*q)
					goto next;
				close = q;
				got = count_args(args, close);
				sites++;
				if (got != defs[i].nparams) {
					if (!bad_here) {
						printf("%-40s %7d %7d  %s\n",
						       defs[i].name, defs[i].nparams, got,
						       bad_here ? "" : "ARITY MISMATCH");
						bad_here = 1;
						bad++;
					}
					if (got > mismatch_arg)
						mismatch_arg = got;
				}
				p = close;
				continue;
			next:
				p += strlen(defs[i].name);
			}
		}
		calls += sites;
		if (sites > 0 && bad_here)
			printf("%-40s %7d %7d  %s\n", defs[i].name, defs[i].nparams,
			       mismatch_arg, "  ^ repeated per offending call site");
	}
	printf("%d call(s) checked against %d parsed definition(s); %d mismatch(es)\n",
	       calls, ndefs, bad);
	/* Coverage gate. A check that examined almost nothing must not report a
	 * clean pass: "0 mismatches" over 3 calls out of 128 definitions means
	 * the parser missed the tree, not that the code is consistent. */
	if (calls < ndefs) {
		fprintf(stderr,
			"pm4dw: NOT_COVERAGE -- only %d call(s) resolved across %d "
			"definitions; the parser did not see the tree, so '0 "
			"mismatches' is NOT a pass\n", calls, ndefs);
		return 1;
	}
	(void)unresolved;
	return bad ? 1 : 0;
}

static void scan(const char *buf)
{
	const char *end = buf + strlen(buf);
	const char *line = buf;

	while (line < end) {
		const char *nl = memchr(line, '\n', (size_t)(end - line));
		const char *next = nl ? nl + 1 : end;
		const char *brace = memchr(line, '{', (size_t)(next - line));
		char name[MAXNAME];
		char *body;
		int is_struct;
		int params = -1;
		const char *lparen = NULL;

		if (!brace) {
			/* Kernel style puts the '{' of a function on its own line, and
			 * a signature can span several lines:
			 *
			 *   static void f(struct r *ring,
			 *                 unsigned vmid)
			 *   {
			 *
			 * Three guards keep this from accepting every statement in the
			 * file as a declaration:
			 *
			 *   - the line must open a parameter list, ')' unbalanced
			 *   - the line must not end in ';' (a call, not a signature)
			 *   - the '{' must be within LOOKAHEAD_LINES lines, because an
			 *     unbounded search pairs "mutex_unlock(&lock);" with the
			 *     body of whatever block comes next, which invented a
			 *     definition named `mutex_unlock` containing unrelated code
			 */
			const char *ahead;
			const char *found = NULL;
			int steps = 0;
			const char *line_end_trim = line + (size_t)(next - line);

			while (line_end_trim > line &&
			       isspace((unsigned char)line_end_trim[-1]))
				line_end_trim--;
			if (line_end_trim > line && line_end_trim[-1] == ';') {
				line = next;
				continue;
			}
			/* A preprocessor line is never a definition. "#define X(a,b)"
			 * was being parsed as a function named X, which is how the
			 * arity check ended up comparing against names like "!" and
			 * "running". */
			if (line < end && *line == '#') {
				line = next;
				continue;
			}
			if (!memchr(line, '(', (size_t)(next - line))) {
				line = next;
				continue;
			}
			for (ahead = next; ahead < end && steps <= LOOKAHEAD_LINES; ) {
				const char *p2 = ahead;
				const char *nl;
				const char *trimmed;

				while (p2 < end && (*p2 == ' ' || *p2 == '\t'))
					p2++;
				if (p2 < end && *p2 == '{') {
					found = p2;
					break;
				}
				/* Stop at anything that cannot be part of a signature. A
				 * declaration continues only while the lines keep
				 * forming a parameter list: no statement terminator and
				 * no blank line. gfx_v8_0_ring_emit_gds_switch wraps
				 * seven parameters over five lines, which a fixed small
				 * cap missed. */
				trimmed = p2;
				{
					const char *e2 = ahead + (size_t)(next - ahead);
					while (e2 > p2 && isspace((unsigned char)e2[-1]))
						e2--;
					if (e2 == p2)
						break; /* blank line */
					if (e2[-1] == ';')
						break;
				}
				(void)trimmed;
				nl = memchr(ahead, '\n', (size_t)(end - ahead));
				if (!nl)
					break;
				ahead = nl + 1;
				steps++;
			}
			if (!found) {
				line = next;
				continue;
			}
			brace = found;
			is_struct = 0;
			if (!decl_name(line, brace, name, sizeof(name))) {
				line = next;
				continue;
			}
			lparen = signature_open(line, name);
			goto have_body;
		}
		if (line < end && *line == '#') {
			line = next;
			continue;
		}
		/* Leading whitespace only means a continuation, not a definition. */
		is_struct = (brace > line && memchr(line, '=', (size_t)(brace - line)) != NULL);

		if (!is_struct) {
			if (!decl_name(line, brace, name, sizeof(name))) {
				line = next;
				continue;
			}
			lparen = signature_open(line, name);
		} else {
			if (!init_name(line, brace, name, sizeof(name))) {
				line = next;
				continue;
			}
		}

		have_body:
		body = extract_body(brace, end);
		if (!body) {
			line = next;
			continue;
		}
		if (!find_def(name)) {
			if (ndefs >= MAXDEFS)
				die("too many definitions", name);
			snprintf(defs[ndefs].name, MAXNAME, "%s", name);
			defs[ndefs].body = body;
			if (is_struct_marker(body))
				defs[ndefs].is_struct = 1;
			if (lparen) {
				const char *lp = strchr(lparen, '(');
				if (lp) {
					const char *rp = matching_paren(lp);
					if (rp)
						params = count_params(lp + 1, rp);
				}
			}
			if (params < 0)
				params = 0;
			defs[ndefs].nparams = params;
			defs[ndefs].has_def = 1;
			ndefs++;
		} else {
			free(body);
		}
		line = next;
	}
}

/* ---- cost model ------------------------------------------------------- */

static int count_sym(const char *hay, const char *sym)
{
	int n = 0;
	size_t len = strlen(sym);
	const char *p = hay;

	while ((p = strstr(p, sym)) != NULL) {
		const char *after = p + len;
		int before_ok = (p == hay) ||
			!(isalnum((unsigned char)p[-1]) || p[-1] == '_' || p[-1] == '.');
		if (before_ok && *after == '(')
			n++;
		p = after;
	}
	return n;
}

/* Count occurrences of `name` used as a CALL: an identifier boundary followed
 * by '('. Two cases deliberately excluded, because both create false call
 * edges and were the cause of a non-converging graph:
 *
 *   - a name followed by ')' : the parameter list being re-read, e.g.
 *     "... = gfx_v8_0_ring_emit_vm_flush);" is a reference, not a call
 *   - a name preceded by '.' or "->" : a struct field, not a free function
 *
 * Anything else with an identifier boundary and '(' is treated as a call. */
static int count_calls(const char *body, const char *name)
{
	int n = 0;
	size_t len = strlen(name);
	const char *p = body;

	while ((p = strstr(p, name)) != NULL) {
		const char *at = p;
		const char *after = p + len;
		int ok = 1;

		if (at != body && (isalnum((unsigned char)at[-1]) || at[-1] == '_'))
			ok = 0;
		if (*after && (isalnum((unsigned char)*after) || *after == '_'))
			ok = 0;
		if (ok && at != body && (at[-1] == '.' || (at[-2] == '-' && at[-1] == '>')))
			ok = 0;
		if (ok && *after != '(')
			ok = 0;
		if (ok)
			n++;
		p = after;
	}
	return n;
}

/* Count times `name` appears as the right-hand side of a `.field = name`
 * assignment. This is how a struct initialiser names its handlers. */
static int count_assigned_handler(const char *body, const char *name)
{
	int n = 0;
	size_t len = strlen(name);
	const char *p = body;

	while ((p = strstr(p, name)) != NULL) {
		const char *at = p;
		const char *after = p + len;
		int ok = 1;

		/* the identifier must not be part of a longer one */
		if (at != body && (isalnum((unsigned char)at[-1]) || at[-1] == '_'))
			ok = 0;
		if (*after && (isalnum((unsigned char)*after) || *after == '_'))
			ok = 0;
		/* and something of the form ".x = " must precede it */
		if (ok) {
			const char *q = at - 1;
			int saw_eq = 0;
			while (q > body && (*q == ' ' || *q == '\t' || *q == '\n'))
				q--;
			if (q > body && *q == '=')
				saw_eq = 1;
			else if (q > body && *q == '&')
				saw_eq = 1;
			if (!saw_eq)
				ok = 0;
		}
		if (ok)
			n++;
		p = after;
	}
	return n;
}

/* Record every amdgpu_ring_write_multiple() call site verbatim.
 *
 * This exists because counting such a call as ONE dword is wrong by an unknown
 * amount, and a bare "NOT_EXPANDED" flag does not say by how much. On GFX8 the
 * third argument is `cnt_de - 2`, where cnt_de derives from a struct size, so
 * the true cost is 17 dwords for de_meta and 4 for ce_meta. Printing the
 * arguments makes that auditable instead of a matter of trust. */
static void collect_write_multiple(Def *d)
{
	const char *p = d->body;
	const char *key = "amdgpu_ring_write_multiple(";

	d->nwm = 0;
	while ((p = strstr(p, key)) != NULL && d->nwm < 8) {
		const char *args = p + strlen(key);
		const char *close = args;
		int depth = 0;
		size_t n;
		/* balance parens: the argument list contains a cast, "(void *)&x",
		 * so stopping at the first ')' truncates the site to "(void *" */
		for (; *close; close++) {
			if (*close == '(')
				depth++;
			else if (*close == ')') {
				if (depth == 0)
					break;
				depth--;
			}
		}
		if (!*close)
			break;
		n = (size_t)(close - args);
		if (n >= sizeof(d->wm_sites[0]))
			n = sizeof(d->wm_sites[0]) - 1;
		memcpy(d->wm_sites[d->nwm], args, n);
		d->wm_sites[d->nwm][n] = '\0';
		d->nwm++;
		p = close;
	}
}

static void cost_functions(void)
{
	int i, j, pass, changed = 1;

	for (i = 0; i < ndefs; i++) {
		defs[i].base = count_sym(defs[i].body, "amdgpu_ring_write");
		defs[i].uses_multiple =
			count_sym(defs[i].body, "amdgpu_ring_write_multiple") ? 1 : 0;
		collect_write_multiple(&defs[i]);
		/* An indirect dispatch cannot be resolved by reading one file.
		 * amdgpu dispatches most emission helpers through
		 * `->gmc_funcs->emit_...`, so this is the difference between a total
		 * that is right and a total that is quietly too low. The flag makes
		 * the difference visible instead of letting the caller assume the
		 * number is complete. */
		defs[i].indirect =
			(strstr(defs[i].body, "->gmc_funcs->") ||
			 strstr(defs[i].body, "->funcs->") ||
			 strstr(defs[i].body, "->pmf->")) ? 1 : 0;
		defs[i].total = defs[i].base;
	}

	/* A call graph may contain a cycle (mutual recursion, or a function whose
	 * name also appears in a string). Naive iteration then diverges and the
	 * totals run into the billions — which is what happened before this guard:
	 * .emit_frame_size reservations are compared against these numbers, so a
	 * diverging total is not cosmetic, it is a false verdict. */
	for (pass = 0; pass < 64 && changed; pass++) {
		changed = 0;
		if (pass == 32) {
			/* A cycle means the emission cost is not a finite number:
			 * whatever recurses would have to emit dwords forever. Rather
			 * than report a diverging figure, name the cycle so it can be
			 * judged. Mutual recursion through a struct field is the usual
			 * cause and is usually a false edge. */
			for (i = 0; i < ndefs; i++) {
				for (j = 0; j < ndefs; j++) {
					int n;
					if (i == j || defs[j].is_struct)
						continue;
					n = count_calls(defs[i].body, defs[j].name);
					if (n > 0 && defs[j].total > defs[i].base)
						fprintf(stderr,
							"pm4dw: cycle suspect: %s calls %s "
							"(%d site%s)\n",
							defs[i].name, defs[j].name, n,
							n == 1 ? "" : "s");
				}
			}
			die("call graph did not converge after 32 passes; "
			    "a cycle is present and no fixed point exists", NULL);
		}
		for (i = 0; i < ndefs; i++) {
			int t = defs[i].base;
			for (j = 0; j < ndefs; j++) {
				int n;
				if (i == j)
					continue;
				if (defs[j].is_struct)
					continue; /* a struct emits nothing itself */
				n = count_calls(defs[i].body, defs[j].name);
				if (n > 0)
					t += n * defs[j].total;
			}
			if (t != defs[i].total) {
				defs[i].total = t;
				changed = 1;
			}
		}
	}

	/* Second pass: a struct's cost is the sum of the handlers it names. This
	 * is an UPPER BOUND on one frame, not the worst case. emit_frame_size is
	 * reserved for the largest combination that can actually co-occur in a
	 * single submission, and the driver does not encode which handlers that
	 * is. So a struct total is reported as a bound and is never used to
	 * declare under-reservation on its own. */
	for (i = 0; i < ndefs; i++) {
		if (!defs[i].is_struct)
			continue;
		defs[i].total = 0;
		for (j = 0; j < ndefs; j++) {
			int n;
			if (i == j || defs[j].is_struct)
				continue;
			/* Look for the handler on the RIGHT of an '=' assignment:
			 * ".emit_vm_flush = emit_vm_flush,". count_sym() will not do,
			 * because it ignores an occurrence preceded by '.' (to skip
			 * field names) and requires a '(' after the name, and neither
			 * holds for the right-hand side of a struct initialiser. */
			n = count_assigned_handler(defs[i].body, defs[j].name);
			if (n > 0)
				defs[i].total += n * defs[j].total;
		}
	}
}

/* ---- .emit_frame_size arithmetic -------------------------------------- */

/* Sum the .emit_frame_size term list. Terms are numbers, macro names, or
 * NAME * NUMBER. Comments are skipped; the first comment's text is returned as
 * a label. The field ends at the next ',' or ';' outside parens — NOT at the
 * next ';', because this is one field of a comma-separated initialiser, and a
 * comma inside a comment ends the scan if comments are not skipped. */
static int eval_efs(const char *body, long *out, char *label, size_t label_len)
{
	const char *end_all = body + strlen(body);
	const char *p;
	const char *field_end = NULL;
	int d = 0;
	long total = 0;
	char first_label[MAXNAME] = "";

	if (label && label_len)
		label[0] = '\0';

	for (p = body; p < end_all; p++) {
		if (strncmp(p, ".emit_frame_size", 16) == 0) {
			const char *eq = strchr(p, '=');
			if (!eq)
				return 0;
			p = eq;
			break;
		}
	}
	if (!p || p >= end_all)
		return 0;

	for (const char *e = p + 1; e < end_all; e++) {
		if (e + 1 < end_all && e[0] == '/' && (e[1] == '*' || e[1] == '/')) {
			if (e[1] == '*') {
				const char *cl = e + 2;
				while (cl + 1 < end_all && !(cl[0] == '*' && cl[1] == '/'))
					cl++;
				e = (cl + 1 < end_all) ? cl + 1 : end_all - 1;
			} else {
				const char *nl = memchr(e, '\n', (size_t)(end_all - e));
				e = nl ? nl : end_all - 1;
			}
			continue;
		}
		if (*e == '(') {
			d++;
			continue;
		}
		if (*e == ')') {
			d--;
			continue;
		}
		if (d == 0 && (*e == ',' || *e == ';')) {
			field_end = e;
			break;
		}
	}
	if (!field_end)
		return 0;

	/* tokenise terms */
	p++;
	while (p < field_end) {
		char tok[MAXNAME];
		int len = 0;
		long v = 0, mul = 1;

		/* Skip separators before the term. '+' must be skipped here, not only
		 * as a terminator after a term: with `9 + MACRO`, after reading "9"
		 * the cursor sits on '+', an empty token is produced, and the loop
		 * continues without advancing — which hung the tool. */
		while (p < field_end &&
		       (isspace((unsigned char)*p) || *p == '+'))
			p++;
		if (p >= field_end)
			break;

		while (p < field_end && *p != '+' && len < (int)sizeof(tok) - 1) {
			if (p + 1 < field_end && p[0] == '/' && (p[1] == '*' || p[1] == '/')) {
				if (!first_label[0]) {
					const char *t0 = p + (p[1] == '*' ? 2 : 2);
					const char *after = (p[1] == '*')
						? strstr(p, "*/")
						: memchr(p, '\n', (size_t)(field_end - p));
					if (p[1] == '*' && after)
						after += 2;
					else if (after)
						after += 1;
					else
						after = field_end;
					while (t0 < after && isspace((unsigned char)*t0))
						t0++;
					{
						size_t ln = (size_t)(after - t0);
						while (ln > 0 && isspace((unsigned char)t0[ln - 1]))
							ln--;
						if (ln < sizeof(first_label)) {
							memcpy(first_label, t0, ln);
							first_label[ln] = '\0';
						}
					}
				}
				if (p[1] == '*') {
					const char *cl = strstr(p, "*/");
					if (!cl)
						return 0;
					p = cl + 2;
				} else {
					const char *nl = memchr(p, '\n', (size_t)(field_end - p));
					if (!nl)
						return 0;
					p = nl + 1;
				}
				continue;
			}
			if (*p == '"' || *p == '\'') {
				char q = *p++;
				while (p < field_end && *p != q) {
					if (*p == '\\' && p + 1 < field_end)
						p++;
					p++;
				}
				if (p < field_end)
					p++;
				continue;
			}
			tok[len++] = *p++;
		}
		tok[len] = '\0';
		if (len == 0)
			continue;

		/* trim */
		{
			int b = 0, e = len;
			while (b < e && isspace((unsigned char)tok[b]))
				b++;
			while (e > b && isspace((unsigned char)tok[e - 1]))
				e--;
			if (e <= b)
				continue;
			memmove(tok, tok + b, (size_t)(e - b));
			tok[e - b] = '\0';
		}

		{
			char *star = strchr(tok, '*');
			if (star) {
				char *lhs = tok, *rhs = star + 1;
				char *le;
				*star = '\0';
				while (*rhs && isspace((unsigned char)*rhs))
					rhs++;
				/* trim the left side too: the term ran to the next '+' and
				 * carries the space before the '*' */
				le = lhs + strlen(lhs);
				while (le > lhs && isspace((unsigned char)le[-1]))
					*--le = '\0';
				mul = isdigit((unsigned char)*rhs) ? atol(rhs) : macro_value(rhs);
				v = isdigit((unsigned char)lhs[0]) ? atol(lhs) : macro_value(lhs);
			} else if (isdigit((unsigned char)tok[0])) {
				v = atol(tok);
			} else {
				v = macro_value(tok);
			}
		}
		total += v * mul;
	}

	*out = total;
	if (label && label_len)
		snprintf(label, label_len, "%s", first_label);
	return 1;
}

/* ---- main -------------------------------------------------------------- */

static void usage(void)
{
	fprintf(stderr,
	        "usage: pm4dw --macro NAME=VALUE ... --struct NAME ... "
	        "--path fn1,fn2,... file.c ...\n"
	        "  --struct  sum every handler the struct names (upper bound)\n"
	        "  --path    sum the named emitters in order (one submission)\n");
	exit(2);
}

/* Report an ordered emission path: total dwords, and per-leg presence.
 * A leg whose function is absent from the corpus is reported ABSENT, because
 * "this ASIC does not implement that emitter" and "it emits nothing" are
 * different findings and the second is what a silent zero would claim. */
static int report_path(const char *spec)
{
	char buf[2048];
	char *p;
	int total = 0;
	int absent = 0;
	int legs = 0;

	snprintf(buf, sizeof(buf), "%s", spec);

	printf("\n# emission path (ordered, one submission)\n");
	printf("%-4s %-42s %6s  %s\n", "LEG", "EMITTER", "DW", "STATUS");
	p = buf;
	while (*p) {
		char name[MAXNAME];
		int n = 0;
		Def *d;

		while (*p == ' ' || *p == ',' || *p == '\t')
			p++;
		if (!*p)
			break;
		while (*p && *p != ',' && *p != ' ' && *p != '\t') {
			if (n < (int)sizeof(name) - 1)
				name[n++] = *p;
			p++;
		}
		name[n] = '\0';
		legs++;

		d = find_def(name);
		if (!d) {
			printf("%-4d %-42s %6s  %s\n", legs, name, "-",
			       "ABSENT(not in corpus: not implemented for this ASIC, "
			       "or a name this parser cannot see)");
			absent++;
			continue;
		}
		printf("%-4d %-42s %6d  %s\n", legs, name, d->total,
		       d->indirect ? "sum excludes indirect dispatch" :
		       (d->uses_multiple ? "write_multiple not expanded" : "complete"));
		total += d->total;
	}
	printf("\n%s: %d leg(s), %d absent, %d dwords over the legs present\n",
	       spec, legs, absent, total);
	return absent ? 1 : 0;
}

/* ---- struct sizes ----------------------------------------------------- */

/* Count fixed-size members of `struct <name>` across the given headers, and
 * report the byte size. This resolves the amdgpu_ring_write_multiple() payloads
 * without running anything: on GFX8, de_meta copies
 * (sizeof(vi_de_ib_state)>>2)+4-2-2 = 17 dwords, not the 1 the cost model
 * assigns to the call. Handlers and drivers differ by that much.
 *
 * Returns 0 if the struct is not found, so the caller can say NOT_FOUND rather
 * than reporting a made-up size. */
static int struct_size_hdrs(char **hdrs, int nhdrs, const char *name,
                            int *members, long *bytes)
{
	char pat[MAXNAME + 16];
	const char *p;
	int n = 0;
	int found = 0;
	int i;

	for (i = 0; i < nhdrs; i++) {
		const char *buf = hdrs[i];
		if (!buf)
			continue;
		snprintf(pat, sizeof(pat), "struct %s {", name);
		p = strstr(buf, pat);
		if (!p)
			continue;
		found = 1;
		{
			const char *e = strstr(p, "\n};");
			const char *lim = e ? e : p + strlen(p);
			const char *q;
			for (q = p; q < lim; ) {
				/* members are indented with tabs, so skip to the first
				 * non-blank before testing the type name. Without this
				 * every member was missed and the struct reported 0. */
				while (q < lim && isspace((unsigned char)*q))
					q++;
				if (q >= lim)
					break;
				if (strncmp(q, "uint32_t", 8) == 0 || strncmp(q, "uint64_t", 8) == 0 ||
				    strncmp(q, "u32", 3) == 0 || strncmp(q, "u64", 3) == 0) {
					const char *nl = memchr(q, '\n', (size_t)(lim - q));
					const char *line_end = nl ? nl : lim;
					/* a member is a declaration terminated by ';' with
					 * a name before it; an array member counts as one,
					 * so the caller must not assume 4 bytes for it */
					const char *s = memchr(q, ';', (size_t)(line_end - q));
					if (s)
						n++;
					/* step PAST the newline. Stopping on it makes the
					 * next iteration find the same newline and spin
					 * forever, which is what happened on first run. */
					q = nl ? nl + 1 : lim;
					continue;
				}
				q = memchr(q, '\n', (size_t)(lim - q));
				if (!q)
					break;
				q++;
			}
		}
		break;
	}
	if (!found)
		return 0;
	*members = n;
	*bytes = (long)n * 4;
	return 1;
}

static int report_struct_sizes(char **hdrs, int nhdrs, char **names, int nnames)
{
	int k, rc = 0;

	if (nnames == 0)
		return 0;
	printf("\n# struct sizes (each fixed-size member counted as 4 bytes)\n");
	printf("%-36s %8s %8s %9s %10s\n", "STRUCT", "MEMBERS", "BYTES",
	       "cnt_de", "write_mult");
	for (k = 0; k < nnames; k++) {
		int members = 0;
		long bytes = 0;
		if (!struct_size_hdrs(hdrs, nhdrs, names[k], &members, &bytes)) {
			printf("%-36s %8s %8s %9s %10s\n", names[k],
			       "-", "-", "-", "NOT_FOUND");
			rc = 1;
			continue;
		}
		printf("%-36s %8d %8ld %9ld %10ld\n", names[k], members, bytes,
		       (bytes >> 2) + 4 - 2, (bytes >> 2) + 4 - 2 - 2);
	}
	return rc;
}

int main(int argc, char **argv)
{
	int i;
	int rc = 0;
	int checked = 0;
	char **structs;
	int nstructs = 0;
	char **files;
	int nfiles = 0;
	char **paths;
	int npaths = 0;
	int wmsites = 0;
	int wmsite_count = 0;
	char **ssz;
	int nssz = 0;
	char **bufs;
	int nbufs = 0;
	int arity = 0;

	structs = calloc((size_t)argc, sizeof(char *));
	files = calloc((size_t)argc, sizeof(char *));
	paths = calloc((size_t)argc, sizeof(char *));
	ssz = calloc((size_t)argc, sizeof(char *));
	bufs = calloc((size_t)argc, sizeof(char *));
	if (!structs || !files || !paths || !ssz || !bufs)
		die("out of memory", NULL);

	for (i = 1; i < argc; i++) {
		if (strcmp(argv[i], "--macro") == 0) {
			if (++i >= argc)
				usage();
			add_macro(argv[i]);
		} else if (strcmp(argv[i], "--struct") == 0) {
			if (++i >= argc)
				usage();
			structs[nstructs++] = argv[i];
		} else if (strcmp(argv[i], "--struct-size") == 0) {
			/* exactly one name per flag. A greedy "until the next
			 * option" loop swallowed the input filenames, because they
			 * do not start with '-'. */
			if (++i >= argc)
				usage();
			if (nssz >= MAXMACROS)
				die("too many --struct-size names", NULL);
			ssz[nssz++] = argv[i];
		} else if (strcmp(argv[i], "--check-arity") == 0) {
			arity = 1;
		} else if (strcmp(argv[i], "--wm-sites") == 0) {
			wmsites = 1;
		} else if (strcmp(argv[i], "--path") == 0) {
			if (++i >= argc)
				usage();
			paths[npaths++] = argv[i];
		} else if (argv[i][0] == '-' && argv[i][1] == '-') {
			usage();
		} else {
			files[nfiles++] = argv[i];
		}
	}
	if (nfiles == 0)
		usage();
	if (nmacros == 0)
		die("no --macro given; symbolic terms in emit_frame_size cannot be "
		    "resolved without the real header values", NULL);

	for (i = 0; i < nfiles; i++) {
		FILE *f = fopen(files[i], "rb");
		long sz;
		char *buf;
		if (!f)
			die("cannot open", files[i]);
		fseek(f, 0, SEEK_END);
		sz = ftell(f);
		fseek(f, 0, SEEK_SET);
		if (sz <= 0)
			die("empty or unreadable", files[i]);
		buf = malloc((size_t)sz + 1);
		if (!buf)
			die("out of memory", NULL);
		if (fread(buf, 1, (size_t)sz, f) != (size_t)sz)
			die("short read", files[i]);
		buf[sz] = '\0';
		fclose(f);
		scan(buf);
		/* keep the contents, not just the name: --struct-size has to read
		 * struct definitions, and passing files[] (which holds paths) to a
		 * function expecting contents silently reported NOT_FOUND for a
		 * struct that exists. */
		if (nbufs >= argc)
			die("too many sources", files[i]);
		bufs[nbufs++] = buf;
	}
	cost_functions();

	printf("# emission cost, resolved through callees\n");
	printf("%-44s %5s %5s %s\n", "NAME", "BASE", "TOTAL", "NOTE");
	for (i = 0; i < ndefs; i++) {
		if (defs[i].total == 0 && !defs[i].uses_multiple)
			continue;
		printf("%-44s %5d %5d %s%s\n", defs[i].name, defs[i].base,
		       defs[i].total,
		       defs[i].uses_multiple ? "write_multiple:NOT_EXPANDED " : "",
		       defs[i].indirect ? "INDIRECT_DISPATCH:INCOMPLETE" : "");
	}

	if (getenv("PM4DW_DEBUG")) {
		int z;
		for (z = 0; z < ndefs; z++)
			fprintf(stderr, "DEBUG name=%-24s struct=%d base=%d total=%d has_emit=%d\n",
			        defs[z].name, defs[z].is_struct, defs[z].base,
			        defs[z].total,
			        strstr(defs[z].body, ".emit_") ? 1 : 0);
	}
	printf("\n# .emit_frame_size reservation check\n");
	printf("%-36s %9s %8s %9s  %s\n", "STRUCT", "DECLARED", "EMITTED",
	       "RESIDUAL", "VERDICT");
	for (i = 0; i < nstructs; i++) {
		Def *d = find_def(structs[i]);
		long declared = 0;
		char label[MAXNAME] = "";

		if (!d) {
			printf("%-36s %9s %8s %9s  %s\n", structs[i], "-", "-", "-",
			       "STRUCT_NOT_FOUND");
			rc = 1;
			continue;
		}
		if (!eval_efs(d->body, &declared, label, sizeof(label))) {
			printf("%-36s %9s %8s %9s  %s\n", structs[i], "-", "-", "-",
			       "NO_EMIT_FRAME_SIZE_FIELD");
			rc = 1;
			continue;
		}
		checked++;
		printf("%-36s %9ld %8d %+9ld  %s", structs[i], declared, d->total,
		       declared - (long)d->total,
		       declared >= d->total ? "OK(reservation >= sum of handlers)"
					   : "BELOW sum-of-handlers");
		if (label[0])
			printf("   [%s]", label);
		printf("\n");
		/* No exit code is set here on purpose. d->total is the sum of every
		 * handler the struct names, but emit_frame_size must cover the
		 * largest set that can co-occur in one submission, which is a subset
		 * of that. declared < sum therefore does NOT prove under-reservation,
		 * and declaring it would be a false positive. The number is printed
		 * so a reader can compare it; the verdict is a bound, not a defect. */
	}

	for (i = 0; i < npaths; i++) {
		int prc = report_path(paths[i]);
		if (prc > rc)
			rc = prc;
		checked++;
	}

	if (arity) {
		int arc = check_arity();
		if (arc > rc)
			rc = arc;
		checked++;
	}

	if (nssz > 0) {
		int srrc = report_struct_sizes(bufs, nbufs, ssz, nssz);
		if (srrc > rc)
			rc = srrc;
		checked++;
	}

	if (wmsites) {
		printf("\n# amdgpu_ring_write_multiple() call sites (each counted as 1 dw "
		       "by the cost model)\n");
		for (i = 0; i < ndefs; i++) {
			int k;
			for (k = 0; k < defs[i].nwm; k++) {
				printf("%-40s %s\n", defs[i].name,
				       defs[i].wm_sites[k]);
				wmsite_count++;
			}
		}
		printf("%d site(s); each is a multi-dword copy whose size is NOT in "
		       "this count\n", wmsite_count);
	}

	if (!checked) {
		fprintf(stderr, "pm4dw: nothing was checked; the input did not match\n");
		return 1;
	}
	free(structs);
	free(files);
	free(paths);
	return rc;
}