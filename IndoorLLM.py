"""
Environment: source indoorGraph/bin/activate

- Base graph is DIRECTED (nx.DiGraph) built from ADJ_TEXT with "_" syntax.
- Each edge gets a "kind" attribute (corridor / entrance / elevator / connector).
- You can request different routing profiles (e.g., accessible, only_elevator, all)
  which filter the graph by allowed edge kinds before running shortest_path.

Usage:
    python IndoorLLM.py START_NODE GOAL_NODE [CONDITION]

Examples:
    python IndoorLLM.py 1 H
    python IndoorLLM.py 1 H accessible
    python IndoorLLM.py EL1 EL4 only_elevator
"""

from __future__ import annotations

import sys
from typing import List, Tuple, Set
import networkx as nx
import math
import matplotlib.pyplot as plt

# -----------------------------
# Node and edge specification
from Graphs.OrioCenter_graph_spec import (
    ADJ_TEXT,
    CORRIDOR_NODES,
    SPECIAL_EDGES,
    POI_METADATA,
    NODE_METADATA,
    NODES_POSITION,
)

def stampa_poi_riconosciuti(G: nx.DiGraph):
    print("\n=== POI RICONOSCIUTI NEL GRAFO ===")
    poi_nodes = [
        (n, data)
        for n, data in G.nodes(data=True)
        if data.get("kind") == "POI"
    ]

    for n, data in sorted(poi_nodes):
        entrances = data.get("entrances", {})
        if entrances:
            sides = ", ".join(f"{k}:{v}" for k, v in entrances.items())
            print(f"{n} -> entrances [{sides}]")
        else:
            print(f"{n} -> no entrance metadata")

    print(f"\nTotale POI trovati: {len(poi_nodes)}\n")

def draw_graph(G):
    pos = {n: G.nodes[n]["position"] for n in G.nodes if "position" in G.nodes[n]}
    nx.draw(G, pos, with_labels=True, node_size=500, font_size=8)
    plt.gca().invert_yaxis()  # utile se coordinate tipo SVG
    plt.show()

# Parse lines like:
#         A _ B, C, D
#         (A -> B), (A -> C), (A -> D)

def parse_adj(text: str) -> List[Tuple[str, str]]:

    edges: List[Tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        src, rhs = line.split(":", 1)
        src = src.strip()
        for v in rhs.split(","):
            dst = v.strip()
            if dst:
                edges.append((src, dst))
    return edges


def _is_corridor(G: nx.DiGraph, n: str) -> bool:
    return G.nodes[n].get("kind") == "NODE" and n in CORRIDOR_NODES

def _is_elevator(G: nx.DiGraph, n: str) -> bool:
    return G.nodes[n].get("poi_type") == "elevator"


def infer_edge_kind(G: nx.DiGraph, u: str, v: str) -> str:
    u_corr = _is_corridor(G, u)
    v_corr = _is_corridor(G, v)
    u_el = _is_elevator(G, u)
    v_el = _is_elevator(G, v)

    if u_corr and v_corr:
        return "corridor"

    # corridor <-> POI (shops/services/elevators) as "entrance"
    if (u_corr and not v_corr) or (v_corr and not u_corr):
        return "entrance"

    # elevator-to-elevator (vertical movement)
    if u_el and v_el:
        return "elevator"

    # fallback
    return "connector"


def euclidean_distance(n1, n2):
    x1, y1 = n1
    x2, y2 = n2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)



