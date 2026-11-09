from copy import deepcopy
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from unittest.mock import patch
from types import SimpleNamespace
from practice.paper_builder import block_catalogue,generate_blueprint

class BlueprintValidationTests(SimpleTestCase):
    def test_catalogue_contains_topics_and_types_without_questions(self):
        rows=block_catalogue()
        self.assertEqual(len(rows),30)
        self.assertTrue(any(b['part']=='a' and b['theme']=='Christianity' and b['section']=='all' for b in rows))
        self.assertTrue(any(b['part']=='d' and b['theme']=='Life and Death' for b in rows))
        self.assertFalse(any('prompt' in b or 'id' in b for b in rows))

    def test_invalid_layouts_are_rejected_before_querying_the_bank(self):
        with patch('practice.paper_builder.public_questions') as bank:
            for raw in [None,{}, {'groups':[]},{'groups':[{}]}, {'groups':[{'id':'g','number':True,'title':'Topic','slots':[]}]},{'groups':[{'id':'g','number':1,'title':'Topic','slots':[{'component':'unknown','part':'b'}]}]}]:
                with self.subTest(raw=raw):
                    with self.assertRaises(ValidationError):generate_blueprint(raw)

    def test_block_resolves_a_bank_question_only_when_building(self):
        data={'title':'Custom practice','include_extra':False,'spag':True,'groups':[{'id':'g','number':7,'title':'My topic','slots':[{'component':'component-1-general','section':2,'part':'d','label':'c(ii)'}]}]}
        q=SimpleNamespace(pk='official-id',part='d',prompt='Original discussion prompt')
        payload={'id':'official-id','kind':'question','component':'component-1-general','number':2,'part':'d','topic':'Life and Death','prompt':'Original discussion prompt','marks':15,'spag':0}
        with patch('practice.paper_builder.public_questions') as bank,patch('practice.paper_builder.question_payload',return_value=payload.copy()),patch('practice.paper_builder.previous_wording',return_value=set()),patch('practice.paper_builder.sign_worksheet',side_effect=lambda p:p):
            bank.return_value.filter.return_value.filter.return_value=[q]
            result=generate_blueprint(data)
            bank.return_value.filter.assert_called_once_with(source_type='official')
            row=result['questions'][0]
            self.assertEqual((row['id'],row['number'],row['part']),('official-id',2,'d'))
            self.assertEqual(row['layout'],{'group':'g','number':7,'title':'My topic','part':'c(ii)'})
            self.assertEqual(result['numbering'],'exam')
