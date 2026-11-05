"""Tests for the scope filter. Run: cd apps/scrapers && pytest tests/test_relevance.py -q"""

# ruff: noqa: E501, RUF001  (real headlines: long lines and en dashes)

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
    (
        HS_BERLIN_TITLE,
        "https://www.hs.fi/ulkomaat/art-2000012345678.html",
        HS_BERLIN_LEAD,
        False,
        "foreign section",
    ),
    (
        HS_BERLIN_TITLE,
        "https://yle.fi/a/74-20123456",
        HS_BERLIN_LEAD,
        False,
        "no section: foreign names in title",
    ),
    (IS_NHL_TITLE, "https://yle.fi/a/74-20123456", "", False, "no section: NHL in title"),
    # --- Swedish-language outlet URLs seen in the production logs ----------
    (
        "Inter ångar på i toppen",
        "https://www.hbl.fi/sport/inter-angar-pa-i-toppen/",
        "",
        False,
        "hbl sport",
    ),
    (
        "Trump: Danmark gav oss Grönland",
        "https://www.hbl.fi/varlden/trump-danmark-gav-oss-gronland/",
        "",
        False,
        "hbl world",
    ),
    (
        "Guide: HBL:s program på Bokmässan",
        "https://www.hbl.fi/kultur/guide-hbl-s-program-pa-bokmassan-pa-sondagen/",
        "",
        False,
        "hbl culture",
    ),
    (
        "Neste tryckte på – Orpo varnade för påföljder i Borgå",
        "https://www.hbl.fi/politik/neste-tryckte-pa-orpo-varnade-for-pafoljder-i-borga/",
        "",
        True,
        "hbl politics",
    ),
    (
        "Niinistö: kriget i Ukraina har blivit allt grymmare",
        "https://www.hbl.fi/finland/niinisto-kriget-i-ukraina-har-blivit-allt-grymmare/",
        "",
        True,
        "domestic section beats foreign term",
    ),
    # --- Finnish politics must stay ----------------------------------------
    (
        "Orpon hallitus leikkaa opintotukea",
        "https://www.hs.fi/politiikka/art-2000012000001.html",
        "",
        True,
        "politics section",
    ),
    (
        "Hallitus leikkaa opintotukea",
        "https://yle.fi/a/74-20111111",
        "",
        True,
        "no section, no out-of-scope cue",
    ),
    (
        "Perussuomalaisten ryhmäjohtaja kritisoi budjettiesitystä",
        "https://www.ku.fi/artikkeli/5446923-x",
        "",
        True,
        "party outlet",
    ),
    (
        "SAK: Valtiovarainministeriön kartoitus lipsahti kannanotoksi",
        "https://www.ku.fi/artikkeli/5446923-sak",
        "",
        True,
        "ministry",
    ),
    # --- rescue rules ------------------------------------------------------
    (
        "Hallitus leikkaa urheilun määrärahoja – seurat huolissaan",
        "https://www.hs.fi/urheilu/art-2000012000002.html",
        "",
        True,
        "political title in a sports section",
    ),
    (
        "Suomen ulkoministeri Valtonen tapasi Rubion Washingtonissa",
        "https://www.is.fi/ulkomaat/art-2000012000003.html",
        "",
        True,
        "foreign section with a Finland link",
    ),
    (
        "Orpo: Suomi tukee Ukrainaa",
        "https://yle.fi/a/74-20122222",
        "",
        True,
        "Finland link beats foreign term",
    ),
    (
        "Kokoomus esittää osinkoveron muutosta",
        "https://yle.fi/a/74-20133333",
        "",
        True,
        "finance word but political title",
    ),
    (
        "Ruotsinkielisten palvelut kuntauudistuksessa",
        "https://yle.fi/a/74-20144444",
        "",
        True,
        "ruotsinkielinen is Finnish politics",
    ),
    # --- more clear drops ---------------------------------------------------
    (
        "Nokian osake laski pörssissä tulosvaroituksen jälkeen",
        "https://yle.fi/a/74-20155555",
        "",
        False,
        "market news",
    ),
    ("Ilves voitti Liigan kärkikamppailun", "https://yle.fi/a/74-20166666", "", False, "sports"),
    (
        "Putin: Venäjä jatkaa hyökkäystä Ukrainassa",
        "https://yle.fi/a/74-20177777",
        "",
        False,
        "geopolitics, no Finland link",
    ),
    (
        "Näin teet täydellisen kanakeiton",
        "https://www.is.fi/ruoka/art-2000012000004.html",
        "",
        False,
        "food section",
    ),
    (
        "Viihdetähti paljasti kihlauksensa",
        "https://www.is.fi/viihde/art-2000012000005.html",
        "",
        False,
        "entertainment section",
    ),
    # --- regression: Finnish place names that start like a foreign country -
    (
        "Puolangan kunnanvaltuusto päätti koulun lakkauttamisesta",
        "https://yle.fi/a/74-20200001",
        "",
        True,
        "Puolanka is Finland, not Poland",
    ),
    (
        "Trumpin tullit uhkaavat Suomen vientiä",
        "https://yle.fi/a/74-20200002",
        "",
        True,
        "foreign name but a Finland link",
    ),
    (
        "Hallituksen leikkaukset iskevät Liigaan",
        "https://yle.fi/a/74-20200003",
        "",
        True,
        "political title with a sports word",
    ),
    (
        "Suomen MM-joukkue voitti Ruotsin jääkiekossa",
        "https://yle.fi/a/74-20200004",
        "",
        False,
        "Finland in a sports title is still sports",
    ),
    # --- ambiguous: must be KEPT (conservative) ----------------------------
    (
        "Yle selvitti: näin suomalaiset äänestävät",
        "https://yle.fi/a/74-20188888",
        "",
        True,
        "ambiguous, kept",
    ),
    (
        "Suomalaiset kokevat luottamuksen laskeneen",
        "https://yle.fi/a/74-20199999",
        "",
        True,
        "ambiguous, kept",
    ),
    ("", "", "", True, "empty input is kept, never crashes"),
]


