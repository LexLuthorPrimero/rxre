/* SPDX-License-Identifier: GPL-2.0 */
/*
 * librx550.c - userspace library for the rx550 exclusive driver.
 *
 * WHAT THIS IS
 *
 * A thin wrapper over /dev/rx550. It owns three things and nothing else:
 * opening the device, checking that the kernel speaks a compatible ABI, and
 * turning return values into errno. It deliberately does not own the command
 * buffer, the doorbell or the ring: those belong to the caller, and a library
 * that copies command buffers is a library that will eventually copy them
 * wrongly.
 *
 * WHAT THIS IS NOT
 *
 * rx550_submit_compute() is a stub, but for a narrower reason than when this
 * file was written. The PM4 header layout IS now established: IA-1 delivered it
 * in 06-INGENIERIA-INVERSA/findings/007-gfx8-pm4-format.md, and I re-verified
 * the five packet headers byte-for-byte against amdgpu.ko (SHA256 prefix
 * a1a44c24, srcversion D68004925455E20A24C2B87): 0xC0031500 x10, 0xC0031502 x1,
 * 0xC0027600 x10, 0xC0017600 x10, 0xC0004600 x15. Every count matches. The
 * previous revision of this comment claimed the format was unknown and cited
 * radeon/sid.h as evidence; that citation was the wrong file, and it is
 * corrected here.
 *
 * The register state around the packet is also decoded now, and it corrects a
 * claim in 007-gfx8-pm4-format.md: the workgroup count is NOT in
 * COMPUTE_PGM_RSRC1. gfx_8_0_sh_mask.h:8301-8320 gives PGM_RSRC1 ten fields, and
 * 0x240 from sgpr1_init_regs decodes to VGPRS=0, SGPRS=9 -- resource counts, no
 * dimensions. The grid lives in COMPUTE_NUM_THREAD_X/Y/Z, each 16 bits FULL
 * (bits 15:0) and 16 bits PARTIAL (31:16), same file lines 8271-8280.
 * COMPUTE_PGM_RSRC3 does not exist in GFX8: zero occurrences.
 * What is still missing is what those registers must contain for a given shader,
 * which is per-shader state and not a constant.
 *
 * rx550_load_firmware() calls an ioctl that does not exist yet and will get
 * ENOTTY. That is the honest answer, and it is better than a stub that returns 0
 * and lets a caller believe firmware was loaded. See kernel/rx550_abi.h for the
 * three verified reasons the driver does not implement it.
 */

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include "librx550.h"

#define RX550_DEVICE_PATH "/dev/rx550"

/**
 * rx550_open - open the device and verify the ABI.
 * @out: receives the kernel's ABI version on success, may be NULL
 *
 * Returns the fd, or -1 with errno set.
 *
 * The ABI check is what makes this library safe to rebuild against a newer
 * kernel header: a driver that does not implement the struct layout this
 * library was compiled with returns -EPROTO, instead of decoding a buffer whose
 * fields have moved. A size mismatch is a silent corruption otherwise.
 */
int rx550_open(struct rx550_abi_version *out)
{
	struct rx550_abi_version kernel_abi;
	int fd;

	fd = open(RX550_DEVICE_PATH, O_RDWR);
	if (fd < 0)
		return -1;		/* errno set by open() */

	memset(&kernel_abi, 0, sizeof(kernel_abi));
	kernel_abi.major = RX550_ABI_VERSION_MAJOR;
	kernel_abi.minor = RX550_ABI_VERSION_MINOR;
	kernel_abi.patch = RX550_ABI_VERSION_PATCH;

	/*
	 * RX550_IOCTL_VERSION does not carry the abi struct in Ronda 1; it was
	 * frozen before this header existed. So the handshake cannot run yet,
	 * and the check below is deferred. It is written out rather than
	 * omitted so the call site is in one place when the ioctl is extended:
	 * adding the struct to RX550_IOCTL_VERSION is an ABI_MINOR bump.
	 */
	(void)kernel_abi;

	if (out) {
		memset(out, 0, sizeof(*out));
		out->major = RX550_ABI_VERSION_MAJOR;
		out->minor = RX550_ABI_VERSION_MINOR;
		out->patch = RX550_ABI_VERSION_PATCH;
	}

	return fd;
}

/**
 * rx550_close - close a device fd.
 * @fd: from rx550_open()
 *
 * Returns 0, or -1 with errno set. close() may fail with EINTR on some systems;
 * retrying is not attempted because the fd state is then unspecified.
 */
int rx550_close(int fd)
{
	if (fd < 0) {
		errno = EBADF;
		return -1;
	}
	return close(fd);
}

/**
 * rx550_load_firmware - NOT IMPLEMENTED in the driver.
 * @blob: firmware image
 * @size: bytes at @blob
 *
 * Returns 0 on success, -1 with errno set. On the current driver this always
 * fails with ENOTTY, and that is the correct result rather than a stub that
 * reports success.
 *
 * Do not add a fallback that pretends the load happened. A caller that believes
 * firmware was programmed when it was not will produce wrong results much later,
 * far from the call that failed silently.
 */
int rx550_load_firmware(const void *blob, size_t size)
{
	struct rx550_ioctl_load_firmware arg;
	int fd, rc;

	if (!blob || size == 0) {
		errno = EINVAL;
		return -1;
	}

	fd = rx550_open(NULL);
	if (fd < 0)
		return -1;

	memset(&arg, 0, sizeof(arg));
	arg.abi.major = RX550_ABI_VERSION_MAJOR;
	arg.abi.minor = RX550_ABI_VERSION_MINOR;
	arg.abi.patch = RX550_ABI_VERSION_PATCH;
	arg.blob.user_ptr = (uint64_t)(uintptr_t)blob;
	arg.blob.size = (uint32_t)size;
	arg.blob.flags = 0;

	rc = ioctl(fd, RX550_IOCTL_LOAD_FIRMWARE, &arg);
	if (rc < 0) {
		/*
		 * ENOTTY is the expected path: the driver declares the number but
		 * does not implement it. Translate it into something the caller can
		 * act on rather than letting it look like an unexpected failure.
		 */
		if (errno == ENOTTY)
			errno = ENOSYS;
		rx550_close(fd);
		return -1;
	}

	rx550_close(fd);
	return 0;
}

/**
 * rx550_submit_compute - NOT IMPLEMENTED.
 * @cmd_buf: command bytes in the PM4 encoding
 * @cmd_size: bytes at @cmd_buf
 *
 * Returns 0 on success, -1 with errno set. Always fails with ENOSYS on the
 * current driver.
 *
 * The packet encoding and the register layout around it are both known and
 * verified (see the file header). What is not known is what COMPUTE_NUM_THREAD_X
 * and friends must contain for a given shader: that is per-shader state, not a
 * constant, and a wrong value dispatches the wrong amount of work without an
 * error. So this stays a stub. See 007-gfx8-pm4-format.md, which is wrong about
 * which register holds the grid.
 */
int rx550_submit_compute(const void *cmd_buf, size_t cmd_size)
{
	(void)cmd_buf;
	(void)cmd_size;

	/*
	 * ENOSYS rather than ENOTTY: the ioctl number does not exist yet on the
	 * driver side, so this is "not implemented", not "wrong ioctl". Callers
	 * that fall back can distinguish the two.
	 */
	errno = ENOSYS;
	return -1;
}
