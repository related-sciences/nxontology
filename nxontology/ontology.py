import abc
import functools
import itertools
import json
import math
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    cast,
)

import fsspec
import networkx as nx
from networkx.readwrite.json_graph import node_link_data, node_link_graph


class Freezable(abc.ABC):
    @property
    @abc.abstractmethod
    def frozen(self) -> bool:
        pass


# Type definitions. networkx does not declare types.
# https://github.com/networkx/networkx/issues/3988#issuecomment-639969263
Node = Hashable
Node_Set = Set[Node]
T = TypeVar("T")
T_Freezable = TypeVar("T_Freezable", bound=Freezable)


def cache_on_frozen(func: Callable[[T_Freezable], T]) -> Callable[[T_Freezable], T]:
    """
    Decorate `func` such that if `self.frozen` is True,
    cache the property's value under the instance.
    `func` must be a method of a Freezable class.

    References:
    - https://stackoverflow.com/q/64882468/4651668
    """
    fname = func.__name__

    @functools.wraps(func)
    def wrapped(self: T_Freezable) -> T:
        if not self.frozen:
            return func(self)
        try:
            method_cache: Dict[str, T] = getattr(self, "__method_cache")
        except AttributeError:
            method_cache: Dict[str, T] = {}  # type: ignore [no-redef]
            setattr(self, "__method_cache", method_cache)
        if fname not in method_cache:
            method_cache[fname] = func(self)
        return method_cache[fname]

    # It would be convenient to `return property(wrapped)`.
    # But mypy looses track of the return type.
    # https://github.com/python/mypy/issues/8083
    return wrapped


