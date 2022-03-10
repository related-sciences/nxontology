import pytest

from nxontology import NXOntology
from nxontology.examples import create_disconnected_nxo, create_metal_nxo


@pytest.fixture
def metal_nxo() -> NXOntology[str]:
    """Returns a newly created metal ontology for each test."""
    return create_metal_nxo()


@pytest.fixture(scope="module")
def metal_nxo_frozen() -> NXOntology[str]:
    """
    Frozen metals ontology,
    scoped such that all tests in this module will receive the same NXOntology instance.
    Do not use for tests that edit the graph or graph/node/edge data.
    """
    metal_nxo = create_metal_nxo()
    metal_nxo.freeze()
    return metal_nxo


@pytest.fixture
def disconnected_nxo() -> NXOntology[str]:
    """Returns a newly created disconnected ontology for each test."""
    return create_disconnected_nxo()
