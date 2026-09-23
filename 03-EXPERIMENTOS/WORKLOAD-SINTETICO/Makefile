CXX     ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra

VULKAN_CFLAGS := $(shell pkg-config --cflags vulkan)
VULKAN_LIBS   := $(shell pkg-config --libs vulkan)
SHADERC_LIBS  := $(shell pkg-config --libs shaderc 2>/dev/null || echo -lshaderc_shared)

main: src/main.cpp
	$(CXX) $(CXXFLAGS) $(VULKAN_CFLAGS) src/main.cpp -o main $(VULKAN_LIBS) $(SHADERC_LIBS)

main-graphics: src/graphics.cpp
	$(CXX) $(CXXFLAGS) $(VULKAN_CFLAGS) src/graphics.cpp -o main-graphics $(VULKAN_LIBS) $(SHADERC_LIBS)

clean:
	rm -f main main-graphics

.PHONY: all clean
all: main main-graphics