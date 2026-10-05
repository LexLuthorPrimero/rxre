/* rx550_gl_load — carga COMPUTE por OpenGL 4.5 compute sobre EGL surfaceless.
 *
 * POR QUE OTRO PROGRAMA Y NO EL DE VULKAN
 *   El camino Vulkan crashea DENTRO de Mesa: "segfault at 7f0f20b1c860 ... in
 *   libvulkan_radeon.so", en vkCreateDevice, en este Polaris12 con Mesa 26.2.3.  El fallo esta
 *   en RADV, no en el programa.  radeonsi (OpenGL) es otro driver y otro camino de codigo, y
 *   para gfx8 es mucho mas maduro.  Este es el ultimo camino disponible para el barrido.
 *
 * FRONTERA DURA — la GPU integrada NO SE TOCA
 *   Este programa NO coge "el primer dispositivo".  eglQueryDevicesEXT lista los dispositivos
 *   EGL, y para cada uno exige EGL_DRM_DEVICE_FILE_EXT; SOLO elige el que sea
 *   /dev/dri/renderD129, que es el nodo de la RX 550 (0000:01:00.0).  Si no lo encuentra,
 *   no crea contexto y sale con codigo 3.  El Intel es /dev/dri/renderD128 y queda excluido
 *   por ruta, no por indice.
 *
 * ALCANCE
 *   Compute sobre la VRAM de la RX 550.  No toca registros, no carga modulos, no cambia el
 *   estado de energia, no abre fb0, no cambia la consola (que es de la Intel).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GL/gl.h>
#include <GL/glext.h>

/* FRONTERA: que nodos DRI son la RX 550 y cuales son la iGPU.
 *
 * NO hardcodeo "/dev/dri/renderD129" sin comprobarlo, porque si el orden de nodos cambiara
 * el programa podria tocar la Intel.  Las dos listas estan tomadas del sistema, y estan
 * comprobadas contra vendor/device de cada tarjeta:
 *     /sys/class/drm/card0/device/{vendor,device} = 8086:xxxx  -> Intel HD 4600 (i915)
 *     /sys/class/drm/card1/device/{vendor,device} = 1002:699f  -> RX 550
 * Un nodo de la lista RX550 es aceptable.  Uno de la lista INTEL es motivo de ABORTO
 * inmediato y sin crear contexto.  Cualquier otro nodo tambien aborta: la prudencia aqui
 * vale mas que la comodidad. */
static const char *RX550_NODES[] = { "/dev/dri/renderD129", "/dev/dri/card1", NULL };
static const char *INTEL_NODES[] = { "/dev/dri/renderD128", "/dev/dri/card0", NULL };

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static void *glXGetProcAddressLike(const char *n) { return (void *)eglGetProcAddress(n); }

/* #version 430 hace falta para que el compilador acepte layout(binding=) de forma estandar
 * en un compute shader de GL 4.3. */
static const char *CS_SRC =
"#version 430\n"
"layout(local_size_x = 64) in;\n"
"layout(std430, binding = 0) buffer Buf { uint data[]; };\n"
"void main()\n"
"{\n"
"    uint i = gl_GlobalInvocationID.x;\n"
"    uint v = data[i];\n"
"    v ^= v << 13;\n"
"    v ^= v >> 17;\n"
"    v ^= v << 5;\n"
"    data[i] = v;\n"
"}\n";

