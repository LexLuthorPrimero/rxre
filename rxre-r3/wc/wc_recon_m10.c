/* wc_recon — hitos 1/2: LC_ALL=C, salida por defecto y flags {-c,-l,-w} + combinaciones.
 * Semántica derivada del oráculo sellado + disasm (vía unibyte con __ctype_b_loc).
 * Bytes altos clasif. NO-espacio; espacio C = {20,09,0a,0b,0c,0d}; palabras=runs no-espacio;
 * líneas=0x0a. Flags en salida GNU: orden fijo líneas → palabras → bytes; ausentes se omiten. */
#include "wc_width_table_gen.h"
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
static int utf8_decode(const unsigned char *s, size_t n, unsigned *cp) {
    if (s[0] < 0x80) { *cp = s[0]; return 1; }
    if (n < 2) return 0;
    unsigned b0 = s[0], b1 = n > 1 ? s[1] : 0, b2 = n > 2 ? s[2] : 0, b3 = n > 3 ? s[3] : 0;
    if ((b0 & 0xe0) == 0xc0 && (b1 & 0xc0) == 0x80) { *cp = ((b0 & 0x1f) << 6) | (b1 & 0x3f); return 2; }
    if ((b0 & 0xf0) == 0xe0 && (b1 & 0xc0) == 0x80 && (b2 & 0xc0) == 0x80) { *cp = ((b0 & 0x0f) << 12) | ((b1 & 0x3f) << 6) | (b2 & 0x3f); return 3; }
    if ((b0 & 0xf8) == 0xf0 && (b1 & 0xc0) == 0x80 && (b2 & 0xc0) == 0x80 && (b3 & 0xc0) == 0x80) { *cp = ((b0 & 0x07) << 18) | ((b1 & 0x3f) << 12) | ((b2 & 0x3f) << 6) | (b3 & 0x3f); return 4; }
    return 0;
}
static int is_unicode_space_cp(unsigned cp) {
    switch (cp) {
        case 0x09: case 0x0a: case 0x0b: case 0x0c: case 0x0d: case 0x20: case 0x85:
        case 0xa0: case 0x1680: case 0x2000: case 0x2001: case 0x2002:
        case 0x2003: case 0x2004: case 0x2005: case 0x2006: case 0x2007: case 0x2008:
        case 0x2009: case 0x200a: case 0x2028: case 0x2029: case 0x202f: case 0x205f:
        case 0x3000: case 0xfeff:
            return 1;
        default: return 0;
    }
}
static int mode_is_utf8(void) {
    const char *e = getenv("LC_ALL");
    if (!e || !*e) e = getenv("LC_CTYPE");   /* empty LC_ALL = not set */
    if (!e || !*e) e = getenv("LANG");       /* fallback to LANG when LC_CTYPE unset */
    if (e && *e && (strstr(e, "utf8") || strstr(e, "UTF-8") || strstr(e, "UTF8"))) return 1;
    return 0;
}
static int is_utf8 = -1;
typedef struct { unsigned long lines, words, bytes, max_line, chars; } wc_count;

