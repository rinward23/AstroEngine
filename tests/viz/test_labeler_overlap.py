from astroengine.viz.core.labeler import Labeler, LabelRequest


def test_labeler_avoids_overlaps_in_primary_band():
    requests = [
        LabelRequest(
            identifier=f"body-{idx}",
            angle=idx * 18.0,
            radius=110.0,
            width=24.0 + (idx % 3) * 6.0,
            height=12.0,
        )
        for idx in range(18)
    ]

    labeler = Labeler(band_radius=110.0, band_height=30.0, radial_step=6.0, max_iterations=4)
    placements = labeler.place(requests)

    primaries = [placement for placement in placements if not placement.leader]
    for index, placement in enumerate(primaries):
        bounds = placement.bounds()
        for other in primaries[index + 1 :]:
            assert not bounds.overlaps(other.bounds(), angle_tolerance=0.1, radial_tolerance=0.1)

    # Fallback leader placements should still expose both endpoints.
    for placement in placements:
        if placement.leader:
            assert placement.leader_start is not None
            assert placement.leader_end is not None
