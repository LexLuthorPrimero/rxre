/* wc_count.c — SRXRE cleanroom — reconstrucción semántica de /usr/bin/wc
 * (/usr/bin/wc — sha256 "81d61459..." — vaddr 0xc40-0x9092, GNU coreutils 9.10).
 * Dominio verificado: LC_ALL=C + es_AR.utf8; salida default (L W B) con flags {-c,-l,-w,-L} y combinaciones;
 * NBSP (0xa0) = separador en C locale. UTF-8 path con 25 codepoints de espacio Unicode comunes.
 * Método: observación asistida + diferencial sellado; ver wc/INDEX.md y wc/SEAL_WC.txt.
 * NO es port 1:1 del desensamblado (NOT_EXECUTED); la reconstrucción reproduce la semántica por verificación
 * sellada (5 corpora × 2 locales, 0 divergencias).
 * Es independiente de glibc para clasificación de bytes (tabla propia C locale + decoder UTF-8 inline).
 */
#include <stddef.h>
#include <string.h>
#include <stdlib.h>

typedef struct { unsigned long lines, words, bytes, max_line; } wc_count;

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
    if (!e || !*e) e = getenv("LC_CTYPE");
    if (!e || !*e) e = getenv("LANG");
    if (e && *e && (strstr(e, "utf8") || strstr(e, "UTF-8") || strstr(e, "UTF8"))) return 1;
    return 0;
}
static int is_utf8 = -1;

static int is_space_c(unsigned char c) {
    /* LC_ALL=C separators (256-byte probe nativo, 2026-11-12):
     * { 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x20, 0xa0 } */
    return c == 0x20 || c == 0x09 || c == 0x0a || c == 0x0b || c == 0x0c || c == 0x0d || c == 0xa0;
}

static wc_count count_c(const unsigned char *s, size_t n) {
    wc_count r = {0, 0, (unsigned long)n, 0};
    unsigned long cur = 0;
    int in_word = 0;
    for (size_t i = 0; i < n; i++) {
        unsigned char c = s[i];
        if (c == 0x0a) { r.lines++; if (cur > r.max_line) r.max_line = cur; cur = 0; }
        if (is_space_c(c)) { in_word = 0; }
        else if (!in_word) { r.words++; in_word = 1; }
        if (c == 0x09) { cur = (cur + 8) & ~7UL; }
        else if (c == 0x0c || c == 0x0d) { cur = 0; }
        else if (c >= 0x20 && c <= 0x7e) { cur += 1; }
        if (cur > r.max_line) r.max_line = cur;
    }
    if (cur > r.max_line) r.max_line = cur;
    return r;
}

static wc_count count_utf8(const unsigned char *s, size_t n) {
    wc_count r = {0, 0, (unsigned long)n, 0};
    unsigned long cur = 0;
    int in_word = 0;
    size_t i = 0;
    while (i < n) {
        unsigned cp; int len = utf8_decode(s + i, n - i, &cp);
        if (len == 0) { len = 1; cp = 0xfffd; }
        if (cp == 0x0a) { r.lines++; if (cur > r.max_line) r.max_line = cur; cur = 0; in_word = 0; }
        else if (is_unicode_space_cp(cp)) {
            in_word = 0;
            if (cp == 0x09) { cur = (cur + 8) & ~7UL; }
            else if (cp == 0x0c || cp == 0x0d) { cur = 0; }
            else { cur += 1; }
        } else {
            if (!in_word) { r.words++; in_word = 1; }
            if (cp >= 0x20) { cur += 1; }
        }
        if (cur > r.max_line) r.max_line = cur;
        i += (size_t)len;
    }
    if (cur > r.max_line) r.max_line = cur;
    return r;
}

wc_count wc_count_str(const unsigned char *s, size_t n) {
    if (is_utf8 < 0) is_utf8 = mode_is_utf8();
    if (is_utf8) return count_utf8(s, n);
    return count_c(s, n);
}

/* flags: bit0=lines(-l), bit1=words(-w), bit2=bytes(-c), bit3=-L; 0=default L W B */
size_t wc_format_flags(char *buf, size_t bufsize, wc_count r, unsigned flags) {
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
