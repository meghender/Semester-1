from graph import Graph
from priorityqueue import PriorityQueue
from mfset import MFSet

def Kruskal(G: Graph):
    n = G.vertices
    mst = Graph(n)
    pq = PriorityQueue()
    mf = MFSet()
    
    for i in range(n): mf.initial(i, i) # [cite: 18]
    for i in range(n):
        for j in range(i + 1, n): # Upper triangle to avoid duplicates
            wt = G.get_weight(i, j)
            if wt is not None: pq.insert(wt, (i, j))
    
    edges = 0
    while edges < n - 1 and not pq.is_empty():
        w, (u, v) = pq.remove_min()
        r1, r2 = mf.find(u), mf.find(v)
        if r1 != r2:
            mf.merge(r1, r2)
            mst.add_edge(u, v, w) # [cite: 26]
            edges += 1
    return mst