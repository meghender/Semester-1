# main.py
# This is the main program that runs everything
# It reads input, validates it, runs the algorithms, and prints results

import time
import sys
from graph_adt import Graph
from ford_fulkerson import ford_fulkerson

def read_matrix_from_file(filename):
    # This function reads a matrix from a text file
    # filename: name of the file to read
    # Returns: the matrix as a 2D list, or None if there's an error
    
    matrix = []
    
    # Try to open and read the file
    try:
        # Open file in read mode
        with open(filename, 'r') as file:
            # Read each line in the file
            for line in file:
                line = line.strip()  # Remove whitespace from ends
                
                # Skip empty lines
                if len(line) > 0:
                    # Split line by spaces/tabs and convert to integers
                    row = []
                    numbers = line.split()  # Split by any whitespace
                    for number_text in numbers:
                        try:
                            number = int(number_text)  # Convert text to integer
                            row.append(number)
                        except ValueError:
                            # This catches decimal numbers and text
                            print(f"Error: File '{filename}' contains non-integer values.")
                            print(f"Found invalid value: '{number_text}'")
                            return None
                    
                    # Only add row if it has elements
                    if len(row) > 0:
                        matrix.append(row)
    
    except FileNotFoundError:
        # File doesn't exist
        print(f"Error: File '{filename}' not found.")
        return None
    
    except Exception as error:
        # Any other unexpected error
        print(f"Error: Could not read file '{filename}'.")
        print(f"Details: {str(error)}")
        return None
    
    # Check if matrix is empty
    if len(matrix) == 0:
        print("Error: Input matrix is empty.")
        return None
    
    # Check if matrix is square (same number of rows and columns)
    number_of_rows = len(matrix)
    for i in range(len(matrix)):
        row = matrix[i]
        if len(row) != number_of_rows:
            print(f"Error: Matrix is not square.")
            print(f"Row {i+1} has {len(row)} elements, expected {number_of_rows}.")
            return None
    
    return matrix


def validate_network(matrix, source, sink):
    # This function checks if the network is valid
    # matrix: capacity matrix
    # source: source node
    # sink: sink node
    # Returns: True if valid, False if invalid
    
    number_of_nodes = len(matrix)
    
    # Check 1: Source and sink cannot be the same (unless only 1 node)
    if source == sink and number_of_nodes > 1:
        print(f"Error: Source and sink are the same node (Node {source}).")
        return False
    
    # Special case: if only 1 node, it's valid (max flow = 0)
    if number_of_nodes == 1:
        return True
    
    # ===== NEW: Check for negative capacities =====
    # This loop checks every cell in the matrix
    for i in range(number_of_nodes):
        for j in range(number_of_nodes):
            capacity = matrix[i][j]
            if capacity < 0:
                print(f"Error: Negative capacity found at position ({i}, {j}).")
                print(f"Capacity value: {capacity}")
                print("All capacities must be non-negative (>= 0).")
                return False
    
    # ===== NEW: Check for self-loops =====
    # Diagonal elements should all be zero (no node connects to itself)
    for i in range(number_of_nodes):
        if matrix[i][i] != 0:
            print(f"Error: Self-loop detected at node {i}.")
            print(f"Diagonal element matrix[{i}][{i}] = {matrix[i][i]} (should be 0).")
            print("A node cannot have an edge to itself.")
            return False
    
    # Check 2: Source should have NO incoming edges
    # This loop adds up all capacities coming INTO the source
    total_incoming_to_source = 0
    for from_node in range(number_of_nodes):
        total_incoming_to_source = total_incoming_to_source + matrix[from_node][source]
    
    if total_incoming_to_source > 0:
        print(f"Error: Invalid network.")
        print(f"The designated source (Node {source}) has incoming edges with total capacity {total_incoming_to_source}.")
        print("A true source should only have outgoing edges, no incoming edges.")
        return False
    
    # Check 3: Sink should have NO outgoing edges
    # This loop adds up all capacities going OUT of the sink
    total_outgoing_from_sink = 0
    for to_node in range(number_of_nodes):
        total_outgoing_from_sink = total_outgoing_from_sink + matrix[sink][to_node]
    
    if total_outgoing_from_sink > 0:
        print(f"Error: Invalid network.")
        print(f"The designated sink (Node {sink}) has outgoing edges with total capacity {total_outgoing_from_sink}.")
        print("A true sink should only have incoming edges, no outgoing edges.")
        return False
    
    # Check 4: No intermediate node should be an extra source or sink
    # This loop checks each node (except source and sink)
    for node in range(number_of_nodes):
        # Skip source and sink
        if node == source or node == sink:
            continue
        
        # Calculate total incoming capacity to this node
        total_incoming = 0
        for from_node in range(number_of_nodes):
            total_incoming = total_incoming + matrix[from_node][node]
        
        # Calculate total outgoing capacity from this node
        total_outgoing = 0
        for to_node in range(number_of_nodes):
            total_outgoing = total_outgoing + matrix[node][to_node]
        
        # If node has output but no input, it's an extra source (invalid)
        if total_incoming == 0 and total_outgoing > 0:
            print(f"Error: Invalid network.")
            print(f"Node {node} is an additional source (no incoming edges, but has outgoing).")
            print("There should be only one source in the network.")
            return False
        
        # If node has input but no output, it's an extra sink (invalid)
        if total_outgoing == 0 and total_incoming > 0:
            print(f"Error: Invalid network.")
            print(f"Node {node} is an additional sink (no outgoing edges, but has incoming).")
            print("There should be only one sink in the network.")
            return False
    
    # ===== NEW: Warning for very large capacities =====
    # Check if any capacity is extremely large (might cause overflow)
    max_safe_int = 2147483647  # Maximum 32-bit signed integer
    for i in range(number_of_nodes):
        for j in range(number_of_nodes):
            if matrix[i][j] > max_safe_int:
                print(f"Warning: Very large capacity at ({i}, {j}): {matrix[i][j]}")
                print("This might cause integer overflow issues.")
                # We don't return False, just warn the user
    
    # All checks passed!
    return True


