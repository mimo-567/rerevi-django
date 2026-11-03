from types import SimpleNamespace
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from practice.selection import choose_slots,previous_wording,wording_key

def question(pk,prompt,part='b'):
    return SimpleNamespace(pk=pk,prompt=prompt,part=part)

class SelectionTests(SimpleTestCase):
    def test_repeated_wording_in_different_records_is_not_fresh(self):
        a=question('a','Describe TWO beliefs about God.')
        copy=question('copy','Describe two beliefs about God!')
        fresh=question('fresh','Describe two beliefs about prayer.')
        for _ in range(20):
            picked=choose_slots([[a,copy,fresh]]*2)
            self.assertEqual(len({wording_key(q) for q in picked}),2)

    def test_earlier_choice_moves_for_a_constrained_slot(self):
        a=question('a','First question');b=question('b','Second question')
        for _ in range(20):self.assertEqual([q.pk for q in choose_slots([[a,b],[a]])],['b','a'])

    def test_previous_wording_is_avoided_until_exhausted(self):
        a=question('a','First question');copy=question('copy','FIRST question!');b=question('b','Second question')
        for _ in range(20):self.assertEqual(choose_slots([[a,copy,b]],{wording_key(a)})[0].pk,'b')
        self.assertEqual(choose_slots([[a]],{wording_key(a)})[0].pk,'a')

    def test_exhausted_wording_can_repeat_without_repeating_a_record(self):
        a=question('a','Same question');b=question('b','Same question');c=question('c','Same question')
        for _ in range(20):
            picked=choose_slots([[a,b],[a],[b,c]])
            self.assertEqual(len({q.pk for q in picked}),3)
            self.assertEqual(picked[1].pk,'a')

    def test_discussion_instructions_do_not_disguise_repeated_statements(self):
        a=question('a','“Religion helps society.”\nDiscuss this statement. Consider two views.','d')
        b=question('b','"Religion helps society!"\nDiscuss this statement. Refer to religious beliefs.','d')
        self.assertEqual(wording_key(a),wording_key(b))

    def test_insufficient_records_fails_instead_of_looping(self):
        a=question('a','Only question')
        with self.assertRaises(ValidationError):choose_slots([[a],[a]])

    def test_invalid_previous_references_are_rejected_without_queries(self):
        for avoid in [None,[{}],[{'kind':[],'id':'a'}],[{'kind':'keyword','id':'not-a-number'}],[{}]*61]:
            with self.subTest(avoid=avoid):
                with self.assertRaises(ValidationError):previous_wording({'avoid':avoid})
