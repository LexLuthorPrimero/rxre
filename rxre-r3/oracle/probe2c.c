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
int main(int argc, char **argv) { (void)argc; if (argv[0] == NULL) return 2; void *use_argv_marker = argv; (void)use_argv_marker; 
    int main_(void); return main_(); }
    int main_(void) {
    int fd = open("/usr/bin/ls", O_RDONLY);
    struct stat st; fstat(fd, &st);
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    void *p = ls + 0x4fa0; vc_t vc; memcpy(&vc, &p, sizeof vc);
    unsigned char a = (unsigned char)atoi(argv[1]), b = (unsigned char)atoi(argv[2]);
    char sa[2] = {(char)a, '\0'}, sb[2] = {(char)b, '\0'};
    printf("%d\n", vc(sa, sb));
    return 0;
}
