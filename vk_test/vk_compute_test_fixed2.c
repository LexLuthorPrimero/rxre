/*
 * vk_compute_test_fixed.c — harness compute Vulkan, resolución de funciones en fases.
 *
 * PROCEDENCIA Y RELACIÓN CON EL ARTEFACTO ORIGINAL
 * ==================================================
 * Este fichero es una REIMPLEMENTACIÓN nueva, escrita desde cero a partir del
 * análisis estático del binario `vk_test/vk_compute_test`
 * (SHA-256 017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745).
 *
 * NO es el binario original recompilado, ni una versión parcheada de él: el
 * código fuente original no existe en el repositorio y nunca estuvo versionado
 * (`git log -- vk_test/` no devuelve commits). Lo que se conserva del original es
 * el FLUJO DE DATOS, reconstruido por desensamblado y documentado en
 * `findings/1616-1625/VK_COMPUTE_TEST_AUDITORIA_ESTATICA.md`.
 *
 * DEFECTO QUE CORRIGE
 * ====================
 * El binario original resolvía los punteros de función mediante `load_func()`,
 * que invocaba `vkGetInstanceProcAddr(g_instance, name)`. En
 * `load_all_functions()` ese lote se ejecutaba ANTES de crear la instancia, con
 * `g_instance == NULL`. Según la especificación de Vulkan,
 * `vkGetInstanceProcAddr(VK_NULL_HANDLE, name)` devuelve puntero válido
 * únicamente para los comandos globales (vkEnumerateInstanceExtensionProperties,
 * vkEnumerateInstanceLayerProperties, vkCreateInstance) y NULL para todos los
 * demás. El original cargaba siete nombres en ese lote; solo el primero es
 * global, por lo que abortaba en `vkEnumeratePhysicalDevices` con exit(1).
 *
 * Aquí la resolución se separa en fases explícitas:
 *   FASE 0  loader      : dlopen/dlsym de libvulkan.so.1 -> vkGetInstanceProcAddr
 *   FASE 1  globales    : vkGetInstanceProcAddr(VK_NULL_HANDLE, ...)
 *   FASE 2  instancia   : vkCreateInstance
 *   FASE 3  de instancia: vkGetInstanceProcAddr(instance, ...)
 *   FASE 4  enumeración : vkEnumeratePhysicalDevices + verificación RX 550
 *   FASE 5  dispositivo : vkCreateDevice + vkGetDeviceQueue
 *   FASE 6  de device   : vkGetDeviceProcAddr(device, ...)
 *
 * CONTRATO DE LA PRUEBA (idéntico al original, según auditoría estática)
 * =======================================================================
 *   - buffer de salida de 4 bytes, binding 0, STORAGE_BUFFER
 *   - CPU lo inicializa a CERO con memset tras mapearlo (0x4013bb)
 *   - dos dispatch: uno de calentamiento y uno de medición
 *   - fence con UINT64_MAX antes de leer
 *   - valor esperado 42 como literal INMEDIATO en el código (0x401e13)
 *   - valor observado leído de memoria MAPEADA (0x401dee)
 *   - comparación y ramas: PASS -> stdout + exit 0, FAIL -> stderr + exit 1
 *
 * COMPILACIÓN
 * ============
 *   gcc -O2 -o vk_test/vk_compute_test_fixed vk_test/vk_compute_test_fixed.c \
 *       -lvulkan
 * (equivalente a: gcc -O2 ... $(pkg-config --cflags --libs vulkan))
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <dlfcn.h>
#include <vulkan/vulkan.h>

#define RX550_VENDOR_ID 0x1002u
#define RX550_DEVICE_ID 0x699fu
#define EXPECTED_VALUE  42u

/* ---- FASE 0: loader ---- */
static void *g_vulkan_lib = NULL;
static PFN_vkGetInstanceProcAddr p_vkGetInstanceProcAddr = NULL;

/* ---- FASE 1: funciones globales ---- */
static PFN_vkCreateInstance p_vkCreateInstance = NULL;

