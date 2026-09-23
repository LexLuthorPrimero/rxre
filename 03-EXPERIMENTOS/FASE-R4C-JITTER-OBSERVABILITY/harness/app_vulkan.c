#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <vulkan/vulkan.h>

#include "jittergen.h"
#include "perframe.h"

static const char *LAYER_NAME = "VK_LAYER_ITERATIVERO_jitter_observer";

/* ------------- config ---------------- */
static int    g_level  = 'A';             /* 'A' | 'B' | 'S'(selftest) */
static int    g_frames = JG_TOTAL;        /* frames a renderizar (incluye preludio) */
static int    g_W = 1920, g_H = 1080;     /* render target */
static uint32_t g_vendor = 0;             /* 0 = primer device; 0x1002=AMD... */
static int    g_pdev = 0;
static uint64_t g_seed = 0x5EED0000u;
static char   g_out[512] = "./results/run";

/* ------------- vulkan state ------------- */
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
static VkBuffer g_ubo;
static VkDeviceMemory g_ubomem;
static PerFrame *g_uboptr;
static VkDescriptorSetLayout g_dsl;
static VkDescriptorPool g_dspool;
static VkDescriptorSet g_ds;
static VkPipelineLayout g_pl;
static VkPipeline g_pipe;
static VkCommandPool g_cpool;
static VkCommandBuffer g_cb;

static void fatal(const char *msg) {
  fprintf(stderr, "FATAL: %s\n", msg);
  exit(2);
}

static uint32_t find_memtype(uint32_t want) {
  VkPhysicalDeviceMemoryProperties mp;
  vkGetPhysicalDeviceMemoryProperties(g_pdevh, &mp);
  for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
    if ((mp.memoryTypes[i].propertyFlags & want) == want) return i;
  fatal("no suitable memory type");
  return 0;
}

/* ---------------- construct matrices (FSR2-equivalent) ---------------- */
static void build_proj(float aspect, float fovy_rad, float znear, float zfar,
                       float M[16]) {
  float f = 1.0f / (float)tan(fovy_rad * 0.5);
  memset(M, 0, 16 * sizeof(float));
  M[0] = f / aspect;
  M[5] = f;
  M[10] = zfar / (znear - zfar);  /* Vulkan [0,1]: ajuste simple; solo para selftest */
  M[11] = -1.0f;
  M[14] = zfar * znear / (znear - zfar);
  M[15] = 0.0f;
}

/* construye M_jit = T(jx_ndc,jy_ndc) * M_base */
static void build_jit_proj(const float Mbase[16], float jx_px, float jy_px,
                           float Mjit[16]) {
  float jx_ndc = 2.0f * jx_px / (float)g_W;
  float jy_ndc = -2.0f * jy_px / (float)g_H;
  float T[16];
  perframe_mat4_translate(jx_ndc, jy_ndc, 0.0f, T);
  perframe_mat4_mul(T, Mbase, Mjit);
}

/* ---------------- selftest (valida la convencion de matrices / recuperacion) ---------------- */
static int run_selftest(void) {
  float Mbase[16], Mjit[16], jx, jy;
  const float cases[6][2] = {
      {0.5f, 0.0f}, {-0.5f, 0.0f}, {0.0f, 0.25f}, {0.0625f, -0.0625f},
      {0.01f, 0.01f}, {-0.125f, -0.25f}};
  double maxerr = 0.0;
  build_proj((float)g_W / (float)g_H, 1.1f, 0.1f, 100.0f, Mbase);
  /* t-small expuesto: asegurar M_base invertible */
  float inv[16];
  if (!perframe_mat4_invert(Mbase, inv)) fatal("selftest: base singular");
  for (int i = 0; i < 6; i++) {
    build_jit_proj(Mbase, cases[i][0], cases[i][1], Mjit);
    perframe_recover_jitter(Mbase, Mjit, (float)g_W, (float)g_H, &jx, &jy);
    double ex = fabs((double)jx - cases[i][0]);
    double ey = fabs((double)jy - cases[i][1]);
    if (ex > maxerr) maxerr = ex;
    if (ey > maxerr) maxerr = ey;
    if (ex > 1e-4 || ey > 1e-4) {
      fprintf(stderr, "SELFTEST FAIL case %d: got (%.6f,%.6f) want (%.6f,%.6f)\n",
              i, jx, jy, cases[i][0], cases[i][1]);
      return 1;
    }
  }
  printf("SELFTEST OK  maxerr=%.3e px\n", maxerr);
  return 0;
}

