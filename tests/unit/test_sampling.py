from app.collector.sampling import SIGNIFICANT_ALTITUDE_CHANGE_FT, PositionSampler


def test_first_sighting_is_always_sampled():
    sampler = PositionSampler(sample_interval_seconds=30.0)
    assert sampler.should_sample("aaaaaa", 0.0, 35.0, 139.0, 1000.0) is True


def test_no_resample_before_interval_without_significant_change():
    sampler = PositionSampler(sample_interval_seconds=30.0)
    sampler.should_sample("aaaaaa", 0.0, 35.0, 139.0, 1000.0)
    assert sampler.should_sample("aaaaaa", 10.0, 35.0, 139.0, 1000.0) is False


def test_resample_after_interval_elapses():
    sampler = PositionSampler(sample_interval_seconds=30.0)
    sampler.should_sample("aaaaaa", 0.0, 35.0, 139.0, 1000.0)
    assert sampler.should_sample("aaaaaa", 31.0, 35.0, 139.0, 1000.0) is True


def test_resample_on_significant_position_change():
    sampler = PositionSampler(sample_interval_seconds=30.0)
    sampler.should_sample("aaaaaa", 0.0, 35.0, 139.0, 1000.0)
    assert sampler.should_sample("aaaaaa", 5.0, 35.01, 139.0, 1000.0) is True


def test_resample_on_significant_altitude_change():
    sampler = PositionSampler(sample_interval_seconds=30.0)
    sampler.should_sample("aaaaaa", 0.0, 35.0, 139.0, 1000.0)
    new_altitude = 1000.0 + SIGNIFICANT_ALTITUDE_CHANGE_FT
    assert sampler.should_sample("aaaaaa", 5.0, 35.0, 139.0, new_altitude) is True


def test_forget_bounds_memory():
    sampler = PositionSampler(sample_interval_seconds=30.0)
    sampler.should_sample("aaaaaa", 0.0, 35.0, 139.0, 1000.0)
    assert sampler.active_count() == 1
    sampler.forget("aaaaaa")
    assert sampler.active_count() == 0


def test_tracked_icaos():
    sampler = PositionSampler(sample_interval_seconds=30.0)
    sampler.should_sample("aaaaaa", 0.0, 35.0, 139.0, 1000.0)
    assert sampler.tracked_icaos() == {"aaaaaa"}
