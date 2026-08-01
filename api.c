#include "include/api.h"
#include <string.h>
#include <stdio.h>
#include <inttypes.h>

// trace carry chain support
#include "include/wires.h"
#include "include/adder.h"


/* Helper to convert ALUOp to control bits */
static void op_to_control(ALUOp op, bit control[4]) {
    uint8_t val = (uint8_t)op & 0x0F;
    for (int i = 0; i < 4; i++) {
        control[i] = (val >> i) & 1 ? BIT_ONE : BIT_ZERO;
    }
}

/* Helper to convert bit to uint8_t - bit is a struct with 'v' member */
static inline uint8_t bit_to_uint8(bit b) {
    return b.v ? 1 : 0;
}

/* Helper to convert uint8_t to bit */
static inline bit uint8_to_bit(uint8_t val) {
    return (bit){val ? 1 : 0};
}

/* Initialize machine */
void machine_init(Machine* state) {
    if (!state) return;

    memset(state, 0, sizeof(Machine));
    bus_init(&state->bus);

    state->pc = PROGRAM_START;
    state->cycle_count = 0;
    state->halted = 0;
    state->mode = MODE_NORMAL;
    state->saturation_enabled = 0;
    state->signed_mode = 0;

    /* Initialize wire arrays */
    memset(state->alu_wires, 0, sizeof(state->alu_wires));
    memset(state->bus_lines, 0, sizeof(state->bus_lines));
}

/* Reset machine */
void machine_reset(Machine* state) {
    if (!state) return;
    machine_init(state);
}

/* Load program */
int machine_load_program(Machine* state, const uint16_t* program, size_t count) {
    if (!state || !program) return 0;
    return bus_load_program(&state->bus, program, count);
}

/* Execute one step */
int machine_step(Machine* state) {
    if (!state || state->halted) return 0;

    /* Fetch instruction from memory */
    // Todo: better value validation
    // if MEMORY_SIZE = 65536
    if (state->pc >= MEMORY_SIZE) { // never happens
        state->halted = 1;
        return 0;
    }

    uint16_t instruction = bus_read(&state->bus, state->pc);
    state->pc++;
    state->cycle_count++;

    /* Decode and execute instruction */
    /* Format: [15:12] = ALUOp, [11:8] = dest, [7:4] = src1, [3:0] = src2 */
    ALUOp op = (ALUOp)((instruction >> 12) & 0x0F);
    uint16_t dest = (instruction >> 8) & 0x0F;
    uint16_t src1 = (instruction >> 4) & 0x0F;
    uint16_t src2 = instruction & 0x0F;

    /* Execute ALU operation */
    return machine_alu_op(state, src1, src2, dest, op);
}

/* Run for N cycles */
uint64_t machine_run(Machine* state, uint64_t max_cycles) {
    if (!state) return 0;

    uint64_t cycles_executed = 0;
    while (cycles_executed < max_cycles && !state->halted) {
        if (!machine_step(state)) {
            break;
        }
        cycles_executed++;
    }

    return cycles_executed;
}

/* Halt execution */
void machine_halt(Machine* state) {
    if (state) state->halted = 1;
}

/* Core ALU operation */
int machine_alu_op(Machine* state, uint16_t src1, uint16_t src2,
                   uint16_t dest, ALUOp op) {
    if (!state) return 0;

    bit control[4];
    op_to_control(op, control);

    /* Execute through bus */
    return bus_alu_op(&state->bus, src1, src2, dest, control);
}

/* Memory operations */
int machine_write(Machine* state, uint16_t addr, uint16_t value) {
    if (!state) return 0;
    return bus_write(&state->bus, addr, value);
}

uint16_t machine_read(const Machine* state, uint16_t addr) {
    if (!state) return 0;
    return bus_read(&state->bus, addr);
}

/* Register access */
uint16_t machine_get_register(const Machine* state, uint8_t reg) {
    if (!state || reg >= NUM_REGISTERS) return 0;
    return bus_read(&state->bus, reg);
}

int machine_set_register(Machine* state, uint8_t reg, uint16_t value) {
    if (!state || reg >= NUM_REGISTERS) return 0;
    return bus_write(&state->bus, reg, value);
}

/* Flag inspection */
uint8_t machine_get_zero_flag(const Machine* state) {
    if (!state) return 0;
    return bit_to_uint8(state->bus.flags.zero);
}

uint8_t machine_get_carry_flag(const Machine* state) {
    if (!state) return 0;
    return bit_to_uint8(state->bus.flags.carry);
}

uint8_t machine_get_overflow_flag(const Machine* state) {
    if (!state) return 0;
    return bit_to_uint8(state->bus.flags.overflow);
}

/* Wire inspection */
uint8_t machine_get_wire(const Machine* state, uint8_t index) {
    if (!state || index >= 64) return 0;
    return bit_to_uint8(state->alu_wires[index]);
}

/* Mode management */
void machine_set_mode(Machine* state, MachineMode mode) {
    if (!state) return;
    state->mode = mode;

    /* TODO: Use SYS instruction to reconfigure ALU safely within valid RAM range
    bit control[4];
    op_to_control(ALU_OP_SYS_VAL, control);

    uint16_t mode_val = (uint16_t)mode;
    uint16_t scratch_addr1 = MEMORY_SIZE - 2;
    uint16_t scratch_addr2 = MEMORY_SIZE - 1;

    bus_load_immediate(&state->bus, scratch_addr1, mode_val);
    bus_alu_op(&state->bus, scratch_addr1, scratch_addr2, scratch_addr2, control);
    */
}

MachineMode machine_get_mode(const Machine* state) {
    if (!state) return MODE_NORMAL;
    return (MachineMode)state->mode;
}

