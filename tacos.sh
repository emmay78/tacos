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

# run TACOS with filename and the chosen flag
function run {
    if [ -z "$1" ]; then
        echo "Error: Filename is required for running."
        print_help
        exit 1
    fi
    
    # Run with the appropriate flag
    if [ "$greedy" = true ]; then
        ./build/bin/tacos "$1" --greedy "$2" # Run with filename and greedy flag
    elif [ -n "$multiple" ]; then
        ./build/bin/tacos "$1" --multiple "$multiple" "$2" # Run with filename and multiple
    elif [ -n "$beam" ]; then
        ./build/bin/tacos "$1" --beam "$beam" "$2" # Run with filename and beam
    else
        ./build/bin/tacos "$1" "$2" # Run with filename only
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
    printf "\t--run (-r): Run the compiled TACOS executable (requires --file, and optionally one of --beam, --multiple, or --greedy)\n"
    printf "\t--file (-f) <filename>: Specify the CSV file for TACOS\n"
    printf "\t--beam (-b) <integer>: Specify the beam integer for TACOS\n"
    printf "\t--multiple (-m) <integer>: Specify the multiple integer for TACOS\n"
    printf "\t--greedy (-g): Run TACOS in greedy mode\n"
    printf "\t--clean (-l): Remove the TACOS build directory\n"
    printf "\t(noflag): Compile and execute TACOS with required parameters\n"
}

# Variables for flags
filename=""
beam=""
multiple=""
greedy=false
verbose=false

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

        -v|--verbose)
            verbose=true
            ;;
        -r|--run)
            # Ensure filename is provided
            if [ -z "$filename" ]; then
                echo "Error: --run requires --file to be specified."
                print_help
                exit 1
            fi
            if [ "$verbose" = true ]; then
                run "$filename" "--verbose"
            else
                run "$filename"
            fi
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
        -b|--beam)
            if [ -n "$beam" ] || [ -n "$multiple" ] || [ "$greedy" = true ]; then
                echo "Error: Only one of --beam, --multiple, or --greedy can be specified."
                print_help
                exit 1
            fi
            if [[ "$2" =~ ^[0-9]+$ ]]; then
                beam="$2"
                shift
            else
                echo "Error: --beam requires an integer argument."
                exit 1
            fi
            ;;
        -m|--multiple)
            if [ -n "$beam" ] || [ -n "$multiple" ] || [ "$greedy" = true ]; then
                echo "Error: Only one of --beam, --multiple, or --greedy can be specified."
                print_help
                exit 1
            fi
            if [[ "$2" =~ ^[0-9]+$ ]]; then
                multiple="$2"
                shift
            else
                echo "Error: --multiple requires an integer argument."
                exit 1
            fi
            ;;
        -g|--greedy)
            if [ -n "$beam" ] || [ -n "$multiple" ] || [ "$greedy" = true ]; then
                echo "Error: Only one of --beam, --multiple, or --greedy can be specified."
                print_help
                exit 1
            fi
            greedy=true
            ;;
        *)
            echo "[TACOS] Unknown flag: $1"
            print_help
            exit 1
            ;;
    esac
    shift
done
# Ensure that filename is provided
if [ -z "$filename" ]; then
    echo "Error: --file is required to run TACOS."
    print_help
    exit 1
else
    compile_chakra
    compile
    if [ "$verbose" = true ]; then
        run "$filename" "--verbose"
    else
        run "$filename"
    fi
fi
