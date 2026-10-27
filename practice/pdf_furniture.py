"""Shared footer rendering for document pages and appended answer pages."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def booklet_footer(c,number,total,reference,is_cover=False):
    from .pdf import FONT
    c.saveState();c.setFillColor(colors.black);c.setFont(FONT,8)
    if not is_cover:c.drawCentredString(A4[0]/2,273*mm,str(number))
    c.drawString(20*mm,12*mm,f'{number:02d}')
    c.setFont(FONT,6.5)
    c.drawCentredString(A4[0]/2,12*mm,reference+' · RE Revi · Unofficial practice')
    c.drawRightString(191*mm,17*mm,f'Page {number} of {total}')
    c.setFont(FONT,5.5)
    c.drawCentredString(A4[0]/2,8*mm,'Official source materials © WJEC Eduqas; additional practice credited separately.')
    c.setFont(FONT,6.5)
    c.drawRightString(191*mm,12*mm,'Turn over.' if number<total else 'End of booklet')
    c.restoreState()

def classic_footer(c,number,paper,document_label=None):
    from .pdf import FONT
    c.saveState();c.setFont(FONT,7)
    if document_label:
        text='RE Revi · Unofficial practice · '+paper['reference']+' · '+document_label
    else:
        c.setFillColor(colors.HexColor('#555555'))
        text='RE Revi · Unofficial practice · Official source materials © WJEC Eduqas; additional practice credited separately'
    c.drawString(18*mm,12*mm,text)
    c.drawRightString(192*mm,12*mm,str(number));c.restoreState()
