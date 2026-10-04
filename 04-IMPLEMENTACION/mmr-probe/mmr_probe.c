/* mmr_probe.c -- LECTOR DE UN REGISTRO MMIO DE GFX8 POR ioctl, SIN ROOT.
 *
 * INVESTIGACION.  No es parte del driver.  No escribe nada.
 *
 * POR QUE EXISTE, y que resuelve:
 *
 *   El mapa de contadores (08-ARQUITECTURA/CONTADORES-GFX8-MAPA.md) determino que
 *   la unica via de lectura MMIO desde userspace sin privilegios es
 *   AMDGPU_INFO_READ_MMR_REG, y que de las 76 entradas de
 *   vi_allowed_read_registers[] (vi.c:665-742) solo 21 leen hardware de verdad:
 *   las otras 53 devuelven adev->gfx.config.*, que es CACHE DE SOFTWARE.
 *
 *   Y que mmGRBM_STATUS (0x2004) es la PRIMERA entrada de esa lista y NO esta en el
 *   switch de cache, luego cae en `default: return RREG32(reg_offset)`
 *   (vi.c:834-835): es MMIO vivo.  Verificado leyendo el codigo, no supuesto.
 *
 *   Eso convierte en ejecutable, por fin, el discriminante que el usuario pidio:
 *   H1 (GPU ocupado) frente a H6 (inanicion), separando Occupation media de
 *   ESTRUCTURA TEMPORAL.  Un agregado no los separa; la serie si.
 *
 * POR QUE ES SEGURO, y por que no lo es tanto como parece:
 *
 *   - No hay una sola llamada a write() sobre el dispositivo.  El ioctl usado es
 *     el unico que el kernel marca con DRM_RENDER_ALLOW (amdgpu_drv.c:3057), y se
 *     abre el NODO RENDER, no el de control.
 *   - PERO abrir el nodo render puede despertar la GPU: el nodo de censo midio que
 *     esta en D3hot con runtime_status=suspended el 99.52 % del uptime.  Abrir un
 *     cliente DRM es un cliente.  Por eso el programa LEE power/runtime_status
 *     ANTES y DESPUES y lo imprime, para que el efecto de potencia sea OBSERVABLE y
 *     no una sorpresa.  Eso no lo hace reversible: lo hace medido.
 *   - count = 1 siempre.  El kernel aborta el lote con -EFAULT si la peticion cruza
 *     un registro no permitido (amdgpu_kms.c:917) y descarta el lote entero, asi que
 *     un lote grande no es "mas datos": es un modo de fallo.
 *
 * Lo que NO hace, y por tanto no puede dar: ningun trabajo en la GPU, ningun
 * envio, ninguna escritura de registro, ningun reset.  La ocupacion que mide es la
 * de una GPU que estequi la ejecutando algo, y si no lo hay, mediria cero.  Cero
 * aqui significa "nada ejecutandose", no "mal medido": por eso se imprime tambien
 * GRBM_STATUS2, y por eso el consumidor tiene que distinguir los dos casos.
 *
 * USO
 *   mmr_probe [--nodo /dev/dri/renderD129] [--offset 0x2004]
 *             [--muestras N] [--intervalo-ms M] [--json]
 *
 * SALIDA: una linea por muestra con marca temporal monotona, valor bruto, y los
 * campos de GRBM_STATUS decodificados.  Al final, un veredicto explicito.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#include <libdrm/drm.h>
#include <libdrm/amdgpu_drm.h>

/* --- offsets y campos, todos verificados contra el corpus, ninguno supuesto ---
 *
 * gca/gfx_8_0_d.h:        mmGRBM_STATUS  = 0x2004   mmGRBM_STATUS2 = 0x2002
 * gca/gfx_8_0_sh_mask.h:  los 24 campos de GRBM_STATUS, con MASK y __SHIFT.
 *
 * El nombre del macro lleva DOBLE guion bajo ("GRBM_STATUS__GUI_ACTIVE__SHIFT")
 * mientras el driver lo invoca con uno solo via REG_GET_FIELD(v, GRBM_STATUS,
 * GUI_ACTIVE).  Se verificó que el bit 31 y la mascara 0x80000000 son los de
 * GUI_ACTIVE, y no se dedujo del nombre.
 */
#define GRBM_STATUS_ADDR 0x2004u
#define GRBM_STATUS2_ADDR 0x2002u

struct campo {
	const char *nombre;
	uint32_t mascara;
	unsigned shift;
};

