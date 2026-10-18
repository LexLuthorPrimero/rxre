/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rxre_swf.c — Implementacion de la simulacion recuperada.
 *
 * REGLA DE PROVENIENCIA:
 *   - Logica de flujo (orden de operaciones de combate) y
 *     nombres de sistema: RECUPERADOS del vocabulario AVM1.
 *   - Valores numericos: PLACEHOLDER marcados
 *     NOT_RECOVERED(RXRE-SWF-015).  NO son datos del original.
 *   - La formula de evasion de la TAC-BAR es un MODELO DERIVADO
 *     de las descripciones recuperadas, no la semantica exacta
 *     del original (que esta en el bytecode no desensamblado).
 */
#include "rxre_swf.h"

#include <string.h>

/* ---- Placeholders de balance: NOT_RECOVERED(RXRE-SWF-015) ---- */
#define DAMAGE_BASE_PLACEHOLDER        10  /* NOT_RECOVERED(RXRE-SWF-015) */
#define HEADSHOT_MULT_PLACEHOLDER     2   /* NOT_RECOVERED(RXRE-SWF-015) */
#define POINTBLANK_MULT_PLACEHOLDER   2   /* NOT_RECOVERED(RXRE-SWF-015) */
#define STUN_CHANCE_PLACEHOLDER      25  /* NOT_RECOVERED(RXRE-SWF-015) */
#define KNOCKDOWN_CHANCE_PLACEHOLDER 15  /* NOT_RECOVERED(RXRE-SWF-015) */
#define DISARM_CHANCE_PLACEHOLDER     10  /* NOT_RECOVERED(RXRE-SWF-015) */

/* Mitigacion de armadura por clase: NOT_RECOVERED(RXRE-SWF-015).
 * "Close-range attacks ignore the enemy's medium or light armor."
 * -> melee/corto ignora light/medium; esto es un modelo del
 *    enunciado recuperado, con magnitudes no recuperadas.      */
static int armor_mitigation_pct(armor_class_t a, int close_range)
{
    /* PLACEHOLDER — porcentaje real no recuperado (RXRE-SWF-015) */
    if (close_range) {
        switch (a) {
        case ARMOR_LIGHT:
        case ARMOR_MEDIUM:
            return 0;   /* ignora light/medium a corta distancia */
        case ARMOR_HEAVY:
            return 25;  /* NOT_RECOVERED(RXRE-SWF-015) */
        case ARMOR_NONE:
        default:
            return 0;
        }
    }
    switch (a) {
    case ARMOR_LIGHT:  return 10;  /* NOT_RECOVERED(RXRE-SWF-015) */
    case ARMOR_MEDIUM: return 20;  /* NOT_RECOVERED(RXRE-SWF-015) */
    case ARMOR_HEAVY:  return 35;  /* NOT_RECOVERED(RXRE-SWF-015) */
    case ARMOR_NONE:
    default:           return 0;
    }
}

const char *weapon_class_name(weapon_class_t w)
{
    static const char *n[] = {
        "none", "pistol", "smg", "rifle", "shotgun",
        "melee", "unarmed", "thrown"
    };
    return (w >= 0 && w < WPN_COUNT) ? n[w] : "?";
}

const char *armor_class_name(armor_class_t a)
{
    static const char *n[] = { "none", "light", "medium", "heavy" };
    return (a >= 0 && a < ARMOR_COUNT) ? n[a] : "?";
}

const char *character_name(character_id_t c)
{
    static const char *n[] = {
        "Sanford", "Deimos", "Hank", "Dr. Christoff", "Player"
    };
    return (c >= 0 && c < CHAR_COUNT) ? n[c] : "?";
}

const char *enemy_type_name(enemy_type_t e)
{
    static const char *n[] = {
        "standard", "G03LM_Mk1", "zombie_agent"
    };
    return (e >= 0 && e < ENEMY_COUNT) ? n[e] : "?";
}

const char *mission_name(mission_t m)
{
    static const char *n[] = {
        "Nexus Stronghold", "Armory", "Recon Hut / Com-Tower",
        "Barracks", "Communication Tower"
    };
    return (m >= 0 && m < MISSION_COUNT) ? n[m] : "?";
}

