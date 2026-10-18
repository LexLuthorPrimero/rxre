savedcmd_scripts/mod/modpost.o := gcc -Wp,-MMD,scripts/mod/.modpost.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu11   -I ./scripts/include   -c -o scripts/mod/modpost.o scripts/mod/modpost.c

source_scripts/mod/modpost.o := scripts/mod/modpost.c

deps_scripts/mod/modpost.o := \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/MODULE_SRCVERSION_ALL) \
    $(wildcard include/config/BASIC_MODVERSIONS) \
    $(wildcard include/config/EXTENDED_MODVERSIONS) \
    $(wildcard include/config/TRIM_UNUSED_KSYMS) \
    $(wildcard include/config/MODULE_UNLOAD) \
    $(wildcard include/config/SECTION_MISMATCH_WARN_ONLY) \
  scripts/include/hash.h \
  scripts/include/hashtable.h \
  scripts/include/array_size.h \
  scripts/include/list.h \
  scripts/include/list_types.h \
  scripts/include/xalloc.h \
  scripts/mod/modpost.h \
  scripts/mod/../../include/linux/module_symbol.h \
  scripts/mod/elfconfig.h \
  scripts/mod/../../include/linux/license.h \

scripts/mod/modpost.o: $(deps_scripts/mod/modpost.o)

$(deps_scripts/mod/modpost.o):
