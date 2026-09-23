#version 450

// EXP-F4-A — Diseño B de DESIGN-GRAPHICS: fragment pesado para la RX 550 (Polaris12).
// Per-pixel workload:
//   - 4 muestras de textura (bilinear) de 4 texturas 4096² RGBA8 (> L2 → DRAM)
//   - UV fragmentados / incoherentes derivados de gl_FragCoord (escala grande + offset por capa)
//   - cadena de ~24 fma sobre los samples (ALU/SCLK alta)
//   - salida de ALTA VARIANZA (bits de gl_FragCoord mezclados) → derrota DCC → CB a DRAM
//   - blending ADITIVO (definido en pipeline) → read-modify-write del CB por capa
//   - overdraw N capas = el host dibuja N veces con un push constant layer offset

layout(binding = 0) uniform sampler2D u_tex[4];

layout(push_constant) uniform PC {
    float scale_w;   // ancho de viewport efectivo (px) = escala * W
    float scale_h;   // alto de viewport efectivo (px) = escala * H
    uint  layer;     // capa actual 0..N-1 (overdraw)
    uint  seed;      // semilla determinista fija (0x5EED0000)
} pc;

layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 o_color;

// hash determinista simple (devuelve 0..1)
float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

void main() {
    // UV fragmentados: escala grande (frecuencia alta) + offset por capa → accesos incoherentes
    vec2 frag_coord = gl_FragCoord.xy;
    vec2 uvf = vec2(
        fract(frag_coord.x / 4096.0 + 0.13 * float(pc.layer) + hash12(vec2(float(pc.layer), pc.seed))),
        fract(frag_coord.y / 4096.0 + 0.37 * float(pc.layer) + hash12(vec2(pc.seed, float(pc.layer))))
    );
    // offsets deterministas por capa para forzar caminos distintos de caché
    float ox = (pc.layer & 1u) == 0u ? 0.07 : 0.43;
    float oy = (pc.layer & 2u) == 0u ? 0.19 : 0.61;
    float oz = (pc.layer & 4u) == 0u ? 0.29 : 0.73;
    vec2 u0 = fract(uvf + vec2(ox, 0.0));
    vec2 u1 = fract(uvf + vec2(0.0, oy));
    vec2 u2 = fract(uvf + vec2(ox, oy));
    vec2 u3 = fract(uvf + vec2(-ox, oy));
    // segundo set de taps: camino de caché distinto (más accesos > L2)
    vec2 u4 = fract(u0 * 1.37 + vec2(oz, 0.11));
    vec2 u5 = fract(u1 * 1.37 + vec2(0.13, oz));
    vec2 u6 = fract(u2 * 1.37 + vec2(oz, oz));
    vec2 u7 = fract(u3 * 1.37 + vec2(0.17, 0.23));

    // 8 muestras de textura (bilinear) — accesos incoherentes, > L2
    vec4 t0 = texture(u_tex[0], u0);
    vec4 t1 = texture(u_tex[1], u1);
    vec4 t2 = texture(u_tex[2], u2);
    vec4 t3 = texture(u_tex[3], u3);
    vec4 t4 = texture(u_tex[0], u4);
    vec4 t5 = texture(u_tex[1], u5);
    vec4 t6 = texture(u_tex[2], u6);
    vec4 t7 = texture(u_tex[3], u7);

    // cadena FMA larga (~90 ops) sobre los 8 samples: ALU/SCLK alta
    float x = fma(t0.r, t1.g, t2.b * t3.a) + t4.r * t5.g + t6.b * t7.a;
    float y = fma(t0.g, t1.b, t2.a * t3.r) + t4.g * t5.b + t6.a * t7.r;
    float z = fma(t0.b, t1.a, t2.r * t3.g) + t4.b * t5.a + t6.r * t7.g;
    float w = fma(t0.a, t1.r, t2.g * t3.b) + t4.a * t5.r + t6.g * t7.b;
    // reducción en espiral sobre las 4 acumuladoras
    for (int i = 0; i < 16; i++) {
        x = fma(x, 1.0003, y * 0.9997);
        y = fma(y, 1.0003, z * 0.9997);
        z = fma(z, 1.0003, w * 0.9997);
        w = fma(w, 1.0003, x * 0.9997);
    }
    x = fma(x, t0.r, fma(t4.r, 0.5, t6.r * 0.25));
    y = fma(y, t1.g, fma(t5.g, 0.5, t7.g * 0.25));
    z = fma(z, t2.b, fma(t6.b, 0.5, t0.b * 0.25));
    w = fma(w, t3.a, fma(t7.a, 0.5, t1.a * 0.25));
    // acumulación final dependiente de los 8 muestras (evita dead-code)
    float a = fma(x, t2.r, fma(y, t3.g, z * t0.b));
    float b = fma(y, t3.g, fma(z, t0.b, w * t1.a));
    float c = fma(z, t0.b, fma(w, t1.a, x * t2.r));
    float d = fma(w, t1.a, fma(x, t2.r, y * t3.g));
    a = fma(a, 0.5, b * 0.5);
    c = fma(c, 0.5, d * 0.5);
    float e = fma(a, 1.001, c * 0.999);
    float f = fma(c, 1.001, a * 0.999);
    float g = fma(e, 0.5, f * 0.5);
    float h = fma(g, 0.51, frag_coord.x * 1e-7 + frag_coord.y * 2e-7);

    // salida de ALTA VARIANZA (bits de frag_coord mezclados) → derrota DCC
    float n = hash12(frag_coord + vec2(pc.seed, pc.layer));
    vec4 acc = vec4(
        h + t0.x * 0.1 + t4.r * 0.03 + n * 0.05,
        h * 0.9 + t1.y * 0.1 + t5.g * 0.03 + n * 0.07,
        h * 0.8 + t2.z * 0.1 + t6.b * 0.03 + n * 0.11,
        1.0
    );
    // normalización para evitar saturación entre capas
    acc.rgb /= float(pc.layer + 1u);

    o_color = vec4(acc.rgb, 1.0);
}