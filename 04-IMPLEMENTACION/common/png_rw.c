/* SPDX-License-Identifier: MIT
 *
 * png_rw.c - see png_rw.h for why this is hand-written and what it refuses.
 *
 * Reference: PNG (Portable Network Graphics) Specification, Version 1.2,
 * W3C Recommendation 21 November 2003. Section numbers cited below refer to
 * it. The CRC is the one from section 5.5, computed by zlib's crc32().
 */

#include "png_rw.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

#define PNG_SIG_BYTES 8
static const uint8_t k_sig[PNG_SIG_BYTES] = {137, 80, 78, 71, 13, 10, 26, 10};

/* Section 3.1: every chunk is length(4) type(4) data crc(4), all big-endian. */
struct chunk_hdr {
    uint32_t len;
    char     type[5];
};

static void seterr(char *err, size_t n, const char *fmt, ...)
    __attribute__((format(printf, 3, 4)));

static void seterr(char *err, size_t n, const char *fmt, ...)
{
    va_list ap;
    if (!err || n == 0)
        return;
    va_start(ap, fmt);
    vsnprintf(err, n, fmt, ap);
    va_end(ap);
}

static uint32_t rd_u32be(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] <<  8) |  (uint32_t)p[3];
}

/* ------------------------------------------------------------------------ */
/* Filtering (section 6)                                                     */
/* ------------------------------------------------------------------------ */

/* Paeth predictor, section 6.2.6. Named as in the spec. */
static int paeth(int a, int b, int c)
{
    int p  = a + b - c;
    int pa = p > a ? p - a : a - p;
    int pb = p > b ? p - b : b - p;
    int pc = p > c ? p - c : c - p;

    if (pa <= pb && pa <= pc) return a;
    if (pb <= pc)             return b;
    return c;
}

/*
 * Undo one filtered scanline in place.
 *   cur   : this row, `stride` bytes, filtered
 *   prev  : the row above, `stride` bytes, already unfiltered (NULL on row 0)
 *   bpp   : bytes per complete pixel, rounded down to 1 (section 6)
 */
static int unfilter(uint8_t *cur, const uint8_t *prev, size_t stride,
                    int filter, int bpp, char *err, size_t errlen)
{
    size_t i;

    switch (filter) {
    case 0: /* None */
        return 0;
    case 1: /* Sub */
        for (i = (size_t)bpp; i < stride; i++)
            cur[i] = (uint8_t)(cur[i] + cur[i - (size_t)bpp]);
        return 0;
    case 2: /* Up */
        if (prev)
            for (i = 0; i < stride; i++)
                cur[i] = (uint8_t)(cur[i] + prev[i]);
        return 0;
    case 3: /* Average */
        for (i = 0; i < stride; i++) {
            int a = (i >= (size_t)bpp) ? cur[i - (size_t)bpp] : 0;
            int b = prev ? prev[i] : 0;
            cur[i] = (uint8_t)(cur[i] + ((a + b) >> 1));
        }
        return 0;
    case 4: /* Paeth */
        for (i = 0; i < stride; i++) {
            int a = (i >= (size_t)bpp) ? cur[i - (size_t)bpp] : 0;
            int b = prev ? prev[i] : 0;
            int c = (prev && i >= (size_t)bpp) ? prev[i - (size_t)bpp] : 0;
            cur[i] = (uint8_t)(cur[i] + paeth(a, b, c));
        }
        return 0;
    default:
        seterr(err, errlen,
               "filtro de scanline %d desconocido (solo 0..5 son validos, "
               "seccion 6)", filter);
        return -1;
    }
}

/* ------------------------------------------------------------------------ */
/* Reader                                                                    */
/* ------------------------------------------------------------------------ */

struct palette {
    uint8_t entries[256][3];
    int     n;
    uint8_t alpha[256];
    int     has_alpha;
};

