class PriorityQueue:
    def __init__(self):
        self.heap = [] # [cite: 19]

    def is_empty(self):
        return len(self.heap) == 0

    def insert(self, priority, value):
        self.heap.append((priority, value))
        self._up(len(self.heap) - 1)

    def remove_min(self):
        if self.is_empty(): return None
        root = self.heap[0]
        last = self.heap.pop()
        if not self.is_empty():
            self.heap[0] = last
            self._down(0)
        return root

    def _up(self, i):
        while i > 0:
            p = (i - 1) // 2
            if self.heap[i][0] < self.heap[p][0]:
                self.heap[i], self.heap[p] = self.heap[p], self.heap[i]
                i = p
            else: break

    def _down(self, i):
        n = len(self.heap)
        while True:
            l, r, s = 2*i+1, 2*i+2, i
            if l < n and self.heap[l][0] < self.heap[s][0]: s = l
            if r < n and self.heap[r][0] < self.heap[s][0]: s = r
            if s != i:
                self.heap[i], self.heap[s] = self.heap[s], self.heap[i]
                i = s
            else: break