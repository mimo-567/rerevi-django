"""Editable vector layouts, based on an Eduqas reference paper, with live content.

All coordinates in the JSON templates are millimetres from the page's lower
left corner; *_top_mm values specify the top edge. No source questions, board
logos, old dates, barcodes or page numbers are embedded in the templates.
"""
import json
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable,Paragraph,Table,TableStyle

TEMPLATE_DIR=Path(__file__).with_name('data')/'pdf_templates'
THEME_IDS=frozenset({'eduqas-booklet'})

def load_template(theme):
    if theme not in THEME_IDS:raise ValueError('Unknown paper template')
    return json.loads((TEMPLATE_DIR/(theme+'.json')).read_text())

class TemplateCover(Flowable):
    """A single-page reusable cover populated from the selected practice set."""
    def __init__(self,paper,options,label,reference,back_pages,profile):
        super().__init__();self.paper=paper;self.options=options;self.label=label
        self.reference=reference;self.back_pages=back_pages;self.profile=profile
        self.width=174*mm;self.height=240*mm
    def draw(self):
        c=self.canv;t=self.profile;pos=t['cover'];paper=self.paper
        c.saveState();c.translate(-20*mm,-27*mm)
        regular=t['font'];bold=t['bold_font'];accent=colors.HexColor(t['accent'])
        def text(value,x,top,width=170,size=10,b=False):
            style=ParagraphStyle('CoverField',fontName=bold if b else regular,fontSize=size,leading=size*1.18)
            p=Paragraph(escape(str(value)).replace('\n','<br/>'),style)
            _,height=p.wrap(width*mm,250*mm);p.drawOn(c,x*mm,top*mm-height)
            return height/mm
        def box(x,y,w,h,fill=False):c.rect(x*mm,y*mm,w*mm,h*mm,fill=int(fill))
        c.setStrokeColor(colors.black);c.setFillColor(colors.black);c.setLineWidth(.55)
        if self.label=='Marking pack':
            text('RE REVI · EDUQAS GCSE RELIGIOUS STUDIES ROUTE A',20,275,170,10,True)
            text('MARKING BOOKLET',20,251,170,24,True)
            y=229
            y-=text(paper['title'],20,y,170,14,True)+5
            y-=text(paper.get('component_name','Mixed topics'),20,y,170,11)+5
            y-=text('Matching paper reference: '+self.reference,20,y,170,11)+5
            y-=text(f'{len(paper["questions"])} questions · {paper["total_marks"]} available marks',20,y,170,11)+15
            y-=text('HOW TO USE THIS BOOKLET',20,y,170,12,True)+7
            for note in [
                'Use this guide with the question paper bearing the same reference. Read each question alongside its marking criteria and indicative content.',
                'Indicative content is a guide, not an exhaustive checklist. Accurate answers in your own words may receive credit.',
                'Additional questions may have general criteria only. If no indicative content was supplied, this is stated beside the question.',
                'SPaG criteria apply only to questions where SPaG is included. Use the original scheme links for further guidance.',
            ]:y-=text(note,20,y,170,11)+6
            y-=10
            y-=text('UNOFFICIAL PRACTICE',20,y,170,12,True)+7
            text('Independently produced by RE Revi. Official source materials and additional practice are identified separately. This is a marking reference, not a candidate answer booklet.',20,y,170,10)
            c.restoreState();return
        if self.options.get('identity_fields',True):
            top=pos['candidate_top_mm']
            box(20,top-20,110,20);c.line(20*mm,(top-10)*mm,130*mm,(top-10)*mm)
            text('Surname',21,top-1,100,10);text('First name(s)',21,top-11,100,10)
            for x,title in [(133,'Centre\nnumber'),(163,'Candidate\nnumber')]:
                box(x,top-20,27,20);c.line(x*mm,(top-10)*mm,(x+27)*mm,(top-10)*mm)
                text(title,x+3,top-1,23,9)
        top=pos['heading_top_mm']
        text('RE REVI',20,top,30,16,True);text('GCSE',49,top,105,17,True)
        text(t['label']+' layout',145,top,46,9,True)
        text(self.reference,49,top-15,125,11)
        y=pos['banner_top_mm']
        c.setFillColor(accent);box(47,y-8,143,8,fill=True);c.setFillColor(colors.black)
        banner=self.label.upper()
        c.setFont(bold,12);c.drawString(49*mm,(y-5.8)*mm,banner);c.setFillColor(colors.black)
        title_top=pos['title_top_mm']
        h=text('RELIGIOUS STUDIES Route A',49,title_top,141,14,True)
        h+=text(paper.get('component_name','Mixed topics'),49,title_top-h-2,141,12,True)+2
        h+=text(paper['title'],49,title_top-h-2,141,9)+2
        timing=(str(paper['minutes'])+' minutes') if paper.get('minutes') and self.label in ('Practice question paper','Answer booklet') else 'Practice time: __________________'
        text(timing,49,title_top-h-3,141,11)
        text('UNOFFICIAL PRACTICE · Eduqas Route A content',20,174,170,8,True)
        rows=[['For marking use only','',''],['Question / style','Maximum\nmark','Mark\nawarded']]
        if paper.get('mode')=='full':
            for number in sorted({q['number'] for q in paper['questions']}):
                rows.append([str(number),str(sum(q['marks'] for q in paper['questions'] if q['number']==number)),''])
        else:
            for part in 'abcd':
                items=[q for q in paper['questions'] if q['part']==part]
                if items:rows.append([part.upper()+' × '+str(len(items)),str(sum(q['marks'] for q in items)),''])
        spag=sum(q.get('spag',0) for q in paper['questions'])
        if spag:rows.append(['SPaG',str(spag),''])
        rows.append(['Total',str(paper['total_marks']),''])
        table=Table(rows,colWidths=[24*mm,21*mm,18*mm],rowHeights=[8*mm,11*mm]+[7*mm]*(len(rows)-2))
        table.setStyle(TableStyle([('SPAN',(0,0),(-1,0)),('GRID',(0,0),(-1,-1),.5,colors.black),('FONTNAME',(0,0),(-1,-1),bold),('FONTSIZE',(0,0),(-1,-1),9),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,0),(-1,1),accent)]))
        _,height=table.wrap(174*mm,240*mm);table.drawOn(c,127*mm,pos['marks_top_mm']*mm-height)
        y=pos['instructions_top_mm']
        text('INSTRUCTIONS TO CANDIDATES',20,y,170,10,True)
        if self.label=='Marking pack':instructions='Use this pack with the practice set bearing the same reference. Indicative content is guidance, not an exhaustive checklist. Additional questions may have general criteria only.'
        elif self.label=='Continuation sheets':instructions='Use these sheets with the matching practice set. Write the question number clearly beside each continued answer.'
        else:instructions='Use black ink or black ball-point pen.\nWrite your details in the spaces above. Answer the selected questions.\nWrite in the spaces provided. Label any continued answers with the question number.'
        y-=8;y-=text(instructions,20,y,170,10)
        note=str(paper.get('instructions') or '')
        if note:y-=text(note[:220]+('… See question pages.' if len(note)>220 else ''),20,y-2,170,9)+2
        y=min(pos['information_top_mm'],y-12)
        text('INFORMATION FOR CANDIDATES',20,y,170,10,True)
        information='Marks are shown in brackets beside each question. SPaG is included only where shown.\nThis is an independently produced ReRevi practice document, not an official exam paper.\nThe selected visual theme does not change the Eduqas Route A specification or marking.'
        text(information,20,y-8,170,9)
        c.restoreState()
