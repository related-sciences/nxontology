import networkx as nx
import pytest
from pronto import Ontology  # type: ignore [attr-defined]

from nxontology.imports import (
    from_file,
    from_obo_library,
    multidigraph_to_digraph,
    pronto_to_multidigraph,
    read_gene_ontology,
)

taxrank_formats = [
    "owl",
    "obo",
]


@pytest.mark.parametrize(
    "format",
    taxrank_formats,
)
def test_from_obo_library_taxrank(format: str) -> None:
    """
    http://www.obofoundry.org/ontology/taxrank.html
    """
    slug = f"taxrank.{format}"
    nxo = from_obo_library(slug)
    (root,) = nxo.roots
    assert root == "TAXRANK:0000000"
    cultivar = nxo.node_info("TAXRANK:0000034")
    assert cultivar.identifier == "TAXRANK:0000034"
    assert cultivar.name == "cultivar"
    assert "TAXRANK:0000000" in cultivar.ancestors


def test_from_file_go() -> None:
    url = "http://release.geneontology.org/2021-02-01/ontology/go-basic.json.gz"
    nxo = from_file(url)
    assert nxo.n_nodes > 20_000
    # pronto < 2.4.0 marked GO:0000003 as obsolete
    # https://github.com/althonos/pronto/issues/122
    assert "GO:0000003" in nxo.graph
    info = nxo.node_info("GO:0042552")
    assert info.identifier == "GO:0042552"
    assert info.name == "myelination"
    assert info.data["namespace"] == "biological_process"
    # has edge from "axon ensheathment" to "myelination"
    assert nxo.graph.has_edge("GO:0008366", "GO:0042552")


@pytest.mark.parametrize(
    "format",
    taxrank_formats,
)
def test_pronto_to_multidigraph(format: str) -> None:
    """
    http://www.obofoundry.org/ontology/taxrank.html
    """
    slug = f"taxrank.{format}"
    onto = Ontology.from_obo_library(slug)
    graph = pronto_to_multidigraph(onto, default_rel_type="is_a")
    assert graph.graph["ontology"] == "taxrank"
    # subterm --> superterm: opposite of NXOntology
    assert graph.has_edge(u="TAXRANK:0000034", v="TAXRANK:0000000", key="is_a")


def test_multigraph_to_digraph():
    mdg = nx.MultiDiGraph()
    mdg.add_edge("a", "b", key="rel_type 1")
    mdg.add_edge("a", "b", key="rel_type 2")
    mdg.add_edge("b", "c", key="rel_type 1")
    mdg.nodes["a"]["attribute"] = "preserve me"
    dg = multidigraph_to_digraph(mdg)
    assert dg.number_of_nodes() == 3
    assert dg.number_of_edges() == 2
    assert dg["b"]["a"]["rel_types"] == ["rel_type 1", "rel_type 2"]
    assert dg["c"]["b"]["rel_types"] == ["rel_type 1"]
    # make sure node data is preserved
    # https://github.com/networkx/networkx/issues/3392
    assert dg.nodes["a"]["attribute"] == "preserve me"
    dg = multidigraph_to_digraph(mdg, reverse=False)
    assert dg.has_edge("a", "b")
    assert not dg.has_edge("b", "a")
    assert dg.nodes["a"]["attribute"] == "preserve me"
    dg = multidigraph_to_digraph(mdg, rel_types=["rel_type 2"])
    assert dg.number_of_nodes() == 3
    assert dg.number_of_edges() == 1
    assert dg.has_edge("b", "a")
    assert dg.nodes["a"]["attribute"] == "preserve me"


def test_read_gene_ontology():
    nxo = read_gene_ontology(release="2021-02-01")
    assert nxo.graph.graph["name"] == "Gene Ontology"
    assert nxo.graph.graph["ontology"] == "go"
    assert nxo.graph.graph["data_version"] == "releases/2021-02-01"
    assert (
        nxo.graph.graph["source_url"]
        == "http://release.geneontology.org/2021-02-01/ontology/go-basic.json.gz"
    )
    bp_info = nxo.node_info("GO:0008150")
    assert bp_info.name == "biological_process"
    assert bp_info.data["namespace"] == "biological_process"
    assert "regulates" in nxo.graph["GO:0006310"]["GO:0000018"]["rel_types"]
    # Transitive reduction should remove this edge
    # from "defense response to insect" to "negative regulation of defense response to insect"
    # since it is redundant with a more specific ancestral path.
    # https://github.com/related-sciences/nxontology/pull/16
    assert not nxo.graph.has_edge("GO:0002213", "GO:1900366")
    # GO:0002213 --> GO:2000068 --> GO:1900366 is more specific
    assert nxo.graph.has_edge("GO:0002213", "GO:2000068")
    assert nxo.graph.has_edge("GO:2000068", "GO:1900366")
    assert nxo.node_info_by_name("biological_process").n_ancestors == 1
