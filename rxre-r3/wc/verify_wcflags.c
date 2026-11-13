#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef struct { unsigned long lines, words, bytes, max_line; } wc_count;
wc_count count(const unsigned char *, size_t);
size_t wc_format(char *, size_t, wc_count, unsigned);
static size_t unesc(const char *src, uint8_t out[8192]) {
    size_t o = 0;
    for (size_t i = 0; src[i]; ) {
        if (src[i] == '\\' && src[i+1] == 'x') {
            unsigned v = 0;
            for (int k = 0; k < 2; k++) { char c = src[i+2+k]; v <<= 4;
                if (c >= '0' && c <= '9') v |= (unsigned)(c - '0'); else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10); }
            out[o++] = (uint8_t)v; i += 4;
        } else out[o++] = (uint8_t)src[i++];
    }
    return o;
}
static unsigned parse_flags(const char *f, size_t len) {
    unsigned bits = 0; int i = 0;
    while (i < (int)len) {
        if (f[i] == ' ') { i++; continue; }
        if (f[i] == '-') { i++;
            while (i < (int)len && f[i] != ' ') {
                if (f[i] == 'l') bits |= 1; else if (f[i] == 'w') bits |= 2; else if (f[i] == 'c') bits |= 4; else if (f[i] == 'L') bits |= 8;
                i++;
            }
        } else i++;
    }
    return bits;
}
int main(int argc, char **argv) {
    (void)argc;
    FILE *c = fopen(argv[1], "rb"), *m = fopen(argv[2], "rb");
    if (!c || !m) return 2;
    char line[16384], exp[256], got[256];
    uint8_t buf[8192];
    size_t n = 0, mism = 0;
    while (fgets(line, sizeof line, c)) {
        char *tab = strchr(line, '\t'); if (!tab) return 2; *tab = '\0';
        size_t flen = (size_t)(tab - line);
        char *nl = strchr(tab + 1, '\n'); if (nl) *nl = '\0';
        size_t len = unesc(tab + 1, buf);
        unsigned bits = parse_flags(line, flen);
        wc_count r = count(buf, len);
        size_t o = wc_format(got, sizeof got, r, bits); (void)o;
        if (!fgets(exp, sizeof exp, m)) return 2;
        char *e = exp; size_t ei;
        for (ei = 0; e[ei]; ei++) e[ei] = (char)e[ei];
        /* normalize: collapse whitespace / trim trailing newline */
        char expn[256], gotn[256]; size_t j = 0; int last_space = 0;
        for (size_t i2 = 0; exp[i2]; i2++) {
            if (exp[i2] == ' ' || exp[i2] == '\t') { if (!last_space) expn[j++] = ' '; last_space = 1; }
            else if (exp[i2] == '\n') { if (last_space) expn[j++] = ' '; last_space = 0; }
            else { expn[j++] = exp[i2]; last_space = 0; }
        }
        j = 0; last_space = 0;
        for (size_t i2 = 0; got[i2]; i2++) {
            if (got[i2] == ' ' || got[i2] == '\t') { if (!last_space) gotn[j++] = ' '; last_space = 1; }
            else { gotn[j++] = got[i2]; last_space = 0; }
        }
        gotn[j] = '\0'; expn[j] = '\0';
        /* strip trailing space in both */
        size_t gj = strlen(gotn); while (gj && gotn[gj-1] == ' ') gotn[--gj] = '\0';
        size_t ej = strlen(expn); while (ej && expn[ej-1] == ' ') expn[--ej] = '\0';
        if (strcmp(gotn, expn) != 0) {
            mism++;
            if (mism <= 20) fprintf(stderr, "MISMATCH line#%zu flags='%s' recon='%s' native='%s'\n", n, line, gotn, expn);
        }
        n++;
    }
    fprintf(stderr, "total=%zu mismatches=%zu\n", n, mism);
    return mism ? 1 : 0;
}
