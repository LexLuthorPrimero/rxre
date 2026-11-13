/* filenvercmp.c — R3 reconstruction, R3-REACTIVE phase (2026-11-12).
 * Literal transcription of the three functions found in /usr/bin/ls vnm:
 *   filenvercmp     @ 0x4fa0
 *   verrevcmp       @ 0x4b60
 *   file_prefixlen  @ 0x4a80
 * Reference: records/disas_all3.txt (objdump -M intel, offsets above).
 * Byte comparator semantics (from disasm, exact magnitudes):
 *   digits: compared via digit-run both-digit path; end-of-string vs digit -> +-1
 *   [A-Za-z]: order = (int)(char)c
 *   '~':      order = -2
 *   NUL/end-of-side sentinel: end-of-a vs non-digit b -> -1 - order(b);
 *     b-exhausted via a [A-Za-z] -> order(a) + 1; via a others -> order(a) + 1
 *     (zero-extended a + 257); a=='~' vs end-of-b -> -1; end-of-a vs '~' -> +1
 *   everything else: order = (int)c + 256 (zero-extended + 256)
 * Digits have order 0 (they only compare against each other via raw byte diff,
 * keeping the FIRST difference; different-length runs are handled inline by the
 * end-of-string / non-digit exits). Leading zeros of each digit run are skipped
 * before the pairwise compare (4cfd / 4d1d).
 * filenvercmp: leading '.' special-cases for "."/".." only; otherwise:
 *   pre = verrevcmp over the dpkg-style extension prefixes;
 *   if pre == 0 and at least one side has an extension -> full-string verrevcmp.
 */

#include <stddef.h>
#include <string.h>

static size_t file_prefixlen(const char *s, size_t *len_io) {
    /* 4a80 */
    size_t rcx = *len_io;                 /* -1 => strlen mode */
    size_t rax = 0, r8 = 0;
    unsigned char dl = 0;

    for (;;) {
    L_4a95:
        if ((long long)rcx < 0) goto L_4b0b;
        /* 4a9a */
        if (rcx == rax) goto L_4b4b;
        r8 = rax + 1;
        rax = rax + 2;
        if (rax >= rcx) { rax = r8; goto L_4a9a; }   /* jae 4b52 */
        rax = r8;                                     /* 4ab4 */
        goto L_4ac0;
    L_4a9a:
        if (rcx == rax) goto L_4b4b;
        r8 = rax + 1;
        rax = rax + 2;
        if (rax >= rcx) { rax = r8; goto L_4a9a; }
        rax = r8;                                     /* 4ab4 */
    L_4ac0:
        if (s[rax] != 0x2e) goto L_4a95;              /* '.' */
        dl = (unsigned char)s[rax + 1];
        if ((signed char)dl <= 0x5a) {                /* jle 4a90 */
            if ((signed char)dl > 0x40) goto L_4ade;  /* A-Z */
            goto L_4a95;
        }
        if ((unsigned char)(dl - 0x61) <= 0x19) goto L_4ade;  /* a-z */
        if (dl == 0x7e) goto L_4ade;                  /* '~' */
        goto L_4a95;
    L_4ade:                                           /* 4ade */
        rax = rax + 2;
        if (rax >= rcx) goto L_4afd;                  /* jae 4afd */
        for (;;) {                                    /* 4ae7 loop */
            dl = (unsigned char)s[rax];
            if ((signed char)dl > 0x5a) {             /* jg 4b28 */
                if ((unsigned char)(dl - 0x61) <= 0x19) goto L_4b40_incr;  /* a-z */
                if (dl == 0x7e) goto L_4b40_incr;                          /* '~' */
                goto L_4afd;                                              /* not ext-char */
            }
            if ((signed char)dl > 0x40) goto L_4b40_incr;  /* A-Z */
            dl = (unsigned char)(dl - 0x30);
            if (dl <= 0x09) goto L_4b40_incr;             /* digit */
            goto L_4afd;                                  /* else */
        L_4b40_incr:                                  /* 4b40 */
            rax = rax + 1;
            if (rax < rcx) continue;                      /* jb 4ae7 */
            goto L_4afd;
        }
    L_4afd:
        {
            size_t rdx = rax + 1;                     /* 4afd/4b01 */
            if (rdx < rcx) goto L_4ac0;               /* jb 4ac0 */
            if ((long long)rcx >= 0) goto L_4a95;     /* jns 4a9a (rcx>=0) */
            /* fall through to strlen tail */
        }
    L_4b0b:
        if (s[rax] == 0x00) goto L_4b4b;              /* 4b0f je */
        r8 = rax + 1;                                 /* 4b11 */
        rax = rax + 2;                                /* 4b15 */
        if (rax < rcx) { rax = r8; goto L_4ac0; }     /* jb 4ab4 */
        rax = r8;                                     /* 4b1e */
        goto L_4b0b;                                  /* 4b21 */
    L_4b4b:
        *len_io = rax;                                /* 4b4b */
        return r8;                                    /* 4b4e */
    }
}

