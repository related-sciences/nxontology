import dataclasses
import math
import pathlib
from typing import Callable

import networkx
import pandas as pd
import pytest

from nxontology.examples import create_disconnected_nxo, create_metal_nxo
from nxontology.exceptions import DuplicateError, NodeNotFound
from nxontology.ontology import Node_Info, NXOntology, Similarity, SimilarityIC


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


def test_node_info_root(metal_nxo_frozen: NXOntology[str]) -> None:
    """Test metal node_info. Metal is the only root node."""
    info = metal_nxo_frozen.node_info("metal")
    assert info.node == "metal"
    assert info.n_descendants == metal_nxo_frozen.n_nodes
    assert info.n_ancestors == 1
    assert info.depth == 0


def test_node_info_gold(metal_nxo_frozen: NXOntology[str]) -> None:
    print(metal_nxo_frozen.graph.graph)
    gold_info = metal_nxo_frozen.node_info("gold")
    assert gold_info.node == "gold"
    assert gold_info.label == "gold"
    assert gold_info.identifier is None
    assert gold_info.url is None
    assert gold_info.n_descendants == 1
    assert gold_info.n_ancestors == 4
    assert gold_info.depth == 2


def test_set_graph_attributes(metal_nxo: NXOntology[str]) -> None:
    assert metal_nxo.name == "Metals"
    metal_nxo.graph.nodes["gold"]["metal_label"] = "test_label"
    metal_nxo.graph.nodes["gold"]["metal_identifier"] = 1
    metal_nxo.graph.nodes["gold"]["metal_url"] = "https://example.com"
    metal_nxo.set_graph_attributes(
        graph_name_attribute="missing_attribute",
        node_label_attribute="metal_label",
        node_identifier_attribute="metal_identifier",
        node_url_attribute="metal_url",
    )
    assert metal_nxo.name is None
    gold_info = metal_nxo.node_info("gold")
    assert gold_info.node == "gold"
    assert gold_info.label == "test_label"
    assert gold_info.identifier == 1
    assert gold_info.url == "https://example.com"
    silver_info = metal_nxo.node_info("silver")
    assert silver_info.node == "silver"
    assert silver_info.label is None
    assert silver_info.identifier is None
    assert silver_info.url is None


def test_node_info_not_found(metal_nxo_frozen: NXOntology[str]) -> None:
    with pytest.raises(NodeNotFound, match="not-a-metal not in graph"):
        metal_nxo_frozen.node_info("not-a-metal")


def test_intrinsic_ic_unscaled(metal_nxo_frozen: NXOntology[str]) -> None:
    assert metal_nxo_frozen.n_nodes == 8
    # number of descendants per node including self
    n_descendants = [
        ("metal", 8),
        ("precious", 5),
        ("coinage", 4),
        ("platinum", 1),
        ("palladium", 1),
        ("gold", 1),
        ("silver", 1),
        ("copper", 1),
    ]
    for node, numerator in n_descendants:
        value = metal_nxo_frozen.node_info(node).intrinsic_ic
        expected = -math.log(numerator / 8)
        assert value == pytest.approx(expected)


@pytest.mark.parametrize(
    "node_0, node_1, expected",
    [
        ("metal", "metal", 1.0),
        ("copper", "copper", 1.0),
        ("copper", "metal", 1 / 3),
        ("platinum", "gold", 0.4),
    ],
)
def test_similarity_batet(
    metal_nxo_frozen: NXOntology[str], node_0: str, node_1: str, expected: float
) -> None:
    sim = Similarity(metal_nxo_frozen, node_0, node_1)
    assert sim.batet == expected


@pytest.mark.parametrize(
    "node_0, node_1, expected",
    [
        ("metal", "metal", "metal"),
        ("copper", "copper", "copper"),
        ("copper", "precious", "metal"),
        ("copper", "silver", "coinage"),
        ("gold", "silver", "coinage"),
    ],
)
def test_similarity_mica(
    metal_nxo_frozen: NXOntology[str], node_0: str, node_1: str, expected: str
) -> None:
    sim = SimilarityIC(
        metal_nxo_frozen, node_0, node_1, ic_metric="intrinsic_ic_sanchez"
    )
    assert sim.mica is not None
    assert sim.mica == expected