/* Ordenado por bit ascendente, tal como sale de gfx_8_0_sh_mask.h. */
static const struct campo CAMPOS[] = {
	{"ME0PIPE0_CMDFIFO_AVAIL", 0x0000000fu,  0},
	{"SRBM_RQ_PENDING",         0x00000020u,  5},
	{"ME0PIPE0_CF_RQ_PENDING",  0x00000080u,  7},
	{"ME0PIPE0_PF_RQ_PENDING",  0x00000100u,  8},
	{"GDS_DMA_RQ_PENDING",      0x00000200u,  9},
	{"DB_CLEAN",                0x00001000u, 12},
	{"CB_CLEAN",                0x00002000u, 13},
	{"TA_BUSY",                 0x00004000u, 14},
	{"GDS_BUSY",                0x00008000u, 15},
	{"WD_BUSY_NO_DMA",          0x00010000u, 16},
	{"VGT_BUSY",                0x00020000u, 17},
	{"IA_BUSY_NO_DMA",          0x00040000u, 18},
	{"IA_BUSY",                 0x00080000u, 19},
	{"SX_BUSY",                 0x00100000u, 20},
	{"WD_BUSY",                 0x00200000u, 21},
	{"SPI_BUSY",                0x00400000u, 22},
	{"BCI_BUSY",                0x00800000u, 23},
	{"SC_BUSY",                 0x01000000u, 24},
	{"PA_BUSY",                 0x02000000u, 25},
	{"DB_BUSY",                 0x04000000u, 26},
	{"CP_COHERENCY_BUSY",       0x10000000u, 28},
	{"CP_BUSY",                 0x20000000u, 29},
	{"CB_BUSY",                 0x40000000u, 30},
	{"GUI_ACTIVE",              0x80000000u, 31},
};
#define N_CAMPOS ((int)(sizeof(CAMPOS) / sizeof(CAMPOS[0])))

/* gfx_v8_0_is_idle(), gfx_v8_0.c:4798-4807:
 *   idle <=> !GUI_ACTIVE  &&  RREG32(mmGRBM_STATUS2) == 0x8
 * Es la unica semantica de estos bits que NO es el nombre.  Se cita como lo que
 * es: una funcion del driver, no una especificacion del hardware.
 */
#define IDLE_STATUS2 0x8u

static const char *NODO_POR_DEFECTO = "/dev/dri/renderD129";
static const char *SYSFS_PM =
	"/sys/bus/pci/devices/0000:01:00.0/power/runtime_status";

static long monotono_ns(void)
{
	struct timespec ts;
	if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
		return -1;
	return (long)ts.tv_sec * 1000000000L + ts.tv_nsec;
}

/* Lectura pura de sysfs.  No escribe, no abre el device, no puede despertarlo. */
static char *leer_runtime_status(void)
{
	static char buf[64];
	int fd = open(SYSFS_PM, O_RDONLY);
	ssize_t n;

	if (fd < 0) {
		snprintf(buf, sizeof buf, "<%s>", strerror(errno));
		return buf;
	}
	n = read(fd, buf, sizeof buf - 1);
	close(fd);
	if (n < 0) {
		snprintf(buf, sizeof buf, "<%s>", strerror(errno));
		return buf;
	}
	while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == '\r'))
		n--;
	buf[n] = '\0';
	return buf;
}

/* EL UNICO ioctl de este programa.  count = 1, siempre.
 * Devuelve 0, o -1 con errno puesto.
 */
static int leer_mmr(int fd, uint32_t byte_offset, uint32_t *out)
{
	struct drm_amdgpu_info info;
	uint32_t valor = 0;
	int rc;

	memset(&info, 0, sizeof info);
	info.return_pointer = (uintptr_t)&valor;
	info.return_size = sizeof valor;
	info.query = AMDGPU_INFO_READ_MMR_REG;
	info.read_mmr_reg.dword_offset = byte_offset / 4u;	/* el kernel cuenta DWORDs */
	info.read_mmr_reg.count = 1;				/* nunca mas: ver cabecera */
	info.read_mmr_reg.instance = 0xffffffffu;
	info.read_mmr_reg.flags = 0;

	rc = ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info);
	if (rc == 0)
		*out = valor;
	return rc;
}

static void usage(const char *argv0)
{
	fprintf(stderr,
		"uso: %s [--nodo DEV] [--offset 0xADDR] [--muestras N]\n"
		"          [--intervalo-ms M] [--json]\n"
		"SOLO LECTURA.  count=1 fijo.  No escribe ningun registro.\n",
		argv0);
}