static int verrevcmp(const char *a, const char *b, size_t la, size_t lb) {
    /* 4b60 — flat, block-free port of the disassembly. */
    size_t i = 0, j = 0;      /* rax, rdx */
    size_t a_lim = la, b_lim = lb;  /* rsi, rcx */
    unsigned char dil, c2;
    int edi, r10d, r10d2 = 0;
    int c2d, c2s;
    int first_diff, a_more, b_more;

    for (;;) {
    L_4b6f:
        if (i < a_lim) goto L_4b90;
        if (j >= b_lim) return 0;                /* 4ecf */
        goto L_4c16;
    L_4b90:
        dil = (unsigned char)a[i];
        r10d = (int)(signed char)dil - 0x30;
        if ((unsigned)r10d <= 0x9U) goto L_4c16; /* a[i] digit */
        if ((signed char)dil > 0x5a) goto L_4c88;
        if ((signed char)dil > 0x40) goto L_4c96;
        if (dil == 0x7e) goto L_4f18;
        goto L_4bc1;                             /* dil <= '@', not digit */
    L_4c88:
        if ((unsigned char)(dil - 0x61) <= 0x19) goto L_4c96;
        goto L_4bb7;
    L_4bb7:
        if (dil == 0x7e) goto L_4f18;
        /* falls through to 4bc1 */
    L_4bc1:
        if (j >= b_lim) return (int)dil + 0x101; /* 4f62 */
        edi = (int)dil + 0x100;                  /* 4bcf */
        c2 = (unsigned char)b[j];
        c2d = (int)c2 - 0x30;
        if ((unsigned)c2d <= 0x9U) return edi;   /* 4c79 */
        if ((signed char)c2 <= 0x5a) {
            if ((signed char)c2 > 0x40) return edi - (int)(signed char)c2;  /* 4e51 -> 4c76 */
            r10d = (int)c2 + 0x100;              /* 4bf9 -> 4c00 */
            if (r10d == edi) { i++; j++; goto L_4b6f; }
            return edi - r10d;                 /* 4c76 */
        }
        if ((unsigned char)(c2 - 0x61) <= 0x19) return edi - (int)(signed char)c2;  /* a-z 4e51 -> 4c76 */
        if (c2 == 0x7e) return edi + 2;          /* 4e7c -> 4c76 */
        r10d = (int)c2 + 0x100;                  /* 4e72 -> 4bf9 -> 4c00 */
        if (r10d == edi) { i++; j++; goto L_4b6f; }
        return edi - r10d;                       /* 4c76 */
    L_4c96:
        edi = (int)(signed char)dil;
        if (j >= b_lim) return edi + 1;          /* 4f50 */
        c2 = (unsigned char)b[j];
        c2d = (int)c2 - 0x30;
        if ((unsigned)c2d <= 0x9U) return edi;   /* 4c79 */
        if ((signed char)c2 <= 0x5a) {
            if ((signed char)c2 > 0x40) goto L_4eq;  /* [A-Z] 4e69 -> 4c00 */
            r10d = (int)c2 + 0x100;                  /* 4cc8 -> 4c76 */
            return edi - r10d;
        }
        if ((unsigned char)(c2 - 0x61) <= 0x19) goto L_4eq;   /* a-z 4e51 -> 4c00 */
        if (c2 == 0x7e) return edi + 2;                       /* 4e7c -> 4c76 */
        r10d = (int)c2 + 0x100;                        /* 4e96 -> 4c76 */
        return edi - r10d;
    L_4eq:
        r10d = (int)(signed char)c2;
        if (r10d == edi) { i++; j++; goto L_4b6f; }  /* 4c05 */
        return edi - r10d;                          /* 4c76 */
    L_4f18:
        if (j >= b_lim) return -1;                /* 4e34 */
        c2 = (unsigned char)b[j];
        c2d = (int)c2 - 0x30;
        if ((unsigned)c2d <= 0x9U) return -2;     /* 4f58 */
        if ((signed char)c2 <= 0x5a) {
            if ((signed char)c2 > 0x40) r10d = (int)(signed char)c2;  /* [A-Z] 4f6d */
            else r10d = (int)c2 + 0x100;                              /* 4f3f */
            return -2 - r10d;
        }
        if ((unsigned char)(c2 - 0x61) <= 0x19) r10d = (int)(signed char)c2;  /* a-z 4f6d */
        else if (c2 == 0x7e) { i++; j++; goto L_4b6f; }                       /* 4f8b */
        else r10d = (int)c2 + 0x100;                                          /* 4f3f */
        return -2 - r10d;
    L_4c16:
        if (j >= b_lim) goto L_4cd8;               /* 4ea2 -> 4cfd (a-digit vs b-exhausted) */
        c2 = (unsigned char)b[j];
        c2s = (int)(signed char)c2;
        c2d = c2s - 0x30;
        if ((unsigned)c2d <= 0x9U) goto L_4cd8;    /* both digits */
        if (i == a_lim) goto L_4ed6;               /* 4ed6 */
        /* entry guarantees i < a_lim and a[i] digit */
        if ((signed char)c2 <= 0x5a) {
            if ((signed char)c2 > 0x40) return -c2s;   /* [A-Z] -> 4c74: 0-(int)c2 */
            return -((int)c2 + 0x100);                   /* 4c6d/4c74: 0-(c2+256) */
        }
        if ((unsigned char)(c2 - 0x61) <= 0x19) return -c2s;  /* a-z -> 4c74 */
        if (c2 == 0x7e) return 2;                            /* 4f90: 0-(-2) */
        return -((int)c2 + 0x100);                            /* 4c6d */
    L_4ed6:
        c2 = (unsigned char)b[j];
        r10d = (int)(signed char)c2;                /* 4c24 */
        if ((signed char)c2 <= 0x5a) {
            if ((signed char)c2 <= 0x40) r10d = (int)c2 + 0x100;  /* 4ee2 */
            /* else [A-Z]: keep sign-extended r10d */
        } else {
            if ((unsigned char)(c2 - 0x61) <= 0x19) {
                /* a-z: keep sign-extended r10d */
            } else if (c2 == 0x7e) r10d = -2;                     /* 4f01/4f06 */
            else r10d = (int)c2 + 0x100;                          /* 4ee2 */
        }
        return -1 - r10d;                             /* 4ee9/4eee */
    L_4cd8:
        first_diff = 0;
        if (i >= a_lim) goto L_4dc8;
        while (a[i] == 0x30) {                        /* 4cfd/4cf0 */
            i++;
            if (i == a_lim) goto L_4dc8;
        }
        if (j >= b_lim) goto L_4eb0;                  /* 4d04/4d07 */
    L_4d1d:
        while (b[j] == 0x30) {                        /* 4d1d/4d10 */
            j++;
            if (j == b_lim) goto L_4e07;
        }
        a_more = (i < a_lim) ? 1 : 0;
        b_more = (b_lim > j) ? 1 : 0;
        if (!a_more) goto L_4e1a;                     /* 4d35 je 4e1a */
        if (!b_more) goto L_4e11;                     /* 4d3e je 4e11 */
    L_digitloop:
        r10d = (int)(signed char)a[i];
        c2d = r10d - 0x30;
        if ((unsigned)c2d > 0x9U) goto L_4d90;
        r10d2 = (int)(signed char)b[j];
        c2d = r10d2 - 0x30;
        if ((unsigned)c2d > 0x9U) goto L_4de0;        /* 4d61 ja */
        {
            int diff = r10d - r10d2;                  /* 4d66 */
            if (first_diff == 0) first_diff = diff;   /* 4d69/cmove */
            i++; j++;
            if (i >= a_lim) goto L_4da4;              /* 4d77 jle */
            if (j >= b_lim) goto L_4d90;              /* 4d7c jg not taken -> 4d90 */
            goto L_digitloop;
        }
    L_4d90:
        if (i >= a_lim) goto L_4da4;                  /* 4d93 jle */
        r10d = (int)(signed char)a[i] - 0x30;
        if ((unsigned)r10d <= 0x9U) return 1;         /* 4de5 */
        goto L_4da4;
    L_4da4:
        if (j >= b_lim) goto L_4db8;                  /* 4da4 jle 4db8 */
        r10d = (int)(signed char)b[j] - 0x30;
        if ((unsigned)r10d <= 0x9U) return -1;        /* 4e34 */
    L_4db8:
        if (first_diff == 0) goto L_4b6f;             /* 4db8 je 4b6f */
        return first_diff;                            /* 4dc0 jmp 4c79 */
    L_4de0:
        if (i >= a_lim) goto L_4da4;                  /* jle 4da4 */
        return 1;                                     /* 4de5 */
    L_4e11:
        if (i >= a_lim) goto L_4e1a;                  /* 4e11 je 4e1a */
        r10d = (int)(signed char)a[i] - 0x30;
        if ((unsigned)r10d > 0x9U) goto L_4b6f;       /* 4eb9 ja 4b6f */
        return 1;                                     /* 4de5 */
    L_4e1a:
        b_more = (b_lim > j) ? 1 : 0;
        if (!b_more) goto L_4b6f;                     /* 4e1a je 4b6f */
        r10d = (int)(signed char)b[j] - 0x30;
        if ((unsigned)r10d > 0x9U) goto L_4b6f;       /* ja 4b6f */
        return -1;                                    /* 4e34 */
    L_4e07:
        a_more = (i < a_lim) ? 1 : 0;
        if (a_more) goto L_4eb9;                      /* 4e0e jne 4eb9 */
        goto L_4e11;                                  /* fall */
    L_4eb0:
        if (i >= a_lim) goto L_4b6f;                  /* 4eb0 jle 4b6f */
        goto L_4eb9;
    L_4eb9:
        r10d = (int)(signed char)a[i] - 0x30;
        if ((unsigned)r10d > 0x9U) goto L_4b6f;       /* ja 4b6f */
        return 1;                                     /* 4de5 */
    L_4dc8:
        if (j < b_lim) goto L_4d1d;                   /* 4dc8 jl 4d1d */
        goto L_4b6f;                                  /* 4dd1 jmp 4b6f */
    }
}

