/* SPDX-License-Identifier: MIT
 *
 * test_hardware_bc3.c -- what does the Polaris 12 TEXTURE UNIT actually do?
 *
 * THE QUESTION (AD-12)
 *   The Microsoft Direct3D 9 "Textures with Alpha Channels (DXT4/DXT5)" document
 *   writes the BC3 alpha interpolation with explicit rounding:
 *
 *       a0 >  a1 : a[i] = ((8-i)*a0 + (i-1)*a1 + 3) / 7,  i = 2..7
 *       a0 <= a1 : a[i] = ((6-i)*a0 + (i-1)*a1 + 2) / 5,  i = 2..5
 *       a0 <= a1 : a[6] = 0, a[7] = 255
 *
 *   bcdec v0.985 truncates instead -- no +3, no +2. AD-11 followed the
 *   documentation, which settles the TEXT. It does not settle the HARDWARE, and
 *   this project ships an ENCODER whose consumer is that hardware: if the
 *   Polaris 12 texture unit truncates, every block this codec emits is decoded
 *   by the RX 550 differently from what rx550_decompress_block() predicts, and
 *   the discrepancy would be baked into the block payload rather than into a
 *   report. RX550-FIRST makes hardware behaviour the criterion, so measure it.
 *
 * THE METHOD -- no shader, no quad, no quad at all
 *   A DXT5-compressed texture can be attached directly as an FBO colour
 *   attachment. glReadPixels from that FBO forces the hardware texture unit to
 *   decompress the blocks and return RGBA8. Nothing is shaded, so the value that
 *   comes back is the SAMPLE R output itself, with no shader arithmetic and no
 *   rounding of our own. glDrawArrays is never called.
 *
 *   This deliberately avoids the Vulkan compute path, which cannot run on this
 *   host at all: vkCreateComputePipelines segfaults inside both
 *   libvulkan_radeon.so and libvulkan_lvp.so with an empty shader and an empty
 *   pipeline layout. OpenGL on radeonsi does not go through that path.
 *
 * RUN IT ON THE DISCRETE GPU
 *     DRI_PRIME=1 ./test_hardware_bc3
 *   MESA_LOADER_DRIVER_OVERRIDE=radeonsi does NOT work here ("glx: failed to
 *   create dri3 screen"). DRI_PRIME=1 is the one that yields a context whose
 *   GL_RENDERER contains "radeonsi, polaris12". The test refuses to report
 *   numbers from any other context; see SELF-VALIDATION 1.
 *
 *   A context is made current on a 1x1 InputOutput window that is never mapped,
 *   through the legacy GLX 1.2 path (glXChooseVisual + glXCreateContext). The
 *   FBConfig path was tried first and does not work on this host: both
 *   X_GLXCreatePbuffer and X_GLXCreateNewContext fail with GLXBadFBConfig,
 *   because the X server's GLX screen belongs to the Intel iGPU that owns the
 *   physical display. Everything here is rendered into an FBO, so the window is
 *   never shown, never mapped and never drawn to.
 *
 * COVERAGE -- exhaustive, not sampled
 *   All 256 x 256 = 65536 (a0, a1) endpoint pairs, all 8 index codes, 16 texels
 *   per block => 1,048,576 hardware observations. Texel p of every block carries
 *   alpha index p % 8, so one block yields all eight index codes at once.
 *
 * SELF-VALIDATION BEFORE ANY COMPARISON
 *   Agreement with a prediction is worthless if the measurement path is broken,
 *   and "0 discrepancies" is exactly what two equally-wrong implementations
 *   produce. Four checks run first, none of which reference the ramp:
 *     1. GL_RENDERER must contain "RX 550", else abort -- on an Intel context
 *        every number below would be the wrong GPU's sampler;
 *     2. GL_EXT_texture_compression_s3tc must be present, else the upload is
 *        not DXT5 at all;
 *     3. the FBO must report GL_FRAMEBUFFER_COMPLETE;
 *     4. indices 0 and 1 must decode to exactly a0 and a1. Those two entries
 *        involve no interpolation, so they test the path itself. If they fail,
 *        nothing after this point means anything.
 *   Colour is forced to black in every block so the RGB channels double as a
 *   check that the texels being read are the texels that were uploaded.
 *
 * WHY NO GL HEADERS
 *   /usr/include/GL is empty and pkg-config finds no "gl" here, so there are no
 *   real GL headers to include and the declarations below are hand-written. That
 *   risk is much smaller than the equivalent Vulkan case, for a specific reason:
 *   no structure layout is ever passed to the GL layer, and the one structure
 *   that is read (XVisualInfo) is only read at offsets 0 and 20, both stable.
 *   Every wrong enum surfaces through glGetError rather than silently corrupting
 *   memory.
 *
 * EXIT
 *   0  hardware matches the ROUNDING prediction   (AD-11 confirmed on hardware)
 *   1  hardware matches the TRUNCATION prediction (AD-11 refuted on hardware)
 *   2  hardware matches neither                  (unclassified; reported, not guessed)
 *   3  the measurement could not be set up
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* ========================================================================== */
/* Minimal GL / GLX / Xlib surface. See "WHY NO GL HEADERS" above.           */
/* ========================================================================== */

