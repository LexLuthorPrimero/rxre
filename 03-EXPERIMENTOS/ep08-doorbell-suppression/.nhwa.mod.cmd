savedcmd_nhwa.mod := printf '%s\n'   nhwa.o | awk '!x[$$0]++ { print("./"$$0) }' > nhwa.mod
