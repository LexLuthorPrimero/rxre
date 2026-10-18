/* mmrlive.c -- research instrument: lee registros MMIO de la RX550 via ioctl,
 * sin root y sin debugfs.
 *
 * RAPH550-MMR-1  ·  C99, sin dependencias fuera de libc.
 *
 * POR QUE EXISTE
 *   sysfs resource0/2/4/5 y /sys/kernel/debug son de root (medido en 1563).
 *   /proc/interrupts es un contador, no un estado.  Este es el UNICO camino
 *   medido que devuelve el VALOR de un registro de hardware sin privilegio,
 *   y solo para los 76 offsets que el propio driver tiene en lista blanca
 *   (vi.c:vi_allowed_read_registers, inventario en el hallazgo 1565).
 *
 * QUE SE ESCRIBE
 *   Nada en la GPU.  Solo AMDGPU_INFO_READ_MMR_REG, que en amdgpu_kms.c:875
 *   no tiene capable(), solo valida rango y llama amdgpu_asic_read_register.
 *   La unica escritura es el ioctl, que es una lectura.
 *
 * SALIDA
 *   TSV por stdout: offset_hex<TAB>nombre<TAB>valor_hex<TAB>errno_texto
 *   Modo --probe: ademas imprime una linea por offset PROBADO y RECHAZADO,
 *   que es el control negativo contra la lista blanca.
 *
 * USO
 *   mmrlive [--probe] [--dev /dev/dri/cardN] [--se N] [--repeat N] [--sleep MS]
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <sys/stat.h>

/* ---- uapi: LA CABECERA REAL, no una copia a mano.
 *
 * ERROR PROPIO que esta replacements corriger:  la primera version de este
 * fichero declaraba struct drm_amdgpu_info a mano con un union de pad[384].
 * Eso daba sizeof = 400, y el numero de ioctl se calcula a partir de sizeof,
 * asi que se enviaba 0x41906440 en vez de 0x40206445.  El kernel contestaba
 * ENOSPC a todos los queries y EINVAL al MMR:  no era el driver, era mi
 * estructura.  Medido con un sizeof()-compilado-contra-la-cabecera-real.
 *
 * Ahora se incluye la cabecera que usa el kernel en ejecucion.  Es la unica
 * forma de que el numero de ioctl no pueda estar mal.
 */
#define __user
#include <drm/amdgpu_drm.h>

/* el numero de ioctl depende de sizeof, asi que se comprueba al compilar */
typedef char assert_info_size[(sizeof(struct drm_amdgpu_info) == 32) ? 1 : -1];

/* consultas usadas por --selftest, para separar "el ioctl no llega" de
 * "este caso concreto esta bloqueado".  Los numeros vienen de la cabecera. */
#define Q_ACCEL_WORKING  AMDGPU_INFO_ACCEL_WORKING
#define Q_HW_IP_COUNT    AMDGPU_INFO_HW_IP_COUNT
#define Q_TIMESTAMP      AMDGPU_INFO_TIMESTAMP
#define Q_VRAM_USAGE     AMDGPU_INFO_VRAM_USAGE
#define Q_GTT_USAGE      AMDGPU_INFO_GTT_USAGE
#define Q_DEV_INFO       AMDGPU_INFO_DEV_INFO
#define Q_MEMORY         AMDGPU_INFO_MEMORY
#define Q_VBIOS          AMDGPU_INFO_VBIOS
#define Q_NUM_HANDLES    AMDGPU_INFO_NUM_HANDLES

#define MAX_MMR 128   /* el kernel rechaza count > 128 (amdgpu_kms.c:899) */

/* ---- la lista blanca de POLARIS12, resuelta de vi.c ----
 * Los offsets salen de gfx_8_0_d.h / oss_3_0_1_d.h / gc_10_1_0_offset.h /
 * gmc_7_1_d.h.  El campo indexed es el segundo miembro de la entrada.
 */
struct mmr_entry {
        uint32_t off;
        const char *name;
        int indexed;
};

