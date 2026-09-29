# VFIO Feasibility Audit — `VFIO-FEASIBILITY-AUDIT-20260925T132242Z`

**Mode:** `READ_ONLY/EVIDENCE`
**Report timestamp:** `2026-09-25T13:22:42Z`
**Scope:** evaluating PCI passthrough of `0000:01:00.0` (AMD RX 550) without applying changes.
**Primary evidence:** `VFIO-FEASIBILITY-AUDIT-20260925T132242Z.json`
**JSON SHA256:** `27fc2799b203c9c30f86d0125c59953f7784930fe6d6158dac4f65509517b62e`

> No GRUB, BIOS, kernel, initramfs, driver, VFIO binding, VM, service, GPU reset, storage, or reboot action was performed. `sudo -n` read-only attempts were made where useful, but the environment required a password; privileged-only facts remain `NOT_AVAILABLE`.

## Compact result

```text
PASSTHROUGH_FEASIBILITY=BLOCKED
HOST_GPU=CONFLICT (physical output Intel HD 4600; observed KWin/Xwayland OpenGL renderer RX550)
GUEST_GPU=RX550 1002:699f 0000:01:00.0 (candidate only; not assigned)
IOMMU=NOT_ENABLED_CURRENTLY
IOMMU_HARDWARE=NOT_SUPPORTED_BY_IDENTIFIED_INTEL_H81_PLATFORM
IOMMU_GROUP=NOT_AVAILABLE (0 groups)
IOMMU_GROUP_SAFE=NOT_AVAILABLE/UNKNOWN
VFIO=COMPONENTS_AVAILABLE_AS_MODULES_NOT_LOADED; NOT_OPERATIONAL
LIBVIRT=NOT_AVAILABLE_CURRENTLY
QEMU=NOT_AVAILABLE_CURRENTLY
RESET=SUPPORTED_INTERFACE_OBSERVED; FLR_AND_REATTACH=UNKNOWN
HDMI_AUDIO=01:00.1_PRESENT; CONDITIONALLY_ASSIGN_WITH_01:00.0
RECOVERY=FAIL
STORAGE_SAFETY=UNKNOWN
REBOOT_REQUIRED=YES_FOR_PERSISTENT_CHANGES; NOT_PERFORMED
MODIFICATIONS_REQUIRED=VT-d-capable hardware; validated IOMMU groups; host Intel-only rendering; reset/reattach proof; libvirt/QEMU stack; recovery plan (NONE APPLIED)
```

## A. Hardware identity

### Intel HD 4600

| Field | Observed value | Classification |
|---|---|---|
| BDF | `0000:00:02.0` | `OBSERVED` |
| Vendor/device | `8086:0412` | `OBSERVED` |
| Class | `0x038000` | `OBSERVED` |
| Subsystem | `1019:7e44` | `OBSERVED` |
| Driver | `i915` | `OBSERVED` |
| Current DRM nodes | `card1`, `renderD128` | `OBSERVED` |
| Physical output | `card1-HDMI-A-1` connected/enabled | `OBSERVED` |

### RX 550 and all `01:00.x` functions

| Function | Identity | Driver | Role | Classification |
|---|---|---|---|---|
| `0000:01:00.0` | `1002:699f`, class `030000`, rev `c7`, subsystem `1002:0b04` | `amdgpu` | RX 550 display | `OBSERVED` |
| `0000:01:00.1` | `1002:aae0`, class `040300`, subsystem `1002:aae0` | `snd_hda_intel` | Baffin HDMI/DP audio | `OBSERVED` |

The kernel log identifies the display function as `POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7`. `01:00.1` is a separate PCI function at the same slot and is bound to the RX550 audio component. No other `01:00.x` function was present in the observed `lspci`/sysfs inventory.

**Numbering conflict:** historical project evidence used `card0=Intel` and `card1=RX550`; the current runtime uses `card1=Intel` and `card2=RX550`. This report uses BDF/vendor/device, never `cardN`, as identity.

## B. IOMMU / VT-d

### Current runtime

- `/sys/kernel/iommu_groups` contains **0** groups.
- `0000:01:00.0/iommu_group` is absent.
- `/sys/class/iommu` is empty.
- `/sys/module/intel_iommu` is absent.
- The kernel command line has no `intel_iommu`, `iommu`, `amd_iommu`, or VFIO parameter.
- The ACPI DMAR table, DRHD structures, RMRR and interrupt-remapping lines were parsed by the kernel.
- Kernel config contains `CONFIG_INTEL_IOMMU=y`, `CONFIG_IOMMU_SUPPORT=y`, and `CONFIG_DMAR_TABLE=y`, but `CONFIG_INTEL_IOMMU_DEFAULT_ON` is not set.

