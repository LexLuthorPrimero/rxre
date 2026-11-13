#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/stat.h>
typedef size_t (*prefixlen_t)(const char *s, int64_t *out_len);
int main(int argc, char **argv) {
    (void)argc;
    int fd = open("/usr/bin/ls", O_RDONLY);
    struct stat st; fstat(fd, &st);
    unsigned char *ls = mmap(NULL, st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    close(fd);
    prefixlen_t prefixlen;
    void *p = ls + 0x4a80;
    memcpy(&prefixlen, &p, sizeof prefixlen);
    size_t rc; int64_t out = -1;
    rc = prefixlen(argv[1], &out);
    printf("prefixlen(\"%s\") = %zu  (*out_len=%lld)\n", argv[1], rc, (long long)out);
    return 0;
}
