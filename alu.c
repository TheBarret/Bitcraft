#include "include/alu.h"
#include "include/gates.h"
#include "include/adder.h"
#include "include/mux.h"
#include <assert.h>
#include <string.h>

/* ---------- Internal Validation ---------- */

static void alu_check(bit b) {
    assert((bit_equal(b, BIT_ZERO) || bit_equal(b, BIT_ONE)) &&
           "alu received a bit with an invalid value");
}

/* ---------- 16-bit Ripple-Carry Adder ---------- */

int adder_16_stride(
    const bit* A,
    const bit* B,
    size_t bits_len,
    bit carry_in,
    bit* sum,
    bit* carry_out,
    bit* carry_into_msb)
{
    if (A == NULL || B == NULL || sum == NULL ||
        carry_out == NULL || carry_into_msb == NULL) {
        return 0;
    }
    if (bits_len != BIT_WORD_WIDTH) {
        return 0;
    }
    for (size_t i = 0; i < bits_len; i++) {
        alu_check(A[i]);
        alu_check(B[i]);
    }
    alu_check(carry_in);

    // Stage 1: Generate and Propagate
    bit G[BIT_WORD_WIDTH];
    bit P[BIT_WORD_WIDTH];
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        G[i] = gate_and(A[i], B[i]);   // generate
        P[i] = gate_xor(A[i], B[i]);   // propagate
    }

    // Store original P for final sum computation
    bit P_orig[BIT_WORD_WIDTH];
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        P_orig[i] = P[i];
    }

    // Inject carry-in at bit 0
    bit p0_and_cin = gate_and(P[0], carry_in);
    G[0] = gate_or(G[0], p0_and_cin);

    // Stage 2: Kogge-Stone parallel prefix network
    // G_next and P_next buffers for double-buffering
    bit G_next[BIT_WORD_WIDTH];
    bit P_next[BIT_WORD_WIDTH];
    bit* G_curr = G;
    bit* P_curr = P;
    bit* G_swap = G_next;
    bit* P_swap = P_next;

    size_t stride = 1;
    while (stride < BIT_WORD_WIDTH) {
        // Copy unchanged low bits
        for (size_t i = 0; i < stride; i++) {
            G_swap[i] = G_curr[i];
            P_swap[i] = P_curr[i];
        }
        // Compute new values for bits stride..N-1
        for (size_t i = stride; i < BIT_WORD_WIDTH; i++) {
            // P_next[i] = P_curr[i] AND P_curr[i - stride]
            P_swap[i] = gate_and(P_curr[i], P_curr[i - stride]);

            // G_next[i] = G_curr[i] OR (P_curr[i] AND G_curr[i - stride])
            bit p_and_g = gate_and(P_curr[i], G_curr[i - stride]);
            G_swap[i] = gate_or(G_curr[i], p_and_g);
        }

        // Swap buffers
        bit* tmp_G = G_curr; G_curr = G_swap; G_swap = tmp_G;
        bit* tmp_P = P_curr; P_curr = P_swap; P_swap = tmp_P;

        stride <<= 1;
    }

    // After the loop, G_curr holds the final carry-generate values.
    // G_curr[i] is the carry INTO bit i+1 (or equivalently, carry out of bit i).
    // P_curr is no longer needed; we use P_orig for sum.

    // Stage 3: Final sum = P_orig XOR carry_in_at_this_bit
    // Carry into bit 0 is carry_in
    // Carry into bit i (i>0) is G_curr[i-1]
    sum[0] = gate_xor(P_orig[0], carry_in);
    for (size_t i = 1; i < BIT_WORD_WIDTH; i++) {
        sum[i] = gate_xor(P_orig[i], G_curr[i - 1]);
    }

    // Stage 4: Output carry and carry_into_msb
    *carry_out = G_curr[BIT_WORD_WIDTH - 1];
    *carry_into_msb = G_curr[BIT_WORD_WIDTH - 2];

    return 1;
}

