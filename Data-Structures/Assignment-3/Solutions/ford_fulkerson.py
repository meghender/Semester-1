# ford_fulkerson.py
# This file implements the Ford-Fulkerson algorithm for finding maximum flow
# Maximum flow = the maximum amount that can flow from source to sink

from bfs_path import bfs_path
from dfs_path import dfs_path

def ford_fulkerson(graph, source, sink, search_method):
    # This is the main Ford-Fulkerson algorithm
    # graph: the flow network
    # source: starting node (usually 0)
    # sink: ending node (usually last node)
    # search_method: either 'BFS' or 'DFS' for finding paths
    # Returns: (maximum_flow_value, updated_graph)
    
    # total_flow keeps track of total flow from source to sink
    total_flow = 0
    
    # Main loop - keeps finding paths until no more paths exist
    # This is the core of Ford-Fulkerson algorithm
    while True:
        
        # STEP 1: Find an augmenting path (a path with available capacity)
        if search_method == 'BFS':
            # Use BFS to find path (this makes it Edmonds-Karp algorithm)
            path_object = bfs_path(graph, source, sink)
        else:
            # Use DFS to find path
            path_object = dfs_path(graph, source, sink)
        
        # Get the actual list of nodes in the path
        path = path_object.get_items()
        
        # If path is empty, no more paths exist - we're done!
        if len(path) == 0:
            break  # Exit the while loop
        
        # STEP 2: Find the bottleneck (minimum capacity) along this path
        # The bottleneck is the edge with smallest remaining capacity
        # It limits how much flow we can push through this path
        
        bottleneck_capacity = float('inf')  # Start with infinity
        
        # This loop examines each edge in the path
        for i in range(len(path) - 1):
            from_node = path[i]      # Current node in path
            to_node = path[i + 1]    # Next node in path
            
            # Find the specific edge from from_node to to_node
            found_edge = None
            for edge in graph.adjacency_list[from_node]:
                if edge[0] == to_node:  # Check if edge goes to to_node
                    found_edge = edge
                    break  # Found it, stop looking
            
            # Calculate remaining capacity of this edge
            max_capacity = found_edge[1]
            current_flow = found_edge[2]
            remaining = max_capacity - current_flow
            
            # Update bottleneck if this edge has less capacity
            if remaining < bottleneck_capacity:
                bottleneck_capacity = remaining
        
        # STEP 3: Update flow along the entire path
        # Add bottleneck_capacity to total flow
        total_flow = total_flow + bottleneck_capacity
        
        # This loop updates flow on each edge in the path
        for i in range(len(path) - 1):
            from_node = path[i]
            to_node = path[i + 1]
            
            # Find and update the forward edge
            edge_updated = False
            for edge in graph.adjacency_list[from_node]:
                if edge[0] == to_node:  # This is the edge we want
                    # Increase flow by bottleneck amount
                    edge[2] = edge[2] + bottleneck_capacity
                    
                    # Get position of reverse edge
                    reverse_edge_position = edge[3]
                    
                    # Update reverse edge (decrease its flow)
                    # This allows algorithm to "undo" flow if needed
                    reverse_edge = graph.adjacency_list[to_node][reverse_edge_position]
                    reverse_edge[2] = reverse_edge[2] - bottleneck_capacity
                    
                    edge_updated = True
                    break  # Done updating this edge
            
            # This should never happen if our code is correct
            if edge_updated == False:
                raise Exception("Error: Could not find edge to update!")
    
    # Return both the total flow and the updated graph
    return total_flow, graph
