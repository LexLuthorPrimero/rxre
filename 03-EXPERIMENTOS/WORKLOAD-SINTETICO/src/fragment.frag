#version 450
// Fragment shader pesado del workload gráfico (Diseño B, DESIGN-GRAPHICS.md).
// - 4 samples bilineal de texturas 4096^2 con UV incoherentes (hash determinista de
//   gl_FragCoord + layer) -> accesos no localizados, w/s >> L2.
// - ~24 FMA por fragmento (4 iteraciones x 6 FMA).
// - Salida de alta entropía por píxel (hash de gl_FragCoord + layer) -> derrota DCC.
// - Determinista: todo deriva de gl_FragCoord y push constants (seed fija).

layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform sampler2D tex[4];

layout(push_constant) uniform PC {
    uvec2 resolution; // pixel size of the color buffer
    uvec2 seed;       // two seed components (deterministic)
    uint  layer;      // current overdraw layer (0-based)
    uint  numTextures;
    uint  fmaIters;   // number of FMA-loop iterations (6 FMA each)
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

    // UV incoherentes: cada píxel mapea a un texel seudoaleatorio del rango completo
    // de la textura (salt depende de capa y seed). Vecinos -> zonas lejanas.
    vec4 s0 = texture(tex[0], rnd2(ip, pc.seed.x ^ 0x1F123BB5u * (l + 1u)));
    vec4 s1 = texture(tex[1], rnd2(ip, pc.seed.y ^ 0x3A392F2Fu * (l + 1u)));
    vec4 s2 = texture(tex[2], rnd2(ip, pc.seed.x ^ 0x5F404129u * (l + 1u)));
    vec4 s3 = texture(tex[3], rnd2(ip, pc.seed.y ^ 0x75377371u * (l + 1u)));

    // ~24 FMA: dependencias largas para mantener ALU ocupada deterministamente.
    float a = s0.x, b = s1.y, c = s2.z, d = s3.w;
    float acc = 0.5;
    for (uint i = 0u; i < pc.fmaIters; ++i) {
        a = fma(a, 1.000003f, b * 0.125f);
        b = fma(b, 0.999997f, c * 0.125f);
        c = fma(c, 1.000001f, d * 0.125f);
        d = fma(d, 0.999999f, a * 0.125f);
        a = fma(a, 1.000003f, c * 0.125f);
        acc = fma(acc, 1.000001f, (a + b + c + d) * 0.25f);
    }

    // Salida de alta entropía (por píxel y por capa) -> DCC sin similitud que comprimir.
    uint h = hashp(ip, pc.seed.x ^ (l * 0x01010101u) ^ uint(int(acc * 255.0)));
    vec3 col = vec3(float((h >> 24) & 255u), float((h >> 16) & 255u),
                    float((h >> 8) & 255u)) / 255.0;
    outColor = vec4(col, 1.0);
}