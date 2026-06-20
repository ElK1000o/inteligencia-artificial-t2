class DescriptorDefinitionService:
    """Defines which descriptors are available and their metadata."""

    COMPOSITIONAL_DESCRIPTORS = [
        "avg_atomic_number",
        "avg_atomic_mass",
        "avg_electronegativity",
        "electronegativity_range",
        "avg_atomic_radius",
        "n_elements",
        "frac_Li",
        "frac_Cu",
        "frac_O",
        "frac_S",
        "frac_P",
        "frac_Fe",
        "frac_Mn",
        "frac_Co",
        "frac_Ni",
        "frac_transition_metals",
        "max_electronegativity",
        "min_electronegativity",
        "std_atomic_number",
        "std_electronegativity",
        "avg_ionization_energy",
        "avg_electron_affinity",
        "stoich_l2",
        "stoich_l3",
        "stoich_l5",
        "stoich_l7",
        "stoich_l10",
        "n_valence_electrons_avg",
        "n_valence_electrons_max",
        "n_valence_electrons_min",
    ]

    STRUCTURAL_DESCRIPTORS = [
        "density",
        "volume_per_atom",
        "space_group_number",
        "lattice_a",
        "lattice_b",
        "lattice_c",
        "alpha",
        "beta",
        "gamma",
        "packing_fraction",
    ]

    @classmethod
    def get_compositional_names(cls) -> list[str]:
        return list(cls.COMPOSITIONAL_DESCRIPTORS)

    @classmethod
    def get_structural_names(cls) -> list[str]:
        return list(cls.STRUCTURAL_DESCRIPTORS)

    @classmethod
    def all_names(cls) -> list[str]:
        return cls.COMPOSITIONAL_DESCRIPTORS + cls.STRUCTURAL_DESCRIPTORS