typedef unsigned int   GLenum;
typedef unsigned char  GLboolean;
typedef unsigned int   GLbitfield;
typedef unsigned int   GLuint;
typedef int            GLint;
typedef int            GLsizei;
typedef int            GLintptr;
typedef float          GLfloat;
typedef void           GLvoid;
typedef struct _XDisplay Display;
typedef unsigned long  Window;
typedef unsigned long  VisualID;

#define GL_NO_ERROR                       0
#define GL_FALSE                          0
#define GL_TRUE                           1
#define GL_TEXTURE_2D                     0x0DE1
#define GL_RGBA                           0x1908
#define GL_UNSIGNED_BYTE                  0x1401
#define GL_UNPACK_ALIGNMENT               0x0CF5
#define GL_TEXTURE_MIN_FILTER             0x2801
#define GL_TEXTURE_MAG_FILTER             0x2800
#define GL_NEAREST                        0x2600
#define GL_COLOR_BUFFER_BIT               0x00004000
#define GL_VERSION                        0x1F02
#define GL_RENDERER                       0x1F01
#define GL_VENDOR                         0x1F00
#define GL_EXTENSIONS                     0x1F03
#define GL_FRAMEBUFFER                    0x8D40
#define GL_COLOR_ATTACHMENT0              0x8CE0
#define GL_FRAMEBUFFER_COMPLETE           0x8CD5
#define GL_MAX_TEXTURE_SIZE               0x0D33
#define GL_COMPRESSED_RGBA_S3TC_DXT5_EXT  0x80F3

#define GLX_RGBA                          4
#define GLX_RED_SIZE                      8
#define GLX_GREEN_SIZE                    9
#define GLX_BLUE_SIZE                     10
#define GLX_ALPHA_SIZE                    11
#define GLX_DEPTH_SIZE                    12
#define GLX_DEPTH_SIZE_ARB                0x8056

#define CWBorderPixel                     (1L << 3)
#define InputOutput                       1

/* XVisualInfo, used only to read .visual (offset 0) and .depth (offset 20). */
typedef struct {
    void*        visual;        /*  0 */
    VisualID     visualid;      /*  8 */
    int          screen;        /* 16 */
    int          depth;         /* 20 */
    int          class_;
    unsigned long red_mask, green_mask, blue_mask;
    int          colormap_size;
    int          bits_per_rgb;
} XVisualInfoT;

/* GL 1.1 / GLX are linked directly against the versioned shared objects, exactly
 * as any GL program is. An earlier revision dlopen()ed libGL instead; with
 * dlopen, glXChooseVisual returned a perfectly good visual (visualid 0x1ef,
 * depth 24, TrueColor) and glXCreateContext then failed on it for both direct
 * and indirect rendering. Linking is what glxgears does and it works. */
extern Display *XOpenDisplay(const char*);
extern int      XDefaultScreen(Display*);
extern Window   XDefaultRootWindow(Display*, int);
extern Window   XCreateSimpleWindow(Display*, Window, int, int,
                                    unsigned, unsigned, unsigned, unsigned,
                                    unsigned, void*, unsigned long, void*);