int main(int argc, char **argv)
{
	const char *nodo = NODO_POR_DEFECTO;
	uint32_t offset = GRBM_STATUS_ADDR;
	long muestras = 8, intervalo_ms = 50;
	int json = 0, fd, i;
	char pm_antes[64], pm_despues[64];
	uint32_t st2 = 0;
	int leido_st2 = 0;
	long t0, t_primero = -1, t_ultimo = -1;
	unsigned distintos = 0;
	uint32_t primero = 0;

	for (i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--nodo") && i + 1 < argc)
			nodo = argv[++i];
		else if (!strcmp(argv[i], "--offset") && i + 1 < argc)
			offset = (uint32_t)strtoul(argv[++i], NULL, 0);
		else if (!strcmp(argv[i], "--muestras") && i + 1 < argc)
			muestras = strtol(argv[++i], NULL, 0);
		else if (!strcmp(argv[i], "--intervalo-ms") && i + 1 < argc)
			intervalo_ms = strtol(argv[++i], NULL, 0);
		else if (!strcmp(argv[i], "--json"))
			json = 1;
		else {
			usage(argv[0]);
			return 2;
		}
	}
	if (muestras < 1 || muestras > 100000) {
		fprintf(stderr, "muestras fuera de rango\n");
		return 2;
	}

	snprintf(pm_antes, sizeof pm_antes, "%s", leer_runtime_status());

	/* El nodo de CONTROL es /dev/dri/card1 y exige el grupo video.  Este programa
	 * no lo abre nunca, y por construccion no puede: solo se le pasa --nodo y el
	 * valor por defecto es el render.  Si alguien pasa --nodo /dev/dri/card1 a mano
	 * sera un fallo de permisos y no un dano: abrir card1 no escribe registros.
	 */
	fd = open(nodo, O_RDWR);
	if (fd < 0) {
		fprintf(stderr,
			"VEREDICTO: NO SE PUDO ABRIR %s: %s\n"
			"  El nodo render es 0666 y deberia abrirse sin privilegios.\n"
			"  Si esto falla, la cadena de supuestos de este programa es falsa.\n",
			nodo, strerror(errno));
		return 3;
	}

	if (!json)
		printf("# nodo=%s offset=0x%04x muestras=%ld intervalo=%ldms\n"
		       "# runtime_status ANTES de abrir: %s\n"
		       "# decodificacion: gca/gfx_8_0_sh_mask.h, 24 campos, verificados\n",
		       nodo, offset, muestras, intervalo_ms, pm_antes);

	t0 = monotono_ns();
	for (i = 0; i < muestras; i++) {
		uint32_t v = 0;
		long t;

		if (leer_mmr(fd, offset, &v) != 0) {
			int e = errno;
			close(fd);
			fprintf(stderr,
				"VEREDICTO: LECTURA RECHAZADA en la muestra %d: %s\n"
				"  offset=0x%04x  errno=%d\n"
				"  -EINVAL significa que el registro NO esta en\n"
				"  vi_allowed_read_registers[] para ESTA ASIC.\n"
				"  -EFAULT con count>1 significa que el lote cruzaba un\n"
				"  registro no permitido; aqui count=1, luego no es eso.\n",
				i, strerror(e), offset, e);
			return 4;
		}
		if (offset == GRBM_STATUS_ADDR && !leido_st2) {
			/* GRBM_STATUS2 solo se lee si el registro pedido es el de
			 * estado, porque es la otra mitad de la definicion de idle.
			 */
			if (leer_mmr(fd, GRBM_STATUS2_ADDR, &st2) == 0)
				leido_st2 = 1;
		}

		t = monotono_ns();
		if (t_primero < 0)
			t_primero = t;
		t_ultimo = t;

		if (i == 0)
			primero = v;
		else if (v != primero)
			distintos++;

		if (!json) {
			int k;
			printf("t=%9.3f ms  0x%08x", (t - t0) / 1e6, v);
			for (k = 0; k < N_CAMPOS; k++) {
				unsigned bit = (v & CAMPOS[k].mascara) >> CAMPOS[k].shift;
				if (bit)
					printf(" %s", CAMPOS[k].nombre);
			}
			if (leido_st2)
				printf("   | STATUS2=0x%08x idle=%s", st2,
				       ((v & 0x80000000u) == 0 && st2 == IDLE_STATUS2)
					       ? "1" : "0");
			printf("\n");
		} else {
			printf("{\"t_ns\":%ld,\"v\":%u,\"status2\":%u,\"status2_leido\":%s}\n",
			       t, v, st2, leido_st2 ? "true" : "false");
		}

		if (i + 1 < muestras && intervalo_ms > 0) {
			struct timespec ts = { intervalo_ms / 1000,
					       (intervalo_ms % 1000) * 1000000L };
			nanosleep(&ts, NULL);
		}
	}
	close(fd);

	snprintf(pm_despues, sizeof pm_despues, "%s", leer_runtime_status());

	if (!json) {
		printf("\n");
		printf("# runtime_status DESPUES: %s%s\n", pm_despues,
		       strcmp(pm_antes, pm_despues)
			   ? "   <-- LA GPU CAMBIO DE ESTADO DE POTENCIA" : "");
		printf("# ventana            : %.1f ms\n", (t_ultimo - t_primero) / 1e6);
		printf("# valores distintos  : %u de %ld muestras\n", distintos, muestras);
		printf("#\n");
	}
	printf("VEREDICTO: LECTURA POSIBLE.  count=1, %ld muestras, sin escrituras.\n",
	       muestras);
	if (distintos == 0)
		printf("  AVISO: valor constante en toda la ventana.  Pode ser idle real,\n"
		       "  y tambien puede ser que lo que se lee no sea MMIO.  NO SE\n"
		       "  DISTINGUE AQUI, y quien use esto tiene que distinguirlo.\n");
	if (strcmp(pm_antes, pm_despues))
		printf("  OBSERVADO: runtime_status %s -> %s.  Abrir el nodo render\n"
		       "  despierta la GPU.  Queda registrado, no revertido.\n",
		       pm_antes, pm_despues);
	return 0;
}