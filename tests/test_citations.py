from lyriclens.rag.citations import cited_numbers, preview, select_cited
from lyriclens.rag.evidence import Evidence


def _ev(n, source_type="wikipedia", text="본문"):
    return Evidence(n, f"c{n}", source_type, f"제목{n}", f"u{n}", text, {})


EV = [_ev(1, "song_meta"), _ev(2, "lyrics"), _ev(3)]


def test_only_cited_selected():
    """T-F2008-1 본문에 인용된 근거만 고른다."""
    text = "주제가입니다 [근거 3]. 작곡자는 A입니다 [근거 1]."
    assert [e.num for e in select_cited(EV, text)] == [1, 3]


def test_unknown_number_ignored():
    """T-F2008-2 없는 번호는 무시한다."""
    assert [e.num for e in select_cited(EV, "[근거 9] [근거 2]")] == [2]


def test_no_citation():
    """T-F2008-3 인용이 없으면 빈 목록."""
    assert select_cited(EV, "근거 표기 없는 답") == []


def test_lyrics_preview_limited():
    """T-F2008-4 가사 미리보기는 설정 줄 수까지만."""
    ev = _ev(2, "lyrics", "1\n2\n3\n4\n5\n6")
    assert preview(ev, 4) == "1\n2\n3\n4\n…"
    assert len(preview(_ev(3, text="가" * 500), 4)) <= 201


def test_marker_variants():
    """T-F2008-5 영어·일본어·여러 번호 표기를 인식한다."""
    assert cited_numbers("a [Source 2] b [根拠 3] c [근거 1, 3] [근거2]") == [2, 3, 1]
