/*
 * VK_LAYER_ITERATIVERO_jitter_observer
 * Capa Vulkan de observabilidad para EXP-F1-A (FASE R-4C).
 *
 * NIVEL A: intercepta vkCmdPushConstants y vuelca el payload (marker, jx, jy).
 * NIVEL B: rastrea allocaciones HOST_VISIBLE + binds de buffers y, en cada
 *          vkQueueSubmit, busca por el magic del UBO per-frame, lee las matrices
 *          y RECONSTRUYE el jitter en px (nunca lee el supuesto offset "jitter").
 *
 * Esta capa NO modifica el sistema ni el driver: se carga vía VK_LAYER_PATH local.
 */
#define _GNU_SOURCE
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vk_layer.h>
#include <vulkan/vulkan_core.h>

#include "../perframe.h"

#define VK_LAYER_EXPORT __attribute__((visibility("default")))

static const char *LAYER_NAME = "VK_LAYER_ITERATIVERO_jitter_observer";

/* -------------------- registry (proceso unico: 1 instancia/device) ---------------- */
#define MAX_REC 128

typedef struct {
  VkDeviceMemory mem;
  uint32_t       typeIndex;
  VkDeviceSize   size;
  void          *mapPtr;
  VkDeviceSize   mapOffset;
  VkDeviceSize   mapSize;
} MemRec;

typedef struct {
  VkBuffer     buf;
  VkDeviceSize size;
} BufRec;

typedef struct {
  VkBuffer     buf;
  VkDeviceMemory mem;
  VkDeviceSize   offset;
} BindRec;

typedef struct {
  VkInstance      instance;
  PFN_vkGetInstanceProcAddr nextGIPA;
  PFN_vkGetDeviceProcAddr   nextGDPA;
  PFN_vkGetPhysicalDeviceMemoryProperties nextMemProps;
  VkPhysicalDeviceMemoryProperties memProps;
  int memPropsValid;
} InstData;

typedef struct {
  VkDevice device;
  InstData *inst;
  PFN_vkDestroyDevice nextDestroyDevice;
  PFN_vkAllocateMemory nextAllocateMemory;
  PFN_vkFreeMemory nextFreeMemory;
  PFN_vkMapMemory nextMapMemory;
  PFN_vkUnmapMemory nextUnmapMemory;
  PFN_vkBindBufferMemory nextBindBufferMemory;
  PFN_vkCreateBuffer nextCreateBuffer;
  PFN_vkDestroyBuffer nextDestroyBuffer;
  PFN_vkQueueSubmit nextQueueSubmit;
  PFN_vkCmdPushConstants nextCmdPushConstants;
  PFN_vkGetDeviceProcAddr nextGDPA;

  MemRec  mems[MAX_REC];  int memCount;
  BufRec  bufs[MAX_REC];  int bufCount;
  BindRec binds[MAX_REC]; int bindCount;
} DevData;

static InstData g_inst = {0};
static DevData  g_dev  = {0};
static FILE    *g_log  = NULL;

/* -------------------- helpers -------------------- */
#define APPEND(arr, cnt, v) \
  if ((cnt) < MAX_REC) { (arr)[(cnt)++] = (v); }
#define REMOVE_IDX(arr, cnt, i) \
  if ((i) < (cnt)) { (arr)[(i)] = (arr)[(cnt) - 1]; (cnt)--; }

static void log_line(DevData *d, const char *fmt, ...) {
  if (!g_log) {
    const char *p = getenv("ITER_LAYER_LOG");
    g_log = p ? fopen(p, "w") : fopen("./layer_recovered.log", "w");
    if (g_log) setvbuf(g_log, NULL, _IOLBF, 0);
  }
  if (g_log && d) {
    va_list ap;
    va_start(ap, fmt);
    vfprintf(g_log, fmt, ap);
    va_end(ap);
    fputc('\n', g_log);
  }
}

static int mem_host_visible(DevData *d, uint32_t typeIndex) {
  if (!d->inst || !d->inst->memPropsValid) return 0;
  if (typeIndex >= d->inst->memProps.memoryTypeCount) return 0;
  return (d->inst->memProps.memoryTypes[typeIndex].propertyFlags &
          VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) != 0;
}

