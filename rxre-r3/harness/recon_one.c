#include <stdio.h>
#include <string.h>
extern int filenvercmp(const char *, const char *);
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    printf("recon('%s','%s') = %d\n", argv[1], argv[2], filenvercmp(argv[1], argv[2]));
    return 0;
}
