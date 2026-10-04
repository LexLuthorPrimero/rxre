/*
 * carga_gfx.c -- carga de shader puro para la RX550, EGL surfaceless + GLES3.
 *
 * QUE ES Y POR QUE ESTA HECHO ASI
 * -------------------------------
 * El proyecto tiene la arista `WORKLOAD -> CLOCK` marcada "MECHANISM KNOWN,
 * EFFECT UNVERIFIED" (E-PWR-008) y NO tiene ninguna medicion de la GPU bajo
 * carga. Esta herramienta produce esa medicion. Tres decisiones, y las tres son
 * deliberadas:
 *
 * 1. EGL SURFACELESS, no una ventana. Sin superficie no hay scanout, no hay
 *    CRTC, no hay KMS. El hallazgo 1085 midi que la consola esta en
 *    `i915drmfb` (la Intel) y que la RX550 no tiene nodo de framebuffer, asi
 *    que surfaceless no puede tocar la pantalla -- y no depende de que eso
 *    siga siendo cierto para no ser seguro.
 *
 * 2. VERIFICACION DE VENDOR ANTES DE CORRER NADA. Se eligen los dispositivos
 *    EGL y se acepta solo el que apunta al nodo cuyo `vendor` en sysfs es
 *    0x1002 (AMD). Si el ICD por defecto fuera el Intel, esto mediria el chip
 *    equivocado y el resultado seria un halluc con clocks. Si no hay ningun
 *    dispositivo AMD, el programa SALE CON ERROR y no produce numeros.
 *
 * 3. SHADER DE ALU PURO, sin texturas ni buffers. El objetivo es saber si
 *    SCLK SUBE bajo carga, y una carga memory-bound confoundiria esa lectura
 *    con el techo de VRAM. Un bucle de FMA sobre gl_FragCoord no toca memoria:
 *    si el reloj sube, sube por compute.
 *
 * QUE NO MIDE
 * -----------
 * No es un benchmark. Da frames y segundos de un shader sintetico, y su valor
 * esta en la CORRELACION frame-rate <-> SCLK, no en el numero absoluto. No
 * mide el techo de la GPU, ni el ancho de banda de memoria, ni la eficiencia
 * energetica. Un numero de fps de aqui no se puede comparar con el de otra
 * aplicacion, y el codigo de salida lo dice.
 *
 * ENTRADA / SALIDA
 * ----------------
 *   --segundos N    duracion de la carga (defecto 6)
 *   --iter N        iteraciones del bucle de shader por fragmento (defecto 64)
 *   --ancho N --alto N   tamano del framebuffer (defecto 256x256)
 *   --forzar-vendor ID   0x1002 por defecto; para tests de vendor equivocado
 *
 *   stdout, una linea por segundo:
 *     t=1.0s  sclk_hz=551000000  mclk_hz=625000000  frames=1234  fps=1234.0
 *   y una linea final con el total.
 *
 *   Codigos de salida:  0 ok · 2 uso · 3 sin EGL · 4 sin dispositivo del vendor
 *                      pedido · 5 sin contexto GLES3 · 6 error de shader
 */
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>

#define LEC_RENDER 256
static char ruta_render[LEC_RENDER];

