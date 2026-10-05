/* rx550_load — generador de carga COMPUTE para la RX 550, en Vulkan compute.
 *
 * POR QUE EXISTE
 *   El proyecto necesita distinguir si los relojes de la escalera DPM son alcanzables de
 *   verdad o solo entradas de tabla. Eso exige carga real, y hasta ahora no habia ninguna
 *   via: /sys/class/drm/card1/device/hwmon esta EBUSY y los atributos pp_* de debugfs no
 *   existen en este kernel (hallazgo 1448). El barrido de carga —el ultimo paso del §77 para
 *   el techo de reloj de memoria— estaba BLOQUEADO por falta de instrumento, no por falta de
 *   teoria. Este programa es ese instrumento.
 *
 * FRONTERA DURA — la GPU integrada del procesador NO SE TOCA
 *   Este programa NO usa "el primer dispositivo que encuentre".  Selecciona EXCLUSIVAMENTE un
 *   dispositivo cuyo vendorID/deviceID sea 0x1002:0x699f, que es el RX 550 de esta maquina
 *   (0000:01:00.0).  Si no lo encuentra NO crea contexto y sale con codigo 3.  No existe ruta
 *   por la que esto cree un contexto sobre 0000:00:02.0 (i915):  el filtro es por identidad
 *   PCI, no por indice, y el Intel no comparte esos dos campos.
 *   Recomendado ademas lanzarlo con VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json
 *   para que el propio loader de Vulkan no abra el nodo de la Intel.
 *
 * ALCANCE
 *   Solo lectura del mapa de memoria de la GPU y envio de comandos de compute.  No toca
 *   registros, no carga ni descarga modulos, no cambia el estado de energia, no abre fb*, no
 *   cambia la salida de consola.  La consola es de la Intel y sigue siendolo.
 *
 * USO
 *   rx550_load [--info] [--seconds N] [--buffer MiB] [--mode fill|rmw|math]
 *   Opciones de instrumentacion:
 *     --dump-prefix PREFIX   escribe el buffer a PREFIX.mode.bin al terminar
 *     --no-sync              no llama a vkDeviceWaitIdle entre iteraciones
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <vulkan/vulkan.h>

#define RX550_VENDOR 0x1002u
#define RX550_DEVICE 0x699fu

/* El kernel es autocontenido: el SPIR-V va incrustado como array, para que el binario sea
 * reproducible y no dependa de leer ficheros en tiempo de ejecucion.  Regenerar el .h con
 * "glslangValidator -V load.comp -o load.spv" y el script que consta en el hallazgo. */
#include "load_spv.h"

/* vk_result_name() no esta declarado en las cabeceras Vulkan de este sistema.  En vez de
 * añadir una dependencia para nombrar un codigo de error, lo traduzco aqui.  Un
 * instrumento que no compila no es un instrumento. */
static const char *res_name(VkResult r)
{
    switch (r) {
    case VK_SUCCESS:                        return "VK_SUCCESS";
    case VK_NOT_READY:                      return "VK_NOT_READY";
    case VK_TIMEOUT:                        return "VK_TIMEOUT";
    case VK_ERROR_OUT_OF_HOST_MEMORY:       return "VK_ERROR_OUT_OF_HOST_MEMORY";
    case VK_ERROR_OUT_OF_DEVICE_MEMORY:     return "VK_ERROR_OUT_OF_DEVICE_MEMORY";
    case VK_ERROR_INITIALIZATION_FAILED:    return "VK_ERROR_INITIALIZATION_FAILED";
    case VK_ERROR_DEVICE_LOST:              return "VK_ERROR_DEVICE_LOST";
    case VK_ERROR_MEMORY_MAP_FAILED:        return "VK_ERROR_MEMORY_MAP_FAILED";
    case VK_ERROR_LAYER_NOT_PRESENT:        return "VK_ERROR_LAYER_NOT_PRESENT";
    case VK_ERROR_EXTENSION_NOT_PRESENT:    return "VK_ERROR_EXTENSION_NOT_PRESENT";
    case VK_ERROR_FEATURE_NOT_PRESENT:      return "VK_ERROR_FEATURE_NOT_PRESENT";
    case VK_ERROR_INCOMPATIBLE_DRIVER:      return "VK_ERROR_INCOMPATIBLE_DRIVER";
    case VK_ERROR_TOO_MANY_OBJECTS:         return "VK_ERROR_TOO_MANY_OBJECTS";
    case VK_ERROR_FORMAT_NOT_SUPPORTED:     return "VK_ERROR_FORMAT_NOT_SUPPORTED";
    case VK_ERROR_FRAGMENTED_POOL:          return "VK_ERROR_FRAGMENTED_POOL";
    case VK_ERROR_OUT_OF_POOL_MEMORY:       return "VK_ERROR_OUT_OF_POOL_MEMORY";
    case VK_ERROR_INVALID_SHADER_NV:        return "VK_ERROR_INVALID_SHADER_NV";
    default:                                return "VkResult (sin nombre en esta tabla)";
    }
}

