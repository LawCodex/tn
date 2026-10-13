#!/usr/bin/env python3
"""Convert archived legislation.tn pages / code PDFs (see tn_fetch.py) to LawCodex Markdown.

Usage: python tn_convert.py RAW_DIR OUT_REPO_DIR
"""
import collections
import datetime
import html as htmlmod
import json
import os
import re
import sys

from lxml import html as LH

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tn_text  # noqa: E402

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()
LOG = open(os.path.join(RAW, "convert.log"), "w", encoding="utf-8")

AR_HEAD = [(r"^(الكتاب|الجزء)\s", 2), (r"^(العنوان|الباب)\s", 3), (r"^القسم\s", 4), (r"^(الفرع|الجزء الفرعي)\s", 5)]
FR_HEAD = [(r"^(LIVRE|Livre|PARTIE|Partie)\s", 2), (r"^(TITRE|Titre)\s", 3), (r"^(CHAPITRE|Chapitre)\s", 4),
           (r"^(Section|SECTION)\s", 5), (r"^(Sous-section|SOUS-SECTION)\s", 6)]
AR_ART = re.compile(r"^((?:ال)?فص[ـ]*ل\s*(?:\d+[\s\-]*(?:مكرر|ثالثا|رابعا|جديد)?|وحي[ـ]*د|[ء-ي]+)|(?:ال)?فصل\s+(?:\d+))\s*(?:[\-–ـ:\.]+\s*|\s+)(.*)$")
FR_ART = re.compile(r"^((?:Article|Art\.)\s*(?:premier|unique|\d+(?:\s*(?:bis|ter|quater|nouveau|\(nouveau\)))?(?:er)?))\s*[\.:\-–—]*\s*(.*)$")


