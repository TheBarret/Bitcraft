#include "include/bus.h"
#include <stdio.h>
#include <string.h>

void bus_init(Bus* bus) {
    memset(bus->memory, 0, sizeof(bus->memory));
    bus->addr_a   = 0;
    bus->addr_b   = 0;
    bus->addr_dest = 0;
    bus->flags.zero     = BIT_ZERO;
    bus->flags.carry    = BIT_ZERO;
    bus->flags.overflow = BIT_ZERO;
}

int bus_write(Bus* bus, uint16_t addr, uint16_t value) {
    // Todo: better value validation
    // if MEMORY_SIZE = 65536
    //if (addr >= MEMORY_SIZE) { // never happens
    //    return 0;
    //}
    bus->memory[addr] = value;
    return 1;
}

uint16_t bus_read(const Bus* bus, uint16_t addr) {
    // Todo: better value validation
    // if MEMORY_SIZE = 65536
    //if (addr >= MEMORY_SIZE) { // never happens
    //    return 0;
    //}
    return bus->memory[addr];
}

int bus_execute(Bus* bus, const bit control[4]) {
    /* Validate addresses */

    // Todo: better value validation
    // if MEMORY_SIZE = 65536

    //if (bus->addr_a >= MEMORY_SIZE || // never happens
    //    bus->addr_b >= MEMORY_SIZE || // never happens
    //    bus->addr_dest >= MEMORY_SIZE) { // never happens
    //    return 0;
    //}

    /* Convert operands from uint16_t to bit[] arrays */
    bit A[BIT_WORD_WIDTH];
    bit B[BIT_WORD_WIDTH];
    bit result[BIT_WORD_WIDTH];

    if (!uint16_to_bits(bus->memory[bus->addr_a], A, BIT_WORD_WIDTH)) {
        return 0;
    }
    if (!uint16_to_bits(bus->memory[bus->addr_b], B, BIT_WORD_WIDTH)) {
        return 0;
    }

    /* Run the ALU */
    alu_flags alu_f;
    if (!alu_forward(A, B, BIT_WORD_WIDTH, control, result, &alu_f)) {
        return 0;
    }

    /* Convert result back and store */
    uint16_t out;
    if (!bits_to_uint16(result, BIT_WORD_WIDTH, &out)) {
        return 0;
    }
    bus->memory[bus->addr_dest] = out;

    /* Update flags */
    bus->flags.zero     = alu_f.zero;
    bus->flags.carry    = alu_f.carry;
    bus->flags.overflow = alu_f.overflow;

    return 1;
}

int bus_alu_op(Bus* bus, uint16_t addr_a, uint16_t addr_b, uint16_t addr_dest, const bit control[4]) {
    bus->addr_a   = addr_a;
    bus->addr_b   = addr_b;
    bus->addr_dest = addr_dest;
    return bus_execute(bus, control);
}

int bus_load_immediate(Bus* bus, uint16_t addr, uint16_t value) { return bus_write(bus, addr, value); }

// update 0.3: load program from console
int bus_load_program(Bus* bus, const uint16_t* words, size_t count) {
    if (bus == NULL || words == NULL) {
        return 0;
    }
    if (count > (size_t)(MEMORY_SIZE - PROGRAM_START)) {
        return 0;
    }
    for (size_t i = 0; i < count; i++) {
        if (!bus_write(bus, (uint16_t)(PROGRAM_START + i), words[i])) {
            return 0;
        }
    }
    return 1;
}

void bus_dump(const Bus* bus, uint16_t start, uint16_t end) {
    // Todo: better value validation
    // if MEMORY_SIZE = 65536
    //if (start >= MEMORY_SIZE) start = MEMORY_SIZE - 1; // never happens
    //if (end   >= MEMORY_SIZE) end   = MEMORY_SIZE - 1; // never happens
    if (start > end) return;

    printf("Bus memory dump [%03u..%03u]:\n", start, end);
    for (uint16_t i = start; i <= end; i++) {
        printf("  [%03u] = 0x%04X", i, bus->memory[i]);
        if (i < NUM_REGISTERS) {
            printf("  (R%u)", i);
        }
        printf("\n");
    }
}
