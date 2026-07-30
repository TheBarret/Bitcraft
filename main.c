#include <stdio.h>
#include <stdlib.h>
//#include <time.h>
#include "include/bit.h"
#include "include/gates.h"
#include "include/adder.h"
#include "include/alu.h"
#include "include/mux.h"
#include "include/bus.h"
#include "include/bus.h"

/*
 * Parses program words directly from argv (hex, e.g. 0x2001).
 * Does not read stdin, will be allocated for CPU operations only.
 */
int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <hex_word> [hex_word ...]\n", argv[0]);
        return 1;
    }

    size_t count = (size_t)(argc - 1);
    uint16_t* words = malloc(count * sizeof(uint16_t));
    if (!words) {
        fprintf(stderr, "out of memory\n");
        return 1;
    }

    for (size_t i = 0; i < count; i++) {
        char* end = NULL;
        unsigned long v = strtoul(argv[i + 1], &end, 16);
        if (end == argv[i + 1] || *end != '\0' || v > 0xFFFF) {
            fprintf(stderr, "bad hex word: %s\n", argv[i + 1]);
            free(words);
            return 1;
        }
        words[i] = (uint16_t)v;
    }

    Bus bus;
    bus_init(&bus);

    if (!bus_load_program(&bus, words, count)) {
        fprintf(stderr, "Error: program load failed\n");
        free(words);
        return 1;
    }
    free(words);

    bus_dump(&bus, PROGRAM_START, PROGRAM_START + (uint16_t)count - 1);

    /* fetch-decode-execute loop goes here once the decoder exists */

    return 0;
}
