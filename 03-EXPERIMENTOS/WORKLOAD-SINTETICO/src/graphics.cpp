// Workload gráfico (Diseño B, DESIGN-GRAPHICS.md) — RX 550 Polaris12 1002:699F.
// Vulkan 1.1, offscreen (sin presentación). Selección estricta de device.
// Seguridad: aborta limpiamente ante device lost / OOM / errores de creación /
// shader / timeout de fence / presupuesto de VRAM no alcanzable.
//
// Emisión determinista al stdout (para correlación del runner externo):
//   device, vendor/device, resolution, format, msaa, layers, textures, tex_size,
//   fma_per_fragment, seed, warmup_s, duration_s, start_wall_ns, end_wall_ns,
//   warmup_frames, frames, fps, frametime_ns (min/avg/max/p50), vram (heap/images),
//   sample_counts_cb, result, error.
#include <vulkan/vulkan.h>
#include <shaderc/shaderc.hpp>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

static constexpr uint32_t VENDOR_RX550   = 0x1002;
static constexpr uint32_t DEVICE_RX550   = 0x699F;
static constexpr uint64_t FENCE_TIMEOUT_NS = 10ull * 1000 * 1000 * 1000; // 10 s (detección de hang)

struct Config {
    uint32_t width       = 1920;
    uint32_t height      = 1080;
    uint32_t layers      = 4;      // overdraw (capas fullscreen acumulativas)
    uint32_t numTex      = 4;      // número de texturas 4096^2
    uint32_t texSize     = 4096;
    uint32_t fmaIters    = 4;      // 4 iteraciones x 6 FMA = 24 FMA/fragmento
    uint32_t seed0       = 0x13579BDFu;
    uint32_t seed1       = 0x2468ACE0u;
    uint32_t warmupSec   = 5;
    uint32_t durationSec = 20;
    uint32_t msaa        = 1;      // 1/2/4/8 (validado contra sampleCounts en runtime)
    bool     requireRx550 = true;
    bool     skipGen  = false; // depuración: no generar texturas (contenido indefinido)
    bool     skipFrag = false; // depuración: solo generación, sin loop de fragment
    std::string shaderDir = "src";
    std::string fragFile  = "fragment.frag"; // shader de fragmento (E1 o F2 experimental)
};

static void fatal(const char* what) {
    std::fprintf(stderr, "ERROR: %s\n", what);
    std::exit(1);
}

static void check(VkResult r, const char* what) {
    if (r == VK_SUCCESS) return;
    if (r == VK_ERROR_DEVICE_LOST) {
        std::fprintf(stderr, "ERROR_DEVICE_LOST: %s\n", what);
        std::exit(2);
    }
    if (r == VK_ERROR_OUT_OF_HOST_MEMORY || r == VK_ERROR_OUT_OF_DEVICE_MEMORY) {
        std::fprintf(stderr, "ERROR_OOM: %s (code=%d)\n", what, (int)r);
        std::exit(4);
    }
    std::fprintf(stderr, "ERROR %d en %s\n", (int)r, what);
    std::exit(1);
}

static std::string readFile(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f.is_open()) {
        std::fprintf(stderr, "ERROR: no se puede abrir %s\n", path.c_str());
        std::exit(1);
    }
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static VkShaderModule compileShader(VkDevice dev, const std::string& glsl,
                                    const char* name, shaderc_shader_kind kind) {
    shaderc::Compiler compiler;
    shaderc::CompileOptions options;
    options.SetTargetEnvironment(shaderc_target_env_vulkan, shaderc_env_version_vulkan_1_1);
    options.SetTargetSpirv(shaderc_spirv_version_1_3);
    options.SetOptimizationLevel(shaderc_optimization_level_performance);
    shaderc::SpvCompilationResult res =
        compiler.CompileGlslToSpv(glsl.data(), glsl.size(), kind, name, options);
    if (res.GetCompilationStatus() != shaderc_compilation_status_success) {
        std::fprintf(stderr, "ERROR shader %s:\n%s\n", name, res.GetErrorMessage().c_str());
        std::exit(1);
    }
    std::vector<uint32_t> spv(res.cbegin(), res.cend());
    VkShaderModuleCreateInfo ci{};
    ci.sType    = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    ci.codeSize = spv.size() * sizeof(uint32_t);
    ci.pCode    = spv.data();
    VkShaderModule module;
    check(vkCreateShaderModule(dev, &ci, nullptr, &module), "vkCreateShaderModule");
    return module;
}

static uint32_t findQueueFamily(VkPhysicalDevice dev, VkQueueFlags flags) {
    uint32_t n = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(dev, &n, nullptr);
    std::vector<VkQueueFamilyProperties> qf(n);
    vkGetPhysicalDeviceQueueFamilyProperties(dev, &n, qf.data());
    for (uint32_t i = 0; i < n; ++i)
        if (qf[i].queueFlags & flags) return i;
    return UINT32_MAX;
}

