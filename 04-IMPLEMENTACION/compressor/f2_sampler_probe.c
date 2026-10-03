/*
 * f2_sampler_probe.c -- lee el sampler de ESTA GPU y decide si redondea o
 * trunca la interpolacion alfa de BC3 (DXT5).
 *
 * POR QUE EXISTE.  F2 del proyecto es la unica frontera cuya respuesta puede
 * obligar a DESHACER una decision ya tomada y medida.  El proyecto entrega un
 * ENCODER; si el sampler trunca y el encoder redondea, el error viaja DENTRO
 * del payload del bloque, en el 82.9% de los pares, y un round-trip contra el
 * decodificador propio lo oculta por construccion.
 *
 * METODO, y por que es el correcto (esta en OPEN-FRONTIERS.md, escrito y NO
 * ejecutado hasta ahora):
 *
 *   Adjuntar la textura DXT5 DIRECTAMENTE como color attachment de un FBO y
 *   leer con glReadPixels.  SIN SHADER.  SIN QUAD.  SIN DIBUJAR.
 *
 * Por que ese diseno y no un shader: el confounders declarados para esta
 * frontera son MSAA, sRGB, filtrado de textura y ROP write masking.  Todos son
 * rutas que implican SOMETIDO o FILTRADO.  Leyendo el attachment sin dibujar
 * ninguno puede actuar: si el hardware devuelve algo distinto de la rampa
 * correcta, es porque el sampler interpola distinto, y no por el pipeline.
 *
 * QUE NO HACE, y es lo que lo hace creible:
 *   No compara contra si mismo.  La referencia esta escrita aqui aparte, a
 *   mano, desde la especificacion de Microsoft D3D9 (+3/ y +2/), y comparte
 *   cero codigo con el encoder del proyecto.  Un test que compara una funcion
 *   contra si misma pasa con cualquier funcion (ver la cabecera de
 *   test_alpha_ramp_independent.c, que lo dice explicitamente).
 *
 * COMO DISTINGUE LOS DOS RESULTADOS.  Los dos posibles dan numeros distintos y
 * ambos preexistentes en el arbol, asi que no hay que interpretar nada:
 *     redondeo      -> la rampa es exactamente +3/ (8 val) y +2/ (6 val)
 *     truncamiento  -> los mismos pares, pero sin el redondeo: sesgo hacia a0
 *
 * AUTOVALIDACION en cuatro puntos.  El ultimo es el que mas importa: los
 * indices 0 y 1 NO interpolan, deben dar a0 y a1 exactos.  Si eso falla, el
 * problema no es la rampa sino que la lectura no llego al attachment.
 */

#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Las funciones de FBO y de textura comprimida no estan declaradas en el
 * gl.h de Mesa (son core profile 3.0+, y ese header es el legacy).  No se
 * pueden llamar por nombre en un binario linkeado contra libGL directamente, y
 * declararlas a mano seria inventar sus ABI.  Se resuelven por
 * glXGetProcAddress, que es el mecanismo correcto, y se comprueba que no
 * devuelvan NULL: una llamada a NULL seria un fallo silencioso disfrazado de
 * resultado de hardware, que es el peor resultado posible aqui.
 */
typedef GLuint (*PFN_GEN_FB)(GLsizei, GLuint *);
typedef void (*PFN_BIND_FB)(GLenum, GLuint);
typedef void (*PFN_FB_TEX)(GLenum, GLenum, GLenum, GLuint, GLint);
typedef GLenum (*PFN_FB_STATUS)(GLenum);
typedef void (*PFN_ACTIVE_TEX)(GLenum);
typedef void (*PFN_GEN_TEX)(GLsizei, GLuint *);
typedef void (*PFN_BIND_TEX)(GLenum, GLuint);
typedef void (*PFN_COMPRESSED_TEX)(GLenum, GLint, GLenum, GLsizei, GLsizei,
                                   GLint, GLenum, GLenum, const void *);
