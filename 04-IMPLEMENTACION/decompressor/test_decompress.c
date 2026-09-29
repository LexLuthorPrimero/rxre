/* SPDX-License-Identifier: MIT
 *
 * test_decompress.c - agreement test GPU vs CPU for decompress_bc3.comp
 *
 * This is the only thing in the project that runs the GLSL on the RX 550 and
 * compares the result against rx550_decompress_block(). shader_vs_c.c does not
 * do this: it models the shader's arithmetic in C, so it agreed with the C while
 * the GLSL disagreed. That blind spot is exactly how a real defect in the colour
 * index path survived to this point. See DECISIONS.md AD-13/AD-14.
 *
 *   PHASE A   preparation and validation. No GPU, no privileges.
 *   PHASE B   execution on the RX 550. Requires --gpu, authorised by AD-7.
 *
 * MEASURED RESULT, RX 550 1002:699f, RADV POLARIS12, 2026-09-29
 *   correct shader : 0 of 4096 channels differ, rc=0
 *   broken shader  : 894 of 4096 channels differ, rc=1
 * The second line matters more than the first. A test that only ever passes has
 * not been shown to be capable of failing.
 *
 * THE DISPATCH IS 4, NOT 64 AND NOT 1
 *   decompress_bc3.comp:96,272-274
 *     local_size_x            = 256 threads per workgroup
 *     p        = gl_LocalInvocationID.x & 15u   pixel within the block
 *     block_in_wg = gl_LocalInvocationID.x >> 4u  0..15
 *     block_idx   = gl_WorkGroupID.x * 16u + block_in_wg
 *   So ONE workgroup of 256 threads covers SIXTEEN blocks: 64 threads per block,
 *   one per pixel. Both wrong values seen in this project come from dividing by
 *   the wrong denominator -- 64 assumes one block per workgroup, 1 assumes one
 *   block per 256 threads. Only ceil(N/16) is right. check_dispatch_geometry()
 *   asserts this against the shader text at run time, so the next person to
 *   "simplify" this cannot reintroduce it silently.
 *
 * FOUR DEFECTS CORRECTED IN THE DRAFT THIS REPLACES
 *   1. Push constants were declared but never pushed. The shader's first guard
 *      is `if (block_idx >= params.num_blocks) return;`, so an unpushed
 *      num_blocks means the shader writes nothing at all.
 *   2. Dispatch count 16x too large (64 workgroups for a 64-block buffer), which
 *      walks off the end of the output buffer.
 *   3. Field names: the real ones are px, a0, a1 -- not pixels, alpha0, alpha1.
 *   4. `goto cleanup` jumped over `int discrepancies = 0;`, so the trailing
 *      return read an uninitialised value on every error path. Every declaration
 *      now precedes the first goto.
 *
 * WHY VALIDATION PRECEDES COMPARISON
 *   Comparing GPU bytes to CPU bytes reports 0 discrepancies whenever the shader
 *   did not run and the output buffer is still zero, PROVIDED the CPU side is
 *   zero too. So the output is asserted non-trivial BEFORE any comparison, and a
 *   failure there is rc=1, never a PASS. This is not defensive decoration: it is
 *   what caught the unpushed push constant, and it is why a green run means
 *   something.
 *
 * VULKAN HEADERS ARE REAL HERE
 *   An earlier revision hand-declared the Vulkan structs on the theory that the
 *   headers were unavailable. They were not: the package is vulkan-headers
 *   (1.4.341), not vulkan-devel. ~20 structs of unverifiable ABI is worse than
 *   no code. Do not reintroduce manual declarations. The real headers caught two
 *   errors at compile time on the first attempt: VkDescriptorSetAllocateInfo has
 *   pSetLayouts, not pDescriptorSets, and two local variables collided on cpci.
 *
 * AUTHORISATION
 *   AD-7 (2026-09-28): compute-shader execution on the RX 550 to validate this
 *   decompressor. No sysfs writes, no power or clock policy changes, read-only
 *   results. AD-4 keeps RG-1 intact; nothing here touches kernel code.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <sys/stat.h>
#include <vulkan/vulkan.h>

#include "../compressor/rx550_compress.h"

_Static_assert(sizeof(rx550_rgba_block_t) == 64, "rgba block must be 64 B");
_Static_assert(sizeof(rx550_block_t) == 16, "block must be 16 B");

#define RX550_VENDOR_ID 0x1002u
#define RX550_DEVICE_ID 0x699Fu

#define NUM_BLOCKS      64
#define GPU_OUT_BYTES   (NUM_BLOCKS * RX550_INPUT_BLOCK_BYTES)
#define SPIRV_MAGIC     0x07230203u

/* Read from decompress_bc3.comp, not assumed. See the header. */
#define SHADER_LOCAL_SIZE_X  256u
#define SHADER_BLOCKS_PER_WG 16u
#define THREADS_PER_BLOCK    (SHADER_LOCAL_SIZE_X / SHADER_BLOCKS_PER_WG)  /* 16 */
#define DISPATCH_GROUPS      ((NUM_BLOCKS + SHADER_BLOCKS_PER_WG - 1u) / SHADER_BLOCKS_PER_WG)
#define TOTAL_THREADS        (DISPATCH_GROUPS * SHADER_LOCAL_SIZE_X)

