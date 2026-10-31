# Puncak Kebiadaban Bangsa — EPUB source

Source of the EPUB built from a scanned PDF (OCR via TurboOCR).

Source: https://langka.logosid.app/book/476

## Build

Do not run any other build script. The pipeline is the only supported path.

    cd /Users/sf/Documents/workspaces/pdf-to-epub-turboocr
    python3 pipeline.py "<path to this folder>" --steps images,build,verify

Config (chapters, typo_fixes, keep_joins, verify rules) lives in book.json.

## Outputs

- book.md: cleaned Markdown (generated, do not hand-edit; put fixes in book.json)
- Puncak Kebiadaban Bangsa - Tim Pemburu Fakta.epub: final EPUB
- verify.json: PASS/FAIL checks
- review.txt: hyphen-join report (23 unjoined breaks still open)

## Notes

- The source PDF (137 MB) and ocr/ are not in the repo: the PDF exceeds GitHub's 100 MB limit, and ocr/ can be regenerated from it.
- Spell checking: tools/ocrcheck (symspell_rs + FrequencyWords id_full.txt 2018). Review flags by hand; names and formal terms are flagged falsely.
