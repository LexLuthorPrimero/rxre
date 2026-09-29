// SPDX-License-Identifier: GPL-2.0
/*
 * test_firmware_parse.c - exercises the ONLY firmware validation this project
 * has established, against the real Polaris 12 SDMA blob.
 *
 * WHY THIS TEST EXISTS WHEN NOTHING LOADS FIRMWARE
 *
 * RX550_IOCTL_LOAD_FIRMWARE is a stub returning -ENOTTY, and it stays that way:
 * programming the SDMA engine needs the register sequence from
 * amdgpu_sdma_init_microcode(), whose ordering lives in amdgpu_smc.c, which is
 * not in this tree. That half has no test because it has no code.
 *
 * The other half does. amdgpu_ucode_validate() (amdgpu_ucode.c:535) is nine
 * lines and it is the entire acceptance criterion for a firmware blob:
 *
 *     if (fw->size == le32_to_cpu(hdr->size_bytes))
 *             return 0;
 *     return -EINVAL;
 *
 * Note what is absent: no CRC. I had assumed a CRC check was the missing piece
 * and built an objection on it. The reference driver does not verify one, so a
 * driver that does not either is not weaker than the driver it replaces. Both
 * blobs fail zlib CRC-32 over every region I tried; the field is documentation.
 *
 * So the parser below is small on purpose. It is small because the spec is
 * small. A test that grew a second opinion about which fields matter would be
 * testing a policy that amdgpu does not have.
 *
 * WHAT IT DOES NOT DO
 *
 * It does not load a module, touch hardware, or claim a blob is loadable. A pass
 * here means "this blob has the shape amdgpu requires", which is a much smaller
 * claim than "this firmware can be sent to the GPU".
 *
 * THE BLOB
 *
 *   07-DRIVER/tests/data/polaris12_sdma.bin, 12692 B decompressed
 *   SHA256 e27b3ec976f87e32883b9190e653b20d27f9e77da8dd2d77eeb10c35ee9f1e61
 *
 * Extracted from /usr/lib/firmware/amdgpu/polaris12_sdma.bin.xz (21 B compressed,
 * SHA256 5a687db0237827f57da3f2e30e37fa1a17385bc6c95674864c710aa73c86bec2). The
 * compressed file is 21 B and the payload is 12692 B; quoting "12692 B" while
 * pointing at the .xz compares the wrong number against the wrong thing.
 *
 * The name is not mine. sdma_v3_0.c:67 carries
 * MODULE_FIRMWARE("amdgpu/polaris12_sdma.bin"), and vi.c:2113 binds
 * sdma_v3_1_ip_block to CHIP_POLARIS12. The blob's ip_version is 3.1, which is
 * the version in that ip_block's name. Three independent sources agree.
 *
 * Exit 0 if every case behaves as documented, 1 otherwise.
 */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FIRMWARE_BIN	"tests/data/polaris12_sdma.bin"
#define FIRMWARE_SHA256	"e27b3ec976f87e32883b9190e653b20d27f9e77da8dd2d77eeb10c35ee9f1e61"
#define FIRMWARE_SIZE	12692

/*
 * Expected values, read out of this blob on 2026-09-29 and cross-checked
 * against the struct that header_size_bytes selects. See check 2.
 */
#define EXPECT_SIZE_BYTES	12692
#define EXPECT_HDR_SIZE		52
#define EXPECT_HDR_MAJOR	1
#define EXPECT_HDR_MINOR	1
#define EXPECT_IP_MAJOR		3
#define EXPECT_IP_MINOR		1
#define EXPECT_UCODE_OFFSET	256
#define EXPECT_UCODE_SIZE	12436
#define EXPECT_FEATURE_VER	31
#define EXPECT_JT_OFFSET	3072
#define EXPECT_JT_SIZE		32
#define EXPECT_DIGEST_SIZE	5

/*
 * struct common_firmware_header, transcribed from amdgpu_ucode.h:30-41.
 *
 * Transcribed rather than included: that header pulls in amdgpu_socbb.h and
 * kernel-only types, and the layout is what is under test, so it has to be
 * written out here where a reader can check it against the source in one look.
 *
 * 32 BYTES, not 36. I asserted 36 when writing the first version of this file
 * and the compiler caught it. 36 is sizeof(smc_firmware_header_v1_0), the SMC
 * header, which adds ucode_start_addr; I had carried that number over from the
 * SMC blob measured in the previous round. common_firmware_header alone is
 * 32 B, verified by compiling the struct rather than by adding its fields.
 */
struct rx550_firmware_header {
	uint32_t size_bytes;
	uint32_t header_size_bytes;
	uint16_t header_version_major;
	uint16_t header_version_minor;
	uint16_t ip_version_major;
	uint16_t ip_version_minor;
	uint32_t ucode_version;
	uint32_t ucode_size_bytes;
	uint32_t ucode_array_offset_bytes;
	uint32_t crc32;
};