int rx550_png_read(const char *path, rx550_image_t *img, char *err, size_t errlen)
{
    FILE    *f = NULL;
    uint8_t *idat = NULL;
    size_t   idat_len = 0, idat_cap = 0;
    uint8_t *raw = NULL, *out = NULL;
    struct palette pal;
    int      w = 0, h = 0, depth = 0, ctype = 0, interlace = 0;
    int      channels = 0, bpp = 1;
    size_t   stride = 0, need;
    long     fsize;
    int      y, rc = -1, have_ihdr = 0;

    memset(img, 0, sizeof *img);
    memset(&pal, 0, sizeof pal);
    pal.n = -1;

    f = fopen(path, "rb");
    if (!f) {
        seterr(err, errlen, "no se pudo abrir '%s'", path);
        return -1;
    }
    if (fseek(f, 0, SEEK_END) != 0 || (fsize = ftell(f)) < 0) {
        seterr(err, errlen, "no se pudo determinar el tamano de '%s'", path);
        goto out;
    }
    rewind(f);

    /* --- signature (section 5) --- */
    {
        uint8_t sig[PNG_SIG_BYTES];
        if (fread(sig, 1, PNG_SIG_BYTES, f) != PNG_SIG_BYTES) {
            seterr(err, errlen, "'%s': truncado antes de la firma PNG", path);
            goto out;
        }
        if (memcmp(sig, k_sig, PNG_SIG_BYTES) != 0) {
            seterr(err, errlen, "'%s': la firma no es PNG (8 bytes magicos)", path);
            goto out;
        }
    }

    /* --- chunk loop --- */
    for (;;) {
        uint8_t     hb[8];
        struct chunk_hdr ch;
        uint8_t    *data = NULL;
        uint32_t    crc_stored, crc_calc;

        if (fread(hb, 1, 8, f) != 8) break;   /* fin de fichero limpio */
        ch.len = rd_u32be(hb);
        memcpy(ch.type, hb + 4, 4);
        ch.type[4] = '\0';

        /* A chunk length is bounded by the file: a 4 GiB length in a 3 kB file
         * is a corrupt or hostile stream, not a real chunk. */
        if ((long)ch.len > fsize) {
            seterr(err, errlen,
                   "'%s': chunk %s declara %u bytes, mas que el fichero (%ld)",
                   path, ch.type, ch.len, fsize);
            goto out;
        }
        if (ch.len) {
            data = malloc(ch.len);
            if (!data) {
                seterr(err, errlen, "sin memoria para el chunk %s (%u B)",
                       ch.type, ch.len);
                goto out;
            }
            if (fread(data, 1, ch.len, f) != ch.len) {
                seterr(err, errlen, "'%s': chunk %s truncado", path, ch.type);
                free(data);
                goto out;
            }
        }
        {
            uint8_t cb[4];
            if (fread(cb, 1, 4, f) != 4) {
                seterr(err, errlen, "'%s': falta el CRC de %s", path, ch.type);
                free(data);
                goto out;
            }
            crc_stored = rd_u32be(cb);
        }
        /* CRC covers the type field and the data, not the length (section 5.5). */
        crc_calc = (uint32_t)crc32(0L, Z_NULL, 0);
        crc_calc = (uint32_t)crc32(crc_calc, (const Bytef *)ch.type, 4);
        if (ch.len)
            crc_calc = (uint32_t)crc32(crc_calc, (const Bytef *)data, ch.len);
        if (crc_calc != crc_stored) {
            seterr(err, errlen,
                   "'%s': CRC de %s = %08x, el fichero declara %08x. "
                   "El stream esta corrupto; no se decodifica.",
                   path, ch.type, crc_calc, crc_stored);
            free(data);
            goto out;
        }

        if (strcmp(ch.type, "IHDR") == 0) {
            if (ch.len != 13) {
                seterr(err, errlen, "IHDR de %u B, la spec dice 13", ch.len);
                free(data); goto out;
            }
            w         = (int)rd_u32be(data + 0);
            h         = (int)rd_u32be(data + 4);
            depth     = data[8];
            ctype     = data[9];
            interlace = data[12];
            have_ihdr = 1;

            if (interlace != 0) {
                seterr(err, errlen,
                       "'%s': PNG entrelazado (Adam7). Este lector solo "
                       "acepta no entrelazado; hace falta otro lector "
                       "para Adam7.", path);
                free(data); goto out;
            }
            if (depth != 8) {
                seterr(err, errlen,
                       "'%s': profundidad %d bits. Este lector solo acepta 8; "
                       "otra profundidad no se reescala, se rechaza.",
                       path, depth);
                free(data); goto out;
            }
            if (w <= 0 || h <= 0 || (long)w * h > 64L * 1024 * 1024) {
                seterr(err, errlen, "'%s': dimensiones %dx%d no aceptables",
                       path, w, h);
                free(data); goto out;
            }
            switch (ctype) {
            case 0: channels = 1; break;  /* grey */
            case 2: channels = 3; break;  /* RGB  */
            case 3: channels = 1; break;  /* palette */
            case 4: channels = 2; break;  /* grey + alpha */
            case 6: channels = 4; break;  /* RGBA */
            default:
                seterr(err, errlen,
                       "'%s': tipo de color %d no soportado (0,2,3,4,6)",
                       path, ctype);
                free(data); goto out;
            }
            bpp    = channels;              /* depth is 8, so bpp == channels */
            stride = (size_t)w * (size_t)channels;
            free(data);
            continue;
        }

        if (strcmp(ch.type, "PLTE") == 0) {
            if (ch.len % 3 || ch.len == 0 || ch.len > 256 * 3) {
                seterr(err, errlen, "PLTE de %u B invalido (multiplo de 3, 1..768)",
                       ch.len);
                free(data); goto out;
            }
            pal.n = (int)(ch.len / 3);
            for (int i = 0; i < pal.n; i++) {
                pal.entries[i][0] = data[i * 3 + 0];
                pal.entries[i][1] = data[i * 3 + 1];
                pal.entries[i][2] = data[i * 3 + 2];
            }
            free(data); continue;
        }

        if (strcmp(ch.type, "tRNS") == 0) {
            if (ctype == 3) {
                for (uint32_t i = 0; i < ch.len && i < 256; i++)
                    pal.alpha[i] = data[i];
                pal.has_alpha = 1;
            }
            free(data); continue;
        }

        if (strcmp(ch.type, "IDAT") == 0) {
            if (idat_len + ch.len > idat_cap) {
                size_t cap = idat_cap ? idat_cap * 2 : 8192;
                while (cap < idat_len + ch.len) cap *= 2;
                uint8_t *n = realloc(idat, cap);
                if (!n) { free(data); seterr(err, errlen, "sin memoria IDAT"); goto out; }
                idat = n; idat_cap = cap;
            }
            memcpy(idat + idat_len, data, ch.len);
            idat_len += ch.len;
            free(data); continue;
        }

        free(data);   /* PLTE-less chunks we do not need are skipped */

        if (strcmp(ch.type, "IEND") == 0) break;
    }

    if (!have_ihdr) {
        seterr(err, errlen, "'%s': sin IHDR", path);
        goto out;
    }
    if (ctype == 3 && pal.n < 0) {
        seterr(err, errlen, "'%s': tipo de color 3 (palette) sin PLTE", path);
        goto out;
    }
    if (idat_len == 0) {
        seterr(err, errlen, "'%s': sin IDAT, no hay pixeles", path);
        goto out;
    }

    /* --- inflate (section 9) --- */
    need = (stride + 1) * (size_t)h;
    raw  = malloc(need);
    if (!raw) { seterr(err, errlen, "sin memoria para %zu B descomprimidos", need); goto out; }
    {
        uLongf got = (uLongf)need;
        int zrc = uncompress(raw, &got, idat, (uLong)idat_len);
        if (zrc != Z_OK || (size_t)got != need) {
            seterr(err, errlen,
                   "'%s': inflate devolvio %d, %zu de %zu B esperados. "
                   "El stream IDAT no coincide con IHDR.",
                   path, zrc, (size_t)got, need);
            goto out;
        }
    }

    /* --- unfilter + expand to RGBA --- */
    out = malloc((size_t)w * (size_t)h * 4u);
    if (!out) { seterr(err, errlen, "sin memoria para la imagen RGBA"); goto out; }

    for (y = 0; y < h; y++) {
        const uint8_t *row  = raw + (stride + 1) * (size_t)y;
        uint8_t       *dst  = out + (size_t)y * (size_t)w * 4u;
        uint8_t       *work = malloc(stride);
        int            x;

        if (!work) { seterr(err, errlen, "sin memoria por scanline"); goto out; }
        memcpy(work, row + 1, stride);
        if (unfilter(work, y ? raw + (stride + 1) * (size_t)(y - 1) + 1 : NULL,
                     stride, row[0], bpp, err, errlen) != 0) {
            free(work);
            goto out;
        }

        for (x = 0; x < w; x++) {
            const uint8_t *s = work + (size_t)x * (size_t)channels;
            uint8_t       *d = dst + (size_t)x * 4u;

            switch (ctype) {
            case 0: d[0] = d[1] = d[2] = s[0]; d[3] = 255; break;
            case 2: d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = 255; break;
            case 3:
                if (s[0] >= pal.n) {
                    seterr(err, errlen,
                           "'%s': indice de paleta %u fuera de PLTE (%d entradas)",
                           path, s[0], pal.n);
                    free(work); goto out;
                }
                d[0] = pal.entries[s[0]][0];
                d[1] = pal.entries[s[0]][1];
                d[2] = pal.entries[s[0]][2];
                d[3] = pal.has_alpha ? pal.alpha[s[0]] : 255;
                break;
            case 4: d[0] = d[1] = d[2] = s[0]; d[3] = s[1]; break;
            case 6: d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = s[3]; break;
            }
        }
        free(work);
    }

    img->width  = w;
    img->height = h;
    img->stride = (size_t)w * 4u;
    img->px     = out;
    out = NULL;
    snprintf(img->source, sizeof img->source, "%s", path);
    rc = 0;

out:
    if (f) fclose(f);
    free(idat);
    free(raw);
    free(out);
    return rc;
}

