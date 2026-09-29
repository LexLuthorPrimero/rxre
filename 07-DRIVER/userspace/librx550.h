/* SPDX-License-Identifier: GPL-2.0 */
/*
 * librx550.h - userspace API for the rx550 exclusive driver.
 *
 * The layout constants and the version macros come from rx550_abi.h, which is
 * shared with the kernel. Do not redeclare a struct here: a userspace struct
 * that disagrees with the kernel's is the classic way a driver corrupts memory
 * and never says so.
 */
#ifndef _RX550_LIBRX550_H
#define _RX550_LIBRX550_H

#include <stddef.h>
#include <stdint.h>

#include "../kernel/rx550_abi.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * rx550_open - open /dev/rx550.
 * @out: receives the driver ABI version, or NULL to skip
 *
 * Returns a file descriptor, or -1 with errno set. ENOENT means the module is
 * not loaded; EACCES or ENXIO usually mean lockdown is refusing the module.
 */
int rx550_open(struct rx550_abi_version *out);

/** rx550_close - close an fd from rx550_open(). 0 on success, -1 on error. */
int rx550_close(int fd);

/**
 * rx550_load_firmware - load a firmware blob.
 *
 * NOT IMPLEMENTED in the driver. Always fails with ENOSYS. See
 * kernel/rx550_abi.h for the three verified reasons.
 */
int rx550_load_firmware(const void *blob, size_t size);

/**
 * rx550_submit_compute - submit a PM4 command buffer.
 *
 * NOT IMPLEMENTED. Always fails with ENOSYS. The GFX8 PM4 encoding is not
 * established in this project.
 */
int rx550_submit_compute(const void *cmd_buf, size_t cmd_size);

#ifdef __cplusplus
}
#endif

#endif /* _RX550_LIBRX550_H */
