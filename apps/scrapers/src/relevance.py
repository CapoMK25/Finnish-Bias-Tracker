"""Scope filter: is this article about Finnish politics?

The project covers political framing in the Finnish press. Everything else
(sports, entertainment, lifestyle, market news, and foreign or geopolitical
stories with no Finnish angle) is dropped before it costs anything: no
scoring call, no embedding, no database row.

Deliberately conservative and deterministic (no LLM call). An article is only
dropped on positive evidence that it is out of scope, and a Finnish-politics
marker in the title always rescues it. When in doubt it is kept.

Decision order:
  1. Domestic or politics section in the URL      -> keep
  2. Clearly non-political label or section      -> drop, unless the title is political
       (HS headline labels such as 'Musiikki |', and sport, viihde, popkulttuuri, ...)
  3. Foreign section (ulkomaat, varlden, ...)     -> drop, unless it has a Finland link
  4. No decisive section: title cues
       sports or market terms, no political term  -> drop
       foreign names, no Finland link             -> drop
  5. Otherwise                                    -> keep

Tune the section sets and word lists below from real data: run
scripts/preview_scope_filter.py to see which URL sections each outlet uses.
"""

from __future__ import annotations

import re
from typing import NamedTuple
from urllib.parse import urlparse

# How much of the article body counts as the "lead" when looking for a Finland link.
LEAD_CHARS = 600


class ScopeDecision(NamedTuple):
    in_scope: bool
    reason: str


# --- URL sections (first path segment, lower case) ---------------------------

# Editorially domestic / political: never dropped on content cues.
# Editorially political: never dropped on content cues.
POLITICAL_SECTIONS = {
    "politiikka",
    "politik",
    "mielipide",
    "opinion",
    "paakirjoitus",
    "paakirjoitukset",
    "vaalit",
    "kolumnit",
    "nakemys",
}

# General domestic news (IS and IL file accidents and crime under /kotimaa/): foreign-name
# rules do not apply, but sports, crime-blotter, weather and lifestyle rules do.
GENERAL_DOMESTIC_SECTIONS = {"kotimaa", "finland"}

DOMESTIC_SECTIONS = POLITICAL_SECTIONS | GENERAL_DOMESTIC_SECTIONS

# Clearly not politics. Dropped unless the title itself is political.
NONPOLITICAL_SECTIONS = {
    "urheilu",
    "nhl",
    "sport",
    "jaakiekko",
    "jalkapallo",
    "moottoriurheilu",
    "formula1",
    "f1",
    "kuntoilu",
    "viihde",
    "ruoka",
    "matkailu",
    "autot",
    "horoskoopit",
    "tv",
    "lifestyle",
    "kulttuuri",
    "kultur",
    "popkulttuuri",
    "musiikki",
    "elokuvat",
    "elokuva",
    "kirjat",
    "sarjat",
    "muoti",
    "tyyli",
    "pelit",
    "esports",
    "e-urheilu",
    "lemmikit",
    "kauneus",
    "sisustus",
}

# HS and some others prefix the headline with a label: "Musiikki | Kurdilaulaja Aynur ...".
# A clearly non-political label acts like a non-political section.
NONPOLITICAL_LABELS = {
    "musiikki",
    "elokuva",
    "elokuvat",
    "kirjat",
    "kirjallisuus",
    "taide",
    "teatteri",
    "tanssi",
    "sarjat",
    "televisio",
    "tv",
    "pelit",
    "ruoka",
    "matkailu",
    "muoti",
    "urheilu",
    "jääkiekko",
    "jalkapallo",
    "viihde",
    "popkulttuuri",
    "kulttuuri",
    "autot",
    "sisustus",
    "lemmikit",
    "kauneus",
    "horoskooppi",
    "hs testaa",
    "sijoittaminen",
}

# Foreign news. Dropped unless the story has a Finland link.
FOREIGN_SECTIONS = {
    "ulkomaat",
    "maailma",
    "varlden",
    "norden",
    "utrikes",
    "international",
}


# Party and ideological organs: politics is their whole subject, so nothing from them is
# filtered. An odd item about AI or a recipe is an acceptable price for never losing a
# political piece. Edit this set to change the policy.
UNFILTERED_SOURCES = {
    "suomenmaa",
    "verkkouutiset",
    "kansan-uutiset",
    "demokraatti",
    "suomen-uutiset",
}


def _rx(*alternatives: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")", re.IGNORECASE)


