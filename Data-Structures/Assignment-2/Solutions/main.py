import sys, time
from graph import Graph
from prim import Prims
from kruskal import Kruskal

def read_matrix(file):
    with open(file, 'r') as f:
        return [list(map(float, line.split())) for line in f if line.strip()]

def main():
    if len(sys.argv) < 2: return
    matrix = read_matrix(sys.argv[1]) # [cite: 31]
    n = len(matrix)
    g = Graph(n)
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] > 0: g.add_edge(i, j, matrix[i][j])

    for algo_name, func in [("Prim's", Prims), ("Kruskal's", Kruskal)]:
        start = time.time()
        mst = func(g)
        runtime = (time.time() - start) * 1000
        total_cost = 0
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                wt = mst.get_weight(i, j)
                if wt: 
                    total_cost += wt
                    edges.append((i+1, j+1)) # 1-based indexing [cite: 46]
        
        print(f"{algo_name} algorithm MST (total cost: {total_cost:.1f}; runtime: {runtime:.2f}ms)")
        for u, v in edges: print(f"({u},{v})") # [cite: 49, 57]

if __name__ == "__main__": main()