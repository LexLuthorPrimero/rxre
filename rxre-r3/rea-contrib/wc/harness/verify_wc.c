/* verify_wc — RXRE cleanroom — verificador paramétrico para wc
 * Uso: verify_wc <cases.txt> <matrix.txt> [mode]
 *   mode: "C" | "utf8" — fuerza la ruta de clasificación; si se omite, se detecta de LC_ALL/LANG.
 * Corpus: "<flags?>\t<content-escapado>" o solo "<content-escapado>".
 * Matrix: salida deseada (cualquier padding; comparación por secuencia de enteros).
 * Exit 0 si 0 divergencias, 1 en otro caso.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
typedef struct { unsigned long lines, words, bytes, max_line; } wc_count;
wc_count wc_count_str(const unsigned char *, size_t);
size_t wc_format_flags(char *, size_t, wc_count, unsigned);

static int g_forced_mode = -1;  /* -1 auto, 0 C, 1 utf8 */
#define MODE_C   0
#define MODE_UTF8 1

static size_t unesc(const char *src, uint8_t out[8192]) {
    size_t o = 0;
    for (size_t i = 0; src[i]; ) {
        if (src[i] == '\\' && src[i+1] == 'x') {
            unsigned v = 0;
            for (int k = 0; k < 2; k++) {
                char c = src[i+2+k]; v <<= 4;
                if (c >= '0' && c <= '9') v |= (unsigned)(c - '0');
                else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10);
                else if (c >= 'A' && c <= 'F') v |= (unsigned)(c - 'A' + 10);
            }
            out[o++] = (uint8_t)v; i += 4;
        } else out[o++] = (uint8_t)src[i++];
    }
    return o;
}
static unsigned parse_flags(const char *f, size_t len) {
    unsigned bits = 0; int i = 0;
    while (i < (int)len) {
        if (f[i] == ' ' || f[i] == '\t') { i++; continue; }
        if (f[i] == '-') {
            i++;
            while (i < (int)len && f[i] != ' ' && f[i] != '\t') {
                if (f[i] == 'l') bits |= 1;
                else if (f[i] == 'w') bits |= 2;
                else if (f[i] == 'c') bits |= 4;
                else if (f[i] == 'L') bits |= 8;
                i++;
            }
        } else i++;
    }
    return bits;
}
static size_t extract_ints(const char *src, unsigned long out[]) {
    size_t n = 0; const char *p = src;
    while (*p && n < 8) {
        if (*p >= '0' && *p <= '9') {
            unsigned long v = 0;
            while (*p >= '0' && *p <= '9') { v = v * 10 + (unsigned long)(*p - '0'); p++; }
            out[n++] = v;
        } else p++;
    }
    return n;
}
int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "uso: verify_wc <cases> <matrix> [C|utf8]\n"); return 2; }
    if (argc >= 4) {
        if (!strcmp(argv[3], "C") || !strcmp(argv[3], "c")) g_forced_mode = MODE_C;
        else if (!strcmp(argv[3], "utf8") || !strcmp(argv[3], "UTF-8")) g_forced_mode = MODE_UTF8;
        else { fprintf(stderr, "modo desconocido '%s' (usa C|utf8)\n", argv[3]); return 2; }
    }
    FILE *c = fopen(argv[1], "rb"), *m = fopen(argv[2], "rb");
    if (!c || !m) { fprintf(stderr, "no se puede abrir cases/matrix\n"); return 2; }
    char line[16384], exp[256], got[256];
    uint8_t buf[8192];
    size_t n = 0, mism = 0;
    int line_no = 0;
    while (fgets(line, sizeof line, c)) {
        line_no++;
        char *nl = strchr(line, '\n'); if (nl) *nl = '\0';
        char *content = line;
        size_t flags_len = 0;
        char *tab = strchr(line, '\t');
        if (tab) { *tab = '\0'; flags_len = (size_t)(tab - line); content = tab + 1; }
        size_t len = unesc(content, buf);
        unsigned bits = flags_len ? parse_flags(line, flags_len) : 0;
        /* forzar modo si se pasó argumento: correr con env propia */
        if (g_forced_mode >= 0) {
            /* hack: forzar LC_ALL via setenv antes de la primera llamada a la dectetora */
            setenv("LC_ALL", g_forced_mode == MODE_C ? "C" : "es_AR.utf8", 1);
        }
        wc_count r = wc_count_str(buf, len);
        size_t o = wc_format_flags(got, sizeof got, r, bits); (void)o;
        if (!fgets(exp, sizeof exp, m)) { fprintf(stderr, "EOF en matrix\n"); return 2; }
        char expn[512] = {0};
        size_t w = 0; int in_ws = 0;
        for (size_t i = 0; exp[i]; i++) {
            if (exp[i] == ' ' || exp[i] == '\t' || exp[i] == '\n') { if (!in_ws && w) expn[w++] = ' '; in_ws = 1; }
            else { expn[w++] = exp[i]; in_ws = 0; }
        }
        if (w && expn[w-1] == ' ') w--;
        expn[w] = '\0';
        unsigned long gi[8], ei[8];
        size_t gn = extract_ints(got, gi), en = extract_ints(expn, ei);
        int bad = gn != en;
        if (!bad) for (size_t i = 0; i < gn; i++) if (gi[i] != ei[i]) { bad = 1; break; }
        if (bad) {
            mism++;
            if (mism <= 10) fprintf(stderr, "MISMATCH line#%d recon='%s' native='%s'\n", line_no, got, expn);
        }
        n++;
    }
    fprintf(stderr, "total=%zu mismatches=%zu\n", n, mism);
    return mism ? 1 : 0;
}
