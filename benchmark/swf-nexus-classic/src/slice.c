/* SPDX-License-Identifier: GPL-2.0 */
/*
 * slice.c — Vertical slice jugable (ncurses).
 *
 * DEMOSTRACION END-TO-END de las mecánicas RECUPERADAS
 * de "Madness Project Nexus Classic.swf":
 *   - Combate: resolve_attack() RECUPERADO (flujo:
 *     evasion TAC-BAR -> conexion -> headshot ->
 *     mitigacion de armadura -> stun/knockdown/disarm).
 *   - Salud maxima: myHealth OBSERVED = 1031.525
 *     (RXRE-SWF-040).
 *   - Tabla de propiedades recuperadas (RXRE-SWF-040).
 *
 * SEPARACION ARQUITECTURAL (seccion 5 del benchmark):
 *   - Simulacion:  rxre_swf.c (independiente de
 *                  renderizado; testeable via
 *                  tests/test_combat.c).
 *   - Input:       slice_input()      -- aqui.
 *   - Colision:    in_range()         -- aqui (2D).
 *   - Rendering:   slice_render()     -- aqui (ncurses).
 *   - Timing:      frame counter      -- aqui.
 *   - Plataforma:  ncurses init/end   -- aqui.
 *
 * APROXIMACIONES (cada una referencia su claim abierto):
 *   - Movimiento:        APPROXIMATION (RXRE-SWF-039:
 *                        el flujo de movimiento del
 *                        original no esta recuperado).
 *   - Colision:          APPROXIMATION (RXRE-SWF-039).
 *   - IA enemiga:        APPROXIMATION (RXRE-SWF-039:
 *                        un solo comportamiento:
 *                        acercarse y atacar).
 *   - Renderizado:       APPROXIMATION (RXRE-SWF-039).
 *   - Valores de dano:   PLACEHOLDER (RXRE-SWF-015:
 *                        la formula exacta no esta
 *                        recuperada; se usa base * un
 *                        multiplicador myDamage OBSERVED).
 *
 * No hay audio (no recuperado; fuera del slice).
 */
#define _DEFAULT_SOURCE   /* usleep() bajo -std=c99 */
#include "rxre_swf.h"

#include <ncurses.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* ---- Configuracion del slice (APPROXIMATION) ---- */
#define ARENA_W 48
#define ARENA_H 20
#define ATTACK_RANGE 2   /* distancia Manhattan max  */
#define ENEMY_HP 1031    /* myHealth OBSERVED (RXRE-SWF-040) */
#define PLAYER_HP 1031   /* myHealth OBSERVED (RXRE-SWF-040) */
#define DMG_BASE 12      /* PLACEHOLDER (RXRE-SWF-015): base no recuperada */
#define DMG_MULT 2.0625f /* myDamage OBSERVED (RXRE-SWF-040) */
#define ENEMY_DMG 8      /* PLACEHOLDER (RXRE-SWF-015) */

/* ---- Estado del juego (simulacion + plataforma) ---- */
typedef struct {
    character_t player;
    enemy_t     enemy;
    int px, py;          /* posicion jugador (APPROX)  */
    int ex, ey;          /* posicion enemigo (APPROX)  */
    int dash_ready;      /* dash disponible            */
    int frame;           /* timing: contador de frames */
    int over;            /* fin de la partida          */
    int won;             /* victoria                   */
    char msg[96];        /* ultimo evento              */
} game_t;

/* Inicializa el estado. Determinista. */
static void game_init(game_t *g)
{
    memset(g, 0, sizeof(*g));
    character_init(&g->player, CHAR_HANK, WPN_PISTOL,
                   ARMOR_LIGHT);
    g->player.health = PLAYER_HP;   /* myHealth OBSERVED */
    enemy_init(&g->enemy, ENEMY_ZOMBIE_AGENT, ARMOR_NONE);
    g->enemy.health = ENEMY_HP;     /* myHealth OBSERVED */
    g->px = ARENA_W / 4;  g->py = ARENA_H / 2;
    g->ex = 3 * ARENA_W / 4; g->ey = ARENA_H / 2;
    g->dash_ready = 1;
    strcpy(g->msg, "flechas=mover espacio=dash enter=atacar");
}

