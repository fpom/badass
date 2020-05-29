#include <stdio.h>

FILE* __ASSLOG__ = NULL;

#define assopen(path) __ASSLOG__=fopen(path, "w")
#define ASSLOG ((__ASSLOG__) ? __ASSLOG__ : stderr)
#define assprint(val, msg, key, ...) (fprintf(ASSLOG, "(:" #msg ":" key ":" __VA_ARGS__ ":)\n"), val)
#define asspass(key, ...) assprint(1, passed, key, __VA_ARGS__)
#define assfail(key, ...) assprint(0, failed, key, __VA_ARGS__)

#define assess(key, expr) ((expr) ? asspass(#key, #expr) : assfail(#key, #expr))
