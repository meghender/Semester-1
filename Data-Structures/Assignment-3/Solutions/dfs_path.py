# dfs_path.py
# DFS stands for "Depth-First Search"
# This algorithm explores as far as possible along each path before backtracking

import sys
from list_adt import List

# Increase recursion limit because DFS uses recursion (function calling itself)
# Default limit is 1000, we increase it to 2000 for deeper paths
sys.setrecursionlimit(2000)

def dfs_path(graph, start_node, end_node):
    # This function finds a path from start_node to end_node using DFS
    # graph: the Graph object containing our network
    # start_node: where we begin (source)
    # end_node: where we want to reach (sink)
    # Returns: a List containing the path, or empty List if no path exists
    
    # visited keeps track of which nodes we've already explored
    visited = []
    for node in range(graph.total_nodes):
        visited.append(False)  # Initially no nodes are visited
    
    # path will store the nodes we visit in order
    path = []
    
    # Define a helper function that does the actual recursive DFS
    def explore_path(current_node):
        # This is a recursive function - it calls itself!
        # current_node: the node we're currently exploring
        # Returns: True if we found a path to end_node, False otherwise
        
        # Mark current node as visited
        visited[current_node] = True
        
        # Add current node to our path
        path.append(current_node)
        
        # Check if we reached our destination
        if current_node == end_node:
            return True  # Success! We found the path
        
        # Explore all edges from current_node
        # This loop checks each possible next step
        for edge_index in range(len(graph.adjacency_list[current_node])):
            edge = graph.adjacency_list[current_node][edge_index]
            
            # Extract information from edge
            next_node = edge[0]          # Where this edge goes
            max_capacity = edge[1]       # Maximum capacity
            current_flow = edge[2]       # Current flow
            reverse_pos = edge[3]        # Reverse edge position
            
            # Calculate how much capacity is left
            remaining_capacity = max_capacity - current_flow
            
            # Check if we can use this edge:
            # 1. Haven't visited next_node yet
            # 2. There's remaining capacity
            if visited[next_node] == False and remaining_capacity > 0:
                # Recursively explore from next_node
                # If this finds a path to end_node, return True immediately
                if explore_path(next_node) == True:
                    return True  # Path found through this edge!
        
        # If we get here, none of the edges led to end_node
        # Backtrack: remove current_node from path
        path.pop()
        return False  # No path found from this node
    
    # Start the recursive exploration from start_node
    if explore_path(start_node) == True:
        # Path was found! Return it wrapped in List object
        return List(path)
    else:
        # No path exists, return empty List
        return List()