def parse_adj(adj_text: str):
    edges = []
    for raw in adj_text.splitlines():
        line = raw.strip()

        # skip righe vuote
        if not line:
            continue

        # skip righe senza ":" (eventuali commenti o righe sporche)
        if ":" not in line:
            continue

        src, rhs = line.split(":", 1)
        src = src.strip()

        for dst in (p.strip() for p in rhs.split(",")):
            if dst:  # elimina pezzi vuoti (es trailing comma)
                edges.append((src, dst))

    return edges


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    # costruisci archi da ADJ_TEXT
    edges = parse_adj(ADJ_TEXT)

    for u, v in edges:

        if u in NODES_POSITION and v in NODES_POSITION:
            weight = euclidean_distance(NODES_POSITION[u], NODES_POSITION[v])
        else:
            weight = 1.0
            # DEBUG 
            # print(f"[weight fallback] {u}->{v} missing pos? u:{u in NODES_POSITION} v:{v in NODES_POSITION}")

        G.add_edge(u, v, weight=weight)

    # aggiungi archi speciali
    for (u, v), kind in SPECIAL_EDGES.items():
        G.add_edge(u, v, kind=kind, weight=3.0) #da sistemare il peso quando faremo percorsi multipiano

    # metadata nodi
    for n in G.nodes:
        G.nodes[n]["kind"] = "NODE" if n in CORRIDOR_NODES else "POI"

        if n in POI_METADATA:
            G.nodes[n].update(POI_METADATA[n])

        if n in NODE_METADATA:
            G.nodes[n].update(NODE_METADATA[n])

        if n in NODES_POSITION:
            x, y = NODES_POSITION[n]
            G.nodes[n]["x"] = x
            G.nodes[n]["y"] = y
            G.nodes[n]["position"] = (x, y)

    # classifica archi (solo se non già classificati)
    for u, v in G.edges:
        if "kind" not in G.edges[u, v]:
            G.edges[u, v]["kind"] = infer_edge_kind(G, u, v)

    return G


# -----------------------------
# Path accessibility / profiles conditions

def allowed_edge_kinds(profile: str) -> Set[str]:
    """
    Corridor + entrance are always allowed.
    profile selects which "special" connectors are allowed in addition.
    """
    base = {"corridor", "entrance"}

    if profile == "all":
        return base | {"elevator", "stairs", "escalator", "connector"}

    if profile == "accessible":
        return base | {"elevator"}

    if profile == "only_elevator":
        return base | {"elevator"}

    if profile == "no_elevator":
        return base | {"stairs", "escalator", "connector"}

    if profile == "only_stairs":
        return base | {"stairs", "connector"}

    if profile == "corridor_only":
        return {"corridor", "entrance"}

    raise ValueError(f"Unknown profile: {profile}")


def filtered_graph_by_profile(G: nx.DiGraph, profile: str) -> nx.DiGraph:
    allowed = allowed_edge_kinds(profile)
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))

    for u, v, data in G.edges(data=True):
        if data.get("kind") in allowed:
            H.add_edge(u, v, **data)

    return H


def shortest_path_with_profile(G: nx.DiGraph, start: str, goal: str, profile: str) -> List[str]:
    H = filtered_graph_by_profile(G, profile)
    return nx.shortest_path(H, start, goal, weight="weight")

def print_top3(G: nx.DiGraph, start: str, goal: str, profile: str = "all"):
    """
    Stampa:
    - miglior percorso
    - secondo miglior percorso
    - terzo miglior percorso
    Mostrando nodi, pesi degli archi e peso totale.
    """

    H = filtered_graph_by_profile(G, profile)

    try:
        paths_generator = nx.shortest_simple_paths(H, start, goal, weight="weight")
    except nx.NetworkXNoPath:
        print(f"Nessun percorso tra {start} e {goal}")
        return

    print(f"\n=== TOP 3 PERCORSI ({start} -> {goal}) profilo='{profile}' ===\n")

    for i, path in enumerate(paths_generator):
        if i >= 3:
            break

        total_weight = 0.0
        edge_weights = []

        for j in range(len(path) - 1):
            u = path[j]
            v = path[j + 1]
            w = H.edges[u, v]["weight"]
            edge_weights.append((u, v, w))
            total_weight += w

        print(f"{i+1}) Percorso:")
        print("   Nodi:", " -> ".join(path))
        print("   Archi e pesi:")
        for (u, v, w) in edge_weights:
            print(f"      {u} -> {v}  peso={w:.2f}")
        print(f"   SOMMA TOTALE PESI = {total_weight:.2f}")
        print()

# -----------------------------
# Utilities

