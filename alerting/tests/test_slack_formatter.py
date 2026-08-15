from alerting.slack_formatter import build_slack_payload


def test_formats_known_rule_with_emoji():
    payload = build_slack_payload(
        {
            "rule": "brute_force",
            "source_ip": "203.0.113.5",
            "detail": "6 failed logins within 0:05:00",
            "triggered_at": "2026-01-01T00:00:00+00:00",
        }
    )
    assert ":rotating_light:" in payload["text"]
    assert "203.0.113.5" in payload["text"]
    assert "6 failed logins" in payload["text"]


def test_falls_back_to_default_emoji_for_unknown_rule():
    payload = build_slack_payload(
        {
            "rule": "future_rule",
            "source_ip": "10.0.0.1",
            "detail": "something new",
            "triggered_at": "2026-01-01T00:00:00+00:00",
        }
    )
    assert ":warning:" in payload["text"]
