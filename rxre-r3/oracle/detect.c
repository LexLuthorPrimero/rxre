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
    unsigned char s[2] = {'\0','\0'}; char c;
    /* enumerate bytes 32..126 to classify by rc(c,'a') sign:
       negative rc -> char-before-'a'; zero rc -> equal; positive rc -> after */
    for (c = 32; c <= 126; c++) { s[0] = (unsigned char)c; int r = vc((char*)s, "a"); (void)r; }
    printf("ok\n");
    return 0;
}
