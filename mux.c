#include "include/mux.h"
#include "include/gates.h"
#include <assert.h>

/*
 * Same pattern as gate_check()/adder_check()/alu_check() elsewhere in
 * bitcraft: every public entry point validates its own inputs directly,
 * so mux_2to1/mux_4to1/mux_16to1 are each independently safe to call,
 * not merely safe by virtue of being composed from gates that happen
 * to validate underneath. Same NDEBUG caveat applies: compiled out in
 * release builds.
 */
static void mux_check(bit b) {
    assert((b.v == 0 || b.v == 1) && "mux received a bit with an invalid value");
}

bit mux_2to1(bit input_a, bit input_b, bit select) {
    mux_check(input_a);
    mux_check(input_b);
    mux_check(select);

    bit not_select = gate_not(select);
    bit left = gate_and(input_a, not_select);
    bit right = gate_and(input_b, select);
    return gate_or(left, right);
}

bit mux_4to1(bit input_0, bit input_1, bit input_2, bit input_3,
             bit select_0, bit select_1) {
    mux_check(input_0);
    mux_check(input_1);
    mux_check(input_2);
    mux_check(input_3);
    mux_check(select_0);
    mux_check(select_1);

    bit mux0 = mux_2to1(input_0, input_1, select_0);
    bit mux1 = mux_2to1(input_2, input_3, select_0);
    return mux_2to1(mux0, mux1, select_1);
}

bit mux_16to1(const bit inputs[16], bit select_0, bit select_1,
              bit select_2, bit select_3) {
    for (size_t i = 0; i < 16; i++) {
        mux_check(inputs[i]);
    }
    mux_check(select_0);
    mux_check(select_1);
    mux_check(select_2);
    mux_check(select_3);

    bit mux0 = mux_4to1(inputs[0], inputs[1], inputs[2], inputs[3],
                        select_0, select_1);
    bit mux1 = mux_4to1(inputs[4], inputs[5], inputs[6], inputs[7],
                        select_0, select_1);
    bit mux2 = mux_4to1(inputs[8], inputs[9], inputs[10], inputs[11],
                        select_0, select_1);
    bit mux3 = mux_4to1(inputs[12], inputs[13], inputs[14], inputs[15],
                        select_0, select_1);
    bit mux01 = mux_2to1(mux0, mux1, select_2);
    bit mux23 = mux_2to1(mux2, mux3, select_2);
    return mux_2to1(mux01, mux23, select_3);
}
