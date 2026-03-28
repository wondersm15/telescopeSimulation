"""
Shared source and seeing helper functions.

Single implementation replacing duplicates in design_tab and images_tab.
"""

from telescope_sim.source.sources import Jupiter, Moon, Saturn, StarField, PointSource


# Seeing presets: name → FWHM in arcseconds (None = no atmosphere)
SEEING_PRESETS = {
    "excellent": 0.8,
    "good": 1.5,
    "average": 2.5,
    "poor": 4.0,
    "none": None,
}


def get_source(source_name):
    """Return an AstronomicalSource from a GUI combo-box label.

    Args:
        source_name: Display name from the combo box, e.g. "Jupiter",
            "Point Source (Star)", "None".

    Returns:
        An AstronomicalSource instance, or None if "None" is selected.
    """
    key = source_name.lower().replace(" ", "")
    if key == "jupiter":
        return Jupiter()
    elif key == "saturn":
        return Saturn()
    elif key == "moon":
        return Moon()
    elif key == "starfield":
        return StarField()
    elif key == "pointsource(star)":
        return PointSource()
    else:
        return None


def get_seeing(seeing_name):
    """Convert a seeing preset label to a numeric value.

    Args:
        seeing_name: Display name from the combo box, e.g. "Good", "None".

    Returns:
        Seeing FWHM in arcseconds, or None for no atmosphere.
    """
    return SEEING_PRESETS.get(seeing_name.lower(), None)