void character_init(character_t *c, character_id_t id,
                    weapon_class_t wpn, armor_class_t armor)
{
    memset(c, 0, sizeof(*c));
    c->id = id;
    c->weapon = wpn;
    c->second_weapon = WPN_NONE;
    c->armor = armor;
    c->health = HEALTH_PLACEHOLDER;   /* NOT_RECOVERED(RXRE-SWF-015) */
    c->tacbar.fullness = TACBAR_FULLNESS_PLACEHOLDER;
    c->tacbar.depletion_per_hit = TACBAR_DEPLETION_PLACEHOLDER;
    /* perks a cero: magnitudes no recuperadas (RXRE-SWF-015) */
}

void enemy_init(enemy_t *e, enemy_type_t t, armor_class_t armor)
{
    memset(e, 0, sizeof(*e));
    e->type = t;
    e->armor = armor;
    e->health = HEALTH_PLACEHOLDER;   /* NOT_RECOVERED(RXRE-SWF-015) */
    e->tacbar.fullness = TACBAR_FULLNESS_PLACEHOLDER;
    e->tacbar.depletion_per_hit = TACBAR_DEPLETION_PLACEHOLDER;
}

combat_result_t resolve_attack(const character_t *att,
                               enemy_t *def,
                               int luck_0_99,
                               int is_headshot,
                               int is_point_blank,
                               int is_dashing,
                               int is_blocked)
{
    combat_result_t r;
    memset(&r, 0, sizeof(r));

    /* --- 1. Evasion vs TAC-BAR -------------------------------------
     * MODELO DERIVADO (no semantica exacta recuperada):
     * la "plenitud" de la TAC-BAR actua como % de evasion.
     * "Keep it from hitting empty, and you'll never take a bullet."
     * "Blocking will reduce TAC-BAR damage, while dodging will
     *  outright prevent it."
     * => la evasion depende SOLO de la plenitud; el bloqueo
     *    NO evada, sino que reduce el agotamiento.       */
    int evasion = def->tacbar.fullness;        /* PLACEHOLDER formula */
    if (evasion > 100) evasion = 100;

    if (luck_0_99 < evasion) {
        /* el ataque impacta la TAC-BAR (evadido) */
        r.tacbar_hit = 1;
        r.connected = 0;
        int dep = def->tacbar.depletion_per_hit;
        if (is_blocked) dep = dep / 2;         /* bloqueo: mitad */
        def->tacbar.fullness -= dep;
        if (def->tacbar.fullness < 0)
            def->tacbar.fullness = 0;
        return r;
    }

    /* --- 2. El ataque conecta -------------------------------------- */
    r.connected = 1;
    r.headshot = is_headshot;

    /* --- 3. Dano base (NOT_RECOVERED RXRE-SWF-015) --------------- */
    int base = DAMAGE_BASE_PLACEHOLDER;

    /* --- 4. Modificadores recuperados (magnitudes no recuperadas) -- */
    if (is_headshot)
        base *= HEADSHOT_MULT_PLACEHOLDER;     /* NOT_RECOVERED(RXRE-SWF-015) */
    if (is_point_blank && att->weapon == WPN_SHOTGUN)
        base *= POINTBLANK_MULT_PLACEHOLDER;   /* NOT_RECOVERED(RXRE-SWF-015) */

    /* perks por clase de arma (nombres recuperados, suma no recuperada) */
    switch (att->weapon) {
    case WPN_RIFLE:
        base += att->perks.rifle_tac_damage;   /* "Perk: Rifle Tac Damage" */
        break;
    case WPN_SMG:
        base += att->perks.smg_tac_damage;     /* "Perk: SMG Tac Damage"   */
        break;
    case WPN_SHOTGUN:
        base += att->perks.shotgun_damage;     /* "Perk: Shotgun Damage"   */
        if (att->perks.extra_shotgun_pellet)
            base += DAMAGE_BASE_PLACEHOLDER;    /* pellet extra (magnitud no recuperada) */
        break;
    case WPN_MELEE:
    case WPN_UNARMED:
        base += att->perks.melee_unarmed_damage; /* "Melee/Unarmed damage +" */
        break;
    default:
        break;
    }

    /* --- 5. Mitigacion de armadura (MODELO derivado) -------------- */
    int close_range = (att->weapon == WPN_MELEE ||
                       att->weapon == WPN_UNARMED ||
                       is_point_blank);
    int mit = armor_mitigation_pct(def->armor, close_range);
    int damage = base * (100 - mit) / 100;

    /* perk de reduccion global de dano (magnitud no recuperada) */
    damage = damage * (100 - att->perks.damage_reduction) / 100;
    if (damage < 0) damage = 0;
    r.damage = damage;                         /* NOT_RECOVERED(RXRE-SWF-015) */

    /* --- 6. Stun / knockdown / disarm / deflect ------------------- */
    if (is_dashing && luck_0_99 < STUN_CHANCE_PLACEHOLDER) {
        r.stun = 1;                            /* "dash attacks stun" */
        def->stunned = 1;
    }
    if (luck_0_99 < KNOCKDOWN_CHANCE_PLACEHOLDER) {
        r.knockdown = 1;                       /* "knocking down enemies" */
        def->knocked_down = 1;
    }
    if (is_blocked && att->perks.disarm_on_block &&
        (att->weapon == WPN_MELEE ||
         att->weapon == WPN_UNARMED) &&
        luck_0_99 < DISARM_CHANCE_PLACEHOLDER) {
        r.disarm = 1;                          /* "disarm their weapon" */
        def->disarmed = 1;
    }
    if (att->perks.deflect_bullets && att->weapon == WPN_MELEE) {
        r.deflected = 1;                       /* "deflect bullets back" */
    }

    /* --- 7. Aplicar dano a la salud ------------------------------- */
    def->health -= damage;

    return r;
}

