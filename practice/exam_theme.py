from .examiner_reports import report_paragraphs
"""Independent exam-booklet theme with regenerated content and page furniture."""
from html import escape
from io import BytesIO
from functools import partial
from .additional_pdf import append_additional_pages
from .pdf_furniture import booklet_footer
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate,Frame,PageTemplate,Paragraph,Spacer,PageBreak,NextPageTemplate,Table,TableStyle,KeepTogether
from django.core.exceptions import ValidationError
from .pdf import FONT,BOLD,AnswerLines,pdf_finish_options
from .answer_space import answer_line_count,LINE_PITCH_POINTS,CONTINUATION_LINES,CONTINUATION_PITCH_POINTS
from .catalogue import COMPONENTS

from .pdf_template import THEME_IDS,load_template,TemplateCover

THEMES={'classic',*THEME_IDS}
LABELS={'questions':'Practice question paper','booklet':'Answer booklet','marking':'Marking pack','continuation':'Continuation sheets'}

def selected_theme(options):
    if options is None:return 'classic'
    if not isinstance(options,dict):raise ValidationError('Invalid PDF options.')
    theme=options.get('theme','classic')
    if not isinstance(theme,str) or theme not in THEMES:raise ValidationError('Choose a valid PDF theme.')
    return theme

class NumberedBookletCanvas(canvas.Canvas):
    """Finalise numbering after pagination, including covers and back pages."""
    def __init__(self,*args,**kwargs):
        self._extra_pages=kwargs.pop('extra_pages',0)
        super().__init__(*args,**kwargs);self._pages=[]
    def showPage(self):
        self._pages.append(dict(self.__dict__));self._startPage()
    def save(self):
        total=len(self._pages)+self._extra_pages
        for state in self._pages:
            self.__dict__.update(state)
            booklet_footer(self,self._pageNumber,total,self._booklet_reference,self._booklet_is_cover)
            super().showPage()
        super().save()

