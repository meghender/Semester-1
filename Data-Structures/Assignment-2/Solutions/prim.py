from graph import Graph

def Prims(G: Graph):
    n = G.vertices
    mst = Graph(n)
    in_mst = [False] * n
    lowcost = [float('inf')] * n
    closest = [-1] * n
    
    lowcost[0] = 0
    for _ in range(n):
        u = -1
        min_val = float('inf')
        for i in range(n):
            if not in_mst[i] and lowcost[i] < min_val:
                min_val, u = lowcost[i], i
        
        if u == -1: break
        in_mst[u] = True
        if closest[u] != -1:
            mst.add_edge(u, closest[u], G.get_weight(u, closest[u])) # [cite: 11]

        for v in range(n):
            wt = G.get_weight(u, v)
            if wt is not None and not in_mst[v] and wt < lowcost[v]:
                lowcost[v], closest[v] = wt, u
    return mst