savedcmd_scripts/sorttable.o := gcc -Wp,-MMD,scripts/.sorttable.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu11   -I ./scripts/include  -I./tools/include -I./tools/arch/x86/include -DUNWINDER_ORC_ENABLED -DMCOUNT_SORT_ENABLED -c -o scripts/sorttable.o scripts/sorttable.c

source_scripts/sorttable.o := scripts/sorttable.c

deps_scripts/sorttable.o := \
  scripts/elf-parse.h \
  tools/include/tools/be_byteshift.h \
  tools/include/tools/le_byteshift.h \
  tools/arch/x86/include/asm/orc_types.h \
  tools/include/linux/types.h \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
  tools/include/linux/compiler.h \
  tools/include/linux/compiler_types.h \
  tools/include/linux/compiler-context-analysis.h \
  tools/include/linux/compiler-gcc.h \

scripts/sorttable.o: $(deps_scripts/sorttable.o)

$(deps_scripts/sorttable.o):
