#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <poll.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define VK_USE_PLATFORM_WAYLAND_KHR
#include <vulkan/vulkan.h>
#include <wayland-client.h>

#include "h12_probe.h"
#include "xdg-shell-client-protocol.h"

#define H12_DEFAULT_FRAMES 120u
#define H12_DEFAULT_WIDTH 640u
#define H12_DEFAULT_HEIGHT 360u
#define H12_DEFAULT_DRAIN_MS 1000u
#define H12_FRAMES_IN_FLIGHT 2u
#define H12_GPU_QUERY_COUNT 2u
#define H12_PRESENT_TIMING_STAGE_CAPACITY 1u
#define H12_MAX_PRESENT_TIMING_DOMAINS 64u
#define H12_PRESENT_TIMING_DOMAIN_RETRIES 4u
#define H12_ACQUIRE_TIMEOUT_NS UINT64_C(1000000000)
#define H12_ACQUIRE_WAIT_SLICE_NS UINT64_C(10000000)
#define H12_FENCE_WAIT_TIMEOUT_NS UINT64_C(5000000000)
#define H12_FENCE_WAIT_SLICE_NS UINT64_C(10000000)
#define H12_MAX_PENDING_FRAME_CALLBACKS 256u
#define H12_MAX_TOPLEVEL_STATES 32u
#define H12_MAX_PENDING_CONFIGURE_DIAGNOSTICS 16u
#define H12_MAX_CALIBRATED_DOMAINS 16u
#define H12_MAX_LOG_PATH 4096u
#define H12_MAX_FRAMES 1000000u
#define H12_MAX_UINT32 0xffffffffu

/* ------------------------------------------------------------------------- */
/* Small, local utilities                                                    */
/* ------------------------------------------------------------------------- */

typedef struct App App;
typedef struct FrameRecord FrameRecord;
typedef struct FrameCallbackData FrameCallbackData;

typedef struct {
  uint32_t frames;
  uint32_t width;
  uint32_t height;
  uint32_t drain_ms;
  VkPresentModeKHR requested_present_mode;
  const char *requested_present_mode_name;
  const char *output_path;
} Config;

typedef struct {
  bool valid;
  uint32_t configure_index;
  uint32_t serial;
  const char *phase;
  const char *classification;
  bool state_only;
  bool frame_valid;
  uint64_t frame_id;
  uint32_t toplevel_configure_count;
  bool toplevel_configure_pending_for_surface;
  bool have_toplevel_configure;
  int32_t toplevel_width;
  int32_t toplevel_height;
  uint32_t toplevel_state_count;
  uint32_t toplevel_states[H12_MAX_TOPLEVEL_STATES];
  bool toplevel_states_truncated;
  bool configured;
  bool surface_size_valid;
  uint32_t surface_width;
  uint32_t surface_height;
  bool swapchain_created;
  uint32_t swapchain_image_count;
  bool initial_configure_completed;
  bool presentation_started;
  bool first_present_completed;
  bool present_call_in_progress;
  uint32_t submitted_frames;
  bool surface_reconfigure_pending;
} ConfigureDiagnostic;

typedef struct {
  bool result_available;
  bool report_complete;
  bool complete;
  uint64_t present_id;
  uint64_t target_time;
  uint32_t stage_count;
  VkPresentStageFlagsEXT stage_mask;
  uint64_t queue_operations_end_time;
  bool queue_operations_end_time_available;
  VkTimeDomainKHR time_domain;
  uint64_t time_domain_id;
  bool conflict;
} PresentTiming;

typedef struct {
  uint32_t sample_id;
  const char *phase;
  uint64_t frame_id;
  bool attempted;
  VkResult result;
  bool raw_valid;
  uint64_t device_timestamp_ticks;
  uint64_t host_timestamp_ns;
  uint64_t max_deviation_ns;
  uint32_t timestamp_valid_bits;
  float timestamp_period_ns;
  const char *status;
  const char *same_run_status;
  const char *reason;
} CalibrationSample;

struct FrameRecord {
  uint64_t frame_id;

  uint64_t cpu_before_recording_ns;
  bool cpu_before_recording_valid;
  uint64_t cpu_before_submit_ns;
  bool cpu_before_submit_valid;
  uint64_t cpu_after_submit_ns;
  bool cpu_after_submit_valid;

  uint64_t gpu_begin_ticks;
  uint64_t gpu_end_ticks;
  uint64_t gpu_elapsed_ticks_modulo;
  uint64_t gpu_elapsed_ns_from_period_modulo;
  bool gpu_elapsed_conversion_available;
  bool gpu_query_requested;
  bool gpu_results_read;
  bool gpu_results_available;
  VkResult gpu_query_result;

  uint32_t image_index;
  VkResult acquire_result;
  VkResult submit_result;
  VkResult present_result;
  VkResult present_per_image_result;

  uint64_t present_call_ns;
  bool present_call_valid;
  uint64_t frame_interval_ns;
  bool frame_interval_valid;

  bool callback_requested;
  /* CPU host-observation timestamps; not Wayland/display timestamps. */
  uint64_t frame_callback_requested_cpu_ns;
  bool frame_callback_requested_cpu_valid;
  bool callback_received;
  uint64_t frame_callback_received_cpu_ns;
  bool frame_callback_received_cpu_valid;
  uint64_t cpu_callback_request_to_receive_ns;
  bool cpu_callback_request_to_receive_valid;
  uint32_t callback_time_ms;
  struct wl_callback *callback_proxy;
  FrameCallbackData *callback_data;

  /* Host observation of fence completion; not a GPU/display timestamp. */
  uint64_t gpu_fence_observed_cpu_ns;
  bool gpu_fence_observed_cpu_valid;
  const char *gpu_fence_observation_source;

  CalibrationSample calibration_before;
  CalibrationSample calibration_after;
  bool calibration_before_valid;
  bool calibration_after_valid;
  bool calibration_mapping_prepared;
  const char *calibration_same_run_status;
  const char *gpu_clock_correlation_status;
  bool gpu_timestamp_begin_cpu_candidate_valid;
  uint64_t gpu_timestamp_begin_cpu_candidate_ns;
  bool gpu_timestamp_end_cpu_candidate_valid;
  uint64_t gpu_timestamp_end_cpu_candidate_ns;
  const char *gpu_clock_mapping_method;
  bool gpu_clock_mapping_source_sample_valid;
  uint32_t gpu_clock_mapping_source_sample_id;
  bool gpu_clock_mapping_spread_valid;
  uint64_t gpu_clock_mapping_spread_ns;
  bool gpu_clock_mapping_max_deviation_valid;
  uint64_t gpu_clock_mapping_max_deviation_ns;
  const char *calibration_drift_status;
  bool calibration_drift_valid;
  uint64_t calibration_device_delta_ticks;
  uint64_t calibration_device_delta_ns;
  uint64_t calibration_host_delta_ns;
  int64_t calibration_residual_ns;

  bool gpu_done;
  bool timing_requested;
  bool present_timing_target_requested;
  bool present_id_requested;
  uint64_t present_id_assigned;
  PresentTiming timing;

  bool emitted;
};

typedef struct {
  VkCommandBuffer command_buffer;
  VkSemaphore acquire_semaphore;
  VkFence fence;
  VkQueryPool query_pool;
  bool in_flight;
  bool gpu_done;
  FrameRecord *active_record;
} FrameResource;

struct FrameCallbackData {
  App *app;
  FrameRecord *record;
};

struct App {
  Config cfg;
  FILE *log;
  bool close_log;
  char run_id[96];
  bool run_id_valid;
  char driver_name[VK_MAX_DRIVER_NAME_SIZE];
  char driver_info[VK_MAX_DRIVER_INFO_SIZE];
  bool driver_properties_valid;

  struct wl_display *display;
  struct wl_registry *registry;
  struct wl_compositor *compositor;
  struct xdg_wm_base *xdg_wm_base;
  struct wl_surface *wl_surface;
  struct xdg_surface *xdg_surface;
  struct xdg_toplevel *xdg_toplevel;
  bool configured;
  bool have_toplevel_size;
  uint32_t toplevel_configure_count;
  bool toplevel_configure_pending_for_surface;
  bool have_toplevel_configure;
  int32_t toplevel_width;
  int32_t toplevel_height;
  uint32_t toplevel_state_count;
  uint32_t toplevel_states[H12_MAX_TOPLEVEL_STATES];
  bool toplevel_states_truncated;
  bool initial_configure_completed;
  uint32_t xdg_surface_configure_count;
  bool presentation_started;
  bool first_present_completed;
  bool present_call_in_progress;
  bool pre_present_extent_change;
  bool surface_reconfigure_pending;
  const char *surface_reconfigure_code;
  bool wayland_needs_write;
  int32_t configured_width;
  int32_t configured_height;

  VkInstance instance;
  uint32_t instance_api_version;
  VkPhysicalDevice physical_device;
  VkPhysicalDeviceProperties physical_properties;
  VkPhysicalDeviceProperties2 physical_properties2;
  bool physical_properties2_valid;
  VkPhysicalDeviceIDProperties id_properties;
  bool id_properties_valid;
  VkPhysicalDeviceVulkan12Properties vulkan12_properties;
  bool vulkan12_properties_valid;
  VkPhysicalDevicePCIBusInfoPropertiesEXT pci_info;
  bool pci_info_valid;
  VkDevice device;
  bool logical_device_created;
  VkQueue queue;
  uint32_t queue_family;

  PFN_vkGetPhysicalDeviceSurfaceSupportKHR pfn_surface_support;
  PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR pfn_surface_capabilities;
  PFN_vkGetPhysicalDeviceSurfaceCapabilities2KHR pfn_surface_capabilities2;
  PFN_vkGetPhysicalDeviceSurfaceFormatsKHR pfn_surface_formats;
  PFN_vkGetPhysicalDeviceSurfacePresentModesKHR pfn_surface_present_modes;
  PFN_vkCreateWaylandSurfaceKHR pfn_create_wayland_surface;
  PFN_vkDestroySurfaceKHR pfn_destroy_surface;
  PFN_vkGetPhysicalDeviceFeatures2KHR pfn_features2;
  PFN_vkGetPhysicalDeviceProperties2KHR pfn_properties2;
  PFN_vkGetPhysicalDeviceCalibrateableTimeDomainsEXT
      pfn_calibrateable_time_domains;
  PFN_vkGetCalibratedTimestampsKHR pfn_get_calibrated_timestamps;
  const char *calibrated_timestamp_variant;
  bool calibrated_function_available;
  bool calibrated_device_domain_supported;
  bool calibrated_monotonic_domain_supported;
  uint32_t calibrated_domains[H12_MAX_CALIBRATED_DOMAINS];
  bool calibrated_domains_truncated;

  bool instance_get_caps2;
  bool instance_get_properties2;
  bool device_swapchain;
  bool device_pci_bus_info;
  bool device_calibrated_timestamps;
  bool device_calibrated_ext;
  bool device_calibrated_khr;
  bool device_present_id2;
  bool device_present_wait2;
  bool device_present_timing;

  bool present_id2_enabled;
  bool present_id2_surface_supported;
  bool present_id2_usable;
  bool present_wait2_enabled;
  bool present_timing_enabled;
  const char *present_id2_capability;
  const char *present_timing_capability;
  const char *present_wait2_capability;
  const char *calibrated_timestamps_capability;
  uint32_t calibrated_domain_count;
  bool calibrated_domain_query_valid;
  const char *timestamp_query_capability;
  bool present_timing_dependency_ok;
  bool present_timing_surface_supported;
  bool present_wait2_surface_supported;
  bool present_wait2_swapchain_enabled;
  VkPresentStageFlagsEXT present_timing_stage_queries;
  VkPresentStageFlagsEXT present_timing_time_domain_stage;
  VkTimeDomainKHR present_timing_time_domain_kind;
  uint64_t present_timing_time_domain_id;
  uint64_t present_timing_time_domains_counter;
  bool present_timing_time_domain_valid;
  uint32_t present_timing_queue_size;
  PFN_vkSetSwapchainPresentTimingQueueSizeEXT pfn_set_present_timing_queue_size;
  PFN_vkGetPastPresentationTimingEXT pfn_get_past_presentation_timing;
  PFN_vkGetSwapchainTimeDomainPropertiesEXT pfn_get_swapchain_time_domains;
  VkPastPresentationTimingEXT *present_timing_results;
  VkPresentStageTimeEXT *present_timing_stage_storage;

  VkSurfaceKHR surface;
  VkSurfaceCapabilitiesKHR surface_capabilities;
  VkSurfaceCapabilitiesPresentId2KHR present_id2_surface_capabilities;
  VkPresentTimingSurfaceCapabilitiesEXT present_timing_surface_capabilities;
  VkSurfaceCapabilitiesPresentWait2KHR present_wait2_surface_capabilities;
  VkSurfaceFormatKHR surface_format;
  VkPresentModeKHR selected_present_mode;
  const char *selected_present_mode_name;
  uint32_t surface_width;
  uint32_t surface_height;
  uint32_t swapchain_image_count;

  VkSwapchainKHR swapchain;
  VkImage *swapchain_images;
  VkImageView *swapchain_views;
  VkFramebuffer *swapchain_framebuffers;
  VkSemaphore *present_semaphores;
  VkRenderPass render_pass;
  VkCommandPool command_pool;
  FrameResource *resources;
  uint32_t resource_count;

  bool gpu_timestamp_capable;
  uint32_t timestamp_valid_bits;
  float timestamp_period_ns;
  uint32_t timestamp_query_count;

  FrameRecord *records;
  ConfigureDiagnostic pending_configure_diagnostics[
      H12_MAX_PENDING_CONFIGURE_DIAGNOSTICS];
  uint32_t pending_configure_diagnostic_count;
  uint32_t calibration_sample_count;
  uint32_t calibration_present_count;
  uint32_t calibration_unknown_count;
  uint32_t calibration_not_available_count;
  uint32_t calibration_mapping_present_count;
  uint32_t calibration_mapping_unknown_count;
  uint32_t calibration_mapping_not_available_count;
  uint64_t calibration_max_deviation_ns;
  bool calibration_max_deviation_valid;
  bool metadata_written;
  uint32_t submitted_frames;
  uint32_t emitted_frames;
  bool swapchain_suboptimal_observed;
  uint64_t last_present_call_ns;
  bool last_present_call_valid;
  uint64_t unmatched_present_timing_count;
  VkResult last_present_timing_poll_result;
  uint32_t present_timing_poll_error_count;

  /* Set when the compositor asks the toplevel to close. */
  bool close_requested;
  uint32_t pending_frame_callbacks;
};

static App *g_abort_app;
static const char *g_abort_phase = "startup";
static bool g_abort_frame_valid;
static uint64_t g_abort_frame_id;
static bool g_abort_event_written;
static bool g_abort_event_pending;
static const char *g_abort_pending_code;
static const char *g_abort_pending_status;
static char g_abort_pending_reason[512];
static bool g_abort_summary_written;
static bool g_abort_cleanup_performed;
static bool g_abort_cleanup_in_progress;
static const char *g_abort_cleanup_status = "NOT_STARTED";
static const char *g_abort_final_state = "RUNNING";

static void json_string(FILE *out, const char *text);
static void write_summary(App *app);
static void cleanup(App *app);
static void emit_structured_abort(App *app, const char *code,
                                  const char *status, const char *reason);
static void structured_abort(App *app, const char *code,
                             const char *status, const char *reason);

static void fatal(const char *fmt, ...)
    __attribute__((noreturn, format(printf, 1, 2)));

static void fatal(const char *fmt, ...)
{
  char reason[512];
  va_list ap;

  reason[0] = '\0';
  va_start(ap, fmt);
  (void)vsnprintf(reason, sizeof(reason), fmt, ap);
  va_end(ap);

  if (g_abort_app != NULL && g_abort_app->log != NULL) {
    const char *fatal_phase = g_abort_phase;
    bool fatal_frame_valid = g_abort_frame_valid;
    uint64_t fatal_frame_id = g_abort_frame_id;
    g_abort_final_state = "ABORTED";
    structured_abort(g_abort_app, "FATAL_ABORT", H12_STATUS_CONFLICT, reason);
    if (!g_abort_cleanup_in_progress) {
      g_abort_cleanup_in_progress = true;
      cleanup(g_abort_app);
      g_abort_cleanup_in_progress = false;
    }
    g_abort_phase = fatal_phase;
    g_abort_frame_valid = fatal_frame_valid;
    g_abort_frame_id = fatal_frame_id;
    emit_structured_abort(
        g_abort_app,
        g_abort_pending_code != NULL ? g_abort_pending_code : "FATAL_ABORT",
        g_abort_pending_status != NULL ? g_abort_pending_status
                                       : H12_STATUS_CONFLICT,
        g_abort_pending_reason[0] != '\0' ? g_abort_pending_reason : reason);
    if (!g_abort_summary_written) {
      write_summary(g_abort_app);
    }
  }

  va_start(ap, fmt);
  vfprintf(stderr, fmt, ap);
  va_end(ap);
  fputc('\n', stderr);
  exit(EXIT_FAILURE);
}

static bool parse_u32(const char *text, uint32_t *value)
{
  char *end = NULL;
  unsigned long parsed;

  if (text == NULL || *text == '\0' || value == NULL) {
    return false;
  }

  errno = 0;
  parsed = strtoul(text, &end, 0);
  if (errno != 0 || end == text || *end != '\0' || parsed > UINT32_MAX) {
    return false;
  }

  *value = (uint32_t)parsed;
  return true;
}

static bool parse_present_mode(const char *text, VkPresentModeKHR *mode,
                               const char **name)
{
  if (strcmp(text, "fifo") == 0) {
    *mode = VK_PRESENT_MODE_FIFO_KHR;
    *name = "FIFO";
  } else if (strcmp(text, "fifo_relaxed") == 0) {
    *mode = VK_PRESENT_MODE_FIFO_RELAXED_KHR;
    *name = "FIFO_RELAXED";
  } else if (strcmp(text, "mailbox") == 0) {
    *mode = VK_PRESENT_MODE_MAILBOX_KHR;
    *name = "MAILBOX";
  } else if (strcmp(text, "immediate") == 0) {
    *mode = VK_PRESENT_MODE_IMMEDIATE_KHR;
    *name = "IMMEDIATE";
  } else {
    return false;
  }
  return true;
}

static void print_usage(const char *program)
{
  printf("Usage: %s [options]\n", program);
  printf("  --frames N          finite number of clear/present frames (default %u)\n",
         H12_DEFAULT_FRAMES);
  printf("  --width N           requested surface width (default %u)\n",
         H12_DEFAULT_WIDTH);
  printf("  --height N          requested surface height (default %u)\n",
         H12_DEFAULT_HEIGHT);
  printf("  --present-mode M    fifo|fifo_relaxed|mailbox|immediate (default fifo)\n");
  printf("  --drain-ms N        bounded callback/timing drain at exit (default %u)\n",
         H12_DEFAULT_DRAIN_MS);
  printf("  --output PATH       JSONL output path, or - for stdout (default -)\n");
  printf("  --help              show this help\n");
  printf("\n");
  printf("The target is fixed to PCI vendor/device %04x:%04x and is verified at runtime.\n",
         H12_TARGET_VENDOR_ID, H12_TARGET_DEVICE_ID);
}

static bool parse_args(int argc, char **argv, Config *cfg)
{
  cfg->frames = H12_DEFAULT_FRAMES;
  cfg->width = H12_DEFAULT_WIDTH;
  cfg->height = H12_DEFAULT_HEIGHT;
  cfg->drain_ms = H12_DEFAULT_DRAIN_MS;
  cfg->requested_present_mode = VK_PRESENT_MODE_FIFO_KHR;
  cfg->requested_present_mode_name = "FIFO";
  cfg->output_path = "-";

  for (int i = 1; i < argc; ++i) {
    const char *arg = argv[i];
    if (strcmp(arg, "--help") == 0) {
      print_usage(argv[0]);
      exit(EXIT_SUCCESS);
    }
    if (i + 1 >= argc) {
      fprintf(stderr, "Missing value for %s\n", arg);
      return false;
    }
    if (strcmp(arg, "--frames") == 0) {
      if (!parse_u32(argv[++i], &cfg->frames) || cfg->frames == 0 ||
          cfg->frames > H12_MAX_FRAMES) {
        fprintf(stderr, "Invalid --frames value (maximum %u)\n",
                H12_MAX_FRAMES);
        return false;
      }
    } else if (strcmp(arg, "--width") == 0) {
      if (!parse_u32(argv[++i], &cfg->width) || cfg->width == 0 ||
          cfg->width > (uint32_t)INT32_MAX) {
        fprintf(stderr, "Invalid --width value\n");
        return false;
      }
    } else if (strcmp(arg, "--height") == 0) {
      if (!parse_u32(argv[++i], &cfg->height) || cfg->height == 0 ||
          cfg->height > (uint32_t)INT32_MAX) {
        fprintf(stderr, "Invalid --height value\n");
        return false;
      }
    } else if (strcmp(arg, "--drain-ms") == 0) {
      if (!parse_u32(argv[++i], &cfg->drain_ms)) {
        fprintf(stderr, "Invalid --drain-ms value\n");
        return false;
      }
    } else if (strcmp(arg, "--present-mode") == 0) {
      if (!parse_present_mode(argv[++i], &cfg->requested_present_mode,
                              &cfg->requested_present_mode_name)) {
        fprintf(stderr, "Invalid --present-mode value\n");
        return false;
      }
    } else if (strcmp(arg, "--output") == 0) {
      cfg->output_path = argv[++i];
    } else {
      fprintf(stderr, "Unknown option: %s\n", arg);
      return false;
    }
  }

  if (strlen(cfg->output_path) >= H12_MAX_LOG_PATH) {
    fprintf(stderr, "--output path is too long\n");
    return false;
  }
  return true;
}

static bool monotonic_ns(uint64_t *value)
{
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
    return false;
  }
  *value = (uint64_t)ts.tv_sec * UINT64_C(1000000000) +
           (uint64_t)ts.tv_nsec;
  return true;
}

static void initialize_run_id(App *app)
{
  uint64_t monotonic_value = 0;
  if (monotonic_ns(&monotonic_value)) {
    (void)snprintf(app->run_id, sizeof(app->run_id), "h12-4-%ld-%" PRIu64,
                   (long)getpid(), monotonic_value);
  } else {
    (void)snprintf(app->run_id, sizeof(app->run_id), "h12-4-%ld",
                   (long)getpid());
  }
  app->run_id[sizeof(app->run_id) - 1u] = '\0';
  app->run_id_valid = app->run_id[0] != '\0';
}

static const char *vk_result_name(VkResult result)
{
  switch (result) {
    case VK_SUCCESS:
      return "VK_SUCCESS";
    case VK_NOT_READY:
      return "VK_NOT_READY";
    case VK_TIMEOUT:
      return "VK_TIMEOUT";
    case VK_EVENT_SET:
      return "VK_EVENT_SET";
    case VK_EVENT_RESET:
      return "VK_EVENT_RESET";
    case VK_INCOMPLETE:
      return "VK_INCOMPLETE";
    case VK_ERROR_OUT_OF_HOST_MEMORY:
      return "VK_ERROR_OUT_OF_HOST_MEMORY";
    case VK_ERROR_OUT_OF_DEVICE_MEMORY:
      return "VK_ERROR_OUT_OF_DEVICE_MEMORY";
    case VK_ERROR_INITIALIZATION_FAILED:
      return "VK_ERROR_INITIALIZATION_FAILED";
    case VK_ERROR_DEVICE_LOST:
      return "VK_ERROR_DEVICE_LOST";
    case VK_ERROR_MEMORY_MAP_FAILED:
      return "VK_ERROR_MEMORY_MAP_FAILED";
    case VK_ERROR_LAYER_NOT_PRESENT:
      return "VK_ERROR_LAYER_NOT_PRESENT";
    case VK_ERROR_EXTENSION_NOT_PRESENT:
      return "VK_ERROR_EXTENSION_NOT_PRESENT";
    case VK_ERROR_FEATURE_NOT_PRESENT:
      return "VK_ERROR_FEATURE_NOT_PRESENT";
    case VK_ERROR_INCOMPATIBLE_DRIVER:
      return "VK_ERROR_INCOMPATIBLE_DRIVER";
    case VK_ERROR_SURFACE_LOST_KHR:
      return "VK_ERROR_SURFACE_LOST_KHR";
    case VK_ERROR_OUT_OF_DATE_KHR:
      return "VK_ERROR_OUT_OF_DATE_KHR";
    case VK_ERROR_PRESENT_TIMING_QUEUE_FULL_EXT:
      return "VK_ERROR_PRESENT_TIMING_QUEUE_FULL_EXT";
    case VK_SUBOPTIMAL_KHR:
      return "VK_SUBOPTIMAL_KHR";
    default:
      return "VK_RESULT_UNNAMED";
  }
}

