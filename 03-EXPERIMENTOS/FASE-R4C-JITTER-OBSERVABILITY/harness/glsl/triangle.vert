#version 450
// Fullscreen triangle (3 vertices, no vertex buffer).
layout(location = 0) out vec2 vUv;

void main() {
  vec2 pos[3] = vec2[](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
  vec2 p = pos[gl_VertexIndex];
  gl_Position = vec4(p, 0.0, 1.0);
  vUv = clamp(p * 0.5 + 0.5, 0.0, 1.0);
}