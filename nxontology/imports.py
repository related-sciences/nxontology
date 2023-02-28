from __future__ import annotations

import logging
from datetime import date
from os import PathLike
from typing import AnyStr, BinaryIO, Counter, cast

import networkx as nx
from pronto import Ontology as Prontology  # type: ignore [attr-defined]
from pronto.term import Term

from nxontology import NXOntology
from nxontology.exceptions import NodeNotFound
from nxontology.node import Node

logger = logging.getLogger(__name__)


def pronto_to_nxontology(onto: Prontology) -> NXOntology[str]:
    """
    Create an `NXOntology` from an input `pronto.Ontology`.
    Obsolete terms are omitted as nodes.
    Only is_a / subClassOf relationships are used for edges.
    """
    nxo: NXOntology[str] = NXOntology()
    nxo.pronto = onto  # type: ignore [attr-defined]
    _apply_pronto_metadata(nxo.graph, onto)
    for term in onto.terms():
        if term.obsolete:
            # obsolete was unreliable in pronto < v2.4.0
            # https://github.com/althonos/pronto/issues/122
            continue
        nxo.add_node(
            term.id,
            identifier=term.id,
            name=term.name,
            namespace=term.namespace,
        )
    for term in onto.terms():
        # add subClassOf / is_a relations
        # https://github.com/althonos/pronto/issues/119
        for child in term.subclasses(distance=1, with_self=False):
            try:
                nxo.add_edge(term.id, child.id)
            except NodeNotFound as e:
                logger.warning(
                    f"Cannot add edge: {term.id} --> {child.id} "
                    f"({term.name} --> {child.name}): {e}"
                )
    return nxo


def _apply_pronto_metadata(graph: nx.Graph, onto: Prontology) -> None:
    """Apply metadata from a pronto.Ontology to the networkx graph data."""
    metadata_fields = [
        ("ontology", onto.metadata.ontology),
        ("data_version", onto.metadata.data_version),
    ]
    for nx_field, pronto_field in metadata_fields:
        if pronto_field:
            graph.graph[nx_field] = pronto_field


def from_obo_library(slug: str) -> NXOntology[str]:
    """
    Read ontology from <http://www.obofoundry.org/>.
    Delegates to [`pronto.Ontology.from_obo_library`](https://pronto.readthedocs.io/en/stable/api/pronto.Ontology.html#pronto.Ontology.from_obo_library).
    """
    onto = Prontology.from_obo_library(slug=slug)
    nxo = pronto_to_nxontology(onto)
    nxo.graph.graph["from_obo_library"] = slug
    return nxo


def from_file(handle: BinaryIO | str | PathLike[AnyStr]) -> NXOntology[str]:
    """
    Read ontology in OBO, OWL, or JSON (OBO Graphs) format via pronto.

    Arguments:
    handle: Either the path to a file or a binary file handle
        that contains a serialized version of the ontology.
    """
    onto = Prontology(handle=handle)
    return pronto_to_nxontology(onto)


def _pronto_edges_for_term(
    term: Term, default_rel_type: str = "is a"
) -> list[tuple[Node, Node, str]]:
    """
    Extract edges including "is a" relationships for a Pronto term.
    https://github.com/althonos/pronto/issues/119#issuecomment-956541286
    """
    rels = []
    source_id = cast(Node, term.id)
    for target in term.superclasses(distance=1, with_self=False):
        rels.append((source_id, cast(Node, target.id), default_rel_type))
    for rel_type, targets in term.relationships.items():
        for target in sorted(targets):
            rels.append(
                (
                    cast(Node, term.id),
                    cast(Node, target.id),
                    rel_type.name or rel_type.id,
                )
            )
    return rels


def pronto_to_multidigraph(
    onto: Prontology, default_rel_type: str = "is a"
) -> nx.MultiDiGraph:
    """
    Convert a `pronto.Ontology` to a `networkx.MultiDiGraph`,
    including all relationship types including "is a".
    The output MultiDiGraph is not directly compatable with NXOntology,
    since NXOntology assumes a DiGraph (without parallel edges) and likely
    encodes edges in the reverse direction, such that edges go from
    superterm to subterm.

    ## References

    - https://github.com/althonos/pronto/issues/119
    - https://github.com/related-sciences/nxontology/issues/14
    """
    graph = nx.MultiDiGraph()
    _apply_pronto_metadata(graph, onto)
    for term in onto.terms():
        if term.obsolete:
            # obsolete was unreliable in pronto < v2.4.0
            # https://github.com/althonos/pronto/issues/122
            continue
        if term.id in graph:
            logger.warning(f"Skipping node already in graph: {term}")
            continue
        graph.add_node(
            term.id,
            identifier=term.id,
            name=term.name,
            namespace=term.namespace,
        )
    for term in onto.terms():
        for source, target, key in _pronto_edges_for_term(  # type: ignore [var-annotated]
            term, default_rel_type
        ):
            for node in source, target:
                if node not in graph:
                    logger.warning(
                        f"Skipping edge: node does not exist in graph: {node}"
                    )
            if graph.has_edge(source, target, key):
                logger.warning(
                    f"Skipping edge already in graph: {source} --> {target} (key={key!r})"
                )
            graph.add_edge(source, target, key=key)
    rel_counts = Counter(key for _, _, key in graph.edges(keys=True))
    logger.info(f"MultiDiGraph relationship counts:\n{rel_counts}")
    return graph


