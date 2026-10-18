/* SPDX-License-Identifier: GPL-2.0 */
/*
 * test_combat.c — Tests unitarios de la logica recuperada.
 *
 * Verifican el FLUJO de combate (evasion, conexion,
 * mitigacion, stun), no el balance numerico (los
 * valores son PLACEHOLDER, RXRE-SWF-015).
 *
 * Contract (seccion 73 del AGENTS): mismos inputs ->
 * mismos outputs; determinismo verificable.
 */
#include "rxre_swf.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg) do {                        \
        checks++;                                     \
        if (!(cond)) {                               \
            failures++;                              \
            printf("  FAIL: %s\n", msg);           \
        }                                            \
    } while (0)

int main(void)
{
    character_t att;
    enemy_t def;
    combat_result_t r;

    printf("test: TAC-BAR llena evita (luck<fullness)\n");
    character_init(&att, CHAR_PLAYER, WPN_PISTOL, ARMOR_NONE);
    enemy_init(&def, ENEMY_STANDARD, ARMOR_NONE);
    def.tacbar.fullness = 100;
    r = resolve_attack(&att, &def, 10, 0, 0, 0, 0);
    CHECK(r.tacbar_hit == 1, "debe impactar la TAC-BAR");
    CHECK(r.connected == 0, "no debe conectar");
    CHECK(r.damage == 0, "sin dano a la salud");
    CHECK(def.tacbar.fullness ==
          100 - TACBAR_DEPLETION_PLACEHOLDER,
          "agota la TAC-BAR");

    printf("test: TAC-BAR vacia siempre conecta\n");
    enemy_init(&def, ENEMY_STANDARD, ARMOR_NONE);
    def.tacbar.fullness = 0;
    r = resolve_attack(&att, &def, 99, 0, 0, 0, 0);
    CHECK(r.connected == 1, "debe conectar");
    CHECK(r.tacbar_hit == 0, "no impacta la TAC-BAR");
    CHECK(r.damage > 0, "inflige dano");

    printf("test: determinismo (mismo input, mismo output)\n");
    enemy_t d1, d2;
    enemy_init(&d1, ENEMY_STANDARD, ARMOR_MEDIUM);
    enemy_init(&d2, ENEMY_STANDARD, ARMOR_MEDIUM);
    d1.tacbar.fullness = 0;
    d2.tacbar.fullness = 0;
    combat_result_t r1 = resolve_attack(&att, &d1, 42, 1, 0, 0, 0);
    combat_result_t r2 = resolve_attack(&att, &d2, 42, 1, 0, 0, 0);
    CHECK(memcmp(&r1, &r2, sizeof(r1)) == 0,
          "resultados identicos");
    CHECK(d1.health == d2.health, "salud identica");

    printf("test: headshot inflige mas que sin headshot\n");
    enemy_t dh, dn;
    enemy_init(&dh, ENEMY_STANDARD, ARMOR_NONE);
    enemy_init(&dn, ENEMY_STANDARD, ARMOR_NONE);
    dh.tacbar.fullness = 0;
    dn.tacbar.fullness = 0;
    combat_result_t rh = resolve_attack(&att, &dh, 99, 1, 0, 0, 0);
    combat_result_t rn = resolve_attack(&att, &dn, 99, 0, 0, 0, 0);
    CHECK(rh.headshot == 1, "headshot marcado");
    CHECK(rh.damage > rn.damage, "headshot > sin headshot");

    printf("test: armadura heavy mitiga mas que light\n");
    enemy_t dl, dha;
    enemy_init(&dl, ENEMY_STANDARD, ARMOR_LIGHT);
    enemy_init(&dha, ENEMY_STANDARD, ARMOR_HEAVY);
    dl.tacbar.fullness = 0;
    dha.tacbar.fullness = 0;
    combat_result_t rl = resolve_attack(&att, &dl, 99, 0, 0, 0, 0);
    combat_result_t rha = resolve_attack(&att, &dha, 99, 0, 0, 0, 0);
    CHECK(rl.damage > rha.damage, "light recibe mas dano que heavy");

    printf("test: melee ignora armadura light y medium\n");
    character_init(&att, CHAR_PLAYER, WPN_MELEE, ARMOR_NONE);
    enemy_t dme, dmd;
    enemy_init(&dme, ENEMY_STANDARD, ARMOR_LIGHT);
    enemy_init(&dmd, ENEMY_STANDARD, ARMOR_MEDIUM);
    dme.tacbar.fullness = 0;
    dmd.tacbar.fullness = 0;
    combat_result_t rme = resolve_attack(&att, &dme, 99, 0, 0, 0, 0);
    combat_result_t rmd = resolve_attack(&att, &dmd, 99, 0, 0, 0, 0);
    CHECK(rme.damage == rmd.damage,
          "melee: light y medium reciben el mismo dano");

    printf("test: bloqueo reduce agotamiento de TAC-BAR\n");
    character_init(&att, CHAR_PLAYER, WPN_PISTOL, ARMOR_NONE);
    enemy_t db1, db2;
    enemy_init(&db1, ENEMY_STANDARD, ARMOR_NONE);
    enemy_init(&db2, ENEMY_STANDARD, ARMOR_NONE);
    db1.tacbar.fullness = 100;
    db2.tacbar.fullness = 100;
    resolve_attack(&att, &db1, 10, 0, 0, 0, 0);  /* sin bloqueo */
    resolve_attack(&att, &db2, 10, 0, 0, 0, 1);  /* con bloqueo */
    CHECK(db2.tacbar.fullness > db1.tacbar.fullness,
          "bloquear agota menos la TAC-BAR");

    printf("test: perk de desarme al bloquear\n");
    character_init(&att, CHAR_PLAYER, WPN_MELEE, ARMOR_NONE);
    att.perks.disarm_on_block = 1;
    enemy_t dd;
    enemy_init(&dd, ENEMY_STANDARD, ARMOR_NONE);
    dd.tacbar.fullness = 0;
    r = resolve_attack(&att, &dd, 5, 0, 0, 0, 1);
    CHECK(r.connected == 1, "conecta (TAC-BAR vacia)");
    CHECK(r.disarm == 1, "desarma");
    CHECK(dd.disarmed == 1, "enemigo desarmado");

    printf("test: dash puede aturdir\n");
    enemy_t ds;
    enemy_init(&ds, ENEMY_G03LM_MK1, ARMOR_HEAVY);
    ds.tacbar.fullness = 0;
    r = resolve_attack(&att, &ds, 10, 0, 0, 1, 0);
    CHECK(r.stun == 1, "dash aturde");
    CHECK(ds.stunned == 1, "enemigo aturdido");

    printf("test: nombres recuperados\n");
    CHECK(strcmp(character_name(CHAR_SANFORD), "Sanford") == 0,
          "Sanford");
    CHECK(strcmp(character_name(CHAR_DEIMOS), "Deimos") == 0,
          "Deimos");
    CHECK(strcmp(character_name(CHAR_HANK), "Hank") == 0, "Hank");
    CHECK(strcmp(character_name(CHAR_CHRISTOFF),
                 "Dr. Christoff") == 0, "Christoff");
    CHECK(strcmp(enemy_type_name(ENEMY_G03LM_MK1),
                 "G03LM_Mk1") == 0, "G03LM_Mk1");
    CHECK(strcmp(enemy_type_name(ENEMY_ZOMBIE_AGENT),
                 "zombie_agent") == 0, "zombie_agent");
    CHECK(strcmp(weapon_class_name(WPN_SHOTGUN),
                 "shotgun") == 0, "shotgun");
    CHECK(strcmp(armor_class_name(ARMOR_HEAVY),
                 "heavy") == 0, "heavy");
    CHECK(strcmp(mission_name(MISSION_NEXUS_STRONGHOLD),
                 "Nexus Stronghold") == 0, "Nexus Stronghold");
    CHECK(strcmp(mission_name(MISSION_ARMORY), "Armory") == 0,
          "Armory");

    /* ---- Tabla de propiedades RECUPERADAS (RXRE-SWF-034/040) ----
     * Verifica que el mapeo propiedad<-multiplicador OBSERVED
     * este presente y sea internamente consistente. */
    printf("test: propiedades recuperadas\n");
    CHECK(rxre_recovered_properties_count == 32,
          "32 propiedades recuperadas");
    /* myDamage: rango de multiplicadores de dano OBSERVED */
    CHECK(rxre_property_find("myDamage") != NULL,
          "myDamage presente");
    const rxre_property_t *dmg = rxre_property_find("myDamage");
    if (dmg) {
        CHECK(dmg->mult_count == 6, "myDamage 6 valores");
        CHECK(dmg->mult_max > 2.5f && dmg->mult_max < 2.6f,
              "myDamage max ~2.515625");
        CHECK(dmg->is_rmw == 0, "myDamage STORE");
    }
    /* myArmor: multiplicadores de armadura OBSERVED */
    const rxre_property_t *arm = rxre_property_find("myArmor");
    CHECK(arm != NULL, "myArmor presente");
    if (arm) {
        CHECK(arm->mult_count == 6, "myArmor 6 valores");
        CHECK(arm->mult_min == 0.0f, "myArmor min 0");
        CHECK(arm->mult_max > 2.57f && arm->mult_max < 2.59f,
              "myArmor max ~2.578125");
    }
    /* myDash: multiplicadores de evasion/dash OBSERVED */
    const rxre_property_t *dash = rxre_property_find("myDash");
    CHECK(dash != NULL, "myDash presente");
    if (dash) {
        CHECK(dash->mult_count == 3, "myDash 3 valores");
        CHECK(dash->mult_min > 1.9f && dash->mult_min < 1.91f,
              "myDash min ~1.90625");
    }
    /* myHealth: salud maxima OBSERVED (no multiplicador) */
    const rxre_property_t *hp = rxre_property_find("myHealth");
    CHECK(hp != NULL, "myHealth presente");
    if (hp) {
        CHECK(hp->mult_max > 1031.0f && hp->mult_max < 1032.0f,
              "myHealth max ~1031.525");
    }
    /* mySpeedRight: tiene RMW (prop *= mult) */
    const rxre_property_t *sr = rxre_property_find("mySpeedRight");
    CHECK(sr != NULL, "mySpeedRight presente");
    if (sr) {
        CHECK(sr->is_rmw == 1, "mySpeedRight tiene RMW");
        CHECK(sr->mult_min < 0.0f, "mySpeedRight tiene negativo");
    }
    /* propiedad inexistente devuelve NULL (no crash) */
    CHECK(rxre_property_find("no_existe_xyz") == NULL,
          "busqueda de propiedad inexistente");

    /* ==== Formulas recuperadas (RXRE-SWF-049/050) ==== */
    printf("test: RXRE-SWF-049 estadistica->modificador\n");
    stats_t st = {30, 90, 40, 30, 30, 100};
    /* modDmg = statSTR/15 = 30/15 = 2.0 */
    CHECK(rxre_mod_dmg(&st) == 2.0f,
          "modDmg = statSTR/15 = 2.0");
    /* modArmor = statEND/15 = 30/15 = 2.0 */
    CHECK(rxre_mod_armor(&st) == 2.0f,
          "modArmor = statEND/15 = 2.0");
    /* modSpeed = statDEX/45 = 90/45 = 2.0 */
    CHECK(rxre_mod_speed(&st) == 2.0f,
          "modSpeed = statDEX/45 = 2.0");
    /* modRecharge = statTAC/10 = 40/10 = 4.0 */
    CHECK(rxre_mod_recharge(&st) == 4.0f,
          "modRecharge = statTAC/10 = 4.0");
    /* modAllySmart = statLEAD/15 = 30/15 = 2.0 */
    CHECK(rxre_mod_ally_smart(&st) == 2.0f,
          "modAllySmart = statLEAD/15 = 2.0");
    /* modHurtTactics = statAWR/50 = 100/50 = 2.0 */
    CHECK(rxre_mod_hurt_tactics(&st) == 2.0f,
          "modHurtTactics = statAWR/50 = 2.0");
    /* stats NULL no hace crash, devuelve 0 */
    CHECK(rxre_mod_dmg(NULL) == 0.0f,
          "modDmg(NULL) = 0 sin crash");

    printf("test: RXRE-SWF-050 aplicacion de danio\n");
    /* unarmed: health=100, unarmed.damage=8 -> 8/4=2 -> 98 */
    CHECK(rxre_apply_unarmed(100, 8.0f) == 98,
          "unarmed: 100 - 8/4 = 98");
    /* unarmed: damage=4 -> 4/4=1 -> 99 */
    CHECK(rxre_apply_unarmed(100, 4.0f) == 99,
          "unarmed: 100 - 4/4 = 99");
    /* aplicacion generica: 100-10=90 */
    CHECK(rxre_apply_damage(100, 10.0f) == 90,
          "apply_damage: 100 - 10 = 90");
    /* clamp a 0 (no negativo) */
    CHECK(rxre_apply_damage(5, 10.0f) == 0,
          "apply_damage clamp a 0");
    CHECK(rxre_apply_unarmed(1, 8.0f) == 0,
          "unarmed clamp a 0");

    printf("test: RXRE-SWF-049/050 recoil, skill, respawn\n");
    /* recoil = weapon.damage * weapon.shots = 2.0*6=12 */
    CHECK(rxre_recoil(2.0f, 6) == 12.0f,
          "recoil = 2.0 * 6 = 12");
    /* skillPoints = level*3 = 5*3=15 */
    CHECK(rxre_skill_points(5) == 15,
          "skillPoints = 5*3 = 15");
    /* respawn = max/2 = 100/2=50 */
    CHECK(rxre_respawn_health(100) == 50,
          "respawn = 100/2 = 50");
    /* targetHealthY = 5*(50/100) = 2.5 */
    CHECK(rxre_target_health_y(50, 100) == 2.5f,
          "targetHealthY = 5*(50/100) = 2.5");
    /* targetHealthY con max=0 no hace crash */
    CHECK(rxre_target_health_y(50, 0) == 0.0f,
          "targetHealthY max=0 -> 0");

    printf("test: RXRE-SWF-049 movimiento y escalado\n");
    /* accel = speed/4 = 8/4=2 */
    CHECK(rxre_accel(8.0f) == 2.0f,
          "accel = 8/4 = 2.0");
    /* speedRight = (intended-cur)/6 = (12-0)/6=2 */
    CHECK(rxre_speed_right(12.0f, 0.0f) == 2.0f,
          "speedRight = (12-0)/6 = 2.0");
    /* damage triple: 2*3=6 */
    CHECK(rxre_damage_triple(2.0f) == 6.0f,
          "damage_triple = 2*3 = 6");
    /* damage halve: 8/2=4 */
    CHECK(rxre_damage_halve(8.0f) == 4.0f,
          "damage_halve = 8/2 = 4");
    /* gun durability: 10-2=8 */
    CHECK(rxre_gun_shot(10) == 8,
          "gun_shot = 10-2 = 8");
    /* gun clamp a 0 */
    CHECK(rxre_gun_shot(1) == 0,
          "gun_shot clamp a 0");

    printf("test: RXRE-SWF-051/052 danio aleatorizado "
           "y critico\n");
    /* damage = Math.floor(random / 4),
     *  random in [-2, TFD] */
    /* TFD=20, random=20 -> 20/4=5 -> floor 5 */
    CHECK(rxre_damage_estimate(20.0f, 20.0f) == 5.0f,
          "damage TFD=20 random=20 -> 5");
    /* TFD=20, random=0 -> 0/4=0 */
    CHECK(rxre_damage_estimate(20.0f, 0.0f) == 0.0f,
          "damage TFD=20 random=0 -> 0");
    /* TFD=20, random=-2 -> -2/4=-0.5 -> floor -1 */
    CHECK(rxre_damage_estimate(20.0f, -2.0f) == -1.0f,
          "damage random=-2 -> floor(-0.5) = -1");
    /* TFD=21, random=21 -> 21/4=5.25 -> floor 5 */
    CHECK(rxre_damage_estimate(21.0f, 21.0f) == 5.0f,
          "damage TFD=21 -> floor(5.25) = 5");
    /* critico de headshot = random(2,120,200)/100 */
    CHECK(rxre_headshot_crit_mult(120.0f) == 1.2f,
          "crit mult 120 -> 1.2 (120%)");
    CHECK(rxre_headshot_crit_mult(200.0f) == 2.0f,
          "crit mult 200 -> 2.0 (200%)");
    CHECK(rxre_headshot_crit_mult(160.0f) == 1.6f,
          "crit mult 160 -> 1.6 (160%)");
    /* el critico requiere el perk */
    CHECK(rxre_headshot_crit_applies(1, 0, 0) == 1,
          "crit aplica con perk");
    CHECK(rxre_headshot_crit_applies(0, 0, 0) == 0,
          "crit NO aplica sin perk");
    /* melee-especial: r18=1 (sin critico) */
    CHECK(rxre_headshot_crit_applies(1, 1, 1) == 0,
          "crit NO aplica en melee-especial");
    CHECK(rxre_headshot_crit_applies(1, 1, 0) == 1,
          "crit aplica en especial no-melee");
    /* pipeline completo: dano aleatorizado x critico
     * damage = floor(random/4) * crit, y se aplica
     * a la salud del objetivo */
    {
        float tfd = 40.0f;
        float rnd = 40.0f;   /* maximo del rango */
        float crit = rxre_headshot_crit_mult(150.0f);
        float dmg = rxre_damage_estimate(tfd, rnd) * crit;
        /* floor(40/4)=10; 10*1.5=15 */
        CHECK(dmg == 15.0f,
              "pipeline: floor(40/4)*1.5 = 15");
        /* salud objetivo 50 -> 35 */
        int nh = rxre_apply_damage(50, dmg);
        CHECK(nh == 35,
              "objetivo 50 - 15 = 35");
    }

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