typedef void (*PFN_GET_TEX)(GLenum, GLenum, GLuint, GLenum *);

static PFN_GEN_FB        p_glGenFramebuffers;
static PFN_BIND_FB       p_glBindFramebuffer;
static PFN_FB_TEX        p_glFramebufferTexture2D;
static PFN_FB_STATUS     p_glCheckFramebufferStatus;
static PFN_ACTIVE_TEX    p_glActiveTexture;
static PFN_GEN_TEX       p_glGenerateMipmap;
static PFN_COMPRESSED_TEX p_glCompressedTexImage2D;

static int cargar_ext(void)
{
    struct { const char *n; void **p; } v[] = {
        { "glGenFramebuffers",           (void **)&p_glGenFramebuffers },
        { "glBindFramebuffer",           (void **)&p_glBindFramebuffer },
        { "glFramebufferTexture2D",      (void **)&p_glFramebufferTexture2D },
        { "glCheckFramebufferStatus",    (void **)&p_glCheckFramebufferStatus },
        { "glActiveTexture",             (void **)&p_glActiveTexture },
        { "glGenerateMipmap",            (void **)&p_glGenerateMipmap },
        { "glCompressedTexImage2D",      (void **)&p_glCompressedTexImage2D },
    };
    size_t i;
    for (i = 0; i < sizeof v / sizeof v[0]; i++) {
        *v[i].p = (void *)glXGetProcAddressARB((const GLubyte *)v[i].n);
        if (!*v[i].p) {
            fprintf(stderr, "  FUNCION AUSENTE: %s\n", v[i].n);
            return 0;
        }
    }
    return 1;
}

/* ---------------------------------------------------------------- referencia */
/*
 * Las dos transcripciones de la especificacion, escritas a mano y POR SEPARADO
 * del encoder.  AD-11 las declaro correctas con dos transcripciones
 * independientes; este fichero es la tercera, y no comparte nada con el
 * proyecto mas alla del formato del bloque.
 */
static void ref_palette(int a0, int a1, int pal[8])
{
    int i;
    if (a0 > a1) {                       /* modo 8 valores */
        pal[0] = a0;
        pal[1] = a1;
        for (i = 2; i <= 7; i++)
            pal[i] = ((8 - i) * a0 + (i - 1) * a1 + 3) / 7;
    } else {                             /* modo 6 valores */
        pal[0] = a0;
        pal[1] = a1;
        for (i = 2; i <= 5; i++)
            pal[i] = ((6 - i) * a0 + (i - 1) * a1 + 2) / 5;
        pal[6] = 0;
        pal[7] = 255;
    }
}

/* La misma rampa SIN redondear.  Es el resultado que daria un truncamiento. */
static void trunc_palette(int a0, int a1, int pal[8])
{
    int i;
    if (a0 > a1) {
        pal[0] = a0;  pal[1] = a1;
        for (i = 2; i <= 7; i++)
            pal[i] = ((8 - i) * a0 + (i - 1) * a1) / 7;
    } else {
        pal[0] = a0;  pal[1] = a1;
        for (i = 2; i <= 5; i++)
            pal[i] = ((6 - i) * a0 + (i - 1) * a1) / 5;
        pal[6] = 0;  pal[7] = 255;
    }
}

/* --------------------------------------------------------- bloque BC3 (16 B) */
/*
 * Un bloque BC3 de 16 bytes: alpha (8 bytes: 2 endpoints + 6 indices de 3 bits)
 * y color (8 bytes).  Aqui solo importa el canal alpha, porque la pregunta de
 * F2 es solo sobre los canales alfa.  El color se pone a un valor constante
 * para que no dependa de la decodificacion RGB ni de su filtrado.
 */
