/* RXRE-004 fixture. Un unico requisito: que RXRE pueda recorrer la vertical
 * binary.inspect sobre un artefacto que RXRE.controla y puede reconstruir.
 * No es codigo de driver. No toca hardware. No tiene sentido fuera del test. */
#include <stdint.h>

/* Direccion de un registro MMIO de la RX550 (0000:01:00.0). Escritura y
 * lectura. Es lo que un analista buscaria al abrir este binario con un
 * backend: el PATTERN de acceso a registro, no la semantica del registro.
 * RXRE NO debe conclusionar nada sobre el hardware a partir de esto. */
#define RX550_MMIO_BASE 0xD0000000u
#define REG_SET_FIELD    0x0000u
#define REG_RMW          0x0001u

volatile uint32_t *mmio(unsigned off) { return (volatile uint32_t *)(RX550_MMIO_BASE + off); }

void escribir_registro(unsigned off, uint32_t v) { *mmio(off) = v; }
uint32_t leer_registro(unsigned off) { return *mmio(off); }
void campo(unsigned off, uint32_t mask, uint32_t val) {
    uint32_t r = leer_registro(off);
    r = (r & ~mask) | (val & mask);
    escribir_registro(off, r);
}
