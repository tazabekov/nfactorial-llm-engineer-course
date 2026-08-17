from config import FIXTURES_DIR
from mcp_servers.twogis import parser


def _html() -> str:
    return (FIXTURES_DIR / "twogis_search.html").read_text(encoding="utf-8")


def test_parses_at_least_three_restaurants():
    results = parser.parse_restaurants(_html())
    assert len(results) >= 3


def test_every_result_has_non_empty_name():
    for restaurant in parser.parse_restaurants(_html()):
        assert restaurant.name.strip()


def test_respects_limit():
    assert len(parser.parse_restaurants(_html(), limit=2)) == 2


def test_empty_html_gives_empty_list():
    assert parser.parse_restaurants("<html><body></body></html>") == []


def test_build_search_url_encodes_query():
    url = parser.build_search_url("суши бар", "almaty")
    assert url.startswith("https://2gis.kz/almaty/search/")
    assert " " not in url
