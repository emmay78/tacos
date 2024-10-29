#!/bin/bash
set -e

## ******************************************************************************
## This source code is licensed under the MIT license found in the
## LICENSE file in the root directory of this source tree.
## ******************************************************************************

# find the absolute path to this script
PROJECT_DIR=$(dirname "$(realpath "$0")")
BUILD_DIR="$PROJECT_DIR/build"

# compile Chakra
function compile_chakra {
    protoc \
      --proto_path="$PROJECT_DIR/libs/chakra/schema/protobuf" \
      --cpp_out="$PROJECT_DIR/libs/chakra/schema/protobuf" \
      "$PROJECT_DIR/libs/chakra/schema/protobuf/et_def.proto"
}

# compile TACOS
function compile {
    cmake -S "$PROJECT_DIR" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
    cmake --build "$BUILD_DIR" --parallel $(nproc)
}

# run TACOS with an optional filename argument
function run {
    if [ -n "$1" ]; then
        ./build/bin/tacos "$1"
    else
        ./build/bin/tacos
    fi
}

# cleanup build
function cleanup {
    rm -f "$PROJECT_DIR/extern/chakra/schema/protobuf/et_def.pb.h"
    rm -f "$PROJECT_DIR/extern/chakra/schema/protobuf/et_def.pb.cc"
    rm -rf "$BUILD_DIR"
}

# help message
function print_help {
    echo "TACOS:"
    printf "\t--help (-h): Print this message\n"
    printf "\t--compile (-c): Compile TACOS\n"
    printf "\t--run (-r): Run the compiled TACOS executable\n"
    printf "\t--file (-f) <filename>: Run TACOS with the specified CSV file\n"
    printf "\t--clean (-l): Remove the TACOS build directory\n"
    printf "\t(noflag): Compile and execute TACOS\n"
}

# Variables for flags
filename=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -h|--help)
            print_help
            exit 0
            ;;
        -l|--clean)
            cleanup
            exit 0
            ;;
        -c|--compile)
            compile_chakra
            compile
            exit 0
            ;;
        -k|--chakra)
            compile_chakra
            exit 0
            ;;
        -r|--run)
            run "$filename"
            exit 0
            ;;
        -f|--file)
            if [ -n "$2" ]; then
                filename="$2"
                shift
            else
                echo "Error: --file requires a filename argument."
                exit 1
            fi
            ;;
        *)
            echo "[TACOS] Unknown flag: $1"
            print_help
            exit 1
            ;;
    esac
    shift
done

# If no flags, compile and run without filename
if [ -z "$filename" ]; then
    compile_chakra
    compile
    run
else
    compile_chakra
    compile
    run "$filename"
fi
