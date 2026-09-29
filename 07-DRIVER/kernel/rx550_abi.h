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
 * WHY THIS IS STILL A STUB, after two corrections. The first version of this
 * comment gave two reasons; both were wrong, in different ways, and the error was
 * mine in both cases. They are recorded rather than replaced, because the second
 * failure was worse than the first and is worth not repeating.
 *
 * WHAT I GOT WRONG #1 -- "there is no Polaris 12 blob".
 * False. Both the repository and the host have them:
 *   - 06-INGENIERIA-INVERSA/firmware/polaris12_smc.bin, 130388 B, SHA256
 *     4b8eb326...c77, committed in IA-1's bee9f4b.
 *   - /usr/lib/firmware/amdgpu/polaris12_*.bin.xz, 20 files. I had grepped that
 *     directory for 'polars|lexa' and got zero, then generalised to "no blob".
 *     "POLARIS" does not match "polars". A misspelt pattern is not a search
 *     result, and I reported its output as one. /lib is a symlink to usr/lib, so
 *     the two paths I treated as different were the same directory throughout.
 *
 * WHAT I GOT WRONG #2 -- "the SDMA blob was DEFERRED by IA-1 and is not in the
 * tree, so there is nothing to load".
 * Also false, and worse: polaris12_sdma.bin.xz was on the host the whole time and
 * decompresses to 12692 B, header 52 B, ip_version 3.1 -- which is exactly the
 * sdma_v3_1_ip_block that vi.c:2113 binds to CHIP_POLARIS12. I had already read
 * vi.c and still asked IA-1 for a file I could have extracted myself.
 *
 * SO THE REAL REASON IS NARROWER, and it is not "the blob is missing":
 *
 *  1. amdgpu owns the SDMA engine. The microcode is loaded by
 *     amdgpu_sdma_init_microcode() from "amdgpu/polaris12_sdma.bin", named at
 *     sdma_v3_0.c:67 by MODULE_FIRMWARE, and the memory is programmed through
 *     registers owned by that IP block. A second driver loading the same engine
 *     on a live GPU is not a copy operation; it is a re-initialisation with no
 *     defined failure mode. Whether that is safe is a hardware question, and
 *     nothing in the source answers it.
 *  2. The CRC is not zlib CRC-32, for BOTH blobs, so a verifier cannot be written
 *     from the tree: SMC declares 0xae2b3b78 vs 0x9d6aef38 computed, SDMA declares
 *     0x67458532 vs 0x5045d5a3. The kernel does not verify it either --
 *     amdgpu_ucode_validate() only checks that size_bytes matches the file size
 *     (amdgpu_ucode.c:535). So the field is documentation, not a gate, and there
 *     is no algorithm in this tree to reproduce.
 *
 * REMOVED, not kept: "PSP v10.0 validates signatures". psp_v10_0.c existing does
 * not establish that this path validates signatures, and amdgpu_smc.c is absent
 * from this partial tree. Asserting it would repeat the same error in the
 * opposite direction.
 *
 * What would change this: a decision to load firmware only in the pre-amdgpu
 * window, plus the firmware load sequence itself, which is in amdgpu_smc.c and
 * not here. Until then -ENOTTY is the honest answer.
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
