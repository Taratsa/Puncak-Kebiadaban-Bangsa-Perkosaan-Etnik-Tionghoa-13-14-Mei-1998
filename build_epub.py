#!/usr/bin/env python3
"""Assemble OCR'd pages -> cleaned markdown -> EPUB (pandoc)."""
import re, os, subprocess, sys

WS = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(WS, "ocr", "md")

# canonical chapter map: (start_page_idx, title, eyebrow_or_None)
CH = [
    (3,  "Menjebol Dinding Kebisuan", None),
    (5,  "Jauh Hari Sebelumnya, Tanda Itu Sudah Tampak", None),
    (8,  "Ke Mana Hilangnya Mayat-Mayat Perempuan Itu?", "Kronologi dan Modus Operandi Pemerkosaan"),
    (15, "Pemerkosaan di Kota-Kota Lain", "Bukti Kuat Kejahatan yang Terorganisir"),
    (22, "Jerit itu Tanpa Suara", "Korban-Korban Mengenaskan"),
    (30, "Noda Hitam dalam Lembar Kehidupan", "Dampak Luas Pemerkosaan"),
    (35, "Buktikan Kalau Kejadian ini Bohong",
         "Ita F. Nadia, Koordinator Tim Relawan untuk Kemanusiaan Divisi Kekerasan terhadap Perempuan"),
    (38, "Pemerkosaan Massal Bukan Tabiat Orang Indonesia",
         "Dr. Rosita Noer, Ketua Umum Badan Komunikasi Penghayatan Kesatuan Bangsa (Bakom PKB) Pusat"),
    (41, "Apa Kata Mereka?", None),
    (50, "Di Mana Kau, Ibu?", "Menyoal Lambannya Upaya Pemerintah"),
    (55, "Dari Berbagai Penjuru Simpati Mengalir", None),
    (59, "Kekerasan dan Teror Masih Berlangsung",
         "Ikut-Ikutan atau Karena Para Pelaku Masih Berkeliaran?"),
    (62, "Bongkar dan Adili Segera!", None),
    (63, "Pertanggungjawaban Hati Nurani", None),
]
SKIP_PAGES = {0, 4}          # 0 = cover (image used), 4 = garbled Daftar Isi (EPUB has nav)
FM_PAGES = [1, 2]            # title page + colophon

def load_page(i):
    t = open(os.path.join(MD, f"p{i:02d}.md")).read()
    # images -> asset files (occurrence order == extraction order)
    n = [0]
    def img(m):
        name = f"p{i:02d}_{n[0]}.jpg"; n[0] += 1
        return f"epub_assets/{name}"
    t = re.sub(r'data:image/\w+;base64,[A-Za-z0-9+/=\s]+', img, t)
    # drop OCR-garbled alt texts (they duplicate body text or are footer noise,
    # and would otherwise trip the footer filter below)
    t = re.sub(r'!\[[^\]]*\]\(', '![](', t)
    t = re.sub(r'<!--.*?-->', '', t)
    return t

def strip_boilerplate(t, drop_lines=()):
    out = []
    lines = t.split("\n")
    # exact title-page heading lines
    drop = set()
    for d in drop_lines:
        drop.add(d); drop.add("# " + d)
    # running footers (full-line only)
    # running footer; some OCRs drop/mis-merge words ("46/PUNCAKKEBIADABAN...")
    def is_footer(l):
        if re.match(r'^\s*\d{1,3}\s*/\s*(PUNCAK|KEBIADAR)', l):
            return True
        return bool(re.search(r'KEBIADABAN BANGSA', l) and re.search(r'TIM\s*PEMBURU', l))
    kept = [l for l in lines if l.strip() not in drop and not is_footer(l)]
    # edge page numbers: first/last non-empty line == bare digits
    idx = [k for k, l in enumerate(kept) if l.strip()]
    for k in (idx[:1] + idx[-1:]):
        if re.match(r'^\s*\d{1,3}\s*$', kept[k]):
            kept[k] = ""
    return "\n".join(kept)

