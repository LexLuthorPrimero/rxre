#version 450

// EXP-F4-A — Diseño B de DESIGN-GRAPHICS: fullscreen triangle bufferless
// Vertex stage: 3 vértices que cubren la pantalla; UV derivados de gl_VertexIndex.
// Sin vertex buffer, sin index buffer.

layout(location = 0) out vec2 v_uv;

void main() {
    // Fullscreen triangle: con gl_VertexIndex 0,1,2 -> triángulo que cubre el viewport completo.
    // Clip space: [-1,-1], [3,-1], [-1,3]  (escritura de cuadrantes + beyond)
    vec2 pos;
    switch (gl_VertexIndex) {
        case 0: pos = vec2(-1.0, -1.0); break;
        case 1: pos = vec2( 3.0, -1.0); break;
        default: pos = vec2(-1.0,  3.0); break;
    }
    gl_Position = vec4(pos, 0.0, 1.0);
    v_uv = pos * 0.5 + 0.5; // 0..2 en el triángulo expandido; se recorta a 0..1 por el scissor
}