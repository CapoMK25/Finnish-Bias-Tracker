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

The labels below are one person's judgement from three scrapes (a local run plus two three-hour production listings).
Rows from party organs are KEEP by policy (UNFILTERED_SOURCES). Edit any you disagree with,
and add new headlines from your own database as you find them. The prompt in src/scope_gate.py
deliberately uses different, invented examples, so this list is a fair test of the model.
"""

# ruff: noqa: E501, RUF001
from __future__ import annotations

import argparse

from src import scope_gate
from src.relevance import UNFILTERED_SOURCES, check_scope

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
        KEEP,
        "suomenmaa",
        "",
        '"Liikkuvat naisäänestäjät ratkaisevat" – Tässä ovat keskustanaisten vaalitavoitteet',
    ),
    (
        KEEP,
        "iltalehti",
        "",
        "Iskeekö hallitus kohta myös rajun marja- ja sienikiellon? Virkamies kommentoi",
    ),
    (
        KEEP,
        "iltalehti",
        "",
        "”Onhan tämä härskiä” – Hallitukselle rankka syytös autoilijoiden pettämisestä",
    ),
    (KEEP, "verkkouutiset", "", "Entä epätavalliset suomalaiset? ”Heitä on liian vähän”"),
    (
        KEEP,
        "demokraatti",
        "",
        "Orpo: Hallitus valmistelee venäläisurheilijoiden viisumien epäämistä – ”Minusta on ihan sama, mistä urheilulajista on kyse”",
    ),
    (KEEP, "verkkouutiset", "", "Petteri Orpo: Meillä on aivan sama unelma Suomesta"),
    (
        KEEP,
        "iltalehti",
        "",
        "Ministeri: Suomen Venäjä-rintama laajenee – Nyt vireillä uusi ”signaali”",
    ),
    (KEEP, "ilta-sanomat", "", "Henri Vanhanen harkitsee eduskuntavaaliehdokkuutta"),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Datakeskukset | Datakeskuksia ei voi suunnitella kunta kerrallaan",
    ),
    (
        KEEP,
        "suomenmaa",
        "",
        'Oppositio sätti hallitusta arjen kustannusten noususta: "Orpon kannattaisi kuunnella kansaa eikä lobbareita"',
    ),
    (
        KEEP,
        "iltalehti",
        "",
        "Ano Turtiaisen entisessä puolueessa jättimyllerrys – Uusi nimi, johtaja ja aate",
    ),
    (KEEP, "svenska-yle", "", "Planeringen av ett litet kärnkraftverk i Helsingfors fortskrider"),
    (
        KEEP,
        "iltalehti",
        "",
        "Kuohunta venäläisurheilijoista: Suomella kova toimi tekeillä – Nyt puhuu Petteri Orpo",
    ),
    (KEEP, "hufvudstadsbladet", "", "En cancerstrategi måste också finansieras"),
    (KEEP, "hufvudstadsbladet", "", "Svenskan har enbart telefontid på fredagar"),
    (KEEP, "hufvudstadsbladet", "", "Kustbanan är snabbaste och billigaste alternativet"),
    (
        KEEP,
        "yle",
        "",
        "Petteri Orpo eväisi venäläisurheilijoiden viisumit: ”Syytä pystyä nopeaan päätöksentekoon”",
    ),
    (
        KEEP,
        "ilta-sanomat",
        "",
        "Nyt puhuu Petteri Orpo: Hallitus valmistelee kovaa iskua venäläisurheilijoille",
    ),
    (KEEP, "verkkouutiset", "", "Ministeriltä suora kysymys oppositioon: Millä rahalla?"),
    (KEEP, "verkkouutiset", "", "SDP:n mukaan yhä useampi suomalainen voi huonommin"),
    (
        KEEP,
        "suomenmaa",
        "",
        "Keskustan Siponen välikysymyskeskustelussa: Datakeskuksille kovempi sähkövero, kotitalouksilta vero pois",
    ),
    (
        KEEP,
        "suomen-uutiset",
        "",
        "Opposition puheet ja teot ristiriidassa – Peltokangas: ”Politiikallanne kansalaisten arjen kustannukset kasvaisivat”",
    ),
    (
        KEEP,
        "demokraatti",
        "",
        "SDP moukaroi hallitusta välikysymyskeskustelussa: ”Perussuomalaisetkin päätyivät laittamaan nimensä ratkaisun alle”",
    ),
    (
        KEEP,
        "verkkouutiset",
        "",
        "Pia Kauma: Ostovoima on kasvanut kahdeksalla kymmenestä suomalaisesta",
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
    (
        DROP,
        "svenska-yle",
        "",
        "Är Andreas Rönnberg handbollslandslagets följande tränare? ”Absolut intresserad”",
    ),
    (DROP, "svenska-yle", "", "Norskt varuhus utsatt för hackarattack ett dygn efter andra länder"),
    (
        DROP,
        "yle",
        "",
        "Paraislainen Marja Lindén on kummi kolmelle, joita ei tunne – kummien puuttuminen ei ole jatkossa este kasteelle",
    ),
    (DROP, "ilta-sanomat", "", "Odotettu käänne säässä"),
    (DROP, "hufvudstadsbladet", "", "Folkhälsans förbund säger upp – 25 kan få gå"),
    (DROP, "ilta-sanomat", "", "Sasu sai äidiltään hätäisen puhelun – uima-altaassa räpiköi ilves"),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Anne osti perheineen kuusi pakettia tarjouskahvia – someraivo leimahti",
    ),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Kalle Rovanperän sopimuksen yksityiskohdat paljastuivat – näin käy palkalle",
    ),
    (
        DROP,
        "yle",
        "",
        "”Tämä on elävä perinne, ja on kaunista päästä astumaan siihen sisään”, kuvaa artistivieras saunakokemustaan Tampereella",
    ),
    (DROP, "iltalehti", "", "Kaaos nuorten juhlissa Helsingissä – ”Eivät pystyneet hengittämään”"),
    (DROP, "iltalehti", "", "Raju törmäys Tampereella: Pyöräilijä lensi 7 metriä"),
    (
        DROP,
        "helsingin-sanomat",
        "",
        "Oikeudenkäynnit | Laituriin törmännyt Viking Line: Allas Pool oli väärässä paikassa",
    ),
    (DROP, "hufvudstadsbladet", "", "Platt fall – Kristerssons tur att försöka"),
    (DROP, "svenska-yle", "", "Böter för kundrådgivare som tittade på patientuppgifter olovligt"),
    (
        DROP,
        "verkkouutiset",
        "",
        "Tilasitko HS:n ennen evästeuudistusta? Juristi kertoo, mitä voit vaatia",
    ),
    (DROP, "yle", "", "Näistä syistä reseptilääke voi jäädä apteekin hyllylle"),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Tämä trendiherkku tulee nyt vastaan joka paikassa – tätä mieltä on ravitsemusterapeutti",
    ),
    (DROP, "ilta-sanomat", "", "FT: Spotifylta uusi palvelu ensi vuoden alussa"),
    (
        DROP,
        "suomen-uutiset",
        "",
        "USA:n vaaleissa ennustetaan demokraattien voittoa – jälkipyykkiä tulee varmasti",
    ),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Pakastimet sulivat, meneekö seuraavaksi sähköt? – asiantuntijoilta synkkä arvio",
    ),
    (DROP, "iltalehti", "", "Mitä tapahtuu Vladimir Putinille? – Venäjä-diplomaatilta suora arvio"),
    (DROP, "svenska-yle", "", "Sverige: Centerledaren nedröstad i riksdagen"),
    (DROP, "suomenmaa", "", "Ruotsin valtiopäivät torppasi keskustajohtajan pääministeriyden"),
    (
        DROP,
        "demokraatti",
        "",
        "Ei onnistunut vieläkään: Elisabeth Thand Ringqvist tyrmättiin Ruotsissa",
    ),
    (
        DROP,
        "helsingin-sanomat",
        "",
        "Terveydenhoito | Anestesiaan voi suhtautua luottavaisin mielin",
    ),
    (
        DROP,
        "verkkouutiset",
        "",
        "Tekeekö kasvisruokavalio miehestä naisellisen? Tutkimus haastaa käsityksen",
    ),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Jos osaat ottaa huomioon nämä 8 asiaa, olet kohteliaampi kuin moni muu",
    ),
    (
        DROP,
        "iltalehti",
        "",
        "Vaaratilanne keskellä päivää: Parvekelasi putosi – Isännöitsijä ei ole koskaan nähnyt vastaavaa",
    ),
    (DROP, "svenska-yle", "", "Unga män misstänks för en serie rån i Esbo"),
    (
        DROP,
        "helsingin-sanomat",
        "",
        "Espoo | Viiden nuoren miehen epäillään uhkailleen ryöstöjen uhreja viidakkoveitsellä",
    ),
    (DROP, "ilta-sanomat", "", "Poliisi epäilee: 20-vuotias nainen surmattu Jyväskylässä"),
    (
        DROP,
        "svenska-yle",
        "",
        "16-åring misstänks ha misshandlat och rånat en 35-åring i en lägenhet i Borgå",
    ),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Poliisi epäilee: Tuntematon mies lyöttäytyi 15-vuotiaan tytön seuraan ja pahoinpiteli teräaseella",
    ),
    (
        DROP,
        "helsingin-sanomat",
        "",
        "Kirjeenvaihtajan analyysi | Sininen tsunami väräjää horisontissa – Mutta vasta siitä alkaisi kunnon vääntö",
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
    (ASK, "iltalehti", "", "HS: STT yritetään vielä pelastaa"),
    (ASK, "svenska-yle", "", "Kervo och Sibbos nya idrottshall används mindre än väntat"),
    (
        ASK,
        "ilta-sanomat",
        "",
        "Porua aiheuttanutta pyörätietä ei tulekaan – syynä liian hyvä näkyvyys pääministerin asuntoon",
    ),
    (ASK, "svenska-yle", "", "Omstridd cykelbro i Mejlans slopas av säkerhetsskäl"),
    (
        ASK,
        "svenska-yle",
        "",
        "Kymen Sanomat: Tillstånds- och tillsynsverket har stoppat Googles datacenterutvidgning i Fredrikshamn",
    ),
    (
        ASK,
        "yle",
        "",
        "Lupa- ja valvontavirasto on pyytänyt Googlea keskeyttämään rakennustöitä Haminassa – syynä uusi huoli liito-oravista",
    ),
    (ASK, "verkkouutiset", "", "HS: STT saattaa sittenkin pelastua"),
    (
        ASK,
        "svenska-yle",
        "",
        "Snart går flyttlasset till nya förlossningsavdelningen vid Vasa centralsjukhus: ”Vi är jättenöjda!”",
    ),
    (ASK, "hufvudstadsbladet", "", "Omstridd cykelbro i Mejlans blir inte av"),
    (ASK, "helsingin-sanomat", "", "Työtaistelu | Parkkipaten työntekijöiden lakko peruuntuu"),
    (
        ASK,
        "yle",
        "",
        "Turvallisuushuolet kaatoivat sillan: Helsinki ei rakenna kiisteltyä pyöräilysiltaa lähelle pääministerin virka-asuntoa",
    ),
    (
        ASK,
        "helsingin-sanomat",
        "",
        "Helsinki | Humallahden siltaa ei rakenneta, koska sillalta näkyisi liian hyvin pääministerin asuntoon",
    ),
    (
        ASK,
        "helsingin-sanomat",
        "",
        "Tupakkalaki | Helsinkiläisessä vesipiippubaarissa rikotaan tupakkalakia toistuvasti",
    ),
    (ASK, "helsingin-sanomat", "", "Media | STT:tä yritetään vielä kerran pelastaa"),
    (ASK, "ilta-sanomat", "", "ParkkiPaten lakko peruuntuu"),
    (ASK, "verkkouutiset", "", "Pysäköinninvalvojien lakko peruuntuu"),
    (ASK, "ilta-sanomat", "", "Kommentti: Ruotsi petti meidät"),
    (ASK, "demokraatti", "", "Nyt tuli varmistus: JHL ja Parkkipate sopuun – tätä se tarkoittaa"),
    (
        ASK,
        "yle",
        "",
        "Yksi hetki laboratoriossa muutti professorin mielen: ”Herran tähden” – tekoäly onkin uhka",
    ),
    (ASK, "svenska-yle", "", "Jobbet betydde allt – nu läggs fabriken i Kristinestad ner"),
    (ASK, "suomenmaa", "", "Parkkipaten työriita ohi, lakko peruuntuu"),
    (KEEP, "demokraatti", "", "Turulta Venäjä-ukaasi – näin kommentoi pormestari Piia Elo"),
    (
        KEEP,
        "helsingin-sanomat",
        "https://www.hs.fi/nakemys/art-2000012384920.html",
        "Muut lehdet | Venäjän kanssa pelaaminen olisi nykyoloissa epäisänmaallista",
    ),
    (
        ASK,
        "demokraatti",
        "",
        "Ruotsalaisselvitys: Tällaisilla verkostoilla Venäjä yrittää vaikuttaa naapurimaihin",
    ),
    (KEEP, "ilta-sanomat", "", "Pääministeri Orpo pommiuhista: ”Tämä on nyt tätä aikaa”"),
    (KEEP, "hufvudstadsbladet", "", "Stubb: ”Sluta gnälla”"),
    (KEEP, "ilta-sanomat", "", "Orpo: ”Perussuomalaiset varmaan tekevät hieman parempaa työtä”"),
    (KEEP, "iltalehti", "", "Poikkeuksellinen tempaus Eduskuntatalolle"),
    (KEEP, "iltalehti", "", "Hallitus varautuu poikkeusoloihin – Esittää uutta valmiuslakia"),
    (KEEP, "svenska-yle", "", "Förslag till ny beredskapslag"),
    (KEEP, "svenska-yle", "", "Orpo om bombhoten mot flygtrafiken: Så här är det nuförtiden"),
    (KEEP, "iltalehti", "", "Kokoomus syöksykierteessä – Näin selittää Petteri Orpo"),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Kannatusluisu | Kokoomuksen kannatus murenee, Orpo: ”Perussuomalaiset varmaan tekee hieman parempaa työtä”",
    ),
    (KEEP, "hufvudstadsbladet", "", "Orpo om bombhoten: Tiden vi lever i"),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Armeija | Pakolliset kertausharjoitukset sotkevat monen opintoja, sanoo Mats Uotila",
    ),
    (KEEP, "hufvudstadsbladet", "", "Nedskärningar hotar det finlandssvenska kulturlivet"),
    (KEEP, "iltalehti", "", "Finnairin pommiuhkaukset: Nyt puhuu Petteri Orpo"),
    (KEEP, "ilta-sanomat", "", "Hallitus: Ikäraja energiajuomille"),
    (
        KEEP,
        "yle",
        "",
        "Hallitus päätti kiistellystä ennallistamisesta: ei pakkoa suojelualueiden ulkopuolelle, luonnonmetsien määrä putosi puoleen",
    ),
    (
        KEEP,
        "yle",
        "",
        "Analyysi: Miksi taloustieteilijät tunkevat nenäänsä koulumaailmaan? – tästä on kyse kiistassa kansallisista kokeista",
    ),
    (KEEP, "yle", "", "Ykkösaamun vieraana presidentti Sauli Niinistö – mitä haluat kysyä?"),
    (
        KEEP,
        "iltalehti",
        "",
        "Veret seisauttavan huono luku jysähti – Nyt puhuu kokoomuksen puoluesihteeri",
    ),
    (KEEP, "helsingin-sanomat", "", "Työttömyys | Työtön tarvitsee työtä eikä leimoja"),
    (KEEP, "ilta-sanomat", "", "Timo Soini: Minja Koskelasta voi tulla valtiovarainministeri"),
    (KEEP, "iltalehti", "", "Yksi kuva paljastaa – Näin jyrkkä on kokoomuksen alamäki"),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Seksuaalirikokset | Poliisi ei ehdi tutkia kaikkia raiskauksia – Poliisiylijohtaja ei hyväksy selitystä",
    ),
    (KEEP, "ilta-sanomat", "", "Viharikoksissa ennätysvuosi – yksi kaupunki nousi Helsingin ohi"),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Asuntokauppa | Ensiasunnon ostoon tulossa iso helpotus: Laskuri näyttää, kuinka paljon hyödyt",
    ),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Eutanasia | Lääkäriavusteinen eutanasia voisi olla vaihtoehto",
    ),
    (
        KEEP,
        "helsingin-sanomat",
        "",
        "Nordic Compass | Pohjoismaalaiset suuryritykset etsivät yhteistä lobbausvoimaa, mukana myös Stubb",
    ),
    (
        DROP,
        "ilta-sanomat",
        "https://www.is.fi/esports/art-2000012390622.html",
        "Huippujoukkue palkkasi pornotähden",
    ),
    (
        DROP,
        "iltalehti",
        "https://www.iltalehti.fi/kotimaa/a/63e8541d-7ace-4042-99bd-8716227c8b3f?utm_source=rss",
        "Ulosajo Ilomantsissa – Kuljettaja kuoli",
    ),
    (DROP, "ilta-sanomat", "", "Mies kuoli ulosajossa"),
    (DROP, "ilta-sanomat", "", "HJK:ssa kova myllerrys: Kahdeksan pelaajaa ulos"),
    (
        DROP,
        "yle",
        "",
        "Cristiano Ronaldo päättää maajoukkueuransa – tunteikas vuodatus Instagramissa",
    ),
    (DROP, "ilta-sanomat", "", "Lindsey Vonn, 42, kertoo poikaystävästään, 30: ”En aio”"),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Maria Kuusiluoma, 57, joutui leikkaukseen – ei palaa teatterin lavalle ennen huhtikuuta",
    ),
    (DROP, "svenska-yle", "", "Otto Svarvar led av panikångest: ”En period saknade jag ångesten”"),
    (DROP, "svenska-yle", "", "Kändiseken Paavolan tammi i Lojo såld"),
    (
        DROP,
        "svenska-yle",
        "",
        "Alisha Potrykus är Finlands Lucia: ”Handlar om allt annat än utseende”",
    ),
    (DROP, "hufvudstadsbladet", "", "Alisha Potrykus är Finlands lucia 2026"),
    (DROP, "svenska-yle", "", "Populära ljusevenemanget i Åbo startar i år från musikhuset Fuga"),
    (
        DROP,
        "svenska-yle",
        "",
        "Vilken är den värsta språkgrodan du minns? Hans-Åke Manelius samlar på roliga och vilseledande missar",
    ),
    (
        DROP,
        "yle",
        "",
        "Nicola Ussherin raejuustopizzan reseptiä on katsottu lähes miljoonaa kertaa",
    ),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Suurin osa suomalaisista tekee hajuveden kanssa haitallisen virheen",
    ),
    (DROP, "ilta-sanomat", "", "9,6/10 – ”uusi” Zelda räjäytti pankin"),
    (
        DROP,
        "helsingin-sanomat",
        "",
        "HS testaa | Mazdan uusi sähköauto keksii sivupeilit uusiksi, ja parkkipaikalla uhkaa pelti rytistä",
    ),
    (DROP, "iltalehti", "", "Tämä tiedetään lumentulosta nyt"),
    (
        DROP,
        "ilta-sanomat",
        "",
        "Halloween-asu johti hurjaan tilanteeseen – sähköpotkulautailija oli lähellä vakavaa vaaraa",
    ),
    (
        DROP,
        "iltalehti",
        "",
        "Poliisilta painava muistutus: Tämä asia halloween-asussa voi olla rikos",
    ),
    (
        DROP,
        "yle",
        "",
        "Poliisi: Oulussa ei tapahtunutkaan alaikäisen pahoinpitelyä terävällä esineellä – nuori sepitti koko jutun",
    ),
    (DROP, "iltalehti", "", "Poliisi epäili järkyttävää rikosta – Nyt paljastui totuus"),
    (
        DROP,
        "iltalehti",
        "",
        "Kaahari ei pysähtynyt edes piikkimattoon – Sitten poliisi avasi tulen",
    ),
    (
        DROP,
        "helsingin-sanomat",
        "",
        "Tuomiot | Nuori mies tiiraili droonilla alastomia ihmisiä Helsingissä",
    ),
    (DROP, "iltalehti", "", "Työntekijä putosi korkeuksista kuolemaansa Paraisilla"),
    (DROP, "ilta-sanomat", "", "Postinjakaja kuoli onnettomuudessa – poliisi pyytää vihjeitä"),
    (
        DROP,
        "iltalehti",
        "",
        "Vakava törmäys postiajoneuvon ja auton välillä – Viisikymppinen Postin kuljettaja kuoli",
    ),
    (DROP, "svenska-yle", "", "Postutdelare dog i en trafikolycka i Åbo"),
    (
        DROP,
        "iltalehti",
        "",
        "Epäilty sarjarikollinen laskettiin vapaaksi – Jäi heti kiinni uudelleen",
    ),
    (DROP, "ilta-sanomat", "", "Susi liikkui koulun ja päiväkodin lähellä Raumalla"),
    (DROP, "svenska-yle", "", "Sverige förlänger gränskontrollerna"),
    (DROP, "iltalehti", "", "Asiantuntija: Tätä Vladimir Putin joutuu nyt miettimään"),
    (
        DROP,
        "yle",
        "",
        "Jenkkivaalien tähti kävi toimittajaan käsiksi – asiantuntija: Voi näyttää aggressiiviselta ja uhkaavalta",
    ),
    (
        DROP,
        "ilta-sanomat",
        "",
        "TV1 näyttää alkuillasta karmivan henkirikoksen Suomen historiasta – ei herkimmille",
    ),
    (
        DROP,
        "helsingin-sanomat",
        "",
        "Sijoittaminen | Mandatumin asiakkaiden tileille tunkeuduttiin: Osa saattanut menettää rahaa",
    ),
    (DROP, "ilta-sanomat", "", "Tietomurto: Asiakkaiden tileillä luvatonta toimintaa"),
    (ASK, "hufvudstadsbladet", "", "Superintelligens är inte ”Trumps påhitt”"),
    (
        ASK,
        "ilta-sanomat",
        "",
        "Sähkön hinta lähes 15-kertaistuu perjantaina – tässä päivän kallein hetki",
    ),
    (
        ASK,
        "svenska-yle",
        "",
        "Falska bombhot och hackade kyldiskar har antagligen ett samband: ”Skapar splittring”",
    ),
    (ASK, "hufvudstadsbladet", "", "Förslag: Bort med ”fel” färg på spårvagnarna"),
    (
        ASK,
        "yle",
        "",
        "Vantaalle rakennetaan valtaisaa uimahallia – yksi erikoisuus pistää siellä silmään",
    ),
    (ASK, "iltalehti", "", "”Surulliseksi vetää” – Tunnettu kirkko puretaan Helsingissä"),
    (ASK, "svenska-yle", "", "Novia i Vasa tar över utbildandet av idrottsinstruktörer"),
    (
        ASK,
        "ilta-sanomat",
        "",
        "Heikki oli lennolla Wieniin, kun pommiuhkasta kuulutettiin – näin matkustajat reagoivat",
    ),
    (
        ASK,
        "ilta-sanomat",
        "",
        "Onko yhteiskuntamme rakennettu haavoittuvaiseksi? Asiantuntijoilla näkemys",
    ),
    (ASK, "ilta-sanomat", "", "Mika Aaltola kommentoi pommiuhkia – mainitsee Venäjän"),
    (
        ASK,
        "yle",
        "",
        "Vantaan Havukoski on tavallinen radanvarsilähiö, jossa ulkomaistaustaisia on enemmän kuin kantaväestöä",
    ),
    (ASK, "yle", "", "Yli kymmenellä lennolla pommiuhkauksia Euroopassa"),
    (
        KEEP,
        "verkkouutiset",
        "",
        "Kinkku pitää pintansa: näitä ruokia suomalaiset haluavat joulupöytään",
    ),
    (KEEP, "verkkouutiset", "", "Suomalaiset ovat tekoälyn käyttäjinä keskitasoa"),
    (KEEP, "suomenmaa", "", "Postia jakanut mies kuoli liikenneonnettomuudessa Turussa"),
    (KEEP, "suomenmaa", "", "Kadoksissa ollut mies löytyi kylmettyneenä maastosta Luumäellä"),
    (KEEP, "demokraatti", "", "Finnair: Perätön pommiuhkaus"),
]


def expected_label(row: tuple[str, str, str, str]) -> str:
    """Party and ideological organs are never filtered, so everything from them is KEEP."""
    label, source = row[0], row[1]
    return KEEP if source in UNFILTERED_SOURCES and label != ASK else label


def evaluate(use_llm: bool) -> str:
    out: list[str] = []
    rows = [(expected_label(g), *g[1:]) for g in GOLDEN]
    rule_drop: dict[int, str] = {}
    for i, (_, source, url, title) in enumerate(rows):
        decision = check_scope(title=title, url=url, source=source)
        if not decision.in_scope:
            rule_drop[i] = decision.reason

    gate_drop: dict[int, str] = {}
    if use_llm:
        survivors = [
            (str(i), title, "")
            for i, (_, source, _, title) in enumerate(rows)
            if i not in rule_drop and source not in UNFILTERED_SOURCES
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

    wrong = [i for i, g in enumerate(rows) if g[0] == KEEP and (i in rule_drop or i in gate_drop)]
    drops = [i for i, g in enumerate(rows) if g[0] == DROP]
    caught = [i for i in drops if i in rule_drop or i in gate_drop]
    missed = [i for i in drops if i not in rule_drop and i not in gate_drop]

    stage = "rules + model gate" if use_llm else "rules only"
    out.append(f"== {stage} ==")
    n_keep = sum(g[0] == KEEP for g in rows)
    out.append(f"KEEP items wrongly dropped: {len(wrong)} of {n_keep}   (must be 0)")
    for i in wrong:
        out.append(f"   !! {verdict(i)}: {rows[i][3][:90]}")
    out.append(f"DROP items caught: {len(caught)} of {len(drops)}   missed: {len(missed)}")
    for i in missed:
        out.append(f"   .. still passes: [{rows[i][1]}] {rows[i][3][:80]}")
    out.append("ASK items (not counted, look at them):")
    for i, g in enumerate(rows):
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
