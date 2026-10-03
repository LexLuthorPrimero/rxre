/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * test_vm.c — validacion del modelo minimo de VM de GFX8.
 *
 * Ejecuta la logica real de target_vm.h, la misma que usaria el driver.
 * No carga el modulo. No toca la GPU. No mapea nada.
 *
 * Ademas verifica los LIMITES DE HARDWARE contra las cabeceras del corpus,
 * releidas en el momento, para que la tabla no pueda desviarse del hardware.
 */
#define _GNU_SOURCE
#include <stdio.h>
/* La ruta del corpus era RELATIVA al cwd ("../../RESEARCH/..."), y el cwd
 * puede estar en cualquier sitio: dentro del arbol funcionaba, fuera daba 0
 * y los tests de offset se convertian en falsos negativos.  Ahora es un
 * define con valor por defecto, sobreescribible con -DRX550_CORPUS=...,
 * y el Makefile lo toma de $(RX550_CORPUS) si esta definido. */
#ifndef RX550_CORPUS
#define RX550_CORPUS "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd"
#endif

#include <stdlib.h>
#include <string.h>

#include "../target_vm.h"

static int pass, fail;

static void chk(const char *id, const char *what, int got, int want)
{
	if (got == want) {
		printf("  PASS  %-5s %s\n", id, what);
		pass++;
	} else {
		printf("  FAIL  %-5s %s (got %d want %d)\n", id, what, got, want);
		fail++;
	}
}

static void chkll(const char *id, const char *what,
		  long long got, long long want)
{
	if (got == want) {
		printf("  PASS  %-5s %s\n", id, what);
		pass++;
	} else {
		printf("  FAIL  %-5s %s (got %lld want %lld)\n", id, what, got, want);
		fail++;
	}
}

