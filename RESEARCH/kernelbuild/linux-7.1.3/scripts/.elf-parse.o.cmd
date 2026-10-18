savedcmd_scripts/elf-parse.o := gcc -Wp,-MMD,scripts/.elf-parse.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu11   -I ./scripts/include  -I./tools/include -c -o scripts/elf-parse.o scripts/elf-parse.c

source_scripts/elf-parse.o := scripts/elf-parse.c

deps_scripts/elf-parse.o := \
  scripts/elf-parse.h \
  tools/include/tools/be_byteshift.h \
  tools/include/tools/le_byteshift.h \

scripts/elf-parse.o: $(deps_scripts/elf-parse.o)

$(deps_scripts/elf-parse.o):
