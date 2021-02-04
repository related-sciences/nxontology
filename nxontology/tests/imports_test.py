import pytest

from nxontology.imports import from_file, from_obo_library


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