def multidigraph_to_digraph(
    graph: nx.MultiDiGraph,
    rel_types: list[str] | tuple[str, ...] | None = None,
    reverse: bool = True,
    reduce: bool = False,
) -> nx.DiGraph:
    """
    Convert a networkx MultiDiGraph to a DiGraph by aggregating edges accross relationship types.
    Can be used to convert the output of `pronto_to_multidigraph` or the obonet package to a DiGraph
    suitable for input to NXOntology. In such cases, you will likely want to set reverse=True to reverse
    edges directions such that edges point from superterms to subterms.

    When rel_types is None, all relationship types are preserved. If rel_types is defined,
    then the MultiDiGraph is first filtered for edges with that key (relationship type).

    If reduce is True, perform a transitive reduction on the DiGraph
    to produce a minimum equivalent graph that removes redundant relationships
    — i.e. those that are already captured by a more specific ancestral path.
    The default is reduce=False since the reduction can be a computationally expensive step.
    """
    logger.info(f"Received MultiDiGraph with {graph.number_of_edges():,} edges.")
    if rel_types is not None:
        graph = graph.copy()
        graph.remove_edges_from(
            [
                (u, v, key)
                for u, v, key in graph.edges(keys=True, data=False)
                if key not in rel_types
            ]
        )
        logger.info(
            f"Filtered MultiDiGraph to {graph.number_of_edges():,} edges of the following types: {rel_types}."
        )
    if reverse:
        graph = graph.reverse(copy=True)
    digraph = nx.DiGraph(graph)
    if reduce:
        n_edges_before = digraph.number_of_edges()
        no_data_digraph = nx.transitive_reduction(digraph)
        # restore data https://github.com/networkx/networkx/issues/3392
        no_data_digraph.add_nodes_from(digraph.nodes.items())
        no_data_digraph.add_edges_from(
            (u, v, digraph[u][v]) for (u, v) in no_data_digraph.edges()
        )
        no_data_digraph.graph.update(digraph.graph)
        digraph = no_data_digraph
        logger.info(
            f"Reduced DiGraph by removing {n_edges_before - digraph.number_of_edges():,} redundant edges."
        )
    for source, target in digraph.edges(data=False):
        digraph[source][target]["rel_types"] = sorted(graph[source][target])
    logger.info(
        f"Converted MultiDiGraph to DiGraph with {digraph.number_of_nodes():,} nodes and {digraph.number_of_edges():,} edges."
    )
    return digraph


def read_gene_ontology(
    release: str = "current",
    source_file: str = "go-basic.json.gz",
    rel_types: list[str]
    | tuple[str, ...]
    | None = (
        "is a",
        "part of",
        "regulates",
        "negatively regulates",
        "positively regulates",
    ),
    reduce: bool = True,
) -> NXOntology[str]:
    """
    Load the Gene Ontology into NXOntology,
    keeping the relationship types from the basic release.
    GO Basic is [described as](http://geneontology.org/docs/download-ontology/):

    > This is the basic version of the GO,
    > filtered such that the graph is guaranteed to be acyclic
    > and annotations can be propagated up the graph.
    > The relations included are
    > is a, part of, regulates, negatively regulates and positively regulates.
    > This version excludes relationships that cross the 3 GO hierarchies.
    > This version should be used with most GO-based annotation tools.
    """
    if release == "current":
        url = f"http://current.geneontology.org/ontology/{source_file}"
    else:
        date.fromisoformat(release)  # check that release is a valid date
        url = f"http://release.geneontology.org/{release}/ontology/{source_file}"
    logger.info(f"Loading Gene Ontology into Pronto from <{url}>.")
    go_pronto = Prontology(handle=url)
    go_multidigraph = pronto_to_multidigraph(go_pronto, default_rel_type="is a")
    go_digraph = multidigraph_to_digraph(
        go_multidigraph,
        rel_types=rel_types,
        reverse=True,
        reduce=reduce,
    )
    go_nxo: NXOntology[str] = NXOntology(go_digraph)
    go_nxo.pronto = go_pronto  # type: ignore [attr-defined]
    go_nxo.graph.graph["name"] = "Gene Ontology"
    go_nxo.graph.graph["source_url"] = url
    return go_nxo