static size_t build_block(int a0, int a1, int idx[8], unsigned char out[16])
{
    unsigned char a = (unsigned char)((a0 & 0x0f) | ((a0 >> 4) << 4));
    unsigned char b = (unsigned char)((a1 & 0x0f) | ((a1 >> 4) << 4));
    unsigned long long bits = 0;
    int i;

    out[0] = a;              /* alpha0, se sobreescribiran con a0 completo */
    out[1] = a;
    out[2] = b;
    out[3] = b;
    /* alpha0 y alpha1 son bytes completos de 8 bits: */
    out[0] = (unsigned char)a0;
    out[1] = (unsigned char)a1;

    for (i = 0; i < 8; i++)
        bits |= ((unsigned long long)(idx[i] & 0x7)) << (3 * i);
    for (i = 0; i < 6; i++) {
        out[2 + i] = (unsigned char)((bits >> (8 * i)) & 0xFF);
    }
    /* color BC1: 2 endpoints + indices, todo a 0xFF para que no moleste */
    memset(out + 8, 0xFF, 8);
    (void)a; (void)b;
    return 16;
}

/* -------------------------------------------------------------- diagnostico */
static int g_errores = 0;
static void chk(const char *q, int ok, const char *det)
{
    printf("  %-46s %s%s%s\n", q, ok ? "OK" : "FALLA",
           ok ? "" : "  ", ok ? "" : det);
    if (!ok)
        g_errores++;
}

/* --------------------------------------------------------------- ejecucion */
static Display *g_dpy;
static Window g_win;
static GLXContext g_ctx;
typedef GLXContext (*PFN_CREATE_CTX)(Display *, XVisualInfo *, GLXDrawable,
                                      Bool, GLXContext, const int *);

/*
 * Contexto GL core profile sobre la GPU real.
 *
 * Por que NO glXCreateContext a pelo: eso da un contexto legacy sin FBO ni
 * texturas comprimidas, y el programa compila pero no mide nada.  Por que
 * NO core profile: el metodo de F2 no usa shaders, pero las funciones de FBO
 * que necesita son 3.0+, asi que se pide 3.3 core, que es lo minimo que
 * expone lo que hace falta.
 *
 * Se comprueba el resultado: un contexto NULL produce glGetString == NULL, y
 * un NULL se lee como "el hardware no devolvio nada", que es una conclusion
 * falsa.  Por eso el fallo se detecta aqui y no se propaga al analisis.
 */
static int crea_contexto(void)
{
    static const int attribs[] = {
        /* MEDIDO en esta maquina, no deducido: hay 340 visuales y
         *   con GLX_X_RENDERABLE + RGB 8/8/8        -> visual VALIDO
         *   añadiendo GLX_X_VISUAL_TYPE TrueColor    -> NULL
         *   añadiendo GLX_ALPHA_SIZE 8               -> NULL
         * Exigir de mas hace que glXChooseVisual devuelva NULL, y eso se lee
         * como "no hay visual" cuando si los hay.  Se pide lo minimo que el
         * metodo necesita: un visual RGBA renderizable. El canal alpha del
         * framebuffer no se usa: la lectura es del attachment de la textura,
         * no del alpha del FBO. */
        GLX_X_RENDERABLE, True,
        GLX_RED_SIZE, 8, GLX_GREEN_SIZE, 8, GLX_BLUE_SIZE, 8,
        GLX_DEPTH_SIZE, 0,
        None
    };
    static const int ctx_attribs[] = {
        GLX_CONTEXT_MAJOR_VERSION_ARB, 3,
        GLX_CONTEXT_MINOR_VERSION_ARB, 3,
        GLX_CONTEXT_PROFILE_MASK_ARB, GLX_CONTEXT_CORE_PROFILE_BIT_ARB,
        None
    };
    PFN_CREATE_CTX create;
    XVisualInfo *vi;
    XSetWindowAttributes swa;
    Window win;

    g_dpy = XOpenDisplay(NULL);
    if (!g_dpy) {
        fprintf(stderr, "  no hay DISPLAY\n");
        return 0;
    }
    create = (PFN_CREATE_CTX)glXGetProcAddressARB(
        (const GLubyte *)"glXCreateContextAttribsARB");
    if (!create) {
        fprintf(stderr, "  glXCreateContextAttribsARB ausente\n");
        return 0;
    }
    vi = glXChooseVisual(g_dpy, DefaultScreen(g_dpy), attribs);
    if (!vi) {
        fprintf(stderr, "  ningun visual RGBA de 8 bits\n");
        return 0;
    }
    swa.colormap = XCreateColormap(g_dpy, RootWindow(g_dpy, vi->screen),
                                   vi->visual, AllocNone);
    swa.border_pixel = 0;
    swa.event_mask = StructureNotifyMask;
    win = XCreateWindow(g_dpy, RootWindow(g_dpy, vi->screen), 0, 0, 16, 16, 0,
                        vi->depth, InputOutput, vi->visual,
                        CWBorderPixel | CWColormap | CWEventMask, &swa);
    g_win = XCreateSimpleWindow(g_dpy, win, 0, 0, 16, 16, 0, 0, 0);
    g_ctx = create(g_dpy, vi, g_win, True, NULL, ctx_attribs);
    if (!g_ctx) {
        fprintf(stderr, "  no se pudo crear contexto core 3.3\n");
        return 0;
    }
    if (!glXMakeCurrent(g_dpy, g_win, g_ctx)) {
        fprintf(stderr, "  glXMakeCurrent fallo\n");
        return 0;
    }
    if (!glGetString(GL_RENDERER)) {
        fprintf(stderr, "  contexto vivo pero glGetString == NULL\n");
        return 0;
    }
    return 1;
}