@pytest.mark.parametrize(
    "title,url,body,expected,why", CASES, ids=[c[4] + " | " + c[0][:30] for c in CASES]
)
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
    [
        (SPORTS_TERMS, w)
        for w in [
            "jääkiekossa",
            "jääkiekko",
            "hiihdossa",
            "hiihto",
            "mäkihypyssä",
            "jalkapallossa",
            "Liigassa",
            "NHL:n",
        ]
    ]
    + [
        (FINANCE_TERMS, w)
        for w in [
            "osakkeet",
            "osakkeen",
            "osingot",
            "osinkoa",
            "yrityskaupan",
            "kryptovaluutan",
            "pörssissä",
        ]
    ]
    + [
        (FOREIGN_TERMS, w)
        for w in [
            "Turkki",
            "Turkin",
            "Venäjän",
            "Ukrainan",
            "Berliinin",
            "Ruotsin",
            "Puolassa",
            "Yhdysvaltojen",
        ]
    ]
    + [
        (POLITICS_RESCUE, w)
        for w in [
            "Häkkäsen",
            "Häkkänen",
            "Valtosen",
            "Kaikkosen",
            "Saarikon",
            "vaaleissa",
            "vaalit",
            "eduskunnan",
            "hallituksen",
            "politiikan",
            "poliittinen",
            "Kelan",
        ]
    ],
)
def test_inflected_forms_match(rx, word):
    assert rx.search(word), word


