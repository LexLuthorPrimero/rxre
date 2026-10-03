/* rx550_hold - AGENT-22 research instrument
 * PURPOSE: keep amdgpu runtime-PM resumed so DPM and hwmon sysfs become readable.
 * WHY: on this target every pp_dpm_ clock read and every hwmon read returns EBUSY
 *      while the device is runtime-suspended, because
 *      amdgpu_pm_get_access_if_active() uses pm_runtime_get_if_active(),
 *      which never resumes. Holding a render-node fd is enough; no root
 *      required. renderD129 is mode 0666.
 * SCOPE/HARDWARE: 1002:699f rev c7 only. Submits NO GPU work. Writes NO attribute.
 * BUILD: gcc -O2 -o rx550_hold rx550_hold.c
 * USAGE: rx550_hold <seconds> [rendernode]
 * SELF-TEST: with the GPU idle, "cat pp_dpm_sclk" must fail EBUSY; while this
 *   holds, the same read must succeed.
 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	int secs = (argc > 1) ? atoi(argv[1]) : 5;
	const char *node = (argc > 2) ? argv[2] : "/dev/dri/renderD129";
	int fd = open(node, O_RDWR | O_CLOEXEC);

	if (fd < 0) {
		fprintf(stderr, "OPEN_FAIL %s\n", node);
		return 2;
	}
	fprintf(stderr, "HOLDING %s fd=%d for %ds\n", node, fd, secs);
	fflush(stderr);
	sleep((unsigned)secs);
	close(fd);
	fprintf(stderr, "RELEASED\n");
	return 0;
}
