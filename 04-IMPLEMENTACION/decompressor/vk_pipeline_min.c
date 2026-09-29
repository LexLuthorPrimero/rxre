/* Diagnostic probe, NOT part of the agreement test.
 *
 * vk_pipeline_min.c -- minimal isolated reproduction of the SIGSEGV observed
 * inside vkCreateComputePipelines() when called from test_decompress.c.
 *
 * Order of operations here is deliberately minimal:
 *     instance -> physical device -> device -> shader module
 *              -> pipeline layout -> COMPUTE PIPELINE
 * There is no corpus, no buffer, no descriptor pool and no command buffer, so
 * nothing this probe does can corrupt driver state before the failing call.
 *
 * Usage: ./vk_pipeline_min <shader.spv>
 * Exit 0 = pipeline created, 139 = SIGSEGV, 2 = setup failure.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <signal.h>
#include <unistd.h>
#include <execinfo.h>

typedef struct VkInstance_T* VkInstance;
typedef struct VkPhysicalDevice_T* VkPhysicalDevice;
typedef struct VkDevice_T* VkDevice;
typedef struct VkShaderModule_T* VkShaderModule;
typedef struct VkPipeline_T* VkPipeline;
typedef struct VkPipelineLayout_T* VkPipelineLayout;
typedef struct VkDescriptorSetLayout_T* VkDescriptorSetLayout;

typedef struct { uint32_t sType; const void* pNext; } VkBase;

typedef struct {
    VkBase b;
    const char* pApplicationName; uint32_t applicationVersion;
    const char* pEngineName;       uint32_t engineVersion; uint32_t apiVersion;
} VkApplicationInfo;
typedef struct {
    VkBase b; uint32_t flags; const VkApplicationInfo* pApplicationInfo;
    uint32_t enabledLayerCount; const char* const* ppEnabledLayerNames;
    uint32_t enabledExtensionCount; const char* const* ppEnabledExtensionNames;
} VkInstanceCreateInfo;
typedef struct {
    VkBase b; uint32_t flags; uint32_t queueFamilyIndex;
    uint32_t queueCount; const float* pQueuePriorities;
} VkDeviceQueueCreateInfo;
typedef struct {
    VkBase b; uint32_t flags; uint32_t queueCreateInfoCount;
    const VkDeviceQueueCreateInfo* pQueueCreateInfos;
    uint32_t enabledLayerCount; const char* const* ppEnabledLayerNames;
    uint32_t enabledExtensionCount; const char* const* ppEnabledExtensionNames;
    const void* pEnabledFeatures;
} VkDeviceCreateInfo;
typedef struct {
    VkBase b; uint32_t flags; size_t codeSize; const uint32_t* pCode;
} VkShaderModuleCreateInfo;
typedef struct {
    uint32_t binding, descriptorType, descriptorCount, stageFlags;
    const void* pImmutableSamplers;
} VkDescriptorSetLayoutBinding;
typedef struct {
    VkBase b; uint32_t flags, bindingCount;
    const VkDescriptorSetLayoutBinding* pBindings;
} VkDescriptorSetLayoutCreateInfo;
typedef struct { uint32_t stageFlags, offset, size; } VkPushConstantRange;
typedef struct {
    VkBase b; uint32_t flags, setLayoutCount;
    const VkDescriptorSetLayout* pSetLayouts;
    uint32_t pushConstantRangeCount; const void* pPushConstantRanges;
} VkPipelineLayoutCreateInfo;
typedef struct {
    uint32_t sType; const void* pNext; uint32_t stageFlags;
    VkShaderModule module; const char* pName; const void* pSpecializationInfo;
} VkPipelineShaderStageCreateInfo;
typedef struct {
    VkBase b; uint32_t flags; VkPipelineShaderStageCreateInfo stage;
    VkPipelineLayout layout; VkPipeline basePipelineHandle; int32_t basePipelineIndex;
} VkComputePipelineCreateInfo;

#define E_SZ sizeof(VkComputePipelineCreateInfo)
#define E_STAGE_OFF offsetof(VkComputePipelineCreateInfo, stage)
#define E_LAYOUT_OFF offsetof(VkComputePipelineCreateInfo, layout)
#define E_BPI_OFF offsetof(VkComputePipelineCreateInfo, basePipelineIndex)
#include <stddef.h>

static int  (*vkCreateInstance)(const VkInstanceCreateInfo*, const void*, VkInstance*);
static int  (*vkEnumeratePhysicalDevices)(VkInstance, uint32_t*, VkPhysicalDevice*);
static void (*vkGetPhysicalDeviceProperties)(VkPhysicalDevice, void*);
static int  (*vkCreateDevice)(VkPhysicalDevice, const VkDeviceCreateInfo*, const void*, VkDevice*);
static int  (*vkCreateShaderModule)(VkDevice, const VkShaderModuleCreateInfo*, const void*, VkShaderModule*);
static int  (*vkCreateDescriptorSetLayout)(VkDevice, const VkDescriptorSetLayoutCreateInfo*, const void*, VkDescriptorSetLayout*);
static int  (*vkCreatePipelineLayout)(VkDevice, const VkPipelineLayoutCreateInfo*, const void*, VkPipelineLayout*);
static int  (*vkCreateComputePipelines)(VkDevice, void*, uint32_t, const VkComputePipelineCreateInfo*, const void*, VkPipeline*);
/* Control: mismo estilo de declaracion a mano, pero ruta de GRAFICOS. */
typedef struct {
    uint32_t sType; const void* pNext; uint32_t stageFlags;
    VkShaderModule module; const char* pName; const void* pSpecializationInfo;
} VkGfxStage;
typedef struct {
    VkBase b; uint32_t flags; VkGfxStage stage; VkPipelineLayout layout;
    uint32_t subpass; VkPipeline basePipelineHandle; int32_t basePipelineIndex;
} VkGraphicsPipelineCreateInfo;
static int (*vkCreateGraphicsPipelines)(VkDevice, void*, uint32_t, const VkGraphicsPipelineCreateInfo*, const void*, VkPipeline*);

