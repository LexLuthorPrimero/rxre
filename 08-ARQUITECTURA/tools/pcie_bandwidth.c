/* BANCO DE ANCHO DE BANDA host <-> dispositivo sobre el enlace PCIe.
 *
 * PREGUNTA: la cadena de 258 -> 284 -> 285 afirma que el techo del enlace es 2,000 GB/s,
 * y lo deriva de cuatro campos de sysfs (current_link_speed = 5,0 GT/s,
 * current_link_width = 4) mas una regla de codificacion (8b/10b). Ningun numero de esa
 * cadena se ha medido jamas. Este banco lo mide.
 *
 * POR QUE OTRO BINARIO y no un modo de vcp: vcp mide tiempos de shader y su layout de dos
 * regiones disjuntas esta validado con cuatro controles. Anadirle un camino de copia
 * mezclaría dos preguntas en un instrumento que ya no se puede tocar sin invalidar lo
 * medido con el. Este banco no necesita pipeline, ni descriptors, ni specialization
 * constants: solo dos buffers y vkCmdCopyBuffer.
 *
 * CONFUNDERS que este archivo controla explicitamente:
 *   - lado del dispositivo: DEVICE_LOCAL (VRAM). Si fuera HOST_VISIBLE, el "lado del
 *     dispositivo" seria ya RAM accesible por la BAR y la copia no cruzaria el enlace.
 *   - el lado del host: HOST_VISIBLE|HOST_COHERENT, obligatorio para que vkCmdCopyBuffer
 *     sirva y para que el host pueda verificar el resultado.
 *   - tamanho multiplo de 4096: una copia parcial de pagina pagaria el coste de
 *     traduction por una fraccion de los bytes, y el ancho de banda saldria inflado.
 *   - calentamiento antes de cronometrar: el enlace y las paginas necesitan uso previo.
 *   - control de contenido: se verifica el patron tras la copia en las DOS direcciones.
 *     Un banco que solo mide tiempo no distingue "copio" de "no copie".
 *
 * USO:  ./pciebw [bytes_maximo] [muestras_por_punto]
 * BUILD: gcc -O2 -Wall -Wextra -o pciebw pcie_bandwidth.c -lvulkan
 */

#define _GNU_SOURCE
#include <vulkan/vulkan.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define TARGET_VENDOR 0x1002u
#define TARGET_DEVICE 0x699Fu

/* El patron. NO puede ser un valor constante: si lo fuera, un buffer que no se copio
 * devolveria el patron y el control pasaria sin que hubiera transferencia. */
#define PATRON(i) (0x5eed0000u ^ ((uint32_t)(i) * 2654435761u))

#define CHECK(x, msg) do { VkResult _r = (x); if (_r != VK_SUCCESS) { \
    fprintf(stderr, "FALLO %s: VkResult=%d en %s:%d\n", msg, _r, __FILE__, __LINE__); \
    exit(2); } } while (0)

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static uint32_t le32(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    unsigned v = 0;
    if (fscanf(f, "%u", &v) != 1) v = 0;
    fclose(f);
    return v;
}