static void json_string(FILE *out, const char *text)
{
  const unsigned char *p = (const unsigned char *)text;
  fputc('"', out);
  while (*p != '\0') {
    switch (*p) {
      case '"':
        fputs("\\\"", out);
        break;
      case '\\':
        fputs("\\\\", out);
        break;
      case '\b':
        fputs("\\b", out);
        break;
      case '\f':
        fputs("\\f", out);
        break;
      case '\n':
        fputs("\\n", out);
        break;
      case '\r':
        fputs("\\r", out);
        break;
      case '\t':
        fputs("\\t", out);
        break;
      default:
        if (*p < 0x20u) {
          fprintf(out, "\\u%04x", (unsigned int)*p);
        } else {
          fputc((int)*p, out);
        }
        break;
    }
    ++p;
  }
  fputc('"', out);
}

static void json_u64_or_null(FILE *out, bool valid, uint64_t value)
{
  if (valid) {
    fprintf(out, "%" PRIu64, value);
  } else {
    fputs("null", out);
  }
}

static void json_i64_or_null(FILE *out, bool valid, int64_t value)
{
  if (valid) {
    fprintf(out, "%" PRId64, value);
  } else {
    fputs("null", out);
  }
}

static void json_i32_or_null(FILE *out, bool valid, int32_t value)
{
  if (valid) {
    fprintf(out, "%" PRId32, value);
  } else {
    fputs("null", out);
  }
}

static bool uuid_is_nonzero(const uint8_t *uuid)
{
  for (uint32_t i = 0; i < VK_UUID_SIZE; ++i) {
    if (uuid[i] != 0u) {
      return true;
    }
  }
  return false;
}

static const char *time_domain_name(uint32_t domain)
{
  switch (domain) {
    case VK_TIME_DOMAIN_DEVICE_KHR:
      return "VK_TIME_DOMAIN_DEVICE_KHR";
    case VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR:
      return "VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR";
    case VK_TIME_DOMAIN_CLOCK_MONOTONIC_RAW_KHR:
      return "VK_TIME_DOMAIN_CLOCK_MONOTONIC_RAW_KHR";
    case VK_TIME_DOMAIN_QUERY_PERFORMANCE_COUNTER_KHR:
      return "VK_TIME_DOMAIN_QUERY_PERFORMANCE_COUNTER_KHR";
    case VK_TIME_DOMAIN_PRESENT_STAGE_LOCAL_EXT:
      return "VK_TIME_DOMAIN_PRESENT_STAGE_LOCAL_EXT";
    case VK_TIME_DOMAIN_SWAPCHAIN_LOCAL_EXT:
      return "VK_TIME_DOMAIN_SWAPCHAIN_LOCAL_EXT";
    default:
      return "VK_TIME_DOMAIN_UNKNOWN";
  }
}

static void json_uuid(FILE *out, bool valid, const uint8_t *uuid)
{
  if (!valid) {
    fputs("null", out);
    return;
  }
  fputc('"', out);
  for (uint32_t i = 0; i < VK_UUID_SIZE; ++i) {
    fprintf(out, "%02x", uuid[i]);
  }
  fputc('"', out);
}

static void json_selected_pci(FILE *out, const App *app)
{
  if (!app->pci_info_valid) {
    json_string(out, "UNKNOWN");
    return;
  }
  char pci[32];
  snprintf(pci, sizeof(pci), "%04x:%02x:%02x.%u", app->pci_info.pciDomain,
           app->pci_info.pciBus, app->pci_info.pciDevice,
           app->pci_info.pciFunction);
  json_string(out, pci);
}

static void json_calibrated_domains(FILE *out, const App *app)
{
  fputc('[', out);
  uint32_t stored = app->calibrated_domain_count;
  if (stored > H12_MAX_CALIBRATED_DOMAINS) {
    stored = H12_MAX_CALIBRATED_DOMAINS;
  }
  for (uint32_t i = 0; i < stored; ++i) {
    if (i != 0u) {
      fputc(',', out);
    }
    json_string(out, time_domain_name(app->calibrated_domains[i]));
  }
  fputc(']', out);
}

static void emit_xdg_surface_configure_diagnostic(
    App *app, const ConfigureDiagnostic *diagnostic)
{
  fprintf(app->log,
          "{\"schema\":\"" H12_PROBE_DIAGNOSTIC_SCHEMA
          "\",\"event\":\"xdg_surface_configure\""
          ",\"configure_index\":%" PRIu32 ",\"serial\":%" PRIu32,
          diagnostic->configure_index, diagnostic->serial);
  fputs(",\"phase\":", app->log);
  json_string(app->log, diagnostic->phase);
  fputs(",\"classification\":", app->log);
  if (diagnostic->classification != NULL) {
    json_string(app->log, diagnostic->classification);
  } else {
    fputs("null", app->log);
  }
  fputs(",\"state_only\":", app->log);
  fputs(diagnostic->state_only ? "true" : "false", app->log);
  fputs(",\"frame_id\":", app->log);
  if (diagnostic->frame_valid) {
    fprintf(app->log, "%" PRIu64, diagnostic->frame_id);
  } else {
    fputs("null", app->log);
  }
  fprintf(app->log,
          ",\"toplevel_configure_count\":%" PRIu32
          ",\"toplevel_configure_seen_before_surface_configure\":%s"
          ",\"have_toplevel_configure\":%s",
          diagnostic->toplevel_configure_count,
          diagnostic->toplevel_configure_pending_for_surface ? "true" : "false",
          diagnostic->have_toplevel_configure ? "true" : "false");
  fputs(",\"toplevel_width\":", app->log);
  json_i32_or_null(app->log, diagnostic->have_toplevel_configure,
                   diagnostic->toplevel_width);
  fputs(",\"toplevel_height\":", app->log);
  json_i32_or_null(app->log, diagnostic->have_toplevel_configure,
                   diagnostic->toplevel_height);
  fprintf(app->log, ",\"toplevel_state_count\":%" PRIu32,
          diagnostic->toplevel_state_count);
  fputs(",\"toplevel_states\":[", app->log);
  uint32_t stored_state_count =
      diagnostic->toplevel_state_count < H12_MAX_TOPLEVEL_STATES
          ? diagnostic->toplevel_state_count
          : H12_MAX_TOPLEVEL_STATES;
  for (uint32_t i = 0; i < stored_state_count; ++i) {
    if (i != 0u) {
      fputs(",", app->log);
    }
    fprintf(app->log, "%" PRIu32, diagnostic->toplevel_states[i]);
  }
  fputs("],\"toplevel_states_truncated\":", app->log);
  fputs(diagnostic->toplevel_states_truncated ? "true" : "false", app->log);
  fputs(",\"surface_configured\":", app->log);
  fputs(diagnostic->configured ? "true" : "false", app->log);
  fputs(",\"surface_width\":", app->log);
  json_u64_or_null(app->log, diagnostic->surface_size_valid,
                   diagnostic->surface_width);
  fputs(",\"surface_height\":", app->log);
  json_u64_or_null(app->log, diagnostic->surface_size_valid,
                   diagnostic->surface_height);
  fputs(",\"swapchain_created\":", app->log);
  fputs(diagnostic->swapchain_created ? "true" : "false", app->log);
  fprintf(app->log, ",\"swapchain_image_count\":%" PRIu32,
          diagnostic->swapchain_image_count);
  fputs(",\"initial_configure_completed\":", app->log);
  fputs(diagnostic->initial_configure_completed ? "true" : "false", app->log);
  fputs(",\"presentation_started\":", app->log);
  fputs(diagnostic->presentation_started ? "true" : "false", app->log);
  fputs(",\"first_present_completed\":", app->log);
  fputs(diagnostic->first_present_completed ? "true" : "false", app->log);
  fputs(",\"present_call_in_progress\":", app->log);
  fputs(diagnostic->present_call_in_progress ? "true" : "false", app->log);
  fprintf(app->log, ",\"submitted_frames\":%" PRIu32
                    ",\"ack_configure_requested\":true"
                    ",\"surface_reconfigure_pending\":%s}\n",
          diagnostic->submitted_frames,
          diagnostic->surface_reconfigure_pending ? "true" : "false");
  fflush(app->log);
}

static void write_xdg_surface_configure_diagnostic(App *app,
                                                    uint32_t serial,
                                                    const char *phase,
                                                    const char *classification,
                                                    bool state_only)
{
  ConfigureDiagnostic diagnostic = {0};
  diagnostic.valid = true;
  diagnostic.configure_index = app->xdg_surface_configure_count;
  diagnostic.serial = serial;
  diagnostic.phase = phase;
  diagnostic.classification = classification;
  diagnostic.state_only = state_only;
  diagnostic.frame_valid = g_abort_frame_valid;
  diagnostic.frame_id = g_abort_frame_id;
  diagnostic.toplevel_configure_count = app->toplevel_configure_count;
  diagnostic.toplevel_configure_pending_for_surface =
      app->toplevel_configure_pending_for_surface;
  diagnostic.have_toplevel_configure = app->have_toplevel_configure;
  diagnostic.toplevel_width = app->toplevel_width;
  diagnostic.toplevel_height = app->toplevel_height;
  diagnostic.toplevel_state_count = app->toplevel_state_count;
  memcpy(diagnostic.toplevel_states, app->toplevel_states,
         sizeof(diagnostic.toplevel_states));
  diagnostic.toplevel_states_truncated = app->toplevel_states_truncated;
  diagnostic.configured = app->configured;
  diagnostic.surface_size_valid = app->surface_width != 0u;
  diagnostic.surface_width = app->surface_width;
  diagnostic.surface_height = app->surface_height;
  diagnostic.swapchain_created = app->swapchain != VK_NULL_HANDLE;
  diagnostic.swapchain_image_count = app->swapchain_image_count;
  diagnostic.initial_configure_completed = app->initial_configure_completed;
  diagnostic.presentation_started = app->presentation_started;
  diagnostic.first_present_completed = app->first_present_completed;
  diagnostic.present_call_in_progress = app->present_call_in_progress;
  diagnostic.submitted_frames = app->submitted_frames;
  diagnostic.surface_reconfigure_pending = app->surface_reconfigure_pending;

  if (app->metadata_written) {
    emit_xdg_surface_configure_diagnostic(app, &diagnostic);
  } else {
    if (app->pending_configure_diagnostic_count >=
        H12_MAX_PENDING_CONFIGURE_DIAGNOSTICS) {
      fatal("too many pre-metadata xdg_surface.configure diagnostics");
    }
    app->pending_configure_diagnostics[
        app->pending_configure_diagnostic_count++] = diagnostic;
  }
}

/* A post-present configure may be safely observed without recreating the
 * swapchain only when the compositor supplied the exact baseline state that
 * has no geometry obligation and the raw extent is unchanged.  Keep this
 * predicate deliberately narrow: any other state or evidence remains a
 * safety hold. */
static bool post_present_extent_matches_active(const App *app)
{
  return app->have_toplevel_configure &&
         app->toplevel_configure_pending_for_surface &&
         app->have_toplevel_size && app->toplevel_width > 0 &&
         app->toplevel_height > 0 && app->surface_width != 0u &&
         app->surface_height != 0u &&
         (uint32_t)app->toplevel_width == app->surface_width &&
         (uint32_t)app->toplevel_height == app->surface_height;
}

static bool post_present_state_only_configure(const App *app)
{
  return app->initial_configure_completed && app->configured &&
         app->presentation_started && app->first_present_completed &&
         !app->present_call_in_progress && !app->surface_reconfigure_pending &&
         app->swapchain != VK_NULL_HANDLE && app->swapchain_image_count > 0u &&
         post_present_extent_matches_active(app) &&
         app->toplevel_state_count == 1u && !app->toplevel_states_truncated &&
         app->toplevel_states[0] ==
             (uint32_t)XDG_TOPLEVEL_STATE_ACTIVATED;
}

static const char *post_present_unsafe_classification(const App *app)
{
  if (app->present_call_in_progress) {
    return "POST_PRESENT_CONFIGURE_DURING_WSI_OPERATION";
  }
  if (app->have_toplevel_configure &&
      app->toplevel_configure_pending_for_surface &&
      !post_present_extent_matches_active(app)) {
    /* This is the future swapchain-recreation boundary.  H12-1 only holds;
     * it does not create or replace a swapchain here. */
    return "POST_PRESENT_EXTENT_CHANGE_REQUIRES_RECONFIGURE";
  }
  return "POST_PRESENT_CONFIGURE_UNCLASSIFIED";
}

static void emit_structured_abort(App *app, const char *code,
                                  const char *status, const char *reason)
{
  if (g_abort_event_written) {
    return;
  }
  g_abort_event_written = true;
  g_abort_final_state = "ABORTED";
  if (reason == NULL) {
    reason = "";
  }
  fputs("{\"schema\":\"" H12_PROBE_ERROR_SCHEMA
        "\",\"event\":\"error\",\"phase\":", app->log);
  json_string(app->log, g_abort_phase);
  fputs(",\"frame_id\":", app->log);
  if (g_abort_frame_valid) {
    fprintf(app->log, "%" PRIu64, g_abort_frame_id);
  } else {
    fputs("null", app->log);
  }
  fputs(",\"code\":", app->log);
  json_string(app->log, code);
  fputs(",\"status\":", app->log);
  json_string(app->log, status);
  fputs(",\"reason\":", app->log);
  json_string(app->log, reason);
  fputs(",\"cleanup_performed\":", app->log);
  fputs(g_abort_cleanup_performed ? "true" : "false", app->log);
  fputs(",\"cleanup_status\":", app->log);
  json_string(app->log, g_abort_cleanup_status);
  fputs(",\"final_state\":", app->log);
  json_string(app->log, g_abort_final_state);
  fputs(",\"summary_emitted\":true}\n", app->log);
  fflush(app->log);
}

static void structured_abort(App *app, const char *code,
                             const char *status, const char *reason)
{
  (void)app;
  if (g_abort_event_written || g_abort_event_pending) {
    return;
  }
  g_abort_event_pending = true;
  g_abort_pending_code = code;
  g_abort_pending_status = status;
  (void)snprintf(g_abort_pending_reason, sizeof(g_abort_pending_reason),
                 "%s", reason != NULL ? reason : "");
}

static bool extension_present(const VkExtensionProperties *properties,
                              uint32_t count, const char *name)
{
  for (uint32_t i = 0; i < count; ++i) {
    if (strcmp(properties[i].extensionName, name) == 0) {
      return true;
    }
  }
  return false;
}

static void check_vk(VkResult result, const char *operation)
{
  if (result != VK_SUCCESS) {
    fatal("%s failed: %s (%d)", operation, vk_result_name(result), result);
  }
}

/* ------------------------------------------------------------------------- */
/* Wayland window                                                            */
/* ------------------------------------------------------------------------- */

static void xdg_surface_handle_configure(void *data,
                                          struct xdg_surface *xdg_surface,
                                          uint32_t serial);
static void xdg_wm_base_handle_ping(void *data, struct xdg_wm_base *wm_base,
                                    uint32_t serial);
static void xdg_toplevel_handle_configure(void *data,
                                          struct xdg_toplevel *toplevel,
                                          int32_t width, int32_t height,
                                          struct wl_array *states);
static void xdg_toplevel_handle_close(void *data,
                                      struct xdg_toplevel *toplevel);
static void xdg_toplevel_handle_configure_bounds(void *data,
                                                  struct xdg_toplevel *toplevel,
                                                  int32_t width, int32_t height);
static void xdg_toplevel_handle_wm_capabilities(void *data,
                                                 struct xdg_toplevel *toplevel,
                                                 struct wl_array *capabilities);
static void frame_callback_done(void *data, struct wl_callback *callback,
                                uint32_t callback_time_ms);
static void registry_global(void *data, struct wl_registry *registry,
                            uint32_t name, const char *interface,
                            uint32_t version);
static void registry_global_remove(void *data, struct wl_registry *registry,
                                   uint32_t name);

static const struct xdg_surface_listener xdg_surface_listener = {
  .configure = xdg_surface_handle_configure,
};

static const struct xdg_wm_base_listener xdg_wm_base_listener = {
  .ping = xdg_wm_base_handle_ping,
};

static const struct xdg_toplevel_listener xdg_toplevel_listener = {
  .configure = xdg_toplevel_handle_configure,
  .close = xdg_toplevel_handle_close,
  .configure_bounds = xdg_toplevel_handle_configure_bounds,
  .wm_capabilities = xdg_toplevel_handle_wm_capabilities,
};

static const struct wl_callback_listener frame_callback_listener = {
  .done = frame_callback_done,
};

static const struct wl_registry_listener registry_listener = {
  .global = registry_global,
  .global_remove = registry_global_remove,
};

static void xdg_wm_base_handle_ping(void *data, struct xdg_wm_base *wm_base,
                                    uint32_t serial)
{
  (void)data;
  xdg_wm_base_pong(wm_base, serial);
}

static void xdg_toplevel_handle_configure(void *data,
                                          struct xdg_toplevel *toplevel,
                                          int32_t width, int32_t height,
                                          struct wl_array *states)
{
  App *app = (App *)data;
  (void)toplevel;
  ++app->toplevel_configure_count;
  app->toplevel_width = width;
  app->toplevel_height = height;
  app->have_toplevel_configure = true;
  app->toplevel_configure_pending_for_surface = true;
  app->toplevel_state_count = 0u;
  app->toplevel_states_truncated = false;
  uint32_t *state;
  wl_array_for_each(state, states) {
    if (app->toplevel_state_count < H12_MAX_TOPLEVEL_STATES) {
      app->toplevel_states[app->toplevel_state_count] = *state;
    } else {
      app->toplevel_states_truncated = true;
    }
    ++app->toplevel_state_count;
  }
  if (width > 0 && height > 0) {
    app->configured_width = width;
    app->configured_height = height;
    app->have_toplevel_size = true;
  }
}

static void xdg_toplevel_handle_close(void *data, struct xdg_toplevel *toplevel)
{
  App *app = (App *)data;
  (void)toplevel;
  app->close_requested = true;
}

static void xdg_toplevel_handle_configure_bounds(void *data,
                                                  struct xdg_toplevel *toplevel,
                                                  int32_t width, int32_t height)
{
  (void)data;
  (void)toplevel;
  (void)width;
  (void)height;
}

static void xdg_toplevel_handle_wm_capabilities(void *data,
                                                 struct xdg_toplevel *toplevel,
                                                 struct wl_array *capabilities)
{
  (void)data;
  (void)toplevel;
  (void)capabilities;
}

static void xdg_surface_handle_configure(void *data,
                                          struct xdg_surface *xdg_surface,
                                          uint32_t serial)
{
  App *app = (App *)data;
  ++app->xdg_surface_configure_count;
  int32_t width = app->cfg.width;
  int32_t height = app->cfg.height;

  if (app->have_toplevel_size) {
    width = app->configured_width;
    height = app->configured_height;
  }
  if (width <= 0 || height <= 0) {
    width = (int32_t)app->cfg.width;
    height = (int32_t)app->cfg.height;
  }

  bool initial_configure = !app->initial_configure_completed;
  bool after_first_present =
      app->first_present_completed || app->present_call_in_progress;
  bool state_only_configure = false;
  const char *classification = NULL;

  if (after_first_present) {
    state_only_configure = post_present_state_only_configure(app);
    if (state_only_configure) {
      classification = "POST_PRESENT_STATE_ONLY_CONFIGURE";
    } else {
      classification = post_present_unsafe_classification(app);
      app->surface_reconfigure_pending = true;
      app->surface_reconfigure_code = classification;
    }
  } else if (initial_configure) {
    classification = "INITIAL_CONFIGURE";
  } else if (app->surface_width != 0u &&
             ((uint32_t)width != app->surface_width ||
              (uint32_t)height != app->surface_height)) {
    classification = "PRE_PRESENT_EXTENT_CHANGE";
  } else {
    classification = "PRE_PRESENT_SAME_EXTENT";
  }

  xdg_surface_ack_configure(xdg_surface, serial);
  xdg_surface_set_window_geometry(app->xdg_surface, 0, 0, width, height);
  const char *diagnostic_phase =
      after_first_present
          ? "post_present"
          : (initial_configure ? "initialization" : "pre_present");
  write_xdg_surface_configure_diagnostic(
      app, serial, diagnostic_phase, classification, state_only_configure);
  app->toplevel_configure_pending_for_surface = false;
  if (after_first_present) {
    /* The exact activated/same-extent case is state-only.  In every other
     * post-present case the safety hold was set above.  In both cases do not
     * issue an application commit: Vulkan Wayland WSI owns attach/damage/commit
     * during present. */
    return;
  }
  if (initial_configure && app->swapchain != VK_NULL_HANDLE) {
    app->surface_reconfigure_pending = true;
    app->surface_reconfigure_code = "SURFACE_INITIAL_CONFIGURE_TOO_LATE";
    return;
  }
  if (!initial_configure && app->surface_width != 0u &&
      ((uint32_t)width != app->surface_width ||
       (uint32_t)height != app->surface_height)) {
    app->pre_present_extent_change = true;
    app->surface_reconfigure_pending = true;
    app->surface_reconfigure_code = "SURFACE_PRE_PRESENT_EXTENT_CHANGE";
    return;
  }
  wl_surface_commit(app->wl_surface);
  app->initial_configure_completed = true;
  app->surface_width = (uint32_t)width;
  app->surface_height = (uint32_t)height;
  app->configured = true;
}

static void frame_callback_done(void *data, struct wl_callback *callback,
                                uint32_t callback_time_ms)
{
  FrameCallbackData *callback_data = (FrameCallbackData *)data;
  FrameRecord *record = callback_data->record;

  if (record != NULL) {
    record->frame_callback_received_cpu_valid =
        monotonic_ns(&record->frame_callback_received_cpu_ns);
    record->cpu_callback_request_to_receive_valid = false;
    if (record->frame_callback_requested_cpu_valid &&
        record->frame_callback_received_cpu_valid &&
        record->frame_callback_received_cpu_ns >=
            record->frame_callback_requested_cpu_ns) {
      record->cpu_callback_request_to_receive_ns =
          record->frame_callback_received_cpu_ns -
          record->frame_callback_requested_cpu_ns;
      record->cpu_callback_request_to_receive_valid = true;
    }
    record->callback_received = true;
    record->callback_time_ms = callback_time_ms;
    record->callback_proxy = NULL;
    record->callback_data = NULL;
  }
  if (callback_data->app != NULL &&
      callback_data->app->pending_frame_callbacks > 0u) {
    --callback_data->app->pending_frame_callbacks;
  }
  wl_callback_destroy(callback);
  free(callback_data);
}

static void registry_global(void *data, struct wl_registry *registry,
                            uint32_t name, const char *interface,
                            uint32_t version)
{
  App *app = (App *)data;

  if (app->compositor == NULL &&
      strcmp(interface, wl_compositor_interface.name) == 0) {
    uint32_t bind_version = version < 4u ? version : 4u;
    app->compositor = (struct wl_compositor *)wl_registry_bind(
        registry, name, &wl_compositor_interface, bind_version);
  } else if (app->xdg_wm_base == NULL &&
             strcmp(interface, xdg_wm_base_interface.name) == 0) {
    uint32_t bind_version = version < 1u ? version : 1u;
    app->xdg_wm_base = (struct xdg_wm_base *)wl_registry_bind(
        registry, name, &xdg_wm_base_interface, bind_version);
    xdg_wm_base_add_listener(app->xdg_wm_base, &xdg_wm_base_listener, app);
  }
}

