#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
typedef int (*vc_t)(const char *, const char *);
static vc_t versioncmp;
int main(int argc, char **argv) {
    (void)argc;
    int fd = open("/usr/bin/ls", O_RDONLY);
    struct stat st; fstat(fd, &st);
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    void *p = ls + 0x4fa0;
    memcpy(&versioncmp, &p, sizeof versioncmp);
    unsigned char a = (unsigned char)atoi(argv[1]), b = (unsigned char)atoi(argv[2]);
    char sa[2] = {(char)a, '\0'}, sb[2] = {(char)b, '\0'};
    printf("%d\n", versioncmp(sa, sb));
    return 0;
}
