"""
test_tools.py
-------------
Tests the agent's TOOLS directly — no LLM API key needed for these.
Run: python test_tools.py

(The full agent loop in agent.py, which needs ANTHROPIC_API_KEY or
GEMINI_API_KEY, is tested separately once a key is added.)
"""

import os
import shutil

from agent import calculator, list_dir, read_file, web_search, write_file

TEST_DIR = "test_tools_tmp"


def test_calculator():
    assert calculator("2 + 2") == "4"
    assert calculator("(10 - 4) * 3") == "18"
    assert calculator("10 / 4") == "2.5"
    assert calculator("not a real expression").startswith("Error")
    print("[PASS] calculator")


def test_file_tools():
    os.makedirs(TEST_DIR, exist_ok=True)
    path = os.path.join(TEST_DIR, "sample.txt")

    result = write_file(path, "hello from the agent")
    assert "Saved" in result

    content = read_file(path)
    assert content == "hello from the agent"

    listing = list_dir(TEST_DIR)
    assert "sample.txt" in listing

    print("[PASS] write_file / read_file / list_dir")


def test_web_search():
    result = web_search("what is an AI agent")
    # Network can be unavailable in some environments; don't hard-fail the
    # whole suite for that, just report it.
    if result.startswith("Error"):
        print(f"[SKIP] web_search (no network or blocked): {result}")
    else:
        assert len(result) > 0
        print("[PASS] web_search")
        print("        sample result:\n" + "\n".join(result.splitlines()[:3]))


def cleanup():
    if os.path.isdir(TEST_DIR):
        shutil.rmtree(TEST_DIR)


if __name__ == "__main__":
    try:
        test_calculator()
        test_file_tools()
        test_web_search()
        print("\nAll tool tests finished.")
    finally:
        cleanup()
