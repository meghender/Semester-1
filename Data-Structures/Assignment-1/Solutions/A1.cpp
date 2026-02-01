#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// ----------------LIST ADT--------------------
struct node{
    int data;
    node* next;  
};

void makenull(node* &L){
    L = new node;
    L -> next = NULL; // Changed nullptr to NULL for older standards
}

void insert_end(node* L, int x){
    node* new_node = new node;
    new_node->data= x;
    new_node->next= NULL;
    node* temp = L;
    while (temp->next != NULL) temp = temp->next;
    temp->next = new_node;  
}

node* first(node* L) { return L->next; }

node* next_node(node* p) {
    if (p == NULL) return NULL;
    return p->next;
}

// ----------------GRAPH ADT--------------------
struct Graph {
    int n;          
    node** adj;     
};

void construct_graph(Graph &G, int n){
    G.n=n;
    G.adj = new node*[n];
    for (int i = 0; i < n; i++) makenull(G.adj[i]);
}

int get_degree(Graph &G, int u) {
    int d = 0;
    node* curr = first(G.adj[u]);
    while (curr != NULL) {
        d++;
        curr = next_node(curr);
    }
    return d;
}

// ----------------LOGIC------------------------------------
struct Match {
    int first_team;
    int second_team;
};

// Global-ish graph to help sorting in older C++
Graph* global_G_ptr;
bool compareNodes(int a, int b) {
    return get_degree(*global_G_ptr, a) > get_degree(*global_G_ptr, b);
}

// ----------------MAIN------------------------------------
int main() {
    int n;
    if (!(cin >> n) || n < 2) return 0;

    vector<Match> matches;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            if (i != j) {
                Match m; m.first_team = i; m.second_team = j;
                matches.push_back(m);
            }
        }
    }

    Graph G;
    construct_graph(G, (int)matches.size());
    for (size_t u = 0; u < matches.size(); u++) {
        for (size_t v = u + 1; v < matches.size(); v++) {
            if (matches[u].first_team == matches[v].first_team || 
                matches[u].first_team == matches[v].second_team || 
                matches[u].second_team == matches[v].first_team || 
                matches[u].second_team == matches[v].second_team) {
                insert_end(G.adj[u], (int)v);
                insert_end(G.adj[v], (int)u);
            }
        }
    }

    // Greedy Coloring
    int m_count = G.n;
    vector<int> order(m_count);
    vector<int> color(m_count, -1);
    for (int i = 0; i < m_count; i++) order[i] = i;

    global_G_ptr = &G;
    sort(order.begin(), order.end(), compareNodes);

    for (int i = 0; i < m_count; i++) {
        int v = order[i];
        vector<bool> used(m_count + 2, false);
        for (node* p = first(G.adj[v]); p; p = next_node(p)) {
            if (color[p->data] != -1) used[color[p->data]] = true;
        }
        int c = 1;
        while (used[c]) c++;
        color[v] = c;
    }

    int max_days = 0;
    for (int i = 0; i < m_count; i++) if (color[i] > max_days) max_days = color[i];

    // Final Output (Fixed format and compatibility)
    for (int d = 1; d <= max_days; d++) {
        bool first_in_line = true;
        for (int i = 0; i < m_count; i++) {
            if (color[i] == d) {
                if (!first_in_line) cout << "; ";
                cout << "(" << matches[i].first_team << matches[i].second_team << ")";
                first_in_line = false;
            }
        }
        cout << "\n";
        if (d < max_days) cout << "\n";
    }

    // Cleanup
    for (int i = 0; i < G.n; i++) {
        node* curr = G.adj[i];
        while (curr) {
            node* temp = curr;
            curr = curr->next;
            delete temp;
        }
    }
    delete[] G.adj;

    return 0;
}