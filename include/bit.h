#ifndef BIT_H
#define BIT_H

#include <stdint.h>
#include <stddef.h>

/*
  The fundamental atom of bitcraft.
  A bit represents exactly two states: 0 or 1.

  `bit` is a distinct struct type, not a bare integer typedef,
  so the compiler rejects implicit conversion from arbitrary ints/bytes.
  The only way to obtain a `bit` is through bit_make() / bit_try_make(), which validate the input value.

  Changelog version: 0.1
 * Initial prototype

  Changelog version: 0.2
 * bit is now a 1-member struct, not unsigned char. No implicit conversion from arbitrary integers anymore.
 * bit_try_make replaces the assert-only path: returns 0/1 instead of aborting,
   so callers can handle bad input instead of the whole process dying.
 * bit_make kept as an assert-based constructor, but documented explicitly as "aborts, and is compiled out under NDEBUG",
   no longer pretending to be a validator.
 * bits_to_uint16 / uint16_to_bits now take an explicit bits_len parameter and reject calls where it isn't 16,
   array decay can no longer silently pass a short buffer.
 * Bit ordering (index 0 = LSB) is now documented in the header, not left implicit.
 * BIT_WORD_WIDTH replaces the hardcoded 16 throughout.
 * All functions return status codes instead of trusting/asserting; nothing crashes on bad data at these entry points.

 */
typedef struct {
    unsigned char v;
} bit;

#define BIT_ZERO ((bit){0})
#define BIT_ONE  ((bit){1})

/* Width, in bits, of the word-level helpers below. */
#define BIT_WORD_WIDTH 16

/* Convenience: number of elements in a stack-declared bit array. */
#define BITS_ARRAY_LEN(arr) (sizeof(arr) / sizeof((arr)[0]))

/*
 * Bit ordering convention used throughout bitcraft:
 * index 0 is the LEAST significant bit,
 * index (WIDTH-1) is the MOST significant bit.
 *  Anything that builds a bit[] array by hand must follow this convention.
 */

/*
 * Validate a raw value and, on success, write it into *out.
 * Returns 1 on success, 0 if value is not strictly 0 or 1
 * (in which case *out is left unmodified), never aborts the program.
 */
int bit_try_make(unsigned char value, bit *out);

/*
 * Construct a bit from a raw value.
 * This aborts via assert() on invalid input,
 * and that check is compiled OUT entirely if NDEBUG is defined.
 * Only use this where an invalid value means "programmer error, crash immediately"
 * e.g. literal constants in your own code.
 * For any value derived from outside the program (parsed, computed, read from a file, etc.)
 * use bit_try_make() instead, and handle the failure case explicitly.
 */
bit bit_make(unsigned char value);

/* Returns 1 if b holds the value 1, 0 if it holds 0. */
int bit_is_one(bit b);

/* Returns 1 if a and b hold the same value. */
int bit_equal(bit a, bit b);

/*
 * Convert between bit arrays and 16-bit integers.
 * bits[0] is the least significant bit;
 * bits[BIT_WORD_WIDTH-1] is the most significant bit.
 *
 * bits_len must equal BIT_WORD_WIDTH,
 * pass it explicitly (e.g. via BITS_ARRAY_LEN(my_array))
 * since arrays decay to pointers and the compiler cannot otherwise verify the caller passed 16 elements.
 *
 * Returns 1 on success. Returns 0 (and leaves *out unmodified)
 * if bits_len != BIT_WORD_WIDTH, if a pointer argument is NULL,
 * or if any element of bits[] is found to hold a value other than 0/1.
 */
int bits_to_uint16(const bit *bits, size_t bits_len, uint16_t *out);

/*
 * Fills bits[0 .. BIT_WORD_WIDTH) from value.
 * Returns 1 on success, 0 if bits_len != BIT_WORD_WIDTH or bits is NULL.
 */
int uint16_to_bits(uint16_t value, bit *bits, size_t bits_len);

#endif
