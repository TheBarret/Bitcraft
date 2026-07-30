#include "include/adder.h"
#include "include/gates.h"
#include <assert.h>

/*
 * Same pattern as gates.c:
 * every public entry point validates its own inputs directly rather than
 * trusting that gate_xor/gate_and further down already did it.
 * This is duplicated work at runtime (each input effectively gets checked twice: once here, once inside the gate calls)
 * in exchange for every public function in the call chain being independently safe to call directly,
 * not just safe when called through this particular path.
 * Same NDEBUG caveat as gate_check()/bit_make() applies: compiled out in release builds.
 */
static void adder_check(bit b) {
    assert((b.v == 0 || b.v == 1) && "adder received a bit with an invalid value");
}

half_adder_result half_adder(bit input_a, bit input_b) {
    adder_check(input_a);
    adder_check(input_b);

    half_adder_result result;
    result.sum = gate_xor(input_a, input_b);
    result.carry = gate_and(input_a, input_b);
    return result;
}

full_adder_result full_adder(bit input_a, bit input_b, bit carry_in) {
    adder_check(input_a);
    adder_check(input_b);
    adder_check(carry_in);

    half_adder_result first = half_adder(input_a, input_b);
    half_adder_result second = half_adder(first.sum, carry_in);

    full_adder_result result;
    result.sum = second.sum;
    result.carry_out = gate_or(first.carry, second.carry);
    return result;
}
