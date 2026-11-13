#define _GNU_SOURCE
/* sort_names.c — R3 hito 12 (black-box): ordena nombres UTF-8 leyéndolos por stdin/archivo,
 * con la reconstrucción filenvercmp verificada sellada. Uso: sort_names <names-file> */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define _GNU_SOURCE
extern int filenvercmp(const char *, const char *);
static int cmp_names(const void *a, const void *b) {
    return filenvercmp(*(const char **)a, *(const char **)b);
}
int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "uso: %s <names>\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { fprintf(stderr, "no open %s\n", argv[1]); return 2; }
    char line[8192]; char *names[100000]; size_t n = 0;
    while (fgets(line, sizeof line, f)) {
        char *nl = strchr(line, '\n'); if (nl) *nl = '\0';
        names[n] = strdup(line); n++;
    }
    fclose(f);
    qsort(names, n, sizeof(char *), cmp_names);
    for (size_t i = 0; i < n; i++) { fputs(names[i], stdout); fputc('\n', stdout); }
    return 0;
}
