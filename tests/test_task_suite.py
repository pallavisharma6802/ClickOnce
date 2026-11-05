import unittest
from click_once.tasks import catalog,arithmetic,solve24,evaluate,quote_totals,article
from fractions import Fraction
class TaskSuiteContract(unittest.TestCase):
    def test_balanced_distinct_catalog(self):
        cases=catalog();self.assertEqual(len(cases),30);self.assertEqual(len({c['id'] for c in cases}),30)
        for f in ('booking','math','wiki','email','offers'):
            self.assertEqual(len([c for c in cases if c['family']==f]),6)
            for level in ('easy','medium','hard'):self.assertEqual(len([c for c in cases if c['family']==f and c['level']==level]),2)
    def test_math_cases_have_independently_checked_witness(self):
        for c in catalog():
            if c['family']=='math':self.assertEqual(arithmetic(solve24(c['numbers']),c['numbers']),Fraction(24))
    def test_math_cannot_cheat_with_result_literal_or_code(self):
        for expr in ('24','__import__("os").system("echo bad")','2**24','1/0'):
            with self.assertRaises((ValueError,SyntaxError,ZeroDivisionError)):arithmetic(expr,[1,2,3,4])
    def test_math_alternative_solution_accepted(self):
        c=next(c for c in catalog() if c['family']=='math')
        self.assertTrue(evaluate(c,dict(saved=True,expression='(1+3)*(2+4)'))['success'])
    def test_unsaved_math_answer_fails(self):
        c=next(c for c in catalog() if c['family']=='math')
        self.assertFalse(evaluate(c,dict(saved=False,expression='1*2*3*4'))['success'])
    def test_email_independent_fields_and_stale_facts(self):
        c=next(c for c in catalog() if c['family']=='email' and c['level']=='hard')
        d=dict(to=c['recipient'],subject=c['event']+' '+c['date'],body=' '.join([c['event'],c['date'],c['time'],c['venue']]))
        self.assertTrue(evaluate(c,dict(saved=True,draft=d))['success'])
        d['body']+=' '+c['old_date'];self.assertFalse(evaluate(c,dict(saved=True,draft=d))['success'])
        from datetime import date
        stale=date.fromisoformat(c['old_date']);human=f'{stale:%B} {stale.day}, {stale.year}'
        d['body']=d['body'].replace(c['old_date'],human);self.assertFalse(evaluate(c,dict(saved=True,draft=d))['success'])
    def test_offers_wrong_or_out_of_stock_vendor_fails(self):
        c=next(c for c in catalog() if c['family']=='offers' and c['level']=='hard')
        t=quote_totals(c);v=min(t,key=t.get)
        self.assertTrue(evaluate(c,dict(saved=True,answer={'vendor':v,'total':f'{t[v]/100:.2f}'}))['success'])
        self.assertFalse(evaluate(c,dict(saved=True,answer={'vendor':c['offers'][0]['vendor'],'total':'0'}))['success'])
    def test_wiki_target_alone_not_enough(self):
        c=next(c for c in catalog() if c['family']=='wiki');u='https://en.wikipedia.org/wiki/'+c['target']
        self.assertFalse(evaluate(c,{},u,navigation=[])['success'])
        self.assertTrue(evaluate(c,{},u,navigation=[{'target':c['target']}])['success'])
        self.assertFalse(evaluate(c,{},u,navigation=[{}],violations=['search'])['success'])
    def test_wiki_namespaces_not_article_targets(self):
        self.assertIsNone(article('https://en.wikipedia.org/wiki/Special:Search'))
        self.assertIsNone(article('https://other.example/wiki/Foo'))

class MonetaryContract(unittest.TestCase):
    def test_independent_known_quote_totals(self):
        expected=['Aster','Aster','Birch','Birch','Elm','Elm'];cents=[2000,2137,7110,7501,5295,5644]
        cases=[c for c in catalog() if c['family']=='offers']
        for c,v,total in zip(cases,expected,cents):
            self.assertTrue(evaluate(c,dict(saved=True,answer={'vendor':v,'total':f'{total/100:.2f}'}))['success'])
    def test_excess_decimal_precision_not_silently_rounded(self):
        from click_once.tasks import money
        with self.assertRaises(ValueError):money('20.001')