def create_graph_from_matrix(matrix):
    # This function converts a capacity matrix into a Graph object
    # matrix: 2D list representing edge capacities
    # Returns: Graph object
    
    number_of_nodes = len(matrix)
    
    # Create new graph with specified number of nodes
    graph = Graph(number_of_nodes)
    
    # Add all edges from matrix to graph
    # This nested loop goes through each cell in the matrix
    for from_node in range(number_of_nodes):
        for to_node in range(number_of_nodes):
            capacity = matrix[from_node][to_node]
            
            # Only add edge if capacity is greater than 0
            if capacity > 0:
                graph.add_edge(from_node, to_node, capacity)
    
    return graph


def print_matrix(matrix):
    # This function prints a matrix in space-separated format
    # matrix: 2D list to print
    
    # This loop goes through each row
    for row in matrix:
        # Convert each number to string and join with spaces
        row_strings = []
        for number in row:
            row_strings.append(str(number))
        
        line = " ".join(row_strings)
        print(line)


def main():
    # This is the main function that coordinates everything
    
    # Check if user provided filename as command-line argument
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_filename>")
        print("Example: python main.py input.txt")
        sys.exit(1)
    
    # Get filename from command line
    input_filename = sys.argv[1]
    
    # STEP 1: Read the capacity matrix from file
    capacity_matrix = read_matrix_from_file(input_filename)
    
    # If reading failed, stop here
    if capacity_matrix is None:
        return
    
    # STEP 2: Set up source and sink
    number_of_nodes = len(capacity_matrix)
    source = 0                    # Source is always first node (node 0)
    sink = number_of_nodes - 1    # Sink is always last node
    
    # STEP 3: Validate the network structure
    if validate_network(capacity_matrix, source, sink) == False:
        return  # Stop if network is invalid
    
    # ===== RUN BFS VERSION (Edmonds-Karp) =====
    
    # Create graph for BFS
    graph_for_bfs = create_graph_from_matrix(capacity_matrix)
    
    # Record start time
    start_time_bfs = time.perf_counter()
    
    # Run Ford-Fulkerson with BFS
    max_flow_bfs, updated_graph_bfs = ford_fulkerson(graph_for_bfs, source, sink, 'BFS')
    
    # Record end time
    end_time_bfs = time.perf_counter()
    
    # Calculate runtime in milliseconds
    runtime_bfs = (end_time_bfs - start_time_bfs) * 1000
    
    # Get final flow matrix
    flow_matrix_bfs = updated_graph_bfs.get_flow_matrix()
    
    # Print results
    print(f"BFS (maximum flow value: {max_flow_bfs}; runtime: {runtime_bfs:.0f}ms)")
    print_matrix(flow_matrix_bfs)
    print()
    
    # ===== RUN DFS VERSION =====
    
    # Create new graph for DFS (must be fresh, not reuse BFS graph)
    graph_for_dfs = create_graph_from_matrix(capacity_matrix)
    
    # Record start time
    start_time_dfs = time.perf_counter()
    
    # Run Ford-Fulkerson with DFS
    max_flow_dfs, updated_graph_dfs = ford_fulkerson(graph_for_dfs, source, sink, 'DFS')
    
    # Record end time
    end_time_dfs = time.perf_counter()
    
    # Calculate runtime in milliseconds
    runtime_dfs = (end_time_dfs - start_time_dfs) * 1000
    
    # Get final flow matrix
    flow_matrix_dfs = updated_graph_dfs.get_flow_matrix()
    
    # Print results
    print(f"DFS (maximum flow value: {max_flow_dfs}; runtime: {runtime_dfs:.0f}ms)")
    print_matrix(flow_matrix_dfs)


# This is the entry point of the program
# When you run "python main.py", this code executes
if __name__ == "__main__":
    main()
