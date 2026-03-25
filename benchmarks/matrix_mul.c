#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ALIGNMENT 64ULL
#define DEFAULT_MATRIX_KB 1024ULL
#define DEFAULT_TILE 32U
#define DEFAULT_WARMUP_PASSES 1U
#define DEFAULT_ROI_PASSES 3U
#define MIN_DIM 32U

#ifdef GEM5
#include <gem5/m5ops.h>
#define ROI_BEGIN() do { m5_reset_stats(0, 0); } while (0)
#define ROI_END() do { m5_dump_stats(0, 0); } while (0)
#else
#define ROI_BEGIN() do { } while (0)
#define ROI_END() do { } while (0)
#endif

typedef enum {
    PATTERN_IJK = 0,
    PATTERN_IKJ,
    PATTERN_JKI,
    PATTERN_BLOCKED,
} Pattern;

static volatile double global_sink = 0.0;

static uint64_t parse_u64_arg(const char *arg, uint64_t fallback) {
    char *end = NULL;
    unsigned long long value;
    if (arg == NULL || *arg == '\0') {
        return fallback;
    }
    errno = 0;
    value = strtoull(arg, &end, 10);
    if (errno != 0 || end == arg || *end != '\0' || value == 0ULL) {
        return fallback;
    }
    return (uint64_t)value;
}

static size_t align_up_size(size_t bytes, size_t alignment) {
    size_t rem = bytes % alignment;
    if (rem == 0U) {
        return bytes;
    }
    return bytes + (alignment - rem);
}

static double *alloc_aligned_matrix(size_t elements) {
    size_t bytes = elements * sizeof(double);
    size_t aligned = align_up_size(bytes, (size_t)ALIGNMENT);
    return (double *)aligned_alloc((size_t)ALIGNMENT, aligned);
}

static uint32_t derive_matrix_dim_from_kb(uint64_t matrix_kb) {
    double bytes = (double)(matrix_kb * 1024ULL);
    double elems = bytes / sizeof(double);
    double side = floor(sqrt(elems));
    uint32_t n;
    if (side < (double)MIN_DIM) {
        side = (double)MIN_DIM;
    }
    n = (uint32_t)side;
    return n;
}

static void zero_matrix(double *m, uint32_t n) {
    uint64_t i;
    uint64_t total = (uint64_t)n * (uint64_t)n;
    for (i = 0ULL; i < total; ++i) {
        m[i] = 0.0;
    }
}

static void init_matrix_a(double *a, uint32_t n) {
    uint32_t i;
    for (i = 0U; i < n; ++i) {
        uint32_t j;
        for (j = 0U; j < n; ++j) {
            double v = (double)(i * 131U + j * 17U) / (double)(n + 1U);
            a[(uint64_t)i * n + j] = v;
        }
    }
}

static void init_matrix_b(double *b, uint32_t n) {
    uint32_t i;
    for (i = 0U; i < n; ++i) {
        uint32_t j;
        for (j = 0U; j < n; ++j) {
            double v = (double)((i ^ j) + 3U) / (double)(j + 1U);
            b[(uint64_t)i * n + j] = v;
        }
    }
}

static double multiply_ijk(
    const double *a,
    const double *b,
    double *c,
    uint32_t n,
    uint32_t passes
) {
    uint32_t p;
    double local = 0.0;
    for (p = 0U; p < passes; ++p) {
        uint32_t i;
        for (i = 0U; i < n; ++i) {
            uint32_t j;
            for (j = 0U; j < n; ++j) {
                uint32_t k;
                double sum = c[(uint64_t)i * n + j];
                for (k = 0U; k < n; ++k) {
                    sum += a[(uint64_t)i * n + k] * b[(uint64_t)k * n + j];
                }
                c[(uint64_t)i * n + j] = sum;
                local += sum * 1e-12;
            }
        }
    }
    return local;
}

static double multiply_ikj(
    const double *a,
    const double *b,
    double *c,
    uint32_t n,
    uint32_t passes
) {
    uint32_t p;
    double local = 0.0;
    for (p = 0U; p < passes; ++p) {
        uint32_t i;
        for (i = 0U; i < n; ++i) {
            uint32_t k;
            for (k = 0U; k < n; ++k) {
                double aik = a[(uint64_t)i * n + k];
                uint32_t j;
                for (j = 0U; j < n; ++j) {
                    uint64_t idx = (uint64_t)i * n + j;
                    double val = c[idx] + aik * b[(uint64_t)k * n + j];
                    c[idx] = val;
                    local += val * 1e-12;
                }
            }
        }
    }
    return local;
}

static double multiply_jki(
    const double *a,
    const double *b,
    double *c,
    uint32_t n,
    uint32_t passes
) {
    uint32_t p;
    double local = 0.0;
    for (p = 0U; p < passes; ++p) {
        uint32_t j;
        for (j = 0U; j < n; ++j) {
            uint32_t k;
            for (k = 0U; k < n; ++k) {
                double bkj = b[(uint64_t)k * n + j];
                uint32_t i;
                for (i = 0U; i < n; ++i) {
                    uint64_t idx = (uint64_t)i * n + j;
                    double val = c[idx] + a[(uint64_t)i * n + k] * bkj;
                    c[idx] = val;
                    local += val * 1e-12;
                }
            }
        }
    }
    return local;
}

