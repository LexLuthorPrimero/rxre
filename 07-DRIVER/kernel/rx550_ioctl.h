/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_ioctl.h - user/kernel ABI for the rx550 exclusive driver.
 *
 * The header is shared verbatim between the module and the userspace test; that
 * is the whole point of putting the structs and the _IOR/_IOWR encoding in one
 * place. A struct that drifts between kernel and userspace is the classic way a
 * driver ends up writing past a userspace buffer, so the sizes below are checked
 * on both sides with _Static_assert rather than trusted.
 *
 * Numbers are fixed forever. IOCTL 0x00 already answered in Ronda 1; a number
 * that gets reused for a different meaning breaks every binary built against the
 * old header, silently, because the ioctl returns success either way.
 */
#ifndef _UAPI_RX550_IOCTL_H
#define _UAPI_RX550_IOCTL_H

#include <linux/types.h>
#include <linux/ioctl.h>

#define RX550_IOCTL_MAGIC 'R'

/*
 * 0x00 - version string. Read-only, fixed-size struct.
 * 0x01 - device properties. Read-only; NOT IMPLEMENTED in Ronda 1. It will
 *        report the gfx generation, which is still NOT_DETERMINED in this
 *        project: the stock amdgpu reads it from hardware registers at runtime
 *        rather than from a table, so it cannot be answered from source.
 * 0x02 - compute submit. NOT IMPLEMENTED. The encoding is the whole hard part
 *        of this project and is deliberately left undefined until IA-1 has
 *        reported the amdgpu IOCTLs and the PM4 packet formats.
 * 0x03 - wait on a fence. NOT IMPLEMENTED. The struct below is a placeholder
 *        with no agreed layout and MUST NOT be used.
 */
#define RX550_IOCTL_VERSION       _IOR(RX550_IOCTL_MAGIC, 0x00, \
                                      struct rx550_version)
#define RX550_IOCTL_DEVICE_INFO   _IOR(RX550_IOCTL_MAGIC, 0x01, \
                                      struct rx550_device_info)
#define RX550_IOCTL_SUBMIT_COMPUTE _IOWR(RX550_IOCTL_MAGIC, 0x02, \
                                        struct rx550_submit_compute)
#define RX550_IOCTL_WAIT_FENCE    _IOWR(RX550_IOCTL_MAGIC, 0x03, \
                                       struct rx550_wait_fence)

/** Driver version. Fixed size so the ioctl encoding is stable. */
struct rx550_version {
	__u32 major;
	__u32 minor;
	__u32 patch;
	char   commit[12];	/**< short git hash, NUL-padded */
};

/**
 * Device properties.
 *
 * gfx_ip is the GFX generation as read from hardware, not as inferred from the
 * PCI device ID. On this host it is NOT_DETERMINED: amdgpu discovers it at
 * runtime in amdgpu_discovery_get_gfx_info() and there is no ASIC table in
 * soc15.c to read it from. See the note in kernel/README.md.
 */
struct rx550_device_info {
	__u32 pci_vendor;
	__u32 pci_device;
	__u32 gfx_ip;		/**< NOT_DETERMINED in Ronda 1 */
	__u32 gfx_ip_major;	/**< 0 if unknown */
	__u32 gfx_ip_minor;	/**< 0 if unknown */
	__u64 vram_size;
	__u64 gtt_size;
	__u32 cu_count;		/**< also NOT_DETERMINED: read from RLC_CU_BUSY */
	__u32 simd_width;
	__u32 reserved[6];
};

/**
 * Compute submit.
 *
 * PLACEHOLDER. No agreed layout. The real structure needs a userspace pointer
 * to a command buffer, a size, a ring index and a doorbell offset, and every
 * one of those has to match hardware behaviour that has not been established
 * yet. Defining it now would freeze a guess into the ABI.
 */
struct rx550_submit_compute {
	__u64 reserved[8];
};

/**
 * Fence wait.
 *
 * PLACEHOLDER, for the same reason as rx550_submit_compute.
 */
struct rx550_wait_fence {
	__u64 reserved[4];
};

#endif /* _UAPI_RX550_IOCTL_H */
