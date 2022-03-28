import pathlib
from datetime import date

import networkx
import pytest

from nxontology.exceptions import DuplicateError, NodeNotFound
from nxontology.ontology import NXOntology


def test_add_nxontology_metadata() -> None:
    nxo: NXOntology[str] = NXOntology()
    assert "nxontology_version" in nxo.graph.graph
    assert nxo.graph.graph["nxontology_created"].startswith(str(date.today().year))


def test_add_nxontology_no_metadata() -> None:
    graph = networkx.DiGraph()
    nxo: NXOntology[str] = NXOntology(graph)
    # When providing an existing graph, we do not update metadata,
    # although this is not a firm decision that this is the right behavior.
    assert "nxontology_created" not in nxo.graph.graph
    assert "nxontology_version" not in nxo.graph.graph


def test_n_nodes(metal_nxo: NXOntology[str]) -> None:
    assert metal_nxo.n_nodes == 8


def test_n_edges(metal_nxo: NXOntology[str]) -> None:
    assert metal_nxo.n_edges == 9


def test_add_node(metal_nxo: NXOntology[str]) -> None:
    assert "brass" not in metal_nxo.graph
    metal_nxo.add_node("brass", color="#b5a642")
    assert "brass" in metal_nxo.graph
    assert metal_nxo.graph.nodes["brass"]["color"] == "#b5a642"


def test_add_node_duplicate(metal_nxo: NXOntology[str]) -> None:
    with pytest.raises(DuplicateError):
        metal_nxo.add_node("gold")


def test_add_edge(metal_nxo: NXOntology[str]) -> None:
    metal_nxo.add_edge("metal", "gold", note="already implied")
    assert metal_nxo.graph.has_edge("metal", "gold")
    assert metal_nxo.graph.edges["metal", "gold"]["note"] == "already implied"


def test_add_edge_missing_node(metal_nxo: NXOntology[str]) -> None:
    assert "brass" not in metal_nxo.graph
    with pytest.raises(NodeNotFound):
        metal_nxo.add_edge("coinage", "brass")


def test_add_edge_duplicate(metal_nxo: NXOntology[str]) -> None:
    with pytest.raises(DuplicateError):
        metal_nxo.add_edge("coinage", "gold")


def test_nxontology_read_write_node_link_json(
    metal_nxo: NXOntology[str], tmp_path: pathlib.Path
) -> None:
    path = str(tmp_path.joinpath("node-link.json"))
    metal_nxo.write_node_link_json(path)
    metal_nxo_roundtrip: NXOntology[str] = NXOntology.read_node_link_json(path)
    assert metal_nxo is not metal_nxo_roundtrip
    assert isinstance(metal_nxo_roundtrip, NXOntology)
    assert networkx.is_isomorphic(metal_nxo.graph, metal_nxo_roundtrip.graph)
    assert metal_nxo.graph.graph == metal_nxo_roundtrip.graph.graph
    assert list(metal_nxo.graph.nodes) == list(metal_nxo_roundtrip.graph.nodes)


def test_nxontology_check_is_dag(metal_nxo: NXOntology[str]) -> None:
    metal_nxo.check_is_dag()
    # add an edge that makes the graph cyclic
    metal_nxo.graph.add_edge("copper", "metal")
    # cannot match whole error message because starting node of loop is non-deterministic
    error = r"NXOntology requires a directed acyclic graph. Cycles found:\n"
    with pytest.raises(ValueError, match=error):
        metal_nxo.check_is_dag()


def test_nxontology_roots(metal_nxo_frozen: NXOntology[str]) -> None:
    roots = metal_nxo_frozen.roots
    assert roots == {"metal"}
    assert metal_nxo_frozen.root == "metal"


def test_nxontology_leaves(metal_nxo_frozen: NXOntology[str]) -> None:
    leaves = metal_nxo_frozen.leaves
    assert leaves == {"copper", "gold", "palladium", "platinum", "silver"}


def test_nxontology_isolates_empty(metal_nxo_frozen: NXOntology[str]) -> None:
    isolates = metal_nxo_frozen.isolates
    assert isolates == set()


def test_nxontology_isolates() -> None:
    nxo: NXOntology[str] = NXOntology()
    nxo.add_node("a")
    nxo.add_node("b")
    assert {"a", "b"} == nxo.isolates


def test_nxontology_disconnected(disconnected_nxo: NXOntology[str]) -> None:
    assert disconnected_nxo.roots == {"metal", "tree", "water"}
    assert not networkx.is_weakly_connected(disconnected_nxo.graph)
    with pytest.raises(ValueError, match="has multiple roots"):
        disconnected_nxo.root


def test_set_graph_attributes(metal_nxo: NXOntology[str]) -> None:
    assert metal_nxo.name == "Metals"
    metal_nxo.graph.nodes["gold"]["metal_label"] = "test_label"
    metal_nxo.graph.nodes["gold"]["metal_identifier"] = 1
    metal_nxo.graph.nodes["gold"]["metal_url"] = "https://example.com"
    metal_nxo.set_graph_attributes(
        graph_name_attribute="missing_attribute",
        node_name_attribute="metal_label",
        node_identifier_attribute="metal_identifier",
        node_url_attribute="metal_url",
    )
    assert metal_nxo.name is None
    gold_info = metal_nxo.node_info("gold")
    assert gold_info.node == "gold"
    assert gold_info.name == "test_label"
    assert gold_info.identifier == 1
    assert gold_info.url == "https://example.com"
    silver_info = metal_nxo.node_info("silver")
    assert silver_info.node == "silver"
    assert silver_info.name is None
    assert silver_info.identifier is None
    assert silver_info.url is None


def test_node_info_by_name() -> None:
    nxo: NXOntology[str] = NXOntology()
    nxo.add_node("a", name="a_name")
    nxo.add_node("b", name="b_name")
    nxo.add_node("c")
    assert nxo.node_info_by_name("a_name").node == "a"
    assert nxo.node_info_by_name("b_name").node == "b"
    with pytest.raises(NodeNotFound, match="No node found named"):
        nxo.node_info_by_name("missing_name")


def test_node_info_not_found(metal_nxo_frozen: NXOntology[str]) -> None:
    with pytest.raises(NodeNotFound, match="not-a-metal not in graph"):
        metal_nxo_frozen.node_info("not-a-metal")
