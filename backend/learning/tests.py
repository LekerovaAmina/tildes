from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Module


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('load_content', verbosity=0)

    def setUp(self):
        self.client = APIClient(HTTP_X_DEVICE_ID='test-device')
        self.module = Module.objects.get(level_id='B2', number=1)

    def test_content(self):
        self.assertEqual(len(self.client.get('/api/levels/').json()), 5)
        self.assertEqual(len(self.client.get('/api/levels/b2/modules/').json()), 10)
        content = self.client.get('/api/levels/b2/content/').json()
        self.assertEqual(len(content['modules']), 10)
        detail = self.client.get(f'/api/modules/{self.module.id}/').json()
        self.assertTrue(detail['words'])
        self.assertNotIn('answer', detail['questions'][0])

    def test_cards_and_points(self):
        word = self.module.words.first()
        r = self.client.post('/api/cards/answer/', {'word_id': word.id, 'result': 'learned'}, format='json').json()
        self.assertEqual(r['points'], 10)
        r = self.client.post('/api/cards/complete/', {'module_id': self.module.id}, format='json').json()
        self.assertEqual((r['gained'], r['first']), (30, True))
        r = self.client.post('/api/cards/complete/', {'module_id': self.module.id}, format='json').json()
        self.assertEqual(r['gained'], 10)
        self.assertEqual(len(self.client.get('/api/cards/review/').json()), 20)

    def test_quiz_only_rewards_improvement(self):
        answers = [q.answer for q in self.module.questions.all()]
        r = self.client.post(f'/api/modules/{self.module.id}/quiz/', {'answers': answers}, format='json').json()
        self.assertEqual((r['correct'], r['gained']), (5, 25))
        r = self.client.post(f'/api/modules/{self.module.id}/quiz/', {'answers': answers}, format='json').json()
        self.assertEqual(r['gained'], 0)

    def test_device_id_required(self):
        self.assertEqual(APIClient().get('/api/progress/').status_code, 400)
