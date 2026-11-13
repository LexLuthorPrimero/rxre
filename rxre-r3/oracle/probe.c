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
static vc_t versioncmp;
int main(int argc, char **argv) {
    const char *path = "/usr/bin/ls";
    int fd = open(path, O_RDONLY);
    struct stat st; fstat(fd, &st);
    unsigned char *ls = mmap(NULL, (size_t)st.st_size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    close(fd);
    void *p = ls + 0x4fa0;
    memcpy(&versioncmp, &p, sizeof versioncmp);
    for (int i = 1; i + 1 < argc; i += 2) {
        int rc = versioncmp(argv[i], argv[i + 1]);
        printf("rc('%s','%s') = %d\n", argv[i], argv[i + 1], rc);
    }
    return 0;
}