#define VK_SUCCESS 0

static void segv(int sig, siginfo_t *si, void *uc)
{
    char buf[1 << 16];
    int fd = open("/proc/self/maps", 0);
    ssize_t n = (fd >= 0) ? read(fd, buf, sizeof buf - 1) : -1;
    if (fd >= 0) close(fd);
    if (n > 0) buf[n] = 0;
    {
        void *bt[64]; int nb = backtrace(bt, 64);
        fprintf(stderr, "*** SIGSEGV addr=%p si_code=%d  backtrace=%d frames\n", si->si_addr, si->si_code, nb);
        for (int k = 0; k < nb; k++) {
            Dl_info di;
            if (dladdr(bt[k], &di) && di.dli_sname)
                fprintf(stderr, "***   #%-2d %s  [%s +0x%lx]\n", k, di.dli_sname,
                        di.dli_fname ? di.dli_fname : "?", (unsigned long)((char*)bt[k]-(char*)di.dli_fbase));
            else if (dladdr(bt[k], &di))
                fprintf(stderr, "***   #%-2d %s +0x%lx  (sin simbolo)\n", k,
                        di.dli_fname ? di.dli_fname : "?", (unsigned long)((char*)bt[k]-(char*)di.dli_fbase));
            else
                fprintf(stderr, "***   #%-2d %p (sin modulo)\n", k, bt[k]);
        }
    }
    fprintf(stderr, "*** SIGSEGV addr=%p si_code=%d\n", si->si_addr, si->si_code);
    fprintf(stderr, "*** mapa (contexto, ultimas 25 lineas):\n");
    { char *p = buf, *e; int k = 0;
      while (p && *p && k < 25) {
          e = strchr(p, '\n'); if (!e) break; *e++ = 0;
          fprintf(stderr, "***   %s\n", p); p = e; k++;
      }
      fprintf(stderr, "*** (mapa tiene %d lineas mostradas)\n", k);
    }
    _exit(139);
}

