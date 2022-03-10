from __future__ import annotations

import math
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Hashable,
    List,
    Optional,
    Set,
    TypeVar,
)

import networkx as nx

from .exceptions import NodeNotFound
from .utils import Freezable, cache_on_frozen

if TYPE_CHECKING:
    from nxontology.ontology import NXOntology


# Type definitions. networkx does not declare types.
# https://github.com/networkx/networkx/issues/3988#issuecomment-639969263
Node = TypeVar("Node", bound=Hashable)


class Node_Info(Freezable, Generic[Node]):
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

    def __init__(self, nxo: NXOntology[Node], node: Node):
        if node not in nxo.graph:
            raise NodeNotFound(f"{node} not in graph.")
        self.nxo = nxo
        self.node = node

    @property
    def label(self) -> Optional[str]:
        """Human readable name / label."""
        value = self._get_node_attribute(
            custom_field="node_label_attribute", default="label"
        )
        return None if value is None else str(value)

    @property
    def identifier(self) -> Optional[Any]:
        """Database / machine identifier."""
        return self._get_node_attribute(
            custom_field="node_identifier_attribute", default="identifier"
        )

    @property
    def url(self) -> Optional[str]:
        """Uniform Resource Locator (URL)"""
        value = self._get_node_attribute(
            custom_field="node_url_attribute", default="url"
        )
        return None if value is None else str(value)

    def _get_node_attribute(self, custom_field: str, default: str) -> Any:
        """Get node attribute for the attribute set by custom_field or by default."""
        key = self.nxo.graph.graph.get(custom_field, default)
        if key == "{node}":
            return self.node
        return self.data.get(key)

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
    def ancestors(self) -> Set[Node]:
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
    def descendants(self) -> Set[Node]:
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
    def depth(self) -> int:
        """Minimum shortest path distance from a root node to this node."""
        depth = min(
            nx.shortest_path_length(self.nxo.graph, root, self.node)
            for root in self.ancestors & self.nxo.roots
        )
        assert isinstance(depth, int)
        return depth

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
        # replace negative sign with abs to avoid returning -0.0.
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
