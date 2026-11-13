#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
#include <unistd.h>
typedef int (*vc_t)(const char *, const char *);
int main(void) {
    int fd = open("/usr/bin/ls", O_RDONLY);
    struct stat st; fstat(fd, &st);
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ|PROT_EXEC, MAP_PRIVATE, fd, 0);
    close(fd);
    void *p = ls + 0x4fa0; vc_t vc; memcpy(&vc, &p, sizeof vc);
    char a[4] = {'q','\0','q','\0'}, b[4] = {'q','\0','q','\0'};
    for (int c = 1; c < 256; c++)
        for (int d = c + 1; d < 256; d++) {
            a[1] = (unsigned char)c; b[1] = (unsigned char)d;
            printf("%d,%d,%d\n", c, d, vc(a, b));
        }
    return 0;
}
