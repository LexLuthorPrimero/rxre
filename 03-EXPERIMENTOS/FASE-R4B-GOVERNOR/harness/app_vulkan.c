/* EXP-F4-A — Governor frametime-feedback read-only. Harness Vulkan (Diseño B). 
 *
 * Reproduce WORKLOAD-SINTETICO/DESIGN-GRAPHICS §5 Diseño B (fragment/banda/ROP-bound):
 *   - offscreen (sin swapchain/present), fullscreen triangle bufferless
 *   - 4 texturas 4096² RGBA8 (~256 MiB total, > L2)
 *   - ~24 fma + 4 muestras por píxel, salida de alta varianza (derrota DCC)
 *   - blending ADITIVO (RMW del CB por capa), overdraw N capas (push constant layer)
 *   - render-scale = viewport/scissor proporcional a s ∈ {1.00,0.87,0.75,0.62,0.50}
 *
 * READ-ONLY ABSOLUTO: solo lee archivos (control_scale.txt) y escribe sus propios
 * logs en results/. No escribe sysfs, no programa contadores, no instala capas.
 * Segur: frametime por fence (clock_gettime MONOTONIC, µs) por frame.
 *
 * Modos:
 *   --mode fixed   escala fija (--scale) [Phase 1 / FIXED]
 *   --mode gov      lee control_scale.txt para la escala objetivo [GOVERNOR]
 *   --mode dist     gov + step de carga N: 4->8 a t=+60 s, 8->4 a t=+120 s [DIST]
 *
 * Uso:
 *   app_vulkan --mode fixed|gov|dist --scale 1.00 --duration 20 --warm 5 \
 *              --out PREFIX --control PATH --vendor 0x1002 --device 0x699F --seed U
 * Escala leída de control_scale.txt (modo gov/dist): archivo de texto con un
 * flotante por línea; el harness lo relee al inicio de cada ventana de 20 s.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <inttypes.h>

#include <vulkan/vulkan.h>

#define TEX 4
#define TEX_DIM 4096
#define TEX_BYTES ((size_t)TEX_DIM * TEX_DIM * 4) /* 64 MiB c/u */

/* push constant layout igual al frag shader */
typedef struct {
  float scale_w;
  float scale_h;
  uint32_t layer;
  uint32_t seed;
} PushPayload;

static const char *SCALES_STR = "1.00,0.87,0.75,0.62,0.50";
static const float SCALES[5] = {1.00f, 0.87f, 0.75f, 0.62f, 0.50f};

/* ---------------- config ---------------- */
static int         g_mode = 0;          /* 0=fixed 1=gov 2=dist */
static float       g_scale = 1.00f;
static int         g_W = 1920, g_H = 1080;
static double      g_duration = 20.0;   /* segundos medidos */
static double      g_warm = 5.0;        /* segundos de warm-up (sin registrar) */
static uint32_t    g_vendor = 0x1002;
static uint32_t    g_device = 0x699F;
static uint64_t    g_seed = 0x5EED0000u;
static char        g_out[512] = "./results/run";
static char        g_control[512] = "./results/control_scale.txt";

/* ---------------- vulkan state ---------------- */
static VkInstance g_inst;
static VkPhysicalDevice g_pdevh;
static VkPhysicalDeviceProperties g_pprops;
static VkDevice g_dev;
static VkQueue g_queue;
static uint32_t g_qfam;
static VkRenderPass g_rp;
static VkFormat g_fmt = VK_FORMAT_R8G8B8A8_UNORM;
static VkImage g_img;
static VkDeviceMemory g_imgmem;
static VkImageView g_imgview;
static VkFramebuffer g_fb;
static VkDescriptorSetLayout g_dsl;
static VkDescriptorPool g_dspool;
static VkDescriptorSet g_ds;
static VkSampler g_sampler;
static VkImage g_tex[TEX];
static VkDeviceMemory g_texmem[TEX];
static VkImageView g_texview[TEX];
static VkPipelineLayout g_pl;
static VkPipeline g_pipe;
static VkCommandPool g_cpool;
static VkCommandBuffer g_cb;

static void fatal(const char *msg) {
  fprintf(stderr, "FATAL: %s\n", msg);
  exit(2);
}