def make_exam_booklet(paper,options,kind='questions'):
    if kind not in LABELS:raise ValidationError('Choose a valid document type.')
    if kind=='continuation':
        from .additional_pdf import make_continuation_pdf
        return make_continuation_pdf(paper,options)
    if kind=='marking':options={**options,'back_pages':0}
    cover,back_pages=pdf_finish_options(options)
    layout=options.get('layout','standard')
    if layout not in ('standard','large','compact'):raise ValidationError('Choose a valid print layout.')
    scale={'standard':1,'large':1.45,'compact':.9}[layout]
    try:
        extra=int(options.get('extra_lines',0));continuation=int(options.get('continuation_pages',2))
    except (TypeError,ValueError):raise ValidationError('Choose valid writing-space options.')
    if not 0<=extra<=20 or not 1<=continuation<=10:raise ValidationError('Choose 0–20 extra lines and 1–10 continuation sheets.')
    reference=str(paper.get('reference') or paper.get('id','')[:10].upper())[:50]
    title=str(paper['title']);label=LABELS[kind]
    if paper.get('mode')=='worksheet' and kind in ('questions','booklet'):label='Question paper and answer booklet'
    profile=load_template(selected_theme(options))
    regular,bold=profile['font'],profile['bold_font']
    stream=BytesIO()
    doc=BaseDocTemplate(stream,pagesize=A4,title=title+' — '+label,author='RE Revi',leftMargin=27.8*mm,rightMargin=22*mm,topMargin=36*mm,bottomMargin=29*mm)
    width=160*mm
    body=ParagraphStyle('ExamBody',fontName=regular,fontSize=profile['font_size']*scale,leading=profile['leading']*scale,spaceAfter=3)
    small=ParagraphStyle('ExamSmall',parent=body,fontSize=7.5*scale,leading=10*scale,spaceAfter=5)
    heading=ParagraphStyle('ExamHeading',parent=body,fontName=bold,fontSize=profile['heading_size']*scale,leading=14*scale,spaceAfter=9)
    def p(value,style=body):return Paragraph(escape(str(value)).replace('\n','<br/>'),style)
    def page_header(canv,document,is_cover=False):
        canv._booklet_reference=reference;canv._booklet_template=profile;canv._booklet_is_cover=is_cover
        canv.saveState();canv.setFillColor(colors.black)
        if not is_cover:
            x,y,w,h=profile['border_mm'];border=profile['border']
            canv.setLineWidth(.55)
            if border in ('box','double'):
                canv.rect(x*mm,y*mm,w*mm,h*mm)
                if border=='double':canv.rect((x-1)*mm,(y-1)*mm,(w+2)*mm,(h+2)*mm)
                canv.setFont(regular,7);canv.drawCentredString(198*mm,265*mm,'Examiner')
                canv.drawCentredString(198*mm,261.5*mm,'only')
            elif border=='margin':
                canv.setFillColor(colors.HexColor(profile['accent']));canv.rect(19*mm,28*mm,6*mm,239*mm,fill=1,stroke=0)
                canv.setFillColor(colors.black);canv.line(25*mm,28*mm,25*mm,267*mm)
                canv.setFont(bold,8);canv.drawString(28*mm,272*mm,'RE Revi · '+profile['label'])
            elif border=='corners':
                canv.setLineWidth(1.4)
                for xx,yy,dx,dy in [(19,28,1,1),(191,28,-1,1),(19,267,1,-1),(191,267,-1,-1)]:
                    canv.line(xx*mm,yy*mm,(xx+8*dx)*mm,yy*mm);canv.line(xx*mm,yy*mm,xx*mm,(yy+8*dy)*mm)
                canv.setFont(bold,8);canv.drawString(28*mm,272*mm,'RE Revi · '+profile['label'])
            else:
                canv.setLineWidth(1.2);canv.line(20*mm,267*mm,191*mm,267*mm)
                canv.setFont(bold,8);canv.drawString(28*mm,272*mm,'RE Revi · '+profile['label'])
        canv.restoreState()
    cover_frame=Frame(*(v*mm for v in profile['cover_frame_mm']),leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='CoverFrame')
    body_frame=Frame(*(v*mm for v in profile['body_frame_mm']),leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='BodyFrame')
    doc.addPageTemplates([PageTemplate(id='Cover',frames=[cover_frame],onPage=lambda c,d:page_header(c,d,True)),PageTemplate(id='Body',frames=[body_frame],onPage=page_header)])
    content=[]
    if cover:
        content.extend([NextPageTemplate('Body'),TemplateCover(paper,options,label,reference,back_pages,profile),PageBreak()])
    else:
        doc.pageTemplates=doc.pageTemplates[1:]
        if kind!='continuation':content.extend([p(title,heading),p(label+' · Unofficial practice · '+reference,small)])
    if kind!='continuation' and paper.get('mode')=='full':
        content.extend([p('Answer all questions.',ParagraphStyle('StartInstructions',parent=body,alignment=1)),Spacer(1,4*mm)])
    elif paper.get('instructions') and kind!='continuation':content.extend([p(paper['instructions']),Spacer(1,3*mm)])
    spacing=LINE_PITCH_POINTS*max(1,scale)
    def continued_pages(count,description):
        for index in range(count):
            if content:content.append(PageBreak())
            content.extend([p(description+f' {index+1} of {count}',heading),p('Question number(s): __________    Name: ____________________',small),Spacer(1,3*mm),AnswerLines(CONTINUATION_LINES,width,CONTINUATION_PITCH_POINTS)])
    if kind=='continuation':
        # A cover already ends in a page break; avoid an extra blank page.
        if cover:content.pop()
        continued_pages(continuation,'Continuation sheet')
    else:
        previous_number=None;previous_topic=None
        for index,q in enumerate(paper['questions']):
            full=paper.get('mode')=='full'
            topic=q.get('section_topic') or q.get('topic','')
            if full and q['number']!=previous_number:
                if index:content.append(PageBreak())
                section=next((s[1] for s in COMPONENTS.get(q.get('component',''),{}).get('sections',[]) if s[0]==q['number']),topic)
                content.append(p(f'{q["number"]}. {section}',heading))
            elif full and q['part'] in ('c','d'):content.append(PageBreak())
            elif index and (options.get('breaks')=='question' or options.get('breaks')=='topic' and topic!=previous_topic or q['part'] in ('c','d')):content.append(PageBreak())
            number=f'({q["part"]})' if full else f'{index+1} ({q["part"]})'
            mark=f'[{q["marks"]}]'+(f' + [{q["spag"]} SPaG]' if q.get('spag') else '')
            prompt=Table([[p(number),p(q['prompt']),p(mark,ParagraphStyle('Marks',parent=body,alignment=2))]],colWidths=[11*mm,126*mm,23*mm])
            prompt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),1)]))
            if kind=='marking':
                content.extend([prompt,p(q.get('scheme_note',''),small),p(q.get('indicative_content') or 'No question-specific mark scheme supplied. Use general criteria as guidance; self-marking is optional.')])
                for field in ('rubric_url','original_scheme_url','spag_rubric_url'):
                    if q.get(field):content.append(p(field.replace('_',' ').title()+': '+q[field],small))
                content.extend(report_paragraphs(q,small))
            else:
                lines=answer_line_count(q['part'],q.get('component',''),q.get('number'))+extra
                if q.get('source_type')=='additional':content.append(p('Additional practice · '+q.get('source_label',''),small))
                if kind=='booklet' or options.get('lined_questions',True):
                    content.extend([KeepTogether([prompt,AnswerLines(2,width,spacing)]),AnswerLines(lines-2,width,spacing)])
                else:content.append(prompt)
            content.append(Spacer(1,3*mm));previous_number=q['number'];previous_topic=topic
    doc.build(content,canvasmaker=partial(NumberedBookletCanvas,extra_pages=back_pages))
    return append_additional_pages(stream.getvalue(),back_pages,paper,theme=selected_theme(options))
