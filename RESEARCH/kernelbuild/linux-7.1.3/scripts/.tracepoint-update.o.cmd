savedcmd_scripts/tracepoint-update.o := gcc -Wp,-MMD,scripts/.tracepoint-update.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu11   -I ./scripts/include  -I./tools/include -c -o scripts/tracepoint-update.o scripts/tracepoint-update.c

source_scripts/tracepoint-update.o := scripts/tracepoint-update.c

deps_scripts/tracepoint-update.o := \
    $(wildcard include/config/TRACEPOINT_VERIFY_USED) \
  scripts/elf-parse.h \
  tools/include/tools/be_byteshift.h \
  tools/include/tools/le_byteshift.h \

scripts/tracepoint-update.o: $(deps_scripts/tracepoint-update.o)

$(deps_scripts/tracepoint-update.o):