static uint64_t now_us(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint64_t)ts.tv_sec * 1000000ull + (uint64_t)ts.tv_nsec / 1000ull;
}

/* ---------------- utilidades vk ---------------- */
static uint32_t find_memtype(uint32_t want) {
  VkPhysicalDeviceMemoryProperties mp;
  vkGetPhysicalDeviceMemoryProperties(g_pdevh, &mp);
  for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
    if ((mp.memoryTypes[i].propertyFlags & want) == want) return i;
  fatal("no suitable memory type");
  return 0;
}

static void init_vulkan(void) {
  VkApplicationInfo ai = {0};
  ai.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
  ai.pApplicationName = "EXP-F4-A-governor-harness";
  ai.applicationVersion = 1;
  ai.apiVersion = VK_API_VERSION_1_0;

  VkInstanceCreateInfo ii = {0};
  ii.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
  ii.pApplicationInfo = &ai;
  if (vkCreateInstance(&ii, NULL, &g_inst) != VK_SUCCESS) fatal("vkCreateInstance");

  uint32_t n = 0;
  if (vkEnumeratePhysicalDevices(g_inst, &n, NULL) != VK_SUCCESS || n == 0)
    fatal("no physical devices");
  VkPhysicalDevice *devs = calloc(n, sizeof(VkPhysicalDevice));
  vkEnumeratePhysicalDevices(g_inst, &n, devs);

  int chosen = -1;
  for (uint32_t i = 0; i < n; i++) {
    VkPhysicalDeviceProperties p;
    vkGetPhysicalDeviceProperties(devs[i], &p);
    if (g_vendor && p.vendorID != g_vendor) continue;
    if (g_device && p.deviceID != g_device) continue;
    chosen = (int)i;
    g_pprops = p;
    break;
  }
  if (chosen < 0) {
    fprintf(stderr, "no device matched vendor=0x%x device=0x%x\n", g_vendor, g_device);
    for (uint32_t i = 0; i < n; i++) {
      VkPhysicalDeviceProperties p;
      vkGetPhysicalDeviceProperties(devs[i], &p);
      fprintf(stderr, "  [%u] vendor 0x%x device 0x%x: %s\n", i, p.vendorID,
              p.deviceID, p.deviceName);
    }
    exit(2);
  }
  g_pdevh = devs[chosen];
  free(devs);

  uint32_t qcount = 0;
  vkGetPhysicalDeviceQueueFamilyProperties(g_pdevh, &qcount, NULL);
  VkQueueFamilyProperties *qps = calloc(qcount, sizeof(VkQueueFamilyProperties));
  vkGetPhysicalDeviceQueueFamilyProperties(g_pdevh, &qcount, qps);
  g_qfam = UINT32_MAX;
  for (uint32_t i = 0; i < qcount; i++)
    if (qps[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) { g_qfam = i; break; }
  free(qps);
  if (g_qfam == UINT32_MAX) fatal("no graphics queue family");

  float prio = 1.0f;
  VkDeviceQueueCreateInfo dq = {0};
  dq.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
  dq.queueFamilyIndex = g_qfam;
  dq.queueCount = 1;
  dq.pQueuePriorities = &prio;

  VkDeviceCreateInfo dd = {0};
  dd.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
  dd.queueCreateInfoCount = 1;
  dd.pQueueCreateInfos = &dq;
  dd.enabledExtensionCount = 0;
  if (vkCreateDevice(g_pdevh, &dd, NULL, &g_dev) != VK_SUCCESS)
    fatal("vkCreateDevice failed");
  vkGetDeviceQueue(g_dev, g_qfam, 0, &g_queue);
}

static void make_target(void) {
  VkImageCreateInfo ic = {0};
  ic.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
  ic.imageType = VK_IMAGE_TYPE_2D;
  ic.format = g_fmt;
  ic.extent.width = (uint32_t)g_W;
  ic.extent.height = (uint32_t)g_H;
  ic.extent.depth = 1;
  ic.mipLevels = 1;
  ic.arrayLayers = 1;
  ic.samples = VK_SAMPLE_COUNT_1_BIT;
  ic.tiling = VK_IMAGE_TILING_OPTIMAL;
  ic.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
  ic.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
  if (vkCreateImage(g_dev, &ic, NULL, &g_img) != VK_SUCCESS) fatal("create image");
  VkMemoryRequirements mr;
  vkGetImageMemoryRequirements(g_dev, g_img, &mr);
  VkMemoryAllocateInfo ma = {0};
  ma.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
  ma.allocationSize = mr.size;
  ma.memoryTypeIndex = find_memtype(VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
  if (vkAllocateMemory(g_dev, &ma, NULL, &g_imgmem) != VK_SUCCESS) fatal("alloc img mem");
  vkBindImageMemory(g_dev, g_img, g_imgmem, 0);

  VkImageViewCreateInfo iv = {0};
  iv.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
  iv.image = g_img;
  iv.viewType = VK_IMAGE_VIEW_TYPE_2D;
  iv.format = g_fmt;
  iv.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
  iv.subresourceRange.levelCount = 1;
  iv.subresourceRange.layerCount = 1;
  vkCreateImageView(g_dev, &iv, NULL, &g_imgview);

  VkAttachmentDescription ad = {0};
  ad.format = g_fmt;
  ad.samples = VK_SAMPLE_COUNT_1_BIT;
  ad.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
  ad.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
  ad.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
  ad.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
  ad.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
  ad.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
  VkAttachmentReference ar = {0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
  VkSubpassDescription sp = {0};
  sp.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
  sp.colorAttachmentCount = 1;
  sp.pColorAttachments = &ar;
  VkRenderPassCreateInfo rp = {0};
  rp.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
  rp.attachmentCount = 1;
  rp.pAttachments = &ad;
  rp.subpassCount = 1;
  rp.pSubpasses = &sp;
  vkCreateRenderPass(g_dev, &rp, NULL, &g_rp);

  VkFramebufferCreateInfo fbc = {0};
  fbc.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
  fbc.renderPass = g_rp;
  fbc.attachmentCount = 1;
  fbc.pAttachments = &g_imgview;
  fbc.width = (uint32_t)g_W;
  fbc.height = (uint32_t)g_H;
  fbc.layers = 1;
  vkCreateFramebuffer(g_dev, &fbc, NULL, &g_fb);
}

/* textura determinista 4096² RGBA8: patrón por posición (seed fija), no uniforme */
static void make_textures(void) {
  VkBufferCreateInfo bc = {0};
  bc.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
  bc.size = TEX_BYTES;
  bc.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
  VkBuffer stage;
  if (vkCreateBuffer(g_dev, &bc, NULL, &stage) != VK_SUCCESS) fatal("create stage buf");
  VkMemoryRequirements mr;
  vkGetBufferMemoryRequirements(g_dev, stage, &mr);
  VkMemoryAllocateInfo ma = {0};
  ma.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
  ma.allocationSize = mr.size;
  ma.memoryTypeIndex = find_memtype(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                                    VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
  VkDeviceMemory stagemem;
  if (vkAllocateMemory(g_dev, &ma, NULL, &stagemem) != VK_SUCCESS) fatal("alloc stage mem");
  vkBindBufferMemory(g_dev, stage, stagemem, 0);

  uint8_t *ptr;
  vkMapMemory(g_dev, stagemem, 0, ma.allocationSize, 0, (void **)&ptr);

  VkImageCreateInfo ic = {0};
  ic.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
  ic.imageType = VK_IMAGE_TYPE_2D;
  ic.format = g_fmt;
  ic.extent.width = TEX_DIM;
  ic.extent.height = TEX_DIM;
  ic.extent.depth = 1;
  ic.mipLevels = 1;
  ic.arrayLayers = 1;
  ic.samples = VK_SAMPLE_COUNT_1_BIT;
  ic.tiling = VK_IMAGE_TILING_OPTIMAL;
  ic.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
  ic.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;

  VkCommandBufferAllocateInfo ca = {0};
  ca.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
  ca.commandPool = g_cpool;
  ca.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
  ca.commandBufferCount = 1;
  VkCommandBuffer cb;
  vkAllocateCommandBuffers(g_dev, &ca, &cb);
  VkCommandBufferBeginInfo bi = {0};
  bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
  vkBeginCommandBuffer(cb, &bi);

  for (int t = 0; t < TEX; t++) {
    /* patrón determinista no uniforme: hash por posición */
    for (int y = 0; y < TEX_DIM; y++) {
      for (int x = 0; x < TEX_DIM; x++) {
        size_t idx = ((size_t)y * TEX_DIM + x) * 4;
        uint32_t h;
        /* mezcla 32 bits determinista de x,y,tex,seed */
        uint32_t v = (uint32_t)x * 0x1f123bb5u ^ (uint32_t)y * 0x7feb352du ^
                     (uint32_t)t * 0x846ca68bu ^ (uint32_t)(g_seed & 0xFFFFFFFFu);
        v = (v ^ (v >> 13)) * 0x5bd1e995u;
        v ^= v >> 15;
        h = v;
        ptr[idx + 0] = (uint8_t)(h & 0xFF);
        ptr[idx + 1] = (uint8_t)((h >> 8) & 0xFF);
        ptr[idx + 2] = (uint8_t)((h >> 16) & 0xFF);
        ptr[idx + 3] = 255u;
      }
    }

    if (vkCreateImage(g_dev, &ic, NULL, &g_tex[t]) != VK_SUCCESS) fatal("create tex");
    VkMemoryRequirements tmr;
    vkGetImageMemoryRequirements(g_dev, g_tex[t], &tmr);
    VkMemoryAllocateInfo tma = {0};
    tma.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    tma.allocationSize = tmr.size;
    tma.memoryTypeIndex = find_memtype(VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (vkAllocateMemory(g_dev, &tma, NULL, &g_texmem[t]) != VK_SUCCESS) fatal("alloc tex mem");
    vkBindImageMemory(g_dev, g_tex[t], g_texmem[t], 0);

    VkImageMemoryBarrier ib = {0};
    ib.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    ib.image = g_tex[t];
    ib.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    ib.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    ib.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    ib.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    ib.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    ib.subresourceRange.levelCount = 1;
    ib.subresourceRange.layerCount = 1;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                         VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0, NULL, 0, NULL,
                         1, &ib);

    VkBufferImageCopy bci = {0};
    bci.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    bci.imageSubresource.layerCount = 1;
    bci.imageExtent.width = TEX_DIM;
    bci.imageExtent.height = TEX_DIM;
    bci.imageExtent.depth = 1;
    vkCmdCopyBufferToImage(cb, stage, g_tex[t], VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                           1, &bci);

    VkImageMemoryBarrier ob = {0};
    ob.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    ob.image = g_tex[t];
    ob.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    ob.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    ob.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    ob.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    ob.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    ob.subresourceRange.levelCount = 1;
    ob.subresourceRange.layerCount = 1;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                         VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0, NULL, 0, NULL,
                         1, &ob);

    VkImageViewCreateInfo iv = {0};
    iv.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    iv.image = g_tex[t];
    iv.viewType = VK_IMAGE_VIEW_TYPE_2D;
    iv.format = g_fmt;
    iv.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    iv.subresourceRange.levelCount = 1;
    iv.subresourceRange.layerCount = 1;
    vkCreateImageView(g_dev, &iv, NULL, &g_texview[t]);
  }
  vkEndCommandBuffer(cb);
  VkSubmitInfo si = {0};
  si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
  si.commandBufferCount = 1;
  si.pCommandBuffers = &cb;
  vkQueueSubmit(g_queue, 1, &si, VK_NULL_HANDLE);
  vkQueueWaitIdle(g_queue);

  vkUnmapMemory(g_dev, stagemem);
  vkDestroyBuffer(g_dev, stage, NULL);
  vkFreeMemory(g_dev, stagemem, NULL);
  vkFreeCommandBuffers(g_dev, g_cpool, 1, &cb);
}

static void make_descriptors(void) {
  VkSamplerCreateInfo sc = {0};
  sc.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
  sc.magFilter = VK_FILTER_LINEAR;
  sc.minFilter = VK_FILTER_LINEAR;
  sc.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
  sc.addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT;
  sc.addressModeV = VK_SAMPLER_ADDRESS_MODE_REPEAT;
  sc.addressModeW = VK_SAMPLER_ADDRESS_MODE_REPEAT;
  vkCreateSampler(g_dev, &sc, NULL, &g_sampler);

  VkDescriptorSetLayoutBinding lb = {0};
  lb.binding = 0;
  lb.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
  lb.descriptorCount = TEX; /* u_tex[4] en binding 0 */
  lb.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
  VkDescriptorSetLayoutCreateInfo dl = {0};
  dl.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
  dl.bindingCount = 1;
  dl.pBindings = &lb;
  vkCreateDescriptorSetLayout(g_dev, &dl, NULL, &g_dsl);

  VkDescriptorPoolSize psz = {VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, TEX};
  VkDescriptorPoolCreateInfo dc = {0};
  dc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
  dc.maxSets = 1;
  dc.poolSizeCount = 1;
  dc.pPoolSizes = &psz;
  vkCreateDescriptorPool(g_dev, &dc, NULL, &g_dspool);

  VkDescriptorSetAllocateInfo dsa = {0};
  dsa.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
  dsa.descriptorPool = g_dspool;
  dsa.descriptorSetCount = 1;
  dsa.pSetLayouts = &g_dsl;
  vkAllocateDescriptorSets(g_dev, &dsa, &g_ds);

  VkDescriptorImageInfo di[TEX];
  VkWriteDescriptorSet wr = {0};
  for (int i = 0; i < TEX; i++) {
    di[i].sampler = g_sampler;
    di[i].imageView = g_texview[i];
    di[i].imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
  }
  wr.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
  wr.dstSet = g_ds;
  wr.dstBinding = 0;
  wr.descriptorCount = TEX;
  wr.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
  wr.pImageInfo = di;
  vkUpdateDescriptorSets(g_dev, 1, &wr, 0, NULL);
}

static VkShaderModule load_spv(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) fatal("cannot open spv");
  fseek(f, 0, SEEK_END);
  long sz = ftell(f);
  rewind(f);
  uint32_t *buf = malloc((size_t)sz);
  if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) fatal("read spv");
  fclose(f);
  VkShaderModuleCreateInfo sm = {0};
  sm.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
  sm.codeSize = (size_t)sz;
  sm.pCode = buf;
  VkShaderModule m;
  if (vkCreateShaderModule(g_dev, &sm, NULL, &m) != VK_SUCCESS) fatal("create shader module");
  free(buf);
  return m;
}

static void make_pipeline(const char *vs, const char *fs) {
  VkShaderModule smv = load_spv(vs);
  VkShaderModule smf = load_spv(fs);

  VkPipelineShaderStageCreateInfo stages[2] = {0};
  stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
  stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
  stages[0].module = smv;
  stages[0].pName = "main";
  stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
  stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
  stages[1].module = smf;
  stages[1].pName = "main";

  VkPushConstantRange pcr = {0};
  pcr.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
  pcr.offset = 0;
  pcr.size = sizeof(PushPayload);

  VkPipelineLayoutCreateInfo plc = {0};
  plc.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
  plc.setLayoutCount = 1;
  plc.pSetLayouts = &g_dsl;
  plc.pushConstantRangeCount = 1;
  plc.pPushConstantRanges = &pcr;
  if (vkCreatePipelineLayout(g_dev, &plc, NULL, &g_pl) != VK_SUCCESS)
    fatal("create pipeline layout");

  VkPipelineVertexInputStateCreateInfo vi = {0};
  vi.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
  VkPipelineInputAssemblyStateCreateInfo ia = {0};
  ia.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
  ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
  VkPipelineViewportStateCreateInfo vpsi = {0};
  vpsi.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
  VkViewport vp = {0, 0, (float)g_W, (float)g_H, 0, 1};
  VkRect2D sc = {{0, 0}, {(uint32_t)g_W, (uint32_t)g_H}};
  vpsi.viewportCount = 1;
  vpsi.pViewports = &vp;
  vpsi.scissorCount = 1;
  vpsi.pScissors = &sc;
  VkPipelineRasterizationStateCreateInfo rs = {0};
  rs.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
  rs.polygonMode = VK_POLYGON_MODE_FILL;
  rs.cullMode = VK_CULL_MODE_NONE;
  rs.lineWidth = 1.0f;
  VkPipelineMultisampleStateCreateInfo ms = {0};
  ms.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
  ms.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;
  /* blending aditivo (RMW del CB por capa, overdraw) */
  VkPipelineColorBlendAttachmentState cba = {0};
  cba.colorWriteMask = 0xF;
  cba.blendEnable = VK_TRUE;
  cba.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
  cba.dstColorBlendFactor = VK_BLEND_FACTOR_ONE;
  cba.colorBlendOp = VK_BLEND_OP_ADD;
  cba.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
  cba.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
  cba.alphaBlendOp = VK_BLEND_OP_ADD;
  VkPipelineColorBlendStateCreateInfo cb = {0};
  cb.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
  cb.attachmentCount = 1;
  cb.pAttachments = &cba;

  VkGraphicsPipelineCreateInfo pc = {0};
  pc.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
  pc.stageCount = 2;
  pc.pStages = stages;
  pc.pVertexInputState = &vi;
  pc.pInputAssemblyState = &ia;
  pc.pViewportState = &vpsi;
  pc.pRasterizationState = &rs;
  pc.pMultisampleState = &ms;
  pc.pColorBlendState = &cb;
  pc.layout = g_pl;
  pc.renderPass = g_rp;
  pc.subpass = 0;
  if (vkCreateGraphicsPipelines(g_dev, VK_NULL_HANDLE, 1, &pc, NULL, &g_pipe) != VK_SUCCESS)
    fatal("create pipeline");

  vkDestroyShaderModule(g_dev, smv, NULL);
  vkDestroyShaderModule(g_dev, smf, NULL);
}

static void make_cmdpool(void) {
  VkCommandPoolCreateInfo cp = {0};
  cp.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
  cp.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
  cp.queueFamilyIndex = g_qfam;
  vkCreateCommandPool(g_dev, &cp, NULL, &g_cpool);
  VkCommandBufferAllocateInfo ca = {0};
  ca.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
  ca.commandPool = g_cpool;
  ca.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
  ca.commandBufferCount = 1;
  vkAllocateCommandBuffers(g_dev, &ca, &g_cb);
}

/* escala efectiva actual + capas N (disturbio) */
static double g_current_scale = 1.00;
static uint32_t g_layers = 4;
static int g_measured = 0;          /* dentro de fase medida (logueando) */
static FILE *g_log = NULL;

/* relee control_scale.txt; escala objetivo en [0.5,1.0] */
static void read_control(void) {
  FILE *f = fopen(g_control, "r");
  if (!f) return;
  double v;
  if (fscanf(f, "%lf", &v) == 1 && v >= 0.30 && v <= 1.0001) {
    g_current_scale = v;
    fprintf(stderr, "[scale] control=%0.3f (%s)\n", v, g_control);
  }
  fclose(f);
}

static void render_frame(uint64_t frame_idx, uint64_t *ft_us) {
  VkCommandBuffer cb = g_cb;
  VkCommandBufferBeginInfo bi = {0};
  bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
  vkBeginCommandBuffer(cb, &bi);

  VkClearValue cv = {0};
  cv.color.float32[0] = 0.02f;
  cv.color.float32[1] = 0.02f;
  cv.color.float32[2] = 0.02f;
  cv.color.float32[3] = 1.0f;
  VkRenderPassBeginInfo rb = {0};
  rb.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
  rb.renderPass = g_rp;
  rb.framebuffer = g_fb;
  rb.renderArea = (VkRect2D){{0, 0}, {(uint32_t)g_W, (uint32_t)g_H}};
  rb.clearValueCount = 1;
  rb.pClearValues = &cv;
  vkCmdBeginRenderPass(cb, &rb, VK_SUBPASS_CONTENTS_INLINE);

  vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, g_pipe);
  vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, g_pl, 0, 1, &g_ds, 0, NULL);

  /* viewport/scissor efectivos = render-scale */
  int vw = (int)(g_W * g_current_scale + 0.5);
  int vh = (int)(g_H * g_current_scale + 0.5);
  if (vw < 1) vw = 1;
  if (vh < 1) vh = 1;
  VkViewport vp = {0, 0, (float)vw, (float)vh, 0, 1};
  VkRect2D sc = {{0, 0}, {(uint32_t)vw, (uint32_t)vh}};
  vkCmdSetViewport(cb, 0, 1, &vp);
  vkCmdSetScissor(cb, 0, 1, &sc);

  /* N capas (overdraw N=4 base; disturbio 4->8->4) */
  for (uint32_t l = 0; l < g_layers; l++) {
    PushPayload pp;
    pp.scale_w = (float)vw;
    pp.scale_h = (float)vh;
    pp.layer = l;
    pp.seed = (uint32_t)g_seed;
    vkCmdPushConstants(cb, g_pl, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(pp), &pp);
    vkCmdDraw(cb, 3, 1, 0, 0);
  }

  vkCmdEndRenderPass(cb);
  vkEndCommandBuffer(cb);

  VkSubmitInfo si = {0};
  si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
  si.commandBufferCount = 1;
  si.pCommandBuffers = &cb;
  vkQueueSubmit(g_queue, 1, &si, VK_NULL_HANDLE);
  vkQueueWaitIdle(g_queue);

  (void)frame_idx;
  if (ft_us) *ft_us = 0; /* el llamador mide el delta */
}

