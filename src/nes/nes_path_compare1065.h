#ifndef NES_PATH_COMPARE1065_H
#define NES_PATH_COMPARE1065_H
/* These paths are compared for equality, with unsigned byte semantics. */
static int nes_path_compare1065(const char *left, const char *right) {
    const unsigned char *a = (const unsigned char *)left;
    const unsigned char *b = (const unsigned char *)right;
    while (*a && *a == *b) { ++a; ++b; }
    return (int)*a - (int)*b;
}
#endif
