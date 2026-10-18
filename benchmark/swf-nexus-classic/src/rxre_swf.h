/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rxre_swf.h — Nucleo de simulacion recuperado de
 * "Madness Project Nexus Classic.swf" (AS2/AVM1).
 *
 * SEPARACION ARQUITECTURAL (seccion 5 del benchmark):
 *   - Este fichero define SOLO estado y simulacion.
 *   - NO hay renderizado, audio ni plataforma aqui.
 *   - La logica de combate es testeable sin render.
 *
 * PROVENIENCIA:
 *   - Los NOMBRES de sistemas, clases de arma, clases de
 *     armadura, perks, personajes y misiones estan RECUPERADOS
 *     del vocabulario AVM1 (raw/avm1-vocab.json).
 *   - Los VALORES NUMERICOS de balance estan PARCIALMENTE
 *     RECUPERADOS (RXRE-SWF-015 = PARTIAL): los valores estan
 *     OBSERVED (extraidos del bytecode via el desensamblador
 *     de la regla de longitud, claims RXRE-SWF-019/020/021/022),
 *     pero la ASIGNACION semantica (que constante es damage,
 *     range, fire-rate) sigue NOT_DETERMINED: requiere el flujo
 *     de control del bytecode, que no se desensambla (tabla de
 *     opcodes incompleta).  Las tablas de candidatos observados
 *     estan en rxre_swf_constants.c.
 *   - Los valores usados por la simulacion que NO tienen asignacion
 *     recuperada llevan el marcador NOT_RECOVERED(RXRE-SWF-015)
 *     y un valor PLACEHOLDER que NO es un dato del original.
 *
 * REFERENCIAS A CLAIMS:
 *   RXRE-SWF-003  AS2/AVM1, no AS3
 *   RXRE-SWF-006  26 clases Madness*, 520 assets
 *   RXRE-SWF-009  shooter tactico: TAC-BAR, armaduras, perks
 *   RXRE-SWF-010  personajes Sanford/Deimos/Hank/Christoff
 *   RXRE-SWF-011  misiones Nexus Stronghold/Armory/Com-Tower
 *   RXRE-SWF-015  constantes: VALORES OBSERVED, mapeo NOT_DETERMINED
 *   RXRE-SWF-019  regla de longitud de accion AVM1
 *   RXRE-SWF-020  Push = opcode 0x96 (no estandar)
 *   RXRE-SWF-021  tipo 9 Push = Const16 (2 bytes)
 *   RXRE-SWF-022  tipo 6 Push != Double (float32+uint32)
 */
#ifndef RXRE_SWF_H
#define RXRE_SWF_H

#include <stddef.h>

/* ---- Clases de arma (RECUPERADO: RXRE-SWF-009) ---- */
typedef enum {
    WPN_NONE = 0,
    WPN_PISTOL,        /* "small, single-handed ranged weapons"   */
    WPN_SMG,           /* "small, two-handed ranged weapons"      */
    WPN_RIFLE,         /* "large, two-handed ranged weapons"      */
    WPN_SHOTGUN,       /* "large, two-handed scatter weapons"       */
    WPN_MELEE,         /* "melee weapons at close range, or thrown" */
    WPN_UNARMED,       /* "one's fists as weapons"                  */
    WPN_THROWN,        /* thrown (Sanford hook: vuelve)             */
    WPN_COUNT
} weapon_class_t;

const char *weapon_class_name(weapon_class_t w);

/* ---- Clases de armadura (RECUPERADO: RXRE-SWF-009) ---- */
typedef enum {
    ARMOR_NONE = 0,
    ARMOR_LIGHT,       /* "light-class armor"  */
    ARMOR_MEDIUM,      /* "medium-class armor" */
    ARMOR_HEAVY,       /* "heavy-class armor"  */
    ARMOR_COUNT
} armor_class_t;

const char *armor_class_name(armor_class_t a);

