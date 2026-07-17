"""Tests for the optical filter library (ND + Wratten colour filters).

Focus: the Wratten colour-filter passbands transmit the right channels and
reject the others. The W25 red filter is a long-pass (sharp cut-on ~590 nm);
a previous Gaussian model leaked ~15% green and made white targets read
orange/yellow (user-reported bug, Round 2 / B9).
"""

import pytest

from telescope_sim.physics.filters import (
    get_filter_by_name, FILTER_LIBRARY,
)


class TestNDFilters:
    def test_nd_flat_and_correct_transmission(self):
        for name, expected in [("ND-0.5", 10 ** -0.5),
                               ("ND-1.0", 0.10),
                               ("ND-2.0", 0.01)]:
            f = get_filter_by_name(name)
            tR, tG, tB = f.channel_transmissions()
            # Neutral: all channels equal (within rounding) and = 10^-OD
            assert tR == pytest.approx(expected, abs=1e-3)
            assert tR == pytest.approx(tG) == pytest.approx(tB)


class TestW25LongPassRed:
    """W25 must pass red and reject green/blue (the orange/yellow bug)."""

    def test_channel_transmissions_red_dominant(self):
        tR, tG, tB = get_filter_by_name("W25 (red)").channel_transmissions()
        assert tR > 0.80, "red should pass"
        assert tG < 0.05, f"green leak too high ({tG:.3f}) -> reads yellow"
        assert tB < 0.02, f"blue leak too high ({tB:.3f})"

    def test_sharp_cut_on_near_590nm(self):
        w = get_filter_by_name("W25 (red)")
        # Long-pass: blocked well below the cut-on, open well above.
        assert w.transmission(486.0) < 0.02
        assert w.transmission(550.0) < 0.05
        assert w.transmission(656.0) > 0.80
        # Monotonic non-decreasing across the band (long-pass shape)
        samples = [w.transmission(wl) for wl in range(450, 701, 10)]
        assert all(b >= a - 1e-9 for a, b in zip(samples, samples[1:]))


class TestColourFiltersRejectOppositeChannels:
    def test_w47_blue_rejects_red(self):
        tR, tG, tB = get_filter_by_name("W47 (blue)").channel_transmissions()
        assert tB > tR and tB > tG
        assert tR < 0.05

    def test_w58_green_dominant_low_blue_leak(self):
        tR, tG, tB = get_filter_by_name("W58 (green)").channel_transmissions()
        assert tG > tR and tG > tB
        assert tB < 0.12, f"blue leak too high ({tB:.3f})"
        assert tR < 0.05


class TestW80ALightBlue:
    """W80A (R3.14): the light-blue Jupiter contrast filter — blue-dominant,
    rejects red, and much BRIGHTER than the dark W47 so the disk stays
    visible."""

    def test_blue_dominant_rejects_red(self):
        tR, tG, tB = get_filter_by_name("W80A (light blue)").channel_transmissions()
        assert tB > tG > tR
        assert tR < 0.05

    def test_brighter_than_dark_w47(self):
        _, _, tB80 = get_filter_by_name("W80A (light blue)").channel_transmissions()
        _, _, tB47 = get_filter_by_name("W47 (blue)").channel_transmissions()
        assert tB80 > 2 * tB47, "W80A must pass much more blue than dark W47"

    def test_reveals_jupiter_belt_contrast(self):
        """Under W80A the blue-absorbing belts darken MORE than the white
        zones — the physically-correct Jupiter contrast effect (and better
        than the red W25, which gives a near-uniform disk)."""
        import numpy as np
        lum_w = np.array([0.2126, 0.7152, 0.0722])
        zone = np.array([235, 220, 185]) / 255.0
        belt = np.array([155, 110, 75]) / 255.0

        def belt_over_zone(fname):
            T = np.array(get_filter_by_name(fname).channel_transmissions())
            return (belt * T * lum_w).sum() / (zone * T * lum_w).sum()

        # Lower ratio = belt darker vs zone = more contrast.
        assert belt_over_zone("W80A (light blue)") < belt_over_zone("W25 (red)")


class TestFilterLibrary:
    def test_library_names_unique_and_lookup(self):
        names = [f.name for f in FILTER_LIBRARY]
        assert len(names) == len(set(names))
        for n in names:
            assert get_filter_by_name(n).name == n

    def test_unknown_filter_falls_back_to_none(self):
        assert get_filter_by_name("does-not-exist").name == "None"