class NXOntology(Freezable):
    """
    Encapsulate a networkx.DiGraph to represent an ontology.
    Regarding edge directionality, parent terms should point to child term.
    Edges should go from general to more specific.
    """

    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph = nx.DiGraph(graph)
        self.check_is_dag()
        self._node_info_cache: Dict[Hashable, Node_Info] = {}

    def check_is_dag(self) -> None:
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("NXOntology requires a directed acyclic graph.")

    def write_node_link_json(self, path: str) -> None:
        """
        Serialize to node-link data.
        """
        nld = node_link_data(self.graph)
        with fsspec.open(path, "wt", compression="infer") as write_file:
            json.dump(obj=nld, fp=write_file, indent=2, ensure_ascii=False)

    @classmethod
    def read_node_link_json(cls, path: str) -> "NXOntology":
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

    @property  # type: ignore [misc]
    @cache_on_frozen
    def roots(self) -> "Node_Set":
        """
        Return all top-level nodes.
        """
        roots = set()
        for node in self.graph.nodes():
            if self.graph.out_degree(node) == 0:
                continue
            if self.graph.in_degree(node) == 0:
                roots.add(node)
        return roots

    @property  # type: ignore [misc]
    @cache_on_frozen
    def leaves(self) -> "Node_Set":
        """
        Return all bottom-level nodes.
        """
        leaves = set()
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0:
                continue
            if self.graph.out_degree(node) == 0:
                leaves.add(node)
        return leaves

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
    ) -> "SimilarityIC":
        """SimilarityIC instance for the specified nodes"""
        return SimilarityIC(self, node_0, node_1, ic_metric)

    def similarity_metrics(
        self,
        node_0: Node,
        node_1: Node,
        ic_metric: str = "intrinsic_ic_sanchez",
        keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compute intrinsic similarity metrics for two nodes.
        """
        sim = self.similarity(node_0, node_1, ic_metric)
        return sim.results(keys=keys)

    def compute_similarities(
        self,
        source_nodes: Iterable[Node],
        target_nodes: Iterable[Node],
        ic_metrics: List[str] = ["intrinsic_ic_sanchez"],
    ) -> Iterable[Dict[str, Any]]:
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

    def node_info(self, node: Node) -> "Node_Info":
        """
        Return Node_Info instance for `node`.
        If frozen, cache node info in `self._node_info_cache`.
        """
        if not self.frozen:
            return Node_Info(self, node)
        if node not in self._node_info_cache:
            self._node_info_cache[node] = Node_Info(self, node)
        return self._node_info_cache[node]

    @property
    def n_nodes(self) -> int:
        """
        Total number of nodes in the graph.
        """
        return len(self.graph)


class Node_Info(Freezable):
    """
    Compute metrics and values for a node of an NXOntology.
    Includes intrinsic information content (IC) metrics.
    "Intrinsic" refers to the ability to calculate this measure from the ontology structure itself,
    without requiring an external corpus to ascertain term frequency.
    """

    ic_metrics: List[str] = [
        "intrinsic_ic",
        "intrinsic_ic_sanchez",
    ]
    """
    Supported information content (IC) metrics.
    Each ic_metric has a scaled version accessible by adding a _scaled suffix.
    """

    def __init__(self, nxo: NXOntology, node: Node):
        self.nxo = nxo
        self.node = node

    @property
    def frozen(self) -> bool:
        return self.nxo.frozen

    @property
    def data(self) -> Dict[Any, Any]:
        """Dictionary of node data (properties) for `self.node` in the networkx graph."""
        data = self.nxo.graph.nodes[self.node]
        assert isinstance(data, dict)
        return data

    @property  # type: ignore [misc]
    @cache_on_frozen
    def ancestors(self) -> Node_Set:
        """
        Get ancestors of node in graph, including the node itself.
        Ancestors refers to more general concepts in an ontology,
        i.e. hypernyms, superterms, subsumers.
        """
        ancestors = nx.ancestors(self.nxo.graph, self.node)
        assert isinstance(ancestors, set)
        ancestors.add(self.node)
        return ancestors

    @property  # type: ignore [misc]
    @cache_on_frozen
    def descendants(self) -> Node_Set:
        """
        Get descendants of node in graph, including the node itself.
        Descendants refers to more specific concepts in an ontology,
        i.e. hyponyms, subterms.
        """
        descendants = nx.descendants(self.nxo.graph, self.node)
        assert isinstance(descendants, set)
        descendants.add(self.node)
        return descendants

    @property
    def n_ancestors(self) -> int:
        """Number of ancestors of node in graph, including itself."""
        return len(self.ancestors)

    @property
    def n_descendants(self) -> int:
        """Number of descendants of node in graph, including itself."""
        return len(self.descendants)

    @property  # type: ignore [misc]
    @cache_on_frozen
    def intrinsic_ic(self) -> float:
        """
        Intrinsic Information Content, as initially proposed by Resnik (1999) in Equation 5.

        Semantic Similarity in a Taxonomy: An Information-Based Measure and its Application to Problems of Ambiguity in Natural Language
        P. Resnik
        Journal of Artificial Intelligence Research (1999-07-01) https://doi.org/gftcpz
        DOI: 10.1613/jair.514
        """
        # equivalent formulation commented out (more common in literature)
        # - math.log(self.n_descendants / self.nxo.n_nodes)
        return math.log(self.nxo.n_nodes) - math.log(self.n_descendants)

    @property  # type: ignore [misc]
    @cache_on_frozen
    def intrinsic_ic_scaled(self) -> float:
        """
        Intrinsic Information Content scaled to be in the range of [0,1].
        Initially proposed by Seco et al (2004).

        An Intrinsic Information Content Metric for Semantic Similarity in WordNet.
        Nuno Seco, Tony Veale, Jer Hayes
        ECAI-04 (2004) https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1065.1695

        Metric of intrinsic information content for measuring semantic similarity in an ontology
        Md. Hanif Seddiqui, Masaki Aono
        APCCM (2010-01-01) https://dl.acm.org/doi/10.5555/1862330.1862343
        """
        # equivalent formulation commented out
        # 1.0 - math.log(self.n_descendants) / math.log(self.nxo.n_nodes)
        return self.intrinsic_ic / math.log(self.nxo.n_nodes)

    @property  # type: ignore [misc]
    @cache_on_frozen
    def intrinsic_ic_sanchez(self) -> float:
        """
        Intrinsic Information Content as proposed by Sánchez et al (2011).

        Ontology-based information content computation
        David Sánchez, Montserrat Batet, David Isern
        Knowledge-Based Systems (2011-03) https://doi.org/cwzw4r
        DOI: 10.1016/j.knosys.2010.10.001
        """
        # ic_sanchez: Definition 4 / Equation 10 from https://doi.org/10.1016/j.knosys.2010.10.001
        all_leaves = self.nxo.leaves
        leaves = all_leaves & self.descendants
        # replace negative sign with math.abs to avoid returning -0.0.
        return abs(
            math.log((len(leaves) / self.n_ancestors + 1) / (len(all_leaves) + 1))
        )

    @property  # type: ignore [misc]
    @cache_on_frozen
    def intrinsic_ic_sanchez_scaled(self) -> float:
        """
        Like intrinsic_ic_sanchez, but scaled to be between [0,1],
        by dividing by the theoretical IC of the most informative node.
        """
        return self.intrinsic_ic_sanchez / math.log(len(self.nxo.leaves) + 1)


class Similarity(Freezable):
    """
    Compute intrinsic similarity metrics for a pair of nodes.
    """

    default_results = [
        "node_0",
        "node_1",
        "node_0_subsumes_1",
        "node_1_subsumes_0",
        "n_common_ancestors",
        "n_union_ancestors",
        "batet",
        "batet_log",
    ]

    def __init__(self, nxo: NXOntology, node_0: Node, node_1: Node):
        self.nxo = nxo
        self.node_0 = node_0
        self.node_1 = node_1
        self.info_0 = nxo.node_info(node_0)
        self.info_1 = nxo.node_info(node_1)

    @property
    def frozen(self) -> bool:
        return self.nxo.frozen

    @property  # type: ignore [misc]
    @cache_on_frozen
    def node_0_subsumes_1(self) -> bool:
        return self.node_0 in self.info_1.ancestors

    @property  # type: ignore [misc]
    @cache_on_frozen
    def node_1_subsumes_0(self) -> bool:
        return self.node_1 in self.info_0.ancestors

    @property  # type: ignore [misc]
    @cache_on_frozen
    def common_ancestors(self) -> "Node_Set":
        return self.info_0.ancestors & self.info_1.ancestors

    @property  # type: ignore [misc]
    @cache_on_frozen
    def union_ancestors(self) -> "Node_Set":
        return self.info_0.ancestors | self.info_1.ancestors

    @property
    def n_common_ancestors(self) -> int:
        return len(self.common_ancestors)

    @property
    def n_union_ancestors(self) -> int:
        return len(self.union_ancestors)

    @property
    def batet(self) -> float:
        """
        Similarity metric based on the following paper:

        An ontology-based measure to compute semantic similarity in biomedicine
        Montserrat Batet, David Sánchez, Aida Valls
        Journal of Biomedical Informatics (2011-02) https://doi.org/dfhkjv
        DOI: 10.1016/j.jbi.2010.09.002 · PMID: 20837160

        Compared to paper, omits log-transformation and modify numerator to keep values between [0,1]
        https://discourse.related.vc/t/an-ontology-based-measure-to-compute-semantic-similarity-in-biomedicine/325/2
        """
        return float(self.n_common_ancestors / self.n_union_ancestors)

    @property
    def batet_log(self) -> float:
        """
        See `batet` docs. Adds a log transformation as implemented at
        https://github.com/sharispe/slib/blob/21c57a5c52a2d0557fec8d9de7b46252452cdcdc/slib-sml/src/main/java/slib/sml/sm/core/measures/graph/framework/dag/Sim_Framework_DAG_Set_Batet_2010.java#L44-L97
        """
        if self.batet == 1.0:
            return 1.0
        return -math.log(1 - self.batet) / math.log(self.n_union_ancestors)

    def results(self, keys: Optional[List[str]] = None) -> Dict[str, Any]:
        if keys is None:
            keys = self.default_results
        return {key: getattr(self, key) for key in keys}


class SimilarityIC(Similarity):
    """
    Compute intrinsic similarity metrics for a pair of nodes,
    including Information Content (IC) derived metrics.
    Changing ic_metric after instantation is not safe due to caching.
    """

    def __init__(
        self,
        graph: NXOntology,
        node_0: Node,
        node_1: Node,
        ic_metric: str = "intrinsic_ic_sanchez",
    ):
        super().__init__(graph, node_0, node_1)
        if ic_metric not in Node_Info.ic_metrics:
            raise ValueError(
                f"{ic_metric!r} is not a supported ic_metric. "
                f"Choose from: {', '.join(Node_Info.ic_metrics)}."
            )
        self.ic_metric = ic_metric
        self.ic_metric_scaled = f"{ic_metric}_scaled"

    default_results = [
        *Similarity.default_results,
        "ic_metric",
        "mica",
        "resnik",
        "resnik_scaled",
        "lin",
        "jiang",
        "jiang_seco",
    ]

    def _get_ic(self, node_info: Node_Info, ic_metric: str) -> float:
        ic = getattr(node_info, ic_metric)
        assert isinstance(ic, float)
        return ic

    @property
    def node_0_ic(self) -> float:
        return self._get_ic(self.info_0, self.ic_metric)

    @property
    def node_0_ic_scaled(self) -> float:
        return self._get_ic(self.info_0, self.ic_metric_scaled)

    @property
    def node_1_ic(self) -> float:
        return self._get_ic(self.info_1, self.ic_metric)

    @property
    def node_1_ic_scaled(self) -> float:
        return self._get_ic(self.info_1, self.ic_metric_scaled)

    @property  # type: ignore [misc]
    @cache_on_frozen
    def _resnik_mica(self) -> Tuple[float, Node]:
        resnik, mica = max(
            (getattr(self.nxo.node_info(n), self.ic_metric), n)
            for n in self.common_ancestors
        )
        assert isinstance(resnik, float)
        return resnik, mica

    @property
    def mica(self) -> Node:
        """Most informative common ancestor."""
        return self._resnik_mica[1]

    @property
    def resnik(self) -> float:
        """
        IC of the most informative common ancestor.

        Semantic Similarity in a Taxonomy: An Information-Based Measure and its Application to Problems of Ambiguity in Natural Language
        P. Resnik
        Journal of Artificial Intelligence Research (1999-07-01) https://doi.org/gftcpz
        DOI: 10.1613/jair.514
        """
        return self._resnik_mica[0]

    @property
    def resnik_scaled(self) -> float:
        """Scaled IC of the most informative common ancestor."""
        resnik_scaled = getattr(self.nxo.node_info(self.mica), self.ic_metric_scaled)
        assert isinstance(resnik_scaled, float)
        return resnik_scaled

    @property
    def lin(self) -> float:
        """
        Lin semantic similarity score.
        Lin similarity is invariant to IC scaling.

        An Information-Theoretic Definition of Similarity
        Dekang Lin
        ICML (1998) https://api.semanticscholar.org/CorpusID:5659557
        """
        denominator = self.node_0_ic + self.node_1_ic
        if denominator == 0.0:
            # both nodes have zero IC (i.e. root self-similarity).
            # DiShIn returns 1.0. Ensures lin always returns 1.0 for self-similarity.
            # https://github.com/lasigeBioTM/DiShIn/blob/d6e5f41c3a8b61d7851f645bfae78a3104f70e1d/ssmpy/ssm.py#L553-L558
            # slib returns 0.0
            # https://github.com/sharispe/slib/blob/21c57a5c52a2d0557fec8d9de7b46252452cdcdc/slib-sml/src/main/java/slib/sml/sm/core/measures/graph/pairwise/dag/node_based/Sim_pairwise_DAG_node_Lin_1998.java#L95-L121
            return 1.0
        return 2 * self.resnik / denominator

    @property
    def jiang(self) -> float:
        """
        Jiang & Conrath similarity score from:

        Semantic similarity based on corpus statistics and lexical taxonomy
        Jiang & Conrath
        COLING (1998) https://www.aclweb.org/anthology/O97-1002
        """
        # Matches the DiShIn implementation
        # https://github.com/lasigeBioTM/DiShIn/blob/d6e5f41c3a8b61d7851f645bfae78a3104f70e1d/ssmpy/ssm.py#L561-L591
        jiang_distance = self.node_0_ic + self.node_1_ic - 2 * self.resnik
        return 1 / (jiang_distance + 1)

    @property
    def jiang_seco(self) -> float:
        """
        Jiang & Conrath similarity score (1998) but using scaled IC
        with the formula proposed by Seco et al (Equation 6).

        An Intrinsic Information Content Metric for Semantic Similarity in WordNet.
        Nuno Seco, Tony Veale, Jer Hayes
        ECAI-04 (2004) https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1065.1695

        From Seco:

        > It should be noted that for the sake of coherence of our implementations
        we normalized and applied a linear transformation to the Jiang and Conrath formula
        transforming it into a similarity function.
        """
        jiang_distance = (
            self.node_0_ic_scaled + self.node_1_ic_scaled - 2 * self.resnik_scaled
        )
        return 1 - jiang_distance / 2
