/* SPDX-License-Identifier: MIT
 *
 * rx550_decompress - BC3 -> RGBA on the RX 550 (Fase 2), command-line face.
 *
 * WHAT IT IS
 *
 * The Vulkan path of ../decompressor/test_decompress.c, generalised from that
 * program's fixed 64-block synthetic corpus to an arbitrary BC3 file, and
 * turned into a tool that writes a PNG instead of only counting differences.
 *
 * The shader is NOT reimplemented here. decompress_bc3.spv is loaded from
 * ../decompressor and executed on the RX 550, identified by PCI
 * vendorID 0x1002 / deviceID 0x699f, never by enumeration index. The reason
 * is in F4-AD-13's neighbourhood and in test_decompress.c: this host exposes
 * three Vulkan devices (Intel iGPU, RX 550, llvmpipe) and their order is not
 * stable across runs, so an index would silently pick the wrong one.
 *
 * WHAT IT PROVES, AND WHAT IT DOES NOT
 *
 * A pass means: for these blocks, the GPU decoder and the CPU decoder produce
 * identical bytes. It does NOT mean the GPU decoder is correct -- it means it
 * agrees with rx550_decompress_block(). Both could be wrong together. The
 * check that catches that is conformance against the transcribed BC3 rule,
 * which lives in ../compressor/test_alpha_ramp_independent.c and is not
 * repeated here. This is the failure mode that produced commit 05c6297: a
 * round trip between two mutually consistent implementations passes while
 * both disagree with the format.
 *
 * VALIDATION PRECEDES COMPARISON
 *
 * Before any byte comparison, the GPU output is checked to be non-trivial and
 * to vary between pixels. A dispatch that never runs leaves the buffer as it
 * was initialised, which compares equal to a zeroed reference and reports a
 * clean "0 discrepancies". That is a false PASS, it already happened once in
 * this project, and it is why those two checks are not decoration.
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <vulkan/vulkan.h>

#include "../compressor/rx550_compress.h"
#include "../common/png_rw.h"

#define RX550_VENDOR_ID 0x1002u
#define RX550_DEVICE_ID 0x699Fu

/* These three must agree with ../decompressor/decompress_bc3.comp. They are
 * asserted against the shader source text at run time, in check_geometry(),
 * because a silent divergence here dispatches the wrong number of workgroups
 * and reads past the end of the buffer. */
#define SHADER_LOCAL_SIZE_X    256u
#define SHADER_BLOCKS_PER_WG   16u
#define DISPATCH_GROUPS(nblocks) \
    (((uint32_t)(nblocks) + SHADER_BLOCKS_PER_WG - 1u) / SHADER_BLOCKS_PER_WG)

static void usage(const char *me)
{
    fprintf(stderr,
        "uso: %s <entrada.bc3> <salida.png> [referencia.rgba]\n"
        "\n"
        "  Fase 2. Decodifica BC3 en la RX 550 por Vulkan compute, escribe\n"
        "  el PNG resultante y lo compara byte a byte con la referencia CPU.\n"
        "  Si se da <referencia.rgba>, compara contra ella; en su defecto\n"
        "  calcula la referencia con el decodificador de este programa.\n"
        "\n"
        "  Requiere autorizacion para ejecutar compute en la GPU (AD-7).\n"
        "  Sale con codigo distinto de cero ante cualquier discrepancia.\n", me);
}

