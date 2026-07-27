from scripts.generate_house_seed_data import _PVI_NATIONAL_BASELINE_DEM_MARGIN, _parse_pvi_dem_margin


def test_national_baseline_margin_matches_the_2020_and_2024_two_party_results():
    # 2024: Trump (R) 49.8%, Harris (D) 48.3% -> two-party margin ~D-1.53
    # 2020: Biden (D) 51.3%, Trump (R) 46.8%  -> two-party margin ~D+4.59
    # Average of the two.
    assert abs(_PVI_NATIONAL_BASELINE_DEM_MARGIN - 1.529) < 0.001


def test_parse_pvi_doubles_the_share_difference_and_adds_the_national_baseline():
    # Cook PVI's own "N" is a vote-share difference from the national
    # average, not a margin -- R+33 means the district's average Republican
    # two-party vote share was 33 points higher than the national average,
    # which converts to roughly double that in margin terms.
    baseline = _PVI_NATIONAL_BASELINE_DEM_MARGIN
    assert _parse_pvi_dem_margin("R+33") == round(baseline + 2 * -33, 2)
    assert _parse_pvi_dem_margin("D+10") == round(baseline + 2 * 10, 2)
    assert _parse_pvi_dem_margin("R+7") == round(baseline - 14, 2)


def test_parse_pvi_even_is_the_national_baseline_not_zero():
    # "EVEN" means the district matches the national average exactly --
    # since that average itself leans slightly Democratic (see the baseline
    # test above), an EVEN district's margin is the baseline, not a flat 0.
    assert _parse_pvi_dem_margin("EVEN") == round(_PVI_NATIONAL_BASELINE_DEM_MARGIN, 2)


def test_parse_pvi_returns_none_for_unscraped_or_unrecognized_values():
    assert _parse_pvi_dem_margin(None) is None
    assert _parse_pvi_dem_margin("") is None
    assert _parse_pvi_dem_margin("garbage") is None