int filenvercmp(const char *a, const char *b) {
    /* 4fa0 */
    if (a == 0 || a[0] == '\0') {
        /* 50f0: neg al; sbb eax,eax -> -(al != 0) */
        if (b == 0 || b[0] == '\0') return 0;
        return -1;
    }
    if (b[0] == '\0') return 1;                        /* 50d4 */

    if (a[0] == '.') {
        size_t pa, pb;
        int flag_ext;

        if (b[0] != '.') return -1;                    /* 5130 */
        if (a[1] == '\0') return (b[1] != '\0') ? -1 : 0;   /* 5140 */
        if (b[1] == '\0') return 1;                          /* 50d0 */
        if (a[1] == '.') {
            if (b[1] == '.') {
                if (b[2] == '\0') return (a[2] != '\0') ? 1 : 0;  /* 5153/5161 */
                if (a[2] != '\0') goto general;                   /* 5128 jne 4ff8 */
                return -1;                                         /* 5130 */
            } else {
                if (a[2] != '\0') goto general;                    /* 5128 */
                return -1;                                          /* 5130 */
            }
        }
        if (b[1] == '.') {
            if (b[2] == '\0') return 1;                       /* 50d0 via 50b9 */
            /* else general */
        } else {
            goto general;
        }
        /* b[1]=='.' && b[2]!='\0' falls to general */
    general:
        {
            size_t out_a = (size_t)-1, out_b = (size_t)-1;
            size_t la_full, lb_full;
            int rc;
            pa = file_prefixlen(a, &out_a);
            la_full = out_a;
            pb = file_prefixlen(b, &out_b);
            lb_full = out_b;
            flag_ext = (pa != la_full) || (pb != lb_full);
            rc = verrevcmp(a, b, pa, pb);
            if (rc != 0) return rc;
            if (!flag_ext) return 0;
            return verrevcmp(a, b, la_full, lb_full);  /* full-string second pass */
        }
    }

    if (b[0] == '.') return 1;                         /* 50d0 via 4ff0 */

    {
        size_t out_a = (size_t)-1, out_b = (size_t)-1;
        size_t pa = file_prefixlen(a, &out_a);
        size_t la_full = out_a;
        size_t pb = file_prefixlen(b, &out_b);
        size_t lb_full = out_b;
        int flag_ext = (pa != la_full) || (pb != lb_full);
        int rc = verrevcmp(a, b, pa, pb);
        if (rc != 0) return rc;
        if (!flag_ext) return 0;
        return verrevcmp(a, b, la_full, lb_full);
    }
}
