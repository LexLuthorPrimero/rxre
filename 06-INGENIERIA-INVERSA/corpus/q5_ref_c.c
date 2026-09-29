/* Referencia independiente en C de lp_build_lerpdxta(), para el barrido Q-5.
 *
 * POR QUE EXISTE, Y POR QUE NO ES OTRA TRANSCRIPCION
 *
 * La prediccion de Q-5 la produce mi transcripcion en Python. Python tiene
 * enteros de precision arbitraria y `>>` con semantica de suelo, mientras que
 * el codigo de Mesa es de 16 bits con wrap y desplazamiento LOGICO. Ese par de
 * diferencias es exactamente donde una transcripcion se equivoca sin que se
 * note: `(-1) >> 6` en Python da -1, y el C pide el patron de bits desplazado.
 *
 * Este fichero implementa la aritmetica con los TIPOS REALES -- int16_t para
 * delta, uint16_t para el wrap y el desplazamiento logico -- de modo que si
 * mi Python calcula lo mismo que el C en las 524288 observaciones, la
 * coincidencia no es de dos transcripciones del mismo texto, sino de dos
 * represents del mismo tipo de dato.
 *
 * NO ES EL EXPERIMENTO. No abre Vulkan, no toca la GPU, no lee texturas. Es
 * aritmetica pura, y sirve para falsar la prediccion ANTES de gastar la
 * autorizacion de RUNTIME_EXECUTION.
 *
 * Fuente: /home/lucas/mesa/src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c
 *         :817-877 (lp_build_lerpdxta) y :985 (llamada desde alpha_channel)
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* weight5 = 255*64/5, weight7 = 255*64/7 -- division entera, como en el C.
 * El fuente escribe 255*64/5 en un literal; aqui se evalua con enteros. */
#define WEIGHT5 3264u
#define WEIGHT7 2331u

/* Transcripcion de s3tc_dxt5_alpha_channel() con la aritmetica de
 * lp_build_lerpdxta(), que es lo que llvmpipe devuelve de verdad.
 *
 * CORRECCION IMPORTANTE, y el error que casi cuela
 * ------------------------------------------------
 * La primera version de este fichero implementaba SOLO lp_build_lerpdxta() y
 * la daba por la funcion completa. No lo es. lp_build_lerpdxta() no pone los
 * codigos 0 y 1: hace la interpolacion y devuelve. Quien decide esos casos, y
 * quien recorta el 6 y el 7 de la rama a0 <= a1, es el CALLER,
 * s3tc_dxt5_alpha_channel(), en lp_bld_format_s3tc.c:1000-1016:
 *
 *     alpha = (alphac == 0) ? alpha0 : alpha1;      <-- codigos 0 y 1
 *     alpha = (alphac >  1) ? ainterp : alpha;      <-- el resto
 *     code_s = alphac & ~sel_mask;                  <-- ~0 cuando a0 <= a1
 *     alpha  = alpha & ~mask6;                      <-- codigo 6 -> 0
 *     alpha  = alpha |  mask7;                      <-- codigo 7 -> todos los 1
 *     alpha  = alpha & 0xff;                        <-- 0xff == 255
 *
 * Es decir: el clamp de 6/7 que el preregistration atribuye al modelo es REAL
 * y esta en el fuente, y solo se aplica cuando a0 <= a1, porque code_s se
 * anula con sel_mask en la rama a0 > a1.
 *
 * Aplicar solo lp_build_lerpdxta() daria basura en los codigos 0 y 1 y
 * omitiria el recorte. Dos implementaciones con el mismo error coinciden
 * entre si, y eso NO es un control.
 *
 * Fuente: lp_bld_format_s3tc.c:817-877 (lerpdxta), :881-1020 (alpha_channel)
 */
static uint8_t alpha_channel(uint8_t a0, uint8_t a1, int code)
{
    int sel7 = (a0 > a1);
    uint16_t w16, shifted, interp;
    int16_t d16;
    int32_t w = sel7 ? (int32_t)WEIGHT7 : (int32_t)WEIGHT5;
    uint8_t a;

    /* --- lp_build_lerpdxta(), verbatim --- */
    w = w * (code - 1);
    w16 = (uint16_t)w;
    shifted = (uint16_t)(w16 >> 6);
    d16 = (int16_t)((uint16_t)a1 - (uint16_t)a0);
    interp = (uint16_t)((uint16_t)((int16_t)d16 * (int16_t)shifted));
    interp = (uint16_t)(interp >> 8);
    a = (uint8_t)((uint16_t)a0 + (uint16_t)interp);

    /* --- el caller, verbatim --- */
    if (code == 0) {
        a = a0;
    } else if (code == 1) {
        a = a1;
    } else if (!sel7) {
        if (code == 6) a = 0;
        if (code == 7) a = 255;
    }
    return a;
}

int main(int argc, char **argv)
{
    const char *out_path = (argc > 1) ? argv[1] : NULL;
    FILE *out = out_path ? fopen(out_path, "wb") : stdout;
    int a0, a1, i;
    unsigned long n = 0;

    if (!out) {
        fprintf(stderr, "no se abre %s\n", out_path);
        return 2;
    }

    /* Orden de recorrido: IGUAL al que usa la prediccion Python, byte a byte.
     * a0 exterior, a1 interior, indice 0..7. 65536 * 8 = 524288. */
    for (a0 = 0; a0 < 256; a0++) {
        for (a1 = 0; a1 < 256; a1++) {
            for (i = 0; i < 8; i++) {
                uint8_t v = alpha_channel((uint8_t)a0, (uint8_t)a1, i);
                fputc(v, out);
                n++;
            }
        }
    }

    if (out_path) {
        fclose(out);
        fprintf(stderr, "escritas %lu observaciones en %s\n", n, out_path);
    }
    return 0;
}
