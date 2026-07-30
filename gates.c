#include "include/gates.h"
#include <assert.h>

/*
 * Every public gate function receives its inputs directly from the
 * caller and cannot assume they were freshly produced by a validating
 * constructor (e.g. bit_make() built under NDEBUG,
 * a struct copied from uninitialized memory, etc).
 * So every entry point below validates its own inputs directly,
 * rather than relying on it having happened somewhere upstream.
 *
 * Same caveat as bit_make(): this is an assert,
 * so it is compiled OUT entirely if NDEBUG is defined.
 * It catches programmer error during development;
 * it is not a substitute for bit_try_make() at trust boundaries (e.g. input parsed from outside the program).
 */
static void gate_check(bit b) {
    assert((b.v == 0 || b.v == 1) && "gate received a bit with an invalid value");
}

bit gate_not(bit input) {
    gate_check(input);
    return bit_is_one(input) ? BIT_ZERO : BIT_ONE;
}

bit gate_and(bit input_a, bit input_b) {
    gate_check(input_a);
    gate_check(input_b);
    if (bit_is_one(input_a) && bit_is_one(input_b)) {
        return BIT_ONE;
    }
    return BIT_ZERO;
}

bit gate_or(bit input_a, bit input_b) {
    gate_check(input_a);
    gate_check(input_b);
    if (bit_is_one(input_a) || bit_is_one(input_b)) {
        return BIT_ONE;
    }
    return BIT_ZERO;
}

bit gate_nand(bit input_a, bit input_b) {
    gate_check(input_a);
    gate_check(input_b);
    return gate_not(gate_and(input_a, input_b));
}

bit gate_nor(bit input_a, bit input_b) {
    gate_check(input_a);
    gate_check(input_b);
    return gate_not(gate_or(input_a, input_b));
}

bit gate_xor(bit input_a, bit input_b) {
    gate_check(input_a);
    gate_check(input_b);
    bit not_a = gate_not(input_a);
    bit not_b = gate_not(input_b);
    bit left = gate_and(input_a, not_b);
    bit right = gate_and(not_a, input_b);
    return gate_or(left, right);
}
