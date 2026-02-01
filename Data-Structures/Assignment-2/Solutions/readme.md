# Minimum Spanning Tree (MST) Solver - Prim's & Kruskal's

This project implements a modular system for finding the Minimum Spanning Tree (MST) of undirected weighted graphs. It includes full implementations of Prim's and Kruskal's algorithms, adhering to strict modular data structure requirements.

## [cite_start]File Structure [cite: 32]
The project consists of the following 6 core modules:
1. [cite_start]`graph.py`: Implementation of the GRAPH Abstract Data Type (ADT)[cite: 33].
2. [cite_start]`prim.py`: Prim's algorithm implementation[cite: 35].
3. [cite_start]`priorityqueue.py`: Min-Heap based PRIORITYQUEUE ADT used for edge selection[cite: 37].
4. [cite_start]`mfset.py`: Merge-Find Set (MFSET) ADT with path compression for cycle detection[cite: 38].
5. [cite_start]`kruskal.py`: Kruskal's algorithm implementation using PRIORITYQUEUE and MFSET[cite: 40].
6. [cite_start]`main.py`: Top-level driver program for reading input, execution, and benchmarking[cite: 43].

## Implementation Details
- [cite_start]**Graph Representation**: Uses an $n \times n$ cost matrix[cite: 30].
- **Edge Selection**: Handles undirected edges by scanning the upper triangular matrix to avoid double-counting.
- [cite_start]**Connectivity**: Filters out non-existent edges (marked as -1) and self-loops (marked as 0)[cite: 30].
- [cite_start]**Output**: Returns the total MST cost and runtime in milliseconds (ms)[cite: 43].

## Execution Instructions
1. Ensure all 6 Python files are in the same directory.
2. Prepare an input file (e.g., `input_graph.txt`) containing the cost matrix.
3. Run the following command in your terminal:

   ```bash
   python3 main.py input_graph.txt