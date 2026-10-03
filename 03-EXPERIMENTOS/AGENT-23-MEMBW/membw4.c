/* membw4.c — the vec4 (16 B/thread) counterpart of membw.c.
 *
 * QUESTION
 *   membw.c saturates at ~41.2 GB/s with 4 B/thread while the mclk ceiling
 *   allows ~96 GB/s.  Is the memory system the limit, or is the access width?
 *
 * METHOD
 *   Identical to membw.c in every respect except the element type: uint4 in,
 *   uint4 out, 16 B per thread per direction.  Everything else -- heap choice,
 *   chunked dispatch, oracle, clock telemetry, traffic accounting -- is
 *   identical, so a difference in GB/s is attributable to the access width and
 *   not to a changed environment.
 *
 *   --iters is intentionally NOT used to make a bandwidth claim: the four lanes
 *   give the ALU four independent chains, so iters is a compute knob only.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <vulkan/vulkan.h>

static void die(const char *what, VkResult r) {
  fprintf(stderr, "FATAL %s -> VkResult %d\n", what, (int)r);
  exit(4);
}
static double mono_s(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
static uint32_t host_ref(uint32_t v, uint32_t iters, uint32_t seed) {
  for (uint32_t k = 0; k < iters; k++) v = (v ^ (v << 13)) * 0x5bd1e995u;
  return v ^ seed;
}
static int cmp_d(const void *a, const void *b) {
  double x = *(const double *)a, y = *(const double *)b;
  return (x > y) - (x < y);
}
static void read_dpm(const char *path, char *out, size_t n) {
  out[0] = 0;
  FILE *f = fopen(path, "r");
  if (!f) { snprintf(out, n, "N/A"); return; }
  char line[512];
  while (fgets(line, sizeof line, f)) {
    if (!strchr(line, '*')) continue;
    char *p = strchr(line, ':');
    if (p) {
      p++;
      while (*p == ' ' || *p == '\t') p++;
      size_t j = 0;
      while (p[j] && p[j] != ' ' && p[j] != '\t' && p[j] != '\n' && j + 1 < n) { out[j] = p[j]; j++; }
      out[j] = 0;
    }
    break;
  }
  fclose(f);
  if (!out[0]) snprintf(out, n, "UNKNOWN");
}

int main(int argc, char **argv) {
  const char *spv = "shaders/membw4.comp.spv";
  uint32_t vendor = 0x1002, device_id = 0x699f;
  uint64_t n = 1ull << 24;        /* uint4 elements -> 256 MiB per buffer */
  uint32_t iters = 0, dispatches = 16, samples = 5, warmup = 2, local_size = 256;
  int heap = -1;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--spv") && i + 1 < argc) spv = argv[++i];
    else if (!strcmp(argv[i], "--vendor") && i + 1 < argc) sscanf(argv[++i], "0x%x", &vendor);
    else if (!strcmp(argv[i], "--device") && i + 1 < argc) sscanf(argv[++i], "0x%x", &device_id);
    else if (!strcmp(argv[i], "--elems") && i + 1 < argc) n = strtoull(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--iters") && i + 1 < argc) iters = (uint32_t)strtoul(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--dispatches") && i + 1 < argc) dispatches = (uint32_t)strtoul(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--samples") && i + 1 < argc) samples = (uint32_t)strtoul(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--warmup") && i + 1 < argc) warmup = (uint32_t)strtoul(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--heap") && i + 1 < argc) heap = atoi(argv[++i]);
    else { fprintf(stderr, "uso: %s [--spv F] [--elems N] [--iters K] [--dispatches D]"
                            " [--samples S] [--warmup W] [--heap H] [--vendor 0x..] [--device 0x..]\n", argv[0]); return 2; }
  }

  VkApplicationInfo app = {VK_STRUCTURE_TYPE_APPLICATION_INFO};
  app.apiVersion = VK_API_VERSION_1_1;
  VkInstanceCreateInfo ici = {VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
  ici.pApplicationInfo = &app;
  VkInstance inst;
  if (vkCreateInstance(&ici, NULL, &inst) != VK_SUCCESS) die("vkCreateInstance", 0);

  uint32_t nd = 0;
  vkEnumeratePhysicalDevices(inst, &nd, NULL);
  VkPhysicalDevice *devs = calloc(nd, sizeof *devs);
  vkEnumeratePhysicalDevices(inst, &nd, devs);
  VkPhysicalDevice phys = VK_NULL_HANDLE;
  for (uint32_t i = 0; i < nd; i++) {
    VkPhysicalDeviceProperties p;
    vkGetPhysicalDeviceProperties(devs[i], &p);
    if (p.vendorID == vendor && p.deviceID == device_id) { phys = devs[i]; break; }
  }
  if (phys == VK_NULL_HANDLE) { fprintf(stderr, "FATAL target not found\n"); return 3; }
  VkPhysicalDeviceProperties pp;
  vkGetPhysicalDeviceProperties(phys, &pp);
  if (pp.deviceType != VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) {
    fprintf(stderr, "FATAL not DISCRETE_GPU\n"); return 3;
  }
  printf("# device      %s\n", pp.deviceName);
  printf("# identity    vendor=0x%04x device=0x%04x type=DISCRETE\n", pp.vendorID, pp.deviceID);
  printf("# kernel      membw4: uint4 (16 B/thread), differs from membw.c ONLY in element width\n");

  uint32_t qf = 0;
  VkQueueFamilyProperties qfp[8];
  uint32_t nqf = 8;
  vkGetPhysicalDeviceQueueFamilyProperties(phys, &nqf, qfp);
  int ok = 0;
  for (uint32_t i = 0; i < nqf; i++) if (qfp[i].queueFlags & VK_QUEUE_COMPUTE_BIT) { qf = i; ok = 1; }
  if (!ok) { fprintf(stderr, "FATAL no compute queue\n"); return 3; }

  VkPhysicalDeviceMemoryProperties mp;
  vkGetPhysicalDeviceMemoryProperties(phys, &mp);
  uint32_t memtype = UINT32_MAX;
  if (heap >= 0 && (uint32_t)heap < mp.memoryHeapCount) {
    for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
      if (mp.memoryTypes[i].heapIndex == (uint32_t)heap) { memtype = i; break; }
  } else {
    for (int pass = 0; pass < 2 && memtype == UINT32_MAX; pass++)
      for (uint32_t i = 0; i < mp.memoryTypeCount; i++) {
        if (!(mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)) continue;
        if (pass == 0 && (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)) continue;
        memtype = i; break;
      }
  }
  if (memtype == UINT32_MAX) { fprintf(stderr, "FATAL no memory type\n"); return 4; }
  uint32_t hi = mp.memoryTypes[memtype].heapIndex;
  printf("# memtype     index=%u heap=%u size=%llu flags=0x%08x\n", memtype, hi,
         (unsigned long long)mp.memoryHeaps[hi].size, mp.memoryTypes[memtype].propertyFlags);
  {
    uint64_t need = n * 16 * 2, have = mp.memoryHeaps[hi].size;
    if (need > have) {
      fprintf(stderr, "FATAL need %llu B but heap %u holds %llu B\n",
              (unsigned long long)need, hi, (unsigned long long)have);
      return 4;
    }
  }

  float prio = 1.0f;
  VkDeviceQueueCreateInfo qci = {VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
  qci.queueFamilyIndex = qf; qci.queueCount = 1; qci.pQueuePriorities = &prio;
  VkDeviceCreateInfo dci = {VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
  dci.queueCreateInfoCount = 1; dci.pQueueCreateInfos = &qci;
  VkDevice dev;
  if (vkCreateDevice(phys, &dci, NULL, &dev) != VK_SUCCESS) die("vkCreateDevice", 0);
  VkQueue queue;
  vkGetDeviceQueue(dev, qf, 0, &queue);

  VkBufferCreateInfo bci = {VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
  bci.size = n * 16;
  bci.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
  VkBuffer bufs[2];
  VkDeviceMemory mems[2];
  for (int i = 0; i < 2; i++) {
    if (vkCreateBuffer(dev, &bci, NULL, &bufs[i]) != VK_SUCCESS) die("vkCreateBuffer", 0);
    VkMemoryRequirements mr;
    vkGetBufferMemoryRequirements(dev, bufs[i], &mr);
    VkMemoryAllocateInfo mai = {VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    mai.allocationSize = mr.size; mai.memoryTypeIndex = memtype;
    if (vkAllocateMemory(dev, &mai, NULL, &mems[i]) != VK_SUCCESS) die("vkAllocateMemory", 0);
    vkBindBufferMemory(dev, bufs[i], mems[i], 0);
  }

  /* host-visible staging type for init + oracle readback */
  uint32_t st_idx = UINT32_MAX;
  for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
    if ((mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) &&
        (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) { st_idx = i; break; }
  if (st_idx == UINT32_MAX) { fprintf(stderr, "FATAL no coherent host type\n"); return 4; }

  VkCommandPoolCreateInfo cpi = {VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
  cpi.queueFamilyIndex = qf; cpi.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
  VkCommandPool cpool;
  vkCreateCommandPool(dev, &cpi, NULL, &cpool);
  VkCommandBufferAllocateInfo cba = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
  cba.commandPool = cpool; cba.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; cba.commandBufferCount = 1;
  VkCommandBuffer cmd;
  vkAllocateCommandBuffers(dev, &cba, &cmd);

  /* scratch: one buffer for staging src in, one for reading dst out */
  VkBufferCreateInfo sci = {VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
  sci.size = n * 16;
  sci.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
  VkBuffer scratch;
  VkDeviceMemory scratch_mem;
  {
    vkCreateBuffer(dev, &sci, NULL, &scratch);
    VkMemoryRequirements mr;
    vkGetBufferMemoryRequirements(dev, scratch, &mr);
    VkMemoryAllocateInfo mai = {VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    mai.allocationSize = mr.size; mai.memoryTypeIndex = st_idx;
    vkAllocateMemory(dev, &mai, NULL, &scratch_mem);
    vkBindBufferMemory(dev, scratch, scratch_mem, 0);
  }

  uint32_t *host_src = NULL;
  {
    void *p = NULL;
    vkMapMemory(dev, scratch_mem, 0, VK_WHOLE_SIZE, 0, &p);
    host_src = (uint32_t *)p;
    uint32_t st = 0x12345678u;
    for (uint64_t i = 0; i < n * 4; i++) {
      st ^= st << 13; st ^= st >> 17; st ^= st << 5;
      host_src[i] = st;
    }
  }

  VkCommandBufferBeginInfo bi = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
  bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
  VkFence fence;
  VkFenceCreateInfo fci = {VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
  vkCreateFence(dev, &fci, NULL, &fence);
  VkSubmitInfo si = {VK_STRUCTURE_TYPE_SUBMIT_INFO};
  si.commandBufferCount = 1; si.pCommandBuffers = &cmd;

  /* upload src */
  vkResetFences(dev, 1, &fence);
  vkBeginCommandBuffer(cmd, &bi);
  { VkBufferCopy r = {0, 0, n * 16}; vkCmdCopyBuffer(cmd, scratch, bufs[0], 1, &r); }
  vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                       0, 0, NULL, 0, NULL, 0, NULL);
  vkEndCommandBuffer(cmd);
  vkQueueSubmit(queue, 1, &si, fence);
  vkWaitForFences(dev, 1, &fence, VK_TRUE, 60ull * 1000 * 1000 * 1000);

  FILE *f = fopen(spv, "rb");
  if (!f) { fprintf(stderr, "FATAL cannot open %s\n", spv); return 4; }
  fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
  uint32_t *code = malloc((size_t)sz);
  if (fread(code, 1, (size_t)sz, f) != (size_t)sz) { fprintf(stderr, "FATAL short SPV\n"); return 4; }
  fclose(f);
  VkShaderModuleCreateInfo smci = {VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
  smci.codeSize = (size_t)sz; smci.pCode = code;
  VkShaderModule sm;
  vkCreateShaderModule(dev, &smci, NULL, &sm);

  VkDescriptorSetLayoutBinding bnd[2] = {0};
  for (int i = 0; i < 2; i++) {
    bnd[i].binding = (uint32_t)i;
    bnd[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    bnd[i].descriptorCount = 1;
    bnd[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
  }
  VkDescriptorSetLayoutCreateInfo dslci = {VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
  dslci.bindingCount = 2; dslci.pBindings = bnd;
  VkDescriptorSetLayout dsl;
  vkCreateDescriptorSetLayout(dev, &dslci, NULL, &dsl);
  VkDescriptorPoolSize dps = {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2};
  VkDescriptorPoolCreateInfo dpci = {VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
  dpci.maxSets = 1; dpci.poolSizeCount = 1; dpci.pPoolSizes = &dps;
  VkDescriptorPool dp;
  vkCreateDescriptorPool(dev, &dpci, NULL, &dp);
  VkDescriptorSetAllocateInfo dsai = {VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
  dsai.descriptorPool = dp; dsai.descriptorSetCount = 1; dsai.pSetLayouts = &dsl;
  VkDescriptorSet ds;
  vkAllocateDescriptorSets(dev, &dsai, &ds);
  VkDescriptorBufferInfo dbi[2];
  VkWriteDescriptorSet wr[2];
  memset(wr, 0, sizeof wr);
  for (int i = 0; i < 2; i++) {
    dbi[i].buffer = bufs[i]; dbi[i].offset = 0; dbi[i].range = VK_WHOLE_SIZE;
    wr[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    wr[i].dstSet = ds; wr[i].dstBinding = (uint32_t)i; wr[i].descriptorCount = 1;
    wr[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; wr[i].pBufferInfo = &dbi[i];
  }
  vkUpdateDescriptorSets(dev, 2, wr, 0, NULL);

  VkPushConstantRange pcr = {VK_SHADER_STAGE_COMPUTE_BIT, 0, 16};
  VkPipelineLayoutCreateInfo plci = {VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
  plci.setLayoutCount = 1; plci.pSetLayouts = &dsl;
  plci.pushConstantRangeCount = 1; plci.pPushConstantRanges = &pcr;
  VkPipelineLayout pl;
  vkCreatePipelineLayout(dev, &plci, NULL, &pl);
  VkComputePipelineCreateInfo cpi2 = {VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
  cpi2.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
  cpi2.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
  cpi2.stage.module = sm; cpi2.stage.pName = "main";
  cpi2.layout = pl;
  VkPipeline pipe;
  if (vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpi2, NULL, &pipe) != VK_SUCCESS)
    die("vkCreateComputePipelines", 0);

  typedef struct { uint32_t n, iters, seed, base; } PC;
  const uint64_t chunk = (uint64_t)65535 * local_size;
  uint32_t pcr_bytes = (uint32_t)sizeof(PC);

  #define RECORD_PASS(cmdbuf, total)                                              \
    do {                                                                           \
      for (uint64_t off = 0; off < (total); off += chunk) {                       \
        uint64_t m = (total) - off; if (m > chunk) m = chunk;                     \
        PC p = { (uint32_t)m, iters, 0xa5a5a5a5u, (uint32_t)off };                \
        vkCmdPushConstants(cmdbuf, pl, VK_SHADER_STAGE_COMPUTE_BIT, 0, pcr_bytes, &p); \
        vkCmdDispatch(cmdbuf, (uint32_t)((m + local_size - 1) / local_size), 1, 1);    \
      }                                                                            \
    } while (0)

  /* ---------- ORACLE ---------- */
  {
    const uint32_t O = 4096;
    vkResetFences(dev, 1, &fence);
    vkBeginCommandBuffer(cmd, &bi);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL);
    RECORD_PASS(cmd, O);
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT,
                         0, 0, NULL, 0, NULL, 0, NULL);
    { VkBufferCopy r = {0, 0, (VkDeviceSize)O * 16}; vkCmdCopyBuffer(cmd, bufs[1], scratch, 1, &r); }
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                         0, 0, NULL, 0, NULL, 0, NULL);
    vkEndCommandBuffer(cmd);
    vkQueueSubmit(queue, 1, &si, fence);
    if (vkWaitForFences(dev, 1, &fence, VK_TRUE, 30ull * 1000 * 1000 * 1000) != VK_SUCCESS) {
      fprintf(stderr, "FATAL oracle timeout\n"); return 5;
    }
    const uint32_t *got = host_src;   /* scratch was overwritten by the readback */
    uint32_t bad = 0;
    uint32_t st = 0x12345678u;
    for (uint32_t i = 0; i < O * 4; i++) {
      st ^= st << 13; st ^= st >> 17; st ^= st << 5;
      uint32_t want = host_ref(st, iters, 0xa5a5a5a5u);
      if (got[i] != want) { if (!bad) fprintf(stderr, "  first mismatch at scalar i=%u got=%08x want=%08x\n", i, got[i], want); bad++; }
    }
    if (bad) { fprintf(stderr, "ORACLE FAILED: %u/%u scalars mismatched\n", bad, O * 4); return 5; }
    fprintf(stderr, "# ORACLE OK: %u uint4 (%u scalars) verified element-wise\n", O, O * 4);
  }

  /* ---------- timing ---------- */
  double total_bytes = (double)n * 32.0 * (double)dispatches;   /* 16 read + 16 written */
  double *gbps = calloc(samples, sizeof(double));
  char (*mclk_s)[32] = calloc(samples, sizeof *mclk_s);
  char (*sclk_s)[32] = calloc(samples, sizeof *sclk_s);

  for (uint32_t w = 0; w < warmup; w++) {
    vkResetCommandBuffer(cmd, 0);
    vkBeginCommandBuffer(cmd, &bi);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL);
    for (uint32_t d = 0; d < dispatches; d++) RECORD_PASS(cmd, n);
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                         0, 0, NULL, 0, NULL, 0, NULL);
    vkEndCommandBuffer(cmd);
    vkResetFences(dev, 1, &fence);
    vkQueueSubmit(queue, 1, &si, fence);
    vkWaitForFences(dev, 1, &fence, VK_TRUE, 180ull * 1000 * 1000 * 1000);
  }

  for (uint32_t s = 0; s < samples; s++) {
    vkResetCommandBuffer(cmd, 0);
    double t0 = mono_s();
    vkBeginCommandBuffer(cmd, &bi);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL);
    for (uint32_t d = 0; d < dispatches; d++) RECORD_PASS(cmd, n);
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                         0, 0, NULL, 0, NULL, 0, NULL);
    vkEndCommandBuffer(cmd);
    vkResetFences(dev, 1, &fence);
    vkQueueSubmit(queue, 1, &si, fence);
    vkWaitForFences(dev, 1, &fence, VK_TRUE, 180ull * 1000 * 1000 * 1000);
    double t1 = mono_s();
    read_dpm("/sys/class/drm/card1/device/pp_dpm_mclk", mclk_s[s], 32);
    read_dpm("/sys/class/drm/card1/device/pp_dpm_sclk", sclk_s[s], 32);
    gbps[s] = total_bytes / (t1 - t0) / 1e9;
    fprintf(stderr, "  sample %u: %.3f GB/s (%.6f s) mclk=%s sclk=%s\n", s, gbps[s], t1 - t0, mclk_s[s], sclk_s[s]);
  }

  double *sorted = malloc(samples * sizeof(double));
  memcpy(sorted, gbps, samples * sizeof(double));
  qsort(sorted, samples, sizeof(double), cmp_d);
  double med = sorted[samples / 2];
  printf("# config      elems=%llu bytes/buffer=%llu iters=%u dispatches=%u samples=%u local=%u\n",
         (unsigned long long)n, (unsigned long long)(n * 16), iters, dispatches, samples, local_size);
  printf("# traffic     %.3f MiB per dispatch (16 B read + 16 B written per element)\n",
         (double)n * 32.0 / 1048576.0);
  printf("# clocks_load");
  for (uint32_t s = 0; s < samples; s++) printf(" [%u mclk=%s sclk=%s]", s, mclk_s[s], sclk_s[s]);
  printf("\n# result      oracle=VERIFIED\n");
  printf("GBPS median %.3f min %.3f max %.3f\n", med, sorted[0], sorted[samples - 1]);
  return 0;
}