int adder_16(
    const bit* A,
    const bit* B,
    size_t bits_len,
    bit carry_in,
    bit* sum,
    bit* carry_out,
    bit* carry_into_msb)
{
    /* NULL checks */
    if (A == NULL || B == NULL || sum == NULL ||
        carry_out == NULL || carry_into_msb == NULL) {
        return 0;
    }

    /* Length check */
    if (bits_len != BIT_WORD_WIDTH) {
        return 0;
    }

    /* Input validation */
    for (size_t i = 0; i < bits_len; i++) {
        alu_check(A[i]);
        alu_check(B[i]);
    }
    alu_check(carry_in);

    bit carry = carry_in;

    /* Chain full-adders */
    for (size_t i = 0; i < bits_len; i++) {
        /* Capture carry into MSB before processing MSB */
        if (i == bits_len - 1) {
            *carry_into_msb = carry;
        }

        full_adder_result fa = full_adder(A[i], B[i], carry);
        sum[i] = fa.sum;
        carry = fa.carry_out;
    }

    *carry_out = carry;
    return 1;
}

/* ---------- Internal: 16-bit Bitwise Operations ---------- */

static void bitwise_not_16(const bit in[BIT_WORD_WIDTH], bit out[BIT_WORD_WIDTH]) {
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        out[i] = gate_not(in[i]);
    }
}

static void bitwise_and_16(const bit a[BIT_WORD_WIDTH], const bit b[BIT_WORD_WIDTH],
                           bit out[BIT_WORD_WIDTH]) {
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        out[i] = gate_and(a[i], b[i]);
    }
}

static void bitwise_or_16(const bit a[BIT_WORD_WIDTH], const bit b[BIT_WORD_WIDTH],
                          bit out[BIT_WORD_WIDTH]) {
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        out[i] = gate_or(a[i], b[i]);
    }
}

static void bitwise_xor_16(const bit a[BIT_WORD_WIDTH], const bit b[BIT_WORD_WIDTH],
                           bit out[BIT_WORD_WIDTH]) {
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        out[i] = gate_xor(a[i], b[i]);
    }
}

static void bitwise_nand_16(const bit a[BIT_WORD_WIDTH], const bit b[BIT_WORD_WIDTH],
                            bit out[BIT_WORD_WIDTH]) {
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        out[i] = gate_nand(a[i], b[i]);
    }
}

static void bitwise_nor_16(const bit a[BIT_WORD_WIDTH], const bit b[BIT_WORD_WIDTH],
                           bit out[BIT_WORD_WIDTH]) {
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        out[i] = gate_nor(a[i], b[i]);
    }
}

/* ---------- Internal: Shifts and Rotates ---------- */

static void shl_16(const bit in[BIT_WORD_WIDTH], bit out[BIT_WORD_WIDTH],
                   bit* carry_out) {
    out[0] = BIT_ZERO;
    for (size_t i = 1; i < BIT_WORD_WIDTH; i++) {
        out[i] = in[i - 1];
    }
    *carry_out = in[BIT_WORD_WIDTH - 1];
}

static void shr_16(const bit in[BIT_WORD_WIDTH], bit out[BIT_WORD_WIDTH],
                   bit* carry_out) {
    out[BIT_WORD_WIDTH - 1] = BIT_ZERO;
    for (size_t i = 0; i < BIT_WORD_WIDTH - 1; i++) {
        out[i] = in[i + 1];
    }
    *carry_out = in[0];
}

static void rol_16(const bit in[BIT_WORD_WIDTH], bit out[BIT_WORD_WIDTH],
                   bit* carry_out) {
    out[0] = in[BIT_WORD_WIDTH - 1];
    for (size_t i = 1; i < BIT_WORD_WIDTH; i++) {
        out[i] = in[i - 1];
    }
    *carry_out = in[BIT_WORD_WIDTH - 1];
}

static void ror_16(const bit in[BIT_WORD_WIDTH], bit out[BIT_WORD_WIDTH],
                   bit* carry_out) {
    out[BIT_WORD_WIDTH - 1] = in[0];
    for (size_t i = 0; i < BIT_WORD_WIDTH - 1; i++) {
        out[i] = in[i + 1];
    }
    *carry_out = in[0];
}

/* ---------- Internal: Flag Computation ---------- */

static bit compute_zero_flag(const bit result[BIT_WORD_WIDTH]) {
    bit all_zero = BIT_ONE;
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        all_zero = gate_and(all_zero, gate_not(result[i]));
    }
    return all_zero;
}

static bit compute_overflow_flag(bit carry_into_msb, bit carry_out_msb) {
    return gate_xor(carry_into_msb, carry_out_msb);
}

/* ---------- Main ALU Forward ---------- */