@pytest.mark.parametrize(
    "rx,word",
    [
        (FOREIGN_TERMS, w)
        for w in ["ruotsinkielinen", "Puolanka", "Puolangan", "Turku", "turkulainen"]
    ]
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


# --- batch from the first local scrape: these slipped through and must now be caught ----------
LEAKED = [
    (
        "Musiikki | Kurdilaulaja Aynur joutui poistumaan lavalta kesken konsertin, koska lauloi omalla kielellään",
        "https://www.hs.fi/popkulttuuri/art-2000012347188.html",
        "popkulttuuri section + label",
    ),
    (
        "Musiikki | Kurdilaulaja Aynur joutui poistumaan lavalta kesken konsertin",
        "https://www.hs.fi/art-2000012347188.html",
        "label alone",
    ),
    (
        "Portugalin poliisi purki kovin ottein mielenosoittajien telttaleirit",
        "https://yle.fi/a/74-20200100",
        "foreign country",
    ),
    (
        "Sota ei ole Myanmarin ainoa kriisi – Tulvat, nälkä ja taudit koskettavat miljoonia",
        "https://www.ku.fi/artikkeli/5446999-x",
        "foreign country",
    ),
]


@pytest.mark.parametrize("title,url,why", LEAKED, ids=[c[2] + " | " + c[0][:25] for c in LEAKED])
def test_leaked_articles_are_now_dropped(title, url, why):
    assert not check_scope(title=title, url=url).in_scope, why


KEPT_FROM_THE_SAME_BATCH = [
    "Politiikan puskaradio: Kysymys kansanedustajien määrästä sai aikaan outoja",
    "Puolustusvoimain komentaja Juhani Kaskeala vei Suomea länteen",
    "Ekonomisti optimistisena: Ongelmat julkisessa taloudessa voidaan ratkoa vajaassa vuodessa",
    "Puolustusala | Supo: Emme ole tulppa puolustusalan työvoimajumissa",
    "Maajussille morsiamessa tuli pettymys, mutta se opetti – Hannu Laturi tähtää nyt eduskuntaan",
    "Markus Leikola: Onko Mamdanin tie Suomen tie – vai syökö eipäs-juupas-väittely tulevaisuutemme?",
    "Psykologi selittää woken sekä maahanmuuttosokeuden – narsismi mädätti kulttuurin ja some nuorten aivot",
    "Oikeusministeri Leena Meri haluaa kiristää rangaistuksia",
    "Perustuslakivaliokunta kuuli asiantuntijoita hallituksen esityksestä",
    "Perussuomalaisten kansanedustaja vaatii Hollolan kunnalta selvitystä",
]


@pytest.mark.parametrize(
    "title", KEPT_FROM_THE_SAME_BATCH, ids=[t[:35] for t in KEPT_FROM_THE_SAME_BATCH]
)
def test_political_titles_from_the_same_batch_stay(title):
    assert check_scope(title=title, url="https://yle.fi/a/74-1").in_scope


@pytest.mark.parametrize(
    "word",
    [
        "Portugalin",
        "Myanmarin",
        "Kreikan",
        "Hollannin",
        "Meksikon",
        "Itävallan",
        "Tšekin",
        "Lähi-idän",
        "Istanbulin",
    ],
)
def test_more_countries_match(word):
    assert FOREIGN_TERMS.search(word), word


@pytest.mark.parametrize(
    "word", ["perustuslaki", "Perussuomalaiset", "Hollola", "oman", "mallin", "kreatiivinen"]
)
def test_country_list_has_no_common_word_collisions(word):
    assert not FOREIGN_TERMS.search(word), word


# --- found in the first three hours of production output --------------------------------------
@pytest.mark.parametrize(
    "title,expected,why",
    [
        (
            "Sverige: Centerledaren nedröstad i riksdagen",
            False,
            "'riksdagen' must not rescue a story about Sweden",
        ),
        ("Platt fall – Kristerssons tur att försöka", False, "Swedish prime minister"),
        ("Norskt varuhus utsatt för hackarattack ett dygn efter andra länder", False, "Norwegian"),
        ("Kommentti: Ruotsi petti meidät", True, "'us' in a Finnish headline: keep when unsure"),
        (
            "Riksdagen godkände budgeten för nästa år",
            True,
            "no foreign term: a Finnish parliament story stays",
        ),
        (
            "Ruotsin valtiopäivät torppasi keskustajohtajan pääministeriyden",
            False,
            "foreign politics",
        ),
    ],
)
def test_production_findings(title, expected, why):
    assert check_scope(title=title, url="https://yle.fi/a/74-1").in_scope is expected, why


# --- audit of the first three hours of foreign drops in production -----------------------------
@pytest.mark.parametrize(
    "title,url,why",
    [
        (
            "Turulta Venäjä-ukaasi – näin kommentoi pormestari Piia Elo",
            "https://demokraatti.fi/turulta-venaja-ukaasi-nain-kommentoi-pormestari-piia-elo/",
            "Finnish local politics",
        ),
        (
            "Muut lehdet | Venäjän kanssa pelaaminen olisi nykyoloissa epäisänmaallista",
            "https://www.hs.fi/nakemys/art-2000012384920.html",
            "HS opinion section",
        ),
        (
            "Oulun kaupunginvaltuusto kiistelee Venäjä-yhteistyöstä",
            "https://yle.fi/a/74-1",
            "city council",
        ),
        (
            "Urheilu | Kaupunginvaltuusto päätti jäähallin rahoituksesta",
            "https://www.hs.fi/urheilu/art-1.html",
            "local government in a sports section",
        ),
    ],
)
def test_audit_false_drops_are_fixed(title, url, why):
    assert check_scope(title=title, url=url).in_scope, why


CORRECT_FOREIGN_DROPS = [
    (
        "Trump: Yhdysvallat lopettaa Israelin sotilaallisen tuen",
        "https://yle.fi/a/74-20254884?origin=rss",
    ),
    (
        "Puola lähetti erikoisjoukkoja Venäjän rajalle – yöllä havaittiin epäilyttävää liikennettä",
        "https://yle.fi/a/74-20254863?origin=rss",
    ),
    (
        "Tšekissä kuohuu: televisio vaikenee ja tuhannet puolustavat vapaata mediaa",
        "https://yle.fi/a/74-20254567?origin=rss",
    ),
    (
        "Analyysi: Puhemies kaitsee itsepäistä poliitikkolaumaa, jotta Ruotsi saisi hallituksen",
        "https://yle.fi/a/74-20254583?origin=rss",
    ),
    (
        "Iranin sota | WSJ: Yhdysvallat iski Hormuzinsalmella olevalle saarelle",
        "https://www.hs.fi/maailma/art-2000012384124.html",
    ),
    (
        "USA:n välivaalit | Selvitimme, mitä Trump on tehnyt amerikkalaisten lompakoille",
        "https://www.hs.fi/visio/art-2000012381692.html",
    ),
    (
        "Raju taisto senaatista: Kaataako kohu Peltolan?",
        "https://www.iltalehti.fi/ulkomaat/a/829e6860",
    ),
    ("Trump piti historiallisen oudon puheen", "https://www.is.fi/ulkomaat/art-2000012382449.html"),
    (
        "Witkoff: Ukrainan, Venäjän ja Yhdysvaltain edustajat tapaavat ensi viikolla",
        "https://demokraatti.fi/witkoff-ukrainan-venajan-ja-yhdysvaltain-edustajat/",
    ),
    (
        "Sota ei ole Myanmarin ainoa kriisi – Tulvat, nälkä ja taudit koskettavat miljoonia",
        "https://www.ku.fi/artikkeli/5446875-sota-ei-ole-myanmarin",
    ),
    (
        "EU isännöi Ukraina-tapaamista ennen Abu Dhabin kokousta",
        "https://www.suomenmaa.fi/uutiset/eu-isannoi-ukraina-tapaamista",
    ),
    (
        "HIV-epidemia riehuu Venäjällä, Kreml voimaton",
        "https://www.verkkouutiset.fi/a/hiv-epidemia-riehuu-venajalla-kreml-voimaton/",
    ),
]


@pytest.mark.parametrize(
    "title,url", CORRECT_FOREIGN_DROPS, ids=[c[0][:30] for c in CORRECT_FOREIGN_DROPS]
)
def test_audited_foreign_drops_stay_dropped(title, url):
    assert not check_scope(title=title, url=url).in_scope


@pytest.mark.parametrize(
    "title",
    [
        "Kulttuuri | Opetus- ja kulttuuriministeriö leikkaa teattereiden tukea",
        "Urheilu | Kunnanvaltuusto äänesti uimahallin sulkemisesta",
        "Musiikki | Valtiovarainministeriö nosti konserttilippujen arvonlisäveroa",
    ],
)
def test_compound_political_words_rescue_non_political_labels(title):
    assert check_scope(title=title, url="https://www.hs.fi/kulttuuri/art-1.html").in_scope


# --- first refinement pass for issue #229: headlines from a three-hour production listing ---------
# (source, url, title); labelled by hand from the headline alone.
POLITICAL_MAINSTREAM = [
    ("ilta-sanomat", "", "Pääministeri Orpo pommiuhista: ”Tämä on nyt tätä aikaa”"),
    ("hufvudstadsbladet", "", "Stubb: ”Sluta gnälla”"),
    ("ilta-sanomat", "", "Orpo: ”Perussuomalaiset varmaan tekevät hieman parempaa työtä”"),
    ("iltalehti", "", "Poikkeuksellinen tempaus Eduskuntatalolle"),
    ("iltalehti", "", "Hallitus varautuu poikkeusoloihin – Esittää uutta valmiuslakia"),
    ("svenska-yle", "", "Förslag till ny beredskapslag"),
    ("svenska-yle", "", "Orpo om bombhoten mot flygtrafiken: Så här är det nuförtiden"),
    ("iltalehti", "", "Kokoomus syöksykierteessä – Näin selittää Petteri Orpo"),
    (
        "helsingin-sanomat",
        "",
        "Kannatusluisu | Kokoomuksen kannatus murenee, Orpo: ”Perussuomalaiset varmaan tekee hieman parempaa työtä”",
    ),
    ("hufvudstadsbladet", "", "Orpo om bombhoten: Tiden vi lever i"),
    (
        "helsingin-sanomat",
        "",
        "Armeija | Pakolliset kertausharjoitukset sotkevat monen opintoja, sanoo Mats Uotila",
    ),
    ("hufvudstadsbladet", "", "Nedskärningar hotar det finlandssvenska kulturlivet"),
    ("iltalehti", "", "Finnairin pommiuhkaukset: Nyt puhuu Petteri Orpo"),
    ("ilta-sanomat", "", "Hallitus: Ikäraja energiajuomille"),
    (
        "yle",
        "",
        "Hallitus päätti kiistellystä ennallistamisesta: ei pakkoa suojelualueiden ulkopuolelle, luonnonmetsien määrä putosi puoleen",
    ),
    (
        "yle",
        "",
        "Analyysi: Miksi taloustieteilijät tunkevat nenäänsä koulumaailmaan? – tästä on kyse kiistassa kansallisista kokeista",
    ),
    ("yle", "", "Ykkösaamun vieraana presidentti Sauli Niinistö – mitä haluat kysyä?"),
    (
        "iltalehti",
        "",
        "Veret seisauttavan huono luku jysähti – Nyt puhuu kokoomuksen puoluesihteeri",
    ),
    ("helsingin-sanomat", "", "Työttömyys | Työtön tarvitsee työtä eikä leimoja"),
    ("ilta-sanomat", "", "Timo Soini: Minja Koskelasta voi tulla valtiovarainministeri"),
    ("iltalehti", "", "Yksi kuva paljastaa – Näin jyrkkä on kokoomuksen alamäki"),
    (
        "helsingin-sanomat",
        "",
        "Seksuaalirikokset | Poliisi ei ehdi tutkia kaikkia raiskauksia – Poliisiylijohtaja ei hyväksy selitystä",
    ),
    ("ilta-sanomat", "", "Viharikoksissa ennätysvuosi – yksi kaupunki nousi Helsingin ohi"),
    (
        "helsingin-sanomat",
        "",
        "Asuntokauppa | Ensiasunnon ostoon tulossa iso helpotus: Laskuri näyttää, kuinka paljon hyödyt",
    ),
    ("helsingin-sanomat", "", "Eutanasia | Lääkäriavusteinen eutanasia voisi olla vaihtoehto"),
    (
        "helsingin-sanomat",
        "",
        "Nordic Compass | Pohjoismaalaiset suuryritykset etsivät yhteistä lobbausvoimaa, mukana myös Stubb",
    ),
]

JUNK_MAINSTREAM = [
    (
        "ilta-sanomat",
        "https://www.is.fi/esports/art-2000012390622.html",
        "Huippujoukkue palkkasi pornotähden",
    ),
    (
        "iltalehti",
        "https://www.iltalehti.fi/kotimaa/a/63e8541d-7ace-4042-99bd-8716227c8b3f?utm_source=rss",
        "Ulosajo Ilomantsissa – Kuljettaja kuoli",
    ),
    ("ilta-sanomat", "", "Mies kuoli ulosajossa"),
    ("ilta-sanomat", "", "HJK:ssa kova myllerrys: Kahdeksan pelaajaa ulos"),
    ("yle", "", "Cristiano Ronaldo päättää maajoukkueuransa – tunteikas vuodatus Instagramissa"),
    ("ilta-sanomat", "", "Lindsey Vonn, 42, kertoo poikaystävästään, 30: ”En aio”"),
    (
        "ilta-sanomat",
        "",
        "Maria Kuusiluoma, 57, joutui leikkaukseen – ei palaa teatterin lavalle ennen huhtikuuta",
    ),
    ("svenska-yle", "", "Kändiseken Paavolan tammi i Lojo såld"),
    ("svenska-yle", "", "Alisha Potrykus är Finlands Lucia: ”Handlar om allt annat än utseende”"),
    ("hufvudstadsbladet", "", "Alisha Potrykus är Finlands lucia 2026"),
    ("svenska-yle", "", "Populära ljusevenemanget i Åbo startar i år från musikhuset Fuga"),
    ("yle", "", "Nicola Ussherin raejuustopizzan reseptiä on katsottu lähes miljoonaa kertaa"),
    ("ilta-sanomat", "", "Suurin osa suomalaisista tekee hajuveden kanssa haitallisen virheen"),
    ("ilta-sanomat", "", "9,6/10 – ”uusi” Zelda räjäytti pankin"),
    (
        "helsingin-sanomat",
        "",
        "HS testaa | Mazdan uusi sähköauto keksii sivupeilit uusiksi, ja parkkipaikalla uhkaa pelti rytistä",
    ),
    ("iltalehti", "", "Tämä tiedetään lumentulosta nyt"),
    ("ilta-sanomat", "", "Odotettu käänne säässä"),
    (
        "ilta-sanomat",
        "",
        "Halloween-asu johti hurjaan tilanteeseen – sähköpotkulautailija oli lähellä vakavaa vaaraa",
    ),
    ("iltalehti", "", "Poliisilta painava muistutus: Tämä asia halloween-asussa voi olla rikos"),
    (
        "yle",
        "",
        "Poliisi: Oulussa ei tapahtunutkaan alaikäisen pahoinpitelyä terävällä esineellä – nuori sepitti koko jutun",
    ),
    ("iltalehti", "", "Poliisi epäili järkyttävää rikosta – Nyt paljastui totuus"),
    ("iltalehti", "", "Kaahari ei pysähtynyt edes piikkimattoon – Sitten poliisi avasi tulen"),
    ("iltalehti", "", "Työntekijä putosi korkeuksista kuolemaansa Paraisilla"),
    ("ilta-sanomat", "", "Postinjakaja kuoli onnettomuudessa – poliisi pyytää vihjeitä"),
    (
        "iltalehti",
        "",
        "Vakava törmäys postiajoneuvon ja auton välillä – Viisikymppinen Postin kuljettaja kuoli",
    ),
    ("svenska-yle", "", "Postutdelare dog i en trafikolycka i Åbo"),
    ("iltalehti", "", "Epäilty sarjarikollinen laskettiin vapaaksi – Jäi heti kiinni uudelleen"),
    ("svenska-yle", "", "Sverige förlänger gränskontrollerna"),
    ("iltalehti", "", "Asiantuntija: Tätä Vladimir Putin joutuu nyt miettimään"),
    (
        "yle",
        "",
        "Jenkkivaalien tähti kävi toimittajaan käsiksi – asiantuntija: Voi näyttää aggressiiviselta ja uhkaavalta",
    ),
    (
        "ilta-sanomat",
        "",
        "TV1 näyttää alkuillasta karmivan henkirikoksen Suomen historiasta – ei herkimmille",
    ),
    (
        "helsingin-sanomat",
        "",
        "Sijoittaminen | Mandatumin asiakkaiden tileille tunkeuduttiin: Osa saattanut menettää rahaa",
    ),
    ("ilta-sanomat", "", "Tietomurto: Asiakkaiden tileillä luvatonta toimintaa"),
]


@pytest.mark.parametrize(
    "source,url,title", POLITICAL_MAINSTREAM, ids=[r[2][:32] for r in POLITICAL_MAINSTREAM]
)
def test_political_headlines_in_mainstream_outlets_are_kept(source, url, title):
    assert check_scope(title=title, url=url, source=source).in_scope


@pytest.mark.parametrize(
    "source,url,title", JUNK_MAINSTREAM, ids=[r[2][:32] for r in JUNK_MAINSTREAM]
)
def test_junk_headlines_in_mainstream_outlets_are_dropped(source, url, title):
    assert not check_scope(title=title, url=url, source=source).in_scope


# --- party and ideological organs are never filtered ---------------------------------------------
@pytest.mark.parametrize(
    "source", ["suomenmaa", "verkkouutiset", "kansan-uutiset", "demokraatti", "suomen-uutiset"]
)
@pytest.mark.parametrize(
    "title,url",
    [
        ("Artturi Lehkonen nousi NHL:n kakkoseksi", "https://example.fi/nhl/art-1.html"),
        (
            "Trump: Yhdysvallat lopettaa Israelin sotilaallisen tuen",
            "https://example.fi/ulkomaat/a/1",
        ),
        ("Postia jakanut mies kuoli liikenneonnettomuudessa Turussa", "https://example.fi/a/2"),
        (
            "Kinkku pitää pintansa: näitä ruokia suomalaiset haluavat joulupöytään",
            "https://example.fi/a/3",
        ),
    ],
)
def test_party_organs_are_never_filtered(source, title, url):
    decision = check_scope(title=title, url=url, source=source)
    assert decision.in_scope and decision.reason.startswith("party-organ")


def test_the_same_headlines_are_filtered_in_a_mainstream_outlet():
    assert not check_scope(
        title="Mies kuoli ulosajossa",
        url="https://www.is.fi/kotimaa/art-1.html",
        source="ilta-sanomat",
    ).in_scope


# --- the false-drop guards: political stories that use the same words as the new rules -----------
@pytest.mark.parametrize(
    "title",
    [
        "Entinen presidentti Ahtisaari kuoli",
        "Entinen ulkoministeri kuoli 80-vuotiaana",
        "Hallitus esittää: poliisin resurssit riittämättömiä, pahoinpitelyt lisääntyneet",
        "Kansanedustaja pahoinpideltiin Helsingissä",
        "Eduskunta keskusteli sääntelystä ja säätiöiden verotuksesta",
        "Hallitus: Valmentajien koulutus saa lisärahoitusta",
        "Petteri Orpo, 56, kertoo vaalitavoitteistaan",
        "Jussi Halla-aho, 49, kommentoi hallituksen linjausta",
        "Viharikoksissa ennätysvuosi – yksi kaupunki nousi Helsingin ohi",
    ],
)
def test_new_rules_do_not_drop_political_stories(title):
    assert check_scope(
        title=title, url="https://www.is.fi/kotimaa/art-1.html", source="ilta-sanomat"
    ).in_scope


@pytest.mark.parametrize(
    "word",
    [
        "ulosajossa",
        "henkirikoksen",
        "hajuveden",
        "kuolemaansa",
        "pahoinpideltiin",
        "säässä",
        "lumentulosta",
        "reseptiä",
    ],
)
def test_new_stems_survive_finnish_inflection(word):
    from src.relevance import ACCIDENT_CRIME_TERMS, LIFESTYLE_TERMS, WEATHER_TERMS

    assert any(rx.search(word) for rx in (ACCIDENT_CRIME_TERMS, LIFESTYLE_TERMS, WEATHER_TERMS)), (
        word
    )


@pytest.mark.parametrize("word", ["sääntö", "säätiö", "säännöt", "kuolinsyy"])
def test_weather_and_crime_lookalikes_do_not_match(word):
    from src.relevance import ACCIDENT_CRIME_TERMS, WEATHER_TERMS

    assert not any(rx.search(word) for rx in (ACCIDENT_CRIME_TERMS, WEATHER_TERMS)), word