def print_node_metadata(G: nx.DiGraph, node_id: str):
    meta = G.nodes[node_id]
    for k, v in meta.items():
        print(f"  - {k}: {v}")


def print_edge_metadata(G: nx.DiGraph, u: str, v: str):
    data = G.edges[u, v]
    print(f"  edge {u} -> {v}: kind={data.get('kind')} weight={data.get('weight')}")





def turn(p_prev, p_cur, p_next,
           eps_deg=10,           # quasi dritto
           slight_deg=35,        # sotto questa soglia = leggermente
           uturn_deg=170):       # sopra questa soglia = inversione

    x1, y1 = p_prev
    x2, y2 = p_cur
    x3, y3 = p_next

    dx1, dy1 = x2 - x1, y2 - y1
    dx2, dy2 = x3 - x2, y3 - y2

    cross = dx1 * dy2 - dy1 * dx2
    dot   = dx1 * dx2 + dy1 * dy2

    ang = math.degrees(math.atan2(cross, dot))

    # U-turn
    if abs(ang) >= uturn_deg:
        return "U-TURN"

    # quasi dritto
    if abs(ang) <= eps_deg:
        return "STRAIGHT"

    # leggermente
    if abs(ang) <= slight_deg:
        return "SLIGHT LEFT" if ang > 0 else "SLIGHT RIGHT"

    # svolta piena
    return "LEFT" if ang > 0 else "RIGHT"


def _get_pos(G, node):
    """
    Prende la posizione dal grafo se presente, altrimenti da NODES_POSITION.
    Ritorna (x, y) oppure None.
    """
    pos = G.nodes.get(node, {}).get("position")
    if pos is not None:
        return pos
    # fallback se usi il dict globale
    return NODES_POSITION.get(node)


def print_direction(G, path, eps_deg=10.0):
    print("Full path:", " -> ".join(path))
    print()
    print("=== Full navigation ===")


    # per evitare LEFT/RIGHT invertiti con coordinate SVG (Y verso il basso),
    # ribaltiamo Y in un sistema cartesiano standard
    def to_cartesian(p):
        x, y = p
        return (x, -y)

    for i in range(1, len(path) - 1):
        n_prev, n_cur, n_next = path[i - 1], path[i], path[i + 1]

        p_prev = _get_pos(G, n_prev)
        p_cur  = _get_pos(G, n_cur)
        p_next = _get_pos(G, n_next)

        # se manca anche solo una posizione, non posso calcolare la turn
        if p_prev is None or p_cur is None or p_next is None:
            print(f"You have arrived at {n_cur}. Continue towards {n_next}.")
            continue

        direzione = turn(to_cartesian(p_prev), to_cartesian(p_cur), to_cartesian(p_next), eps_deg=eps_deg)
        print(f"You have arrived at {n_cur}. Go {direzione} towards {n_next}.")

    print("\n")

def print_poi_path(G, path, eps_deg=10.0):
    # stessa identica logica di print_direction
    print("=== List of POIs along the path. ===")
    def to_cartesian(p):
        x, y = p
        return (x, -y)

    for i in range(1, len(path)):
        prev, n = path[i - 1], path[i]

        p_prev = _get_pos(G, prev)
        p_n    = _get_pos(G, n)
        if p_prev is None or p_n is None:
            continue

        # trova POI collegati a n (archi entrance in/out)
        pois = set()
        for v in G.successors(n):
            if G.nodes[v].get("kind") == "POI" and G.edges[n, v].get("kind") == "entrance":
                pois.add(v)
        for u in G.predecessors(n):
            if G.nodes[u].get("kind") == "POI" and G.edges[u, n].get("kind") == "entrance":
                pois.add(u)

        if not pois:
            continue

        for poi in sorted(pois):
            p_poi = _get_pos(G, poi)
            if p_poi is None:
                continue

            direction = turn(
                to_cartesian(p_prev),
                to_cartesian(p_n),
                to_cartesian(p_poi),
                eps_deg=eps_deg
            )
            print(f"Coming from {prev}, {poi} is on your {direction.lower()} at node {n}.")

