// SPDX-License-Identifier: GPL-2.0
/*
 * rx550_main.c - skeleton of the rx550 exclusive driver, Ronda 1.
 *
 * WHAT THIS IS
 *
 * A character device that answers exactly one ioctl: a version ping. It is
 * deliberately the smallest thing that can be compiled and reviewed, so that the
 * build plumbing, the ABI header and the userspace round trip are proven before
 * anything touches hardware.
 *
 * WHAT THIS IS NOT
 *
 * It does not yet program a GPU. There is no ring submission, no memory
 * management, no interrupt handler, and no fence. The three remaining ioctls are
 * declared in the ABI header with placeholder structs and are not implemented;
 * see the note there about why they are not defined yet.
 *
 * THE STUBS, AND WHY THEY ARE STUBS
 *
 * Both remaining ioctls are declared in the ABI and refuse cleanly. Neither is
 * waiting for somebody to write code; both are waiting for a fact.
 *
 * RX550_IOCTL_SUBMIT_COMPUTE -> -ENOSYS
 * The PM4 packet encoding is established and verified against amdgpu.ko
 * (0xC0031500 x10, 0xC0031502 x1, 0xC0027600 x10, 0xC0017600 x10, 0xC0004600
 * x15; all five counts reproduced). The register layout around it is established
 * too: the grid is COMPUTE_NUM_THREAD_X/Y/Z, and COMPUTE_PGM_RSRC1 holds
 * resource counts, not dimensions.
 *
 * What is missing is a sequence that runs on this ASIC. The one in gfx_v8_0.c
 * is gfx_v8_0_do_edc_gpr_workarounds(), whose first statement is
 *
 *     if (adev->asic_type != CHIP_CARRIZO) return 0;
 *
 * so it is a Carrizo EDC workaround that never executes on Polaris 12, and it
 * loads three different init shaders, not a client shader. A dispatch built from
 * it would be the wrong sequence for the wrong reason, and a malformed one fails
 * by doing nothing. -ENOSYS is the honest answer.
 *
 * RX550_IOCTL_LOAD_FIRMWARE -> -ENOTTY
 * The blob exists and parses: tests/test_firmware_parse.c validates the real
 * polaris12_sdma.bin against the criterion from amdgpu_ucode.c:535. What is
 * missing is the register programming, whose ordering lives in amdgpu_smc.c and
 * is not in this tree. Writing registers without that ordering is not an
 * incomplete implementation, it is a guess executed against live hardware.
 *
 * WHY cdev AND NOT DRM
 *
 * DRM is the right long-term answer and this driver will grow into one. It is
 * not the right answer for the first module, for three reasons that are about
 * risk rather than taste:
 *
 *   1. DRM's core has a large surface that must be right before it is useful:
 *      GEM, sync objects, a modesetting or a compute path, and a device model
 *      with master/DRM-master semantics that a headless compute driver never
 *      uses. Taking all of that on in the first commit means debugging the DRM
 *      core and the hardware at the same time.
 *   2. A char device has one failure mode to reason about: the ioctl encoding
 *      and the struct layout. That is exactly the thing Ronda 1 needs to verify.
 *   3. cdev is a strict subset of what a DRM device would need, so the
 *      migration later is additive rather than a rewrite: /dev/rx550 becomes
 *      the DRM primary node, and the ioctls become drm_ioctls.
 *
 * The cost of this choice is stated plainly: a char device does not give
 * userspace a mapped BAR, and BAR mapping is what a real GPU driver needs. That
 * arrives with the DRM migration, not before.
 *
 * WHY CHAR DEVICE AND NOT A RAW MINOR
 *
 * A single static major number hardcodes a global namespace into the kernel and
 * cannot be allocated dynamically. cdev lets udev create /dev/rx550, so the
 * device node appears only when the module is loaded.
 */

#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/uaccess.h>
#include <linux/version.h>

#include "rx550_ioctl.h"

#define RX550_DEVICE_NAME	"rx550"
#define RX550_CLASS_NAME	"rx550"

/*
 * The ABI structs are shared with userspace. Check the sizes on this side too:
 * if a struct is resized here without the header being updated, the ioctl
 * encoding changes silently and userspace keeps passing the old size.
 *
 * rx550_device_info is 72 bytes, and that number is not 5*4 + 2*8 + 2*4 + 6*4 =
 * 72 by arithmetic alone: there are 4 bytes of padding at offset 20, because
 * gfx_ip_minor ends at 20 and vram_size is a __u64, which the compiler aligns to
 * 8. Verified with offsetof, not by adding. The size was first asserted as 96
 * and then as 64, both wrong; the compiler caught it each time, which is the
 * entire reason these are _Static_assert and not comments.
 */
_Static_assert(sizeof(struct rx550_version) == 24,
	       "rx550_version must stay 24 bytes");