/* ---- FASE 3: funciones de instancia ---- */
static PFN_vkDestroyInstance      p_vkDestroyInstance      = NULL;
static PFN_vkEnumeratePhysicalDevices p_vkEnumeratePhysicalDevices = NULL;
static PFN_vkGetPhysicalDeviceProperties p_vkGetPhysicalDeviceProperties = NULL;
static PFN_vkGetPhysicalDeviceMemoryProperties p_vkGetPhysicalDeviceMemoryProperties = NULL;
static PFN_vkGetPhysicalDeviceQueueFamilyProperties p_vkGetPhysicalDeviceQueueFamilyProperties = NULL;

/* ---- FASE 5: funciones de dispositivo ---- */
static PFN_vkCreateDevice   p_vkCreateDevice   = NULL;
static PFN_vkDestroyDevice  p_vkDestroyDevice  = NULL;
static PFN_vkGetDeviceQueue p_vkGetDeviceQueue = NULL;

/* ---- FASE 6: funciones de device ---- */
static PFN_vkCreateBuffer               p_vkCreateBuffer;
static PFN_vkDestroyBuffer              p_vkDestroyBuffer;
static PFN_vkGetBufferMemoryRequirements p_vkGetBufferMemoryRequirements;
static PFN_vkAllocateMemory             p_vkAllocateMemory;
static PFN_vkFreeMemory                 p_vkFreeMemory;
static PFN_vkBindBufferMemory           p_vkBindBufferMemory;
static PFN_vkMapMemory                  p_vkMapMemory;
static PFN_vkUnmapMemory                p_vkUnmapMemory;
static PFN_vkCreateShaderModule         p_vkCreateShaderModule;
static PFN_vkDestroyShaderModule        p_vkDestroyShaderModule;
static PFN_vkCreateDescriptorSetLayout  p_vkCreateDescriptorSetLayout;
static PFN_vkDestroyDescriptorSetLayout p_vkDestroyDescriptorSetLayout;
static PFN_vkCreatePipelineLayout       p_vkCreatePipelineLayout;
static PFN_vkDestroyPipelineLayout      p_vkDestroyPipelineLayout;
static PFN_vkCreateComputePipelines     p_vkCreateComputePipelines;
static PFN_vkDestroyPipeline            p_vkDestroyPipeline;
static PFN_vkCreateDescriptorPool       p_vkCreateDescriptorPool;
static PFN_vkDestroyDescriptorPool      p_vkDestroyDescriptorPool;
static PFN_vkAllocateDescriptorSets     p_vkAllocateDescriptorSets;
static PFN_vkUpdateDescriptorSets       p_vkUpdateDescriptorSets;
static PFN_vkCreateCommandPool          p_vkCreateCommandPool;
static PFN_vkDestroyCommandPool         p_vkDestroyCommandPool;
static PFN_vkAllocateCommandBuffers     p_vkAllocateCommandBuffers;
static PFN_vkFreeCommandBuffers         p_vkFreeCommandBuffers;
static PFN_vkBeginCommandBuffer         p_vkBeginCommandBuffer;
static PFN_vkEndCommandBuffer           p_vkEndCommandBuffer;
static PFN_vkCmdBindPipeline            p_vkCmdBindPipeline;
static PFN_vkCmdBindDescriptorSets      p_vkCmdBindDescriptorSets;
static PFN_vkCmdDispatch                p_vkCmdDispatch;
static PFN_vkQueueSubmit                p_vkQueueSubmit;
static PFN_vkCreateFence                p_vkCreateFence;
static PFN_vkDestroyFence               p_vkDestroyFence;
static PFN_vkWaitForFences              p_vkWaitForFences;
static PFN_vkDeviceWaitIdle             p_vkDeviceWaitIdle;

/* informe de error uniforme, equivalente al original */
static int vk_error(const char *name, int line, VkResult r)
{
	fprintf(stderr, "Vulkan error at line %d: %s = %d\n", line, name, (int)r);
	return 1;
}

#define CHECK(call, name)                                    \
	do {                                                    \
		VkResult r_ = (call);                             \
		if (r_ != VK_SUCCESS)                             \
			return vk_error((name), __LINE__, r_);     \
	} while (0)