# --- Word lists (Finnish and Swedish stems; \w* covers inflections) ----------
# Finnish consonant gradation changes the stem (jääkiekko -> jääkiekossa, vaali -> vaaleissa,
# Häkkänen -> Häkkäsen), so stems stop before the changing consonant and tests/test_relevance.py
# checks inflected forms. Add a test for every new word you add.

# A Finland link: used to rescue foreign-looking stories. No "riksdag": in Swedish it names
# both Finland's and Sweden's parliament. "meidät/meille/meidän" (we/us/our) counts: a Finnish
# headline that says "us" is talking about Finland.
FINLAND_MARKER = _rx(
    r"suom\w*",
    r"finland\w*",
    r"finsk\w*",
    r"helsinki\w*",
    r"helsingfors",
    r"eduskun\w*",
    r"kansanedustaj\w*",
    r"kokoomu\w*",
    r"perussuomalai\w*",
    r"sdp\b",
    r"vasemmistoliit\w*",
    r"kristillisdemokraat\w*",
    r"rkp\b",
    r"liike nyt",
    r"keskustapuolue\w*",
    r"orpo\w*",
    r"stubb\w*",
    r"purra\w*",
    r"häkkä(?:nen|se)\w*",
    r"valto(?:nen|se)\w*",
    r"saariko\w*",
    r"kaikko(?:nen|se)\w*",
    r"niinistö\w*",
    r"sanna marin\w*",
    r"mei(?:d|ll|lt|t|ss)\w*",
    r"pormestar\w*",
    r"kaupunginjohtaj\w*",
    r"kaupunginvaltuust\w*",
    r"kunnanvaltuust\w*",
    r"kunnanjohtaj\w*",
    r"kuntavaali\w*",
    r"espoo\w*",
    r"vantaa\w*",
    r"tampere\w*",
    r"turku\w*",
    r"turu(?:n|lta|lle|ssa|sta|ksi)\b",
    r"oulu\w*",
    r"jyväskyl\w*",
    r"kuopio\w*",
    r"kuopi(?:on|ossa)\b",
    r"lahti\w*",
    r"lahden",
    r"pori\b",
    r"porin",
    r"vaasa\w*",
    r"joensuu\w*",
    r"rovaniem\w*",
    r"kotka\w*",
    r"seinäjo\w*",
    r"lappeenrann\w*",
    r"hämeenlinn\w*",
    r"esbo\b",
    r"vanda\b",
    r"åbo\b",
    r"borgå\b",
    r"tammerfors\b",
    r"uleåborg\b",
    r"aaltola\w*",
)

# A political term: rescues a story that matched a sports/market/section rule.
# "ministeri" and "valtuusto" also match as the end of a compound (valtiovarainministeriö,
# kaupunginvaltuusto).
# Deliberately has no generic "Finland" word: a sports story about Suomen
# maajoukkue is still sports.
POLITICS_RESCUE = _rx(
    r"hallitu\w*",
    r"eduskun\w*",
    r"\w*ministeri\w*",
    r"kansanedustaj\w*",
    r"puolue\w*",
    r"polii?t\w*",
    r"vaal[ie]\w*",
    r"lakiesity\w*",
    r"lakiehdotu\w*",
    r"kokoomu\w*",
    r"perussuomalai\w*",
    r"sdp\b",
    r"vasemmistoliit\w*",
    r"kristillisdemokraat\w*",
    r"rkp\b",
    r"orpo\w*",
    r"stubb\w*",
    r"purra\w*",
    r"häkkä(?:nen|se)\w*",
    r"valto(?:nen|se)\w*",
    r"saariko\w*",
    r"kaikko(?:nen|se)\w*",
    r"kela(?:n|sta|lta|lle|ssa)?\b",
    r"regering\w*",
    r"riksdag\w*",
    r"minister\w*",
    r"politik\w*",
    r"politisk\w*",
    r"partiledare\w*",
    r"pormestar\w*",
    r"\w*valtuust\w*",
    r"kaupunginhallitu\w*",
    r"kunnanhallitu\w*",
    r"kuntavaali\w*",
    r"presidentti\w*",
    r"puheenjohtaj\w*",
    r"halla-aho\w*",
    r"lindtman\w*",
    r"ohisalo\w*",
    r"minja koskela",
    r"li andersson",
    r"sari essayah",
    r"statsminister\w*",
    r"president\w*",
)

