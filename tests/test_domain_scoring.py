from astroengine.scoring import compute_domain_factor


MULTIPLIERS = {"MIND": 1.25, "BODY": 1.0, "SPIRIT": 1.0}


def test_weighted_scoring_dot_product() -> None:
    domains = {"MIND": 0.8, "BODY": 0.2}
    factor = compute_domain_factor(domains, MULTIPLIERS, method="weighted")
    assert abs(factor - 1.2) < 1e-9


def test_top_scoring_uses_argmax() -> None:
    domains = {"BODY": 0.6, "MIND": 0.4}
    factor = compute_domain_factor(domains, MULTIPLIERS, method="top")
    assert factor == 1.0


def test_softmax_returns_expected_value() -> None:
    domains = {"MIND": 0.5, "BODY": 0.5}
    factor = compute_domain_factor(domains, MULTIPLIERS, method="softmax", temperature=8.0)
    assert 1.0 <= factor <= 1.25

