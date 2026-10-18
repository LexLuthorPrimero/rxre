/* SPDX-License-Identifier: GPL-2.0 */
/*
 * main.c — Harness de escenarios deterministicos.
 *
 * Prueba la logica recuperada sin renderizado ni audio.
 * Cada escenario imprime el estado para inspeccion.
 * Los valores numericos son PLACEHOLDER (RXRE-SWF-015);
 * lo que se verifica es el FLUJO, no el balance.
 */
#include "rxre_swf.h"

#include <stdio.h>
#include <string.h>

static void print_result(const char *label,
                         const combat_result_t *r)
{
    printf("  %-28s connected=%d tacbar_hit=%d headshot=%d "
           "damage=%d stun=%d knockdown=%d disarm=%d deflected=%d\n",
           label, r->connected, r->tacbar_hit, r->headshot,
           r->damage, r->stun, r->knockdown, r->disarm,
           r->deflected);
}

int main(void)
{
    character_t att;
    enemy_t def;
    combat_result_t r;

    printf("=== Escenario 1: TAC-BAR llena evita el impacto ===\n");
    character_init(&att, CHAR_SANFORD, WPN_RIFLE, ARMOR_NONE);
    enemy_init(&def, ENEMY_STANDARD, ARMOR_NONE);
    def.tacbar.fullness = 100;
    r = resolve_attack(&att, &def, 50, 0, 0, 0, 0);
    print_result("TAC-BAR llena, luck=50", &r);
    printf("  tacbar.fullness tras impacto = %d\n", def.tacbar.fullness);

    printf("\n=== Escenario 2: TAC-BAR vacia siempre conecta ===\n");
    enemy_init(&def, ENEMY_STANDARD, ARMOR_NONE);
    def.tacbar.fullness = 0;
    r = resolve_attack(&att, &def, 99, 0, 0, 0, 0);
    print_result("TAC-BAR vacia, luck=99", &r);
    printf("  enemy.health tras impacto = %d\n", def.health);

    printf("\n=== Escenario 3: headshot duplica dano (placeholder) ===\n");
    enemy_init(&def, ENEMY_STANDARD, ARMOR_NONE);
    def.tacbar.fullness = 0;
    r = resolve_attack(&att, &def, 99, 1, 0, 0, 0);
    print_result("headshot=1", &r);

    printf("\n=== Escenario 4: armadura pesada mitiga mas que ligera ===\n");
    enemy_t def_light, def_heavy;
    enemy_init(&def_light, ENEMY_STANDARD, ARMOR_LIGHT);
    enemy_init(&def_heavy, ENEMY_STANDARD, ARMOR_HEAVY);
    def_light.tacbar.fullness = 0;
    def_heavy.tacbar.fullness = 0;
    combat_result_t rl = resolve_attack(&att, &def_light, 99, 0, 0, 0, 0);
    combat_result_t rh = resolve_attack(&att, &def_heavy, 99, 0, 0, 0, 0);
    print_result("armadura light", &rl);
    print_result("armadura heavy", &rh);
    printf("  (heavy debe mitigar mas: damage_light >= damage_heavy)\n");

    printf("\n=== Escenario 5: melee ignora armadura light/medium ===\n");
    character_init(&att, CHAR_SANFORD, WPN_MELEE, ARMOR_NONE);
    enemy_init(&def_light, ENEMY_STANDARD, ARMOR_LIGHT);
    enemy_init(&def_heavy, ENEMY_STANDARD, ARMOR_MEDIUM);
    def_light.tacbar.fullness = 0;
    def_heavy.tacbar.fullness = 0;
    rl = resolve_attack(&att, &def_light, 99, 0, 0, 0, 0);
    rh = resolve_attack(&att, &def_heavy, 99, 0, 0, 0, 0);
    print_result("melee vs light", &rl);
    print_result("melee vs medium", &rh);
    printf("  (corto ignora light/medium: ambos damage iguales al base)\n");

    printf("\n=== Escenario 6: bloqueo reduce agotamiento de TAC-BAR ===\n");
    character_init(&att, CHAR_SANFORD, WPN_PISTOL, ARMOR_NONE);
    enemy_init(&def, ENEMY_STANDARD, ARMOR_NONE);
    def.tacbar.fullness = 100;
    r = resolve_attack(&att, &def, 50, 0, 0, 0, 1);  /* blocked=1 */
    print_result("bloqueado, luck=50", &r);
    printf("  tacbar.fullness tras bloqueo = %d\n", def.tacbar.fullness);

    printf("\n=== Escenario 7: perk de desarme al bloquear ===\n");
    character_init(&att, CHAR_SANFORD, WPN_MELEE, ARMOR_NONE);
    att.perks.disarm_on_block = 1;
    enemy_init(&def, ENEMY_STANDARD, ARMOR_NONE);
    def.tacbar.fullness = 0;
    r = resolve_attack(&att, &def, 5, 0, 0, 0, 1);
    print_result("bloqueado + disarm perk", &r);
    printf("  enemy.disarmed = %d\n", def.disarmed);

    printf("\n=== Escenario 8: dash aturde ===\n");
    enemy_init(&def, ENEMY_G03LM_MK1, ARMOR_HEAVY);
    def.tacbar.fullness = 0;
    r = resolve_attack(&att, &def, 10, 0, 0, 1, 0);  /* dashing=1 */
    print_result("dash, luck=10", &r);
    printf("  enemy.stunned = %d\n", def.stunned);

    printf("\n=== Escenario 9: personajes y misiones recuperados ===\n");
    for (int i = 0; i < CHAR_COUNT; i++)
        printf("  personaje[%d] = %s\n", i, character_name((character_id_t)i));
    for (int i = 0; i < MISSION_COUNT; i++)
        printf("  mision[%d] = %s\n", i, mission_name((mission_t)i));
    for (int i = 0; i < ENEMY_COUNT; i++)
        printf("  enemigo[%d] = %s\n", i, enemy_type_name((enemy_type_t)i));

    printf("\nNOTA: todos los numeros son PLACEHOLDER "
           "(RXRE-SWF-015). Se verifica el flujo, no el balance.\n");
    return 0;
}
