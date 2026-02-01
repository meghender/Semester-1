# bfs_path.py
# BFS stands for "Breadth-First Search"
# This algorithm explores nodes level by level, like ripples in water

from list_adt import List

def bfs_path(graph, start_node, end_node):
    # This function finds a path from start_node to end_node using BFS
    # graph: the Graph object containing our network
    # start_node: where we begin (usually node 0, the source)
    # end_node: where we want to reach (usually last node, the sink)
    # Returns: a List containing the path, or empty List if no path exists
    
    # parent_info keeps track of how we reached each node
    # parent_info[node] = (previous_node, edge_index) 
    # This helps us reconstruct the path later
    parent_info = []
    for node in range(graph.total_nodes):
        parent_info.append(-1)  # -1 means "not visited yet"
    
    # visited keeps track of which nodes we've already checked
    visited = []
    for node in range(graph.total_nodes):
        visited.append(False)  # Initially, no nodes are visited
    
    # queue holds nodes we need to explore
    # In BFS, we use a queue (first-in, first-out)
    queue = []
    
    # Start by adding the starting node to our queue
    queue.append(start_node)
    visited[start_node] = True  # Mark start as visited
    
    # This flag tells us if we found a path
    found_path = False
    
    # Main BFS loop - continues until queue is empty
    while len(queue) > 0:
        # Get the first node from queue (FIFO - First In First Out)
        current_node = queue.pop(0)
        
        # Check if we reached our destination
        if current_node == end_node:
            found_path = True
            break  # Stop searching, we found it!
        
        # Look at all edges going out from current_node
        # enumerate gives us both the index and the edge
        for edge_index in range(len(graph.adjacency_list[current_node])):
            edge = graph.adjacency_list[current_node][edge_index]
            
            # Extract edge information
            next_node = edge[0]          # Where this edge leads
            max_capacity = edge[1]       # Maximum flow capacity
            current_flow = edge[2]       # Current flow in edge
            reverse_pos = edge[3]        # Position of reverse edge
            
            # Calculate remaining capacity (how much more flow we can push)
            remaining_capacity = max_capacity - current_flow
            
            # Check if we can use this edge:
            # 1. Haven't visited next_node yet
            # 2. There's remaining capacity (can push more flow)
            if visited[next_node] == False and remaining_capacity > 0:
                visited[next_node] = True  # Mark as visited
                parent_info[next_node] = (current_node, edge_index)  # Remember how we got here
                queue.append(next_node)  # Add to queue to explore later
    
    # If we didn't find a path, return empty list
    if found_path == False:
        return List()
    
    # Reconstruct the path by going backwards from end to start
    path = []
    current = end_node
    
    # This loop goes backwards through parent_info
    # It continues until we reach the start node
    while current != start_node:
        path.append(current)  # Add current node to path
        previous_node, edge_idx = parent_info[current]  # Get parent info
        current = previous_node  # Move to parent
    
    path.append(start_node)  # Don't forget to add the start node
    
    # Reverse the path so it goes from start to end (not end to start)
    path.reverse()
    
    # Return the path wrapped in our List object
    return List(path)
