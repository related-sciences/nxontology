import math
import pathlib

import networkx
import pandas as pd
import pytest

from nxontology.ontology import Node_Info, NXOntology, Similarity, SimilarityIC


def create_metal_nxo() -> NXOntology:
    """
    Metals ontology from Fig 1 of "Semantic Similarity Definition" at
    https://doi.org/10.1016/B978-0-12-809633-8.20401-9.
    Also published at https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-2-5/figures/1
    Note edge direction is opposite of the drawing.
    Edges go from general to specific.
    """
    nxo = NXOntology()
    edges = [
        ("metal", "precious"),
        ("metal", "coinage"),
        ("precious", "platinum"),
        ("precious", "palladium"),
        ("precious", "gold"),
        ("precious", "silver"),
        ("coinage", "gold"),
        ("coinage", "silver"),
        ("coinage", "copper"),
    ]
    nxo.graph.add_edges_from(edges)
    return nxo


@pytest.fixture  # type: ignore [misc]
def metal_nxo() -> NXOntology:
    """Returns a newly created metal ontology for each test."""
    return create_metal_nxo()


@pytest.fixture(scope="module")  # type: ignore [misc]
def metal_nxo_frozen() -> NXOntology:
    """
    Frozen metals ontology,
    scoped such that all tests in this module will receive the same NXOntology instance.
    Do not use for tests that edit the graph or graph/node/edge data.
    """
    metal_nxo = create_metal_nxo()
    metal_nxo.freeze()
    return metal_nxo


def test_nxontology_read_write_node_link_json(
    metal_nxo: NXOntology, tmp_path: pathlib.Path
) -> None:
    path = str(tmp_path.joinpath("node-link.json"))
    metal_nxo.write_node_link_json(path)
    metal_nxo_roundtrip = NXOntology.read_node_link_json(path)
    assert metal_nxo is not metal_nxo_roundtrip
    assert isinstance(metal_nxo_roundtrip, NXOntology)
    assert networkx.is_isomorphic(metal_nxo.graph, metal_nxo_roundtrip.graph)
    assert metal_nxo.graph.graph == metal_nxo_roundtrip.graph.graph
    assert list(metal_nxo.graph.nodes) == list(metal_nxo_roundtrip.graph.nodes)


def test_nxontology_check_is_dag(metal_nxo: NXOntology) -> None:
    metal_nxo.check_is_dag()
    # add an edge that makes the graph cyclic
    metal_nxo.graph.add_edge("copper", "metal")
    with pytest.raises(ValueError):
        metal_nxo.check_is_dag()


def test_nxontology_roots(metal_nxo_frozen: NXOntology) -> None:
    roots = metal_nxo_frozen.roots
    assert roots == {"metal"}


def test_nxontology_leaves(metal_nxo_frozen: NXOntology) -> None:
    leaves = metal_nxo_frozen.leaves
    assert leaves == {"copper", "gold", "palladium", "platinum", "silver"}


def test_node_info_gold(metal_nxo_frozen: NXOntology) -> None:
    gold_info = metal_nxo_frozen.node_info("gold")
    assert gold_info.node == "gold"
    assert gold_info.n_descendants == 1
    assert gold_info.n_ancestors == 4


def test_intrinsic_ic_unscaled(metal_nxo_frozen: NXOntology) -> None:
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
)  # type: ignore [misc]
def test_similarity_batet(
    metal_nxo_frozen: NXOntology, node_0: str, node_1: str, expected: float
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
)  # type: ignore [misc]
def test_similarity_mica(
    metal_nxo_frozen: NXOntology, node_0: str, node_1: str, expected: float
) -> None:
    sim = SimilarityIC(
        metal_nxo_frozen, node_0, node_1, ic_metric="intrinsic_ic_sanchez"
    )
    assert sim.mica == expected


def test_similarity_unsupported_metric(metal_nxo_frozen: NXOntology) -> None:
    with pytest.raises(ValueError, match="not a supported ic_metric"):
        SimilarityIC(metal_nxo_frozen, "gold", "silver", ic_metric="ic_unsupported")


def test_cache_on_frozen_leaves(metal_nxo: NXOntology) -> None:
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


def test_cache_on_node_info(metal_nxo: NXOntology) -> None:
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


def get_metal_similarity_tsv() -> str:
    """
    Returns TSV text for all similarity metrics on the metal ontology.
    """
    metal_nxo = create_metal_nxo()
    nodes = sorted(metal_nxo.graph)
    sims = metal_nxo.compute_similarities(
        source_nodes=nodes,
        target_nodes=nodes,
        ic_metrics=Node_Info.ic_metrics,
    )
    metal_sim_df = pd.DataFrame(sims)
    tsv = metal_sim_df.to_csv(sep="\t", index=False, float_format="%.3g")
    assert isinstance(tsv, str)
    return tsv


metal_sim_path: pathlib.Path = pathlib.Path(__file__).parent.joinpath(
    "ontology_test_metal_sim.tsv"
)


def test_metal_similarities() -> None:
    """
    If this test fails, regenerate the expected output by executing:
    ```
    ./bin/run_pipeline rs_utils/tests/ontology_utils_test.py export_metal_similarity_tsv
    ```
    Confirm the changes to ontology_utils_test_metal_sim.tsv are desired before committing.
    """
    tsv = get_metal_similarity_tsv()
    expect_tsv = metal_sim_path.read_text()
    assert tsv == expect_tsv


def export_metal_similarity_tsv() -> None:
    """
    Regenerate ontology_utils_test_metal_sim.tsv
    Execute this with:
    """
    tsv = get_metal_similarity_tsv()
    metal_sim_path.write_text(tsv)


if __name__ == "__main__":
    import fire

    fire.Fire({"export_metal_similarity_tsv": export_metal_similarity_tsv})