int alu_forward(
    const bit* A,
    const bit* B,
    size_t bits_len,
    const bit control[4],
    bit* result,
    alu_flags* flags)
{
    /* NULL checks */
    if (A == NULL || B == NULL || control == NULL ||
        result == NULL || flags == NULL) {
        return 0;
    }

    /* Length check */
    if (bits_len != BIT_WORD_WIDTH) {
        return 0;
    }

    /* Input validation */
    for (size_t i = 0; i < bits_len; i++) {
        alu_check(A[i]);
        alu_check(B[i]);
    }
    for (size_t i = 0; i < 4; i++) {
        alu_check(control[i]);
    }

    /* --- Decode control --- */
    bit c0 = control[0];  /* LSB */
    bit c1 = control[1];
    bit c2 = control[2];
    bit c3 = control[3];  /* MSB */

    /* --- B inverted for subtraction --- */
    bit B_not[BIT_WORD_WIDTH];
    bitwise_not_16(B, B_not);

    /* --- Operation results --- */
    bit result_add[BIT_WORD_WIDTH];
    bit result_sub[BIT_WORD_WIDTH];
    bit result_and[BIT_WORD_WIDTH];
    bit result_or[BIT_WORD_WIDTH];
    bit result_xor[BIT_WORD_WIDTH];
    bit result_nand[BIT_WORD_WIDTH];
    bit result_nor[BIT_WORD_WIDTH];
    bit result_not_a[BIT_WORD_WIDTH];
    bit result_pass_a[BIT_WORD_WIDTH];
    bit result_pass_b[BIT_WORD_WIDTH];
    bit result_shl[BIT_WORD_WIDTH];
    bit result_shr[BIT_WORD_WIDTH];
    bit result_rol[BIT_WORD_WIDTH];
    bit result_ror[BIT_WORD_WIDTH];
    bit result_cmp[BIT_WORD_WIDTH];
    bit result_sys[BIT_WORD_WIDTH];

    /* Internal CMP result (for zero flag computation) */
    bit cmp_internal[BIT_WORD_WIDTH];

    bit carry_add, carry_sub, carry_shl, carry_shr, carry_rol, carry_ror;
    bit carry_cmp;
    bit carry_into_msb_add, carry_into_msb_sub, carry_into_msb_cmp;
    int ok;

    /* --- ADD: A + B --- */
    ok = adder_16(A, B, bits_len, BIT_ZERO, result_add,
                  &carry_add, &carry_into_msb_add);
    if (!ok) {
        return 0;
    }

    /* --- SUB: A - B = A + (~B) + 1 --- */
    ok = adder_16(A, B_not, bits_len, BIT_ONE, result_sub,
                  &carry_sub, &carry_into_msb_sub);
    if (!ok) {
        return 0;
    }

    /* --- AND --- */
    bitwise_and_16(A, B, result_and);

    /* --- OR --- */
    bitwise_or_16(A, B, result_or);

    /* --- XOR --- */
    bitwise_xor_16(A, B, result_xor);

    /* --- NAND --- */
    bitwise_nand_16(A, B, result_nand);

    /* --- NOR --- */
    bitwise_nor_16(A, B, result_nor);

    /* --- NOT_A --- */
    bitwise_not_16(A, result_not_a);

    /* --- PASS_A --- */
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        result_pass_a[i] = A[i];
    }

    /* --- PASS_B --- */
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        result_pass_b[i] = B[i];
    }

    /* --- SHL --- */
    shl_16(A, result_shl, &carry_shl);

    /* --- SHR --- */
    shr_16(A, result_shr, &carry_shr);

    /* --- ROL --- */
    rol_16(A, result_rol, &carry_rol);

    /* --- ROR --- */
    ror_16(A, result_ror, &carry_ror);

    /* --- CMP: same as SUB, but result = 0 --- */
    /* Compute subtraction internally for flags, then discard result */
    ok = adder_16(A, B_not, bits_len, BIT_ONE, cmp_internal,
                  &carry_cmp, &carry_into_msb_cmp);
    if (!ok) {
        return 0;
    }
    /* result is forced to zero, but we keep cmp_internal for zero flag */
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        result_cmp[i] = BIT_ZERO;
    }

    /* --- SYS: result = 0, flags = 0 (reserved) ---
     * Placeholder for ALU-behavior modifiers
     * - Saturation mode (clamp)
     * - Inverse mode (indifferent behavior)
     */

    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        result_sys[i] = BIT_ZERO;
    }

    /* --- MUX: 16-to-1 selection using tree of 2-to-1 muxes ---
     *
     * For each bit position, we have 16 possible results (one from each
     * operation: ADD, SUB, AND, OR, XOR, NAND, NOR, NOT_A, PASS_A, PASS_B,
     * SHL, SHR, ROL, ROR, CMP, SYS).
     *
     * The 4 control bits (c0..c3) select which one becomes the final output.
     *
     * The selection is built as a balanced binary tree:
     *   Level 1: c0 pairs adjacent operations (0/1, 2/3, 4/5, ...)
     *   Level 2: c1 pairs groups of 4 (0-3, 4-7, 8-11, 12-15)
     *   Level 3: c2 pairs groups of 8 (0-7, 8-15)
     *   Level 4: c3 selects between the final two groups
     *
     * This is equivalent to: result = inputs[control] but built
     * entirely from gates (mux_2to1), with no magic array indexing.
     */
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        bit mux_0_1  = mux_2to1(result_add[i], result_sub[i], c0);
        bit mux_2_3  = mux_2to1(result_and[i], result_or[i], c0);
        bit mux_4_5  = mux_2to1(result_xor[i], result_nand[i], c0);
        bit mux_6_7  = mux_2to1(result_nor[i], result_not_a[i], c0);
        bit mux_8_9  = mux_2to1(result_pass_a[i], result_pass_b[i], c0);
        bit mux_10_11 = mux_2to1(result_shl[i], result_shr[i], c0);
        bit mux_12_13 = mux_2to1(result_rol[i], result_ror[i], c0);
        bit mux_14_15 = mux_2to1(result_cmp[i], result_sys[i], c0);

        bit mux_0_3  = mux_2to1(mux_0_1, mux_2_3, c1);
        bit mux_4_7  = mux_2to1(mux_4_5, mux_6_7, c1);
        bit mux_8_11 = mux_2to1(mux_8_9, mux_10_11, c1);
        bit mux_12_15 = mux_2to1(mux_12_13, mux_14_15, c1);

        bit mux_0_7  = mux_2to1(mux_0_3, mux_4_7, c2);
        bit mux_8_15 = mux_2to1(mux_8_11, mux_12_15, c2);

        result[i] = mux_2to1(mux_0_7, mux_8_15, c3);
    }

    /* --- Compute Zero Flag ---
     *
     * For CMP, zero flag comes from the internal subtraction result,
     * not the forced-zero output. For all other ops, zero flag comes
     * from the selected result.
     *
     * CMP is selected when control[3:0] = 1110, which is:
     * c0 = 0, c1 = 1, c2 = 1, c3 = 1
     */
    int is_cmp = (bit_is_one(c0) == 0 &&
                  bit_is_one(c1) == 1 &&
                  bit_is_one(c2) == 1 &&
                  bit_is_one(c3) == 1);

    if (is_cmp) {
        flags->zero = compute_zero_flag(cmp_internal);
    } else {
        flags->zero = compute_zero_flag(result);
    }

    /* --- Compute Carry Flag ---
     *
     * For subtraction (SUB and CMP), carry flag represents BORROW:
     *   C = 1 means borrow occurred (A < B)
     *   C = 0 means no borrow occurred (A >= B)
     *
     * This is the inverse of the adder's carry_out.
     */
    bit carry_sub_borrow = gate_not(carry_sub);
    bit carry_cmp_borrow = gate_not(carry_cmp);

    bit carry_select[16] = {
        carry_add,          /* 0000: ADD */
        carry_sub_borrow,   /* 0001: SUB */
        BIT_ZERO,           /* 0010: AND */
        BIT_ZERO,           /* 0011: OR */
        BIT_ZERO,           /* 0100: XOR */
        BIT_ZERO,           /* 0101: NAND */
        BIT_ZERO,           /* 0110: NOR */
        BIT_ZERO,           /* 0111: NOT_A */
        BIT_ZERO,           /* 1000: PASS_A */
        BIT_ZERO,           /* 1001: PASS_B */
        carry_shl,          /* 1010: SHL */
        carry_shr,          /* 1011: SHR */
        carry_rol,          /* 1100: ROL */
        carry_ror,          /* 1101: ROR */
        carry_cmp_borrow,   /* 1110: CMP */
        BIT_ZERO            /* 1111: SYS */
    };

    bit c_0_1  = mux_2to1(carry_select[0], carry_select[1], c0);
    bit c_2_3  = mux_2to1(carry_select[2], carry_select[3], c0);
    bit c_4_5  = mux_2to1(carry_select[4], carry_select[5], c0);
    bit c_6_7  = mux_2to1(carry_select[6], carry_select[7], c0);
    bit c_8_9  = mux_2to1(carry_select[8], carry_select[9], c0);
    bit c_10_11 = mux_2to1(carry_select[10], carry_select[11], c0);
    bit c_12_13 = mux_2to1(carry_select[12], carry_select[13], c0);
    bit c_14_15 = mux_2to1(carry_select[14], carry_select[15], c0);

    bit c_0_3  = mux_2to1(c_0_1, c_2_3, c1);
    bit c_4_7  = mux_2to1(c_4_5, c_6_7, c1);
    bit c_8_11 = mux_2to1(c_8_9, c_10_11, c1);
    bit c_12_15 = mux_2to1(c_12_13, c_14_15, c1);

    bit c_0_7  = mux_2to1(c_0_3, c_4_7, c2);
    bit c_8_15 = mux_2to1(c_8_11, c_12_15, c2);

    flags->carry = mux_2to1(c_0_7, c_8_15, c3);

    /* --- Compute Overflow Flag ---
     *
     * Overflow is computed the same way for ADD, SUB, and CMP:
     *   Overflow = carry_into_MSB XOR carry_out_of_MSB
     *
     * For SUB and CMP, we use the raw carry_out from the adder,
     * not the inverted borrow flag.
     */
    bit overflow_add = compute_overflow_flag(carry_into_msb_add, carry_add);
    bit overflow_sub = compute_overflow_flag(carry_into_msb_sub, carry_sub);
    bit overflow_cmp = compute_overflow_flag(carry_into_msb_cmp, carry_cmp);

    bit overflow_select[16] = {
        overflow_add,       /* 0000: ADD */
        overflow_sub,       /* 0001: SUB */
        BIT_ZERO,           /* 0010: AND */
        BIT_ZERO,           /* 0011: OR */
        BIT_ZERO,           /* 0100: XOR */
        BIT_ZERO,           /* 0101: NAND */
        BIT_ZERO,           /* 0110: NOR */
        BIT_ZERO,           /* 0111: NOT_A */
        BIT_ZERO,           /* 1000: PASS_A */
        BIT_ZERO,           /* 1001: PASS_B */
        BIT_ZERO,           /* 1010: SHL */
        BIT_ZERO,           /* 1011: SHR */
        BIT_ZERO,           /* 1100: ROL */
        BIT_ZERO,           /* 1101: ROR */
        overflow_cmp,       /* 1110: CMP */
        BIT_ZERO            /* 1111: SYS */
    };

    bit o_0_1  = mux_2to1(overflow_select[0], overflow_select[1], c0);
    bit o_2_3  = mux_2to1(overflow_select[2], overflow_select[3], c0);
    bit o_4_5  = mux_2to1(overflow_select[4], overflow_select[5], c0);
    bit o_6_7  = mux_2to1(overflow_select[6], overflow_select[7], c0);
    bit o_8_9  = mux_2to1(overflow_select[8], overflow_select[9], c0);
    bit o_10_11 = mux_2to1(overflow_select[10], overflow_select[11], c0);
    bit o_12_13 = mux_2to1(overflow_select[12], overflow_select[13], c0);
    bit o_14_15 = mux_2to1(overflow_select[14], overflow_select[15], c0);

    bit o_0_3  = mux_2to1(o_0_1, o_2_3, c1);
    bit o_4_7  = mux_2to1(o_4_5, o_6_7, c1);
    bit o_8_11 = mux_2to1(o_8_9, o_10_11, c1);
    bit o_12_15 = mux_2to1(o_12_13, o_14_15, c1);

    bit o_0_7  = mux_2to1(o_0_3, o_4_7, c2);
    bit o_8_15 = mux_2to1(o_8_11, o_12_15, c2);

    flags->overflow = mux_2to1(o_0_7, o_8_15, c3);

    return 1;
}
