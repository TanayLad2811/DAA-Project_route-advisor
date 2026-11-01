import random

import networkx as nx
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from app.algorithms.astar import run_astar
from app.algorithms.bfs import run_bfs
from app.algorithms.dfs import run_dfs
from app.algorithms.dijkstra import run_dijkstra
from app.algorithms.graph_ds import AdjacencyGraph
from app.schemas.graph import Edge, Graph, Node, NodeType
from app.schemas.route import RouteOptions


def make_diamond_graph() -> Graph:
    """Diamond graph:
         1
       /   \
      0     3 (exit)
       \\   /
         2
    Path 0-1-3 has weight 10 + 10 = 20
    Path 0-2-3 has weight 2 + 3 = 5
    """
    nodes = [
        Node(id=0, x=0.0, y=10.0, type=NodeType.START),
        Node(id=1, x=10.0, y=0.0, type=NodeType.WALKABLE),
        Node(id=2, x=10.0, y=20.0, type=NodeType.WALKABLE),
        Node(id=3, x=20.0, y=10.0, type=NodeType.EXIT),
    ]
    edges = [
        Edge(id=1, source=0, target=1, length_px=10.0, weight=10.0),
        Edge(id=2, source=1, target=3, length_px=10.0, weight=10.0),
        Edge(id=3, source=0, target=2, length_px=2.0, weight=2.0),
        Edge(id=4, source=2, target=3, length_px=3.0, weight=3.0),
    ]
    return Graph(
        plan_id="diamond",
        strategy="skeleton",
        image_width=100,
        image_height=100,
        nodes=nodes,
        edges=edges,
        exits=[3],
    )


def test_bfs_hop_optimality():
    """BFS must find the route with fewest hops regardless of edge weights."""
    # Graph where direct edge 0-3 has weight 100 (1 hop),
    # while 0-1-2-3 has total weight 3 (3 hops)
    nodes = [
        Node(id=0, x=0, y=0),
        Node(id=1, x=1, y=0),
        Node(id=2, x=2, y=0),
        Node(id=3, x=3, y=0),
    ]
    edges = [
        Edge(id=1, source=0, target=3, length_px=100.0, weight=100.0),
        Edge(id=2, source=0, target=1, length_px=1.0, weight=1.0),
        Edge(id=3, source=1, target=2, length_px=1.0, weight=1.0),
        Edge(id=4, source=2, target=3, length_px=1.0, weight=1.0),
    ]
    g = Graph(
        plan_id="hops_test",
        strategy="skeleton",
        image_width=50,
        image_height=50,
        nodes=nodes,
        edges=edges,
        exits=[3],
    )
    ag = AdjacencyGraph.from_schema(g)

    res = run_bfs(ag, start_node=0, exit_nodes=[3])
    assert len(res.routes) == 1
    # 0 -> 3 directly is 1 hop
    assert res.routes[0].node_ids == [0, 3]
    assert res.routes[0].hops == 1


def test_dijkstra_shortest_distance():
    """Dijkstra must find the path with smallest sum of weights."""
    g = make_diamond_graph()
    ag = AdjacencyGraph.from_schema(g)

    res = run_dijkstra(ag, start_node=0, exit_nodes=[3])
    assert len(res.routes) >= 1
    # Path 0-2-3 (weight 5) should be primary
    assert res.routes[0].node_ids == [0, 2, 3]
    assert res.routes[0].distance_px == 5.0


def test_astar_equals_dijkstra():
    """A* with Euclidean heuristic must produce the same shortest distance as Dijkstra."""
    g = make_diamond_graph()
    ag = AdjacencyGraph.from_schema(g)

    dijk_res = run_dijkstra(ag, start_node=0, exit_nodes=[3])
    astar_res = run_astar(ag, start_node=0, exit_nodes=[3])

    assert dijk_res.routes[0].node_ids == astar_res.routes[0].node_ids
    assert dijk_res.routes[0].distance_px == astar_res.routes[0].distance_px


