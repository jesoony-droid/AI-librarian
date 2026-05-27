import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

html_path = pathlib.Path("보고서_source.html").resolve()
pdf_path  = pathlib.Path("AI사서응답시스템_개발보고서.pdf").resolve()

print(f"변환 중: {html_path}")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file:///{html_path}", wait_until="networkidle")
    page.pdf(
        path=str(pdf_path),
        format="A4",
        print_background=True,
        display_header_footer=False,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )
    browser.close()

print(f"완료: {pdf_path}")