SPORTS_TERMS = _rx(
    r"nhl\b",
    r"khl\b",
    r"liiga\w*",
    r"jääkiek\w*",
    r"jalkapall\w*",
    r"valioliig\w*",
    r"mestarien liig\w*",
    r"formula\s?1\b",
    r"f1\b",
    r"moottoriurheil\w*",
    r"olympi\w*",
    r"hiih[td]\w*",
    r"mäkihyp\w*",
    r"salibandy\w*",
    r"koripall\w*",
    r"lentopall\w*",
    r"tennis\w*",
    r"golf\w*",
    r"pesäpall\w*",
    r"maalipörss\w*",
    r"pistepörss\w*",
    r"yleisurheil\w*",
    r"nyrkkeil\w*",
    r"ufc\b",
    r"mma\b",
    r"ishockey\w*",
    r"fotboll\w*",
    r"formel 1",
    r"hjk\b",
    r"kups\b",
    r"maajoukkue\w*",
    r"valmentaj\w*",
    r"pelaaj\w*",
    r"seurajoukkue\w*",
    r"mestaruu\w*",
    r"finaali\w*",
    r"mm-kisa\w*",
    r"maalivahti\w*",
    r"veikkausliig\w*",
    r"handboll\w*",
    r"landslag\w*",
    r"tränare\w*",
    r"innebandy\w*",
    r"käsipall\w*",
)

# Market and business news only: central-bank or tax *policy* is not matched.
FINANCE_TERMS = _rx(
    r"pörss\w*",
    r"osak(?:e|kee|kei)\w*",
    r"osin[kg]\w*",
    r"tulosvaroitu\w*",
    r"tulosjulkistu\w*",
    r"yrityskaup\w*",
    r"kryptovaluut\w*",
    r"bitcoin\w*",
    r"ethereum\w*",
    r"euribor\w*",
    r"börs\w*",
    r"aktie\w*",
    r"kvartalsrapport\w*",
)

# Crime-blotter and accident reports: who died where, who was arrested. Policy angles
# (hate-crime statistics, police resources) use other words and are not matched.
ACCIDENT_CRIME_TERMS = _rx(
    r"ulosajo\w*",
    r"liikenneonnettomuu\w*",
    r"onnettomuudess\w*",
    r"kolari\w*",
    r"kuoli\b",
    r"kuolemaansa",
    r"henkiriko\w*",
    r"surmattu",
    r"surmasi",
    r"pahoinpidel\w*",
    r"pahoinpitel\w*",
    r"ryöstö\w*",
    r"puukot\w*",
    r"poliisi epäile\w*",
    r"poliisi epäili\w*",
    r"trafikolycka\w*",
    r"misstänks\b",
    r"misshandl\w*",
    r"rånat\b",
    r"rån i\b",
    r"dog i\b",
    r"kaahar\w*",
    r"rattijuop\w*",
    r"sarjarikol\w*",
    r"tietomur\w*",
    r"tietomurr\w*",
)

# Video games and esports.
GAMES_TERMS = _rx(
    r"esports\b",
    r"e-urheil\w*",
    r"zelda\b",
    r"playstation\w*",
    r"nintendo\w*",
    r"xbox\w*",
    r"counter-strike\w*",
    r"fortnite\w*",
    r"minecraft\w*",
)

# Weather reports. "sää" must stand alone or take a case ending: sääntö, säätiö do not match.
WEATHER_TERMS = _rx(
    r"sää(?:ssä|n|stä|llä|lle|ennuste\w*)?\b",
    r"lumentulo\w*",
    r"lumisade\w*",
    r"ilmatieteen\w*",
    r"myrskyvaroitu\w*",
    r"hellevaroitu\w*",
)

# Recipes, perfume, horoscopes and seasonal fun.
LIFESTYLE_TERMS = _rx(
    r"resepti\w*",
    r"hajuve\w*",
    r"horoskoop\w*",
    r"halloween\w*",
    r"lucia\b",
    r"luciakandidat\w*",
    r"ljusevenemang\w*",
    r"sisustu\w*",
    r"kändis\w*",
    r"julkkis\w*",
)

# Tabloid celebrity format: "Lindsey Vonn, 42, kertoo ..." (name, comma, two-digit age, comma).
TABLOID_PERSON = re.compile(r"^\s*(?:[A-ZÅÄÖ][\w'\u2019.-]+ ){1,3}[A-ZÅÄÖ][\w'\u2019.-]+, \d{2}, ")

