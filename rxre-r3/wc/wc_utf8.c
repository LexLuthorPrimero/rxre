/* wc_utf8.h — subconjunto UTF-8 mínimo (hito 8): decodifica secuencias y clasifica
 * codepoints en el set de espacios Unicode completo conocido (25 cp). */
#include <stddef.h>
#include <string.h>
/* Returns bytes consumed (0 = invalid / treat byte as non-space), and cp if decoded. */
static int utf8_decode(const unsigned char *s, size_t n, unsigned *cp) {
    if (n == 1) { if (s[0] < 0x80) { *cp = s[0]; return 1; } return 0; }
    unsigned b0 = s[0], b1 = n > 1 ? s[1] : 0, b2 = n > 2 ? s[2] : 0, b3 = n > 3 ? s[3] : 0;
    if ((b0 & 0xe0) == 0xc0 && (b1 & 0xc0) == 0x80) { *cp = ((b0 & 0x1f) << 6) | (b1 & 0x3f); return 2; }
    if ((b0 & 0xf0) == 0xe0 && (b1 & 0xc0) == 0x80 && (b2 & 0xc0) == 0x80) { *cp = ((b0 & 0x0f) << 12) | ((b1 & 0x3f) << 6) | (b2 & 0x3f); return 3; }
    if ((b0 & 0xf8) == 0xf0 && (b1 & 0xc0) == 0x80 && (b2 & 0xc0) == 0x80 && (b3 & 0xc0) == 0x80) { *cp = ((b0 & 0x07) << 18) | ((b1 & 0x3f) << 12) | ((b2 & 0x3f) << 6) | (b3 & 0x3f); return 4; }
    return 0;
}
static int is_unicode_space_cp(unsigned cp) {
    switch (cp) {
        case 0x09: case 0x0a: case 0x0b: case 0x0c: case 0x0d: case 0x20: case 0x85:
        case 0xa0: /* NBSP */ case 0x1680: case 0x2000: case 0x2001: case 0x2002:
        case 0x2003: case 0x2004: case 0x2005: case 0x2006: case 0x2007: case 0x2008:
        case 0x2009: case 0x200a: case 0x2028: case 0x2029: case 0x202f: case 0x205f:
        case 0x3000: case 0xfeff:
            return 1;
        default: return 0;
    }
}