/* Snapshot operations */
void machine_snapshot(const Machine* state, uint16_t* memory_copy,
                      uint16_t* registers_copy, uint16_t* flags) {
    if (!state) return;

    if (memory_copy) {
        memcpy(memory_copy, state->bus.memory, sizeof(state->bus.memory));
    }

    if (registers_copy) {
        for (int i = 0; i < NUM_REGISTERS; i++) {
            registers_copy[i] = bus_read(&state->bus, i);
        }
    }

    if (flags) {
        flags[0] = bit_to_uint8(state->bus.flags.zero);
        flags[1] = bit_to_uint8(state->bus.flags.carry);
        flags[2] = bit_to_uint8(state->bus.flags.overflow);
    }
}

/* Trace carry chain support */
static void trace_carry_chain(uint16_t a_val, uint16_t b_val, bit carry_in,
                               bit wires_out[BIT_WORD_WIDTH]) {
    bit A[BIT_WORD_WIDTH], B[BIT_WORD_WIDTH];
    uint16_to_bits(a_val, A, BIT_WORD_WIDTH);
    uint16_to_bits(b_val, B, BIT_WORD_WIDTH);

    bit carry = carry_in;
    for (size_t i = 0; i < BIT_WORD_WIDTH; i++) {
        full_adder_result fa = full_adder(A[i], B[i], carry);
        wires_out[i] = fa.carry_out;
        carry = fa.carry_out;
    }
}

int machine_alu_op_traced(Machine* state, uint16_t src1, uint16_t src2,
                          uint16_t dest, ALUOp op) {
    if (!state) return 0;

    /* Read operands BEFORE the op runs — dest may alias src1/src2 */
    uint16_t a_val = bus_read(&state->bus, src1);
    uint16_t b_val = bus_read(&state->bus, src2);

    bit control[4];
    op_to_control(op, control);

    int ok = bus_alu_op(&state->bus, src1, src2, dest, control);
    if (!ok) return 0;

    /* --- Control-bit wires --- */
    for (int i = 0; i < 4; i++) {
        state->alu_wires[WIRE_CONTROL_BASE + i] = control[i];
    }

    /* --- Result wires: read back what was actually written --- */
    bit result_bits[BIT_WORD_WIDTH];
    uint16_to_bits(bus_read(&state->bus, dest), result_bits, BIT_WORD_WIDTH);
    for (int i = 0; i < BIT_WORD_WIDTH; i++) {
        state->alu_wires[WIRE_RESULT_BASE + i] = result_bits[i];
    }

    /* --- Carry-chain wires: only meaningful for ADD/SUB/CMP --- */
    if (op == ALU_OP_ADD_VAL || op == ALU_OP_SUB_VAL || op == ALU_OP_CMP_VAL) {
        bit carry_in = (op == ALU_OP_ADD_VAL) ? BIT_ZERO : BIT_ONE;
        uint16_t b_operand = (op == ALU_OP_ADD_VAL) ? b_val : (uint16_t)(~b_val);
        bit carry_wires[BIT_WORD_WIDTH];
        trace_carry_chain(a_val, b_operand, carry_in, carry_wires);
        for (int i = 0; i < BIT_WORD_WIDTH; i++) {
            state->alu_wires[WIRE_CARRY_BASE + i] = carry_wires[i];
        }
    } else {
        for (int i = 0; i < BIT_WORD_WIDTH; i++) {
            state->alu_wires[WIRE_CARRY_BASE + i] = BIT_ZERO;
        }
    }

    /* --- Flags, straight from the real result --- */
    state->alu_wires[WIRE_ZERO]       = state->bus.flags.zero;
    state->alu_wires[WIRE_CARRY_FLAG] = state->bus.flags.carry;
    state->alu_wires[WIRE_OVERFLOW]   = state->bus.flags.overflow;

    return 1;
}

/* Debug helpers */
void machine_dump(Machine* state, uint16_t start, uint16_t end) {
    if (!state) return;
    bus_dump(&state->bus, start, end);
    printf("\n***[Dump]*****************************************\n");
    printf("\nMachine:\n");
    printf("  PC: 0x%04X\n", state->pc);
    printf("  Cycles: %" PRIu64 "\n", state->cycle_count);
    printf("  Halted: %s\n", state->halted ? "Yes" : "No");
    printf("  Mode: %d\n", state->mode);
    printf("  Flags: Z=%d C=%d O=%d\n",
           bit_to_uint8(state->bus.flags.zero),
           bit_to_uint8(state->bus.flags.carry),
           bit_to_uint8(state->bus.flags.overflow));
    printf("Registers:\n");
    for (int i = 0; i < NUM_REGISTERS; i++) {
        printf(" R%d = 0x%04X\n", i, bus_read(&state->bus, i));
    }
}

const char* machine_op_to_string(ALUOp op) {
    switch(op) {
        case ALU_OP_ADD_VAL: return "ADD";
        case ALU_OP_SUB_VAL: return "SUB";
        case ALU_OP_AND_VAL: return "AND";
        case ALU_OP_OR_VAL: return "OR";
        case ALU_OP_XOR_VAL: return "XOR";
        case ALU_OP_NAND_VAL: return "NAND";
        case ALU_OP_NOR_VAL: return "NOR";
        case ALU_OP_NOT_VAL: return "NOT";
        case ALU_OP_PASS_A_VAL: return "PASS_A";
        case ALU_OP_PASS_B_VAL: return "PASS_B";
        case ALU_OP_SHL_VAL: return "SHL";
        case ALU_OP_SHR_VAL: return "SHR";
        case ALU_OP_ROL_VAL: return "ROL";
        case ALU_OP_ROR_VAL: return "ROR";
        case ALU_OP_CMP_VAL: return "CMP";
        case ALU_OP_SYS_VAL: return "SYS";
        default: return "UNKNOWN";
    }
}
