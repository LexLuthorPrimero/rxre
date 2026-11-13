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
volatile int base_ready = 0;
int main(void) {
    const char *path = "/usr/bin/ls";
    int fd = open(path, O_RDONLY);
    struct stat st; fstat(fd, &st);
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    close(fd);
    void *p = ls + 0x4fa0; vc_t vc; memcpy(&vc, &p, sizeof vc);
    base_ready = 1;
    int r = vc(getenv("A"), getenv("B"));
    printf("rc=%d\n", r);
    return 0;
}
