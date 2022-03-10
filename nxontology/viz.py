from __future__ import annotations

from typing import Iterable

from networkx.drawing.nx_agraph import to_agraph
from pygraphviz.agraph import AGraph

from nxontology.node import Node, Node_Info
from nxontology.similarity import SimilarityIC


def create_similarity_graphviz(
    sim: SimilarityIC[Node],
    nodes: Iterable[Node] | None = None,
) -> AGraph:
    """
    Create a pygraphviz AGraph to render the similarity subgraph with graphviz.
    Works by creating a subgraph in networkx with the relevant nodes.
    Then attributes are added to the subgraph to expose the proper metadata
    and style information to graphviz. See https://graphviz.org/doc/info/attrs.html.

    ## Parameters:
    - sim: SimilarityIC instance, which also provides access to the underlying nxo/graph.
    - nodes: Nodes to include in the subgraph. If None, set to the union of ancestors.
    """
    source = sim.node_0
    target = sim.node_1
    if nodes is None:
        nodes = sim.union_ancestors
    nodes = set(nodes)
    # independent shallow copy: creates new independent attribute dicts
    subgraph = sim.nxo.graph.subgraph(nodes).copy()
    # node labels and fill/font colors
    for node, data in subgraph.nodes(data=True):
        data["style"] = "filled"
        info = sim.nxo.node_info(node)
        data["label"] = (
            f"<{info.name}<br/>"
            '<font point-size="9">'
            f"IC<sub>res</sub> {info.intrinsic_ic_scaled:.2f} · "
            f"IC<sub>sán</sub> {info.intrinsic_ic_sanchez_scaled:.2f}"
            "</font>>"
        )
        if info.identifier:
            data["tooltip"] = info.identifier
        if info.url:
            data["URL"] = info.url
        scaled_ic = getattr(info, sim.ic_metric_scaled)
        data["fillcolor"] = get_hex_color(scaled_ic)
        data["fontcolor"] = "#ffffff" if scaled_ic > 0.7 else "#000000"
    # node styles
    for node in nodes - sim.union_ancestors:
        # subgraph.nodes[node]["style"] += ",invis"
        subgraph.nodes[node]["penwidth"] = 0.0
    # disjoint ancestors excluding source & target style
    for node in nodes & sim.union_ancestors - sim.common_ancestors - {source, target}:
        subgraph.nodes[node]["style"] += ",dotted"
    # common ancestors style
    for node in nodes & sim.common_ancestors:
        subgraph.nodes[node]["style"] += ",solid"
    if sim.mica:
        subgraph.nodes[sim.mica]["penwidth"] = 2.5
    # source and target style
    for node in nodes & {source, target}:
        subgraph.nodes[node]["style"] += ",dashed"
        subgraph.nodes[node]["penwidth"] = 2.5
    # title
    ic_abbr = {"intrinsic_ic": "res", "intrinsic_ic_sanchez": "sán"}[sim.ic_metric]
    source_verbose_label = get_verbose_node_label(sim.info_0)
    target_verbose_label = get_verbose_node_label(sim.info_1)
    subgraph_name = f"{sim.nxo.name} subgraph" if sim.nxo.name else "Subgraph"
    subgraph.graph["label"] = (
        f"<{subgraph_name} with ancestors of {source_verbose_label} and {target_verbose_label}. "
        f"Similarity: common ancestors = {sim.n_common_ancestors}, union ancestors = {sim.n_union_ancestors}, Lin<sub>{ic_abbr}</sub> = {sim.lin:.2f}>"
    )
    subgraph.graph["labelloc"] = "t"
    # raster resolution
    subgraph.graph["dpi"] = 125
    gviz = to_agraph(subgraph)
    gviz.layout("dot")
    return gviz


def get_verbose_node_label(info: Node_Info[Node]) -> str:
    """Return verbose label like 'name (identifier)'."""
    verbose_label = info.name
    assert isinstance(verbose_label, str)
    if info.identifier:
        verbose_label += f" ({info.identifier})"
    return verbose_label


colormap: dict[int, str] = {
    0: "#f7fcf5",
    1: "#f6fcf4",
    2: "#f4fbf2",
    3: "#f3faf0",
    4: "#f1faee",
    5: "#f0f9ed",
    6: "#eff9eb",
    7: "#edf8ea",
    8: "#ecf8e8",
    9: "#eaf7e6",
    10: "#e9f7e5",
    11: "#e7f6e3",
    12: "#e6f5e1",
    13: "#e4f5df",
    14: "#e2f4dd",
    15: "#dff3da",
    16: "#ddf2d8",
    17: "#dbf1d5",
    18: "#d8f0d2",
    19: "#d6efd0",
    20: "#d3eecd",
    21: "#d1edcb",
    22: "#ceecc8",
    23: "#ccebc6",
    24: "#caeac3",
    25: "#c7e9c0",
    26: "#c4e8bd",
    27: "#c1e6ba",
    28: "#bee5b8",
    29: "#bbe4b4",
    30: "#b8e3b2",
    31: "#b5e1ae",
    32: "#b2e0ac",
    33: "#afdfa8",
    34: "#abdda5",
    35: "#a9dca3",
    36: "#a5db9f",
    37: "#a3da9d",
    38: "#9fd899",
    39: "#9cd797",
    40: "#98d594",
    41: "#95d391",
    42: "#91d28e",
    43: "#8dd08a",
    44: "#8ace88",
    45: "#86cc85",
    46: "#83cb82",
    47: "#7fc97f",
    48: "#7cc87c",
    49: "#78c679",
    50: "#73c476",
    51: "#70c274",
    52: "#6bc072",
    53: "#68be70",
    54: "#63bc6e",
    55: "#60ba6c",
    56: "#5bb86a",
    57: "#58b668",
    58: "#53b466",
    59: "#4eb264",
    60: "#4bb062",
    61: "#46ae60",
    62: "#43ac5e",
    63: "#3fa95c",
    64: "#3ea75a",
    65: "#3ba458",
    66: "#39a257",
    67: "#369f54",
    68: "#339c52",
    69: "#319a50",
    70: "#2f974e",
    71: "#2d954d",
    72: "#2a924a",
    73: "#289049",
    74: "#258d47",
    75: "#228a44",
    76: "#208843",
    77: "#1d8640",
    78: "#1a843f",
    79: "#17813d",
    80: "#157f3b",
    81: "#127c39",
    82: "#107a37",
    83: "#0c7735",
    84: "#097532",
    85: "#077331",
    86: "#03702e",
    87: "#016e2d",
    88: "#006b2b",
    89: "#00682a",
    90: "#006428",
    91: "#006227",
    92: "#005e26",
    93: "#005a24",
    94: "#005723",
    95: "#005321",
    96: "#005120",
    97: "#004d1f",
    98: "#004a1e",
    99: "#00471c",
    100: "#00441b",
}
"""
Colormap of greens. Generated from the following code:
```python
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex
# https://matplotlib.org/examples/color/colormaps_reference.html
colormap: "matplotlib.colors.LinearSegmentedColormap" = plt.cm.Greens
{x: to_hex(colormap(x / 100)) for x in range(0, 101)}
```
Generation code for colormap not included to keep dependencies light.
"""


def get_hex_color(x: float) -> str:
    """Return a hex-encoded color like '#rrggbb' for a float between 0.0 and 1.0."""
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"x must be between 0.0 and 1.0: got {x}")
    return colormap[round(100 * x)]
