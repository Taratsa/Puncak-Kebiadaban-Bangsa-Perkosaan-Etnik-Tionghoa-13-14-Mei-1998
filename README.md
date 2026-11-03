# Puncak Kebiadaban Bangsa — EPUB source

Source of the EPUB built from a scanned PDF (OCR via TurboOCR).

Source: https://langka.logosid.app/book/476

## Build

book.md is the hand-edited source (book.json "source": "book.md"). Edit book.md directly; do not regenerate it. The build only runs pandoc on book.md and then verifies.

    cd /Users/sf/Documents/workspaces/pdf-to-epub-turboocr
    python3 pipeline.py "<path to this folder>" --steps build,verify

Do not run the ocr or images steps for this book: book.md is not regenerated from the OCR pages in this mode.

Config (chapters, typo_fixes, keep_joins, verify rules) lives in book.json.

## Outputs

- book.md: cleaned Markdown, hand-edited source (edit directly)
- Puncak Kebiadaban Bangsa - Tim Pemburu Fakta.epub: final EPUB
- verify.json: PASS/FAIL checks
- review.txt: hyphen-join report (23 unjoined breaks still open)

## Notes

- The source PDF (137 MB) and ocr/ are not in the repo: the PDF exceeds GitHub's 100 MB limit, and ocr/ can be regenerated from it.
- Spell checking: tools/ocrcheck (symspell_rs + FrequencyWords id_full.txt 2018). Review flags by hand; names and formal terms are flagged falsely.

## Edition

The EPUB is built in the MasasilaM edition style (book.json "finish"): title page, colophon,
nested TOC, poem and figure markup. Layout and stylesheet follow MasasilaM's
*Menyambut Kongres Kebudayaan* (https://masasilam.com, CC0 1.0). Manual corrections to the
chapters "Apa Kata Mereka?" through "Pertanggungjawaban Hati Nurani" are by MasasilaM.
Validate with `epubcheck`.