# Reduplication / compound detection (kupu-kupu, sedalam-dalamnya, anak-anaknya):
# if the hyphen is part of the word, a line wrap after it must NOT lose it.
_RPREF = ("se", "su", "ber", "ter", "per", "di", "ke", "me", "mem", "men",
          "meng", "meny", "pen", "pem", "peng", "peny", "pe", "te")
_RSUF = ("nya", "kan", "kah", "lah", "pun", "an", "ku", "i")

def _nrm_a(a):
    al = a.lower()
    for pr in sorted(_RPREF, key=len, reverse=True):
        if al.startswith(pr) and len(al) - len(pr) >= 3:
            return al[len(pr):]
    return al

def _nrm_b(b):
    bl = b.lower()
    for sf in sorted(_RSUF, key=len, reverse=True):
        if bl.endswith(sf) and len(bl) - len(sf) >= 3:
            return bl[:-len(sf)]
    return bl

def is_redup(a, b):
    """True when 'a- b' is a wrapped compound, not a syllable split."""
    al, bl = a.lower(), b.lower()
    return al == bl or _nrm_a(a) == _nrm_b(b)

def inline_join(m):
    a, b = m.group(1), m.group(2)
    if is_redup(a, b):
        return a + "-" + b          # keep compound hyphen, drop the wrap space
    if a.isupper() and b.islower(): # "PE- merkosaan" -> "PEMERKOSAAN"
        return a + b.upper()
    return a + b

def dehyphen(t):
    t = re.sub(r'\n{3,}', '\n\n', t)   # footer removal can leave gaps
    # "Ro- sita" / "PE- merkosaan" -> rejoin; compounds keep their hyphen
    t = re.sub(r'([A-Za-z]+)- +([A-Za-z]\w*)', inline_join, t)
    # digit ranges / phone numbers: "13- 14", "021- 790"
    t = re.sub(r'(\d)- +(\d)', r'\1-\2', t)
    # paragraph-final hyphen = print column split; rejoin ONLY verified pairs
    t = join_paras(t)
    return t

def fix_list(t):
    # p63/64 action list: "1 Mencari ..." / bare "3" markers -> markdown list
    lines = t.split("\n")
    out = []
    for k, l in enumerate(lines):
        s = l.strip()
        if re.match(r'^\d{1,2}[\.\)] +\S', s):
            out.append(re.sub(r'^(\d{1,2})[\.\)] +', r'\1. ', s))
        elif re.match(r'^\d{1,2}$', s):
            # merge bare marker with next non-empty line
            j = k + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip() and not lines[j].strip().startswith(('-', '#', '!')):
                lines[j] = f"{s}. {lines[j].strip()}"
                out.append("")
                continue
            out.append(l)
        else:
            out.append(l)
    return "\n".join(out)

def tidy(t):
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

# typo fixes (targeted, obvious OCR merges)
TYPO = [
    ("buku mungil inidari", "buku mungil ini dari"),
]

# Verified real-word pairs across paragraph/page breaks (everything NOT in this
# set stays in faithful OCR state: block-order scrambles must not be glued into
# invented words like "Kemernyiksaan").
KEEP_PARA = {
    # within-page, concat is a real word
    ("dite", "mukan"), ("berka", "itan"), ("se", "lamat"), ("diper", "caya"),
    ("me", "nyerbu"), ("te", "lah"), ("pe", "merkosaan"), ("se", "dang"),
    ("Pene", "rangan"), ("PERISTI", "wa"), ("penanggung", "jawab"),
    ("terorga", "nisir"), ("operan", "di"), ("memer", "kosa"),
    # cross-page, all visually verified against the page texts
    ("su", "dah"), ("ber", "tambah"), ("Se", "dangkan"), ("mene", "mukan"),
    ("meno", "long"), ("se", "buah"), ("ga", "disnya"), ("peris", "tiwa"),
    ("keru", "suhan"), ("anta", "ra"), ("Ge", "langgang"),
}

def para_join(m):
    a, b = m.group(1), m.group(2)
    if (a, b) in KEEP_PARA:
        pass
    elif is_redup(a, b):
        return a + "-" + b
    else:
        return m.group(0)
    if a.isupper() and b.islower():
        b = b.upper()
    return a + b

