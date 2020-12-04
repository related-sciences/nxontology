# NetworkX-based Python library for representing ontologies

[![GitHub Actions CI Build Status](https://img.shields.io/github/workflow/status/related-sciences/nxontology/Build?label=actions&style=for-the-badge&logo=github&logoColor=white)](https://github.com/related-sciences/nxontology/actions)  
[![Software License](https://img.shields.io/github/license/related-sciences/nxontology?style=for-the-badge&logo=Apache&logoColor=white)](https://github.com/related-sciences/nxontology/blob/main/LICENSE)  
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge&logo=Python&logoColor=white)](https://github.com/psf/black)  
[![PyPI](https://img.shields.io/pypi/v/nxontology.svg?style=for-the-badge&logo=PyPI&logoColor=white)](https://pypi.org/project/nxontology/)  

## Summary

nxontology is a Python library for representing ontologies using a NetworkX graph.
Currently, the main area of functionality is computing similarity measures between pairs of nodes.

## Usage

Here, we'll use the example [metals ontology](https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-2-5/figures/1 "From Figure 1 of Disjunctive shared information between ontology concepts: application to Gene Ontology. Couto & Silva. 2011. Released under CC BY 2.0."):

![Metals ontology from Couto & Silva (2011)](https://raw.githubusercontent.com/related-sciences/nxontology/3e5ad706dab65bfaa07f5bf57257deac9741195c/media/metals.svg?sanitize=true)
<!-- use absolute URL instead of media/metals.svg for PyPI long_description -->

Note that `NXOntology` represents the ontology as a [`networkx.DiGraph`](https://networkx.org/documentation/stable/reference/classes/digraph.html), where edge direction goes from superterm to subterm.
Currently, users must create their own `networkx.DiGraph` to use this package.

Given an `NXOntology` instance, here how to compute intrinsic similarity metrics.

```python
from nxontology.examples import create_metal_nxo
metals = create_metal_nxo()
# Freezing the ontology prevents adding or removing nodes or edges.
# Frozen ontologies cache expensive computations.
metals.freeze()
# Get object for computing similarity, using the Sanchez et al metric for information content.
similarity = metals.similarity("gold", "silver", ic_metric="intrinsic_ic_sanchez")
# Access a single similarity metric
similarity.lin
# Access all similarity metrics
similarity.results()
```

The final line outputs a dictionary like:

```python
{
    'node_0': 'gold',
    'node_1': 'silver',
    'node_0_subsumes_1': False,
    'node_1_subsumes_0': False,
    'n_common_ancestors': 3,
    'n_union_ancestors': 5,
    'batet': 0.6,
    'batet_log': 0.5693234419266069,
    'ic_metric': 'intrinsic_ic_sanchez',
    'mica': 'coinage',
    'resnik': 0.8754687373538999,
    'resnik_scaled': 0.48860840553061435,
    'lin': 0.5581154235118403, 
    'jiang': 0.41905978419640516,
    'jiang_seco': 0.6131471927654584,
}
```

## Bibliography

Here's a list of alternative projects with code for computing semantic similarity measures on ontologies:

- [Semantic Measures Library & ToolKit](https://www.semantic-measures-library.org/sml/) at [sharispe/slib](https://github.com/sharispe/slib) in Java.
- [DiShIn](http://labs.rd.ciencias.ulisboa.pt/dishin/) at [lasigeBioTM/DiShIn](https://github.com/lasigeBioTM/DiShIn) in Python.
- [Sematch](http://sematch.gsi.upm.es/) at [gsi-upm/sematch](https://github.com/gsi-upm/sematch) in Python.
- [ontologySimilarity](https://rdrr.io/cran/ontologySimilarity/) mirrored at [cran/ontologySimilarity](https://github.com/cran/ontologySimilarity). Part of the [ontologyX](https://doi.org/10.1093/bioinformatics/btw763 "ontologyX: a suite of R packages for working with ontological data") suite of R packages. 
- Materials for Machine Learning with Ontologies at [bio-ontology-research-group/machine-learning-with-ontologies](https://github.com/bio-ontology-research-group/machine-learning-with-ontologies) (compilation)

Below are a list of references related to ontology-derived measures of similarity.
Feel free to add any reference that provides useful context and details for algorithms supported by this package.

<!--
# code to generate references (does not include small number of manual edits) 
manubot cite \
  --format=markdown \
  doi:10.1371/journal.pcbi.1000443 \
  url:https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1065.1695 \
  doi:10.1186/1471-2105-9-S5-S4 \
  doi:10.1093/bib/bbaa199 \
  doi:10.1613/jair.514 \
  https://api.semanticscholar.org/CorpusID:5659557 \
  doi:10.1093/bioinformatics/btw763 \
  https://dl.acm.org/doi/10.5555/1862330.1862343 \
  doi:10.1186/2041-1480-2-5 \
  doi:10.1016/j.jbi.2013.11.006 \
  doi:10.5772/intechopen.89032 \
  doi:10.1016/j.jbi.2010.09.002 \
  doi:10.1186/1471-2105-13-261 \
  doi:10.1016/j.jbi.2011.03.013 \
  doi:10.1016/j.knosys.2010.10.001
-->

1. **Semantic Similarity in Biomedical Ontologies**   
Catia Pesquita, Daniel Faria, André O. Falcão, Phillip Lord, Francisco M. Couto  
*PLoS Computational Biology* (2009-07-31) <https://doi.org/cx8h87>   
DOI: [10.1371/journal.pcbi.1000443](https://doi.org/10.1371/journal.pcbi.1000443) · PMID: [19649320](https://www.ncbi.nlm.nih.gov/pubmed/19649320) · PMCID: [PMC2712090](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2712090)

2. **An Intrinsic Information Content Metric for Semantic Similarity in WordNet.**   
Nuno Seco, Tony Veale, Jer Hayes  
*In Proceedings of the 16th European Conference on Artificial Intelligence (ECAI-04),* (2004) <https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1065.1695>

3. **Metrics for GO based protein semantic similarity: a systematic evaluation**   
Catia Pesquita, Daniel Faria, Hugo Bastos, António EN Ferreira, André O Falcão, Francisco M Couto  
*BMC Bioinformatics* (2008-04-29) <https://doi.org/cmcgw6>   
DOI: [10.1186/1471-2105-9-s5-s4](https://doi.org/10.1186/1471-2105-9-s5-s4) · PMID: [18460186](https://www.ncbi.nlm.nih.gov/pubmed/18460186) · PMCID: [PMC2367622](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2367622)

4. **Semantic similarity and machine learning with ontologies**   
Maxat Kulmanov, Fatima Zohra Smaili, Xin Gao, Robert Hoehndorf  
*Briefings in Bioinformatics* (2020-10-13) <https://doi.org/ghfqkt>   
DOI: [10.1093/bib/bbaa199](https://doi.org/10.1093/bib/bbaa199) · PMID: [33049044](https://www.ncbi.nlm.nih.gov/pubmed/33049044)

5. **Semantic Similarity in a Taxonomy: An Information-Based Measure and its Application to Problems of Ambiguity in Natural Language**   
P. Resnik  
*Journal of Artificial Intelligence Research* (1999-07-01) <https://doi.org/gftcpz>   
DOI: [10.1613/jair.514](https://doi.org/10.1613/jair.514)

6. **An Information-Theoretic Definition of Similarity**   
Dekang Lin  
*ICML* (1998) <https://api.semanticscholar.org/CorpusID:5659557>

7. **ontologyX: a suite of R packages for working with ontological data**   
Daniel Greene, Sylvia Richardson, Ernest Turro  
*Bioinformatics* (2017-01-05) <https://doi.org/f9k7sx>   
DOI: [10.1093/bioinformatics/btw763](https://doi.org/10.1093/bioinformatics/btw763) · PMID: [28062448](https://www.ncbi.nlm.nih.gov/pubmed/28062448) · PMCID: [PMC5386138](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5386138)

8. **Metric of intrinsic information content for measuring semantic similarity in an ontology**   
Md. Hanif Seddiqui, Masaki Aono  
*Proceedings of the Seventh Asia-Pacific Conference on Conceptual Modelling - Volume 110* (2010-01-01) <https://dl.acm.org/doi/10.5555/1862330.1862343>   
ISBN: [9781920682927](https://worldcat.org/isbn/9781920682927)

9. **Disjunctive shared information between ontology concepts: application to Gene Ontology**   
Francisco M Couto, Mário J Silva  
*Journal of Biomedical Semantics* (2011) <https://doi.org/fnb73v>   
DOI: [10.1186/2041-1480-2-5](https://doi.org/10.1186/2041-1480-2-5) · PMID: [21884591](https://www.ncbi.nlm.nih.gov/pubmed/21884591) · PMCID: [PMC3200982](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3200982)

10. **A framework for unifying ontology-based semantic similarity measures: A study in the biomedical domain**   
Sébastien Harispe, David Sánchez, Sylvie Ranwez, Stefan Janaqi, Jacky Montmain  
*Journal of Biomedical Informatics* (2014-04) <https://doi.org/f52557>   
DOI: [10.1016/j.jbi.2013.11.006](https://doi.org/10.1016/j.jbi.2013.11.006) · PMID: [24269894](https://www.ncbi.nlm.nih.gov/pubmed/24269894)

11. **Semantic Similarity in Cheminformatics**   
João D. Ferreira, Francisco M. Couto  
*IntechOpen* (2020-07-15) <https://doi.org/ghh2d4>   
DOI: [10.5772/intechopen.89032](https://doi.org/10.5772/intechopen.89032)

12. **An ontology-based measure to compute semantic similarity in biomedicine**   
Montserrat Batet, David Sánchez, Aida Valls  
*Journal of Biomedical Informatics* (2011-02) <https://doi.org/dfhkjv>   
DOI: [10.1016/j.jbi.2010.09.002](https://doi.org/10.1016/j.jbi.2010.09.002) · PMID: [20837160](https://www.ncbi.nlm.nih.gov/pubmed/20837160)

13. **Semantic similarity in the biomedical domain: an evaluation across knowledge sources**   
Vijay N Garla, Cynthia Brandt  
*BMC Bioinformatics* (2012-10-10) <https://doi.org/gb8vpn>   
DOI: [10.1186/1471-2105-13-261](https://doi.org/10.1186/1471-2105-13-261) · PMID: [23046094](https://www.ncbi.nlm.nih.gov/pubmed/23046094) · PMCID: [PMC3533586](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3533586)
 
14. **Semantic similarity estimation in the biomedical domain: An ontology-based information-theoretic perspective**   
David Sánchez, Montserrat Batet  
*Journal of Biomedical Informatics* (2011-10) <https://doi.org/d2436q>   
DOI: [10.1016/j.jbi.2011.03.013](https://doi.org/10.1016/j.jbi.2011.03.013) · PMID: [21463704](https://www.ncbi.nlm.nih.gov/pubmed/21463704)

15. **Ontology-based information content computation**   
David Sánchez, Montserrat Batet, David Isern  
*Knowledge-Based Systems* (2011-03) <https://doi.org/cwzw4r>   
DOI: [10.1016/j.knosys.2010.10.001](https://doi.org/10.1016/j.knosys.2010.10.001)
