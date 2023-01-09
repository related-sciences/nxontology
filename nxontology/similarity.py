from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Generic

if TYPE_CHECKING:
    from nxontology.ontology import NXOntology

from networkx import shortest_path_length

from nxontology.node import Node, Node_Info
from nxontology.utils import Freezable, cache_on_frozen


class Similarity(Freezable, Generic[Node]):
    """
    Compute intrinsic similarity metrics for a pair of nodes.
    """

    default_results = [
        "node_0",
        "node_1",
        "node_0_subsumes_1",
        "node_1_subsumes_0",
        "depth",
        "n_common_ancestors",
        "n_union_ancestors",
        "batet",
        "batet_log",
    ]

    def __init__(self, nxo: NXOntology[Node], node_0: Node, node_1: Node):
        self.nxo = nxo
        self.node_0 = node_0
        self.node_1 = node_1
        self.info_0 = nxo.node_info(node_0)
        self.info_1 = nxo.node_info(node_1)

    @property
    def frozen(self) -> bool:
        return self.nxo.frozen

    @property
    @cache_on_frozen
    def node_0_subsumes_1(self) -> bool:
        return self.node_0 in self.info_1.ancestors

    @property
    @cache_on_frozen
    def node_1_subsumes_0(self) -> bool:
        return self.node_1 in self.info_0.ancestors

    @property
    @cache_on_frozen
    def depth(self) -> int | None:
        """
        Get the depth of node_1 beneath node_0 as a positive int, when node_0 is an ancestor of node_1.
        Get the depth of node_0 beneath node_1 as a negative int, when node_1 is an ancestor of node_0.
        Returns None if neither node is an ancestor of the other.
        """
        if self.node_0 == self.node_1:
            return 0
        if self.node_0_subsumes_1:
            return int(shortest_path_length(self.nxo.graph, self.node_0, self.node_1))
        if self.node_1_subsumes_0:
            return -int(shortest_path_length(self.nxo.graph, self.node_1, self.node_0))
        return None

    @property
    @cache_on_frozen
    def common_ancestors(self) -> set[Node]:
        return self.info_0.ancestors & self.info_1.ancestors

    @property
    @cache_on_frozen
    def union_ancestors(self) -> set[Node]:
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
        # replace negative sign with abs to avoid returning -0.0.
        return abs(math.log(1 - self.batet) / math.log(self.n_union_ancestors))

    def results(self, keys: list[str] | None = None) -> dict[str, Any]:
        if keys is None:
            keys = self.default_results
        return {key: getattr(self, key) for key in keys}


class SimilarityIC(Similarity[Node]):
    """
    Compute intrinsic similarity metrics for a pair of nodes,
    including Information Content (IC) derived metrics.
    Changing ic_metric after instantation is not safe due to caching.
    """

    def __init__(
        self,
        graph: NXOntology[Node],
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

    def _get_ic(self, node_info: Node_Info[Node], ic_metric: str) -> float:
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

    @property
    @cache_on_frozen
    def _resnik_mica(self) -> tuple[float, Node | None]:
        if not self.common_ancestors:
            return 0.0, None
        resnik, mica = max(
            (getattr(self.nxo.node_info(n), self.ic_metric), n)
            for n in self.common_ancestors
        )
        assert isinstance(resnik, float)
        return resnik, mica

    @property
    def mica(self) -> Node | None:
        """
        Most informative common ancestor.
        None if no common ancestors exist.
        """
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
        if self.mica is None:
            return 0.0
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
        ECAI-04 (2004) httpsf://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1065.1695

        From Seco:

        > It should be noted that for the sake of coherence of our implementations
        we normalized and applied a linear transformation to the Jiang and Conrath formula
        transforming it into a similarity function.
        """
        jiang_distance = (
            self.node_0_ic_scaled + self.node_1_ic_scaled - 2 * self.resnik_scaled
        )
        return 1 - jiang_distance / 2
