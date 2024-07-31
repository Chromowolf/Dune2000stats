import numpy as np

def bron_kerbosch_with_pivot(R, P, X, neighbors, cliques):
    if not P and not X:
        cliques.append(R)
        return

    u = next(iter(P | X))  # P.union(X), select a pivot
    for v in P - neighbors[u]:  # P.difference(neighbors[u])
        new_neighbors = P & neighbors[v]  # P.intersection(neighbors[v])
        bron_kerbosch_with_pivot(R | {v}, new_neighbors, X & neighbors[v], neighbors, cliques)
        P.remove(v)
        X.add(v)

def find_maximal_cliques_with_pivot(graph):
    N = graph.shape[0]
    P = set(range(N))
    R = set()
    X = set()
    cliques = []
    neighbors = [set(np.nonzero(graph[v])[0]) - {v} for v in range(N)]  # [{neighbors of 1}, {neighbors of 2}, ...]
    bron_kerbosch_with_pivot(R, P, X, neighbors, cliques)
    return sorted(cliques, key=len, reverse=True)  # Sort by the size of the cliques in descending order


if __name__ == "__main__":
    # Example usage:
    graph_array = np.array([
        [0, 1, 0, 0, 1, 0],
        [1, 0, 0, 0, 1, 0],
        [0, 0, 0, 1, 1, 0],
        [0, 0, 1, 0, 1, 0],
        [1, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0]
    ])

    maximal_cliques_with_pivot = find_maximal_cliques_with_pivot(graph_array)
    maximal_cliques_with_pivot = [sorted(list(clique)) for clique in maximal_cliques_with_pivot]

    print("Maximal cliques in the graph with pivot optimization:", maximal_cliques_with_pivot)

    nrow = graph_array.shape[0]
    # Step 2: Vectorized comparison to set b[i,j] and b[j,i] to 1 where both a[i,j] and a[j,i] are 0
    # Use broadcasting to compare all pairs of elements in 'a'
    n_array = (graph_array == 0) & (graph_array.T == 0)
    print(n_array)
    print(find_maximal_cliques_with_pivot(n_array))