/* ------------------------------------------------------------------ tiempo */
static double ahora(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

/* ------------------------------------------- vendor del nodo, desde sysfs */
static long vendor_de(const char *nodo)
{
    char p[512], b[32], base[256];
    int fd, n;
    char *v, *sl;
    /* EGL devuelve a veces /dev/dri/card1 y otras /dev/dri/renderD129. Ambos
     * existen en /sys/class/drm/ con el MISMO basename, asi que se quita el
     * prefijo del directorio. MEDIDO: la primera version construia
     * /sys/class/drm//dev/dri/card1/device/vendor y devolvia -1 para todo, que
     * el programa imprimia como 0xffffffffffffffff -- un numero que parece una
     * medicion y es un fallo de camino. */
    snprintf(base, sizeof(base), "%s", nodo);
    sl = strrchr(base, '/');
    if (sl) snprintf(base, sizeof(base), "%s", sl + 1);
    snprintf(p, sizeof(p), "/sys/class/drm/%s/device/vendor", base);
    fd = open(p, O_RDONLY);
    if (fd < 0)
        return -1;
    n = read(fd, b, sizeof(b) - 1);
    close(fd);
    if (n <= 0)
        return -1;
    b[n] = 0;
    v = strstr(b, "0x");
    return v ? strtol(v, NULL, 16) : strtol(b, NULL, 16);
}

/* ------------------------------------------------------- lectura de clocks */
static long lee_hz(const char *base, const char *rel)
{
    char p[512], b[32];
    int fd, n;
    long v = -1;
    snprintf(p, sizeof(p), "/sys/class/hwmon/%s/%s", base, rel);
    fd = open(p, O_RDONLY);
    if (fd < 0)
        return -1;
    n = read(fd, b, sizeof(b) - 1);
    close(fd);
    if (n <= 0)
        return -1;
    b[n] = 0;
    v = strtol(b, NULL, 10);
    return v;
}

/* El hwmon de esta GPU: se busca por nombre, no se supone hwmon1.
 * MEDIDO en el 1059/1085 que suponer el indice es una suposicion sobre un
 * arbol que cambia; el NOMBRE es estable. */
static int localiza_hwmon(char *out, size_t n_out, const char *want_sclk)
{
    char base[512];
    int i;
    for (i = 0; i < 8; i++) {
        char p[600], b[64];
        int fd, n;
        snprintf(base, sizeof(base), "/sys/class/hwmon/hwmon%d", i);
        snprintf(p, sizeof(p), "%s/name", base);
        fd = open(p, O_RDONLY);
        if (fd < 0)
            continue;
        n = read(fd, b, sizeof(b) - 1);
        close(fd);
        if (n <= 0)
            continue;
        b[n] = 0;
        if (!strncmp(b, want_sclk, strlen(want_sclk))) {
            snprintf(out, n_out, "hwmon%d", i);
            return 0;
        }
    }
    return -1;
}

/* ------------------------------------------------------------- shaders */
/* ALU pura: cadena de FMA sobre gl_FragCoord. Sin textura, sin buffer, sin
 * dependencia de memoria. El bucle con `iter` esta SIN desenrollar a proposito:
 * el compilador no puede_vectorizarlo si el resultado se acumula, y asi la
 * carga escala con `--iter` de forma controlada. */
static const char *VS =
    "#version 300 es\n"
    "void main(){\n"
    "  vec2 p = vec2((gl_VertexID<<1)&2, gl_VertexID&2);\n"
    "  gl_Position = vec4(p*2.0-1.0, 0.0, 1.0);\n"
    "}\n";

static const char *FS =
    "#version 300 es\n"
    "precision highp float;\n"
    "uniform int  u_iter;\n"
    "uniform float u_gain;\n"
    "out vec4 o_color;\n"
    "void main(){\n"
    "  vec2 c = gl_FragCoord.xy;\n"
    "  float a = 1.000001;\n"
    "  float x = c.x*0.001 + c.y*0.002;\n"
    "  for (int i = 0; i < u_iter; ++i)\n"
    "    x = a*x + 0.5;\n"   /* cadena de dependencia: no vectorizable */
    "  o_color = vec4(fract(x*u_gain), 0.25, 0.5, 1.0);\n"
    "}\n";

static GLuint compila(GLenum tipo, const char *src, const char *etq)
{
    GLuint s = glCreateShader(tipo);
    GLint ok = 0;
    glShaderSource(s, 1, &src, NULL);
    glCompileShader(s);
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[1024];
        glGetShaderInfoLog(s, sizeof(log), NULL, log);
        fprintf(stderr, "FALLO al compilar %s:\n%s\n", etq, log);
        glDeleteShader(s);
        return 0;
    }
    return s;
}

static void uso(const char *argv0)
{
    fprintf(stderr,
        "uso: %s [--segundos N] [--iter N] [--ancho N] [--alto N]\n"
        "          [--forzar-vendor 0xID]\n", argv0);
}

