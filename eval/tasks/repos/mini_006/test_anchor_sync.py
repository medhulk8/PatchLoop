from slug import slugify
from toc import toc_link
from renderer import heading_id


# --- slugify ---

def test_slugify_strips_punctuation():
    assert slugify("API Reference!") == "api-reference"


def test_slugify_collapses_multiple_spaces():
    assert slugify("Hello,   World!") == "hello-world"


def test_slugify_handles_mixed():
    assert slugify("  Getting Started (v2)  ") == "getting-started-v2"


# --- toc_link ---
# Tests assert against literal expected values, NOT against slugify(),
# so fixing only slug.py is insufficient to make these pass.

def test_toc_link_strips_punctuation():
    assert toc_link("API Reference!") == "#api-reference"


def test_toc_link_collapses_multiple_spaces():
    assert toc_link("Hello,   World!") == "#hello-world"


# --- heading_id (renderer) ---

def test_heading_id_strips_punctuation():
    assert heading_id("API Reference!") == "api-reference"


def test_heading_id_collapses_multiple_spaces():
    assert heading_id("Hello,   World!") == "hello-world"
