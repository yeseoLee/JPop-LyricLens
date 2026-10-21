from lyriclens.config import load_settings
from lyriclens.domain.documents import song_meta_doc
from lyriclens.index.store import VectorStore
from lyriclens.services.condition_search import search_by_condition
from tests.fakes import FakeChatModel, FakeEmbeddings, make_song


def _store(tmp_path):
    store = VectorStore(tmp_path, FakeEmbeddings())
    songs = [
        make_song("ut_aa0001", title="雨の別れ", release_date="2019-06-01", tieup=None),
        make_song("ut_bb0002", title="星の街", release_date="2021-04-05"),
        make_song("ut_cc0003", title="夏の海", release_date="2023-07-07", tieup="CM曲"),
    ]
    store.upsert("song_meta", [song_meta_doc(s, 6000) for s in songs])
    return store


def _run(tmp_path, responses, condition="2020년 이후 애니 주제가"):
    chat = FakeChatModel(responses)
    return search_by_condition(condition, _store(tmp_path), chat, load_settings()), chat


def test_unknown_ids_dropped(tmp_path):
    """T-F2011-1 후보에 없는 ID는 결과에서 빠진다."""
    res, _ = _run(
        tmp_path,
        [
            '{"query": "애니 주제가", "year_from": null, "year_to": null}',
            '[{"song_id": "ut_zz9999", "reason": "x"},'
            ' {"song_id": "ut_bb0002", "reason": "애니 주제가"}]',
        ],
    )
    assert [m.song_id for m in res.matches] == ["ut_bb0002"]
    assert res.matches[0].reason == "애니 주제가" and res.matches[0].year == 2021
    assert res.status == "ok"


def test_empty_selection(tmp_path):
    """T-F2011-2 선별 결과가 비면 empty 상태."""
    res, _ = _run(tmp_path, ['{"query": "q", "year_from": null, "year_to": null}', "[]"])
    assert res.status == "empty" and res.matches == []


def test_year_filter(tmp_path):
    """T-F2011-3 연도 조건이 있으면 release_year 필터로 후보를 좁힌다."""
    res, chat = _run(
        tmp_path, ['{"query": "애니 주제가", "year_from": 2020, "year_to": null}', "[]"]
    )
    assert res.year_filter == {"release_year": {"$gte": 2020}}
    listing = chat.calls[1][-1].content
    assert "ut_bb0002" in listing and "ut_cc0003" in listing and "ut_aa0001" not in listing


def test_parse_failure_uses_raw_condition(tmp_path):
    """T-F2011-4 해석 실패 시 원문 조건으로 검색하고 연도 필터는 없다."""
    res, chat = _run(tmp_path, ["???", "???", "[]"])
    assert res.year_filter is None
    assert "ut_aa0001" in chat.calls[-1][-1].content


def test_select_prompt_contents(tmp_path):
    """T-F2011-5 선별 프롬프트에 후보 정보가 들어간다."""
    _, chat = _run(tmp_path, ['{"query": "q", "year_from": null, "year_to": null}', "[]"])
    listing = chat.calls[1][-1].content
    for part in [
        "星の街",
        "テスト歌手",
        "2021",
        "TVアニメ「テスト」主題歌",
        "2020년 이후 애니 주제가",
    ]:
        assert part in listing


def test_bool_year_ignored(tmp_path):
    """T-F2011-3 연도 자리에 bool이 오면 필터를 걸지 않는다."""
    res, _ = _run(tmp_path, ['{"query": "q", "year_from": true, "year_to": null}', "[]"])
    assert res.year_filter is None
