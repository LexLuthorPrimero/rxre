savedcmd_rx550_drv.mod := printf '%s\n'   rx550_target.o pci_resource.o rx550_mmio_access.o rx550_pdb0.o | awk '!x[$$0]++ { print("./"$$0) }' > rx550_drv.mod
