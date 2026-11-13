/* blackbox — genera la lista ordenada según filenvercmp (tie: strcmp) para un set de nombres. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern int filenvercmp(const char *, const char *);
static const char *arr[4096];
static int cmp_fn(const void *pa, const void *pb) {
    const char *a = *(const char **)pa, *b = *(const char **)pb;
    int rc = filenvercmp(a, b);
    if (rc != 0) return rc < 0 ? -1 : (rc > 0 ? 1 : 0);
    return strcmp(a, b);
}
int main(int argc, char **argv) {
    int n = argc - 1;
    if (n > 4096) return 2;
    for (int i = 0; i < n; i++) arr[i] = argv[i + 1];
    qsort(arr, (size_t)n, sizeof(char *), cmp_fn);
    for (int i = 0; i < n; i++) puts(arr[i]);
    return 0;
}
