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
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    void *p = ls + 0x4fa0; vc_t vc; memcpy(&vc, &p, sizeof vc);
    char a[2] = {'\0','\0'}, b[2] = {'\0','\0'};
    for (int i = 1; i < 128; i++) {
        for (int j = i+1; j < 128; j++) {
            a[0] = (unsigned char)i; b[0] = (unsigned char)j;
            int rc = vc(a, b);
            printf("%d,%d,%d\n", i, j, rc);
        }
    }
    return 0;
}
