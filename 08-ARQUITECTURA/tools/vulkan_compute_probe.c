/* vulkan_compute_probe.c — carga de cómputo Vulkan headless sobre el ASIC objetivo.
 *
 * POR QUÉ EXISTE. Es la capacidad que falta para toda la parte medible de §H. Con ella se
 * responde la pregunta de §52 (qué limita esta GPU) y se puede cerrar el discriminante
 * 258-2, que exige una carga que eleve mclk y sclk.
 *
 * REGLA DE SEGURIDAD QUE IMPONE ESTE FICHERO. El sistema tiene llvmpipe como dispositivo
 * Vulkan de tipo CPU. Una herramienta de benchmark que degrade a llvmpipe mid[e] el
 * procesador y produce un número plausible y falso. Por eso este programa exige el
 * vendor:device exacto y ABORTA si no lo encuentra. No hay ruta de reserva.
 *
 * NIVEL DE PERMISOS. NIVEL 1: crea una instancia Vulkan y despacha un kernel. No escribe
 * registros de hardware, no toca sysfs, no cambia estado persistente. Sube relojes y consumo,
 * que es la operación normal de la GPU; por eso la duración la fija el llamante y el
 * programa no tiene lazo infinito.
 *
 * BUILD:  gcc -O2 -o vcp vulkan_compute_probe.c -lvulkan
 * USO:    ./vcp [iteraciones_por_item] [items]
 */

#define _GNU_SOURCE
#include <vulkan/vulkan.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stddef.h>
#include <time.h>

/* El ASIC objetivo. vendor:device leido de /sys/bus/pci/devices/0000:01:00.0 */
#define TARGET_VENDOR 0x1002u
#define TARGET_DEVICE 0x699Fu

#define PATRON_INICIAL 0x5eed1234u
/* La MISMA transformacion que probe.comp, replicada en el host. Si el kernel y esta
 * funcion divergen, el readback lo detecta: por eso estan escritas una al lado de la otra. */
static inline uint32_t paso(uint32_t x) { return x * 1664525u + 1013904223u; }
/* probe.comp hace ademas, DESPUES del bucle:  a ^= (a >> 13);
 * sin esta linea el modelo del host rechaza un kernel que funciona. El control solo
 * es valido si replica el shader completo, no una parte. */
static inline uint32_t cierre(uint32_t x) { return x ^ (x >> 13); }
/* El MISMO hash que occ.comp, byte a byte. Si el compilador de shader y este fichero
 * divergen, el readback aborta con 4: por eso estan escritos uno al lado del otro y por eso
 * el control del banco es del kernel, no del primero que se escribio. */
static inline uint32_t occ_hash(uint32_t x)
{
    x ^= x >> 16; x *= 0x7feb352du;
    x ^= x >> 15; x *= 0x846ca68bu;
    x ^= x >> 16;
    return x;
}

/* Modelo de chain.comp, el kernel del discriminante de 278. Se replica aqui porque el
 * control tiene que ser del kernel que se ejecuta: con el modelo de occ.comp, chain.comp
 * abortaria con 4 y no distinguiriamos 'modelo equivocado' de 'bucle eliminado'. */
static inline uint32_t chain_model(uint32_t i, uint32_t iters,
                                   uint32_t wsize, uint32_t steps)
{
    uint32_t idx = occ_hash(i + 0x9e3779b9u) % wsize;
    uint32_t acc = 0u;
    for (uint32_t k = 0; k < iters; k++) {
        uint32_t v = PATRON_INICIAL + idx;
        acc = acc * 1664525u + v + 1013904223u;
        idx = acc % wsize;
        /* El % wsize va dentro del bucle, igual que en el shader. Si se deja fuera,
         * idx queda como hash de 32 bits y la lectura siguiente sale del buffer. */
        for (uint32_t s = 0; s < steps; s++) idx = occ_hash(idx) % wsize;
        acc = acc + idx;
    }
    return acc;
}

#define CHECK(x, msg) do { VkResult _r = (x); if (_r != VK_SUCCESS) { \
    fprintf(stderr, "FALLO %s: VkResult=%d en %s:%d\n", msg, _r, __FILE__, __LINE__); \
    exit(2); } } while (0)

/* Codigo GLSL del kernel. compilar con:
 *   glslangValidator -V probe.comp -o probe.spv
 * Un bucle de FMA puro: sin trafico de memoria, mide techo de ALU.
 */
/* Ruta del SPIR-V: argv[3], con probe.spv por defecto. Parametrizable porque cambiar el
 * kernel es lo que cambia lo que se mide; si la ruta fuera fija, cambiar de kernel exigiría
 * tocar el programa, que es el defecto opuesto al que este fichero evita en todas partes. */
static const char *g_spv = "probe.spv";
/* Segunda specialization constant: el numero de cadenas independientes del kernel ALU. */
static uint32_t g_nacc = 8u;
static int g_batch = 1;     /* --batch=M: M despachos en el MISMO command buffer.
                             * Discriminante del coste de envio: si los ~38 us que cuesta un
                             * envio se pagan UNA vez por command buffer, agrupar M
                             * despachos divide esa parte por M. Si se pagaran por
                             * despacho, agrupar no ahorra nada. Es la diferencia entre
                             * "el envio es un coste" y "el envio es un coste por
                             * comando", y son cosas distintas para un driver propio. */
static int g_tex = 0;      /* --tex: la cadena lee de una VkImage, no del storage buffer.
                             * Discriminante de 282-1: una imagen tiene su propia ruta de
                             * texel, y si esa ruta difiere de la del buffer, la diferencia
                             * localiza el camino. Con la bandera apagada no cambia nada:
                             * es el mismo banco con un binding menos. */
static int g_control = 1;   /* comparar con el modelo del host; 0 solo con --nocontrol */
/* Working set en dwords, argc[5]. 0 = igual a items. Existe para DESACOPLAR el buffer del
 * despacho: con pocos hilos (pocos items) y conjunto de trabajo grande (muchos wsize) es
 * donde la latencia no se puede ocultar. Si buffer y dispatch fueran la misma magnitud, los
 * dos requisitos serian incompatibles por construccion. */
static uint32_t g_wsize = 0u;
/* Tercera specialization constant, argv[7]: pasos de hash por iteracion en chain.comp.
 * Existe para el discriminante de 278: si el coste marginal escala con STEPS, el hardware
 * ejecuta la cadena; si no, el bucle se optimiza. Con una sola constant no se puede
 * separar 'trabajo real' de 'trabajo eliminado'. */
static uint32_t g_steps = 1u;
/* Tipo de memoria del buffer del kernel, argv[8] o --mem=: 0=DEVICE_LOCAL (VRAM),
 * 1=HOST_VISIBLE (RAM), 2=ambos si existe. Discriminante de 282: el acceso del shader
 * tiene que distinguir VRAM de RAM, y si no distingue, la ruta de lectura no es la que
 * se cree. */
static int g_mem = 0;
/* --rep=N: repite el envio cronometrado N veces dentro de la misma region.
 * Sirve para separar el coste POR ENVIO de un calentamiento UNICO: si las
 * repeticiones 2..N cuestan menos que la primera, el interceptor de la recta
 * t = a + b*ITERS no es un coste de envio sino un transitorio. */
static int g_rep = 1;
/* indice del tipo de memoria del staging, impreso para comparar con el del kernel */
static uint32_t hmi_dbg = UINT32_MAX;
/* Que modelo del host se usa para el readback, argv[6]: 0 = paso/cierre (probe.comp),
 * 1 = cadena dependiente (occ.comp). Un banco con UN solo modelo no puede validar un
 * segundo kernel: el control tiene que ser del kernel que se ejecuta, no del primero. */
static int g_model = 0;
/* Modo del indice en div.comp, argv[9]: 0=modulo, 1=mascara. El discriminante de 286. */
static int g_mode = 0;
/* page.comp: 0=indice contiguo, 1=indice paginado. Discriminante cache contra TLB. */
static int g_page = 0;
/* reuse.comp: direcciones por hilo = distancia de reutilizacion. constant_id=2. */
static uint32_t g_blk = 16u;
/* spread.comp: separacion de bloques dentro de un wavefront. constant_id=4. */
static uint32_t g_grp = 1u;
/* lane.comp: 0 = difusion (todos los carriles misma direccion), 1 = disperso. */
static uint32_t g_lane = 1u;
/* Copia exacta del hash de lane.comp. El modelo del host tiene que hacer la MISMA
 * cuenta que el shader: si difieren, el control de contenido no distingue un kernel
 * correcto de uno roto, y por eso no puede usarse como prueba del patron. */
static inline uint32_t hash32(uint32_t x) {
    x ^= x >> 16; x *= 0x7feb352du;
    x ^= x >> 15; x *= 0x846ca68bu;
    x ^= x >> 16;
    return x;
}
/* lane.comp: 1 = el shader escribe la ultima direccion leida, en vez de la cadena. */
static uint32_t g_addr = 0u;
/* lane.comp: dwords que avanza el reparto CONTIGUO por vuelta. constant_id=4. */
static uint32_t g_stride = 262144u;
/* lane.comp: hasta donde se esparcen las direcciones, dentro de un biffer mayor.
 * 0 = todo el biffer. Separate el TAMANO RESERVADO del SEPARADO. constant_id=5. */
