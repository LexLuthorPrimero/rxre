#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
typedef int (*vc_t)(const char *, const char *);
int main(int argc, char **argv) {
    (void)argc;
    int fd = open("/usr/bin/ls", O_RDONLY);
    struct stat st; fstat(fd, &st);
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ|PROT_EXEC, MAP_PRIVATE, fd, 0);
    void *p = ls + 0x4fa0; vc_t vc; memcpy(&vc, &p, sizeof vc);
    printf("%d\n", vc(argv[1], argv[2]));
    return 0;
}
