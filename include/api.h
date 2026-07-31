#ifndef API_H
#define API_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "bit.h"
#include "bus.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Standardized ALU Operation Codes
 * Maps directly to 4-bit control words (0x0 to 0xF)
 */
typedef enum {
    ALU_OP_ADD_VAL  = 0x0,
    ALU_OP_SUB_VAL  = 0x1,
    ALU_OP_AND_VAL  = 0x2,
    ALU_OP_OR_VAL   = 0x3,
    ALU_OP_XOR_VAL  = 0x4,
    ALU_OP_NAND_VAL = 0x5,
    ALU_OP_NOR_VAL  = 0x6,
    ALU_OP_NOT_VAL  = 0x7,
    ALU_OP_PASS_A_VAL = 0x8,
    ALU_OP_PASS_B_VAL = 0x9,
    ALU_OP_SHL_VAL  = 0xA,
    ALU_OP_SHR_VAL  = 0xB,
    ALU_OP_ROL_VAL  = 0xC,
    ALU_OP_ROR_VAL  = 0xD,
    ALU_OP_CMP_VAL  = 0xE,
    ALU_OP_SYS_VAL  = 0xF
} ALUOp;

/*
 * Machine Execution Modes
 */
typedef enum {
    MODE_NORMAL = 0,
    MODE_SATURATE = 1,
    MODE_SIGNED = 2,
    MODE_ROUND = 3,
    MODE_POLARITY_INVERT = 4
} MachineMode;

/*
 * Machine state
 * Full layout, direct mapping into Python ctypes/CFFI.
 */
typedef struct {
    Bus bus;                 /* System bus (memory size updated to 64K) */
    uint16_t pc;             /* Program counter (Python-managed) */
    uint64_t cycle_count;    /* Total execution cycles */
    uint8_t halted;          /* Halt flag (1 = halted) */

    /* Internal wire and signal inspection */
    bit alu_wires[64];       /* Gate-level ALU signal lines */
    bit bus_lines[16];       /* Active bus data lines */

    /* Runtime Configuration */
    uint8_t mode;
    uint8_t saturation_enabled;
    uint8_t signed_mode;
} Machine;

/* --- Lifecycle Management --- */
void machine_init(Machine* state);
void machine_reset(Machine* state);
int machine_load_program(Machine* state, const uint16_t* program, size_t count);

/* --- Execution Control --- */
int machine_step(Machine* state);
uint64_t machine_run(Machine* state, uint64_t max_cycles);
void machine_halt(Machine* state);

/* --- Core ALU Bridge --- */
int machine_alu_op(Machine* state, uint16_t src1, uint16_t src2, uint16_t dest, ALUOp op);

/* --- Memory & Register Access --- */
int machine_write(Machine* state, uint16_t addr, uint16_t value);
uint16_t machine_read(const Machine* state, uint16_t addr);
uint16_t machine_get_register(const Machine* state, uint8_t reg);
int machine_set_register(Machine* state, uint8_t reg, uint16_t value);

/* --- Inspection Helpers --- */
uint8_t machine_get_zero_flag(const Machine* state);
uint8_t machine_get_carry_flag(const Machine* state);
uint8_t machine_get_overflow_flag(const Machine* state);
uint8_t machine_get_wire(const Machine* state, uint8_t index);

/* --- Mode Management --- */
void machine_set_mode(Machine* state, MachineMode mode);
MachineMode machine_get_mode(const Machine* state);

/* --- Debug & Diagnostics --- */
void machine_snapshot(const Machine* state, uint16_t* memory_copy, uint16_t* registers_copy, uint16_t* flags);

int machine_alu_op_traced(Machine* state, uint16_t src1, uint16_t src2,
                          uint16_t dest, ALUOp op);

void machine_dump(Machine* state, uint16_t start, uint16_t end);
const char* machine_op_to_string(ALUOp op);

#ifdef __cplusplus
}
#endif

#endif /* API_H */
