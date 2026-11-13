#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef struct { unsigned long lines, words, bytes; } wc_count;
wc_count count(const unsigned char *, size_t);
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
int main(int argc, char **argv) { (void)argc;
    FILE *c = fopen(argv[1], "rb"), *m = fopen(argv[2], "rb");
    if (!c || !m) return 2;
    char line[16384]; uint8_t buf[8192];
    size_t n = 0, mism = 0;
    while (fgets(line, sizeof line, c)) {
        char *nl = strchr(line, '\n'); if (nl) *nl = '\0';
        size_t len = unesc(line, buf);
        wc_count r = count(buf, len);
        char exp[64]; if (!fgets(exp, sizeof exp, m)) return 2;
        unsigned long el, ew, eb;
        if (sscanf(exp, "%lu %lu %lu", &el, &ew, &eb) != 3) return 2;
        if (r.lines != el || r.words != ew || r.bytes != eb) {
            mism++;
            if (mism <= 20) fprintf(stderr, "MISMATCH line#%zu recon=(%lu %lu %lu) native=(%lu %lu %lu)\n", n, r.lines, r.words, r.bytes, el, ew, eb);
        }
        n++;
    }
    fprintf(stderr, "total=%zu mismatches=%zu\n", n, mism);
    return mism ? 1 : 0;
}