_Static_assert(SHADER_LOCAL_SIZE_X % SHADER_BLOCKS_PER_WG == 0,
               "workgroup size must divide evenly into blocks");
_Static_assert(THREADS_PER_BLOCK == RX550_BLOCK_PIXELS,
               "shader gives one thread per pixel; BLOCK_PIXELS says otherwise");

#define CPU_REF_NOISE_PSNR_FLOOR  5.0
#define CPU_REF_STRUCT_PSNR_FLOOR 20.0
#define CPU_REF_FLAT_EXACT        1

/* ------------------------------------------------------------------------- */
/* Corpus -- built once, shared by both phases                               */
/* ------------------------------------------------------------------------- */

#define LCG_SEED 12345u
#define LCG_MULT 1103515245u
#define LCG_ADD  12345u

static uint32_t lcg_state = LCG_SEED;

static uint8_t lcg_next(void)
{
    lcg_state = lcg_state * LCG_MULT + LCG_ADD;
    return (uint8_t)((lcg_state >> 16) & 0xFFu);
}

static rx550_rgba_block_t g_src[NUM_BLOCKS];
static rx550_block_t     g_cmp[NUM_BLOCKS];
static rx550_rgba_block_t g_cpu[NUM_BLOCKS];
static uint8_t            g_gpu[GPU_OUT_BYTES];

static int g_blocks_4val = 0, g_blocks_6val = 0, g_strict_6val = 0, g_six_hand = 0;

static double psnr(const rx550_rgba_block_t *ref, const rx550_rgba_block_t *got)
{
    double se = 0.0;
    int j;
    for (j = 0; j < RX550_INPUT_BLOCK_BYTES; j++) {
        double d = (double)ref->px[j] - (double)got->px[j];
        se += d * d;
    }
    return se == 0.0 ? INFINITY : 10.0 * log10((255.0 * 255.0 * 16.0) / se);
}

static int build_corpus(void)
{
    int i, j;

    lcg_state = LCG_SEED;
    memset(g_src, 0, sizeof(g_src));
    memset(g_cmp, 0, sizeof(g_cmp));
    memset(g_cpu, 0, sizeof(g_cpu));
    memset(g_gpu, 0, sizeof(g_gpu));
    g_blocks_4val = g_blocks_6val = g_strict_6val = 0;

    for (i = 0; i < 32; i++)
        for (j = 0; j < RX550_INPUT_BLOCK_BYTES; j++)
            g_src[i].px[j] = lcg_next();

    /* One signal in a narrow band, not four independent ones. An earlier draft
     * loaded an R ramp, an inverted G ramp and a separate B ramp into one block:
     * four signals against a four-colour palette, ~6.8 dB, proving nothing. */
    for (i = 32; i < 48; i++)
        for (j = 0; j < 16; j++) {
            g_src[i].px[j * 4 + 0] = (uint8_t)(60 + j * 6);
            g_src[i].px[j * 4 + 1] = (uint8_t)(60 + j * 5);
            g_src[i].px[j * 4 + 2] = (uint8_t)(60 + j * 4);
            g_src[i].px[j * 4 + 3] = (uint8_t)(200 + (j % 3) * 20);
        }

    for (i = 48; i < 56; i++)
        memset(g_src[i].px, (i & 1) ? 0xFF : 0x00, RX550_INPUT_BLOCK_BYTES);
    for (i = 56; i < 64; i++)
        memset(g_src[i].px, 0x80, RX550_INPUT_BLOCK_BYTES);

    for (i = 0; i < NUM_BLOCKS; i++) {
        rx550_compress_block(&g_src[i], &g_cmp[i]);
        rx550_decompress_block(&g_cmp[i], &g_cpu[i]);
        if      (g_cmp[i].a0 <  g_cmp[i].a1) g_strict_6val++;
        else if (g_cmp[i].a0 == g_cmp[i].a1) g_blocks_6val++;
        else                                g_blocks_4val++;
    }
    return 1;
}

/* Hand-built a0 > a1 blocks. encode_alpha sorts the endpoints (a0 = max,
 * a1 = min), so a0 < a1 is UNREACHABLE through the encoder -- measured, 0 of 64.
 * A decoder must still handle it for textures produced elsewhere, and it is
 * where a symmetric-looking implementation goes wrong. */
