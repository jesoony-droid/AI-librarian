import fitz, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
doc = fitz.open("AI사서응답시스템_개발보고서.pdf")
page = doc[0]

print("=== 1페이지 흰색 도형 전체 ===")
for d in page.get_drawings():
    fill = d.get("fill")
    color = d.get("color")
    rect = d.get("rect")
    if fill and fill == (1.0, 1.0, 1.0):
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        print(f"  WHITE fill  w={w:.1f} h={h:.1f}  rect={[round(x,1) for x in rect]}")
    elif color and color == (1.0, 1.0, 1.0):
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        print(f"  WHITE stroke w={w:.1f} h={h:.1f}  rect={[round(x,1) for x in rect]}")