static int check_geometry(const char *comp_path)
{
    FILE *f = fopen(comp_path, "r");
    char  line[512];
    int   seen_local = 0, seen_shift = 0, seen_mul = 0, bad = 0;

    if (!f) {
        fprintf(stderr, "ERROR: no se pudo abrir '%s'\n", comp_path);
        return 0;
    }
    while (fgets(line, sizeof line, f)) {
        if (strstr(line, "local_size_x") && strstr(line, "256")) seen_local = 1;
        if (strstr(line, "gl_LocalInvocationID.x >> 4u"))            seen_shift = 1;
        if (strstr(line, "gl_WorkGroupID.x * 16u"))                 seen_mul   = 1;
    }
    fclose(f);

    if (!seen_local) { fprintf(stderr, "ERROR: el shader ya no declara local_size_x = 256\n"); bad++; }
    if (!seen_shift) { fprintf(stderr, "ERROR: el shader ya no usa '>> 4u'; revisa BLOCKS_PER_WG\n"); bad++; }
    if (!seen_mul)   { fprintf(stderr, "ERROR: el shader ya no usa '* 16u'; revisa BLOCKS_PER_WG\n"); bad++; }
    if (bad) {
        fprintf(stderr, "La geometria de dispatch ya no coincide con el shader. No se continua:\n"
                        "un dispatch erroneo lee o escribe fuera del buffer.\n");
        return 0;
    }
    return 1;
}

static uint32_t find_memory_type(const VkPhysicalDeviceMemoryProperties *mp,
                                 uint32_t bits, VkMemoryPropertyFlags want)
{
    for (uint32_t i = 0; i < mp->memoryTypeCount; i++)
        if ((bits & (1u << i)) && (mp->memoryTypes[i].propertyFlags & want) == want)
            return i;
    return UINT32_MAX;
}

#define CHK(expr, what)                                                        \
    do {                                                                       \
        VkResult _r = (expr);                                                  \
        if (_r != VK_SUCCESS) {                                                \
            fprintf(stderr, "ERROR: %s -> VkResult %d\n", (what), (int)_r);     \
            goto cleanup;                                                      \
        }                                                                      \
    } while (0)

