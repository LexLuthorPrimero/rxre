#include <vulkan/vulkan.h>
#include <shaderc/shaderc.hpp>

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

static constexpr uint32_t RX550_VENDOR_ID = 0x1002;
static constexpr uint32_t RX550_DEVICE_ID = 0x699F;
static constexpr uint32_t LOCAL_SIZE      = 256;

struct Params {
    uint64_t durationSec  = 30;
    uint32_t workgroups   = 4096;
    uint32_t iterations   = 512;
    uint32_t stride       = 16;
    uint32_t seed         = 42;
    uint64_t vramBytes    = 1ull << 28;
    std::string shaderPath = "src/compute.comp";
    bool requireRx550      = true;
};

static void die(const char* what) {
    std::fprintf(stderr, "ERROR: %s\n", what);
    std::exit(1);
}

static void check(VkResult r, const char* what) {
    if (r != VK_SUCCESS)
        die(what);
}

static std::string readFile(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f.is_open()) {
        std::fprintf(stderr, "ERROR: no se pudo abrir %s\n", path.c_str());
        std::exit(1);
    }
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static VkShaderModule compileShader(VkDevice dev, const std::string& glsl) {
    shaderc::Compiler compiler;
    shaderc::CompileOptions options;
    options.SetTargetEnvironment(shaderc_target_env_vulkan, shaderc_env_version_vulkan_1_1);
    options.SetTargetSpirv(shaderc_spirv_version_1_3);
    options.SetOptimizationLevel(shaderc_optimization_level_performance);

    shaderc::SpvCompilationResult res =
        compiler.CompileGlslToSpv(glsl.data(), glsl.size(),
                                  shaderc_compute_shader, "compute.comp", options);
    if (res.GetCompilationStatus() != shaderc_compilation_status_success) {
        std::fprintf(stderr, "ERROR shader:\n%s\n", res.GetErrorMessage().c_str());
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

static uint32_t findComputeQueueFamily(VkPhysicalDevice dev) {
    uint32_t n = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(dev, &n, nullptr);
    std::vector<VkQueueFamilyProperties> qf(n);
    vkGetPhysicalDeviceQueueFamilyProperties(dev, &n, qf.data());
    for (uint32_t i = 0; i < n; ++i)
        if (qf[i].queueFlags & VK_QUEUE_COMPUTE_BIT)
            return i;
    return UINT32_MAX;
}

static uint32_t findMemoryType(VkPhysicalDevice dev, uint32_t typeBits) {
    VkPhysicalDeviceMemoryProperties mem;
    vkGetPhysicalDeviceMemoryProperties(dev, &mem);
    for (uint32_t i = 0; i < mem.memoryTypeCount; ++i)
        if (typeBits & (1u << i))
            return i;
    return UINT32_MAX;
}

static VkPhysicalDevice pickPhysicalDevice(VkInstance inst, uint32_t wantVendor,
                                          uint32_t wantDevice) {
    uint32_t n = 0;
    check(vkEnumeratePhysicalDevices(inst, &n, nullptr), "vkEnumeratePhysicalDevices count");
    std::vector<VkPhysicalDevice> pds(n);
    check(vkEnumeratePhysicalDevices(inst, &n, pds.data()), "vkEnumeratePhysicalDevices");

    VkPhysicalDevice fallback = VK_NULL_HANDLE;
    for (VkPhysicalDevice pd : pds) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(pd, &p);
        std::printf("device: %s vendor=0x%04X device=0x%04X driver=0x%08X\n",
                    p.deviceName, p.vendorID, p.deviceID, p.driverVersion);
        if (p.vendorID == wantVendor && p.deviceID == wantDevice)
            return pd;
        if (!fallback)
            fallback = pd;
    }
    if (fallback)
        std::fprintf(stderr, "warning: RX 550 no encontrada, usando %s\n", "otra");
    return fallback;
}

int main(int argc, char** argv) {
    Params P;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto next = [&](const char* name) -> const char* {
            if (i + 1 >= argc) {
                std::fprintf(stderr, "falta valor para %s\n", name);
                std::exit(1);
                return nullptr;
            }
            return argv[++i];
        };
        if (a == "--duration")     P.durationSec = std::strtoull(next("--duration"), nullptr, 10);
        else if (a == "--workgroups") P.workgroups = (uint32_t)std::strtoul(next("--workgroups"), nullptr, 10);
        else if (a == "--iterations") P.iterations = (uint32_t)std::strtoul(next("--iterations"), nullptr, 10);
        else if (a == "--stride")   P.stride = (uint32_t)std::strtoul(next("--stride"), nullptr, 10);
        else if (a == "--seed")     P.seed = (uint32_t)std::strtoul(next("--seed"), nullptr, 10);
        else if (a == "--vram")     P.vramBytes = std::strtoull(next("--vram"), nullptr, 10);
        else if (a == "--shader")   P.shaderPath = next("--shader");
        else if (a == "--any-gpu")  P.requireRx550 = false;
        else {
            std::fprintf(stderr,
                "uso:\n  %s [--duration N] [--workgroups N] [--iterations N] [--stride N]\n"
                "      [--seed N] [--vram BYTES] [--shader PATH] [--any-gpu]\n", argv[0]);
            return 1;
        }
    }

    if (P.vramBytes < (1ull << 16))
        P.vramBytes = 1ull << 16;

    VkInstance inst;
    VkApplicationInfo app{};
    app.sType              = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName   = "workload-sintetico";
    app.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
    app.apiVersion         = VK_API_VERSION_1_1;

    VkInstanceCreateInfo ici{};
    ici.sType                   = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    ici.pApplicationInfo        = &app;
    check(vkCreateInstance(&ici, nullptr, &inst), "vkCreateInstance");

    VkPhysicalDevice pd = pickPhysicalDevice(inst, RX550_VENDOR_ID, RX550_DEVICE_ID);
    if (!pd)
        die("no hay device Vulkan");
    VkPhysicalDeviceProperties p;
    vkGetPhysicalDeviceProperties(pd, &p);
    if (P.requireRx550 && !(p.vendorID == RX550_VENDOR_ID && p.deviceID == RX550_DEVICE_ID))
        die("se requiere RX 550 0x1002:0x699F presente (use --any-gpu solo para desarrollo)");

    uint32_t qf = findComputeQueueFamily(pd);
    if (qf == UINT32_MAX)
        die("sin queue family compute");

    float priority = 1.0f;
    VkDeviceQueueCreateInfo qci{};
    qci.sType            = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    qci.queueFamilyIndex = qf;
    qci.queueCount       = 1;
    qci.pQueuePriorities = &priority;

    VkDeviceCreateInfo dci{};
    dci.sType                   = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    dci.queueCreateInfoCount    = 1;
    dci.pQueueCreateInfos       = &qci;
    dci.enabledExtensionCount   = 0;
    dci.enabledLayerCount       = 0;

    VkDevice dev;
    check(vkCreateDevice(pd, &dci, nullptr, &dev), "vkCreateDevice");

    VkQueue queue;
    vkGetDeviceQueue(dev, qf, 0, &queue);

    /* buffer (presión de VRAM) */
    VkPhysicalDeviceMemoryProperties mem;
    vkGetPhysicalDeviceMemoryProperties(pd, &mem);

    VkBufferCreateInfo bci{};
    bci.sType       = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    bci.size        = P.vramBytes;
    bci.usage       = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    bci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    VkBuffer buffer;
    check(vkCreateBuffer(dev, &bci, nullptr, &buffer), "vkCreateBuffer");

    VkMemoryRequirements mreq;
    vkGetBufferMemoryRequirements(dev, buffer, &mreq);
    uint32_t memType = findMemoryType(pd, mreq.memoryTypeBits);
    if (memType == UINT32_MAX)
        die("sin tipo de memoria compatible");

    /* priorizar DEVICE_LOCAL para presión real de VRAM */
    int32_t chosen = -1;
    for (uint32_t i = 0; i < mem.memoryTypeCount; ++i) {
        if ((mreq.memoryTypeBits & (1u << i))) {
            if (mem.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT) {
                chosen = (int32_t)i;
                break;
            }
        }
    }
    if (chosen < 0)
        chosen = (int32_t)memType;

    VkMemoryAllocateInfo mai{};
    mai.sType           = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    mai.allocationSize  = mreq.size;
    mai.memoryTypeIndex = (uint32_t)chosen;

    VkDeviceMemory memory;
    check(vkAllocateMemory(dev, &mai, nullptr, &memory), "vkAllocateMemory");
    check(vkBindBufferMemory(dev, buffer, memory, 0), "vkBindBufferMemory");

    /* descriptor set */
    VkDescriptorSetLayoutBinding binding{};
    binding.binding         = 0;
    binding.descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    binding.descriptorCount = 1;
    binding.stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT;

    VkDescriptorSetLayoutCreateInfo dlci{};
    dlci.sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    dlci.bindingCount = 1;
    dlci.pBindings    = &binding;

    VkDescriptorSetLayout dsl;
    check(vkCreateDescriptorSetLayout(dev, &dlci, nullptr, &dsl), "vkCreateDescriptorSetLayout");

    VkDescriptorPoolSize poolSize{};
    poolSize.type            = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    poolSize.descriptorCount = 1;

    VkDescriptorPoolCreateInfo dpci{};
    dpci.sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    dpci.maxSets       = 1;
    dpci.poolSizeCount = 1;
    dpci.pPoolSizes    = &poolSize;

    VkDescriptorPool pool;
    check(vkCreateDescriptorPool(dev, &dpci, nullptr, &pool), "vkCreateDescriptorPool");

    VkDescriptorSetLayout layouts[] = {dsl};
    VkDescriptorSetAllocateInfo dsai{};
    dsai.sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    dsai.descriptorPool     = pool;
    dsai.descriptorSetCount = 1;
    dsai.pSetLayouts        = layouts;

    VkDescriptorSet dset;
    check(vkAllocateDescriptorSets(dev, &dsai, &dset), "vkAllocateDescriptorSets");

    VkDescriptorBufferInfo dbi{};
    dbi.buffer = buffer;
    dbi.offset = 0;
    dbi.range  = VK_WHOLE_SIZE;

    VkWriteDescriptorSet wds{};
    wds.sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    wds.dstSet          = dset;
    wds.dstBinding      = 0;
    wds.descriptorCount = 1;
    wds.descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    wds.pBufferInfo     = &dbi;
    vkUpdateDescriptorSets(dev, 1, &wds, 0, nullptr);

    /* pipeline */
    std::string glsl = readFile(P.shaderPath);
    VkShaderModule sm = compileShader(dev, glsl);

    struct PC {
        uint32_t iterations;
        uint32_t stride;
        uint32_t seed;
    };

    VkPushConstantRange pcr{};
    pcr.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    pcr.offset     = 0;
    pcr.size       = sizeof(PC);

    VkPipelineLayoutCreateInfo plci{};
    plci.sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    plci.setLayoutCount         = 1;
    plci.pSetLayouts            = layouts;
    plci.pushConstantRangeCount = 1;
    plci.pPushConstantRanges    = &pcr;

    VkPipelineLayout playout;
    check(vkCreatePipelineLayout(dev, &plci, nullptr, &playout), "vkCreatePipelineLayout");

    VkPipelineShaderStageCreateInfo ss{};
    ss.sType               = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    ss.stage               = VK_SHADER_STAGE_COMPUTE_BIT;
    ss.module              = sm;
    ss.pName               = "main";

    VkComputePipelineCreateInfo cpci{};
    cpci.sType              = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
    cpci.stage              = ss;
    cpci.layout             = playout;

    VkPipeline pipeline;
    check(vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpci, nullptr, &pipeline),
          "vkCreateComputePipelines");

    /* command buffer */
    VkCommandPoolCreateInfo cpi{};
    cpi.sType            = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    cpi.flags            = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    cpi.queueFamilyIndex = qf;

    VkCommandPool cpool;
    check(vkCreateCommandPool(dev, &cpi, nullptr, &cpool), "vkCreateCommandPool");

    VkCommandBufferAllocateInfo cbai{};
    cbai.sType              = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    cbai.commandPool        = cpool;
    cbai.level              = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cbai.commandBufferCount = 1;

    VkCommandBuffer cb;
    check(vkAllocateCommandBuffers(dev, &cbai, &cb), "vkAllocateCommandBuffers");

    VkCommandBufferBeginInfo cbbi{};
    cbbi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    cbbi.flags = VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT;

    check(vkBeginCommandBuffer(cb, &cbbi), "vkBeginCommandBuffer");
    PC pc{};
    pc.iterations = P.iterations;
    pc.stride     = P.stride;
    pc.seed       = P.seed;
    vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
    vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_COMPUTE, playout, 0, 1, &dset, 0, nullptr);
    vkCmdPushConstants(cb, playout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(PC), &pc);
    vkCmdDispatch(cb, P.workgroups, 1, 1);
    check(vkEndCommandBuffer(cb), "vkEndCommandBuffer");

    VkFenceCreateInfo fci{};
    fci.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    VkFence fence;
    check(vkCreateFence(dev, &fci, nullptr, &fence), "vkCreateFence");

    VkSubmitInfo si{};
    si.sType              = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    si.commandBufferCount = 1;
    si.pCommandBuffers    = &cb;

    /* bucle de duración */
    auto start = std::chrono::steady_clock::now();
    uint64_t dispatches = 0;
    while (true) {
        auto now = std::chrono::steady_clock::now();
        double el = std::chrono::duration<double>(now - start).count();
        if (el >= (double)P.durationSec)
            break;
        check(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit");
        check(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "vkWaitForFences");
        check(vkResetFences(dev, 1, &fence), "vkResetFences");
        ++dispatches;
    }
    vkDeviceWaitIdle(dev);

    auto end = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(end - start).count();
    double fps = (double)dispatches / (elapsed > 0 ? elapsed : 1.0);

    std::printf("device=%s\n", p.deviceName);
    std::printf("vendor=0x%04X device=0x%04X\n", p.vendorID, p.deviceID);
    std::printf("duration=%.3f s\ndispatches=%llu\nfps=%.2f\n",
                elapsed, (unsigned long long)dispatches, fps);
    std::printf("workgroups=%u iterations=%u stride=%u seed=%u vram=%llu bytes\n",
                P.workgroups, P.iterations, P.stride, P.seed,
                (unsigned long long)P.vramBytes);
    std::printf("shader_path=%s\n", P.shaderPath.c_str());

    vkDestroyFence(dev, fence, nullptr);
    vkDestroyCommandPool(dev, cpool, nullptr);
    vkDestroyPipeline(dev, pipeline, nullptr);
    vkDestroyPipelineLayout(dev, playout, nullptr);
    vkDestroyShaderModule(dev, sm, nullptr);
    vkDestroyDescriptorPool(dev, pool, nullptr);
    vkDestroyDescriptorSetLayout(dev, dsl, nullptr);
    vkFreeMemory(dev, memory, nullptr);
    vkDestroyBuffer(dev, buffer, nullptr);
    vkDestroyDevice(dev, nullptr);
    vkDestroyInstance(inst, nullptr);
    return 0;
}