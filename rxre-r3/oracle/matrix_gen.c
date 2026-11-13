/* matrix_gen.c — oráculo independiente desde /usr/bin/ls (vaddr 0x4fa0) para R3.
 * Lee cases en formato escapeado "a<TAB>b\n", escribe "%d\n" por caso. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include <signal.h>
#include <setjmp.h>

typedef int (*versioncmp_t)(const char *, const char *);

static versioncmp_t versioncmp;
static sigjmp_buf jb;
static volatile sig_atomic_t crash;

static void on_sig(int s) { (void)s; crash = 1; siglongjmp(jb, 1); }

/* decodifica "\\xHH" y bytes planos; retorna longitud */
static size_t unescape(const char *src, uint8_t out[4096]) {
    size_t o = 0;
    for (size_t i = 0; src[i]; ) {
        if (src[i] == '\\' && src[i+1] == 'x') {
            unsigned v = 0;
            for (int k = 0; k < 2; k++) {
                char c = src[i+2+k];
                v <<= 4;
                if (c >= '0' && c <= '9') v |= (unsigned)(c - '0');
                else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10);
                else if (c >= 'A' && c <= 'F') v |= (unsigned)(c - 'A' + 10);
                else { fprintf(stderr, "bad escape %s\n", src); exit(2); }
            }
            out[o++] = (uint8_t)v;
            i += 4;
        } else {
            out[o++] = (uint8_t)src[i++];
        }
    }
    return o;
}

int main(int argc, char **argv) { (void)argc; (void)argv;
    const char *ls_path = "/usr/bin/ls";
    const char *cases_path = (argc > 1) ? argv[1] : "cases.txt";
    const char *out_path = (argc > 2) ? argv[2] : "matrix_native.txt";
    int fd = open(ls_path, O_RDONLY);
    if (fd < 0) { perror("open ls"); return 2; }
    struct stat st; if (fstat(fd, &st) != 0) { perror("fstat"); return 2; }
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    close(fd);
    if (ls == MAP_FAILED) { perror("mmap"); return 2; }
    {
        void *p = ls + 0x4fa0;
        memcpy(&versioncmp, &p, sizeof versioncmp);
    }

    FILE *in = fopen(cases_path, "rb"), *out = fopen(out_path, "wb");
    if (!in || !out) { perror("fopen"); return 2; }
    char line[16384];
    uint8_t a[4096], b[4096];
    char abuf[4096], bbuf[4096];
    line[0] = '\0';
    size_t nlines = 0;
    while (fgets(line, sizeof line, in)) {
        char *tab = strchr(line, '\t');
        if (!tab) { fprintf(stderr, "bad case line %zu\n", nlines); return 2; }
        *tab = '\0';
        char *astart = line, *bstart = tab + 1;
        char *nl = strchr(bstart, '\n'); if (nl) *nl = '\0';
        size_t alen = unescape(astart, a);
        size_t blen = unescape(bstart, b);
        memcpy(abuf, a, alen); abuf[alen] = '\0';
        memcpy(bbuf, b, blen); bbuf[blen] = '\0';
        a[0] = 0; b[0] = 0;
        if (crash == 0) { signal(SIGSEGV, on_sig); signal(SIGILL, on_sig); signal(SIGABRT, on_sig); }
        crash = 0;
        if (sigsetjmp(jb, 1) == 0) {
            int rc = versioncmp(abuf, bbuf);
            fprintf(out, "%d\n", rc);
        } else {
            fprintf(out, "CRASH\n");
        }
        nlines++;
    }
    fprintf(stderr, "cases=%zu\n", nlines);
    fclose(in); fclose(out);
    return 0;
}
