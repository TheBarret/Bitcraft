#ifndef GATES_H
#define GATES_H

#include "bit.h"

/*
 * Primitive logic gates built directly from the bit object.
 *
 * Every gate here assumes its inputs are valid `bit` values (i.e. were
 * produced by bit_make()/bit_try_make() or another gate).
 * That invariant is checked defensively at the top of each function, not just assumed silently.
 */

/* NOT gate - inverts the input */
bit gate_not(bit input);

/* AND gate - outputs 1 only when both inputs are 1 */
bit gate_and(bit input_a, bit input_b);

/* OR gate - outputs 1 when at least one input is 1 */
bit gate_or(bit input_a, bit input_b);

/* NAND gate - outputs 0 only when both inputs are 1 */
bit gate_nand(bit input_a, bit input_b);

/* NOR gate - outputs 1 only when both inputs are 0 */
bit gate_nor(bit input_a, bit input_b);

/* XOR gate - outputs 1 when inputs differ */
bit gate_xor(bit input_a, bit input_b);

#endif