static const struct mmr_entry mmr_whitelist[] = {
        /* TABLA GENERADA.  76 entradas = las 76 de vi.c:vi_allowed_read_registers.
         * No editar a mano:  revkit/tools/gen_mmr_table.py la emite desde el
         * driver, y el recuento se comprueba contra el del fuente.
         * offsets: gca/gfx_8_0_d.h, oss/oss_3_0_1_d.h, gc/gc_10_1_0_offset.h,
         *           gmc/gmc_7_1_d.h, y vid.h para SDMA*_REGISTER_OFFSET. */
        { 0x0025, "mmSDMA0_STATUS_REG+SDMA0_REGISTER_OFFSET", 0 },
        { 0x0225, "mmSDMA0_STATUS_REG+SDMA1_REGISTER_OFFSET", 0 },
        { 0x0393, "mmSRBM_STATUS2", 0 },
        { 0x0394, "mmSRBM_STATUS", 0 },
        { 0x0395, "mmSRBM_STATUS3", 0 },
        { 0x09D8, "mmMC_ARB_RAMCFG", 0 },
        { 0x2002, "mmGRBM_STATUS2", 0 },
        { 0x2004, "mmGRBM_STATUS", 0 },
        { 0x2005, "mmGRBM_STATUS_SE0", 0 },
        { 0x2006, "mmGRBM_STATUS_SE1", 0 },
        { 0x200E, "mmGRBM_STATUS_SE2", 0 },
        { 0x200F, "mmGRBM_STATUS_SE3", 0 },
        { 0x2084, "mmCP_CPC_STATUS", 0 },
        { 0x2085, "mmCP_CPC_BUSY_STAT", 0 },
        { 0x2086, "mmCP_CPC_STALLED_STAT1", 0 },
        { 0x2087, "mmCP_CPF_STATUS", 0 },
        { 0x2088, "mmCP_CPF_BUSY_STAT", 0 },
        { 0x2089, "mmCP_CPF_STALLED_STAT1", 0 },
        { 0x219C, "mmCP_STALLED_STAT3", 0 },
        { 0x219D, "mmCP_STALLED_STAT1", 0 },
        { 0x219E, "mmCP_STALLED_STAT2", 0 },
        { 0x21A0, "mmCP_STAT", 0 },
        { 0x263D, "mmCC_RB_BACKEND_DISABLE", 1 },
        { 0x263E, "mmGB_ADDR_CONFIG", 0 },
        { 0x263F, "mmGB_BACKEND_MAP", 0 },
        { 0x2644, "mmGB_TILE_MODE0", 0 },
        { 0x2645, "mmGB_TILE_MODE1", 0 },
        { 0x2646, "mmGB_TILE_MODE2", 0 },
        { 0x2647, "mmGB_TILE_MODE3", 0 },
        { 0x2648, "mmGB_TILE_MODE4", 0 },
        { 0x2649, "mmGB_TILE_MODE5", 0 },
        { 0x264A, "mmGB_TILE_MODE6", 0 },
        { 0x264B, "mmGB_TILE_MODE7", 0 },
        { 0x264C, "mmGB_TILE_MODE8", 0 },
        { 0x264D, "mmGB_TILE_MODE9", 0 },
        { 0x264E, "mmGB_TILE_MODE10", 0 },
        { 0x264F, "mmGB_TILE_MODE11", 0 },
        { 0x2650, "mmGB_TILE_MODE12", 0 },
        { 0x2651, "mmGB_TILE_MODE13", 0 },
        { 0x2652, "mmGB_TILE_MODE14", 0 },
        { 0x2653, "mmGB_TILE_MODE15", 0 },
        { 0x2654, "mmGB_TILE_MODE16", 0 },
        { 0x2655, "mmGB_TILE_MODE17", 0 },
        { 0x2656, "mmGB_TILE_MODE18", 0 },
        { 0x2657, "mmGB_TILE_MODE19", 0 },
        { 0x2658, "mmGB_TILE_MODE20", 0 },
        { 0x2659, "mmGB_TILE_MODE21", 0 },
        { 0x265A, "mmGB_TILE_MODE22", 0 },
        { 0x265B, "mmGB_TILE_MODE23", 0 },
        { 0x265C, "mmGB_TILE_MODE24", 0 },
        { 0x265D, "mmGB_TILE_MODE25", 0 },
        { 0x265E, "mmGB_TILE_MODE26", 0 },
        { 0x265F, "mmGB_TILE_MODE27", 0 },
        { 0x2660, "mmGB_TILE_MODE28", 0 },
        { 0x2661, "mmGB_TILE_MODE29", 0 },
        { 0x2662, "mmGB_TILE_MODE30", 0 },
        { 0x2663, "mmGB_TILE_MODE31", 0 },
        { 0x2664, "mmGB_MACROTILE_MODE0", 0 },
        { 0x2665, "mmGB_MACROTILE_MODE1", 0 },
        { 0x2666, "mmGB_MACROTILE_MODE2", 0 },
        { 0x2667, "mmGB_MACROTILE_MODE3", 0 },
        { 0x2668, "mmGB_MACROTILE_MODE4", 0 },
        { 0x2669, "mmGB_MACROTILE_MODE5", 0 },
        { 0x266A, "mmGB_MACROTILE_MODE6", 0 },
        { 0x266B, "mmGB_MACROTILE_MODE7", 0 },
        { 0x266C, "mmGB_MACROTILE_MODE8", 0 },
        { 0x266D, "mmGB_MACROTILE_MODE9", 0 },
        { 0x266E, "mmGB_MACROTILE_MODE10", 0 },
        { 0x266F, "mmGB_MACROTILE_MODE11", 0 },
        { 0x2670, "mmGB_MACROTILE_MODE12", 0 },
        { 0x2671, "mmGB_MACROTILE_MODE13", 0 },
        { 0x2672, "mmGB_MACROTILE_MODE14", 0 },
        { 0x2673, "mmGB_MACROTILE_MODE15", 0 },
        { 0x26DF, "mmGC_USER_RB_BACKEND_DISABLE", 1 },
        { 0xA0D4, "mmPA_SC_RASTER_CONFIG", 1 },
        { 0xA0D5, "mmPA_SC_RASTER_CONFIG_1", 1 },
};

