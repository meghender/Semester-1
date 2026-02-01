# graph_adt.py
# This file contains the Graph class for representing a flow network
# A flow network is like a system of pipes where water flows from source to sink

class Graph:
    
    def __init__(self, number_of_nodes):
        # This function initializes our graph with a fixed number of nodes
        # number_of_nodes: how many nodes (vertices) are in the graph
        
        self.total_nodes = number_of_nodes
        
        # adjacency_list stores all the edges for each node
        # Each node has a list of edges going out from it
        # Each edge is stored as: [destination_node, max_capacity, current_flow, reverse_edge_position]
        self.adjacency_list = []
        
        # Create empty list for each node
        # This loop runs once for each node in the graph
        for node in range(number_of_nodes):
            self.adjacency_list.append([])  # Add empty list for this node
    
    def add_edge(self, from_node, to_node, max_capacity):
        # This function adds an edge (connection) between two nodes
        # from_node: the starting node
        # to_node: the ending node  
        # max_capacity: maximum flow this edge can handle
        
        # For flow networks, we need both forward and backward edges
        
        # Forward edge: represents actual pipe from from_node to to_node
        # Format: [destination, capacity, current_flow, where_is_reverse_edge]
        forward_edge = [to_node, max_capacity, 0, len(self.adjacency_list[to_node])]
        
        # Backward edge: used for algorithm (allows "undoing" flow)
        # Format: [destination, capacity, current_flow, where_is_forward_edge]
        backward_edge = [from_node, 0, 0, len(self.adjacency_list[from_node])]
        
        # Add forward edge to from_node's list
        self.adjacency_list[from_node].append(forward_edge)
        
        # Add backward edge to to_node's list
        self.adjacency_list[to_node].append(backward_edge)
    
    def get_flow_matrix(self):
        # This function creates a 2D matrix showing the flow between all nodes
        # Returns a matrix where flow_matrix[i][j] = flow from node i to node j
        
        # Create empty matrix filled with zeros
        flow_matrix = []
        for i in range(self.total_nodes):
            row = []
            for j in range(self.total_nodes):
                row.append(0)  # Initialize all flows to 0
            flow_matrix.append(row)
        
        # Fill in the actual flow values
        # This outer loop goes through each node
        for current_node in range(self.total_nodes):
            # This inner loop goes through all edges from current_node
            for edge in self.adjacency_list[current_node]:
                destination = edge[0]        # Where this edge goes
                capacity = edge[1]           # Max flow allowed
                current_flow = edge[2]       # How much is flowing now
                reverse_position = edge[3]   # Position of reverse edge
                
                # Only record positive flows (actual flow, not reverse flow)
                if current_flow > 0:
                    flow_matrix[current_node][destination] = current_flow
        
        return flow_matrix
