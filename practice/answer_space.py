"""Writing-space profile measured from the three Summer 2025 Eduqas Route A papers.

A/B share a page: 6 + 15 dotted lines. C has 24. D has 23 or 24
on its first page plus 25 on the continuation page. Vector pitch is
24.96963 pt; line width is approximately 160 mm. Compact text must
never reduce the baseline writing allocation.
"""
LINE_PITCH_POINTS = 24.96963
LINE_WIDTH_MM = 160
BASE_LINES = {'a':6,'b':15,'c':24,'d':49}
CONTINUATION_LINES = 25
CONTINUATION_PITCH_POINTS = 23.97084

def answer_line_count(part,component='',number=None):
    if part=='d' and component in ('component-1-general','component-2-christianity') and number==1:
        return 48
    return BASE_LINES[part]
