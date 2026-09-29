// SPDX-License-Identifier: GPL-2.0
/*
 * test_firmware_load.c - checks that rx550_load_firmware() fails CORRECTLY.
 *
 * This test is not here to see firmware load. Firmware loading is not
 * implemented and should not be, so there is no success path to test. What it
 * tests is that every failure path fails the way it claims to.
 *
 * Why that is worth a test
 *
 * A stub that returns 0 is the worst outcome available: the caller believes the
 * GPU was programmed, and the program diverges later, far from the call. A stub
 * that returns -1 is only half a fix -- it must fail with an errno the caller
 * can act on, and it must not fail for the wrong reason. A stub that returns
 * ENOTTY instead of ENOSYS tells a caller to look at its ioctl encoding when the
 * real problem is that the feature is not written. Those are different bugs and
 * they are worth telling apart.
 *
 * The cases below are, on the current driver, deterministic. Every one of them
 * should fail BEFORE touching /dev/rx550, because the library validates its
 * arguments first. That is itself a property worth asserting: an argument check
 * that runs after open() turns a client bug into a dependency on the module
 * being loaded.
 *
 * Exit 0 if every case behaves as documented, 1 otherwise.
 */

#include <errno.h>
#include <stdio.h>
#include <string.h>

#include "../userspace/librx550.h"

static int failures;
static int checks;

static void check(int cond, const char *what, const char *detail)
{
	checks++;
	if (cond) {
		printf("  [ OK ] %s\n", what);
	} else {
		printf("  [FAIL] %s -- %s\n", what, detail);
		failures++;
	}
}

/* Assert that a call fails with a SPECIFIC errno, not merely that it fails. */
static void expect_errno(const char *what, int want, int (*fn)(const void *, size_t),
			 const void *arg, size_t len)
{
	int rc, got;

	errno = 0;
	rc = fn(arg, len);
	got = errno;

	if (rc == 0) {
		char buf[128];
		snprintf(buf, sizeof buf,
			 "returned SUCCESS (errno was %d); a stub that claims to have "
			 "loaded firmware is the failure this test exists to catch", got);
		check(0, what, buf);
		return;
	}
	if (got != want) {
		char buf[128];
		snprintf(buf, sizeof buf, "returned %d with errno %d (%s), expected errno %d (%s)",
			 rc, got, strerror(got), want, strerror(want));
		check(0, what, buf);
		return;
	}
	check(1, what, "");
}

int main(void)
{
	static const unsigned char blob[64] = { 0 };

	printf("=== test_firmware_load: rx550_load_firmware() failure paths ===\n");
	printf("    the driver does not implement firmware loading; that is the\n");
	printf("    expected state, not a defect. See kernel/rx550_abi.h.\n\n");

	printf("1. Argument validation, before any device access:\n");
	/* A null blob must be caught without opening /dev/rx550. If it were not,
	 * these two cases would report ENOENT instead of EINVAL, and a client
	 * bug would look like a missing module. */
	expect_errno("null blob -> EINVAL, not ENOENT", EINVAL,
		     rx550_load_firmware, NULL, sizeof(blob));
	expect_errno("zero size -> EINVAL, not ENOENT", EINVAL,
		     rx550_load_firmware, blob, 0);

	printf("\n2. With valid arguments, the ioctl itself must refuse:\n");
	/*
	 * The module is not loaded, so this fails at open() with ENOENT and never
	 * reaches the ioctl. That is the correct behaviour on this host, and it
	 * means the ENOSYS path cannot be exercised without a loaded module --
	 * stated rather than asserted, because claiming coverage here would be the
	 * "test that passes without testing" pattern.
	 */
	{
		int rc, got;

		errno = 0;
		rc = rx550_load_firmware(blob, sizeof(blob));
		got = errno;
		if (rc == 0) {
			check(0, "valid arguments must not report success", "returned 0");
		} else if (got == ENOENT) {
			printf("  [ -- ] valid arguments -> ENOENT (module not loaded; the\n"
			       "         ioctl path is NOT covered on this host)\n");
		} else if (got == ENOSYS) {
			printf("  [ OK ] valid arguments -> ENOSYS, the driver refused it\n");
		} else {
			char buf[128];
			snprintf(buf, sizeof buf, "unexpected errno %d (%s); expected ENOENT "
				 "or ENOSYS", got, strerror(got));
			check(0, "valid arguments fail as documented", buf);
		}
		checks++;
	}

	printf("\n3. Submit is a stub and must say so:\n");
	{
		int rc, got;

		errno = 0;
		rc = rx550_submit_compute(blob, sizeof(blob));
		got = errno;
		if (rc == 0) {
			check(0, "rx550_submit_compute must not report success",
			      "returned 0; the GFX8 PM4 encoding is not established");
		} else if (got == ENOSYS) {
			check(1, "rx550_submit_compute -> ENOSYS, correct for a stub", "");
		} else {
			char buf[128];
			snprintf(buf, sizeof buf, "errno %d (%s), expected ENOSYS",
				 got, strerror(got));
			check(0, "rx550_submit_compute fails with ENOSYS", buf);
		}
	}

	printf("\n4. ABI layout, shared with the kernel:\n");
	{
		/* These must match the _Static_asserts on the kernel side. Ronda 1
		 * showed what happens when they do not: the build fails, which is
		 * the desired outcome. */
		struct rx550_abi_version v;

		memset(&v, 0, sizeof(v));
		v.major = RX550_ABI_VERSION_MAJOR;
		v.minor = RX550_ABI_VERSION_MINOR;
		v.patch = RX550_ABI_VERSION_PATCH;

		check(sizeof(struct rx550_abi_version) == RX550_ABI_VERSION_SIZE,
		      "abi_version size matches the ABI header constant", "");
		check(sizeof(struct rx550_fw_blob) == RX550_FW_BLOB_SIZE,
		      "fw_blob size matches the ABI header constant", "");
		check(sizeof(struct rx550_ioctl_load_firmware) == RX550_LOAD_FIRMWARE_SIZE,
		      "load_firmware size matches the ABI header constant", "");
	}

	printf("\n5. IOCTL numbers are frozen:\n");
	check(RX550_IOCTL_NR_VERSION == 0x00, "0x00 VERSION unchanged", "");
	check(RX550_IOCTL_NR_DEVICE_INFO == 0x01, "0x01 DEVICE_INFO unchanged", "");
	check(RX550_IOCTL_NR_SUBMIT_COMPUTE == 0x02, "0x02 SUBMIT_COMPUTE unchanged", "");
	check(RX550_IOCTL_NR_WAIT_FENCE == 0x03, "0x03 WAIT_FENCE unchanged", "");
	check(RX550_IOCTL_NR_LOAD_FIRMWARE == 0x04,
	      "0x04 LOAD_FIRMWARE appended, nothing renumbered", "");

	printf("\n%d checks, %d failure(s)\n", checks, failures);
	if (failures) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	printf("\nNOT covered: the ENOSYS path of a loaded driver. Firmware loading is\n"
	       "not implemented, and the module cannot be loaded on this host\n"
	       "(CONFIG_SECURITY_LOCKDOWN_LSM=y, unsigned modules rejected), so that\n"
	       "path is unexercised rather than passing.\n");
	return 0;
}
