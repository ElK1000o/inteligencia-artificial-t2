# Literature Review — MatEnergy-ML

## 1. DFT Databases and High-Throughput Computation

### 1.1 Materials Project
The Materials Project (Jain et al., 2013) provides a centralized repository of DFT-computed properties for over 150,000 inorganic compounds. Properties include formation energy, energy above hull, band gap, elastic constants, and magnetic ordering. All calculations use VASP with PBE-GGA functionals and Hubbard U corrections for d- and f-electron systems.

> Jain, A. et al. (2013). Commentary: The Materials Project: A materials genome approach to accelerating materials innovation. APL Materials, 1(1), 011002. [TODO: DOI: 10.1063/1.4812323]

### 1.2 AFLOW
AFLOW (Curtarolo et al., 2012) is an automated framework for high-throughput DFT calculations, focused on alloy systems and prototype crystal structures. It contains data for over 3 million compounds.

> Curtarolo, S. et al. (2012). AFLOW: An automatic framework for high-throughput materials discovery. Computational Materials Science, 58, 218–226. [TODO: DOI]

### 1.3 JARVIS-DFT
The Joint Automated Repository for Various Integrated Simulations (JARVIS) provides DFT-computed data using OptB88vdW and beyond-DFT methods (JARVIS-TB, JARVIS-ML).

> Choudhary, K. et al. (2020). The joint automated repository for various integrated simulations (JARVIS) for data-driven materials design. npj Computational Materials, 6(1), 173. [TODO: DOI]

### 1.4 OQMD
The Open Quantum Materials Database (OQMD) provides formation energies for over 800,000 compounds computed with VASP/PBE.

> Saal, J. E. et al. (2013). Materials Design and Discovery with High-Throughput Density Functional Theory. JOM, 65(11), 1501–1509. [TODO: DOI]

---

## 2. Machine Learning for Material Property Prediction

### 2.1 General-Purpose Frameworks
Ward et al. (2016) introduced a general ML framework using compositional features (element statistics) to predict a wide range of material properties. Their Magpie framework directly inspired the compositional descriptor approach used in MatEnergy-ML.

> Ward, L. et al. (2016). A general-purpose machine learning framework for predicting properties of inorganic materials. npj Computational Materials, 2(1), 16028. [TODO: DOI]

### 2.2 Crystal Graph Neural Networks
Xie & Grossman (2018) proposed the Crystal Graph Convolutional Neural Network (CGCNN), which encodes crystal structure as a graph. CGCNN significantly outperforms compositional features for structure-dependent properties.

> Xie, T., & Grossman, J. C. (2018). Crystal Graph Convolutional Neural Networks for an Accurate and Interpretable Prediction of Material Properties. Physical Review Letters, 120(14), 145301. [TODO: DOI]

### 2.3 MEGNet
Chen et al. (2019) extended graph neural networks to MatErials Graph Network (MEGNet), including state attributes (temperature, pressure).

> Chen, C. et al. (2019). Graph Networks as a Universal Machine Learning Framework for Molecules and Crystals. Chemistry of Materials, 31(9), 3564–3572. [TODO: DOI]

### 2.4 Matbench Benchmark
The Matbench benchmark (Dunn et al., 2020) standardizes ML evaluation on materials science tasks, enabling fair comparison of methods on formation energy, band gap, and other targets.

> Dunn, A. et al. (2020). Benchmarking Materials Property Prediction Methods: The Matbench Test Set and Automatminer Reference Algorithm. npj Computational Materials, 6(1), 138. [TODO: DOI]

---

## 3. Feature Engineering for Materials ML

### 3.1 Compositional Descriptors
Meredig et al. (2014) and Ward et al. (2016) showed that composition-based features (average elemental properties, statistics) can predict formation energies and other DFT properties with reasonable accuracy (MAE ~0.08 eV/atom for formation energy).

> Meredig, B. et al. (2014). Combinatorial Screening for New Materials in Unconstrained Composition Space with Machine Learning. Physical Review B, 89(9), 094104. [TODO: DOI]

### 3.2 Structural Descriptors
Behler & Parrinello (2007) introduced symmetry functions for neural network potentials, one of the earliest structural descriptor sets. Since then, many structural fingerprints have been developed (SOAP, ACE, etc.).

> Behler, J., & Parrinello, M. (2007). Generalized Neural-Network Representation of High-Dimensional Potential-Energy Surfaces. Physical Review Letters, 98(14), 146401. [TODO: DOI]

### 3.3 matminer
matminer (Ward et al., 2018) is a Python library that automates featurization of materials data, integrating pymatgen, AFLOW-ML, and Materials Project APIs.

> Ward, L. et al. (2018). Matminer: An open source toolkit for materials data mining. Computational Materials Science, 152, 60–69. [TODO: DOI]

---

## 4. Li-ion Battery Materials

### 4.1 LiFePO4 Cathodes
Padhi et al. (1997) introduced LiFePO4 (olivine) as a cathode material. Its low toxicity, thermal stability, and cycle life make it a benchmark for computational screening.

> Padhi, A. K. et al. (1997). Phospho-olivines as Positive-Electrode Materials for Rechargeable Lithium Batteries. Journal of the Electrochemical Society, 144(4), 1188. [TODO: DOI]

### 4.2 Computational Screening of Cathodes
Urban et al. (2016) provide a review of DFT-based screening criteria for Li-ion cathode materials, discussing voltage, stability, and diffusion barriers.

> Urban, A. et al. (2016). Computational understanding of Li-ion batteries. npj Computational Materials, 2(1), 16002. [TODO: DOI]

### 4.3 Solid Electrolytes
Bachman et al. (2016) review solid-state Li-ion conductors, including LLZO (Li₇La₃Zr₂O₁₂) and LGPS, providing DFT screening criteria.

> Bachman, J. C. et al. (2016). Inorganic Solid-State Electrolytes for Lithium Batteries: Mechanisms and Properties Governing Ion Conduction. Chemical Reviews, 116(1), 140–162. [TODO: DOI]

---

## 5. Energy Above Hull and Thermodynamic Stability

The energy above the convex hull (E_hull) is the standard DFT criterion for thermodynamic stability screening. A material with E_hull = 0 is on the convex hull at 0 K. The threshold of 0.05 eV/atom for "stability" is empirical and widely used in the community.

> Sun, W. et al. (2016). The thermodynamic scale of inorganic crystalline metastability. Science Advances, 2(11), e1600225. [TODO: DOI]

---

## 6. Limitations of DFT-Based ML

### 6.1 Functional Errors
PBE-GGA systematically underestimates band gaps and overestimates lattice constants. Formation energy errors of 0.1 eV/atom are common for transition metal oxides.

> Perdew, J. P. et al. (1996). Generalized Gradient Approximation Made Simple. Physical Review Letters, 77(18), 3865. [TODO: DOI]

### 6.2 Metastability and Synthesizability
A material with E_hull = 0 is thermodynamically stable at 0 K in vacuum, but may be unstable at room temperature, under atmosphere, or under electrochemical conditions. Computational screening does not guarantee synthesizability.

> Aykol, M. et al. (2018). Thermodynamic limit for synthesis of metastable inorganic materials. Science Advances, 4(4), eaaq0148. [TODO: DOI]

---

*Note: All references marked [TODO: DOI] require verification of the full citation before submission. Do not fabricate DOIs or page numbers.*
