// SPDX-License-Identifier: GPL-2.0
/*
 * test_version_ioctl.c - userspace round trip for RX550_IOCTL_VERSION.
 *
 * The point of this test is not that the version is 1.0.0. It is that the
 * userspace header, the kernel header and the ioctl encoding agree: if the
 * struct is resized on one side only, the _IOR encoding changes and this test
 * fails with ENOTTY or a garbage version instead of silently working.
 *
 * It cannot pass on a host where the module is not loaded, which is the current
 * state (see kernel/README.md on module signing). The failure path is therefore
 * a real path, not an edge case, and it says which cause it found.
 *
 * Exit 0 on success, 1 on any failure.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include "../kernel/rx550_ioctl.h"

/* The sizes must match what the module asserts. See kernel/rx550_main.c. */
_Static_assert(sizeof(struct rx550_version) == 24,
	       "rx550_version must stay 24 bytes on both sides");
_Static_assert(sizeof(struct rx550_device_info) == 72,
	       "rx550_device_info must stay 72 bytes on both sides "
	       "(4 B padding at offset 20)");

int main(void)
{
	struct rx550_version ver;
	const char *path = "/dev/rx550";
	int fd, rc;

	memset(&ver, 0, sizeof(ver));

	fd = open(path, O_RDWR);
	if (fd < 0) {
		/*
		 * The usual cause on this host: the module is not loaded, or it
		 * could not be loaded. Distinguish "no such device" from anything
		 * else, because they mean different things.
		 */
		if (errno == ENOENT)
			fprintf(stderr, "FAIL: %s does not exist. "
				"Is the module loaded? (insmod rx550.ko)\n", path);
		else if (errno == ENXIO || errno == EPERM)
			fprintf(stderr, "FAIL: open %s: %s. "
				"Possibly lockdown rejecting an unsigned module.\n",
				path, strerror(errno));
		else
			fprintf(stderr, "FAIL: open %s: %s\n", path, strerror(errno));
		return 1;
	}

	rc = ioctl(fd, RX550_IOCTL_VERSION, &ver);
	if (rc < 0) {
		/*
		 * ENOTTY here means the encoding disagrees: the struct this
		 * binary was built against is not the one the module serves.
		 * That is the failure this test exists to catch.
		 */
		if (errno == ENOTTY)
			fprintf(stderr, "FAIL: ioctl returned ENOTTY. The _IOR encoding "
				"disagrees with the module: struct size mismatch "
				"between kernel and userspace headers.\n");
		else
			fprintf(stderr, "FAIL: ioctl: %s\n", strerror(errno));
		close(fd);
		return 1;
	}

	printf("rx550 driver version %u.%u.%u\n", ver.major, ver.minor, ver.patch);
	printf("  commit: %s\n", ver.commit);
	printf("  struct rx550_version: %zu bytes\n", sizeof(ver));

	close(fd);
	printf("PASS\n");
	return 0;
}
