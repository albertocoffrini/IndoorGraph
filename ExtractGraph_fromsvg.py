import xml.etree.ElementTree as ET
import math
import re
from collections import defaultdict

SVG_FILE = "Grafica/Progetto Bologna.svg"  # cambia se necessario
OUTPUT_FILE = "Graphs/Bologna_graph_output.py"

THRESHOLD = 85


# -------------------------------------------------
# Utility

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def parse_path(d):
    d = d.replace(",", " ")
    tokens = re.findall(r"[MLml]|-?\d+\.?\d*", d)

    if len(tokens) < 5:
        return None

    if tokens[0] not in ("M", "m"):
        return None

    x1 = float(tokens[1])
    y1 = float(tokens[2])

    if tokens[3] in ("l", "L"):
        if tokens[3] == "l":
            dx = float(tokens[4])
            dy = float(tokens[5])
            x2 = x1 + dx
            y2 = y1 + dy
        else:
            x2 = float(tokens[4])
            y2 = float(tokens[5])
    else:
        return None

    return x1, y1, x2, y2


# -------------------------------------------------
# Parsing SVG

tree = ET.parse(SVG_FILE)
root = tree.getroot()

ns = {"svg": "http://www.w3.org/2000/svg"}

nodes = {}

# ----------- NODI -----------
for text in root.findall(".//svg:text", ns):

    label = "".join(text.itertext()).strip()
    if not label:
        continue

    if "x" not in text.attrib or "y" not in text.attrib:
        continue

    x = float(text.attrib["x"].replace("px", ""))
    y = float(text.attrib["y"].replace("px", ""))

    y -= 3  # correzione baseline

    nodes[label] = (round(x, 3), round(y, 3))


# ----------- ARCHI -----------
edges = []
adj = defaultdict(set)

for path in root.findall(".//svg:path", ns):

    d_attr = path.attrib.get("d")
    if not d_attr:
        continue

    parsed = parse_path(d_attr)
    if not parsed:
        continue

    x1, y1, x2, y2 = parsed

    n1, d1 = min(
        ((name, distance(x1, y1, *coords)) for name, coords in nodes.items()),
        key=lambda x: x[1]
    )

    n2, d2 = min(
        ((name, distance(x2, y2, *coords)) for name, coords in nodes.items()),
        key=lambda x: x[1]
    )

    if d1 < THRESHOLD and d2 < THRESHOLD and n1 != n2:
        edges.append((n1, n2))
        adj[n1].add(n2)
        adj[n2].add(n1)


# -------------------------------------------------
# Scrittura output 

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    # NODES_POSITION
    f.write("NODES_POSITION = {\n")
    for name in sorted(nodes):
        x, y = nodes[name]
        f.write(f'    "{name}": ({x}, {y}),\n')
    f.write("}\n\n")

    # ADJ_TEXT
    f.write('ADJ_TEXT = """\n')
    for name in sorted(adj):
        neighbors = sorted(adj[name])
        line = f'{name}: {", ".join(neighbors)}'
        f.write(line + "\n")
    f.write('"""\n')