# Foreign countries, leaders and places that are not Finland. "ruotsi" excludes
# "ruotsinkielinen" (Swedish-speaking Finns are Finnish politics).
FOREIGN_TERMS = _rx(
    r"saksa\w*",
    r"berliin\w*",
    r"ranska\w*",
    r"pariisi\w*",
    r"britanni\w*",
    r"lontoo\w*",
    r"italia\w*",
    r"espanja\w*",
    r"puola(?!ng|nk)\w*",
    r"unkari\w*",
    r"turkk?i\w*",
    r"kiina\w*",
    r"japani\w*",
    r"intia\w*",
    r"brasilia\w*",
    r"argentiina\w*",
    r"venezuela\w*",
    r"usa\b",
    r"yhdysvalt\w*",
    r"washington\w*",
    r"trump\w*",
    r"biden\w*",
    r"putin\w*",
    r"venäjä\w*",
    r"venäl\w*",
    r"moskova\w*",
    r"zelensk\w*",
    r"ukrain\w*",
    r"kiova\w*",
    r"israel\w*",
    r"gaza\w*",
    r"hamas\w*",
    r"palestiina\w*",
    r"iran\w*",
    r"irak\w*",
    r"syyria\w*",
    r"afganistan\w*",
    r"pohjois-korea\w*",
    r"taiwan\w*",
    r"valko-venäjä\w*",
    r"erdogan\w*",
    r"macron\w*",
    r"netanyahu\w*",
    r"ruotsi(?!nkiel)\w*",
    r"ruotsalai\w*",
    r"norja\w*",
    r"norjalai\w*",
    r"tanska\w*",
    r"tanskalai\w*",
    r"ryssland\w*",
    r"ukraina\w*",
    r"kina\b",
    r"tyskland\w*",
    r"frankrike\w*",
    r"storbritannien\w*",
    r"syrien\w*",
    r"grönland\w*",
    r"danmark\w*",
    r"norge\w*",
    r"portugal\w*",
    r"myanmar\w*",
    r"turkiet\w*",
    # more countries (Finnish stems; short or ambiguous ones such as Peru, Mali, Oman are
    # left out on purpose: perustuslaki, mallin and oman are common Finnish words)
    r"albania\w*",
    r"algeria\w*",
    r"armenia\w*",
    r"australia\w*",
    r"azerbaidzan\w*",
    r"bangladesh\w*",
    r"belgia\w*",
    r"bolivia\w*",
    r"bosnia\w*",
    r"bulgaria\w*",
    r"chile\w*",
    r"kolumbia\w*",
    r"kuuba\w*",
    r"kreik\w*",
    r"egypti\w*",
    r"etiopia\w*",
    r"filippiin\w*",
    r"georgia\w*",
    r"ghana\w*",
    r"haiti\w*",
    r"hollan\w*",
    r"alankoma\w*",
    r"indonesia\w*",
    r"irlanti\w*",
    r"islanti\w*",
    r"jordania\w*",
    r"jemen\w*",
    r"kambodza\w*",
    r"kanada\w*",
    r"kazakstan\w*",
    r"kenia\w*",
    r"kroatia\w*",
    r"kuwait\w*",
    r"libanon\w*",
    r"libya\w*",
    r"malesia\w*",
    r"meksik\w*",
    r"marokko\w*",
    r"mongolia\w*",
    r"nepal\w*",
    r"nigeria\w*",
    r"pakistan\w*",
    r"portugali\w*",
    r"qatar\w*",
    r"romania\w*",
    r"saudi\w*",
    r"serbia\w*",
    r"singapore\w*",
    r"slovakia\w*",
    r"slovenia\w*",
    r"somalia\w*",
    r"sudan\w*",
    r"sveitsi\w*",
    r"thaimaa\w*",
    r"tunisia\w*",
    r"uganda\w*",
    r"uzbekistan\w*",
    r"vietnam\w*",
    r"itävalt\w*",
    r"itävall\w*",
    r"tšekk?i\w*",
    r"etelä-korea\w*",
    r"lähi-id\w*",
    r"kongo\w*",
    r"zimbabwe\w*",
    r"istanbul\w*",
    r"ankara\w*",
    r"kairo\w*",
    r"teheran\w*",
    r"bagdad\w*",
    r"damaskos\w*",
    r"jerusalem\w*",
    r"tel aviv\w*",
    r"peking\w*",
    r"tokio\w*",
    r"bangkok\w*",
    r"lissabon\w*",
    r"rooma\w*",
    r"madrid\w*",
    r"varsova\w*",
    r"budapest\w*",
    r"ateena\w*",
    r"new york\w*",
    r"kalifornia\w*",
    r"sverige\w*",
    r"sveriges",
    r"kristersson\w*",
    r"norsk\w*",
    r"dansk\w*",
    r"jenkki\w*",
    r"amerikka\w*",
    r"amerikkalai\w*",
)


