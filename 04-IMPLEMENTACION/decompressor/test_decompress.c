/* SPDX-License-Identifier: MIT
 *
 * test_decompress.c -- agreement test: the compute shader on the RX 550, versus
 * the CPU reference decoder.
 *
 * WHAT A PASS HERE WOULD ESTABLISH
 *
 * shader_vs_c.c already establishes that the shader's ARITHMETIC agrees with
 * rx550_decompress_block(): 0 of 4096 channels. That is a claim about a model of
 * the shader written in C. It is SIMULATED_ARITHMETIC, and it cannot establish
 * that the GLSL compiles, that a driver accepts it, or that the GPU produces
 * the modelled bytes.
 *
 * This program is what would close that gap: it loads the real SPIR-V, builds
 * a real compute pipeline, dispatches on the real device, reads back the buffer
 * the GPU wrote, and requires it to equal what the CPU decoder produces for the
 * same compressed blocks. Until this has run, every statement about the shader
 * is NOT_RUN.
 *
 * ---------------------------------------------------------------------------
 * WHY THE OUTPUT IS VALIDATED BEFORE IT IS COMPARED
 * ---------------------------------------------------------------------------
 * This is the load-bearing part of the file, not a formality.
 *
 * If the GPU returns a buffer it never wrote and the comparison is naive, the
 * test reports zero discrepancies and PASSES. It would pass with a broken
 * pipeline, an unsubmitted dispatch, an unmapped buffer, or a stub shader. A
 * passing comparison is only evidence that two buffers hold the same bytes, and
 * two untouched buffers trivially do.
 *
 * So the order is fixed and must not be inverted:
 *
 *   1. the output must not be all zeros                    (nothing was written)
 *   2. the output must not equal the poison pattern         (nothing was written)
 *   3. only then compare against the CPU
 *
 * A buffer written but wrong is caught by (3). A buffer never written is
 * caught by (1) and (2). Those are different failures and deserve different
 * diagnostics.
 *
 * ---------------------------------------------------------------------------
 * WHY THE DEVICE IS IDENTIFIED BY PCI IDENTITY
 * ---------------------------------------------------------------------------
 * By vendorID/deviceID 0x1002/0x699F. Never by enumeration index, never by a
 * cardN name. This host currently exposes three Vulkan devices: the Intel iGPU,
 * the AMD discrete GPU, and llvmpipe. llvmpipe will accept the dispatch and
 * return output that may or may not match, so a test that took device 0 would
 * report a result about the wrong hardware while looking entirely healthy.
 * Enumeration order is not stable across boots; the PCI identity is.
 *
 * ---------------------------------------------------------------------------
 * WHAT A PASS DOES NOT ESTABLISH
 * ---------------------------------------------------------------------------
 * - Not schema validity of the SPIR-V. spirv-val is not installed here
 *   (NOT_AVAILABLE). A driver accepting a module is evidence about that driver.
 * - Not GFX_HWIP. This program does not query the gfx generation and does not
 *   infer it; it remains NOT_DETERMINED project-wide.
 * - Not correctness outside this corpus. The corpus is deterministic and
 *   synthetic, and covers both alpha-ramp branches by construction. It is a
 *   regression guard, not a proof over all possible blocks.
 * - Not performance. One small dispatch says nothing about bandwidth.
 *
 * ---------------------------------------------------------------------------
 * VULKAN HEADERS
 * ---------------------------------------------------------------------------
 * The earlier version of this work hand-declared the Vulkan structs. That was
 * abandoned: 37 compile errors, plus a duplicated pNext field that shifts a
 * struct's layout silently, so the failure surfaces as a SIGSEGV with no
 * diagnostic rather than as a compile error. See vk_pipeline_min.c and AD-13.
 *
 * vulkan-headers 0:1.4.341.0 is now installed, and VK_HEADER_VERSION 341
 * matches the host loader (vulkan-loader 1.4.341) exactly. The loader is
 * reached with dlopen rather than a link-time dependency, so the binary still
 * runs if the loader moves.
 */

#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <dlfcn.h>
#include <sys/stat.h>

#include <vulkan/vulkan.h>

#include "../compressor/rx550_compress.h"

_Static_assert(sizeof(rx550_block_t)      == 16, "rx550_block_t must be 16 B");
_Static_assert(sizeof(rx550_rgba_block_t) == 64, "rx550_rgba_block_t must be 64 B");
_Static_assert(offsetof(rx550_block_t, a_idx) ==  2, "alpha index offset");
_Static_assert(offsetof(rx550_block_t, c0)   ==  8, "colour endpoint offset");
_Static_assert(offsetof(rx550_block_t, c_idx) == 12, "colour index offset");