int main(int argc, char **argv)
{
    double segundos = 6.0, t0, tin, tout, frames = 0;
    int iter = 64, ancho = 256, alto = 256;
    long vendor_pedido = 0x1002;
    EGLDisplay dpy = EGL_NO_DISPLAY;
    EGLContext ctx = EGL_NO_CONTEXT;
    EGLConfig cfg;
    EGLint ncfg = 0, major, minor;
    EGLDeviceEXT devs[16];
    EGLint ndev = 0, i, elegido = -1;
    PFNEGLQUERYDEVICESEXTPROC query_devices;
    PFNEGLGETPLATFORMDISPLAYEXTPROC get_platform_display;
    PFNEGLQUERYDEVICESTRINGEXTPROC query_device_string;
    GLuint prog = 0, vs = 0, fs = 0, vao = 0;
    GLint loc_iter, loc_gain;
    char hw[32];
    int tener_hw = (localiza_hwmon(hw, sizeof(hw), "amdgpu") == 0);
    int s;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--segundos") && i + 1 < argc) segundos = atof(argv[++i]);
        else if (!strcmp(argv[i], "--iter") && i + 1 < argc) iter = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--ancho") && i + 1 < argc) ancho = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--alto") && i + 1 < argc) alto = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--forzar-vendor") && i + 1 < argc) vendor_pedido = strtol(argv[++i], NULL, 0);
        else { uso(argv[0]); return 2; }
    }

    query_devices = (PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
    get_platform_display = (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
    query_device_string = (PFNEGLQUERYDEVICESTRINGEXTPROC)eglGetProcAddress("eglQueryDeviceStringEXT");
    if (!query_devices || !get_platform_display || !query_device_string) {
        fprintf(stderr, "sin EGL_EXT_platform_base / device_base / device_enumeration\n");
        return 3;
    }

    query_devices(16, devs, &ndev);
    if (ndev <= 0) {
        fprintf(stderr, "EGL no expone ningun dispositivo\n");
        return 3;
    }

    /* SELECCION POR VENDOR. Esto es lo que impide medir la Intel. */
    for (i = 0; i < ndev; i++) {
        const char *f = query_device_string(devs[i], 0x3233 /*EGL_DRM_DEVICE_FILE_EXT*/);
        long v;
        if (!f)
            continue;
        snprintf(ruta_render, sizeof(ruta_render), "%s", f);
        v = vendor_de(ruta_render);
        fprintf(stderr, "dispositivo EGL %d: %-22s vendor=0x%lx%s\n",
                (int)i, ruta_render, v, (v == vendor_pedido) ? "   <== ELEGIDO" : "");
        if (v == vendor_pedido && elegido < 0)
            elegido = (int)i;
    }
    if (elegido < 0) {
        fprintf(stderr, "ningun dispositivo EGL apunta al vendor 0x%lx. "
                        "No se produce ninguna medicion.\n", vendor_pedido);
        return 4;
    }

    dpy = get_platform_display(0x313F /*EGL_PLATFORM_DEVICE_EXT, leido de eglext.h*/, devs[elegido], NULL);
    if (dpy == EGL_NO_DISPLAY) { fprintf(stderr, "eglGetPlatformDisplayEXT fallo\n"); return 3; }
    if (!eglInitialize(dpy, &major, &minor)) { fprintf(stderr, "eglInitialize fallo\n"); return 3; }
    if (!eglBindAPI(EGL_OPENGL_ES_API)) { fprintf(stderr, "eglBindAPI fallo\n"); return 3; }

    if (!eglChooseConfig(dpy, (EGLint[]){EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
                                        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
                                        EGL_NONE}, &cfg, 1, &ncfg) || ncfg < 1) {
        fprintf(stderr, "eglChooseConfig: sin config GLES3\n"); return 5;
    }
    ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, (EGLint[]){EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE});
    if (ctx == EGL_NO_CONTEXT) { fprintf(stderr, "eglCreateContext fallo\n"); return 5; }
    if (!eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx)) {
        fprintf(stderr, "eglMakeCurrent fallo\n"); return 5;
    }
    fprintf(stderr, "GL_RENDERER   = %s\n", (const char *)glGetString(GL_RENDERER));
    fprintf(stderr, "GL_VERSION    = %s\n", (const char *)glGetString(GL_VERSION));
    fprintf(stderr, "GLSL          = %s\n", (const char *)glGetString(GL_SHADING_LANGUAGE_VERSION));
    fprintf(stderr, "ancho x alto  = %d x %d   iter = %d\n", ancho, alto, iter);

    vs = compila(GL_VERTEX_SHADER, VS, "vertice");
    fs = compila(GL_FRAGMENT_SHADER, FS, "fragmento");
    if (!vs || !fs) return 6;
    prog = glCreateProgram();
    glAttachShader(prog, vs); glAttachShader(prog, fs); glLinkProgram(prog);
    { GLint ok = 0; glGetProgramiv(prog, GL_LINK_STATUS, &ok);
      if (!ok) { char l[1024]; glGetProgramInfoLog(prog, sizeof(l), NULL, l);
                 fprintf(stderr, "FALLO al enlazar:\n%s\n", l); return 6; } }
    glUseProgram(prog);
    loc_iter = glGetUniformLocation(prog, "u_iter");
    loc_gain = glGetUniformLocation(prog, "u_gain");
    glUniform1i(loc_iter, iter);
    glUniform1f(loc_gain, 1.0f);
    glGenVertexArrays(1, &vao); glBindVertexArray(vao);
    glViewport(0, 0, ancho, alto);

    if (tener_hw) fprintf(stderr, "hwmon        = /sys/class/hwmon/%s\n", hw);
    else          fprintf(stderr, "hwmon        = NO LOCALIZADO (los clocks saldran -1)\n");
    fprintf(stderr, "render node  = %s\n\n", ruta_render);

    printf("t_s  sclk_hz  mclk_hz  frames  fps\n");
    fflush(stdout);
    t0 = ahora();
    tin = t0;
    for (s = 1; s <= (int)segundos; s++) {
        double tfin = t0 + s;
        long sc = -1, mc = -1;
        if (tener_hw) {
            sc = lee_hz(hw, "freq1_input");
            mc = lee_hz(hw, "freq2_input");
        }
        while (ahora() < tfin) {
            glClearColor(0.f, 0.f, 0.f, 1.f);
            glClear(GL_COLOR_BUFFER_BIT);
            glDrawArrays(GL_TRIANGLES, 0, 3);
            glFinish();
            frames++;
        }
        tout = ahora();
        printf("t=%.1f  sclk_hz=%ld  mclk_hz=%ld  frames=%.0f  fps=%.1f\n",
               (double)s, sc, mc, frames, frames / (tout - tin));
        fflush(stdout);
        tin = tout;
    }
    tout = ahora();
    printf("\nTOTAL  %.2f s  frames=%.0f  fps=%.1f  (NO es un benchmark: "
           "shader sintetico, valor en la correlacion con sclk)\n",
           tout - t0, frames, frames / (tout - t0));

    glDeleteProgram(prog); glDeleteShader(vs); glDeleteShader(fs);
    eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    eglDestroyContext(dpy, ctx);
    eglTerminate(dpy);
    return 0;
}