from nxontology import NXOntology


def create_metal_nxo() -> NXOntology[str]:
    """
    Metals ontology from Fig 1 of "Semantic Similarity Definition" at
    https://doi.org/10.1016/B978-0-12-809633-8.20401-9.
    Also published at https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-2-5/figures/1
    Note edge direction is opposite of the drawing.
    Edges go from general to specific.
    """
    nxo: NXOntology[str] = NXOntology()
    nxo.graph.graph["name"] = "Metals"
    nxo.set_graph_attributes(node_name_attribute="{node}")
    edges = [
        ("metal", "precious"),
        ("metal", "coinage"),
        ("precious", "platinum"),
        ("precious", "palladium"),
        ("precious", "gold"),
        ("precious", "silver"),
        ("coinage", "gold"),
        ("coinage", "silver"),
        ("coinage", "copper"),
    ]
    nxo.graph.add_edges_from(edges)
    return nxo


def create_disconnected_nxo() -> NXOntology[str]:
    """
    Fictitious ontology with disjoint / disconnected components.
    Has multiple root nodes. Helpful for testing.
    https://github.com/related-sciences/nxontology/issues/4
    """
    nxo: NXOntology[str] = NXOntology()
    nxo.add_node("water")
    edges = [
        ("metal", "precious"),
        ("metal", "coinage"),
        ("tree", "conifer"),
        ("conifer", "pine"),
    ]
    nxo.graph.add_edges_from(edges)
    return nxo
