#ifndef ALU_H
#define ALU_H

#include "bit.h"
#include <stddef.h>

/*
 * 16-bit ALU with 4-bit control (16 operations).
 *
 * Operation encoding:
 *   0000: ADD        - A + B
 *   0001: SUB        - A - B
 *   0010: AND        - A & B
 *   0011: OR         - A | B
 *   0100: XOR        - A ^ B
 *   0101: NAND       - ~(A & B)
 *   0110: NOR        - ~(A | B)
 *   0111: NOT_A      - ~A
 *   1000: PASS_A     - A
 *   1001: PASS_B     - B
 *   1010: SHL        - A << 1
 *   1011: SHR        - A >> 1
 *   1100: ROL        - rotate left by 1
 *   1101: ROR        - rotate right by 1
 *   1110: CMP        - compare (flags only, result = 0)
 *   1111: SYS        - ALU specific system commands to modify ALU saturation(clamp) or inverse run modes
 */

#define ALU_OP_ADD      0x0
#define ALU_OP_SUB      0x1
#define ALU_OP_AND      0x2
#define ALU_OP_OR       0x3
#define ALU_OP_XOR      0x4
#define ALU_OP_NAND     0x5
#define ALU_OP_NOR      0x6
#define ALU_OP_NOT_A    0x7
#define ALU_OP_PASS_A   0x8
#define ALU_OP_PASS_B   0x9
#define ALU_OP_SHL      0xA
#define ALU_OP_SHR      0xB
#define ALU_OP_ROL      0xC
#define ALU_OP_ROR      0xD
#define ALU_OP_CMP      0xE
#define ALU_OP_SYS      0xF

/*
 * ALU flags
 */
typedef struct {
    bit zero;      /* Result is all zeros */
    bit carry;     /* Carry out of MSB (unsigned overflow) */
    bit overflow;  /* Signed overflow (two's complement) */
} alu_flags;

/*
 * 16-bit ripple-carry adder.
 * Built entirely from full_adders.
 *
 * Parameters:
 *   - A, B: input operands (must be BIT_WORD_WIDTH bits)
 *   - bits_len: must equal BIT_WORD_WIDTH (enforced at runtime)
 *   - carry_in: carry input (0 or 1)
 *   - sum: output buffer (must be BIT_WORD_WIDTH bits)
 *   - carry_out: carry out of MSB
 *   - carry_into_msb: carry that was fed into the MSB (for overflow detection)
 *
 * Returns:
 *   1 on success, 0 on error (NULL pointer, wrong length, invalid bits)
 */

int adder_16(
    const bit* A,
    const bit* B,
    size_t bits_len,
    bit carry_in,
    bit* sum,
    bit* carry_out,
    bit* carry_into_msb
);

/*
 * ALU forward path.
 *
 * Parameters:
 *   - A, B: input operands (must be BIT_WORD_WIDTH bits)
 *   - bits_len: must equal BIT_WORD_WIDTH (enforced at runtime)
 *   - control: 4-bit operation selector (control[0] = LSB)
 *   - result: output buffer (must be BIT_WORD_WIDTH bits)
 *   - flags: output flags (zero, carry, overflow)
 *
 * Returns:
 *   1 on success, 0 on error (NULL pointer, wrong length, invalid bits)
 */
int alu_forward(
    const bit* A,
    const bit* B,
    size_t bits_len,
    const bit control[4],
    bit* result,
    alu_flags* flags
);

#endif