static uint32_t g_sub = 0u;

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static uint32_t read32(const char *path)
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
    uint32_t iters = (argc > 1) ? (uint32_t)strtoul(argv[1], NULL, 10) : 64;
    uint32_t items = (argc > 2) ? (uint32_t)strtoul(argv[2], NULL, 10) : (1u << 20);
    if (argc > 3) g_spv = argv[3];
    if (argc > 4) g_nacc = (uint32_t)strtoul(argv[4], NULL, 10);
    if (argc > 5) g_wsize = (uint32_t)strtoul(argv[5], NULL, 10);
    if (argc > 6) g_model = (int)strtoul(argv[6], NULL, 10);
    if (argc > 7) g_steps = (uint32_t)strtoul(argv[7], NULL, 10);
    if (argc > 9) g_mode = (int)strtoul(argv[9], NULL, 10);
    if (argc > 10) g_blk = (uint32_t)strtoul(argv[10], NULL, 10);
    if (argc > 11) g_grp = (uint32_t)strtoul(argv[11], NULL, 10);
    if (argc > 12) g_lane = (uint32_t)strtoul(argv[12], NULL, 10);
    if (argc > 13) g_addr = (uint32_t)strtoul(argv[13], NULL, 10);
    if (argc > 14) g_stride = (uint32_t)strtoul(argv[14], NULL, 10);
    if (argc > 15) g_sub = (uint32_t)strtoul(argv[15], NULL, 10);
    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "--rep=", 6)) continue;
            /* Un valor no pedido tiene que ser ERROR, no 0 silencioso. El flag --mem murio
         * justo por eso: strtoul("host") es 0, --mem=host caia al valor por defecto y
         * ninguna corrida aviso. Una bandera que no entiende el programa es un fallo. */
        if (!isdigit((unsigned char)argv[i][6])) {
            fprintf(stderr, "--rep solo admite un numero entero positivo; '%s' no lo es\n",
                    argv[i] + 6);
            return 2;
        }
        g_rep = (int)strtoul(argv[i] + 6, NULL, 10);
        if (g_rep < 1) {
            fprintf(stderr, "--rep=%d no tiene sentido\n", g_rep);
            return 2;
        }
    }
    { int i; for (i = 1; i < argc; i++) {
        /* --tex va AQUI y no en el bucle de --rep. Ahi hay un continue que descarta
     * todo lo que no empiece por "--rep=", asi que una bandera puesta ahi es
     * codigo muerto que ademas parece viva. Es el mismo defecto que se llevo por
     * delante la linea del despacho en 607: una instruccion en el sitio
     * equivocado no da error, da silencio. */
    if (!strcmp(argv[i], "--nocontrol")) g_control = 0;
    else if (!strcmp(argv[i], "--tex")) g_tex = 1;
    else if (!strncmp(argv[i], "--batch=", 8)) g_batch = (int)strtoul(argv[i] + 8, NULL, 10);
      } }
    if (!iters || !items) { fprintf(stderr, "iter/items deben ser > 0\n"); return 2; }
    if (!g_nacc) g_nacc = 1;
    if (!g_wsize) g_wsize = items;
    /* El conjunto de trabajo no puede ser menor que el despacho: una palabra escrita fuera
     * del buffer es corrupcion de memoria, no un resultado raro. Fallar aqui y no en la GPU. */
    if (g_wsize < items) {
        fprintf(stderr, "wsize (%u) < items (%u): el dispatch escribe fuera del buffer\n",
                g_wsize, items);
        return 2;
    }
    /* WSIZE (constant_id=1) delimita la REGION DE LECTURA y tiene que ser al menos items de
     * ancho, porque los kernels leen d[i] para todo i < items. Si WSIZE < items, la escritura
     * en d[WSIZE + i] cae dentro de la region que el propio kernel esta leyendo y se reproduce
     * la carrera que 283 elimino. Detectado al validar probe.comp con WSIZE=8 e items=256. */
    if (g_model == 7) {
        /* El buffer tiene lectura [0, g_wsize) con el patron y escritura
         * [g_wsize, g_wsize + items), con bytes = (g_wsize + items) * 4. Los shaders
         * escriben en d[WSIZE + i] y el readback lee desde d[g_wsize]. Solo coinciden si
         * WSIZE == wsize, y para los modelos 0-4 eso nunca se exigio: se cumplia por
         * costumbre, al pasar los mismos numeros en argv[4] y argv[5]. Es un invariante
         * del instrumento, no del shader, asi que va aqui y no en el GLSL. */
        if (g_nacc != g_wsize) {
            fprintf(stderr, "lane.comp: WSIZE (%u) != wsize (%u); el shader escribiria en "
                            "d[WSIZE+i] y el readback leeria desde d[wsize]\n", g_nacc, g_wsize);
            return 2;
        }
        if (g_lane > 2u) {
            fprintf(stderr, "lane.comp: LANEMODE (%u) solo admite 0 (difusion), "
                            "1 (disperso) o 2 (contiguo)\n", g_lane);
            return 2;
        }
        /* STRIDE son los dwords que avanza CADA HILO por vuelta, no el desplazamiento de un
         * grupo, asi que no hay ninguna relacion con WSIZE: todas las direcciones se reducen
         * modulo WSIZE y son validas. Lo que si importa para que el modo siga siendo CONTIGUO
         * es que el paso sea multiplo de 64, para que los bloques de 64 carriles de vueltas
         * sucesivas no se entrelacen. Y que el patron sea el que dice, eso lo comprueba el
         * control de entropia, no este invariante. */
        if (g_lane == 2u && (g_stride < 64u || (g_stride % 64u) != 0u)) {
            fprintf(stderr, "lane.comp: STRIDE (%u) tiene que ser multiplo de 64 y al menos 64; "
                            "con otro valor el reparto CONTIGUO deja de serlo\n", g_stride);
            return 2;
        }
        if (g_sub != 0u && (g_sub > g_nacc || g_sub % 64u) != 0u) {
            fprintf(stderr, "lane.comp: SUBRANGE (%u) tiene que ser multiplo de 64 y no "
                            "mayor que WSIZE (%u)\n", g_sub, g_nacc);
            return 2;
        }
        if (g_addr > 1u) {
            fprintf(stderr, "lane.comp: ADDR (%u) solo admite 0 o 1\n", g_addr);
            return 2;
        }
    }
    if (g_model == 6) {
        /* spread.comp necesita WSIZE == items * B, como reuse.comp: el numero de bloques
         * es items y el ultimo bloque tiene que caber en la region de lectura. */
        uint64_t need6 = (uint64_t)items * g_blk;
        if (need6 != (uint64_t)g_nacc || need6 > (uint64_t)g_wsize) {
            fprintf(stderr, "spread.comp: WSIZE (%u) != items x B (%llu), o excede wsize (%u)\n",
                    g_nacc, (unsigned long long)need6, g_wsize);
            return 2;
        }
        /* GRP debe ser coprimo con 64: si no, (i%64)*GRP mod 64 no es una permutacion y
         * varios hilos comparten bloque, que es un experimento distinto. */
        if (g_grp == 0 || (g_grp % 2u) == 0 || (g_grp & 63u) == 0) {
            fprintf(stderr, "spread.comp: GRP (%u) no es coprimo con 64; no seria una "
                            "permutacion de los bloques\n", g_grp);
            return 2;
        }
    }
    if (g_model == 5) {
        /* reuse.comp exige WSIZE == items * blk, porque el bloque del hilo i empieza en
         * i*blk y la region de escritura en WSIZE+i. Si no cuadra, el bloque del ultimo
         * hilo se sale de la region de lectura. */
        uint64_t need = (uint64_t)items * g_blk;
        if (need != (uint64_t)g_nacc || need > (uint64_t)g_wsize) {
            fprintf(stderr, "reuse.comp: WSIZE (%u) != items x blk (%llu), o excede wsize (%u)\n",
                    g_nacc, (unsigned long long)need, g_wsize);
            return 2;
        }
    }
    if (g_nacc < items) {
        fprintf(stderr, "WSIZE (%u) < items (%u): la escritura en d[WSIZE+i] cae dentro de la"
                        " region de lectura; el control no seria valido\n", g_nacc, items);
        return 2;
    }

    /* --- instancia, sin capas, sin WSI --- */
    VkApplicationInfo ai = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO };
    ai.pApplicationName = "vcp"; ai.apiVersion = VK_API_VERSION_1_1;
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO };
    ici.pApplicationInfo = &ai;
    VkInstance inst; CHECK(vkCreateInstance(&ici, NULL, &inst), "vkCreateInstance");

    uint32_t nd = 0; CHECK(vkEnumeratePhysicalDevices(inst, &nd, NULL), "enumPhysDev");
    if (!nd) { fprintf(stderr, "FALLO: no hay dispositivos fisicos\n"); return 2; }
    VkPhysicalDevice *devs = calloc(nd, sizeof *devs);
    CHECK(vkEnumeratePhysicalDevices(inst, &nd, devs), "enumPhysDev2");

    /* --- seleccion estricta del ASIC objetivo --- */
    VkPhysicalDevice gpu = VK_NULL_HANDLE;
    VkPhysicalDeviceProperties props; memset(&props, 0, sizeof props);
    int idx = -1;
    for (uint32_t i = 0; i < nd; i++) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(devs[i], &p);
        printf("  dispositivo[%u] vendor=0x%04x device=0x%04x  %s  [%s]\n",
               i, p.vendorID, p.deviceID, p.deviceName,
               p.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU ? "TIPO CPU" :
               p.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU ? "DISCRETA" :
               p.deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU ? "INTEGRADA" : "OTRO");
        if (p.vendorID == TARGET_VENDOR && p.deviceID == TARGET_DEVICE) { gpu = devs[i]; props = p; idx = (int)i; }
    }
    if (gpu == VK_NULL_HANDLE) {
        fprintf(stderr, "ABORTO: no se encontro %04x:%04x. Sin fallback a otro dispositivo:\n"
                        "  un resultado en llvmpipe mediria la CPU, no la GPU.\n",
                TARGET_VENDOR, TARGET_DEVICE);
        return 3;
    }
    printf("SELECCIONADO indice=%d  %s\n", idx, props.deviceName);
    if (props.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU) {
        fprintf(stderr, "ABORTO: el dispositivo seleccionado es de TIPO CPU\n"); return 3;
    }

    /* Las propiedades de la familia de cola NO se leian antes. La llamada era
     *
     *     uint32_t qf = 0; vkGetPhysicalDeviceQueueFamilyProperties(gpu, &qf, NULL);
     *
     * que pasa el PUNTERO donde la funcion espera el CONTADOR, y NULL donde espera el
     * puntero a propiedades. Escribia en qf el numero de familias y no leia ninguna. El
     * banco usaba la familia 0 a ciegas, y le salia bien porque este dispositivo tiene una
     * sola. Pero en cuanto hay que PREGUNTARLE algo a la familia -- y lo que hace falta son
     * las marcas de tiempo -- hay que leerla de verdad, asi que se lee.
     */
    uint32_t nqf = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(gpu, &nqf, NULL);
    if (!nqf) { fprintf(stderr, "FALLO: sin familias de cola\n"); return 2; }
    VkQueueFamilyProperties *qfp = (VkQueueFamilyProperties *)calloc(nqf, sizeof(*qfp));
    if (!qfp) { fprintf(stderr, "FALLO: sin memoria para las familias de cola\n"); return 5; }
    vkGetPhysicalDeviceQueueFamilyProperties(gpu, &nqf, qfp);
    uint32_t qf = UINT32_MAX;
    for (uint32_t k = 0; k < nqf; k++)
       if ((qfp[k].queueFlags & VK_QUEUE_GRAPHICS_BIT) &&
           (qfp[k].queueFlags & VK_QUEUE_COMPUTE_BIT)) { qf = k; break; }
    if (qf == UINT32_MAX) {
       fprintf(stderr, "ABORTO(2): ninguna familia de cola tiene GRAPHICS y COMPUTE\n");
       for (uint32_t k = 0; k < nqf; k++)
         fprintf(stderr, "  familia[%u] flags=0x%08x count=%u\n", k,
                     qfp[k].queueFlags, qfp[k].queueCount);
       return 2;
    }
    printf("COLA      familias=%u elegida=%u flags=0x%08x\n", nqf, qf, qfp[qf].queueFlags);

    /* Las marcas de tiempo son la unica forma de distinguir "la GPU no hizo nada" de
     * "la GPU hizo algo mal". Sin ellas, un envio fallido y un kernel que calcula mal se
     * ven IGUALES: un buffer que no cambio. Y --mem=2 se presento justamente asi, con el
     * veneno de memoria sin inicializar de Mesa, y no habia forma de saber si el comando
     * se habia ejecutado.
     *
     * timestampValidBits puede ser 0, que significa que no hay marcas. Se consulta, se
     * guarda, y si no hay el banco lo DICE y sigue funcionando: una capacidad ausente no
     * puede ser un ABORTO en un banco que ya tiene trabajo. */
    float ts_period = 0.0f;
    int ts_hay = 0;
    /* timestampValidBits vive en la FAMILIA de cola; timestampPeriod vive en los LIMITES
     * del dispositivo. No estan en la misma estructura, y confundirlos no compila. */
    if (qfp[qf].timestampValidBits > 0) { ts_period = props.limits.timestampPeriod; ts_hay = 1; }
    printf("TIMESTAMP timestampValidBits=%u timestampPeriod=%.3f ns  %s\n",
           qfp[qf].timestampValidBits, ts_period, ts_hay ? "utilizable" : "NO utilizable");
    fflush(stdout);

    float prio = 1.0f;
    VkDeviceQueueCreateInfo qci = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO };
    qci.queueFamilyIndex = 0; qci.queueCount = 1; qci.pQueuePriorities = &prio;
    VkDeviceCreateInfo dci = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO };
    dci.queueCreateInfoCount = 1; dci.pQueueCreateInfos = &qci;
    VkDevice dev; CHECK(vkCreateDevice(gpu, &dci, NULL, &dev), "vkCreateDevice");
    VkQueue queue; vkGetDeviceQueue(dev, 0, 0, &queue);

    /* --- shader --- */
    FILE *f = fopen(g_spv, "rb");
    if (!f) { fprintf(stderr, "FALLO: no existe %s (compilar el shader primero)\n", g_spv); return 2; }
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    if (sz <= 0) { fprintf(stderr, "FALLO: %s esta vacio\n", g_spv); return 2; }
    void *code = malloc((size_t)sz);
    if (fread(code, 1, (size_t)sz, f) != (size_t)sz) { fprintf(stderr, "FALLO: lectura corta\n"); return 2; }
    fclose(f);

    VkShaderModuleCreateInfo smci = { .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO };
    smci.codeSize = (size_t)sz; smci.pCode = code;
    VkShaderModule sm; CHECK(vkCreateShaderModule(dev, &smci, NULL, &sm), "vkCreateShaderModule");

    /* --- descriptor pool: un storage buffer --- */
    /* Binding 0 siempre: el storage buffer, que es a la vez region de lectura y de
     * escritura. Binding 1 solo con --tex: la imagen de la que lee la cadena. Que el
     * shader use usampler2D y no uimage2D decide cual de los dos es este binding, y por
     * eso el layout tiene que coincidir con lo que el shader pidio, no con lo que
     * convenga: un layout que no coincide no da un error claro, da basura. */
    VkDescriptorSetLayoutBinding bnd[2]; memset(bnd, 0, sizeof(bnd));
    bnd[0].binding = 0; bnd[0].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    bnd[0].descriptorCount = 1; bnd[0].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    uint32_t nbnd = 1;
    if (g_tex) {
       bnd[1].binding = 1; bnd[1].descriptorType = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE;
       bnd[1].descriptorCount = 1; bnd[1].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
       nbnd = 2;
    }
    VkDescriptorSetLayoutCreateInfo dslci = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO };
    dslci.bindingCount = nbnd; dslci.pBindings = bnd;
    VkDescriptorSetLayout dsl;
    CHECK(vkCreateDescriptorSetLayout(dev, &dslci, NULL, &dsl), "vkCreateDescriptorSetLayout");

    VkPipelineLayoutCreateInfo plci = { .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO };
    plci.setLayoutCount = 1; plci.pSetLayouts = &dsl;
    VkPipelineLayout pl; CHECK(vkCreatePipelineLayout(dev, &plci, NULL, &pl), "vkCreatePipelineLayout");

    /* --- specialization: ITERS llega al shader de verdad ---
     * Sin esto, el bucle vive horneado en el SPIR-V y el argumento iters de la linea de
     * comandos solo llegaba al printf: el harness reportaba una configuración que no
     * ejecutaba. Con VkSpecializationInfo el valor reportado ES el valor ejecutado.
     */
        /* constant_id=2 tiene dos significados segun el kernel: STEPS en chain/div,
     * B (direcciones por hilo) en reuse.comp y en spread.comp. Que lo decida el modelo,
     * no el orden de los argumentos: con spec[2] = g_steps, reuse.comp recibia STEPS
     * en B y el control fallaba 0 de 64 sin que el mensaje dijera por que. Repetido en
     * spread.comp, donde el fallo fue el mismo y por el mismo sitio. */
    uint32_t sc2 = (g_model == 5 || g_model == 6) ? g_blk : g_steps;
    uint32_t g_mode_used = g_mode;
