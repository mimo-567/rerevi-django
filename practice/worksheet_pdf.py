from .examiner_reports import report_paragraphs
from io import BytesIO
from html import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from django.core.exceptions import ValidationError
from .pdf import FONT, BOLD, AnswerLines, exam_cover, pdf_finish_options
from .answer_space import answer_line_count, LINE_PITCH_POINTS, CONTINUATION_LINES, CONTINUATION_PITCH_POINTS

def make_worksheet_pdf(paper,options,kind):
    if not isinstance(options,dict) or kind not in ('questions','booklet','marking','continuation'): raise ValidationError('Invalid PDF options.')
    if kind=='marking':options={**options,'back_pages':0}
    if kind=='booklet':kind='questions'  # Old tabs use the combined download too.
    if kind=='continuation':
        from .additional_pdf import make_continuation_pdf
        return make_continuation_pdf(paper,options)
    from .exam_theme import selected_theme,make_exam_booklet
    if selected_theme(options)!='classic':return make_exam_booklet(paper,options,kind)
    include_cover,back_pages=pdf_finish_options(options)
    layout=options.get('layout','standard')
    if layout not in ('standard','large','compact'): raise ValidationError('Choose a valid print layout.')
    scale={'standard':1,'large':1.45,'compact':.9}[layout]
    try:
        extra=max(0,min(20,int(options.get('extra_lines',0))))
        continuation=max(1,min(10,int(options.get('continuation_pages',2))))
    except (TypeError,ValueError): raise ValidationError('Invalid writing-space options.')
    stream=BytesIO()
    duplex=options.get('duplex') is True
    doc=SimpleDocTemplate(stream,pagesize=A4,leftMargin=23*mm if duplex else 18*mm,rightMargin=23*mm if duplex else 18*mm,topMargin=20*mm,bottomMargin=20*mm,title=paper['title'])
    width=(164 if duplex else 174)*mm
    normal=ParagraphStyle('Body',fontName=FONT,fontSize=10.5*scale,leading=16*scale,spaceAfter=8)
    heading=ParagraphStyle('Heading',parent=normal,fontName=BOLD,fontSize=17*scale,leading=23*scale)
    small=ParagraphStyle('Small',parent=normal,fontSize=8.5*scale,leading=13*scale)
    def p(value,style=normal): return Paragraph(escape(str(value)).replace('\n','<br/>'),style)
    labels={'questions':'Question paper and answer booklet','booklet':'Answer booklet','marking':'Marking pack','continuation':'Continuation sheets'}
    cover_content=exam_cover(paper,labels[kind],width,back_pages) if include_cover else []
    content=[p(paper['title'],heading),p(labels[kind]+' · Reference '+paper['reference'],small),p('RE Revi · Unofficial practice · '+str(paper['total_marks'])+' marks',small)]
    if kind!='marking' and options.get('identity_fields',True): content += [p('Name: ____________________  Class: __________  Date: __________',small)]
    content += [p(paper['instructions']),Spacer(1,5*mm)]
    if kind=='continuation':
        content=[]
        for page in range(continuation):
            if page: content.append(PageBreak())
            content += [p(paper['title'][:80],small),p('Continuation sheet · Reference '+paper['reference'],small),p('Name: ____________________    Question number(s): __________',small),Spacer(1,3*mm),AnswerLines(CONTINUATION_LINES,width,CONTINUATION_PITCH_POINTS)]
    else:
        previous=None
        for index,q in enumerate(paper['questions']):
            topic=q.get('section_topic') or q['topic']
            if index and (options.get('breaks')=='question' or options.get('breaks')=='topic' and topic!=previous): content.append(PageBreak())
            label=f"{index+1} ({q['part']}) · {q['marks']} marks"+(f" + {q['spag']} SPaG" if q['spag'] else '')
            content += [p(label,small),p(q['prompt'])]
            if q['source_label']: content.append(p('Source: '+q['source_label'],small))
            if kind=='marking':
                content.append(p(q['scheme_note'] or 'Self-marking guidance.'))
                content.append(p(q['indicative_content'] or 'No question-specific mark scheme supplied. Use the linked general criteria as guidance; self-marking is optional.'))
                for field in ('rubric_url','original_scheme_url','spag_rubric_url'):
                    if q.get(field): content.append(p(field.replace('_',' ').title()+': '+q[field],small))
                content.extend(report_paragraphs(q,small))
            elif kind=='booklet' or options.get('lined_questions',True):
                lines=answer_line_count(q['part'],q.get('component',''),q.get('number'))+extra
                spacing=LINE_PITCH_POINTS*max(1,scale)
                # The flowable splits across pages without dropping any writing lines.
                content.append(AnswerLines(lines,width,spacing))
            content.append(Spacer(1,6*mm));previous=topic
    content=cover_content+content
    def footer(canvas,document):
        from .pdf_furniture import classic_footer
        classic_footer(canvas,document.page,paper,labels[kind])
    doc.build(content,onFirstPage=footer,onLaterPages=footer)
    from .additional_pdf import append_additional_pages
    return append_additional_pages(stream.getvalue(),back_pages,paper,document_label=labels[kind])