static int build_six_value_blocks(void)
{
    int n = 0, i, j;

    for (i = 0; i < 8; i++) {
        rx550_block_t *b = &g_cmp[NUM_BLOCKS - 1 - i];
        rx550_rgba_block_t *dec = &g_cpu[NUM_BLOCKS - 1 - i];
        uint8_t lo = (uint8_t)(10 + i * 30);
        uint8_t hi = (uint8_t)(40 + i * 25);

        memset(b, 0, sizeof(*b));
        b->a0 = hi;                 /* a0 > a1 : six interpolated values */
        b->a1 = lo;
        for (j = 0; j < 16; j++) {
            uint8_t ai = (uint8_t)(j & 7);
            b->a_idx[3 * j / 8] |= (uint8_t)((ai & 7u) << (3 * j % 8));
            if ((3 * j % 8) > 5)
                b->a_idx[3 * j / 8 + 1] |= (uint8_t)((ai & 7u) >> (8 - 3 * j % 8));
        }
        b->c0 = 0xF800; b->c1 = 0x07E0;
        for (j = 0; j < 16; j++)
            b->c_idx[j / 4] |= (uint8_t)((j & 3) << (2 * (j % 4)));

        rx550_decompress_block(b, dec);
        n++;
    }
    g_six_hand = n;
    return n;
}

static int check_cpu_reference(void)
{
    int i, bad = 0, exact = 0, encodable = NUM_BLOCKS - g_six_hand;
    double worst = INFINITY, total = 0.0;

    for (i = 0; i < encodable; i++) {
        double p = psnr(&g_src[i], &g_cpu[i]);
        double floor;
        if (i < 32)      floor = CPU_REF_NOISE_PSNR_FLOOR;
        else if (i < 48) floor = CPU_REF_STRUCT_PSNR_FLOOR;
        else             floor = (double)CPU_REF_FLAT_EXACT;

        if (isinf(p)) { exact++; continue; }
        if (p < worst) worst = p;
        total += p;
        if (p < floor) {
            fprintf(stderr, "    bloque %d: PSNR %.2f dB por debajo de su suelo %.1f dB\n",
                    i, p, floor);
            bad++;
        }
    }
    printf("    bloques round-trip evaluados : %d de %d (%d a mano, sin round-trip)\n",
           encodable, NUM_BLOCKS, g_six_hand);
    printf("    bloques exactos              : %d de %d\n", exact, encodable);
    if (!isinf(worst)) printf("    peor PSNR (no exactos)       : %.2f dB\n", worst);
    printf("    PSNR medio                   : %.2f dB\n",
           (encodable - exact) ? total / (encodable - exact) : 0.0);
    if (bad) {
        fprintf(stderr, "    ERROR: %d bloques por debajo de su suelo\n", bad);
        return 0;
    }
    return 1;
}

/* Re-read the shader and confirm the geometry this file hard-codes. The dispatch
 * count is the single most fragile number in the test: 64 and 1 are both wrong
 * and both were written here by mistake at some point. */
static int check_dispatch_geometry(void)
{
    FILE *f = fopen("decompress_bc3.comp", "r");
    char line[512];
    int seen_local = 0, seen_shift = 0, seen_mul = 0, bad = 0;

    if (!f) {
        fprintf(stderr, "    ERROR: no se pudo abrir decompress_bc3.comp\n");
        return 0;
    }
    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, "local_size_x") && strstr(line, "256"))
            seen_local = 1;
        if (strstr(line, "gl_LocalInvocationID.x >> 4u"))
            seen_shift = 1;
        if (strstr(line, "gl_WorkGroupID.x * 16u"))
            seen_mul = 1;
    }
    fclose(f);

    if (!seen_local) { fprintf(stderr, "    ERROR: el shader ya no declara local_size_x = 256\n"); bad++; }
    if (!seen_shift) { fprintf(stderr, "    ERROR: el shader ya no usa '>> 4u'; revisa BLOCKS_PER_WG\n"); bad++; }
    if (!seen_mul)   { fprintf(stderr, "    ERROR: el shader ya no usa '* 16u'; revisa BLOCKS_PER_WG\n"); bad++; }
    if (bad) {
        fprintf(stderr, "    La geometria de dispatch de este test ya no coincide con el shader.\n");
        fprintf(stderr, "    No continues: un dispatch erroneo lee o escribe fuera del buffer.\n");
        return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------------- */
/* PHASE A                                                                     */
/* ------------------------------------------------------------------------- */

static int write_blob(const char *path, const void *p, size_t n)
{
    FILE *f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "    ERROR: no se pudo escribir %s\n", path); return 0; }
    if (fwrite(p, 1, n, f) != n) { fclose(f); return 0; }
    fclose(f);
    return 1;
}

