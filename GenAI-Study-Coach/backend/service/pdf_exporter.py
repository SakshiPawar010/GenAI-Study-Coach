from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
import re

W = A4[0] - 1.4 * inch  # usable width

class PDFExporter:
    PRIMARY   = HexColor('#667eea')
    SECONDARY = HexColor('#764ba2')
    GREEN     = HexColor('#28a745')
    RED       = HexColor('#dc3545')
    AMBER     = HexColor('#ffc107')
    LIGHT_BG  = HexColor('#f0f2ff')
    CARD_BG   = HexColor('#f8f9fa')
    BORDER    = HexColor('#dee2e6')
    DARK_TEXT = HexColor('#212529')
    MID_TEXT  = HexColor('#495057')

    def _styles(self):
        s = getSampleStyleSheet()
        add = s.add
        add(ParagraphStyle('AppTitle',    fontSize=22, textColor=white,        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=2))
        add(ParagraphStyle('AppSub',      fontSize=11, textColor=HexColor('#d0d8ff'), alignment=TA_CENTER, fontName='Helvetica', spaceAfter=0))
        add(ParagraphStyle('SecHeader',   fontSize=13, textColor=white,        fontName='Helvetica-Bold', spaceAfter=0, spaceBefore=0))
        add(ParagraphStyle('BodyText2',   fontSize=11, textColor=self.DARK_TEXT, fontName='Helvetica', spaceAfter=4, leading=16))
        add(ParagraphStyle('BulletItem',  fontSize=11, textColor=self.DARK_TEXT, fontName='Helvetica', spaceAfter=3, leftIndent=12, leading=15))
        add(ParagraphStyle('Bold11',      fontSize=11, textColor=self.DARK_TEXT, fontName='Helvetica-Bold', spaceAfter=3))
        add(ParagraphStyle('QNum',        fontSize=10, textColor=white,        fontName='Helvetica-Bold', alignment=TA_CENTER))
        add(ParagraphStyle('QText',       fontSize=12, textColor=self.DARK_TEXT, fontName='Helvetica-Bold', spaceAfter=4, leading=16))
        add(ParagraphStyle('OptText',     fontSize=11, textColor=self.MID_TEXT,  fontName='Helvetica', spaceAfter=2, leftIndent=8, leading=14))
        add(ParagraphStyle('AnsText',     fontSize=11, textColor=self.GREEN,    fontName='Helvetica-Bold', spaceAfter=0, leftIndent=8))
        add(ParagraphStyle('DayLabel',    fontSize=12, textColor=white,        fontName='Helvetica-Bold', spaceAfter=0))
        add(ParagraphStyle('DayBody',     fontSize=11, textColor=self.DARK_TEXT, fontName='Helvetica', spaceAfter=3, leftIndent=8, leading=15))
        add(ParagraphStyle('CardQ',       fontSize=12, textColor=self.PRIMARY,  fontName='Helvetica-Bold', spaceAfter=3))
        add(ParagraphStyle('CardA',       fontSize=11, textColor=self.DARK_TEXT, fontName='Helvetica', spaceAfter=0, leftIndent=8, leading=15))
        add(ParagraphStyle('SmallGray',   fontSize=9,  textColor=HexColor('#888888'), fontName='Helvetica', spaceAfter=0))
        return s

    # ── helpers ──────────────────────────────────────────────────────────────

    def _clean(self, text):
        """Strip non-ASCII and markdown bold markers."""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        return re.sub(r'[^\x00-\x7F]+', '', text).strip()

    def _header_banner(self, title, subtitle, styles):
        """Gradient-style header table."""
        t = Table(
            [[Paragraph(title, styles['AppTitle'])],
             [Paragraph(subtitle, styles['AppSub'])]],
            colWidths=[W]
        )
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), self.PRIMARY),
            ('ROUNDEDCORNERS', [8]),
            ('TOPPADDING',    (0,0), (-1,-1), 14),
            ('BOTTOMPADDING', (0,0), (-1,-1), 14),
            ('LEFTPADDING',   (0,0), (-1,-1), 16),
            ('RIGHTPADDING',  (0,0), (-1,-1), 16),
        ]))
        return t

    def _section_header(self, text, styles):
        t = Table([[Paragraph(text, styles['SecHeader'])]], colWidths=[W])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), self.PRIMARY),
            ('TOPPADDING',    (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING',   (0,0), (-1,-1), 12),
            ('RIGHTPADDING',  (0,0), (-1,-1), 12),
        ]))
        return t

    def _build_pdf(self, story):
        buf = io.BytesIO()
        try:
            doc = SimpleDocTemplate(buf, pagesize=A4,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch,
                                    leftMargin=0.7*inch, rightMargin=0.7*inch)
            doc.build(story)
            buf.seek(0)
            return buf
        except Exception:
            buf.close()
            raise

    # ── Summary ──────────────────────────────────────────────────────────────

    def export_summary(self, summary_text):
        styles = self._styles()
        story = [
            self._header_banner('GenAI Study Coach', 'Study Summary', styles),
            Spacer(1, 0.2*inch),
        ]

        lines = summary_text.split('\n')
        i = 0
        while i < len(lines):
            raw = lines[i].strip()

            # Detect markdown table block
            if raw.startswith('|') and i + 1 < len(lines) and '---' in lines[i + 1]:
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                story.append(self._build_md_table(table_lines, styles))
                story.append(Spacer(1, 0.1*inch))
                continue

            if not raw:
                story.append(Spacer(1, 0.06*inch))
            elif raw == '---':
                story.append(HRFlowable(width='100%', thickness=1, color=self.BORDER))
                story.append(Spacer(1, 0.06*inch))
            elif raw.startswith('##') or (raw.startswith('**') and raw.endswith('**') and len(raw) > 4):
                text = self._clean(raw.lstrip('#').strip())
                story.append(Spacer(1, 0.08*inch))
                story.append(self._section_header(text, styles))
                story.append(Spacer(1, 0.06*inch))
            elif raw.startswith(('•', '-', '*')) and not raw.startswith('**'):
                text = self._clean(raw.lstrip('•-* '))
                story.append(Paragraph(f'• {text}', styles['BulletItem']))
            else:
                text = self._clean(raw)
                if text:
                    story.append(Paragraph(text, styles['BodyText2']))
            i += 1

        return self._build_pdf(story)

    def _build_md_table(self, table_lines, styles):
        """Convert markdown pipe-table lines into a styled ReportLab Table."""
        rows = []
        for line in table_lines:
            if re.match(r'^\|[-| :]+\|$', line):  # separator row
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows.append(cells)

        if not rows:
            return Spacer(1, 0)

        col_count = max(len(r) for r in rows)
        # Pad rows to equal column count
        rows = [r + [''] * (col_count - len(r)) for r in rows]
        col_w = W / col_count

        # Build Paragraph cells
        pdf_rows = []
        for ri, row in enumerate(rows):
            pdf_row = []
            for cell in row:
                st = styles['Bold11'] if ri == 0 else styles['BodyText2']
                pdf_row.append(Paragraph(self._clean(cell), st))
            pdf_rows.append(pdf_row)

        t = Table(pdf_rows, colWidths=[col_w] * col_count, hAlign='LEFT')
        ts = [
            # Header row
            ('BACKGROUND',    (0, 0), (-1, 0), self.PRIMARY),
            ('TEXTCOLOR',     (0, 0), (-1, 0), white),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            # All cells
            ('FONTSIZE',      (0, 0), (-1, -1), 10),
            ('TOPPADDING',    (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('GRID',          (0, 0), (-1, -1), 0.5, self.BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.CARD_BG]),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]
        t.setStyle(TableStyle(ts))
        return t

    # ── Quiz ─────────────────────────────────────────────────────────────────

    def export_quiz(self, quiz_data):
        styles = self._styles()
        questions = quiz_data.get('quiz', [])
        difficulty = quiz_data.get('difficulty', 'medium').capitalize()
        story = [
            self._header_banner('GenAI Study Coach', f'Practice Quiz  |  Difficulty: {difficulty}  |  {len(questions)} Questions', styles),
            Spacer(1, 0.2*inch),
        ]

        for i, q in enumerate(questions):
            # Question number badge + question text side by side
            badge = Table([[Paragraph(str(i+1), styles['QNum'])]], colWidths=[0.35*inch])
            badge.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), self.PRIMARY),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 4),
                ('RIGHTPADDING',  (0,0), (-1,-1), 4),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ]))
            q_text = self._clean(q.get('question', ''))
            q_row = Table([[badge, Paragraph(q_text, styles['QText'])]], colWidths=[0.42*inch, W - 0.42*inch])
            q_row.setStyle(TableStyle([
                ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING',   (0,0), (-1,-1), 0),
                ('RIGHTPADDING',  (0,0), (-1,-1), 0),
                ('TOPPADDING',    (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))

            # Options
            opts = []
            labels = ['A', 'B', 'C', 'D']
            for j, opt in enumerate(q.get('options', [])):
                label = labels[j] if j < len(labels) else str(j+1)
                opts.append(Paragraph(f'{label}.  {self._clean(opt)}', styles['OptText']))

            # Answer
            ans = Paragraph(f'✓  Answer: {self._clean(q.get("answer", ""))}', styles['AnsText'])

            # Wrap in a light-bg box
            inner = [[q_row]] + [[o] for o in opts] + [[Spacer(1, 4)], [ans]]
            box = Table(inner, colWidths=[W - 0.3*inch])
            box.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), self.CARD_BG),
                ('BOX',           (0,0), (-1,-1), 0.8, self.BORDER),
                ('TOPPADDING',    (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 10),
                ('RIGHTPADDING',  (0,0), (-1,-1), 10),
                # green tint on answer row
                ('BACKGROUND',    (0, len(inner)-1), (-1, len(inner)-1), HexColor('#eafaf1')),
            ]))

            story.append(KeepTogether([box, Spacer(1, 0.12*inch)]))

        return self._build_pdf(story)

    # ── Roadmap ───────────────────────────────────────────────────────────────

    def export_roadmap(self, roadmap_text):
        styles = self._styles()
        story = [
            self._header_banner('GenAI Study Coach', '7-Day Study Roadmap', styles),
            Spacer(1, 0.2*inch),
        ]

        day_colors = [
            HexColor('#667eea'), HexColor('#764ba2'), HexColor('#f093fb'),
            HexColor('#4facfe'), HexColor('#43e97b'), HexColor('#fa709a'),
            HexColor('#fee140'),
        ]
        day_idx = -1
        day_items = []

        def flush_day():
            if day_idx < 0 or not day_items:
                return []
            color = day_colors[day_idx % len(day_colors)]
            label_t = Table([[Paragraph(f'Day {day_idx + 1}', styles['DayLabel'])]], colWidths=[0.8*inch])
            label_t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), color),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 10),
                ('RIGHTPADDING',  (0,0), (-1,-1), 10),
            ]))
            body_rows = [[Paragraph(f'• {self._clean(it)}', styles['DayBody'])] for it in day_items]
            body_t = Table(body_rows, colWidths=[W - 0.8*inch - 0.1*inch])
            body_t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), self.CARD_BG),
                ('TOPPADDING',    (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING',   (0,0), (-1,-1), 10),
                ('RIGHTPADDING',  (0,0), (-1,-1), 10),
                ('BOX',           (0,0), (-1,-1), 0.5, self.BORDER),
            ]))
            row = Table([[label_t, body_t]], colWidths=[0.8*inch, W - 0.8*inch])
            row.setStyle(TableStyle([
                ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING',   (0,0), (-1,-1), 0),
                ('RIGHTPADDING',  (0,0), (-1,-1), 0),
                ('TOPPADDING',    (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            return [KeepTogether([row, Spacer(1, 0.1*inch)])]

        for line in roadmap_text.split('\n'):
            raw = line.strip()
            if not raw:
                continue
            lower = raw.lower()
            # Detect "Day N" header
            m = re.match(r'^(?:day\s*(\d+)|(\d+)\.\s*day)', lower)
            if m or re.match(r'^day\s*\d+', lower):
                story.extend(flush_day())
                day_items = []
                day_idx += 1
                # If the day line has content after the day label, treat it as first item
                rest = re.sub(r'^day\s*\d+[:\-–]?\s*', '', raw, flags=re.IGNORECASE).strip()
                if rest:
                    day_items.append(rest)
            else:
                day_items.append(raw.lstrip('•-* '))

        story.extend(flush_day())
        return self._build_pdf(story)

    # ── Flashcards ────────────────────────────────────────────────────────────

    def export_flashcards(self, flashcard_data):
        styles = self._styles()
        cards = flashcard_data.get('flashcards', [])
        story = [
            self._header_banner('GenAI Study Coach', f'Flashcards  |  {len(cards)} Cards', styles),
            Spacer(1, 0.2*inch),
        ]

        # 2-column grid
        pairs = []
        for i, card in enumerate(cards):
            front = self._clean(card.get('front', ''))
            back  = self._clean(card.get('back', ''))
            num   = Paragraph(f'Card {i+1}', styles['SmallGray'])
            q     = Paragraph(front, styles['CardQ'])
            a     = Paragraph(f'A: {back}', styles['CardA'])
            cell  = Table([[num], [q], [HRFlowable(width='100%', thickness=0.5, color=self.BORDER)], [a]],
                          colWidths=[(W - 0.15*inch) / 2])
            cell.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), self.CARD_BG),
                ('BOX',           (0,0), (-1,-1), 0.8, self.PRIMARY),
                ('TOPPADDING',    (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LEFTPADDING',   (0,0), (-1,-1), 10),
                ('RIGHTPADDING',  (0,0), (-1,-1), 10),
                # light blue top strip
                ('BACKGROUND',    (0,0), (0,0), HexColor('#eef0ff')),
            ]))
            pairs.append(cell)

        # Fill to even number
        if len(pairs) % 2:
            pairs.append(Spacer(1, 1))

        col_w = (W - 0.15*inch) / 2
        for i in range(0, len(pairs), 2):
            row = Table([[pairs[i], pairs[i+1]]], colWidths=[col_w, col_w],
                        hAlign='LEFT')
            row.setStyle(TableStyle([
                ('LEFTPADDING',   (0,0), (-1,-1), 0),
                ('RIGHTPADDING',  (0,0), (-1,-1), 0),
                ('TOPPADDING',    (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                ('INNERGRID',     (0,0), (-1,-1), 0, white),
                ('LEFTPADDING',   (0,1), (0,1), 8),
            ]))
            story.append(KeepTogether([row, Spacer(1, 0.1*inch)]))

        return self._build_pdf(story)