int main(int argc, char **argv)
{
    VkDeviceSize max_bytes = (argc > 1) ? strtoull(argv[1], NULL, 10) : (256ull << 20);
    int          muestras   = (argc > 2) ? atoi(argv[2]) : 9;
    /* --selfcheck: NO hace la copia D->H. El control de contenido tiene que detectar que
     * el staging se quedo con el valor de invalidacion, y el banco tiene que salir con 4.
     * Es el control del propio banco: sin el, "el control dice ok" no demuestra que el
     * control sea capaz de decir "no". */
    int selfcheck = 0;
    for (int a = 1; a < argc; a++) if (!strcmp(argv[a], "--selfcheck")) selfcheck = 1;
    if (selfcheck) { muestras = 3; max_bytes = 1u << 20; }
    if (max_bytes < (1u << 12)) max_bytes = (1u << 12);
    if (muestras < 3) muestras = 3;

    VkApplicationInfo ai = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO };
    ai.pApplicationName = "pciebw"; ai.apiVersion = VK_API_VERSION_1_1;
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO };
    ici.pApplicationInfo = &ai;
    VkInstance inst; CHECK(vkCreateInstance(&ici, NULL, &inst), "vkCreateInstance");

    uint32_t n = 0; CHECK(vkEnumeratePhysicalDevices(inst, &n, NULL), "enum");
    VkPhysicalDevice *ph = calloc(n, sizeof *ph);
    CHECK(vkEnumeratePhysicalDevices(inst, &n, ph), "enum2");
    VkPhysicalDevice gpu = VK_NULL_HANDLE;
    for (uint32_t i = 0; i < n; i++) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(ph[i], &p);
        printf("  dispositivo[%u] vendor=0x%04x device=0x%04x  %s\n",
               i, p.vendorID, p.deviceID, p.deviceName);
        if (p.vendorID == TARGET_VENDOR && p.deviceID == TARGET_DEVICE) gpu = ph[i];
    }
    if (!gpu) { fprintf(stderr, "ABORTO(5): no se encontro el ASIC objetivo\n"); return 5; }

    VkDeviceQueueCreateInfo qci = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO };
    qci.queueFamilyIndex = 0; qci.queueCount = 1;
    VkDeviceCreateInfo dci = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO };
    dci.queueCreateInfoCount = 1; dci.pQueueCreateInfos = &qci;
    VkDevice dev; CHECK(vkCreateDevice(gpu, &dci, NULL, &dev), "vkCreateDevice");
    VkQueue queue; vkGetDeviceQueue(dev, 0, 0, &queue);

    /* Los cuatro campos de sysfs que sostienen la cadena. Se imprimen porque el numero
     * que produce este banco solo tiene sentido junto a ellos. */
    const char *D = "/sys/bus/pci/devices/0000:01:00.0";
    char cs[160], cw[160], ms[160], mw[160];
    snprintf(cs, sizeof cs, "%s/current_link_speed", D);
    snprintf(cw, sizeof cw, "%s/current_link_width", D);
    snprintf(ms, sizeof ms, "%s/max_link_speed", D);
    snprintf(mw, sizeof mw, "%s/max_link_width", D);
    printf("ENLACE  actual %u x %u   maximo %u x %u   (campos de sysfs, sin root)\n",
           le32(cw), le32(cs), le32(mw), le32(ms));

    /* --- dos buffers del mismo tamano: staging mapeable y buffer del dispositivo --- */
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(gpu, &mp);
    uint32_t hmi = UINT32_MAX, dmi = UINT32_MAX;
    for (uint32_t i = 0; i < mp.memoryTypeCount; i++) {
        VkMemoryPropertyFlags f = mp.memoryTypes[i].propertyFlags;
        if (hmi == UINT32_MAX && (f & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT))
            hmi = i;
        if (dmi == UINT32_MAX && (f & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT) &&
            !(f & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT))
            dmi = i;
    }
    if (hmi == UINT32_MAX || dmi == UINT32_MAX) {
        fprintf(stderr, "ABORTO(5): falta HOST_VISIBLE o DEVICE_LOCAL puro\n"); return 5;
    }
    printf("MEMTIPOS  staging=tipo[%u] flags=0x%08x heap=%u   "
           "dispositivo=tipo[%u] flags=0x%08x heap=%u\n",
           hmi, mp.memoryTypes[hmi].propertyFlags, mp.memoryTypes[hmi].heapIndex,
           dmi, mp.memoryTypes[dmi].propertyFlags, mp.memoryTypes[dmi].heapIndex);

    VkBufferCreateInfo bci = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO };
    bci.size = max_bytes; bci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    bci.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    VkBuffer sbuf, dbuf;
    CHECK(vkCreateBuffer(dev, &bci, NULL, &sbuf), "vkCreateBuffer(stage)");
    CHECK(vkCreateBuffer(dev, &bci, NULL, &dbuf), "vkCreateBuffer(dev)");

    VkMemoryRequirements r1, r2;
    vkGetBufferMemoryRequirements(dev, sbuf, &r1);
    vkGetBufferMemoryRequirements(dev, dbuf, &r2);
    VkMemoryAllocateInfo mai1 = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
    VkMemoryAllocateInfo mai2 = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
    mai1.allocationSize = r1.size; mai1.memoryTypeIndex = hmi;
    mai2.allocationSize = r2.size; mai2.memoryTypeIndex = dmi;
    VkDeviceMemory smem, dmem;
    CHECK(vkAllocateMemory(dev, &mai1, NULL, &smem), "vkAllocateMemory(stage)");
    CHECK(vkAllocateMemory(dev, &mai2, NULL, &dmem), "vkAllocateMemory(dev)");
    CHECK(vkBindBufferMemory(dev, sbuf, smem, 0), "bind(stage)");
    CHECK(vkBindBufferMemory(dev, dbuf, dmem, 0), "bind(dev)");

    void *host = NULL;
    if (vkMapMemory(dev, smem, 0, VK_WHOLE_SIZE, 0, &host) != VK_SUCCESS) {
        fprintf(stderr, "FALLO: no se pudo mapear el staging\n"); return 5;
    }
    /* el patron se escribe una vez, en todo el staging */
    { uint32_t *w = (uint32_t *)host;
      for (VkDeviceSize o = 0; o + 4 <= max_bytes; o += 4) w[o / 4] = PATRON(o / 4); }

    VkCommandPoolCreateInfo cpci = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO };
    cpci.queueFamilyIndex = 0;
    VkCommandPool pool; CHECK(vkCreateCommandPool(dev, &cpci, NULL, &pool), "vkCreateCommandPool");
    VkCommandBufferAllocateInfo cbai = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO };
    cbai.commandPool = pool; cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; cbai.commandBufferCount = 1;
    VkCommandBuffer cmd; CHECK(vkAllocateCommandBuffers(dev, &cbai, &cmd), "alloc(cmd)");
    VkFenceCreateInfo fci = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    VkFence fence; CHECK(vkCreateFence(dev, &fci, NULL, &fence), "vkCreateFence");

    VkSubmitInfo si = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO };
    si.commandBufferCount = 1; si.pCommandBuffers = &cmd;

    printf("\n");
    printf("  %-12s %-14s %-14s %-14s %-8s\n",
           "bytes", "h->d GB/s", "d->h GB/s", "techo GB/s", "control");
    printf("  %-12s %-14s %-14s %-14s %-8s\n",
           "------------", "--------------", "--------------", "--------------", "--------");

    /* Techo derivado de los campos leidos: GT/s x lanes x 8/10 / 8. Se calcula aqui y no
     * se copia de 258, para que el banco no dependa de una nota previa. */
    /* le32 lee un entero: de "5.0 GT/s PCIe" saca 5, o sea GT/s. El ancho es un entero
     * de lanes. Con eso, GB/s = GT/s x lanes x (payload/total) / 8, porque GT/s son 1e9
     * bit/s y /8 pasa a bytes. En la primera version dividia ademas por 1e9 y salia 0. */
    double gt_s = (double)le32(cs);
    double lanes = (double)le32(cw);
    double techo = gt_s * lanes * ((gt_s >= 8.0) ? (128.0 / 130.0) : (8.0 / 10.0)) / 8.0;

    int exit_code = 0;
    for (VkDeviceSize sz = 4096; sz <= max_bytes; sz *= 4) {
        VkBufferCopy cp = { .srcOffset = 0, .dstOffset = 0, .size = sz };
        /* Dos command buffers, H->D y D->H. Se registran una vez y se reenvian, asi que
         * NO pueden llevar ONE_TIME_SUBMIT_BIT, que declara el buffer de un solo uso.
         * Y el array se construye DESPUES de que c2 tenga valor: en el primer intento lo
         * construi antes de asignarlo y el banco Segmentation Fault. */
        VkCommandBuffer c2 = VK_NULL_HANDLE;
        CHECK(vkAllocateCommandBuffers(dev, &cbai, &c2), "alloc(cmd2)");
        VkCommandBuffer cb[2] = { cmd, c2 };
        VkCommandBufferBeginInfo bi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
        bi.flags = VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT;

        CHECK(vkBeginCommandBuffer(cb[0], &bi), "begin(H->D)");
        vkCmdCopyBuffer(cb[0], sbuf, dbuf, 1, &cp);
        CHECK(vkEndCommandBuffer(cb[0]), "end(H->D)");
        CHECK(vkBeginCommandBuffer(cb[1], &bi), "begin(D->H)");
        vkCmdCopyBuffer(cb[1], dbuf, sbuf, 1, &cp);
        CHECK(vkEndCommandBuffer(cb[1]), "end(D->H)");

        double t[2] = { 0, 0 };
        int    valido = 1;
        for (int dir = 0; dir < 2; dir++) {
            /* calentamiento: enlace y paginas en uso antes de medir */
            for (int w = 0; w < 3; w++) {
                si.pCommandBuffers = &cb[dir];
                CHECK(vkResetFences(dev, 1, &fence), "reset(w)");
                CHECK(vkQueueSubmit(queue, 1, &si, fence), "submit(w)");
                CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "wait(w)");
            }
            double mejor = 1e30, suma = 0; int usados = 0;
            for (int r = 0; r < muestras; r++) {
                double a = now_s();
                CHECK(vkResetFences(dev, 1, &fence), "reset");
                CHECK(vkQueueSubmit(queue, 1, &si, fence), "submit");
                CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "wait");
                double b = now_s();
                double dt = b - a;
                if (dt > 0) { if (dt < mejor) mejor = dt; suma += dt; usados++; }
            }
            /* mediana aproximada por la minima, que es el mejor estimador del ancho de
             * banda porque el ruido solo puede alargar el tiempo, no acortarlo. Se reporta
             * tambien el cociente minimo/medio para que la dispersion sea visible. */
            double prom = usados ? suma / usados : 0;
            t[dir] = (mejor < 1e29 && prom > 0) ? mejor : prom;
            printf("  dir=%d sz=%-10llu  min=%.9f  medio=%.9f  min/medio=%.3f\n",
                   dir, (unsigned long long)sz, mejor, prom, mejor / (prom > 0 ? prom : 1));
        }

        /* CONTROL DE CONTENIDO: tras D->H el staging debe traer lo que el dispositivo tenia.
         * Si la copia no ocurrio, el staging conserva lo que el host escribio, que es el
         * mismo patron, y el control NO lo detectaria. Por eso el patron se invalida en el
         * staging ANTES de copiar D->H: si la copia funciona vuelve el patron, y si no
         * vuelve el valor de invalidacion. Ese es el discriminante de las dos salidas. */
        { uint32_t *w = (uint32_t *)host;
          for (VkDeviceSize o = 0; o + 4 <= sz; o += 4) w[o / 4] = 0xDEADBEEFu; }
        if (!selfcheck) {
            si.pCommandBuffers = &cb[1];
            CHECK(vkResetFences(dev, 1, &fence), "reset(ctrl)");
            CHECK(vkQueueSubmit(queue, 1, &si, fence), "submit(ctrl)");
            CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "wait(ctrl)");
        }
        { uint32_t *w = (uint32_t *)host;
          VkDeviceSize malas = 0;
          for (VkDeviceSize o = 0; o + 4 <= sz; o += 4)
              if (w[o / 4] != PATRON(o / 4)) malas++;
          if (malas) { fprintf(stderr, "  CONTROL FALLIDO en sz=%llu: %llu de %llu palabras\n",
                               (unsigned long long)sz, (unsigned long long)malas,
                               (unsigned long long)(sz / 4)); valido = 0; exit_code = 4; }
        }

        double hd = t[0] > 0 ? (double)sz / t[0] / 1e9 : 0;
        double dh = t[1] > 0 ? (double)sz / t[1] / 1e9 : 0;
        printf("  %-12llu %-14.3f %-14.3f %-14.3f %-8s\n",
               (unsigned long long)sz, hd, dh, techo, valido ? "ok" : "MAL");
        vkFreeCommandBuffers(dev, pool, 1, &c2);
    }

    printf("\nTECHO    derivado de sysfs = %.3f GB/s   (no copiado de 258)\n", techo);
    printf("NOTA     el minimo es el mejor estimador del ancho de banda: el ruido de sistema\n");
    printf("         solo puede alargar el tiempo medido, nunca acortarlo.\n");
    return exit_code;
}