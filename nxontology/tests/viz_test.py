import pathlib
import shutil
from typing import List, Optional

import pytest

pytest.importorskip("pygraphviz")

from nxontology import NXOntology
from nxontology.viz import create_similarity_graphviz

output_dir = pathlib.Path(__file__).parent.joinpath("viz_outputs")


def setup_module():
    """Create empty viz_outputs directory before running tests in this module."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()


@pytest.mark.parametrize("source,target", [("gold", "silver"), ("palladium", "metal")])
@pytest.mark.parametrize("nodes_str", ["all", "union_ancestors"])
def test_create_graphviz(
    metal_nxo_frozen: NXOntology[str],
    source: str,
    target: str,
    nodes_str: str,
) -> None:
    id_ = f"{source}-{target}-{nodes_str}"
    if nodes_str == "all":
        nodes: Optional[List[str]] = list(metal_nxo_frozen.graph)
    elif nodes_str == "union_ancestors":
        nodes = None
    else:
        raise ValueError(f"nodes must be 'all' or 'union_ancestors', not {nodes_str!r}")
    sim = metal_nxo_frozen.similarity(source, target)
    gviz = create_similarity_graphviz(sim, nodes=nodes)
    gviz.write(output_dir.joinpath(f"metals-sim-{id_}.dot"))
    gviz.draw(output_dir.joinpath(f"metals-sim-{id_}.svg"))
    gviz.draw(output_dir.joinpath(f"metals-sim-{id_}.png"))