void rx550_image_free(rx550_image_t *img)
{
    if (!img)
        return;
    free(img->px);
    img->px = NULL;
    img->width = img->height = 0;
    img->stride = 0;
}

/* ------------------------------------------------------------------------ */
/* Writer                                                                    */
/* ------------------------------------------------------------------------ */

static void put_u32be(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >>  8); p[3] = (uint8_t)(v);
}

static int emit_chunk(FILE *f, const char *type, const uint8_t *data, size_t len)
{
    uint8_t  hb[8], cb[4];
    uint32_t crc;

    put_u32be(hb, (uint32_t)len);
    memcpy(hb + 4, type, 4);
    if (fwrite(hb, 1, 8, f) != 8) return -1;
    if (len && fwrite(data, 1, len, f) != len) return -1;

    crc = (uint32_t)crc32(0L, Z_NULL, 0);
    crc = (uint32_t)crc32(crc, (const Bytef *)type, 4);
    if (len)
        crc = (uint32_t)crc32(crc, (const Bytef *)data, len);
    put_u32be(cb, crc);
    return fwrite(cb, 1, 4, f) == 4 ? 0 : -1;
}

int rx550_png_write(const char *path, const uint8_t *px, int w, int h,
                    char *err, size_t errlen)
{
    FILE    *f = NULL;
    uint8_t *raw = NULL;
    uLongf   bound;
    uint8_t  ihdr[13];
    int      y, rc = -1;
    size_t   stride = (size_t)w * 4u, need;

    if (w <= 0 || h <= 0) {
        seterr(err, errlen, "dimensiones invalidas %dx%d", w, h);
        return -1;
    }
    f = fopen(path, "wb");
    if (!f) { seterr(err, errlen, "no se pudo escribir '%s'", path); return -1; }

    if (fwrite(k_sig, 1, PNG_SIG_BYTES, f) != PNG_SIG_BYTES) {
        seterr(err, errlen, "no se pudo escribir la firma"); goto out;
    }
    put_u32be(ihdr + 0, (uint32_t)w);
    put_u32be(ihdr + 4, (uint32_t)h);
    ihdr[8]  = 8;   /* bit depth  */
    ihdr[9]  = 6;   /* colour type: RGBA */
    ihdr[10] = 0;   /* compression */
    ihdr[11] = 0;   /* filter      */
    ihdr[12] = 0;   /* interlace   */
    if (emit_chunk(f, "IHDR", ihdr, sizeof ihdr) != 0) {
        seterr(err, errlen, "no se pudo escribir IHDR"); goto out;
    }

    /* Filter type 0 (None) on every scanline. The corpus is synthetic and the
     * consumer is a diff tool, not an encoder benchmark; a filter choice here
     * would only change the file size, never the pixels. */
    need = (stride + 1) * (size_t)h;
    raw  = malloc(need);
    if (!raw) { seterr(err, errlen, "sin memoria para el buffer de scanlines"); goto out; }
    for (y = 0; y < h; y++) {
        raw[(stride + 1) * (size_t)y] = 0;
        memcpy(raw + (stride + 1) * (size_t)y + 1,
               px + (size_t)y * stride, stride);
    }

    bound = compressBound((uLong)need);
    {
        uint8_t *z = malloc(bound);
        if (!z) { seterr(err, errlen, "sin memoria para el stream zlib"); goto out; }
        if (compress2(z, &bound, raw, (uLong)need, 6) != Z_OK) {
            seterr(err, errlen, "compress2() fallo");
            free(z); goto out;
        }
        if (emit_chunk(f, "IDAT", z, (size_t)bound) != 0) {
            seterr(err, errlen, "no se pudo escribir IDAT");
            free(z); goto out;
        }
        free(z);
    }
    if (emit_chunk(f, "IEND", NULL, 0) != 0) {
        seterr(err, errlen, "no se pudo escribir IEND"); goto out;
    }
    rc = 0;

out:
    if (f) fclose(f);
    free(raw);
    return rc;
}
