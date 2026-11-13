/* wc_files0.c — R3 hito 15: soporte para --files0-from en el modelo reconstruido.
 * Uso: wc_files0 <list-path> [default|l]
 *   default: L W B per file + total;  l: líneas por archivo + total
 * Lee la lista file de rutas separadas por NUL; para cada archivo, cuenta con count()
 * (misma ruta de código que la reconstrucción verificada sellada) y acumula.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <signal.h>
#include <setjmp.h>
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

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "uso: %s <list> [default|l]\n", argv[0]); return 2; }
    const char *list_path = argv[1];
    int line_only = (argc >= 3 && strcmp(argv[2], "l") == 0);

    /* read list file completely */
    unsigned char *list = NULL; size_t list_len = 0;
    if (read_file_all(list_path, &list, &list_len) != 0) { fprintf(stderr, "no se puede leer %s\n", list_path); return 2; }

    unsigned long tot_l = 0, tot_w = 0, tot_b = 0;
    int nfail = 0;
    size_t pos = 0;
    while (pos < list_len) {
        size_t start = pos;
        while (pos < list_len && list[pos] != '\0') pos++;
        size_t name_len = pos - start;
        if (pos < list_len) pos++; /* skip NUL */
        if (name_len == 0) continue;
        char *name = strndup((const char *)list + start, name_len);
        unsigned char *content = NULL; size_t n = 0;
        if (read_file_all(name, &content, &n) != 0) {
            fprintf(stderr, "wc: %s: No existe el fichero o el directorio\n", name);
            nfail++;
            free(name);
            continue;
        }
        wc_count r = count(content, n);
        if (line_only) {
            printf("%lu %s\n", r.lines, name);
        } else {
            printf("%lu %lu %lu %s\n", r.lines, r.words, r.bytes, name);
        }
        tot_l += r.lines; tot_w += r.words; tot_b += r.bytes;
        free(content); free(name);
    }
    if (line_only) printf("%lu total\n", tot_l);
    else printf("%lu %lu %lu total\n", tot_l, tot_w, tot_b);
    free(list);
    return nfail ? 1 : 0;
}