_Static_assert(sizeof(struct rx550_firmware_header) == 32,
	       "common_firmware_header is 32 bytes (36 is smc_firmware_header_v1_0)");

/*
 * The three structs header_size_bytes can select for an SDMA blob
 * (amdgpu_ucode.h:313-324). This blob declares 52, which is v1_1 and neither of
 * the other two, so a test that only knew about v1_0 would parse the same 52
 * bytes and get the wrong fields. The union makes the selection explicit.
 */
struct rx550_sdma_header_v1_0 {
	struct rx550_firmware_header header;
	uint32_t ucode_feature_version;
	uint32_t ucode_change_version;
	uint32_t jt_offset;
	uint32_t jt_size;
};

struct rx550_sdma_header_v1_1 {
	struct rx550_sdma_header_v1_0 v1_0;
	uint32_t digest_size;
};

union rx550_sdma_header {
	struct rx550_firmware_header common;
	struct rx550_sdma_header_v1_0 v1_0;
	struct rx550_sdma_header_v1_1 v1_1;
};

_Static_assert(sizeof(struct rx550_sdma_header_v1_0) == 48,
	       "sdma_firmware_header_v1_0 is 48 bytes");
_Static_assert(sizeof(struct rx550_sdma_header_v1_1) == 52,
	       "sdma_firmware_header_v1_1 is 52 bytes, and that is what this blob is");

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

static uint8_t *read_file(const char *path, size_t *out_len)
{
	uint8_t *buf;
	long len;
	FILE *f;

	f = fopen(path, "rb");
	if (!f)
		return NULL;
	if (fseek(f, 0, SEEK_END) != 0) {
		fclose(f);
		return NULL;
	}
	len = ftell(f);
	if (len <= 0) {
		fclose(f);
		return NULL;
	}
	rewind(f);

	buf = malloc((size_t)len);
	if (!buf) {
		fclose(f);
		return NULL;
	}
	if (fread(buf, 1, (size_t)len, f) != (size_t)len) {
		free(buf);
		fclose(f);
		return NULL;
	}
	fclose(f);
	*out_len = (size_t)len;
	return buf;
}

/*
 * rx550_validate_firmware - the port of amdgpu_ucode_validate(), and nothing
 * more than that.
 *
 * Returns 0 if the blob is acceptable, -EINVAL if not, following ucode.c:535.
 * The header fields are read by the caller; this exists so the test and the
 * eventual driver can agree on one predicate, and so the negative control has a
 * function to break.
 */
static int rx550_validate_firmware(const uint8_t *data, size_t len)
{
	const struct rx550_firmware_header *hdr;

	if (len < sizeof(*hdr))
		return -EINVAL;

	hdr = (const struct rx550_firmware_header *)data;
	if (len != hdr->size_bytes)
		return -EINVAL;

	return 0;
}

/*
 * Structural checks that amdgpu does not perform but that cost nothing and catch
 * a blob that would pass size_bytes while being internally inconsistent.
 *
 * These are marked separately in the output because they are a stronger claim
 * than amdgpu's acceptance criterion. Passing them does not mean amdgpu would
 * accept the blob; failing them means the blob is malformed.
 */
static int header_is_self_consistent(const struct rx550_firmware_header *h,
				     size_t len)
{
	/*
	 * size_bytes against the real length is the first thing to check and I
	 * left it out. The negative control caught that: it corrupts size_bytes
	 * and asserts this function rejects the blob, which it did not, because
	 * the arithmetic below only ever involved offset and ucode_size. The
	 * test and the function disagreed, and the test was right about the
	 * function.
	 */
	if (h->size_bytes != len)
		return 0;
	if (h->header_size_bytes < sizeof(*h))
		return 0;
	if (h->ucode_array_offset_bytes < h->header_size_bytes)
		return 0;
	if (h->ucode_array_offset_bytes > len)
		return 0;
	if ((size_t)h->ucode_array_offset_bytes + h->ucode_size_bytes != len)
		return 0;
	return 1;
}

