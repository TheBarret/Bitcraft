#ifndef ADDER_H
#define ADDER_H

#include "bit.h"

/*
 * Arithmetic components built from gates.
 * Each component is built from simpler components below it.
 * No component uses any operation beyond what its subcomponents provide.
 */

/* Half-adder: adds two bits, produces sum and carry */
typedef struct {
    bit sum;
    bit carry;
} half_adder_result;

half_adder_result half_adder(bit input_a, bit input_b);

/* Full-adder: adds two bits plus carry-in, produces sum and carry-out */
typedef struct {
    bit sum;
    bit carry_out;
} full_adder_result;

full_adder_result full_adder(bit input_a, bit input_b, bit carry_in);

#endif
