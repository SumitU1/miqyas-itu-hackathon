"""Build the ITU technical report (docx) from the official submission template.

Usage: python scripts/build_report.py [--out report/Miqyas_ITU_Technical_Report.docx]

Opens docs/template_src/ITU-submission-template.docx, keeps its title block, heading
numbering, table style and page set-up, and replaces the sample text with the report
text in scripts/report_content.py. Numbers in the text come from docs/ROADMAP_STATUS.md,
docs/SCENARIOS.md and the files under runs/2026-10-28/.
"""
import argparse
import copy
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import report_content as C  # noqa: E402

TEMPLATE = ROOT / "docs" / "template_src" / "ITU-submission-template.docx"
FONT = "Times New Roman"
BODY_PT = C.BODY_PT
TABLE_PT = C.TABLE_PT


def set_font(run, size, bold=None, italic=None):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_runs(par, text, size):
    """Write text into a paragraph; **x** marks bold."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        r = par.add_run(part)
        set_font(r, size, bold=(i % 2 == 1))


def tight(par, after=3, before=0):
    pf = par.paragraph_format
    pf.space_after = Pt(after)
    pf.space_before = Pt(before)
    pf.line_spacing = 1.0


def clear(par):
    for r in list(par.runs):
        r._element.getparent().remove(r._element)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "report" / "Miqyas_ITU_Technical_Report.docx"))
    args = ap.parse_args()

    d = docx.Document(str(TEMPLATE))
    body = d.element.body
    kids = list(body.iterchildren())
    heading_proto = copy.deepcopy(kids[5])      # numbered "List Paragraph" heading
    table_proto = copy.deepcopy(kids[15])       # Grid Table Light
    sect = kids[-1]

    # Title block (paragraphs 0-3 of the template).
    paras = d.paragraphs
    clear(paras[0])
    r = paras[0].add_run(C.TITLE)
    set_font(r, 14, bold=True)
    for p, label, val in ((paras[1], "Team leader: ", C.TEAM_LEADER),
                          (paras[2], "Team members: ", C.TEAM_MEMBERS),
                          (paras[3], "Github link: ", C.GITHUB)):
        clear(p)
        add_runs(p, "**" + label + "**" + val, BODY_PT)
        tight(p, after=1)

    # Remove everything after the title block (keep sectPr).
    for el in kids[4:-1]:
        body.remove(el)

    def heading(text):
        el = copy.deepcopy(heading_proto)
        sect.addprevious(el)
        p = docx.text.paragraph.Paragraph(el, d)
        clear(p)
        r = p.add_run(text)
        set_font(r, BODY_PT + 1, bold=True)
        tight(p, after=2, before=5)
        return p

    def para(text, size=None, after=3, italic=False):
        p = d.add_paragraph()
        sect.addprevious(p._element)
        add_runs(p, text, size or BODY_PT)
        if italic:
            for r in p.runs:
                r.italic = True
        tight(p, after=after)
        return p

    def table(header, rows, widths_cm):
        el = copy.deepcopy(table_proto)
        sect.addprevious(el)
        t = docx.table.Table(el, d)
        # drop sample rows
        for tr in list(el.findall(qn("w:tr"))):
            el.remove(tr)
        t.autofit = False
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        # grid
        grid = el.find(qn("w:tblGrid"))
        for gc in list(grid):
            grid.remove(gc)
        for w in widths_cm:
            gc = grid.makeelement(qn("w:gridCol"), {qn("w:w"): str(int(w * 567))})
            grid.append(gc)
        for ri, row in enumerate([header] + rows):
            new_row = t.add_row()
            trpr = new_row._tr.get_or_add_trPr()
            trpr.append(trpr.makeelement(qn("w:cantSplit"), {}))
            if ri == 0:
                trpr.append(trpr.makeelement(qn("w:tblHeader"), {}))
            cells = new_row.cells
            for ci, txt in enumerate(row):
                cells[ci].width = docx.shared.Cm(widths_cm[ci])
                cp = cells[ci].paragraphs[0]
                clear(cp)
                add_runs(cp, ("**" + txt + "**") if ri == 0 else txt, TABLE_PT)
                tight(cp, after=0)
                if ri == 0:
                    cp.paragraph_format.keep_with_next = True
        return t

    # 1 Introduction
    heading("Introduction")
    for t in C.INTRO:
        para(t)

    # 2 Description of the use case
    heading("Description of the use case")
    for t in C.USE_CASE:
        para(t)

    # 3 Use case requirements
    heading("Use case requirement")
    para(C.REQ_LEAD)
    for t in C.REQUIREMENTS:
        para(t, after=1)

    # 4 Mapping
    heading("Mapping with ITU-T Y.3172 Readiness 2.0 Report, and domain-specific policies")
    para(C.MAP_LEAD, after=2)
    table(C.MAP_HEADER, C.MAP_ROWS, C.MAP_WIDTHS)
    para(C.MAP_NOTE, size=TABLE_PT + 0.5, after=2, italic=True)

    # 5 Error scenarios
    heading("Error scenarios.")
    para(C.SCEN_LEAD, after=2)
    table(C.SCEN_HEADER, C.SCEN_ROWS, C.SCEN_WIDTHS)
    for t in C.SCEN_AFTER:
        para(t, after=2)

    # 6 Gaps
    heading("Policy gaps and standards gaps derived from the mapping exercise")
    para(C.GAP_LEAD, after=2)
    table(C.GAP_HEADER, C.GAP_ROWS, C.GAP_WIDTHS)
    for t in C.LIMITS:
        para(t, after=2)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out))
    print("wrote", out)


if __name__ == "__main__":
    main()
