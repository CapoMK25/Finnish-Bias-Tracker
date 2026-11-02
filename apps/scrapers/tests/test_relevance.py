"""Tests for the scope filter. Run: cd apps/scrapers && pytest tests/test_relevance.py -q"""

import pytest

from src.relevance import check_scope

HS_BERLIN_TITLE = (
    "HS Berliinissä | Saksan politiikkaan tuli ”Voldemort” nimeltä Ibrahim Ibrahim, "
    "jota Berliinin vasemmisto\u00adjohtaja pelkää"
)
HS_BERLIN_LEAD = (
    "Saksan politiikassa on tapahtunut tänä syksynä paljon outoja asioita, ja lisää "
    "outoutta tarjoaa mies nimeltä Ibrahim Ibrahim.\nHän hallitsee juuri nyt maan "
    "poliittista ilmatilaa, vaikka häntä ei edes näy eikä hänestä kuulu.\nIbrahim, 70, "
    "on saksanpalestiinalainen Palestiina-aktivisti, jolla on läheisiä kytkentöjä "
    "jyrkän vasemmistolaisen Linke-puolueen radikaaliin siipeen."
)
IS_NHL_TITLE = (
    "Artturi Lehkonen nousi jo NHL:n maalipörssin kakkoseksi – Cale Makar hykerteli "
    "kaukalossa: ”Hän on yksi parhaista kavereistani!”"
)


# (title, url, body, expected in_scope, why)
CASES = [
    # --- the two examples from the issue -----------------------------------
    (IS_NHL_TITLE, "https://www.is.fi/nhl/art-2000012380458.html", "", False, "NHL section"),
    (HS_BERLIN_TITLE, "https://www.hs.fi/ulkomaat/art-2000012345678.html", HS_BERLIN_LEAD, False, "foreign section"),
    (HS_BERLIN_TITLE, "https://yle.fi/a/74-20123456", HS_BERLIN_LEAD, False, "no section: foreign names in title"),
    (IS_NHL_TITLE, "https://yle.fi/a/74-20123456", "", False, "no section: NHL in title"),
    # --- Swedish-language outlet URLs seen in the production logs ----------
    ("Inter ångar på i toppen", "https://www.hbl.fi/sport/inter-angar-pa-i-toppen/", "", False, "hbl sport"),
    ("Trump: Danmark gav oss Grönland", "https://www.hbl.fi/varlden/trump-danmark-gav-oss-gronland/", "", False, "hbl world"),
    ("Guide: HBL:s program på Bokmässan", "https://www.hbl.fi/kultur/guide-hbl-s-program-pa-bokmassan-pa-sondagen/", "", False, "hbl culture"),
    ("Neste tryckte på – Orpo varnade för påföljder i Borgå", "https://www.hbl.fi/politik/neste-tryckte-pa-orpo-varnade-for-pafoljder-i-borga/", "", True, "hbl politics"),
    ("Niinistö: kriget i Ukraina har blivit allt grymmare", "https://www.hbl.fi/finland/niinisto-kriget-i-ukraina-har-blivit-allt-grymmare/", "", True, "domestic section beats foreign term"),
    # --- Finnish politics must stay ----------------------------------------
    ("Orpon hallitus leikkaa opintotukea", "https://www.hs.fi/politiikka/art-2000012000001.html", "", True, "politics section"),
    ("Hallitus leikkaa opintotukea", "https://yle.fi/a/74-20111111", "", True, "no section, no out-of-scope cue"),
    ("Perussuomalaisten ryhmäjohtaja kritisoi budjettiesitystä", "https://www.ku.fi/artikkeli/5446923-x", "", True, "party outlet"),
    ("SAK: Valtiovarainministeriön kartoitus lipsahti kannanotoksi", "https://www.ku.fi/artikkeli/5446923-sak", "", True, "ministry"),
    # --- rescue rules ------------------------------------------------------
    ("Hallitus leikkaa urheilun määrärahoja – seurat huolissaan", "https://www.hs.fi/urheilu/art-2000012000002.html", "", True, "political title in a sports section"),
    ("Suomen ulkoministeri Valtonen tapasi Rubion Washingtonissa", "https://www.is.fi/ulkomaat/art-2000012000003.html", "", True, "foreign section with a Finland link"),
    ("Orpo: Suomi tukee Ukrainaa", "https://yle.fi/a/74-20122222", "", True, "Finland link beats foreign term"),
    ("Kokoomus esittää osinkoveron muutosta", "https://yle.fi/a/74-20133333", "", True, "finance word but political title"),
    ("Ruotsinkielisten palvelut kuntauudistuksessa", "https://yle.fi/a/74-20144444", "", True, "ruotsinkielinen is Finnish politics"),
    # --- more clear drops ---------------------------------------------------
    ("Nokian osake laski pörssissä tulosvaroituksen jälkeen", "https://yle.fi/a/74-20155555", "", False, "market news"),
    ("Ilves voitti Liigan kärkikamppailun", "https://yle.fi/a/74-20166666", "", False, "sports"),
    ("Putin: Venäjä jatkaa hyökkäystä Ukrainassa", "https://yle.fi/a/74-20177777", "", False, "geopolitics, no Finland link"),
    ("Näin teet täydellisen kanakeiton", "https://www.is.fi/ruoka/art-2000012000004.html", "", False, "food section"),
    ("Viihdetähti paljasti kihlauksensa", "https://www.is.fi/viihde/art-2000012000005.html", "", False, "entertainment section"),
    # --- regression: Finnish place names that start like a foreign country -
    ("Puolangan kunnanvaltuusto päätti koulun lakkauttamisesta", "https://yle.fi/a/74-20200001", "", True, "Puolanka is Finland, not Poland"),
    ("Trumpin tullit uhkaavat Suomen vientiä", "https://yle.fi/a/74-20200002", "", True, "foreign name but a Finland link"),
    ("Hallituksen leikkaukset iskevät Liigaan", "https://yle.fi/a/74-20200003", "", True, "political title with a sports word"),
    ("Suomen MM-joukkue voitti Ruotsin jääkiekossa", "https://yle.fi/a/74-20200004", "", False, "Finland in a sports title is still sports"),
    # --- ambiguous: must be KEPT (conservative) ----------------------------
    ("Yle selvitti: näin suomalaiset äänestävät", "https://yle.fi/a/74-20188888", "", True, "ambiguous, kept"),
    ("Suomalaiset kokevat luottamuksen laskeneen", "https://yle.fi/a/74-20199999", "", True, "ambiguous, kept"),
    ("", "", "", True, "empty input is kept, never crashes"),
]