static int range_has(const wc_range *r, size_t n, unsigned cp) {
    size_t lo = 0, hi = n;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (r[mid].hi < cp) lo = mid + 1; else hi = mid;
    }
    return lo < n && r[lo].lo <= cp && cp <= r[lo].hi;
}
static int cp_width(unsigned cp) {
    size_t ncf = sizeof WC_CF_1 / sizeof WC_CF_1[0];
    size_t lo = 0, hi = ncf;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (WC_CF_1[mid] < cp) lo = mid + 1; else hi = mid;
    }
    if (lo < ncf && WC_CF_1[lo] == cp) return 1;              /* soft hyphen + visible Cf */
    if (range_has(WC_ZERO, sizeof WC_ZERO / sizeof WC_ZERO[0], cp)) return 0;
    if (range_has(WC_WIDE, sizeof WC_WIDE / sizeof WC_WIDE[0], cp)) return 2;
    return 1;
}
static int is_space_c(unsigned char c) {
    /* LC_ALL=C separators (256-byte probe vs native oracle, 2026-11-12):
     * { 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x20, 0xa0 } */
    return c == 0x20 || c == 0x09 || c == 0x0a || c == 0x0b || c == 0x0c || c == 0x0d || c == 0xa0;
}
static wc_count count_c(const unsigned char *s, size_t n) {
    wc_count r = {0, 0, (unsigned long)n, 0, 0};
    unsigned long cur = 0;
    int in_word = 0;
    r.chars = (unsigned long)n;
    for (size_t i = 0; i < n; i++) {
        unsigned char c = s[i];
        if (c == 0x0a) { r.lines++; if (cur > r.max_line) r.max_line = cur; cur = 0; }
        if (is_space_c(c)) { in_word = 0; }
        else if (!in_word) { r.words++; in_word = 1; }
        if (c == 0x09) { cur = (cur + 8) & ~7UL; }
        else if (c == 0x0c || c == 0x0d) { cur = 0; }   /* \f \r: reset de columna (wc -L) */
        else if (c >= 0x20 && c <= 0x7e) { cur += 1; }
        if (cur > r.max_line) r.max_line = cur;   /* max por posición, no solo en \n */
    }
    if (cur > r.max_line) r.max_line = cur;
    return r;
}
static wc_count count_utf8(const unsigned char *s, size_t n) {
    /* UTF-8 path (hito 8): decodifica codepoints y clasifica contra el set de espacios Unicode completo.
     * Secuencia inválida → \uFFFD (no es espacio); líneas=\n; bytes = tamaño del buffer. */
    wc_count r = {0, 0, (unsigned long)n, 0, 0};
    unsigned long cur = 0;
    int in_word = 0;
    size_t i = 0;
    while (i < n) {
        unsigned cp; int len = utf8_decode(s + i, n - i, &cp);
        if (len == 0) { len = 1; cp = 0xfffd; }
        r.chars++;
        if (cp == 0x0a) { r.lines++; if (cur > r.max_line) r.max_line = cur; cur = 0; in_word = 0; }
        else if (is_unicode_space_cp(cp)) {
            in_word = 0;
            if (cp == 0x09) { cur = (cur + 8) & ~7UL; }
            else if (cp == 0x0c || cp == 0x0d) { cur = 0; }
            else { cur += (unsigned long)cp_width(cp); }
        } else {
            if (!in_word) { r.words++; in_word = 1; }
            cur += (unsigned long)cp_width(cp);
        }
        if (cur > r.max_line) r.max_line = cur;
        i += (size_t)len;
    }
    if (cur > r.max_line) r.max_line = cur;
    return r;
}
wc_count count(const unsigned char *s, size_t n) {
    if (is_utf8 < 0) is_utf8 = mode_is_utf8();
    if (is_utf8) return count_utf8(s, n);
    return count_c(s, n);
}
/* flags: bit0=lines(-l), bit1=words(-w), bit2=bytes(-c); 0 => default L W B */
size_t wc_format(char *buf, size_t bufsize, wc_count r, unsigned flags) {
    int fl, fw, fb, fm;
    if (flags == 0) { fl = fw = fb = 1; fm = 0; } else { fl = !!(flags & 1); fw = !!(flags & 2); fb = !!(flags & 4); fm = !!(flags & 8); }
    size_t o = 0;
    unsigned long vals[4] = { r.lines, r.words, r.bytes, r.max_line };
    int out[4] = { fl, fw, fb, fm };
    int first = 1;
    for (int k = 0; k < 4; k++) {
        if (!out[k]) continue;
        if (!first) { if (o + 1 < bufsize) buf[o++] = ' '; }
        first = 0;
        char tmp[24];
        int t = 0;
        unsigned long v = vals[k];
        if (v == 0) { tmp[t++] = '0'; }
        while (v) { tmp[t++] = (char)('0' + (v % 10)); v /= 10; }
        while (t) { if (o + 1 < bufsize) buf[o++] = tmp[--t]; }
    }
    if (o < bufsize) buf[o] = '\0';
    return o;
}