def test_similarity_unsupported_metric(metal_nxo_frozen: NXOntology[str]) -> None:
    with pytest.raises(ValueError, match="not a supported ic_metric"):
        SimilarityIC(metal_nxo_frozen, "gold", "silver", ic_metric="ic_unsupported")


def test_cache_on_frozen_leaves(metal_nxo: NXOntology[str]) -> None:
    # cache disabled
    leaves = metal_nxo.leaves
    assert "leaves" not in getattr(metal_nxo, "__method_cache", {})
    # with cold cache
    metal_nxo.freeze()
    cached_leaves = metal_nxo.leaves
    assert leaves is not cached_leaves
    assert "leaves" in getattr(metal_nxo, "__method_cache")
    assert cached_leaves is metal_nxo.__method_cache["leaves"]  # type: ignore [attr-defined]
    # with warm cache
    assert metal_nxo.leaves is cached_leaves


def test_cache_on_node_info(metal_nxo: NXOntology[str]) -> None:
    # cache disabled
    assert not metal_nxo.frozen
    gold = metal_nxo.node_info("gold")
    assert "gold" not in metal_nxo._node_info_cache
    # with cold cache
    metal_nxo.freeze()
    cached_gold = metal_nxo.node_info("gold")
    assert "gold" in metal_nxo._node_info_cache
    assert cached_gold is not gold
    # with warm cache
    assert metal_nxo.node_info("gold") is cached_gold


def get_similarity_tsv(nxo: NXOntology[str]) -> str:
    """
    Returns TSV text for all similarity metrics on the provided ontology.
    """
    nodes = sorted(nxo.graph)
    sims = nxo.compute_similarities(
        source_nodes=nodes,
        target_nodes=nodes,
        ic_metrics=Node_Info.ic_metrics,
    )
    sim_df = pd.DataFrame(sims)
    tsv = sim_df.to_csv(
        sep="\t", index=False, float_format="%.3g", line_terminator="\n"
    )
    assert isinstance(tsv, str)
    return tsv


@dataclasses.dataclass
class Ontology:
    name: str
    sim_path: pathlib.Path
    ctor: Callable[[], NXOntology[str]]


directory: pathlib.Path = pathlib.Path(__file__).parent
metal_sim_path: pathlib.Path = directory.joinpath("ontology_test_metal_sim.tsv")
disconnected_sim_path: pathlib.Path = directory.joinpath(
    "ontology_test_disconnected_sim.tsv"
)
test_ontologies = [
    Ontology("metal", metal_sim_path, create_metal_nxo),
    Ontology("disconnected", disconnected_sim_path, create_disconnected_nxo),
]


@pytest.mark.parametrize("ontology", test_ontologies)
def test_similarities(ontology: Ontology) -> None:
    """
    If this test fails, regenerate the expected output by executing:
    ```
    python nxontology/tests/ontology_test.py export_similarity_tsvs
    ```
    Confirm the changes to ontology_utils_test_metal_sim.tsv are desired before committing.
    """
    nxo = ontology.ctor()
    nxo.freeze()
    tsv = get_similarity_tsv(nxo)
    expect_tsv = ontology.sim_path.read_text()
    assert tsv == expect_tsv


def export_similarity_tsvs() -> None:
    """
    Regenerate ontology_utils_test_metal_sim.tsv
    """
    for ontology in test_ontologies:
        nxo = ontology.ctor()
        tsv = get_similarity_tsv(nxo)
        ontology.sim_path.write_text(tsv)


if __name__ == "__main__":
    import fire

    fire.Fire({"export_similarity_tsvs": export_similarity_tsvs})