static VkPhysicalDevice pickPhysicalDevice(VkInstance inst, uint32_t wantVendor,
                                           uint32_t wantDevice,
                                           VkPhysicalDeviceProperties* outProps) {
    uint32_t n = 0;
    check(vkEnumeratePhysicalDevices(inst, &n, nullptr), "vkEnumeratePhysicalDevices(count)");
    std::vector<VkPhysicalDevice> pds(n);
    check(vkEnumeratePhysicalDevices(inst, &n, pds.data()), "vkEnumeratePhysicalDevices");
    for (VkPhysicalDevice pd : pds) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(pd, &p);
        std::printf("device: %s vendor=0x%04X device=0x%04X driver=0x%08X\n",
                    p.deviceName, p.vendorID, p.deviceID, p.driverVersion);
        if (p.vendorID == wantVendor && p.deviceID == wantDevice) {
            *outProps = p;
            return pd;
        }
    }
    return VK_NULL_HANDLE;
}

struct Image {
    VkImage       image  = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView   view   = VK_NULL_HANDLE;
    VkDeviceSize  vram   = 0;
};

static void createImage(VkDevice dev, VkPhysicalDevice pd, uint32_t w, uint32_t h,
                        VkFormat fmt, VkImageUsageFlags usage,
                        VkDeviceSize* totalVram, Image* out,
                        VkSampleCountFlagBits samples = VK_SAMPLE_COUNT_1_BIT) {
    VkImageCreateInfo ci{};
    ci.sType       = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    ci.imageType   = VK_IMAGE_TYPE_2D;
    ci.format      = fmt;
    ci.extent      = {w, h, 1};
    ci.mipLevels   = 1;
    ci.arrayLayers = 1;
    ci.samples     = samples;
    ci.tiling      = VK_IMAGE_TILING_OPTIMAL;
    ci.usage       = usage;
    ci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    check(vkCreateImage(dev, &ci, nullptr, &out->image), "vkCreateImage");

    VkMemoryRequirements req;
    vkGetImageMemoryRequirements(dev, out->image, &req);

    VkPhysicalDeviceMemoryProperties m;
    vkGetPhysicalDeviceMemoryProperties(pd, &m);
    int32_t chosen = -1;
    for (uint32_t i = 0; i < m.memoryTypeCount; ++i)
        if ((req.memoryTypeBits & (1u << i)) &&
            (m.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)) {
            chosen = (int32_t)i;
            break;
        }
    if (chosen < 0) fatal("imagen sin tipo de memoria DEVICE_LOCAL (asignación imposible)");

    VkMemoryAllocateInfo mai{};
    mai.sType           = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    mai.allocationSize  = req.size;
    mai.memoryTypeIndex = (uint32_t)chosen;
    check(vkAllocateMemory(dev, &mai, nullptr, &out->memory), "vkAllocateMemory(imagen)");
    check(vkBindImageMemory(dev, out->image, out->memory, 0), "vkBindImageMemory");
    out->vram = req.size;
    *totalVram += req.size;

    VkImageViewCreateInfo vci{};
    vci.sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    vci.image            = out->image;
    vci.viewType         = VK_IMAGE_VIEW_TYPE_2D;
    vci.format           = fmt;
    vci.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    check(vkCreateImageView(dev, &vci, nullptr, &out->view), "vkCreateImageView");
}

// Debe coincidir exactamente con el layout(push_constant) de fragment.frag
// (offsets std430: res 0-8, seed 8-16, layer 16, numTextures 20, fmaIters 24; total 28 B).
struct PCFrag {
    uint32_t resX, resY, seed0, seed1, layer, numTextures, fmaIters;
};

