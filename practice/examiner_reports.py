"""Official, verified examiner-report references; guidance is kept separate from schemes."""
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def reports():
    return json.loads((Path(__file__).parent/'data'/'examiner_reports.json').read_text())

def report_fields(subject,paper,year=None,series='',official=True):
    rows=[r for r in reports() if r['subject']==subject and r['paper']==paper]
    if not rows:return {'examiner_report_url':'','examiner_report_title':'','examiner_report_note':''}
    name=str(series).strip().lower().split(' ')[0]
    matches=[r for r in rows if official and str(r['year'])==str(year) and r['series'].lower()==name]
    report=(matches or sorted(rows,key=lambda r:(r['year'],r['series'] in ('November','Autumn')),reverse=True))[0]
    note=('Matches the original exam series. This report covers the wider paper or qualification; use the mark scheme to award marks.' if matches else f"General examiner advice from {report['series']} {report['year']}; this is not a report on this practice set. Use the relevant mark scheme to award marks.")
    return {'examiner_report_url':report['url'],'examiner_report_title':report['title'],'examiner_report_note':note}


def report_paragraphs(question,style):
    from html import escape
    from reportlab.platypus import Paragraph
    url=question.get('examiner_report_url','')
    if not url:return []
    title=question.get('examiner_report_title') or 'Official examiner report'
    note=question.get('examiner_report_note','Examiner advice supplements the mark scheme.')
    return [Paragraph('<link href="'+escape(url,quote=True)+'" color="#303b6b"><u>'+escape(title)+'</u></link>',style),Paragraph(escape(note),style)]
