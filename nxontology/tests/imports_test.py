import pytest
from pronto import Ontology  # type: ignore [attr-defined]

from nxontology.imports import from_file, from_obo_library, pronto_to_multidigraph


@pytest.mark.parametrize(
    "format",
    [
        "owl",
        "obo",
    ],
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
    assert cultivar.label == "cultivar"
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
    assert info.label == "myelination"
    assert info.data["namespace"] == "biological_process"
    # has edge from "axon ensheathment" to "myelination"
    assert nxo.graph.has_edge("GO:0008366", "GO:0042552")


@pytest.mark.parametrize(
    "format",
    [
        "owl",
        "obo",
    ],
)
def test_pronto_to_multidigraph(format: str) -> None:
    """
    http://www.obofoundry.org/ontology/taxrank.html
    """
    slug = f"taxrank.{format}"
    onto = Ontology.from_obo_library(slug)
    graph = pronto_to_multidigraph(onto)
    # subterm --> superterm: opposite of NXOntology
    assert graph.has_edge(u="TAXRANK:0000034", v="TAXRANK:0000000", key="is a")
