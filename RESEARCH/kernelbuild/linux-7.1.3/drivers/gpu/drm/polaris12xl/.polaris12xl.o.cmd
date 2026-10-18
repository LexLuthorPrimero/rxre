savedcmd_drivers/gpu/drm/polaris12xl/polaris12xl.o := ld -m elf_x86_64 -z noexecstack --no-warn-rwx-segments   -r -o drivers/gpu/drm/polaris12xl/polaris12xl.o @drivers/gpu/drm/polaris12xl/polaris12xl.mod  ; ./tools/objtool/objtool --hacks=jump_label --hacks=noinstr --hacks=skylake --ibt --orc --retpoline --rethunk --sls --static-call --uaccess --prefix=16  --link  --module drivers/gpu/drm/polaris12xl/polaris12xl.o

drivers/gpu/drm/polaris12xl/polaris12xl.o: $(wildcard ./tools/objtool/objtool)
