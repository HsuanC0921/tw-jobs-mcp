import pytest

from tw_jobs_mcp.j104 import codes, query


def test_names_resolve_to_codes():
    assert codes.resolve("area", ["台北市"]) == ["6001001000"]
    assert codes.resolve("area", ["台北市大安區"]) == ["6001001005"]
    assert codes.resolve("jobcat", ["軟體工程師"])


def test_ready_made_code_passes_through():
    assert codes.resolve("area", ["6001001000"]) == ["6001001000"]


def test_ambiguous_name_lists_options():
    with pytest.raises(codes.AmbiguousName) as err:
        codes.resolve("area", ["中山區"])
    assert len(err.value.options) > 1
    assert all("中山區" in name for _, name in err.value.options)


def test_unknown_name_has_no_options():
    with pytest.raises(codes.AmbiguousName) as err:
        codes.resolve("area", ["不存在的地方"])
    assert err.value.options == []


def test_search_ranks_exact_before_longer_names():
    assert codes.search("area", "台北市")[0] == ("6001001000", "台北市")


def test_defaults():
    p = query.build()
    assert p == {"order": "15", "page": "1", "pagesize": "20"}


def test_keyword_and_filters():
    p = query.build(keyword="python", area=["台北市"], remote=True, new_only=True)
    assert p["keyword"] == "python" and p["area"] == "6001001000"
    assert p["remoteWork"] == "1,2" and p["isnew"] == "7"


def test_salary_needs_unit_code():
    p = query.build(salary_min=2_000_000, salary_unit="年薪")
    assert (p["scmin"], p["sctp"], p["scstrict"]) == ("2000000", "Y", "1")
    assert p["order"] == "15"  # asking for a salary floor does not change the sort


def test_negotiable_postings_are_opt_in_and_need_a_salary_floor():
    assert "scneg" not in query.build(salary_min=60000)
    assert query.build(salary_min=60000, include_negotiable=True)["scneg"] == "1"
    assert "scneg" not in query.build(include_negotiable=True)  # nothing to include without a floor


def test_job_type_is_sent_as_ro():
    p = query.build(job_type="兼職")
    assert p["ro"] == "2" and "wt" not in p


@pytest.mark.parametrize("years", range(0, 14))
def test_my_years_only_includes_buckets_the_candidate_qualifies_for(years):
    sent = [int(c) for c in query.build(my_years=years)["jobexp"].split(",")]
    floors = query.EXPERIENCE
    assert sent and all(floors[c] <= years for c in sent)
    assert [c for c in floors if floors[c] <= years] == sent


def test_education_names():
    assert query.build(education="大學")["edu"] == "4"


@pytest.mark.parametrize("bad", [
    {"sort": "zzz"}, {"job_type": "接案"}, {"education": "幼稚園"}, {"page": 0},
    {"per_page": 0}, {"per_page": 31}, {"my_years": -1},
    {"salary_min": 1, "salary_unit": "週薪"},
])
def test_bad_arguments_are_rejected(bad):
    with pytest.raises(query.ArgError):
        query.build(**bad)