/* ---- Input (plataforma: ncurses) ---- */
/* Devuelve el caracter pulsado o 0 si no hay input. */
static int slice_input(void)
{
    int ch = getch();          /* no-bloqueante (nodelay) */
    return ch;
}

/* ---- Colision / rango (APPROXIMATION, RXRE-SWF-039) ---- */
static int in_range(int x0, int y0, int x1, int y1)
{
    int dx = x0 - x1; if (dx < 0) dx = -dx;
    int dy = y0 - y1; if (dy < 0) dy = -dy;
    return (dx + dy) <= ATTACK_RANGE;
}

/* ---- Actualizacion de la simulacion ---- */
static void game_update(game_t *g, int ch)
{
    int moved = 0;

    /* --- Input -> movimiento (APPROXIMATION) --- */
    switch (ch) {
    case KEY_UP:    if (g->py > 1) { g->py--; moved = 1; } break;
    case KEY_DOWN:  if (g->py < ARENA_H - 2) { g->py++; moved = 1; } break;
    case KEY_LEFT:  if (g->px > 1) { g->px--; moved = 1; } break;
    case KEY_RIGHT: if (g->px < ARENA_W - 2) { g->px++; moved = 1; } break;
    case ' ':       /* dash: 2 celdas + flag para el prox. ataque */
        if (g->dash_ready) {
            /* direccion del dash: hacia el enemigo (APPROX) */
            if (g->ex > g->px && g->px < ARENA_W - 2) g->px++;
            if (g->ex < g->px && g->px > 1) g->px--;
            if (g->ey > g->py && g->py < ARENA_H - 2) g->py++;
            if (g->ey < g->py && g->py > 1) g->py--;
            g->dash_ready = 0;
            moved = 1;
            strcpy(g->msg, "dash! (el proximo ataque puede aturdir)");
        }
        break;
    case '\n': case '\r': case 'j': /* atacar */
        if (in_range(g->px, g->py, g->ex, g->ey)) {
            /* Combate RECUPERADO: resolve_attack().
             * luck determinista (frame % 100) para
             * reproducibilidad; headshot aleatorio
             * determinista; dashing si acabo de dash. */
            int luck = (g->frame * 37) % 100;
            int head = (g->frame % 5 == 0);
            combat_result_t r = resolve_attack(
                &g->player, &g->enemy, luck, head,
                0 /* point-blank */, !g->dash_ready
                /* is_dashing si el dash se consumio */,
                0 /* blocked */);
            if (r.connected) {
                g->enemy.health -= r.damage;
                snprintf(g->msg, sizeof(g->msg),
                         "dano %d%s%s%s%s",
                         r.damage,
                         r.headshot ? " HEADSHOT" : "",
                         r.stun ? " STUN" : "",
                         r.knockdown ? " KNOCKDOWN" : "",
                         r.disarm ? " DISARM" : "");
                if (g->enemy.health <= 0) {
                    g->enemy.health = 0;
                    g->over = 1; g->won = 1;
                    strcpy(g->msg, "enemigo derrotado (R=reiniciar)");
                }
            } else {
                strcpy(g->msg, r.tacbar_hit
                       ? "impacto en TAC-BAR (evasion fallida)"
                       : "el enemigo EVADIO el ataque");
            }
            /* recarga de dash tras atacar (APPROX) */
            g->dash_ready = 1;
        } else {
            strcpy(g->msg, "fuera de rango");
        }
        break;
    case 'r': case 'R':
        game_init(g);
        return;
    case 'q': case 'Q': case 27: /* q o ESC: salir */
        g->over = 1; g->won = 0;
        return;
    default:
        break;
    }
    (void)moved;

    /* --- IA enemiga (APPROXIMATION, RXRE-SWF-039):
     * un solo comportamiento: acercarse al jugador y
     * atacar cuando esta en rango. */
    if (!g->over && g->frame % 2 == 0) {
        if (g->ex > g->px) g->ex--;
        else if (g->ex < g->px) g->ex++;
        if (g->ey > g->py) g->ey--;
        else if (g->ey < g->py) g->ey++;
        if (in_range(g->px, g->py, g->ex, g->ey)
            && g->frame % 8 == 0) {
            /* ataque enemigo simplificado (PLACEHOLDER) */
            g->player.health -= ENEMY_DMG;
            snprintf(g->msg, sizeof(g->msg),
                     "el enemigo te golpea (-%d)", ENEMY_DMG);
            if (g->player.health <= 0) {
                g->player.health = 0;
                g->over = 1; g->won = 0;
                strcpy(g->msg, "derrotado (R=reiniciar)");
            }
        }
    }

    g->frame++;
}