These observations support:

```text
IOMMU=NOT_ENABLED_CURRENTLY
IOMMU_GROUP=NOT_AVAILABLE
```

DMAR table presence and kernel compilation do not prove that a currently active IOMMU or usable groups exist.

### Hardware support

- The Intel i7-4790 product page says **VT-d: Yes**.
- The local board is `ECS H81H3-M4`; DMI and the H81/C220 PCI IDs identify the Intel H81 platform.
- Intel's official H81 chipset specification says **Intel VT-d: No**.
- ECS's official board specification identifies the H81H3-M4 as an Intel H81 board.

Therefore the CPU feature and the platform feature must not be conflated:

```text
CPU_VT_D=SUPPORTED (i7-4790)
H81_CHIPSET_VT_D=NOT_SUPPORTED (official Intel H81 specification)
PLATFORM_IOMMU=NOT_SUPPORTED_BY_IDENTIFIED_H81_PLATFORM
```

Intel's page also warns that feature availability depends on the complete system. No contrary local board implementation was found, so a BIOS toggle is not treated as a valid remedy for the identified H81 chipset.

## C. IOMMU group safety

`IOMMU_GROUP_SAFE=NOT_AVAILABLE/UNKNOWN`.

The Linux VFIO model makes an IOMMU group the unit of ownership. Because no group is exposed, the following required safety questions cannot be answered:

- Does `01:00.0` share a group with `01:00.1`?
- Does the RX550 share a group with the Intel HD 4600?
- Does the root port, SATA controller, Ethernet, or another critical device share the group?
- Can the RX550 be assigned without taking an essential host device?

Relevant devices were identified locally, but their group IDs are `UNKNOWN`:

| Device | Role | Driver | Group |
|---|---|---|---|
| `0000:00:02.0` | Intel HD 4600 | `i915` | `UNKNOWN` |
| `0000:00:1f.2` | H81 AHCI/SATA for `/dev/sda` and `/dev/sdb` | `ahci` | `UNKNOWN` |
| `0000:03:00.0` | Realtek Ethernet `enp3s0` | `r8169` | `UNKNOWN` |
| `0000:00:01.0` | RX550 PCIe root port | `pcieport` | `UNKNOWN` |
| `0000:01:00.0` | RX550 display | `amdgpu` | `UNKNOWN` |
| `0000:01:00.1` | RX550 audio | `snd_hda_intel` | `UNKNOWN` |

No `SAFE_CANDIDATE` classification is defensible from this state.

## D. VFIO driver

`modinfo` shows that the following components exist for the running kernel:

- `vfio`
- `vfio-pci`
- `vfio_iommu_type1`
- `kvm_intel`

They are not loaded. `/sys/bus/pci/drivers/vfio-pci` is absent, and `/dev/vfio/vfio` exists without any group device nodes. A container node alone is not evidence of a usable assignment path.

```text
VFIO_CORE=AVAILABLE_NOT_LOADED
VFIO_PCI=AVAILABLE_NOT_LOADED
VFIO_IOMMU_TYPE1=AVAILABLE_NOT_LOADED
VFIO_BIND=NOT_AVAILABLE
```

No bind, unbind, `new_id`, or module-load action was attempted.

## E. KVM, libvirt, QEMU and VMs

- `kvm_intel` is loaded and `/dev/kvm` exists.
- `libvirt`/`virsh`/`libvirtd`/`virtqemud` are not installed or not found.
- `qemu-system-x86_64` is not installed or not found; only `qemu-common` and ancillary packages were observed.
- `virt-manager` is not installed or not found.
- `/etc/libvirt`, `/var/lib/libvirt`, and `/var/lib/virt` are absent.
- No `qemu` or libvirt process was observed.

Therefore:

```text
KVM=KERNEL_SIDE_AVAILABLE
LIBVIRT=NOT_AVAILABLE_CURRENTLY
QEMU=NOT_AVAILABLE_CURRENTLY
VIRT_MANAGER=NOT_AVAILABLE_CURRENTLY
EXISTING_VMS=NOT_AVAILABLE (not proven empty)
NODEDEV_ENUMERATION=NOT_AVAILABLE
```

QEMU and libvirt support PCI hostdev/VFIO conceptually, but that does not establish local readiness.