if (g_model == 7) { sc2 = g_lane; g_mode_used = g_addr; }
    /* lane.comp: constant_id=2 es LANEMODE y constant_id=3 es ADDR. */
    uint32_t spec[6] = { iters, g_nacc, sc2, g_mode_used,
                         (g_model == 7) ? g_stride : g_grp,
                         (g_model == 7) ? g_sub : g_lane };
    VkSpecializationMapEntry me[6] = {
        { 0, 0, sizeof(uint32_t) },
        /* offset ES el desplazamiento DENTRO de pData, no el offset del campo pData
         * dentro de VkSpecializationInfo. Con sizeof(void*)=8 el valor antiguo era 12 y
         * constant_id=1 leia 8 bytes mas alla del buffer: el driver lo ignoraba y el
         * shader se quedaba con el valor por defecto. probe.comp no lo noto porque su
         * segunda sc no afectaba al resultado que el banco comparaba. */
        { 1, sizeof(uint32_t), sizeof(uint32_t) },
        /* La TERCERA, anadida en 278. Los offsets son 0, 4, 8: los desplazamientos DENTRO
         * de pData, que es lo que pide la especificacion de VkSpecializationMapEntry. */
        { 2, 2 * sizeof(uint32_t), sizeof(uint32_t) },
        { 3, 3 * sizeof(uint32_t), sizeof(uint32_t) },
        { 4, 4 * sizeof(uint32_t), sizeof(uint32_t) },
        { 5, 5 * sizeof(uint32_t), sizeof(uint32_t) },
    };
    /* El numero de entradas TIENE que coincidir con las specialization constants que el
     * shader declara. Mandar entradas para constant_id que el SPIR-V no define no da error:
     * el driver las ignora en silencio y el kernel recibe un valor que nadie pidio. Ya ha
     * pasado dos veces (reuse.comp y spread.comp); aqui se hace explicito con nentries,
     * derivado del modelo, para que el banco no pueda repetirlo. */
    /* lane.comp declara 4 specialization constants (0..3), no 6: 4 y 5 no existen en su
     * SPIR-V y el driver las ignora en silencio. */
    uint32_t nentries = 6u;   /* los 6 ids existen en los ocho shaders */
    VkSpecializationInfo si_info = { .mapEntryCount = (uint32_t)nentries, .pMapEntries = me,
                                      .dataSize = sizeof(spec), .pData = spec };

    VkComputePipelineCreateInfo cpci = { .sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO };
    cpci.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    cpci.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    cpci.stage.module = sm; cpci.stage.pName = "main";
    cpci.stage.pSpecializationInfo = &si_info;
    cpci.layout = pl;
    VkPipeline pipe; CHECK(vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpci, NULL, &pipe), "vkCreateComputePipelines");

    /* --- buffer: g_wsize * 4 bytes. NO items: ver g_wsize. El patron se inicializa en las
     * g_wsize palabras, no en items, porque el kernel recorre todo el conjunto de trabajo. */
    /* El buffer tiene DOS regiones disjuntas: lectura [0, g_wsize) con el patron, y
     * escritura [g_wsize, g_wsize + items) con el resultado del kernel. Antes era una sola
     * region y el kernel leia lo que escribian otros hilos: con ITERS=64 el control fallaba
     * 0 de 40 (282). Disjuntas, la carrera es imposible por construccion. */
    /* Con ADDR=1 lane.comp escribe DOS regiones tras g_wsize: [g_wsize, +items) con la
     * direccion y [g_wsize+items, +2*items) con la cadena. Reservar el doble no cuesta
     * nada y evita que el instrumento tenga que saber que kernel esta en marcha. */
    VkDeviceSize bytes = (VkDeviceSize)(g_wsize + 2u * items) * 4;
    VkDeviceSize off_escritura = (VkDeviceSize)g_wsize * 4;
    VkBufferCreateInfo bci = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO };
    bci.size = bytes; bci.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    bci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VkBuffer buf; CHECK(vkCreateBuffer(dev, &bci, NULL, &buf), "vkCreateBuffer");
    VkMemoryRequirements mr; vkGetBufferMemoryRequirements(dev, buf, &mr);
    /* Seleccion del tipo de memoria del buffer del KERNEL. Tres modos, para el discriminante
     * de 282: si el acceso del shader se resuelve en VRAM, cambiar el tipo de memoria tiene
     * que cambiar el tiempo. Si no cambia, la ruta no es la que creo.
     *   --mem=vram   DEVICE_LOCAL            (lo que hacia siempre: VRAM del ASIC)
     *   --mem=host   HOST_VISIBLE            (RAM del sistema, mapeada)
     *   --mem=both   HOST_VISIBLE|DEVICE_LOCAL (si el driver lo ofrece: BAR o UMA)
     * El staging de lectura SIEMPRE es HOST_VISIBLE, porque tiene que ser mapeable por el
     * host para el readback; el tipo del buffer del kernel es lo que se varia. */
    VkPhysicalDeviceMemoryProperties mprops2; vkGetPhysicalDeviceMemoryProperties(gpu, &mprops2);
    VkMemoryPropertyFlags need = 0;
    if (g_mem == 1)      need = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
    else if (g_mem == 2) need = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;
    else                 need = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;
    uint32_t bits = mr.memoryTypeBits, want = UINT32_MAX;
    for (uint32_t i = 0; i < bits && i < mprops2.memoryTypeCount; i++) {
        if ((mprops2.memoryTypes[i].propertyFlags & need) == need) { want = 1u << i; break; }
    }
    if (want == UINT32_MAX) {
        /* Reportar los tipos que hay, en vez de callar: un discriminante que no puede
         * ejecutarse tiene que decir por que, no devolver un numero inventado. */
        fprintf(stderr, "ABORTO(2): ningun tipo de memoria cumple");
        for (uint32_t i = 0; i < bits && i < mprops2.memoryTypeCount; i++)
            fprintf(stderr, "\n  tipo[%u] flags=0x%08x heap=%u", i,
                    mprops2.memoryTypes[i].propertyFlags, mprops2.memoryTypes[i].heapIndex);
        return 2;
    }
    VkMemoryAllocateInfo mai = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
    mai.allocationSize = mr.size; mai.memoryTypeIndex = want;
    VkDeviceMemory mem; CHECK(vkAllocateMemory(dev, &mai, NULL, &mem), "vkAllocateMemory");
    CHECK(vkBindBufferMemory(dev, buf, mem, 0), "vkBindBufferMemory");


    VkDescriptorPoolSize ps[2];
    ps[0].type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; ps[0].descriptorCount = 1;
    uint32_t nps = 1;
    if (g_tex) { ps[1].type = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE; ps[1].descriptorCount = 1; nps = 2; }
    VkDescriptorPoolCreateInfo dpci = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO };
    dpci.maxSets = 1; dpci.poolSizeCount = nps; dpci.pPoolSizes = ps;
    VkDescriptorPool dp; CHECK(vkCreateDescriptorPool(dev, &dpci, NULL, &dp), "vkCreateDescriptorPool");
    VkDescriptorSetAllocateInfo dsai = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO };
    dsai.descriptorPool = dp; dsai.descriptorSetCount = 1; dsai.pSetLayouts = &dsl;
    VkDescriptorSet ds; CHECK(vkAllocateDescriptorSets(dev, &dsai, &ds), "vkAllocateDescriptorSets");
    /* --- la imagen de la ruta de texel, solo con --tex ------------------
     *
     * Cada decision y su por que:
     *   VK_IMAGE_TILING_LINEAR. Una imagen lineal se rellena con una copia de buffer, que
     *     es lo que hace falta para darle EXACTAMENTE el mismo patron que el storage
     *     buffer. Una imagen teselada exigiria una copia de host a teselas, y con ella
     *     entraria en el experimento una transformacion de disposicion que es
     *     precisamente lo que no se quiere medir.
     *   VK_FORMAT_R32_UINT. Un uint por texel: 4 B por acceso, los mismos 4 B que
     *     d[idx]. Con rgba32ui un texelFetch traeria 16 B de los que se usaria uno, y la
     *     razon de bytes por acceso dejaria de coincidir entre las dos rutas.
     *   extent = (WSIZE, 1). El indice del shader va como texel, asi que el espacio
     *     direccionable tiene que ser exactamente WSIZE texeles.
     *   La imagen va SIEMPRE a DEVICE_LOCAL. Es la ruta de texel de la GPU. Si se
     *     permitiera --mem=host sobre ella, el banco mediria dos cosas a la vez: la ruta
     *     de texel y la de la memoria. --mem solo varia el storage buffer.
     */
    VkImage img = VK_NULL_HANDLE; VkDeviceMemory imem = VK_NULL_HANDLE; VkImageView iv = VK_NULL_HANDLE;
    VkSubresourceLayout lay; memset(&lay, 0, sizeof(lay));
    uint32_t img_bytes = g_wsize * 4u;
    if (g_tex) {
       VkImageCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO };
       ici.imageType = VK_IMAGE_TYPE_2D;
       ici.format = VK_FORMAT_R32_UINT;
       ici.extent.width = g_wsize; ici.extent.height = 1; ici.extent.depth = 1;
       ici.mipLevels = 1; ici.arrayLayers = 1;
       ici.samples = VK_SAMPLE_COUNT_1_BIT;
       ici.tiling = VK_IMAGE_TILING_LINEAR;
       ici.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
       ici.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
       ici.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
       CHECK(vkCreateImage(dev, &ici, NULL, &img), "vkCreateImage");
       VkMemoryRequirements imr; vkGetImageMemoryRequirements(dev, img, &imr);
       uint32_t ibits = imr.memoryTypeBits, iwant = UINT32_MAX;
       VkPhysicalDeviceMemoryProperties imp; vkGetPhysicalDeviceMemoryProperties(gpu, &imp);
       for (uint32_t i = 0; i < ibits && i < imp.memoryTypeCount; i++)
          if (imp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT) { iwant = 1u << i; break; }
       if (iwant == UINT32_MAX) { fprintf(stderr, "ABORTO(2): la imagen no cabe en DEVICE_LOCAL\n"); return 2; }
       VkMemoryAllocateInfo imai = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
       imai.allocationSize = imr.size; imai.memoryTypeIndex = iwant;
       CHECK(vkAllocateMemory(dev, &imai, NULL, &imem), "vkAllocateMemory(img)");
       CHECK(vkBindImageMemory(dev, img, imem, 0), "vkBindImageMemory");

    vkGetImageSubresourceLayout(dev, img,
        &(VkImageSubresource){ VK_IMAGE_ASPECT_COLOR_BIT, 0, 0 }, &lay);
    /* La imageView. Sin ella el descriptor de binding 1 apunta a VK_NULL_HANDLE y el
     * despacho no produce nada: sin error de API, sin linea IMAGEN, y un buffer de
     * ceros que el banco lee como "el resultado no es el esperado". */
    VkImageViewCreateInfo ivci = { .sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO };
    ivci.image = img; ivci.viewType = VK_IMAGE_VIEW_TYPE_2D;
    ivci.format = VK_FORMAT_R32_UINT;
    ivci.subresourceRange = (VkImageSubresourceRange){
        .aspectMask = VK_IMAGE_ASPECT_COLOR_BIT, .baseMipLevel = 0, .levelCount = 1,
        .baseArrayLayer = 0, .layerCount = 1 };
    CHECK(vkCreateImageView(dev, &ivci, NULL, &iv), "vkCreateImageView");

    /* DISPOSICION DE LA IMAGEN: esto NO es un porton, es una observacion.
     *
     * La primera version de este banco abortaba cuando rowPitch != WSIZE*4. En esta
     * placa el porton saltaba a partir de unos 64 KiB con rowPitch == 0, y la
     * conclusion que saqué de ahi -- "el hardware no pone el texel i en i*4" -- era
     * falsa: un rowPitch de 0 quiere decir que el driver no relleno el campo, no que
     * la disposicion este mal. Confundir "no lo sé" con "no está" produce un falso
     * negativo, y el banco se niega a medir cuando la disposicion podria ser correcta.
     *
     * El metadato del driver se REPORTA y no se cree. Lo que decide es el contenido:
     * texdump.comp lee el texel i y lo escribe en el SSBO, y tiene que coincidir con el
     * patron. Ese control HAY que ejecutarlo a mano antes de medir con --tex; todavia
     * no esta cableado en bench.py, y esta nota lo registra como la accion siguiente
     * en vez de darlo por hecho. Un comentario que afirma un control que el codigo no
     * hace es peor que no tener comentario: el que lo lea dara por cubierto algo que
     * no lo esta. */
    {
        int pitch_ok = (lay.rowPitch == img_bytes);
        printf("IMAGEN    VkFormat=R32_UINT extent=%ux%u tiling=LINEAR bytes=%u "
               "rowPitch=%llu offset=%llu  (REPORTADO POR EL DRIVER, no verificado)\n",
               g_wsize, 1u, img_bytes, (unsigned long long)lay.rowPitch,
               (unsigned long long)lay.offset);
        printf("DISPOS    rowPitch %s WSIZE*4=%u; %s\n",
               pitch_ok ? "coincide con" : "NO coincide con", img_bytes,
               pitch_ok ? "disposicion declarada coherente"
                        : "campo no rellenado o con relleno; la disposicion se verifica "
                          "por contenido con texdump.spv antes de medir");
        fflush(stdout);
    }
}
    
    VkDescriptorBufferInfo dbi = { .buffer = buf, .offset = 0, .range = bytes };
    VkWriteDescriptorSet wr = { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET };
    wr.dstSet = ds; wr.dstBinding = 0; wr.descriptorCount = 1;
    wr.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; wr.pBufferInfo = &dbi;
    /* Binding 0 se escribe SIEMPRE, y el binding 1 ADEMAS con --tex. Poner la escritura
     * de binding 0 dentro del else de --tex deja el storage buffer sin descriptor cuando
     * la bandera esta encendida, y entonces el despacho no produce nada. No da error de
     * API: el conjunto se asigna bien, la llamada devuelve exito, y lo que sale es un
     * buffer de ceros que el banco lee como "el resultado no es el esperado". Un
     * instrumento que solo informa del sintoma esconde justo la causa. */
    vkUpdateDescriptorSets(dev, 1, &wr, 0, NULL);
    if (g_tex) {
        /* SHADER_READ_ONLY_OPTIMAL. El driver hace la transicion desde el layout que el
         * tenga apuntado, que tras la copia es TRANSFER_DST_OPTIMAL. */
        VkDescriptorImageInfo dii = { .sampler = VK_NULL_HANDLE, .imageView = iv,
                                     .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
        VkWriteDescriptorSet w2 = { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET };
        w2.dstSet = ds; w2.dstBinding = 1; w2.descriptorCount = 1;
        w2.descriptorType = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE; w2.pImageInfo = &dii;
        vkUpdateDescriptorSets(dev, 1, &w2, 0, NULL);
    }

    /* --- inicializacion desde el host con un patron conocido.
     * Sin esto el buffer arranca en cero, todos los items dan el mismo resultado y el
     * checksum de salida es cero LEGITIMO, indistinguible de "no se ejecuto".
     */
    /* El patron NO se escribe directamente en la memoria DEVICE_LOCAL: no es
     * HOST_VISIBLE y el host no puede mapearla. La via correcta es un buffer de staging
     * en memoria del host, mapearlo ahi, y copiarlo al buffer del dispositivo con un
     * vkCmdCopyBuffer antes de despachar. */

    /* --- command pool y buffer --- */
    VkCommandPoolCreateInfo cpci2 = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO };
    cpci2.queueFamilyIndex = 0;
    VkCommandPool pool; CHECK(vkCreateCommandPool(dev, &cpci2, NULL, &pool), "vkCreateCommandPool");
    VkCommandBufferAllocateInfo cbai = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO };
    /* DOS command buffers, no uno. La correccion de 268: la copia del patron vivia en el
     * MISMO command buffer que el despacho, y como la region cronometrada reenvia ese buffer,
     * el tiempo medido includia una copia host->dispositivo proporcional a `items`.
     * Medido con el kernel nulo: 3,2577 ns por dword, 1,228 GB/s, el 58% del tiempo.
     * Un banco que mide el kernel mezclandole la copia no mide el kernel. */
    cbai.commandPool = pool; cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; cbai.commandBufferCount = 2;
    VkCommandBuffer cmd[2]; CHECK(vkAllocateCommandBuffers(dev, &cbai, cmd), "vkAllocateCommandBuffers");
    VkCommandBuffer *cmd_dispatch = &cmd[0];   /* solo el despacho: esto es lo que se cronometra */
    VkCommandBuffer *cmd_pattern  = &cmd[1];   /* solo la copia del patron: fuera del reloj */

    /* --- staging en memoria del host: patron conocido -> copia al dispositivo --- */
    VkPhysicalDeviceMemoryProperties mprops; vkGetPhysicalDeviceMemoryProperties(gpu, &mprops);
    uint32_t hmi = UINT32_MAX;
    for (uint32_t i = 0; i < mprops.memoryTypeCount; i++)
        if (mprops.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) { hmi = i; break; }
    if (hmi == UINT32_MAX) { fprintf(stderr, "FALLO: no hay memoria HOST_VISIBLE\n"); return 5; }
    hmi_dbg = hmi;
    /* Aqui ya estan los dos tipos asignados. Printarlos juntos es lo que permite descartar
     * el confound de que --mem=0 y --mem=1 acaben en el mismo heap. */
    { VkPhysicalDeviceMemoryProperties mpx; vkGetPhysicalDeviceMemoryProperties(gpu, &mpx);
      uint32_t ti = 0;
      while (ti < mpx.memoryTypeCount && ti < 32 && !((want >> ti) & 1u)) ti++;
      if (ti >= mpx.memoryTypeCount || ti >= 32) ti = 0;
      uint32_t si = (hmi_dbg < mpx.memoryTypeCount) ? hmi_dbg : 0;
      printf("MEMTIPOS  kernel=tipo[%u] flags=0x%08x heap=%u  staging=tipo[%u] flags=0x%08x heap=%u"
             "  (memoryTypeCount=%u)\n",
             ti, mpx.memoryTypes[ti].propertyFlags, mpx.memoryTypes[ti].heapIndex,
             si, mpx.memoryTypes[si].propertyFlags, mpx.memoryTypes[si].heapIndex,
             mpx.memoryTypeCount);
      fflush(stdout); }
    VkBufferCreateInfo sbi = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO };
    sbi.size = bytes; sbi.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
    sbi.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VkBuffer sbuf; CHECK(vkCreateBuffer(dev, &sbi, NULL, &sbuf), "vkCreateBuffer(stage)");
    VkMemoryAllocateInfo smi = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
    smi.allocationSize = bytes; smi.memoryTypeIndex = hmi;
    VkDeviceMemory smem; CHECK(vkAllocateMemory(dev, &smi, NULL, &smem), "vkAllocateMemory(stage)");
    CHECK(vkBindBufferMemory(dev, sbuf, smem, 0), "vkBindBufferMemory(stage)");
    void *stage = NULL;
    if (vkMapMemory(dev, smem, 0, VK_WHOLE_SIZE, 0, &stage) != VK_SUCCESS) {
        fprintf(stderr, "FALLO: no se pudo mapear la memoria de staging\n"); return 5;
    }
    { uint32_t *w = (uint32_t *)stage;
      for (uint32_t i = 0; i < g_wsize; i++) w[i] = PATRON_INICIAL + i; }

    /* Pool de marcas de tiempo: dos, una antes del despacho y otra despues. */
    VkQueryPool qpool = VK_NULL_HANDLE;
    if (ts_hay) {
       VkQueryPoolCreateInfo qpci = { .sType = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO };
       qpci.queryType = VK_QUERY_TYPE_TIMESTAMP; qpci.queryCount = 2;
       if (vkCreateQueryPool(dev, &qpci, NULL, &qpool) != VK_SUCCESS) { qpool = VK_NULL_HANDLE; ts_hay = 0; }
    }


    VkCommandBufferBeginInfo cbbi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
    cbbi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    /* La copia del patron va SOLA en su command buffer. */
    CHECK(vkBeginCommandBuffer(*cmd_pattern, &cbbi), "vkBeginCommandBuffer(pattern)");
    /* Solo la region de lectura recibe el patron; la de escritura la escribe el kernel. */
    VkBufferCopy init = { .srcOffset = 0, .dstOffset = 0, .size = off_escritura };
    vkCmdCopyBuffer(*cmd_pattern, sbuf, buf, 1, &init);
    /* El patron tambien a la imagen, en el MISMO command buffer del patron y por tanto
     * fuera del reloj. Poner la copia dentro del despacho seria el error de 268: el banco
     * mediria la copia y no el kernel. */
    if (g_tex) {
       VkBufferImageCopy bic = { .bufferOffset = 0,
           .bufferRowLength = 0, .bufferImageHeight = 0,
           .imageSubresource = { .aspectMask = VK_IMAGE_ASPECT_COLOR_BIT,
                                  .mipLevel = 0, .baseArrayLayer = 0, .layerCount = 1 },
           .imageOffset = {0,0,0}, .imageExtent = { g_wsize, 1u, 1u } };
       vkCmdCopyBufferToImage(*cmd_pattern, sbuf, img,
           VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &bic);
    }
    CHECK(vkEndCommandBuffer(*cmd_pattern), "vkEndCommandBuffer(pattern)");
    /* Y el despacho va SOLO en el suyo, que es el unico que se cronometra. */
    CHECK(vkBeginCommandBuffer(*cmd_dispatch, &cbbi), "vkBeginCommandBuffer(dispatch)");
    /* Las marcas van dentro del command buffer del despacho, que es el que se reenvia en la
     * region cronometrada. vkCmdResetQueryPool tiene que ir DESPUES de vkBeginCommandBuffer. */
    if (qpool) {
       vkCmdResetQueryPool(*cmd_dispatch, qpool, 0, 2);
       vkCmdWriteTimestamp(*cmd_dispatch, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, qpool, 0);
    }
    /* Las marcas van dentro del command buffer del despacho, que es el que se reenvia en la
     * region cronometrada. vkCmdResetQueryPool tiene que ir DESPUES de vkBeginCommandBuffer. */
    if (qpool) {
       vkCmdResetQueryPool(*cmd_dispatch, qpool, 0, 2);
       vkCmdWriteTimestamp(*cmd_dispatch, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, qpool, 0);
    }
    vkCmdBindPipeline(*cmd_dispatch, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
    vkCmdBindDescriptorSets(*cmd_dispatch, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL);
    uint32_t grp = 64;
    /* M despachos en el mismo command buffer. Todos escriben en la MISMA region y con el
     * mismo patron, asi que el ultimo deja el resultado esperado y el control de contenido
     * sigue significando lo mismo: no se esta midiendo una acumulacion. Y las escrituras
     * se solapan, asi que este banco NO mideclusion alguna: solo el coste del envio. */
    for (int bi = 0; bi < g_batch; bi++)
        vkCmdDispatch(*cmd_dispatch, items / grp, 1, 1);
    if (qpool)
       vkCmdWriteTimestamp(*cmd_dispatch, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, qpool, 1);
    if (qpool)
       vkCmdWriteTimestamp(*cmd_dispatch, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, qpool, 1);
    CHECK(vkEndCommandBuffer(*cmd_dispatch), "vkEndCommandBuffer(dispatch)");
    printf("BATCH    despachos_por_envio=%d  items=%u  iters=%u\n", g_batch, items, iters);
    fflush(stdout);

    VkFenceCreateInfo fci = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    VkFence fence; CHECK(vkCreateFence(dev, &fci, NULL, &fence), "vkCreateFence");

    /* --- calibracion: una pasada en frio, patron y despacho, para que los relojes suban --- */
    VkSubmitInfo si = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO };
    si.commandBufferCount = 1; si.pCommandBuffers = cmd_pattern;
    CHECK(vkResetFences(dev, 1, &fence), "vkResetFences");
    CHECK(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit(patron)");
    CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "vkWaitForFences(patron)");
    si.pCommandBuffers = cmd_dispatch;
    CHECK(vkResetFences(dev, 1, &fence), "vkResetFences(cal)");
    CHECK(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit(cal)");
    CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "vkWaitForFences(cal)");