static void registry_global_remove(void *data, struct wl_registry *registry,
                                   uint32_t name)
{
  (void)data;
  (void)registry;
  (void)name;
}

static void wayland_dispatch_pending(App *app)
{
  while (wl_display_dispatch_pending(app->display) < 0) {
    if (errno == EAGAIN) {
      break;
    }
    fatal("wl_display_dispatch_pending failed");
  }
}

static void wayland_flush(App *app)
{
  while (wl_display_flush(app->display) < 0) {
    if (errno == EAGAIN) {
      app->wayland_needs_write = true;
      return;
    }
    fatal("wl_display_flush failed");
  }
  app->wayland_needs_write = false;
}

static void wayland_service(App *app, int timeout_ms)
{
  wayland_dispatch_pending(app);
  wayland_flush(app);

  struct pollfd poll_fd;
  poll_fd.fd = wl_display_get_fd(app->display);
  poll_fd.events = POLLIN;
  if (app->wayland_needs_write) {
    poll_fd.events |= POLLOUT;
  }
  poll_fd.revents = 0;

  int poll_result;
  do {
    poll_result = poll(&poll_fd, 1, timeout_ms);
  } while (poll_result < 0 && errno == EINTR);

  if (poll_result < 0) {
    fatal("poll(Wayland fd) failed: %s", strerror(errno));
  }
  if (poll_result == 0) {
    return;
  }
  if ((poll_fd.revents & POLLNVAL) != 0) {
    fatal("Wayland file descriptor became invalid");
  }
  if ((poll_fd.revents & POLLHUP) != 0) {
    fatal("Wayland display closed while probing");
  }
  if ((poll_fd.revents & POLLERR) != 0) {
    fatal("Wayland display reported a socket error");
  }
  if ((poll_fd.revents & POLLIN) != 0) {
    if (wl_display_dispatch(app->display) < 0) {
      fatal("wl_display_dispatch failed");
    }
  }
  if ((poll_fd.revents & POLLOUT) != 0) {
    wayland_flush(app);
  }
  wayland_dispatch_pending(app);
  wayland_flush(app);
}

static void abort_if_surface_reconfigured(App *app)
{
  if (!app->surface_reconfigure_pending) {
    return;
  }
  const char *code = app->surface_reconfigure_code != NULL
                         ? app->surface_reconfigure_code
                         : "SURFACE_RECONFIGURE_UNCLASSIFIED";
  const char *reason;
  if (strcmp(code, "SURFACE_INITIAL_CONFIGURE_TOO_LATE") == 0) {
    reason = "the initial xdg_surface.configure was not completed before "
             "swapchain creation";
  } else if (strcmp(code, "SURFACE_PRE_PRESENT_EXTENT_CHANGE") == 0) {
    reason = "xdg_surface.configure changed the extent before the first "
             "present; H12-1 has no swapchain recreation path";
  } else if (strcmp(code, "POST_PRESENT_EXTENT_CHANGE_REQUIRES_RECONFIGURE") == 0) {
    reason = "xdg_surface.configure arrived after the first present with an "
             "extent incompatible with the active surface; H12-1 has no "
             "swapchain recreation path";
  } else if (strcmp(code, "POST_PRESENT_CONFIGURE_DURING_WSI_OPERATION") == 0) {
    reason = "xdg_surface.configure arrived while the Vulkan Wayland WSI "
             "present operation was in progress; continuing safely is not "
             "supported by H12-1";
  } else if (strcmp(code, "POST_PRESENT_CONFIGURE_UNCLASSIFIED") == 0) {
    reason = "xdg_surface.configure arrived after the first present but did "
             "not satisfy the narrow activated/same-extent state-only path; "
             "raw state and dimensions were recorded and H12-1 stopped";
  } else {
    reason = "xdg_surface.configure was classified as an unclassified surface "
             "state change";
  }
  structured_abort(app, code, H12_STATUS_CONFLICT, reason);
  fatal("%s", reason);
}

static void init_wayland(App *app)
{
  app->display = wl_display_connect(NULL);
  if (app->display == NULL) {
    fatal("wl_display_connect failed; native Wayland is required");
  }

  app->registry = wl_display_get_registry(app->display);
  if (app->registry == NULL) {
    fatal("wl_display_get_registry failed");
  }
  wl_registry_add_listener(app->registry, &registry_listener, app);

  if (wl_display_roundtrip(app->display) < 0 ||
      wl_display_roundtrip(app->display) < 0) {
    fatal("Wayland registry roundtrip failed");
  }
  if (app->compositor == NULL) {
    fatal("Wayland compositor global is unavailable");
  }
  if (app->xdg_wm_base == NULL) {
    fatal("xdg_wm_base global is unavailable");
  }

  app->wl_surface = wl_compositor_create_surface(app->compositor);
  if (app->wl_surface == NULL) {
    fatal("wl_compositor_create_surface failed");
  }
  app->xdg_surface = xdg_wm_base_get_xdg_surface(app->xdg_wm_base,
                                                  app->wl_surface);
  if (app->xdg_surface == NULL) {
    fatal("xdg_wm_base_get_xdg_surface failed");
  }
  xdg_surface_add_listener(app->xdg_surface, &xdg_surface_listener, app);

  app->xdg_toplevel = xdg_surface_get_toplevel(app->xdg_surface);
  if (app->xdg_toplevel == NULL) {
    fatal("xdg_surface_get_toplevel failed");
  }
  xdg_toplevel_add_listener(app->xdg_toplevel, &xdg_toplevel_listener, app);
  xdg_toplevel_set_title(app->xdg_toplevel, "H12-1 clear/present probe");
  xdg_toplevel_set_app_id(app->xdg_toplevel, "org.rx550.h12_probe");
  xdg_toplevel_set_min_size(app->xdg_toplevel, (int32_t)app->cfg.width,
                            (int32_t)app->cfg.height);
  xdg_toplevel_set_max_size(app->xdg_toplevel, (int32_t)app->cfg.width,
                            (int32_t)app->cfg.height);

  /* xdg-shell requires an initial no-buffer commit before configure. */
  wl_surface_commit(app->wl_surface);
  if (wl_display_roundtrip(app->display) < 0) {
    fatal("Wayland initial xdg_surface configure failed");
  }
  if (!app->initial_configure_completed || !app->configured) {
    fatal("xdg_surface did not provide a completed initial configure");
  }
  wayland_service(app, 0);
  abort_if_surface_reconfigured(app);
  wayland_flush(app);
}

/* ------------------------------------------------------------------------- */
/* Vulkan instance/device                                                     */
/* ------------------------------------------------------------------------- */

