import os

import pytest

from lyriclens.collect.wikipedia import WikiClient


@pytest.mark.live
def test_live_search():
    """T-F2004-5 (live) 실제 한국어 위키백과 검색."""
    contact = os.environ.get("WIKI_CONTACT")
    if not contact:
        pytest.skip("WIKI_CONTACT 없음")
    assert WikiClient(contact=contact).search("요네즈 켄시", 3)
