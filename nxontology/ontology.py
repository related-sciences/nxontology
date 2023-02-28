from __future__ import annotations

import itertools
import json
import logging
from typing import Any, Generic, Iterable, cast

import fsspec
import networkx as nx
from networkx.algorithms.cycles import simple_cycles
from networkx.algorithms.isolate import isolates
from networkx.readwrite.json_graph import node_link_data, node_link_graph

from nxontology.node import Node

from .exceptions import DuplicateError, NodeNotFound
from .node import Node_Info
from .similarity import SimilarityIC
from .utils import Freezable, cache_on_frozen, get_datetime_now, get_nxontology_version

logger = logging.getLogger(__name__)


class NXOntology(Freezable, Generic[Node]):
    """
    Encapsulate a networkx.DiGraph to represent an ontology.
    Regarding edge directionality, parent terms should point to child term.
    Edges should go from general to more specific.
    """

    def __init__(self, graph: nx.DiGraph | None = None):
        self.graph = nx.DiGraph(graph)
        if graph is None:
            # Store the nxontology version that created the graph as metadata,
            # in case there are compatability issues in the future.
            self._add_nxontology_metadata()
        self.check_is_dag()
        self._node_info_cache: dict[Node, Node_Info[Node]] = {}

    def _add_nxontology_metadata(self) -> None:
        self.graph.graph["nxontology_version"] = get_nxontology_version()
        self.graph.graph["nxontology_created"] = get_datetime_now()

    def check_is_dag(self) -> None:
        if nx.is_directed_acyclic_graph(self.graph):
            return
        # show at most 5 cycles to keep stderr manageable
        cycles = itertools.islice(simple_cycles(self.graph), 5)
        cycles_str = "\n".join(
            " --> ".join(str(n) for n in [*cycle, cycle[0]]) for cycle in cycles
        )
        raise ValueError(
            f"NXOntology requires a directed acyclic graph. Cycles found:\n{cycles_str}"
        )

    @property
    def name(self) -> str | None:
        """Short human-readable name for the ontology."""
        key = self.graph.graph.get("graph_name_attribute", "name")
        name = self.graph.graph.get(key)
        if name is not None:
            return str(name)
        return None

    def write_node_link_json(self, path: str) -> None:
        """
        Serialize to node-link data.
        """
        nld = node_link_data(self.graph)
        with fsspec.open(path, "wt", compression="infer") as write_file:
            json.dump(obj=nld, fp=write_file, indent=2, ensure_ascii=False)

    @classmethod
    def read_node_link_json(cls, path: str) -> NXOntology[Node]:
        """
        Retrun a new graph from node-link format as written by `write_node_link_json`.
        """
        with fsspec.open(path, "rt", compression="infer") as read_file:
            nld = json.load(read_file)
        digraph = node_link_graph(nld, directed=True, multigraph=False)
        assert isinstance(digraph, nx.DiGraph)
        # Construct an NXOntology from the DiGraph
        nxo = cls(digraph)
        return nxo

    def add_node(self, node_for_adding: Node, **attr: Any) -> None:
        """
        Like networkx.DiGraph.add_node but raises a DuplicateError
        if the node already exists.
        """
        if node_for_adding in self.graph:
            raise DuplicateError(f"node already in graph: {node_for_adding}")
        self.graph.add_node(node_for_adding, **attr)

    def add_edge(self, u_of_edge: Node, v_of_edge: Node, **attr: Any) -> None:
        """
        Like networkx.DiGraph.add_edge but
        raises a NodeNotFound if either node does not exist
        or a DuplicateError if the edge already exists.
        Edge should from general to specific,
        such that `u_of_edge` is a parent/superterm/hypernym of `v_of_edge`.
        """
        for node in u_of_edge, v_of_edge:
            if node not in self.graph:
                raise NodeNotFound(f"node does not exist in graph: {node}")
        if self.graph.has_edge(u_of_edge, v_of_edge):
            raise DuplicateError(f"edge already in graph: {u_of_edge} --> {v_of_edge}")
        self.graph.add_edge(u_of_edge, v_of_edge, **attr)

    @property
    @cache_on_frozen
    def roots(self) -> set[Node]:
        """
        Return all top-level nodes, including isolates.
        """
        roots = set()
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0:
                roots.add(node)
        return roots

    @property
    def root(self) -> Node:
        """
        Sole root of this directed acyclic graph.
        If this ontology has multiple roots, raise ValueError.
        This function is intended as a convenience function for ontologies that are weakly connected,
        meaning all nodes derive from a single root.
        """
        roots = self.roots
        if len(roots) == 1:
            (root,) = roots
            return root
        raise ValueError("Ontology has multiple roots.")

    @property
    @cache_on_frozen
    def leaves(self) -> set[Node]:
        """
        Return all bottom-level nodes, including isolates.
        """
        leaves = set()
        for node in self.graph.nodes():
            if self.graph.out_degree(node) == 0:
                leaves.add(node)
        return leaves

    @property
    @cache_on_frozen
    def isolates(self) -> set[Node]:
        """
        Return disconnected nodes.
        """
        return set(isolates(self.graph))

    def freeze(self) -> None:
        """
        Modify graph to prevent further change by adding or removing nodes or edges.
        Node and edge data can still be modified.
        Enables caching of potentially expensive operations.
        """
        nx.freeze(self.graph)

    @property
    def frozen(self) -> bool:
        """Whether the graph is currently frozen."""
        return cast(bool, nx.is_frozen(self.graph))

    def similarity(
        self,
        node_0: Node,
        node_1: Node,
        ic_metric: str = "intrinsic_ic_sanchez",
    ) -> SimilarityIC[Node]:
        """SimilarityIC instance for the specified nodes"""
        return SimilarityIC(self, node_0, node_1, ic_metric)

    def similarity_metrics(
        self,
        node_0: Node,
        node_1: Node,
        ic_metric: str = "intrinsic_ic_sanchez",
        keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Compute intrinsic similarity metrics for two nodes.
        """
        sim = self.similarity(node_0, node_1, ic_metric)
        return sim.results(keys=keys)

    def compute_similarities(
        self,
        source_nodes: Iterable[Node],
        target_nodes: Iterable[Node],
        ic_metrics: list[str] | tuple[str, ...] = ("intrinsic_ic_sanchez",),
    ) -> Iterable[dict[str, Any]]:
        """
        Yield similarity metric dictionaries for all combinations of
        source_node-target_node-ic_metric.
        """
        self.freeze()
        for node_0, node_1, ic_metric in itertools.product(
            source_nodes, target_nodes, ic_metrics
        ):
            metrics = self.similarity_metrics(node_0, node_1, ic_metric=ic_metric)
            yield metrics

    def node_info(self, node: Node) -> Node_Info[Node]:
        """
        Return Node_Info instance for `node`.
        If frozen, cache node info in `self._node_info_cache`.
        """
        if not self.frozen:
            return Node_Info(self, node)
        if node not in self._node_info_cache:
            self._node_info_cache[node] = Node_Info(self, node)
        return self._node_info_cache[node]

    @cache_on_frozen
    def _get_name_to_node_info(self) -> dict[str, Node_Info[Node]]:
        name_to_node_info: dict[str, Node_Info[Node]] = {}
        for node in self.graph:
            info = self.node_info(node)
            name = info.name
            if not name:
                continue
            if name in name_to_node_info:
                logger.warning(
                    f"Node name duplicated for nodes {name_to_node_info[name].node!r} & {node!r}: {name!r}"
                )
            name_to_node_info[name] = info
        return name_to_node_info

    def node_info_by_name(self, name: str) -> Node_Info[Node]:
        """
        Return Node_Info instance using a lookup by name.
        """
        name_to_node_info = self._get_name_to_node_info()
        if name not in name_to_node_info:
            raise NodeNotFound(f"No node found named {name!r}.")
        return name_to_node_info[name]

    @property
    def n_nodes(self) -> int:
        """
        Total number of nodes in the graph.
        """
        # int wrapper is solely to satisfy mypy
        return int(self.graph.number_of_nodes())

    @property
    def n_edges(self) -> int:
        """
        Total number of edges in the graph.
        """
        # int wrapper is solely to satisfy mypy
        return int(self.graph.number_of_edges())

    def set_graph_attributes(
        self,
        *,
        graph_name_attribute: str | None = None,
        node_name_attribute: str | None = None,
        node_identifier_attribute: str | None = None,
        node_url_attribute: str | None = None,
    ) -> None:
        """
        Convenience method to set attributes on the graph that are recognized by nxontology.
        - graph_name_attribute: graph attribute for looking up the graph's name.
          Example name of a graph are as 'Metal', 'EFO', 'MeSH'.
          Defaults to "name" if not set.
        - node_name_attribute: node attribute for looking up a node's name.
          Defaults to "name" if not set.
        - node_identifier_attribute: node attribute for looking up a node's identifier.
          Defaults to "identifier" if not set.
        - node_url_attribute: node attribute for looking up a node's URL.
          Defaults to "url" if not set.
        Setting the value of `node_*_attribute` arguments to '{node}' specifies using the
        node itself rather than an attribute. This is helpful for example when nodes are
        indexed by their identifiers, such that there is no need to include a duplicate
        identifier node attribute.
        """
        if graph_name_attribute:
            self.graph.graph["graph_name_attribute"] = graph_name_attribute
        if node_name_attribute:
            self.graph.graph["node_name_attribute"] = node_name_attribute
        if node_identifier_attribute:
            self.graph.graph["node_identifier_attribute"] = node_identifier_attribute
        if node_url_attribute:
            self.graph.graph["node_url_attribute"] = node_url_attribute