/* Busca una propiedad recuperada por nombre (RXRE-SWF-034).
 * Busqueda lineal: el conjunto es pequeno (32) y es
 * tabla de datos OBSERVED, no hot path. */
const rxre_property_t *rxre_property_find(const char *name)
{
    int i;
    if (name == NULL) {
        return NULL;
    }
    for (i = 0; i < rxre_recovered_properties_count; i++) {
        if (strcmp(rxre_recovered_properties[i].name, name) == 0) {
            return &rxre_recovered_properties[i];
        }
    }
    return NULL;
}

/* ---- Formulas de combate recuperadas (RXRE-SWF-049/050) ----
 * PROVEN: recuperadas del stream principal AVM1 por el
 * ejecutor simbolico (tools/avm1_sym.py).  RXRE-SWF-049
 * (estadistica->modificador, movimiento, escalado, fuentes
 * de armadura) y RXRE-SWF-050 (aplicacion de danio,
 * confirmada por traza de bytecode + pool + balance neto 0).
 *
 * La MITIGACION de armadura (como myArmor reduce el danio)
 * NO se recupera: esta en la rutina nativa inDamage/inArmor
 * (token 2B, RXRE-SWF-048). */

/* Estadistica -> modificador (RXRE-SWF-049, PROVEN).
 * modDmg=statSTR/15, modArmor=statEND/15,
 * modSpeed=statDEX/45, modRecharge=statTAC/10,
 * modAllySmart=statLEAD/15, modHurtTactics=statAWR/50. */
float rxre_mod_dmg(const stats_t *s)
{
    return (s ? (float)s->statSTR / 15.0f : 0.0f);
}

float rxre_mod_armor(const stats_t *s)
{
    return (s ? (float)s->statEND / 15.0f : 0.0f);
}

float rxre_mod_speed(const stats_t *s)
{
    return (s ? (float)s->statDEX / 45.0f : 0.0f);
}

float rxre_mod_recharge(const stats_t *s)
{
    return (s ? (float)s->statTAC / 10.0f : 0.0f);
}

float rxre_mod_ally_smart(const stats_t *s)
{
    return (s ? (float)s->statLEAD / 15.0f : 0.0f);
}

float rxre_mod_hurt_tactics(const stats_t *s)
{
    return (s ? (float)s->statAWR / 50.0f : 0.0f);
}

/* Aplicacion de danio generica (RXRE-SWF-050, PROVEN el
 * patron target.health -= damage). */
int rxre_apply_damage(int target_health, float damage)
{
    int nh = (int)(target_health - damage);
    return (nh < 0) ? 0 : nh;
}

/* Aplicacion de danio desarmado (RXRE-SWF-050, PROVEN):
 * target.myHealth -= myDataRef.myUnarmed.myDamage / 4. */
int rxre_apply_unarmed(int target_health,
                       float unarmed_myDamage)
{
    return rxre_apply_damage(target_health,
                             unarmed_myDamage / 4.0f);
}