/* ---------------- vulkan setup ---------------- */
static void init_vulkan(void) {
  VkApplicationInfo ai = {0};
  ai.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
  ai.pApplicationName = "EXP-F1-A-jitter-harness";
  ai.applicationVersion = 1;
  ai.apiVersion = VK_API_VERSION_1_0;

  const char *layers[1] = {LAYER_NAME};
  VkInstanceCreateInfo ii = {0};
  ii.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
  ii.pApplicationInfo = &ai;
  ii.enabledLayerCount = 1;
  ii.ppEnabledLayerNames = layers;

  VkResult r = vkCreateInstance(&ii, NULL, &g_inst);
  if (r != VK_SUCCESS) {
    fprintf(stderr, "vkCreateInstance failed (%d) - capa no presente? VK_LAYER_PATH=%s\n",
            r, getenv("VK_LAYER_PATH") ? getenv("VK_LAYER_PATH") : "(unset)");
    exit(2);
  }

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
    if (g_vendor == 0 && (int)i != g_pdev) continue;
    chosen = (int)i;
    g_pprops = p;
    break;
  }
  if (chosen < 0) {
    fprintf(stderr, "no device matched vendor=0x%x pdev=%d\n", g_vendor, g_pdev);
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

/* color attachment (fuera de pantalla) */
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
  if (vkCreateImage(g_dev, &ic, NULL, &g_img) != VK_SUCCESS)
    fatal("create image");
  VkMemoryRequirements mr;
  vkGetImageMemoryRequirements(g_dev, g_img, &mr);
  VkMemoryAllocateInfo ma = {0};
  ma.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
  ma.allocationSize = mr.size;
  ma.memoryTypeIndex = find_memtype(VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
  if (vkAllocateMemory(g_dev, &ma, NULL, &g_imgmem) != VK_SUCCESS)
    fatal("alloc img mem");
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

/* UBO per-frame host-visible */
static void make_ubo(void) {
  VkBufferCreateInfo bc = {0};
  bc.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
  bc.size = sizeof(PerFrame) + 128;
  bc.usage = VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT;
  if (vkCreateBuffer(g_dev, &bc, NULL, &g_ubo) != VK_SUCCESS)
    fatal("create ubo");
  VkMemoryRequirements mr;
  vkGetBufferMemoryRequirements(g_dev, g_ubo, &mr);
  VkMemoryAllocateInfo ma = {0};
  ma.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
  ma.allocationSize = mr.size;
  ma.memoryTypeIndex =
      find_memtype(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
  if (vkAllocateMemory(g_dev, &ma, NULL, &g_ubomem) != VK_SUCCESS)
    fatal("alloc ubo mem");
  vkBindBufferMemory(g_dev, g_ubo, g_ubomem, 0);
  vkMapMemory(g_dev, g_ubomem, 0, ma.allocationSize, 0, (void **)&g_uboptr);

  VkDescriptorSetLayoutBinding lb = {0};
  lb.binding = 0;
  lb.descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
  lb.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
  VkDescriptorSetLayoutCreateInfo dl = {0};
  dl.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
  dl.bindingCount = 1;
  dl.pBindings = &lb;
  vkCreateDescriptorSetLayout(g_dev, &dl, NULL, &g_dsl);

  VkDescriptorPoolSize psz = {VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1};
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

  VkDescriptorBufferInfo dbi = {0};
  dbi.buffer = g_ubo;
  dbi.range = sizeof(PerFrame);
  VkWriteDescriptorSet wr = {0};
  wr.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
  wr.dstSet = g_ds;
  wr.dstBinding = 0;
  wr.descriptorCount = 1;
  wr.descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
  wr.pBufferInfo = &dbi;
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
  pcr.size = (uint32_t)sizeof(PushPayload);

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
  VkPipelineColorBlendAttachmentState cba = {0};
  cba.colorWriteMask = 0xF;
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

/* ---------------- frame render ---------------- */
static void render_frame(int idx, float jx_px, float jy_px) {
  /* actualiza UBO por frame (memoria host-visible mapeada) */
  if (g_level == 'B') {
    float Mbase[16];
    build_proj((float)g_W / (float)g_H, 1.1f, 0.1f, 100.0f, Mbase);
    g_uboptr->magic = PERFRAME_MAGIC;
    g_uboptr->frameMarker = (uint32_t)idx;
    g_uboptr->viewport[0] = (float)g_W;
    g_uboptr->viewport[1] = (float)g_H;
    memcpy(g_uboptr->projBase, Mbase, sizeof(Mbase));
    build_jit_proj(Mbase, jx_px, jy_px, g_uboptr->projJit);
    g_uboptr->color[0] = 0.12f;
    g_uboptr->color[1] = 0.34f;
    g_uboptr->color[2] = 0.56f;
    g_uboptr->color[3] = 1.0f;
  } else {
    /* NIVEL A: el UBO no lleva magic/matrices -> la capa no lo interpreta */
    g_uboptr->color[0] = 0.12f;
    g_uboptr->color[1] = 0.34f;
    g_uboptr->color[2] = 0.56f;
    g_uboptr->color[3] = 1.0f;
  }

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
  vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, g_pl, 0, 1, &g_ds,
                          0, NULL);

  if (g_level == 'A') {
    PushPayload pp;
    pp.frameMarker = (uint32_t)idx;
    pp.jitterX = jx_px;
    pp.jitterY = jy_px;
    pp.pad = 0.0f;
    vkCmdPushConstants(cb, g_pl, VK_SHADER_STAGE_FRAGMENT_BIT, 0,
                       (uint32_t)sizeof(PushPayload), &pp);
  }

  vkCmdDraw(cb, 3, 1, 0, 0);
  vkCmdEndRenderPass(cb);
  vkEndCommandBuffer(cb);

  VkSubmitInfo si = {0};
  si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
  si.commandBufferCount = 1;
  si.pCommandBuffers = &cb;
  vkQueueSubmit(g_queue, 1, &si, VK_NULL_HANDLE);
  vkQueueWaitIdle(g_queue); /* secuencial y simple; no es benchmark de perf */
}

int main(int argc, char **argv) {
  const char *gt_path = NULL;
  const char *spv_vs = NULL, *spv_fs = NULL;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--level") && i + 1 < argc) g_level = argv[++i][0];
    else if (!strcmp(argv[i], "--frames") && i + 1 < argc)
      g_frames = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--size") && i + 1 < argc) {
      sscanf(argv[++i], "%dx%d", &g_W, &g_H);
    } else if (!strcmp(argv[i], "--vendor") && i + 1 < argc)
      sscanf(argv[++i], "0x%x", &g_vendor);
    else if (!strcmp(argv[i], "--pdev") && i + 1 < argc)
      g_pdev = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--seed") && i + 1 < argc)
      g_seed = strtoull(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--out") && i + 1 < argc) {
      snprintf(g_out, sizeof(g_out), "%s", argv[++i]);
    } else if (!strcmp(argv[i], "--gt") && i + 1 < argc)
      gt_path = argv[++i];
    else if (!strcmp(argv[i], "--vs") && i + 1 < argc)
      spv_vs = argv[++i];
    else if (!strcmp(argv[i], "--fs") && i + 1 < argc)
      spv_fs = argv[++i];
    else if (!strcmp(argv[i], "--selftest")) g_level = 'S';
    else {
      fprintf(stderr, "uso: %s --level A|B --out PREFIX [--frames N] [--size WxH] "
                      "[--vendor 0x..] [--pdev i] [--seed u64] [--gt path] "
                      "[--vs spv] [--fs spv] [--selftest]\n", argv[0]);
      return 2;
    }
  }

  if (g_level == 'S') return run_selftest();

  if (g_level != 'A' && g_level != 'B') {
    fprintf(stderr, "nivel debe ser A o B\n");
    return 2;
  }

  /* rutas SPV por defecto: relativas al ejecutable (build/_gen) */
  if (!spv_vs || !spv_fs) {
    char exedir[1024];
    ssize_t n = readlink("/proc/self/exe", exedir, sizeof(exedir) - 1);
    if (n <= 0) fatal("readlink /proc/self/exe");
    exedir[n] = '\0';
    char *slash = strrchr(exedir, '/');
    if (slash) *slash = '\0';
    static char def_vs[1100], def_fs[1100];
    if (!spv_vs) {
      snprintf(def_vs, sizeof(def_vs), "%s/_gen/triangle.vert.spv", exedir);
      spv_vs = def_vs;
    }
    if (!spv_fs) {
      snprintf(def_fs, sizeof(def_fs), "%s/_gen/triangle.frag.spv", exedir);
      spv_fs = def_fs;
    }
  }

  JitterSeq seq = {0};
  if (jitter_generate(&seq, g_seed) != 0) fatal("jitter_generate");
  if (g_frames > seq.n) g_frames = seq.n;

  char *tmp = malloc(strlen(g_out) + 16);
  /* GT -> canal de referencia */
  if (!gt_path) {
    snprintf(tmp, strlen(g_out) + 16, "%s_gt.json", g_out);
    gt_path = tmp;
  }
  if (jitter_write_gt(&seq, g_seed, gt_path) != 0) fatal("write gt");

  /* config dump */
  snprintf(tmp, strlen(g_out) + 16, "%s_config.txt", g_out);
  FILE *cf = fopen(tmp, "w");
  if (!cf) fatal("write config");
  fprintf(cf, "app=EXP-F1-A-jitter-harness\nlevel=%c\nframes=%d\nsize=%dx%d\n"
              "seed=%llu\nlayer=%s\n",
          g_level, g_frames, g_W, g_H, (unsigned long long)g_seed, LAYER_NAME);
  if (getenv("VK_ICD_FILENAMES")) fprintf(cf, "VK_ICD_FILENAMES=%s\n", getenv("VK_ICD_FILENAMES"));
  if (getenv("VK_LAYER_PATH")) fprintf(cf, "VK_LAYER_PATH=%s\n", getenv("VK_LAYER_PATH"));
  if (getenv("ITER_LAYER_LOG")) fprintf(cf, "ITER_LAYER_LOG=%s\n", getenv("ITER_LAYER_LOG"));
  if (g_vendor) fprintf(cf, "vendor_filter=0x%x\n", g_vendor);
  else fprintf(cf, "vendor_filter=0\n");
  fclose(cf);

  init_vulkan();
  make_target();
  make_ubo();
  make_pipeline(spv_vs ? spv_vs : "_gen/triangle.vert.spv",
                spv_fs ? spv_fs : "_gen/triangle.frag.spv");
  make_cmdpool();

  fprintf(stderr, "[EXP-F1-A] device=%s vendor=0x%x dev=0x%x level=%c frames=%d\n",
          g_pprops.deviceName, g_pprops.vendorID, g_pprops.deviceID, g_level,
          g_frames);

  for (int i = 0; i < g_frames; i++)
    render_frame(i, seq.jx[i], seq.jy[i]);

  jitter_free(&seq);

  fprintf(stderr, "[EXP-F1-A] done\n");

  /* teardown minimo */
  vkDeviceWaitIdle(g_dev);
  return 0;
}