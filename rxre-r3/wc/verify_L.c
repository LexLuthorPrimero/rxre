#define _GNU_SOURCE
/* verify_L.c — R3 hito 10: verifica -L (max-line width) de la reconstrucción
 * contra el oráculo sellado (matrix_native_m_utf8.txt, LC_ALL=es_AR.utf8 wc -m).
 * Uso: verify_m <cases-file> <matrix-file> [C|utf8]   (utf8 = fuerza ruta multibyte)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
typedef struct { unsigned long lines, words, bytes, max_line, chars; } wc_count;
wc_count count(const unsigned char *, size_t);
static size_t unescape(const char *src, uint8_t out[4096]) {
    size_t o = 0;
    for (size_t i = 0; src[i]; ) {
        if (src[i] == '\\' && src[i+1] == 'x') {
            unsigned v = 0;
            for (int k = 0; k < 2; k++) { char c = src[i+2+k]; v <<= 4;
                if (c >= '0' && c <= '9') v |= (unsigned)(c - '0');
                else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10);
                else v |= (unsigned)(c - 'A' + 10); }
            out[o++] = (uint8_t)v; i += 4;
        } else out[o++] = (uint8_t)src[i++];
    }
    return o;
}
static int mode = 2; /* 0=C, 1=utf8, 2=auto(from env) */
int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "uso: %s <cases> <matrix> [C|utf8]\n", argv[0]); return 2; }
    if (argc >= 4) mode = (strcmp(argv[3], "C") == 0) ? 0 : 1;
    /* fuerza modo vía entorno que is_utf8 honra */
    if (mode == 0) setenv("LC_ALL", "C", 1);
    else if (mode == 1) setenv("LC_ALL", "es_AR.utf8", 1);
    FILE *cases = fopen(argv[1], "rb");
    FILE *expected = fopen(argv[2], "rb");
    if (!cases || !expected) return 2;
    char line[16384]; uint8_t a[4096]; char abuf[4096];
    size_t n = 0, mism = 0;
    while (fgets(line, sizeof line, cases)) {
        char *nl = strchr(line, '\n'); if (nl) *nl = '\0';
        size_t alen = unescape(line, a);
        memcpy(abuf, a, alen); abuf[alen] = '\0';
        /* modo auto/C/utf8: wc_recon decide por env; tests C y utf8 se fuerzan por env */
        wc_count r = count(a, alen);
        char exp[64];
        if (!fgets(exp, sizeof exp, expected)) { fprintf(stderr, "unexpected EOF after line %zu\n", n); return 2; }
        long expected_l = strtol(exp, NULL, 10);
        if ((long)r.max_line != expected_l) {
            mism++;
            if (mism <= 20)
                fprintf(stderr, "MISMATCH line=%zu recon_max_line=%lu native_max_line=%ld\n", n, r.max_line, expected_l);
        }
        n++;
    }
    fclose(cases); fclose(expected);
    fprintf(stderr, "total=%zu mismatches=%zu\n", n, mism);
    return mism ? 1 : 0;
}
