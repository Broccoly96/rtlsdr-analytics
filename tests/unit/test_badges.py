from __future__ import annotations

from dataclasses import replace

from app.domain.badges import BADGES, BadgeStats

_EMPTY_STATS = BadgeStats(
    total_aircraft=0,
    total_types=0,
    max_farthest_km=None,
    max_total_pass_count=None,
    max_distinct_callsigns=None,
    favorites_count=0,
    days_running=0,
    max_concurrent_ever=None,
)


def test_no_badges_earned_with_empty_stats():
    assert all(not badge.is_earned(_EMPTY_STATS) for badge in BADGES)


def test_badge_keys_are_unique():
    keys = [badge.key for badge in BADGES]
    assert len(keys) == len(set(keys))


def test_first_contact_earned_with_one_aircraft():
    stats = replace(_EMPTY_STATS, total_aircraft=1)
    badge = next(b for b in BADGES if b.key == "first_contact")
    assert badge.is_earned(stats)


def test_aircraft_tier_badges_respect_thresholds():
    stats = replace(_EMPTY_STATS, total_aircraft=100)
    earned = {b.key for b in BADGES if b.is_earned(stats)}
    assert "aircraft_100" in earned
    assert "aircraft_500" not in earned
    assert "aircraft_1000" not in earned


def test_far_catch_requires_threshold_distance():
    below = replace(_EMPTY_STATS, max_farthest_km=299.9)
    at = replace(_EMPTY_STATS, max_farthest_km=300.0)
    badge = next(b for b in BADGES if b.key == "far_catch")
    assert not badge.is_earned(below)
    assert badge.is_earned(at)


def test_favorite_collector_uses_favorites_count():
    stats = replace(_EMPTY_STATS, favorites_count=5)
    badge = next(b for b in BADGES if b.key == "favorite_collector")
    assert badge.is_earned(stats)
    assert badge.progress(stats) == 5


def test_veteran_badges_use_days_running():
    stats = replace(_EMPTY_STATS, days_running=365)
    earned = {b.key for b in BADGES if b.is_earned(stats)}
    assert "veteran_month" in earned
    assert "veteran_year" in earned


def test_progress_defaults_to_none_when_unset():
    # every badge must define a progress fn (even if it just returns None)
    for badge in BADGES:
        badge.progress(_EMPTY_STATS)  # must not raise
