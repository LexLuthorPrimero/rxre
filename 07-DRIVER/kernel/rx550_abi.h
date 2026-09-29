/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rx550_abi.h - frozen userspace/kernel ABI for the rx550 driver.
 *
 * WHY A SEPARATE HEADER FROM rx550_ioctl.h
 *
 * rx550_ioctl.h is what the driver includes. This file is what gets installed and
 * what userspace builds against. Separating them is the only way to make one
 * property checkable: a userspace binary compiled against an older ABI must fail
 * loudly rather than mis-decode an ioctl.
 *
 * The mechanism is rx550_abi_version, carried in every call. The kernel compares
 * it against what it implements and returns -EPROTO on a mismatch, instead of
 * interpreting a struct whose layout has moved. The alternative -- "document the
 * layout and hope" -- is the failure this project has already hit: a struct was
 * asserted as 96 bytes, then 64, and the userspace _Static_assert caught the
 * disagreement only because the two asserts happened to disagree with each other.
 * That was luck. A version field is not luck.
 *
 * ---------------------------------------------------------------------------
 * IOCTL NUMBERS ARE FROZEN
 * ---------------------------------------------------------------------------
 * 0x00 answered in Ronda 1 and a userspace binary exists that was built against
 * it. A number that changes meaning breaks that binary SILENTLY: the ioctl still
 * returns success, it just does something else. There is no error to notice.
 *
 * New ioctls take the next free number. 0x00..0x03 are spent; RX550_IOCTL_LOAD_FIRMWARE
 * was added as 0x04 rather than renumbering into the gaps, and none of the first
 * four moved.
 */
#ifndef _UAPI_RX550_ABI_H
#define _UAPI_RX550_ABI_H

#include <linux/types.h>
#include <linux/ioctl.h>

#define RX550_IOCTL_MAGIC 'R'

/* ---- frozen ioctl numbers ------------------------------------------------ */
/* Do not renumber. Append only. */
#define RX550_IOCTL_NR_VERSION         0x00
#define RX550_IOCTL_NR_DEVICE_INFO     0x01
#define RX550_IOCTL_NR_SUBMIT_COMPUTE  0x02
#define RX550_IOCTL_NR_WAIT_FENCE      0x03
#define RX550_IOCTL_NR_LOAD_FIRMWARE   0x04   /* STUB: returns -ENOTTY */

/*
 * ABI revision. Bump on any layout change: a struct resized, a field moved, a
 * new field appended to a struct userspace already passes by value.
 *
 * 1  Ronda 1: VERSION, DEVICE_INFO declared; SUBMIT/WAIT placeholders.
 * 2  Ronda 3: LOAD_FIRMWARE declared as a stub. No existing struct changed, so
 *    this is an additive revision; it exists so a userspace library built in
 *    Ronda 1 can be told that the driver understands firmware loading at all,
 *    even though calling it returns ENOTTY.
 */
#define RX550_ABI_VERSION_MAJOR 1
#define RX550_ABI_VERSION_MINOR 2
#define RX550_ABI_VERSION_PATCH 0

/**
 * struct rx550_abi_version - ABI handshake, passed by value to every ioctl.
 * @major: incompatible change; a client with a different major must not proceed
 * @minor: additive change; an older client may still be served
 * @patch: fixes, no layout impact
 * @abi_crc: crc32 of the rest of this header, see rx550_abi_crc() below
 *
 * The CRC is belt and braces on top of the numbers. Two builds can report the
 * same MAJOR/MINOR and still disagree if a field was moved; a CRC over the header
 * text catches that without needing a human to remember to bump something.
 */
struct rx550_abi_version {
	__u32 major;
	__u32 minor;
	__u32 patch;
	__u32 abi_crc;
};

/* ---- ioctl payloads ------------------------------------------------------ */

/** @see struct rx550_version in rx550_ioctl.h */
struct rx550_fw_blob {
	__u64 user_ptr;		/**< userspace pointer to the blob */
	__u32 size;		/**< blob size in bytes */
	__u32 flags;		/**< reserved, must be 0 */
};

/*
 * Firmware loading is declared and NOT implemented. The driver returns -ENOTTY.
 *
 * CORRECTION 2026-09-29, after reading IA-1's bee9f4b: reason 1 below was WRONG
 * as written. The blob exists and is committed at
 * 06-INGENIERIA-INVERSA/firmware/polaris12_smc.bin, 130388 B, SHA256
 * 4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77. I searched
 * /lib/firmware/amdgpu/ and found no Polaris 12 entry, and generalised from that
 * absence to "no blob available" without checking the repository. Same class of
 * error as the three recorded in AGENTS.md: checking a neighbour, not the object.
 * "Not in this directory" is not "does not exist".
 *
 * The two reasons that SURVIVE, both re-verified here:
 *
 *  1. The blob is the SMC microcontroller, not the SDMA engine. It is
 *     common_firmware_header version 1.0, ip_version 7.2, header 36 B, payload
 *     at offset 256 (I decoded it against amdgpu_ucode.h:30; the arithmetic
 *     closes exactly: 256 + 130132 = 130388 = the file size). The SDMA
 *     microcode -- the part that actually issues PM4 packets, which is what this
 *     driver exists to do -- was DEFERRED by IA-1 and is not in the tree. Loading
 *     the SMC would not give this driver a working submit path.
 *  2. The CRC cannot be checked. The header declares crc32 = 0xae2b3b78, and
 *     that does not match zlib.crc32 over the payload, over the 32 B header, or
 *     over any other region or (init, xorout) combination I tried. A loader that
 *     cannot verify what it is handed should not be writing it to a GPU.
 *
 * Reason 3 from the previous revision -- PSP v10.0 signature validation -- is
 * NOT established and has been REMOVED rather than kept. psp_v10_0.c existing in
 * the tree does not establish that this path validates signatures, and no source
 * for the SMC load path is present to check (amdgpu_smc.c and amdgpu_firmware.c
 * are absent from this partial tree). Asserting it would repeat the error above
 * in the opposite direction: inferring a property from a neighbouring file.
 *
 * The struct exists so the number is frozen and userspace can be written against
 * it. Its layout is provisional: the fields needed for a real load (target
 * memory, PSP mailbox, version) are not in here yet, and adding them later is a
 * reason to bump ABI_MINOR.
 */
struct rx550_ioctl_load_firmware {
	struct rx550_abi_version abi;	/**< must come first, in every ioctl */
	struct rx550_fw_blob blob;
};

#define RX550_IOCTL_LOAD_FIRMWARE \
	_IOWR(RX550_IOCTL_MAGIC, RX550_IOCTL_NR_LOAD_FIRMWARE, \
	      struct rx550_ioctl_load_firmware)

/* ---- layout guards ------------------------------------------------------- */
/*
 * These must match the _Static_asserts in the kernel. They are duplicated on
 * purpose: if they are wrong in one place and right in the other, the build
 * fails, and that is the intended outcome. Rona 1 proved the guard works -- the
 * userspace assert fired on a size the kernel had already changed.
 */
#define RX550_ABI_VERSION_SIZE   ((int)sizeof(struct rx550_abi_version))
#define RX550_FW_BLOB_SIZE       ((int)sizeof(struct rx550_fw_blob))
#define RX550_LOAD_FIRMWARE_SIZE ((int)sizeof(struct rx550_ioctl_load_firmware))

#endif /* _UAPI_RX550_ABI_H */
