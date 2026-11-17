"""Tests for Adaptive Frame Sampler."""
import pytest
from vision.adaptive_sampler import AdaptiveSampler


def test_sampler_default_rates():
    sampler = AdaptiveSampler(active_fps=5.0, idle_fps=2.0, deep_idle_fps=1.0)
    assert sampler.get_target_fps("ACTIVE") == 5.0
    assert sampler.get_target_fps("IDLE") == 2.0
    assert sampler.get_target_fps("DEEP_IDLE") == 1.0


def test_should_sample_timing():
    sampler = AdaptiveSampler(active_fps=5.0, idle_fps=2.0, deep_idle_fps=1.0)

    # First frame at t=1.0 should be sampled
    assert sampler.should_sample("ACTIVE", current_time=1.0) is True

    # Immediate second frame at t=1.05 (< 0.2s interval) should be rejected
    assert sampler.should_sample("ACTIVE", current_time=1.05) is False

    # Frame at t=1.19 still rejected
    assert sampler.should_sample("ACTIVE", current_time=1.19) is False

    # Frame at t=1.21 (>= 0.20s interval) should be sampled
    assert sampler.should_sample("ACTIVE", current_time=1.21) is True


def test_adaptive_rate_transitions():
    sampler = AdaptiveSampler(active_fps=5.0, idle_fps=2.0, deep_idle_fps=1.0)

    # In IDLE, interval is 0.5s
    assert sampler.should_sample("IDLE", current_time=10.0) is True
    assert sampler.should_sample("IDLE", current_time=10.3) is False
    assert sampler.should_sample("IDLE", current_time=10.51) is True

    # In DEEP_IDLE, interval is 1.0s
    assert sampler.should_sample("DEEP_IDLE", current_time=20.0) is True
    assert sampler.should_sample("DEEP_IDLE", current_time=20.8) is False
    assert sampler.should_sample("DEEP_IDLE", current_time=21.05) is True


def test_sampler_update_rates():
    sampler = AdaptiveSampler(active_fps=5.0, idle_fps=2.0, deep_idle_fps=1.0)
    sampler.update_rates(active_fps=10.0, idle_fps=4.0)
    assert sampler.get_target_fps("ACTIVE") == 10.0
    assert sampler.get_target_fps("IDLE") == 4.0
    assert sampler.get_target_fps("DEEP_IDLE") == 1.0