int main(int argc, char **argv)
{
    VkInstance       instance = VK_NULL_HANDLE;
    VkPhysicalDevice phys = VK_NULL_HANDLE;
    VkDevice         dev = VK_NULL_HANDLE;
    VkQueue          queue = VK_NULL_HANDLE;
    VkShaderModule   shader = VK_NULL_HANDLE;
    VkDescriptorSetLayout dsl = VK_NULL_HANDLE;
    VkPipelineLayout playout = VK_NULL_HANDLE;
    VkPipeline       pipe = VK_NULL_HANDLE;
    VkDescriptorPool dpool = VK_NULL_HANDLE;
    VkDescriptorSet  dset = VK_NULL_HANDLE;
    VkBuffer         inbuf = VK_NULL_HANDLE, outbuf = VK_NULL_HANDLE;
    VkDeviceMemory   inmem = VK_NULL_HANDLE, outmem = VK_NULL_HANDLE;
    VkCommandPool    cpool = VK_NULL_HANDLE;
    VkCommandBuffer  cbuf = VK_NULL_HANDLE;
    VkPhysicalDeviceMemoryProperties memprops;
    VkMemoryRequirements inreq, outreq;
    uint32_t         qfam = UINT32_MAX;
    uint8_t         *bc3 = NULL, *gpu = NULL, *cpu = NULL, *orig = NULL;
    char             err[512];
    const char      *comp_path = "../decompressor/decompress_bc3.comp";
    const char      *spv_path  = "../decompressor/decompress_bc3.spv";
    uint32_t        *spv = NULL;
    size_t           spv_bytes = 0, nblocks = 0, out_bytes;
    void            *mapped = NULL;
    int              coherent = 1, i, rc = 1, nonzero = 0, varies = 0;
    int              discrepancies = 0;
    VkDeviceSize     in_size;
    rx550_image_t    img;

    memset(&img, 0, sizeof img);

    if (argc < 3 || argc > 4) { usage(argv[0]); return 2; }

    /* ---- input ---- */
    {
        FILE *f = fopen(argv[1], "rb");
        long  sz;
        if (!f) { fprintf(stderr, "ERROR: no se pudo abrir '%s'\n", argv[1]); return 1; }
        fseek(f, 0, SEEK_END); sz = ftell(f); rewind(f);
        if (sz <= 0 || sz % (long)RX550_BLOCK_BYTES) {
            fprintf(stderr, "ERROR: '%s' mide %ld B; debe ser multiplo de %d\n",
                    argv[1], sz, RX550_BLOCK_BYTES);
            fclose(f); return 1;
        }
        nblocks = (size_t)sz / RX550_BLOCK_BYTES;
        bc3 = malloc((size_t)sz);
        if (!bc3) { fprintf(stderr, "ERROR: sin memoria\n"); fclose(f); return 1; }
        if (fread(bc3, 1, (size_t)sz, f) != (size_t)sz) {
            fprintf(stderr, "ERROR: lectura incompleta de '%s'\n", argv[1]);
            fclose(f); free(bc3); return 1;
        }
        fclose(f);
    }
    out_bytes = nblocks * RX550_INPUT_BLOCK_BYTES;
    printf("  entrada   : %s\n", argv[1]);
    printf("  bloques   : %zu (%zu B BC3 -> %zu B RGBA)\n",
           nblocks, nblocks * RX550_BLOCK_BYTES, out_bytes);

    if (!check_geometry(comp_path)) { free(bc3); return 1; }
    printf("  geometria : local_size_x=%u, %u bloques por workgroup, "
           "%u workgroups para %zu bloques\n",
           SHADER_LOCAL_SIZE_X, SHADER_BLOCKS_PER_WG, DISPATCH_GROUPS(nblocks), nblocks);

    /* ---- CPU reference ---- */
    cpu = calloc(nblocks, RX550_INPUT_BLOCK_BYTES);
    if (!cpu) { fprintf(stderr, "ERROR: sin memoria para la referencia CPU\n"); goto cleanup; }
    for (i = 0; (size_t)i < nblocks; i++)
        rx550_decompress_block((const rx550_block_t *)bc3 + i,
                               (rx550_rgba_block_t *)cpu + i);

    if (argc == 4) {
        FILE *f = fopen(argv[3], "rb");
        long  sz;
        if (!f) {
            fprintf(stderr, "ERROR: no se pudo abrir la referencia '%s'\n", argv[3]);
            goto cleanup;
        }
        fseek(f, 0, SEEK_END); sz = ftell(f); rewind(f);
        if ((size_t)sz != out_bytes) {
            fprintf(stderr, "ERROR: la referencia mide %ld B, la imagen tiene %zu B\n",
                    sz, out_bytes);
            fclose(f); goto cleanup;
        }
        orig = malloc((size_t)sz);
        if (!orig) { fclose(f); fprintf(stderr, "ERROR: sin memoria\n"); goto cleanup; }
        if (fread(orig, 1, (size_t)sz, f) != (size_t)sz) {
            fprintf(stderr, "ERROR: lectura incompleta de la referencia\n");
            fclose(f); goto cleanup;
        }
        fclose(f);
    } else {
        orig = cpu;
    }

    /* ---- Vulkan ---- */
    in_size = nblocks * RX550_BLOCK_BYTES;

    {
        VkApplicationInfo app = {0};
        VkInstanceCreateInfo ici = {0};
        app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        app.pApplicationName = "rx550_decompress";
        app.applicationVersion = VK_MAKE_VERSION(1,0,0);
        app.pEngineName = "rx550"; app.engineVersion = VK_MAKE_VERSION(1,0,0);
        app.apiVersion = VK_API_VERSION_1_0;
        ici.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
        ici.pApplicationInfo = &app;
        CHK(vkCreateInstance(&ici, NULL, &instance), "vkCreateInstance");
    }

    {
        uint32_t ndev = 0, n;
        VkPhysicalDevice *devs;
        CHK(vkEnumeratePhysicalDevices(instance, &ndev, NULL), "vkEnumeratePhysicalDevices(1)");
        if (ndev == 0) { fprintf(stderr, "ERROR: sin dispositivos Vulkan\n"); goto cleanup; }
        devs = calloc(ndev, sizeof *devs);
        if (!devs) { fprintf(stderr, "ERROR: sin memoria\n"); goto cleanup; }
        CHK(vkEnumeratePhysicalDevices(instance, &ndev, devs), "vkEnumeratePhysicalDevices(2)");
        for (n = 0; n < ndev; n++) {
            VkPhysicalDeviceProperties p;
            vkGetPhysicalDeviceProperties(devs[n], &p);
            printf("    [%u] %04x:%04x  %s\n", n, p.vendorID, p.deviceID, p.deviceName);
            if (p.vendorID == RX550_VENDOR_ID && p.deviceID == RX550_DEVICE_ID && phys == VK_NULL_HANDLE)
                phys = devs[n];
        }
        free(devs);
        if (phys == VK_NULL_HANDLE) {
            fprintf(stderr, "ERROR: no se encontro %04x:%04x por identidad PCI\n",
                    RX550_VENDOR_ID, RX550_DEVICE_ID);
            goto cleanup;
        }
        printf("  OK: RX 550 identificada por PCI, no por indice\n");
    }

    {
        uint32_t nqf = 0, n;
        VkQueueFamilyProperties *qfs;
        vkGetPhysicalDeviceQueueFamilyProperties(phys, &nqf, NULL);
        qfs = calloc(nqf ? nqf : 1, sizeof *qfs);
        if (!qfs) { fprintf(stderr, "ERROR: sin memoria\n"); goto cleanup; }
        vkGetPhysicalDeviceQueueFamilyProperties(phys, &nqf, qfs);
        for (n = 0; n < nqf; n++)
            if (qfs[n].queueFlags & VK_QUEUE_COMPUTE_BIT) { qfam = n; break; }
        free(qfs);
        if (qfam == UINT32_MAX) {
            fprintf(stderr, "ERROR: ninguna queue family con compute\n"); goto cleanup;
        }
    }

    {
        float prio = 1.0f;
        VkDeviceQueueCreateInfo qci = {0};
        VkDeviceCreateInfo     dci = {0};
        qci.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        qci.queueFamilyIndex = qfam; qci.queueCount = 1; qci.pQueuePriorities = &prio;
        dci.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
        dci.queueCreateInfoCount = 1; dci.pQueueCreateInfos = &qci;
        CHK(vkCreateDevice(phys, &dci, NULL, &dev), "vkCreateDevice");
    }
    vkGetDeviceQueue(dev, qfam, 0, &queue);
    vkGetPhysicalDeviceMemoryProperties(phys, &memprops);

    {
        FILE *sf = fopen(spv_path, "rb");
        if (!sf) {
            fprintf(stderr, "ERROR: no se pudo abrir '%s'. Generalo con:\n"
                            "  make -C ../decompressor decompress_bc3.spv\n", spv_path);
            goto cleanup;
        }
        fseek(sf, 0, SEEK_END); spv_bytes = (size_t)ftell(sf); rewind(sf);
        spv = malloc(spv_bytes);
        if (!spv || fread(spv, 1, spv_bytes, sf) != spv_bytes) {
            fprintf(stderr, "ERROR: lectura de SPIR-V incompleta\n");
            fclose(sf); free(spv); spv = NULL; goto cleanup;
        }
        fclose(sf);
        if (spv_bytes < 4 || spv[0] != 0x07230203u) {
            fprintf(stderr, "ERROR: '%s' no es un modulo SPIR-V (magic %08x)\n",
                    spv_path, spv[0]);
            goto cleanup;
        }
    }
    printf("  SPIR-V    : %s (%zu B)\n", spv_path, spv_bytes);

    {
        VkShaderModuleCreateInfo smci = {0};
        smci.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        smci.codeSize = spv_bytes; smci.pCode = spv;
        CHK(vkCreateShaderModule(dev, &smci, NULL, &shader), "vkCreateShaderModule");
        free(spv); spv = NULL;
    }

    {
        VkDescriptorSetLayoutBinding binds[2] = {0};
        /* EVERY Vk*CreateInfo below is zero-initialised first and then filled
         * in. A designated initialiser `= { .sType = ... }` zeroes the rest
         * too, but only because the whole object is initialised; declaring
         * `T x;` and then assigning x.sType leaves every other field --
         * flags, pNext, and any field a future header adds -- as stack
         * garbage. The loader then reads pNext as a pointer. That is the
         * crash this comment exists to prevent, and it is the same failure
         * mode test_decompress.c records for hand-declared Vulkan structs. */
        VkDescriptorSetLayoutCreateInfo dslci = {0};
        for (i = 0; i < 2; i++) {
            binds[i].binding = (uint32_t)i;
            binds[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            binds[i].descriptorCount = 1;
            binds[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        }
        dslci.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        dslci.bindingCount = 2; dslci.pBindings = binds;
        CHK(vkCreateDescriptorSetLayout(dev, &dslci, NULL, &dsl), "vkCreateDescriptorSetLayout");

        VkPushConstantRange      pcr  = {0};
        VkPipelineLayoutCreateInfo plci = {0};
        VkComputePipelineCreateInfo cpci = {0};
        pcr.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        pcr.offset = 0; pcr.size = sizeof(uint32_t);
        plci.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        plci.setLayoutCount = 1; plci.pSetLayouts = &dsl;
        plci.pushConstantRangeCount = 1; plci.pPushConstantRanges = &pcr;
        CHK(vkCreatePipelineLayout(dev, &plci, NULL, &playout), "vkCreatePipelineLayout");

        cpci.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
        cpci.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        cpci.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        cpci.stage.module = shader; cpci.stage.pName = "main";
        cpci.layout = playout;
        CHK(vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpci, NULL, &pipe),
            "vkCreateComputePipelines");
    }

    {
        VkBufferCreateInfo bci = {0};
        bci.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        bci.size = in_size; bci.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        bci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
        /* Zero-initialised: see the note above dslci. */
        VkCommandPoolCreateInfo   cpool_ci = {0};
        VkCommandBufferAllocateInfo cbai  = {0};
        VkCommandBufferBeginInfo  cbbi    = {0};
        VkDescriptorPoolSize      dps     = {0};
        VkDescriptorPoolCreateInfo dpci   = {0};
        VkDescriptorSetAllocateInfo dsai  = {0};
        VkDescriptorBufferInfo    dbi_in  = {0}, dbi_out = {0};
        VkWriteDescriptorSet      w[2]    = {0};
        VkSubmitInfo              si      = {0};
        uint32_t num_blocks = (uint32_t)nblocks;
        uint32_t it, it_out;

        CHK(vkCreateBuffer(dev, &bci, NULL, &inbuf), "vkCreateBuffer(input)");
        bci.size = out_bytes;
        CHK(vkCreateBuffer(dev, &bci, NULL, &outbuf), "vkCreateBuffer(output)");
        vkGetBufferMemoryRequirements(dev, inbuf, &inreq);
        vkGetBufferMemoryRequirements(dev, outbuf, &outreq);

        it = find_memory_type(&memprops, inreq.memoryTypeBits,
                              VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                              VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        if (it == UINT32_MAX) {
            it = find_memory_type(&memprops, inreq.memoryTypeBits,
                                  VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT);
            coherent = 0;
        }
        it_out = find_memory_type(&memprops, outreq.memoryTypeBits,
                                  coherent ? (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                                              VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
                                           :  VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT);
        if (it == UINT32_MAX || it_out == UINT32_MAX) {
            fprintf(stderr, "ERROR: sin memoria HOST_VISIBLE para buffers\n");
            goto cleanup;
        }

        {
            VkMemoryAllocateInfo mai = {0};
            mai.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
            mai.allocationSize = inreq.size; mai.memoryTypeIndex = it;
            CHK(vkAllocateMemory(dev, &mai, NULL, &inmem), "vkAllocateMemory(input)");
            mai.allocationSize = outreq.size;
            mai.memoryTypeIndex = it_out;
            CHK(vkAllocateMemory(dev, &mai, NULL, &outmem), "vkAllocateMemory(output)");
        }
        vkBindBufferMemory(dev, inbuf, inmem, 0);
        vkBindBufferMemory(dev, outbuf, outmem, 0);

        /* Poison the output before the dispatch. If the shader never writes,
         * the readback below is this pattern, and 0xDEADBEEF surviving is
         * therefore an observable fact rather than an absence. */
        CHK(vkMapMemory(dev, outmem, 0, out_bytes, 0, &mapped), "vkMapMemory(output)");
        {
            uint32_t poison = 0xDEADBEEFu, *w32 = (uint32_t *)mapped;
            size_t nw = out_bytes / 4;
            if (out_bytes % 4) memset((uint8_t *)mapped + nw * 4, 0xA5, out_bytes - nw * 4);
            for (size_t k = 0; k < nw; k++) w32[k] = poison;
            if (!coherent) {
                VkMappedMemoryRange r = {0};
                r.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
                r.memory = outmem; r.offset = 0; r.size = VK_WHOLE_SIZE;
                vkFlushMappedMemoryRanges(dev, 1, &r);
            }
        }
        vkUnmapMemory(dev, outmem);

        CHK(vkMapMemory(dev, inmem, 0, in_size, 0, &mapped), "vkMapMemory(input)");
        memcpy(mapped, bc3, (size_t)in_size);
        if (!coherent) {
            VkMappedMemoryRange r = {0};
            r.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            r.memory = inmem; r.offset = 0; r.size = VK_WHOLE_SIZE;
            vkFlushMappedMemoryRanges(dev, 1, &r);
        }
        vkUnmapMemory(dev, inmem);

        dps.type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; dps.descriptorCount = 2;
        dpci.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        dpci.maxSets = 1; dpci.poolSizeCount = 1; dpci.pPoolSizes = &dps;
        CHK(vkCreateDescriptorPool(dev, &dpci, NULL, &dpool), "vkCreateDescriptorPool");
        dsai.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        dsai.descriptorPool = dpool; dsai.descriptorSetCount = 1;
        dsai.pSetLayouts = &dsl;
        CHK(vkAllocateDescriptorSets(dev, &dsai, &dset), "vkAllocateDescriptorSets");

        dbi_in.buffer = inbuf;  dbi_in.offset = 0; dbi_in.range = in_size;
        dbi_out.buffer = outbuf; dbi_out.offset = 0; dbi_out.range = out_bytes;
        for (i = 0; i < 2; i++) {
            w[i] = (VkWriteDescriptorSet){0};
            w[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
            w[i].dstSet = dset; w[i].dstBinding = (uint32_t)i;
            w[i].descriptorCount = 1;
            w[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            w[i].pBufferInfo = (i == 0) ? &dbi_in : &dbi_out;
        }
        vkUpdateDescriptorSets(dev, 2, w, 0, NULL);

        cpool_ci.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
        cpool_ci.queueFamilyIndex = qfam;
        CHK(vkCreateCommandPool(dev, &cpool_ci, NULL, &cpool), "vkCreateCommandPool");
        cbai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        cbai.commandPool = cpool; cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cbai.commandBufferCount = 1;
        CHK(vkAllocateCommandBuffers(dev, &cbai, &cbuf), "vkAllocateCommandBuffers");
        cbbi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        cbbi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        CHK(vkBeginCommandBuffer(cbuf, &cbbi), "vkBeginCommandBuffer");
        vkCmdBindPipeline(cbuf, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
        vkCmdBindDescriptorSets(cbuf, VK_PIPELINE_BIND_POINT_COMPUTE, playout, 0, 1, &dset, 0, NULL);
        /* Declaring the range is not enough; it must be pushed, or the shader
         * reads an uninitialised num_blocks and writes nothing. */
        vkCmdPushConstants(cbuf, playout, VK_SHADER_STAGE_COMPUTE_BIT, 0,
                           sizeof(num_blocks), &num_blocks);
        vkCmdDispatch(cbuf, DISPATCH_GROUPS(nblocks), 1, 1);
        CHK(vkEndCommandBuffer(cbuf), "vkEndCommandBuffer");
        si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        si.commandBufferCount = 1; si.pCommandBuffers = &cbuf;
        CHK(vkQueueSubmit(queue, 1, &si, VK_NULL_HANDLE), "vkQueueSubmit");
        CHK(vkQueueWaitIdle(queue), "vkQueueWaitIdle");

        gpu = malloc(out_bytes);
        if (!gpu) { fprintf(stderr, "ERROR: sin memoria para la lectura\n"); goto cleanup; }
        CHK(vkMapMemory(dev, outmem, 0, out_bytes, 0, &mapped), "vkMapMemory(output)");
        if (!coherent) {
            VkMappedMemoryRange r = {0};
            r.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            r.memory = outmem; r.offset = 0; r.size = VK_WHOLE_SIZE;
            vkInvalidateMappedMemoryRanges(dev, 1, &r);
        }
        memcpy(gpu, mapped, out_bytes);
        vkUnmapMemory(dev, outmem);
    }
    printf("  dispatch  : %u workgroups x %u hilos, esperado en la cola\n",
           DISPATCH_GROUPS(nblocks), SHADER_LOCAL_SIZE_X);

    /* ---- VALIDATION BEFORE COMPARISON ---- */
    {
        size_t poisoned = 0, k;
        for (k = 0; k + 3 < out_bytes; k += 4) {
            uint32_t w32;
            memcpy(&w32, gpu + k, 4);
            if (w32 == 0xDEADBEEFu) poisoned += 4;
        }
        for (i = 0; (size_t)i < out_bytes; i++) if (gpu[i]) nonzero++;
        for (i = 1; (size_t)i < out_bytes; i++) if (gpu[i] != gpu[0]) { varies = 1; break; }

        printf("  validacion previa a comparar:\n");
        printf("    bytes no nulos            : %d de %zu\n", nonzero, out_bytes);
        printf("    bytes con patron 0xDEADBEEF: %zu\n", poisoned);
        printf("    la salida varia           : %s\n", varies ? "si" : "NO");

        if (poisoned > 0) {
            fprintf(stderr, "ERROR: %zu B conservan el patron veneno. El shader no\n"
                            "       escribio esas palabras; comparar ahora daria un\n"
                            "       PASS sin haber ejecutado nada.\n", poisoned);
            goto cleanup;
        }
        if (nonzero == 0) {
            fprintf(stderr, "ERROR: la salida es TODA CERO. Un dispatch que no corre\n"
                            "       deja el buffer como estaba y compara igual que una\n"
                            "       referencia a cero: 0 discrepancias y PASS, que no\n"
                            "       probaria nada.\n");
            goto cleanup;
        }
        if (!varies) {
            fprintf(stderr, "ERROR: la salida es constante; el shader no decodifica.\n");
            goto cleanup;
        }
    }

    /* ---- compare GPU vs reference ---- */
    for (i = 0; (size_t)i < out_bytes; i++)
        if (gpu[i] != orig[i]) {
            if (discrepancies < 8)
                fprintf(stderr, "      byte %d: GPU=%3u ref=%3u\n", i, gpu[i], orig[i]);
            discrepancies++;
        }
    printf("  comparacion: %d de %zu bytes discrepantes (GPU vs %s)\n",
           discrepancies, out_bytes, argc == 4 ? argv[3] : "referencia CPU");

    /* ---- write PNG ---- */
    /*
     * GPU output is BLOCK ordered: block b's pixel p sits at b*64 + p*4. A PNG
     * needs IMAGE order, where block (bx,by) pixel (px,py) is at
     * (by*4+py)*stride + (bx*4+px)*4. For a single block the two coincide,
     * which is why a 64-block-corpus test can pass without this ever mattering;
     * for a real 256-block texture they do not, and writing the buffer out
     * unchanged produces a scrambled image that still "round-trips" against a
     * reference if the reference is scrambled the same way.
     *
     * The block grid is inferred as square (nblocks = side^2). That is a real
     * limitation and it is checked, not assumed: a non-square block grid
     * refuses to write a PNG rather than writing a wrong one.
     */
    {
        int side = (int)(nblocks / RX550_BLOCK_PIXELS);
        int w = side * RX550_BLOCK_DIM, h = side * RX550_BLOCK_DIM;

        if ((size_t)side * (size_t)side != nblocks) {
            fprintf(stderr, "AVISO: %zu bloques no forman un cuadrado de bloques "
                            "(%zu != k^2). El PNG no se escribe; el buffer de "
                            "%zu B esta disponible en memoria. Pases -W/-H para "
                            "una retícula no cuadrada.\n", nblocks, nblocks, out_bytes);
        } else {
            uint8_t *img_px = malloc(out_bytes);
            int bx, by, px, py;
            if (!img_px) {
                fprintf(stderr, "ERROR: sin memoria para reordenar a imagen\n");
                goto cleanup;
            }
            for (by = 0; by < side; by++)
                for (bx = 0; bx < side; bx++)
                    for (py = 0; py < RX550_BLOCK_DIM; py++)
                        for (px = 0; px < RX550_BLOCK_DIM; px++) {
                            size_t row = (size_t)(by * RX550_BLOCK_DIM + py);
                            size_t col = (size_t)(bx * RX550_BLOCK_DIM + px);
                            size_t src = ((size_t)(by * side + bx) * RX550_INPUT_BLOCK_BYTES)
                                       + (size_t)(py * RX550_BLOCK_DIM + px) * 4u;
                            /* BOTH terms carry the *4. Multiplying only the column
                             * term makes this a pixel offset for the row and a
                             * byte offset for the column, which writes the first
                             * row correctly and every later row into the wrong
                             * place. The symptom is a plausible-looking image
                             * whose top strip is right, so it survives a glance. */
                            size_t dst = (row * (size_t)w + col) * 4u;
                            memcpy(img_px + dst, gpu + src, 4);
                        }
            if (rx550_png_write(argv[2], img_px, w, h, err, sizeof err) != 0) {
                fprintf(stderr, "ERROR: %s\n", err);
            } else {
                printf("  PNG       : %s (%dx%d, reordenado de bloque a imagen)\n",
                       argv[2], w, h);
            }
            free(img_px);
        }
    }

    printf("  VEREDICTO  : %s\n",
           discrepancies == 0 ? "GPU == referencia, 0 discrepancias" : "HAY DISCREPANCIAS");
    rc = (discrepancies == 0) ? 0 : 1;

cleanup:
    /* ORDER MATTERS. The command buffer must be freed BEFORE its pool is
     * destroyed: vkFreeCommandBuffers returns it to the driver's free list,
     * and freeing it after the pool is gone dereferences a destroyed pool.
     * test_decompress.c has the same requirement; getting it wrong segfaults
     * inside radv_reset_cmd_buffer() at exit, AFTER a correct comparison, so
     * it looks like the shader failed when it did not. */
    if (cbuf && cpool) vkFreeCommandBuffers(dev, cpool, 1, &cbuf);
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
    free(spv); free(bc3); free(gpu); free(cpu);
    if (orig && orig != cpu) free(orig);
    return rc;
}