/* FASE 0 */
static int load_loader(void)
{
	g_vulkan_lib = dlopen("libvulkan.so.1", RTLD_NOW);
	if (!g_vulkan_lib) {
		fprintf(stderr, "Cannot open libvulkan.so.1\n");
		return 1;
	}
	p_vkGetInstanceProcAddr =
		(PFN_vkGetInstanceProcAddr)dlsym(g_vulkan_lib, "vkGetInstanceProcAddr");
	if (!p_vkGetInstanceProcAddr) {
		fprintf(stderr, "Cannot load vkGetInstanceProcAddr\n");
		return 1;
	}
	return 0;
}

/* FASE 3: resolución con instancia válida; aborta si falta alguna */
static int load_instance_funcs(VkInstance inst, const char *phase)
{
#define LOAD_INST(field, name)                                            \
	do {                                                                  \
		field = (PFN_##name)p_vkGetInstanceProcAddr(inst, #name);       \
		if (!field) {                                                    \
			fprintf(stderr, "Failed to load Vulkan function: %s\n", #name); \
			return 1;                                                  \
		}                                                               \
	} while (0)

	(void)phase;
	LOAD_INST(p_vkEnumeratePhysicalDevices, vkEnumeratePhysicalDevices);
	LOAD_INST(p_vkGetPhysicalDeviceProperties, vkGetPhysicalDeviceProperties);
	LOAD_INST(p_vkGetPhysicalDeviceMemoryProperties, vkGetPhysicalDeviceMemoryProperties);
	LOAD_INST(p_vkGetPhysicalDeviceQueueFamilyProperties, vkGetPhysicalDeviceQueueFamilyProperties);
	/* Comandos de INSTANCIA: se resuelven con vkGetInstanceProcAddr(instance,…)
	 * porque reciben VkPhysicalDevice, no VkDevice. Deben cargarse ANTES de
	 * crear el VkDevice. Reparación 2026-10-16: faltaban y producían SIGSEGV. */
	LOAD_INST(p_vkCreateDevice, vkCreateDevice);
	LOAD_INST(p_vkDestroyDevice, vkDestroyDevice);
	LOAD_INST(p_vkDestroyInstance, vkDestroyInstance);
#undef LOAD_INST
	return 0;
}

/* FASE 6: resolución con VkDevice válido */
static int load_device_funcs(VkDevice dev)
{
	PFN_vkGetDeviceProcAddr p_vkGetDeviceProcAddr =
		(PFN_vkGetDeviceProcAddr)p_vkGetInstanceProcAddr(NULL, "vkGetDeviceProcAddr");
	if (!p_vkGetDeviceProcAddr) {
		fprintf(stderr, "Failed to load Vulkan function: vkGetDeviceProcAddr\n");
		return 1;
	}

#define LOAD_DEV(field, name)                                          \
	do {                                                              \
		field = (PFN_##name)p_vkGetDeviceProcAddr(dev, #name);      \
		if (!field) {                                                \
			fprintf(stderr, "Failed to load Vulkan function: %s\n", #name); \
			return 1;                                              \
		}                                                           \
	} while (0)

	LOAD_DEV(p_vkCreateBuffer, vkCreateBuffer);
	LOAD_DEV(p_vkDestroyBuffer, vkDestroyBuffer);
	LOAD_DEV(p_vkGetBufferMemoryRequirements, vkGetBufferMemoryRequirements);
	LOAD_DEV(p_vkAllocateMemory, vkAllocateMemory);
	LOAD_DEV(p_vkFreeMemory, vkFreeMemory);
	LOAD_DEV(p_vkBindBufferMemory, vkBindBufferMemory);
	LOAD_DEV(p_vkMapMemory, vkMapMemory);
	LOAD_DEV(p_vkUnmapMemory, vkUnmapMemory);
	LOAD_DEV(p_vkCreateShaderModule, vkCreateShaderModule);
	LOAD_DEV(p_vkDestroyShaderModule, vkDestroyShaderModule);
	LOAD_DEV(p_vkCreateDescriptorSetLayout, vkCreateDescriptorSetLayout);
	LOAD_DEV(p_vkDestroyDescriptorSetLayout, vkDestroyDescriptorSetLayout);
	LOAD_DEV(p_vkCreatePipelineLayout, vkCreatePipelineLayout);
	LOAD_DEV(p_vkDestroyPipelineLayout, vkDestroyPipelineLayout);
	LOAD_DEV(p_vkCreateComputePipelines, vkCreateComputePipelines);
	LOAD_DEV(p_vkDestroyPipeline, vkDestroyPipeline);
	LOAD_DEV(p_vkCreateDescriptorPool, vkCreateDescriptorPool);
	LOAD_DEV(p_vkDestroyDescriptorPool, vkDestroyDescriptorPool);
	LOAD_DEV(p_vkAllocateDescriptorSets, vkAllocateDescriptorSets);
	LOAD_DEV(p_vkUpdateDescriptorSets, vkUpdateDescriptorSets);
	LOAD_DEV(p_vkCreateCommandPool, vkCreateCommandPool);
	LOAD_DEV(p_vkDestroyCommandPool, vkDestroyCommandPool);
	LOAD_DEV(p_vkAllocateCommandBuffers, vkAllocateCommandBuffers);
	LOAD_DEV(p_vkFreeCommandBuffers, vkFreeCommandBuffers);
	LOAD_DEV(p_vkBeginCommandBuffer, vkBeginCommandBuffer);
	LOAD_DEV(p_vkEndCommandBuffer, vkEndCommandBuffer);
	LOAD_DEV(p_vkCmdBindPipeline, vkCmdBindPipeline);
	LOAD_DEV(p_vkCmdBindDescriptorSets, vkCmdBindDescriptorSets);
	LOAD_DEV(p_vkCmdDispatch, vkCmdDispatch);
	LOAD_DEV(p_vkQueueSubmit, vkQueueSubmit);
	LOAD_DEV(p_vkCreateFence, vkCreateFence);
	LOAD_DEV(p_vkDestroyFence, vkDestroyFence);
	LOAD_DEV(p_vkWaitForFences, vkWaitForFences);
	LOAD_DEV(p_vkDeviceWaitIdle, vkDeviceWaitIdle);
	/* Comando de DEVICE: se resuelve con vkGetDeviceProcAddr(device,…) porque
	 * requiere un VkDevice válido. Debe cargarse DESPUÉS de crear el device.
	 * Reparación 2026-10-16: faltaba y habría producido SIGSEGV al invocar
	 * p_vkGetDeviceQueue justo después de vkCreateDevice. */
	LOAD_DEV(p_vkGetDeviceQueue, vkGetDeviceQueue);
#undef LOAD_DEV
	return 0;
}

static uint32_t find_memory_type(const VkPhysicalDeviceMemoryProperties *mp, uint32_t bits)
{
	for (uint32_t i = 0; i < mp->memoryTypeCount; i++)
		if (bits & (1u << i))
			return i;
	return UINT32_MAX;
}

static int run_dispatch(VkDevice dev, VkQueue queue, uint32_t qfam,
                        VkDescriptorSet dset, VkPipelineLayout pl_layout,
                        VkPipeline pipeline, VkShaderModule shader_mod,
                        VkCommandPool cmd_pool, VkBuffer buf, VkFence fence)
{
	VkCommandBufferAllocateInfo cb_ai = { VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO };
	cb_ai.commandPool = cmd_pool;
	cb_ai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
	cb_ai.commandBufferCount = 1;

	VkCommandBuffer cmd = VK_NULL_HANDLE;
	CHECK(p_vkAllocateCommandBuffers(dev, &cb_ai, &cmd), "vkAllocateCommandBuffers");

	VkCommandBufferBeginInfo cb_begin = { VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
	cb_begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
	CHECK(p_vkBeginCommandBuffer(cmd, &cb_begin), "vkBeginCommandBuffer");

	p_vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
	p_vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pl_layout,
	                          0, 1, &dset, 0, NULL);
	p_vkCmdDispatch(cmd, 1, 1, 1);
	CHECK(p_vkEndCommandBuffer(cmd), "vkEndCommandBuffer");

	VkSubmitInfo si = { VK_STRUCTURE_TYPE_SUBMIT_INFO };
	si.commandBufferCount = 1;
	si.pCommandBuffers = &cmd;
	CHECK(p_vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit");

	CHECK(p_vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "vkWaitForFences");

	p_vkFreeCommandBuffers(dev, cmd_pool, 1, &cmd);
	(void)qfam;
	return 0;
}

int main(int argc, char **argv)
{
	const char *shader_path =
		(argc > 1) ? argv[1] : "/tmp/rxre_spirv_tests/simple.comp.spv";

	printf("=== Vulkan Compute Test — RX 550 / POLARIS12 (fases) ===\n");

	/* FASE 0 */
	if (load_loader())
		return 1;

	/* FASE 1: solo el comando global */
	p_vkCreateInstance =
		(PFN_vkCreateInstance)p_vkGetInstanceProcAddr(NULL, "vkCreateInstance");
	if (!p_vkCreateInstance) {
		fprintf(stderr, "Failed to load Vulkan function: vkCreateInstance\n");
		return 1;
	}

	/* FASE 2 */
	VkApplicationInfo app = { VK_STRUCTURE_TYPE_APPLICATION_INFO };
	app.pApplicationName = "vk_compute_test_fixed";
	app.applicationVersion = 1;
	app.pEngineName = "none";
	app.engineVersion = 1;
	app.apiVersion = VK_API_VERSION_1_0;

	VkInstanceCreateInfo ici = { VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO };
	ici.pApplicationInfo = &app;

	VkInstance instance = VK_NULL_HANDLE;
	CHECK(p_vkCreateInstance(&ici, NULL, &instance), "vkCreateInstance");

	/* FASE 3 */
	if (load_instance_funcs(instance, "instance")) {
			p_vkDestroyInstance(instance, NULL);
		return 1;
	}

	/* FASE 4: enumerar y verificar RX 550 */
	uint32_t count = 0;
	CHECK(p_vkEnumeratePhysicalDevices(instance, &count, NULL),
	      "vkEnumeratePhysicalDevices");
	if (count == 0) {
		fprintf(stderr, "No Vulkan physical devices\n");
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	VkPhysicalDevice *devs = calloc(count, sizeof(*devs));
	if (!devs) {
		fprintf(stderr, "Out of memory\n");
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	CHECK(p_vkEnumeratePhysicalDevices(instance, &count, devs),
	      "vkEnumeratePhysicalDevices");

	VkPhysicalDevice pdev = VK_NULL_HANDLE;
	for (uint32_t i = 0; i < count; i++) {
		VkPhysicalDeviceProperties pr = { 0 };
		p_vkGetPhysicalDeviceProperties(devs[i], &pr);
		printf("GPU%u: %s  vendor=0x%04x device=0x%04x type=%u\n",
		       i, pr.deviceName, pr.vendorID, pr.deviceID, (unsigned)pr.deviceType);
		if (pr.vendorID == RX550_VENDOR_ID && pr.deviceID == RX550_DEVICE_ID) {
			pdev = devs[i];
			printf(">>> SELECTED: %s (RX 550 / POLARIS12)\n", pr.deviceName);
		}
	}
	if (pdev == VK_NULL_HANDLE) {
		fprintf(stderr, "RX 550 (vendor=0x%04x device=0x%04x) NOT found\n",
		        RX550_VENDOR_ID, RX550_DEVICE_ID);
		free(devs);
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	free(devs);

	/* cola compute */
	uint32_t qfam = UINT32_MAX;
	uint32_t qcount = 0;
	p_vkGetPhysicalDeviceQueueFamilyProperties(pdev, &qcount, NULL);
	VkQueueFamilyProperties *qf = calloc(qcount ? qcount : 1, sizeof(*qf));
	p_vkGetPhysicalDeviceQueueFamilyProperties(pdev, &qcount, qf);
	for (uint32_t i = 0; i < qcount; i++)
		if (qf[i].queueFlags & VK_QUEUE_COMPUTE_BIT) {
			qfam = i;
			break;
		}
	free(qf);
	if (qfam == UINT32_MAX) {
		fprintf(stderr, "No compute queue family\n");
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}

	VkPhysicalDeviceMemoryProperties mem_props = { 0 };
	p_vkGetPhysicalDeviceMemoryProperties(pdev, &mem_props);

	/* FASE 5: creación del dispositivo y obtención de la cola compute.
	 * p_vkCreateDevice (comando de instancia) ya fue resuelto en la FASE 3.
	 * p_vkGetDeviceQueue (comando de device) se resuelve en la FASE 6. */
	float prio = 1.0f;
	VkDeviceQueueCreateInfo qci = { VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO };
	qci.queueFamilyIndex = qfam;
	qci.queueCount = 1;
	qci.pQueuePriorities = &prio;

	VkDeviceCreateInfo dci = { VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO };
	dci.queueCreateInfoCount = 1;
	dci.pQueueCreateInfos = &qci;

	VkDevice dev = VK_NULL_HANDLE;
	/* Defensa en profundidad: load_instance_funcs() ya aborta si falta el
	 * puntero, pero el core dump del 2026-10-16 mostró que una llamada
	 * através de un puntero nulo produce SIGSEGV con r12=0x0 y salida
	 * silenciosa (buffer no vaciado). Se verifica explícitamente para que un
	 * fallo futuro sea un mensaje legible, no unasegmentación. */
	if (!p_vkCreateDevice) {
		fprintf(stderr, "Failed to load Vulkan function: vkCreateDevice\n");
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	CHECK(p_vkCreateDevice(pdev, &dci, NULL, &dev), "vkCreateDevice");

	VkQueue queue = VK_NULL_HANDLE;
	p_vkGetDeviceQueue(dev, qfam, 0, &queue);

	/* FASE 6 */
	if (load_device_funcs(dev)) {
		p_vkDestroyDevice(dev, NULL);
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}

	/* --- resources --- */
	FILE *f = fopen(shader_path, "rb");
	if (!f) {
		fprintf(stderr, "Cannot open shader: %s\n", shader_path);
		p_vkDestroyDevice(dev, NULL);
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	fseek(f, 0, SEEK_END);
	long sz = ftell(f);
	fseek(f, 0, SEEK_SET);
	uint32_t *code = malloc((size_t)sz);
	if (!code || fread(code, 1, (size_t)sz, f) != (size_t)sz) {
		fprintf(stderr, "Cannot read shader: %s\n", shader_path);
		fclose(f);
		free(code);
		p_vkDestroyDevice(dev, NULL);
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	fclose(f);

	VkBufferCreateInfo bci = { VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO };
	bci.size = 4;
	bci.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
	bci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
	VkBuffer out_buf = VK_NULL_HANDLE;
	CHECK(p_vkCreateBuffer(dev, &bci, NULL, &out_buf), "vkCreateBuffer");

	VkMemoryRequirements mr = { 0 };
	p_vkGetBufferMemoryRequirements(dev, out_buf, &mr);

	VkMemoryAllocateInfo mai = { VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
	mai.allocationSize = mr.size;
	mai.memoryTypeIndex = find_memory_type(&mem_props,
		VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
	if (mai.memoryTypeIndex == UINT32_MAX) {
		fprintf(stderr, "No suitable memory type found\n");
		free(code);
		p_vkDestroyDevice(dev, NULL);
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	VkDeviceMemory out_mem = VK_NULL_HANDLE;
	CHECK(p_vkAllocateMemory(dev, &mai, NULL, &out_mem), "vkAllocateMemory");
	CHECK(p_vkBindBufferMemory(dev, out_buf, out_mem, 0), "vkBindBufferMemory");

	void *mapped = NULL;
	CHECK(p_vkMapMemory(dev, out_mem, 0, 4, 0, &mapped), "vkMapMemory");
	memset(mapped, 0, 4); /* PURGA A CERO: el 42 solo puede venir del dispatch */
	p_vkUnmapMemory(dev, out_mem);

	VkDescriptorSetLayoutBinding b = { 0 };
	b.binding = 0;
	b.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
	b.descriptorCount = 1;
	b.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;

	VkDescriptorSetLayoutCreateInfo dslci = { VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO };
	dslci.bindingCount = 1;
	dslci.pBindings = &b;
	VkDescriptorSetLayout dsl = VK_NULL_HANDLE;
	CHECK(p_vkCreateDescriptorSetLayout(dev, &dslci, NULL, &dsl),
	      "vkCreateDescriptorSetLayout");

	VkPipelineLayoutCreateInfo plci = { VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO };
	plci.setLayoutCount = 1;
	plci.pSetLayouts = &dsl;
	VkPipelineLayout pl_layout = VK_NULL_HANDLE;
	CHECK(p_vkCreatePipelineLayout(dev, &plci, NULL, &pl_layout),
	      "vkCreatePipelineLayout");

	VkShaderModuleCreateInfo smci = { VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO };
	smci.codeSize = (size_t)sz;
	smci.pCode = code;
	VkShaderModule shader_mod = VK_NULL_HANDLE;
	CHECK(p_vkCreateShaderModule(dev, &smci, NULL, &shader_mod),
	      "vkCreateShaderModule");
	printf("Shader module created.\n");

	VkComputePipelineCreateInfo cpi = { VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO };
	cpi.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
	cpi.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
	cpi.stage.module = shader_mod;
	cpi.stage.pName = "main";
	cpi.layout = pl_layout;
	VkPipeline pipeline = VK_NULL_HANDLE;
	CHECK(p_vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpi, NULL, &pipeline),
	      "vkCreateComputePipelines");
	printf("Compute pipeline created.\n");

	VkDescriptorPoolSize ps = { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1 };
	VkDescriptorPoolCreateInfo dpci = { VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO };
	dpci.maxSets = 1;
	dpci.poolSizeCount = 1;
	dpci.pPoolSizes = &ps;
	VkDescriptorPool dpool = VK_NULL_HANDLE;
	CHECK(p_vkCreateDescriptorPool(dev, &dpci, NULL, &dpool),
	      "vkCreateDescriptorPool");

	VkDescriptorSetAllocateInfo dsai = { VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO };
	dsai.descriptorPool = dpool;
	dsai.descriptorSetCount = 1;
	dsai.pSetLayouts = &dsl;
	VkDescriptorSet dset = VK_NULL_HANDLE;
	CHECK(p_vkAllocateDescriptorSets(dev, &dsai, &dset),
	      "vkAllocateDescriptorSets");

	VkDescriptorBufferInfo dbi = { out_buf, 0, 4 };
	VkWriteDescriptorSet w = { VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET };
	w.dstSet = dset;
	w.dstBinding = 0;
	w.descriptorCount = 1;
	w.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
	w.pBufferInfo = &dbi;
	p_vkUpdateDescriptorSets(dev, 1, &w, 0, NULL);

	VkCommandPoolCreateInfo cpci = { VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO };
	cpci.queueFamilyIndex = qfam;
	cpci.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT |
	             VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
	VkCommandPool cmd_pool = VK_NULL_HANDLE;
	CHECK(p_vkCreateCommandPool(dev, &cpci, NULL, &cmd_pool),
	      "vkCreateCommandPool");

	VkFenceCreateInfo fci = { VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
	VkFence fence = VK_NULL_HANDLE;
	CHECK(p_vkCreateFence(dev, &fci, NULL, &fence), "vkCreateFence");

	/* dispatch #1 (calentamiento) + #2 (medición) */
	if (run_dispatch(dev, queue, qfam, dset, pl_layout, pipeline, shader_mod,
	                 cmd_pool, out_buf, fence))
		return 1;
	printf("Command buffer recorded (dispatch 1x1x1).\n");

	/* lectura */
	CHECK(p_vkMapMemory(dev, out_mem, 0, 4, 0, &mapped), "vkMapMemory");
	uint32_t observed = *(uint32_t *)mapped;
	p_vkUnmapMemory(dev, out_mem);

	uint32_t expected = EXPECTED_VALUE; /* literal independiente en el código */
	printf("Expected output: %u\n", expected);
	printf("Observed output: %u\n", observed);
	if (observed != expected) {
		fprintf(stderr, "RESULT: FAIL \n");
		return 1;
	}
	printf("RESULT: PASS \n");
	return 0;
}
