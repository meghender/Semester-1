#!/bin/bash
# This script compiles the encoder and decoder C++ programs.
# The -O3 flag is used for high-level optimization.
g++ -std=c++11 -O3 encoder.cpp -o encoder
g++ -std=c++11 -O3 decoder.cpp -o decoder