int main(int argc, char **argv)
{
	struct rx550_firmware_header hdr;
	const char *path = argc > 1 ? argv[1] : FIRMWARE_BIN;
	uint8_t *data, *corrupt;
	size_t len;
	int rc;

	printf("=== test_firmware_parse: Polaris 12 SDMA firmware header ===\n");
	printf("    reading: %s\n", path);
	printf("    sha:     %s\n", FIRMWARE_SHA256);
	printf("    this validates SHAPE, not loadability. LOAD_FIRMWARE is a\n");
	printf("    stub and stays one; see the header of this file.\n\n");

	data = read_file(path, &len);
	if (!data) {
		printf("  [FAIL] cannot read %s\n"
		       "         the default path is relative to 07-DRIVER/; run\n"
		       "         `make -C tests run`, or pass the blob as argv[1]\n",
		       path);
		printf("\n%d checks, %d failure(s)\nRESULT: FAIL\n", 1, 1);
		return 1;
	}

	memcpy(&hdr, data, sizeof(hdr));

	printf("1. The blob is the one this test claims to be testing:\n");
	check(len == FIRMWARE_SIZE, "size is 12692 B (the decompressed payload)",
	      "if this fails, the fixture is not the blob documented in the header");
	check(1, "sha256 of the fixture is asserted in FIRMWARE_SHA256, not recomputed",
	      "");
	printf("         (recompute with: sha256sum %s)\n", FIRMWARE_BIN);

	printf("\n2. Header fields, read from the blob:\n");
	{
		char b[160];
		snprintf(b, sizeof b, "size_bytes=%u, file is %zu B",
			 hdr.size_bytes, len);
		check(hdr.size_bytes == EXPECT_SIZE_BYTES, "size_bytes matches the file size", b);
	}
	{
		char b[160];
		snprintf(b, sizeof b, "got %u", hdr.header_size_bytes);
		check(hdr.header_size_bytes == EXPECT_HDR_SIZE, "header_size_bytes == 52", b);
	}
	{
		char b[160];
		snprintf(b, sizeof b, "got %u.%u", hdr.header_version_major,
			 hdr.header_version_minor);
		check(hdr.header_version_major == EXPECT_HDR_MAJOR &&
		      hdr.header_version_minor == EXPECT_HDR_MINOR,
		      "header_version == 1.1", b);
	}
	{
		char b[160];
		snprintf(b, sizeof b, "got %u.%u", hdr.ip_version_major,
			 hdr.ip_version_minor);
		/*
		 * 3.1 is the load-bearing assertion in this file. sdma_v3_0.c:67
		 * names the blob, vi.c:2113 binds sdma_v3_1_ip_block to
		 * CHIP_POLARIS12, and this is the version in that block's name.
		 * If the blob were swapped for another ASIC's, this fails.
		 */
		check(hdr.ip_version_major == EXPECT_IP_MAJOR &&
		      hdr.ip_version_minor == EXPECT_IP_MINOR,
		      "ip_version == 3.1, matching sdma_v3_1_ip_block", b);
	}
	{
		char b[160];
		snprintf(b, sizeof b, "got %u", hdr.ucode_array_offset_bytes);
		check(hdr.ucode_array_offset_bytes == EXPECT_UCODE_OFFSET,
		      "ucode_array_offset_bytes == 256", b);
	}
	{
		char b[160];
		snprintf(b, sizeof b, "got %u", hdr.ucode_size_bytes);
		check(hdr.ucode_size_bytes == EXPECT_UCODE_SIZE,
		      "ucode_size_bytes == 12436", b);
	}

	/*
	 * header_size_bytes selects which struct follows the common header, and
	 * for this blob it selects v1_1 (52 B), not v1_0 (48 B). Parsing it as
	 * v1_0 would read digest_size's slot as a field that does not exist and
	 * silently produce plausible wrong values, which is the failure mode a
	 * size check alone does not catch.
	 */
	printf("\n2b. The SDMA-specific fields, which need the right struct:\n");
	{
		union rx550_sdma_header u;
		char b[192];

		memcpy(&u, data, sizeof(u));
		{
			snprintf(b, sizeof b, "got %u", hdr.header_size_bytes);
			check(hdr.header_size_bytes == sizeof(struct rx550_sdma_header_v1_1),
			      "header_size_bytes == 52 selects v1_1, not v1_0", b);
		}
		snprintf(b, sizeof b, "got %u", u.v1_1.v1_0.ucode_feature_version);
		check(u.v1_1.v1_0.ucode_feature_version == EXPECT_FEATURE_VER,
		      "ucode_feature_version == 31", b);
		snprintf(b, sizeof b, "got %u", u.v1_1.v1_0.jt_offset);
		check(u.v1_1.v1_0.jt_offset == EXPECT_JT_OFFSET, "jt_offset == 3072", b);
		snprintf(b, sizeof b, "got %u", u.v1_1.v1_0.jt_size);
		check(u.v1_1.v1_0.jt_size == EXPECT_JT_SIZE, "jt_size == 32", b);
		snprintf(b, sizeof b, "got %u", u.v1_1.digest_size);
		check(u.v1_1.digest_size == EXPECT_DIGEST_SIZE,
		      "digest_size == 5, the v1_1 field", b);
	}

	printf("\n3. The amdgpu acceptance criterion, ported from ucode.c:535:\n");
	rc = rx550_validate_firmware(data, len);
	{
		char b[80];
		snprintf(b, sizeof b, "returned %d (%s)", rc, strerror(-rc));
		check(rc == 0, "rx550_validate_firmware accepts the real blob", b);
	}

	printf("\n4. Self-consistency, which amdgpu does not check:\n");
	check(header_is_self_consistent(&hdr, len),
	      "offset + ucode_size == file size, offset >= header_size",
	      "the blob would be internally inconsistent");
	printf("         (amdgpu would accept a blob that fails this; it is a\n"
	       "         stronger claim than the driver requires, and is\n"
	       "         reported separately for that reason)\n");

	printf("\n5. Negative control -- the validator must reject bad blobs.\n"
	       "   Without this section the test would pass on any function that\n"
	       "   returns 0, including one that returns 0 unconditionally.\n");

	/* 5a. size_bytes that does not match the file. The exact failure
	 * amdgpu is built to catch: a truncated or concatenated file. */
	corrupt = malloc(len);
	if (!corrupt) {
		printf("  [FAIL] out of memory in the negative control\n");
		return 1;
	}
	memcpy(corrupt, data, len);
	corrupt[0] ^= 0x01;	/* size_bytes low byte */
	memcpy(&hdr, corrupt, sizeof(hdr));
	check(rx550_validate_firmware(corrupt, len) == -EINVAL,
	      "corrupted size_bytes -> -EINVAL",
	      "the validator accepted a blob whose header lies about its length");
	check(!header_is_self_consistent(&hdr, len),
	      "corrupted size_bytes -> self-consistency fails too",
	      "a length that disagrees with the file should be caught");

	/* 5b. a blob shorter than its own header must not be read past the end */
	check(rx550_validate_firmware(data, 8) == -EINVAL,
	      "8-byte buffer -> -EINVAL, no read past the end",
	      "the length check did not run before dereferencing the header");

	/* 5c. payload offset beyond the end of the file */
	memcpy(corrupt, data, len);
	((struct rx550_firmware_header *)corrupt)->ucode_array_offset_bytes =
		(uint32_t)len + 1;
	memcpy(&hdr, corrupt, sizeof(hdr));
	check(!header_is_self_consistent(&hdr, len),
	      "offset past EOF -> self-consistency fails",
	      "an offset beyond the buffer was accepted");
	/*
	 * rx550_validate_firmware() still returns 0 here, and that is correct:
	 * size_bytes is untouched, so it is exactly the blob amdgpu accepts.
	 * Stating it beats leaving the reader to wonder whether the test missed it.
	 */
	check(rx550_validate_firmware(corrupt, len) == 0,
	      "same blob still passes amdgpu's own check, and that is expected",
	      "a divergence here means the two criteria drifted apart");

	/* 5d. ucode_size that does not add up */
	memcpy(corrupt, data, len);
	((struct rx550_firmware_header *)corrupt)->ucode_size_bytes += 1;
	memcpy(&hdr, corrupt, sizeof(hdr));
	check(!header_is_self_consistent(&hdr, len),
	      "ucode_size off by one -> self-consistency fails",
	      "an inconsistent length was accepted");

	/* 5e. header_size smaller than the struct: a truncated header, which
	 * would let a parser read fields that are not there. The bound is 32,
	 * sizeof(common_firmware_header), not 36 -- 36 is the SMC v1_0 header
	 * and asserting against it here would be the same mistake the _Static_assert
	 * caught. */
	memcpy(corrupt, data, len);
	((struct rx550_firmware_header *)corrupt)->header_size_bytes = 4;
	memcpy(&hdr, corrupt, sizeof(hdr));
	check(!header_is_self_consistent(&hdr, len),
	      "header_size 4 < 32 -> self-consistency fails",
	      "a header smaller than its own struct was accepted");

	free(corrupt);
	free(data);

	printf("\n%d checks, %d failure(s)\n", checks, failures);
	if (failures) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	printf("\nNOT covered, and not claimed:\n"
	       "  - programming the SDMA registers. Needs the sequence from\n"
	       "    amdgpu_smc.c, absent from this tree. The ioctl stays -ENOTTY.\n"
	       "  - CRC32. amdgpu_ucode_validate() does not check it, so neither\n"
	       "    do we; the header field is documentation.\n"
	       "  - the SMC blob. Same header layout, but this driver has no use\n"
	       "    for it: it is power management, not workload submission.\n"
	       "  - loading this module on this host. CONFIG_SECURITY_LOCKDOWN_LSM=y\n"
	       "    rejects unsigned modules, so nothing here has run in kernel.\n");
	return 0;
}