/*
 * TAC-BAR (RECUPERADO el CONCEPTO: RXRE-SWF-009).
 * "Your TAC-BAR indicates your battle prowess ... Keep it from
 *  hitting empty, and you'll never take a bullet."
 * "Blocking will reduce TAC-BAR damage, while dodging will
 *  outright prevent it."
 *
 * Escala y tasas: NOT_RECOVERED(RXRE-SWF-015).
 */
typedef struct {
    int fullness;          /* PLACEHOLDER 0..100; escala real no recuperada */
    int depletion_per_hit; /* PLACEHOLDER; tasa real no recuperada */
} tacbar_t;

#define TACBAR_FULLNESS_PLACEHOLDER 100 /* NOT_RECOVERED(RXRE-SWF-015) */
#define TACBAR_DEPLETION_PLACEHOLDER 34 /* NOT_RECOVERED(RXRE-SWF-015) */

/* ---- Perks (nombres RECUPERADOS, magnitudes NO: RXRE-SWF-015) ---- */
typedef struct {
    int rifle_tac_damage;     /* "Perk: Rifle Tac Damage"     */
    int smg_tac_damage;       /* "Perk: SMG Tac Damage"       */
    int shotgun_damage;       /* "Perk: Shotgun Damage"       */
    int damage_reduction;     /* "Damage Reduction +"         */
    int melee_unarmed_damage; /* "Melee/Unarmed damage +"     */
    int tacbar_damage;        /* "Tac-Bar damage +"           */
    int carry_second_weapon;  /* "Carry a second weapon"      */
    int doubletime_reload;    /* "Doubletime your shotgun reload" */
    int extra_shotgun_pellet; /* "Each blast ... additional pellet" */
    int three_hit_combo;      /* "three-hit combos ... finisher" */
    int disarm_on_block;      /* "Timed blocking ... disarm"    */
    int deflect_bullets;      /* "Melee weapon will deflect bullets back" */
} perks_t;

/* ---- Personaje (RECUPERADO: RXRE-SWF-010) ---- */
typedef enum {
    CHAR_SANFORD = 0,  /* "Sanford always equips a special hook weapon" */
    CHAR_DEIMOS,
    CHAR_HANK,
    CHAR_CHRISTOFF,    /* Dr. Christoff */
    CHAR_PLAYER,       /* protagonista genérico del modo campaña */
    CHAR_COUNT
} character_id_t;

const char *character_name(character_id_t c);

typedef struct {
    character_id_t id;
    weapon_class_t weapon;
    weapon_class_t second_weapon; /* solo si carry_second_weapon */
    armor_class_t armor;
    int health;        /* NOT_RECOVERED(RXRE-SWF-015): valor real desconocido */
    tacbar_t tacbar;
    perks_t perks;
} character_t;

#define HEALTH_PLACEHOLDER 100 /* NOT_RECOVERED(RXRE-SWF-015) */

/* ---- Enemigo (RECUPERADO: G03LM Mk1, zombie agent) ---- */
typedef enum {
    ENEMY_STANDARD = 0,
    ENEMY_G03LM_MK1,     /* "new G03LM Mk1 units for training at the Nexus Stronghold" */
    ENEMY_ZOMBIE_AGENT,  /* "zombie_agent_classic" */
    ENEMY_COUNT
} enemy_type_t;

const char *enemy_type_name(enemy_type_t e);

typedef struct {
    enemy_type_t type;
    armor_class_t armor;
    int health;
    tacbar_t tacbar;   /* TAC-BAR del defensor (evasion) */
    int stunned;
    int knocked_down;
    int disarmed;
} enemy_t;

/* ---- Resultado de combate ---- */
typedef struct {
    int connected;      /* el ataque conecto (no evadio)        */
    int tacbar_hit;     /* impacto en la TAC-BAR (evasion fallo) */
    int headshot;       /* "Headshots deal increased damage"     */
    int damage;         /* NOT_RECOVERED(RXRE-SWF-015)           */
    int stun;           /* "dash attacks stun opponents"         */
    int knockdown;      /* "knocking down enemies"               */
    int disarm;         /* "disarm their weapon"                 */
    int deflected;      /* "deflect bullets back at opponents"   */
} combat_result_t;

