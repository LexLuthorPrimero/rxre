# C Reconstruction of Madness Project Nexus Classic

## Project Overview
This project implements a faithful behavioral reconstruction of the Flash game "Madness Project Nexus Classic" from the SWF file `/home/lucas/Escritorio/flash/Madness Project Nexus Classic.swf`.

## Analysis Summary
- **Artifact**: SWF v10 (compressed) with SHA256: `44584a02d85a883384bad34617eb800d79301a8daeabf20244f6b75755ff9342`
- **File Size**: 15.6 MB compressed (20.5 MB uncompressed)
- **Tag Count**: 9,788 tags
- **ActionScript**: 2.0/AVM1 (75 action tags, 39,595 action records)
- **Sprites**: 2,448 DefineSprite tags
- **Sounds**: 137 DefineSound tags
- **Architecture**: GF8 (Polaris12 - AMD RX 550)

## Reconstruction Goals
This is a **behavioral reconstruction** - not source code recovery. The objective is to implement the same game logic, state management, and interactions using C, with the same gameplay behavior as the original Flash game.

## Deliverables
1. **Executable Foundation** - Build system, application lifecycle, logging
2. **Resource Reconstruction** - Sprite hierarchy, sounds, animations, frame data
3. **Program Reconstruction** - Game state, input handling, main game loop
4. **Gameplay Reconstruction** - Player/enemy behavior, physics, collision, combat
5. **Integration** - Menus, UI, audio, progression, testing
6. **Differential Verification** - Compare behavior with original SWF

## Technical Constraints
- Must compile and run independently (no Flash runtime)
- Use local resources when legally permissible
- Maintain traceability: SWF evidence → RXRE claims → C implementation
- Follow the RXRE workflow for evidence-grounded development

## Building Blocks
- **Game Engine Core**: Main loop, state machine, timing
- **Entity System**: Player, enemies, projectiles, animations
- **Input System**: Keyboard/gamepad handling
- **Audio System**: Sound playback and effects
- **Graphics System**: Sprite rendering, animation, transformations
- **Physics System**: Collision detection, movement, game rules
- **Resource Management**: Loading, caching, cleanup
- **Persistence**: Save states, high scores, progress

## Testing Strategy
- Unit tests for core systems
- Integration tests for game mechanics
- Functional verification against original SWF behavior
- Performance benchmarking

## Code Organization
```
reconstruction/
├── src/
│   ├── core/          # Engine core (main loop, state management)
│   ├── systems/       # Game systems (input, physics, audio, graphics)
│   ├── entities/      # Game entities (player, enemies, projectiles)
│   ├── resources/     # Resource management (sprites, sounds, fonts)
│   ├── ui/           # User interface (menus, HUD)
│   └── tests/        # Unit and integration tests
├── assets/            # Extracted game resources
├── include/           # Header files
└── build/            # Build configuration
```

## Evidence-to-Code Traceability
Every implementation decision must be linked to:
1. Original SWF evidence (tag definitions, bytecode instructions)
2. RXRE knowledge claims and epistemic state
3. Specific game behavior or pattern from SWF analysis

## Completion Criteria
The reconstruction is successful only if:
1. Builds and runs independently (no Flash runtime)
2. Implements verified gameplay systems from evidence
3. Passes differential verification against original
4. Maintains evidence traceability throughout
5. Can demonstrate material gameplay equivalence

## Current Status
**Phase A - Executable Foundation**: Under development
**Phase B - Resource Reconstruction**: Pending sprite bytecode analysis
**Phase C - Program Reconstruction**: Pending state machine extraction
**Phase D - Gameplay Reconstruction**: Pending combat/rule extraction
**Phase E - Integration**: Pending UI/progression extraction
**Phase F - Verification**: Pending test development
