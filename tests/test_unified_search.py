from pathlib import Path

import yaml

from lyriclens.config import load_settings
from lyriclens.services.search_catalog import Catalog, validate_aliases
from lyriclens.services.search_text import kana_to_romaji, normalize_query
from lyriclens.services.unified_search import rrf_fuse, unified_search
from tests.fakes import FakeChatModel

ROOT = Path(__file__).resolve().parents[1]
METAS = [
    {"song_id": "y1", "title": "夜に駆ける", "title_kana": "よるにかける", "artist": "YOASOBI"},
    {"song_id": "y2", "title": "アイドル", "title_kana": "あいどる", "artist": "YOASOBI"},
    {
        "song_id": "h1",
        "title": "Pretender",
        "title_kana": "ぷりてんだー",
        "artist": "Official髭男dism",
    },
    {"song_id": "l1", "title": "紅蓮華", "title_kana": "ぐれんげ", "artist": "LiSA"},
    {"song_id": "k1", "title": "Lemon", "title_kana": "れもん", "artist": "米津玄師"},
]
ARTISTS = {
    "YOASOBI": ["요아소비"],
    "Official髭男dism": ["히게단", "ヒゲダン"],
    "LiSA": ["리사"],
    "米津玄師": ["요네즈"],
}
TITLES = {"y2": ["아이돌", "Idol"], "k1": ["레몬"]}


def _catalog():
    return Catalog.build(METAS, ARTISTS, TITLES)


def _ids(hits):
    return [h.song_id for h in hits]


class NoStore:
    """벡터 채널이 아무것도 돌려주지 않는 저장소 대역."""

    def search(self, name, query, k, where=None):
        return []


def _search(query, chat=None, **search_cfg):
    settings = load_settings(overrides={"search": {**load_settings().search, **search_cfg}})
    return unified_search(query, _catalog(), NoStore(), chat or FakeChatModel(["{}"]), settings)


def test_normalize():
    """T-SEARCH-1 정규화."""
    assert normalize_query("ＹＯＡ SOBI") == normalize_query("yoasobi")
    assert normalize_query("ドライフラワー") == normalize_query("どらいふらわ")
    assert normalize_query(" 夜に、駆ける! ") == "夜に駆ける"


def test_kana_to_romaji():
    """T-SEARCH-2 히라가나 → 로마자."""
    assert kana_to_romaji("よるにかける") == "yorunikakeru"
    assert kana_to_romaji("ぐれんげ") == "gurenge"
    assert kana_to_romaji("しゅくめい") == "shukumei"
    assert kana_to_romaji("がっこう") == "gakkou"


def test_nickname_to_artist_songs():
    """T-SEARCH-3 별명 → 그 아티스트의 곡."""
    hits = _search("히게단", use_llm=False)
    assert _ids(hits)[:1] == ["h1"]
    assert set(_ids(_search("요아소비", use_llm=False))[:2]) == {"y1", "y2"}


def test_typo_fuzzy():
    """T-SEARCH-4 오탈자는 퍼지 일치로 1위."""
    assert _ids(_search("紅連華", use_llm=False))[0] == "l1"
    assert _ids(_search("Pretendr", use_llm=False))[0] == "h1"
    assert _ids(_search("Yoru ni Kakeru", use_llm=False))[0] == "y1"


def test_mixed_artist_and_title():
    """T-SEARCH-5 아티스트+제목 질의는 둘 다 맞는 곡이 1위."""
    assert _ids(_search("요아소비 아이돌", use_llm=False))[0] == "y2"


def test_rrf():
    """T-SEARCH-6 여러 채널에 걸린 곡이 앞서고 완전 일치는 맨 앞."""
    fused = rrf_fuse({"a": ["x", "y"], "b": ["y", "z"]}, {"a": 1.0, "b": 1.0}, k=60)
    assert fused[0] == "y"
    fused = rrf_fuse({"a": ["x", "y"], "b": ["y", "z"]}, {"a": 1.0, "b": 1.0}, k=60, pinned=["z"])
    assert fused[0] == "z"


def test_llm_guess_filters_unknown_and_survives_bad_json():
    """T-SEARCH-7 카탈로그에 없는 추정은 버리고, JSON 실패해도 검색은 된다."""
    chat = FakeChatModel(
        [
            '{"kind": "description", "ja_query": "法医学ドラマ", '
            '"title_guess": ["Lemon", "없는곡"], "artist_guess": ["米津玄師"]}'
        ]
    )
    hits = _search("법의학 드라마 주제가", chat=chat)
    assert _ids(hits)[0] == "k1"
    assert any("llm_guess" in h.channels for h in hits)
    bad = _search("법의학 드라마 주제가", chat=FakeChatModel(["형식 없음"]))
    assert isinstance(bad, list)


def test_no_llm_when_disabled():
    """T-SEARCH-8 use_llm=false 면 LLM 호출 0회."""
    chat = FakeChatModel(["{}"])
    _search("아무 질의", chat=chat, use_llm=False)
    assert chat.calls == []


def test_alias_file_valid():
    """T-SEARCH-9 사전 파일: 40명 모두 있고 별칭이 서로 겹치지 않는다."""
    aliases = yaml.safe_load((ROOT / "config/artist_aliases.yaml").read_text())["aliases"]
    artists = [
        a["name"] for a in yaml.safe_load((ROOT / "config/artists.yaml").read_text())["artists"]
    ]
    assert validate_aliases(aliases, artists) == []
    assert validate_aliases({"A": ["x"], "B": ["X"]}, ["A", "B"])  # 정규화 후 겹침


def test_service_unified_search(tmp_path):
    """T-SEARCH-10 서비스 계층에서 통합 검색 결과를 돌려준다."""
    from lyriclens.collect.cache import CollectCache
    from lyriclens.domain.indexing import index_songs
    from lyriclens.index.store import VectorStore
    from lyriclens.ui.service import LyricLensService
    from tests.fakes import FakeEmbeddings, FakeWikiClient, make_song

    store = VectorStore(tmp_path / "chroma", FakeEmbeddings())
    index_songs([make_song("ut_aa0001")], store, item_text_max_chars=6000, lyrics_chunk_lines=8)
    svc = LyricLensService(
        load_settings(overrides={"search": {**load_settings().search, "use_llm": False}}),
        store,
        FakeChatModel(),
        FakeWikiClient([]),
        CollectCache(tmp_path / "c.json"),
    )
    hits = svc.unified_search("星の街")
    assert hits and hits[0].song_id == "ut_aa0001" and hits[0].reasons