int main(int argc, char** argv) {
    Config C;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto next = [&](const char* name) -> const char* {
            if (i + 1 >= argc) { std::fprintf(stderr, "falta valor para %s\n", name); std::exit(1); }
            return argv[++i];
        };
        if      (a == "--duration")   C.durationSec = (uint32_t)std::strtoul(next("--duration"), nullptr, 10);
        else if (a == "--warmup")     C.warmupSec   = (uint32_t)std::strtoul(next("--warmup"), nullptr, 10);
        else if (a == "--width")      C.width       = (uint32_t)std::strtoul(next("--width"), nullptr, 10);
        else if (a == "--height")     C.height      = (uint32_t)std::strtoul(next("--height"), nullptr, 10);
        else if (a == "--layers")     C.layers      = (uint32_t)std::strtoul(next("--layers"), nullptr, 10);
        else if (a == "--textures")   C.numTex      = (uint32_t)std::strtoul(next("--textures"), nullptr, 10);
        else if (a == "--tex-size")   C.texSize     = (uint32_t)std::strtoul(next("--tex-size"), nullptr, 10);
        else if (a == "--fma-iters")  C.fmaIters    = (uint32_t)std::strtoul(next("--fma-iters"), nullptr, 10);
        else if (a == "--msaa")       C.msaa        = (uint32_t)std::strtoul(next("--msaa"), nullptr, 10);
        else if (a == "--seed")       C.seed0       = (uint32_t)std::strtoul(next("--seed"), nullptr, 0);
        else if (a == "--seed-extra") C.seed1       = (uint32_t)std::strtoul(next("--seed-extra"), nullptr, 0);
        else if (a == "--shader-dir") C.shaderDir   = next("--shader-dir");
        else if (a == "--frag")       C.fragFile    = next("--frag");
        else if (a == "--any-gpu")    C.requireRx550 = false;
        else if (a == "--skip-gen")   C.skipGen  = true;
        else if (a == "--skip-frag")  C.skipFrag = true;
        else {
            std::fprintf(stderr,
                "uso:\n  %s [--duration N] [--warmup N] [--width N] [--height N]\n"
                "      [--layers N] [--textures N] [--tex-size N] [--fma-iters N] [--msaa 1|2|4|8]\n"
                "      [--seed HEX] [--seed-extra HEX] [--shader-dir PATH] [--frag FILE]\n"
                "      [--any-gpu] [--skip-gen] [--skip-frag]   (solo depuración de faults)\n",
                argv[0]);
            return 1;
        }
    }
    if (C.numTex != 4) C.numTex = 4; // shader fijo samplea tex[0..3]
    if (C.layers < 1) C.layers = 1;
    if (C.texSize > 8192) C.texSize = 8192;
    if (C.texSize % 8) C.texSize = (C.texSize / 8 + 1) * 8; // alineación múltiplo de 8 (copy/format)

    using clock = std::chrono::steady_clock;

    VkApplicationInfo app{};
    app.sType              = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName   = "workload-grafico";
    app.apiVersion         = VK_API_VERSION_1_1;
    VkInstanceCreateInfo ici{};
    ici.sType              = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    ici.pApplicationInfo   = &app;
    VkInstance inst;
    check(vkCreateInstance(&ici, nullptr, &inst), "vkCreateInstance");

    VkPhysicalDeviceProperties p;
    VkPhysicalDevice pd = pickPhysicalDevice(inst, VENDOR_RX550, DEVICE_RX550, &p);
    if (!pd) fatal("RX 550 0x1002:0x699F no encontrada (use --any-gpu solo para desarrollo)");
    if (C.requireRx550 && !(p.vendorID == VENDOR_RX550 && p.deviceID == DEVICE_RX550))
        fatal("se requiere RX 550 0x1002:0x699F");

    // Fase 0 (verificación en runtime): capacidades del formato RGBA8_UNORM.
    VkFormat fmt = VK_FORMAT_R8G8B8A8_UNORM;
    VkFormatProperties fp;
    vkGetPhysicalDeviceFormatProperties(pd, fmt, &fp);
    std::printf("format_features linear=0x%X optimal=0x%X buffer=0x%X\n",
                fp.linearTilingFeatures, fp.optimalTilingFeatures, fp.bufferFeatures);
    if (!(fp.optimalTilingFeatures & VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT))
        fatal("formato sin COLOR_ATTACHMENT (creación de recursos imposible)");
    if (!(fp.optimalTilingFeatures & VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT))
        fatal("formato sin SAMPLED_IMAGE (creación de recursos imposible)");
    if (!(fp.optimalTilingFeatures & VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT))
        fatal("formato sin STORAGE_IMAGE (creación de recursos imposible)");
    VkImageFormatProperties ifp;
    if (vkGetPhysicalDeviceImageFormatProperties(pd, fmt, VK_IMAGE_TYPE_2D,
                                                 VK_IMAGE_TILING_OPTIMAL,
                                                 VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT, 0, &ifp) != VK_SUCCESS)
        fatal("vkGetPhysicalDeviceImageFormatProperties falló (CB)");
    std::printf("sample_counts_cb=%u max_image_dim=%u max_mip=%u max_layers=%u\n",
                ifp.sampleCounts, ifp.maxExtent.width, ifp.maxMipLevels, ifp.maxArrayLayers);

    // MSAA: validar contra las capacidades del CB (bits 1/2/4/8...).
    VkSampleCountFlagBits msaaFlag = VK_SAMPLE_COUNT_1_BIT;
    switch (C.msaa) {
        case 2:  msaaFlag = VK_SAMPLE_COUNT_2_BIT;  break;
        case 4:  msaaFlag = VK_SAMPLE_COUNT_4_BIT;  break;
        case 8:  msaaFlag = VK_SAMPLE_COUNT_8_BIT;  break;
        case 1:  msaaFlag = VK_SAMPLE_COUNT_1_BIT;  break;
        default: fatal("--msaa debe ser 1, 2, 4 u 8");
    }
    if ((ifp.sampleCounts & (VkSampleCountFlags)msaaFlag) == 0)
        fatal("sample count de CB no soportado por el dispositivo");

    uint32_t qf = findQueueFamily(pd, VK_QUEUE_GRAPHICS_BIT);
    if (qf == UINT32_MAX) fatal("sin queue family graphics");

    float priority = 1.0f;
    VkDeviceQueueCreateInfo qci{};
    qci.sType            = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    qci.queueFamilyIndex = qf;
    qci.queueCount       = 1;
    qci.pQueuePriorities = &priority;
    VkDeviceCreateInfo dci{};
    dci.sType                = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    dci.queueCreateInfoCount = 1;
    dci.pQueueCreateInfos    = &qci;
    VkDevice dev;
    check(vkCreateDevice(pd, &dci, nullptr, &dev), "vkCreateDevice");
    VkQueue queue;
    vkGetDeviceQueue(dev, qf, 0, &queue);

    // Presupuesto VRAM: heap device-local visible antes de crear.
    VkPhysicalDeviceMemoryProperties memprops;
    vkGetPhysicalDeviceMemoryProperties(pd, &memprops);
    VkDeviceSize heapSize = 0;
    for (uint32_t i = 0; i < memprops.memoryHeapCount; ++i)
        if (memprops.memoryHeaps[i].flags & VK_MEMORY_HEAP_DEVICE_LOCAL_BIT)
            heapSize = std::max(heapSize, memprops.memoryHeaps[i].size);

    VkDeviceSize totalVram = 0;
    std::vector<Image> tex(C.numTex);
    for (uint32_t i = 0; i < C.numTex; ++i)
        createImage(dev, pd, C.texSize, C.texSize, fmt,
                    VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT, &totalVram, &tex[i]);
    Image cb;
    createImage(dev, pd, C.width, C.height, fmt, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
                &totalVram, &cb, msaaFlag);

    if (totalVram > heapSize) { // asignación imposible -> aborto limpio
        std::fprintf(stderr, "ERROR: presupuesto VRAM %llu > heap %llu\n",
                     (unsigned long long)totalVram, (unsigned long long)heapSize);
        std::exit(5);
    }
    std::printf("vram_known: heap=%llu imagenes=%llu MiB\n",
                (unsigned long long)heapSize, (unsigned long long)(totalVram >> 20));

    VkCommandPoolCreateInfo cpi{};
    cpi.sType            = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    cpi.flags            = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    cpi.queueFamilyIndex = qf;
    VkCommandPool cpool;
    check(vkCreateCommandPool(dev, &cpi, nullptr, &cpool), "vkCreateCommandPool");

    auto allocCB = [&](VkCommandBuffer* cb) {
        VkCommandBufferAllocateInfo a{};
        a.sType              = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        a.commandPool        = cpool;
        a.level              = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        a.commandBufferCount = 1;
        check(vkAllocateCommandBuffers(dev, &a, cb), "vkAllocateCommandBuffers");
    };
    auto submitSync = [&](VkCommandBuffer cbk) {
        VkFenceCreateInfo fci{};
        fci.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        VkFence fence;
        check(vkCreateFence(dev, &fci, nullptr, &fence), "vkCreateFence(setup)");
        VkSubmitInfo si{};
        si.sType              = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        si.commandBufferCount = 1;
        si.pCommandBuffers    = &cbk;
        check(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit(setup)");
        VkResult wr = vkWaitForFences(dev, 1, &fence, VK_TRUE, FENCE_TIMEOUT_NS);
        if (wr == VK_TIMEOUT) { std::fprintf(stderr, "ERROR: hang de GPU en setup (fence timeout)\n"); std::exit(3); }
        check(wr, "vkWaitForFences(setup)");
        vkDestroyFence(dev, fence, nullptr);
    };
// Generación determinista de texturas: contenido calculado en HOST (misma familia de hash
    // que el fragment shader) y subido con vkCmdCopyBufferToImage. Sin storage IMAGE en GFX8
    // (los imageStore de gen.comp causaban VM faults deterministas; ver R-11).
    uint64_t texPx    = (uint64_t)C.texSize * C.texSize;
    uint64_t bufBytes = (uint64_t)C.numTex * texPx * 4u;
    VkBufferCreateInfo bc{};
    bc.sType       = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    bc.size        = bufBytes;
    bc.usage       = VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
    bc.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VkBuffer hostBuf;
    check(vkCreateBuffer(dev, &bc, nullptr, &hostBuf), "vkCreateBuffer(host)");
    VkMemoryRequirements hr;
    vkGetBufferMemoryRequirements(dev, hostBuf, &hr);
    int32_t hmIdx = -1;
    for (uint32_t i = 0; i < memprops.memoryTypeCount; ++i)
        if ((hr.memoryTypeBits & (1u << i)) &&
            (memprops.memoryTypes[i].propertyFlags &
             (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) ==
            (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) {
            hmIdx = (int32_t)i;
            break;
        }
    if (hmIdx < 0) fatal("sin tipo HOST_VISIBLE|HOST_COHERENT para texturas");
    VkMemoryAllocateInfo hmai{};
    hmai.sType           = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    hmai.allocationSize  = hr.size;
    hmai.memoryTypeIndex = (uint32_t)hmIdx;
    VkDeviceMemory hostMem;
    check(vkAllocateMemory(dev, &hmai, nullptr, &hostMem), "vkAllocateMemory(host)");
    check(vkBindBufferMemory(dev, hostBuf, hostMem, 0), "vkBindBufferMemory(host)");

    auto hash32 = [](uint32_t x, uint32_t y, uint32_t salt) -> uint32_t {
        uint32_t h = x * 0x9E3779B1u ^ y * 0x85EBCA77u ^ salt;
        h ^= h >> 16; h *= 0x7FEB352Du; h ^= h >> 15;
        h *= 0x846CA68Bu; h ^= h >> 16;
        return h;
    };
    if (!C.skipGen) {
        uint8_t* map = nullptr;
        check(vkMapMemory(dev, hostMem, 0, VK_WHOLE_SIZE, 0, (void**)&map), "vkMapMemory(host)");
        for (uint32_t t = 0; t < C.numTex; ++t) {
            uint32_t salt = C.seed1 ^ (C.seed0 + 0x9E3779B9u * (t + 1));
            for (uint32_t y = 0; y < C.texSize; ++y)
                for (uint32_t x = 0; x < C.texSize; ++x) {
                    uint32_t h   = hash32(x, y, salt);
                    uint64_t off = ((uint64_t)t * texPx + (uint64_t)y * C.texSize + x) * 4u;
                    map[off + 0] = h & 255u;
                    map[off + 1] = (h >> 8) & 255u;
                    map[off + 2] = (h >> 16) & 255u;
                    map[off + 3] = (h >> 24) & 255u;
                }
        }
        vkUnmapMemory(dev, hostMem);
    }

    // Upload único: UNDEFINED -> TRANSFER_DST -> copy -> SHADER_READ_ONLY (para fragment).
    VkCommandBuffer upCb;
    allocCB(&upCb);
    {
        VkCommandBufferBeginInfo bi{};
        bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(upCb, &bi), "vkBeginCommandBuffer(upload)");
        std::vector<VkImageMemoryBarrier> pre(C.numTex);
        std::vector<VkBufferImageCopy>    cps(C.numTex);
        for (uint32_t i = 0; i < C.numTex; ++i) {
            pre[i].sType               = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            pre[i].oldLayout           = VK_IMAGE_LAYOUT_UNDEFINED;
            pre[i].newLayout           = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            pre[i].srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            pre[i].dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            pre[i].image               = tex[i].image;
            pre[i].subresourceRange    = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
            cps[i].imageSubresource    = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
            cps[i].imageExtent         = {C.texSize, C.texSize, 1};
            cps[i].bufferOffset        = (VkDeviceSize)i * texPx * 4u;
        }
        vkCmdPipelineBarrier(upCb, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT,
                             0, 0, nullptr, 0, nullptr, (uint32_t)pre.size(), pre.data());
        if (!C.skipGen)
            vkCmdCopyBufferToImage(upCb, hostBuf, tex[0].image,
                                   VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                                   (uint32_t)cps.size(), cps.data());
        std::vector<VkImageMemoryBarrier> post(C.numTex);
        for (uint32_t i = 0; i < C.numTex; ++i) {
            post[i].sType               = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            post[i].oldLayout           = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            post[i].newLayout           = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            post[i].srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            post[i].dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            post[i].image               = tex[i].image;
            post[i].subresourceRange    = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        }
        vkCmdPipelineBarrier(upCb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
                             0, 0, nullptr, 0, nullptr, (uint32_t)post.size(), post.data());
        check(vkEndCommandBuffer(upCb), "vkEndCommandBuffer(upload)");
    }
    submitSync(upCb);

    // Sampler bilineal, clamp a borde (sin cadena de mipmaps).
    VkSamplerCreateInfo sc{};
    sc.sType            = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    sc.magFilter        = VK_FILTER_LINEAR;
    sc.minFilter        = VK_FILTER_LINEAR;
    sc.mipmapMode       = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    sc.addressModeU     = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sc.addressModeV     = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sc.addressModeW     = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sc.minLod           = 0.0f;
    sc.maxLod           = 0.0f;
    VkSampler sampler;
    check(vkCreateSampler(dev, &sc, nullptr, &sampler), "vkCreateSampler");

    // Descriptor set de fragmento: array combinado image+sampler (textura + RGBA8_UNORM).
    VkDescriptorSetLayoutBinding fragBind[1]{};
    fragBind[0].binding         = 0;
    fragBind[0].descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    fragBind[0].descriptorCount = C.numTex;
    fragBind[0].stageFlags      = VK_SHADER_STAGE_FRAGMENT_BIT;
    VkDescriptorSetLayoutCreateInfo fdlc{};
    fdlc.sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    fdlc.bindingCount = 1;
    fdlc.pBindings    = fragBind;
    VkDescriptorSetLayout fdsl;
    check(vkCreateDescriptorSetLayout(dev, &fdlc, nullptr, &fdsl), "vkCreateDescriptorSetLayout(frag)");

    VkPushConstantRange fPcr{};
    fPcr.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
    fPcr.offset     = 0;
    fPcr.size       = sizeof(PCFrag);
    VkPipelineLayoutCreateInfo fplc{};
    fplc.sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    fplc.setLayoutCount         = 1;
    fplc.pSetLayouts            = &fdsl;
    fplc.pushConstantRangeCount = 1;
    fplc.pPushConstantRanges    = &fPcr;
    VkPipelineLayout fpll;
    check(vkCreatePipelineLayout(dev, &fplc, nullptr, &fpll), "vkCreatePipelineLayout(frag)");

    VkDescriptorPoolSize fPoolSize{};
    fPoolSize.type            = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    fPoolSize.descriptorCount = C.numTex;
    VkDescriptorPoolCreateInfo fdp{};
    fdp.sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    fdp.poolSizeCount = 1;
    fdp.pPoolSizes    = &fPoolSize;
    fdp.maxSets       = 1;
    VkDescriptorPool fpool;
    check(vkCreateDescriptorPool(dev, &fdp, nullptr, &fpool), "vkCreateDescriptorPool(frag)");
    VkDescriptorSetAllocateInfo fdsa{};
    fdsa.sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    fdsa.descriptorPool     = fpool;
    fdsa.descriptorSetCount = 1;
    fdsa.pSetLayouts        = &fdsl;
    VkDescriptorSet fset;
    check(vkAllocateDescriptorSets(dev, &fdsa, &fset), "vkAllocateDescriptorSets(frag)");
    std::vector<VkDescriptorImageInfo> dii(C.numTex);
    std::vector<VkWriteDescriptorSet> fwr(C.numTex);
    for (uint32_t i = 0; i < C.numTex; ++i) {
        dii[i].sampler     = sampler;
        dii[i].imageView   = tex[i].view;
        dii[i].imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        fwr[i].sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        fwr[i].dstSet          = fset;
        fwr[i].dstBinding      = 0;
        fwr[i].dstArrayElement = i;
        fwr[i].descriptorCount = 1;
        fwr[i].descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        fwr[i].pImageInfo      = &dii[i];
    }
    vkUpdateDescriptorSets(dev, (uint32_t)fwr.size(), fwr.data(), 0, nullptr);

    // Render pass: 1 attachment de color, loadOp=CLEAR, storeOp=STORE,
    // finalLayout=COLOR_ATTACHMENT (offscreen; DCC puede permanecer ON y es derrotado por entropía).
    VkAttachmentDescription ad{};
    ad.format         = fmt;
    ad.samples        = msaaFlag;
    ad.loadOp         = VK_ATTACHMENT_LOAD_OP_CLEAR;
    ad.storeOp        = VK_ATTACHMENT_STORE_OP_STORE;
    ad.stencilLoadOp  = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    ad.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    ad.initialLayout  = VK_IMAGE_LAYOUT_UNDEFINED;
    ad.finalLayout    = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkAttachmentReference cr{};
    cr.attachment = 0;
    cr.layout     = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkSubpassDescription sp{};
    sp.pipelineBindPoint    = VK_PIPELINE_BIND_POINT_GRAPHICS;
    sp.colorAttachmentCount = 1;
    sp.pColorAttachments    = &cr;
    VkRenderPassCreateInfo rpci{};
    rpci.sType           = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    rpci.attachmentCount = 1;
    rpci.pAttachments    = &ad;
    rpci.subpassCount    = 1;
    rpci.pSubpasses      = &sp;
    VkRenderPass rpass;
    check(vkCreateRenderPass(dev, &rpci, nullptr, &rpass), "vkCreateRenderPass");

    VkImageView fbView = cb.view;
    VkFramebufferCreateInfo fbc{};
    fbc.sType           = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    fbc.renderPass      = rpass;
    fbc.attachmentCount = 1;
    fbc.pAttachments    = &fbView;
    fbc.width           = C.width;
    fbc.height          = C.height;
    fbc.layers          = 1;
    VkFramebuffer fb;
    check(vkCreateFramebuffer(dev, &fbc, nullptr, &fb), "vkCreateFramebuffer");

    std::string vertSrc = readFile(C.shaderDir + "/vertex.vert");
    std::string fragSrc = readFile(C.shaderDir + "/" + C.fragFile);
    VkShaderModule vertMod = compileShader(dev, vertSrc, "vertex.vert", shaderc_vertex_shader);
    VkShaderModule fragMod = compileShader(dev, fragSrc, C.fragFile.c_str(), shaderc_fragment_shader);

    VkPipelineShaderStageCreateInfo stages[2]{};
    stages[0].sType  = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[0].stage  = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = vertMod;
    stages[0].pName  = "main";
    stages[1].sType  = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[1].stage  = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[1].module = fragMod;
    stages[1].pName  = "main";

    VkPipelineVertexInputStateCreateInfo vis{};
    vis.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
    VkPipelineInputAssemblyStateCreateInfo ias{};
    ias.sType    = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
    ias.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    VkViewport vp{};
    vp.width  = (float)C.width;
    vp.height = (float)C.height;
    vp.maxDepth = 1.0f;
    VkRect2D scissor{};
    scissor.extent = {C.width, C.height};
    VkPipelineViewportStateCreateInfo vs{};
    vs.sType         = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
    vs.viewportCount = 1;
    vs.pViewports    = &vp;
    vs.scissorCount  = 1;
    vs.pScissors     = &scissor;
    VkPipelineRasterizationStateCreateInfo rs{};
    rs.sType       = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
    rs.polygonMode = VK_POLYGON_MODE_FILL;
    rs.cullMode    = VK_CULL_MODE_NONE;
    rs.frontFace   = VK_FRONT_FACE_COUNTER_CLOCKWISE;
    rs.lineWidth   = 1.0f;
    VkPipelineMultisampleStateCreateInfo ms{};
    ms.sType                = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
    ms.rasterizationSamples = msaaFlag;
    VkPipelineColorBlendAttachmentState cba{};
    cba.blendEnable         = VK_TRUE;
    cba.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
    cba.dstColorBlendFactor = VK_BLEND_FACTOR_ONE;
    cba.colorBlendOp        = VK_BLEND_OP_ADD;
    cba.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
    cba.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
    cba.alphaBlendOp        = VK_BLEND_OP_ADD;
    cba.colorWriteMask      = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                              VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
    VkPipelineColorBlendStateCreateInfo cbs{};
    cbs.sType           = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
    cbs.attachmentCount = 1;
    cbs.pAttachments    = &cba;
    VkGraphicsPipelineCreateInfo gpci{};
    gpci.sType               = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
    gpci.stageCount          = 2;
    gpci.pStages             = stages;
    gpci.pVertexInputState   = &vis;
    gpci.pInputAssemblyState = &ias;
    gpci.pViewportState      = &vs;
    gpci.pRasterizationState = &rs;
    gpci.pMultisampleState   = &ms;
    gpci.pColorBlendState    = &cbs;
    gpci.layout              = fpll;
    gpci.renderPass          = rpass;
    gpci.subpass             = 0;
    VkPipeline gpipe;
    check(vkCreateGraphicsPipelines(dev, VK_NULL_HANDLE, 1, &gpci, nullptr, &gpipe),
          "vkCreateGraphicsPipelines");
// Loop despegado del driver: cada frame espera fence (frame pacing estricto,
    // apretando la banda de potencia de la GPU; sin presentación).
    VkCommandBuffer frameCb;
    allocCB(&frameCb);
    auto recordFrame = [&](uint32_t layer0) {
        VkCommandBufferBeginInfo bi{};
        bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(frameCb, &bi), "vkBeginCommandBuffer(frame)");
        VkClearValue clear{};
        clear.color = {{0.0f, 0.0f, 0.0f, 0.0f}};
        VkRenderPassBeginInfo rpbi{};
        rpbi.sType           = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        rpbi.renderPass      = rpass;
        rpbi.framebuffer     = fb;
        rpbi.renderArea      = {0, 0, C.width, C.height};
        rpbi.clearValueCount = 1;
        rpbi.pClearValues    = &clear;
        vkCmdBeginRenderPass(frameCb, &rpbi, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(frameCb, VK_PIPELINE_BIND_POINT_GRAPHICS, gpipe);
        vkCmdBindDescriptorSets(frameCb, VK_PIPELINE_BIND_POINT_GRAPHICS, fpll, 0, 1, &fset, 0, nullptr);
        for (uint32_t lyr = 0; lyr < C.layers; ++lyr) {
            PCFrag pc{};
            pc.resX        = C.width;
            pc.resY        = C.height;
            pc.seed0       = C.seed0;
            pc.seed1       = C.seed1;
            pc.layer       = layer0 + lyr;
            pc.numTextures = C.numTex;
            pc.fmaIters    = C.fmaIters;
            vkCmdPushConstants(frameCb, fpll, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(PCFrag), &pc);
            vkCmdDraw(frameCb, 3, 1, 0, 0);
        }
        vkCmdEndRenderPass(frameCb);
        check(vkEndCommandBuffer(frameCb), "vkEndCommandBuffer(frame)");
    };

    uint64_t startWallNs  = 0;
    uint64_t endWallNs    = 0;
    uint32_t warmupFrames = 0;
    uint32_t frames       = 0;
    uint64_t totalNs      = 0, minNs = 0, maxNs = 0;
    std::vector<uint64_t> frameTimes;

    using wall = std::chrono::system_clock;
    auto wallNs = []() -> int64_t {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(wall::now().time_since_epoch()).count();
    };

    VkFence fence = VK_NULL_HANDLE;
    if (!C.skipFrag) {
    VkFenceCreateInfo fenceCi{};
    fenceCi.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    check(vkCreateFence(dev, &fenceCi, nullptr, &fence), "vkCreateFence(loop)");
    auto submitWait = [&] {
        VkSubmitInfo si{};
        si.sType              = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        si.commandBufferCount = 1;
        si.pCommandBuffers    = &frameCb;
        check(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit(loop)");
        VkResult wr = vkWaitForFences(dev, 1, &fence, VK_TRUE, FENCE_TIMEOUT_NS);
        if (wr == VK_TIMEOUT) {
            std::fprintf(stderr, "ERROR: hang de GPU en loop (fence timeout)\n");
            std::exit(3);
        }
        check(wr, "vkWaitForFences(loop)");
        check(vkResetFences(dev, 1, &fence), "vkResetFences");
    };

    {
        auto w0 = clock::now();
        while (true) {
            recordFrame(0);
            submitWait();
            auto t1 = clock::now();
            warmupFrames++;
            if (std::chrono::duration_cast<std::chrono::seconds>(t1 - w0).count()
                    >= (int64_t)C.warmupSec)
                break;
        }
    }

    startWallNs = (uint64_t)wallNs();
    {
        auto m0 = clock::now();
        uint64_t elapsedSec = 0;
        while (elapsedSec < C.durationSec) {
            recordFrame(0);
            auto t0 = clock::now();
            submitWait();
            auto t1 = clock::now();
            uint64_t ft = (uint64_t)std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count();
            frameTimes.push_back(ft);
            totalNs += ft;
            if (!frames || ft > maxNs) maxNs = ft;
            if (!frames || ft < minNs) minNs = ft;
            frames++;
            elapsedSec = (uint64_t)std::chrono::duration_cast<std::chrono::seconds>(
                             clock::now() - m0).count();
        }
        endWallNs = (uint64_t)wallNs();
    }
    }
    uint64_t p50 = 0;
    if (!frameTimes.empty()) {
        std::sort(frameTimes.begin(), frameTimes.end());
        p50 = frameTimes[frameTimes.size() / 2];
    }

    std::printf("result: EJECUCIÓN_VÁLIDA\n"); // solo si llegamos aquí sin abortar
    std::printf("device: %s\n", p.deviceName);
    std::printf("vendor_device: 0x%04X:0x%04X\n", p.vendorID, p.deviceID);
    std::printf("resolution: %ux%u format=R8G8B8A8_UNORM msaa=%ux\n", C.width, C.height, C.msaa);
    std::printf("layers: %u textures: %u tex_size: %u\n", C.layers, C.numTex, C.texSize);
    std::printf("fma_per_fragment: %u\n", C.fmaIters * 6);
    std::printf("seed: 0x%08X 0x%08X\n", C.seed0, C.seed1);
    std::printf("warmup_s: %u duration_s: %u\n", C.warmupSec, C.durationSec);
    std::printf("start_wall_ns: %llu\n", (unsigned long long)startWallNs);
    std::printf("end_wall_ns: %llu\n", (unsigned long long)endWallNs);
    std::printf("frames: warmup=%u measure=%u\n", warmupFrames, frames);
    std::printf("fps: %.3f\n", frames ? (double)frames / (double)C.durationSec : 0.0);
    std::printf("frametime_ns: min=%llu avg=%llu max=%llu p50=%llu\n",
                (unsigned long long)minNs,
                frames ? (unsigned long long)(totalNs / frames) : 0ull,
                (unsigned long long)maxNs, (unsigned long long)p50);
    std::printf("vram: heap_bytes=%llu images_bytes=%llu\n",
                (unsigned long long)heapSize, (unsigned long long)totalVram);
    std::printf("sample_counts_cb: %u (soporta hasta MSAA 8x)\n", ifp.sampleCounts);

    vkDestroyFence(dev, fence, nullptr);
    vkDestroySampler(dev, sampler, nullptr);
    vkDestroyPipeline(dev, gpipe, nullptr);
    vkDestroyPipelineLayout(dev, fpll, nullptr);
    vkDestroyRenderPass(dev, rpass, nullptr);
    vkDestroyFramebuffer(dev, fb, nullptr);
    vkDestroyShaderModule(dev, vertMod, nullptr);
    vkDestroyShaderModule(dev, fragMod, nullptr);
    vkDestroyDescriptorPool(dev, fpool, nullptr);
    vkDestroyDescriptorSetLayout(dev, fdsl, nullptr);
    vkFreeCommandBuffers(dev, cpool, 1, &upCb);
    vkDestroyBuffer(dev, hostBuf, nullptr);
    vkFreeMemory(dev, hostMem, nullptr);
    if (frameCb) vkFreeCommandBuffers(dev, cpool, 1, &frameCb);
    vkDestroyCommandPool(dev, cpool, nullptr);
    for (uint32_t t = 0; t < C.numTex; ++t) {
        vkDestroyImageView(dev, tex[t].view, nullptr);
        vkDestroyImage(dev, tex[t].image, nullptr);
        vkFreeMemory(dev, tex[t].memory, nullptr);
    }
    vkDestroyImageView(dev, cb.view, nullptr);
    vkDestroyImage(dev, cb.image, nullptr);
    vkFreeMemory(dev, cb.memory, nullptr);
    vkDestroyDevice(dev, nullptr);
    vkDestroyInstance(inst, nullptr);
    return 0;
}