# Tunisia (TN) — legislation as Markdown

Part of [LawCodex](https://github.com/LawCodex): the legislation of every country as plain Markdown in git.

Tunisian laws, organic laws and decree-laws in **Arabic** (`ar/`) and **French** (`fr/`), and the
consolidated codes in French, from the official legislation portal of the Presidency of the Government,
**www.legislation.tn** («بوابة التشريع» / Portail de la législation), via Internet Archive captures.

**Total: 1,157 files** (retrieved 2026-10-13).

| Directory | Files | Years |
|---|---|---|
| `ar/laws/<year>/` | 460 | 2000–2019 |
| `ar/organic-laws/<year>/` | 67 | 2001–2019 |
| `ar/decree-laws/<year>/` | 64 | 2005–2020 |
| `fr/lois/<year>/` | 418 | 2000–2019 |
| `fr/lois-organiques/<year>/` | 55 | 2001–2019 |
| `fr/decrets-lois/<year>/` | 62 | 2005–2020 |
| `fr/codes/` | 31 | consolidated editions of the Imprimerie Officielle (captured 2019–2021) |

## Structure

```
ar/laws/2016/law-2016-10.md          قانون عدد 10 لسنة 2016
fr/lois/2016/loi-2016-10.md          Loi n° 2016-10
ar/organic-laws/…, fr/lois-organiques/… (قانون أساسي / loi organique)
ar/decree-laws/…, fr/decrets-lois/…   (مرسوم / décret-loi)
fr/codes/<name>.md                   e.g. penal.md (Code pénal), coc.md (Code des obligations et des contrats)
```

Headings: العنوان/الباب, القسم, الفرع / Titre, Chapitre, Section; articles (الفصل / Article) `######`.
Front matter: `date` (date of the text), `official_journal` (JORT number / year / date), `source` (the
legislation.tn page), `archived_source` and `archived` (the Wayback capture used), `status: unknown`.
Laws are the texts as published in the JORT (not consolidated); codes are the consolidated editions
("édition revue et corrigée") published by the Imprimerie Officielle de la République Tunisienne.

The Arabic and French texts are both published in the *Journal Officiel de la République Tunisienne*;
Arabic is the official language (the French edition is published for information).

## Sources and method

www.legislation.tn has answered "503 Service temporarily unavailable" since about 2021–2022 (still the case
on the retrieval date). Its pages and files were therefore taken from the **Internet Archive**
(captures 2013–2021): `scripts/tn_fetch.py` lists captures of `detailtexte/Loi-num-…` and
`detailtexte/Décret-loi-…` pages (grouped by the text identifier, e.g. `__2016014000101`) and of
`sites/default/files/codes/*.pdf`, and downloads the most recent complete capture of each.
`scripts/tn_convert.py` extracts the Arabic and French full-text tabs of each page and converts the code
PDFs (removing the diagonal "Imprimerie Officielle" watermark fragments).

## Not covered / known gaps

* **Constitution**: the 2022 Constitution is published by the Presidency (carthage.tn) only as page images
  and by the Assembly (arp.tn) as a scanned PDF; the 2014 Constitution on legislation.tn is superseded.
  No text was published rather than OCR'ing scans.
* **Texts without full text**: for laws before 2000 the portal pages contain only metadata (title, JORT
  reference, links to scanned JORT PDFs); 1,244 such pages were skipped.
* **After 2020**: laws and decree-laws adopted after the portal went offline (including the 2021–2023
  decree-laws) are not covered. The JORT site (iort.gov.tn) is a session-based application and was not crawled.
* **Arabic codes**: the Arabic code PDFs use fonts without a usable Unicode mapping (glyph names, broken
  letters); all 33 were skipped. The French codes are published.
* Coverage is limited to what the Internet Archive captured (about 1,100 distinct laws/decree-laws).
* Decrees, arrêtés and circulars are out of scope.

## Licence

Official texts are excluded from copyright protection in Tunisia (Loi n° 94-36 du 24 février 1994 relative à la
propriété littéraire et artistique, art. 7: official texts of a legislative, administrative or judicial
nature). The Markdown conversion is published under CC0.

## Regenerate

```
python scripts/tn_fetch.py ../_raw/tn       # Wayback CDX + downloads (resumable; THREADS env, default 4)
python scripts/tn_convert.py ../_raw/tn .
```
Requires Python 3 with `requests`, `lxml`, `pypdf`, and poppler-utils (`pdftotext`).
