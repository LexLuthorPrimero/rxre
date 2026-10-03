# rx550_pciid — componente 1: identidad PCI
#
# Kbuild. Se compila contra el arbol del kernel en ejecucion:
#
#   make -C /usr/src/kernels/7.1.3-200.nobara.fc44.x86_64 M=$PWD modules
#
# No enlaza contra amdgpu: este componente no usa ninguna funcion suya.

obj-m += rx550_pciid.o

# Warnings altos. Sin excepciones: este componente debe seguir limpio al
# crecer, no solo hoy.
ccflags-y += -Wall -Wextra
