#ifndef MUX_H
#define MUX_H

#include "bit.h"

/*
 * 1-bit 2-to-1 multiplexor
 * select = 0 → output = input_a
 * select = 1 → output = input_b
 */
bit mux_2to1(bit input_a, bit input_b, bit select);

/*
 * 1-bit 4-to-1 multiplexor
 * select = 00 → output = input_0
 * select = 01 → output = input_1
 * select = 10 → output = input_2
 * select = 11 → output = input_3
 */
bit mux_4to1(bit input_0, bit input_1, bit input_2, bit input_3,
             bit select_0, bit select_1);

/*
 * 1-bit 16-to-1 multiplexor
 * select = 0000 → output = input_0
 * ... etc ...
 * select = 1111 → output = input_15
 */
bit mux_16to1(const bit inputs[16], bit select_0, bit select_1,
              bit select_2, bit select_3);

#endif
