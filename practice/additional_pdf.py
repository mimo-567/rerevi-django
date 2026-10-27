"""Keep Eduqas additional-page rules and columns, with matching theme text."""
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader,PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from .pdf_furniture import booklet_footer,classic_footer

SOURCE=Path(__file__).with_name('data')/'pdf_templates'/'eduqas-additional-source.pdf'

def append_additional_pages(document,count,paper,theme='classic',document_label=None):
    if not count:return document
    original=PdfReader(BytesIO(document)) if document else None;writer=PdfWriter()
    if original:writer.append(original,import_outline=False)
    if original and original.metadata:
        writer.add_metadata({k:str(v) for k,v in original.metadata.items() if v is not None})
    first=len(original.pages) if original else 0
    total=first+count
    if not original:writer.add_metadata({'/Title':paper['title']+' — Continuation sheets','/Author':'RE Revi'})
    reference=str(paper.get('reference') or str(paper.get('id',''))[:10].upper())[:50]
    from .pdf import FONT,BOLD
    if theme=='eduqas-booklet':
        from .pdf_template import load_template
        profile=load_template(theme);regular,bold=profile['font'],profile['bold_font']
    else:regular,bold=FONT,BOLD
    for index in range(count):
        # Read a fresh page so overlays cannot accumulate across repeated pages.
        page=PdfReader(SOURCE).pages[0]
        overlay=BytesIO();c=canvas.Canvas(overlay,pagesize=A4)
        c.setFillColor(colors.white)
        # Keep the source rules and columns; replace text and page furniture.
        for x,y,w,h in [(279,760,37,25),(0,0,15,842),(0,0,A4[0],85),
                        (59,717.5,48,24.9),(110,717.5,426,24.9),(540,718,44,25)]:
            c.rect(x,y,w,h,fill=1,stroke=0)
        number=first+index+1
        c.setFillColor(colors.black);c.setFont(bold,9)
        c.drawString(62.6756,732,'Question');c.drawString(62.6756,722,'number')
        c.setFont(bold,10.5)
        c.drawCentredString(322.5,732,'Additional page, if required.')
        c.drawCentredString(322.5,721.5,'Write the question number(s) in the left-hand margin.')
        c.setFont(regular,7)
        c.drawCentredString(559.5,733,'Examiner');c.drawCentredString(559.5,724,'only')
        if theme=='eduqas-booklet':booklet_footer(c,number,total,reference)
        else:classic_footer(c,number,paper,document_label)
        c.save();page.merge_page(PdfReader(BytesIO(overlay.getvalue())).pages[0])
        writer.add_page(page)
    output=BytesIO();writer.write(output);return output.getvalue()


def make_continuation_pdf(paper,options):
    """Standalone continuation packs share the exact additional-page layout."""
    from django.core.exceptions import ValidationError
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate
    from .pdf import exam_cover,pdf_finish_options
    from .exam_theme import selected_theme
    from .pdf_template import TemplateCover,load_template
    cover,back_pages=pdf_finish_options(options)
    theme=selected_theme(options)
    if options.get('layout','standard') not in ('standard','large','compact'):
        raise ValidationError('Choose a valid print layout.')
    try:count=int(options.get('continuation_pages',2))
    except (TypeError,ValueError):raise ValidationError('Choose 1–10 continuation sheets.')
    if not 1<=count<=10:raise ValidationError('Choose 1–10 continuation sheets.')
    document=None
    if cover:
        stream=BytesIO()
        if theme=='eduqas-booklet':
            c=canvas.Canvas(stream,pagesize=A4,title=paper['title']+' — Continuation sheets',author='RE Revi')
            reference=str(paper.get('reference') or str(paper.get('id',''))[:10].upper())[:50]
            TemplateCover(paper,options,'Continuation sheets',reference,back_pages,load_template(theme)).drawOn(c,20*mm,27*mm)
            booklet_footer(c,1,1+count+back_pages,reference,is_cover=True)
            c.showPage();c.save()
        else:
            doc=SimpleDocTemplate(stream,pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=20*mm,bottomMargin=20*mm,title=paper['title']+' — Continuation sheets',author='RE Revi')
            content=exam_cover(paper,'Continuation sheets',174*mm,back_pages)
            content.pop()  # Standalone cover needs no trailing page break.
            def footer(c,d):classic_footer(c,d.page,paper,'Continuation sheets')
            doc.build(content,onFirstPage=footer,onLaterPages=footer)
        document=stream.getvalue()
    return append_additional_pages(document,count+back_pages,paper,theme=theme,document_label='Continuation sheets')
