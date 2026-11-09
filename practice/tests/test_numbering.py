from copy import deepcopy
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from pypdf import PdfReader
from practice.numbering import question_label
from practice.worksheets import validate_paper,sign_worksheet
from practice.services import paper_from_token
from practice.worksheet_pdf import make_worksheet_pdf

def question(id,part='b',group='beliefs',display=4,label=None):
    return {'id':id,'kind':'question','component':'component-2-christianity','number':1,'part':part,'topic':'Beliefs','section_topic':'Beliefs and Teachings','prompt':'Explain Christian beliefs about God.' if part=='c' else 'Discuss this statement: belief matters.','marks':{'b':5,'c':8,'d':15}[part],'spag':6 if part=='d' else 0,'layout':{'group':group,'number':display,'title':'Christian Beliefs','part':label or part}}

def paper():
    return {'title':'Numbered practice','numbering':'exam','questions':[question('b'),question('d','d',label='c(ii)')]}

class NumberingTests(SimpleTestCase):
    def test_display_number_does_not_change_source_or_spag(self):
        p=validate_paper(paper());q=p['questions'][1]
        self.assertEqual((q['number'],q['part'],q['marks'],q['spag']),(1,'d',15,6))
        self.assertEqual(question_label(p,q,1,True),'4(c)(ii)')
        self.assertEqual(p['total_marks'],26)

    def test_portable_token_preserves_tree(self):
        p=sign_worksheet(paper());restored=paper_from_token(p['token'])
        self.assertEqual(restored['numbering'],'exam')
        self.assertEqual(restored['questions'][1]['layout'],p['questions'][1]['layout'])

    def test_legacy_files_still_use_sequential_labels(self):
        raw=paper();raw.pop('numbering')
        for q in raw['questions']:q.pop('layout')
        p=validate_paper(raw)
        self.assertEqual(question_label(p,p['questions'][1],1),'2 (d)')

    def test_ambiguous_or_inconsistent_trees_are_rejected(self):
        variants=[]
        p=paper();p['questions'][1]['layout']['part']='b';variants.append(p)
        p=paper();p['questions'][1]['layout']['title']='Different heading';variants.append(p)
        p=paper();p['questions'][1]['layout']['group']='other';variants.append(p)
        p=paper();p['questions'][1].pop('layout');variants.append(p)
        p=paper();p['questions'][1]['layout']['part']='<b>';variants.append(p)
        p=paper();p['questions'][1]['layout']['number']=True;variants.append(p)
        p=paper();p['questions'][1]['layout']['title']='x'*121;variants.append(p)
        p=paper();other=question('c','c','other',2);p['questions'].insert(1,other);variants.append(p)
        for p in variants:
            with self.subTest(p=p):
                with self.assertRaises(ValidationError):validate_paper(p)

    def test_shared_snapshot_uses_custom_numbering(self):
        from practice.sharing import create_share,load_share,delete_share
        p=sign_worksheet(paper())
        with TemporaryDirectory() as directory,self.settings(SHARE_DIR=Path(directory)):
            share=create_share({'consent':True,'paper_token':p['token'],'answers':{'question:d':'Sample answer'},'days':1})
            snapshot=load_share(share['token'])
            self.assertEqual(snapshot['questions'][1]['display_label'],'4(c)(ii)')
            self.assertEqual(snapshot['questions'][1]['group_title'],'Christian Beliefs')
            self.assertTrue(delete_share(share['token'],share['delete_token']))

    def test_both_pdf_themes_use_custom_labels_in_questions_and_marking(self):
        p=validate_paper(paper())
        for theme in ['classic','eduqas-booklet']:
            for document in ['questions','marking']:
                with self.subTest(theme=theme,document=document):
                    content=make_worksheet_pdf(p,{'theme':theme,'cover':False,'lined_questions':False},document)
                    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(content)).pages)
                    self.assertIn('4. Christian Beliefs',text)
                    self.assertIn('(c)(ii)',text)
                    self.assertRegex(text,r'6\s+SPaG')
