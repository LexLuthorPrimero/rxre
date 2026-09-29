#ifndef H12_PROBE_H
#define H12_PROBE_H

/*
 * H12-1: controlled Vulkan/Wayland clear/present probe.
 *
 * This header contains only build-time constants and the public status
 * vocabulary.  H12-4 adds a same-run DEVICE/CLOCK_MONOTONIC calibration
 * record; it intentionally contains no system-control interfaces.
 */

#define H12_PROBE_SCHEMA "h12-1.frame.v4"
#define H12_PROBE_METADATA_SCHEMA "h12-4.metadata.v1"
#define H12_PROBE_ERROR_SCHEMA "h12-1.error.v2"
#define H12_PROBE_SUMMARY_SCHEMA "h12-4.summary.v1"
#define H12_PROBE_CALIBRATION_SCHEMA "h12-4.calibration.v1"
#define H12_PROBE_DIAGNOSTIC_SCHEMA "h12-1.diagnostic.v1"

/* The H12 target is fixed and must be verified at runtime. */
#define H12_TARGET_VENDOR_ID 0x1002u
#define H12_TARGET_DEVICE_ID 0x699fu

/* Capability/observation vocabulary used by the JSONL output.  H12-4
 * calibration/mapping records use PRESENT, UNKNOWN and NOT_AVAILABLE;
 * CONFLICT remains reserved for the existing H12-3 safety paths. */
#define H12_STATUS_PRESENT "PRESENT"
#define H12_STATUS_UNKNOWN "UNKNOWN"
#define H12_STATUS_CONFLICT "CONFLICT"
#define H12_STATUS_NOT_AVAILABLE "NOT_AVAILABLE"

#endif /* H12_PROBE_H */
