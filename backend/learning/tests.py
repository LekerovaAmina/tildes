from django.core.management import call_command
from django.db import connection
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from rest_framework.test import APIClient

from .models import (
    AuditLog,
    CardAnswer,
    CardSession,
    Module,
    PointTransaction,
    QuizAttempt,
    QuizAttemptAnswer,
    User,
    UserActivityDay,
    UserLessonProgress,
    Word,
)

SCHEMA_TABLES = {
    # Пользователи и контент
    'levels', 'users', 'modules', 'media_files', 'lessons', 'lesson_blocks', 'words', 'texts',
    'grammar_rules', 'grammar_table_rows', 'grammar_examples', 'quizzes', 'quiz_questions', 'quiz_options',
    # Админка
    'audit_log',
    # Прогресс ученика
    'point_transactions', 'user_activity_days', 'user_word_progress', 'user_lesson_progress',
    'card_sessions', 'card_answers', 'quiz_attempts', 'quiz_attempt_answers',
}


class SchemaTests(TestCase):
    def test_all_23_tables_exist(self):
        self.assertEqual(len(SCHEMA_TABLES), 23)
        self.assertLessEqual(SCHEMA_TABLES, set(connection.introspection.table_names()))

    def test_reserved_tables_not_created_yet(self):
        tables = set(connection.introspection.table_names())
        self.assertFalse({'listening_tasks', 'speaking_tasks', 'writing_tasks'} & tables)


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('load_content', verbosity=0)

    def setUp(self):
        self.client = APIClient(HTTP_X_DEVICE_ID='test-device')
        self.module = Module.objects.get(level__code='B2', number=1)
        self.words = list(Word.objects.filter(lesson__module=self.module))

    def answers(self):
        detail = self.client.get(f'/api/modules/{self.module.id}/').json()
        from .models import QuizQuestion
        return [
            next(i for i, o in enumerate(QuizQuestion.objects.get(pk=q['id']).options.all()) if o.is_correct)
            for q in detail['questions']
        ]

    def test_content_structure(self):
        self.assertEqual(self.module.lessons.count(), 4)
        main = self.module.lessons.first()
        self.assertEqual(main.code, '1.1')
        self.assertEqual(
            list(main.blocks.values_list('block_type', flat=True)), ['words', 'cards', 'grammar', 'text', 'quiz'],
        )
        self.assertEqual(Word.objects.count(), 225)

    def test_content_api(self):
        self.assertEqual(len(self.client.get('/api/levels/').json()), 5)
        self.assertEqual(len(self.client.get('/api/levels/b2/modules/').json()), 10)
        content = self.client.get('/api/levels/b2/content/').json()
        self.assertEqual(len(content['modules']), 10)
        detail = self.client.get(f'/api/modules/{self.module.id}/').json()
        self.assertEqual(len(detail['words']), len(self.words))
        self.assertEqual(len(detail['lessons']), 4)
        self.assertTrue(detail['grammar']['table'])
        self.assertTrue(detail['text']['paragraphs'])
        self.assertNotIn('answer', detail['questions'][0])
        self.assertEqual(len(detail['questions'][0]['options']), 4)

    def test_unpublished_content_hidden(self):
        Module.objects.filter(pk=self.module.pk).update(status='draft')
        self.assertEqual(len(self.client.get('/api/levels/b2/modules/').json()), 9)
        self.assertEqual(self.client.get(f'/api/modules/{self.module.id}/').status_code, 404)

    def test_cards_points_and_session(self):
        r = self.client.post('/api/cards/answer/', {'word_id': self.words[0].id, 'result': 'learned'}, format='json').json()
        self.assertEqual(r['points'], 10)
        self.client.post('/api/cards/answer/', {'word_id': self.words[1].id, 'result': 'again'}, format='json')
        r = self.client.post('/api/cards/complete/', {'module_id': self.module.id}, format='json').json()
        self.assertEqual((r['gained'], r['first'], r['points']), (30, True, 42))

        session = CardSession.objects.get()
        self.assertEqual((session.mode, session.module_id, session.cards_total), ('topic', self.module.id, 2))
        self.assertEqual((session.learned_count, session.again_count, session.points_earned), (1, 1, 42))
        self.assertIsNotNone(session.finished_at)
        self.assertEqual(CardAnswer.objects.filter(session=session).count(), 2)

        r = self.client.post('/api/cards/complete/', {'module_id': self.module.id}, format='json').json()
        self.assertEqual((r['gained'], r['first']), (10, False))
        self.assertEqual(len(self.client.get('/api/cards/review/').json()), 20)

        user = User.objects.get()
        self.assertEqual(sum(PointTransaction.objects.values_list('amount', flat=True)), user.points)
        self.assertTrue(user.is_device)
        self.assertEqual(UserActivityDay.objects.count(), 1)

    def test_quiz_only_rewards_improvement(self):
        answers = self.answers()
        wrong = [(a + 1) % 4 for a in answers]
        r = self.client.post(f'/api/modules/{self.module.id}/quiz/', {'answers': wrong[:2] + answers[2:]}, format='json').json()
        self.assertEqual((r['correct'], r['gained']), (3, 15))
        r = self.client.post(f'/api/modules/{self.module.id}/quiz/', {'answers': answers}, format='json').json()
        self.assertEqual((r['correct'], r['gained'], r['best']), (5, 10, 5))
        r = self.client.post(f'/api/modules/{self.module.id}/quiz/', {'answers': answers}, format='json').json()
        self.assertEqual(r['gained'], 0)
        self.assertEqual(QuizAttempt.objects.count(), 3)
        self.assertEqual(QuizAttemptAnswer.objects.count(), 15)

    def test_progress_and_reset(self):
        self.client.patch('/api/progress/', {'name': 'Амина', 'level': 'b2'}, format='json')
        self.client.post('/api/topics/read/', {'module_id': self.module.id, 'section': 'grammar'}, format='json')
        self.client.post('/api/cards/answer/', {'word_id': self.words[0].id, 'result': 'again'}, format='json')
        self.client.post('/api/cards/complete/', {'module_id': self.module.id}, format='json')
        self.client.post(f'/api/modules/{self.module.id}/quiz/', {'answers': self.answers()}, format='json')

        p = self.client.get('/api/progress/').json()
        self.assertEqual((p['name'], p['level'], p['points'], p['streak']), ('Амина', 'B2', 57, 1))
        self.assertEqual(p['completedCardTopics'], [self.module.id])
        self.assertEqual(p['quizBest'], {str(self.module.id): 5})
        self.assertEqual(p['readTopics'][str(self.module.id)], {'words': False, 'grammar': True, 'text': False})
        self.assertEqual(p['wordStats'][str(self.words[0].id)], {'learned': 0, 'again': 1})

        lb = self.client.get('/api/leaderboard/').json()
        self.assertEqual((lb[0]['name'], lb[0]['me']), ('Амина', True))

        self.client.post('/api/progress/reset/')
        p = self.client.get('/api/progress/').json()
        self.assertEqual((p['points'], p['wordStats'], p['completedCardTopics']), (0, {}, []))
        self.assertFalse(PointTransaction.objects.exists())

    def test_reload_keeps_progress(self):
        self.client.post('/api/cards/answer/', {'word_id': self.words[0].id, 'result': 'learned'}, format='json')
        self.client.post('/api/cards/complete/', {'module_id': self.module.id}, format='json')
        call_command('load_content', verbosity=0)
        self.assertTrue(Word.objects.filter(pk=self.words[0].id).exists())
        self.assertEqual(UserLessonProgress.objects.get().cards_completions, 1)
        self.assertEqual(self.client.get('/api/progress/').json()['completedCardTopics'], [self.module.id])

    def test_device_id_required(self):
        self.assertEqual(APIClient().get('/api/progress/').status_code, 400)


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('load_content', verbosity=0)

    def test_roles(self):
        student = User.objects.create_user('s@example.com', 'pass-12345')
        editor = User.objects.create_user('e@example.com', 'pass-12345', role=User.Role.EDITOR)
        admin = User.objects.create_superuser('a@example.com', 'pass-12345')
        self.assertFalse(student.is_staff)
        self.assertTrue(editor.has_perm('learning.change_word'))
        self.assertFalse(editor.has_perm('learning.change_user'))
        self.assertTrue(admin.has_perm('learning.change_user'))

    def test_edit_writes_audit_log(self):
        admin = User.objects.create_superuser('a@example.com', 'pass-12345')
        self.client.force_login(admin)
        word = Word.objects.first()
        r = self.client.post(f'/admin/learning/word/{word.id}/change/', {
            'lesson': word.lesson_id, 'kz': word.kz, 'ru': 'новый перевод', 'transcription': '',
            'part_of_speech': '', 'example_kz': '', 'example_ru': '', 'sort_order': word.sort_order,
            'status': 'published',
        })
        self.assertEqual(r.status_code, 302)
        log = AuditLog.objects.get()
        self.assertEqual((log.action, log.entity_type, log.entity_id, log.actor), ('update', 'words', word.id, admin))
        self.assertEqual(log.changes['ru'][1], 'новый перевод')

    def test_admin_pages_open(self):
        self.client.force_login(User.objects.create_superuser('a@example.com', 'pass-12345'))
        for path in ['', 'learning/user/', 'learning/user/add/', 'learning/module/', 'learning/lesson/1/change/',
                     'learning/grammarrule/1/change/', 'learning/quizquestion/1/change/', 'learning/auditlog/',
                     'learning/mediafile/add/', 'learning/pointtransaction/']:
            self.assertEqual(self.client.get('/admin/' + path).status_code, 200, path)


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_login_me_logout(self):
        r = self.client.post('/api/auth/register/', {'email': 'Aru@Example.kz', 'password': 'Qazaq-Til-2026', 'name': 'Ару'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data['user']['email'], 'aru@example.kz')
        user = User.objects.get(email='aru@example.kz')
        self.assertTrue(user.check_password('Qazaq-Til-2026'))

        r = self.client.post('/api/auth/login/', {'email': 'aru@example.kz', 'password': 'wrong-pass-1'}, format='json')
        self.assertIn(r.status_code, (401, 403))

        r = self.client.post('/api/auth/login/', {'email': 'ARU@example.kz', 'password': 'Qazaq-Til-2026'}, format='json')
        self.assertEqual(r.status_code, 200)
        token = r.data['token']

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        r = self.client.get('/api/auth/me/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['user']['name'], 'Ару')
        # Остальной API видит вошедшего пользователя без X-Device-Id
        self.assertEqual(self.client.get('/api/progress/').status_code, 200)

        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 200)
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))

    def test_register_validation(self):
        self.client.post('/api/auth/register/', {'email': 'a@b.kz', 'password': 'Qazaq-Til-2026'}, format='json')
        r = self.client.post('/api/auth/register/', {'email': 'A@b.kz', 'password': 'Qazaq-Til-2026'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.data)
        r = self.client.post('/api/auth/register/', {'email': 'c@b.kz', 'password': '123'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)

    def test_register_keeps_device_progress(self):
        self.client.get('/api/progress/', HTTP_X_DEVICE_ID='dev-1')
        device_user = User.objects.get(email='dev-1@' + User.DEVICE_EMAIL_DOMAIN)
        r = self.client.post('/api/auth/register/', {'email': 'd@b.kz', 'password': 'Qazaq-Til-2026'}, format='json', HTTP_X_DEVICE_ID='dev-1')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['user']['id'], device_user.id)
        self.assertFalse(User.objects.filter(email='dev-1@' + User.DEVICE_EMAIL_DOMAIN).exists())

    def test_staff_login_opens_admin(self):
        User.objects.create_superuser('boss@b.kz', 'Qazaq-Til-2026')
        r = self.client.post('/api/auth/login/', {'email': 'boss@b.kz', 'password': 'Qazaq-Til-2026'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['redirect'], '/admin/')
        self.assertTrue(r.data['user']['is_staff'])
        # Сессия открыта — админка пускает без повторного входа
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_student_login_has_no_redirect(self):
        self.client.post('/api/auth/register/', {'email': 's@b.kz', 'password': 'Qazaq-Til-2026'}, format='json')
        r = self.client.post('/api/auth/login/', {'email': 's@b.kz', 'password': 'Qazaq-Til-2026'}, format='json')
        self.assertNotIn('redirect', r.data)
        self.assertFalse(r.data['user']['is_staff'])
        self.assertEqual(self.client.get('/admin/').status_code, 302)  # на страницу входа админки

    def test_admin_login_through_frontend_address(self):
        """Админка через прокси Vite: форма входа приходит с Origin http://localhost:5173 — не 403."""
        User.objects.create_superuser('boss@b.kz', 'Qazaq-Til-2026')
        browser = Client(enforce_csrf_checks=True)
        browser.get('/admin/login/')
        r = browser.post(
            '/admin/login/?next=/admin/',
            {'username': 'boss@b.kz', 'password': 'Qazaq-Til-2026', 'csrfmiddlewaretoken': browser.cookies['csrftoken'].value},
            HTTP_ORIGIN='http://localhost:5173',
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/admin/')

    @override_settings(DEBUG=True)
    def test_ensure_admin_creates_default_admin(self):
        call_command('ensure_admin', verbosity=0)
        call_command('ensure_admin', verbosity=0)  # повторный запуск ничего не ломает
        admin = User.objects.get(email='admin@admin.com')
        self.assertTrue(admin.is_superuser and admin.is_staff)
        self.assertTrue(admin.check_password('admin123'))
        r = self.client.post('/api/auth/login/', {'email': 'admin@admin.com', 'password': 'admin123'}, format='json')
        self.assertEqual(r.data['redirect'], '/admin/')

    def test_ensure_admin_refuses_default_password_in_production(self):
        with self.assertRaises(CommandError):
            call_command('ensure_admin', verbosity=0)  # в тестах DEBUG=False, как в продакшене
        self.assertFalse(User.objects.filter(email='admin@admin.com').exists())

