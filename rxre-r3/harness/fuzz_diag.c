#define _GNU_SOURCE
/* fuzz_diag — R3 diagnostic only (NOT a sealed artifact).
 * Random byte-pair differential: reconstruction vs native (mmap of /usr/bin/ls 0x4fa0).
 * Alphabet biased to the corpus domain: letters, digits, '.', '~', others incl. high bytes.
 * Seeded PRNG (fixed constant) for reproducibility of the diagnostic run itself.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
#include <unistd.h>
typedef int (*vc_t)(const char *, const char *);
static vc_t native_fn;
extern int filenvercmp(const char *, const char *);

static const unsigned char ALPHA[] = {
    'a','b','c','d','e','A','B','Z','z',
    '0','1','2','9',
    '.','.','.','~','~',
    '-','+','_','%','#','&','!','(',')',
    0x7f, 0x80, 0xff, 0x5c
};
static unsigned long rng_state;
static unsigned long xr(void){ unsigned long x = rng_state; x ^= x<<13; x ^= x>>7; x ^= x<<17; rng_state = x; return x; }
static size_t gen_str(unsigned char *out) {
    size_t maxlen = 1 + (size_t)(xr() % 13);
    size_t n = (size_t)(xr() % (maxlen + 1));
    for (size_t i = 0; i < n; i++) out[i] = ALPHA[xr() % sizeof ALPHA];
    out[n] = 0;
    return n;
}
int main(int argc, char **argv) {
    long total = (argc > 1) ? atol(argv[1]) : 200000; rng_state = (argc > 2) ? (unsigned long)atoll(argv[2]) : 0x9E3779B97F4A7C15ULL;
    int fd = open("/usr/bin/ls", O_RDONLY);
    if (fd < 0) return 2;
    struct stat st; fstat(fd, &st);
    void *ls = mmap(NULL, (size_t)st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    close(fd);
    native_fn = (vc_t)((unsigned char *)ls + 0x4fa0);
    unsigned char buf_a[32], buf_b[32];
    long mism = 0;
    for (long i = 0; i < total; i++) {
        gen_str(buf_a); gen_str(buf_b);
        int rc_native = native_fn((char *)buf_a, (char *)buf_b);
        int rc_recon  = filenvercmp((char *)buf_a, (char *)buf_b);
        if (rc_native != rc_recon) {
            mism++;
            if (mism <= 20) {
                fprintf(stderr, "MISMATCH a='");
                for (unsigned char *p = buf_a; *p; p++) fprintf(stderr, "\\x%02x", *p);
                fprintf(stderr, "' b='");
                for (unsigned char *p = buf_b; *p; p++) fprintf(stderr, "\\x%02x", *p);
                fprintf(stderr, "' recon=%d native=%d\n", rc_recon, rc_native);
            }
        }
    }
    fprintf(stderr, "total=%ld mismatches=%ld\n", total, mism);
    return mism ? 1 : 0;
}
