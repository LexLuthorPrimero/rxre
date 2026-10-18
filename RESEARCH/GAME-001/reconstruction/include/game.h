#ifndef GAME_H
#define GAME_H

#include <stdint.h>
#include <stddef.h>

#define WINDOW_WIDTH 800
#define WINDOW_HEIGHT 600
#define FRAME_RATE 30
#define MAX_SPRITES 2448
#define MAX_SOUNDS 137

// Evidence-based game states from SWF DoAction tag #9779 strings:
// exitAll -> createMainMenu <-> createWorldMap
// createHireStore -> exitHireStore/back
// createItemStore -> exitItemStore/back
// createTeamSetup -> exitTeamSetup/back
// createNewGuy -> exitNewGuy/back
// generateLevel/generateArena - Level creation
// createCharacter/madness_character_creator - Character creator
// newCutscene/madness_cutscene - Cutscenes
// gameSelect/madness_game_select - Main menu
// madness_game_menu -> madness_menu_top_bar - In-game menu
// madness_transition - Scene transitions
typedef enum {
    STATE_EXIT_ALL = 0,           // Initial exit/cleanup state
    STATE_MAIN_MENU = 1,          // createMainMenu, gameSelect/madness_game_select
    STATE_WORLD_MAP = 2,          // createWorldMap
    STATE_HIRE_STORE = 3,         // createHireStore, storeHire
    STATE_ITEM_STORE = 4,         // createItemStore, storeItem
    STATE_TEAM_SETUP = 5,         // createTeamSetup, teamSetup
    STATE_CHARACTER_CREATOR = 6,  // createCharacter, madness_character_creator
    STATE_CUTSCENE = 7,           // newCutscene, madness_cutscene
    STATE_GAMEPLAY = 8,           // Active gameplay (was STATE_PLAYING)
    STATE_PAUSED = 9,             // madness_game_menu, madness_menu_top_bar
    STATE_LEVEL_TRANSITION = 10,  // generateLevel, generateArena
    STATE_TRANSITION = 11,        // madness_transition
    STATE_GAME_OVER = 12          // Death/wipe state
} GameState;

typedef enum {
    INPUT_NONE = 0,
    INPUT_LEFT,
    INPUT_RIGHT,
    INPUT_UP,
    INPUT_DOWN,
    INPUT_JUMP,
    INPUT_ATTACK,
    INPUT_USE,
    INPUT_PAUSE,
    INPUT_QUIT
} InputAction;

typedef struct {
    float x, y;
    float vx, vy;
    float ax, ay;
    float rotation;
    float scale_x, scale_y;
    uint32_t width, height;
    uint32_t sprite_id;
    uint32_t health;
    uint32_t max_health;
    uint32_t damage;
    int32_t direction;
    int32_t state;
    int32_t frame;
    int32_t total_frames;
    float animation_speed;
    int32_t alive;
    int32_t invincible_frames;
} GameObject;

typedef struct {
    uint32_t id;
    uint32_t sound_type;
    uint32_t loop_count;
    float volume;
    int32_t loaded;
} Sound;

typedef struct {
    uint32_t tag_index;
    uint32_t frame_start;
    uint32_t frame_end;
    uint32_t total_frames;
    float fps;
    int32_t loop_enabled;
    float loop_point;
} Animation;

typedef struct {
    uint32_t tag_id;
    uint32_t depth;
    float x, y;
    float rotation;
    float scale_x, scale_y;
    int32_t visible;
    int32_t alpha;
} SpriteInstance;

typedef struct {
    GameState current_state;
    GameState previous_state;
    GameObject player;
    GameObject* enemies;
    GameObject* projectiles;
    Sound* sounds;
    Animation* animations;
    SpriteInstance* sprite_instances;

    uint32_t frame_count;
    uint32_t sprite_count;
    uint32_t sound_count;
    uint32_t max_enemies;
    uint32_t max_projectiles;
    uint32_t score;
    uint32_t lives;
    uint32_t level;

    int32_t keys[256];
    uint32_t input_frame;

    uint32_t game_start_time;
    uint32_t last_frame_time;
    float delta_time;

    int32_t debug_mode;
    int32_t quit_requested;

    // Evidence-based systems from SWF analysis
    uint32_t cash;                    // playerCash from DoAction #9773
    uint32_t earned_xp;               // earnedXP from DoAction #9773
    uint32_t arena_kills;             // arenaKills from DoAction #9773
    uint32_t arena_waves;             // arenaWaves from DoAction #9773
    uint32_t pulse_timer;             // pulseTimer from DoAction #9773
} GameContext;

