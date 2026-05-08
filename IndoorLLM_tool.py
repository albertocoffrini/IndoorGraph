# IndoorLLM_tool.py

from typing import Dict, Any
import math
import networkx as nx
from IndoorLLM import (
    build_graph,
    shortest_path_with_profile,
    turn,
    _get_pos,
)



def compute_navigation(start: str, goal: str, profile: str = "all") -> Dict[str, Any]:

    if not profile: #default value all
        profile = "all"

    G = build_graph()

    if not G.has_node(start):
        return {"error": f"Node start '{start}' not found"}

    if not G.has_node(goal):
        return {"error": f"Node goal '{goal}' not found"}

    try:
        path = shortest_path_with_profile(G, start, goal, profile)
    except nx.NetworkXNoPath:
        return {"error": f"No path from {start} to {goal} with profile '{profile}'"}
    except ValueError as e:
        return {"error": str(e)}

    # Generiamo direzioni testuali senza print
    directions = generate_directions_POI_NL(G, path)

    return {
        "start": start,
        "goal": goal,
        "profile": profile,
        "path": path,
        "directions": directions,
        "steps": len(path) - 1
    }




def generate_directions(G, path):
    def to_cartesian(p):
        x, y = p
        return (x, -y)

    instructions = []

    for i in range(1, len(path) - 1):
        n_prev, n_cur, n_next = path[i - 1], path[i], path[i + 1]

        p_prev = _get_pos(G, n_prev)
        p_cur  = _get_pos(G, n_cur)
        p_next = _get_pos(G, n_next)

        if p_prev is None or p_cur is None or p_next is None:
            instructions.append(f"Continue towards {n_next}.")
            continue

        direction = turn(
            to_cartesian(p_prev),
            to_cartesian(p_cur),
            to_cartesian(p_next),
        )

        instructions.append(
            f"Arrived at {n_cur}, go {direction} towards {n_next}."
        )

    return instructions



def generate_directions_POIs(G, path, eps_deg=10.0):
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

            if(direction_poi != "u-turn"):
                instructions.append(
                    f"at node {cur}, {poi} is on your {direction_poi.lower()}."
            )
    # for instr in instructions:
    #     print(instr)
    return instructions


def generate_directions_POI_NL(G, path, eps_deg=10.0):
    def to_cartesian(p):
        x, y = p
        return (x, -y)

    def translate_dir(d):
        return {
            "STRAIGHT": "straight",
            "LEFT": "left",
            "RIGHT": "right",
            "SLIGHT LEFT": "slightly left",
            "SLIGHT RIGHT": "slightly right",
            "BACK": "back"
        }.get(d, d.lower())

    instructions = []

    for i in range(1, len(path)):
        prev = path[i - 1]
        cur  = path[i]

        p_prev = _get_pos(G, prev)
        p_cur  = _get_pos(G, cur)

        if p_prev is None or p_cur is None:
            continue

        parts = []

        # MOVEMENT
        if i < len(path) - 1:
            nxt = path[i + 1]
            p_next = _get_pos(G, nxt)

            if p_next is not None:
                direction = translate_dir(
                    turn(
                        to_cartesian(p_prev),
                        to_cartesian(p_cur),
                        to_cartesian(p_next),
                    )
                )

                parts.append(f"From node {cur}, go {direction} towards {nxt}")

        # POI
        left_pois = []
        right_pois = []

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

            if "LEFT" in direction_poi:
                left_pois.append(poi)
            elif "RIGHT" in direction_poi:
                right_pois.append(poi)

        poi_parts = []

        if left_pois:
            poi_parts.append(f"{', '.join(left_pois)} on your left")
        if right_pois:
            poi_parts.append(f"{', '.join(right_pois)} on your right")

        if poi_parts:
            parts.append("you will find " + " and ".join(poi_parts))


        if parts:
            instructions.append(". ".join(parts) + ".")

    return instructions