/* Esta funcion NUNCA se ejecuta salvo para logging. Reconstruye jitter correcto
 * usando la convencion validada en el selftest de la app. */
static void snapshot_ubo(DevData *d) {
  for (int b = 0; b < d->bindCount; b++) {
    BindRec *br = &d->binds[b];
    MemRec  *mr = NULL;
    for (int m = 0; m < d->memCount; m++)
      if (d->mems[m].mem == br->mem) { mr = &d->mems[m]; break; }
    if (!mr || !mr->mapPtr || !mem_host_visible(d, mr->typeIndex)) continue;

    const PerFrame *pf = (const PerFrame *)((const char *)mr->mapPtr + br->offset);
    if (!pf) continue;
    if (pf->magic != PERFRAME_MAGIC) continue;

    float jx, jy;
    perframe_recover_jitter(pf->projBase, pf->projJit, pf->viewport[0],
                            pf->viewport[1], &jx, &jy);
    log_line(d, "%u %.9f %.9f", pf->frameMarker, (double)jx, (double)jy);
  }
}

/* -------------------- intercepted: instance -------------------- */
static VKAPI_ATTR void VKAPI_CALL jit_GetPhysicalDeviceMemoryProperties(
    VkPhysicalDevice physicalDevice, VkPhysicalDeviceMemoryProperties *pProp) {
  if (!g_inst.nextMemProps) {
    /* sin chain: devolver vitadeshimo zeros */
    memset(pProp, 0, sizeof(*pProp));
    return;
  }
  g_inst.nextMemProps(physicalDevice, pProp);
  g_inst.memProps = *pProp;
  g_inst.memPropsValid = 1;
}

static VKAPI_ATTR VkResult VKAPI_CALL jit_CreateInstance(
    const VkInstanceCreateInfo *pCreateInfo, const VkAllocationCallbacks *pAllocator,
    VkInstance *pInstance) {
  PFN_vkGetInstanceProcAddr gipa = NULL;

  const VkLayerInstanceCreateInfo *lc =
      (const VkLayerInstanceCreateInfo *)pCreateInfo->pNext;
  while (lc) {
    if (lc->sType == VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO &&
        lc->function == VK_LAYER_LINK_INFO && lc->u.pLayerInfo) {
      gipa = lc->u.pLayerInfo->pfnNextGetInstanceProcAddr;
      break;
    }
    lc = (const VkLayerInstanceCreateInfo *)lc->pNext;
  }
  if (!gipa) return VK_ERROR_INITIALIZATION_FAILED;

  PFN_vkCreateInstance createInstance =
      (PFN_vkCreateInstance)gipa(NULL, "vkCreateInstance");
  VkResult r = createInstance(pCreateInfo, pAllocator, pInstance);
  if (r != VK_SUCCESS) return r;

  g_inst.instance = *pInstance;
  g_inst.nextGIPA = gipa;
  PFN_vkGetInstanceProcAddr instGIPA =
      (PFN_vkGetInstanceProcAddr)gipa(*pInstance, "vkGetInstanceProcAddr");
  g_inst.nextGDPA =
      (PFN_vkGetDeviceProcAddr)instGIPA(*pInstance, "vkGetDeviceProcAddr");
  g_inst.nextMemProps = (PFN_vkGetPhysicalDeviceMemoryProperties)
      instGIPA(*pInstance, "vkGetPhysicalDeviceMemoryProperties");
  return r;
}

static VKAPI_ATTR void VKAPI_CALL jit_DestroyInstance(
    VkInstance instance, const VkAllocationCallbacks *pAllocator) {
  if (g_inst.nextGIPA)
    ((PFN_vkDestroyInstance)g_inst.nextGIPA(instance, "vkDestroyInstance"))(
        instance, pAllocator);
  if (g_log) fclose(g_log);
  g_log = NULL;
  memset(&g_inst, 0, sizeof(g_inst));
  memset(&g_dev, 0, sizeof(g_dev));
}