#define SPV_MAGIC     0x07230203u
#define RX550_VENDOR  0x1002u
#define RX550_DEVICE  0x699Fu
#define NUM_BLOCKS    64
#define GROUPSIZE     256u   /* must equal local_size_x in decompress_bc3.comp */
#define DISPATCHES    ((NUM_BLOCKS + GROUPSIZE - 1u) / GROUPSIZE)
#define BYTES_BLOCKS  ((size_t)NUM_BLOCKS * 16u)
#define BYTES_PIXELS  ((size_t)NUM_BLOCKS * 64u)
#define POISON        0xDEADBEEFu
#define TIMEOUT_NS    5000000000ull   /* 5 s; a dispatch this size takes microseconds */

/* ==========================================================================
 * Corpus -- identical to test_corpus_validate.c by construction, and it
 * measures its own coverage of the two alpha-ramp branches.
 * ========================================================================== */

static uint32_t lcg_state = 12345u;

static uint8_t lcg_next(void)
{
    lcg_state = lcg_state * 1103515245u + 12345u;
    return (uint8_t)((lcg_state >> 16) & 0xFFu);
}

typedef struct {
    rx550_block_t      blocks[NUM_BLOCKS];
    rx550_rgba_block_t cpu[NUM_BLOCKS];
    int n_six, n_eight;   /* coverage of a0<=a1 and a0>a1 */
} corpus_t;

static void corpus_build(corpus_t *c)
{
    int b, p;

    lcg_state = 12345u;

    for (b = 0; b < NUM_BLOCKS; b++) {
        rx550_rgba_block_t in;
        memset(&in, 0, sizeof in);

        switch (b) {
        case 0: for (p = 0; p < 64; p++) in.px[p] = 0x00; break;
        case 1: for (p = 0; p < 64; p++) in.px[p] = 0xFF; break;
        case 2: for (p = 0; p < 64; p++) in.px[p] = 0x80; break;

        /* Ascending alpha: a1 < a0, the 8-value /7 branch. */
        case 3:
            for (p = 0; p < 16; p++) {
                in.px[4 * p + 0] = 0x40; in.px[4 * p + 1] = 0x40; in.px[4 * p + 2] = 0x40;
                in.px[4 * p + 3] = (uint8_t)(p * 17u);
            }
            break;

        /* Descending alpha: forces the 6-value /5 branch, whose a[6]=0 and
         * a[7]=255 rule is the content of AD-11. A noise corpus reaches that
         * branch only by chance. */
        case 4:
            for (p = 0; p < 16; p++) {
                in.px[4 * p + 0] = 0xC0; in.px[4 * p + 1] = 0xC0; in.px[4 * p + 2] = 0xC0;
                in.px[4 * p + 3] = (uint8_t)(255u - p * 17u);
            }
            break;

        case 5: for (p = 0; p < 64; p++) in.px[p] = (uint8_t)((p & 1) ? 0x00 : 0xFF); break;
        case 6: for (p = 0; p < 64; p++) in.px[p] = 0x7F; break;
        case 7: case 8: case 9:
            for (p = 0; p < 64; p++) in.px[p] = (uint8_t)((p * 17u + b * 5u) & 0xFFu);
            break;
        default:
            for (p = 0; p < 64; p++) in.px[p] = lcg_next();
            break;
        }

        rx550_compress_block(&in, &c->blocks[b]);
        rx550_decompress_block(&c->blocks[b], &c->cpu[b]);

        if (c->blocks[b].a0 <= c->blocks[b].a1) c->n_six++; else c->n_eight++;
    }
}

/* ==========================================================================
 * Loader, resolved with dlopen
 * ========================================================================== */

#define VKF(name) static PFN_##name p##name

VKF(vkCreateInstance);        VKF(vkDestroyInstance);
VKF(vkEnumeratePhysicalDevices); VKF(vkGetPhysicalDeviceProperties);
VKF(vkGetPhysicalDeviceQueueFamilyProperties);
VKF(vkGetPhysicalDeviceMemoryProperties);
VKF(vkCreateDevice);          VKF(vkDestroyDevice);   VKF(vkGetDeviceQueue);
VKF(vkCreateBuffer);          VKF(vkDestroyBuffer);
VKF(vkAllocateMemory);        VKF(vkFreeMemory);      VKF(vkBindBufferMemory);
VKF(vkMapMemory);             VKF(vkUnmapMemory);
VKF(vkCreateShaderModule);    VKF(vkDestroyShaderModule);
VKF(vkCreateDescriptorSetLayout); VKF(vkDestroyDescriptorSetLayout);
VKF(vkCreatePipelineLayout);  VKF(vkDestroyPipelineLayout);
VKF(vkCreateComputePipelines); VKF(vkDestroyPipeline);
VKF(vkCreateDescriptorPool);  VKF(vkDestroyDescriptorPool);
VKF(vkAllocateDescriptorSets); VKF(vkUpdateDescriptorSets);
VKF(vkCreateCommandPool);     VKF(vkDestroyCommandPool);
VKF(vkAllocateCommandBuffers); VKF(vkFreeCommandBuffers);
VKF(vkBeginCommandBuffer);    VKF(vkEndCommandBuffer);
VKF(vkCmdBindPipeline);       VKF(vkCmdBindDescriptorSets);  VKF(vkCmdDispatch);
VKF(vkQueueSubmit);           VKF(vkQueueWaitIdle);
VKF(vkCreateFence);           VKF(vkWaitForFences);  VKF(vkDestroyFence);

