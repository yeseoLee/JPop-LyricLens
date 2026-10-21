from lyriclens.domain.lyrics import quote_lines, split_stanzas


def test_split_stanzas():
    """T-LYR-1 빈 줄 기준으로 나누고 긴 연은 max_lines씩 다시 나눈다."""
    lyrics = "a\nb\n\n\nc\nd\ne\nf\ng\n"
    assert split_stanzas(lyrics, max_lines=3) == ["a\nb", "c\nd\ne", "f\ng"]


def test_quote_lines():
    """T-LYR-2 max_lines 줄까지만 남기고 잘렸으면 … 를 붙인다."""
    assert quote_lines("1\n2\n3\n4\n5", 2) == "1\n2\n…"
    assert quote_lines("1\n2", 4) == "1\n2"