_Static_assert(sizeof(struct rx550_device_info) == 72,
	       "rx550_device_info must stay 72 bytes (4 B padding at offset 20)");

static long rx550_ioctl(struct file *file, unsigned int cmd,
			unsigned long arg);

static dev_t rx550_devt;
static struct cdev rx550_cdev;
static struct class *rx550_class;

static const struct file_operations rx550_fops = {
	.owner		= THIS_MODULE,
	.open		= nonseekable_open,
	.unlocked_ioctl	= rx550_ioctl,
	.compat_ioctl	= compat_ptr_ioctl,
};

/**
 * rx550_ioctl_version - RX550_IOCTL_VERSION: report the driver version.
 * @file: opened device, unused
 * @arg: userspace pointer to struct rx550_version
 * @cmd: the ioctl number
 *
 * Returns 0 on success, -EFAULT if the copy back fails, -ENOTTY if the ioctl
 * number is not one we serve.
 */
static long rx550_ioctl_version(struct file *file, unsigned int cmd,
				unsigned long arg)
{
	struct rx550_version ver;

	(void)file;

	if (cmd != RX550_IOCTL_VERSION)
		return -ENOTTY;

	memset(&ver, 0, sizeof(ver));
	ver.major = 1;
	ver.minor = 0;
	ver.patch = 0;
	/*
	 * The build does not have a git hash available, and inventing one would
	 * be worse than saying so. An empty commit field is honest; a wrong one
	 * is not.
	 */
	strscpy(ver.commit, "unversioned", sizeof(ver.commit));

	if (copy_to_user((void __user *)arg, &ver, sizeof(ver)))
		return -EFAULT;

	return 0;
}

/**
 * rx550_ioctl_device_info - RX550_IOCTL_DEVICE_INFO: NOT IMPLEMENTED.
 *
 * gfx_ip and cu_count would be reported here, and both are read from hardware
 * registers at runtime by the stock driver rather than from a table. Returning
 * -ENOTTY is the honest answer in Ronda 1: returning zeros would be a claim
 * that the values are zero.
 */
static long rx550_ioctl_device_info(struct file *file, unsigned int cmd,
				    unsigned long arg)
{
	(void)file; (void)cmd; (void)arg;
	return -ENOTTY;
}

static long rx550_ioctl(struct file *file, unsigned int cmd,
			unsigned long arg)
{
	switch (cmd) {
	case RX550_IOCTL_VERSION:
		return rx550_ioctl_version(file, cmd, arg);
	case RX550_IOCTL_DEVICE_INFO:
		return rx550_ioctl_device_info(file, cmd, arg);
	default:
		/*
		 * Including SUBMIT_COMPUTE and WAIT_FENCE here deliberately: they
		 * return -ENOTTY like any other unknown ioctl, so a userspace
		 * program that calls them gets a clear error instead of a
		 * placeholder struct interpreted as real.
		 */
		return -ENOTTY;
	}
}

static int __init rx550_init(void)
{
	int rc;

	rc = alloc_chrdev_region(&rx550_devt, 0, 1, RX550_DEVICE_NAME);
	if (rc < 0) {
		pr_err("rx550: alloc_chrdev_region failed: %d\n", rc);
		return rc;
	}

	cdev_init(&rx550_cdev, &rx550_fops);
	rx550_cdev.owner = THIS_MODULE;
	rc = cdev_add(&rx550_cdev, rx550_devt, 1);
	if (rc < 0) {
		pr_err("rx550: cdev_add failed: %d\n", rc);
		goto err_chrdev;
	}

	rx550_class = class_create(RX550_CLASS_NAME);
	if (IS_ERR(rx550_class)) {
		rc = PTR_ERR(rx550_class);
		pr_err("rx550: class_create failed: %d\n", rc);
		goto err_cdev;
	}

	/* DEVICE_NAME constant, so no lifetime bug. */
	if (IS_ERR(device_create(rx550_class, NULL, rx550_devt, NULL,
				 RX550_DEVICE_NAME))) {
		pr_err("rx550: device_create failed\n");
		rc = -ENODEV;
		goto err_class;
	}

	pr_info("rx550: driver loaded\n");
	return 0;

err_class:
	class_destroy(rx550_class);
err_cdev:
	cdev_del(&rx550_cdev);
err_chrdev:
	unregister_chrdev_region(rx550_devt, 1);
	return rc;
}

static void __exit rx550_exit(void)
{
	device_destroy(rx550_class, rx550_devt);
	class_destroy(rx550_class);
	cdev_del(&rx550_cdev);
	unregister_chrdev_region(rx550_devt, 1);
	pr_info("rx550: driver unloaded\n");
}

module_init(rx550_init);
module_exit(rx550_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("RX550 exclusive driver project");
MODULE_DESCRIPTION("Exclusive driver for the RX 550 (Polaris 12, GFX8). Ronda 1: version ping only.");
MODULE_VERSION("1.0.0");