#define CHECK_VK(expr, what)                                                    \
    do {                                                                         \
        VkResult _r = (expr);                                                   \
        if (_r != VK_SUCCESS) {                                                 \
            fprintf(stderr, "FALLO %s: VkResult %d (%s)\n", (what), (int)_r,     \
                    res_name(_r));                                              \
            return 3;                                                           \
        }                                                                        \
    } while (0)

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

int main(int argc, char **argv)
{
    int seconds = 8, mib = 256, mode = 1, info_only = 0, do_sync = 1;
    const char *dump_prefix = NULL;

    /* stdout sin buffer: si el proceso revienta, el registro de donde llego no se pierde
     * con el buffer.  Ya me costo un diagnostico vacio por no haberlo puesto. */
    setvbuf(stdout, NULL, _IONBF, 0);

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--seconds") && i + 1 < argc) seconds = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--buffer") && i + 1 < argc) mib = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--info")) info_only = 1;
        else if (!strcmp(argv[i], "--no-sync")) do_sync = 0;
        else if (!strcmp(argv[i], "--dump-prefix") && i + 1 < argc) dump_prefix = argv[++i];
        else if (!strcmp(argv[i], "--mode") && i + 1 < argc) {
            const char *m = argv[++i];
            mode = !strcmp(m, "fill") ? 0 : !strcmp(m, "rmw") ? 1 : 2;
        } else { fprintf(stderr, "opcion desconocida: %s\n", argv[i]); return 2; }
    }

    VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
                              .pApplicationName = "rx550_load",
                              .apiVersion = VK_API_VERSION_1_1 };
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
                                 .pApplicationInfo = &app };
    VkInstance inst;
    CHECK_VK(vkCreateInstance(&ici, NULL, &inst), "vkCreateInstance");

    uint32_t n = 0;
    CHECK_VK(vkEnumeratePhysicalDevices(inst, &n, NULL), "vkEnumeratePhysicalDevices");
    if (!n) { fprintf(stderr, "0 dispositivos fisicos\n"); return 3; }
    VkPhysicalDevice *pds = calloc(n, sizeof *pds);
    if (!pds) return 3;
    CHECK_VK(vkEnumeratePhysicalDevices(inst, &n, pds), "vkEnumeratePhysicalDevices#2");

    /* ---- LA FRONTERA: identidad PCI, no indice ---- */
    VkPhysicalDevice gpu = VK_NULL_HANDLE;
    uint32_t chosen = UINT32_MAX;
    printf("=== dispositivos fisicos que ve Vulkan ===\n");
    for (uint32_t i = 0; i < n; i++) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(pds[i], &p);
        printf("  [%u] vendorID=0x%04X deviceID=0x%04X  %-9s \"%s\"\n",
               i, p.vendorID, p.deviceID,
               p.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU ? "DISCRETE" : "otro",
               p.deviceName);
        if (p.vendorID == RX550_VENDOR && p.deviceID == RX550_DEVICE) { gpu = pds[i]; chosen = i; }
    }
    if (gpu == VK_NULL_HANDLE) {
        fprintf(stderr, "ABORTO: ningun dispositivo es 1002:699f (la RX 550 de esta maquina).\n"
                        "        No se crea contexto sobre ninguno. La iGPU no se toca.\n");
        return 3;
    }
    printf("  --> seleccionado [%u] por identidad PCI: la RX 550. "
           "No se creara contexto sobre otro.\n\n", chosen);

    VkPhysicalDeviceProperties pr;
    vkGetPhysicalDeviceProperties(gpu, &pr);
    printf("=== la tarjeta, segun RADV ===\n");
    printf("  deviceName    %s\n", pr.deviceName);
    printf("  apiVersion    %u.%u.%u\n", VK_VERSION_MAJOR(pr.apiVersion),
           VK_VERSION_MINOR(pr.apiVersion), VK_VERSION_PATCH(pr.apiVersion));
    /* driverName es Vulkan 1.2 core: no esta en VkPhysicalDeviceProperties, hay que pedirlo
     * con vkGetPhysicalDeviceProperties2.  Es la PROCEDENCIA del resultado, asi que vale la
     * pena tenerlo. */
    VkPhysicalDeviceDriverProperties drvp = { .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES };
    VkPhysicalDeviceProperties2 p2 = { .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
                                       .pNext = &drvp };
    vkGetPhysicalDeviceProperties2(gpu, &p2);
    printf("  driverName    %s  version %s\n", drvp.driverName, drvp.driverInfo);
    printf("  conjunctions   %u  descriptorSets %u  memoryAllocCount %u\n",
           drvp.conformanceVersion.major * 100 + drvp.conformanceVersion.minor,
           pr.limits.maxBoundDescriptorSets, pr.limits.maxMemoryAllocationCount);
    printf("  maxWorkGroups %u x %u x %u\n",
           pr.limits.maxComputeWorkGroupCount[0], pr.limits.maxComputeWorkGroupCount[1],
           pr.limits.maxComputeWorkGroupCount[2]);
    printf("  maxWGInvoc    %u\n", pr.limits.maxComputeWorkGroupInvocations);
    printf("  maxStorageRange %u MiB   maxPushConstantSize %u B\n",
           (unsigned)(pr.limits.maxStorageBufferRange >> 20),
           pr.limits.maxPushConstantsSize);
    if (info_only) return 0;

    uint32_t qn = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(gpu, &qn, NULL);
    VkQueueFamilyProperties *qfp = calloc(qn, sizeof *qfp);
    vkGetPhysicalDeviceQueueFamilyProperties(gpu, &qn, qfp);
    uint32_t qi = UINT32_MAX;
    for (uint32_t i = 0; i < qn; i++)
        if (qfp[i].queueFlags & VK_QUEUE_COMPUTE_BIT) { qi = i; break; }
    if (qi == UINT32_MAX) { fprintf(stderr, "sin cola de compute\n"); return 3; }
    printf("  cola compute: familia %u, %d colas\n\n", qi, qfp[qi].queueCount);

    float prio = 1.0f;
    VkDeviceQueueCreateInfo dq = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                                   .queueFamilyIndex = qi, .queueCount = 1,
                                   .pQueuePriorities = &prio };
    VkDeviceCreateInfo dc = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
                              .queueCreateInfoCount = 1, .pQueueCreateInfos = &dq };
    VkDevice dev;
    CHECK_VK(vkCreateDevice(gpu, &dc, NULL, &dev), "vkCreateDevice");
    VkQueue q; vkGetDeviceQueue(dev, qi, 0, &q);

    /* ---- buffer ---- */
    VkDeviceSize bytes = (VkDeviceSize)mib << 20;
    VkBufferCreateInfo bc = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
                              .size = bytes, .usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
                              .sharingMode = VK_SHARING_MODE_EXCLUSIVE };
    VkBuffer buf; CHECK_VK(vkCreateBuffer(dev, &bc, NULL, &buf), "vkCreateBuffer");
    VkMemoryRequirements mr; vkGetBufferMemoryRequirements(dev, buf, &mr);
    VkPhysicalDeviceMemoryProperties mp; vkGetPhysicalDeviceMemoryProperties(gpu, &mp);
    uint32_t mt = UINT32_MAX;
    for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
        if (mr.memoryTypeBits & (1u << i)) { mt = i; break; }
    VkMemoryAllocateInfo ma = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
                                .allocationSize = mr.size, .memoryTypeIndex = mt };
    VkDeviceMemory mem; CHECK_VK(vkAllocateMemory(dev, &ma, NULL, &mem), "vkAllocateMemory");
    CHECK_VK(vkBindBufferMemory(dev, buf, mem, 0), "vkBindBufferMemory");

    /* ---- push constants: mode, iters, base ---- */
    VkPushConstantRange pcr = { .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
                                .offset = 0, .size = 12 };
    VkDescriptorSetLayoutBinding bnd = { .binding = 0,
                                        .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                                        .descriptorCount = 1,
                                        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT };
    VkDescriptorSetLayoutCreateInfo dsl = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
                                           .bindingCount = 1, .pBindings = &bnd };
    VkDescriptorSetLayout dslo; CHECK_VK(vkCreateDescriptorSetLayout(dev, &dsl, NULL, &dslo), "dsl");
    VkPipelineLayoutCreateInfo pl = { .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
                                      .setLayoutCount = 1, .pSetLayouts = &dslo,
                                      .pushConstantRangeCount = 1, .pPushConstantRanges = &pcr };
    VkPipelineLayout plo; CHECK_VK(vkCreatePipelineLayout(dev, &pl, NULL, &plo), "plo");

    VkShaderModuleCreateInfo sm = { .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
                                    .codeSize = K_SPV_LOAD_BYTES, .pCode = k_spv_load };
    VkShaderModule shm; CHECK_VK(vkCreateShaderModule(dev, &sm, NULL, &shm), "vkCreateShaderModule");
    VkComputePipelineCreateInfo cp = { .sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
                                       .stage = { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                                                  .module = shm, .pName = "main" },
                                       .layout = plo };
    VkPipeline pipe; CHECK_VK(vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cp, NULL, &pipe),
                              "vkCreateComputePipelines");

    VkDescriptorPoolSize ps = { .type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1 };
    VkDescriptorPoolCreateInfo dp = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
                                      .maxSets = 1, .poolSizeCount = 1, .pPoolSizes = &ps };
    VkDescriptorPool dpool; CHECK_VK(vkCreateDescriptorPool(dev, &dp, NULL, &dpool), "dpool");
    VkDescriptorSetAllocateInfo da = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
                                       .descriptorPool = dpool, .descriptorSetCount = 1,
                                       .pSetLayouts = &dslo };
    VkDescriptorSet ds; CHECK_VK(vkAllocateDescriptorSets(dev, &da, &ds), "alloc sets");
    VkDescriptorBufferInfo dbi = { .buffer = buf, .offset = 0, .range = bytes };
    VkWriteDescriptorSet w = { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                               .dstSet = ds, .dstBinding = 0, .descriptorCount = 1,
                               .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                               .pBufferInfo = &dbi };
    vkUpdateDescriptorSets(dev, 1, &w, 0, NULL);

    VkCommandPoolCreateInfo cm = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
                                   .queueFamilyIndex = qi };
    VkCommandPool pool; CHECK_VK(vkCreateCommandPool(dev, &cm, NULL, &pool), "cmdpool");
    VkCommandBufferAllocateInfo cb = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
                                       .commandPool = pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
                                       .commandBufferCount = 1 };
    VkCommandBuffer cmd; CHECK_VK(vkAllocateCommandBuffers(dev, &cb, &cmd), "cmdbuf");

    /* maxComputeWorkGroupCount[0] es 65535 en la practica. Un dispatch de 256 MiB son
     * 1048576 workgroups, que lo excede. Por eso el kernel lleva un push constant "base" y el
     * host trocea el rango en trozos de como mucho maxWG. Sin esto el dispatch es invalido. */
    /* maxComputeWorkGroupCount[0] se lee 4294967295 en RADV, no 65535.  Multiplicarlo por 64
     * en uint32 DESBORDA, y el numero de trozos saldria mal.  Uso la spec: el minimo
     * garantizado es 65535, asi que fijo ahi y trabajo en 64 bits para el producto. */
    uint64_t reported = pr.limits.maxComputeWorkGroupCount[0];
    uint64_t max_wg64 = (reported == 0u || reported > 65535u) ? 65535u : reported;
    uint32_t max_wg = (uint32_t)max_wg64;
    uint64_t per_dispatch = max_wg64 * 64u;
    uint64_t elements64 = bytes / 4u;
    if (elements64 > 0xFFFFFFFFull) {
        fprintf(stderr, "el buffer es demasiado grande para un indice uint32 del shader\n");
        return 3;
    }
    uint32_t elements = (uint32_t)elements64;
    uint32_t chunks = (uint32_t)((elements64 + per_dispatch - 1u) / per_dispatch);
    printf("  maxWorkGroups declarado por RADV %llu  ->  uso %llu (minimo garantizado por spec)\n",
           (unsigned long long)reported, (unsigned long long)max_wg64);

    printf("=== la carga que se va a medir ===\n");
    printf("  buffer        %d MiB  (%u elementos de 4 B)\n", mib, elements);
    printf("  local_size_x  64\n");
    printf("  maxWorkGroups %u  -> %u workgroups por dispatch, %u trozos para cubrir todo\n",
           max_wg, max_wg, chunks);
    printf("  modo          %s\n", mode == 0 ? "fill" : mode == 1 ? "rmw" : "math");
    printf("  duracion      %d s   sincronizacion por iteracion: %s\n",
           seconds, do_sync ? "si" : "no");
    printf("\nARRANCANDO  (muestrea gpu_busy_percent, pp_dpm_sclk, pp_dpm_mclk y\n"
           "             amdgpu_pm_info mientras esto corre)\n\n");
    fflush(stdout);

    const double t0 = now_s();
    uint32_t iters = 0;
    float best = 0.0f;
    for (;;) {
        double el = now_s() - t0;
        if (el >= (double)seconds) break;
        VkCommandBufferBeginInfo bi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
                                        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT };
        CHECK_VK(vkBeginCommandBuffer(cmd, &bi), "begin");
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
        vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, plo, 0, 1, &ds, 0, NULL);
        for (uint32_t c = 0; c < chunks; c++) {
            uint32_t pcv[3] = { (uint32_t)mode, mode == 2 ? 64u : 1u,
                                (uint32_t)((uint64_t)c * per_dispatch) };
            vkCmdPushConstants(cmd, plo, VK_SHADER_STAGE_COMPUTE_BIT, 0, 12, pcv);
            vkCmdDispatch(cmd, max_wg, 1, 1);
        }
        CHECK_VK(vkEndCommandBuffer(cmd), "end");
        VkSubmitInfo si = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
                            .commandBufferCount = 1, .pCommandBuffers = &cmd };
        CHECK_VK(vkQueueSubmit(q, 1, &si, VK_NULL_HANDLE), "submit");
        if (do_sync) CHECK_VK(vkQueueWaitIdle(q), "waitidle");
        iters++;
        if ((iters % 16) == 0) {
            float gbs = (float)((double)bytes * iters / (now_s() - t0) / 1e9);
            if (gbs > best) best = gbs;
            printf("  t=%6.2fs  iter=%-6u  %8.2f GB/s  (pico %.2f)\n",
                   now_s() - t0, iters, gbs, best);
            fflush(stdout);
        }
    }
    double el = now_s() - t0;
    double mean_gbs = (double)bytes * iters / el / 1e9;
    printf("\nFINALIZADO  %.3f s  %u iteraciones\n", el, iters);
    printf("  ancho de banda aparente  media %.2f GB/s   pico %.2f GB/s\n", mean_gbs, best);
    printf("  bytes movidos por iteracion (logico): %.0f MiB leidos + %.0f MiB escritos\n",
           (double)bytes / (1 << 20), (double)bytes / (1 << 20));

    if (dump_prefix) {
        uint32_t hmt = UINT32_MAX;
        for (uint32_t i = 0; i < mp.memoryTypeCount; i++)
            if ((mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) &&
                (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) &&
                (mp.memoryTypes[i].heapIndex == mr.memoryTypeBits ? 0 : 1)) { hmt = i; break; }
        if (hmt == UINT32_MAX) {
            fprintf(stderr, "no hay memoria host-visible coherente; volcado omitido\n");
        } else {
            VkDeviceMemory hmem; VkBuffer hbuf;
            VkBufferCreateInfo hbc = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
                                       .size = bytes, .usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                                       .sharingMode = VK_SHARING_MODE_EXCLUSIVE };
            VkMemoryAllocateInfo cma = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
                                         .allocationSize = bytes, .memoryTypeIndex = hmt };
            VkCommandBufferBeginInfo b2 = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
                                            .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT };
            if (vkCreateBuffer(dev, &hbc, NULL, &hbuf) == VK_SUCCESS &&
                vkAllocateMemory(dev, &cma, NULL, &hmem) == VK_SUCCESS &&
                vkBindBufferMemory(dev, hbuf, hmem, 0) == VK_SUCCESS) {
                VkBufferCopy region = { .srcOffset = 0, .dstOffset = 0, .size = bytes };
                vkResetCommandBuffer(cmd, 0);
                vkBeginCommandBuffer(cmd, &b2);
                vkCmdCopyBuffer(cmd, buf, hbuf, 1, &region);
                vkEndCommandBuffer(cmd);
                VkSubmitInfo s2 = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
                                    .commandBufferCount = 1, .pCommandBuffers = &cmd };
                vkQueueSubmit(q, 1, &s2, VK_NULL_HANDLE);
                vkQueueWaitIdle(q);
                void *ptr = NULL;
                if (vkMapMemory(dev, hmem, 0, VK_WHOLE_SIZE, 0, &ptr) == VK_SUCCESS) {
                    char path[512];
                    snprintf(path, sizeof path, "%s.mode%d.bin", dump_prefix, mode);
                    FILE *f = fopen(path, "wb");
                    if (f) { fwrite(ptr, 1, (size_t)bytes, f); fclose(f);
                             printf("  volcado: %s (%u bytes)\n", path, (unsigned)bytes); }
                    else fprintf(stderr, "  no se pudo escribir %s\n", path);
                    vkUnmapMemory(dev, hmem);
                } else fprintf(stderr, "  vkMapMemory del volcado fallo\n");
            } else fprintf(stderr, "  no se pudo crear el buffer de volcado\n");
        }
    }

    vkDeviceWaitIdle(dev);
    vkDestroyCommandPool(dev, pool, NULL);
    vkDestroyPipeline(dev, pipe, NULL);
    vkDestroyShaderModule(dev, shm, NULL);
    vkDestroyPipelineLayout(dev, plo, NULL);
    vkDestroyDescriptorPool(dev, dpool, NULL);
    vkDestroyDescriptorSetLayout(dev, dslo, NULL);
    vkDestroyBuffer(dev, buf, NULL);
    vkFreeMemory(dev, mem, NULL);
    vkDestroyDevice(dev, NULL);
    vkDestroyInstance(inst, NULL);
    free(pds); free(qfp);
    return 0;
}
