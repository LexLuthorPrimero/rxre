/* membw.c — AGENT-23 · VRAM/memory bandwidth harness for the RX550 (GFX8, RADV).
 *
 * WHY THIS EXISTS
 *   FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md closed every bandwidth
 *   figure as VERIFIED / DERIVED / ESTIMATED / UNKNOWN, and left the central one
 *   UNKNOWN: "Bandwidth REAL (medido) VRAM".  Its reason was "no hay interfaz de
 *   lectura sin ejecutar pruebas".  That reason is a claim about the interfaces
 *   it probed (sysfs, debugfs denied, no root), not about capability in general:
 *   a Vulkan compute dispatch is a userspace measurement path and needs no root.
 *
 * WHAT IT MEASURES
 *   Achieved memory throughput of a read+write stream over a chosen heap:
 *     heap 0  DEVICE_LOCAL            1.75 GiB   -> pure VRAM traffic
 *     heap 2  DEVICE_LOCAL+HOST_VIS   256 MiB     -> BAR0-mapped VRAM
 *     heap 1  HOST_VISIBLE            5.77 GiB    -> GTT / system DRAM
 *   Dispatches are timed on the host against a fence.  Traffic accounting is
 *   explicit: bytes = n * 4 read + n * 4 written per dispatch.
 *
 * WHY IT CAN BE TRUSTED
 *   1. Device identity is asserted.  The default display on this host is the
 *      Intel HD 4600, so a harness that picks device 0 silently measures the
 *      wrong ASIC (HARDWARE-FINGERPRINT.md §6).  vendor/device are checked and a
 *      mismatch is a hard failure, not a warning.
 *   2. Oracle before timing.  A small run is read back and compared element-wise
 *      against the value the host itself can predict.  A shader that did
 *      nothing, read nothing, or was eliminated by the compiler fails here, and
 *      the program exits non-zero without reporting any bandwidth.
 *   3. Reported flags.  The heap and memory-type propertyFlags are printed, so
 *      the artifact states which memory class produced the number.
 *   4. Clock telemetry is sampled around the samples, because a bandwidth number
 *      without its MCLK is not interpretable.
 *
 * EXIT CODES
 *   0 measured and oracle-verified   2 usage   3 device mismatch/unsupported
 *   4 allocation or pipeline failure 5 ORACLE FAILED (no bandwidth reported)
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

/* ---- the same transform as shaders/membw.comp, evaluated on the host ---- */
static uint32_t host_ref(uint32_t v, uint32_t iters, uint32_t seed) {
  for (uint32_t k = 0; k < iters; k++)
    v = (v ^ (v << 13)) * 0x5bd1e995u;
  return v ^ seed;
}

static int cmp_d(const void *a, const void *b) {
  double x = *(const double *)a, y = *(const double *)b;
  return (x > y) - (x < y);
}