#define N_WHITELIST ((int)(sizeof(mmr_whitelist)/sizeof(mmr_whitelist[0])))

/* control negativo: offsets que el driver NO tiene en lista blanca.
 * Expected: EFAULT o EINVAL.  Si alguno devolviera exito, mi tabla de 1565
 * estaria incompleta y la herramienta estaria mintiendo sobre si misma. */
static const uint32_t mmr_negatives[] = {
        0x0F80,   /* IH_RB_BASE   -- el objetivo de 1534 */
        0x0F82,   /* IH_RB_RPTR   */
        0x0F83,   /* IH_RB_WPTR   */
        0x0F84,   /* IH_CNTL      */
        0x151A,   /* INTERRUPT_CNTL */
        0x0000,   /* MMIO        */
        0xDEAD,   /* fuera de rango */
};

#define N_NEGATIVES ((int)(sizeof(mmr_negatives)/sizeof(mmr_negatives[0])))

static int read_one(int fd, uint32_t off, uint32_t se, uint32_t sh,
                    uint32_t *out)
{
        struct drm_amdgpu_info info;
        uint32_t regs[MAX_MMR];

        memset(&info, 0, sizeof(info));
        memset(regs, 0, sizeof(regs));
        info.return_pointer = (uint64_t)(unsigned long)regs;
        info.return_size   = sizeof(regs);
        info.query         = AMDGPU_INFO_READ_MMR_REG;
        info.read_mmr_reg.dword_offset = off;
        info.read_mmr_reg.count        = 1;
        info.read_mmr_reg.instance = (se << AMDGPU_INFO_MMR_SE_INDEX_SHIFT)
                                     | (sh << AMDGPU_INFO_MMR_SH_INDEX_SHIFT);
        info.read_mmr_reg.flags = 0;

        if (ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info) < 0)
                return -errno;
        *out = regs[0];
        return 0;
}

/* envia un query sin datos de entrada y devuelve el errno (0 si exito) */
static int try_query(int fd, uint32_t query, uint64_t *val)
{
        struct drm_amdgpu_info info;
        uint64_t out = 0;

        memset(&info, 0, sizeof(info));
        info.return_pointer = (uint64_t)(unsigned long)&out;
        info.return_size   = sizeof(out);
        info.query         = query;

        if (ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info) < 0)
                return -errno;
        if (val) *val = out;
        return 0;
}

static int selftest(int fd)
{
        static const struct { uint32_t q; const char *n; } qs[] = {
                { Q_ACCEL_WORKING, "AMDGPU_INFO_ACCEL_WORKING" },
                { Q_HW_IP_COUNT,   "AMDGPU_INFO_HW_IP_COUNT"   },
                { Q_TIMESTAMP,     "AMDGPU_INFO_TIMESTAMP"     },
                { Q_VRAM_USAGE,    "AMDGPU_INFO_VRAM_USAGE"    },
                { Q_GTT_USAGE,     "AMDGPU_INFO_GTT_USAGE"     },
                { Q_DEV_INFO,      "AMDGPU_INFO_DEV_INFO"      },
                { Q_MEMORY,        "AMDGPU_INFO_MEMORY"        },
                { Q_VBIOS,         "AMDGPU_INFO_VBIOS"         },
                { Q_NUM_HANDLES,   "AMDGPU_INFO_NUM_HANDLES"   },
        };
        int i;

        printf("IOCTL\tDRM_IOCTL_AMDGPU_INFO\t0x%08X\tsizeof(struct drm_amdgpu_info)=%zu\n",
               (unsigned)DRM_IOCTL_AMDGPU_INFO, sizeof(struct drm_amdgpu_info));
        for (i = 0; i < (int)(sizeof(qs)/sizeof(qs[0])); i++) {
                uint64_t v = 0;
                int rc = try_query(fd, qs[i].q, &v);
                printf("QUERY\t%s\t0x%02X\t%s\t%s\n", qs[i].n, qs[i].q,
                       rc == 0 ? "OK" : strerror(-rc),
                       rc == 0 ? "" : "");
        }
        /* y el caso que nos interesa, aislado */
        {
                uint32_t v = 0;
                int rc = read_one(fd, 0x2004, 0, 0, &v);   /* mmGRBM_STATUS */
                printf("QUERY\tREAD_MMR_REG(0x2004 mmGRBM_STATUS)\t0x15\t%s\n",
                       rc == 0 ? "OK" : strerror(-rc));
        }
        return 0;
}