static VKAPI_ATTR VkResult VKAPI_CALL jit_CreateDevice(
    VkPhysicalDevice physicalDevice, const VkDeviceCreateInfo *pCreateInfo,
    const VkAllocationCallbacks *pAllocator, VkDevice *pDevice) {
  PFN_vkGetDeviceProcAddr gdpa = NULL;

  const VkLayerDeviceCreateInfo *lc =
      (const VkLayerDeviceCreateInfo *)pCreateInfo->pNext;
  while (lc) {
    if (lc->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO &&
        lc->function == VK_LAYER_LINK_INFO && lc->u.pLayerInfo) {
      gdpa = lc->u.pLayerInfo->pfnNextGetDeviceProcAddr;
      break;
    }
    lc = (const VkLayerDeviceCreateInfo *)lc->pNext;
  }
  if (!gdpa) return VK_ERROR_INITIALIZATION_FAILED;

  PFN_vkCreateDevice createDevice = (PFN_vkCreateDevice)
      g_inst.nextGIPA(g_inst.instance, "vkCreateDevice");
  VkResult r = createDevice(physicalDevice, pCreateInfo, pAllocator, pDevice);
  if (r != VK_SUCCESS) return r;

  g_dev.device = *pDevice;
  g_dev.nextGDPA = gdpa;
  g_dev.nextDestroyDevice = (PFN_vkDestroyDevice)gdpa(*pDevice, "vkDestroyDevice");
  g_dev.nextAllocateMemory = (PFN_vkAllocateMemory)gdpa(*pDevice, "vkAllocateMemory");
  g_dev.nextFreeMemory = (PFN_vkFreeMemory)gdpa(*pDevice, "vkFreeMemory");
  g_dev.nextMapMemory = (PFN_vkMapMemory)gdpa(*pDevice, "vkMapMemory");
  g_dev.nextUnmapMemory = (PFN_vkUnmapMemory)gdpa(*pDevice, "vkUnmapMemory");
  g_dev.nextBindBufferMemory =
      (PFN_vkBindBufferMemory)gdpa(*pDevice, "vkBindBufferMemory");
  g_dev.nextCreateBuffer = (PFN_vkCreateBuffer)gdpa(*pDevice, "vkCreateBuffer");
  g_dev.nextDestroyBuffer = (PFN_vkDestroyBuffer)gdpa(*pDevice, "vkDestroyBuffer");
  g_dev.nextQueueSubmit = (PFN_vkQueueSubmit)gdpa(*pDevice, "vkQueueSubmit");
  g_dev.nextCmdPushConstants =
      (PFN_vkCmdPushConstants)gdpa(*pDevice, "vkCmdPushConstants");
  g_dev.inst = &g_inst;
  return r;
}

/* -------------------- intercepted: device -------------------- */
static VKAPI_ATTR VkResult VKAPI_CALL jit_AllocateMemory(
    VkDevice device, const VkMemoryAllocateInfo *pAllocateInfo,
    const VkAllocationCallbacks *pAllocator, VkDeviceMemory *pMemory) {
  VkResult r = g_dev.nextAllocateMemory(device, pAllocateInfo, pAllocator, pMemory);
  if (r == VK_SUCCESS) {
    MemRec mr = {*pMemory, pAllocateInfo->memoryTypeIndex, pAllocateInfo->allocationSize,
                 0, 0, 0};
    APPEND(g_dev.mems, g_dev.memCount, mr);
  }
  return r;
}

static VKAPI_ATTR void VKAPI_CALL jit_FreeMemory(
    VkDevice device, VkDeviceMemory mem, const VkAllocationCallbacks *pAllocator) {
  for (int i = 0; i < g_dev.memCount; i++)
    if (g_dev.mems[i].mem == mem) { REMOVE_IDX(g_dev.mems, g_dev.memCount, i); break; }
  g_dev.nextFreeMemory(device, mem, pAllocator);
}

