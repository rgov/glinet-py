"""Validate every fixture's response against its OpenRPC schema.

One unittest test per fixture, generated dynamically via the load_tests
protocol. Run with:

    uv run python -m unittest discover tests
    uv run python -m unittest discover tests -v        # verbose: name per test
    uv run python -m unittest tests.test_fixtures.FixtureCase  # single test class
"""
import sys
import unittest
from pathlib import Path

# scripts/ is sibling to tests/; add it to sys.path so we can import paths.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from jsonschema import Draft202012Validator  # noqa: E402
from paths import load_fixtures, load_openrpc_methods  # noqa: E402

_SCHEMAS = {m["name"]: m["result"]["schema"] for m in load_openrpc_methods()}


class FixtureCase(unittest.TestCase):
    """Validate one fixture's documented response against its schema."""

    def __init__(self, fixture):
        super().__init__("runTest")
        self.fixture = fixture

    def id(self):
        return f"tests.test_fixtures.FixtureCase.{self.fixture['name']}"

    def __str__(self):
        return self.fixture["name"]

    def runTest(self):
        fx = self.fixture
        if "response_parse_error" in fx:
            self.skipTest(f"source example malformed: {fx['response_parse_error']}")
        schema = _SCHEMAS.get(fx["name"])
        if schema is None:
            self.fail(f"no schema generated for {fx['name']}")
        result = (fx["response"] or {}).get("result")
        errs = list(Draft202012Validator(schema).iter_errors(result))
        if errs:
            self.fail("\n".join(
                f"{list(e.absolute_path) or '(root)'}: {e.message}"
                for e in errs
            ))


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    for fx in load_fixtures():
        suite.addTest(FixtureCase(fx))
    return suite