## F. Host graphics

### Physical output

The Intel connector is active:

```text
card1-HDMI-A-1: connected, enabled, DPMS On
card1-VGA-1: disconnected
card2-DVI-D-1: disconnected
card2-HDMI-A-2: disconnected in the captured state
```

### Actual renderer

KWin's read-only D-Bus support information reported:

```text
Operation Mode: Wayland
Output backend: DRM
Compositing Type: OpenGL
OpenGL vendor: AMD
OpenGL renderer: AMD Radeon RX 550 / 550 Series (radeonsi, polaris12, ACO)
```

`glxinfo -B` on the current Xwayland display also reported the RX550 as the OpenGL renderer. `vulkaninfo --summary` enumerated both RX550 and Intel, but enumeration alone was not treated as proof of KWin selection.

Observed clients included Xwayland, KWin-related desktop services, `ksmserver`, `kded6`, `plasmashell`, Firefox, Konsole and ChatGPT with current RX550 DRM/render FDs. The unprivileged scan was not complete for root namespaces; no full ownership claim is made.

**Conclusion:** the physical monitor path is Intel, but the current compositor/Xwayland renderer is RX550. `RX550_NOT_REQUIRED_FOR_DESKTOP=FAIL` for the current state. Assigning it away without first proving an Intel-only rendering path risks host video loss.

## G. Reset and reattach

Observed without executing a reset:

```text
/sys/bus/pci/devices/0000:01:00.0/reset_method = bus
/sys/bus/pci/devices/0000:01:00.0/reset = exists
amdgpu module parameter reset_method = -1 (auto)
```

The kernel log reports Polaris12 initialization and `Using BACO for runtime pm`. It does not prove a successful detach/reattach cycle.

```text
RESET_INTERFACE=SUPPORTED_INTERFACE_OBSERVED
FLR=UNKNOWN
VENDOR_RESET=NOT_AVAILABLE
RESET_AFTER_GUEST=UNKNOWN
REATTACH_TO_AMDGPU=UNKNOWN
```

The Linux PCI/VFIO documentation describes reset and group ownership mechanisms, but the local reset method was not executed and no QEMU/libvirt lifecycle was tested.

## H. HDMI/DP audio

`0000:01:00.1` exists and is the RX550's Baffin HDMI/DP audio function. The kernel bound it to `snd_hda_intel` and associated it with `0000:01:00.0` through the amdgpu audio component.

If the guest requires HDMI/DP audio, both `01:00.0` and `01:00.1` must be considered together. The actual IOMMU group viability and guest-side behavior are `UNKNOWN`. Assigning only the display function could leave an audio-function/driver conflict; assigning both cannot be validated until a usable group and reset path exist.

## I. Existing VM

`EXISTING_VM=NOT_AVAILABLE`, not `NONE`. The current runtime has no available libvirt/QEMU management interface, so no trustworthy VM inventory, XML, firmware, machine type, CPU mode, RAM, storage, network, or PCI-device list could be obtained. No VM was created or modified.

## J. Storage safety

`/dev/sda` was identified as a Samsung HM500JI SATA disk. Its sysfs ancestry is:

```text
/dev/sda
  -> /sys/devices/pci0000:00/0000:00:1f.2/ata1/host0/...
```

`/dev/sdb` also descends from the same `0000:00:1f.2` H81 AHCI controller. No IOMMU group can be compared, so:

```text
STORAGE_SAFETY=UNKNOWN
```

No storage write, SMART command, scrub, mount change, or controller action was performed.

## K. Reversibility and required future changes

No future step was executed. Conceptually:

| Step | Classification | Notes |
|---|---|---|
| Current audit only | `REVERSIBLE` | No system change. |
| Move to a VT-d-capable platform | `REQUIRES_HARDWARE_NOT_CURRENTLY_AVAILABLE` | H81 is documented as VT-d=No. |
| BIOS/IOMMU enablement on compatible hardware | `REQUIRES_BIOS` | Firmware and reboot required; not a remedy for the identified H81 specification. |
| Persistent VFIO modules/initramfs | `REVERSIBLE_WITH_REBOOT` | Conceptual only; not performed. |
| Bind RX550 display/audio to VFIO | `HIGH_RISK` | Group viability, client shutdown, reset and recovery are unvalidated. |
| Create a hostdev VM | `REVERSIBLE_WITH_UNKNOWN_REATTACH` | Domain deletion is not equivalent to physical GPU recovery. |
| Return RX550 to `amdgpu` | `UNKNOWN` | No detach/reattach test exists. |
| Make KDE/Wayland Intel-only | `REVERSIBLE_WITH_REBOOT` | Current KWin/Xwayland evidence shows RX550 is active. |