static VKAPI_ATTR VkResult VKAPI_CALL jit_MapMemory(
    VkDevice device, VkDeviceMemory mem, VkDeviceSize offset, VkDeviceSize size,
    VkMemoryMapFlags flags, void **ppData) {
  VkResult r = g_dev.nextMapMemory(device, mem, offset, size, flags, ppData);
  if (r == VK_SUCCESS)
    for (int i = 0; i < g_dev.memCount; i++)
      if (g_dev.mems[i].mem == mem) {
        g_dev.mems[i].mapPtr = *ppData;
        g_dev.mems[i].mapOffset = offset;
        g_dev.mems[i].mapSize = size;
        break;
      }
  return r;
}

static VKAPI_ATTR void VKAPI_CALL jit_UnmapMemory(
    VkDevice device, VkDeviceMemory mem) {
  for (int i = 0; i < g_dev.memCount; i++)
    if (g_dev.mems[i].mem == mem) g_dev.mems[i].mapPtr = NULL;
  g_dev.nextUnmapMemory(device, mem);
}

static VKAPI_ATTR VkResult VKAPI_CALL jit_CreateBuffer(
    VkDevice device, const VkBufferCreateInfo *pCreateInfo,
    const VkAllocationCallbacks *pAllocator, VkBuffer *pBuffer) {
  VkResult r = g_dev.nextCreateBuffer(device, pCreateInfo, pAllocator, pBuffer);
  if (r == VK_SUCCESS) {
    BufRec br = {*pBuffer, pCreateInfo->size};
    APPEND(g_dev.bufs, g_dev.bufCount, br);
  }
  return r;
}

static VKAPI_ATTR void VKAPI_CALL jit_DestroyBuffer(
    VkDevice device, VkBuffer buffer, const VkAllocationCallbacks *pAllocator) {
  for (int i = 0; i < g_dev.bufCount; i++)
    if (g_dev.bufs[i].buf == buffer) { REMOVE_IDX(g_dev.bufs, g_dev.bufCount, i); break; }
  g_dev.nextDestroyBuffer(device, buffer, pAllocator);
}

static VKAPI_ATTR VkResult VKAPI_CALL jit_BindBufferMemory(
    VkDevice device, VkBuffer buffer, VkDeviceMemory memory, VkDeviceSize offset) {
  VkResult r = g_dev.nextBindBufferMemory(device, buffer, memory, offset);
  if (r == VK_SUCCESS) {
    BindRec br = {buffer, memory, offset};
    APPEND(g_dev.binds, g_dev.bindCount, br);
  }
  return r;
}

static const char *jit_env_enabled(const char *name) {
  const char *v = getenv(name);
  return (v && strcmp(v, "1") == 0) ? v : NULL;
}

static VKAPI_ATTR VkResult VKAPI_CALL jit_QueueSubmit(
    VkQueue queue, uint32_t submitCount, const VkSubmitInfo *pSubmits, VkFence fence) {
  if (jit_env_enabled("ITER_JITTER_LAYER_LEVEL_B")) snapshot_ubo(&g_dev);
  return g_dev.nextQueueSubmit(queue, submitCount, pSubmits, fence);
}

static VKAPI_ATTR void VKAPI_CALL jit_CmdPushConstants(
    VkCommandBuffer commandBuffer, VkPipelineLayout layout,
    VkShaderStageFlags stageFlags, uint32_t offset, uint32_t size,
    const void *pValues) {
  if (jit_env_enabled("ITER_JITTER_LAYER_LEVEL_A") && pValues && size >= 16) {
    const PushPayload *pp = (const PushPayload *)pValues;
    log_line(&g_dev, "%u %.9f %.9f", pp->frameMarker, (double)pp->jitterX,
             (double)pp->jitterY);
  }
  g_dev.nextCmdPushConstants(commandBuffer, layout, stageFlags, offset, size, pValues);
}

/* -------------------- dispatch resolvers -------------------- */
static PFN_vkVoidFunction get_cts_for_instance(const char *name);
static PFN_vkVoidFunction VKAPI_CALL layer_GetDeviceProcAddr(VkDevice dev,
                                                             const char *name);
static VKAPI_ATTR void VKAPI_CALL jit_DestroyDevice(
    VkDevice device, const VkAllocationCallbacks *pAllocator);

