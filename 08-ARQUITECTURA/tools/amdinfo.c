/* amdinfo -- lectura por ioctl AMDGPU_INFO en ESTA caja, sin privilegios.
 *
 * POR QUE ESTE INSTRUMENTO EXISTE
 *
 * El proyecto tiene 123 huecos clasificados como UN_REGISTRO, que la
 * herramienta describe como "se cierra leyendo un registro". Eso suena
 * accionable, pero hay una pregunta previa: ¿existe ruta SIN PRIVILEGIOS para
 * leer estado de la tarjeta? Medido el 2026-10-03:
 *
 *   /sys/kernel/debug/dri/1/   montado, modo 0700 root; sudo pide contrasena
 *   /dev/dri/card1              crw-rw----+ root:video; este usuario NO esta
 *                               en el grupo video -> EACCES en los 19 queries
 *   /dev/dri/renderD129         crw-rw-rw- -> 15 de 19 responden
 *
 * El descriptor tiene que ser O_RDWR porque la capa DRM comprueba permisos de
 * escritura ANTES de dejar pasar cualquier ioctl, tambien los de lectura.
 * Medido: con O_RDONLY, 0 de 19. Eso NO significa que se escriba nada --
 * AMDGPU_INFO_* es lectura por definicion -- pero si significa que el contrato
 * WRITES_GPU=no de una herramienta que abre O_RDWR no lo dice.
 *
 * La UAPI correcta (las tres correcciones que hizo falta para que compilara):
 *   el sub-id NO va en el buffer de retorno, va en la union de drm_amdgpu_info:
 *     query_fw.fw_type   para AMDGPU_INFO_FW_VERSION
 *     query_hw_ip.type   para AMDGPU_INFO_HW_IP_INFO
 *     sensor_info.type   para AMDGPU_INFO_SENSOR
 *   y drm_amdgpu_info_vram_gtt tiene {vram_size, vram_cpu_accessible_size,
 *   gtt_size}, no los nombres que yo asumia.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <inttypes.h>
#include <sys/ioctl.h>
#include <drm/amdgpu_drm.h>
#include <drm/drm.h>

static unsigned char buf[8192] __attribute__((aligned(8)));

static int io(int fd, struct drm_amdgpu_info *info) {
  memset(buf, 0, sizeof buf);
  info->return_pointer = (uint64_t)(uintptr_t)buf;
  errno = 0;
  return ioctl(fd, DRM_IOCTL_AMDGPU_INFO, info);
}

static void u32n(const char *n, unsigned v) { printf("  %-28s %u\n", n, v); }

int main(int argc, char **argv) {
  const char *nodo = argc > 1 ? argv[1] : "/dev/dri/renderD129";
  int fd = open(nodo, O_RDWR);
  if (fd < 0) { fprintf(stderr, "open %s: %s\n", nodo, strerror(errno)); return 2; }
  printf("nodo %s (O_RDWR exigido por la capa DRM)\n", nodo);
  printf("device_id leido abajo tiene que ser 0x699f: si no, esto no es la RX550\n\n");

  struct drm_amdgpu_info in;
  memset(&in, 0, sizeof in);

  printf("=== DEV_INFO ===\n");
  memset(&in, 0, sizeof in);
  in.query = AMDGPU_INFO_DEV_INFO;
  in.return_size = sizeof(struct drm_amdgpu_info_device);
  if (io(fd, &in) == 0) {
    struct drm_amdgpu_info_device d;
    memcpy(&d, buf, sizeof d);
    u32n("device_id", d.device_id);
    printf("  %-28s 0x%04x %s\n", "  ^ DEBE SER 699f", d.device_id,
           d.device_id == 0x699f ? "OK, es la RX550" : "NO ES LA RX550");
    u32n("chip_rev", d.chip_rev); u32n("external_rev", d.external_rev);
    u32n("pci_rev", d.pci_rev); u32n("family", d.family);
    u32n("num_shader_engines", d.num_shader_engines);
    u32n("num_shader_arrays_per_engine", d.num_shader_arrays_per_engine);
    u32n("num_rb_pipes", d.num_rb_pipes);
    u32n("num_hw_gfx_contexts", d.num_hw_gfx_contexts);
    u32n("cu_active_number", d.cu_active_number);
    u32n("enabled_rb_pipes_mask", d.enabled_rb_pipes_mask);
    u32n("pcie_gen", d.pcie_gen);
    u32n("gpu_counter_freq (kHz)", d.gpu_counter_freq);
    printf("  %-28s %" PRIu64 " kHz = %.0f MHz\n", "max_engine_clock",
           (uint64_t)d.max_engine_clock, (double)d.max_engine_clock / 1000.0);
    printf("  %-28s %" PRIu64 " kHz = %.0f MHz\n", "max_memory_clock",
           (uint64_t)d.max_memory_clock, (double)d.max_memory_clock / 1000.0);
    printf("  %-28s 0x%08x  <-- la cabecera lo declara INVALID\n",
           "cu_ao_mask (NO USAR)", d.cu_ao_mask);
    printf("  cu_bitmap[0]              0x%08x 0x%08x 0x%08x 0x%08x\n",
           d.cu_bitmap[0][0], d.cu_bitmap[0][1], d.cu_bitmap[0][2], d.cu_bitmap[0][3]);
  } else printf("  ERRNO %s\n", strerror(errno));

  printf("\n=== VRAM_GTT ===\n");
  memset(&in, 0, sizeof in);
  in.query = AMDGPU_INFO_VRAM_GTT;
  in.return_size = sizeof(struct drm_amdgpu_info_vram_gtt);
  if (io(fd, &in) == 0) {
    struct drm_amdgpu_info_vram_gtt v;
    memcpy(&v, buf, sizeof v);
    printf("  %-28s %" PRIu64 "  (%.0f MiB)\n", "vram_size",
           (uint64_t)v.vram_size, (double)v.vram_size/1048576.0);
    printf("  %-28s %" PRIu64 "  (%.0f MiB)\n", "vram_cpu_accessible_size",
           (uint64_t)v.vram_cpu_accessible_size,
           (double)v.vram_cpu_accessible_size/1048576.0);
    printf("  %-28s %" PRIu64 "  (%.0f MiB)\n", "gtt_size",
           (uint64_t)v.gtt_size, (double)v.gtt_size/1048576.0);
  } else printf("  ERRNO %s\n", strerror(errno));

  printf("\n=== HW IP (los bloques que el kernel instancia) ===\n");
  unsigned n_ip = 0;
  memset(&in, 0, sizeof in);
  in.query = AMDGPU_INFO_HW_IP_COUNT; in.return_size = 4;
  if (io(fd, &in) == 0) { memcpy(&n_ip, buf, 4); }
  printf("  bloques IP presentes: %u\n", n_ip);
  for (unsigned i = 0; i < n_ip; i++) {
    struct drm_amdgpu_info_hw_ip h;
    memset(&in, 0, sizeof in);
    memset(&h, 0, sizeof h);
    in.query = AMDGPU_INFO_HW_IP_INFO;
    in.query_hw_ip.type = i; in.query_hw_ip.ip_instance = 0;
    in.return_size = sizeof h;
    if (io(fd, &in) == 0) {
      memcpy(&h, buf, sizeof h);
      /* ip_discovery_version: bits 23:16 major, 15:8 minor, 7:0 revision.
       * El hallazgo 231 dice que este campo "cierra gfx hwip"; aqui se ve el
       * numero entero, que es lo que habria que contrastar. */
      unsigned v = h.ip_discovery_version;
      printf("   ip_discovery_version=%-3u  major=%u minor=%u revision=%u   "
             "available_rings=0x%x  ib_start_align=%u ib_size_align=%u\n",
             v, (v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff,
             h.available_rings, h.ib_start_alignment, h.ib_size_alignment);
    }
  }

  printf("\n=== FW_VERSION (firmware que el kernel cargo) ===\n");
  struct { unsigned t; const char *n; } fws[] = {
    {AMDGPU_INFO_FW_VCE,"VCE"},{AMDGPU_INFO_FW_UVD,"UVD"},{AMDGPU_INFO_FW_GMC,"GMC"},
    {AMDGPU_INFO_FW_GFX_ME,"GFX_ME"},{AMDGPU_INFO_FW_GFX_PFP,"GFX_PFP"},
    {AMDGPU_INFO_FW_GFX_CE,"GFX_CE"},{AMDGPU_INFO_FW_GFX_RLC,"GFX_RLC"},
    {AMDGPU_INFO_FW_GFX_MEC,"GFX_MEC"},{AMDGPU_INFO_FW_SMC,"SMC"},
    {AMDGPU_INFO_FW_SDMA,"SDMA"},{AMDGPU_INFO_FW_SOS,"SOS"},{AMDGPU_INFO_FW_ASD,"ASD"},
    {AMDGPU_INFO_FW_VCN,"VCN"},{AMDGPU_INFO_FW_DMCU,"DMCU"},
  };
  for (unsigned i = 0; i < sizeof fws/sizeof fws[0]; i++) {
    struct drm_amdgpu_info_firmware fw;
    memset(&in, 0, sizeof in); memset(&fw, 0, sizeof fw);
    in.query = AMDGPU_INFO_FW_VERSION;
    in.query_fw.fw_type = fws[i].t; in.query_fw.ip_instance = 0;
    in.return_size = sizeof fw;
    if (io(fd, &in) == 0) {
      memcpy(&fw, buf, sizeof fw);
      printf("  FW_%-8s ver=%-4u (0x%08x)  feature=0x%08x\n",
             fws[i].n, fw.ver, fw.ver, fw.feature);
    } else printf("  FW_%-8s ERRNO %s\n", fws[i].n, strerror(errno));
  }

  printf("\n=== SENSOR ===\n");
  struct { unsigned t; const char *n; } sens[] = {
    {AMDGPU_INFO_SENSOR_GFX_SCLK,"GFX_SCLK"},{AMDGPU_INFO_SENSOR_GFX_MCLK,"GFX_MCLK"},
    {AMDGPU_INFO_SENSOR_GPU_TEMP,"GPU_TEMP"},{AMDGPU_INFO_SENSOR_GPU_LOAD,"GPU_LOAD"},
    {AMDGPU_INFO_SENSOR_GPU_AVG_POWER,"GPU_AVG_POWER"},
    {AMDGPU_INFO_SENSOR_VDDNB,"VDDNB"},{AMDGPU_INFO_SENSOR_VDDGFX,"VDDGFX"},
    {AMDGPU_INFO_SENSOR_GPU_INPUT_POWER,"GPU_INPUT_POWER"},
  };
  for (unsigned i = 0; i < sizeof sens/sizeof sens[0]; i++) {
    int32_t sensor_val = 0;
    memset(&in, 0, sizeof in); memset(&sensor_val, 0, sizeof sensor_val);
    in.query = AMDGPU_INFO_SENSOR;
    in.sensor_info.type = sens[i].t;
    in.return_size = 4;
    if (io(fd, &in) == 0) {
      memcpy(&sensor_val, buf, 4);
      switch (sens[i].t) {
        case AMDGPU_INFO_SENSOR_GFX_SCLK:
        case AMDGPU_INFO_SENSOR_GFX_MCLK:
          printf("  %-16s %d  = %.0f MHz\n", sens[i].n, sensor_val, (double)sensor_val/10.0); break;
        case AMDGPU_INFO_SENSOR_GPU_LOAD:
          printf("  %-16s %d %%   (el driver lo llama 'average graphics activity')\n", sens[i].n, (int32_t)sensor_val); break;
        case AMDGPU_INFO_SENSOR_GPU_AVG_POWER:
        case AMDGPU_INFO_SENSOR_GPU_INPUT_POWER:
          printf("  %-16s %.1f W\n", sens[i].n, (double)sensor_val/1000.0); break;
        default: printf("  %-16s %d\n", sens[i].n, (int32_t)sensor_val); break;
      }
    } else printf("  %-16s ERRNO %s\n", sens[i].n, strerror(errno));
  }

  printf("\n=== MEMORY (vis_VRAM / heaps) ===\n");
  unsigned vis = 0;
  memset(&in, 0, sizeof in);
  in.query = AMDGPU_INFO_VIS_VRAM_USAGE; in.return_size = 4;
  if (io(fd, &in) == 0) { memcpy(&vis, buf, 4); printf("  vis_vram_usage %u\n", vis); }

  close(fd);
  return 0;
}
