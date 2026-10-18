savedcmd_scripts/ipe/polgen/polgen := gcc -Wp,-MMD,scripts/ipe/polgen/.polgen.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu11   -I ./scripts/include -I./include -I./include/uapi     -o scripts/ipe/polgen/polgen scripts/ipe/polgen/polgen.c   

source_scripts/ipe/polgen/polgen := scripts/ipe/polgen/polgen.c

deps_scripts/ipe/polgen/polgen := \

scripts/ipe/polgen/polgen: $(deps_scripts/ipe/polgen/polgen)

$(deps_scripts/ipe/polgen/polgen):