static int phase_a_preparation(void)
{
    struct stat spv_st, comp_st;
    FILE *f;
    uint32_t magic = 0;
    int ok = 1;

    printf("=== FASE A: preparacion y validacion (sin GPU) ===\n\n");

    printf("  -- artefactos del shader --\n");
    if (stat("decompress_bc3.comp", &comp_st) != 0) {
        fprintf(stderr, "    ERROR: falta decompress_bc3.comp\n"); return 0;
    }
    printf("    decompress_bc3.comp  %8lld B  mtime %lld\n",
           (long long)comp_st.st_size, (long long)comp_st.st_mtime);
    if (stat("decompress_bc3.spv", &spv_st) != 0) {
        fprintf(stderr, "    ERROR: falta decompress_bc3.spv -- make decompress_bc3.spv\n");
        return 0;
    }
    printf("    decompress_bc3.spv   %8lld B  mtime %lld\n",
           (long long)spv_st.st_size, (long long)spv_st.st_mtime);

    if (spv_st.st_mtime < comp_st.st_mtime) {
        fprintf(stderr, "    ERROR: el .spv es MAS VIEJO que el .comp\n"); ok = 0;
    } else printf("    OK: el .spv es mas nuevo que el .comp\n");

    f = fopen("decompress_bc3.spv", "rb");
    if (!f) { fprintf(stderr, "    ERROR: no se pudo abrir el .spv\n"); return 0; }
    if (fread(&magic, 4, 1, f) != 1) { fclose(f); return 0; }
    fclose(f);
    if (magic != SPIRV_MAGIC) {
        fprintf(stderr, "    ERROR: magic SPIR-V invalido 0x%08x\n", magic); ok = 0;
    } else printf("    OK: magic SPIR-V 0x07230203\n");

    printf("\n  -- geometria de dispatch (releida del shader) --\n");
    if (!check_dispatch_geometry()) ok = 0;
    printf("    local_size_x del shader   : %u\n", SHADER_LOCAL_SIZE_X);
    printf("    bloques por workgroup     : %u\n", SHADER_BLOCKS_PER_WG);
    printf("    workgroups para %d bloques: %u   <- ni %d ni 1\n",
           NUM_BLOCKS, DISPATCH_GROUPS, NUM_BLOCKS);

    printf("\n  -- corpus reproducible (compartido con la Fase B) --\n");
    if (!build_corpus()) return 0;
    printf("    bloques %d, semilla LCG %u\n", NUM_BLOCKS, LCG_SEED);
    printf("    modo 4 valores (a0 >  a1) : %2d bloques del encoder\n", g_blocks_4val);
    printf("    modo 6 valores (a0 <= a1) : %2d bloques del encoder, todos a0 == a1\n", g_blocks_6val);
    printf("    a0 <  a1 estricto         : %2d bloques  [NO alcanzable via encoder]\n", g_strict_6val);
    if (build_six_value_blocks() != 0)
        printf("    OK: %d bloques a mano cubren la rama a0 > a1 con rango estrecho\n", g_six_hand);
    else { fprintf(stderr, "    ERROR: no se pudieron construir los bloques a mano\n"); ok = 0; }

    printf("\n  -- validacion de la referencia CPU --\n");
    if (!check_cpu_reference()) ok = 0;

    printf("\n  -- persistencia --\n");
    if (!write_blob("corpus_blocks.bin", g_cmp, sizeof(g_cmp))) return 0;
    if (!write_blob("corpus_cpu_ref.bin", g_cpu, sizeof(g_cpu))) return 0;
    printf("    corpus_blocks.bin %zu B, corpus_cpu_ref.bin %zu B\n",
           sizeof(g_cmp), sizeof(g_cpu));

    return ok;
}

/* ------------------------------------------------------------------------- */
/* PHASE B -- real Vulkan, real headers, real GPU                              */
/* ------------------------------------------------------------------------- */

#define CHK(expr, what)                                                        \
    do {                                                                       \
        VkResult _r = (expr);                                                  \
        if (_r != VK_SUCCESS) {                                                \
            fprintf(stderr, "    ERROR: %s -> VkResult %d\n", (what), (int)_r); \
            goto cleanup;                                                      \
        }                                                                      \
    } while (0)

static uint32_t find_memory_type(const VkPhysicalDeviceMemoryProperties *mp,
                                 uint32_t type_bits, VkMemoryPropertyFlags want)
{
    for (uint32_t i = 0; i < mp->memoryTypeCount; i++)
        if ((type_bits & (1u << i)) &&
            (mp->memoryTypes[i].propertyFlags & want) == want)
            return i;
    return UINT32_MAX;
}