def yq(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def heading_level(line, lang):
    if len(line) > 120:
        return None
    for rx, lvl in (AR_HEAD if lang == "ar" else FR_HEAD):
        if re.match(rx, line):
            return lvl
    return None


def to_md(lines, lang, reflow=False):
    out, para = [], []

    def flush():
        if para:
            out.append(" ".join(para).strip())
            out.append("")
            para.clear()

    for raw in lines:
        s = raw.strip()
        if not s or s == "\f" or re.match(r"^[\-–\s]*\d{1,4}[\-–\s]*$", s):
            if not reflow or not s:
                flush()
            continue
        lvl = heading_level(s, lang)
        if lvl:
            flush()
            out.append("#" * lvl + " " + s.replace("#", ""))
            out.append("")
            continue
        m = (AR_ART if lang == "ar" else FR_ART).match(s)
        if m and len(m.group(1)) < 40:
            flush()
            out.append("###### " + re.sub(r"ـ+", "", m.group(1)).strip())
            out.append("")
            if m.group(2).strip():
                para.append(m.group(2).strip())
            continue
        if reflow:
            if para and (re.search(r"[\.:؛;!؟\?]$", para[-1]) or re.match(r"^[\-–•\*]|^\d+[\.\)\-]\s", s)):
                flush()
            para.append(s)
        else:
            para.append(s)
            flush()
    flush()
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def tab_lines(doc, tab):
    divs = doc.xpath('//div[@id="%s"]//div[contains(@class,"tab-containt")]' % tab)
    if not divs:
        return []
    d = divs[0]
    for br in d.iter("br"):
        br.tail = "\n" + (br.tail or "")
    for p in d.iter("p", "div", "tr", "li"):
        p.tail = "\n" + (p.tail or "")
    txt = d.text_content()
    return [tn_text.clean_line(x) for x in txt.split("\n")]


def detail(path):
    raw = open(path, "rb").read().decode("utf-8", "replace")
    doc = LH.fromstring(raw)
    meta = {}
    for li in doc.xpath('//div[contains(@class,"list")]//li'):
        sp = li.xpath("./span")
        if sp:
            k = sp[0].text_content().strip().rstrip(":").strip()
            meta[k] = li.text_content().replace(sp[0].text_content(), "").strip()
    h1 = doc.xpath('//div[@class="detail-txt-content"]/h1')
    title = h1[0].text_content().strip() if h1 else ""
    pdfs = doc.xpath('//a[contains(@class,"link_pdf")]/@href')
    return meta, title, tab_lines(doc, "tabs_AR"), tab_lines(doc, "tabs_FR"), pdfs


def main():
    man = {}
    for line in open(os.path.join(RAW, "manifest.jsonl"), encoding="utf-8"):
        d = json.loads(line)
        if d.get("file"):
            man[d["key"]] = d
    counts = collections.Counter()
    for k, d in sorted(man.items()):
        path = os.path.join(RAW, "dl", d["file"])
        if d["tag"] == "code":
            convert_code(d, path, counts)
            continue
        meta, title, ar, fr, pdfs = detail(path)
        nature = meta.get("طبيعة النص") or meta.get("Nature du texte") or ""
        year = meta.get("سنة النص") or meta.get("Année du texte") or ""
        num = (meta.get("النص عدد") or meta.get("Numéro du texte") or "").lstrip("0") or "0"
        date = meta.get("تاريخ النص") or meta.get("Date du texte") or ""
        jo = "%s / %s (%s)" % (meta.get("عدد الرائد") or meta.get("Numéro du JORT") or "",
                               meta.get("سنة الرائد") or meta.get("Année du JORT") or "",
                               meta.get("تاريخ الرائد") or meta.get("Date du JORT") or "")
        dm = re.match(r"(\d{4})/(\d{2})/(\d{2})", date)
        iso = "%s-%s-%s" % dm.groups() if dm else None
        if not year.isdigit():
            print("NOMETA", k, file=LOG)
            continue
        is_dl = d["tag"] == "decret-loi" or "مرسوم" in nature
        texts = {"ar": [x for x in ar if x], "fr": [x for x in fr if x]}
        wrote = False
        for lang, lines in texts.items():
            body = "\n".join(lines)
            if len(lines) < 2 or "غير متوفرة" in body[:200] or "non disponibles" in body[:200] or len(body) < 80:
                continue
            first = lines[0]
            organic = bool(re.search(r"قانون أساسي|loi organique", first + " " + title, re.I))
            typ = "decree_law" if is_dl else ("organic_law" if organic else "law")
            sub = {"decree_law": ("decree-laws", "decrets-lois", "decret-loi" if lang == "fr" else "decree-law"),
                   "organic_law": ("organic-laws", "lois-organiques", "loi-organique" if lang == "fr" else "organic-law"),
                   "law": ("laws", "lois", "loi" if lang == "fr" else "law")}[typ]
            dirn = sub[0] if lang == "ar" else sub[1]
            fn = os.path.join(OUT, lang, dirn, year, "%s-%s-%s.md" % (sub[2], year, num))
            ttl = re.sub(r"\(\d\)\.?$", "", first).strip() if lang == "fr" else re.sub(r"\(\d\)\.?$", "", title or first).strip()
            ident = ("Loi n° %s-%s" % (year, num)) if lang == "fr" else ("%s عدد %s لسنة %s" % ("قانون أساسي" if organic else (nature or "قانون"), num, year))
            if organic and lang == "fr":
                ident = "Loi organique n° %s-%s" % (year, num)
            if typ == "decree_law" and lang == "fr":
                ident = "Décret-loi n° %s-%s" % (year, num)
            fm = ["---", "title: " + yq(ttl), "identifier: " + yq(ident), "type: " + typ, "jurisdiction: tn",
                  "language: " + lang]
            if iso:
                fm.append("date: " + iso)
            fm += ["status: unknown", "official_journal: " + yq("JORT " + jo), "source: " + yq(d["original"]),
                   "archived_source: " + yq(d["wayback"]),
                   "archived: %s-%s-%s" % (d["timestamp"][:4], d["timestamp"][4:6], d["timestamp"][6:8]),
                   "retrieved: " + TODAY, "---"]
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            with open(fn, "w", encoding="utf-8") as f:
                f.write("\n".join(fm) + "\n\n# " + ttl + "\n\n" + to_md(lines, lang))
            counts[(lang, typ)] += 1
            wrote = True
        if not wrote:
            print("NOTEXT", k, d["original"], file=LOG)
            counts["no_text"] += 1
    for k, v in sorted(counts.items(), key=str):
        print(k, v)


CODE_NAMES = {}


def convert_code(d, path, counts):
    name = d["original"].rsplit("/", 1)[-1][:-4]
    is_ar = name.lower().endswith("arabe") or re.search(r"arabe(-\d+)?$", name, re.I)
    base = re.sub(r"(?i)arabe(-\d+)?$", "", name)
    lang = "ar" if is_ar else "fr"
    try:
        lines = tn_text.pdf_lines(path, arabic=(lang == "ar"))
    except Exception as e:  # noqa
        print("ERR", d["key"], e, file=LOG)
        return
    if lang == "fr":
        # drop fragments of the diagonal watermark "Imprimerie Officielle de la République Tunisienne"
        wm = "imprimerieofficielledelarépubliquetunisienne"
        lines = [x for x in lines if not (x.strip() and len(x) < 70
                                         and all(t.lower().replace("’", "'") in wm for t in x.split()))]
    nonempty = [x for x in lines if x.strip() and x != "\f"]
    if len(nonempty) < 20:
        print("SKIP scanned", d["key"], file=LOG)
        counts["code_skipped"] += 1
        return
    if lang == "ar":
        ok, why = tn_text.acceptable(nonempty)
        if not ok:
            alt = tn_text.pdf_lines_poppler(path)
            alt_ne = [x for x in alt if x.strip() and x != "\f"]
            ok2, why2 = tn_text.acceptable(alt_ne)
            alt_txt = "\n".join(alt_ne)
            misordered = len(re.findall(r"\d\(|\)\d|\d\)\s*1[34]\d\d", alt_txt))
            if ok2 and misordered <= max(2, len(alt_txt) // 30000):
                lines, nonempty, ok = alt, alt_ne, True
                print("USING poppler text (pypdf: %s)" % why, d["key"], file=LOG)
            else:
                why = why + " / poppler: " + (why2 or "misordered numbers %d" % misordered)
        if not ok:
            print("SKIP quality", why, d["key"], file=LOG)
            counts["code_skipped"] += 1
            return
    else:
        fw = re.findall(r"[A-Za-zÀ-ÿ]+", "\n".join(nonempty))
        share = sum(1 for w in fw if w.lower() in ("de", "la", "le", "et", "les", "des", "du", "à", "en", "par", "au")) / max(1, len(fw))
        if share < 0.12:
            print("SKIP quality fr", d["key"], file=LOG)
            counts["code_skipped"] += 1
            return
    ti = next((i for i, x in enumerate(nonempty[:40]) if re.search(r"^(مجلة|CODE|Code)", x.strip())), None)
    if ti is None:
        ti = next((i for i, x in enumerate(nonempty[:40]) if re.search(r"مجلة|Code|CODE", x)), 0)
    parts = [nonempty[ti].strip()]
    for x in nonempty[ti + 1:ti + 4]:
        if re.match(r"^(Publications|Edition|Édition|Imprimerie|REPUBLIQUE|République|\d|Adresse|Site|Mise à jour|Textes)", x.strip()):
            break
        parts.append(x.strip())
    title = re.sub(r"\s+", " ", " ".join(parts)).strip(" ,")
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    fn = os.path.join(OUT, lang, "codes", slug + ".md")
    fm = ["---", "title: " + yq(title.strip()), "identifier: " + yq(base), "type: code", "jurisdiction: tn",
          "language: " + lang, "status: unknown", "consolidated: true", "source: " + yq(d["original"]),
          "archived_source: " + yq(d["wayback"]),
          "archived: %s-%s-%s" % (d["timestamp"][:4], d["timestamp"][4:6], d["timestamp"][6:8]),
          "retrieved: " + TODAY, "---"]
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    with open(fn, "w", encoding="utf-8") as f:
        f.write("\n".join(fm) + "\n\n# " + title.strip() + "\n\n" + to_md(lines, lang, reflow=True))
    counts[(lang, "code")] += 1


if __name__ == "__main__":
    main()
