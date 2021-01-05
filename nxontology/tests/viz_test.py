import pathlib
from typing import List, Optional

import pytest

from nxontology import NXOntology
from nxontology.viz import create_similarity_graphviz

output_dir = pathlib.Path(__file__).parent.joinpath("viz_outputs")


@pytest.mark.parametrize("source,target", [("gold", "silver")])
@pytest.mark.parametrize("nodes_str", ["all", "union_ancestors"])
def test_create_graphviz(
    metal_nxo_frozen: NXOntology, source: str, target: str, nodes_str: str
) -> None:
    source = "silver"
    target = "gold"
    id_ = f"{source}-{target}-{nodes_str}"
    if nodes_str == "all":
        nodes: Optional[List[str]] = list(metal_nxo_frozen.graph)
    elif nodes_str == "union_ancestors":
        nodes = None
    else:
        raise ValueError(f"nodes must be 'all' or 'union_ancestors', not {nodes_str!r}")
    sim = metal_nxo_frozen.similarity(source, target)
    gviz = create_similarity_graphviz(sim, nodes=nodes)
    gviz.write(output_dir.joinpath(f"sim-{id_}.dot"))
    gviz.draw(output_dir.joinpath(f"sim-{id_}.svg"))
    gviz.draw(output_dir.joinpath(f"sim-{id_}.png"))
