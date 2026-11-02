"""Measure the scope filter on labelled headlines before trusting it.

Usage, from apps/scrapers with the venv active:
    python -m scripts.eval_scope_gate          # rules only: no API key, no cost
    python -m scripts.eval_scope_gate --llm    # rules, then the model gate (one real call)

What to read in the output:
  1. "KEEP items wrongly dropped" must be empty. A political article that is dropped is the
     costly mistake: it silently removes coverage.
  2. "DROP items missed" is the waste that still gets through; the gate should shrink it.
  3. "ASK" items have no firm label (they depend on the article text). Look at them and
     decide; they are not counted.

The labels below are one person's judgement from a single scrape. Edit any you disagree with,
and add new headlines from your own database as you find them. The prompt in src/scope_gate.py
deliberately uses different, invented examples, so this list is a fair test of the model.
"""

# ruff: noqa: E501, RUF001
from __future__ import annotations

import argparse

from src import scope_gate
from src.relevance import check_scope

KEEP, DROP, ASK = "KEEP", "DROP", "ASK"

# (label, source, url or "", title)
GOLDEN: list[tuple[str, str, str, str]] = [
    (
        KEEP,
        "iltalehti",
        "",
        "Politiikan puskaradio: Kysymys kansanedustajien määrästä sai aikaan outoja – Jani Mäkelästä sikisi kepulainen aluepoliitikko",
    ),
    (
        KEEP,
        "verkkouutiset",
        "",
        "Puolustusvoimain komentaja Juhani Kaskeala vei Suomea länteen, vaikka ylipäällikkönä oli Tarja Halonen",
    ),
    (
        KEEP,
        "verkkouutiset",
        "",
        "Ekonomisti optimistisena: Ongelmat julkisessa taloudessa voidaan ratkoa vajaassa vuodessa",
    ),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Puolustusala | Supo: Emme ole tulppa puolustusalan työvoimajumissa",
    ),
    (
        KEEP,
        "suomenmaa",
        "",
        "Maajussille morsiamessa tuli pettymys, mutta se opetti – Hannu Laturi tähtää nyt eduskuntaan",
    ),
    (
        KEEP,
        "demokraatti",
        "",
        "Markus Leikola: Onko Mamdanin tie Suomen tie – vai syökö eipäs-juupas-väittely tulevaisuutemme?",
    ),
    (
        KEEP,
        "suomen-uutiset",
        "",
        "Psykologi selittää woken sekä maahanmuuttosokeuden – narsismi mädätti kulttuurin ja some nuorten aivot",
    ),
    (
        KEEP,
        "suomen-uutiset",
        "",
        "Oikeusministeri Leena Meri haluaa kiristää rangaistuksia: ”Liiallisista paljousalennuksista on päästävä eroon”",
    ),
    (
        DROP,
        "helsingin-sanomat",
        "https://www.hs.fi/popkulttuuri/art-2000012347188.html",
        "Musiikki | Kurdilaulaja Aynur joutui poistumaan lavalta kesken konsertin, koska lauloi omalla kielellään",
    ),
    (DROP, "yle", "", "Portugalin poliisi purki kovin ottein mielenosoittajien telttaleirit"),
    (
        DROP,
        "ilta-sanomat",
        "",
        "”Suomi on kuin sisään kasvanut varpaankynsi” – IS:n lukijat kommentoivat lasten karkkikierroksia",
    ),
    (DROP, "hufvudstadsbladet", "", "Jag tror inte på de svenska influerarnas Parisfantasi"),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Tyylitietoiset ottavat nyt mallia sipuleista – tältä tyyli näyttää",
    ),
    (
        DROP,
        "iltalehti",
        "",
        "17-vuotias Pinja laittoi pakollisen merkin autoon – Sitten alkoi vaarallinen käytös",
    ),
    (DROP, "hufvudstadsbladet", "", "De är årets luciakandidater"),
    (
        DROP,
        "kansan-uutiset",
        "",
        "Sota ei ole Myanmarin ainoa kriisi – Tulvat, nälkä ja taudit koskettavat miljoonia",
    ),
    (
        DROP,
        "ilta-sanomat",
        "https://www.is.fi/nhl/art-2000012380458.html",
        "Artturi Lehkonen nousi jo NHL:n maalipörssin kakkoseksi – Cale Makar hykerteli kaukalossa",
    ),
    (
        DROP,
        "helsingin-sanomat",
        "https://www.hs.fi/ulkomaat/art-2000012345678.html",
        "HS Berliinissä | Saksan politiikkaan tuli ”Voldemort” nimeltä Ibrahim Ibrahim, jota Berliinin vasemmistojohtaja pelkää",
    ),
    (ASK, "svenska-yle", "", "Vem döljer sig i handen?"),
    (ASK, "suomenmaa", "", "Vieraskynä: Rakentamisessa on nähtävä metsä puilta"),
    (ASK, "kansan-uutiset", "", "Äärimmäinen kuumuus uhkaa raskaana olevia ja vastasyntyneitä"),
    (ASK, "demokraatti", "", "Meri Valkama: Nostalgianhalu nielaisee tulevaisuuden"),
    (
        ASK,
        "yle",
        "",
        "Ylen toimittaja pyysi kauppajäteiltä tietonsa, ja aineisto paljasti hämmentäviä arvioita",
    ),
    (
        ASK,
        "svenska-yle",
        "",
        "Har du en privat pensionsförsäkring? Efter årsskiftet blir de olönsamma",
    ),
]