/* ---- Renderizado (APPROXIMATION, RXRE-SWF-039) ---- */
static void slice_render(const game_t *g)
{
    int x, y;

    clear();

    /* Arena */
    for (y = 0; y < ARENA_H; y++) {
        for (x = 0; x < ARENA_W; x++) {
            if (y == 0 || y == ARENA_H - 1 ||
                x == 0 || x == ARENA_W - 1) {
                addch('#');
            } else if (x == g->px && y == g->py) {
                attron(COLOR_PAIR(1)); addch('@'); attroff(COLOR_PAIR(1));
            } else if (x == g->ex && y == g->ey) {
                attron(COLOR_PAIR(2)); addch('E'); attroff(COLOR_PAIR(2));
            } else {
                addch('.');
            }
        }
        addch('\n');
    }

    /* Barras de salud y TAC-BAR */
    mvprintw(ARENA_H + 1, 0,
             "Jugador @  HP %4d/%d  TAC-BAR %3d  arma: %s  armadura: %s",
             g->player.health, PLAYER_HP,
             g->player.tacbar.fullness,
             weapon_class_name(g->player.weapon),
             armor_class_name(g->player.armor));
    mvprintw(ARENA_H + 2, 0,
             "Enemigo  E  HP %4d/%d  TAC-BAR %3d  tipo: %s  %s%s%s",
             g->enemy.health, ENEMY_HP,
             g->enemy.tacbar.fullness,
             enemy_type_name(g->enemy.type),
             g->enemy.stunned ? "STUNNED " : "",
             g->enemy.knocked_down ? "DOWN " : "",
             g->enemy.disarmed ? "DISARMED" : "");
    mvprintw(ARENA_H + 3, 0, "frame %d  %s", g->frame, g->msg);
    mvprintw(ARENA_H + 4, 0,
             "Mecanica de combate: RECUPERADA (resolve_attack). "
             "Movimiento/IA/render: APPROXIMATION (RXRE-SWF-039).");

    refresh();
}

/* ---- Plataforma: init/fin de ncurses ---- */
static void platform_init(void)
{
    initscr();
    cbreak();
    noecho();
    curs_set(0);
    nodelay(stdscr, TRUE);   /* input no-bloqueante */
    keypad(stdscr, TRUE);    /* flechas */
    if (has_colors()) {
        start_color();
        init_pair(1, COLOR_GREEN, COLOR_BLACK);  /* jugador */
        init_pair(2, COLOR_RED, COLOR_BLACK);      /* enemigo */
    }
}

static void platform_end(void)
{
    curs_set(1);
    endwin();
}

/* ---- Bucle principal ---- */
int main(void)
{
    game_t g;

    game_init(&g);
    platform_init();

    while (!g.over) {
        int ch = slice_input();
        game_update(&g, ch);
        slice_render(&g);
        usleep(33000);       /* ~30 fps (FrameRate OBSERVED=30) */
    }

    /* pantalla final */
    slice_render(&g);
    nodelay(stdscr, FALSE);
    mvprintw(ARENA_H + 6, 0,
             "%s  Pulsa cualquier tecla para salir.",
             g.won ? "VICTORIA" : "DERROTA");
    refresh();
    getch();

    platform_end();
    return 0;
}