static void load_instance_function_pointers(App *app)
{
  app->pfn_create_wayland_surface =
      (PFN_vkCreateWaylandSurfaceKHR)vkGetInstanceProcAddr(
          app->instance, "vkCreateWaylandSurfaceKHR");
  app->pfn_destroy_surface = (PFN_vkDestroySurfaceKHR)vkGetInstanceProcAddr(
      app->instance, "vkDestroySurfaceKHR");
  app->pfn_surface_support =
      (PFN_vkGetPhysicalDeviceSurfaceSupportKHR)vkGetInstanceProcAddr(
          app->instance, "vkGetPhysicalDeviceSurfaceSupportKHR");
  app->pfn_surface_capabilities =
      (PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR)vkGetInstanceProcAddr(
          app->instance, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
  app->pfn_surface_formats =
      (PFN_vkGetPhysicalDeviceSurfaceFormatsKHR)vkGetInstanceProcAddr(
          app->instance, "vkGetPhysicalDeviceSurfaceFormatsKHR");
  app->pfn_surface_present_modes =
      (PFN_vkGetPhysicalDeviceSurfacePresentModesKHR)vkGetInstanceProcAddr(
          app->instance, "vkGetPhysicalDeviceSurfacePresentModesKHR");
  if (app->instance_api_version >= VK_API_VERSION_1_1 ||
      app->instance_get_caps2) {
    app->pfn_surface_capabilities2 =
        (PFN_vkGetPhysicalDeviceSurfaceCapabilities2KHR)vkGetInstanceProcAddr(
            app->instance, "vkGetPhysicalDeviceSurfaceCapabilities2");
  }
  if (app->pfn_surface_capabilities2 == NULL &&
      app->instance_get_caps2) {
    app->pfn_surface_capabilities2 =
        (PFN_vkGetPhysicalDeviceSurfaceCapabilities2KHR)vkGetInstanceProcAddr(
            app->instance, "vkGetPhysicalDeviceSurfaceCapabilities2KHR");
  }
  if (app->instance_api_version >= VK_API_VERSION_1_1 ||
      app->instance_get_properties2) {
    app->pfn_features2 =
        (PFN_vkGetPhysicalDeviceFeatures2KHR)vkGetInstanceProcAddr(
            app->instance, "vkGetPhysicalDeviceFeatures2");
    if (app->pfn_features2 == NULL) {
      app->pfn_features2 =
          (PFN_vkGetPhysicalDeviceFeatures2KHR)vkGetInstanceProcAddr(
              app->instance, "vkGetPhysicalDeviceFeatures2KHR");
    }
    app->pfn_properties2 =
        (PFN_vkGetPhysicalDeviceProperties2KHR)vkGetInstanceProcAddr(
            app->instance, "vkGetPhysicalDeviceProperties2");
    if (app->pfn_properties2 == NULL) {
      app->pfn_properties2 =
          (PFN_vkGetPhysicalDeviceProperties2KHR)vkGetInstanceProcAddr(
              app->instance, "vkGetPhysicalDeviceProperties2KHR");
    }
    app->pfn_calibrateable_time_domains =
        (PFN_vkGetPhysicalDeviceCalibrateableTimeDomainsEXT)
            vkGetInstanceProcAddr(
                app->instance,
                "vkGetPhysicalDeviceCalibrateableTimeDomainsKHR");
    if (app->pfn_calibrateable_time_domains == NULL) {
      app->pfn_calibrateable_time_domains =
          (PFN_vkGetPhysicalDeviceCalibrateableTimeDomainsEXT)
              vkGetInstanceProcAddr(
                  app->instance,
                  "vkGetPhysicalDeviceCalibrateableTimeDomainsEXT");
    }
  }

  if (app->pfn_create_wayland_surface == NULL ||
      app->pfn_destroy_surface == NULL ||
      app->pfn_surface_support == NULL ||
      app->pfn_surface_capabilities == NULL ||
      app->pfn_surface_formats == NULL ||
      app->pfn_surface_present_modes == NULL) {
    fatal("Required Vulkan Wayland/WSI entry points are unavailable");
  }
}

static void create_instance(App *app)
{
  uint32_t loader_api = VK_API_VERSION_1_0;
  PFN_vkEnumerateInstanceVersion enumerate_instance_version =
      (PFN_vkEnumerateInstanceVersion)vkGetInstanceProcAddr(
          NULL, "vkEnumerateInstanceVersion");
  if (enumerate_instance_version != NULL &&
      enumerate_instance_version(&loader_api) != VK_SUCCESS) {
    loader_api = VK_API_VERSION_1_0;
  }
  if (loader_api < VK_API_VERSION_1_1) {
    loader_api = VK_API_VERSION_1_0;
  }
  app->instance_api_version = loader_api;

  uint32_t instance_extension_count = 0;
  check_vk(vkEnumerateInstanceExtensionProperties(NULL, &instance_extension_count,
                                                    NULL),
           "vkEnumerateInstanceExtensionProperties(count)");
  VkExtensionProperties *instance_extensions = calloc(instance_extension_count,
                                                       sizeof(*instance_extensions));
  if (instance_extensions == NULL) {
    fatal("Out of memory enumerating instance extensions");
  }
  check_vk(vkEnumerateInstanceExtensionProperties(NULL, &instance_extension_count,
                                                    instance_extensions),
           "vkEnumerateInstanceExtensionProperties(list)");

  bool have_surface = extension_present(instance_extensions,
                                        instance_extension_count,
                                        VK_KHR_SURFACE_EXTENSION_NAME);
  bool have_wayland = extension_present(instance_extensions,
                                        instance_extension_count,
                                        VK_KHR_WAYLAND_SURFACE_EXTENSION_NAME);
  app->instance_get_caps2 = extension_present(
      instance_extensions, instance_extension_count,
      VK_KHR_GET_SURFACE_CAPABILITIES_2_EXTENSION_NAME);
  app->instance_get_properties2 = extension_present(
      instance_extensions, instance_extension_count,
      VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME);
  free(instance_extensions);

  if (!have_surface || !have_wayland) {
    fatal("Required instance extensions are unavailable: VK_KHR_surface and "
          "VK_KHR_wayland_surface");
  }

  const char *enabled_extensions[4];
  uint32_t enabled_count = 0;
  enabled_extensions[enabled_count++] = VK_KHR_SURFACE_EXTENSION_NAME;
  enabled_extensions[enabled_count++] = VK_KHR_WAYLAND_SURFACE_EXTENSION_NAME;
  if (app->instance_get_caps2 && app->instance_api_version < VK_API_VERSION_1_1) {
    enabled_extensions[enabled_count++] =
        VK_KHR_GET_SURFACE_CAPABILITIES_2_EXTENSION_NAME;
  }
  if (app->instance_get_properties2 &&
      app->instance_api_version < VK_API_VERSION_1_1) {
    enabled_extensions[enabled_count++] =
        VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME;
  }

  VkApplicationInfo application_info = {
    .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
    .pApplicationName = "h12-1-vulkan-wayland-probe",
    .applicationVersion = VK_MAKE_VERSION(1, 0, 0),
    .pEngineName = "none",
    .engineVersion = VK_MAKE_VERSION(1, 0, 0),
    .apiVersion = app->instance_api_version,
  };
  VkInstanceCreateInfo create_info = {
    .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    .pApplicationInfo = &application_info,
    .enabledExtensionCount = enabled_count,
    .ppEnabledExtensionNames = enabled_extensions,
  };
  check_vk(vkCreateInstance(&create_info, NULL, &app->instance),
           "vkCreateInstance");
  load_instance_function_pointers(app);
}

static void create_vulkan_surface(App *app)
{
  VkWaylandSurfaceCreateInfoKHR create_info = {
    .sType = VK_STRUCTURE_TYPE_WAYLAND_SURFACE_CREATE_INFO_KHR,
    .display = app->display,
    .surface = app->wl_surface,
  };
  check_vk(app->pfn_create_wayland_surface(app->instance, &create_info, NULL,
                                           &app->surface),
           "vkCreateWaylandSurfaceKHR");
}

static void query_device_extensions(App *app)
{
  uint32_t count = 0;
  check_vk(vkEnumerateDeviceExtensionProperties(app->physical_device, NULL,
                                                 &count, NULL),
           "vkEnumerateDeviceExtensionProperties(count)");
  VkExtensionProperties *properties = calloc(count, sizeof(*properties));
  if (properties == NULL) {
    fatal("Out of memory enumerating device extensions");
  }
  check_vk(vkEnumerateDeviceExtensionProperties(app->physical_device, NULL,
                                                 &count, properties),
           "vkEnumerateDeviceExtensionProperties(list)");

  app->device_swapchain = extension_present(properties, count,
                                             VK_KHR_SWAPCHAIN_EXTENSION_NAME);
  app->device_pci_bus_info = extension_present(
      properties, count, VK_EXT_PCI_BUS_INFO_EXTENSION_NAME);
  app->device_calibrated_ext = extension_present(
      properties, count, VK_EXT_CALIBRATED_TIMESTAMPS_EXTENSION_NAME);
  app->device_calibrated_khr = extension_present(
      properties, count, VK_KHR_CALIBRATED_TIMESTAMPS_EXTENSION_NAME);
  app->device_calibrated_timestamps =
      app->device_calibrated_ext || app->device_calibrated_khr;
  app->device_present_id2 = extension_present(
      properties, count, VK_KHR_PRESENT_ID_2_EXTENSION_NAME);
  app->device_present_wait2 = extension_present(
      properties, count, VK_KHR_PRESENT_WAIT_2_EXTENSION_NAME);
  app->device_present_timing = extension_present(
      properties, count, VK_EXT_PRESENT_TIMING_EXTENSION_NAME);
  free(properties);

  if (!app->device_swapchain) {
    fatal("Required device extension is unavailable: VK_KHR_swapchain");
  }
}

static void query_calibrated_domains(App *app)
{
  app->calibrated_domain_query_valid = false;
  app->calibrated_domain_count = 0;
  app->calibrated_domains_truncated = false;
  app->calibrated_device_domain_supported = false;
  app->calibrated_monotonic_domain_supported = false;
  memset(app->calibrated_domains, 0, sizeof(app->calibrated_domains));

  if (!app->device_calibrated_timestamps ||
      app->pfn_calibrateable_time_domains == NULL) {
    app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
    return;
  }
  uint32_t available_count = 0;
  VkResult result = app->pfn_calibrateable_time_domains(
      app->physical_device, &available_count, NULL);
  if (result != VK_SUCCESS) {
    app->calibrated_timestamps_capability = H12_STATUS_UNKNOWN;
    return;
  }
  if (available_count == 0u) {
    app->calibrated_domain_query_valid = true;
    app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
    return;
  }

  uint32_t query_count = available_count;
  if (query_count > H12_MAX_CALIBRATED_DOMAINS) {
    query_count = H12_MAX_CALIBRATED_DOMAINS;
  }
  VkTimeDomainKHR *domain_values = calloc(query_count, sizeof(*domain_values));
  if (domain_values == NULL) {
    app->calibrated_timestamps_capability = H12_STATUS_UNKNOWN;
    return;
  }
  uint32_t written_count = query_count;
  result = app->pfn_calibrateable_time_domains(
      app->physical_device, &written_count, domain_values);
  if (result != VK_SUCCESS && result != VK_INCOMPLETE) {
    free(domain_values);
    app->calibrated_timestamps_capability = H12_STATUS_UNKNOWN;
    return;
  }
  bool domain_count_inconsistent = written_count != query_count;
  if (written_count > query_count) {
    written_count = query_count;
  }

  app->calibrated_domain_count = written_count;
  app->calibrated_domains_truncated =
      available_count > H12_MAX_CALIBRATED_DOMAINS || result == VK_INCOMPLETE ||
      domain_count_inconsistent;
  for (uint32_t i = 0; i < written_count; ++i) {
    app->calibrated_domains[i] = (uint32_t)domain_values[i];
    if (domain_values[i] == VK_TIME_DOMAIN_DEVICE_KHR) {
      app->calibrated_device_domain_supported = true;
    } else if (domain_values[i] == VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR) {
      app->calibrated_monotonic_domain_supported = true;
    }
  }
  free(domain_values);
  app->calibrated_domain_query_valid = true;
  if (app->calibrated_domains_truncated) {
    app->calibrated_timestamps_capability = H12_STATUS_UNKNOWN;
  } else if (!app->calibrated_device_domain_supported ||
             !app->calibrated_monotonic_domain_supported) {
    app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
  } else {
    app->calibrated_timestamps_capability = H12_STATUS_PRESENT;
  }
}

static void select_physical_device(App *app)
{
  uint32_t count = 0;
  check_vk(vkEnumeratePhysicalDevices(app->instance, &count, NULL),
           "vkEnumeratePhysicalDevices(count)");
  if (count == 0) {
    fatal("No Vulkan physical devices");
  }

  VkPhysicalDevice *devices = calloc(count, sizeof(*devices));
  if (devices == NULL) {
    fatal("Out of memory enumerating physical devices");
  }
  check_vk(vkEnumeratePhysicalDevices(app->instance, &count, devices),
           "vkEnumeratePhysicalDevices(list)");

  int matches = 0;
  VkPhysicalDevice selected = VK_NULL_HANDLE;
  VkPhysicalDeviceProperties selected_properties = {0};
  for (uint32_t i = 0; i < count; ++i) {
    VkPhysicalDeviceProperties properties = {0};
    vkGetPhysicalDeviceProperties(devices[i], &properties);
    fprintf(stderr,
            "Vulkan device [%u]: vendor=0x%04x device=0x%04x name=\"%s\"\n",
            i, properties.vendorID, properties.deviceID, properties.deviceName);
    if (properties.vendorID == H12_TARGET_VENDOR_ID &&
        properties.deviceID == H12_TARGET_DEVICE_ID) {
      selected = devices[i];
      selected_properties = properties;
      ++matches;
    }
  }
  free(devices);

  if (matches != 1) {
    fatal("Expected exactly one Vulkan device %04x:%04x, found %d",
          H12_TARGET_VENDOR_ID, H12_TARGET_DEVICE_ID, matches);
  }
  app->physical_device = selected;
  app->physical_properties = selected_properties;
  app->timestamp_period_ns = app->physical_properties.limits.timestampPeriod;
  query_device_extensions(app);

  if (app->pfn_properties2 != NULL) {
    app->physical_properties2 = (VkPhysicalDeviceProperties2){
      .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,
    };
    app->id_properties = (VkPhysicalDeviceIDProperties){
      .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES,
    };
    app->physical_properties2.pNext = &app->id_properties;

    if (app->instance_api_version >= VK_API_VERSION_1_2) {
      app->vulkan12_properties = (VkPhysicalDeviceVulkan12Properties){
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_PROPERTIES,
      };
      app->vulkan12_properties.pNext = &app->id_properties;
      app->physical_properties2.pNext = &app->vulkan12_properties;
    }
    if (app->device_pci_bus_info) {
      app->pci_info = (VkPhysicalDevicePCIBusInfoPropertiesEXT){
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PCI_BUS_INFO_PROPERTIES_EXT,
      };
      app->pci_info.pNext = app->physical_properties2.pNext;
      app->physical_properties2.pNext = &app->pci_info;
    }
    app->pfn_properties2(app->physical_device, &app->physical_properties2);
    app->physical_properties2_valid = true;
    app->id_properties_valid =
        uuid_is_nonzero(app->id_properties.deviceUUID) &&
        uuid_is_nonzero(app->id_properties.driverUUID);
    app->physical_properties = app->physical_properties2.properties;
    app->timestamp_period_ns = app->physical_properties.limits.timestampPeriod;
    app->pci_info_valid = app->device_pci_bus_info &&
                          (app->pci_info.pciDomain != 0 ||
                           app->pci_info.pciBus != 0 ||
                           app->pci_info.pciDevice != 0 ||
                           app->pci_info.pciFunction != 0);
    if (app->instance_api_version >= VK_API_VERSION_1_2) {
      app->vulkan12_properties_valid = true;
      memcpy(app->driver_name, app->vulkan12_properties.driverName,
             sizeof(app->driver_name));
      memcpy(app->driver_info, app->vulkan12_properties.driverInfo,
             sizeof(app->driver_info));
      app->driver_name[sizeof(app->driver_name) - 1u] = '\0';
      app->driver_info[sizeof(app->driver_info) - 1u] = '\0';
      app->driver_properties_valid = app->driver_name[0] != '\0';
    }
  }
  if (!app->driver_properties_valid) {
    (void)snprintf(app->driver_name, sizeof(app->driver_name), "%s", "UNKNOWN");
    (void)snprintf(app->driver_info, sizeof(app->driver_info), "%s", "UNKNOWN");
  }
  query_calibrated_domains(app);
}

static void select_queue_family(App *app)
{
  uint32_t count = 0;
  vkGetPhysicalDeviceQueueFamilyProperties(app->physical_device, &count, NULL);
  VkQueueFamilyProperties *families = calloc(count, sizeof(*families));
  if (families == NULL) {
    fatal("Out of memory enumerating queue families");
  }
  vkGetPhysicalDeviceQueueFamilyProperties(app->physical_device, &count,
                                           families);

  app->queue_family = H12_MAX_UINT32;
  VkQueueFamilyProperties selected_family = {0};
  for (uint32_t i = 0; i < count; ++i) {
    VkBool32 supported = VK_FALSE;
    VkResult result = app->pfn_surface_support(app->physical_device, i,
                                                app->surface, &supported);
    if (result != VK_SUCCESS) {
      continue;
    }
    fprintf(stderr,
            "Queue family [%u]: flags=0x%x count=%u timestamp_bits=%u surface=%s\n",
            i, families[i].queueFlags, families[i].queueCount,
            families[i].timestampValidBits, supported ? "yes" : "no");
    if (app->queue_family == H12_MAX_UINT32 &&
        (families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0 &&
        supported == VK_TRUE) {
      if (families[i].queueCount == 0) {
        continue;
      }
      app->queue_family = i;
      selected_family = families[i];
    }
  }
  free(families);

  if (app->queue_family == H12_MAX_UINT32) {
    fatal("No graphics queue family supports the Wayland Vulkan surface");
  }
  app->timestamp_valid_bits = selected_family.timestampValidBits;
  app->timestamp_query_count = app->timestamp_valid_bits > 0u ? H12_GPU_QUERY_COUNT : 0u;
}

static void query_device_features(App *app)
{
  if (app->pfn_features2 == NULL) {
    return;
  }

  VkPhysicalDeviceFeatures2 features = {
    .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
  };
  VkPhysicalDevicePresentId2FeaturesKHR present_id2 = {
    .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_ID_2_FEATURES_KHR,
  };
  VkPhysicalDevicePresentWait2FeaturesKHR present_wait2 = {
    .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_WAIT_2_FEATURES_KHR,
  };
  VkPhysicalDevicePresentTimingFeaturesEXT present_timing = {
    .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_TIMING_FEATURES_EXT,
  };

  void *tail = NULL;
  if (app->device_present_id2) {
    present_id2.pNext = tail;
    tail = &present_id2;
  }
  if (app->device_present_wait2) {
    present_wait2.pNext = tail;
    tail = &present_wait2;
  }
  if (app->device_present_timing) {
    present_timing.pNext = tail;
    tail = &present_timing;
  }
  features.pNext = tail;
  app->pfn_features2(app->physical_device, &features);

  if (app->device_present_id2 && app->pfn_surface_capabilities2 != NULL &&
      present_id2.presentId2) {
    app->present_id2_enabled = true;
  }
  if (app->device_present_wait2 && present_wait2.presentWait2 &&
      app->present_id2_enabled) {
    app->present_wait2_enabled = true;
  }
  bool calibrated_for_present_timing = app->device_calibrated_khr;
  app->present_timing_dependency_ok =
      app->device_present_timing && app->present_id2_enabled &&
      calibrated_for_present_timing && app->pfn_properties2 != NULL &&
      app->pfn_surface_capabilities2 != NULL;
  if (app->present_timing_dependency_ok && present_timing.presentTiming) {
    app->present_timing_capability = H12_STATUS_PRESENT;
  } else {
    app->present_timing_capability = H12_STATUS_NOT_AVAILABLE;
  }
  if (app->present_wait2_enabled) {
    app->present_wait2_capability = H12_STATUS_PRESENT;
  } else {
    app->present_wait2_capability = H12_STATUS_NOT_AVAILABLE;
  }
  if (!app->device_calibrated_timestamps) {
    app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
  } else if (!app->calibrated_domain_query_valid) {
    app->calibrated_timestamps_capability = H12_STATUS_UNKNOWN;
  }
}

static void create_device(App *app)
{
  const char *enabled_extensions[8];
  uint32_t enabled_count = 0;
  enabled_extensions[enabled_count++] = VK_KHR_SWAPCHAIN_EXTENSION_NAME;
  if (app->device_pci_bus_info && app->pfn_properties2 != NULL) {
    enabled_extensions[enabled_count++] = VK_EXT_PCI_BUS_INFO_EXTENSION_NAME;
  }
  if (app->pfn_properties2 != NULL) {
    if (app->device_calibrated_khr) {
      enabled_extensions[enabled_count++] =
          VK_KHR_CALIBRATED_TIMESTAMPS_EXTENSION_NAME;
    } else if (app->device_calibrated_ext) {
      enabled_extensions[enabled_count++] =
          VK_EXT_CALIBRATED_TIMESTAMPS_EXTENSION_NAME;
    }
  }
  if (app->present_id2_enabled) {
    enabled_extensions[enabled_count++] = VK_KHR_PRESENT_ID_2_EXTENSION_NAME;
  }
  if (app->present_wait2_enabled) {
    enabled_extensions[enabled_count++] = VK_KHR_PRESENT_WAIT_2_EXTENSION_NAME;
  }

  /* Only enable the timing extension when its feature and dependencies pass. */
  if (app->present_timing_capability != NULL &&
      strcmp(app->present_timing_capability, H12_STATUS_PRESENT) == 0 &&
      app->present_timing_dependency_ok) {
    enabled_extensions[enabled_count++] = VK_EXT_PRESENT_TIMING_EXTENSION_NAME;
  }

  VkPhysicalDevicePresentId2FeaturesKHR enabled_present_id2 = {
    .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_ID_2_FEATURES_KHR,
  };
  VkPhysicalDevicePresentWait2FeaturesKHR enabled_present_wait2 = {
    .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_WAIT_2_FEATURES_KHR,
  };
  VkPhysicalDevicePresentTimingFeaturesEXT enabled_present_timing = {
    .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PRESENT_TIMING_FEATURES_EXT,
  };
  void *feature_tail = NULL;
  if (app->present_id2_enabled) {
    enabled_present_id2.presentId2 = VK_TRUE;
    enabled_present_id2.pNext = feature_tail;
    feature_tail = &enabled_present_id2;
  }
  if (app->present_wait2_enabled) {
    enabled_present_wait2.presentWait2 = VK_TRUE;
    enabled_present_wait2.pNext = feature_tail;
    feature_tail = &enabled_present_wait2;
  }
  if (app->present_timing_capability != NULL &&
      strcmp(app->present_timing_capability, H12_STATUS_PRESENT) == 0 &&
      app->present_timing_dependency_ok) {
    enabled_present_timing.presentTiming = VK_TRUE;
    enabled_present_timing.pNext = feature_tail;
    feature_tail = &enabled_present_timing;
  }

  float priority = 1.0f;
  VkDeviceQueueCreateInfo queue_info = {
    .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
    .queueFamilyIndex = app->queue_family,
    .queueCount = 1,
    .pQueuePriorities = &priority,
  };
  VkDeviceCreateInfo device_info = {
    .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
    .pNext = feature_tail,
    .queueCreateInfoCount = 1,
    .pQueueCreateInfos = &queue_info,
    .enabledExtensionCount = enabled_count,
    .ppEnabledExtensionNames = enabled_extensions,
  };
  check_vk(vkCreateDevice(app->physical_device, &device_info, NULL,
                           &app->device),
           "vkCreateDevice");
  app->logical_device_created = true;
  vkGetDeviceQueue(app->device, app->queue_family, 0, &app->queue);
}

static void load_device_function_pointers(App *app)
{
  if (app->present_timing_capability != NULL &&
      strcmp(app->present_timing_capability, H12_STATUS_PRESENT) == 0 &&
      app->present_timing_dependency_ok) {
    app->pfn_set_present_timing_queue_size =
        (PFN_vkSetSwapchainPresentTimingQueueSizeEXT)vkGetDeviceProcAddr(
            app->device, "vkSetSwapchainPresentTimingQueueSizeEXT");
    app->pfn_get_past_presentation_timing =
        (PFN_vkGetPastPresentationTimingEXT)vkGetDeviceProcAddr(
            app->device, "vkGetPastPresentationTimingEXT");
    app->pfn_get_swapchain_time_domains =
        (PFN_vkGetSwapchainTimeDomainPropertiesEXT)vkGetDeviceProcAddr(
            app->device, "vkGetSwapchainTimeDomainPropertiesEXT");
    if (app->pfn_set_present_timing_queue_size == NULL ||
        app->pfn_get_past_presentation_timing == NULL ||
        app->pfn_get_swapchain_time_domains == NULL) {
      app->present_timing_capability = H12_STATUS_CONFLICT;
      app->present_timing_enabled = false;
      app->present_timing_dependency_ok = false;
    }
  }

  if (!app->device_calibrated_timestamps) {
    app->calibrated_timestamp_variant = NULL;
    app->pfn_get_calibrated_timestamps = NULL;
    app->calibrated_function_available = false;
    app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
    return;
  }
  app->calibrated_timestamp_variant = NULL;
  if (app->device_calibrated_khr) {
    app->pfn_get_calibrated_timestamps =
        (PFN_vkGetCalibratedTimestampsKHR)vkGetDeviceProcAddr(
            app->device, "vkGetCalibratedTimestampsKHR");
    if (app->pfn_get_calibrated_timestamps != NULL) {
      app->calibrated_timestamp_variant = "KHR";
    }
  } else {
    app->pfn_get_calibrated_timestamps =
        (PFN_vkGetCalibratedTimestampsKHR)vkGetDeviceProcAddr(
            app->device, "vkGetCalibratedTimestampsEXT");
    if (app->pfn_get_calibrated_timestamps != NULL) {
      app->calibrated_timestamp_variant = "EXT";
    }
  }
  app->calibrated_function_available =
      app->pfn_get_calibrated_timestamps != NULL;
  if (!app->calibrated_function_available ||
      app->pfn_calibrateable_time_domains == NULL) {
    app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
  } else if (!app->calibrated_domain_query_valid) {
    app->calibrated_timestamps_capability = H12_STATUS_UNKNOWN;
  } else if (app->calibrated_domains_truncated) {
    app->calibrated_timestamps_capability = H12_STATUS_UNKNOWN;
  } else if (!app->calibrated_device_domain_supported ||
             !app->calibrated_monotonic_domain_supported) {
    app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
  } else {
    app->calibrated_timestamps_capability = H12_STATUS_PRESENT;
  }
}

/* ------------------------------------------------------------------------- */
/* Surface capabilities and swapchain                                        */
/* ------------------------------------------------------------------------- */

static bool format_is_preferred(VkFormat format)
{
  return format == VK_FORMAT_B8G8R8A8_UNORM ||
         format == VK_FORMAT_B8G8R8A8_SRGB ||
         format == VK_FORMAT_R8G8B8A8_UNORM ||
         format == VK_FORMAT_R8G8B8A8_SRGB;
}

static const char *present_mode_name(VkPresentModeKHR mode)
{
  switch (mode) {
    case VK_PRESENT_MODE_IMMEDIATE_KHR:
      return "IMMEDIATE";
    case VK_PRESENT_MODE_MAILBOX_KHR:
      return "MAILBOX";
    case VK_PRESENT_MODE_FIFO_KHR:
      return "FIFO";
    case VK_PRESENT_MODE_FIFO_RELAXED_KHR:
      return "FIFO_RELAXED";
    default:
      return "UNRECOGNIZED";
  }
}

static void query_surface_state(App *app)
{
  memset(&app->present_id2_surface_capabilities, 0,
         sizeof(app->present_id2_surface_capabilities));
  memset(&app->present_timing_surface_capabilities, 0,
         sizeof(app->present_timing_surface_capabilities));
  memset(&app->present_wait2_surface_capabilities, 0,
         sizeof(app->present_wait2_surface_capabilities));

  if (app->pfn_surface_capabilities2 != NULL) {
    VkSurfaceCapabilities2KHR capabilities = {
      .sType = VK_STRUCTURE_TYPE_SURFACE_CAPABILITIES_2_KHR,
    };
    VkSurfaceCapabilitiesPresentId2KHR present_id2_capabilities = {
      .sType = VK_STRUCTURE_TYPE_SURFACE_CAPABILITIES_PRESENT_ID_2_KHR,
    };
    VkPresentTimingSurfaceCapabilitiesEXT timing_capabilities = {
      .sType = VK_STRUCTURE_TYPE_PRESENT_TIMING_SURFACE_CAPABILITIES_EXT,
    };
    VkSurfaceCapabilitiesPresentWait2KHR wait2_capabilities = {
      .sType = VK_STRUCTURE_TYPE_SURFACE_CAPABILITIES_PRESENT_WAIT_2_KHR,
    };
    void *tail = NULL;
    if (app->present_id2_enabled) {
      present_id2_capabilities.pNext = tail;
      tail = &present_id2_capabilities;
    }
    bool timing_capability_ready =
        app->present_timing_capability != NULL &&
        strcmp(app->present_timing_capability, H12_STATUS_PRESENT) == 0 &&
        app->present_timing_dependency_ok;
    if (timing_capability_ready) {
      timing_capabilities.pNext = tail;
      tail = &timing_capabilities;
    }
    if (app->present_wait2_enabled) {
      wait2_capabilities.pNext = tail;
      tail = &wait2_capabilities;
    }
    capabilities.pNext = tail;
    VkPhysicalDeviceSurfaceInfo2KHR surface_info = {
      .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SURFACE_INFO_2_KHR,
      .surface = app->surface,
    };
    check_vk(app->pfn_surface_capabilities2(app->physical_device, &surface_info,
                                             &capabilities),
             "vkGetPhysicalDeviceSurfaceCapabilities2");
    app->surface_capabilities = capabilities.surfaceCapabilities;
    if (app->present_id2_enabled) {
      app->present_id2_surface_capabilities = present_id2_capabilities;
      app->present_id2_surface_supported =
          present_id2_capabilities.presentId2Supported == VK_TRUE;
      app->present_id2_usable = app->present_id2_surface_supported;
      app->present_id2_capability = app->present_id2_usable
                                        ? H12_STATUS_PRESENT
                                        : H12_STATUS_NOT_AVAILABLE;
    }
    if (timing_capability_ready &&
        app->present_id2_usable) {
      app->present_timing_surface_capabilities = timing_capabilities;
      app->present_timing_surface_supported =
          timing_capabilities.presentTimingSupported == VK_TRUE;
      app->present_timing_stage_queries =
          timing_capabilities.presentStageQueries;
    }
    if (app->present_wait2_enabled) {
      app->present_wait2_surface_capabilities = wait2_capabilities;
      app->present_wait2_surface_supported =
          wait2_capabilities.presentWait2Supported == VK_TRUE;
    }
  } else {
    check_vk(app->pfn_surface_capabilities(app->physical_device, app->surface,
                                            &app->surface_capabilities),
             "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
  }

  uint32_t format_count = 0;
  check_vk(app->pfn_surface_formats(app->physical_device, app->surface,
                                    &format_count, NULL),
           "vkGetPhysicalDeviceSurfaceFormatsKHR(count)");
  if (format_count == 0) {
    fatal("Wayland Vulkan surface exposes no formats");
  }
  VkSurfaceFormatKHR *formats = calloc(format_count, sizeof(*formats));
  if (formats == NULL) {
    fatal("Out of memory enumerating surface formats");
  }
  check_vk(app->pfn_surface_formats(app->physical_device, app->surface,
                                    &format_count, formats),
           "vkGetPhysicalDeviceSurfaceFormatsKHR(list)");
  app->surface_format = formats[0];
  for (uint32_t i = 0; i < format_count; ++i) {
    if (format_is_preferred(formats[i].format)) {
      app->surface_format = formats[i];
      break;
    }
  }
  free(formats);

  uint32_t mode_count = 0;
  check_vk(app->pfn_surface_present_modes(app->physical_device, app->surface,
                                           &mode_count, NULL),
           "vkGetPhysicalDeviceSurfacePresentModesKHR(count)");
  if (mode_count == 0) {
    fatal("Wayland Vulkan surface exposes no present modes");
  }
  VkPresentModeKHR *modes = calloc(mode_count, sizeof(*modes));
  if (modes == NULL) {
    fatal("Out of memory enumerating present modes");
  }
  check_vk(app->pfn_surface_present_modes(app->physical_device, app->surface,
                                           &mode_count, modes),
           "vkGetPhysicalDeviceSurfacePresentModesKHR(list)");

  bool requested_supported = false;
  for (uint32_t i = 0; i < mode_count; ++i) {
    if (modes[i] == app->cfg.requested_present_mode) {
      requested_supported = true;
      break;
    }
  }
  if (!requested_supported) {
    fprintf(stderr, "Requested present mode %s is not supported; available:",
            app->cfg.requested_present_mode_name);
    for (uint32_t i = 0; i < mode_count; ++i) {
      fprintf(stderr, " %s", present_mode_name(modes[i]));
    }
    fputc('\n', stderr);
    free(modes);
    fatal("Requested present mode is unavailable");
  }
  app->selected_present_mode = app->cfg.requested_present_mode;
  app->selected_present_mode_name = present_mode_name(app->selected_present_mode);
  free(modes);

  uint32_t desired_width = app->surface_width != 0 ? app->surface_width
                                                    : app->cfg.width;
  uint32_t desired_height = app->surface_height != 0 ? app->surface_height
                                                     : app->cfg.height;
  const VkSurfaceCapabilitiesKHR *caps = &app->surface_capabilities;
  if (caps->currentExtent.width != H12_MAX_UINT32) {
    desired_width = caps->currentExtent.width;
    desired_height = caps->currentExtent.height;
  }
  desired_width = desired_width < caps->minImageExtent.width
                      ? caps->minImageExtent.width
                      : desired_width;
  desired_height = desired_height < caps->minImageExtent.height
                       ? caps->minImageExtent.height
                       : desired_height;
  if (caps->maxImageExtent.width != 0 &&
      desired_width > caps->maxImageExtent.width) {
    desired_width = caps->maxImageExtent.width;
  }
  if (caps->maxImageExtent.height != 0 &&
      desired_height > caps->maxImageExtent.height) {
    desired_height = caps->maxImageExtent.height;
  }
  if (desired_width == 0 || desired_height == 0) {
    fatal("Resolved surface extent is zero");
  }
  app->surface_width = desired_width;
  app->surface_height = desired_height;
  app->swapchain_image_count = caps->minImageCount;
  if (app->swapchain_image_count == 0) {
    app->swapchain_image_count = 1;
  }
  if (caps->maxImageCount != 0 &&
      app->swapchain_image_count > caps->maxImageCount) {
    app->swapchain_image_count = caps->maxImageCount;
  }
  if (app->swapchain_image_count == 0) {
    fatal("Swapchain has no usable image count");
  }

  app->present_timing_enabled = false;
  if (app->present_timing_capability != NULL &&
      strcmp(app->present_timing_capability, H12_STATUS_PRESENT) == 0 &&
      app->present_timing_dependency_ok && app->present_id2_usable &&
      app->present_timing_surface_supported &&
      (app->present_timing_stage_queries &
       VK_PRESENT_STAGE_QUEUE_OPERATIONS_END_BIT_EXT) != 0) {
    app->present_timing_enabled = true;
  } else if (app->present_timing_capability != NULL &&
             strcmp(app->present_timing_capability, H12_STATUS_PRESENT) == 0) {
    app->present_timing_capability = H12_STATUS_NOT_AVAILABLE;
  }

  if (app->present_wait2_capability != NULL &&
      strcmp(app->present_wait2_capability, H12_STATUS_PRESENT) == 0 &&
      (!app->present_id2_usable ||
       !app->present_wait2_surface_supported)) {
    app->present_wait2_capability = H12_STATUS_NOT_AVAILABLE;
  }
}

static void create_render_pass(App *app)
{
  VkAttachmentDescription attachment = {
    .format = app->surface_format.format,
    .samples = VK_SAMPLE_COUNT_1_BIT,
    .loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR,
    .storeOp = VK_ATTACHMENT_STORE_OP_STORE,
    .stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE,
    .stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE,
    .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    .finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
  };
  VkAttachmentReference color_attachment = {
    .attachment = 0,
    .layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
  };
  VkSubpassDescription subpass = {
    .pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS,
    .colorAttachmentCount = 1,
    .pColorAttachments = &color_attachment,
  };
  VkRenderPassCreateInfo render_pass_info = {
    .sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
    .attachmentCount = 1,
    .pAttachments = &attachment,
    .subpassCount = 1,
    .pSubpasses = &subpass,
  };
  check_vk(vkCreateRenderPass(app->device, &render_pass_info, NULL,
                               &app->render_pass),
           "vkCreateRenderPass");
}

static void destroy_swapchain_images(App *app)
{
  if (app->swapchain_framebuffers != NULL) {
    for (uint32_t i = 0; i < app->swapchain_image_count; ++i) {
      if (app->swapchain_framebuffers[i] != VK_NULL_HANDLE) {
        vkDestroyFramebuffer(app->device, app->swapchain_framebuffers[i], NULL);
      }
    }
    free(app->swapchain_framebuffers);
    app->swapchain_framebuffers = NULL;
  }
  if (app->swapchain_views != NULL) {
    for (uint32_t i = 0; i < app->swapchain_image_count; ++i) {
      if (app->swapchain_views[i] != VK_NULL_HANDLE) {
        vkDestroyImageView(app->device, app->swapchain_views[i], NULL);
      }
    }
    free(app->swapchain_views);
    app->swapchain_views = NULL;
  }
  free(app->swapchain_images);
  app->swapchain_images = NULL;
  if (app->swapchain != VK_NULL_HANDLE) {
    vkDestroySwapchainKHR(app->device, app->swapchain, NULL);
    app->swapchain = VK_NULL_HANDLE;
  }
}

static uint32_t first_set_bit_u32(uint32_t value)
{
  if (value == 0) {
    return 0;
  }
  return value & (~value + 1u);
}

static void create_swapchain(App *app, bool with_present_timing)
{
  VkSurfaceTransformFlagBitsKHR transform =
      VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR;
  if ((app->surface_capabilities.supportedTransforms & transform) == 0) {
    uint32_t transform_bits = first_set_bit_u32(
        app->surface_capabilities.supportedTransforms);
    if (transform_bits == 0) {
      fatal("Surface exposes no supported transform");
    }
    transform = (VkSurfaceTransformFlagBitsKHR)transform_bits;
  }
  VkCompositeAlphaFlagBitsKHR composite_alpha =
      VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
  if ((app->surface_capabilities.supportedCompositeAlpha & composite_alpha) == 0) {
    uint32_t alpha_bits = first_set_bit_u32(
        app->surface_capabilities.supportedCompositeAlpha);
    if (alpha_bits == 0) {
      fatal("Surface exposes no supported composite alpha");
    }
    composite_alpha = (VkCompositeAlphaFlagBitsKHR)alpha_bits;
  }

  VkFlags swapchain_flags = 0;
  if (app->present_id2_usable) {
    swapchain_flags |= VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR;
  }
  if (with_present_timing) {
    swapchain_flags |= VK_SWAPCHAIN_CREATE_PRESENT_TIMING_BIT_EXT;
  }

  VkSwapchainCreateInfoKHR create_info = {
    .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
    .flags = swapchain_flags,
    .surface = app->surface,
    .minImageCount = app->swapchain_image_count,
    .imageFormat = app->surface_format.format,
    .imageColorSpace = app->surface_format.colorSpace,
    .imageExtent = (VkExtent2D){app->surface_width, app->surface_height},
    .imageArrayLayers = 1,
    .imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
    .imageSharingMode = VK_SHARING_MODE_EXCLUSIVE,
    .queueFamilyIndexCount = 1,
    .pQueueFamilyIndices = &app->queue_family,
    .preTransform = transform,
    .compositeAlpha = composite_alpha,
    .presentMode = app->selected_present_mode,
    .clipped = VK_TRUE,
    .oldSwapchain = VK_NULL_HANDLE,
  };
  check_vk(vkCreateSwapchainKHR(app->device, &create_info, NULL,
                                 &app->swapchain),
           "vkCreateSwapchainKHR");

  uint32_t image_count = 0;
  check_vk(vkGetSwapchainImagesKHR(app->device, app->swapchain, &image_count,
                                    NULL),
           "vkGetSwapchainImagesKHR(count)");
  if (image_count == 0) {
    fatal("Swapchain returned zero images");
  }
  app->swapchain_image_count = image_count;
  app->swapchain_images = calloc(image_count, sizeof(*app->swapchain_images));
  app->swapchain_views = calloc(image_count, sizeof(*app->swapchain_views));
  app->swapchain_framebuffers = calloc(image_count,
                                       sizeof(*app->swapchain_framebuffers));
  app->present_semaphores = calloc(image_count,
                                   sizeof(*app->present_semaphores));
  if (app->swapchain_images == NULL || app->swapchain_views == NULL ||
      app->swapchain_framebuffers == NULL ||
      app->present_semaphores == NULL) {
    fatal("Out of memory allocating swapchain image arrays");
  }
  check_vk(vkGetSwapchainImagesKHR(app->device, app->swapchain, &image_count,
                                    app->swapchain_images),
           "vkGetSwapchainImagesKHR(list)");

  for (uint32_t i = 0; i < image_count; ++i) {
    VkSemaphoreCreateInfo semaphore_info = {
      .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO,
    };
    check_vk(vkCreateSemaphore(app->device, &semaphore_info, NULL,
                                &app->present_semaphores[i]),
             "vkCreateSemaphore(present-by-image)");
  }

  create_render_pass(app);
  for (uint32_t i = 0; i < image_count; ++i) {
    VkImageViewCreateInfo view_info = {
      .sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
      .image = app->swapchain_images[i],
      .viewType = VK_IMAGE_VIEW_TYPE_2D,
      .format = app->surface_format.format,
      .subresourceRange = (VkImageSubresourceRange){
        .aspectMask = VK_IMAGE_ASPECT_COLOR_BIT,
        .baseMipLevel = 0,
        .levelCount = 1,
        .baseArrayLayer = 0,
        .layerCount = 1,
      },
    };
    check_vk(vkCreateImageView(app->device, &view_info, NULL,
                               &app->swapchain_views[i]),
             "vkCreateImageView(swapchain)");

    VkFramebufferCreateInfo framebuffer_info = {
      .sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
      .renderPass = app->render_pass,
      .attachmentCount = 1,
      .pAttachments = &app->swapchain_views[i],
      .width = app->surface_width,
      .height = app->surface_height,
      .layers = 1,
    };
    check_vk(vkCreateFramebuffer(app->device, &framebuffer_info, NULL,
                                  &app->swapchain_framebuffers[i]),
             "vkCreateFramebuffer(swapchain)");
  }
}

static void initialize_present_timing(App *app)
{
  if (!app->present_timing_enabled) {
    return;
  }
  if (app->pfn_set_present_timing_queue_size == NULL ||
      app->pfn_get_past_presentation_timing == NULL ||
      app->pfn_get_swapchain_time_domains == NULL) {
    app->present_timing_enabled = false;
    app->present_timing_capability = H12_STATUS_CONFLICT;
    return;
  }

  if (app->swapchain_image_count > UINT32_MAX / 2u) {
    app->present_timing_enabled = false;
    app->present_timing_capability = H12_STATUS_CONFLICT;
    return;
  }
  app->present_timing_queue_size = app->swapchain_image_count * 2u;
  if (app->present_timing_queue_size < 8u) {
    app->present_timing_queue_size = 8u;
  }
  VkResult result = app->pfn_set_present_timing_queue_size(
      app->device, app->swapchain, app->present_timing_queue_size);
  if (result != VK_SUCCESS) {
    fprintf(stderr,
            "vkSetSwapchainPresentTimingQueueSizeEXT failed: %s; timing disabled\n",
            vk_result_name(result));
    app->present_timing_enabled = false;
    app->present_timing_capability = H12_STATUS_CONFLICT;
    return;
  }

  VkSwapchainTimeDomainPropertiesEXT domains = {
    .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_TIME_DOMAIN_PROPERTIES_EXT,
  };
  uint64_t domains_counter = 0;
  result = app->pfn_get_swapchain_time_domains(app->device, app->swapchain,
                                                &domains, &domains_counter);
  if (result != VK_SUCCESS || domains.timeDomainCount == 0) {
    fprintf(stderr,
            "vkGetSwapchainTimeDomainPropertiesEXT unavailable: %s; timing disabled\n",
            vk_result_name(result));
    app->present_timing_enabled = false;
    app->present_timing_capability = H12_STATUS_CONFLICT;
    return;
  }

  VkTimeDomainKHR *domain_values = calloc(domains.timeDomainCount,
                                          sizeof(*domain_values));
  uint64_t *domain_ids = calloc(domains.timeDomainCount, sizeof(*domain_ids));
  if (domain_values == NULL || domain_ids == NULL) {
    free(domain_values);
    free(domain_ids);
    fatal("Out of memory querying present timing domains");
  }
  domains.pTimeDomains = domain_values;
  domains.pTimeDomainIds = domain_ids;
  result = app->pfn_get_swapchain_time_domains(app->device, app->swapchain,
                                                &domains, &domains_counter);
  if (result != VK_SUCCESS) {
    free(domain_values);
    free(domain_ids);
    app->present_timing_enabled = false;
    app->present_timing_capability = H12_STATUS_CONFLICT;
    return;
  }
  for (uint32_t i = 0; i < domains.timeDomainCount; ++i) {
    if (domain_values[i] == VK_TIME_DOMAIN_SWAPCHAIN_LOCAL_EXT) {
      app->present_timing_time_domain_kind = VK_TIME_DOMAIN_SWAPCHAIN_LOCAL_EXT;
      app->present_timing_time_domain_id = domain_ids[i];
      app->present_timing_time_domain_stage = 0;
      app->present_timing_time_domain_valid = true;
      break;
    }
  }
  if (!app->present_timing_time_domain_valid) {
    for (uint32_t i = 0; i < domains.timeDomainCount; ++i) {
      if (domain_values[i] == VK_TIME_DOMAIN_PRESENT_STAGE_LOCAL_EXT) {
        app->present_timing_time_domain_kind =
            VK_TIME_DOMAIN_PRESENT_STAGE_LOCAL_EXT;
        app->present_timing_time_domain_id = domain_ids[i];
        app->present_timing_time_domain_stage =
            VK_PRESENT_STAGE_QUEUE_OPERATIONS_END_BIT_EXT;
        app->present_timing_time_domain_valid = true;
        break;
      }
    }
  }
  free(domain_values);
  free(domain_ids);
  if (!app->present_timing_time_domain_valid) {
    app->present_timing_enabled = false;
    app->present_timing_capability = H12_STATUS_CONFLICT;
    return;
  }

  app->present_timing_time_domains_counter = domains_counter;
  app->present_timing_stage_queries =
      VK_PRESENT_STAGE_QUEUE_OPERATIONS_END_BIT_EXT;
  app->present_timing_results = calloc(
      app->present_timing_queue_size, sizeof(*app->present_timing_results));
  app->present_timing_stage_storage = calloc(
      app->present_timing_queue_size, sizeof(*app->present_timing_stage_storage));
  if (app->present_timing_results != NULL &&
      app->present_timing_stage_storage != NULL) {
    for (uint32_t i = 0; i < app->present_timing_queue_size; ++i) {
      app->present_timing_results[i].sType =
          VK_STRUCTURE_TYPE_PAST_PRESENTATION_TIMING_EXT;
      app->present_timing_results[i].pPresentStages =
          &app->present_timing_stage_storage[i];
    }
  }
  if (app->present_timing_results == NULL ||
      app->present_timing_stage_storage == NULL) {
    free(app->present_timing_results);
    free(app->present_timing_stage_storage);
    app->present_timing_results = NULL;
    app->present_timing_stage_storage = NULL;
    app->present_timing_enabled = false;
    app->present_timing_capability = H12_STATUS_CONFLICT;
  }
}

static void create_swapchain_and_timing(App *app)
{
  bool with_timing = app->present_timing_enabled;
  create_swapchain(app, with_timing);
  if (with_timing) {
    initialize_present_timing(app);
  }
}

/* ------------------------------------------------------------------------- */
/* GPU timestamps and frame resources                                        */
/* ------------------------------------------------------------------------- */

static void create_command_resources(App *app)
{
  VkCommandPoolCreateInfo pool_info = {
    .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
    .flags = 0,
    .queueFamilyIndex = app->queue_family,
  };
  check_vk(vkCreateCommandPool(app->device, &pool_info, NULL,
                                &app->command_pool),
           "vkCreateCommandPool");

  app->resource_count = H12_FRAMES_IN_FLIGHT;
  if (app->resource_count > app->swapchain_image_count) {
    app->resource_count = app->swapchain_image_count;
  }
  if (app->resource_count == 0) {
    app->resource_count = 1;
  }
  app->resources = calloc(app->resource_count, sizeof(*app->resources));
  app->records = calloc(app->cfg.frames, sizeof(*app->records));
  if (app->resources == NULL || app->records == NULL) {
    fatal("Out of memory allocating frame resources");
  }

  for (uint32_t i = 0; i < app->resource_count; ++i) {
    FrameResource *resource = &app->resources[i];
    VkCommandBufferAllocateInfo command_info = {
      .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
      .commandPool = app->command_pool,
      .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
      .commandBufferCount = 1,
    };
    check_vk(vkAllocateCommandBuffers(app->device, &command_info,
                                        &resource->command_buffer),
             "vkAllocateCommandBuffers");

    VkSemaphoreCreateInfo semaphore_info = {
      .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO,
    };
    check_vk(vkCreateSemaphore(app->device, &semaphore_info, NULL,
                                &resource->acquire_semaphore),
             "vkCreateSemaphore(acquire)");

    VkFenceCreateInfo fence_info = {
      .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
    };
    check_vk(vkCreateFence(app->device, &fence_info, NULL, &resource->fence),
             "vkCreateFence(submit)");

    if (app->gpu_timestamp_capable) {
      VkQueryPoolCreateInfo query_info = {
        .sType = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO,
        .queryType = VK_QUERY_TYPE_TIMESTAMP,
        .queryCount = H12_GPU_QUERY_COUNT,
      };
      check_vk(vkCreateQueryPool(app->device, &query_info, NULL,
                                  &resource->query_pool),
               "vkCreateQueryPool(timestamp)");
    }
  }
}

static uint64_t timestamp_mask(uint32_t valid_bits)
{
  if (valid_bits == 0) {
    return 0;
  }
  if (valid_bits >= 64u) {
    return UINT64_MAX;
  }
  return (UINT64_C(1) << valid_bits) - UINT64_C(1);
}

/* Validate the immutable H12-4 evidence context before allowing a candidate.
 * The numeric VkDevice handle is deliberately not part of this contract. */
static const char *calibration_same_run_status(const App *app)
{
  if (!app->device_calibrated_timestamps ||
      !app->calibrated_function_available ||
      app->pfn_calibrateable_time_domains == NULL) {
    return H12_STATUS_NOT_AVAILABLE;
  }
  if (!app->calibrated_domain_query_valid) {
    return H12_STATUS_UNKNOWN;
  }
  if (!app->calibrated_device_domain_supported ||
      !app->calibrated_monotonic_domain_supported) {
    return H12_STATUS_NOT_AVAILABLE;
  }
  if (app->calibrated_domains_truncated ||
      app->calibrated_timestamps_capability == NULL ||
      strcmp(app->calibrated_timestamps_capability, H12_STATUS_PRESENT) != 0 ||
      !app->run_id_valid || !app->id_properties_valid ||
      !app->driver_properties_valid || !app->pci_info_valid ||
      app->queue_family == H12_MAX_UINT32 || !app->logical_device_created ||
      app->physical_device == VK_NULL_HANDLE ||
      app->physical_properties.vendorID != H12_TARGET_VENDOR_ID ||
      app->physical_properties.deviceID != H12_TARGET_DEVICE_ID ||
      app->timestamp_period_ns <= 0.0f || app->timestamp_valid_bits == 0u ||
      app->timestamp_valid_bits > 64u ||
      app->calibrated_timestamp_variant == NULL) {
    return H12_STATUS_UNKNOWN;
  }
  return H12_STATUS_PRESENT;
}

static void write_calibration_sample(App *app,
                                      const CalibrationSample *sample)
{
  fprintf(app->log,
          "{\"schema\":\"" H12_PROBE_CALIBRATION_SCHEMA
          "\",\"event\":\"calibration_sample\""
          ",\"run_id\":");
  json_string(app->log, app->run_id_valid ? app->run_id : "UNKNOWN");
  fprintf(app->log, ",\"sample_id\":%" PRIu32, sample->sample_id);
  fputs(",\"phase\":", app->log);
  json_string(app->log, sample->phase);
  fprintf(app->log, ",\"frame_id\":%" PRIu64, sample->frame_id);
  fputs(",\"device_time_domain\":", app->log);
  json_string(app->log, time_domain_name(VK_TIME_DOMAIN_DEVICE_KHR));
  fprintf(app->log, ",\"device_time_domain_id\":%" PRIu32,
          (uint32_t)VK_TIME_DOMAIN_DEVICE_KHR);
  fputs(",\"host_time_domain\":", app->log);
  json_string(app->log, time_domain_name(VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR));
  fprintf(app->log, ",\"host_time_domain_id\":%" PRIu32,
          (uint32_t)VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR);
  fputs(",\"device_timestamp_ticks\":", app->log);
  json_u64_or_null(app->log, sample->raw_valid,
                   sample->device_timestamp_ticks);
  fputs(",\"host_timestamp_ns\":", app->log);
  json_u64_or_null(app->log, sample->raw_valid, sample->host_timestamp_ns);
  fputs(",\"max_deviation_ns\":", app->log);
  json_u64_or_null(app->log, sample->raw_valid, sample->max_deviation_ns);
  fprintf(app->log, ",\"timestamp_period_ns\":%.9g",
          (double)sample->timestamp_period_ns);
  fprintf(app->log, ",\"timestamp_valid_bits\":%" PRIu32,
          sample->timestamp_valid_bits);
  fputs(",\"calibrated_timestamp_variant\":", app->log);
  json_string(app->log,
              app->calibrated_timestamp_variant != NULL
                  ? app->calibrated_timestamp_variant
                  : "NONE");
  fprintf(app->log, ",\"calibrated_function_available\":%s",
          app->calibrated_function_available ? "true" : "false");
  fprintf(app->log, ",\"queue_family_index\":%" PRIu32, app->queue_family);
  fputs(",\"device_uuid\":", app->log);
  json_uuid(app->log, app->id_properties_valid, app->id_properties.deviceUUID);
  fputs(",\"driver_uuid\":", app->log);
  json_uuid(app->log, app->id_properties_valid, app->id_properties.driverUUID);
  fprintf(app->log, ",\"vendor_id\":\"0x%04x\",\"device_id\":\"0x%04x\"",
          app->physical_properties.vendorID, app->physical_properties.deviceID);
  fputs(",\"selected_pci\":", app->log);
  json_selected_pci(app->log, app);
  fputs(",\"driver_name\":", app->log);
  json_string(app->log, app->driver_properties_valid ? app->driver_name
                                                       : "UNKNOWN");
  fputs(",\"driver_info\":", app->log);
  json_string(app->log, app->driver_properties_valid ? app->driver_info
                                                       : "UNKNOWN");
  fprintf(app->log, ",\"driver_version\":%" PRIu32,
          app->physical_properties.driverVersion);
  fputs(",\"vk_result\":", app->log);
  if (sample->attempted) {
    json_string(app->log, vk_result_name(sample->result));
  } else {
    fputs("null", app->log);
  }
  fputs(",\"calibration_status\":", app->log);
  json_string(app->log, sample->status);
  fputs(",\"same_run_validation_status\":", app->log);
  json_string(app->log, sample->same_run_status);
  fputs(",\"logical_device_scope\":\"single_vk_device_per_run\"", app->log);
  fputs(",\"logical_device_created\":true", app->log);
  fputs(",\"reason\":", app->log);
  json_string(app->log, sample->reason != NULL ? sample->reason : "");
  fputs("}\n", app->log);
}

static void capture_calibration_sample(App *app, FrameRecord *record,
                                       const char *phase,
                                       CalibrationSample *sample)
{
  memset(sample, 0, sizeof(*sample));
  sample->sample_id = app->calibration_sample_count;
  sample->phase = phase;
  sample->frame_id = record->frame_id;
  sample->timestamp_valid_bits = app->timestamp_valid_bits;
  sample->timestamp_period_ns = app->timestamp_period_ns;
  sample->status = H12_STATUS_UNKNOWN;
  sample->same_run_status = calibration_same_run_status(app);
  sample->reason = "calibration was not available";

  ++app->calibration_sample_count;
  if (sample->same_run_status != NULL &&
      strcmp(sample->same_run_status, H12_STATUS_NOT_AVAILABLE) == 0) {
    sample->status = H12_STATUS_NOT_AVAILABLE;
    sample->reason = "calibrated timestamps extension, function, or required domain unavailable";
    ++app->calibration_not_available_count;
    write_calibration_sample(app, sample);
    return;
  }
  if (app->pfn_get_calibrated_timestamps == NULL ||
      !app->calibrated_device_domain_supported ||
      !app->calibrated_monotonic_domain_supported) {
    sample->status =
        sample->same_run_status != NULL &&
                strcmp(sample->same_run_status, H12_STATUS_NOT_AVAILABLE) == 0
            ? H12_STATUS_NOT_AVAILABLE
            : H12_STATUS_UNKNOWN;
    sample->reason = "calibrated timestamps capability could not be validated";
    if (strcmp(sample->status, H12_STATUS_NOT_AVAILABLE) == 0) {
      ++app->calibration_not_available_count;
    } else {
      ++app->calibration_unknown_count;
    }
    write_calibration_sample(app, sample);
    return;
  }
  if (app->calibrated_domains_truncated) {
    sample->status = H12_STATUS_UNKNOWN;
    sample->reason = "calibrated timestamp domain list was truncated";
    ++app->calibration_unknown_count;
    write_calibration_sample(app, sample);
    return;
  }
  if (app->timestamp_period_ns <= 0.0f || app->timestamp_valid_bits == 0u) {
    sample->status = H12_STATUS_UNKNOWN;
    sample->reason = "device timestamp period or valid bits are unusable";
    ++app->calibration_unknown_count;
    write_calibration_sample(app, sample);
    return;
  }

  /* H12-4 deliberately requests only these two domains.  Other domains
   * returned by the capability query are audit data, never mapping inputs. */
  VkCalibratedTimestampInfoKHR infos[2] = {
    {
      .sType = VK_STRUCTURE_TYPE_CALIBRATED_TIMESTAMP_INFO_KHR,
      .timeDomain = VK_TIME_DOMAIN_DEVICE_KHR,
    },
    {
      .sType = VK_STRUCTURE_TYPE_CALIBRATED_TIMESTAMP_INFO_KHR,
      .timeDomain = VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR,
    },
  };
  uint64_t timestamps[2] = {0, 0};
  uint64_t max_deviation_ns = 0;
  sample->attempted = true;
  sample->result = app->pfn_get_calibrated_timestamps(
      app->device, 2, infos, timestamps, &max_deviation_ns);
  sample->device_timestamp_ticks = timestamps[0];
  sample->host_timestamp_ns = timestamps[1];
  sample->max_deviation_ns = max_deviation_ns;
  sample->raw_valid = sample->result == VK_SUCCESS;
  if (sample->raw_valid &&
      (!app->calibration_max_deviation_valid ||
       max_deviation_ns > app->calibration_max_deviation_ns)) {
    app->calibration_max_deviation_ns = max_deviation_ns;
    app->calibration_max_deviation_valid = true;
  }
  if (sample->result != VK_SUCCESS) {
    sample->status = H12_STATUS_UNKNOWN;
    sample->reason = "vkGetCalibratedTimestamps returned a non-success result";
    ++app->calibration_unknown_count;
  } else if (max_deviation_ns == 0u) {
    sample->status = H12_STATUS_UNKNOWN;
    sample->reason = "maxDeviation was zero";
    ++app->calibration_unknown_count;
  } else {
    sample->status = H12_STATUS_PRESENT;
    sample->reason = NULL;
    ++app->calibration_present_count;
  }
  write_calibration_sample(app, sample);
}

static uint64_t normalized_timestamp(uint64_t value, uint32_t valid_bits)
{
  /* Mask only for comparison.  H12-4 never unwraps a decreasing counter. */
  return timestamp_mask(valid_bits) & value;
}

static bool signed_timestamp_difference(uint64_t value, uint64_t base,
                                        int64_t *delta)
{
  if (value >= base) {
    uint64_t difference = value - base;
    if (difference > (uint64_t)INT64_MAX) {
      return false;
    }
    *delta = (int64_t)difference;
    return true;
  }
  uint64_t difference = base - value;
  if (difference > (uint64_t)INT64_MAX) {
    return false;
  }
  *delta = -(int64_t)difference;
  return true;
}

static bool scale_signed_tick_delta(int64_t ticks, float period_ns,
                                    int64_t *nanoseconds)
{
  if (!(period_ns > 0.0f)) {
    return false;
  }
  if (ticks == 0) {
    *nanoseconds = 0;
    return true;
  }
  long double product = (long double)ticks * (long double)period_ns;
  if (product != product || product > (long double)INT64_MAX ||
      product < (long double)INT64_MIN) {
    return false;
  }
  int64_t converted = (int64_t)product;
  if ((long double)converted != product) {
    return false;
  }
  *nanoseconds = converted;
  return true;
}

static bool add_signed_nanoseconds(uint64_t base, int64_t delta,
                                   uint64_t *result)
{
  if (delta >= 0) {
    uint64_t magnitude = (uint64_t)delta;
    if (base > UINT64_MAX - magnitude) {
      return false;
    }
    *result = base + magnitude;
    return true;
  }
  uint64_t magnitude = (uint64_t)(-(delta + 1)) + 1u;
  if (base < magnitude) {
    return false;
  }
  *result = base - magnitude;
  return true;
}

static bool subtract_unsigned_to_i64(uint64_t left, uint64_t right,
                                     int64_t *result)
{
  if (left >= right) {
    uint64_t difference = left - right;
    if (difference > (uint64_t)INT64_MAX) {
      return false;
    }
    *result = (int64_t)difference;
    return true;
  }
  uint64_t difference = right - left;
  if (difference > (uint64_t)INT64_MAX) {
    return false;
  }
  *result = -(int64_t)difference;
  return true;
}

static bool candidate_from_sample(const App *app, uint64_t gpu_ticks,
                                   const CalibrationSample *sample,
                                   uint64_t *candidate_ns)
{
  uint64_t normalized_gpu = normalized_timestamp(
      gpu_ticks, app->timestamp_valid_bits);
  uint64_t normalized_sample = normalized_timestamp(
      sample->device_timestamp_ticks, app->timestamp_valid_bits);
  int64_t tick_delta = 0;
  int64_t nanosecond_delta = 0;
  return signed_timestamp_difference(normalized_gpu, normalized_sample,
                                    &tick_delta) &&
         scale_signed_tick_delta(tick_delta, app->timestamp_period_ns,
                                &nanosecond_delta) &&
         add_signed_nanoseconds(sample->host_timestamp_ns,
                                nanosecond_delta, candidate_ns);
}

static bool map_bracketed_timestamp(
    const App *app, uint64_t gpu_ticks, const CalibrationSample *before,
    const CalibrationSample *after, uint64_t *candidate_ns,
    uint64_t *spread_ns, uint32_t *source_sample_id)
{
  uint64_t normalized_gpu = normalized_timestamp(
      gpu_ticks, app->timestamp_valid_bits);
  uint64_t normalized_before = normalized_timestamp(
      before->device_timestamp_ticks, app->timestamp_valid_bits);
  uint64_t normalized_after = normalized_timestamp(
      after->device_timestamp_ticks, app->timestamp_valid_bits);
  if (normalized_before > normalized_after || normalized_gpu < normalized_before ||
      normalized_gpu > normalized_after) {
    return false;
  }

  uint64_t before_candidate = 0;
  uint64_t after_candidate = 0;
  if (!candidate_from_sample(app, gpu_ticks, before, &before_candidate) ||
      !candidate_from_sample(app, gpu_ticks, after, &after_candidate) ||
      after_candidate < before_candidate) {
    return false;
  }
  uint64_t spread = after_candidate - before_candidate;
  uint64_t distance_before = normalized_gpu - normalized_before;
  uint64_t distance_after = normalized_after - normalized_gpu;
  *candidate_ns = distance_before <= distance_after ? before_candidate
                                                     : after_candidate;
  *spread_ns = spread;
  *source_sample_id = distance_before <= distance_after ? before->sample_id
                                                        : after->sample_id;
  return true;
}

static void prepare_calibration_drift(App *app, FrameRecord *record)
{
  record->calibration_drift_status = H12_STATUS_UNKNOWN;
  record->calibration_drift_valid = false;
  record->calibration_device_delta_ticks = 0;
  record->calibration_device_delta_ns = 0;
  record->calibration_host_delta_ns = 0;
  record->calibration_residual_ns = 0;
  if (record->calibration_same_run_status == NULL ||
      strcmp(record->calibration_same_run_status, H12_STATUS_PRESENT) != 0) {
    record->calibration_drift_status =
        record->calibration_same_run_status != NULL &&
                strcmp(record->calibration_same_run_status,
                       H12_STATUS_NOT_AVAILABLE) == 0
            ? H12_STATUS_NOT_AVAILABLE
            : H12_STATUS_UNKNOWN;
    return;
  }

  const CalibrationSample *before = &record->calibration_before;
  const CalibrationSample *after = &record->calibration_after;
  if (!record->calibration_before_valid || !record->calibration_after_valid ||
      before->status == NULL || after->status == NULL) {
    return;
  }
  if (strcmp(before->status, H12_STATUS_NOT_AVAILABLE) == 0 ||
      strcmp(after->status, H12_STATUS_NOT_AVAILABLE) == 0) {
    record->calibration_drift_status = H12_STATUS_NOT_AVAILABLE;
    return;
  }
  if (strcmp(before->status, H12_STATUS_PRESENT) != 0 ||
      strcmp(after->status, H12_STATUS_PRESENT) != 0 ||
      strcmp(before->same_run_status, H12_STATUS_PRESENT) != 0 ||
      strcmp(after->same_run_status, H12_STATUS_PRESENT) != 0 ||
      !before->raw_valid || !after->raw_valid ||
      before->timestamp_period_ns != app->timestamp_period_ns ||
      after->timestamp_period_ns != app->timestamp_period_ns ||
      before->timestamp_valid_bits != app->timestamp_valid_bits ||
      after->timestamp_valid_bits != app->timestamp_valid_bits) {
    return;
  }

  uint64_t before_ticks = normalized_timestamp(
      before->device_timestamp_ticks, app->timestamp_valid_bits);
  uint64_t after_ticks = normalized_timestamp(
      after->device_timestamp_ticks, app->timestamp_valid_bits);
  if (before_ticks > after_ticks || after->host_timestamp_ns < before->host_timestamp_ns) {
    return;
  }
  uint64_t device_delta_ticks = after_ticks - before_ticks;
  uint64_t host_delta_ns = after->host_timestamp_ns - before->host_timestamp_ns;
  if (device_delta_ticks > (uint64_t)INT64_MAX) {
    return;
  }
  int64_t device_delta_ns = 0;
  int64_t residual_ns = 0;
  if (!scale_signed_tick_delta((int64_t)device_delta_ticks,
                               app->timestamp_period_ns, &device_delta_ns) ||
      !subtract_unsigned_to_i64((uint64_t)device_delta_ns, host_delta_ns,
                                &residual_ns)) {
    return;
  }
  record->calibration_device_delta_ticks = device_delta_ticks;
  record->calibration_device_delta_ns = (uint64_t)device_delta_ns;
  record->calibration_host_delta_ns = host_delta_ns;
  record->calibration_residual_ns = residual_ns;
  record->calibration_drift_valid = true;
  record->calibration_drift_status = H12_STATUS_PRESENT;
}

static void prepare_calibration_mapping(App *app, FrameRecord *record)
{
  if (record->calibration_mapping_prepared) {
    return;
  }
  record->calibration_mapping_prepared = true;
  record->calibration_same_run_status = calibration_same_run_status(app);
  record->gpu_clock_correlation_status = H12_STATUS_UNKNOWN;
  record->gpu_timestamp_begin_cpu_candidate_valid = false;
  record->gpu_timestamp_end_cpu_candidate_valid = false;
  record->gpu_timestamp_begin_cpu_candidate_ns = 0;
  record->gpu_timestamp_end_cpu_candidate_ns = 0;
  record->gpu_clock_mapping_method = NULL;
  record->gpu_clock_mapping_source_sample_valid = false;
  record->gpu_clock_mapping_source_sample_id = 0;
  record->gpu_clock_mapping_spread_valid = false;
  record->gpu_clock_mapping_spread_ns = 0;
  record->gpu_clock_mapping_max_deviation_valid = false;
  record->gpu_clock_mapping_max_deviation_ns = 0;

  prepare_calibration_drift(app, record);
  const CalibrationSample *before = &record->calibration_before;
  const CalibrationSample *after = &record->calibration_after;
  bool raw_samples_present = record->calibration_before_valid &&
                             record->calibration_after_valid &&
                             before->status != NULL && after->status != NULL &&
                             strcmp(before->status, H12_STATUS_PRESENT) == 0 &&
                             strcmp(after->status, H12_STATUS_PRESENT) == 0 &&
                             before->raw_valid && after->raw_valid;
  if (raw_samples_present) {
    record->gpu_clock_mapping_max_deviation_valid = true;
    record->gpu_clock_mapping_max_deviation_ns =
        before->max_deviation_ns > after->max_deviation_ns
            ? before->max_deviation_ns
            : after->max_deviation_ns;
  }
  if (strcmp(record->calibration_same_run_status, H12_STATUS_PRESENT) != 0 ||
      !record->calibration_before_valid || !record->calibration_after_valid ||
      strcmp(before->same_run_status, H12_STATUS_PRESENT) != 0 ||
      strcmp(after->same_run_status, H12_STATUS_PRESENT) != 0) {
    record->gpu_clock_correlation_status =
        strcmp(record->calibration_same_run_status, H12_STATUS_NOT_AVAILABLE) == 0
            ? H12_STATUS_NOT_AVAILABLE
            : H12_STATUS_UNKNOWN;
    if (strcmp(record->gpu_clock_correlation_status,
               H12_STATUS_NOT_AVAILABLE) == 0) {
      ++app->calibration_mapping_not_available_count;
    } else {
      ++app->calibration_mapping_unknown_count;
    }
    return;
  }
  if (strcmp(before->status, H12_STATUS_NOT_AVAILABLE) == 0 ||
      strcmp(after->status, H12_STATUS_NOT_AVAILABLE) == 0) {
    record->gpu_clock_correlation_status = H12_STATUS_NOT_AVAILABLE;
    ++app->calibration_mapping_not_available_count;
    return;
  }
  if (strcmp(before->status, H12_STATUS_PRESENT) != 0 ||
      strcmp(after->status, H12_STATUS_PRESENT) != 0 ||
      strcmp(before->same_run_status, H12_STATUS_PRESENT) != 0 ||
      strcmp(after->same_run_status, H12_STATUS_PRESENT) != 0 ||
      !before->raw_valid || !after->raw_valid ||
      before->timestamp_period_ns != app->timestamp_period_ns ||
      after->timestamp_period_ns != app->timestamp_period_ns ||
      before->timestamp_valid_bits != app->timestamp_valid_bits ||
      after->timestamp_valid_bits != app->timestamp_valid_bits) {
    ++app->calibration_mapping_unknown_count;
    return;
  }
  if (!record->gpu_results_available) {
    ++app->calibration_mapping_unknown_count;
    return;
  }
  uint64_t normalized_begin = normalized_timestamp(
      record->gpu_begin_ticks, app->timestamp_valid_bits);
  uint64_t normalized_end = normalized_timestamp(
      record->gpu_end_ticks, app->timestamp_valid_bits);
  if (normalized_begin > normalized_end) {
    ++app->calibration_mapping_unknown_count;
    return;
  }
  if (before->host_timestamp_ns > after->host_timestamp_ns) {
    ++app->calibration_mapping_unknown_count;
    return;
  }

  uint64_t begin_candidate = 0;
  uint64_t end_candidate = 0;
  uint64_t begin_spread = 0;
  uint64_t end_spread = 0;
  uint32_t begin_source = 0;
  uint32_t end_source = 0;
  if (!map_bracketed_timestamp(app, record->gpu_begin_ticks, before, after,
                               &begin_candidate, &begin_spread, &begin_source) ||
      !map_bracketed_timestamp(app, record->gpu_end_ticks, before, after,
                               &end_candidate, &end_spread, &end_source) ||
      begin_candidate > end_candidate) {
    ++app->calibration_mapping_unknown_count;
    return;
  }

  record->gpu_timestamp_begin_cpu_candidate_valid = true;
  record->gpu_timestamp_begin_cpu_candidate_ns = begin_candidate;
  record->gpu_timestamp_end_cpu_candidate_valid = true;
  record->gpu_timestamp_end_cpu_candidate_ns = end_candidate;
  record->gpu_clock_mapping_method = "NEAREST_BRACKETED";
  record->gpu_clock_mapping_source_sample_valid = begin_source == end_source;
  record->gpu_clock_mapping_source_sample_id =
      record->gpu_clock_mapping_source_sample_valid ? begin_source : 0;
  record->gpu_clock_mapping_spread_valid = true;
  record->gpu_clock_mapping_spread_ns =
      begin_spread > end_spread ? begin_spread : end_spread;
  record->gpu_clock_correlation_status = H12_STATUS_PRESENT;
  ++app->calibration_mapping_present_count;
}

static void read_gpu_timestamps(App *app, FrameResource *resource)
{
  FrameRecord *record = resource->active_record;
  if (record == NULL || record->gpu_results_read) {
    return;
  }
  record->gpu_results_read = true;
  if (!record->gpu_query_requested) {
    record->gpu_query_result = VK_ERROR_FEATURE_NOT_PRESENT;
    return;
  }

  uint64_t values[H12_GPU_QUERY_COUNT] = {0, 0};
  record->gpu_query_result = vkGetQueryPoolResults(
      app->device, resource->query_pool, 0, H12_GPU_QUERY_COUNT,
      sizeof(values), values, sizeof(uint64_t),
      VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);
  if (record->gpu_query_result != VK_SUCCESS) {
    return;
  }

  uint64_t mask = timestamp_mask(app->timestamp_valid_bits);
  record->gpu_begin_ticks = values[0] & mask;
  record->gpu_end_ticks = values[1] & mask;
  record->gpu_elapsed_ticks_modulo =
      (record->gpu_end_ticks - record->gpu_begin_ticks) & mask;
  long double elapsed_ns =
      (long double)record->gpu_elapsed_ticks_modulo *
      (long double)app->timestamp_period_ns;
  if (elapsed_ns >= 0.0L &&
      elapsed_ns <= (long double)UINT64_MAX) {
    record->gpu_elapsed_ns_from_period_modulo = (uint64_t)elapsed_ns;
    record->gpu_elapsed_conversion_available = true;
  }
  record->gpu_results_available = true;
}

static void complete_resource(App *app, FrameResource *resource,
                              const char *observation_source)
{
  if (!resource->in_flight) {
    return;
  }
  FrameRecord *record = resource->active_record;
  if (record != NULL && !record->gpu_fence_observed_cpu_valid) {
    record->gpu_fence_observed_cpu_valid =
        monotonic_ns(&record->gpu_fence_observed_cpu_ns);
    if (record->gpu_fence_observed_cpu_valid) {
      record->gpu_fence_observation_source = observation_source;
    }
  }
  read_gpu_timestamps(app, resource);
  if (record != NULL) {
    capture_calibration_sample(app, record, "after_frame",
                               &record->calibration_after);
    record->calibration_after_valid = true;
  }
  if (resource->active_record != NULL) {
    resource->active_record->gpu_done = true;
  }
  resource->gpu_done = true;
  resource->in_flight = false;
}

static void poll_gpu_resources(App *app)
{
  for (uint32_t i = 0; i < app->resource_count; ++i) {
    FrameResource *resource = &app->resources[i];
    if (!resource->in_flight) {
      continue;
    }
    VkResult status = vkGetFenceStatus(app->device, resource->fence);
    if (status == VK_ERROR_DEVICE_LOST) {
      fatal("vkGetFenceStatus reported VK_ERROR_DEVICE_LOST");
    }
    if (status != VK_NOT_READY && status != VK_SUCCESS) {
      fatal("vkGetFenceStatus failed: %s", vk_result_name(status));
    }
    if (status == VK_SUCCESS) {
      complete_resource(app, resource, "vkGetFenceStatus");
    }
  }
}

static bool wait_for_resource_until(App *app, FrameResource *resource,
                                    uint64_t timeout_ns)
{
  if (!resource->in_flight) {
    return true;
  }

  uint64_t start_ns = 0;
  if (!monotonic_ns(&start_ns)) {
    fatal("CLOCK_MONOTONIC failed while waiting for a fence");
  }
  for (;;) {
    uint64_t now_ns = 0;
    if (!monotonic_ns(&now_ns)) {
      fatal("CLOCK_MONOTONIC failed while waiting for a fence");
    }
    if (now_ns - start_ns >= timeout_ns) {
      return false;
    }
    uint64_t remaining_ns = timeout_ns - (now_ns - start_ns);
    uint64_t slice_ns = remaining_ns < H12_FENCE_WAIT_SLICE_NS
                            ? remaining_ns
                            : H12_FENCE_WAIT_SLICE_NS;
    VkResult result = vkWaitForFences(app->device, 1, &resource->fence,
                                      VK_TRUE, slice_ns);
    if (result == VK_SUCCESS) {
      complete_resource(app, resource, "vkWaitForFences");
      return true;
    }
    if (result == VK_TIMEOUT) {
      poll_gpu_resources(app);
      wayland_service(app, 1);
      abort_if_surface_reconfigured(app);
      continue;
    }
    if (result == VK_ERROR_DEVICE_LOST) {
      fatal("vkWaitForFences reported VK_ERROR_DEVICE_LOST");
    }
    fatal("vkWaitForFences failed: %s", vk_result_name(result));
  }
}

static void wait_for_resource(App *app, FrameResource *resource)
{
  if (!wait_for_resource_until(app, resource, H12_FENCE_WAIT_TIMEOUT_NS)) {
    structured_abort(app, "GPU_FENCE_TIMEOUT", H12_STATUS_CONFLICT,
                     "GPU fence did not signal within the bounded safety timeout");
    fatal("GPU fence did not signal within the bounded safety timeout");
  }
}

static FrameResource *find_free_resource(App *app)
{
  for (uint32_t i = 0; i < app->resource_count; ++i) {
    if (!app->resources[i].in_flight) {
      return &app->resources[i];
    }
  }

  poll_gpu_resources(app);
  for (uint32_t i = 0; i < app->resource_count; ++i) {
    if (!app->resources[i].in_flight) {
      return &app->resources[i];
    }
  }

  wait_for_resource(app, &app->resources[0]);
  return &app->resources[0];
}

static void acquire_next_image_with_service(App *app,
                                             FrameResource *resource,
                                             FrameRecord *record)
{
  uint64_t start_ns = 0;
  if (!monotonic_ns(&start_ns)) {
    fatal("CLOCK_MONOTONIC failed before vkAcquireNextImageKHR");
  }

  for (;;) {
    if (app->close_requested) {
      fatal("compositor requested close while waiting for a swapchain image");
    }
    uint64_t now_ns = 0;
    if (!monotonic_ns(&now_ns)) {
      fatal("CLOCK_MONOTONIC failed while waiting for a swapchain image");
    }
    if (now_ns - start_ns >= H12_ACQUIRE_TIMEOUT_NS) {
      structured_abort(app, "ACQUIRE_TIMEOUT", H12_STATUS_CONFLICT,
                       "vkAcquireNextImageKHR timed out after the bounded acquire window");
      fatal("vkAcquireNextImageKHR timed out after the bounded acquire window");
    }

    uint64_t remaining_ns = H12_ACQUIRE_TIMEOUT_NS - (now_ns - start_ns);
    uint64_t wait_ns = remaining_ns < H12_ACQUIRE_WAIT_SLICE_NS
                            ? remaining_ns
                            : H12_ACQUIRE_WAIT_SLICE_NS;
    record->acquire_result = vkAcquireNextImageKHR(
        app->device, app->swapchain, wait_ns, resource->acquire_semaphore,
        VK_NULL_HANDLE, &record->image_index);
    if (record->acquire_result == VK_SUCCESS ||
        record->acquire_result == VK_SUBOPTIMAL_KHR) {
      if (record->acquire_result == VK_SUBOPTIMAL_KHR) {
        app->swapchain_suboptimal_observed = true;
      }
      return;
    }
    if (record->acquire_result == VK_TIMEOUT ||
        record->acquire_result == VK_NOT_READY) {
      wayland_service(app, 1);
      abort_if_surface_reconfigured(app);
      continue;
    }
    fatal("vkAcquireNextImageKHR failed: %s",
          vk_result_name(record->acquire_result));
  }
}

/* ------------------------------------------------------------------------- */
/* Present timing polling                                                    */
/* ------------------------------------------------------------------------- */

static FrameRecord *find_record_by_present_id(App *app, uint64_t present_id)
{
  for (uint32_t i = 0; i < app->submitted_frames; ++i) {
    FrameRecord *record = &app->records[i];
    if (record->present_id_assigned == present_id) {
      return record;
    }
  }
  return NULL;
}

static void copy_present_timing_result(App *app, FrameRecord *record,
                                       const VkPastPresentationTimingEXT *source)
{
  record->timing.result_available = true;
  record->timing.report_complete = source->reportComplete == VK_TRUE;
  record->timing.present_id = source->presentId;
  record->timing.target_time = source->targetTime;
  record->timing.stage_count = source->presentStageCount;
  record->timing.stage_mask = 0;
  record->timing.queue_operations_end_time = 0;
  record->timing.queue_operations_end_time_available = false;
  uint32_t stage_count = source->presentStageCount;
  if (stage_count > H12_PRESENT_TIMING_STAGE_CAPACITY) {
    stage_count = H12_PRESENT_TIMING_STAGE_CAPACITY;
  }
  record->timing.stage_count = stage_count;
  for (uint32_t i = 0; source->pPresentStages != NULL && i < stage_count; ++i) {
    VkPresentStageTimeEXT stage = source->pPresentStages[i];
    record->timing.stage_mask |= stage.stage;
    if ((stage.stage & VK_PRESENT_STAGE_QUEUE_OPERATIONS_END_BIT_EXT) != 0 &&
        stage.time != 0) {
      record->timing.queue_operations_end_time = stage.time;
      record->timing.queue_operations_end_time_available = true;
    }
  }
  bool selected_domain =
      source->timeDomainId != 0 &&
      source->timeDomainId == app->present_timing_time_domain_id &&
      source->timeDomain == app->present_timing_time_domain_kind;
  record->timing.complete =
      record->timing.report_complete &&
      record->timing.queue_operations_end_time_available && selected_domain;
  record->timing.time_domain = source->timeDomain;
  record->timing.time_domain_id = source->timeDomainId;
}

static bool refresh_present_timing_domain(App *app)
{
  if (app->pfn_get_swapchain_time_domains == NULL ||
      !app->present_timing_time_domain_valid) {
    return false;
  }

  VkSwapchainTimeDomainPropertiesEXT count_query = {
    .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_TIME_DOMAIN_PROPERTIES_EXT,
  };
  uint64_t counter = 0;
  VkResult result = app->pfn_get_swapchain_time_domains(
      app->device, app->swapchain, &count_query, &counter);
  if (result != VK_SUCCESS || count_query.timeDomainCount == 0 ||
      count_query.timeDomainCount > H12_MAX_PRESENT_TIMING_DOMAINS) {
    return false;
  }

  uint32_t capacity = count_query.timeDomainCount;
  for (uint32_t attempt = 0; attempt < H12_PRESENT_TIMING_DOMAIN_RETRIES;
       ++attempt) {
    VkTimeDomainKHR *domain_values = calloc(capacity, sizeof(*domain_values));
    uint64_t *domain_ids = calloc(capacity, sizeof(*domain_ids));
    if (domain_values == NULL || domain_ids == NULL) {
      free(domain_values);
      free(domain_ids);
      fatal("Out of memory refreshing present timing domains");
    }

    VkSwapchainTimeDomainPropertiesEXT domains = {
      .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_TIME_DOMAIN_PROPERTIES_EXT,
      .timeDomainCount = capacity,
      .pTimeDomains = domain_values,
      .pTimeDomainIds = domain_ids,
    };
    result = app->pfn_get_swapchain_time_domains(app->device, app->swapchain,
                                                  &domains, &counter);
    if (result == VK_SUCCESS) {
      bool found = false;
      for (uint32_t i = 0; i < domains.timeDomainCount; ++i) {
        if (domain_ids[i] == app->present_timing_time_domain_id &&
            domain_values[i] == app->present_timing_time_domain_kind) {
          found = true;
          break;
        }
      }
      free(domain_values);
      free(domain_ids);
      if (!found) {
        return false;
      }
      app->present_timing_time_domains_counter = counter;
      return true;
    }

    free(domain_values);
    free(domain_ids);
    if (result != VK_INCOMPLETE || capacity >= H12_MAX_PRESENT_TIMING_DOMAINS) {
      return false;
    }
    capacity *= 2u;
  }
  return false;
}

static void report_present_timing_poll_error(App *app, VkResult result)
{
  ++app->present_timing_poll_error_count;
  app->present_timing_capability = H12_STATUS_CONFLICT;
  structured_abort(app, "PRESENT_TIMING_POLL_FAILED", H12_STATUS_CONFLICT,
                   vk_result_name(result));
  fatal("present timing poll failed: %s", vk_result_name(result));
}

static void poll_present_timing(App *app)
{
  if (!app->present_timing_enabled || app->pfn_get_past_presentation_timing == NULL ||
      app->present_timing_results == NULL) {
    return;
  }

  VkPastPresentationTimingInfoEXT info = {
    .sType = VK_STRUCTURE_TYPE_PAST_PRESENTATION_TIMING_INFO_EXT,
    .flags = VK_PAST_PRESENTATION_TIMING_ALLOW_PARTIAL_RESULTS_BIT_EXT,
    .swapchain = app->swapchain,
  };
  VkPastPresentationTimingPropertiesEXT properties = {
    .sType = VK_STRUCTURE_TYPE_PAST_PRESENTATION_TIMING_PROPERTIES_EXT,
    .presentationTimingCount = app->present_timing_queue_size,
    .pPresentationTimings = app->present_timing_results,
  };
  for (uint32_t i = 0; i < app->present_timing_queue_size; ++i) {
    /* VUID-... requires the input capacity to cover every requested stage.
     * H12-1 requests exactly one stage. */
    app->present_timing_results[i].presentStageCount =
        H12_PRESENT_TIMING_STAGE_CAPACITY;
  }

  VkResult result = app->pfn_get_past_presentation_timing(
      app->device, &info, &properties);
  app->last_present_timing_poll_result = result;
  if (result != VK_SUCCESS && result != VK_INCOMPLETE) {
    report_present_timing_poll_error(app, result);
    return;
  }
  if (properties.timeDomainsCounter !=
          app->present_timing_time_domains_counter &&
      !refresh_present_timing_domain(app)) {
    app->present_timing_capability = H12_STATUS_CONFLICT;
    structured_abort(app, "PRESENT_TIMING_DOMAIN_CHANGED", H12_STATUS_CONFLICT,
                     "VK_EXT_present_timing selected time domain became unavailable");
    fatal("VK_EXT_present_timing selected time domain became unavailable");
  }
  uint32_t result_count = properties.presentationTimingCount;
  if (result_count > app->present_timing_queue_size) {
    result_count = app->present_timing_queue_size;
  }
  for (uint32_t i = 0; i < result_count; ++i) {
    VkPastPresentationTimingEXT *timing = &app->present_timing_results[i];
    if (timing->presentId == 0) {
      ++app->unmatched_present_timing_count;
      continue;
    }
    FrameRecord *record = find_record_by_present_id(app, timing->presentId);
    if (record == NULL) {
      ++app->unmatched_present_timing_count;
      continue;
    }
    if (timing->timeDomainId != 0 &&
        (timing->timeDomainId != app->present_timing_time_domain_id ||
         timing->timeDomain != app->present_timing_time_domain_kind)) {
      app->present_timing_capability = H12_STATUS_CONFLICT;
      structured_abort(app, "PRESENT_TIMING_DOMAIN_MISMATCH",
                       H12_STATUS_CONFLICT,
                       "present timing result did not use the selected time domain");
      fatal("present timing result did not use the selected time domain");
    }
    copy_present_timing_result(app, record, timing);
  }
}

/* ------------------------------------------------------------------------- */
/* Frame recording and logging                                               */
/* ------------------------------------------------------------------------- */

static void request_frame_callback(App *app, FrameRecord *record)
{
  if (app->pending_frame_callbacks >= H12_MAX_PENDING_FRAME_CALLBACKS) {
    structured_abort(app, "FRAME_CALLBACK_BACKLOG_LIMIT", H12_STATUS_CONFLICT,
                     "wl_surface.frame callback backlog reached the safety limit");
    fatal("wl_surface.frame callback backlog reached the safety limit");
  }
  FrameCallbackData *callback_data = calloc(1, sizeof(*callback_data));
  if (callback_data == NULL) {
    fatal("Out of memory allocating wl_surface.frame callback");
  }
  callback_data->app = app;
  callback_data->record = record;
  record->frame_callback_requested_cpu_valid =
      monotonic_ns(&record->frame_callback_requested_cpu_ns);
  struct wl_callback *callback = wl_surface_frame(app->wl_surface);
  if (callback == NULL) {
    free(callback_data);
    fatal("wl_surface_frame returned NULL");
  }
  wl_callback_add_listener(callback, &frame_callback_listener, callback_data);
  record->callback_requested = true;
  record->callback_proxy = callback;
  record->callback_data = callback_data;
  ++app->pending_frame_callbacks;
}

static void record_command_buffer(App *app, FrameResource *resource,
                                  FrameRecord *record)
{
  check_vk(vkResetCommandBuffer(resource->command_buffer, 0),
           "vkResetCommandBuffer");

  VkCommandBufferBeginInfo begin_info = {
    .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
    .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
  };
  record->cpu_before_recording_valid =
      monotonic_ns(&record->cpu_before_recording_ns);
  check_vk(vkBeginCommandBuffer(resource->command_buffer, &begin_info),
           "vkBeginCommandBuffer");
  if (record->gpu_query_requested) {
    vkCmdResetQueryPool(resource->command_buffer, resource->query_pool, 0,
                        H12_GPU_QUERY_COUNT);
  }

  if (record->gpu_query_requested) {
    vkCmdWriteTimestamp(resource->command_buffer,
                        VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                        resource->query_pool, 0);
  }

  VkClearValue clear_value = {
    .color = {{0.08f, 0.16f, 0.24f, 1.0f}},
  };
  VkRenderPassBeginInfo render_pass_begin = {
    .sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
    .renderPass = app->render_pass,
    .framebuffer = app->swapchain_framebuffers[record->image_index],
    .renderArea = (VkRect2D){
      .offset = {0, 0},
      .extent = {app->surface_width, app->surface_height},
    },
    .clearValueCount = 1,
    .pClearValues = &clear_value,
  };
  vkCmdBeginRenderPass(resource->command_buffer, &render_pass_begin,
                       VK_SUBPASS_CONTENTS_INLINE);
  vkCmdEndRenderPass(resource->command_buffer);

  if (record->gpu_query_requested) {
    vkCmdWriteTimestamp(resource->command_buffer,
                        VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
                        resource->query_pool, 1);
  }
  check_vk(vkEndCommandBuffer(resource->command_buffer),
           "vkEndCommandBuffer");
}

static bool per_image_result_is_error(const FrameRecord *record)
{
  return record->present_per_image_result != VK_SUCCESS &&
         record->present_per_image_result != VK_SUBOPTIMAL_KHR;
}

static VkResult present_after_submit(App *app, FrameRecord *record,
                                     VkSemaphore present_semaphore)
{
  VkPresentId2KHR present_id2 = {
    .sType = VK_STRUCTURE_TYPE_PRESENT_ID_2_KHR,
    .swapchainCount = 1,
    .pPresentIds = &record->present_id_assigned,
  };
  VkPresentTimingInfoEXT timing_info = {
    .sType = VK_STRUCTURE_TYPE_PRESENT_TIMING_INFO_EXT,
    .flags = 0,
    .targetTime = 0,
    .timeDomainId = app->present_timing_time_domain_id,
    .presentStageQueries = app->present_timing_stage_queries,
    .targetTimeDomainPresentStage = app->present_timing_time_domain_stage,
  };
  VkPresentTimingsInfoEXT timings_info = {
    .sType = VK_STRUCTURE_TYPE_PRESENT_TIMINGS_INFO_EXT,
    .swapchainCount = 1,
    .pTimingInfos = &timing_info,
  };
  VkSwapchainKHR swapchain = app->swapchain;
  uint32_t image_index = record->image_index;
  VkResult per_image_result = VK_SUCCESS;
  VkPresentInfoKHR present_info = {
    .sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
    .waitSemaphoreCount = 1,
    .pWaitSemaphores = &present_semaphore,
    .swapchainCount = 1,
    .pSwapchains = &swapchain,
    .pImageIndices = &image_index,
    .pResults = &per_image_result,
  };

  void *tail = NULL;
  if (app->present_id2_usable) {
    present_id2.pNext = tail;
    tail = &present_id2;
    record->present_id_requested = true;
  }
  if (record->timing_requested && app->present_timing_enabled) {
    timings_info.pNext = tail;
    tail = &timings_info;
  }
  present_info.pNext = tail;

  if (!record->present_call_valid) {
    record->present_call_valid = monotonic_ns(&record->present_call_ns);
    if (record->frame_id > 0 && app->last_present_call_valid &&
        record->present_call_valid &&
        record->present_call_ns >= app->last_present_call_ns) {
      record->frame_interval_ns =
          record->present_call_ns - app->last_present_call_ns;
      record->frame_interval_valid = true;
    }
    if (record->present_call_valid) {
      app->last_present_call_ns = record->present_call_ns;
      app->last_present_call_valid = true;
    }
  }

  app->presentation_started = true;
  app->present_call_in_progress = true;
  VkResult result = vkQueuePresentKHR(app->queue, &present_info);
  app->present_call_in_progress = false;
  if (result == VK_SUCCESS || result == VK_SUBOPTIMAL_KHR) {
    app->first_present_completed = true;
    if (record->frame_id + 1u > app->submitted_frames) {
      app->submitted_frames = record->frame_id + 1u;
    }
  }
  record->present_result = result;
  record->present_per_image_result = per_image_result;
  return result;
}

static void present_frame_with_optional_timing(App *app,
                                               FrameRecord *record,
                                               VkSemaphore present_semaphore)
{
  VkResult result = present_after_submit(app, record, present_semaphore);
  if (result == VK_ERROR_PRESENT_TIMING_QUEUE_FULL_EXT) {
    /* Vulkan still enqueues the present operation and consumes its wait
     * semaphore.  Retrying the same image/semaphore would be invalid. */
    app->present_timing_capability = H12_STATUS_CONFLICT;
    record->timing.conflict = true;
    char reason[160];
    (void)snprintf(reason, sizeof(reason),
                   "vkQueuePresentKHR returned queue-full for present_id=%" PRIu64
                   "; the consumed semaphore will not be retried",
                   record->present_id_assigned);
    structured_abort(app, "PRESENT_TIMING_QUEUE_FULL", H12_STATUS_CONFLICT,
                     reason);
    fatal("%s", reason);
  }
  if (result == VK_SUBOPTIMAL_KHR ||
      record->present_per_image_result == VK_SUBOPTIMAL_KHR) {
    app->swapchain_suboptimal_observed = true;
  }
  if (result != VK_SUCCESS && result != VK_SUBOPTIMAL_KHR) {
    fatal("vkQueuePresentKHR failed: %s", vk_result_name(result));
  }
  if (per_image_result_is_error(record)) {
    fatal("vkQueuePresentKHR per-image result: %s",
          vk_result_name(record->present_per_image_result));
  }
}

static void submit_and_present_frame(App *app, FrameResource *resource,
                                     FrameRecord *record)
{
  if (record->image_index >= app->swapchain_image_count ||
      app->present_semaphores == NULL) {
    fatal("Present semaphore array/image index is invalid");
  }
  /* One present semaphore per acquired image.  The submit waits on the
   * acquire semaphore before signalling this handle, so a later acquire of the
   * same image cannot race the prior present wait. */
  VkSemaphore present_semaphore =
      app->present_semaphores[record->image_index];

  /* Complete the pre-present Wayland barrier before requesting frame.  A
   * same-size configure may be acknowledged here.  After the first present,
   * only the exact activated/same-extent state-only case may continue; a
   * changed extent or unsupported synchronization remains a hard conflict. */
  wayland_flush(app);
  wayland_service(app, 0);
  abort_if_surface_reconfigured(app);
  capture_calibration_sample(app, record, "before_frame",
                             &record->calibration_before);
  record->calibration_before_valid = true;
  request_frame_callback(app, record);

  VkPipelineStageFlags wait_stage = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
  VkSubmitInfo submit_info = {
    .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
    .waitSemaphoreCount = 1,
    .pWaitSemaphores = &resource->acquire_semaphore,
    .pWaitDstStageMask = &wait_stage,
    .commandBufferCount = 1,
    .pCommandBuffers = &resource->command_buffer,
    .signalSemaphoreCount = 1,
    .pSignalSemaphores = &present_semaphore,
  };
  record->cpu_before_submit_valid = monotonic_ns(&record->cpu_before_submit_ns);
  record->submit_result = vkQueueSubmit(app->queue, 1, &submit_info,
                                         resource->fence);
  record->cpu_after_submit_valid = monotonic_ns(&record->cpu_after_submit_ns);
  if (record->submit_result != VK_SUCCESS) {
    fatal("vkQueueSubmit failed: %s", vk_result_name(record->submit_result));
  }
  resource->in_flight = true;
  resource->gpu_done = false;
  resource->active_record = record;

  /* The callback request is already queued; WSI now owns the present commit. */
  wayland_flush(app);
  present_frame_with_optional_timing(app, record, present_semaphore);
}

static void write_frame_record(App *app, FrameRecord *record, bool final)
{
  prepare_calibration_mapping(app, record);
  const char *gpu_status;
  if (record->gpu_results_available) {
    gpu_status = H12_STATUS_PRESENT;
  } else if (record->gpu_query_requested && record->gpu_results_read &&
             record->gpu_query_result != VK_SUCCESS &&
             record->gpu_query_result != VK_NOT_READY) {
    gpu_status = H12_STATUS_CONFLICT;
  } else if (record->gpu_query_requested &&
             (!final || record->gpu_query_result == VK_NOT_READY)) {
    gpu_status = H12_STATUS_UNKNOWN;
  } else {
    gpu_status = H12_STATUS_NOT_AVAILABLE;
  }
  const char *timing_status;
  if (record->timing.conflict) {
    timing_status = H12_STATUS_CONFLICT;
  } else if (!record->timing_requested) {
    timing_status = H12_STATUS_NOT_AVAILABLE;
  } else if (record->timing.complete) {
    timing_status = H12_STATUS_PRESENT;
  } else if (record->timing.result_available || !final) {
    timing_status = H12_STATUS_UNKNOWN;
  } else {
    timing_status = H12_STATUS_NOT_AVAILABLE;
  }
  const char *callback_status = record->callback_received
                                    ? H12_STATUS_PRESENT
                                    : (final ? H12_STATUS_NOT_AVAILABLE
                                             : H12_STATUS_UNKNOWN);

  fprintf(app->log, "{\"schema\":\"" H12_PROBE_SCHEMA
                    "\",\"event\":\"frame\",\"run_id\":");
  json_string(app->log, app->run_id_valid ? app->run_id : "UNKNOWN");
  fputs(",\"logical_device_scope\":\"single_vk_device_per_run\"", app->log);
  fputs(",\"logical_device_created\":true", app->log);
  fputs(",\"device_uuid\":", app->log);
  json_uuid(app->log, app->id_properties_valid, app->id_properties.deviceUUID);
  fputs(",\"driver_uuid\":", app->log);
  json_uuid(app->log, app->id_properties_valid, app->id_properties.driverUUID);
  fprintf(app->log, ",\"vendor_id\":\"0x%04x\",\"device_id\":\"0x%04x\"",
          app->physical_properties.vendorID, app->physical_properties.deviceID);
  fputs(",\"selected_pci\":", app->log);
  json_selected_pci(app->log, app);
  fputs(",\"driver_name\":", app->log);
  json_string(app->log, app->driver_properties_valid ? app->driver_name
                                                       : "UNKNOWN");
  fputs(",\"driver_info\":", app->log);
  json_string(app->log, app->driver_properties_valid ? app->driver_info
                                                       : "UNKNOWN");
  fprintf(app->log, ",\"driver_version\":%" PRIu32,
          app->physical_properties.driverVersion);
  fprintf(app->log, ",\"queue_family_index\":%" PRIu32,
          app->queue_family);
  fprintf(app->log, ",\"timestamp_period_ns\":%.9g",
          (double)app->timestamp_period_ns);
  fprintf(app->log, ",\"timestamp_valid_bits\":%" PRIu32,
          app->timestamp_valid_bits);
  fputs(",\"calibrated_timestamp_variant\":", app->log);
  json_string(app->log,
              app->calibrated_timestamp_variant != NULL
                  ? app->calibrated_timestamp_variant
                  : "NONE");
  fprintf(app->log, ",\"calibrated_function_available\":%s",
          app->calibrated_function_available ? "true" : "false");
  fputs(",\"device_time_domain\":", app->log);
  json_string(app->log, time_domain_name(VK_TIME_DOMAIN_DEVICE_KHR));
  fprintf(app->log, ",\"device_time_domain_id\":%" PRIu32,
          (uint32_t)VK_TIME_DOMAIN_DEVICE_KHR);
  fputs(",\"host_time_domain\":", app->log);
  json_string(app->log, time_domain_name(VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR));
  fprintf(app->log, ",\"host_time_domain_id\":%" PRIu32,
          (uint32_t)VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR);
  fprintf(app->log, ",\"frame_id\":%" PRIu64, record->frame_id);
  fputs(",\"calibration_before_sample_id\":", app->log);
  json_u64_or_null(app->log, record->calibration_before_valid,
                   record->calibration_before.sample_id);
  fputs(",\"calibration_after_sample_id\":", app->log);
  json_u64_or_null(app->log, record->calibration_after_valid,
                   record->calibration_after.sample_id);
  fputs(",\"calibration_before_status\":", app->log);
  if (record->calibration_before_valid &&
      record->calibration_before.status != NULL) {
    json_string(app->log, record->calibration_before.status);
  } else {
    fputs("null", app->log);
  }
  fputs(",\"calibration_after_status\":", app->log);
  if (record->calibration_after_valid &&
      record->calibration_after.status != NULL) {
    json_string(app->log, record->calibration_after.status);
  } else {
    fputs("null", app->log);
  }
  fputs(",\"calibration_same_run_status\":", app->log);
  json_string(app->log, record->calibration_same_run_status);
  fputs(",\"cpu_timestamp_before_recording_ns\":", app->log);
  json_u64_or_null(app->log, record->cpu_before_recording_valid,
                   record->cpu_before_recording_ns);
  fputs(",\"cpu_timestamp_before_submit_ns\":", app->log);
  json_u64_or_null(app->log, record->cpu_before_submit_valid,
                   record->cpu_before_submit_ns);
  fputs(",\"cpu_timestamp_after_submit_ns\":", app->log);
  json_u64_or_null(app->log, record->cpu_after_submit_valid,
                   record->cpu_after_submit_ns);
  fputs(",\"frame_callback_requested_cpu_ns\":", app->log);
  json_u64_or_null(app->log, record->frame_callback_requested_cpu_valid,
                   record->frame_callback_requested_cpu_ns);
  fputs(",\"frame_callback_received_cpu_ns\":", app->log);
  json_u64_or_null(app->log, record->frame_callback_received_cpu_valid,
                   record->frame_callback_received_cpu_ns);
  fputs(",\"cpu_callback_request_to_receive_ns\":", app->log);
  json_u64_or_null(app->log, record->cpu_callback_request_to_receive_valid,
                   record->cpu_callback_request_to_receive_ns);

  fputs(",\"gpu_timestamp_status\":", app->log);
  json_string(app->log, gpu_status);
  fputs(",\"gpu_query_result\":", app->log);
  if (record->gpu_query_requested) {
    json_string(app->log, vk_result_name(record->gpu_query_result));
  } else {
    fputs("null", app->log);
  }
  fputs(",\"gpu_timestamp_begin_ticks\":", app->log);
  json_u64_or_null(app->log, record->gpu_results_available,
                   record->gpu_begin_ticks);
  fputs(",\"gpu_timestamp_end_ticks\":", app->log);
  json_u64_or_null(app->log, record->gpu_results_available,
                   record->gpu_end_ticks);
  fputs(",\"gpu_elapsed_ticks_modulo\":", app->log);
  json_u64_or_null(app->log, record->gpu_results_available,
                   record->gpu_elapsed_ticks_modulo);
  fputs(",\"gpu_elapsed_ns_from_period_modulo\":", app->log);
  json_u64_or_null(app->log, record->gpu_elapsed_conversion_available,
                   record->gpu_elapsed_ns_from_period_modulo);
  fputs(",\"gpu_elapsed_conversion_status\":", app->log);
  json_string(app->log, record->gpu_elapsed_conversion_available
                              ? H12_STATUS_PRESENT
                              : H12_STATUS_NOT_AVAILABLE);
  fputs(",\"gpu_clock_correlation_status\":", app->log);
  json_string(app->log, record->gpu_clock_correlation_status);
  fputs(",\"gpu_timestamp_begin_cpu_candidate_ns\":", app->log);
  json_u64_or_null(app->log, record->gpu_timestamp_begin_cpu_candidate_valid,
                   record->gpu_timestamp_begin_cpu_candidate_ns);
  fputs(",\"gpu_timestamp_end_cpu_candidate_ns\":", app->log);
  json_u64_or_null(app->log, record->gpu_timestamp_end_cpu_candidate_valid,
                   record->gpu_timestamp_end_cpu_candidate_ns);
  fputs(",\"gpu_clock_mapping_method\":", app->log);
  if (record->gpu_clock_mapping_method != NULL) {
    json_string(app->log, record->gpu_clock_mapping_method);
  } else {
    fputs("null", app->log);
  }
  fputs(",\"gpu_clock_mapping_source_sample_id\":", app->log);
  json_u64_or_null(app->log, record->gpu_clock_mapping_source_sample_valid,
                   record->gpu_clock_mapping_source_sample_id);
  fputs(",\"gpu_clock_mapping_spread_ns\":", app->log);
  json_u64_or_null(app->log, record->gpu_clock_mapping_spread_valid,
                   record->gpu_clock_mapping_spread_ns);
  fputs(",\"gpu_clock_mapping_max_deviation_ns\":", app->log);
  json_u64_or_null(app->log, record->gpu_clock_mapping_max_deviation_valid,
                   record->gpu_clock_mapping_max_deviation_ns);
  fputs(",\"calibration_drift_status\":", app->log);
  json_string(app->log, record->calibration_drift_status);
  fputs(",\"calibration_device_delta_ticks\":", app->log);
  json_u64_or_null(app->log, record->calibration_drift_valid,
                   record->calibration_device_delta_ticks);
  fputs(",\"calibration_device_delta_ns\":", app->log);
  json_u64_or_null(app->log, record->calibration_drift_valid,
                   record->calibration_device_delta_ns);
  fputs(",\"calibration_host_delta_ns\":", app->log);
  json_u64_or_null(app->log, record->calibration_drift_valid,
                   record->calibration_host_delta_ns);
  fputs(",\"calibration_residual_ns\":", app->log);
  json_i64_or_null(app->log, record->calibration_drift_valid,
                   record->calibration_residual_ns);

  fputs(",\"gpu_fence_observed_cpu_ns\":", app->log);
  json_u64_or_null(app->log, record->gpu_fence_observed_cpu_valid,
                   record->gpu_fence_observed_cpu_ns);
  fputs(",\"gpu_fence_observation_source\":", app->log);
  if (record->gpu_fence_observed_cpu_valid &&
      record->gpu_fence_observation_source != NULL) {
    json_string(app->log, record->gpu_fence_observation_source);
  } else {
    fputs("null", app->log);
  }

  fputs(",\"present_call_timestamp_ns\":", app->log);
  json_u64_or_null(app->log, record->present_call_valid, record->present_call_ns);
  fputs(",\"present_id_requested\":", app->log);
  fputs(record->present_id_requested ? "true" : "false", app->log);
  fputs(",\"present_id_assigned\":", app->log);
  json_u64_or_null(app->log, record->present_id_requested,
                   record->present_id_assigned);
  fputs(",\"present_timing_status\":", app->log);
  json_string(app->log, timing_status);
  fputs(",\"present_timing_report_complete\":", app->log);
  if (record->timing.result_available) {
    fputs(record->timing.report_complete ? "true" : "false", app->log);
  } else {
    fputs("null", app->log);
  }
  fputs(",\"present_timing_present_id\":", app->log);
  json_u64_or_null(app->log, record->timing.result_available,
                   record->timing.present_id);
  fputs(",\"present_timing_target_requested\":", app->log);
  fputs(record->present_timing_target_requested ? "true" : "false", app->log);
  fputs(",\"present_timing_target_time_ns\":", app->log);
  json_u64_or_null(app->log, record->timing.result_available,
                   record->timing.target_time);
  fputs(",\"present_timing_stage_count\":", app->log);
  json_u64_or_null(app->log, record->timing.result_available,
                   record->timing.stage_count);
  fputs(",\"present_timing_stage_mask\":", app->log);
  json_u64_or_null(app->log, record->timing.result_available,
                   (uint64_t)record->timing.stage_mask);
  fputs(",\"present_timing_queue_operations_end_time\":", app->log);
  json_u64_or_null(app->log, record->timing.queue_operations_end_time_available,
                   record->timing.queue_operations_end_time);
  fputs(",\"present_timing_time_domain\":", app->log);
  json_u64_or_null(app->log, record->timing.result_available,
                   (uint64_t)record->timing.time_domain);
  fputs(",\"present_timing_time_domain_id\":", app->log);
  json_u64_or_null(app->log, record->timing.result_available,
                   record->timing.time_domain_id);

  fputs(",\"wl_surface_frame_callback_status\":", app->log);
  json_string(app->log, callback_status);
  fputs(",\"wl_surface_frame_callback_time_ms\":", app->log);
  json_u64_or_null(app->log, record->callback_received,
                   record->callback_time_ms);
  fputs(",\"frame_interval_ns\":", app->log);
  json_u64_or_null(app->log, record->frame_interval_valid,
                   record->frame_interval_ns);
  fputs(",\"frame_interval_source\":\"present_call_cpu_monotonic\"", app->log);

  fputs(",\"image_index\":", app->log);
  fprintf(app->log, "%" PRIu32, record->image_index);
  fputs(",\"acquire_result\":", app->log);
  json_string(app->log, vk_result_name(record->acquire_result));
  fputs(",\"submit_result\":", app->log);
  json_string(app->log, vk_result_name(record->submit_result));
  fputs(",\"present_result\":", app->log);
  json_string(app->log, vk_result_name(record->present_result));
  fputs(",\"present_per_image_result\":", app->log);
  json_string(app->log, vk_result_name(record->present_per_image_result));
  fputs("}\n", app->log);
  fflush(app->log);
  record->emitted = true;
  ++app->emitted_frames;
}

static bool record_ready(App *app, FrameRecord *record, bool final)
{
  (void)app;
  if (!record->gpu_done) {
    return false;
  }
  if (!record->callback_received && !final) {
    return false;
  }
  if (record->timing_requested && !record->timing.complete &&
      !record->timing.conflict && !final) {
    return false;
  }
  return true;
}

static void emit_ready_records(App *app, bool final)
{
  while (app->emitted_frames < app->submitted_frames) {
    FrameRecord *record = &app->records[app->emitted_frames];
    if (!record_ready(app, record, final)) {
      break;
    }
    write_frame_record(app, record, final);
  }
}

static void drain_and_emit(App *app)
{
  g_abort_app = app;
  g_abort_phase = "drain";
  g_abort_frame_valid = app->submitted_frames > 0u;
  g_abort_frame_id = g_abort_frame_valid
                         ? (uint64_t)app->submitted_frames - 1u
                         : 0u;
  uint64_t start_ns = 0;
  if (!monotonic_ns(&start_ns)) {
    fatal("CLOCK_MONOTONIC failed at drain start");
  }
  uint64_t drain_ns = (uint64_t)app->cfg.drain_ms * UINT64_C(1000000);

  for (;;) {
    poll_gpu_resources(app);
    poll_present_timing(app);
    wayland_service(app, 10);
    abort_if_surface_reconfigured(app);
    emit_ready_records(app, false);

    bool all_gpu_done = true;
    for (uint32_t i = 0; i < app->resource_count; ++i) {
      if (app->resources[i].in_flight) {
        all_gpu_done = false;
        break;
      }
    }
    if (all_gpu_done && app->emitted_frames == app->submitted_frames) {
      break;
    }
    uint64_t now_ns = 0;
    if (!monotonic_ns(&now_ns)) {
      fatal("CLOCK_MONOTONIC failed during drain");
    }
    if (now_ns - start_ns >= drain_ns) {
      break;
    }
  }

  for (uint32_t i = 0; i < app->resource_count; ++i) {
    wait_for_resource(app, &app->resources[i]);
  }
  poll_present_timing(app);
  emit_ready_records(app, true);
}

/* ------------------------------------------------------------------------- */
/* Metadata and lifecycle                                                    */
/* ------------------------------------------------------------------------- */

static void write_metadata(App *app)
{
  fprintf(app->log,
          "{\"schema\":\"" H12_PROBE_METADATA_SCHEMA
          "\",\"event\":\"metadata\",\"target_pci\":\"%04x:%04x\"",
          H12_TARGET_VENDOR_ID, H12_TARGET_DEVICE_ID);
  fputs(",\"run_id\":", app->log);
  json_string(app->log, app->run_id_valid ? app->run_id : "UNKNOWN");
  fputs(",\"selected_pci\":", app->log);
  json_selected_pci(app->log, app);
  fputs(",\"device_name\":", app->log);
  json_string(app->log, app->physical_properties.deviceName);
  fprintf(app->log, ",\"vendor_id\":\"0x%04x\",\"device_id\":\"0x%04x\"",
          app->physical_properties.vendorID, app->physical_properties.deviceID);
  fputs(",\"device_uuid\":", app->log);
  json_uuid(app->log, app->id_properties_valid, app->id_properties.deviceUUID);
  fputs(",\"driver_uuid\":", app->log);
  json_uuid(app->log, app->id_properties_valid, app->id_properties.driverUUID);
  fputs(",\"driver_name\":", app->log);
  json_string(app->log, app->driver_properties_valid ? app->driver_name
                                                       : "UNKNOWN");
  fputs(",\"driver_info\":", app->log);
  json_string(app->log, app->driver_properties_valid ? app->driver_info
                                                       : "UNKNOWN");
  fprintf(app->log, ",\"driver_version\":%" PRIu32,
          app->physical_properties.driverVersion);
  fprintf(app->log, ",\"queue_family_index\":%" PRIu32
                    ",\"queue_count\":1",
          app->queue_family);
  fprintf(app->log, ",\"surface_width\":%" PRIu32
                    ",\"surface_height\":%" PRIu32
                    ",\"swapchain_image_count\":%" PRIu32
                    ",\"initial_xdg_configure_completed\":"
                    "%s,\"xdg_surface_configure_count\":%" PRIu32
                    ",\"toplevel_configure_count\":%" PRIu32,
          app->surface_width, app->surface_height,
          app->swapchain_image_count,
          app->initial_configure_completed ? "true" : "false",
          app->xdg_surface_configure_count,
          app->toplevel_configure_count);
  fprintf(app->log, ",\"present_mode_requested\":");
  json_string(app->log, app->cfg.requested_present_mode_name);
  fputs(",\"present_mode_selected\":", app->log);
  json_string(app->log, app->selected_present_mode_name);
  fputs(",\"timestamp_query_capability\":", app->log);
  json_string(app->log, app->timestamp_query_capability);
  fprintf(app->log, ",\"timestamp_valid_bits\":%" PRIu32
                    ",\"timestamp_period_ns\":%.9g",
          app->timestamp_valid_bits, (double)app->timestamp_period_ns);
  fputs(",\"cpu_timestamp_clock\":\"CLOCK_MONOTONIC\"", app->log);
  fputs(",\"gpu_timestamp_domain\":\"VK_TIME_DOMAIN_DEVICE\"", app->log);
  fputs(",\"gpu_timestamp_conversion\":"
        "\"timestampPeriod; modulo elapsed ticks; CPU candidates only from H12-4 brackets\"",
        app->log);
  fputs(",\"present_timing_time_domain_stage\":", app->log);
  json_u64_or_null(app->log, app->present_timing_time_domain_valid,
                   app->present_timing_time_domain_stage);
  fputs(",\"present_timing_time_domain_kind\":", app->log);
  json_u64_or_null(app->log, app->present_timing_time_domain_valid,
                   (uint64_t)app->present_timing_time_domain_kind);
  fputs(",\"present_timing_time_domains_counter\":", app->log);
  json_u64_or_null(app->log, app->present_timing_time_domain_valid,
                   app->present_timing_time_domains_counter);
  fputs(",\"present_id2_capability\":", app->log);
  json_string(app->log, app->present_id2_capability);
  fputs(",\"present_id2_surface_supported\":", app->log);
  fputs(app->present_id2_surface_supported ? "true" : "false", app->log);
  fputs(",\"present_timing_capability\":", app->log);
  json_string(app->log, app->present_timing_capability);
  fputs(",\"present_wait2_capability\":", app->log);
  json_string(app->log, app->present_wait2_capability);
  fputs(",\"present_wait2_swapchain_enabled\":", app->log);
  fputs(app->present_wait2_swapchain_enabled ? "true" : "false", app->log);
  fputs(",\"calibrated_timestamps_capability\":", app->log);
  json_string(app->log, app->calibrated_timestamps_capability);
  fputs(",\"calibrated_timestamp_variant\":", app->log);
  json_string(app->log,
              app->calibrated_timestamp_variant != NULL
                  ? app->calibrated_timestamp_variant
                  : "NONE");
  fputs(",\"calibrated_function_available\":", app->log);
  fputs(app->calibrated_function_available ? "true" : "false", app->log);
  fputs(",\"calibrated_domain_query_valid\":", app->log);
  fputs(app->calibrated_domain_query_valid ? "true" : "false", app->log);
  fputs(",\"calibration_same_run_status\":", app->log);
  json_string(app->log, calibration_same_run_status(app));
  fputs(",\"logical_device_scope\":\"single_vk_device_per_run\"", app->log);
  fputs(",\"logical_device_created\":true", app->log);
  fputs(",\"calibrated_timestamp_domain_count\":", app->log);
  json_u64_or_null(app->log, app->calibrated_domain_query_valid,
                   app->calibrated_domain_count);
  fputs(",\"calibrated_timestamp_domains_raw\":[", app->log);
  uint32_t domain_count = app->calibrated_domain_count;
  if (domain_count > H12_MAX_CALIBRATED_DOMAINS) {
    domain_count = H12_MAX_CALIBRATED_DOMAINS;
  }
  for (uint32_t i = 0; i < domain_count; ++i) {
    if (i != 0u) {
      fputc(',', app->log);
    }
    fprintf(app->log, "%" PRIu32, app->calibrated_domains[i]);
  }
  fputc(']', app->log);
  fputs(",\"calibrated_timestamp_domains\":", app->log);
  json_calibrated_domains(app->log, app);
  fputs(",\"calibrated_device_domain_supported\":", app->log);
  fputs(app->calibrated_device_domain_supported ? "true" : "false", app->log);
  fputs(",\"calibrated_clock_monotonic_supported\":", app->log);
  fputs(app->calibrated_monotonic_domain_supported ? "true" : "false", app->log);
  fputs(",\"calibrated_domains_truncated\":", app->log);
  fputs(app->calibrated_domains_truncated ? "true" : "false", app->log);
  fputs(",\"calibrated_device_time_domain\":", app->log);
  json_string(app->log, time_domain_name(VK_TIME_DOMAIN_DEVICE_KHR));
  fprintf(app->log, ",\"calibrated_device_time_domain_id\":%" PRIu32,
          (uint32_t)VK_TIME_DOMAIN_DEVICE_KHR);
  fputs(",\"calibrated_host_time_domain\":", app->log);
  json_string(app->log, time_domain_name(VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR));
  fprintf(app->log, ",\"calibrated_host_time_domain_id\":%" PRIu32,
          (uint32_t)VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR);
  fputs(",\"gpu_cpu_clock_correlation\":", app->log);
  json_string(app->log, H12_STATUS_UNKNOWN);
  fputs(",\"first_pixel\":", app->log);
  json_string(app->log, H12_STATUS_NOT_AVAILABLE);
  fputs(",\"vblank\":", app->log);
  json_string(app->log, H12_STATUS_NOT_AVAILABLE);
  fputs(",\"display_latency\":", app->log);
  json_string(app->log, H12_STATUS_NOT_AVAILABLE);
  fputs(",\"queue_ownership_exclusive\":", app->log);
  json_string(app->log, H12_STATUS_UNKNOWN);
  fputs(",\"async_overlap\":", app->log);
  json_string(app->log, H12_STATUS_UNKNOWN);
  fputs(",\"pcie_bandwidth\":", app->log);
  json_string(app->log, H12_STATUS_NOT_AVAILABLE);
  fputs("}\n", app->log);
  fflush(app->log);
  app->metadata_written = true;
  for (uint32_t i = 0; i < app->pending_configure_diagnostic_count; ++i) {
    emit_xdg_surface_configure_diagnostic(
        app, &app->pending_configure_diagnostics[i]);
  }
  app->pending_configure_diagnostic_count = 0u;
}

static void write_summary(App *app)
{
  fprintf(app->log,
          "{\"schema\":\"" H12_PROBE_SUMMARY_SCHEMA
          "\",\"event\":\"summary\",\"run_id\":");
  json_string(app->log, app->run_id_valid ? app->run_id : "UNKNOWN");
  fputs(",\"calibration_same_run_status\":", app->log);
  json_string(app->log, calibration_same_run_status(app));
  fprintf(app->log, ",\"frames_requested\":%" PRIu32
                    ",\"frames_submitted\":%" PRIu32 ",\"frames_emitted\":%" PRIu32
          ",\"unmatched_present_timing_observations\":%" PRIu64
          ",\"present_timing_poll_error_count\":%" PRIu32
          ",\"pending_frame_callbacks_final\":%" PRIu32
          ",\"calibration_sample_count\":%" PRIu32
          ",\"calibration_present_count\":%" PRIu32
          ",\"calibration_unknown_count\":%" PRIu32
          ",\"calibration_not_available_count\":%" PRIu32
          ",\"calibration_mapping_present_count\":%" PRIu32
          ",\"calibration_mapping_unknown_count\":%" PRIu32
          ",\"calibration_mapping_not_available_count\":%" PRIu32
          ",\"calibration_max_deviation_ns\":",
          app->cfg.frames, app->submitted_frames, app->emitted_frames,
          app->unmatched_present_timing_count,
          app->present_timing_poll_error_count,
          app->pending_frame_callbacks, app->calibration_sample_count,
          app->calibration_present_count, app->calibration_unknown_count,
          app->calibration_not_available_count,
          app->calibration_mapping_present_count,
          app->calibration_mapping_unknown_count,
          app->calibration_mapping_not_available_count);
  json_u64_or_null(app->log, app->calibration_max_deviation_valid,
                   app->calibration_max_deviation_ns);
  fputs(",\"final_state\":", app->log);
  json_string(app->log, g_abort_final_state);
  fputs(",\"cleanup_performed\":", app->log);
  fputs(g_abort_cleanup_performed ? "true" : "false", app->log);
  fputs(",\"cleanup_status\":", app->log);
  json_string(app->log, g_abort_cleanup_status);
  fputs(",\"initial_xdg_configure_completed\":", app->log);
  fputs(app->initial_configure_completed ? "true" : "false", app->log);
  fputs(",\"first_present_completed\":", app->log);
  fputs(app->first_present_completed ? "true" : "false", app->log);
  fprintf(app->log, ",\"xdg_surface_configure_count\":%" PRIu32
                    ",\"toplevel_configure_count\":%" PRIu32,
          app->xdg_surface_configure_count,
          app->toplevel_configure_count);
  fputs(",\"surface_reconfigure_pending\":", app->log);
  fputs(app->surface_reconfigure_pending ? "true" : "false", app->log);
  fputs(",\"surface_reconfigure_code\":", app->log);
  if (app->surface_reconfigure_code != NULL) {
    json_string(app->log, app->surface_reconfigure_code);
  } else {
    fputs("null", app->log);
  }
  fputs(",\"gpu_cpu_clock_correlation_final\":", app->log);
  if (app->emitted_frames > 0u &&
      app->calibration_mapping_present_count == app->emitted_frames &&
      app->calibration_mapping_unknown_count == 0u &&
      app->calibration_mapping_not_available_count == 0u) {
    json_string(app->log, H12_STATUS_PRESENT);
  } else if (app->emitted_frames > 0u &&
             app->calibration_mapping_not_available_count == app->emitted_frames &&
             app->calibration_mapping_present_count == 0u &&
             app->calibration_mapping_unknown_count == 0u) {
    json_string(app->log, H12_STATUS_NOT_AVAILABLE);
  } else {
    json_string(app->log, H12_STATUS_UNKNOWN);
  }
  fputs(",\"last_present_timing_poll_result\":", app->log);
  json_string(app->log, vk_result_name(app->last_present_timing_poll_result));
  fputs(",\"present_timing_capability_final\":", app->log);
  json_string(app->log, app->present_timing_capability);
  fputs(",\"present_timing_time_domains_counter_final\":", app->log);
  json_u64_or_null(app->log, app->present_timing_time_domain_valid,
                   app->present_timing_time_domains_counter);
  fputs(",\"swapchain_suboptimal_observed\":", app->log);
  fputs(app->swapchain_suboptimal_observed ? "true" : "false", app->log);
  fputs("}\n", app->log);
  fflush(app->log);
  g_abort_summary_written = true;
}

static void run_frames(App *app)
{
  for (uint32_t frame_id = 0; frame_id < app->cfg.frames; ++frame_id) {
    g_abort_app = app;
    g_abort_phase = "frame_loop";
    g_abort_frame_valid = true;
    g_abort_frame_id = frame_id;
    wayland_service(app, 0);
    abort_if_surface_reconfigured(app);
    if (app->close_requested) {
      fatal("compositor requested close before frame %" PRIu32, frame_id);
    }
    FrameResource *resource = find_free_resource(app);
    FrameRecord *record = &app->records[frame_id];
    memset(record, 0, sizeof(*record));
    record->frame_id = frame_id;
    record->callback_proxy = NULL;
    record->callback_data = NULL;
    record->image_index = H12_MAX_UINT32;
    record->acquire_result = VK_SUCCESS;
    record->submit_result = VK_SUCCESS;
    record->present_result = VK_SUCCESS;
    record->present_per_image_result = VK_SUCCESS;
    record->gpu_query_result = VK_NOT_READY;
    record->gpu_query_requested = app->gpu_timestamp_capable;
    record->present_id_assigned = frame_id + 1u;
    record->present_id_requested = app->present_id2_usable;
    record->timing_requested = app->present_timing_enabled;
    record->timing.present_id = record->present_id_assigned;
    resource->active_record = record;

    check_vk(vkResetFences(app->device, 1, &resource->fence),
             "vkResetFences");
    acquire_next_image_with_service(app, resource, record);
    if (record->image_index == H12_MAX_UINT32 ||
        record->image_index >= app->swapchain_image_count) {
      fatal("vkAcquireNextImageKHR returned invalid image index");
    }

    record_command_buffer(app, resource, record);
    /* Wayland Vulkan WSI owns the buffer attach/commit performed by
     * vkQueuePresentKHR.  The callback is requested inside the pre-present
     * barrier in submit_and_present_frame(), after pending configures settle. */
    submit_and_present_frame(app, resource, record);
    wayland_flush(app);

    poll_present_timing(app);
    poll_gpu_resources(app);
    wayland_service(app, 0);
    abort_if_surface_reconfigured(app);
    emit_ready_records(app, false);
  }
  drain_and_emit(app);
}

static void destroy_frame_callbacks(App *app)
{
  if (app->records == NULL) {
    return;
  }
  for (uint32_t i = 0; i < app->cfg.frames; ++i) {
    bool had_pending_callback =
        app->records[i].callback_proxy != NULL ||
        app->records[i].callback_data != NULL;
    if (app->records[i].callback_proxy != NULL) {
      wl_callback_destroy(app->records[i].callback_proxy);
      app->records[i].callback_proxy = NULL;
    }
    if (app->records[i].callback_data != NULL) {
      free(app->records[i].callback_data);
      app->records[i].callback_data = NULL;
    }
    if (had_pending_callback && app->pending_frame_callbacks > 0u) {
      --app->pending_frame_callbacks;
    }
  }
}

static void cleanup(App *app)
{
  g_abort_app = app;
  g_abort_phase = "cleanup";
  g_abort_frame_valid = false;
  g_abort_cleanup_status = "STARTED";
  if (app->display != NULL) {
    destroy_frame_callbacks(app);
  }

  if (app->device != VK_NULL_HANDLE) {
    if (app->resources != NULL) {
      for (uint32_t i = 0; i < app->resource_count; ++i) {
        FrameResource *resource = &app->resources[i];
        if (resource->in_flight) {
          wait_for_resource(app, resource);
        }
      }
    }
    VkResult idle_result = vkDeviceWaitIdle(app->device);
    if (idle_result != VK_SUCCESS) {
      fatal("vkDeviceWaitIdle failed: %s", vk_result_name(idle_result));
    }
    if (app->present_semaphores != NULL) {
      for (uint32_t i = 0; i < app->swapchain_image_count; ++i) {
        if (app->present_semaphores[i] != VK_NULL_HANDLE) {
          vkDestroySemaphore(app->device, app->present_semaphores[i], NULL);
          app->present_semaphores[i] = VK_NULL_HANDLE;
        }
      }
      free(app->present_semaphores);
      app->present_semaphores = NULL;
    }
    if (app->resources != NULL) {
      for (uint32_t i = 0; i < app->resource_count; ++i) {
        FrameResource *resource = &app->resources[i];
        if (resource->query_pool != VK_NULL_HANDLE) {
          vkDestroyQueryPool(app->device, resource->query_pool, NULL);
        }
        if (resource->fence != VK_NULL_HANDLE) {
          vkDestroyFence(app->device, resource->fence, NULL);
        }
        if (resource->acquire_semaphore != VK_NULL_HANDLE) {
          vkDestroySemaphore(app->device, resource->acquire_semaphore, NULL);
        }
      }
      free(app->resources);
      app->resources = NULL;
    }
    free(app->records);
    app->records = NULL;
    if (app->command_pool != VK_NULL_HANDLE) {
      vkDestroyCommandPool(app->device, app->command_pool, NULL);
    }
    destroy_swapchain_images(app);
    if (app->render_pass != VK_NULL_HANDLE) {
      vkDestroyRenderPass(app->device, app->render_pass, NULL);
    }
    vkDestroyDevice(app->device, NULL);
    app->device = VK_NULL_HANDLE;
  }

  free(app->present_timing_results);
  free(app->present_timing_stage_storage);
  app->present_timing_results = NULL;
  app->present_timing_stage_storage = NULL;

  if (app->instance != VK_NULL_HANDLE) {
    if (app->surface != VK_NULL_HANDLE && app->pfn_destroy_surface != NULL) {
      app->pfn_destroy_surface(app->instance, app->surface, NULL);
    }
    vkDestroyInstance(app->instance, NULL);
    app->instance = VK_NULL_HANDLE;
  }

  if (app->xdg_toplevel != NULL) {
    xdg_toplevel_destroy(app->xdg_toplevel);
  }
  if (app->xdg_surface != NULL) {
    xdg_surface_destroy(app->xdg_surface);
  }
  if (app->wl_surface != NULL) {
    wl_surface_destroy(app->wl_surface);
  }
  if (app->registry != NULL) {
    wl_registry_destroy(app->registry);
  }
  if (app->compositor != NULL) {
    wl_compositor_destroy(app->compositor);
  }
  if (app->xdg_wm_base != NULL) {
    xdg_wm_base_destroy(app->xdg_wm_base);
  }
  if (app->display != NULL) {
    wl_display_disconnect(app->display);
    app->display = NULL;
  }

  g_abort_cleanup_performed = true;
  g_abort_cleanup_status = "COMPLETED";
}

static void initialize_capability_defaults(App *app)
{
  app->present_id2_capability = H12_STATUS_NOT_AVAILABLE;
  app->present_timing_capability = H12_STATUS_NOT_AVAILABLE;
  app->present_wait2_capability = H12_STATUS_NOT_AVAILABLE;
  app->calibrated_timestamps_capability = H12_STATUS_NOT_AVAILABLE;
  app->timestamp_query_capability = H12_STATUS_NOT_AVAILABLE;
  app->present_wait2_swapchain_enabled = false;
  app->last_present_timing_poll_result = VK_SUCCESS;
  app->present_timing_poll_error_count = 0;
  app->surface = VK_NULL_HANDLE;
  app->swapchain = VK_NULL_HANDLE;
  app->render_pass = VK_NULL_HANDLE;
  app->command_pool = VK_NULL_HANDLE;
  app->gpu_timestamp_capable = false;
  app->timestamp_period_ns = 0.0f;
}

int main(int argc, char **argv)
{
  App app;
  memset(&app, 0, sizeof(app));
  initialize_capability_defaults(&app);
  initialize_run_id(&app);
  g_abort_phase = "startup";
  g_abort_frame_valid = false;

  if (!parse_args(argc, argv, &app.cfg)) {
    print_usage(argv[0]);
    return EXIT_FAILURE;
  }

  if (strcmp(app.cfg.output_path, "-") == 0) {
    app.log = stdout;
    app.close_log = false;
  } else {
    app.log = fopen(app.cfg.output_path, "wx");
    if (app.log == NULL) {
      fprintf(stderr, "Cannot open output %s: %s\n", app.cfg.output_path,
              strerror(errno));
      return EXIT_FAILURE;
    }
    app.close_log = true;
  }

  g_abort_app = &app;
  g_abort_phase = "wayland_init";
  init_wayland(&app);
  g_abort_phase = "vulkan_setup";
  create_instance(&app);
  create_vulkan_surface(&app);
  select_physical_device(&app);
  query_device_features(&app);
  select_queue_family(&app);
  create_device(&app);
  query_surface_state(&app);
  load_device_function_pointers(&app);
  app.gpu_timestamp_capable =
      app.timestamp_valid_bits > 0 && app.timestamp_query_count >= 2u &&
      app.timestamp_period_ns > 0.0f;
  app.timestamp_query_capability = app.gpu_timestamp_capable
                                       ? H12_STATUS_PRESENT
                                       : H12_STATUS_NOT_AVAILABLE;
  create_swapchain_and_timing(&app);
  create_command_resources(&app);
  write_metadata(&app);
  g_abort_phase = "frame_loop";
  run_frames(&app);
  cleanup(&app);
  g_abort_phase = "summary";
  g_abort_frame_valid = false;
  g_abort_final_state = "COMPLETED";
  write_summary(&app);
  if (app.close_log) {
    fclose(app.log);
  }
  g_abort_app = NULL;
  return EXIT_SUCCESS;
}