int main(int argc, char **argv) {
  const char *spv_vs = NULL, *spv_fs = NULL;
  double warm_override = -1.0;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--mode") && i + 1 < argc) {
      const char *m = argv[++i];
      if (!strcmp(m, "fixed")) g_mode = 0;
      else if (!strcmp(m, "gov")) g_mode = 1;
      else if (!strcmp(m, "dist")) g_mode = 2;
      else fatal("mode debe ser fixed|gov|dist");
    } else if (!strcmp(argv[i], "--scale") && i + 1 < argc)
      g_scale = atof(argv[++i]);
    else if (!strcmp(argv[i], "--size") && i + 1 < argc)
      sscanf(argv[++i], "%dx%d", &g_W, &g_H);
    else if (!strcmp(argv[i], "--duration") && i + 1 < argc)
      g_duration = atof(argv[++i]);
    else if (!strcmp(argv[i], "--warm") && i + 1 < argc)
      warm_override = atof(argv[++i]);
    else if (!strcmp(argv[i], "--vendor") && i + 1 < argc)
      sscanf(argv[++i], "0x%x", &g_vendor);
    else if (!strcmp(argv[i], "--device") && i + 1 < argc)
      sscanf(argv[++i], "0x%x", &g_device);
    else if (!strcmp(argv[i], "--seed") && i + 1 < argc)
      g_seed = strtoull(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--out") && i + 1 < argc)
      snprintf(g_out, sizeof(g_out), "%s", argv[++i]);
    else if (!strcmp(argv[i], "--control") && i + 1 < argc)
      snprintf(g_control, sizeof(g_control), "%s", argv[++i]);
    else if (!strcmp(argv[i], "--vs") && i + 1 < argc)
      spv_vs = argv[++i];
    else if (!strcmp(argv[i], "--fs") && i + 1 < argc)
      spv_fs = argv[++i];
    else {
      fprintf(stderr, "uso: %s --mode fixed|gov|dist --out PREFIX [--scale s] "
                      "[--size WxH] [--duration s] [--warm s] [--control PATH] "
                      "[--vendor 0x..] [--device 0x..] [--seed u64] [--vs spv] [--fs spv]\n",
              argv[0]);
      return 2;
    }
  }

  if (warm_override >= 0) g_warm = warm_override;

  /* rutas SPV por defecto */
  char exedir[1024];
  ssize_t nn = readlink("/proc/self/exe", exedir, sizeof(exedir) - 1);
  if (nn <= 0) fatal("readlink");
  exedir[nn] = '\0';
  char *slash = strrchr(exedir, '/');
  if (slash) *slash = '\0';
  static char def_vs[1100], def_fs[1100];
  if (!spv_vs) snprintf(def_vs, sizeof(def_vs), "%s/_gen/triangle.vert.spv", exedir);
  if (!spv_fs) snprintf(def_fs, sizeof(def_fs), "%s/_gen/triangle.frag.spv", exedir);
  if (!spv_vs) spv_vs = def_vs;
  if (!spv_fs) spv_fs = def_fs;

  init_vulkan();
  make_target();
  make_cmdpool();
  make_textures();
  make_descriptors();
  make_pipeline(spv_vs, spv_fs);

  fprintf(stderr, "[EXP-F4-A] device=%s vendor=0x%x dev=0x%x mode=%d scale_start=%0.3f "
                  "duration=%.0f warm=%.0f size=%dx%d\n",
          g_pprops.deviceName, g_pprops.vendorID, g_pprops.deviceID, g_mode,
          g_current_scale, g_duration, g_warm, g_W, g_H);

  char *tmp = malloc(strlen(g_out) + 32);
  snprintf(tmp, strlen(g_out) + 32, "%s_frames.tsv", g_out);
  g_log = fopen(tmp, "w");
  if (!g_log) fatal("cannot open frame log");
  fprintf(g_log, "#ts_epoch_s\tts_us_mono\tframe_us\tscale\tlayers\n");

  /* establece escala inicial */
  if (g_mode == 0) g_current_scale = g_scale;
  else if (g_mode >= 1) read_control();

  /* warm-up */
  uint64_t w0 = now_us();
  fprintf(stderr, "[EXP-F4-A] warm-up %.0f s\n", g_warm);
  for (;;) {
    uint64_t t0 = now_us();
    render_frame(0, NULL);
    uint64_t t1 = now_us();
    if ((double)(t1 - w0) / 1e6 >= g_warm) break;
    (void)t0;
  }
  vkDeviceWaitIdle(g_dev);

  /* fase medida */
  uint64_t m0 = now_us();
  double m0_epoch = (double)time(NULL);
  double win = 20.0; /* ventana del governor */
  uint64_t fr = 0;
  fprintf(stderr, "[EXP-F4-A] medindo %.0f s (m0_mono_us=%" PRIu64 ")\n", g_duration, m0);

  /* file m0: alineación de ventanas del governor (ts MONOTONIC y epoch de pared del inicio medido) */
  {
    char *mp = malloc(strlen(g_out) + 16);
    snprintf(mp, strlen(g_out) + 16, "%s_m0.txt", g_out);
    FILE *mf = fopen(mp, "w");
    if (!mf) fatal("cannot open m0 file");
    fprintf(mf, "%" PRIu64 "\n%.6f\n", m0, m0_epoch);
    fclose(mf);
    free(mp);
  }

  for (;;) {
    uint64_t t0 = now_us();
    render_frame(fr, NULL);
    uint64_t t1 = now_us();
    uint64_t ft = t1 - t0;
    double elast = (double)(t1 - m0) / 1e6;
    if (g_measured == 0) g_measured = 1; /* ya estamos midiendo */
    fprintf(g_log, "%.3f\t%" PRIu64 "\t%" PRIu64 "\t%.3f\t%u\n",
            m0_epoch + (double)(t1 - m0) / 1e6, t1, ft, g_current_scale, g_layers);
    fflush(g_log); /* online: el governor lee el log mientras corre */

    /* en modo gov/dist, releer escala al inicio de cada ventana (250 ms después del cruce,
       para dar tiempo al governor de escribir tras su cómputo de p99 en el límite) */
    if (g_mode >= 1) {
      double wf = elast / win;
      static double last_window = -1.0;
      double wfloor = floor(wf);
      if (wfloor != last_window && (elast - wfloor * win) >= 1.0) {
        last_window = wfloor;
        read_control();
      }
    }
    /* disturbio: step de carga N 4->8 a +60 s, retorno 8->4 a +120 s */
    if (g_mode >= 2) {
      if (elast >= 60.0 && g_layers != 8) {
        g_layers = 8;
        fprintf(stderr, "[EXP-F4-A] DIST step: N=8 (t=+%.1f s)\n", elast);
      }
      if (elast >= 120.0 && g_layers != 4) {
        g_layers = 4;
        fprintf(stderr, "[EXP-F4-A] DIST retorno: N=4 (t=+%.1f s)\n", elast);
      }
    }
    if (elast >= g_duration) break;
    fr++;
  }

  fclose(g_log);
  free(tmp);
  fprintf(stderr, "[EXP-F4-A] done frames=%" PRIu64 " final_scale=%0.3f\n", fr + 1,
          g_current_scale);
  vkDeviceWaitIdle(g_dev);
  return 0;
}