extern void    *glXChooseVisual(Display*, int, int*);
extern void    *glXCreateContext(Display*, void*, void*, int);
extern int      glXMakeCurrent(Display*, Window, void*);
extern void     glXDestroyContext(Display*, void*);
extern void    *glXGetProcAddressARB(const unsigned char*);

extern const unsigned char *glGetString(GLenum);
extern GLenum   glGetError(void);
extern void     glPixelStorei(GLenum, GLint);

/* GL 2.0+ entry points have no exported symbol; they come from the extension
 * mechanism, which is per-context, so they must be fetched at run time. */
static void     (*glGetIntegerv)(GLenum, GLint*);
static void     (*glViewport)(GLint, GLint, GLsizei, GLsizei);
static void     (*glClearColor)(GLfloat, GLfloat, GLfloat, GLfloat);
static void     (*glClear)(GLbitfield);
static void     (*glGenTextures)(GLsizei, GLuint*);
static void     (*glBindTexture)(GLenum, GLuint);
static void     (*glTexParameteri)(GLenum, GLenum, GLint);
static void     (*glCompressedTexImage2D)(GLenum, GLint, GLenum, GLsizei, GLsizei,
                                          GLint, GLsizei, const GLvoid*);
static void     (*glGenFramebuffers)(GLsizei, GLuint*);
static void     (*glBindFramebuffer)(GLenum, GLuint);
static void     (*glFramebufferTexture2D)(GLenum, GLenum, GLenum, GLuint, GLint);
static GLenum   (*glCheckFramebufferStatus)(GLenum);
static void     (*glDeleteFramebuffers)(GLsizei, const GLuint*);
static void     (*glDeleteTextures)(GLsizei, const GLuint*);
static void     (*glReadPixels)(GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void*);

/* ========================================================================== */

#define BLOCK_BYTES 16
#define BLOCK_PX    16

/* Side of one chunk in blocks: 64 -> 256x256 texels, 4096 endpoint pairs, so
 * the 65536 pairs are covered in 16 chunks. */
#define CHUNK_BLOCKS 64
#define CHUNK_PX     (CHUNK_BLOCKS * 4)

/* ---- the two hypotheses, written out independently ------------------------ */
static uint8_t pred_round(uint8_t a0, uint8_t a1, unsigned i)
{
    if (i == 0) return a0;
    if (i == 1) return a1;
    if (a0 > a1)
        return (uint8_t)(((8 - i) * (int)a0 + (i - 1) * (int)a1 + 3) / 7);
    if (i >= 6) return (i == 6) ? 0 : 255;
    return (uint8_t)(((6 - i) * (int)a0 + (i - 1) * (int)a1 + 2) / 5);
}
static uint8_t pred_trunc(uint8_t a0, uint8_t a1, unsigned i)
{
    if (i == 0) return a0;
    if (i == 1) return a1;
    if (a0 > a1)
        return (uint8_t)(((8 - i) * (int)a0 + (i - 1) * (int)a1) / 7);
    if (i >= 6) return (i == 6) ? 0 : 255;
    return (uint8_t)(((6 - i) * (int)a0 + (i - 1) * (int)a1) / 5);
}

/* One DXT5 block. Colour is forced to black (c0 = c1 = 0, all colour indices 0)
 * so the RGB channels are a control and only alpha carries information. */
static void make_block(uint8_t a0, uint8_t a1, uint8_t *blk)
{
    unsigned p;
    memset(blk, 0, BLOCK_BYTES);
    blk[0] = a0;
    blk[1] = a1;
    for (p = 0; p < BLOCK_PX; p++) {
        unsigned idx = p % 8u;              /* covers all eight index codes */
        unsigned bit = 3u * p;
        blk[2 + (bit >> 3)] |= (uint8_t)((idx << (bit & 7u)) & 0xFFu);
        if ((bit & 7u) > 5u)
            blk[2 + (bit >> 3) + 1] |= (uint8_t)(idx >> (8u - (bit & 7u)));
    }
}

