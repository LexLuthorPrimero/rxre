# Build configuration for Madness Project Nexus Classic Reconstruction
# Evidence-grounded behavioral reconstruction of Flash game SWF

CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2 -g3 -I../include -ISDL2 -ISDL2_image
LDFLAGS = -lm -L/usr/lib64 -lSDL2 -lSDL2_image -Wl,-rpath,/usr/lib64
TARGET = mad_nexus
BUILD_DIR = .
SRC_DIR = ../src

SRCS = $(SRC_DIR)/main.c
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)

all: $(TARGET)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(TARGET): $(OBJS)
	@echo "[LINK] Creating $(TARGET)..."
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)
	@echo "[OK] Build complete: $(TARGET) (linked with SDL2)"

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	@echo "[COMPILE] $<..."
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	@echo "[CLEAN] Removing build artifacts..."
	rm -f $(TARGET) $(OBJS)
	@echo "[OK] Clean complete"

info:
	@echo "=== Madness Project Nexus Classic Reconstruction - Build Info ==="
	@echo "Target: $(TARGET)"
	@echo "Compiler: $(CC) $(CFLAGS)"
	@echo "Sources: $(SRCS)"
	@echo "Libraries: SDL2, SDL2_image"
	@echo ""
	@echo "=== SWF Source Evidence ==="
	@echo "Artifact: Madness Project Nexus Classic.swf"
	@echo "SHA256: 44584a02d85a883384bad34617eb800d79301a8daeabf20244f6b75755ff9342"
	@echo "File size: 15,612,129 bytes (compressed)"
	@echo "Uncompressed: 20,491,352 bytes"
	@echo "SWF version: 10 (AVM1/ActionScript 2.0)"
	@echo "Frame rate: 30 FPS"
	@echo "Tag count: 9,788"
	@echo "DefineSprite count: 2,448"
	@echo "DefineSound count: 137"
	@echo "DoAction count: 6"
	@echo "DoInitAction count: 69"
	@echo "Action records: 39,595"