static void usage(void)
{
        fprintf(stderr,
"mmrlive -- lectura de registros MMIO de la RX550 sin root\n"
"uso: mmrlive [--probe] [--dev RUTA] [--se N] [--sh N] [--repeat N] [--sleep MS]\n"
"  --probe    imprime tambien los controles negativos (offsets no permitidos)\n"
"  --selftest prueba varios queries del mismo ioctl para separar el\n"
"             fallo de plumbing de un caso bloqueado\n"
"  --dev     nodo DRM por defecto /dev/dri/card1\n"
"  --se      indice de SE para los registros GRBM indexados (0)\n"
"  --sh      indice de SH para los registros GRBM indexados (0)\n"
"  --repeat  numero de pasadas (1)\n"
"  --sleep   milisegundos entre pasadas (100)\n");
}

int main(int argc, char **argv)
{
        const char *dev = "/dev/dri/card1";
        int probe = 0, rep = 1, se = 0, sh = 0, sleepms = 100, self = 0;
        int i, r, fd;

        for (i = 1; i < argc; i++) {
                if (!strcmp(argv[i], "--probe"))          probe = 1;
                else if (!strcmp(argv[i], "--selftest"))   self = 1;
                else if (!strcmp(argv[i], "--dev") && i+1 < argc) dev = argv[++i];
                else if (!strcmp(argv[i], "--se") && i+1 < argc)  se = atoi(argv[++i]);
                else if (!strcmp(argv[i], "--sh") && i+1 < argc)  sh = atoi(argv[++i]);
                else if (!strcmp(argv[i], "--repeat") && i+1 < argc) rep = atoi(argv[++i]);
                else if (!strcmp(argv[i], "--sleep") && i+1 < argc) sleepms = atoi(argv[++i]);
                else { usage(); return 2; }
        }

        /* Declaracion explicita del target, antes de tocar nada.  La frontera
         * dura del proyecto prohibe escribir sobre 0000:00:02.0.  Este
         * instrumento solo LEE y solo sobre el nodo que se le pase, asi que
         * imprime el target para que quede en el log. */
        fprintf(stderr, "# mmrlive: dev=%s  solo-lectura  whitelista=%d  negativos=%d\n",
                dev, N_WHITELIST, probe ? N_NEGATIVES : 0);

        fd = open(dev, O_RDWR | O_CLOEXEC);
        if (fd < 0) {
                fprintf(stderr, "mmrlive: open(%s): %s\n", dev, strerror(errno));
                return 1;
        }

        if (self) {
                selftest(fd);
                close(fd);
                return 0;
        }

        for (r = 0; r < rep; r++) {
                if (rep > 1)
                        fprintf(stderr, "# pasada %d de %d\n", r + 1, rep);

                for (i = 0; i < N_WHITELIST; i++) {
                        uint32_t v = 0;
                        int rc = read_one(fd, mmr_whitelist[i].off,
                                          mmr_whitelist[i].indexed ? se : 0,
                                          mmr_whitelist[i].indexed ? sh : 0,
                                          &v);
                        if (rc == 0)
                                printf("0x%04X\t%s\t0x%08X\tOK\n",
                                       mmr_whitelist[i].off,
                                       mmr_whitelist[i].name, v);
                        else
                                printf("0x%04X\t%s\t-\t%s\n",
                                       mmr_whitelist[i].off,
                                       mmr_whitelist[i].name, strerror(-rc));
                }

                if (probe) {
                        for (i = 0; i < N_NEGATIVES; i++) {
                                uint32_t v = 0;
                                int rc = read_one(fd, mmr_negatives[i], 0, 0, &v);
                                if (rc == 0)
                                        printf("0x%04X\tNEGATIVO\t0x%08X\tACEPTADO_INESPERADO\n",
                                               mmr_negatives[i], v);
                                else
                                        printf("0x%04X\tNEGATIVO\t-\tRECHAZADO:%s\n",
                                               mmr_negatives[i], strerror(-rc));
                        }
                }

                if (r + 1 < rep && sleepms > 0) {
                        struct timespec ts;
                        ts.tv_sec  = sleepms / 1000;
                        ts.tv_nsec = (long)(sleepms % 1000) * 1000000L;
                        nanosleep(&ts, NULL);
                }
        }

        close(fd);
        return 0;
}