def evaluate(use_llm: bool) -> str:
    out: list[str] = []
    rule_drop: dict[int, str] = {}
    for i, (_, _, url, title) in enumerate(GOLDEN):
        decision = check_scope(title=title, url=url)
        if not decision.in_scope:
            rule_drop[i] = decision.reason

    gate_drop: dict[int, str] = {}
    if use_llm:
        survivors = [
            (str(i), title, "") for i, (_, _, _, title) in enumerate(GOLDEN) if i not in rule_drop
        ]
        for key, (keep, why) in scope_gate.classify(survivors).items():
            if not keep:
                gate_drop[int(key)] = why

    def verdict(i: int) -> str:
        if i in rule_drop:
            return f"DROPPED by rules ({rule_drop[i]})"
        if i in gate_drop:
            return f"DROPPED by gate ({gate_drop[i]})"
        return "kept"

    wrong = [i for i, g in enumerate(GOLDEN) if g[0] == KEEP and (i in rule_drop or i in gate_drop)]
    drops = [i for i, g in enumerate(GOLDEN) if g[0] == DROP]
    caught = [i for i in drops if i in rule_drop or i in gate_drop]
    missed = [i for i in drops if i not in rule_drop and i not in gate_drop]

    stage = "rules + model gate" if use_llm else "rules only"
    out.append(f"== {stage} ==")
    n_keep = sum(g[0] == KEEP for g in GOLDEN)
    out.append(f"KEEP items wrongly dropped: {len(wrong)} of {n_keep}   (must be 0)")
    for i in wrong:
        out.append(f"   !! {verdict(i)}: {GOLDEN[i][3][:90]}")
    out.append(f"DROP items caught: {len(caught)} of {len(drops)}   missed: {len(missed)}")
    for i in missed:
        out.append(f"   .. still passes: [{GOLDEN[i][1]}] {GOLDEN[i][3][:80]}")
    out.append("ASK items (not counted, look at them):")
    for i, g in enumerate(GOLDEN):
        if g[0] == ASK:
            out.append(f"   ?? {verdict(i):<36} [{g[1]}] {g[3][:70]}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the scope filter on labelled headlines.")
    parser.add_argument(
        "--llm", action="store_true", help="also run the model gate (needs MISTRAL_API_KEY)"
    )
    args = parser.parse_args()
    print(evaluate(use_llm=False))
    if args.llm:
        print()
        print(evaluate(use_llm=True))
        print(f"\nmodel used: {scope_gate._model()}")


if __name__ == "__main__":
    main()
