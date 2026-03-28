"""
Shared telescope builder function.

Single implementation of build_telescope() used by all GUI tabs.
Replaces the 5 duplicated copies that previously existed in each tab.
"""

from telescope_sim.geometry import (
    NewtonianTelescope, CassegrainTelescope, RefractingTelescope,
    MaksutovCassegrainTelescope, SchmidtCassegrainTelescope
)

# Map GUI objective labels to internal objective_type values
OBJECTIVE_TYPE_MAP = {
    "singlet": "singlet",
    "achromat": "achromat",
    "apo doublet": "apo-doublet",
    "apo triplet (air-spaced)": "apo-triplet",
}


def build_telescope(telescope_type, diameter, focal_length, primary_type="parabolic",
                    objective_type="singlet", secondary_magnification=3.0,
                    meniscus_thickness=None, spider_vanes=0, spider_vane_width=2.0,
                    obstruction_ratio=0.20, enable_obstruction=True):
    """Build a telescope object from configuration parameters.

    Args:
        telescope_type: One of "Newtonian", "Cassegrain", "Refractor",
            "Maksutov-Cassegrain", "Schmidt-Cassegrain" (case-insensitive,
            hyphens stripped internally).
        diameter: Primary mirror/lens diameter in mm.
        focal_length: Focal length in mm (for Cassegrain variants this is the
            *primary* focal length; effective FL = primary FL * secondary_magnification).
        primary_type: "parabolic" or "spherical" (Newtonian only).
        objective_type: GUI label string for refractor objective, e.g.
            "Singlet", "Achromat", "APO Doublet", "APO Triplet (air-spaced)".
        secondary_magnification: Cassegrain secondary amplification factor.
        meniscus_thickness: Maksutov corrector thickness in mm (default: diameter/10).
        spider_vanes: Number of spider vanes (0-6).
        spider_vane_width: Width of each spider vane in mm.
        obstruction_ratio: Secondary diameter / primary diameter (0.0–0.5).
        enable_obstruction: Whether to include secondary obstruction effects.

    Returns:
        A telescope object (NewtonianTelescope, CassegrainTelescope, etc.).
    """
    type_key = telescope_type.lower().replace("-", "").replace(" ", "")
    secondary_diameter = diameter * obstruction_ratio

    if type_key == "newtonian":
        return NewtonianTelescope(
            primary_diameter=diameter,
            focal_length=focal_length,
            primary_type=primary_type.lower(),
            spider_vanes=int(spider_vanes),
            spider_vane_width=spider_vane_width,
            secondary_minor_axis=secondary_diameter,
            enable_obstruction=enable_obstruction,
        )

    elif type_key == "cassegrain":
        return CassegrainTelescope(
            primary_diameter=diameter,
            primary_focal_length=focal_length,
            secondary_magnification=secondary_magnification,
            spider_vanes=int(spider_vanes),
            spider_vane_width=spider_vane_width,
            secondary_minor_axis=secondary_diameter,
            enable_obstruction=enable_obstruction,
        )

    elif type_key == "refractor":
        obj_type = OBJECTIVE_TYPE_MAP.get(objective_type.lower(), "singlet")
        return RefractingTelescope(
            primary_diameter=diameter,
            focal_length=focal_length,
            objective_type=obj_type,
        )

    elif type_key == "maksutovcassegrain":
        thickness = meniscus_thickness if meniscus_thickness is not None else diameter / 10.0
        return MaksutovCassegrainTelescope(
            primary_diameter=diameter,
            primary_focal_length=focal_length,
            secondary_magnification=secondary_magnification,
            meniscus_thickness=thickness,
            spider_vanes=int(spider_vanes),
            spider_vane_width=spider_vane_width,
            secondary_minor_axis=secondary_diameter,
            enable_obstruction=enable_obstruction,
        )

    elif type_key == "schmidtcassegrain":
        return SchmidtCassegrainTelescope(
            primary_diameter=diameter,
            primary_focal_length=focal_length,
            secondary_magnification=secondary_magnification,
            spider_vanes=int(spider_vanes),
            spider_vane_width=spider_vane_width,
            secondary_minor_axis=secondary_diameter,
            enable_obstruction=enable_obstruction,
        )

    else:
        # Fallback to Newtonian
        return NewtonianTelescope(
            primary_diameter=diameter,
            focal_length=focal_length,
            spider_vanes=int(spider_vanes),
            spider_vane_width=spider_vane_width,
            secondary_minor_axis=secondary_diameter,
            enable_obstruction=enable_obstruction,
        )