/* ---- clock telemetry ------------------------------------------------------
 * amdgpu prints pp_dpm_* as "0: 300Mhz *" where the '*' is a TRAILING marker on
 * the active state, not a prefix.  Reading the token after it is the only way to
 * get the clock that is actually in force while the GPU is loaded; an earlier
 * revision of this harness looked for text *after* the '*', found nothing, and
 * reported UNKNOWN for every reading. */
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
  const char *spv = "shaders/membw.comp.spv";
  uint32_t vendor = 0x1002, device_id = 0x699f;   /* the target ASIC */
  uint64_t n = 1ull << 26;        /* elements per buffer (default 256 MiB each) */
  uint32_t iters = 0;
  uint32_t dispatches = 64;
  uint32_t samples = 7;
  uint32_t warmup = 2;
  int heap = -1;                  /* -1 = pick DEVICE_LOCAL, prefer not host-visible */
  uint32_t local_size = 256;
  int barriers = 1;               /* memory barrier between dependent dispatches */

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
    else if (!strcmp(argv[i], "--no-barriers")) barriers = 0;
    else {
      fprintf(stderr, "uso: %s [--spv F] [--vendor 0x..] [--device 0x..] [--elems N]\n"
                      "          [--iters K] [--dispatches D] [--samples S] [--warmup W]\n"
                      "          [--heap H] [--local-size L]\n", argv[0]);
      return 2;
    }
  }
  if (samples == 0) samples = 1;

  /* ---------- instance / physical device ---------- */
  VkApplicationInfo app = {VK_STRUCTURE_TYPE_APPLICATION_INFO};
  app.apiVersion = VK_API_VERSION_1_1;
  app.pApplicationName = "membw";
  VkInstanceCreateInfo ici = {VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
  ici.pApplicationInfo = &app;
  VkInstance inst;
  if (vkCreateInstance(&ici, NULL, &inst) != VK_SUCCESS) die("vkCreateInstance", 0);

  uint32_t nd = 0;
  if (vkEnumeratePhysicalDevices(inst, &nd, NULL) != VK_SUCCESS || nd == 0) {
    fprintf(stderr, "FATAL no vulkan physical device\n"); return 4;
  }
  VkPhysicalDevice *devs = calloc(nd, sizeof *devs);
  vkEnumeratePhysicalDevices(inst, &nd, devs);

  VkPhysicalDevice phys = VK_NULL_HANDLE;
  for (uint32_t i = 0; i < nd; i++) {
    VkPhysicalDeviceProperties p;
    vkGetPhysicalDeviceProperties(devs[i], &p);
    if (p.vendorID == vendor && p.deviceID == device_id) { phys = devs[i]; break; }
  }
  if (phys == VK_NULL_HANDLE) {
    fprintf(stderr, "FATAL target ASIC 0x%04x:0x%04x not found among %u devices; "
                    "refusing to measure a different GPU\n", vendor, device_id, nd);
    for (uint32_t i = 0; i < nd; i++) {
      VkPhysicalDeviceProperties p;
      vkGetPhysicalDeviceProperties(devs[i], &p);
      fprintf(stderr, "  present: vendor=0x%04x device=0x%04x type=%u %s\n",
              p.vendorID, p.deviceID, p.deviceType, p.deviceName);
    }
    return 3;
  }
  VkPhysicalDeviceProperties pp;
  vkGetPhysicalDeviceProperties(phys, &pp);
  if (pp.deviceType != VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) {
    fprintf(stderr, "FATAL deviceType=%u is not DISCRETE_GPU; refusing\n", pp.deviceType);
    return 3;
  }
  printf("# device      %s\n", pp.deviceName);
  printf("# identity    vendor=0x%04x device=0x%04x type=DISCRETE api=%u.%u.%u\n",
         pp.vendorID, pp.deviceID, VK_VERSION_MAJOR(pp.apiVersion),
         VK_VERSION_MINOR(pp.apiVersion), VK_VERSION_PATCH(pp.apiVersion));

  uint32_t qf = 0;
  VkQueueFamilyProperties qfp[8];
  uint32_t nqf = 8;
  vkGetPhysicalDeviceQueueFamilyProperties(phys, &nqf, qfp);
  int found_compute = 0;
  for (uint32_t i = 0; i < nqf; i++)
    if (qfp[i].queueFlags & VK_QUEUE_COMPUTE_BIT) { qf = i; found_compute = 1; }
  if (!found_compute) { fprintf(stderr, "FATAL no compute queue family\n"); return 3; }

  VkPhysicalDeviceMemoryProperties mp;
  vkGetPhysicalDeviceMemoryProperties(phys, &mp);

  /* ---- choose memory type: requested heap, else DEVICE_LOCAL, preferring a
     type that is NOT host-visible so the stream stays inside VRAM ---- */
  uint32_t memtype = UINT32_MAX;
  if (heap >= 0 && (uint32_t)heap < mp.memoryHeapCount) {
    for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
      if (mp.memoryTypes[i].heapIndex == (uint32_t)heap) { memtype = i; break; }
    if (memtype == UINT32_MAX) { fprintf(stderr, "FATAL heap %d has no memory type\n", heap); return 4; }
  } else {
    for (int pass = 0; pass < 2 && memtype == UINT32_MAX; pass++) {
      VkMemoryPropertyFlags want = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;
      for (uint32_t i = 0; i < mp.memoryTypeCount; i++) {
        if ((mp.memoryTypes[i].propertyFlags & want) != want) continue;
        if (pass == 0 && (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)) continue;
        memtype = i; break;
      }
    }
    if (memtype == UINT32_MAX) { fprintf(stderr, "FATAL no DEVICE_LOCAL memory type\n"); return 4; }
  }
  uint32_t hi = mp.memoryTypes[memtype].heapIndex;
  printf("# memtype     index=%u heap=%u size=%llu flags=0x%08x%s%s%s%s\n", memtype, hi,
         (unsigned long long)mp.memoryHeaps[hi].size, mp.memoryTypes[memtype].propertyFlags,
         (mp.memoryTypes[memtype].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT) ? " DEVICE_LOCAL" : "",
         (mp.memoryTypes[memtype].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) ? " HOST_VISIBLE" : "",
         (mp.memoryTypes[memtype].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) ? " HOST_COHERENT" : "",
         (mp.memoryTypes[memtype].propertyFlags & VK_MEMORY_PROPERTY_HOST_CACHED_BIT) ? " HOST_CACHED" : "");

  /* ---------- device ---------- */
  float prio = 1.0f;
  VkDeviceQueueCreateInfo qci = {VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
  qci.queueFamilyIndex = qf; qci.queueCount = 1; qci.pQueuePriorities = &prio;
  VkDeviceCreateInfo dci = {VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
  dci.queueCreateInfoCount = 1; dci.pQueueCreateInfos = &qci;
  VkDevice dev;
  if (vkCreateDevice(phys, &dci, NULL, &dev) != VK_SUCCESS) die("vkCreateDevice", 0);
  VkQueue queue;
  vkGetDeviceQueue(dev, qf, 0, &queue);

  /* Two buffers must both fit in the chosen heap.  An earlier revision requested
     512 MiB from the 256 MiB BAR heap: vkAllocateMemory still returned SUCCESS
     and the run reported a nonsense 591674 GB/s, because the driver demoted the
     allocation instead of failing.  A silent demotion is an INVALID_RESULT, so
     the request is checked against the heap here rather than trusted. */
  {
    uint64_t need = n * 4 * 2;
    uint64_t have = mp.memoryHeaps[hi].size;
    if (need > have) {
      fprintf(stderr, "FATAL need %llu B (two buffers of %llu B) but heap %u holds only %llu B\n",
              (unsigned long long)need, (unsigned long long)(n * 4), hi, (unsigned long long)have);
      return 4;
    }
    printf("# headroom    need=%llu B heap=%llu B (%llu B spare)\n",
           (unsigned long long)need, (unsigned long long)have, (unsigned long long)(have - need));
  }

  /* ---------- two buffers ---------- */
  VkBufferCreateInfo bci = {VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
  bci.size = n * 4;
  bci.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
  bci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
  VkBuffer bufs[2];
  VkDeviceMemory mems[2];
  for (int i = 0; i < 2; i++) {
    if (vkCreateBuffer(dev, &bci, NULL, &bufs[i]) != VK_SUCCESS) die("vkCreateBuffer", 0);
    VkMemoryRequirements mr;
    vkGetBufferMemoryRequirements(dev, bufs[i], &mr);
    VkMemoryAllocateInfo mai = {VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    mai.allocationSize = mr.size; mai.memoryTypeIndex = memtype;
    if (vkAllocateMemory(dev, &mai, NULL, &mems[i]) != VK_SUCCESS) die("vkAllocateMemory", 0);
    if (vkBindBufferMemory(dev, bufs[i], mems[i], 0) != VK_SUCCESS) die("vkBindBufferMemory", 0);
  }

  /* initialise src on the host (only meaningful for host-visible memory) */
  uint32_t *host_src = NULL;
  if (mp.memoryTypes[memtype].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) {
    void *p = NULL;
    if (vkMapMemory(dev, mems[0], 0, VK_WHOLE_SIZE, 0, &p) != VK_SUCCESS) die("vkMapMemory", 0);
    host_src = (uint32_t *)p;
    uint32_t st = 0x12345678u;
    for (uint64_t i = 0; i < n; i++) {
      st ^= st << 13; st ^= st >> 17; st ^= st << 5;
      host_src[i] = st;
    }
  } else {
    /* device-local: push a known pattern with a copy from a staging buffer */
    VkBufferCreateInfo sci = {VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
    sci.size = n * 4;
    sci.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
    VkBuffer staging;
    if (vkCreateBuffer(dev, &sci, NULL, &staging) != VK_SUCCESS) die("vkCreateBuffer staging", 0);
    VkMemoryRequirements mr;
    vkGetBufferMemoryRequirements(dev, staging, &mr);
    uint32_t st_idx = UINT32_MAX;
    for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
      if ((mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) &&
          (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) { st_idx = i; break; }
    if (st_idx == UINT32_MAX) { fprintf(stderr, "FATAL no coherent host staging type\n"); return 4; }
    VkMemoryAllocateInfo mai = {VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    mai.allocationSize = mr.size; mai.memoryTypeIndex = st_idx;
    VkDeviceMemory stmem;
    if (vkAllocateMemory(dev, &mai, NULL, &stmem) != VK_SUCCESS) die("vkAllocateMemory staging", 0);
    vkBindBufferMemory(dev, staging, stmem, 0);
    void *p = NULL;
    vkMapMemory(dev, stmem, 0, VK_WHOLE_SIZE, 0, &p);
    host_src = (uint32_t *)p;
    uint32_t st = 0x12345678u;
    for (uint64_t i = 0; i < n; i++) {
      st ^= st << 13; st ^= st >> 17; st ^= st << 5;
      host_src[i] = st;
    }
    /* copy staging -> buf0 */
    VkCommandPoolCreateInfo cpci = {VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
    cpci.queueFamilyIndex = qf; cpci.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    VkCommandPool pool;
    vkCreateCommandPool(dev, &cpci, NULL, &pool);
    VkCommandBufferAllocateInfo cbai = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    cbai.commandPool = pool; cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; cbai.commandBufferCount = 1;
    VkCommandBuffer cb;
    vkAllocateCommandBuffers(dev, &cbai, &cb);
    VkCommandBufferBeginInfo cbbi = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    cbbi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkBeginCommandBuffer(cb, &cbbi);
    VkBufferCopy region = {0, 0, n * 4};
    vkCmdCopyBuffer(cb, staging, bufs[0], 1, &region);
    vkEndCommandBuffer(cb);
    VkSubmitInfo si = {VK_STRUCTURE_TYPE_SUBMIT_INFO};
    si.commandBufferCount = 1; si.pCommandBuffers = &cb;
    vkQueueSubmit(queue, 1, &si, VK_NULL_HANDLE);
    vkQueueWaitIdle(queue);
    fprintf(stderr, "# initialised src via staging copy\n");
  }

  /* ---------- shader ---------- */
  FILE *f = fopen(spv, "rb");
  if (!f) { fprintf(stderr, "FATAL cannot open %s\n", spv); return 4; }
  fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
  uint32_t *code = malloc((size_t)sz);
  if (fread(code, 1, (size_t)sz, f) != (size_t)sz) { fprintf(stderr, "FATAL short SPV read\n"); return 4; }
  fclose(f);
  VkShaderModuleCreateInfo smci = {VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
  smci.codeSize = (size_t)sz; smci.pCode = code;
  VkShaderModule sm;
  if (vkCreateShaderModule(dev, &smci, NULL, &sm) != VK_SUCCESS) die("vkCreateShaderModule", 0);

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

  VkDescriptorPoolSize ps = {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2};
  VkDescriptorPoolCreateInfo dpci = {VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
  dpci.maxSets = 1; dpci.poolSizeCount = 1; dpci.pPoolSizes = &ps;
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
  VkComputePipelineCreateInfo cpci2 = {VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
  cpci2.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
  cpci2.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
  cpci2.stage.module = sm; cpci2.stage.pName = "main";
  cpci2.layout = pl;
  VkPipeline pipe;
  if (vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpci2, NULL, &pipe) != VK_SUCCESS)
    die("vkCreateComputePipelines", 0);

  VkCommandPoolCreateInfo cp2 = {VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
  cp2.queueFamilyIndex = qf; cp2.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
  VkCommandPool cpool;
  vkCreateCommandPool(dev, &cp2, NULL, &cpool);
  VkCommandBufferAllocateInfo cba = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
  cba.commandPool = cpool; cba.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; cba.commandBufferCount = 1;
  VkCommandBuffer cmd;
  vkAllocateCommandBuffers(dev, &cba, &cmd);
  VkFenceCreateInfo fci = {VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
  VkFence fence;
  vkCreateFence(dev, &fci, NULL, &fence);

  /* vkCmdDispatch caps the x workgroup count at 65535, so a large buffer is
     covered by several chunked dispatches with a base offset in the push
     constants.  Recording one full pass over the buffer = one "iteration";
     a pass moves n*8 bytes (4 read + 4 written). */
  typedef struct { uint32_t n, iters, seed, base; } PC;
  const uint64_t chunk = (uint64_t)65535 * local_size;
  uint64_t chunks = (n + chunk - 1) / chunk;
  uint32_t pcr_bytes = (uint32_t)sizeof(PC);

  #define RECORD_PASS(cmdbuf, total_elems)                                              \
    do {                                                                               \
      for (uint64_t off = 0; off < (total_elems); off += chunk) {                     \
        uint64_t m = (total_elems) - off; if (m > chunk) m = chunk;                    \
        PC p = { (uint32_t)m, iters, 0xa5a5a5a5u, (uint32_t)off };                    \
        vkCmdPushConstants(cmdbuf, pl, VK_SHADER_STAGE_COMPUTE_BIT, 0,                 \
                           pcr_bytes, &p);                                            \
        /* A barrier between chunks is REQUIRED for correctness whenever the    */   \
        /* chunks touch overlapping storage.  Consecutive chunks of one pass are */   \
        /* disjoint by construction (base advances by `m`), so the only real     */   \
        /* dependency is pass d -> pass d+1 of the same buffer.  The barrier is */   \
        /* therefore a real cost, not an artefact, and measuring with it absent  */   \
        /* would report a bandwidth the hardware cannot sustain.                */   \
        if (barriers)                                                                   \
          vkCmdPipelineBarrier(cmdbuf, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,          \
                               VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, 0,               \
                               0, NULL, 0, NULL, 0, NULL);                            \
        vkCmdDispatch(cmdbuf, (uint32_t)((m + local_size - 1) / local_size), 1, 1);    \
      }                                                                                \
    } while (0)

  VkCommandBufferBeginInfo bi = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
  bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;

  /* ---------- ORACLE: small run, read back, compare element-wise ----------
     Without this, a shader the compiler eliminated would report infinite
     bandwidth.  Result is a hard gate: no oracle, no number.                */
  {
    const uint32_t O = 4096;
    vkResetFences(dev, 1, &fence);
    vkBeginCommandBuffer(cmd, &bi);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL);
    RECORD_PASS(cmd, O);
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                             VK_PIPELINE_STAGE_HOST_BIT, 0, 0, NULL, 0, NULL, 0, NULL);
    vkEndCommandBuffer(cmd);
    VkSubmitInfo si = {VK_STRUCTURE_TYPE_SUBMIT_INFO};
    si.commandBufferCount = 1; si.pCommandBuffers = &cmd;
    if (vkQueueSubmit(queue, 1, &si, fence) != VK_SUCCESS) die("submit oracle", 0);
    if (vkWaitForFences(dev, 1, &fence, VK_TRUE, 30ull * 1000 * 1000 * 1000) != VK_SUCCESS) {
      fprintf(stderr, "FATAL oracle timed out\n"); return 5;
    }
    /* device-local dst is not mappable: copy the first 4096 elements back */
    uint32_t *got = malloc((size_t)O * 4);
    uint32_t *want = malloc((size_t)O * 4);
    int readable = 0;
    if ((mp.memoryTypes[memtype].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)) {
      void *p = NULL;
      vkMapMemory(dev, mems[1], 0, VK_WHOLE_SIZE, 0, &p);
      memcpy(got, p, (size_t)O * 4);
      vkUnmapMemory(dev, mems[1]);
      readable = 1;
    } else {
      /* scratch staging buffer + copy */
      VkBufferCreateInfo sci2 = {VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
      sci2.size = (VkDeviceSize)O * 4;
      sci2.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT;
      VkBuffer scratch;
      vkCreateBuffer(dev, &sci2, NULL, &scratch);
      VkMemoryRequirements mr2;
      vkGetBufferMemoryRequirements(dev, scratch, &mr2);
      uint32_t st2 = UINT32_MAX;
      for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
        if ((mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) &&
            (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) { st2 = i; break; }
      VkMemoryAllocateInfo mai2 = {VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
      mai2.allocationSize = mr2.size; mai2.memoryTypeIndex = st2;
      VkDeviceMemory sm2;
      vkAllocateMemory(dev, &mai2, NULL, &sm2);
      vkBindBufferMemory(dev, scratch, sm2, 0);
      void *p = NULL;
      vkMapMemory(dev, sm2, 0, VK_WHOLE_SIZE, 0, &p);
      vkResetFences(dev, 1, &fence);
      vkBeginCommandBuffer(cmd, &bi);
      VkBufferCopy reg = {0, 0, (VkDeviceSize)O * 4};
      vkCmdCopyBuffer(cmd, bufs[1], scratch, 1, &reg);
      vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                           0, 0, NULL, 0, NULL, 0, NULL);
      vkEndCommandBuffer(cmd);
      vkQueueSubmit(queue, 1, &si, fence);
      vkWaitForFences(dev, 1, &fence, VK_TRUE, 30ull * 1000 * 1000 * 1000);
      memcpy(got, p, (size_t)O * 4);
      vkUnmapMemory(dev, sm2);
      readable = 1;
    }
    /* host_src holds the pattern for the whole buffer; first 4096 were written */
    uint32_t st = 0x12345678u;
    for (uint32_t i = 0; i < O; i++) {
      st ^= st << 13; st ^= st >> 17; st ^= st << 5;
      want[i] = host_ref(st, iters, 0xa5a5a5a5u);
    }
    uint32_t bad = 0;
    if (readable)
      for (uint32_t i = 0; i < O; i++)
        if (got[i] != want[i]) { if (!bad) fprintf(stderr, "  first mismatch at i=%u got=%08x want=%08x\n", i, got[i], want[i]); bad++; }
    if (bad || !readable) {
      fprintf(stderr, "ORACLE FAILED: %u/%u elements mismatched (readable=%d)\n", bad, O, readable);
      return 5;
    }
    fprintf(stderr, "# ORACLE OK: %u elements verified element-wise\n", O);
  }

  /* ---------- timing ---------- */
  double bytes_per_dispatch = (double)n * 8.0;          /* 4 read + 4 written */
  double total_bytes = bytes_per_dispatch * (double)dispatches;
  double *gbps = calloc(samples, sizeof(double));
  char (*mclk_s)[32] = calloc(samples, sizeof *mclk_s);
  char (*sclk_s)[32] = calloc(samples, sizeof *sclk_s);

  char mclk0[128], sclk0[128], mclk1[128], sclk1[128];
  read_dpm("/sys/class/drm/card1/device/pp_dpm_mclk", mclk0, sizeof mclk0);
  read_dpm("/sys/class/drm/card1/device/pp_dpm_sclk", sclk0, sizeof sclk0);

  for (uint32_t w = 0; w < warmup; w++) {
    vkResetCommandBuffer(cmd, 0);
    vkBeginCommandBuffer(cmd, &bi);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL);
    for (uint32_t d = 0; d < dispatches; d++)
      RECORD_PASS(cmd, n);
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                         0, 0, NULL, 0, NULL, 0, NULL);
    vkEndCommandBuffer(cmd);
    vkResetFences(dev, 1, &fence);
    VkSubmitInfo si = {VK_STRUCTURE_TYPE_SUBMIT_INFO};
    si.commandBufferCount = 1; si.pCommandBuffers = &cmd;
    vkQueueSubmit(queue, 1, &si, fence);
    vkWaitForFences(dev, 1, &fence, VK_TRUE, 120ull * 1000 * 1000 * 1000);
  }

  for (uint32_t s = 0; s < samples; s++) {
    vkResetCommandBuffer(cmd, 0);
    VkCommandBufferBeginInfo bi = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    double t0 = mono_s();
    vkBeginCommandBuffer(cmd, &bi);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL);
    for (uint32_t d = 0; d < dispatches; d++)
      RECORD_PASS(cmd, n);
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                         0, 0, NULL, 0, NULL, 0, NULL);
    vkEndCommandBuffer(cmd);
    vkResetFences(dev, 1, &fence);
    VkSubmitInfo si = {VK_STRUCTURE_TYPE_SUBMIT_INFO};
    si.commandBufferCount = 1; si.pCommandBuffers = &cmd;
    vkQueueSubmit(queue, 1, &si, fence);
    vkWaitForFences(dev, 1, &fence, VK_TRUE, 120ull * 1000 * 1000 * 1000);
    double t1 = mono_s();
    /* clock sampled right after each timed pass, i.e. under sustained load */
    read_dpm("/sys/class/drm/card1/device/pp_dpm_mclk", mclk_s[s], 32);
    read_dpm("/sys/class/drm/card1/device/pp_dpm_sclk", sclk_s[s], 32);
    gbps[s] = total_bytes / (t1 - t0) / 1e9;
    fprintf(stderr, "  sample %u: %.3f GB/s (%.6f s) mclk=%s sclk=%s\n",
            s, gbps[s], t1 - t0, mclk_s[s], sclk_s[s]);
  }

  read_dpm("/sys/class/drm/card1/device/pp_dpm_mclk", mclk1, sizeof mclk1);
  read_dpm("/sys/class/drm/card1/device/pp_dpm_sclk", sclk1, sizeof sclk1);

  double *sorted = malloc(samples * sizeof(double));
  memcpy(sorted, gbps, samples * sizeof(double));
  qsort(sorted, samples, sizeof(double), cmp_d);
  double med = sorted[samples / 2];

  printf("# config      elems=%llu bytes/buffer=%llu iters=%u dispatches=%u samples=%u local=%u\n",
         (unsigned long long)n, (unsigned long long)(n * 4), iters, dispatches, samples, local_size);
  printf("# clocks      mclk_before=%s mclk_after=%s sclk_before=%s sclk_after=%s\n",
         mclk0, mclk1, sclk0, sclk1);
  printf("# clocks_load");
  for (uint32_t s = 0; s < samples; s++) printf(" [%u mclk=%s sclk=%s]", s, mclk_s[s], sclk_s[s]);
  printf("\n");
  printf("# traffic     %.3f MiB per dispatch (%.0f B read + %.0f B written per element)\n",
         bytes_per_dispatch / 1048576.0, 4.0, 4.0);
  printf("# result      oracle=VERIFIED\n");
  printf("GBPS median %.3f min %.3f max %.3f\n", med, sorted[0], sorted[samples - 1]);
  fprintf(stderr, "# GBPS median=%.3f min=%.3f max=%.3f\n", med, sorted[0], sorted[samples - 1]);
  return 0;
}