/*
 * Resuelve un ataque.  Flujo RECUPERADO de las descripciones:
 *   1. Determinar si el ataque conecta vs. la TAC-BAR (evasion).
 *   2. Si conecta: aplicar modificadores (headshot, perk de clase).
 *   3. Aplicar mitigacion de armadura.
 *   4. Determinar stun/knockdown/disarm.
 *
 * deterministic: mismos inputs -> mismo output (para tests).
 * La semantica de "conecta vs evadia" usa un valor de suerte
 * pasado por el llamador para que sea determinista y testeable.
 */
combat_result_t resolve_attack(const character_t *att,
                               enemy_t *def,
                               int luck_0_99,
                               int is_headshot,
                               int is_point_blank,
                               int is_dashing,
                               int is_blocked);

/* Inicializa un personaje con perks neutros y TAC-BAR llena. */
void character_init(character_t *c, character_id_t id,
                    weapon_class_t wpn, armor_class_t armor);

/* Inicializa un enemigo. */
void enemy_init(enemy_t *e, enemy_type_t t, armor_class_t armor);

/* Escena / mision (RECUPERADO: RXRE-SWF-007, RXRE-SWF-011). */
typedef enum {
    SCENE_PRELOADER = 0,  /* etiqueta "preoader" (sic) */
    SCENE_SOUND,          /* etiqueta "sound"          */
    SCENE_MENU,           /* etiqueta "menu"           */
    SCENE_GAMESCREEN,     /* etiqueta "gameScreen"     */
    SCENE_COUNT
} scene_t;

typedef enum {
    MISSION_NEXUS_STRONGHOLD = 0,
    MISSION_ARMORY,
    MISSION_RECON_HUT_COMTOWER,
    MISSION_BARRACKS,
    MISSION_COMMUNICATION_TOWER,
    MISSION_COUNT
} mission_t;

const char *mission_name(mission_t m);

/* ---- Constantes numericas OBSERVED (RXRE-SWF-015 PARTIAL) ----
 * Tablas de candidatos recuperados del bytecode AVM1
 * (claims RXRE-SWF-019/020/021/022).  Los VALORES estan
 * OBSERVED; la ASIGNACION a mecanica es NOT_DETERMINED
 * (requiere flujo de control).  Ver rxre_swf_constants.c. */

/* Multiplicadores float32 observados en rango de combate [1.0,2.5].
 * Tipo 6 de Push = (float32_LE, uint32_LE); el float32 es el
 * multiplicador.  NO es un dato asignado a una mecanica. */
extern const float rxre_observed_multipliers[];
extern const int   rxre_observed_multipliers_count;

/* Pares (multiplicador, fraccion 0.32) observados.  La fraccion
 * {0.0,0.2,0.4,0.6,0.8} es el segundo uint32 del tipo 6,
 * interpretado como fraccion fija 0.32; uso NOT_DETERMINED. */
typedef struct { float mult; float frac; int count; } rxre_pair_t;
extern const rxre_pair_t rxre_observed_pairs[];
extern const int         rxre_observed_pairs_count;

/* Constantes enteras observadas (distintas, ordenadas por valor).
 * Candidatos a damage base, rango, fire-rate, tasas de TAC-BAR,
 * % mitigacion, etc.  Asignacion NOT_DETERMINED(RXRE-SWF-015). */
typedef struct { int value; int count; } rxre_int_t;
extern const rxre_int_t rxre_observed_integers[];
extern const int        rxre_observed_integers_count;