def test_dfs_all_matches_networkx():
    """DFS all mode must find all simple paths matching NetworkX."""
    g = make_diamond_graph()
    ag = AdjacencyGraph.from_schema(g)

    # Hand-written DFS
    dfs_res = run_dfs(
        ag,
        start_node=0,
        exit_nodes=[3],
        options=RouteOptions(dfs_mode="all"),
    )
    hand_paths = [r.node_ids for r in dfs_res.routes]

    # NetworkX oracle
    nx_g = nx.Graph()
    for e in g.edges:
        nx_g.add_edge(e.source, e.target, weight=e.weight)
    nx_paths = list(nx.all_simple_paths(nx_g, source=0, target=3))

    assert len(hand_paths) == len(nx_paths)
    for p in nx_paths:
        assert p in hand_paths


def test_blocked_edge_reroute():
    """When the shortest corridor (edge 3: 0-2) is blocked, Dijkstra must reroute via 0-1-3."""
    g = make_diamond_graph()
    # Block edge 3 (between 0 and 2)
    ag = AdjacencyGraph.from_schema(g, blocked_edge_ids={3})

    res = run_dijkstra(ag, start_node=0, exit_nodes=[3])
    assert len(res.routes) == 1
    # Must now use the alternative path 0-1-3
    assert res.routes[0].node_ids == [0, 1, 3]
    assert res.routes[0].distance_px == 20.0


def test_start_at_exit_edge_case():
    """When start == exit, algorithm should return a 0-distance path with warning."""
    g = make_diamond_graph()
    ag = AdjacencyGraph.from_schema(g)

    for algo_fn in [run_bfs, run_dijkstra, run_astar]:
        res = algo_fn(ag, start_node=3, exit_nodes=[3])
        assert len(res.routes) == 1
        assert res.routes[0].node_ids == [3]
        assert res.routes[0].distance_px == 0.0
        assert "already at an exit" in res.warnings[0]


def test_unreachable_exit():
    """Disconnected graph must report no route with warnings without crashing."""
    nodes = [Node(id=0, x=0, y=0), Node(id=1, x=10, y=10)]
    edges = []  # Disconnected
    g = Graph(
        plan_id="disconnected",
        strategy="skeleton",
        image_width=20,
        image_height=20,
        nodes=nodes,
        edges=edges,
        exits=[1],
    )
    ag = AdjacencyGraph.from_schema(g)

    res_bfs = run_bfs(ag, start_node=0, exit_nodes=[1])
    assert len(res_bfs.routes) == 0
    assert len(res_bfs.warnings) > 0

    res_dijk = run_dijkstra(ag, start_node=0, exit_nodes=[1])
    assert len(res_dijk.routes) == 0

    res_dfs = run_dfs(ag, start_node=0, exit_nodes=[1])
    assert len(res_dfs.routes) == 0


# Property-Based Testing with Hypothesis: 200 Random Graphs comparing Dijkstra vs NetworkX
@hyp_settings(max_examples=200, deadline=None)
@given(
    num_nodes=st.integers(min_value=4, max_value=25),
    edge_prob=st.floats(min_value=0.2, max_value=0.6),
    seed=st.integers(min_value=1, max_value=100000),
)
def test_hypothesis_dijkstra_matches_networkx(num_nodes: int, edge_prob: float, seed: int):
    random.seed(seed)
    # Generate random connected-component graph using networkx
    G_nx = nx.erdos_renyi_graph(num_nodes, edge_prob, seed=seed)
    if not nx.is_connected(G_nx) or num_nodes < 2:
        return

    nodes = []
    edges = []
    eid = 1
    for i in G_nx.nodes():
        nodes.append(Node(id=i, x=float(i * 10), y=float((i % 5) * 10)))

    for u, v in G_nx.edges():
        w = round(random.uniform(1.0, 50.0), 2)
        G_nx[u][v]["weight"] = w
        edges.append(Edge(id=eid, source=u, target=v, length_px=w, weight=w))
        eid += 1

    start_node = 0
    exit_node = num_nodes - 1

    g_schema = Graph(
        plan_id="hypo_test",
        strategy="skeleton",
        image_width=500,
        image_height=500,
        nodes=nodes,
        edges=edges,
        exits=[exit_node],
    )
    ag = AdjacencyGraph.from_schema(g_schema)

    # Hand-written Dijkstra
    res = run_dijkstra(ag, start_node=start_node, exit_nodes=[exit_node])
    assert len(res.routes) >= 1
    hand_dist = res.routes[0].distance_px

    # NetworkX oracle shortest path length
    nx_dist = nx.shortest_path_length(
        G_nx, source=start_node, target=exit_node, weight="weight"
    )

    assert abs(hand_dist - nx_dist) < 1e-3