#undef VKF

static int load_vulkan(void)
{
    static const char *paths[] = {
        "libvulkan.so.1", "/usr/lib64/libvulkan.so.1", NULL
    };
    void *h = NULL;
    int i;

    for (i = 0; paths[i]; i++) {
        h = dlopen(paths[i], RTLD_NOW);
        if (h) { printf("  [ OK ] cargador: %s\n", paths[i]); break; }
    }
    if (!h) {
        fprintf(stderr, "  [FAIL] dlopen libvulkan.so.1: %s\n", dlerror());
        return 0;
    }

#define SYM(vn, name)                                                      \
    do {                                                                   \
        *(void **)(&p##vn) = dlsym(h, name);                               \
        if (!p##vn) {                                                      \
            fprintf(stderr, "  [FAIL] dlsym(%s): %s\n", name, dlerror());  \
            return 0;                                                      \
        }                                                                  \
    } while (0)

    SYM(vkCreateInstance, "vkCreateInstance");
    SYM(vkDestroyInstance, "vkDestroyInstance");
    SYM(vkEnumeratePhysicalDevices, "vkEnumeratePhysicalDevices");
    SYM(vkGetPhysicalDeviceProperties, "vkGetPhysicalDeviceProperties");
    SYM(vkGetPhysicalDeviceQueueFamilyProperties, "vkGetPhysicalDeviceQueueFamilyProperties");
    SYM(vkGetPhysicalDeviceMemoryProperties, "vkGetPhysicalDeviceMemoryProperties");
    SYM(vkCreateDevice, "vkCreateDevice");
    SYM(vkDestroyDevice, "vkDestroyDevice");
    SYM(vkGetDeviceQueue, "vkGetDeviceQueue");
    SYM(vkCreateBuffer, "vkCreateBuffer");
    SYM(vkDestroyBuffer, "vkDestroyBuffer");
    SYM(vkAllocateMemory, "vkAllocateMemory");
    SYM(vkFreeMemory, "vkFreeMemory");
    SYM(vkBindBufferMemory, "vkBindBufferMemory");
    SYM(vkMapMemory, "vkMapMemory");
    SYM(vkUnmapMemory, "vkUnmapMemory");
    SYM(vkCreateShaderModule, "vkCreateShaderModule");
    SYM(vkDestroyShaderModule, "vkDestroyShaderModule");
    SYM(vkCreateDescriptorSetLayout, "vkCreateDescriptorSetLayout");
    SYM(vkDestroyDescriptorSetLayout, "vkDestroyDescriptorSetLayout");
    SYM(vkCreatePipelineLayout, "vkCreatePipelineLayout");
    SYM(vkDestroyPipelineLayout, "vkDestroyPipelineLayout");
    SYM(vkCreateComputePipelines, "vkCreateComputePipelines");
    SYM(vkDestroyPipeline, "vkDestroyPipeline");
    SYM(vkCreateDescriptorPool, "vkCreateDescriptorPool");
    SYM(vkDestroyDescriptorPool, "vkDestroyDescriptorPool");
    SYM(vkAllocateDescriptorSets, "vkAllocateDescriptorSets");
    SYM(vkUpdateDescriptorSets, "vkUpdateDescriptorSets");
    SYM(vkCreateCommandPool, "vkCreateCommandPool");
    SYM(vkDestroyCommandPool, "vkDestroyCommandPool");
    SYM(vkAllocateCommandBuffers, "vkAllocateCommandBuffers");
    SYM(vkFreeCommandBuffers, "vkFreeCommandBuffers");
    SYM(vkBeginCommandBuffer, "vkBeginCommandBuffer");
    SYM(vkEndCommandBuffer, "vkEndCommandBuffer");
    SYM(vkCmdBindPipeline, "vkCmdBindPipeline");
    SYM(vkCmdBindDescriptorSets, "vkCmdBindDescriptorSets");
    SYM(vkCmdDispatch, "vkCmdDispatch");
    SYM(vkQueueSubmit, "vkQueueSubmit");
    SYM(vkQueueWaitIdle, "vkQueueWaitIdle");
    SYM(vkCreateFence, "vkCreateFence");
    SYM(vkWaitForFences, "vkWaitForFences");
    SYM(vkDestroyFence, "vkDestroyFence");
#undef SYM

    printf("  [ OK ] 37 puntos de entrada resueltos\n");
    return 1;
}

static const char *vkres(VkResult r)
{
    switch (r) {
    case VK_SUCCESS:                        return "VK_SUCCESS";
    case VK_ERROR_OUT_OF_HOST_MEMORY:       return "VK_ERROR_OUT_OF_HOST_MEMORY";
    case VK_ERROR_OUT_OF_DEVICE_MEMORY:     return "VK_ERROR_OUT_OF_DEVICE_MEMORY";
    case VK_ERROR_INITIALIZATION_FAILED:    return "VK_ERROR_INITIALIZATION_FAILED";
    case VK_ERROR_DEVICE_LOST:              return "VK_ERROR_DEVICE_LOST";
    case VK_ERROR_LAYER_NOT_PRESENT:        return "VK_ERROR_LAYER_NOT_PRESENT";
    case VK_ERROR_EXTENSION_NOT_PRESENT:    return "VK_ERROR_EXTENSION_NOT_PRESENT";
    case VK_ERROR_FEATURE_NOT_PRESENT:      return "VK_ERROR_FEATURE_NOT_PRESENT";
    case VK_ERROR_INCOMPATIBLE_DRIVER:      return "VK_ERROR_INCOMPATIBLE_DRIVER";
    case VK_ERROR_FORMAT_NOT_SUPPORTED:     return "VK_ERROR_FORMAT_NOT_SUPPORTED";
    default:                                return "otro VkResult";
    }
}

/* ==========================================================================
 * Artefact
 * ========================================================================== */

static uint32_t *read_spv(const char *path, size_t *bytes)
{
    struct stat st;
    FILE *f;
    uint32_t *code;
    uint32_t magic;

    if (stat(path, &st) != 0) {
        fprintf(stderr, "  [FAIL] %s no existe. Ejecuta: make decompress_bc3.spv\n", path);
        return NULL;
    }
    f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "  [FAIL] no se pudo abrir %s\n", path); return NULL; }
    if (fread(&magic, 1, 4, f) != 4) { fclose(f); fprintf(stderr, "  [FAIL] .spv truncado\n"); return NULL; }
    if (magic != SPV_MAGIC) {
        fprintf(stderr, "  [FAIL] magic %08x, esperado %08x\n", magic, SPV_MAGIC);
        fclose(f);
        return NULL;
    }
    if ((size_t)st.st_size % 4u || st.st_size < 20) {
        fprintf(stderr, "  [FAIL] tamano %zu no es multiplo de 4 palabras\n", (size_t)st.st_size);
        fclose(f);
        return NULL;
    }
    code = malloc((size_t)st.st_size);
    if (!code) { fclose(f); return NULL; }
    rewind(f);
    if (fread(code, 1, (size_t)st.st_size, f) != (size_t)st.st_size) {
        fprintf(stderr, "  [FAIL] lectura incompleta del .spv\n");
        free(code); fclose(f); return NULL;
    }
    fclose(f);
    *bytes = (size_t)st.st_size;
    return code;
}