int main(int argc, char **argv)
{
    Display *dpy;
    void *ctx = NULL;
    Window win = 0;
    GLuint tex = 0, fbo = 0;
    GLint maxtex = 0;
    const char *rend;
    uint8_t *blocks, *px;
    uint64_t obs = 0, only_round = 0, only_trunc = 0, agree_both = 0, neither = 0;
    uint64_t endpoint_ok = 0, endpoint_bad = 0;
    unsigned chunk;
    int rc = 3;

    (void)argc; (void)argv;

    printf("=== AD-12: comportamiento del sampler BC3 del Polaris 12 ===\n\n");


    dpy = XOpenDisplay(NULL);
    if (!dpy) { fprintf(stderr, "FATAL: XOpenDisplay fallo (falta DISPLAY)\n"); return 3; }

    {   /* Exactly the attribute list glxgears uses. Asking for ALPHA_SIZE=8 and
         * DEPTH_SIZE=0 is stricter and glXChooseVisual then returns a visual for
         * which no context can be created on this server. */
        int fa[] = { GLX_RGBA,
                    GLX_RED_SIZE, 1, GLX_GREEN_SIZE, 1, GLX_BLUE_SIZE, 1,
                    0 };
        XVisualInfoT *vi = (XVisualInfoT*)glXChooseVisual(dpy, XDefaultScreen(dpy), fa);
        if (!vi) { fprintf(stderr, "FATAL: glXChooseVisual devolvio NULL\n"); return 3; }
        ctx = glXCreateContext(dpy, vi->visual, NULL, 1 /* direct */);
        if (!ctx) ctx = glXCreateContext(dpy, vi->visual, NULL, 0 /* indirect */);
        if (!ctx) { fprintf(stderr, "FATAL: glXCreateContext devolvio NULL "
                                   "(directo e indirecto)\n"); return 3; }
        win = XCreateSimpleWindow(dpy, XDefaultRootWindow(dpy, XDefaultScreen(dpy)),
                                  0, 0, 16, 16, 0, (unsigned)vi->depth,
                                  InputOutput, vi->visual, CWBorderPixel, NULL);
    }
    if (!glXMakeCurrent(dpy, win, ctx)) {
        fprintf(stderr, "FATAL: glXMakeCurrent fallo\n"); return 3;
    }

#define P(v, n) do { *(void**)&v = glXGetProcAddressARB((const unsigned char*)(n)); \
                     if (!v) { fprintf(stderr, "FATAL: glXGetProcAddressARB(%s) fallo\n", n); \
                               exit(3); } } while (0)
    P(glGetIntegerv, "glGetIntegerv");
    P(glViewport, "glViewport");
    P(glClearColor, "glClearColor");
    P(glClear, "glClear");
    P(glGenTextures, "glGenTextures");
    P(glBindTexture, "glBindTexture");
    P(glTexParameteri, "glTexParameteri");
    P(glCompressedTexImage2D, "glCompressedTexImage2D");
    P(glGenFramebuffers, "glGenFramebuffers");
    P(glBindFramebuffer, "glBindFramebuffer");
    P(glFramebufferTexture2D, "glFramebufferTexture2D");
    P(glCheckFramebufferStatus, "glCheckFramebufferStatus");
    P(glDeleteFramebuffers, "glDeleteFramebuffers");
    P(glDeleteTextures, "glDeleteTextures");
    P(glReadPixels, "glReadPixels");

    /* ===================== SELF-VALIDATION 1: which GPU? ================== */
    rend = (const char*)glGetString(GL_RENDERER);
    printf("  DISPLAY      : %s\n", (getenv("DISPLAY") ? getenv("DISPLAY") : "(unset)"));
    printf("  DRI_PRIME    : %s\n", (getenv("DRI_PRIME") ? getenv("DRI_PRIME") : "(unset)"));
    printf("  GL_VENDOR    : %s\n", (const char*)glGetString(GL_VENDOR));
    printf("  GL_VERSION   : %s\n", (const char*)glGetString(GL_VERSION));
    printf("  GL_RENDERER  : %s\n", rend ? rend : "(null)");
    if (!rend || !strstr(rend, "RX 550")) {
        fprintf(stderr, "\n  ABORT: el contexto NO es la RX 550. Todo lo que se "
                        "midiera seria el sampler de otra GPU.\n"
                        "  Reejecuta con:  DRI_PRIME=1 ./test_hardware_bc3\n");
        return 3;
    }
    printf("  contexto     : RX 550 CONFIRMADO\n");

    /* ===================== SELF-VALIDATION 2: S3TC present? =============== */
    {   const char *ext = (const char*)glGetString(GL_EXTENSIONS);
        if (!ext || !strstr(ext, "GL_EXT_texture_compression_s3tc")) {
            fprintf(stderr, "\n  ABORT: sin GL_EXT_texture_compression_s3tc; "
                            "la subida no seria DXT5.\n");
            return 3;
        }
        printf("  S3TC         : presente\n");
    }

    glGetIntegerv(GL_MAX_TEXTURE_SIZE, &maxtex);
    printf("  MAX_TEXTURE  : %d\n", (int)maxtex);
    if (maxtex < CHUNK_PX) { fprintf(stderr, "  ABORT: textura demasiado grande\n"); return 3; }

    blocks = malloc((size_t)CHUNK_BLOCKS * CHUNK_BLOCKS * BLOCK_BYTES);
    px     = malloc((size_t)CHUNK_PX * CHUNK_PX * 4);
    if (!blocks || !px) { fprintf(stderr, "FATAL: OOM\n"); return 3; }

    glGenTextures(1, &tex);
    glBindTexture(GL_TEXTURE_2D, tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glGenFramebuffers(1, &fbo);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);

    /* ===================== SELF-VALIDATION 3: FBO complete? =============== */
    {   uint8_t probe[BLOCK_BYTES];
        make_block(0, 0, probe);
        glCompressedTexImage2D(GL_TEXTURE_2D, 0, GL_COMPRESSED_RGBA_S3TC_DXT5_EXT,
                               CHUNK_PX, CHUNK_PX, 0, (GLsizei)sizeof probe, probe);
        {   GLenum e = glGetError();
            if (e != GL_NO_ERROR) {
                fprintf(stderr, "\n  ABORT: glCompressedTexImage2D -> GL error 0x%04X\n", e);
                return 3;
            }
        }
        glBindFramebuffer(GL_FRAMEBUFFER, fbo);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0);
        {   GLenum st = glCheckFramebufferStatus(GL_FRAMEBUFFER);
            if (st != GL_FRAMEBUFFER_COMPLETE) {
                fprintf(stderr, "\n  ABORT: FBO incompleto (0x%04X)\n", st);
                return 3;
            }
        }
        printf("  FBO          : completo\n\n");
    }

    printf("  barriendo 65536 pares de endpoints en 16 trozos de %dx%d texels...\n",
           CHUNK_PX, CHUNK_PX);

    for (chunk = 0; chunk < 16u; chunk++) {
        unsigned bx, by, p, base = chunk * (CHUNK_BLOCKS * CHUNK_BLOCKS);

        for (by = 0; by < CHUNK_BLOCKS; by++)
            for (bx = 0; bx < CHUNK_BLOCKS; bx++) {
                unsigned pair = base + by * CHUNK_BLOCKS + bx;
                uint8_t a0 = (uint8_t)(pair >> 8), a1 = (uint8_t)(pair & 0xFFu);
                make_block(a0, a1, blocks + ((size_t)by * CHUNK_BLOCKS + bx) * BLOCK_BYTES);
            }

        glCompressedTexImage2D(GL_TEXTURE_2D, 0, GL_COMPRESSED_RGBA_S3TC_DXT5_EXT,
                               CHUNK_PX, CHUNK_PX, 0,
                               (GLsizei)((size_t)CHUNK_BLOCKS * CHUNK_BLOCKS * BLOCK_BYTES),
                               blocks);
        {   GLenum e = glGetError();
            if (e != GL_NO_ERROR) {
                fprintf(stderr, "\n  ABORT: glCompressedTexImage2D -> GL error 0x%04X "
                                "en el trozo %u\n", e, chunk);
                return 3;
            }
        }

        glBindFramebuffer(GL_FRAMEBUFFER, fbo);
        glViewport(0, 0, CHUNK_PX, CHUNK_PX);
        glClearColor(0, 0, 0, 0);
        glClear(GL_COLOR_BUFFER_BIT);
        glReadPixels(0, 0, CHUNK_PX, CHUNK_PX, GL_RGBA, GL_UNSIGNED_BYTE, px);

        for (by = 0; by < CHUNK_BLOCKS; by++)
            for (bx = 0; bx < CHUNK_BLOCKS; bx++) {
                unsigned pair = base + by * CHUNK_BLOCKS + bx;
                uint8_t a0 = (uint8_t)(pair >> 8), a1 = (uint8_t)(pair & 0xFFu);
                for (p = 0; p < BLOCK_PX; p++) {
                    unsigned i = p % 8u;
                    int tx = (int)(bx * 4 + (p % 4u));
                    int ty = (int)(by * 4 + (p / 4u));
                    const uint8_t *t = px + ((size_t)ty * CHUNK_PX + tx) * 4;
                    uint8_t hw = t[3];
                    uint8_t pr = pred_round(a0, a1, i), pt = pred_trunc(a0, a1, i);
                    obs++;
                    if (i < 2) {           /* self-validation 4: endpoints */
                        if (hw == (i == 0 ? a0 : a1)) endpoint_ok++;
                        else endpoint_bad++;
                        continue;
                    }
                    if      (pr == pt) { if (hw == pr) agree_both++; else neither++; }
                    else if (hw == pr) { only_round++; }
                    else if (hw == pt) { only_trunc++; }
                    else                { neither++; }
                }
            }
    }

    /* ===================== RESULTS ======================================== */
    printf("\n=== VALIDACION DE LA MEDICION (antes de comparar) ===\n");
    printf("  endpoints a0/a1 correctos : %llu / %llu\n",
           (unsigned long long)endpoint_ok,
           (unsigned long long)(endpoint_ok + endpoint_bad));
    printf("  observaciones totales      : %llu\n", (unsigned long long)obs);
    if (endpoint_bad) {
        printf("  [FAIL] %llu endpoints NO decodificaron a su valor declarado; el "
               "camino de medida esta roto.\n", (unsigned long long)endpoint_bad);
        return 3;
    }
    printf("  [ OK ] los endpoints decodifican exactamente: el camino es valido.\n");
    {   size_t n = (size_t)CHUNK_PX * CHUNK_PX * 4, nz = 0;
        for (size_t k = 0; k < n; k++) if (px[k] != 0) nz++;
        printf("  color de control          : %zu bytes no nulos de %zu (esperado 0)\n",
               nz, n);
        if (nz) printf("  [WARN] hay color donde no deberia: revisa la alineacion.\n");
    }

    printf("\n=== CLASIFICACION DEL HARDWARE ===\n");
    printf("  solo coincide con REDONDEO (+3/+2) : %llu\n", (unsigned long long)only_round);
    printf("  solo coincide con TRUNCAMIENTO      : %llu\n", (unsigned long long)only_trunc);
    printf("  ambos (las predicciones coinciden)  : %llu\n", (unsigned long long)agree_both);
    printf("  ni uno ni otro                      : %llu\n", (unsigned long long)neither);

    printf("\n=== VEREDICTO ===\n");
    if (only_trunc == 0 && only_round > 0 && neither == 0) {
        printf("  EL HARDWARE USA REDONDEO (+3/+2).\n");
        printf("  AD-11 CONFIRMADO en el Polaris 12. bcdec v0.985 es el que diverge "
               "del hardware.\n");
        printf("  El encoder con redondeo es correcto para esta GPU.\n");
        rc = 0;
    } else if (only_round == 0 && only_trunc > 0 && neither == 0) {
        printf("  EL HARDWARE USA TRUNCAMIENTO.\n");
        printf("  AD-11 REFUTADO en el Polaris 12: la documentacion de D3D9 describe un\n");
        printf("  redondeo que esta GPU NO reproduce. bcdec v0.985 coincide con ella.\n");
        printf("  CONSECUENCIA: el encoder con redondeo emite bloques que el sampler de la\n");
        printf("  RX 550 decodifica distinto a rx550_decompress_block(). El error es\n");
        printf("  sistematico y va DENTRO del payload del bloque, no en un informe.\n");
        rc = 1;
    } else {
        printf("  CLASIFICACION MIXTA: el hardware no encaja en ninguna de las dos\n");
        printf("  hipotesis. Se reporta; no se decide por estos numeros.\n");
        rc = 2;
    }

    glDeleteTextures(1, &tex);
    glDeleteFramebuffers(1, &fbo);
    glXDestroyContext(dpy, ctx);
    free(blocks); free(px);
    return rc;
}
