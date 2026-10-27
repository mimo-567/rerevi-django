from io import BytesIO
import math
from .answer_space import answer_line_count, LINE_PITCH_POINTS, LINE_WIDTH_MM
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Flowable
FONT_DIR=Path('/usr/share/fonts/truetype/dejavu')
if (FONT_DIR/'DejaVuSans.ttf').is_file():
    pdfmetrics.registerFont(TTFont('ExamSans',str(FONT_DIR/'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('ExamBold',str(FONT_DIR/'DejaVuSans-Bold.ttf')))
    FONT,BOLD='ExamSans','ExamBold'
else: FONT,BOLD='Helvetica','Helvetica-Bold'

class AnswerLines(Flowable):
    """Dotted writing lines that keep their allocation when split across pages."""
    def __init__(self,count,width,spacing=LINE_PITCH_POINTS):
        Flowable.__init__(self)
        self.count=int(count);self.width=min(width,LINE_WIDTH_MM*mm)
        self.spacing=spacing;self.height=self.count*spacing
    def wrap(self,available_width,available_height):
        self.width=min(self.width,available_width)
        return self.width,self.height
    def split(self,available_width,available_height):
        fit=min(self.count,math.floor((available_height+1e-6)/self.spacing))
        if fit<min(2,self.count):return []
        if fit==self.count:return [self]
        return [AnswerLines(fit,self.width,self.spacing),AnswerLines(self.count-fit,self.width,self.spacing)]
    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(colors.HexColor('#231f20'))
        self.canv.setLineWidth(.75);self.canv.setLineCap(1)
        self.canv.setDash([0,2.25])
        for i in range(self.count):
            y=self.height-(i+1)*self.spacing
            self.canv.line(0,y,self.width,y)
        self.canv.restoreState()

def make_pdf(paper,options=None):
    from .exam_theme import selected_theme,make_exam_booklet
    if selected_theme(options)!='classic':
        booklet_options=dict(options or {})
        booklet_options.setdefault('cover',paper['mode']=='full')
        return make_exam_booklet(paper,booklet_options,'questions')
    include_cover,back_pages=pdf_finish_options(options,default_cover=paper['mode']=='full')
    stream=BytesIO(); width=174*mm
    doc=SimpleDocTemplate(stream,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=21*mm,bottomMargin=20*mm,title=paper['title'],author='RE Revi')
    normal=ParagraphStyle('Body',fontName=FONT,fontSize=10.5,leading=16,spaceAfter=8)
    heading=ParagraphStyle('Heading',parent=normal,fontName=BOLD,fontSize=18,leading=24,spaceAfter=16)
    small=ParagraphStyle('Small',parent=normal,fontSize=8,leading=12)
    def p(text,style=normal): return Paragraph(escape(text).replace('\n','<br/>'),style)
    content=exam_cover(paper,'Question paper',width,back_pages) if include_cover else []
    if not include_cover:
        content.extend([p(paper['title'],heading),p(paper['component_name']),p(f"{paper['total_marks']} marks · Unofficial practice paper",small),p('Name: ____________________________________ Date: _________________'),Spacer(1,4*mm)])
    previous_number=None
    for index,q in enumerate(paper['questions']):
        if paper['mode']=='full':
            if q['number']!=previous_number:
                if index:content.append(PageBreak())
                content.append(p(f"{q['number']}. {q['topic']}",heading))
            elif q['part'] in ('c','d'): content.append(PageBreak())
        elif index and (q['part']=='d' or (paper['mode']=='custom' and paper['questions'][index-1]['part']=='d')):
            content.append(PageBreak())
        label=f"{q['number']}({q['part']})" if paper['mode']=='full' else str(index+1)+f" ({q['part']})"
        question=p(f"{label}  {q['prompt']}\n[{q['marks']} marks"+(f" + {q['spag']} SPaG" if q['spag'] else '')+']')
        lines=answer_line_count(q['part'],q.get('component',''),q.get('number'))
        if q.get('source_type')=='additional': content.append(p(q['source_label']+' · No question-specific mark scheme supplied.' if not q.get('indicative_content') else q['source_label'],small))
        content.extend([KeepTogether([question,AnswerLines(2,width)]),AnswerLines(lines-2,width),Spacer(1,7*mm)])
        previous_number=q['number']
    def footer(canvas,doc):
        from .pdf_furniture import classic_footer
        classic_footer(canvas,doc.page,paper)
    doc.build(content,onFirstPage=footer,onLaterPages=footer)
    from .additional_pdf import append_additional_pages
    return append_additional_pages(stream.getvalue(),back_pages,paper)


def pdf_finish_options(options,default_cover=True):
    from django.core.exceptions import ValidationError
    if options is None:options={}
    if not isinstance(options,dict):raise ValidationError('Invalid PDF options.')
    try:back_pages=int(options.get('back_pages',0))
    except (TypeError,ValueError):raise ValidationError('Choose 0–10 additional pages.')
    if not 0<=back_pages<=10:raise ValidationError('Choose 0–10 additional pages.')
    return options.get('cover',default_cover) is True,back_pages

def exam_cover(paper,document_label,width,back_pages=0):
    """An independently branded exam-style cover for every document type."""
    if document_label=='Marking pack':return marking_cover(paper,width)
    from reportlab.platypus import Table,TableStyle
    body=ParagraphStyle('CoverBody',fontName=FONT,fontSize=9,leading=12,spaceAfter=5)
    heading=ParagraphStyle('CoverTitle',parent=body,fontName=BOLD,fontSize=15,leading=20,spaceAfter=8)
    small=ParagraphStyle('CoverSmall',parent=body,fontSize=8,leading=10)
    def p(value,style=body):return Paragraph(escape(str(value)).replace('\n','<br/>'),style)
    width=min(width,160*mm)
    candidate=Table([
        [p('Surname: __________________________'),p('Centre number: ______________')],
        [p('First name(s): ______________________'),p('Candidate number: ___________')],
        [p('Class: ____________________________'),p('Date: ______________________')],
    ],colWidths=[width*.60,width*.40])
    candidate.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.7,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    content=[p('RE REVI · GCSE RELIGIOUS STUDIES · ROUTE A',small),Spacer(1,5*mm),candidate,Spacer(1,6*mm),p(paper['title'],heading),p(document_label+' · '+paper.get('component_name','Religious Studies')),p('UNOFFICIAL PRACTICE — independently produced by RE Revi',small)]
    reference=paper.get('reference') or str(paper.get('id',''))[:10].upper()
    if reference:content.append(p('Paper reference: '+reference,small))
    if paper.get('minutes'):
        minutes=paper['minutes'];content.append(p(f'Time allowed: {minutes} minutes'))
    else:content.append(p('Practice time: ____________________'))
    rows=[[p('Question / style',small),p('Maximum marks',small),p('Your mark',small)]]
    if paper.get('mode')=='full':
        for number in sorted({q['number'] for q in paper['questions']}):
            maximum=sum(q['marks'] for q in paper['questions'] if q['number']==number)
            rows.append([p('Question '+str(number),small),p(maximum,small),''])
    else:
        for part in ('a','b','c','d'):
            questions=[q for q in paper['questions'] if q['part']==part]
            if questions:rows.append([p(part.upper()+f' ({len(questions)} questions)',small),p(sum(q['marks'] for q in questions),small),''])
    spag=sum(q.get('spag',0) for q in paper['questions'])
    if spag:rows.append([p('SPaG (eligible questions)',small),p(spag,small),''])
    rows.append([p('Total',small),p(paper['total_marks'],small),''])
    scores=Table(rows,colWidths=[width*.55,width*.25,width*.20],hAlign='LEFT')
    scores.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.black),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f2f2f2')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    content.extend([Spacer(1,4*mm),scores,Spacer(1,6*mm),p('INSTRUCTIONS',ParagraphStyle('CoverSection',parent=body,fontName=BOLD))])
    if document_label=='Marking pack':
        instructions='Use this pack to review the matching practice set. Indicative content is not an exhaustive checklist. Additional practice may have general criteria without question-specific guidance.'
    elif document_label=='Continuation sheets':
        instructions='Use these sheets with the matching practice paper. Write your name and the question number(s) clearly on each sheet.'
    else:
        instructions='Use black ink or black ball-point pen. Follow the instructions in your practice set. Write answers in the spaces provided and label any continued answers clearly.'
    content.append(p(instructions))
    if paper.get('mode')=='full':content.append(p('Answer all questions. The marks for each question are shown in brackets. Refer to relevant religious wisdom and authority where required.'))
    elif paper.get('instructions'):
        text=paper['instructions']
        content.append(p(text[:180]+('… See the full worksheet instructions on the following page.' if len(text)>180 else '')))
    content.extend([p('INFORMATION',ParagraphStyle('CoverInformation',parent=body,fontName=BOLD)),p('SPaG marks are included only where shown. This is an unofficial practice document, not an Eduqas examination paper. Official source material and additional practice are identified separately.',small),PageBreak()])
    return content



def marking_cover(paper,width):
    """Reference cover for marking, with no candidate or score-entry fields."""
    heading=ParagraphStyle('MarkingCoverTitle',fontName=BOLD,fontSize=24,leading=30,spaceAfter=16)
    body=ParagraphStyle('MarkingCoverBody',fontName=FONT,fontSize=11,leading=16,spaceAfter=12)
    subheading=ParagraphStyle('MarkingCoverSection',parent=body,fontName=BOLD,fontSize=13,leading=18)
    def p(value,style=body):return Paragraph(escape(str(value)).replace('\n','<br/>'),style)
    reference=paper.get('reference') or str(paper.get('id',''))[:10].upper()
    return [p('RE REVI · EDUQAS GCSE RELIGIOUS STUDIES ROUTE A',body),Spacer(1,10*mm),p('Marking booklet',heading),p(paper['title'],subheading),p(paper.get('component_name','Mixed topics')),p('Matching paper reference: '+reference),p(f'{len(paper["questions"])} questions · {paper["total_marks"]} available marks'),Spacer(1,10*mm),p('HOW TO USE THIS BOOKLET',subheading),p('Use this guide with the question paper bearing the same reference. Read each question alongside its marking criteria and indicative content.'),p('Indicative content is a guide, not an exhaustive checklist. Accurate answers in your own words may receive credit. Additional questions may have general criteria only; missing indicative content is not an answer key.'),p('SPaG criteria apply only to questions where SPaG is included. Use the original scheme links for further guidance.'),Spacer(1,8*mm),p('UNOFFICIAL PRACTICE',subheading),p('Independently produced by RE Revi. Official source materials and additional practice are identified separately. This is a marking reference, not a candidate answer booklet.'),PageBreak()]
