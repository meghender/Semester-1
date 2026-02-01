# Assignment 3: Ford-Fulkerson Maximum Flow Algorithm

## Overview
This project implements the Ford-Fulkerson algorithm to find the maximum flow in a directed weighted network. It compares two strategies for finding augmenting paths:
1. Edmonds-Karp Algorithm: Uses Breadth-First Search (BFS).
2. DFS-based Ford-Fulkerson: Uses Depth-First Search (DFS).

The implementation adheres to the modular structure required by the assignment guidelines.

## Project Modules
The code is divided into 6 distinct components:
1. graph_adt.py: Implementation of the GRAPH ADT using adjacency lists.
2. list_adt.py: Implementation of the LIST ADT for path sequencing.
3. bfs_path.py: BFS-based pathfinding function.
4. dfs_path.py: Iterative DFS-based pathfinding to handle large n without recursion limits.
5. ford_fulkerson.py: Core algorithm that calculates maximum flow and returns a flow graph.
6. main.py: Top-level program for file I/O, network validation, and benchmarking.

## Requirements
- Python 3.x
- No external libraries required.

## How to Run
1. Place all .py files and your input capacity matrix file (e.g., input.txt) in the same directory.
2. Open the terminal and execute:
   ```bash
   python3 main.py <input_filename>



Example: python3 main.py input.txt

Input Format
The input should be an n x n capacity matrix in a text file where:

The first row/column corresponds to the Source.

The last row/column corresponds to the Sink.

Diagonal elements and unconnected vertices are 0.

Output Format
The program prints the flow matrices for both BFS and DFS versions, along with:

Maximum flow value.

Runtime in milliseconds (ms).


# Contributors :

Meghender Pal (2025AIB2563)

Siddharth (2025AIB2670)