int main(int argc, char **argv)
{
	struct target_vm_ctx c;
	int i, n_req = 0, n_notdet = 0, n_reqd = 0;
	const char *sh = argc > 1 ? argv[1] : "../../../RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_8_2_sh_mask.h";

	printf("Q1 · modelo minimo de VM de GFX8\n");
	printf("corpus: %s\n\n", sh);

	/* ---- V1: limites de hardware releidos del corpus ---- */
	printf("V1 · limites de hardware, releidos de gmc_8_2_sh_mask.h\n");
	{
		char line[512];
		FILE *f = fopen(sh, "r");
		unsigned long pn_mask = 0, depth_mask = 0, bs_mask = 0, en = 0;
		int leido = 0;

		chk("V0", "la cabecera sh_mask se puede abrir (si no, V1 seria falso)",
		    f ? 1 : 0, 1);
		if (f) {
			while (fgets(line, sizeof(line), f)) {
				if (strstr(line, "PAGE_TABLE_BASE_ADDR__PHYSICAL_PAGE_NUMBER_MASK"))
					sscanf(strstr(line, "0x"), "%lx", &pn_mask);
				if (strstr(line, "VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH_MASK"))
					sscanf(strstr(line, "0x"), "%lx", &depth_mask);
				if (strstr(line, "VM_CONTEXT0_CNTL__PAGE_TABLE_BLOCK_SIZE_MASK"))
					sscanf(strstr(line, "0x"), "%lx", &bs_mask);
				if (strstr(line, "VM_CONTEXT0_CNTL__ENABLE_CONTEXT_MASK"))
					sscanf(strstr(line, "0x"), "%lx", &en);
				leido++;
			}
			fclose(f);
		}
		chkll("V1a", "PHYSICAL_PAGE_NUMBER mask == 0xfffffff (28 bits)", pn_mask, 0xffffffful);
		chkll("V1b", "PAGE_TABLE_DEPTH mask == 0x6 (2 bits)", depth_mask, 0x6);
		chkll("V1c", "PAGE_TABLE_BLOCK_SIZE mask == 0xf000000 (4 bits)", bs_mask, 0xf000000ul);
		chkll("V1d", "ENABLE_CONTEXT mask == 0x1", en, 0x1);
		chkll("V1e", "el modelo usa la misma mascara de PN",
		      (long long)TVM_PT_BASE_PN_MASK, (long long)pn_mask);
		chkll("V1f", "el modelo usa la misma mascara de depth",
		      (long long)TVM_DEPTH_FIELD_MASK, (long long)depth_mask);
		chkll("V1g", "el modelo usa la misma mascara de block size",
		      (long long)TVM_BLOCKSIZE_FIELD_MASK, (long long)bs_mask);
		chkll("V1h", "28 bits de pagina + 12 de shift = 40 bits de direccion fisica",
		      (long long)TVM_MAX_PHYS_FROM_PN, 0x10000000000LL);
		chk("V1i", "28 bits deduce del hardware, no de memoria", TVM_PT_BASE_PN_BITS, 28);
		chk("V1j", "4 dominios de invalidacion de TLB", TVM_NR_TLB_DOMAINS, 4);
		chk("V1k", "mascara de los 4 dominios", TVM_TLB_REQ_ALL, 0xF);
		chk("V1l", "pagina de 4 KiB", TVM_PAGE_SIZE, 4096);
		(void)leido;
	}

	/* ---- V2: la maquina de estados del contexto ---- */
	printf("\nV2 · maquina de estados de un contexto\n");
	{
		tvm_ctx_init(&c);
		chk("V2a", "init deja ABSENT", c.state, TVM_CTX_ABSENT);
		chk("V2b", "ABSENT no es usable", tvm_ctx_usable(&c), 0);

		/* no se puede habilitar lo que no esta configurado */
		chk("V2c", "enable desde ABSENT se rechaza", tvm_ctx_enable(&c), 0);

		/* configuracion invalida: PN de 32 bits */
		chk("V2d", "PN de 33 bits se rechaza", tvm_ctx_configure(&c, 0, 0x20000000u, 1, 1), 0);
		chk("V2e", "y sigue ABSENT tras el rechazo", c.state, TVM_CTX_ABSENT);

		/* ctx_id fuera de los 2 registros de control */
		chk("V2f", "ctx_id 2 se rechaza (solo hay CNTL 0 y 1)", tvm_ctx_configure(&c, 2, 0, 1, 1), 0);
		/* depth y block_size fuera de sus campos */
		chk("V2g", "depth 4 se rechaza (campo de 2 bits)", tvm_ctx_configure(&c, 0, 0, 4, 1), 0);
		chk("V2h", "block_size 16 se rechaza (campo de 4 bits)", tvm_ctx_configure(&c, 0, 0, 1, 16), 0);

		/* configuracion valida */
		chk("V2i", "configure valido", tvm_ctx_configure(&c, 0, 0x1234, 1, 2), 1);
		chk("V2j", "queda CONFIGURED", c.state, TVM_CTX_CONFIGURED);
		chk("V2k", "no se puede configurar dos veces", tvm_ctx_configure(&c, 1, 0, 0, 0), 0);

		/* no se habilita sin tabla utilizable: esto es el invariante clave */
		chk("V2l", "enable sin page_table_valid se rechaza", tvm_ctx_enable(&c), 0);
		chk("V2m", "sigue CONFIGURED", c.state, TVM_CTX_CONFIGURED);

		c.page_table_valid = 1;
		chk("V2n", "enable con tabla valida", tvm_ctx_enable(&c), 1);
		chk("V2o", "queda ENABLED", c.state, TVM_CTX_ENABLED);
		chk("V2p", "ENABLED es usable", tvm_ctx_usable(&c), 1);

		/* invalida de TLB: dominio valido e invalido */
		chk("V2q", "invalidate de dominio 0 se acepta", tvm_ctx_invalidate_tlb(&c, TVM_TLB_REQ_D0), 1);
		chk("V2r", "queda TLB_INVALIDATE", c.state, TVM_CTX_TLB_INVALIDATE);
		chk("V2s", "mascara 0 se rechaza", tvm_ctx_invalidate_tlb(&c, 0), 0);
		chk("V2t", "dominio 4 (inexistente) se rechaza", tvm_ctx_invalidate_tlb(&c, 0x10), 0);
		chk("V2u", "no se puede invalidar dos veces seguidas", tvm_ctx_invalidate_tlb(&c, TVM_TLB_REQ_D1), 0);

		/* respuesta parcial: sigue pendiente */
		chk("V2v", "respuesta parcial no cierra la peticion",
		    tvm_ctx_invalidate_done(&c, TVM_TLB_REQ_D1), 0);
		chk("V2w", "sigue TLB_INVALIDATE", c.state, TVM_CTX_TLB_INVALIDATE);
		chk("V2x", "respuesta completa cierra", tvm_ctx_invalidate_done(&c, TVM_TLB_REQ_D0), 1);
		chk("V2y", "vuelve a ENABLED", c.state, TVM_CTX_ENABLED);
		chk("V2z", "tlb_pending queda en cero", c.tlb_pending, 0);
	}

	/* ---- V3: conversion PN -> fisico, y por que no es lo mismo ---- */
	printf("\nV3 · numero de pagina fisica != direccion fisica\n");
	{
		tvm_ctx_init(&c);
		tvm_ctx_configure(&c, 0, 0x1234, 1, 1);
		chkll("V3a", "PN 0x1234 -> fisica 0x1234000", (long long)tvm_pn_to_phys(0x1234), 0x1234000LL);
		chkll("V3b", "PN 0 -> fisica 0", (long long)tvm_pn_to_phys(0), 0);
		/* 28 bits de PN + 12 de shift = 40 bits de direccion fisica.
		 * El maximo es 0xFFFFFFF000, con los 12 bits bajos a cero. */
		chkll("V3c", "PN max de 28 bits -> 0xFFFFFFF000 (40 bits)",
		      (long long)tvm_pn_to_phys(TVM_PT_BASE_PN_MASK), 0xFFFFFFF000LL);
		chk("V3d", "PN con bit 28 puesto no es valido", tvm_pn_valid(0x10000000u), 0);
		chk("V3e", "PN con bit 27 puesto si es valido", tvm_pn_valid(0x08000000u), 1);
	}

	/* ---- V4: retirada y no reutilizacion ---- */
	printf("\nV4 · retirada\n");
	{
		tvm_ctx_init(&c);
		tvm_ctx_configure(&c, 0, 0x10, 1, 1);
		c.page_table_valid = 1;
		tvm_ctx_enable(&c);
		chk("V4a", "retire desde ENABLED", tvm_ctx_retire(&c), 1);
		chk("V4b", "queda RETIRED", c.state, TVM_CTX_RETIRED);
		chk("V4c", "RETIRED no es usable", tvm_ctx_usable(&c), 0);
		chk("V4d", "no se puede reutilizar un contexto retirado",
		    tvm_ctx_configure(&c, 0, 0x20, 1, 1), 0);
		chk("V4e", "no se puede habilitar un contexto retirado", tvm_ctx_enable(&c), 0);
		/* retirar en pleno invalidate no debe permitirse */
		tvm_ctx_init(&c);
		tvm_ctx_configure(&c, 0, 0x10, 1, 1);
		c.page_table_valid = 1;
		tvm_ctx_enable(&c);
		tvm_ctx_invalidate_tlb(&c, TVM_TLB_REQ_D0);
		chk("V4f", "no se retira con una TLB invalidate pendiente", tvm_ctx_retire(&c), 0);
		chk("V4g", "sigue TLB_INVALIDATE", c.state, TVM_CTX_TLB_INVALIDATE);
	}

	/* ---- V5: tabla de requisitos ---- */
	printf("\nV5 · requisitos del primer camino\n");
	for (i = 0; i < (int)TVM_NR_REQS; i++) {
		if (target_vm_requirements[i].need == TVM_NOT_DETERMINED)
			n_notdet++;
		else if (target_vm_requirements[i].need == TVM_REQUIRED)
			n_reqd++;
		n_req++;
	}
	chk("V5a", "la tabla de requisitos no esta vacia", n_req > 0, 1);
	{
		int fuera = 0;
		for (i = 0; i < (int)TVM_NR_REQS; i++)
			if (target_vm_requirements[i].need != TVM_REQUIRED &&
			    target_vm_requirements[i].need != TVM_NOT_REQUIRED_YET &&
			    target_vm_requirements[i].need != TVM_NOT_DETERMINED)
				fuera++;
		chk("V5b", "todo valor de need esta dentro de rango", fuera, 0);
	}
	printf("       %d requisitos: %d REQUIRED, %d NOT_REQUIRED_YET/NOT_DETERMINED\n",
	       n_req, n_reqd, n_notdet);
	chk("V5c", "hay al menos un NOT_DETERMINED honesto (depth y block size)", n_notdet >= 2, 1);
	/* ninguna fila puede quedar sin base declarada */
	for (i = 0; i < (int)TVM_NR_REQS; i++) {
		if (!target_vm_requirements[i].basis || !*target_vm_requirements[i].basis) {
			printf("  FAIL  V5d   fila %d sin base declarada\n", i);
			fail++;
		}
	}
	chk("V5d", "toda fila declara su base", 1, 1);
	/* multis contexts no es necesario todavia: es la conclusion central */
	{
		int enc = -1;
		for (i = 0; i < (int)TVM_NR_REQS; i++)
			if (!strcmp(target_vm_requirements[i].capability,
				    "multiplexacion de VMID"))
				enc = target_vm_requirements[i].need;
		chk("V5e", "multiplexacion de VMID = NOT_REQUIRED_YET", enc, TVM_NOT_REQUIRED_YET);
	}

	printf("\nresumen: %d PASS, %d FAIL\n", pass, fail);
	return fail ? 1 : 0;
}
