/* SPDX-License-Identifier: MIT
 * Validador diferencial: ejecuta en CPU la MISMA logica que ejecutaria el shader
 * GLSL, y la compara bloque a bloque contra el decodificador C de Fase 1.
 *
 * No necesita GPU, ni Vulkan, ni compilador GLSL. Sirve para decidir si la
 * algoritmo del shader es correcto ANTES de escribir una linea de GLSL que
 * nadie podria compilar ni ejecutar en este host.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "rx550_compress.h"

/* ---- como esta escrito el shader, literalmente (especificacion RE-03-F2) --- */
static void shader_as_specified(const rx550_block_t *b, uint8_t out[64])
{
    uint32_t b0, b1, b2, b3;
    memcpy(&b0, (const uint8_t *)b +  0, 4);
    memcpy(&b1, (const uint8_t *)b +  4, 4);
    memcpy(&b2, (const uint8_t *)b +  8, 4);
    memcpy(&b3, (const uint8_t *)b + 12, 4);

    uint32_t a0 = b0 & 0xFF, a1 = (b0 >> 8) & 0xFF, ap[8];
    ap[0] = a0; ap[1] = a1;
    if (a0 > a1) for (uint32_t i = 2; i < 8; i++) ap[i] = ((8-i)*a0 + (i-1)*a1 + 3)/7;
    else { for (uint32_t i = 2; i < 6; i++) ap[i] = ((6-i)*a0 + (i-1)*a1 + 2)/5; ap[6]=0; ap[7]=255; }

    /* TAL COMO VIENE EN LA ESPECIFICACION -- lee de block0/block1 */
    uint32_t c0_565 = (b0 >> 16) & 0xFFFF;
    uint32_t c1_565 = (b1 >> 16) & 0xFFFF;

    uint32_t r0 = ((c0_565>>11)&0x1F)*255/31, g0 = ((c0_565>>5)&0x3F)*255/63, b0c = (c0_565&0x1F)*255/31;
    uint32_t r1 = ((c1_565>>11)&0x1F)*255/31, g1 = ((c1_565>>5)&0x3F)*255/63, b1c = (c1_565&0x1F)*255/31;

    uint32_t pr[4], pg[4], pb[4];
    pr[0]=r0; pg[0]=g0; pb[0]=b0c; pr[1]=r1; pg[1]=g1; pb[1]=b1c;
    if (c0_565 > c1_565) {
        pr[2]=(2*r0+r1+1)/3; pg[2]=(2*g0+g1+1)/3; pb[2]=(2*b0c+b1c+1)/3;
        pr[3]=(r0+2*r1+1)/3; pg[3]=(g0+2*g1+1)/3; pb[3]=(b0c+2*b1c+1)/3;
    } else {
        pr[2]=(r0+r1)/2; pg[2]=(g0+g1)/2; pb[2]=(b0c+b1c)/2;
        pr[3]=0; pg[3]=0; pb[3]=0;
    }

    for (uint32_t px = 0; px < 16; px++) {
        uint32_t ao = px * 3, ai;
        if (ao < 32)       ai = (b0 >> ao) & 0x7;
        else if (ao < 48)  ai = (b1 >> (ao-32)) & 0x7;
        else               ai = (b2 >> (ao-48)) & 0x7;
        uint32_t ci = (b3 >> (px*2)) & 0x3;
        out[px*4+0] = (uint8_t)pr[ci];
        out[px*4+1] = (uint8_t)pg[ci];
        out[px*4+2] = (uint8_t)pb[ci];
        out[px*4+3] = (uint8_t)ap[ai];
    }
}

