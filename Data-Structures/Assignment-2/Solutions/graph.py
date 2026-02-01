class Graph:
    def __init__(self, v):
        self.vertices = v
        self.adj_matrix = [[-1.0] * v for _ in range(v)] # [cite: 30]

    def add_edge(self, u, v, w):
        self.adj_matrix[u][v] = float(w)
        self.adj_matrix[v][u] = float(w) # Undirected [cite: 12]

    def get_weight(self, u, v):
        return self.adj_matrix[u][v] if self.adj_matrix[u][v] != -1.0 else None