/* ---- Propiedades de juego RECUPERADAS (RXRE-SWF-034) ----
 * Nombres de propiedades resueltos via ConstantPool (RXRE-SWF-031)
 * y mapeados a sus multiplicadores float32 observados.
 *
 * PROVENIENCIA: el NOMBRE de cada propiedad esta RECUPERADO
 * (resuelto del pool de 908 entradas, RXRE-SWF-031); el
 * CONJUNTO de multiplicadores float32 aplicados a cada propiedad
 * esta OBSERVED (extraido de los patrones SetMember(0x4F) y
 * read-modify-write GetMember(0x4E)->Multiply(0x0C)->SetMember(0x4F),
 * RXRE-SWF-028/029).
 *
 * LIMITACION (RXRE-SWF-039): la FORMULA exacta (valor base, orden
 * de operaciones, efecto del uint32 del tipo 6, flujo de control
 * de tick/createWound) sigue NOT_DETERMINED: requiere la simulacion
 * de pila con flujo de control completo.  Estos datos son el
 * mapeo propiedad<-multiplicador, NO la implementacion del original.
 *
 * is_rmw: 1 = read-modify-write (prop *= mult), 0 = asignacion
 * directa (prop = mult). */
typedef struct {
    const char *name;     /* nombre de propiedad RECUPERADO */
    float mult_min;       /* multiplicador float32 minimo OBSERVED */
    float mult_max;       /* multiplicador float32 maximo OBSERVED */
    int   mult_count;     /* # de valores distintos observados */
    int   is_rmw;         /* 1 = *=, 0 = = */
} rxre_property_t;
extern const rxre_property_t rxre_recovered_properties[];
extern const int             rxre_recovered_properties_count;

/* Busca una propiedad recuperada por nombre.
 * Devuelve NULL si no esta (no hace crash). */
const rxre_property_t *rxre_property_find(const char *name);

/* ---- Formulas de combate recuperadas (RXRE-SWF-049/050) ----
 *
 * RECUPERADAS del stream principal AVM1 por el ejecutor
 * simbolico (tools/avm1_sym.py).  PROVEN:
 *   - RXRE-SWF-049: estadistica->modificador, movimiento,
 *     escalado de danio, fuentes de armadura.  Resueltas
 *     por pool (ConstantPool) + balance de pila.
 *   - RXRE-SWF-050: APLICACION de danio.  Confirmada por
 *     traza de bytecode (script 1627, acc 31869-31884) +
 *     pool + balance de pila neto 0.
 *
 * LIMITACION: la MITIGACION de armadura (como myArmor
 * reduce el danio entrante) NO se recupera — esta en la
 * rutina nativa inDamage/inArmor (token 2B, RXRE-SWF-048).
 * El danio de ARMA (vs desarmado) usa la misma resta
 * target.health-=damage con una variable de danio cuyo
 * computo completo (con mitigacion) es NOT_RECOVERED. */

/* Estadisticas de personaje (nombres RECUPERADOS del pool). */
typedef struct {
    int statSTR;    /* fuerza   -> modDmg       */
    int statDEX;    /* destreza -> modSpeed     */
    int statTAC;    /* tactica  -> modRecharge  */
    int statEND;    /* resist.  -> modArmor     */
    int statLEAD;   /* lider    -> modAllySmart */
    int statAWR;    /* alerta   -> modHurtTact  */
} stats_t;

/* Estadistica -> modificador (RXRE-SWF-049, PROVEN).
 * modDmg=statSTR/15, modArmor=statEND/15,
 * modSpeed=statDEX/45, modRecharge=statTAC/10,
 * modAllySmart=statLEAD/15, modHurtTactics=statAWR/50. */
float rxre_mod_dmg(const stats_t *s);
float rxre_mod_armor(const stats_t *s);
float rxre_mod_speed(const stats_t *s);
float rxre_mod_recharge(const stats_t *s);
float rxre_mod_ally_smart(const stats_t *s);
float rxre_mod_hurt_tactics(const stats_t *s);

/* Aplicacion de danio (RXRE-SWF-050, PROVEN):
 *   target.myHealth = target.myHealth
 *                   - (myDataRef.myUnarmed.myDamage / 4)
 * El objetivo pierde salud = danio desarmado / 4.
 * Devuelve la nueva salud (min 0). */
int rxre_apply_unarmed(int target_health,
                       float unarmed_myDamage);

