import logging
from os import PathLike
from typing import Any, BinaryIO, Union

from pronto import Ontology as Prontology  # type: ignore [attr-defined]

from nxontology import NXOntology
from nxontology.exceptions import NodeNotFound


def pronto_to_nxontology(onto: Prontology) -> NXOntology:
    nxo = NXOntology()
    nxo.pronto = onto  # type: ignore [attr-defined]
    for term in onto.terms():
        # obsolete is unreliable https://github.com/althonos/pronto/issues/122
        # if term.obsolete:
        #     continue
        nxo.add_node(
            term.id,
            identifier=term.id,
            label=term.name,
            namespace=term.namespace,
        )
    for term in onto.terms():
        # add subClassOf / is_a relations
        for child in term.subclasses(distance=1, with_self=False):
            try:
                nxo.add_edge(term.id, child.id)
            except NodeNotFound as e:
                logging.warning(
                    f"Cannot add edge: {term.id} --> {child.id} "
                    f"({term.name} --> {child.name}): {e}"
                )
    return nxo


def from_obo_library(slug: str) -> NXOntology:
    """
    Read ontology from <http://www.obofoundry.org/>.
    """
    onto = Prontology.from_obo_library(slug=slug)
    nxo = pronto_to_nxontology(onto)
    nxo.graph.graph["from_obo_library"] = slug
    return nxo


def from_file(handle: Union[BinaryIO, str, PathLike[Any]]) -> NXOntology:
    """
    Read ontology in OBO, OWL, or JSON (OBO Graphs) format via pronto.

    Arguments:
    handle: Either the path to a file or a binary file handle
        that contains a serialized version of the ontology.
    """
    onto = Prontology(handle=handle)
    return pronto_to_nxontology(onto)
