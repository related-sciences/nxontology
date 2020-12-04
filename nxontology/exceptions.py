import networkx.exception as nx_exception


class NXO_Exception(Exception):
    """Base class for exceptions in nxontology."""


class DuplicateError(NXO_Exception):
    """
    A node or edge is being added to the graph when it already exists.
    NetworkX add_* methods silently update existing nodes or edges,
    but duplicate additions often arise from dirty input data
    that should be explicitly addressed before graph creation.
    """


class NodeNotFound(NXO_Exception, nx_exception.NodeNotFound):  # type: ignore [misc]
    """Exception raised if requested node is not present in the graph."""