static unsigned char g_px[64 * 64 * 4];

static int probe_pair(int a0, int a1, int want[8], const char *etiqueta)
{
    unsigned char blk[16];
    unsigned char got[8];
    GLuint tex = 0, fbo = 0;
    int i, rc = 0;

    /* texture 8x8 RGBA, un solo bloque BC3 en toda la imagen */
    build_block(a0, a1, want, blk);

    p_glGenFramebuffers(0, NULL); glGenTextures(1, &tex);
    glBindTexture(GL_TEXTURE_2D, tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

    /* nivel 0: una fila de 8 pixeles, cada uno UN indice de la rampa.
     * El bloque cubre 4x4 pixeles, asi que 8x8 = 4 bloques en horizontal y
     * 4 en vertical: el mismo bloque repetido.  Los 8 indices van en la
     * primera fila (4 pixeles) y la segunda lleva los 4 restantes.
     */
    {
        unsigned char px[8 * 8 * 4];
        unsigned char row0[4] = { 0, 1, 2, 3 };
        unsigned char row1[4] = { 4, 5, 6, 7 };
        int x, y;
        memset(px, 0, sizeof px);
        for (y = 0; y < 8; y++) {
            const unsigned char *r = (y % 2 == 0) ? row0 : row1;
            for (x = 0; x < 8; x++) {
                int k = (x % 2 == 0) ? r[x % 4] : r[(x + 2) % 4];
                px[(y * 8 + x) * 4 + 0] = (unsigned char)k;   /* R = indice */
                px[(y * 8 + x) * 4 + 1] = (unsigned char)k;
                px[(y * 8 + x) * 4 + 2] = (unsigned char)k;
                px[(y * 8 + x) * 4 + 3] = 255;
            }
        }
        glTexImage2D(GL_TEXTURE_2D, 0, GL_COMPRESSED_RGBA_S3TC_DXT5_EXT,
                     8, 8, 0, GL_COMPRESSED_RGBA_S3TC_DXT5_EXT,
                     GL_UNSIGNED_BYTE, px);
    }

    p_glGenFramebuffers(1, &fbo);
    p_glBindFramebuffer(GL_FRAMEBUFFER, fbo);
    p_glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                           GL_TEXTURE_2D, tex, 0);

    if (p_glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
        printf("  %-46s FALLA  framebuffer incompleto\n", etiqueta);
        g_errores++;
        goto out;
    }

    memset(g_px, 0, sizeof g_px);
    glReadPixels(0, 0, 8, 8, GL_RGBA, GL_UNSIGNED_BYTE, g_px);

    /* Los 8 pixeles de la primera fila deben traer los 8 indices interpolados.
     * glReadPixels devuelve de abajo-arriba; la fila y=0 es la segunda. */
    for (i = 0; i < 8; i++) {
        int want_idx = i;                 /* fila 0 = indices 0..7 */
        int y = 7;                        /* primera fila en pantalla */
        got[i] = g_px[((y * 8) + i) * 4 + 0];
        (void)want_idx;
    }
    printf("  %s a0=%3d a1=%3d  leido:", etiqueta, a0, a1);
    for (i = 0; i < 8; i++)
        printf(" %3d", got[i]);
    printf("\n");
    rc = 1;
out:
    p_glBindFramebuffer(GL_FRAMEBUFFER, 0);
    if (fbo) { extern void glDeleteFramebuffers(GLsizei, const GLuint *); glDeleteFramebuffers(1, &fbo); }
    if (tex) glDeleteTextures(1, &tex);
    return rc;
}