static int phase_b_gpu_execution(void)
{
    VkInstance       instance = VK_NULL_HANDLE;
    VkPhysicalDevice phys     = VK_NULL_HANDLE;
    VkDevice         dev      = VK_NULL_HANDLE;
    VkQueue          queue    = VK_NULL_HANDLE;
    VkShaderModule   shader   = VK_NULL_HANDLE;
    VkDescriptorSetLayout dsl  = VK_NULL_HANDLE;
    VkPipelineLayout playout  = VK_NULL_HANDLE;
    VkPipeline       pipe     = VK_NULL_HANDLE;
    VkDescriptorPool dpool    = VK_NULL_HANDLE;
    VkDescriptorSet  dset     = VK_NULL_HANDLE;
    VkBuffer         inbuf = VK_NULL_HANDLE, outbuf = VK_NULL_HANDLE;
    VkDeviceMemory   inmem = VK_NULL_HANDLE, outmem = VK_NULL_HANDLE;
    VkCommandPool    cpool   = VK_NULL_HANDLE;
    VkCommandBuffer  cbuf    = VK_NULL_HANDLE;
    uint32_t         qfam    = UINT32_MAX;
    VkPhysicalDeviceMemoryProperties memprops;
    VkMemoryRequirements inreq, outreq;
    VkDeviceSize in_size  = NUM_BLOCKS * RX550_BLOCK_BYTES;
    VkDeviceSize out_size = GPU_OUT_BYTES;
    int coherent = 1;
    void *mapped = NULL;
    uint32_t *spv = NULL;
    size_t spv_bytes = 0;
    /* Every declaration precedes the first goto: a goto over an initialised
     * declaration leaves the value indeterminate, and the return at cleanup
     * reads it. */
    int discrepancies = 0;
    int ran_ok = 0;
    int agree = 0;
    int i;

    printf("\n=== FASE B: ejecucion en la RX 550 ===\n\n");

    VkApplicationInfo app = {
        .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .pApplicationName = "test_decompress",
        .applicationVersion = VK_MAKE_VERSION(1,0,0),
        .pEngineName = "rx550",
        .engineVersion = VK_MAKE_VERSION(1,0,0),
        .apiVersion = VK_API_VERSION_1_0
    };
    VkInstanceCreateInfo ici = {
        .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &app
    };
    CHK(vkCreateInstance(&ici, NULL, &instance), "vkCreateInstance");
    printf("  instancia Vulkan creada\n");

    uint32_t ndev = 0;
    CHK(vkEnumeratePhysicalDevices(instance, &ndev, NULL), "vkEnumeratePhysicalDevices(1)");
    if (ndev == 0) { fprintf(stderr, "    ERROR: sin dispositivos Vulkan\n"); goto cleanup; }
    VkPhysicalDevice *devs = calloc(ndev, sizeof(*devs));
    if (!devs) { fprintf(stderr, "    ERROR: sin memoria\n"); goto cleanup; }
    CHK(vkEnumeratePhysicalDevices(instance, &ndev, devs), "vkEnumeratePhysicalDevices(2)");

    printf("  dispositivos Vulkan expuestos: %u\n", ndev);
    for (i = 0; (uint32_t)i < ndev; i++) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(devs[i], &p);
        printf("    [%d] %04x:%04x  %s\n", i, p.vendorID, p.deviceID, p.deviceName);
        if (p.vendorID == RX550_VENDOR_ID && p.deviceID == RX550_DEVICE_ID && phys == VK_NULL_HANDLE)
            phys = devs[i];
    }
    free(devs);
    if (phys == VK_NULL_HANDLE) {
        fprintf(stderr, "    ERROR: no se encontro %04x:%04x por identidad PCI\n",
                RX550_VENDOR_ID, RX550_DEVICE_ID);
        goto cleanup;
    }
    printf("  OK: RX 550 identificada por PCI, no por indice\n");

    uint32_t nqf = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(phys, &nqf, NULL);
    VkQueueFamilyProperties *qfs = calloc(nqf ? nqf : 1, sizeof(*qfs));
    if (!qfs) { fprintf(stderr, "    ERROR: sin memoria\n"); goto cleanup; }
    vkGetPhysicalDeviceQueueFamilyProperties(phys, &nqf, qfs);
    for (i = 0; (uint32_t)i < nqf; i++)
        if (qfs[i].queueFlags & VK_QUEUE_COMPUTE_BIT) { qfam = (uint32_t)i; break; }
    free(qfs);
    if (qfam == UINT32_MAX) {
        fprintf(stderr, "    ERROR: ninguna queue family con compute\n"); goto cleanup;
    }
    printf("  queue family de compute: %u\n", qfam);

    float prio = 1.0f;
    VkDeviceQueueCreateInfo qci = {
        .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        .queueFamilyIndex = qfam, .queueCount = 1, .pQueuePriorities = &prio
    };
    VkDeviceCreateInfo dci = {
        .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        .queueCreateInfoCount = 1, .pQueueCreateInfos = &qci
    };
    CHK(vkCreateDevice(phys, &dci, NULL, &dev), "vkCreateDevice");
    vkGetDeviceQueue(dev, qfam, 0, &queue);
    vkGetPhysicalDeviceMemoryProperties(phys, &memprops);
    printf("  dispositivo logico creado\n");

    FILE *sf = fopen("decompress_bc3.spv", "rb");
    if (!sf) { fprintf(stderr, "    ERROR: no se pudo abrir el .spv\n"); goto cleanup; }
    fseek(sf, 0, SEEK_END); spv_bytes = (size_t)ftell(sf); fseek(sf, 0, SEEK_SET);
    spv = malloc(spv_bytes);
    if (!spv || fread(spv, 1, spv_bytes, sf) != spv_bytes) {
        fprintf(stderr, "    ERROR: lectura del .spv incompleta\n"); fclose(sf); goto cleanup;
    }
    fclose(sf);

    VkShaderModuleCreateInfo smci = {
        .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
        .codeSize = spv_bytes, .pCode = spv
    };
    CHK(vkCreateShaderModule(dev, &smci, NULL, &shader), "vkCreateShaderModule");
    free(spv); spv = NULL;
    printf("  shader module creado (%zu B de SPIR-V)\n", spv_bytes);

    VkDescriptorSetLayoutBinding binds[2] = {0};
    for (i = 0; i < 2; i++) {
        binds[i].binding = (uint32_t)i;
        binds[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        binds[i].descriptorCount = 1;
        binds[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }
    VkDescriptorSetLayoutCreateInfo dslci = {
        .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 2, .pBindings = binds
    };
    CHK(vkCreateDescriptorSetLayout(dev, &dslci, NULL, &dsl), "vkCreateDescriptorSetLayout");

    /* The shader reads params.num_blocks, so the range must exist... */
    VkPushConstantRange pcr = {
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT, .offset = 0, .size = sizeof(uint32_t)
    };
    VkPipelineLayoutCreateInfo plci = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount = 1, .pSetLayouts = &dsl,
        .pushConstantRangeCount = 1, .pPushConstantRanges = &pcr
    };
    CHK(vkCreatePipelineLayout(dev, &plci, NULL, &playout), "vkCreatePipelineLayout");
    printf("  pipeline layout con push constant (offset 0, %zu B)\n", sizeof(uint32_t));

    VkComputePipelineCreateInfo cpci = {
        .sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
        .stage = { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                   .stage = VK_SHADER_STAGE_COMPUTE_BIT, .module = shader, .pName = "main" },
        .layout = playout
    };
    CHK(vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpci, NULL, &pipe),
        "vkCreateComputePipelines");
    printf("  compute pipeline creado\n");

    VkBufferCreateInfo bci = {
        .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        .size = in_size, .usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
        .sharingMode = VK_SHARING_MODE_EXCLUSIVE
    };
    CHK(vkCreateBuffer(dev, &bci, NULL, &inbuf), "vkCreateBuffer(input)");
    bci.size = out_size;
    CHK(vkCreateBuffer(dev, &bci, NULL, &outbuf), "vkCreateBuffer(output)");

    vkGetBufferMemoryRequirements(dev, inbuf, &inreq);
    vkGetBufferMemoryRequirements(dev, outbuf, &outreq);

    uint32_t it = find_memory_type(&memprops, inreq.memoryTypeBits,
                                  VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                                  VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    if (it == UINT32_MAX) {
        it = find_memory_type(&memprops, inreq.memoryTypeBits, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT);
        coherent = 0;
        printf("  AVISO: no hay HOST_COHERENT; se usara flush/invalidate explicitos\n");
    }
    VkMemoryAllocateInfo mai = {
        .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        .allocationSize = inreq.size, .memoryTypeIndex = it
    };
    CHK(vkAllocateMemory(dev, &mai, NULL, &inmem), "vkAllocateMemory(input)");
    mai.allocationSize = outreq.size;
    mai.memoryTypeIndex = find_memory_type(&memprops, outreq.memoryTypeBits,
              coherent ? (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
                       :  VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT);
    CHK(vkAllocateMemory(dev, &mai, NULL, &outmem), "vkAllocateMemory(output)");
    vkBindBufferMemory(dev, inbuf, inmem, 0);
    vkBindBufferMemory(dev, outbuf, outmem, 0);
    printf("  memoria asignada y ligada\n");

    CHK(vkMapMemory(dev, inmem, 0, in_size, 0, &mapped), "vkMapMemory(input)");
    memcpy(mapped, g_cmp, in_size);
    if (!coherent) {
        VkMappedMemoryRange r = { .sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
                                 .memory = inmem, .offset = 0, .size = VK_WHOLE_SIZE };
        vkFlushMappedMemoryRanges(dev, 1, &r);
    }
    vkUnmapMemory(dev, inmem);
    printf("  corpus subido a la GPU: %d bloques, %zu B\n", NUM_BLOCKS, in_size);

    VkDescriptorPoolSize dps = { .type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 2 };
    VkDescriptorPoolCreateInfo dpci = {
        .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets = 1, .poolSizeCount = 1, .pPoolSizes = &dps
    };
    CHK(vkCreateDescriptorPool(dev, &dpci, NULL, &dpool), "vkCreateDescriptorPool");

    VkDescriptorSetAllocateInfo dsai = {
        .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool = dpool, .descriptorSetCount = 1, .pSetLayouts = &dsl
    };
    CHK(vkAllocateDescriptorSets(dev, &dsai, &dset), "vkAllocateDescriptorSets");

    VkDescriptorBufferInfo dbi_in  = { .buffer = inbuf,  .offset = 0, .range = in_size };
    VkDescriptorBufferInfo dbi_out = { .buffer = outbuf, .offset = 0, .range = out_size };
    VkWriteDescriptorSet w[2] = {0};
    for (i = 0; i < 2; i++) {
        w[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        w[i].dstSet = dset; w[i].dstBinding = (uint32_t)i; w[i].descriptorCount = 1;
        w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        w[i].pBufferInfo = (i == 0) ? &dbi_in : &dbi_out;
    }
    vkUpdateDescriptorSets(dev, 2, w, 0, NULL);

    VkCommandPoolCreateInfo cpool_ci = {
        .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO, .queueFamilyIndex = qfam
    };
    CHK(vkCreateCommandPool(dev, &cpool_ci, NULL, &cpool), "vkCreateCommandPool");

    VkCommandBufferAllocateInfo cbai = {
        .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        .commandPool = cpool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
        .commandBufferCount = 1
    };
    CHK(vkAllocateCommandBuffers(dev, &cbai, &cbuf), "vkAllocateCommandBuffers");

    VkCommandBufferBeginInfo cbbi = {
        .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
    };
    CHK(vkBeginCommandBuffer(cbuf, &cbbi), "vkBeginCommandBuffer");
    vkCmdBindPipeline(cbuf, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(cbuf, VK_PIPELINE_BIND_POINT_COMPUTE, playout, 0, 1, &dset, 0, NULL);

    /* Declaring the push constant range is not enough: it must be pushed, or the
     * shader's own bounds check reads an uninitialised num_blocks and the
     * output buffer stays zero. */
    uint32_t num_blocks = NUM_BLOCKS;
    vkCmdPushConstants(cbuf, playout, VK_SHADER_STAGE_COMPUTE_BIT, 0,
                       sizeof(num_blocks), &num_blocks);

    /* ceil(NUM_BLOCKS / 16), not NUM_BLOCKS and not NUM_BLOCKS/256. */
    vkCmdDispatch(cbuf, DISPATCH_GROUPS, 1, 1);
    CHK(vkEndCommandBuffer(cbuf), "vkEndCommandBuffer");

    VkSubmitInfo si = {
        .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
        .commandBufferCount = 1, .pCommandBuffers = &cbuf
    };
    CHK(vkQueueSubmit(queue, 1, &si, VK_NULL_HANDLE), "vkQueueSubmit");
    CHK(vkQueueWaitIdle(queue), "vkQueueWaitIdle");
    ran_ok = 1;
    printf("  dispatch: %u workgroups x %u hilos = %u hilos, %u bloques por wg -> %u bloques\n",
           DISPATCH_GROUPS, SHADER_LOCAL_SIZE_X, TOTAL_THREADS, SHADER_BLOCKS_PER_WG,
           DISPATCH_GROUPS * SHADER_BLOCKS_PER_WG);
    printf("  shader ejecutado y esperado en la cola\n");

    CHK(vkMapMemory(dev, outmem, 0, out_size, 0, &mapped), "vkMapMemory(output)");
    if (!coherent) {
        VkMappedMemoryRange r = { .sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
                                 .memory = outmem, .offset = 0, .size = VK_WHOLE_SIZE };
        vkInvalidateMappedMemoryRanges(dev, 1, &r);
    }
    memcpy(g_gpu, mapped, out_size);
    vkUnmapMemory(dev, outmem);

    /* ---- VALIDATION BEFORE COMPARISON. See header. ----
     * An all-zero readback compares equal to a zero reference and yields a
     * clean "0 discrepancies". Refuse that, and make it a failure. */
    printf("\n  -- validacion de datos ANTES de comparar --\n");
    {
        int nonzero = 0, varies = 0;
        for (i = 0; i < GPU_OUT_BYTES; i++) if (g_gpu[i]) nonzero++;
        printf("    bytes no nulos en la salida: %d de %d\n", nonzero, GPU_OUT_BYTES);
        if (nonzero == 0) {
            fprintf(stderr, "    ERROR: la salida es TODA CERO; el shader no escribio.\n");
            fprintf(stderr, "    Comparar ahora daria 0 discrepancias y PASS, que no probaria nada.\n");
            fprintf(stderr, "    Causas probables: push constant no empujado, dispatch no enviado,\n");
            fprintf(stderr, "    pipeline mal construido o buffer no enlazado.\n");
            goto cleanup;
        }
        for (i = 1; i < GPU_OUT_BYTES; i++) if (g_gpu[i] != g_gpu[0]) { varies = 1; break; }
        printf("    la salida varia entre pixeles: %s\n", varies ? "si" : "NO");
        if (!varies) {
            fprintf(stderr, "    ERROR: salida constante; el shader no esta decodificando.\n");
            goto cleanup;
        }
    }

    printf("\n  -- comparacion byte a byte GPU vs CPU --\n");
    {
        int a_bad = 0, rgb_bad = 0, a_blocks = 0, rgb_blocks = 0;
        for (i = 0; i < NUM_BLOCKS; i++) {
            int ja = 0, jr = 0, px, ch;
            for (px = 0; px < 16; px++) {
                for (ch = 0; ch < 4; ch++) {
                    uint8_t g = g_gpu[i * RX550_INPUT_BLOCK_BYTES + px * 4 + ch];
                    uint8_t c = g_cpu[i].px[px * 4 + ch];
                    if (g != c) {
                        discrepancies++;
                        if (ch == 3) ja++; else jr++;
                        if (discrepancies <= 8)
                            fprintf(stderr, "      bloque %d px %d canal %d: GPU=%3u CPU=%3u\n",
                                    i, px, ch, g, c);
                    }
                }
            }
            a_bad += ja; rgb_bad += jr;
            if (ja) a_blocks++;
            if (jr) rgb_blocks++;
        }
        printf("    discrepancias totales : %d de %d canales\n", discrepancies, GPU_OUT_BYTES);
        printf("      canal alfa (A)    : %d  en %d bloques\n", a_bad, a_blocks);
        printf("      canales RGB        : %d  en %d bloques\n", rgb_bad, rgb_blocks);
        printf("    cobertura: %d bloques modo 4 valores, %d modo 6 (a0==a1), %d a mano (a0>a1)\n",
               g_blocks_4val, g_blocks_6val, g_six_hand);
        agree = (discrepancies == 0);
    }

cleanup:
    if (cpool)   vkDestroyCommandPool(dev, cpool, NULL);
    if (dpool)   vkDestroyDescriptorPool(dev, dpool, NULL);
    if (pipe)    vkDestroyPipeline(dev, pipe, NULL);
    if (playout) vkDestroyPipelineLayout(dev, playout, NULL);
    if (dsl)     vkDestroyDescriptorSetLayout(dev, dsl, NULL);
    if (shader)  vkDestroyShaderModule(dev, shader, NULL);
    if (inbuf)   vkDestroyBuffer(dev, inbuf, NULL);
    if (outbuf)  vkDestroyBuffer(dev, outbuf, NULL);
    if (inmem)   vkFreeMemory(dev, inmem, NULL);
    if (outmem)  vkFreeMemory(dev, outmem, NULL);
    if (dev)     vkDestroyDevice(dev, NULL);
    if (instance) vkDestroyInstance(instance, NULL);
    free(spv);

    if (!ran_ok) {
        fprintf(stderr, "\n  FASE B: no se llego a ejecutar el shader\n");
        return 0;
    }
    /* Exit 0 must mean the GPU output equals the CPU output. An earlier revision
     * printed [FAIL] to stderr and returned 0, so make and CI would have read a
     * failing test as a passing one. */
    printf("\n  VEREDICTO: %s (%d discrepancias)\n",
           agree ? "GPU == CPU, agreement test PASADO"
                 : "GPU != CPU, agreement test FALLIDO",
           discrepancies);
    return agree;
}

int main(int argc, char **argv)
{
    printf("=== Agreement test GPU vs CPU para decompress_bc3.comp ===\n");
    printf("    encoder : ../compressor, BC3 conforme a la spec Microsoft (AD-11)\n");
    printf("    shader  : decompress_bc3.comp -> decompress_bc3.spv\n");
    printf("    objetivo: el GLSL en la RX 550 produce lo que produce el C\n\n");

    if (!phase_a_preparation()) {
        printf("\nRESULTADO: FASE A FALLIDA\n");
        return 1;
    }
    printf("\nRESULTADO: FASE A OK\n");

    if (argc > 1 && strcmp(argv[1], "--gpu") == 0)
        return phase_b_gpu_execution() ? 0 : 1;

    printf("\nFase B omitida. Usa --gpu (autorizado por AD-7).\n");
    printf("Estado del enlace shader<->C: NO ESTABLECIDO hasta que corra.\n");
    return 0;
}