## L. Principal risks

- **Host video loss — critical, observed:** KWin reports RX550 as its OpenGL renderer.
- **No usable hardware IOMMU — critical, supported:** H81 official VT-d=No; current groups=0.
- **IOMMU group isolation — unknown:** no group enumeration.
- **Audio function conflict — high, observed:** `01:00.1` is a bound multifunction audio device.
- **amdgpu/VFIO conflict — high, supported:** amdgpu currently owns `01:00.0`; VFIO is not bound.
- **Reset/reattach — high, unknown:** no guest lifecycle test.
- **Monitor dependency — high, observed:** Intel output connector is active, but RX550 is the observed renderer.
- **HDD/SATA risk — critical, unknown:** `/dev/sda` is behind `00:1f.2`, but group sharing is unavailable.
- **Recovery loss — critical, fail:** the existing project recovery gate remains `FAIL`; no VFIO-specific recovery path was validated.
- **Incomplete privileged visibility — medium, not available:** password-gated sudo prevented a complete root FD/audit pass.

## M. Conclusion

```text
PASSTHROUGH_FEASIBILITY=BLOCKED
```

The primary blocker is not a missing package or a disabled kernel switch: the identified Intel H81 platform is officially documented as lacking VT-d, and the running host exposes no IOMMU groups. Secondary blockers are the absence of libvirt/QEMU/virt-manager, current RX550 use by the desktop renderer, unknown audio/group/reset behavior, unknown SATA group safety, and no validated recovery route.

This is a feasibility result only. No implementation is authorized or performed.

## N. Sources and provenance

Official sources consulted on 2026-09-25:

1. [Intel H81 chipset specifications](https://www.intel.com/content/www/us/en/products/sku/75016/intel-h81-chipset/specifications.html) — VT-d: No.
2. [Intel Core i7-4790 specifications](https://www.intel.com/content/www/us/en/products/sku/80806/intel-core-i74790-processor-8m-cache-up-to-4-00-ghz/specifications.html) — CPU VT-d: Yes.
3. [ECS H81H3-M4 specification](https://www.ecs.com.tw/en/Product/Motherboard/H81H3-M4/specification) — board/platform identification.
4. [Linux VFIO documentation](https://docs.kernel.org/driver-api/vfio.html) — IOMMU groups as ownership units and binding semantics.
5. [Linux amdgpu module parameters](https://docs.kernel.org/gpu/amdgpu/module-parameters.html) — reset-method interface.
6. [Linux PCI sysfs documentation](https://docs.kernel.org/PCI/sysfs-pci.html) — PCI resource/reset interfaces.
7. [libvirt domain XML: hostdev assignment](https://libvirt.org/formatdomain.html#host-device-assignment) — PCI hostdev/managed lifecycle.
8. [libvirt node-device XML](https://libvirt.org/formatnode.html) — PCI/IOMMU group reporting.
9. [QEMU device pass-through documentation](https://www.qemu.org/docs/master/system/device-emulation.html#device-pass-through) — generic device pass-through semantics.

Local project sources and SHA256 hashes are recorded in the companion JSON. The repository was already dirty/uncommitted before this audit; no commit was made and no historical project document was overwritten.

## Accounting

```text
C1_EXECUTED=0
RUNTIME_MATERIALIZED=0
GPU_WRITES=0 (by this audit)
STORAGE_WRITES=0 (by this audit)
SYSTEM_CHANGES=0
VM_CREATED=0
VFIO_BOUND=0
REBOOT=0
RESET_EXECUTED=0
KWIN_XWAYLAND_STOPPED=0
PACKAGE_CHANGES=0
COMMIT=0
```

The accounting is scoped to actions performed by this audit; it is not a claim about unrelated background agents.

## Hashes

- JSON: `VFIO-FEASIBILITY-AUDIT-20260925T132242Z.json`
  SHA256: `27fc2799b203c9c30f86d0125c59953f7784930fe6d6158dac4f65509517b62e`
- Markdown: `VFIO-FEASIBILITY-AUDIT-20260925T132242Z.md`
  SHA256: recorded after final write and reported in the L1 response.

**NEXT:** `STOP_AND_REQUEST_SEPARATE_AUTHORIZATION`
