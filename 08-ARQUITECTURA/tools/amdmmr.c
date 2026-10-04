/* amdmmr -- lee la lista blanca de READ_MMR_REG. Solo lectura.
 *
 * Que acota esto. El proyecto tiene 123 huecos clasificados UN_REGISTRO, "se
 * cierra leyendo un registro". La UNICA via de MMIO desde userspace sin root
 * es AMDGPU_INFO_READ_MMR_REG, y el hallazgo 924 ya dijo que tiene lista blanca.
 * Esa lista son 19 registros (soc21.c:287-307). Leerlos acota el alcance real
 * de los 123.
 *
 * Los offsets salen de reg_offset[hwip][inst][seg] + reg, y para GC todos los
 * BASE_IDX son 0, asi que el offset es el del registro. Se prueban los 19.
 *
 * OJO: el kernel hace amdgpu_gfx_off_ctrl(adev,false) antes y (adev,true) despues,
 * alrededor del bucle de lectura. Y aqui hay que decir lo que hace, porque el
 * nombreInvite a error y esta version anterior de este comentario lo decia mal:
 *
 *   - off_ctrl(adev,false) NO apaga el motor.  Desactiva la FUNCION gfx-off,  es
 *     decir: cancela el apagado pendiente del bloque GFX  (cancel_delayed_work_sync)
 *     y, si el bloque ya estaba apagado,  lo vuelve a alimentar
 *     (amdgpu_dpm_set_powergating_by_smu, false) y RE-INICIALIZA los golden
 *     settings del SPM  (amdgpu_gfx_init_spm_golden).
 *   - off_ctrl(adev,true) suelta la peticion  (gfx_off_req_count--),  y si el
 *     recuento llega a cero programa el apagado diferido.
 *
 * MEDIDO que la funcion devuelve VOID:  no hay retorno que comprobar.  Y MEDIDO que
 * si el ASIC no anuncia PP_GFXOFF  las DOS llamadas son no-op
 * (if (!(adev->pm.pp_feature & PP_GFXOFF_MASK)) return;),  de modo que en una
 * tarjeta sin esa feature la lectura es pasiva de verdad.
 *
 * ASI QUE LA CLASE CORRECTA de esta herramienta es CONTROLLED_WRITE sobre el estado
 * de ALIMENTACION del bloque GFX  —transitorio, refcontado, reversible por
 * construccion porque la rama enable=true va DESPUES del bucle y se ejecuta
 * aunque el bucle salga por break con -EFAULT—,  y no READ_ONLY.  Que no escriba
 * no significa que no cambie el hardware.
 *
 * Y por eso el numero de llamadas es exactamente 19 y no un barrido:  la lista
 * blanca de soc21.c:287-307  (soc21_allowed_read_registers[])  tiene 19 entradas,
 * todas SOC15_REG_ENTRY(GC,0,…),  y soc21_read_register devuelve -EINVAL para
 * cualquier otro offset.  Ese 19 esta CONTADO en la tabla del corpus,  no dicho
 * aqui antes de contar.  Y es el de soc21:  soc15, soc24, soc_v1_0, cik, nv, si y
 * vi tienen la suya,  y el numero NO es transferible.
 *
 * Ver el hallazgo 1041.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <drm/amdgpu_drm.h>
#include <drm/drm.h>

static struct { unsigned off; const char *n; } R[] = {
  {0x0da4,"regGRBM_STATUS"},        {0x0da2,"regGRBM_STATUS2"},
  {0x0da5,"regGRBM_STATUS_SE0"},    {0x0da6,"regGRBM_STATUS_SE1"},
  {0x0dae,"regGRBM_STATUS_SE2"},    {0x0daf,"regGRBM_STATUS_SE3"},
  {0x0025,"regSDMA0_STATUS_REG"},   {0x0625,"regSDMA1_STATUS_REG"},
  {0x0f40,"regCP_STAT"},            {0x0f3d,"regCP_STALLED_STAT1"},
  {0x0f3e,"regCP_STALLED_STAT2"},    {0x0f3c,"regCP_STALLED_STAT3"},
  {0x0e28,"regCP_CPF_BUSY_STAT"},   {0x0e29,"regCP_CPF_STALLED_STAT1"},
  {0x0e27,"regCP_CPF_STATUS"},      {0x0e25,"regCP_CPC_BUSY_STAT"},
  {0x0e26,"regCP_CPC_STALLED_STAT1"},{0x0e24,"regCP_CPC_STATUS"},
  {0x13de,"regGB_ADDR_CONFIG"},
  /* dos que NO estan en la lista, para ver que el filtro existe de verdad */
  {0x0000,"NO-listado regVGA_GFX_BASE lo que sea en 0"},
  {0x0013,"NO-listado offset 0x13"},
};

int main(int argc, char **argv) {
  const char *nodo = argc > 1 ? argv[1] : "/dev/dri/renderD129";
  int fd = open(nodo, O_RDWR);
  if (fd < 0) { fprintf(stderr, "open: %s\n", strerror(errno)); return 2; }
  uint32_t v = 0;
  printf("lista blanca de soc21.c:287 -- %d entradas, mas 2 controles negativos\n\n",
         (int)(sizeof R / sizeof R[0]) - 2);
  printf("%-42s %-8s %s\n", "registro", "offset", "leido");
  printf("---------------------------------------------------------------\n");
  int ok = 0;
  for (unsigned i = 0; i < sizeof R / sizeof R[0]; i++) {
    struct drm_amdgpu_info in; memset(&in, 0, sizeof in);
    in.query = AMDGPU_INFO_READ_MMR_REG;
    in.read_mmr_reg.dword_offset = R[i].off;
    in.read_mmr_reg.count = 1;
    in.read_mmr_reg.instance = 0xffffffff;   /* todos los SE/SH */
    in.return_size = sizeof v;
    in.return_pointer = (uint64_t)(uintptr_t)&v;
    errno = 0;
    if (ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &in) == 0) { ok++; printf("%-42s 0x%04x    0x%08x\n", R[i].n, R[i].off, v); }
    else printf("%-42s 0x%04x    ERRNO %s\n", R[i].n, R[i].off, strerror(errno));
  }
  printf("\nleidos %d\n", ok);
  close(fd);
  return 0;
}