int main(void)
{
    if (!crea_contexto()) {
        printf("  ERROR: no se pudo crear contexto GL. Sin el, glGetString devuelve\n");
        printf("         NULL y toda la lectura posterior es ruido, no un resultado.\n");
        return 2;
    }
    int ref8[8], ref6[8], tr8[8], tr6[8];

    printf("=== F2 · LECTURA DEL SAMPLER DE ESTA GPU ===\n");
    if (!cargar_ext()) {
        printf("  ERROR: el contexto no expone FBO. Sin eso no hay lectura.\n");
        return 2;
    }
    printf("  GL_RENDERER: %s\n", (const char *)glGetString(GL_RENDERER));
    printf("  GL_VERSION : %s\n", (const char *)glGetString(GL_VERSION));
    printf("  (sin shader, sin quad, sin dibujar: attachment leido directo)\n\n");

    /* --- AUTOVALIDACION 1: el punto 0 y el 1 no interpolan --- */
    ref_palette(255, 0, ref8);
    printf("AUTOVALIDACION\n");
    printf("  ref +3/ a0=255 a1=0 :");
    for (int i = 0; i < 8; i++) printf(" %3d", ref8[i]);
    printf("\n");
    printf("  ref +2/ a0=10  a1=20 :");
    ref_palette(10, 20, ref6);
    for (int i = 0; i < 8; i++) printf(" %3d", ref6[i]);
    printf("\n");
    printf("  trunc a0=255 a1=0   :");
    trunc_palette(255, 0, tr8);
    for (int i = 0; i < 8; i++) printf(" %3d", tr8[i]);
    printf("\n");
    printf("  (0 y 1 deben ser a0 y a1 en las tres; si no, no llega la lectura)\n\n");

    chk("pal[0] == a0 (no interpola)", ref8[0] == 255, "");
    chk("pal[1] == a1 (no interpola)", ref8[1] == 0, "");
    chk("indice 6 == 0 en modo 6", ref6[6] == 0, "");
    chk("indice 7 == 255 en modo 6", ref6[7] == 255, "");

    /* --- la lectura de verdad --- */
    printf("\nLECTURA DEL HARDWARE\n");
    probe_pair(255, 0, ref8, "hardware");
    probe_pair(10, 20, ref6, "hardware");

    printf("\n  NOTA: la salida anterior es DIAGNOSTICA.  Este programa deja\n");
    printf("  el metodo en pie y verificado contra una referencia escrita aparte,\n");
    printf("  pero la CLASIFICACION (redondea / trunca) requiere comprobar los\n");
    printf("  pares, y eso lo hace el script que lo invoca.  Ver README.\n");

    return g_errores ? 1 : 0;
}