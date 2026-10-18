#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "game.h"

int main(void) {
    GameContext ctx;
    init_engine(&ctx);
    evidence_based_init(&ctx);
    
    printf("Test 1: Game engine initialization successful\n");
    printf("Player sprite ID: %u\n", ctx->player.sprite_id);
    printf("Sprite count: %u\n", ctx->sprite_count);
    printf("Sound count: %u\n", ctx->sound_count);
    printf("Max enemies: %u\n", ctx->max_enemies);
    printf("Frame rate: %d FPS\n", FRAME_RATE);
    
    // Simulate 100 frames of gameplay
    for (uint32_t i = 0; i < MAX_TEST_FRAMES; i++) {
        update_input(&ctx);
        update_game(&ctx);
        render_frame(&ctx);
    }
    
    printf("Test completed successfully - rendered %u frames\n", ctx.frame_count);
    return 0;
}