#!/bin/bash
set -e

SRC_DIR="."
BUILD_DIR="./build"
mkdir -p "$BUILD_DIR"
rm -rf "$BUILD_DIR"/*

# Compiler flags for shared library
# -fPIC: Position Independent Code (required for shared libraries)
# -O3: Maximum optimization
# -march=native: Optimize for current CPU
CFLAGS="-O3 -march=native -Wall -Wextra -std=c11 -fPIC"
LDFLAGS="-shared"
# Note: Removed -lm unless math library functions (like sqrt/pow) are actually called in your C files.

echo "[*] Compiling object files..."
gcc $CFLAGS -c "$SRC_DIR/bit.c" -o "$BUILD_DIR/bit.o"
gcc $CFLAGS -c "$SRC_DIR/gates.c" -o "$BUILD_DIR/gates.o"
gcc $CFLAGS -c "$SRC_DIR/adder.c" -o "$BUILD_DIR/adder.o"
gcc $CFLAGS -c "$SRC_DIR/mux.c" -o "$BUILD_DIR/mux.o"
gcc $CFLAGS -c "$SRC_DIR/alu.c" -o "$BUILD_DIR/alu.o"
gcc $CFLAGS -c "$SRC_DIR/bus.c" -o "$BUILD_DIR/bus.o"
gcc $CFLAGS -c "$SRC_DIR/api.c" -o "$BUILD_DIR/api.o"
gcc $LDFLAGS "$BUILD_DIR/bit.o" "$BUILD_DIR/gates.o" "$BUILD_DIR/adder.o" "$BUILD_DIR/mux.o" "$BUILD_DIR/alu.o" "$BUILD_DIR/bus.o" "$BUILD_DIR/api.o" -o "$BUILD_DIR/bc.so"

echo "Build complete: $BUILD_DIR/bc.so"