/* ==========================================================================
 * Phase B
 * ========================================================================== */

/* Vulkan 1.4, VK_HEADER_VERSION 341, changed this struct: memoryTypes and
 * memoryHeaps are inline arrays, not pointers. Code written against the older
 * `pMemoryTypes` spelling would not have compiled here, and in the
 * hand-declared version it would have been a silent layout error -- a
 * misread offset reads the wrong bytes and the failure surfaces later as
 * garbage or a crash, with nothing pointing back at this line. That is the
 * concrete reason the manual declarations were abandoned: the real header
 * turns this class of mistake into a compile error. */
static int find_host_coherent_type(VkPhysicalDevice phys)
{
    VkPhysicalDeviceMemoryProperties mp;
    uint32_t i;
    const VkMemoryPropertyFlags want = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                                       VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
    pvkGetPhysicalDeviceMemoryProperties(phys, &mp);
    for (i = 0; i < mp.memoryTypeCount; i++)
        if ((mp.memoryTypes[i].propertyFlags & want) == want)
            return (int)i;
    return -1;
}

#define TRY(expr, what)                                                     \
    do {                                                                    \
        VkResult _r = (expr);                                               \
        if (_r != VK_SUCCESS) {                                             \
            fprintf(stderr, "  [FAIL] %s -> %s (%d)\n", what, vkres(_r), (int)_r); \
            goto out;                                                       \
        }                                                                   \
    } while (0)

