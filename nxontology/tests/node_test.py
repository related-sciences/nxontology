import math

import pytest

from nxontology.ontology import NXOntology


def test_node_info_root(metal_nxo_frozen: NXOntology[str]) -> None:
    """Test metal node_info. Metal is the only root node."""
    info = metal_nxo_frozen.node_info("metal")
    assert info.node == "metal"
    assert info.n_descendants == metal_nxo_frozen.n_nodes
    assert info.n_ancestors == 1
    assert info.roots == {"metal"}
    assert info.leaves == {"copper", "gold", "palladium", "platinum", "silver"}
    assert info.depth == 0
    assert info.parents == set()
    assert info.parent is None
    assert info.children == {"precious", "coinage"}
    paths_to_leaves = list(info.paths_to_leaves)
    assert len(paths_to_leaves) == 7
    assert ["metal", "coinage", "silver"] in paths_to_leaves


def test_node_info_gold(metal_nxo_frozen: NXOntology[str]) -> None:
    print(metal_nxo_frozen.graph.graph)
    gold_info = metal_nxo_frozen.node_info("gold")
    assert gold_info.node == "gold"
    assert gold_info.name == "gold"
    assert gold_info.identifier is None
    assert gold_info.url is None
    assert gold_info.parents == {"precious", "coinage"}
    assert gold_info.children == set()
    assert gold_info.n_descendants == 1
    assert gold_info.n_ancestors == 4
    assert gold_info.roots == {"metal"}
    assert gold_info.leaves == {"gold"}
    assert gold_info.depth == 2


def test_node_info_single_parent(metal_nxo_frozen: NXOntology[str]) -> None:
    copper = metal_nxo_frozen.node_info("copper")
    assert copper.parents == {"coinage"}
    assert copper.parent == "coinage"
    paths_from_roots = list(copper.paths_from_roots)
    assert len(paths_from_roots) == 1
    assert paths_from_roots[0] == ["metal", "coinage", "copper"]


def test_node_info_multiple_parents(metal_nxo_frozen: NXOntology[str]) -> None:
    silver = metal_nxo_frozen.node_info("silver")
    assert silver.parents == {"precious", "coinage"}
    with pytest.raises(ValueError, match="has multiple parents"):
        silver.parent
    paths_from_roots = list(silver.paths_from_roots)
    assert len(paths_from_roots) == 2


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


def test_node_name(metal_nxo: NXOntology[str]) -> None:
    gold = metal_nxo.node_info("gold")
    assert gold.name == "gold"
    with pytest.deprecated_call():
        assert gold.label == "gold"