/* Aplicacion de danio generica (patron PROVEN RXRE-SWF-050:
 * target.health -= damage).  El VALOR de damage para armas
 * es NOT_RECOVERED (rutina nativa); el patron de resta
 * esta PROVEN. */
int rxre_apply_damage(int target_health, float damage);

/* Rebobinado: recoilTimer = weapon.myDamage * weapon.myShots
 * (RXRE-SWF-049/050, PROVEN). */
float rxre_recoil(float weapon_myDamage, int weapon_myShots);

/* Puntos de habilidad: skillPoints = myLevel * 3
 * (RXRE-SWF-049/050, PROVEN). */
int rxre_skill_points(int myLevel);

/* Salud al renacer: myHealth = myHealthMax / 2
 * (RXRE-SWF-049/050, PROVEN). */
int rxre_respawn_health(int myHealthMax);

/* Posicion Y de la barra de salud objetivo:
 * targetHealthY = 5 * (myHealth / myHealthMax)
 * (RXRE-SWF-049/050, PROVEN). */
float rxre_target_health_y(int myHealth, int myHealthMax);

/* Movimiento: myAccel = mySpeed / 4 (RXRE-SWF-049, PROVEN).
 * Tambien mySpeedRight = (intendedX - _x) / 6. */
float rxre_accel(float mySpeed);
float rxre_speed_right(float intended_x, float cur_x);

/* Escalado de danio (RXRE-SWF-049, PROVEN): myDamage *= 3
 * (powerup) y myDamage = myDamage / 2 (mitad). */
float rxre_damage_triple(float myDamage);
float rxre_damage_halve(float myDamage);

/* Fuente de armadura (RXRE-SWF-049, PROVEN):
 *   myHeadArmor = myHat.myArmor  (tambien myMask, myMouth)
 *   myBodyArmor = myShirt.myArmor
 * El valor de myArmor de cada pieza es el multiplicador
 * float32 observado (RXRE-SWF-040).  La COMBINACION exacta
 * (suma vs otra) NO se recupera completamente. */

/* Estimador de daño por impacto.
 *
 * damage = Math.floor(
 *     SwainMath.randomNumber(2, -2, totalFrameDamage) / 4)
 *
 *   SwainMath.randomNumber(precision, lo, hi) ->
 *   valor en [lo, hi] redondeado a `precision`
 *   decimales (RXRE-SWF-052, PROVEN: 418 sitios).
 *   Rango = [-2, totalFrameDamage] -> /4 -> [-1, TFD/4]
 *   -> tras clamp de salud: [0, totalFrameDamage/4].
 *
 * NOTA: se usa floor (no round) porque el codigo
 * recuperado es SwainMath.randomNumber(...)/4 con
 * Math.floor() envolviendo el resultado (acc 14279).
 * random_val debe estar en [-2, totalFrameDamage].
 */
float rxre_damage_estimate(float total_frame_damage,
                           float random_val);

/* Multiplicador de crítico de headshot.
 *
 * r18 = SwainMath.randomNumber(2, 120, 200) / 100
 *     = [1.20, 2.00]  (120% - 200% del daño)
 *
 * Gated por perkHeadshotCrits
 * (myDataRef.havePerk(perkHeadshotCrits, 2,
 *  MadnessDataFile)). Para amSpecial && myCat==melee:
 * r18 = 1 (sin crítico).
 *
 * random_120_200 debe estar en [120, 200].
 */
float rxre_headshot_crit_mult(float random_120_200);

/* ¿Aplica el crítico de headshot?
 * 1 = sí (perkHeadshotCrits y no es melee-especial),
 * 0 = no. */
int rxre_headshot_crit_applies(int has_perk_headshot_crits,
                               int am_special,
                               int my_cat_is_melee);

/* Durabilidad de arma: myGun.myHealth -= 2 por disparo
 * (RXRE-SWF-049/050, PROVEN). */
int rxre_gun_shot(int gun_health);

#endif /* RXRE_SWF_H */