int main(int argc, char **argv)
{
    const char *path = (argc > 1) ? argv[1] : "decompress_bc3.spv";
    struct sigaction sa; memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = segv; sa.sa_flags = SA_SIGINFO;
    sigaction(SIGSEGV, &sa, NULL);

    void *h = dlopen("/usr/lib64/libvulkan.so.1", RTLD_NOW);
    if (!h) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 2; }
    #define S(v,n) do { void *p = dlsym(h, n); if (!p) { fprintf(stderr, "falta %s\n", n); return 2; } \
                        *(void**)&v = p; } while (0)
    S(vkCreateInstance,"vkCreateInstance");
    S(vkEnumeratePhysicalDevices,"vkEnumeratePhysicalDevices");
    S(vkGetPhysicalDeviceProperties,"vkGetPhysicalDeviceProperties");
    S(vkCreateDevice,"vkCreateDevice");
    S(vkCreateShaderModule,"vkCreateShaderModule");
    S(vkCreateDescriptorSetLayout,"vkCreateDescriptorSetLayout");
    S(vkCreatePipelineLayout,"vkCreatePipelineLayout");
    S(vkCreateComputePipelines,"vkCreateComputePipelines");
    S(vkCreateGraphicsPipelines,"vkCreateGraphicsPipelines");
    {
        Dl_info di;
        #define SHOW(v,n) if (dladdr((void*)v,&di)) \
            printf("  %-32s -> %s +0x%lx\n", n, di.dli_fname?di.dli_fname:"?", \
                   (unsigned long)((char*)v-(char*)di.dli_fbase)); \
            else printf("  %-32s -> FUERA DE TODA LIBRERIA\n", n);
        SHOW(vkCreateInstance,"vkCreateInstance")
        SHOW(vkCreateDevice,"vkCreateDevice")
        SHOW(vkCreateShaderModule,"vkCreateShaderModule")
        SHOW(vkCreateDescriptorSetLayout,"vkCreateDescriptorSetLayout")
        SHOW(vkCreatePipelineLayout,"vkCreatePipelineLayout")
        SHOW(vkCreateComputePipelines,"vkCreateComputePipelines")
        #undef SHOW
    }

    printf("layout: size=%zu stage@%zu layout@%zu basePipelineIndex@%zu (esperado 96/24/72/88)\n",
           E_SZ, E_STAGE_OFF, E_LAYOUT_OFF, E_BPI_OFF);

    VkApplicationInfo app = { {0,0}, "vkmin", 1, "rx550", 1, (1u<<22)|(3u<<12) };
    VkInstanceCreateInfo ici = { {1,0}, 0, &app, 0,0, 0,0 };
    VkInstance inst = NULL;
    if (vkCreateInstance(&ici, NULL, &inst) != VK_SUCCESS) { fprintf(stderr,"instance\n"); return 2; }

    unsigned char props[4096]; uint32_t n = 0, i; VkPhysicalDevice pd = NULL;
    vkEnumeratePhysicalDevices(inst, &n, NULL);
    VkPhysicalDevice *devs = calloc(n, sizeof *devs);
    vkEnumeratePhysicalDevices(inst, &n, devs);
    /* argv[2]=="lvp" -> fuerza lavapipe (llvmpipe). Mismo codigo, otro ICD:
     * separa "mi declaracion de Vulkan es incorrecta" de "RADV falla aqui". */
    int want_lvp = (argc > 2 && !strcmp(argv[2], "lvp"));
    for (i = 0; i < n; i++) {
        uint32_t ven, dev; memset(props,0,sizeof props);
        vkGetPhysicalDeviceProperties(devs[i], props);
        memcpy(&ven, props+8, 4); memcpy(&dev, props+12, 4);
        int is_rx = (ven == 0x1002 && dev == 0x699F);
        int is_lvp = (ven == 0x10005);
        if ((want_lvp && is_lvp) || (!want_lvp && is_rx)) {
            pd = devs[i];
            printf("device: %.*s (vendor=0x%x device=0x%x)\n", 40, (char*)(props+20), ven, dev);
            break;
        }
    }
    free(devs);
    if (!pd) { fprintf(stderr, "device no encontrado\n"); return 2; }

    float prio = 1.0f;
    VkDeviceQueueCreateInfo q = { {2,0}, 0, 0, 1, &prio };
    VkDeviceCreateInfo dc = { {3,0}, 0, 1, &q, 0,0, 0,0, NULL };
    VkDevice devh = NULL;
    if (vkCreateDevice(pd, &dc, NULL, &devh) != VK_SUCCESS) { fprintf(stderr,"device\n"); return 2; }
    printf("device logico creado\n");

    FILE *f = fopen(path, "rb"); if (!f) { fprintf(stderr,"abrir %s\n", path); return 2; }
    fseek(f,0,SEEK_END); long sz = ftell(f); fseek(f,0,SEEK_SET);
    uint32_t *code = malloc(sz); if (fread(code,1,sz,f) != (size_t)sz) return 2; fclose(f);
    printf("SPIR-V: %ld B, magic=0x%08x\n", sz, code[0]);

    VkShaderModuleCreateInfo sm = { {16,0}, 0, (size_t)sz, code };
    VkShaderModule mod = NULL;
    if (vkCreateShaderModule(devh, &sm, NULL, &mod) != VK_SUCCESS) { fprintf(stderr,"module\n"); return 2; }
    printf("shader module creado\n");

    VkDescriptorSetLayoutBinding binds[2]; memset(binds,0,sizeof binds);
    for (int k = 0; k < 2; k++) {
        binds[k].binding = (uint32_t)k; binds[k].descriptorType = 1;
        binds[k].descriptorCount = 1; binds[k].stageFlags = 0x20;
    }
    VkDescriptorSetLayoutCreateInfo dslci = { {32,0}, 0, 2, binds };
    VkDescriptorSetLayout dsl = NULL;
    if (vkCreateDescriptorSetLayout(devh, &dslci, NULL, &dsl) != VK_SUCCESS) { fprintf(stderr,"dsl\n"); return 2; }
    printf("descriptor set layout creado\n");

    int min_mode = (argc > 4 && !strcmp(argv[4], "min"));
    VkPushConstantRange pcr = { 0x20, 0, 4 };
    VkPipelineLayoutCreateInfo plci = min_mode
        ? (VkPipelineLayoutCreateInfo){ {30,0}, 0, 0, NULL, 0, NULL }
        : (VkPipelineLayoutCreateInfo){ {30,0}, 0, 1, &dsl, 1, &pcr };
    if (min_mode) {
        VkDescriptorSetLayoutCreateInfo e = { {32,0}, 0, 0, NULL };
    }
    VkPipelineLayout playout = NULL;
    if (vkCreatePipelineLayout(devh, &plci, NULL, &playout) != VK_SUCCESS) { fprintf(stderr,"playout\n"); return 2; }
    printf("pipeline layout creado\n");

    VkComputePipelineCreateInfo cpci; memset(&cpci, 0, sizeof cpci);
    /* argv[3] = sType del shader stage. 1 = INSTANCE_CREATE_INFO (lo que
     * usaba antes, un valor equivocado); 17 = SHADER_STAGE_CREATE_INFO. */
    uint32_t stage_sType = (argc > 3) ? (uint32_t)strtoul(argv[3], NULL, 0) : 17u;
    int fill = (argc > 6) ? atoi(argv[6]) : 99;
    printf("stage.sType = %u   fill = %d\n", stage_sType, fill);
    cpci.b.sType = 39;
    if (fill >= 1) cpci.stage.sType = stage_sType;
    if (fill >= 2) cpci.stage.stageFlags = 0x4;
    if (fill >= 3) cpci.stage.module = mod;
    if (fill >= 4) cpci.stage.pName = "main";
    if (fill >= 5) cpci.layout = playout;
    if (fill >= 6) cpci.basePipelineIndex = -1;
    printf("cpci: sType=%u stage.sType=%u stageFlags=%u module=%p pName=%p layout=%p bpi=%d\n",
           cpci.b.sType, cpci.stage.sType, cpci.stage.stageFlags, (void*)cpci.stage.module,
           (void*)cpci.stage.pName, (void*)cpci.layout, cpci.basePipelineIndex);
    printf("-> vkCreateComputePipelines (nada ejecutado antes de esta linea)\n");
    fflush(stdout);

    VkPipeline pipe = NULL;

    /* argv[5]="zero" : count=0 y pCreateInfos=NULL. El driver NO PUEDE leer
     * ningun byte mio. Si aun asi revienta con la MISMA direccion, el fallo no
     * depende de lo que yo pase: es incondicionado. */
    if (argc > 5 && !strcmp(argv[5], "zero")) {
        printf("-> vkCreateComputePipelines(count=0, pCreateInfos=NULL)\n"); fflush(stdout);
        int z = vkCreateComputePipelines(devh, NULL, 0, NULL, NULL, &pipe);
        printf("-> count=0 devolvio rc=%d SIN SEGFAULT\n", z); return 0;
    }
    if (argc > 5 && !strcmp(argv[5], "gfxzero")) {
        printf("-> vkCreateGraphicsPipelines(count=0, pCreateInfos=NULL)\n"); fflush(stdout);
        int z = vkCreateGraphicsPipelines(devh, NULL, 0, NULL, NULL, &pipe);
        printf("-> graficos count=0 devolvio rc=%d SIN SEGFAULT\n", z); return 0;
    }
    int rc = vkCreateComputePipelines(devh, NULL, 1, &cpci, NULL, &pipe);
    printf("-> vkCreateComputePipelines rc=%d pipe=%p  SIN SEGFAULT\n", rc, (void*)pipe);
    return 0;
}
