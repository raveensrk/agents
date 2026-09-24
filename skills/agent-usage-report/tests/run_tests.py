#!/usr/bin/env python3
"""Tests for agent-usage-report.

Run with:

    python3 tests/run_tests.py

The adapter tests point every harness at ``tests/fixtures`` through the
environment overrides the adapters already honour, so they never touch real
logs. Expected token totals are written out explicitly: if an adapter changes
its parsing, these numbers fail loudly.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))

FIXTURES = ROOT / "tests" / "fixtures"


def build_opencode_db(path):
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT);
        CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, data TEXT,
                              time_created INTEGER);
        CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
                           data TEXT, time_created INTEGER);
        """
    )
    conn.execute("INSERT INTO session VALUES (?, ?)", ("ses1", "/tmp/demo"))
    conn.execute(
        "INSERT INTO message VALUES (?, ?, ?, ?)",
        ("u1", "ses1", json.dumps({"role": "user"}), 1),
    )
    conn.execute(
        "INSERT INTO part VALUES (?, ?, ?, ?, ?)",
        ("p1", "u1", "ses1", json.dumps({"type": "text", "text": "please run the tests"}), 1),
    )
    conn.execute(
        "INSERT INTO message VALUES (?, ?, ?, ?)",
        ("a1", "ses1", json.dumps({
            "role": "assistant", "cost": 0.004,
            "tokens": {"total": 1600, "input": 1000, "output": 100, "reasoning": 0,
                       "cache": {"write": 0, "read": 500}},
            "modelID": "opencode-test", "providerID": "opencode", "finish": "stop",
        }), 2),
    )
    conn.commit()
    conn.close()


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "opencode.db"
        build_opencode_db(db)
        os.environ["AGENT_REPORT_PI_DIR"] = str(FIXTURES / "pi")
        os.environ["AGENT_REPORT_CLAUDE_DIR"] = str(FIXTURES / "claude")
        os.environ["AGENT_REPORT_CODEX_DIR"] = str(FIXTURES / "codex")
        os.environ["AGENT_REPORT_OPENCODE_DB"] = str(db)

        import collect
        self.collect = collect
        self.records, self.detected, self.missing = collect.load({})
        self.turns = {r["harness"]: r for r in self.records if r["kind"] == "assistant"}

    def tearDown(self):
        for key in ("AGENT_REPORT_PI_DIR", "AGENT_REPORT_CLAUDE_DIR",
                    "AGENT_REPORT_CODEX_DIR", "AGENT_REPORT_OPENCODE_DB"):
            os.environ.pop(key, None)
        self.tmp.cleanup()

    def test_all_harnesses_detected(self):
        names = {item["name"] for item in self.detected}
        self.assertEqual(names, {"pi", "claude_code", "codex", "opencode"})

    def test_pi_tokens(self):
        turn = self.turns["pi"]
        self.assertEqual((turn["input"], turn["cache_read"], turn["output"], turn["total"]),
                         (1000, 500, 100, 1600))
        self.assertEqual(turn["cost"], 0.004)
        self.assertEqual(turn["tool_calls"], 1)
        self.assertEqual(turn["tool_errors"], 1)

    def test_claude_tokens(self):
        turn = self.turns["claude_code"]
        self.assertEqual((turn["input"], turn["cache_read"], turn["cache_write"],
                          turn["output"], turn["total"]), (2, 400, 300, 50, 752))
        self.assertEqual(turn["reasoning"], 5)
        self.assertEqual(turn["tool_errors"], 1)

    def test_codex_folds_cache_into_input(self):
        turn = self.turns["codex"]
        self.assertEqual((turn["input"], turn["cache_read"], turn["output"], turn["total"]),
                         (400, 600, 40, 1040))
        self.assertEqual(turn["stop_reason"], "error")

    def test_opencode_tokens(self):
        turn = self.turns["opencode"]
        self.assertEqual((turn["input"], turn["cache_read"], turn["output"], turn["total"]),
                         (1000, 500, 100, 1600))
        self.assertEqual(turn["cost"], 0.004)

    def test_aggregate_totals(self):
        dataset = self.collect.aggregate(self.records)
        self.assertEqual(dataset["turns"], 4)
        self.assertEqual(dataset["requests"], 4)
        self.assertEqual(dataset["sessions"], 4)
        self.assertEqual(sum(e["total"] for e in dataset["models"].values()), 4992)


