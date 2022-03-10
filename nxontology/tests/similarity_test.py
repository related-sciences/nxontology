import dataclasses
import pathlib
from typing import Callable

import pandas as pd
import pytest

from nxontology.examples import create_disconnected_nxo, create_metal_nxo
from nxontology.node import Node_Info
from nxontology.ontology import NXOntology
from nxontology.similarity import Similarity, SimilarityIC


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
metal_sim_path: pathlib.Path = directory.joinpath("similarity_test_metal.tsv")
disconnected_sim_path: pathlib.Path = directory.joinpath(
    "similarity_test_disconnected.tsv"
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
    python nxontology/tests/similarity_test.py export_similarity_tsvs
    ```
    Confirm the changes to similarity_test_metal.tsv and similarity_test_disconnected.tsv are desired before committing.
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