_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    # Soft hyphens and other invisible characters split words and defeat matching.
    return text.replace("\u00ad", "").replace("\u200b", "")


def _lead(body: str) -> str:
    """Opening of the body as plain text. It may be an RSS summary with HTML in it."""
    return _clean(_TAG.sub(" ", (body or "")[: LEAD_CHARS * 2]))[:LEAD_CHARS]


_LABEL = re.compile(r"^\s*([^|:]{2,30}?)\s*\|\s*(.+)$", re.DOTALL)


def _split_label(title: str) -> tuple[str, str]:
    """("musiikki", "Kurdilaulaja ...") for "Musiikki | Kurdilaulaja ..."; ("", title) otherwise."""
    m = _LABEL.match(title)
    return (m.group(1).strip().lower(), m.group(2)) if m else ("", title)


def _section(url: str) -> str:
    """First path segment of the URL, e.g. 'nhl' for https://www.is.fi/nhl/art-1.html."""
    try:
        path = urlparse(url or "").path
    except ValueError:
        return ""
    parts = [p for p in path.split("/") if p]
    return parts[0].lower() if parts else ""


def _first(rx: re.Pattern[str], text: str) -> str:
    m = rx.search(text)
    return m.group(0).lower() if m else ""


def check_scope(*, title: str, url: str = "", body: str = "", source: str = "") -> ScopeDecision:
    """Decide whether an article belongs in the project. Pure, fast, no I/O.

    `source` is the outlet slug; party and ideological organs are never filtered.
    """
    if source in UNFILTERED_SOURCES:
        return ScopeDecision(True, f"party-organ:{source}")

    title = _clean(title or "")
    lead = _lead(body)
    section = _section(url)

    # 1. Political section
    if section in POLITICAL_SECTIONS:
        return ScopeDecision(True, f"domestic-section:{section}")

    # 2a. Clearly non-political headline label ("Musiikki | ...")
    label, rest = _split_label(title)
    if label in NONPOLITICAL_LABELS:
        if POLITICS_RESCUE.search(rest):
            return ScopeDecision(True, f"kept:political-title-in-label-{label}")
        return ScopeDecision(False, f"non-political-label:{label}")

    # 2. Clearly non-political section
    if section in NONPOLITICAL_SECTIONS:
        if POLITICS_RESCUE.search(title):
            return ScopeDecision(True, f"kept:political-title-in-{section}")
        return ScopeDecision(False, f"non-political-section:{section}")

    # 3. Foreign section
    if section in FOREIGN_SECTIONS:
        if FINLAND_MARKER.search(f"{title} {lead}"):
            return ScopeDecision(True, f"kept:finland-link-in-{section}")
        return ScopeDecision(False, f"foreign-section:{section}")

    # 4. No decisive section: look for positive evidence in the title
    political = POLITICS_RESCUE.search(title)
    if not political:
        term = _first(SPORTS_TERMS, title)
        if term:
            return ScopeDecision(False, f"sports-term:{term}")
        for family, rx in (
            ("finance", FINANCE_TERMS),
            ("crime-or-accident", ACCIDENT_CRIME_TERMS),
            ("games", GAMES_TERMS),
            ("weather", WEATHER_TERMS),
            ("lifestyle", LIFESTYLE_TERMS),
        ):
            term = _first(rx, title)
            if term:
                return ScopeDecision(False, f"{family}-term:{term}")
        if TABLOID_PERSON.match(title):
            return ScopeDecision(False, "tabloid-person")

    term = _first(FOREIGN_TERMS, title)
    if (
        term
        and section not in GENERAL_DOMESTIC_SECTIONS
        and not FINLAND_MARKER.search(f"{title} {lead}")
    ):
        return ScopeDecision(False, f"foreign-term:{term}")

    # 5. Default: keep
    return ScopeDecision(True, "in-scope")