@pytest.mark.parametrize("title,url,body,expected,why", CASES, ids=[c[4] + " | " + c[0][:30] for c in CASES])
def test_scope(title, url, body, expected, why):
    decision = check_scope(title=title, url=url, body=body)
    assert decision.in_scope is expected, f"{why}: got {decision}"


def test_reason_is_reported():
    decision = check_scope(title=IS_NHL_TITLE, url="https://www.is.fi/nhl/art-2000012380458.html")
    assert decision.reason == "non-political-section:nhl"


def test_soft_hyphen_does_not_defeat_matching():
    # "Berlii\u00adnin" with an invisible hyphen inside must still be recognised
    decision = check_scope(title="Berlii\u00adnin hallinto vaihtuu", url="https://yle.fi/a/74-1")
    assert not decision.in_scope


def test_malformed_url_does_not_crash():
    assert check_scope(title="Hallitus kokoontuu", url="http://[bad").in_scope


# --- inflected forms: Finnish consonant gradation must not defeat the word lists ----------
from src.relevance import FINANCE_TERMS, FOREIGN_TERMS, POLITICS_RESCUE, SPORTS_TERMS  # noqa: E402


@pytest.mark.parametrize(
    "rx,word",
    [(SPORTS_TERMS, w) for w in ["jääkiekossa", "jääkiekko", "hiihdossa", "hiihto", "mäkihypyssä", "jalkapallossa", "Liigassa", "NHL:n"]]
    + [(FINANCE_TERMS, w) for w in ["osakkeet", "osakkeen", "osingot", "osinkoa", "yrityskaupan", "kryptovaluutan", "pörssissä"]]
    + [(FOREIGN_TERMS, w) for w in ["Turkki", "Turkin", "Venäjän", "Ukrainan", "Berliinin", "Ruotsin", "Puolassa", "Yhdysvaltojen"]]
    + [(POLITICS_RESCUE, w) for w in ["Häkkäsen", "Häkkänen", "Valtosen", "Kaikkosen", "Saarikon", "vaaleissa", "vaalit", "eduskunnan", "hallituksen", "politiikan", "poliittinen", "Kelan"]],
)
def test_inflected_forms_match(rx, word):
    assert rx.search(word), word


@pytest.mark.parametrize(
    "rx,word",
    [(FOREIGN_TERMS, w) for w in ["ruotsinkielinen", "Puolanka", "Puolangan", "Turku", "turkulainen"]]
    + [(FINANCE_TERMS, w) for w in ["osakas", "osallistuu"]]
    + [(POLITICS_RESCUE, w) for w in ["poliisi", "kelata", "hallitsee"]],
)
def test_lookalikes_do_not_match(rx, word):
    assert not rx.search(word), word


def test_html_summary_is_stripped_before_matching():
    # An RSS <summary> arrives with markup; the Finland link inside it must still count.
    url = "https://www.is.fi/ulkomaat/art-2000012000009.html"
    title = "Trumpin tullit ravistavat maailmankauppaa"
    assert not check_scope(title=title, url=url, body="<p>Maailmankauppa horjuu.</p>").in_scope
    html_lead = "<p>Tullit osuvat <b>Suomen</b> vientiin.</p>"
    assert check_scope(title=title, url=url, body=html_lead).in_scope
