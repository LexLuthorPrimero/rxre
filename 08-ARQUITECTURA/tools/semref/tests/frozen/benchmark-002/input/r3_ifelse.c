/*
 * r3_ifelse.c — fixture de la regresión R-3.
 *
 * Reproduce el defecto encontrado en el barrido real: cuando la regla de
 * Coccinelle encaja en un `if/else`, reemplaza la rama COMPLETA, y lineas de
 * contexto que no son llamadas —"else", "x = false;"— aparecen tambien como
 * lineas eliminadas ("-") en el unified diff. Un parser que acepte cualquier
 * linea "-" como sitio de llamada las cuenta de mas.
 *
 * El parser roto sobre este fichero produce 4 sitios; el correcto, 3.
 * La diferencia es exactamente una linea "else" por cada if/else con dos ramas.
 *
 * NO contiene codigo del kernel. Los nombres de las funciones se eligieron para
 * que R-1 siga discriminatingando: "r3_two_calls" se ordena despues de
 * "r3_one_call" y se define despues, de modo que elegir "el ultimo del indice
 * por nombre" en lugar de "el de mayor linea" produce una envolvente distinta.
 */

struct amdgpu_ring {
	int id;
};

struct amdgpu_device {
	struct amdgpu_ring *rings[4];
};

int amdgpu_fence_process(struct amdgpu_ring *ring);	/* solo prototipo: 0 DEFINITION */

/* CASO 1: una sola rama llama. El "else" NO es una llamada. */
int r3_one_call(struct amdgpu_device *adev, int src_id)
{
	struct amdgpu_ring *ring = adev->rings[src_id];

	if (src_id == 224)
		amdgpu_fence_process(ring);
	else
		return 0;
	return 0;
}

/* CASO 2: ambas ramas llaman. Deben contarse 2, no 3. */
int r3_two_calls(struct amdgpu_device *adev, int src_id)
{
	struct amdgpu_ring *ring = adev->rings[src_id];
	struct amdgpu_ring *other = adev->rings[src_id + 1];

	if (src_id == 224)
		amdgpu_fence_process(ring);
	else
		amdgpu_fence_process(other);
	return 0;
}