def draw_graph_with_path(G, path, show_pois=True):
    """
    Disegna il grafo e sovrappone il path evidenziando nodi/archi del percorso.
    Usa _get_pos(G,node) e lo stesso to_cartesian usato in print_direction.
    """
    def to_cartesian(p):
        x, y = p
        return (x, -y)

    # costruisci dizionario pos con trasformazione coerente
    pos = {}
    for n in G.nodes:
        p = _get_pos(G, n)
        if p is not None:
            pos[n] = to_cartesian(p)

    plt.figure(figsize=(20, 10))
    ax = plt.gca()
    ax.set_aspect('equal')

    # draw all edges softly
    all_edges = list(G.edges())
    nx.draw_networkx_edges(G, pos,
                           edgelist=all_edges,
                           edge_color='lightgray',
                           arrows=True,
                           arrowstyle='-|>',
                           arrowsize=10,
                           width=1,
                           connectionstyle="arc3,rad=0.0",
                           alpha=0.6)

    # highlight path edges
    path_edges = [(path[i], path[i+1]) for i in range(len(path)-1) if path[i] in pos and path[i+1] in pos]
    if path_edges:
        nx.draw_networkx_edges(G, pos,
                               edgelist=path_edges,
                               edge_color='red',
                               arrows=True,
                               arrowstyle='-|>',
                               arrowsize=14,
                               width=3,
                               connectionstyle="arc3,rad=0.0",
                               alpha=0.9)

    # draw nodes: corridor vs poi
    corridor_nodes = [n for n, d in G.nodes(data=True) if d.get("kind") != "POI" and n in pos]
    poi_nodes = [n for n, d in G.nodes(data=True) if d.get("kind") == "POI" and n in pos]

    nx.draw_networkx_nodes(G, pos, nodelist=corridor_nodes, node_size=150, node_color='lightblue', label='corridor')
    if show_pois:
        nx.draw_networkx_nodes(G, pos, nodelist=poi_nodes, node_size=120, node_color='orange', node_shape='s', label='POI')

    # emphasize path nodes
    path_nodes_in_pos = [n for n in path if n in pos]
    if path_nodes_in_pos:
        nx.draw_networkx_nodes(G, pos, nodelist=path_nodes_in_pos, node_size=260, node_color='red', label='path')

    # labels: puoi mostrare solo i nodi del path + POI per chiarezza
    labels = {n: n for n in path_nodes_in_pos}
    if show_pois:
        for p in poi_nodes:
            labels[p] = p
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

    # legenda semplice
    handles, labels_ = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels_, loc='upper right')

    plt.title("Graph with highlighted path")
    plt.axis('off')
    plt.show(block=True)


# def generate_directions_POIs(G, path, eps_deg=10.0):
    def to_cartesian(p):
        x, y = p
        return (x, -y)

    instructions = []

    for i in range(1, len(path)):
        prev = path[i - 1]
        cur  = path[i]

        p_prev = _get_pos(G, prev)
        p_cur  = _get_pos(G, cur)

        if p_prev is None or p_cur is None:
            instructions.append(f"Continue towards {cur}.")
            continue

        # -------- TURN (solo se esiste next) --------
        if i < len(path) - 1:
            nxt = path[i + 1]
            p_next = _get_pos(G, nxt)

            if p_next is not None:
                direction = turn(
                    to_cartesian(p_prev),
                    to_cartesian(p_cur),
                    to_cartesian(p_next),
                )

                instructions.append(
                    f"Arrived at {cur}, go {direction} towards {nxt}."
                )

        # -------- POI LOGIC --------
        pois = set()

        for v in G.successors(cur):
            if G.nodes[v].get("kind") == "POI" and G.edges[cur, v].get("kind") == "entrance":
                pois.add(v)

        for u in G.predecessors(cur):
            if G.nodes[u].get("kind") == "POI" and G.edges[u, cur].get("kind") == "entrance":
                pois.add(u)

        for poi in sorted(pois):
            p_poi = _get_pos(G, poi)
            if p_poi is None:
                continue

            direction_poi = turn(
                to_cartesian(p_prev),
                to_cartesian(p_cur),
                to_cartesian(p_poi),
                eps_deg=eps_deg
            )

            instructions.append(
                f"Coming from {prev}, {poi} is on your {direction_poi.lower()} at node {cur}."
            )
    for instr in instructions:
        print(instr)
    return instructions
