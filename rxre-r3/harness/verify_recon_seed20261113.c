#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
extern int filenvercmp(const char *, const char *);
static size_t unescape(const char *src, uint8_t out[4096]) {
    size_t o = 0;
    for (size_t i = 0; src[i]; ) {
        if (src[i] == '\\' && src[i+1] == 'x') {
            unsigned v = 0;
            for (int k = 0; k < 2; k++) { char c = src[i+2+k]; v <<= 4;
                if (c >= '0' && c <= '9') v |= (unsigned)(c - '0'); else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10); else v |= (unsigned)(c - 'A' + 10); }
            out[o++] = (uint8_t)v; i += 4;
        } else out[o++] = (uint8_t)src[i++];
    }
    return o;
}
int main(void) {
    FILE *cases = fopen("/tmp/rxre-r3/oracle/cases_seed20261113.txt", "rb");
    FILE *expected = fopen("/tmp/rxre-r3/oracle/matrix_native_20261113.txt", "rb");
    if (!cases || !expected) return 2;
    char line[16384]; uint8_t a[4096], b[4096]; char abuf[4096], bbuf[4096];
    size_t n = 0; size_t mism = 0;
    while (fgets(line, sizeof line, cases)) {
        char *tab = strchr(line, '\t'); *tab = '\0';
        char *a0 = line, *b0 = tab + 1; char *nl = strchr(b0, '\n'); if (nl) *nl = '\0';
        size_t alen = unescape(a0, a); size_t blen = unescape(b0, b);
        memcpy(abuf, a, alen); abuf[alen] = '\0';
        memcpy(bbuf, b, blen); bbuf[blen] = '\0';
        int rc = filenvercmp(abuf, bbuf);
        char exp[64]; if (!fgets(exp, sizeof exp, expected)) { fprintf(stderr, "unexpected EOF\n"); return 2; }
        int expected_rc = atoi(exp);
        if (rc != expected_rc) {
            mism++;
            if (mism <= 20) fprintf(stderr, "MISMATCH a='%s' b='%s' recon=%d native=%d\n", a0, b0, rc, expected_rc);
        }
        n++;
    }
    fprintf(stderr, "total=%zu mismatches=%zu\n", n, mism);
    return mism ? 1 : 0;
}