static double multiply_blocked(
    const double *a,
    const double *b,
    double *c,
    uint32_t n,
    uint32_t tile,
    uint32_t passes
) {
    uint32_t p;
    double local = 0.0;
    if (tile == 0U) {
        tile = 1U;
    }

    for (p = 0U; p < passes; ++p) {
        uint32_t ii;
        for (ii = 0U; ii < n; ii += tile) {
            uint32_t kk;
            uint32_t i_end = (ii + tile < n) ? (ii + tile) : n;
            for (kk = 0U; kk < n; kk += tile) {
                uint32_t jj;
                uint32_t k_end = (kk + tile < n) ? (kk + tile) : n;
                for (jj = 0U; jj < n; jj += tile) {
                    uint32_t j_end = (jj + tile < n) ? (jj + tile) : n;
                    uint32_t i;
                    for (i = ii; i < i_end; ++i) {
                        uint32_t k;
                        for (k = kk; k < k_end; ++k) {
                            double aik = a[(uint64_t)i * n + k];
                            uint32_t j;
                            for (j = jj; j < j_end; ++j) {
                                uint64_t idx = (uint64_t)i * n + j;
                                double val = c[idx] + aik * b[(uint64_t)k * n + j];
                                c[idx] = val;
                                local += val * 1e-12;
                            }
                        }
                    }
                }
            }
        }
    }
    return local;
}

static Pattern parse_pattern(const char *arg, int *ok) {
    if (arg == NULL) {
        *ok = 0;
        return PATTERN_IJK;
    }
    if (strcmp(arg, "ijk") == 0) {
        *ok = 1;
        return PATTERN_IJK;
    }
    if (strcmp(arg, "ikj") == 0) {
        *ok = 1;
        return PATTERN_IKJ;
    }
    if (strcmp(arg, "jki") == 0) {
        *ok = 1;
        return PATTERN_JKI;
    }
    if (strcmp(arg, "blocked") == 0) {
        *ok = 1;
        return PATTERN_BLOCKED;
    }
    *ok = 0;
    return PATTERN_IJK;
}

static const char *pattern_name(Pattern p) {
    switch (p) {
        case PATTERN_IJK:
            return "ijk";
        case PATTERN_IKJ:
            return "ikj";
        case PATTERN_JKI:
            return "jki";
        case PATTERN_BLOCKED:
            return "blocked";
        default:
            return "unknown";
    }
}

static double run_pattern(
    Pattern p,
    const double *a,
    const double *b,
    double *c,
    uint32_t n,
    uint32_t tile,
    uint32_t passes
) {
    switch (p) {
        case PATTERN_IJK:
            return multiply_ijk(a, b, c, n, passes);
        case PATTERN_IKJ:
            return multiply_ikj(a, b, c, n, passes);
        case PATTERN_JKI:
            return multiply_jki(a, b, c, n, passes);
        case PATTERN_BLOCKED:
            return multiply_blocked(a, b, c, n, tile, passes);
        default:
            return 0.0;
    }
}

static void print_usage(const char *prog) {
    printf("Usage: %s [matrix_kb] [pattern]\n", prog);
    printf("Patterns: ijk | ikj | jki | blocked\n");
    printf("Example: %s 1024 blocked\n", prog);
}

int main(int argc, char **argv) {
    uint64_t matrix_kb = DEFAULT_MATRIX_KB;
    uint32_t n;
    uint32_t tile = DEFAULT_TILE;
    uint64_t elements;
    double *a;
    double *b;
    double *c;
    Pattern pattern;
    int pattern_ok;
    double warmup_acc;
    double roi_acc;

    if (argc > 1 && (strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0)) {
        print_usage(argv[0]);
        return 0;
    }

    if (argc > 1) {
        matrix_kb = parse_u64_arg(argv[1], DEFAULT_MATRIX_KB);
    }

    if (argc > 2) {
        pattern = parse_pattern(argv[2], &pattern_ok);
        if (!pattern_ok) {
            fprintf(stderr, "invalid pattern: %s\n", argv[2]);
            print_usage(argv[0]);
            return 1;
        }
    } else {
        pattern = PATTERN_IJK;
    }

    n = derive_matrix_dim_from_kb(matrix_kb);
    if (tile > n) {
        tile = n;
    }
    elements = (uint64_t)n * (uint64_t)n;

    a = alloc_aligned_matrix((size_t)elements);
    b = alloc_aligned_matrix((size_t)elements);
    c = alloc_aligned_matrix((size_t)elements);

    if (a == NULL || b == NULL || c == NULL) {
        fprintf(stderr, "allocation failed for matrix dimension %u\n", n);
        free(a);
        free(b);
        free(c);
        return 1;
    }

    init_matrix_a(a, n);
    init_matrix_b(b, n);

    /* Warm-up is intentionally outside ROI to stabilize cache/TLB state. */
    zero_matrix(c, n);
    warmup_acc = run_pattern(pattern, a, b, c, n, tile, DEFAULT_WARMUP_PASSES);
    global_sink += warmup_acc;

    /* ROI contains only the selected kernel for clean cache measurements. */
    zero_matrix(c, n);
    ROI_BEGIN();
    roi_acc = run_pattern(pattern, a, b, c, n, tile, DEFAULT_ROI_PASSES);
    ROI_END();

    global_sink += roi_acc;
    global_sink += c[(uint64_t)(n / 2U) * n + (n / 2U)];

    printf(
        "RESULT: pattern=%s, matrix_kb=%llu, N=%u, tile=%u, passes=%u, sink=%.10e\n",
        pattern_name(pattern),
        (unsigned long long)matrix_kb,
        n,
        tile,
        DEFAULT_ROI_PASSES,
        global_sink
    );

    free(a);
    free(b);
    free(c);
    return 0;
}