static PFN_vkVoidFunction VKAPI_CALL layer_GetInstanceProcAddr(VkInstance inst,
                                                               const char *name) {
  if (inst == VK_NULL_HANDLE) {
    if (!strcmp(name, "vkGetInstanceProcAddr"))
      return (PFN_vkVoidFunction)layer_GetInstanceProcAddr;
    if (!strcmp(name, "vkCreateInstance")) return (PFN_vkVoidFunction)jit_CreateInstance;
    if (!strcmp(name, "vkGetDeviceProcAddr"))
      return (PFN_vkVoidFunction)layer_GetDeviceProcAddr;
    return NULL;
  }
  return get_cts_for_instance(name);
}

static PFN_vkVoidFunction VKAPI_CALL layer_GetDeviceProcAddr(VkDevice dev,
                                                             const char *name) {
  if (dev == VK_NULL_HANDLE) return NULL;
  if (!strcmp(name, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)layer_GetDeviceProcAddr;
  if (!strcmp(name, "vkAllocateMemory")) return (PFN_vkVoidFunction)jit_AllocateMemory;
  if (!strcmp(name, "vkFreeMemory")) return (PFN_vkVoidFunction)jit_FreeMemory;
  if (!strcmp(name, "vkMapMemory")) return (PFN_vkVoidFunction)jit_MapMemory;
  if (!strcmp(name, "vkUnmapMemory")) return (PFN_vkVoidFunction)jit_UnmapMemory;
  if (!strcmp(name, "vkCreateBuffer")) return (PFN_vkVoidFunction)jit_CreateBuffer;
  if (!strcmp(name, "vkDestroyBuffer")) return (PFN_vkVoidFunction)jit_DestroyBuffer;
  if (!strcmp(name, "vkBindBufferMemory")) return (PFN_vkVoidFunction)jit_BindBufferMemory;
  if (!strcmp(name, "vkQueueSubmit")) return (PFN_vkVoidFunction)jit_QueueSubmit;
  if (!strcmp(name, "vkCmdPushConstants")) return (PFN_vkVoidFunction)jit_CmdPushConstants;
  if (!strcmp(name, "vkDestroyDevice")) return (PFN_vkVoidFunction)jit_DestroyDevice;
  if (g_dev.nextGDPA) return g_dev.nextGDPA(dev, name);
  return NULL;
}

static PFN_vkVoidFunction get_cts_for_instance(const char *name) {
  if (!strcmp(name, "vkGetInstanceProcAddr")) return (PFN_vkVoidFunction)layer_GetInstanceProcAddr;
  if (!strcmp(name, "vkCreateInstance")) return (PFN_vkVoidFunction)jit_CreateInstance;
  if (!strcmp(name, "vkDestroyInstance")) return (PFN_vkVoidFunction)jit_DestroyInstance;
  if (!strcmp(name, "vkCreateDevice")) return (PFN_vkVoidFunction)jit_CreateDevice;
  if (!strcmp(name, "vkGetPhysicalDeviceMemoryProperties"))
    return (PFN_vkVoidFunction)jit_GetPhysicalDeviceMemoryProperties;
  if (!strcmp(name, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)layer_GetDeviceProcAddr;
  if (g_inst.nextGIPA && g_inst.instance)
    return g_inst.nextGIPA(g_inst.instance, name);
  return NULL;
}

static VKAPI_ATTR void VKAPI_CALL jit_DestroyDevice(
    VkDevice device, const VkAllocationCallbacks *pAllocator) {
  if (g_dev.nextDestroyDevice) g_dev.nextDestroyDevice(device, pAllocator);
  memset(&g_dev, 0, sizeof(g_dev));
}

/* ----------- entry points exported to loader ----------- */
VK_LAYER_EXPORT PFN_vkVoidFunction VKAPI_CALL vkGetInstanceProcAddr(
    VkInstance inst, const char *name) {
  return layer_GetInstanceProcAddr(inst, name);
}

VK_LAYER_EXPORT PFN_vkVoidFunction VKAPI_CALL vkGetDeviceProcAddr(
    VkDevice dev, const char *name) {
  return layer_GetDeviceProcAddr(dev, name);
}