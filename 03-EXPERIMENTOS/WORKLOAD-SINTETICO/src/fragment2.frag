#version 450
// Fragment shader "muestreo denso + ILP" (F2). Modificación ESTRUCTURAL de fase 2
// (research R-13, DESIGN-GRAPHICS): E1 emitía 4 fetches independientes y los
// consumía en cadenas FMA semiseriales; este emite 8 fetchs independientes
// TODOS realmente consumidos por 8 cadenas FMA independientes (ILP), de modo que:
//   - el trabajo de memoria por fragmento se duplica (mecanismo que toca el
//     cuello de botella fetch->uso; mem_busy hoy ~36 % no saturado);
//   - la latencia de los fetch se oculta con más ILP dentro de la onda;
//   - la salida de entropía depende de TODOS los resultados (no eliminable).
// Determinismo, layout (push constant + tex[0..3]) idénticos a fragment.frag.

layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform sampler2D tex[4];

layout(push_constant) uniform PC {
    uvec2 resolution; // pixel size of the color buffer
    uvec2 seed;       // two seed components (deterministic)
    uint  layer;      // current overdraw layer (0-based)
    uint  numTextures;
    uint  fmaIters;   // number of ALU iterations (8 independent chains each)
} pc;

uint hashp(uvec2 p, uint salt) {
    uint h = p.x * 0x9E3779B1u ^ p.y * 0x85EBCA77u ^ salt;
    h ^= h >> 16;
    h *= 0x7FEB352Du;
    h ^= h >> 15;
    h *= 0x846CA68Bu;
    h ^= h >> 16;
    return h;
}

vec2 rnd2(uvec2 ip, uint salt) {
    return vec2(hashp(ip, salt), hashp(ip, salt ^ 0x9E3779B9u)) / 4294967296.0;
}

void main() {
    uvec2 ip = uvec2(gl_FragCoord.xy);
    uint  l  = pc.layer;

    // 8 UVs independientes (misma familia hash que E1, saltes nuevas por par/capa).
    vec2 u0 = rnd2(ip, pc.seed.x ^ 0x1F123BB5u * (l + 1u));
    vec2 u1 = rnd2(ip, pc.seed.y ^ 0x3A392F2Fu * (l + 1u));
    vec2 u2 = rnd2(ip, pc.seed.x ^ 0x5F404129u * (l + 1u));
    vec2 u3 = rnd2(ip, pc.seed.y ^ 0x75377371u * (l + 1u));
    vec2 u4 = rnd2(ip, pc.seed.x ^ 0x8A4A4B41u * (l + 1u));
    vec2 u5 = rnd2(ip, pc.seed.y ^ 0x9F5A596Du * (l + 1u));
    vec2 u6 = rnd2(ip, pc.seed.x ^ 0xB67112E8u * (l + 1u));
    vec2 u7 = rnd2(ip, pc.seed.y ^ 0xC7C90ABFu * (l + 1u));

    // 8 fetchs independientes; se reutilizan las 4 texturas con saltes distintas
    // (todo sigue yendo a DRAM; nº de accesos por fragmento duplicado).
    vec4 s0 = texture(tex[0], u0);
    vec4 s1 = texture(tex[1], u1);
    vec4 s2 = texture(tex[2], u2);
    vec4 s3 = texture(tex[3], u3);
    vec4 s4 = texture(tex[0], u4);
    vec4 s5 = texture(tex[1], u5);
    vec4 s6 = texture(tex[2], u6);
    vec4 s7 = texture(tex[3], u7);

    // 8 cadenas FMA independientes (ILP); trabajo dependiente del resultado de CADA fetch.
    float c0 = s0.x, c1 = s1.y, c2 = s2.z, c3 = s3.w;
    float c4 = s4.x, c5 = s5.y, c6 = s6.z, c7 = s7.w;
    for (uint i = 0u; i < pc.fmaIters; ++i) {
        c0 = fma(c0, 1.000003f, s0.y * 0.0625f);
        c1 = fma(c1, 0.999997f, s1.x * 0.0625f);
        c2 = fma(c2, 1.000001f, s2.w * 0.0625f);
        c3 = fma(c3, 0.999999f, s3.z * 0.0625f);
        c4 = fma(c4, 1.000003f, s4.y * 0.0625f);
        c5 = fma(c5, 0.999997f, s5.x * 0.0625f);
        c6 = fma(c6, 1.000001f, s6.w * 0.0625f);
        c7 = fma(c7, 0.999999f, s7.z * 0.0625f);
    }
    float acc = (c0 + c1 + c2 + c3 + c4 + c5 + c6 + c7) * 0.125f;

    // Salida de alta entropía (por píxel y capa), dependiente de TODOS los fetch.
    uint h = hashp(ip, pc.seed.x ^ (l * 0x01010101u) ^ uint(int(acc * 255.0)));
    vec3 col = vec3(float((h >> 24) & 255u), float((h >> 16) & 255u),
                    float((h >> 8) & 255u)) / 255.0;
    outColor = vec4(col, 1.0);
}