// Core engine functions
void init_engine(GameContext* ctx);
void cleanup_engine(GameContext* ctx);
void update_input(GameContext* ctx);
void update_game(GameContext* ctx);
void render_frame(GameContext* ctx);
void debug_draw(GameContext* ctx);
void evidence_based_init(GameContext* ctx);
void build_info(void);

// Game object management
void create_player(GameContext* ctx);
void create_enemy(GameContext* ctx, float x, float y);
void create_projectile(GameContext* ctx, float x, float y, float vx, float vy);
void update_objects(GameContext* ctx);
void check_collisions(GameContext* ctx);
void cleanup_objects(GameContext* ctx);

// Resource management
void load_resources(GameContext* ctx);
void unload_resources(GameContext* ctx);

// State management - Evidence-based from SWF DoAction/DoInitAction tags
void enter_state(GameContext* ctx, GameState new_state);
void update_state(GameContext* ctx);
void handle_state_input(GameContext* ctx);
void handle_state_update(GameContext* ctx);
void handle_state_render(GameContext* ctx);

// Audio management - Evidence-based from SwainAudioPlayer strings
void play_sound(GameContext* ctx, uint32_t sound_id);
void stop_sound(GameContext* ctx, uint32_t sound_id);
void update_audio(GameContext* ctx);
void init_audio_system(GameContext* ctx);

// Input management - Evidence-based from KeyManager strings
void handle_key_input(GameContext* ctx, int32_t keycode, int32_t pressed);
void update_key_manager(GameContext* ctx);

// Menu systems - Evidence-based from menu system strings
void create_main_menu(GameContext* ctx);
void exit_main_menu(GameContext* ctx);
void create_world_map(GameContext* ctx);
void exit_world_map(GameContext* ctx);
void create_hire_store(GameContext* ctx);
void exit_hire_store(GameContext* ctx);
void create_item_store(GameContext* ctx);
void exit_item_store(GameContext* ctx);
void create_team_setup(GameContext* ctx);
void exit_team_setup(GameContext* ctx);
void create_character_creator(GameContext* ctx);
void exit_character_creator(GameContext* ctx);
void create_cutscene(GameContext* ctx);
void exit_cutscene(GameContext* ctx);

// Store systems - Evidence-based from store system strings
void store_hire(GameContext* ctx);
void store_item(GameContext* ctx);
void store_team_setup(GameContext* ctx);

// World/Level systems - Evidence-based from world system strings
void generate_level(GameContext* ctx);
void generate_arena(GameContext* ctx);

// Character systems - Evidence-based from character system strings
void create_character(GameContext* ctx);
void madness_character_creator(GameContext* ctx);

// Cutscene systems - Evidence-based from cutscene system strings
void new_cutscene(GameContext* ctx);
void cutscene_done(GameContext* ctx);

// Transition systems - Evidence-based from transition system strings
void madness_transition(GameContext* ctx);
void transition_lock(GameContext* ctx);
void new_transition(GameContext* ctx);

// Save/Load systems - Evidence-based from save system strings
void save_game(GameContext* ctx);
void load_game(GameContext* ctx);

// Newgrounds API systems - Evidence-based from API strings
void unlock_medal(GameContext* ctx, uint32_t medal_id);
void post_score(GameContext* ctx, uint32_t score);
void get_score_board(GameContext* ctx);

// Helper functions
float get_delta_time(void);
uint32_t get_current_time(void);

// Evidence-based initialization from SWF analysis
void evidence_based_init(GameContext* ctx);

#endif // GAME_H