/* Rebobinado (RXRE-SWF-049/050, PROVEN):
 * recoilTimer = weapon.myDamage * weapon.myShots. */
float rxre_recoil(float weapon_myDamage, int weapon_myShots)
{
    return weapon_myDamage * (float)weapon_myShots;
}

/* Puntos de habilidad (RXRE-SWF-049/050, PROVEN):
 * skillPoints = myLevel * 3. */
int rxre_skill_points(int myLevel)
{
    return myLevel * 3;
}

/* Salud al renacer (RXRE-SWF-049/050, PROVEN):
 * myHealth = myHealthMax / 2. */
int rxre_respawn_health(int myHealthMax)
{
    return myHealthMax / 2;
}

/* Posicion Y de la barra de salud (RXRE-SWF-049/050, PROVEN):
 * targetHealthY = 5 * (myHealth / myHealthMax). */
float rxre_target_health_y(int myHealth, int myHealthMax)
{
    if (myHealthMax <= 0) {
        return 0.0f;
    }
    return 5.0f * ((float)myHealth / (float)myHealthMax);
}

/* Movimiento (RXRE-SWF-049, PROVEN):
 * myAccel = mySpeed / 4;  mySpeedRight = (intendedX-_x)/6. */
float rxre_accel(float mySpeed)
{
    return mySpeed / 4.0f;
}

float rxre_speed_right(float intended_x, float cur_x)
{
    return (intended_x - cur_x) / 6.0f;
}

/* Escalado de danio (RXRE-SWF-049, PROVEN):
 * myDamage *= 3 (powerup);  myDamage = myDamage / 2. */
float rxre_damage_triple(float myDamage)
{
    return myDamage * 3.0f;
}

float rxre_damage_halve(float myDamage)
{
    return myDamage / 2.0f;
}

/* Durabilidad de arma (RXRE-SWF-049/050, PROVEN):
 * myGun.myHealth -= 2 por disparo. */
int rxre_gun_shot(int gun_health)
{
    int nh = gun_health - 2;
    return (nh < 0) ? 0 : nh;
}

/* ---- Aleatorizacion del danio y critico de headshot
 *       (RXRE-SWF-051/052) ----
 *
 * CONVENCION (RXRE-SWF-052, PROVEN): los argumentos
 * se empujan en orden INVERSO (AVM1), asi que
 * Push[R3,-2,2,SwainMath] DECLARA
 *   SwainMath.randomNumber(2, -2, R3)
 * y NO randomNumber(R3,-2,2).  El rango es
 * [lo, hi] = [-2, R3].
 *
 * damage = Math.floor(
 *     SwainMath.randomNumber(2, -2, TFD) / 4)
 */
float rxre_damage_estimate(float total_frame_damage,
                           float random_val)
{
    float r = random_val;
    /* SwainMath.randomNumber(2,-2,TFD) devuelve un
     * valor en [-2, TFD]; acotamos la entrada del
     * llamador a ese rango (faithful al contrato). */
    if (r > total_frame_damage) {
        r = total_frame_damage;
    }
    if (r < -2.0f) {
        r = -2.0f;
    }
    /* /4 y Math.floor().  El cast a int trunca
     * hacia cero, no hacia -inf; para replicar
     * floor() correctamente hay que hacer el
     * floor explicito sobre el float. */
    {
        float q = r / 4.0f;
        float f = (float)(int)q;
        /* si q es negativo y no entero, floor es
         * una unidad mas abajo que el cast */
        if (q < 0.0f && q != f) {
            f -= 1.0f;
        }
        return f;
    }
}

/* r18 = SwainMath.randomNumber(2,120,200)/100
 *     = [1.20, 2.00]  (120% - 200%). */
float rxre_headshot_crit_mult(float random_120_200)
{
    return random_120_200 / 100.0f;
}

/* ¿Aplica el critico?  Gated por perkHeadshotCrits;
 * r18=1 para amSpecial && myCat==melee. */
int rxre_headshot_crit_applies(int has_perk_headshot_crits,
                               int am_special,
                               int my_cat_is_melee)
{
    if (!has_perk_headshot_crits) {
        return 0;
    }
    /* amSpecial && melee -> r18 = 1 (sin critico) */
    if (am_special && my_cat_is_melee) {
        return 0;
    }
    return 1;
}