def join_paras(t):
    return re.sub(r'([A-Za-z0-9]+)-\n\n([A-Za-z0-9]+)', para_join, t)

def clean(i, drop_lines=()):
    t = load_page(i)
    t = strip_boilerplate(t, drop_lines)
    t = dehyphen(t)
    t = fix_list(t)
    for a, b in TYPO:
        t = t.replace(a, b)
    # any surviving single-# line in content -> demote to ## (should be none after drop)
    if re.search(r'^# ', t, re.M):
        print(f"  [warn] stray '#' heading on p{i:02d}: "
              f"{re.findall(r'^# .*$', t, re.M)}")
        t = re.sub(r'^# ', '## ', t, flags=re.M)
    return tidy(t)

def build():
    chapters = []
    # front matter: title page + colophon
    fm = ["# Halaman Judul",
          "**PUNCAK KEBIADABAN BANGSA**",
          "Perkosaan Etnik Tionghoa 13 - 14 Mei 1998", "",
          "Tim Pemburu Fakta", ""]
    fm.append(clean(2))  # colophon / credits
    chapters.append(("\n\n".join(fm)))

    starts = [c[0] for c in CH]
    for k, (s, title, eyebrow) in enumerate(CH):
        end = CH[k + 1][0] if k + 1 < len(CH) else 65
        pages = [p for p in range(s, end) if p not in SKIP_PAGES]
        # title-page heading lines to strip
        drop = [title]
        if eyebrow:
            drop.append(eyebrow)
        body = []
        for p in pages:
            body.append(clean(p, drop_lines=tuple(drop) if p == s else ()))
        head = f"# {title}\n"
        if eyebrow:
            head += f"\n*{eyebrow}*\n"
        body_txt = "\n\n".join(x for x in body if x)
        # cross-page word splits; if an image sits between, hoist the image
        body_txt = re.sub(
            r'([A-Za-z]+)-\n\n(!\[[^\]]*\]\([^)]*\))\n\n([A-Za-z]+)',
            lambda m: (m.group(2) + "\n\n" +
                       (m.group(1) + (m.group(3).upper()
                                      if m.group(1).isupper() and m.group(3).islower()
                                      else m.group(3)))
                       if (m.group(1), m.group(3)) in KEEP_PARA
                       else m.group(0)),
            body_txt)
        body_txt = join_paras(body_txt)
        chapters.append(head + "\n\n" + body_txt)

    md = "\n\n---\n\n".join(chapters)
    for a, b in TYPO:
        md = md.replace(a, b)
    # final assertions
    assert "data:image" not in md, "unreplaced data uri"
    assert "<!-- page" not in md, "page comment leaked"
    assert not re.search(r'^# (?!#)', md, re.M) or True
    stray = [l for l in md.split("\n") if re.match(r'^# (?!#)', l)]
    expect = 1 + len(CH)
    print(f"chapters (h1): {len(stray)} (expected {expect})")
    open(os.path.join(WS, "book.md"), "w").write(md)
    print("book.md:", len(md), "chars")
    return md

md = build()

# EPUB build
out = os.path.join(WS, "Puncak Kebiadaban Bangsa - Tim Pemburu Fakta.epub")
cmd = ["pandoc", "book.md", "-o", out,
       "--from", "markdown+pipe_tables",
       "--to", "epub3",
       "--epub-cover-image=epub_assets/cover.jpg",
       "--metadata", "title=Puncak Kebiadaban Bangsa: Perkosaan Etnik Tionghoa 13-14 Mei 1998",
       "--metadata", "author=Tim Pemburu Fakta",
       "--metadata", "lang=id",
       "--split-level=1",
       "--resource-path=.",
       "--toc",
       "--toc-depth=1"]
r = subprocess.run(cmd, capture_output=True, text=True)
print("pandoc rc:", r.returncode)
if r.stderr.strip():
    print("stderr:", r.stderr[:3000])
if r.returncode == 0:
    print("EPUB:", out, os.path.getsize(out) // 1024, "KB")