/* --- lo que la GPU dice que ha hecho, y no solo lo que el host ve ---------
 *
 * El intervalo entre las dos marcas es el tiempo de GPU del command buffer del
 * despacho. Si es cero, el despacho no llego a ejecutarse, y eso es una informacion
 * que ningun readback da: el buffer simplemente no cambio. Si es mayor que cero, el
 * comando se ejecuto y lo que se ve en el buffer es el resultado de la GPU.
 *
 * Un pool de marcas vacio o con valores no disponibles NO es un cero: es una ausencia.
 * Se distingue de un cero de verdad, porque un intervalo de cero con el pool
 * disponible significa que no hubo trabajo, y un intervalo no disponible significa que
 * no se pudo saber. */
    double gpu_ms = -1.0;
    uint64_t qv[2] = { 0, 0 };
    VkResult qrc = VK_SUCCESS;
    if (qpool)
        qrc = vkGetQueryPoolResults(dev, qpool, 0, 2, sizeof(qv), qv, sizeof(uint64_t),
                                    VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);
    if (qrc == VK_SUCCESS && qv[1] >= qv[0])
        gpu_ms = (double)(qv[1] - qv[0]) * ts_period / 1.0e6;   /* el periodo va en ns */
    char gpu_txt[64];
    if (gpu_ms >= 0.0) snprintf(gpu_txt, sizeof(gpu_txt), "%.6f", gpu_ms);
    else               snprintf(gpu_txt, sizeof(gpu_txt), "NO DISPONIBLE");
    printf("GPU      intervalo_marcas=%s ms  pool=%s  ts_period=%s  qrc=%d  qv=[%llu,%llu]\n",
           gpu_txt, qpool ? "presente" : "ausente",
           ts_hay ? (ts_period > 0 ? "util" : "0") : "no",
           (int)qrc, (unsigned long long)qv[0], (unsigned long long)qv[1]);
    fflush(stdout);

    /* --- medicion --- */
    const char *H = "/sys/class/drm/card1/device/hwmon/hwmon1";
    char p_mclk[256], p_sclk[256], p_pw[256], p_t[256];
    snprintf(p_mclk, sizeof p_mclk, "%s/freq2_input", H);
    snprintf(p_sclk, sizeof p_sclk, "%s/freq1_input", H);
    snprintf(p_pw,   sizeof p_pw,   "%s/power1_input", H);
    snprintf(p_t,    sizeof p_t,    "%s/temp1_input", H);

    printf("CONFIG    kernel=%s items=%u iters=%u nacc=%u steps=%u model=%d bytes=%llu\n",
           g_spv, items, iters, g_nacc, g_steps, g_model, (unsigned long long)bytes);
    printf("ANTES     mclk=%u Hz  sclk=%u Hz  ppt=%u uW  temp=%u mC\n",
           read32(p_mclk), read32(p_sclk), read32(p_pw), read32(p_t));

    /* El patron se (re)escribe FUERA del reloj: el kernel debe correr sobre el patron
     * conocido, pero reenviar la copia dentro de la medicion la contaminaria. Esa
     * contaminacion es la que encontro 268 y media el 58% del tiempo. */
    si.pCommandBuffers = cmd_pattern;
    CHECK(vkResetFences(dev, 1, &fence), "vkResetFences(patron2)");
    CHECK(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit(patron2)");
    CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "vkWaitForFences(patron2)");

    double t0 = now_s();
    for (int rep = 0; rep < g_rep; rep++) {
        /* ESTA LINEA SE PERDIO AL ANADIR --rep Y ROMPIO TODO. La linea 521 de arriba
         * deja si.pCommandBuffers apuntando a cmd_pattern, y la copia del patron no
         * debe entrar en el reloj. Sin restaurarla aqui, el bucle cronometrado subia
         * el buffer entero por el PCIe en vez de despachar, y daba: tiempo
         * independiente de ITERS, proporcional a la huella, a 0,73 ns por dword, que es
         * 1,375 GB/s, la velocidad del enlace. Con esa senal es facil creer que la GPU
         * cobra por reserva. Lo detecta 607: el tiempo tiene que crecer con ITERS. */
    si.pCommandBuffers = cmd_dispatch;
    CHECK(vkResetFences(dev, 1, &fence), "vkResetFences2");
    CHECK(vkQueueSubmit(queue, 1, &si, fence), "vkQueueSubmit2");
    CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX), "vkWaitForFences2");
    double tre = now_s();
    /* La marca se lee AQUI, dentro del bucle, y no una sola vez tras la calibracion.
     * Leerla una sola vez empareja el intervalo de GPU de la calibracion con la mediana
     * de host de las repeticiones, y esos dos numeros NO describen el mismo trabajo:
     * salia gpu/host de 2,5, que es fisicamente imposible. Cada medicion lleva su
     * marca, o no lleva ninguna. */
    double gpu_rep = -1.0;
    if (qpool) {
        uint64_t qv[2] = { 0, 0 };
        if (vkGetQueryPoolResults(dev, qpool, 0, 2, sizeof(qv), qv, sizeof(uint64_t),
                              VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) == VK_SUCCESS
            && qv[1] >= qv[0])
            gpu_rep = (double)(qv[1] - qv[0]) * ts_period / 1.0e6;
    }
    printf("TIEMPO    %.6f s", tre - t0);
    if (gpu_rep >= 0.0) printf("  gpu=%.6f ms", gpu_rep);
    else printf("  gpu=no disponible");
    printf("\n");
    t0 = now_s();
        t0 = now_s();
    }


    /* --- READBACK: la comprobacion de que el kernel ESCRIBIO algo.
     *
     * Sin esto, el programa no puede distinguir "el kernel ejecuto" de "el kernel fue
     * eliminado por el optimizador" o de "el despacho no llego a la cola". Un banco de
     * pruebas que solo mide tiempo mide lo que sea que pase, incluido el no hacer nada.
     * El checksum hace que el resultado del kernel forme parte del artefacto: si el
     * buffer sigue a cero, el trabajo no ocurrio y el tiempo medido no significa nada.
     */
    {
        /* la lectura va al MISMO staging que el host tiene mapeado (sbuf/stage).
         * Antes se copiaba a un segundo buffer de host, y luego se leia el primero:
         * dos buffers distintos, y el control comparaba memoria que nadie habia escrito. */
        VkCommandBufferAllocateInfo ra = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO };
        ra.commandPool = pool; ra.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; ra.commandBufferCount = 1;
        VkCommandBuffer rcmd; CHECK(vkAllocateCommandBuffers(dev, &ra, &rcmd), "vkAlloc(rb)");
        VkCommandBufferBeginInfo rb = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
        rb.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        CHECK(vkBeginCommandBuffer(rcmd, &rb), "vkBegin(rb)");
        /* El readback lee la region de escritura, que empieza en off_escritura. */
        VkBufferCopy region = { .srcOffset = off_escritura, .dstOffset = 0,
                                .size = (VkDeviceSize)items * 4 };
        vkCmdCopyBuffer(rcmd, buf, sbuf, 1, &region);   /* dispositivo -> staging mapeado */
        CHECK(vkEndCommandBuffer(rcmd), "vkEnd(rb)");

        VkFence rf; VkFenceCreateInfo rfc = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
        CHECK(vkCreateFence(dev, &rfc, NULL, &rf), "vkCreateFence(rb)");
        VkSubmitInfo rsi = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO };
        rsi.commandBufferCount = 1; rsi.pCommandBuffers = &rcmd;
        CHECK(vkQueueSubmit(queue, 1, &rsi, rf), "vkQueueSubmit(rb)");
        CHECK(vkWaitForFences(dev, 1, &rf, VK_TRUE, UINT64_MAX), "vkWaitForFences(rb)");

        void *host = stage;   /* el staging del host, ya mapeado */
        if (host) {
            const uint32_t *h = (const uint32_t *)host;
            uint32_t probe = (items < 256u) ? items : 256u;
            /* Control VALIDO: el host calcula por su cuenta el valor esperado del kernel
             * y compara palabra a palabra. "distinto del patron inicial" NO alcanza,
             * porque cero puede ser la respuesta legitima. */
            uint32_t bad = 0, unchanged = 0;
            if (!g_control) {
                uint32_t nz = 0, pr = (items < 256u) ? items : 256u;
                for (uint32_t i = 0; i < pr; i++) if (h[i]) nz++;
                /* La prediccion del modelo para el item 0, SIEMPRE. Antes solo se
                 * imprimia cuando el control de contenido fallaba, y hay una razon por
                 * la que eso no basta: una herramienta que replica la cadena en otro
                 * lenguaje -- huella.py lo hace -- necesita poder comprobar su replica
                 * contra esta. Sin una linea que exponga el valor del modelo, la replica
                 * no se puede verificar contra nada y el calculo que hace encima no vale
                 * nada. Un numero que no se puede contrastar con su propio generador
                 * esta en la misma situacion que un numero sin unidad. */
                {
                    uint32_t pred = 0;
                    /* La MISMA expresion que el switch de mas abajo, copiada. Que el
                     * modelo se exponga con una copia y no llamando a una funcion es
                     * duplicacion: si divergen, el valor que se imprime dice una cosa y el
                     * control que decide dice otra, y el self-test de huella.py compararia
                     * contra una copia muerta. */
                    if (g_model == 1) {
                        uint32_t oi = occ_hash(0x9e3779b9u) % g_nacc, oa = 0u;
                        for (uint32_t k = 0; k < iters; k++) {
                            oa = oa * 1664525u + (PATRON_INICIAL + oi) + 1013904223u;
                            oi = occ_hash(oa ^ (k * 0x85ebca6bu)) % g_nacc;
                        }
                        pred = oa;
                    }
                    printf("MODELO   item0=0x%08x  modelo=%u  wsize=%u\n", pred, g_model, g_wsize);
                }
                printf("READBACK  [SIN CONTROL] %u de %u no nulos; no se compara con el modelo\n", nz, pr);
                if (!nz) { fprintf(stderr, "ABORTO(4): sin trabajo escrito.\n"); return 4; }
                return 0;
            }
    /* El bucle del control de contenido. La cabecera se perdio al insertar el bloque
     * de arriba; se restituye aqui y con el mismo rango que usaba el original,
     * min(items, 256), que es lo que el readback lee. */
    for (uint32_t i = 0; i < probe; i++) {
                if (g_model == 7) {
                    /* lane.comp: mismo numero de cargas de carril, otro reparto de direcciones. */
                    uint32_t lane = i % 64u;
                    uint32_t base = i - lane;
                    uint32_t idx;
                    if      (g_lane == 1u) idx = hash32(i + 0x9e3779b9u) % g_nacc;
                    else if (g_lane == 2u) idx = (base + lane + 0x9e3779b9u)
                                                % (g_sub ? g_sub : g_nacc);
                    else                    idx = base % (g_sub ? g_sub : g_nacc);
                    uint32_t acc = 0u;
                    for (uint32_t k = 0; k < iters; k++) {
                        if (g_lane == 0u) idx = (base + k * 2654435761u)
                                                % (g_sub ? g_sub : g_nacc);
                        if (g_lane == 2u) idx = (base + lane + k * g_stride)
                                                % (g_sub ? g_sub : g_nacc);
                        uint32_t v = PATRON_INICIAL + idx;
                        acc = acc * 1664525u + v + 1013904223u;
                        if (g_lane == 1u) idx = hash32(acc ^ (k * 0x85ebca6bu))
                                                    % (g_sub ? g_sub : g_nacc);
                    }
                    want = (g_addr == 1u) ? idx : acc;
                } else if (g_model == 6) {
                    /* spread.comp: mismos bloques, otro reparto entre vias. */
                    uint32_t blk = ((i / 64u) * 64u + ((i % 64u) * g_grp) % 64u) * g_blk;
                    uint32_t acc = 0u;
                    for (uint32_t k = 0; k < iters; k++) {
                        uint32_t idx = blk + ((acc ^ k) % g_blk);
                        uint32_t v = PATRON_INICIAL + idx;
                        acc = acc * 1664525u + v + 1013904223u;
                    }
                    want = acc;
                } else if (g_model == 5) {
                    /* reuse.comp: cada hilo tiene un bloque de g_blk direcciones y elige
                     * dentro de el pseudoaleatoriamente. La distancia de reutilizacion es
                     * g_blk, y la huella es items x g_blk. */
                    uint32_t blk = i * g_blk;
                    uint32_t acc = 0u;
                    for (uint32_t k = 0; k < iters; k++) {
                        uint32_t idx = blk + ((acc ^ k) % g_blk);
                        uint32_t v = PATRON_INICIAL + idx;
                        acc = acc * 1664525u + v + 1013904223u;
                    }
                    want = acc;
                } else if (g_model == 4) {
                    /* page.comp: misma huella en bytes, distinto numero de paginas. */
                    uint32_t npag = (g_nacc + 1023u) / 1024u;
                    uint32_t idx = (g_page == 0) ? (i % g_nacc)
                                                 : ((i % npag) * 1024u + (i % 1024u));
                    uint32_t acc = 0u;
                    for (uint32_t k = 0; k < iters; k++) {
                        uint32_t v = PATRON_INICIAL + idx;
                        acc = acc * 1664525u + v + 1013904223u;
                        idx = acc % g_nacc;
                        acc = acc + idx;
                    }
                    want = acc;
                } else if (g_model == 3) {
                    /* div.comp: cadena dependiente con indice por division o por mascara.
                     * Las dos ramas tienen el mismo numero de pasos, asi que si el tiempo
                     * difiere es la operacion, no la cantidad de trabajo. */
                    uint32_t idx = occ_hash(i + 0x9e3779b9u) % g_nacc;
                    uint32_t acc = 0u;
                    for (uint32_t k = 0; k < iters; k++) {
                        uint32_t v = PATRON_INICIAL + idx;
                        acc = acc * 1664525u + v + 1013904223u;
                        idx = (g_mode == 0) ? (acc % g_nacc) : (acc & (g_nacc - 1u));
                        for (uint32_t s = 0; s < g_steps; s++) idx = occ_hash(idx) % g_nacc;
                        acc = acc + idx;
                    }
                    want = acc;
                } else if (g_model == 2) {
                    want = chain_model(i, iters, g_nacc, g_steps);
                } else if (g_model == 1) {
                    /* occ.comp: cadena dependiente con indice pseudoaleatorio.
                     * Se replica aqui palabra a palabra. El contenido del buffer es el
                     * patron, asi que d[idx] = PATRON_INICIAL + idx en cada paso. */
                    uint32_t idx = occ_hash(i + 0x9e3779b9u) % g_nacc;   /* g_nacc == WSIZE */
                    uint32_t acc = 0u;
                    for (uint32_t k = 0; k < iters; k++) {
                        uint32_t v = PATRON_INICIAL + idx;
                        acc = acc * 1664525u + v + 1013904223u;
                        idx = occ_hash(acc ^ (k * 0x85ebca6bu)) % g_nacc;
                    }
                    want = acc;
                } else {
                    want = PATRON_INICIAL + i;   /* lo que hay en el buffer */
                    want += i;                   /* probe.comp: a = d[i] + i, ANTES del bucle */
                    for (uint32_t k = 0; k < iters; k++) want = paso(want);
                    want = cierre(want);
                }
                if (h[i] != want) {
                    if (bad < 3)
                        fprintf(stderr, "  DATO i=%u  gpu=0x%08x  modelo=0x%08x\n", i, h[i], want);
                    bad++;
                }
                if (h[i] == (PATRON_INICIAL + i)) unchanged++;
            }
            printf("READBACK  %u de %u dwords verificados contra el modelo del host: "
                   "%u coinciden, %u NO, %u sin modificar\n", probe, items,
                   probe - bad, bad, unchanged);
            if (bad) {
                fprintf(stderr, "ABORTO(4): %u de %u palabras NO coinciden con el modelo.\n"
                                "  tiempo %f s, pero el resultado no es el esperado: no es un dato.\n",
                        bad, probe, 0.0);
                return 4;
            }
            if (unchanged) {
                fprintf(stderr, "AVISO: %u palabras quedaron sin modificar.\n", unchanged);
            }
            /* CONTROL ESTRUCTURAL del patron de direcciones, sobre la SALIDA DEL DISPOSITIVO
             * y sin usar el modelo del host. El control de contenido de arriba NO puede
             * detectar un modo degenerado: si el host y el shader hacen la misma cuenta
             * equivocada, coinciden perfectamente. Este control mira la propiedad que el
             * experimento necesita de verdad.
             *   ADDR=1 + LANEMODE=0 (difusion) : los 64 carriles de un wavefront deben
             *                                        leer la MISMA direccion.
             *   ADDR=1 + LANEMODE=1 (disperso) : carriles vecinos deben leer direcciones
             *                                        DISTINTAS.
             * Con ADDR=0 el shader escribe la cadena y esto no se puede comprobar. */
            if (g_model == 7 && g_addr == 1 && probe >= 128u) {
                uint32_t igual = 0, distinto = 0, pares = 0;
                for (uint32_t i = 0; i + 1u < probe; i++) {
                    if (((i + 1u) % 64u) == 0u) continue;   /* no cruza wavefronts */
                    pares++;
                    if (h[i] == h[i + 1u]) igual++; else distinto++;
                }
                if (getenv("VCP_DUMP")) {
                    /* Indices 0..3 (carriles 0..3 del wavefront 0), 64..67 (wavefront 1) y
                     * 128..131 (wavefront 2): si dentro de un wavefront todos coinciden pero
                     * entre wavefronts no, el reparto es de wavefront, no de carril. */
                    static const uint32_t q[] = {0,1,2,3, 64,65,66,67, 128,129,130,131};
                    printf("DUMP gpu LANEMODE=%u :", g_lane);
                    for (unsigned z = 0; z < sizeof(q)/sizeof(q[0]); z++) printf(" %u", h[q[z]]);
                    printf("\nDUMP host              :");
                    for (unsigned z = 0; z < sizeof(q)/sizeof(q[0]); z++) {
                        uint32_t i2 = q[z], lane2 = i2 % 64u, base2 = i2 - lane2;
                        uint32_t ix = (g_lane == 1u) ? (hash32(i2 + 0x9e3779b9u) % g_nacc) : (base2 % g_nacc);
                        uint32_t ac = 0u;
                        for (uint32_t k = 0; k < iters; k++) {
                            if (g_lane == 0u) ix = (base2 + k * 2654435761u) % g_nacc;
                            ac = ac * 1664525u + PATRON_INICIAL + ix + 1013904223u;
                            if (g_lane == 1u) ix = ac % g_nacc;
                        }
                        printf(" %u", ix);
                    }
                    printf("\nDUMP params: g_lane=%u g_addr=%u g_nacc=%u items=%u iters=%u\n",
                           g_lane, g_addr, g_nacc, items, iters);
                }
                printf("PATRON    LANEMODE=%u : de %u pares de carriles contiguos, "
                       "%u comparten direccion, %u difieren (umbral de fallo: %u de %u)\n",
                       g_lane, pares, igual, distinto,
                       g_lane == 0u ? (distinto * 2u > pares ? 1u : 0u)
                                    : (igual * 2u > pares ? 1u : 0u), pares);
                if (g_lane == 0u && (distinto * 2u > pares)) {
                    fprintf(stderr, "ABORTO(7): el modo DIFUSION produjo carriles con "
                                    "direcciones distintas (%u de %u). No es difusion.\n",
                            distinto, pares);
                    return 7;
                }
                if (g_lane == 1u && (igual * 2u > pares)) {
                    fprintf(stderr, "ABORTO(7): el modo DISPERSO produjo carriles que "
                                    "comparten direccion (%u de %u). No es disperso.\n",
                            igual, pares);
                    return 7;
                }
                /* ENTROPIA MINIMA. La mayoria detecta el colapso total, pero no una cadena
                 * que se contraiga a unas pocas decenas de direcciones: 262-1 y 287 se
                 * apoyaron en kernels que hacen exactamente eso. Se exige que el numero de
                 * direcciones DISTINTAS entre los hilos probados sea al menos la mitad de
                 * ellos. Es un umbral de instrumento, y por que sea alto importa: un kernel
                 * degenerado mide el kernel, no el hardware. */
                uint32_t ndist = 0;
                for (uint32_t a = 0; a < probe; a++) {
                    uint32_t visto = 0;
                    for (uint32_t b = 0; b < a; b++) if (h[b] == h[a]) { visto = 1; break; }
                    if (!visto) ndist++;
                }
                /* La entropia tiene que ser ALTA en disperso y BAJA en difusion, y cada modo
                 * tiene su propio umbral. Exigir alta en los dos habria hecho fallar la
                 * difusion, que es poco entropica por construccion y a proposito. */
                uint32_t minimo = (g_lane == 1u) ? (probe / 2u) : 2u;
                uint32_t maximo = (g_lane == 1u) ? probe : (probe / 32u + 2u);
                const char *modo = (g_lane == 1u) ? "DISPERSO"
                                 : (g_lane == 2u) ? "CONTIGUO" : "DIFUSION";
                if (g_lane == 2u) { minimo = probe - probe / 64u; maximo = probe; }
                printf("ENTROPIA  %-9s %u direcciones distintas entre %u hilos "
                       "(admitido %u..%u)\n", modo, ndist, probe, minimo, maximo);
                if (ndist < minimo || ndist > maximo) {
                    fprintf(stderr, "ABORTO(8): %s con %u direcciones distintas entre %u hilos, "
                                    "fuera de %u..%u. El kernel no esta haciendo lo que dice "
                                    "y su tiempo no describe el hardware.\n",
                            modo, ndist, probe, minimo, maximo);
                    return 8;
                }
            }
        } else {
            fprintf(stderr, "AVISO: no se pudo mapear la memoria del host; sin readback.\n");
        }
    }

    printf("NOTA      una sola pasada es demasiado corta para un estado estacionario.\n");
    printf("          para benchmark, repetir N>=30 con calentamiento y reportar\n");
    printf("          mediana y varianza, nunca una sola muestra.\n");

    vkDeviceWaitIdle(dev);
    return 0;
}