class PricingTests(unittest.TestCase):
    def test_cost_from_rates(self):
        import pricing
        rates = {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write": 6.25}
        tokens = {"input": 1_000_000, "output": 1_000_000,
                  "cache_read": 1_000_000, "cache_write": 1_000_000}
        self.assertAlmostEqual(pricing.compute_cost(tokens, rates), 36.75)

    def test_catalog_resolves_namespaced_and_aliased(self):
        import pricing
        catalog = pricing.Catalog()
        catalog.add("openai", "gpt-x", {"input": 1, "output": 2})
        self.assertIsNotNone(catalog.resolve("openai-codex", "gpt-x"))
        self.assertIsNotNone(catalog.resolve("openai", "openai/gpt-x"))
        self.assertIsNone(catalog.resolve("openai", "nope"))

    def test_snapshot_is_usable_offline(self):
        import pricing
        catalog = pricing.build_catalog({}, offline=True)
        self.assertGreater(catalog.size(), 100)


class ScoringTests(unittest.TestCase):
    def _dataset(self):
        def model(name, turns, requests, **kw):
            base = {
                "model": name, "turns": turns, "requests": requests,
                "input": 0, "cache_read": 0, "cache_write": 0, "output": 0,
                "reasoning": 0, "total": 0, "tool_calls": 0, "tool_errors": 0,
                "error_stops": 0, "corrections": 0, "context_window": 0,
                "cost_total": kw.pop("cost_total", 0.0), "cost_recorded": 0.0,
                "cost_per_million": kw.pop("cost_per_million", 0.0),
                "providers": {}, "harnesses": {}, "thinking_levels": {},
                "rates": None, "tools": {},
            }
            base.update(kw)
            return base

        models = {
            "steady": model("steady", 400, 100, cost_per_million=1.0, output=1000, total=10000),
            "flaky": model("flaky", 300, 100, cost_per_million=5.0, error_stops=30,
                           tool_errors=20, total=10000, output=1000),
            "tiny": model("tiny", 5, 5, cost_per_million=0.1, output=50, total=500),
        }
        return {"models": models, "sessions": 1, "requests": 205, "turns": 705,
                "projects": {}, "daily": {}, "hourly": [[0] * 24 for _ in range(7)],
                "switches": {}}

    def test_min_turns_excludes_small_samples(self):
        import score
        dataset = score.compute(self._dataset(), {"score": {"min_turns": 30, "shrink_turns": 0}})
        self.assertEqual({e["model"] for e in dataset["unranked"]}, {"tiny"})
        self.assertIsNone(dataset["models"]["tiny"]["intelligence_score"])

    def test_failures_lower_the_score(self):
        import score
        dataset = score.compute(self._dataset(), {"score": {"min_turns": 30, "shrink_turns": 0}})
        self.assertGreater(dataset["models"]["steady"]["intelligence_score"],
                           dataset["models"]["flaky"]["intelligence_score"])

    def test_shrinkage_pulls_in_small_samples(self):
        import score
        raw = score.compute(self._dataset(), {"score": {"min_turns": 3, "shrink_turns": 0}})
        shrunk = score.compute(self._dataset(), {"score": {"min_turns": 3, "shrink_turns": 500}})
        mean_raw = sum(e["intelligence_raw"] for e in raw["ranking"]) / len(raw["ranking"])
        mean_shrunk = sum(e["intelligence_score"] for e in shrunk["ranking"]) / len(shrunk["ranking"])
        before = abs(raw["models"]["tiny"]["intelligence_raw"] - mean_raw)
        after = abs(shrunk["models"]["tiny"]["intelligence_score"] - mean_shrunk)
        self.assertLess(after, before)

    def test_efficiency_prefers_cheaper_equal_model(self):
        import score
        dataset = self._dataset()
        dataset["models"]["cheap"] = dict(dataset["models"]["steady"], model="cheap",
                                          cost_per_million=0.1)
        result = score.compute(dataset, {"score": {"min_turns": 30, "shrink_turns": 0}})
        self.assertGreater(result["models"]["cheap"]["efficiency_score"],
                           result["models"]["steady"]["efficiency_score"])


class RenderTests(unittest.TestCase):
    def test_html_is_self_contained(self):
        import collect, pricing, render, score
        records = [
            {"kind": "user", "harness": "t", "session_id": "1", "project": "/p",
             "timestamp": 1, "text": "hi"},
            {"kind": "assistant", "harness": "t", "session_id": "1", "project": "/p",
             "timestamp": 2, "provider": "p", "model": "m", "input": 10, "cache_read": 0,
             "cache_write": 0, "output": 5, "reasoning": 0, "total": 15, "cost": 0.01,
             "cost_source": "recorded", "stop_reason": "stop", "tool_calls": 1,
             "tool_errors": 0, "thinking_level": None, "context_window": None,
             "text": "", "tools": {"read": 1}},
        ]
        dataset = collect.aggregate(records)
        pricing.attach(dataset, pricing.Catalog())
        score.compute(dataset, {"score": {"min_turns": 1, "shrink_turns": 0}})
        meta = {"window": "all time", "window_start": "a", "window_end": "b",
                "generated": "now", "detected": [], "missing": [],
                "pricing_source": "test", "pricing_models": 0}
        html = render.build(dataset, meta, {})
        self.assertIn("<!doctype html>", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("%s", html)
        self.assertIn("Most intelligent", html)

    def test_leaderboard_is_sortable_and_filterable(self):
        import collect, pricing, render, score
        records = [
            {"kind": "assistant", "harness": "h<%d>" % index, "session_id": str(index),
             "project": "/p", "timestamp": index + 1, "provider": "p",
             "model": "model-%d" % index, "input": 10 * index, "cache_read": 0,
             "cache_write": 0, "output": 5, "reasoning": 0, "total": 10 * index + 5,
             "cost": 0.01 * index, "cost_source": "recorded", "stop_reason": "stop",
             "tool_calls": 1, "tool_errors": 0, "thinking_level": None,
             "context_window": None, "text": "", "tools": {}}
            for index in range(1, 5)
        ]
        dataset = collect.aggregate(records)
        pricing.attach(dataset, pricing.Catalog())
        score.compute(dataset, {"score": {"min_turns": 1, "shrink_turns": 0}})
        meta = {"window": "all time", "window_start": "a", "window_end": "b",
                "generated": "now", "detected": [], "missing": [],
                "pricing_source": "test", "pricing_models": 0}
        html = render.build(dataset, meta, {})
        self.assertIn('id="lb"', html)
        self.assertIn("data-key='cost_total'", html)
        self.assertIn("data-sort=", html)
        self.assertIn('id="lb-search"', html)
        self.assertIn('id="lb-harness"', html)
        self.assertIn('id="lb-ranked"', html)
        self.assertIn("All harnesses", html)


class OutputDirTests(unittest.TestCase):
    def test_default_is_downloads(self):
        import report
        class Args(object):
            out = None
        self.assertEqual(report._output_dir(Args(), {}), Path.home() / "Downloads")

    def test_out_flag_wins(self):
        import report
        class Args(object):
            out = "/tmp/custom/report.html"
        self.assertEqual(report._output_dir(Args(), {}), Path("/tmp/custom"))

    def test_config_output_dir(self):
        import report
        class Args(object):
            out = None
        self.assertEqual(report._output_dir(Args(), {"output_dir": "/tmp/elsewhere"}),
                         Path("/tmp/elsewhere"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
