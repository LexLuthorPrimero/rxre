/* wc_files0.c — R3 hito 15/16: wc --files0-from + flags L/W/B/M/F combinables.
 * Uso: wc_files0 <list-path> [l] [w] [c] [m] [L]
 *   sin flags: L W B (+ -c equivalente a bytes); flags eligen columnas; misma orden GNU L W M C F.
 * Requiere LC_ALL heredado para seleccionar ruta (C/utf8).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
typedef struct { unsigned long lines, words, bytes, max_line, chars; } wc_count;
wc_count count(const unsigned char *, size_t);
static int read_file_all(const char *path, unsigned char **out, size_t *n) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    size_t cap = 1 << 16, len = 0;
    unsigned char *buf = malloc(cap);
    if (!buf) { fclose(f); return -1; }
    for (;;) {
        if (len == cap) { cap <<= 1; buf = realloc(buf, cap); if (!buf) { fclose(f); return -1; } }
        size_t r = fread(buf + len, 1, cap - len, f);
        if (r == 0) break;
        len += r;
    }
    fclose(f);
    *out = buf; *n = len;
    return 0;
}
static size_t format_cols(char *buf, size_t bufsize, wc_count r, unsigned long flags) {
    if (flags == 0) flags = 1 | 2 | 4;
    int out[5] = { !!(flags & 1), !!(flags & 2), !!(flags & 16), !!(flags & 4), !!(flags & 8) };
    unsigned long vals[5] = { r.lines, r.words, r.chars, r.bytes, r.max_line };
    size_t o = 0; int first = 1;
    for (int k = 0; k < 5; k++) {
        if (!out[k]) continue;
        if (!first) { if (o + 1 < bufsize) buf[o++] = ' '; }
        first = 0;
        char tmp[24]; int t = 0; unsigned long v = vals[k];
        if (v == 0) tmp[t++] = '0';
        while (v) { tmp[t++] = (char)('0' + (v % 10)); v /= 10; }
        while (t && o + 1 < bufsize) buf[o++] = tmp[--t];
    }
    if (o < bufsize) buf[o] = '\0';
    return o;
}
int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "uso: %s <list> [l] [w] [c] [m] [L]\n", argv[0]); return 2; }
    const char *list_path = argv[1];
    unsigned long flags = 0;
    for (int i = 2; i < argc; i++) {
        const char *a = argv[i];
        if      (!strcmp(a, "l")) flags |= 1;
        else if (!strcmp(a, "w")) flags |= 2;
        else if (!strcmp(a, "c")) flags |= 4;
        else if (!strcmp(a, "L")) flags |= 8;
        else if (!strcmp(a, "m")) flags |= 16;
        else { fprintf(stderr, "flag desconocido '%s'\n", a); return 2; }
    }
    unsigned char *list = NULL; size_t list_len = 0;
    if (read_file_all(list_path, &list, &list_len) != 0) { fprintf(stderr, "no se puede abrir %s\n", list_path); return 2; }
    unsigned long tot_l = 0, tot_w = 0, tot_b = 0, tot_m = 0, tot_L = 0;
    int nfail = 0;
    size_t pos = 0;
    while (pos < list_len) {
        size_t start = pos;
        while (pos < list_len && list[pos] != '\0') pos++;
        size_t nlen = pos - start;
        if (pos < list_len) pos++;
        if (nlen == 0) continue;
        char *name = strndup((const char *)list + start, nlen);
        unsigned char *content = NULL; size_t n = 0;
        if (read_file_all(name, &content, &n) != 0) {
            fprintf(stderr, "wc: %s: No existe el fichero o el directorio\n", name);
            nfail++; free(name); continue;
        }
        wc_count r = count(content, n);
        char out[256]; format_cols(out, sizeof out, r, flags);
        printf("%s %s\n", out, name);
        tot_l += r.lines; tot_w += r.words; tot_b += r.bytes; tot_m += r.chars; if (r.max_line > tot_L) tot_L = r.max_line;
        free(content); free(name);
    }
    wc_count tot = { tot_l, tot_w, tot_b, tot_L, tot_m };
    char out[256]; format_cols(out, sizeof out, tot, flags);
    printf("%s total\n", out);
    free(list);
    return nfail ? 1 : 0;
}
