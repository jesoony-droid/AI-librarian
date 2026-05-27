"""AI 사서 응답시스템 개발 보고서 — 전면 재설계"""
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os

FONT_R  = "C:/Windows/Fonts/malgun.ttf"
FONT_B  = "C:/Windows/Fonts/malgunbd.ttf"
OUTPUT  = "AI사서응답시스템_개발보고서.pdf"

BLUE   = (30,  90, 160)
DARK   = (25,  25,  40)
GRAY   = (110, 110, 120)
LGRAY  = (246, 247, 252)
MGRAY  = (218, 224, 238)
WHITE  = (255, 255, 255)
GREEN  = (35,  145,  70)
RED    = (195,  55,  55)
ACCENT = (218, 232, 255)
ORANGE = (185,  85,  15)   # 단점 바 색상
LNEED  = (228, 240, 255)   # 필요성 배경
LCON   = (255, 243, 218)   # 단점 배경


# ═══════════════════════════════════════════════════════════
class PDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.add_font("MG", "",  FONT_R)
        self.add_font("MG", "B", FONT_B)
        self.set_auto_page_break(True, margin=20)

    # ── 헤더 / 푸터 ─────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("MG", "", 7.5)
        self.set_text_color(*GRAY)
        self.cell(0, 6, "AI 사서 응답시스템 개발 보고서", align="L")
        self.cell(0, 6, str(self.page_no()), align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*MGRAY)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(),
                  self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_draw_color(*MGRAY)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(),
                  self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_font("MG", "", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 5,
            "국립중앙도서관 Q&A 기반 RAG 시스템  |  문헌정보학과 대학원  |  디지털도서관특강",
            align="C")

    # ── 타이포그래피 ────────────────────────────────────
    def sec(self, txt):
        """섹션 헤딩 (h1): 파란 배경, 흰 글자"""
        self.ln(2)
        self.set_fill_color(*BLUE)
        self.set_text_color(*WHITE)
        self.set_font("MG", "B", 12)
        self.cell(0, 9, f"  {txt}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)
        self.set_text_color(*DARK)

    def sub(self, txt):
        """소제목 (h2): 파란 왼쪽 강조선"""
        self.ln(3)
        x, y = self.l_margin, self.get_y()
        self.set_fill_color(*BLUE)
        self.rect(x, y + 1.5, 3, 6, "F")
        self.set_font("MG", "B", 10.5)
        self.set_text_color(*BLUE)
        self.set_xy(x + 6, y)
        self.cell(0, 9, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*DARK)
        self.ln(1)

    def body(self, txt, indent=0):
        self.set_font("MG", "", 10)
        self.set_text_color(*DARK)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 6.5, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def bul(self, txt, level=0):
        indent = 4 + level * 6
        self.set_font("MG", "", 10)
        self.set_text_color(*DARK)
        self.set_x(self.l_margin + indent)
        self.cell(5, 6.5, "•" if level == 0 else "-")
        self.multi_cell(0, 6.5, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _count_lines(self, txt: str, width: float, fs: int) -> int:
        """주어진 너비에 텍스트가 몇 줄 필요한지 계산."""
        self.set_font("MG", "", fs)
        words = str(txt).split()
        if not words:
            return 1
        lines, cur = 1, 0.0
        for w in words:
            ww = self.get_string_width(w + " ")
            if cur + ww > width - 4 and cur > 0:
                lines += 1
                cur = ww
            else:
                cur += ww
        return lines

    def tbl(self, headers, rows, widths=None, fs=9):
        W = self.w - self.l_margin - self.r_margin
        if not widths:
            widths = [W / len(headers)] * len(headers)
        LH  = fs * 0.42 + 1.5   # 줄 높이 (mm)
        PAD = 2.2                # 셀 위아래 여백

        # 전체 표 높이 추정 — 한 페이지에 들어갈 수 있는데 현재 페이지에 안 맞으면 새 페이지
        est_row_h = LH + PAD * 2
        total_h = 8 + est_row_h * len(rows)
        fresh_h = self.h - self.t_margin - self.b_margin - 15
        remaining = self.h - self.b_margin - self.get_y()
        if total_h <= fresh_h and remaining < total_h:
            self.add_page()

        # ── 헤더 ──────────────────────────────────────
        self.set_fill_color(*BLUE)
        self.set_text_color(*WHITE)
        self.set_font("MG", "B", fs)
        for h, cw in zip(headers, widths):
            self.cell(cw, 8, f"  {h}", fill=True)
        self.ln()

        # ── 데이터 행 ──────────────────────────────────
        for ri, row in enumerate(rows):
            # 행 높이: 가장 많은 줄이 필요한 셀 기준
            row_h = LH + PAD * 2
            for txt, cw in zip(row, widths):
                n = self._count_lines(f"  {txt}", cw, fs)
                row_h = max(row_h, n * LH + PAD * 2)

            # 페이지 경계 처리
            if self.get_y() + row_h > self.h - self.b_margin:
                self.add_page()

            x0, y0 = self.l_margin, self.get_y()
            fill = LGRAY if ri % 2 == 0 else WHITE
            self.set_font("MG", "", fs)
            self.set_text_color(*DARK)

            x = x0
            for txt, cw in zip(row, widths):
                # 배경 사각형
                self.set_fill_color(*fill)
                self.rect(x, y0, cw, row_h, "F")
                # 텍스트 (multi_cell로 자동 줄바꿈)
                self.set_xy(x, y0 + PAD)
                self.multi_cell(
                    cw, LH, f"  {txt}",
                    fill=False, align="L",
                    new_x=XPos.RIGHT, new_y=YPos.TOP,
                )
                x += cw

            self.set_xy(x0, y0 + row_h)
        self.ln(4)

    def note_box(self, label, text, bar_col, bg_col):
        """컬러 배지 + 내용 한 줄 박스 (필요성/단점용)."""
        x0  = self.l_margin + 3
        W   = self.w - x0 - self.r_margin
        LH  = 5.3
        PAD = 2.2
        LBW = 22   # 라벨 열 너비

        n     = self._count_lines(text, W - LBW - 8, 9)
        row_h = max(LH + PAD * 2, n * LH + PAD * 2)

        if self.get_y() + row_h > self.h - self.b_margin:
            self.add_page()

        y0 = self.get_y()
        self.set_fill_color(*bg_col)
        self.rect(x0, y0, W, row_h, "F")
        self.set_fill_color(*bar_col)
        self.rect(x0, y0, 3, row_h, "F")

        # 라벨 (세로 중앙)
        cy = y0 + (row_h - LH) / 2
        self.set_font("MG", "B", 8.5)
        self.set_text_color(*bar_col)
        self.set_xy(x0 + 6, cy)
        self.cell(LBW, LH, label)

        # 본문
        self.set_font("MG", "", 9)
        self.set_text_color(*DARK)
        self.set_xy(x0 + LBW + 7, y0 + PAD)
        self.multi_cell(W - LBW - 9, LH, text, fill=False, align="L",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_xy(self.l_margin, y0 + row_h)
        self.ln(1)

    def need_con(self, need_text, con_text):
        """필요성(파랑) + 단점(주황) 박스 쌍."""
        self.ln(1)
        self.note_box("필요성", need_text, BLUE,   LNEED)
        self.note_box("단점",   con_text,  ORANGE, LCON)
        self.ln(2)

    def lesson_bul(self, title, body):
        """교훈 항목: 파란 왼쪽 바 + 굵은 제목 + 본문."""
        x0 = self.l_margin
        W  = self.w - x0 - self.r_margin
        self.ln(2)
        y0 = self.get_y()

        # 제목
        self.set_font("MG", "B", 10.5)
        self.set_text_color(*BLUE)
        self.set_xy(x0 + 7, y0)
        self.multi_cell(W - 7, 7.5, title, fill=False,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        y1 = self.get_y()
        # 제목 높이만큼 왼쪽 파란 바
        self.set_fill_color(*BLUE)
        self.rect(x0, y0, 3, y1 - y0, "F")

        # 구분선
        self.set_draw_color(*MGRAY)
        self.set_line_width(0.25)
        self.line(x0 + 7, y1, x0 + W, y1)
        self.ln(1.5)

        # 본문
        self.set_font("MG", "", 10)
        self.set_text_color(*DARK)
        self.set_x(x0 + 7)
        self.multi_cell(W - 7, 6.2, body,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def callout(self, title, lines, color=ACCENT):
        """파란 왼쪽 바를 행별로 즉시 그려 페이지 경계 오류 방지."""
        self.ln(2)
        x, w = self.l_margin, self.w - self.l_margin - self.r_margin

        def _row(h, txt="", bold=False, txt_color=DARK):
            y1 = self.get_y()
            self.set_fill_color(*color)
            self.set_font("MG", "B" if bold else "", 9.5)
            self.set_text_color(*txt_color)
            self.set_x(x)
            if txt:
                self.multi_cell(w, h, txt, fill=True,
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                self.cell(w, h, "", fill=True,
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            y2 = self.get_y()
            # 페이지 경계를 넘지 않은 경우에만 파란 바 그리기
            if y2 > y1:
                self.set_fill_color(*BLUE)
                self.rect(x, y1, 3, y2 - y1, "F")

        _row(8, "      " + title, bold=True, txt_color=BLUE)
        for ln in lines:
            _row(6, "        " + ln) if ln else _row(2.5)
        _row(3)
        self.ln(4)


# ═══════════════════════════════════════════════════════════
#  표지 (1 페이지)
# ═══════════════════════════════════════════════════════════
def cover(pdf):
    pdf.add_page()
    W, L = 210, 18
    TW = W - L * 2  # 174 mm

    # ── 헤더 ──────────────────────────────────────────
    pdf.set_fill_color(*BLUE)
    pdf.rect(0, 0, W, 60, "F")

    pdf.set_font("MG", "B", 22)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(L, 11)
    pdf.cell(0, 12, "AI 사서 응답시스템 개발 보고서")

    pdf.set_font("MG", "", 9.5)
    pdf.set_xy(L, 27)
    pdf.cell(0, 7, "국립중앙도서관 Q&A 기반 RAG 시스템 구축 과정 및 운영 계획")

    pdf.set_draw_color(160, 195, 240)
    pdf.set_line_width(0.4)
    pdf.line(L, 38, W - L, 38)

    pdf.set_font("MG", "", 9)
    pdf.set_xy(L, 41)
    pdf.cell(0, 6, "문헌정보학과 대학원  |  디지털도서관특강  |  2026. 05. 18. 발표")

    # 우측 배지
    bx = W - L - 42
    pdf.set_fill_color(*WHITE)
    pdf.rect(bx, 40, 42, 14, "F")
    pdf.set_font("MG", "B", 8.5)
    pdf.set_text_color(*BLUE)
    pdf.set_xy(bx, 42)
    pdf.cell(42, 5, "RAG + Hybrid Search", align="C")
    pdf.set_font("MG", "", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(bx, 48)
    pdf.cell(42, 5, "Gemini 2.5 Flash", align="C")

    # ── 통계 카드 5개 ─────────────────────────────────
    cards = [
        ("5,907건", "수집 Q&A"),
        ("5,907건", "임베딩 완료"),
        ("99.95%",  "수집 성공률"),
        ("9건",     "해결된 오류"),
        ("0원",     "임베딩 비용"),
    ]
    CW = (TW - 4 * 3) / 5
    for i, (num, desc) in enumerate(cards):
        cx = L + i * (CW + 3)
        pdf.set_fill_color(*ACCENT)
        pdf.rect(cx, 64, CW, 22, "F")
        pdf.set_fill_color(*BLUE)
        pdf.rect(cx, 64, 2.5, 22, "F")
        pdf.set_font("MG", "B", 13)
        pdf.set_text_color(*BLUE)
        pdf.set_xy(cx + 5, 66)
        pdf.cell(CW - 5, 9, num)
        pdf.set_font("MG", "", 7.5)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(cx + 5, 76)
        pdf.cell(CW - 5, 6, desc)

    # ── 차트 두 개 ────────────────────────────────────
    CT  = 91
    DX  = L + 92      # 구분선 x

    # 왼쪽: 데이터 수집 현황 (수평 막대)
    pdf.set_font("MG", "B", 8.5)
    pdf.set_text_color(*BLUE)
    pdf.set_xy(L, CT)
    pdf.cell(0, 6, "데이터 수집 현황")
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.3)
    pdf.line(L, CT + 6, DX - 4, CT + 6)

    BARW = 50
    bar_data = [
        ("수집 대상",   5910, (175, 200, 232)),
        ("수집 완료",   5907, BLUE),
        ("임베딩 완료", 5907, GREEN),
        ("파싱 오류(제외)", 3, RED),
    ]
    by = CT + 9
    for lbl, val, col in bar_data:
        ratio = val / 5910
        pdf.set_font("MG", "", 7.5)
        pdf.set_text_color(*DARK)
        pdf.set_xy(L, by + 1)
        pdf.cell(26, 5.5, lbl)
        pdf.set_fill_color(222, 227, 240)
        pdf.rect(L + 27, by + 1.5, BARW, 4, "F")
        pdf.set_fill_color(*col)
        fw = BARW * ratio
        if fw > 0.3:
            pdf.rect(L + 27, by + 1.5, fw, 4, "F")
        pdf.set_font("MG", "B", 7)
        pdf.set_text_color(*DARK)
        pdf.set_xy(L + 27 + BARW + 2, by + 1)
        pdf.cell(0, 5.5, f"{val:,}")
        by += 9

    pdf.set_font("MG", "", 6.5)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(L, by + 1)
    pdf.cell(0, 5, "* 나머지 3건: HTML 파싱 오류로 수집 불가")

    # 오른쪽: 검색 방식 비중 (분할 막대 + 표)
    RX = DX + 3
    RW = W - L - RX

    pdf.set_font("MG", "B", 8.5)
    pdf.set_text_color(*BLUE)
    pdf.set_xy(RX, CT)
    pdf.cell(0, 6, "검색 방식 비중 (RRF 하이브리드)")
    pdf.set_draw_color(*BLUE)
    pdf.line(RX, CT + 6, W - L, CT + 6)

    SBY = CT + 9
    SBH = 14
    W35 = RW * 0.35
    W65 = RW * 0.65

    pdf.set_fill_color(95, 148, 218)
    pdf.rect(RX, SBY, W35, SBH, "F")
    pdf.set_font("MG", "B", 7.5)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(RX + 1, SBY + 1)
    pdf.cell(W35 - 2, 5.5, "BM25 키워드", align="C")
    pdf.set_font("MG", "B", 10)
    pdf.set_xy(RX + 1, SBY + 6.5)
    pdf.cell(W35 - 2, 7, "35%", align="C")

    pdf.set_fill_color(*BLUE)
    pdf.rect(RX + W35, SBY, W65, SBH, "F")
    pdf.set_font("MG", "B", 7.5)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(RX + W35 + 1, SBY + 1)
    pdf.cell(W65 - 2, 5.5, "벡터 유사도 검색", align="C")
    pdf.set_font("MG", "B", 10)
    pdf.set_xy(RX + W35 + 1, SBY + 6.5)
    pdf.cell(W65 - 2, 7, "65%", align="C")

    # 가중치 유형 미니 테이블
    TY = SBY + SBH + 4
    t_hs  = ["쿼리 유형", "BM25", "벡터"]
    t_cws = [RW - 28, 14, 14]
    t_rows = [
        ["기본 (일반 질문)", "35%", "65%"],
        ["주제 탐색형",      "20%", "80%"],
        ["고유명사/ISBN",    "70%", "30%"],
    ]
    tx = RX
    pdf.set_fill_color(*BLUE)
    pdf.set_font("MG", "B", 7)
    pdf.set_text_color(*WHITE)
    for h, cw in zip(t_hs, t_cws):
        pdf.set_xy(tx, TY); pdf.cell(cw, 6, " " + h, fill=True); tx += cw
    TY += 6
    for ri, row in enumerate(t_rows):
        tx = RX
        pdf.set_fill_color(*LGRAY) if ri % 2 == 0 else pdf.set_fill_color(*WHITE)
        pdf.set_font("MG", "", 7)
        pdf.set_text_color(*DARK)
        for txt, cw in zip(row, t_cws):
            pdf.set_xy(tx, TY); pdf.cell(cw, 5.5, " " + txt, fill=True); tx += cw
        TY += 5.5

    # ── 개발 단계 타임라인 ────────────────────────────
    TLY = 144
    pdf.set_font("MG", "B", 8.5)
    pdf.set_text_color(*BLUE)
    pdf.set_xy(L, TLY)
    pdf.cell(0, 6, "개발 단계 타임라인")
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.3)
    pdf.line(L, TLY + 6, W - L, TLY + 6)

    phases = [
        ("Phase 1", "기획/설계",  (158, 184, 230)),
        ("Phase 2", "데이터수집", (108, 148, 212)),
        ("Phase 3", "DB/임베딩",  (62,  116, 192)),
        ("Phase 4", "검색구현",   (35,   90, 172)),
        ("Phase 5", "API/UI",     (20,   68, 152)),
        ("Phase 6", "Gemini통합", (10,   48, 130)),
    ]
    PHW, PHH, PHG = 26, 20, 3.2
    phx, phy = L, TLY + 9
    for i, (pnum, pname, col) in enumerate(phases):
        r2, g2, b2 = col
        pdf.set_fill_color(*col)
        pdf.rect(phx, phy, PHW, PHH, "F")
        pdf.set_fill_color(min(r2+50,255), min(g2+50,255), min(b2+50,255))
        pdf.rect(phx, phy, PHW, 5, "F")
        pdf.set_font("MG", "B", 6.5)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(phx, phy); pdf.cell(PHW, 5, pnum, align="C")
        pdf.set_font("MG", "", 7.5)
        pdf.set_xy(phx, phy + 8); pdf.cell(PHW, 5, pname, align="C")
        if i < 5:
            ax, ay = phx + PHW + 0.5, phy + PHH / 2
            pdf.set_draw_color(*GRAY); pdf.set_line_width(0.4)
            pdf.line(ax, ay, ax + PHG - 1, ay)
            pdf.line(ax + PHG - 1, ay, ax + PHG - 2.5, ay - 1.5)
            pdf.line(ax + PHG - 1, ay, ax + PHG - 2.5, ay + 1.5)
        phx += PHW + PHG

    # ── 최종 성과 요약 ────────────────────────────────
    SMY = 180
    pdf.set_fill_color(*BLUE)
    pdf.rect(L, SMY, TW, 8, "F")
    pdf.set_font("MG", "B", 8.5)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(L + 4, SMY)
    pdf.cell(0, 8, "최종 성과 요약")

    left_items = [
        "수집 데이터: 5,907건 (국립중앙도서관 Q&A 전체)",
        "DB: PostgreSQL + pgvector, 384차원 벡터 임베딩",
        "검색: RRF 하이브리드 (BM25 35% + 벡터 65%)",
        "AI 답변: Gemini 2.5 Flash 스트리밍 + 출처 URL 제공",
        "UI: 마크다운 렌더링 · 대기 오버레이 · 질문 히스토리",
    ]
    right_items = [
        "임베딩 비용: 0원 (로컬 무료 모델 사용)",
        "재시작: 명령어 1줄로 즉시 구동 가능",
        "무결과 시 유사 질문 3개 자동 제안",
        "외부 공개: ngrok HTTPS URL 스마트폰 시연 가능",
        "와이파이 변경 시에도 정상 동작",
    ]
    HW = TW // 2
    IY = SMY + 9
    pdf.set_fill_color(*ACCENT)
    pdf.rect(L, SMY + 8, TW, 5 * 8 + 2, "F")
    for item in left_items:
        pdf.set_fill_color(*BLUE)
        pdf.rect(L + 1, IY + 2, 2, 4.5, "F")
        pdf.set_font("MG", "", 8)
        pdf.set_text_color(*DARK)
        pdf.set_xy(L + 5, IY)
        pdf.cell(HW - 6, 7.5, item)
        IY += 8
    IY = SMY + 9
    for item in right_items:
        pdf.set_fill_color(*BLUE)
        pdf.rect(L + HW + 1, IY + 2, 2, 4.5, "F")
        pdf.set_font("MG", "", 8)
        pdf.set_text_color(*DARK)
        pdf.set_xy(L + HW + 5, IY)
        pdf.cell(HW - 7, 7.5, item)
        IY += 8

    # ── 기술 스택 태그 ────────────────────────────────
    TAG_TOP = SMY + 8 + 5 * 8 + 5
    pdf.set_font("MG", "B", 8)
    pdf.set_text_color(*DARK)
    pdf.set_xy(L, TAG_TOP)
    pdf.cell(0, 6, "기술 스택")
    tags = [
        ("Python 3.14",          (30,  90, 160)),
        ("FastAPI",               (0,  148, 100)),
        ("PostgreSQL 17",         (50, 100, 180)),
        ("pgvector",              (90,  58, 168)),
        ("Gemini 2.5 Flash",      (198, 98,   0)),
        ("google.genai SDK",      (175, 78,   0)),
        ("sentence-transformers", (48, 138,  78)),
        ("RRF 하이브리드 검색",   (30,  90, 160)),
    ]
    tx, ty = L, TAG_TOP + 8
    for tag, col in tags:
        pdf.set_font("MG", "", 7.5)
        tw = pdf.get_string_width(tag) + 7
        if tx + tw > W - L:
            tx = L; ty += 8
        pdf.set_fill_color(*col)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(tx, ty)
        pdf.cell(tw, 6.5, tag, fill=True, align="C")
        tx += tw + 3

    # ── 하단 라인 + 날짜 ──────────────────────────────
    pdf.set_draw_color(*GRAY)
    pdf.set_line_width(0.3)
    pdf.line(L, 263, W - L, 263)
    pdf.set_font("MG", "", 8)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(L, 266)
    pdf.cell(0, 5, "작성일: 2026년 5월 15일  |  발표일: 2026년 5월 18일")
    pdf.set_xy(L, 266)
    pdf.cell(0, 5, "본 보고서는 Claude Code(AI)와 협업하여 작성되었습니다.", align="R")


# ═══════════════════════════════════════════════════════════
#  본문
# ═══════════════════════════════════════════════════════════
def body(pdf):

    # ── 1. 프로젝트 개요 ─────────────────────────────────
    pdf.add_page()
    pdf.sec("1. 프로젝트 개요")

    pdf.sub("1.1 배경 및 목적")
    pdf.body(
        "국립중앙도서관은 '사서문답' 서비스를 통해 이용자 질문에 전문 사서가 직접 답변하는 "
        "Q&A 데이터를 5,900건 이상 축적하고 있습니다. 그러나 이 데이터가 검색 가능한 형태로 "
        "체계화되지 않아 이용자가 원하는 정보를 효율적으로 찾기 어려운 상황이었습니다."
    )
    pdf.body(
        "본 프로젝트는 이 Q&A 데이터를 RAG(Retrieval-Augmented Generation) 방식으로 "
        "구조화하여, 자연어 질문 입력 시 유사 Q&A를 자동 검색하고 Gemini AI가 "
        "이를 바탕으로 답변을 생성하는 AI 사서 응답시스템을 구축하는 것을 목표로 합니다."
    )

    pdf.sub("1.2 시스템 동작 흐름")
    flow = [
        ("이용자 질문 입력",    "브라우저 웹 UI"),
        ("FastAPI 서버 처리",   "/api/ask 엔드포인트"),
        ("하이브리드 검색",     "BM25(35%) + 벡터 유사도(65%) → RRF 통합"),
        ("상위 5건 컨텍스트 구성", "질문 + 답변 + 출처 URL"),
        ("Gemini 2.5 Flash 호출", "스트리밍 방식으로 실시간 답변 생성"),
        ("이용자에게 전달",     "AI 답변 + 참고 출처 URL 표시"),
    ]
    pdf.tbl(["단계", "내용"], flow, [55, 119])

    pdf.sub("1.3 기술 스택 선정 이유")
    pdf.tbl(
        ["기술", "선정 이유"],
        [
            ["PostgreSQL 17 + pgvector", "벡터 검색과 전문검색을 단일 DB로 통합 → 인프라 단순화"],
            ["paraphrase-multilingual-MiniLM", "무료 로컬 실행, 다국어(한국어) 지원, 384차원"],
            ["Gemini 2.5 Flash",         "무료 tier 제공, 한국어 고품질 응답, 스트리밍 지원"],
            ["google.genai SDK",         "기존 google.generativeai deprecated → 최신 공식 SDK"],
            ["FastAPI",                  "비동기 StreamingResponse 지원, 자동 API 문서 생성"],
            ["RRF 하이브리드 검색",       "키워드 정확도 + 의미 유사도 결합으로 검색 품질 향상"],
        ],
        [68, 106],
    )

    # ── 2. 개발 단계별 진행 과정 ─────────────────────────
    pdf.add_page()
    pdf.sec("2. 개발 단계별 진행 과정")

    pdf.sub("Phase 1 — 기획 및 설계")
    pdf.body(
        "초기에는 OpenAI GPT-4 + text-embedding-ada-002 조합을 계획하였으나 "
        "API 크레딧 부족으로 대안을 마련하였습니다. "
        "임베딩은 Hugging Face 무료 로컬 모델(sentence-transformers)로, "
        "AI 답변은 Google Gemini 무료 tier로 전환하여 전체 시스템을 비용 0원으로 설계하였습니다."
    )
    pdf.callout("핵심 설계 결정", [
        "임베딩: 유료 API 대신 로컬 sentence-transformers → 비용 0원, 인터넷 불필요",
        "검색: 키워드 단독이 아닌 BM25+벡터 하이브리드 방식 → 정확도 향상",
        "AI 답변: Gemini 무료 tier 활용 → 운영 비용 최소화",
        "DB: PostgreSQL 하나로 전문검색+벡터 검색 통합 → 인프라 단순화",
    ])

    pdf.sub("Phase 2 — 데이터 수집 (크롤링)")
    pdf.body(
        "국립중앙도서관 사서문답 서비스에서 591페이지 × 10건 = 5,910건을 수집 대상으로 "
        "설정하고 자동 크롤러를 개발하였습니다. 최종 5,907건을 수집하였으며 "
        "나머지 3건은 HTML 내 특수문자 파싱 오류로 제외되었습니다."
    )
    pdf.tbl(
        ["항목", "내용"],
        [
            ["수집 대상",   "국립중앙도서관 사서문답 서비스 (nl.go.kr)"],
            ["수집 필드",   "질문, 답변, 도서관명, 카테고리, 조회수, 출처 URL, 키(ackRecKey)"],
            ["최종 수집량", "5,907건 (99.95%)"],
            ["제외 건수",   "3건 (HTML 특수문자 파싱 불가)"],
        ],
        [35, 139],
    )

    pdf.sub("Phase 3 — DB 구축 및 임베딩")
    pdf.body(
        "PostgreSQL 17에 pgvector 확장을 설치하여 벡터 저장 및 코사인 유사도 검색 환경을 "
        "구축하였습니다. paraphrase-multilingual-MiniLM-L12-v2 모델로 각 Q&A의 질문 텍스트를 "
        "384차원 벡터로 변환하여 저장하였습니다. 5,907건 전체 임베딩 완료 후 "
        "HNSW 인덱스를 생성하여 검색 속도를 최적화하였습니다."
    )

    pdf.sub("Phase 4 — 하이브리드 검색 구현")
    pdf.body(
        "PostgreSQL 전문검색(BM25)과 pgvector 코사인 유사도 검색을 결합하고, "
        "RRF(Reciprocal Rank Fusion) 알고리즘으로 두 결과를 통합합니다. "
        "쿼리 유형을 자동 판별하여 가중치를 동적으로 조정합니다."
    )
    pdf.tbl(
        ["쿼리 유형", "BM25 비중", "벡터 비중", "판별 조건"],
        [
            ["기본 (기본값)", "35%", "65%", "기타 모든 질문"],
            ["주제 탐색형",   "20%", "80%", "'주제', '관련', '추천' 등 포함"],
            ["고유명사형",    "70%", "30%", "ISBN, 저자명, 출판사 등 포함"],
        ],
        [40, 22, 22, 90],
    )

    pdf.sub("Phase 5 — FastAPI 서버 및 웹 UI")
    pdf.body("FastAPI로 3개 엔드포인트를 구현하고 HTML 단일 파일 웹 UI를 제공합니다.")
    pdf.tbl(
        ["엔드포인트", "역할"],
        [
            ["GET  /",          "웹 UI 서빙 (frontend/index.html)"],
            ["POST /api/search","하이브리드 검색 결과 JSON 반환 (AI 없음)"],
            ["POST /api/ask",   "검색 + Gemini RAG 스트리밍 답변 생성"],
        ],
        [45, 129],
    )

    pdf.sub("Phase 6 — Gemini AI 통합")
    pdf.body(
        "처음에는 Anthropic Claude API를 계획하였으나 결제 화면 이슈로 Google Gemini API로 "
        "전환하였습니다. 전환 과정에서 코드가 Anthropic SDK와 google.generativeai 방식으로 "
        "혼재되는 문제가 발생하였으며, 이를 google.genai 최신 SDK로 완전히 재통합하였습니다. "
        "모델은 gemini-2.5-flash를 최종 채택하였습니다."
    )

    # ── 3. 오류 및 해결 ──────────────────────────────────
    pdf.add_page()
    pdf.sec("3. 발생 오류 및 해결 과정")

    pdf.body(
        "프로젝트 전 단계에 걸쳐 총 9건의 오류가 발생하였으며, 모두 해결하여 "
        "최종 시스템을 완성하였습니다."
    )
    pdf.tbl(
        ["#", "오류명", "발생 단계", "핵심 원인", "해결 방법"],
        [
            ["1", "크롤러 파라미터 오류",    "Phase 2", "pageNum → page 파라미터 혼동",   "실제 API 파라미터 page로 수정"],
            ["2", "views 필드 파싱 오류",    "Phase 2", "천단위 쉼표로 int() 변환 실패",   '.replace(",","") 전처리 추가'],
            ["3", "pgvector 설치 복잡성",    "Phase 3", "Windows 환경 빌드 과정 복잡",     "사전 빌드 파일 수동 설치"],
            ["4", "Gemini 전환 코드 혼재",   "Phase 6", "Anthropic+genai 코드 혼재",       "generate() 함수 전체 재작성"],
            ["5", "패키지 미설치",           "Phase 6", "google-generativeai 누락",        "pip install google-generativeai"],
            ["6", "SDK deprecated 경고",     "Phase 6", "google.generativeai 지원 종료",   "google.genai 최신 SDK로 전환"],
            ["7", "API 쿼터 초과 (429)",     "Phase 6", "무료 tier 일일 한도 초과",        "gemini-2.5-flash + 새 API 키 발급"],
            ["8", "구버전 서버 프로세스 잔류", "배포/테스트", "--reload 후 구버전 잔류",    "Stop-Process로 전체 종료 후 재시작"],
            ["9", "한글 인코딩 출력 오류",   "전체",    "Windows CP949/UTF-8 불일치",      "stdout.buffer.write(encode('utf-8'))"],
        ],
        [8, 44, 26, 48, 48],
        fs=8,
    )

    pdf.body("발생한 9건의 오류를 단계 순서에 따라 상세히 설명합니다.")

    pdf.callout("오류 1 — 크롤러 파라미터 오류", [
        "[문제] 국립중앙도서관 목록 API 호출 시 페이지 파라미터를 pageNum으로 설정.",
        "       실제 API는 page 파라미터를 사용하여 매 요청이 1페이지만 반복 수집됨.",
        "       5,910건 수집 시도 중 동일한 10건이 591회 반복 저장되는 오류 발생.",
        "[해결] 브라우저 개발자 도구로 실제 요청 파라미터를 확인하여 page로 수정.",
        "       수집 데이터 전체 삭제 후 재수집 진행.",
    ])

    pdf.callout("오류 2 — views 필드 파싱 오류", [
        "[문제] 조회수(views) 필드 값이 HTML에서 '1,234' 형태의 천단위 쉼표 포함 문자열로 수집됨.",
        "       int('1,234') 변환 시 ValueError 발생, 해당 건 전체 DB 적재 실패.",
        "[해결] int 변환 직전에 .replace(',', '') 전처리를 추가하여 쉼표 제거 후 변환.",
    ])

    pdf.callout("오류 3 — pgvector 설치 복잡성 (Windows 환경)", [
        "[문제] pgvector는 PostgreSQL C 확장으로, Linux는 make install로 간단하나",
        "       Windows에서는 Visual Studio Build Tools 및 PostgreSQL 개발 헤더 경로 설정 필요.",
        "       pip 패키지(pgvector)는 Python 클라이언트일 뿐, DB 서버 확장과 별개.",
        "       공식 문서대로 진행 시 nmake 빌드 오류 반복 발생.",
        "[해결] GitHub Releases에서 Windows용 사전 빌드 바이너리를 다운로드.",
        "       C:\\Temp\\pgvector_extract 에 압축 해제 후 .dll/.control 파일을 PostgreSQL",
        "       설치 디렉터리에 수동 복사하여 CREATE EXTENSION vector 성공.",
    ])

    pdf.callout("오류 4 — Gemini 전환 코드 혼재", [
        "[문제] Claude → Gemini 전환 도중 작업이 중단되어 google.generativeai import와",
        "       Anthropic SDK 스타일 호출(ai.messages.stream())이 동일 파일 내 혼재.",
        "       서버 실행 시 AttributeError 발생, /api/ask 엔드포인트 응답 불가.",
        "[해결] generate() 함수 전면 재작성.",
        "       google.genai 최신 SDK의 client.models.generate_content_stream() 방식으로 교체.",
    ])

    pdf.callout("오류 5 — 패키지 미설치", [
        "[문제] google.generativeai 임포트 시 ModuleNotFoundError 발생.",
        "       가상환경 초기 설정 시 requirements.txt에 해당 패키지가 누락된 상태.",
        "[해결] pip install google-generativeai 로 즉시 설치.",
        "       이후 requirements.txt에 추가하여 재현 방지.",
    ])

    pdf.callout("오류 6 — SDK deprecated 경고", [
        "[문제] google.generativeai 라이브러리가 공식 deprecated 처리됨.",
        "       임포트 시 DeprecationWarning 출력, 일부 신규 모델 파라미터 미지원.",
        "       기존 코드 그대로 사용 시 향후 버전에서 완전 제거될 위험.",
        "[해결] google.genai (google-genai 패키지) 최신 SDK로 전면 전환.",
        "       Client 초기화 방식 및 스트리밍 호출 구조 전체 재작성 완료.",
    ])

    pdf.callout("오류 7 — Gemini API 쿼터 초과 (429)", [
        "[문제] gemini-2.0-flash 무료 tier 일일 요청 한도 초과로 RESOURCE_EXHAUSTED 오류 발생.",
        "       새 API 키를 발급해도 동일 GCP 프로젝트 내에서는 쿼터가 공유되어 동일 오류 반복.",
        "[해결] gemini-2.5-flash 모델(별도 독립 쿼터)로 변경 + 신규 GCP 프로젝트에서 API 키 재발급.",
        "       무료 한도는 UTC 자정(KST 오전 9시)에 자동 초기화됨.",
        "       쿼터 초과 시 검색 결과를 직접 반환하는 폴백 로직도 추가 구현.",
    ])

    pdf.callout("오류 8 — 구버전 서버 프로세스 잔류 (진단 어려움)", [
        "[문제] uvicorn --reload 옵션으로 재시작 후에도 구버전 reloader 프로세스가 포트 8000 점유.",
        "       코드 수정이 전혀 반영되지 않아 /api/ask가 항상 동일 메시지(16자)만 반환.",
        "       코드·DB·임베딩 모두 정상인데 결과가 바뀌지 않아 원인 파악에 시간 소요.",
        "[해결] Get-Process python* | Stop-Process -Force 로 모든 Python 프로세스 강제 종료.",
        "       이후 uvicorn api.main:app --port 8000 (--reload 없이) 로 재시작하여 정상화.",
        "       운영 시 --reload 옵션 미사용 권장.",
    ])

    pdf.callout("오류 9 — 한글 인코딩 출력 오류", [
        "[문제] Windows 콘솔 기본 인코딩이 CP949(EUC-KR)인 환경에서",
        "       Python print()로 UTF-8 한글 문자열 출력 시 UnicodeEncodeError 발생.",
        "       크롤링 진행 로그에서 도서관명·카테고리 등 한글 정보 출력 불가.",
        "[해결] sys.stdout.buffer.write(text.encode('utf-8') + b'\\n') 방식으로 직접 바이트 출력.",
        "       또는 PYTHONIOENCODING=utf-8 환경변수 설정으로 해결.",
    ])

    # ── 4. 최종 시스템 현황 ──────────────────────────────
    pdf.add_page()
    pdf.sec("4. 최종 시스템 현황")

    pdf.sub("4.1 완성된 기능")
    pdf.tbl(
        ["기능", "상태", "세부 내용"],
        [
            ["국립중앙도서관 Q&A 크롤링",  "완료",    "5,907건, 591페이지 전체 수집"],
            ["PostgreSQL DB 구축",         "완료",    "ai_librarian DB, qa_records 테이블"],
            ["로컬 임베딩 생성",           "완료",    "384차원, 5,907건 전체 적용"],
            ["BM25 전문검색",              "완료",    "PostgreSQL plainto_tsquery (simple)"],
            ["벡터 유사도 검색",           "완료",    "pgvector 코사인 거리"],
            ["RRF 하이브리드 검색",        "완료",    "쿼리 유형별 가중치 자동 조정"],
            ["FastAPI 서버",               "완료",    "포트 8000, 3개 엔드포인트"],
            ["Gemini RAG 스트리밍 답변",   "완료",    "gemini-2.5-flash, 출처 URL 포함"],
            ["웹 UI",                      "완료",    "브라우저 접속, 실시간 스트리밍"],
            ["시스템 프롬프트 정교화",     "개선완료", "역할·형식·출처인용·폴백 구조화"],
            ["DB 연결 풀",                 "개선완료", "ThreadedConnectionPool(min=2, max=10)"],
            ["답변 텍스트 정제",           "개선완료", "곡선 따옴표·괄호 공백 정규화 후 전체 재임베딩"],
            ["질문+답변 결합 임베딩",      "개선완료", "질문+답변(200자) 결합 임베딩으로 교체, 5,907건 재생성"],
            ["한국어 형태소 분석",         "개선완료", "kiwipiepy 기반 morphemes 컬럼 + GIN 인덱스 (5,907건)"],
            ["AI 답변 마크다운 렌더링",    "개선완료", "marked.js — 굵게·목록·제목·코드 서식, 스트리밍 중 실시간 렌더링"],
            ["AI 답변 대기 UX",            "개선완료", "중앙 오버레이 팝업 — 책 아이콘 애니메이션 + 단계별 상태 메시지 순환"],
            ["질문 히스토리",              "개선완료", "localStorage 사이드바 — 클릭 재검색, 최대 30건, 새로고침 유지"],
            ["무결과 유사 질문 제안",      "개선완료", "결과 없을 때 /api/suggest — 유사 질문 3개를 카드로 제시"],
            ["ngrok 외부 공개",            "완료",    "ngrok HTTPS 터널 — 스마트폰 접속 가능, URL 발급 완료"],
            ["유용도 피드백",              "완료",    "답변 하단 좋아요/별로에요 버튼 — localStorage 저장, 품질 개선 데이터 수집"],
        ],
        [62, 20, 92],
    )

    pdf.sub("4.2 프로젝트 파일 구조")
    pdf.body("루트 경로: C:\\VIBE\\9. AI사서응답시스템\\")
    pdf.tbl(
        ["파일 / 폴더", "역할"],
        [
            ["api/main.py",         "FastAPI 서버 — Gemini RAG 스트리밍, 3개 엔드포인트"],
            ["search/hybrid.py",    "RRF 하이브리드 검색 (BM25 + 벡터, 알파 자동 조정)"],
            ["search/keyword.py",   "BM25 전문검색 (PostgreSQL)"],
            ["search/vector.py",    "pgvector 코사인 유사도 검색"],
            ["crawler/crawl.py",    "국립중앙도서관 Q&A 크롤러"],
            ["crawler/data/",       "keys.json, qa_data.json (5,907건)"],
            ["db/schema.sql",       "PostgreSQL 스키마 (VECTOR 384차원)"],
            ["db/embed.py",         "DB 적재 + 임베딩 생성"],
            ["frontend/index.html", "웹 UI (마크다운·히스토리·유사질문 제안 포함)"],
            [".env",                "DATABASE_URL, GEMINI_API_KEY"],
            ["RESUME.md",           "재시작 가이드 (발표 당일 체크리스트 포함)"],
        ],
        [58, 116],
    )

    pdf.sub("4.3 서버 재시작 방법")
    pdf.callout("명령어 (PowerShell — 두 줄)", [
        'cd "C:\\VIBE\\9. AI사서응답시스템"',
        "uvicorn api.main:app --port 8000",
        "",
        "로컬 접속: http://localhost:8000",
        "PostgreSQL은 자동시작 설정됨 (별도 실행 불필요)",
        "와이파이 변경 시에도 정상 동작 (DB/임베딩은 로컬, Gemini만 인터넷 필요)",
    ])

    pdf.sub("4.4 외부 공개 (ngrok)")
    pdf.callout("접속 정보", [
        "외부 URL :  https://conjure-overpay-reverb.ngrok-free.dev",
        "버  전   :  ngrok v3.39.2  (설치 완료, 인증 토큰 등록 완료)",
        "",
        "주의 ①  로컬 서버(uvicorn)가 실행 중이어야 터널 작동",
        "주의 ②  첫 접속 시 ngrok 경고 페이지 → Visit Site 클릭",
        "주의 ③  Gemini 쿼터 리셋: UTC 자정 (KST 오전 9시)",
    ])
    pdf.callout("터널 실행 명령어 (PowerShell — 서버 시작 후 새 창에서)", [
        "① 서버 먼저 실행 (기존 창):",
        "     uvicorn api.main:app --port 8000",
        "",
        "② 새 PowerShell 창에서 경로 변수 설정 후 터널 열기:",
        r"     $ng = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'",
        r"     $ng = Join-Path $ng 'Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe'",
        "     & $ng http 8000",
        "",
        "③ 발급된 외부 URL 확인:",
        "     (Invoke-RestMethod 'http://localhost:4040/api/tunnels').tunnels.public_url",
    ])

    # ── 5. 개선 방안 ─────────────────────────────────────
    pdf.add_page()
    pdf.sec("5. 개선 방안")

    pdf.sub("5.1 데이터 품질 — 한국어 특화 임베딩 모델 도입")
    pdf.bul("BGE-M3, KoSimCSE 등 한국어 특화 모델로 교체 시 도서관 전문 용어 검색 정밀도 개선 가능")
    pdf.need_con(
        "현재 paraphrase-multilingual-MiniLM은 범용 다국어 모델로, 도서관 전문 용어·한국어 어휘 변이에서 "
        "의미 유사도 정확도가 제한됨. '사서', '소장', '청구기호' 등 고유 개념에서 벡터 거리 오차 발생 가능.",
        "전체 5,907건 재임베딩 수 시간 소요, 모델 파일 수 GB 저장 공간 부담, "
        "한국어 특화 모델일수록 영어·다국어 질문 대응력 저하, 라이선스 확인 필요.",
    )

    pdf.sub("5.2 검색 품질 — 도서관 용어 동의어 사전 구축")
    pdf.bul("'대출=빌리기', '반납=돌려주기' 등 일상어-전문용어 매핑으로 BM25 키워드 검색 재현율 향상")
    pdf.need_con(
        "이용자는 전문 용어에 익숙하지 않아 일상어로 질문하면 키워드 검색에서 결과가 누락됨. "
        "벡터 검색이 보완하고 있으나 고유명사·약어 처리는 한계가 있음.",
        "사전 초기 구축 및 유지보수에 도메인 전문가 투입 필요, "
        "과잉 확장 시 무관한 결과 혼입 가능, 신조어·비표준 표현의 주기적 갱신 부담.",
    )

    pdf.sub("5.3 AI 답변 품질 — 응답 캐싱 도입")
    pdf.bul("Redis 또는 DB에 빈출 질문 상위 50건 답변 사전 저장 → Gemini API 호출 횟수 절감")
    pdf.need_con(
        "동일·유사 질문이 반복될 때마다 Gemini API를 호출하면 무료 쿼터 소진이 가속됨. "
        "캐싱 도입 시 응답 속도 향상과 쿼터 절약을 동시에 달성 가능.",
        "Redis 서버 별도 구축·운영 필요 (추가 인프라), 캐시 유효기간 및 무효화 로직 관리 복잡, "
        "AI 답변 품질 개선 시 기존 캐시 전체 재생성 필요.",
    )

    pdf.sub("5.4 시스템 안정성 — 프로세스 자동 관리")
    pdf.bul("PM2 또는 Windows 서비스 등록으로 서버 자동 시작·재시작 및 상시 운영 환경 구성")
    pdf.need_con(
        "현재는 PowerShell에서 uvicorn 명령어를 수동 실행해야 하며, "
        "컴퓨터 재시작 시 서버가 복구되지 않아 지속 서비스가 불가능함.",
        "PM2는 Node.js 환경 별도 필요 (이종 스택 혼재), "
        "Windows 서비스 등록은 관리자 권한 및 설정 복잡성 수반, 모니터링 도구 추가 학습 필요.",
    )

    # ── 6. 향후 운영 방안 ────────────────────────────────
    pdf.add_page()
    pdf.sec("6. 향후 운영 방안")

    pdf.sub("6.1 데이터 최신성 유지 — 증분 수집 스케줄러")
    pdf.bul("월 1회 자동 크롤러 실행으로 신규 Q&A를 감지·수집하고 신규 건만 임베딩 생성하여 DB 적재")
    pdf.need_con(
        "현재 5,907건은 특정 시점의 스냅샷으로, 시간이 지날수록 최신 사서 답변이 누락되어 "
        "검색 커버리지가 점차 저하됨. 증분 수집 시 전체 재임베딩 없이 DB 최신성 유지 가능.",
        "스케줄러 실행을 위해 서버 상시 가동 필요, 국립중앙도서관 웹 구조 변경 시 크롤러 수정 필요, "
        "robots.txt 정책 변경 시 수집 불가 위험 존재.",
    )

    pdf.sub("6.2 비용 최적화 — API 한도 확대 및 로컬 LLM 전환")
    pdf.bul("① Google for Education 계정 신청: 학술·교육 목적으로 Gemini API 무료 한도 확대 가능")
    pdf.need_con(
        "무료 tier 일일 한도 초과 시 AI 답변 중단, 폴백 응답으로 대체됨. "
        "Education 계정 승인 시 한도 제한 완화로 안정적 운영 가능.",
        "교육 기관 인증 절차 필요, 심사 승인까지 기간 불확실.",
    )
    pdf.bul("② 로컬 LLM 전환: Ollama + LLaMA3-Korean 또는 EXAONE으로 API 비용 0원, 개인정보 보호")
    pdf.need_con(
        "API 의존성 제거로 쿼터 제한 없이 운영 가능, 개인정보가 외부 서버로 전송되지 않음.",
        "GPU 미탑재 노트북에서 응답 30초 이상 소요, 한국어 답변 품질이 Gemini 2.5 Flash 대비 저하.",
    )

    pdf.sub("6.3 접근성 확대 — 상시 외부 배포")
    pdf.bul("현재 ngrok 터널 운영 중 → 향후 Render.com, Railway 등 무료 클라우드로 고정 URL 상시 운영")
    pdf.need_con(
        "ngrok은 재시작마다 URL이 변경되어 지속 서비스에 한계. "
        "클라우드 배포 시 24시간 고정 URL 제공, 별도 PC 가동 불필요.",
        "Render.com 무료 플랜은 15분 비활성 시 서버 슬립 (첫 응답 30초 지연), "
        "컴퓨팅 제한으로 임베딩 모델 로딩 속도 저하, PostgreSQL 별도 클라우드 DB 연동 필요.",
    )

    pdf.sub("6.4 확장 가능성")
    pdf.bul("① 피드백 데이터 활용 (구현 완료): 수집된 좋아요/별로에요를 검색 가중치·프롬프트 개선 근거로 활용")
    pdf.bul("② 다른 도서관 Q&A로 확장: 공공도서관·대학도서관 데이터 추가 수집 후 동일 시스템 적용")
    pdf.need_con(
        "단일 도서관 데이터로는 질문 커버리지에 한계. "
        "복수 도서관 데이터 통합 시 다양한 주제의 사서 답변을 제공할 수 있음.",
        "각 도서관별 웹 구조 달라 크롤러 별도 개발 필요, 데이터 형식·용어 체계 상이로 전처리 추가 작업 필요.",
    )
    pdf.bul("③ 멀티모달 확장: 도서 표지·도표 포함 자료 검색 시 Gemini의 멀티모달 기능 활용 가능")
    pdf.need_con(
        "텍스트 질문만 처리하는 현재 시스템을 이미지 기반 검색으로 확장하여 서비스 범위 대폭 확대 가능.",
        "이미지 임베딩 추가 비용 발생, 도서 표지·도표 이미지의 저작권 처리 방안 검토 필요.",
    )

    # ── 7. 결론 ──────────────────────────────────────────
    pdf.add_page()
    pdf.sec("7. 결론")

    pdf.sub("7.1 프로젝트 요약")
    pdf.body(
        "본 프로젝트는 국립중앙도서관이 '사서문답' 서비스를 통해 축적한 5,907건의 전문 사서 답변 데이터를 "
        "AI가 검색·활용할 수 있는 형태로 구조화하는 데서 출발하였습니다. "
        "단순 키워드 검색의 한계를 극복하기 위해 BM25 전문검색과 벡터 유사도 검색을 "
        "RRF 알고리즘으로 통합한 하이브리드 검색 엔진을 구현하였으며, "
        "여기에 Gemini 2.5 Flash RAG를 결합하여 이용자의 자연어 질문에 "
        "실시간 스트리밍 방식으로 출처 기반 답변을 제공하는 시스템을 완성하였습니다."
    )
    pdf.body(
        "전체 시스템은 임베딩 비용 0원(로컬 모델), AI 답변 비용 0원(Gemini 무료 tier)으로 구축되었으며, "
        "마크다운 렌더링, 답변 대기 오버레이, 질문 히스토리, 유사 질문 제안, 유용도 피드백 버튼까지 "
        "이용자 경험을 고려한 UI 개선도 함께 구현하였습니다. "
        "ngrok을 통해 외부 HTTPS URL도 발급하여 스마트폰을 포함한 외부 환경에서도 즉시 접속이 가능합니다."
    )

    pdf.sub("7.2 개발 과정에서 얻은 교훈")
    pdf.lesson_bul(
        "실제 운영 환경 이슈 체득",
        "크롤러 파라미터 오류, pgvector Windows 설치 복잡성, SDK deprecated 전환, "
        "API 쿼터 초과, 구버전 서버 프로세스 잔류 등 교과서에서 다루지 않는 9건의 문제를 직접 해결하며 "
        "RAG 시스템 개발의 전주기적 복잡성을 체득하였습니다. "
        "특히 코드가 정상임에도 결과가 바뀌지 않았던 프로세스 잔류 문제는 "
        "개발 환경의 상태 관리가 기술 구현 못지않게 중요함을 보여주는 사례였습니다."
    )
    pdf.lesson_bul(
        "비용 최소화 설계의 실증",
        "OpenAI, Anthropic 등 유료 API 없이 로컬 sentence-transformers 임베딩과 "
        "Gemini 무료 tier만으로 실용적 수준의 RAG를 구축할 수 있음을 확인하였습니다. "
        "임베딩 비용 0원, AI 답변 비용 0원이라는 결과는 "
        "예산 제약이 있는 학술·공공·소규모 환경에 적용 가능한 구체적 아키텍처를 제시한다는 점에서 의의가 있습니다."
    )
    pdf.lesson_bul(
        "하이브리드 검색의 실질적 효과",
        "키워드(BM25)와 의미(벡터) 검색을 RRF로 결합하면 단일 방식 대비 "
        "재현율과 정밀도가 균형 있게 향상됨을 실험적으로 확인하였습니다. "
        "고유명사·ISBN 포함 질문에는 키워드 비중을 높이고, "
        "주제 탐색형 질문에는 벡터 비중을 높이는 동적 가중치 조정이 실질적 개선 효과를 보였습니다."
    )
    pdf.lesson_bul(
        "이용자 경험의 지속적 중요성",
        "검색·AI 엔진 완성 이후에도 마크다운 렌더링, 답변 대기 UX, 질문 히스토리, "
        "무결과 제안, 유용도 피드백 버튼 등 UI 개선 작업이 전체 개발의 상당 부분을 차지하였습니다. "
        "기술적 정확성과 더불어 이용자가 체감하는 서비스 품질이 "
        "도서관 정보 시스템의 실질적 활용도를 결정하는 핵심 요소임을 재확인하였습니다."
    )

    pdf.add_page()
    pdf.sub("7.3 최종 성과 요약")
    pdf.ln(1)
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(*WHITE)
    pdf.set_font("MG", "B", 10)
    pdf.cell(0, 8, "  시스템 완성 현황",
             fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    results = [
        ("수집 데이터",     "5,907건 (국립중앙도서관 사서문답 전체, 99.95% 성공률)"),
        ("DB 구축",         "PostgreSQL 17 + pgvector, 384차원 임베딩 완료"),
        ("검색 방식",       "RRF 하이브리드 (BM25 35% + 벡터 65%, 쿼리 유형별 자동 조정)"),
        ("AI 답변",         "Gemini 2.5 Flash 스트리밍 + 출처 [1] URL 인용 형식 제공"),
        ("프롬프트 개선",   "역할·형식·제약 구조화, 폴백 응답(쿼터 초과 시 검색결과 직접 표시)"),
        ("DB 연결 풀",      "ThreadedConnectionPool(min=2, max=10), 자동 재연결 포함"),
        ("텍스트 정제",     "곡선 따옴표·괄호 공백 정규화, 5,907건 전체 재임베딩 완료"),
        ("결합 임베딩",     "질문+답변(200자) 결합 임베딩으로 교체, 의미 검색 정확도 향상"),
        ("형태소 분석",     "kiwipiepy BM25 검색 — 한국어 형태소 기반 morphemes 컬럼 + GIN 인덱스"),
        ("마크다운 렌더링",  "marked.js 기반 실시간 렌더링 — 굵게·번호목록·제목·인라인 코드 서식, 스트리밍 중 적용"),
        ("UI 대기 개선",     "화면 중앙 오버레이 팝업 — 책 아이콘 float 애니메이션 + 단계별 상태 메시지 순환 (2초 간격 페이드)"),
        ("질문 히스토리",   "localStorage 기반 좌측 사이드바 — 최근 30건, 클릭 재검색, 새로고침 후에도 유지"),
        ("무결과 질문 제안", "결과 없을 때 /api/suggest — 벡터 유사도 Top 3 질문을 클릭 가능한 카드로 표시"),
        ("유용도 피드백",   "답변 하단 좋아요/별로에요 버튼 — localStorage 저장, 서비스 품질 개선 기초 데이터 수집"),
        ("외부 공개",       "ngrok 터널 — https://conjure-overpay-reverb.ngrok-free.dev (스마트폰 시연 가능)"),
        ("운영 비용",       "임베딩 0원(로컬), AI 답변은 Gemini 무료 tier 활용"),
        ("재시작",          "uvicorn api.main:app --port 8000 — 명령어 1줄로 즉시 구동"),
        ("이동성",          "와이파이 변경 시에도 정상 동작 (DB·임베딩은 로컬)"),
    ]
    TW = pdf.w - pdf.l_margin - pdf.r_margin
    for ri, (label, val) in enumerate(results):
        pdf.set_fill_color(*LGRAY) if ri % 2 == 0 else pdf.set_fill_color(*WHITE)
        pdf.set_font("MG", "B", 9.5)
        pdf.set_text_color(*BLUE)
        pdf.cell(30, 7.5, f"  {label}", fill=True)
        pdf.set_font("MG", "", 9.5)
        pdf.set_text_color(*DARK)
        pdf.cell(TW - 30, 7.5, f"  {val}", fill=True)
        pdf.ln()
    pdf.set_font("MG", "", 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 6,
             "본 보고서는 Claude Code(AI)와 협업하여 작성되었습니다.",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    pdf = PDF()
    cover(pdf)
    body(pdf)
    out = os.path.join(os.path.dirname(__file__), OUTPUT)
    pdf.output(out)
    print(f"저장: {out}  ({os.path.getsize(out):,} bytes)")