# -----------------------------
# main

def generate_directions_POIs(G, path, eps_deg=10.0):

    def to_cartesian(p):
        x, y = p
        return (x, -y)

    instructions = []

    if len(path) > 0:
        instructions.append(f"Starting point: {path[0]}.")

    for i in range(1, len(path)):

        prev = path[i - 1]
        cur = path[i]

        p_prev = _get_pos(G, prev)
        p_cur = _get_pos(G, cur)

        if p_prev is None or p_cur is None:
            instructions.append(f"Continue towards {cur}.")
            continue

        # =========================================================
        # ARRIVO AL NODO
        # =========================================================

        instructions.append(f"Arrived at {cur}.")

        # =========================================================
        # POI DEL NODO CORRENTE
        # =========================================================

        pois = set()

        for v in G.successors(cur):
            if (
                G.nodes[v].get("kind") == "POI"
                and G.edges[cur, v].get("kind") == "entrance"
            ):
                pois.add(v)

        for u in G.predecessors(cur):
            if (
                G.nodes[u].get("kind") == "POI"
                and G.edges[u, cur].get("kind") == "entrance"
            ):
                pois.add(u)

        for poi in sorted(pois):

            p_poi = _get_pos(G, poi)

            if p_poi is None:
                continue

            direction_poi = turn(
                to_cartesian(p_prev),
                to_cartesian(p_cur),
                to_cartesian(p_poi),
                eps_deg=eps_deg
            )

            instructions.append(
                f"{poi} is on your {direction_poi.lower()}."
            )

        # =========================================================
        # DIREZIONE VERSO IL PROSSIMO NODO
        # =========================================================

        if i < len(path) - 1:

            nxt = path[i + 1]
            p_next = _get_pos(G, nxt)

            if p_next is not None:

                direction = turn(
                    to_cartesian(p_prev),
                    to_cartesian(p_cur),
                    to_cartesian(p_next),
                )

                instructions.append(
                    f"Go {direction} towards {nxt}."
                )

    for instr in instructions:
        print(instr)

    return instructions


def main():

    if len(sys.argv) not in (3, 4):
        print("Usage: python graph_networkx_main3.py START GOAL [PROFILE]")
        print("Profiles: all, accessible, only_elevator, no_elevator, only_stairs, corridor_only")
        return

    start, goal = sys.argv[1], sys.argv[2]
    profile = sys.argv[3] if len(sys.argv) == 4 else "all"

    G = build_graph()
    print("Nodes in graph:", G.number_of_nodes())
    print("Nodes with position:", sum(1 for n in G.nodes if n in NODES_POSITION))
    missing = [n for n in G.nodes if n not in NODES_POSITION]
    print("Missing positions (first 50):", missing[:50])

    # stampa_poi_riconosciuti(G) #DEBUG

    if not G.has_node(start) or not G.has_node(goal):
        print(f"Start or goal node not found. start={start} goal={goal}")
        return

    try:
        path = shortest_path_with_profile(G, start, goal, profile)
    except ValueError as e:
        print(e)
        return
    except nx.NetworkXNoPath:
        print(f"No path from {start} to {goal} with profile '{profile}'")
        return

    print(f"Path (profile='{profile}') {start} -> {goal}")
    print("  " + " -> ".join(path))


    # stampe di OUTPUT
    # print_top3(G, start, goal, profile)
    # print_direction(G, path, eps_deg=10.0 )
    generate_directions_POIs(G, path)

    # stampa GRAFICA
    # draw_graph(G)
    draw_graph_with_path(G, path, show_pois=True)


if __name__ == "__main__":
    main()
