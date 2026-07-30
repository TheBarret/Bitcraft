#include "include/bit.h"
#include <assert.h>

int bit_try_make(unsigned char value, bit *out) {
    if (value != 0 && value != 1) {
        return 0;
    }
    if (out) {
        out->v = value;
    }
    return 1;
}

bit bit_make(unsigned char value) {
    assert((value == 0 || value == 1) && "bit value must be strictly 0 or 1");
    bit b;
    b.v = (value == 1) ? 1 : 0;
    return b;
}

int bit_is_one(bit b) {
    return b.v == 1;
}

int bit_equal(bit a, bit b) {
    return a.v == b.v;
}

int bits_to_uint16(const bit *bits, size_t bits_len, uint16_t *out) {
    if (bits == NULL || out == NULL || bits_len != BIT_WORD_WIDTH) {
        return 0;
    }
    uint16_t result = 0;
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        if (bits[i].v != 0 && bits[i].v != 1) {
            /* Corrupted/uninitialized bit array
               refuse to interpret it rather than silently producing a wrong number.
            */
            return 0;
        }
        if (bits[i].v == 1) {
            result |= (uint16_t)(1U << i);
        }
    }
    *out = result;
    return 1;
}

int uint16_to_bits(uint16_t value, bit *bits, size_t bits_len) {
    if (bits == NULL || bits_len != BIT_WORD_WIDTH) {
        return 0;
    }
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        bits[i].v = (unsigned char)((value >> i) & 1U);
    }
    return 1;
}