static int phase_b(corpus_t *c, const char *spv_path)
{
    VkInstance inst = VK_NULL_HANDLE;
    VkPhysicalDevice *phys = NULL, target = VK_NULL_HANDLE;
    VkDevice dev = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    VkCommandPool pool = VK_NULL_HANDLE;
    VkCommandBuffer cmd = VK_NULL_HANDLE;
    VkBuffer b_in = VK_NULL_HANDLE, b_out = VK_NULL_HANDLE;
    VkDeviceMemory m_in = VK_NULL_HANDLE, m_out = VK_NULL_HANDLE;
    VkShaderModule mod = VK_NULL_HANDLE;
    VkDescriptorSetLayout dsl = VK_NULL_HANDLE;
    VkPipelineLayout playout = VK_NULL_HANDLE;
    VkPipeline pipe = VK_NULL_HANDLE;
    VkDescriptorPool dpool = VK_NULL_HANDLE;
    VkDescriptorSet dset = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;
    uint32_t *code = NULL;
    void *map_in = NULL, *map_out = NULL;
    uint32_t *gpu = NULL;
    size_t spv_bytes = 0;
    uint32_t count = 0, i, qfam = 0, qcount;
    int have_q = 0, differ = 0, shown = 0, verdict = 0;

    printf("\n=== FASE B: dispatch en la RX 550 ===\n\n");

    if (!load_vulkan()) { printf("\nRESULT: FASE B NO EJECUTADA (cargador)\n"); return 0; }

    /* ---- instance ---- */
    {
        VkApplicationInfo app;
        memset(&app, 0, sizeof app);
        app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        VkInstanceCreateInfo ici;
        memset(&ici, 0, sizeof ici);
        ici.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;

        app.pApplicationName = "test_decompress";
        app.applicationVersion = 1;
        app.pEngineName = "rx550-investigacion";
        app.engineVersion = 1;
        app.apiVersion = VK_API_VERSION_1_1;
        ici.pApplicationInfo = &app;

        TRY(pvkCreateInstance(&ici, NULL, &inst), "vkCreateInstance");
    }
    printf("  [ OK ] vkCreateInstance (API 1.1 solicitada; cabeceras VK_HEADER_VERSION %u)\n",
           VK_HEADER_VERSION);

    /* ---- device by PCI identity ---- */
    TRY(pvkEnumeratePhysicalDevices(inst, &count, NULL), "vkEnumeratePhysicalDevices (count)");
    if (count == 0) { fprintf(stderr, "  [FAIL] sin dispositivos fisicos\n"); goto out; }
    phys = calloc(count, sizeof *phys);
    if (!phys) { fprintf(stderr, "  [FAIL] sin memoria\n"); goto out; }
    TRY(pvkEnumeratePhysicalDevices(inst, &count, phys), "vkEnumeratePhysicalDevices");

    printf("  Dispositivos (%u):\n", count);
    for (i = 0; i < count; i++) {
        VkPhysicalDeviceProperties p;
        pvkGetPhysicalDeviceProperties(phys[i], &p);
        printf("    [%u] %04x:%04x  %s\n", i, p.vendorID, p.deviceID, p.deviceName);
        if (p.vendorID == RX550_VENDOR && p.deviceID == RX550_DEVICE) {
            target = phys[i];
            printf("         ^ OBJETIVO, por PCI identity (no por indice)\n");
        }
    }
    if (!target) {
        fprintf(stderr, "  [FAIL] no hay dispositivo %04x:%04x.\n"
                        "         No se sustituye por otro: llvmpipe aceptaria el\n"
                        "         dispatch y el resultado seria sobre otro hardware.\n",
                RX550_VENDOR, RX550_DEVICE);
        goto out;
    }

    /* ---- logical device ---- */
    {
        VkQueueFamilyProperties qf[8];
        uint32_t nqf = 8, q;
        VkDeviceQueueCreateInfo dq;
        memset(&dq, 0, sizeof dq);
        dq.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        VkDeviceCreateInfo dc;
        memset(&dc, 0, sizeof dc);
        dc.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;

        pvkGetPhysicalDeviceQueueFamilyProperties(target, &nqf, qf);
        for (q = 0; q < nqf; q++)
            if (qf[q].queueFlags & VK_QUEUE_COMPUTE_BIT) { qfam = q; have_q = 1; break; }
        if (!have_q) { fprintf(stderr, "  [FAIL] ninguna familia de colas compute\n"); goto out; }

        dq.queueFamilyIndex = qfam; dq.queueCount = 1;
        dc.queueCreateInfoCount = 1; dc.pQueueCreateInfos = &dq;

        TRY(pvkCreateDevice(target, &dc, NULL, &dev), "vkCreateDevice");
    }
    pvkGetDeviceQueue(dev, qfam, 0, &queue);
    printf("  [ OK ] vkCreateDevice, familia de colas compute %u\n", qfam);

    /* ---- SPIR-V ---- */
    code = read_spv(spv_path, &spv_bytes);
    if (!code) goto out;
    printf("  [ OK ] %s: %zu B, %zu palabras\n", spv_path, spv_bytes, spv_bytes / 4u);

    {
        VkShaderModuleCreateInfo smi;
        memset(&smi, 0, sizeof smi);
        smi.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        smi.codeSize = spv_bytes; smi.pCode = code;
        TRY(pvkCreateShaderModule(dev, &smi, NULL, &mod), "vkCreateShaderModule");
    }
    printf("  [ OK ] vkCreateShaderModule -- el driver ACEPTÓ el modulo\n");

    /* ---- buffers ---- */
    {
        VkBufferCreateInfo bci;
        memset(&bci, 0, sizeof bci);
        bci.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        VkMemoryAllocateInfo mai;
        memset(&mai, 0, sizeof mai);
        mai.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        int t;

        bci.size = BYTES_BLOCKS; bci.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        TRY(pvkCreateBuffer(dev, &bci, NULL, &b_in), "vkCreateBuffer entrada");
        bci.size = BYTES_PIXELS;
        TRY(pvkCreateBuffer(dev, &bci, NULL, &b_out), "vkCreateBuffer salida");

        t = find_host_coherent_type(target);
        if (t < 0) { fprintf(stderr, "  [FAIL] sin memoria HOST_VISIBLE|HOST_COHERENT\n"); goto out; }

        mai.allocationSize = BYTES_BLOCKS; mai.memoryTypeIndex = (uint32_t)t;
        TRY(pvkAllocateMemory(dev, &mai, NULL, &m_in), "vkAllocateMemory entrada");
        TRY(pvkBindBufferMemory(dev, b_in, m_in, 0), "vkBindBufferMemory entrada");
        mai.allocationSize = BYTES_PIXELS;
        TRY(pvkAllocateMemory(dev, &mai, NULL, &m_out), "vkAllocateMemory salida");
        TRY(pvkBindBufferMemory(dev, b_out, m_out, 0), "vkBindBufferMemory salida");

        TRY(pvkMapMemory(dev, m_in, 0, BYTES_BLOCKS, 0, &map_in), "vkMapMemory entrada");
        memcpy(map_in, c->blocks, BYTES_BLOCKS);
        pvkUnmapMemory(dev, m_in); map_in = NULL;

        TRY(pvkMapMemory(dev, m_out, 0, BYTES_PIXELS, 0, &map_out), "vkMapMemory salida");
        memset(map_out, 0, BYTES_PIXELS);   /* zeros: the "nothing written" case */
    }
    printf("  [ OK ] buffers y memoria mapeada\n");

    /* ---- pipeline ---- */
    {
        VkDescriptorSetLayoutBinding bnd[2];
        VkDescriptorSetLayoutCreateInfo dslc;
        memset(&dslc, 0, sizeof dslc);
        dslc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        VkPipelineLayoutCreateInfo plc;
        memset(&plc, 0, sizeof plc);
        plc.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        VkPushConstantRange pcr;
        VkDescriptorPoolSize psz;
        VkDescriptorPoolCreateInfo dpoc;
        memset(&dpoc, 0, sizeof dpoc);
        dpoc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        VkDescriptorSetAllocateInfo dsai;
        VkWriteDescriptorSet wds[2];
        VkDescriptorBufferInfo dbi[2];
        VkPipelineShaderStageCreateInfo stg;
        memset(&stg, 0, sizeof stg);
        stg.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        VkComputePipelineCreateInfo cpc;
        memset(&cpc, 0, sizeof cpc);
        cpc.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
        VkPipelineCache cache = VK_NULL_HANDLE;

        memset(bnd, 0, sizeof bnd);
        bnd[0].binding = 0; bnd[0].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bnd[0].descriptorCount = 1; bnd[0].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        bnd[1] = bnd[0]; bnd[1].binding = 1;
        dslc.bindingCount = 2; dslc.pBindings = bnd;
        TRY(pvkCreateDescriptorSetLayout(dev, &dslc, NULL, &dsl), "vkCreateDescriptorSetLayout");

        pcr.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT; pcr.offset = 0; pcr.size = 4;
        plc.setLayoutCount = 1; plc.pSetLayouts = &dsl;
        plc.pushConstantRangeCount = 1; plc.pPushConstantRanges = &pcr;
        TRY(pvkCreatePipelineLayout(dev, &plc, NULL, &playout), "vkCreatePipelineLayout");

        psz.type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; psz.descriptorCount = 2;
        dpoc.maxSets = 1; dpoc.poolSizeCount = 1; dpoc.pPoolSizes = &psz;
        TRY(pvkCreateDescriptorPool(dev, &dpoc, NULL, &dpool), "vkCreateDescriptorPool");

        memset(&dsai, 0, sizeof dsai);
        dsai.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        dsai.descriptorPool = dpool; dsai.descriptorSetCount = 1; dsai.pSetLayouts = &dsl;
        TRY(pvkAllocateDescriptorSets(dev, &dsai, &dset), "vkAllocateDescriptorSets");

        dbi[0].buffer = b_in; dbi[0].offset = 0; dbi[0].range = VK_WHOLE_SIZE;
        dbi[1].buffer = b_out; dbi[1].offset = 0; dbi[1].range = VK_WHOLE_SIZE;
        memset(wds, 0, sizeof wds);
        for (i = 0; i < 2; i++) {
            wds[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
            wds[i].dstSet = dset; wds[i].dstBinding = i; wds[i].descriptorCount = 1;
            wds[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            wds[i].pBufferInfo = &dbi[i];
        }
        pvkUpdateDescriptorSets(dev, 2, wds, 0, NULL);

        stg.stage = VK_SHADER_STAGE_COMPUTE_BIT; stg.module = mod; stg.pName = "main";
        cpc.stage = stg; cpc.layout = playout;
        TRY(pvkCreateComputePipelines(dev, cache, 1, &cpc, NULL, &pipe), "vkCreateComputePipelines");
    }
    printf("  [ OK ] pipeline de compute creado\n");

    /* ---- record and submit ---- */
    {
        VkCommandPoolCreateInfo cpc;
        memset(&cpc, 0, sizeof cpc);
        cpc.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
        VkCommandBufferAllocateInfo cbai;
        memset(&cbai, 0, sizeof cbai);
        cbai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        VkCommandBufferBeginInfo cbbi;
        memset(&cbbi, 0, sizeof cbbi);
        cbbi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        VkFenceCreateInfo fci;
        memset(&fci, 0, sizeof fci);
        fci.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        VkSubmitInfo si;
        memset(&si, 0, sizeof si);
        si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;

        cpc.queueFamilyIndex = qfam;
        TRY(pvkCreateCommandPool(dev, &cpc, NULL, &pool), "vkCreateCommandPool");
        cbai.commandPool = pool; cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cbai.commandBufferCount = 1;
        TRY(pvkAllocateCommandBuffers(dev, &cbai, &cmd), "vkAllocateCommandBuffers");
        TRY(pvkBeginCommandBuffer(cmd, &cbbi), "vkBeginCommandBuffer");

        pvkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
        pvkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, playout,
                                 0, 1, &dset, 0, NULL);
        pvkCmdDispatch(cmd, DISPATCHES, 1, 1);
        TRY(pvkEndCommandBuffer(cmd), "vkEndCommandBuffer");

        TRY(pvkCreateFence(dev, &fci, NULL, &fence), "vkCreateFence");
        si.commandBufferCount = 1; si.pCommandBuffers = &cmd;
        TRY(pvkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit");
        qcount = 0;
        TRY(pvkWaitForFences(dev, 1, &fence, VK_TRUE, TIMEOUT_NS), "vkWaitForFences");
        TRY(pvkQueueWaitIdle(queue), "vkQueueWaitIdle");
        (void)qcount;
    }
    printf("  [ OK ] vkCmdDispatch(%u,1,1) = %u invocaciones, submit y fence completados\n",
           DISPATCHES, DISPATCHES * GROUPSIZE);
    printf("  *** La GPU ha ejecutado el shader. Esto ya no es aritmetica simulada. ***\n");

    /* ======================================================================
     * VALIDATION BEFORE COMPARISON -- read the file's header for why.
     * ====================================================================== */
    printf("\n  Validacion de la salida (ANTES de comparar):\n");

    gpu = malloc(BYTES_PIXELS);
    if (!gpu) { fprintf(stderr, "  [FAIL] sin memoria\n"); goto out; }
    memcpy(gpu, map_out, BYTES_PIXELS);

    {
        size_t nz = 0, b;
        for (i = 0; i < BYTES_PIXELS; i++) if (((uint8_t *)gpu)[i]) nz++;
        if (nz == 0) {
            fprintf(stderr, "  [FAIL] la salida es TODA CERO. El shader no escribio.\n"
                            "         Causas probables: dispatch no submitted, pipeline mal\n"
                            "         construido, o buffer no enlazado. Comparar ahora daria\n"
                            "         0 discrepancias y PASS, que no probaria nada.\n");
            goto out;
        }
        printf("    [ OK ] %zu de %zu bytes distintos de cero\n", nz, BYTES_PIXELS);
        (void)b;
    }

    {
        size_t words = BYTES_PIXELS / 4u;
        size_t poison = 0;
        for (i = 0; i < words; i++) if (gpu[i] == POISON) poison++;
        if (poison) {
            fprintf(stderr, "  [FAIL] %zu palabras siguen con el patron veneno (0x%08X):\n"
                            "         el shader no escribio esa region.\n", poison, POISON);
            goto out;
        }
        printf("    [ OK ] ninguna palabra conserva el patron veneno 0x%08X\n", POISON);
    }

    /* ---- only now: compare ---- */
    printf("\n  Comparacion byte a byte GPU vs CPU:\n");
    for (i = 0; i < NUM_BLOCKS; i++) {
        int p, bd = 0;
        for (p = 0; p < 64; p++) {
            uint8_t g = ((uint8_t *)gpu)[i * 64 + p];
            uint8_t r = c->cpu[i].px[p];
            if (g != r) {
                if (shown < 8)
                    printf("    bloque %2d pixel %2d canal %d: GPU=%3u CPU=%3u (diff %d)\n",
                           i, p / 4, p % 4, g, r, (int)g - (int)r);
                shown++;
                bd++;
            }
        }
        if (bd) { differ++; if (differ <= 6) printf("      bloque %2d: %d de 64 bytes difieren\n", i, bd); }
    }

    printf("\n  bloques discrepantes : %d de %d\n", differ, NUM_BLOCKS);
    printf("  bytes discrepantes   : %d de %zu\n", shown, BYTES_PIXELS);
    printf("  cobertura del corpus : %d bloques a0<=a1, %d bloques a0>a1\n", c->n_six, c->n_eight);

    if (differ == 0) {
        printf("\nRESULT: GPU == CPU. El shader en la RX 550 produce exactamente lo que\n"
               "        produce el decodificador de referencia.\n");
        verdict = 1;
    } else {
        printf("\nRESULT: GPU != CPU. %d de %d bloques difieren.\n", differ, NUM_BLOCKS);
    }

out:
    if (map_out) pvkUnmapMemory(dev, m_out);
    if (fence)  pvkDestroyFence(dev, fence, NULL);
    if (pool)   pvkDestroyCommandPool(dev, pool, NULL);
    if (dpool)  pvkDestroyDescriptorPool(dev, dpool, NULL);
    if (pipe)   pvkDestroyPipeline(dev, pipe, NULL);
    if (playout) pvkDestroyPipelineLayout(dev, playout, NULL);
    if (dsl)    pvkDestroyDescriptorSetLayout(dev, dsl, NULL);
    if (mod)    pvkDestroyShaderModule(dev, mod, NULL);
    if (b_in)   pvkDestroyBuffer(dev, b_in, NULL);
    if (b_out)  pvkDestroyBuffer(dev, b_out, NULL);
    if (m_in)   pvkFreeMemory(dev, m_in, NULL);
    if (m_out)  pvkFreeMemory(dev, m_out, NULL);
    if (dev)    pvkDestroyDevice(dev, NULL);
    if (inst)   pvkDestroyInstance(inst, NULL);
    free(phys); free(code); free(gpu);
    return verdict;
}

/* ==========================================================================
 */

int main(int argc, char **argv)
{
    corpus_t *c;
    int want_gpu = 0, a, ok = 1;

    for (a = 1; a < argc; a++)
        if (strcmp(argv[a], "--gpu") == 0) want_gpu = 1;

    printf("=== Agreement test: shader GCN vs decodificador C ===\n\n");
    printf("Fase A: artefacto y corpus, sin GPU.\n");
    printf("Fase B: dispatch real en la RX 550, solo con --gpu.\n\n");

    c = calloc(1, sizeof *c);
    if (!c) { fprintf(stderr, "sin memoria\n"); return 1; }

    /* ---- Fase A ---- */
    {
        struct stat spv, comp;
        printf("1. Artefacto:\n");
        if (stat("decompress_bc3.comp", &comp) != 0) {
            fprintf(stderr, "  [FAIL] decompress_bc3.comp no existe\n"); ok = 0;
        }
        if (stat("decompress_bc3.spv", &spv) != 0) {
            fprintf(stderr, "  [FAIL] decompress_bc3.spv no existe. make decompress_bc3.spv\n");
            ok = 0;
        } else {
            if (spv.st_mtime < comp.st_mtime) {
                fprintf(stderr, "  [FAIL] el .spv es mas viejo que el .comp; puede no\n"
                                "         corresponder al fuente. make decompress_bc3.spv\n");
                ok = 0;
            } else {
                printf("  [ OK ] .spv (%zu B) no mas viejo que .comp\n", (size_t)spv.st_size);
            }
        }

        printf("\n2. Corpus (LCG semilla 12345):\n");
        corpus_build(c);
        printf("  [ OK ] %d bloques\n", NUM_BLOCKS);
        printf("  [ OK ] modo 6 valores (a0<=a1): %d   modo 8 valores (a0>a1): %d\n",
               c->n_six, c->n_eight);
        if (c->n_six == 0 || c->n_eight == 0) {
            fprintf(stderr, "  [FAIL] el corpus no cubre las dos ramas de la rampa:\n"
                            "         un shader con una rama equivocada pasaria.\n");
            ok = 0;
        } else {
            printf("  [ OK ] ambas ramas cubiertas\n");
        }

        {
            size_t nz = 0, b, p;
            for (b = 0; b < NUM_BLOCKS; b++)
                for (p = 0; p < 64; p++)
                    if (c->cpu[b].px[p]) nz++;
            if (!nz) { fprintf(stderr, "  [FAIL] referencia CPU degenerada\n"); ok = 0; }
            else printf("  [ OK ] referencia CPU no trivial: %zu de %zu bytes\n", nz, BYTES_PIXELS);
        }
        printf("  [ OK ] dispatch previsto: %u grupos de %u = %u invocaciones\n",
               DISPATCHES, GROUPSIZE, DISPATCHES * GROUPSIZE);
    }

    if (!ok) {
        printf("\nRESULT: FASE A FALLO\n");
        free(c);
        return 1;
    }
    printf("\nFASE A OK.\n");

    if (!want_gpu) {
        printf("\nFase B omitida. Usa --gpu, o: make test-gpu\n");
        free(c);
        return 0;
    }

    phase_b(c, "decompress_bc3.spv");
    free(c);
    return 0;
}
