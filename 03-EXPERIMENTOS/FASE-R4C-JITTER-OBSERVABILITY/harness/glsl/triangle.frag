#version 450
// Fragment shader: uses only the UBO binding 0 (uniform buffer with color at
// offset 0). The jitter travels via push constants / uniform matrix REPRESENTATION,
// NOT via the shader, since this harness only tests observability of the data path.
layout(set = 0, binding = 0) uniform PerFrameUBO {
  vec4 color; // bytes 0..15 (first vec4 of PerFrame layout)
} pfu;

layout(location = 0) in vec2 vUv;
layout(location = 0) out vec4 fragColor;

void main() {
  fragColor = pfu.color;
}