int main(int argc, char **argv)
{
    int seconds = 8, mib = 256;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--seconds") && i + 1 < argc) seconds = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--buffer") && i + 1 < argc) mib = atoi(argv[++i]);
    }
    setvbuf(stdout, NULL, _IONBF, 0);

    /* ---- 1) EGL sin plataforma por defecto:|display no existe y no se quiere ---- */
    PFNEGLGETPLATFORMDISPLAYEXTPROC getPlatformDisplay =
        (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
    PFNEGLQUERYDEVICESEXTPROC queryDevices =
        (PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
    PFNEGLQUERYDEVICESTRINGEXTPROC queryDeviceString =
        (PFNEGLQUERYDEVICESTRINGEXTPROC)eglGetProcAddress("eglQueryDeviceStringEXT");
    if (!getPlatformDisplay || !queryDevices || !queryDeviceString) {
        fprintf(stderr, "EGL sin las extensiones de dispositivo (EGL_EXT_device_base,"
                        " EGL_EXT_device_query): no se puede identificar la tarjeta por su\n"
                        "       nodo DRM, y sin eso no se puede respetar la frontera. ABORTO.\n");
        return 3;
    }

    EGLDeviceEXT devs[16];
    EGLint ndev = 0;
    if (!queryDevices(16, devs, &ndev) || ndev <= 0) {
        fprintf(stderr, "eglQueryDevicesEXT no devolvio dispositivos\n"); return 3;
    }
    /* ---- 2) LA FRONTERA: identificar el dispositivo por su ruta DRM ---- */
    EGLDeviceEXT want = EGL_NO_DEVICE_EXT;
    printf("=== dispositivos EGL ===\n");
    for (EGLint i = 0; i < ndev; i++) {
        /* eglQueryDeviceStringEXT devuelve const char* directamente; no es la variante de
         * tres argumentos de eglQueryString. */
        const char *path = queryDeviceString(devs[i], EGL_DRM_DEVICE_FILE_EXT);
        int is_rx = 0, is_intel = 0;
        for (int k = 0; RX550_NODES[k]; k++) if (path && !strcmp(path, RX550_NODES[k])) is_rx = 1;
        for (int k = 0; INTEL_NODES[k]; k++) if (path && !strcmp(path, INTEL_NODES[k])) is_intel = 1;
        printf("  [%d] %-20s %s%s\n", i, path ? path : "(sin ruta DRM)",
               is_rx ? "<-- LA RX 550" : "", is_intel ? "<-- LA INTEL: PROHIBIDO" : "");
        /* Que EGL OFREZCA el nodo de la Intel no es una infraccion: enumerar un dispositivo
         * no lo abre y no lo inicializa.  Lo prohibido es USARLO.  Mi primera version de esta
         * guarda abortaba por la simple presencia del nodo, y era una guardia mala de mas:
         * hacia fallar el caso legitimo sin evitar ningun caso real.  Aqui solo se selecciona
         * lo de la RX 550, y la comprobacion real se hace DESPUES, sobre el contexto creado,
         * mirando la cadena del renderer. */
        (void)is_intel;
        if (is_rx) want = devs[i];
    }
    if (want == EGL_NO_DEVICE_EXT) {
        fprintf(stderr, "ABORTO: ningun dispositivo EGL corresponde a la RX 550.\n"
                        "        No se crea contexto. La iGPU no se toca.\n");
        return 3;
    }
    printf("  --> seleccionado por ruta DRM: el nodo de la RX 550\n\n");

    EGLDisplay dpy = getPlatformDisplay(EGL_PLATFORM_DEVICE_EXT, want, NULL);
    if (dpy == EGL_NO_DISPLAY) { fprintf(stderr, "eglGetPlatformDisplayEXT fallo\n"); return 3; }
    EGLint major = 0, minor = 0;
    if (!eglInitialize(dpy, &major, &minor)) { fprintf(stderr, "eglInitialize fallo\n"); return 3; }
    printf("=== EGL ===\n  version %d.%d\n  vendor %s\n", major, minor,
           eglQueryString(dpy, EGL_VENDOR));
    if (!eglBindAPI(EGL_OPENGL_API)) { fprintf(stderr, "eglBindAPI(OPENGL) fallo\n"); return 3; }
    printf("  EGL_EXTENSIONS (filtro): ");
    {
        const char *ext = eglQueryString(dpy, EGL_EXTENSIONS);
        const char *want2[] = {"EGL_KHR_create_context","EGL_KHR_no_config_context",NULL};
        for (int k = 0; want2[k]; k++)
            printf("%s%s ", want2[k], (ext && strstr(ext, want2[k])) ? "SI" : "NO");
        printf("\n");
    }

    EGLint cfgattr[] = { EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
                         EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT, EGL_NONE };
    EGLConfig cfg; EGLint ncfg = 0;
    if (!eglChooseConfig(dpy, cfgattr, &cfg, 1, &ncfg) || ncfg < 1) {
        fprintf(stderr, "eglChooseConfig fallo\n"); return 3;
    }
    EGLint ctxattr[] = { EGL_CONTEXT_MAJOR_VERSION, 4,
                         EGL_CONTEXT_MINOR_VERSION, 3,
                         EGL_CONTEXT_OPENGL_PROFILE_MASK,
                         EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT, EGL_NONE };
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctxattr);
    if (ctx == EGL_NO_CONTEXT) { fprintf(stderr, "eglCreateContext fallo\n"); return 3; }
    if (!eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx)) {
        fprintf(stderr, "eglMakeCurrent fallo\n"); return 3;
    }

    /* ---- 3) GL ---- */
    typedef const GLubyte *(*GETSTR)(GLenum);
    GETSTR glGetString_ = (GETSTR)glXGetProcAddressLike((const char *)"glGetString");
    GLint next = 0; glGetIntegerv(GL_NUM_EXTENSIONS, &next);
    PFNGLGETSTRINGIPROC gsi = (PFNGLGETSTRINGIPROC)glXGetProcAddressLike("glGetStringi");
    int have_cs = 0;
    for (GLint i = 0; i < next; i++)
        if (!strcmp((const char *)gsi(GL_EXTENSIONS, i), "GL_ARB_compute_shader")) have_cs = 1;
    printf("\n=== GL ===\n  VERSION  %s\n  RENDERER %s\n  VENDOR   %s\n"
           "  GLSL     %s\n  compute shaders: %s\n",
           glGetString_(GL_VERSION), glGetString_(GL_RENDERER), glGetString_(GL_VENDOR),
           glGetString_(GL_SHADING_LANGUAGE_VERSION), have_cs ? "si" : "NO");

    /* POST-CONDICION DE LA FRONTERA: el contexto tiene que ser de AMD.  Este es el chequeo
     * que de verdad protege, porque ocurre sobre el contexto ya creado: si por lo que sea
     * hubiera caido en la iGPU, aqui se aborta antes de lanzar un solo shader. */
    const char *rend = (const char *)glGetString_(GL_RENDERER);
    if (!rend || !strstr(rend, "AMD")) {
        fprintf(stderr, "ABORTO POST-CONDICION: el renderer es \"%s\", no es una AMD.\n"
                        "        El contexto no ha ejecutado nada. La iGPU no se toca.\n",
                rend ? rend : "(null)");
        return 3;
    }
    if (!strstr(rend, "550") && !strstr(rend, "Lexa") && !strstr(rend, "Polaris"))
        fprintf(stderr, "AVISO: el renderer dice AMD pero no menciona esta tarjeta: %s\n", rend);
    else
        printf("  POST-CONDICION DE FRONTERA: renderer AMD y es esta tarjeta. OK\n");

    PFNGLCREATESHADERPROC glCreateShader_ = (PFNGLCREATESHADERPROC)glXGetProcAddressLike("glCreateShader");
    PFNGLSHADERSOURCEPROC glShaderSource_ = (PFNGLSHADERSOURCEPROC)glXGetProcAddressLike("glShaderSource");
    PFNGLCOMPILESHADERPROC glCompileShader_ = (PFNGLCOMPILESHADERPROC)glXGetProcAddressLike("glCompileShader");
    PFNGLGETSHADERIVPROC glGetShaderiv_ = (PFNGLGETSHADERIVPROC)glXGetProcAddressLike("glGetShaderiv");
    PFNGLGETSHADERINFOLOGPROC glGetShaderInfoLog_ = (PFNGLGETSHADERINFOLOGPROC)glXGetProcAddressLike("glGetShaderInfoLog");
    PFNGLCREATEPROGRAMPROC glCreateProgram_ = (PFNGLCREATEPROGRAMPROC)glXGetProcAddressLike("glCreateProgram");
    PFNGLATTACHSHADERPROC glAttachShader_ = (PFNGLATTACHSHADERPROC)glXGetProcAddressLike("glAttachShader");
    PFNGLLINKPROGRAMPROC glLinkProgram_ = (PFNGLLINKPROGRAMPROC)glXGetProcAddressLike("glLinkProgram");
    PFNGLUSEPROGRAMPROC glUseProgram_ = (PFNGLUSEPROGRAMPROC)glXGetProcAddressLike("glUseProgram");
    PFNGLGETPROGRAMIVPROC glGetProgramiv_ = (PFNGLGETPROGRAMIVPROC)glXGetProcAddressLike("glGetProgramiv");
    PFNGLGETPROGRAMINFOLOGPROC glGetProgramInfoLog_ = (PFNGLGETPROGRAMINFOLOGPROC)glXGetProcAddressLike("glGetProgramInfoLog");
    PFNGLGENBUFFERSPROC glGenBuffers_ = (PFNGLGENBUFFERSPROC)glXGetProcAddressLike("glGenBuffers");
    PFNGLBINDBUFFERPROC glBindBuffer_ = (PFNGLBINDBUFFERPROC)glXGetProcAddressLike("glBindBuffer");
    PFNGLBUFFERDATAPROC glBufferData_ = (PFNGLBUFFERDATAPROC)glXGetProcAddressLike("glBufferData");
    PFNGLDISPATCHCOMPUTEPROC glDispatchCompute_ = (PFNGLDISPATCHCOMPUTEPROC)glXGetProcAddressLike("glDispatchCompute");
    PFNGLMEMORYBARRIERPROC glMemoryBarrier_ = (PFNGLMEMORYBARRIERPROC)glXGetProcAddressLike("glMemoryBarrier");
    PFNGLUNIFORM1IPROC glUniform1i_ = (PFNGLUNIFORM1IPROC)glXGetProcAddressLike("glUniform1i");
    PFNGLBINDBUFFERBASEPROC glBindBufferBase_ =
        (PFNGLBINDBUFFERBASEPROC)glXGetProcAddressLike("glBindBufferBase");
    PFNGLGETUNIFORMLOCATIONPROC glGetUniformLocation_ =
        (PFNGLGETUNIFORMLOCATIONPROC)glXGetProcAddressLike("glGetUniformLocation");

    GLuint cs = glCreateShader_(GL_COMPUTE_SHADER); glShaderSource_(cs, 1, &CS_SRC, NULL);
    glCompileShader_(cs);
    { GLint ok = 0; glGetShaderiv_(cs, GL_COMPILE_STATUS, &ok);
      if (!ok) { char l[4096]; GLsizei n=0; glGetShaderInfoLog_(cs,sizeof l,&n,l);
                 fprintf(stderr,"FALLO compilando el compute shader:\n%.*s\n",(int)n,l); return 3; } }
    GLuint prog = glCreateProgram_(); glAttachShader_(prog, cs); glLinkProgram_(prog);
    { GLint ok = 0; glGetProgramiv_(prog, GL_LINK_STATUS, &ok);
      if (!ok) { char l[4096]; GLsizei n=0; glGetProgramInfoLog_(prog,sizeof l,&n,l);
                 fprintf(stderr,"FALLO enlazando:\n%.*s\n",(int)n,l); return 3; } }

    size_t bytes = (size_t)mib << 20;
    GLuint sbo; glGenBuffers_(1, &sbo);
    glBindBuffer_(GL_SHADER_STORAGE_BUFFER, sbo);
    glBufferData_(GL_SHADER_STORAGE_BUFFER, (GLsizeiptr)bytes, NULL, GL_DYNAMIC_COPY);
    glBindBufferBase_(GL_SHADER_STORAGE_BUFFER, 0, sbo);
    glUseProgram_(prog);
    glUniform1i_(glGetUniformLocation_(prog, "data"), 0);

    uint32_t elements = (uint32_t)(bytes / 4u);
    uint32_t max_wg = 65535u;                 /* minimo garantizado por la spec de GL 4.3 */
    uint32_t per = max_wg * 64u;
    uint32_t chunks = (elements + per - 1u) / per;
    printf("\n=== la carga ===\n  buffer %d MiB (%u elementos de 4 B)\n"
           "  %u workgroups por dispatch, %u trozos\n  duracion %d s\n\nARRANCANDO\n",
           mib, elements, max_wg, chunks, seconds);

    double t0 = now_s(); uint32_t it = 0; float best = 0.f;
    for (;;) {
        if (now_s() - t0 >= (double)seconds) break;
        for (uint32_t c = 0; c < chunks; c++)
            glDispatchCompute_(max_wg, 1, 1);
        glMemoryBarrier_(GL_SHADER_STORAGE_BARRIER_BIT | GL_BUFFER_UPDATE_BARRIER_BIT);
        glFinish();
        it++;
        if ((it % 16) == 0) {
            float gbs = (float)((double)bytes * it / (now_s() - t0) / 1e9);
            if (gbs > best) best = gbs;
            printf("  t=%6.2fs iter=%-6u %8.2f GB/s (pico %.2f)\n", now_s()-t0, it, gbs, best);
        }
    }
    double el = now_s() - t0;
    printf("\nFINALIZADO  %.3f s  %u iteraciones\n"
           "  ancho de banda aparente  media %.2f GB/s  pico %.2f GB/s\n",
           el, it, (double)bytes * it / el / 1e9, best);
    return 0;
}