/* ---- version corregida: mismos offsets, misma paleta que el codificador C --- */
static uint8_t expand5(uint32_t v) { return (uint8_t)((v << 3) | (v >> 2)); }
static void shader_corrected(const rx550_block_t *b, uint8_t out[64])
{
    uint32_t b0,b1,b2,b3;
    memcpy(&b0,(const uint8_t*)b+ 0,4); memcpy(&b1,(const uint8_t*)b+ 4,4);
    memcpy(&b2,(const uint8_t*)b+ 8,4); memcpy(&b3,(const uint8_t*)b+12,4);

    uint32_t a0 = b0 & 0xFF, a1 = (b0>>8)&0xFF, ap[8];
    ap[0]=a0; ap[1]=a1;
    if (a0 > a1) for (uint32_t i=2;i<8;i++) ap[i]=((8-i)*a0+(i-1)*a1+3)/7;
    else { for (uint32_t i=2;i<6;i++) ap[i]=((6-i)*a0+(i-1)*a1+2)/5; ap[6]=0; ap[7]=255; }

    /* CORREGIDO: los endpoints de color viven en block2, no en block0/block1 */
    uint32_t c0_565 =  b2        & 0xFFFF;
    uint32_t c1_565 = (b2 >> 16) & 0xFFFF;
    uint32_t r0=expand5((c0_565>>11)&0x1F), g0=expand5((c0_565>>5)&0x3F), b0c=expand5(c0_565&0x1F);
    uint32_t r1=expand5((c1_565>>11)&0x1F), g1=expand5((c1_565>>5)&0x3F), b1c=expand5(c1_565&0x1F);

    /* CORREGIDO: siempre modo 4 colores, como el codificador de Fase 1 */
    uint32_t pr[4],pg[4],pb[4];
    pr[0]=r0; pg[0]=g0; pb[0]=b0c;  pr[1]=r1; pg[1]=g1; pb[1]=b1c;
    pr[2]=expand5((2*(c0_565>>11&0x1F)+(c1_565>>11&0x1F))/3);
    pg[2]=expand5((2*(c0_565>>5 &0x3F)+(c1_565>>5 &0x3F))/3);
    pb[2]=expand5((2*(c0_565     &0x1F)+(c1_565     &0x1F))/3);
    pr[3]=expand5(((c0_565>>11&0x1F)+2*(c1_565>>11&0x1F))/3);
    pg[3]=expand5(((c0_565>>5 &0x3F)+2*(c1_565>>5 &0x3F))/3);
    pb[3]=expand5(((c0_565     &0x1F)+2*(c1_565     &0x1F))/3);

    /* CORREGIDO: extraccion por BYTES, que es el inverso exacto de pack_3bit().
     * Los indices de 3 bits no alinean con los bytes: el pixel 5 ya cruza el
     * byte 1, y el pixel 5 CRUZA ademas la frontera de 32 bits entre b0 y b1.
     * Cualquier division por palabras tiene que tratar ese caso aparte. */
    const uint8_t *A = (const uint8_t *)b;   /* los 16 bytes del bloque */
    for (uint32_t px = 0; px < 16; px++) {
        uint32_t bit  = 3 * px;
        uint32_t byte = bit >> 3;
        uint32_t sh   = bit & 7u;
        uint32_t ai   = (uint32_t)A[2 + byte] >> sh;
        if (sh > 5u) ai |= (uint32_t)A[2 + byte + 1] << (8u - sh);
        ai &= 0x7;
        uint32_t ci = (b3 >> (px*2)) & 0x3;
        out[px*4+0]=(uint8_t)pr[ci]; out[px*4+1]=(uint8_t)pg[ci];
        out[px*4+2]=(uint8_t)pb[ci]; out[px*4+3]=(uint8_t)ap[ai];
    }
}

int main(void)
{
    rx550_rgba_block_t in; rx550_block_t blk; rx550_rgba_block_t ref;
    uint8_t as_spec[64], cor[64];
    unsigned bad_spec=0, bad_cor=0, p, c, n=0;
    unsigned srgb_sb=0, sbp=0, srgb_cb=0, cbp=0;

    /* corpus determinista: 64 bloques, patron vario + degenerados */
    for (n = 0; n < 64; n++) {
        for (p = 0; p < 16; p++) for (c = 0; c < 4; c++) {
            uint32_t v;
            if (n == 0)      v = 0xFF;
            else if (n == 1) v = 0x00;
            else if (n == 2) v = 0x80;
            else if (n < 8)  v = (uint32_t)(p * 16);
            else             v = (n * 2654435761u + p * 40503u + c * 97u) & 0xFF;
            in.px[p*4+c] = (uint8_t)v;
        }
        rx550_compress_block_c(&in, &blk);
        rx550_decompress_block(&blk, &ref);
        shader_as_specified(&blk, as_spec);
        shader_corrected  (&blk, cor);

        for (p = 0; p < 16; p++) for (c = 0; c < 4; c++) {
            uint8_t r = ref.px[p*4+c], s = as_spec[p*4+c], k = cor[p*4+c];
            if (s != r) { bad_spec++; if (c<3) { srgb_sb += (s>r?s-r:r-s); sbp++; } }
            if (k != r) { bad_cor++;  if (c<3) { srgb_cb += (k>r?k-r:r-k); cbp++; } }
        }
    }
    printf("  bloques del corpus          : %u\n", n);
    printf("  canales totales comparados  : %u\n", n*16*4);
    printf("\n  shader TAL COMO LA ESPECIFICACION:\n");
    printf("    canales incorrectos       : %u / %u  (%.1f%%)\n",
           bad_spec, n*16*4, 100.0*bad_spec/(n*16*4));
    printf("    error medio RGB           : %.2f\n", sbp? (double)srgb_sb/sbp : 0.0);
    printf("\n  shader CORREGIDO:\n");
    printf("    canales incorrectos       : %u / %u\n", bad_cor, n*16*4);
    printf("    error medio RGB           : %.2f\n", cbp? (double)srgb_cb/cbp : 0.0);
    printf("\n  VEREDICTO: %s\n", bad_cor==0 ? "CORREGIDO == decodificador C" : "AUN DISCREPANTE");
    return bad_cor==0 ? 0 : 1;
}
