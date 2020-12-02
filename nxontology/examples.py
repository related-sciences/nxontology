from nxontology import NXOntology


def create_metal_nxo() -> NXOntology:
    """
    Metals ontology from Fig 1 of "Semantic Similarity Definition" at
    https://doi.org/10.1016/B978-0-12-809633-8.20401-9.
    Also published at https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-2-5/figures/1
    Note edge direction is opposite of the drawing.
    Edges go from general to specific.
    """
    nxo = NXOntology()
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
