from lyriclens.rag.language import detect_language


def test_detect_language():
    """T-F2007-5 질문 언어를 ko/ja/en 으로 판별한다."""
    assert detect_language("이 곡은 어떤 드라마 주제가인가요?") == "ko"
    assert detect_language("この曲はどのドラマの主題歌ですか") == "ja"
    assert detect_language("Which drama is this song for?") == "en"
    assert detect_language("主題歌") == "ja"
    assert detect_language("Lemon 가사 뜻") == "ko"
