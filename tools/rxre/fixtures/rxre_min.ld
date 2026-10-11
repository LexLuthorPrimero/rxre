/* Enlazador minimo. Sin libc, sin crt, sin PIE: el fixture tiene que ser
 * reconstruible byte a byte con una sola instruccion documentada. */
ENTRY(_start)
SECTIONS {
  . = 0x400000;
  .text : { *(.text*) }
  .rodata : { *(.rodata*) }
  .data : { *(.data*) }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame) }
}
