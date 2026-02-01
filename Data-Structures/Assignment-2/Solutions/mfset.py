class MFSet:
    def __init__(self):
        self.parent = {} # [cite: 22]

    def initial(self, name, x):
        self.parent[x] = x # Each vertex starts in its own set [cite: 23]

    def find(self, x):
        if self.parent[x] == x: return x
        self.parent[x] = self.find(self.parent[x]) # Path Compression [cite: 23]
        return self.parent[x]

    def merge(self, root1, root2):
        if root1 != root2: self.parent[root2] = root1