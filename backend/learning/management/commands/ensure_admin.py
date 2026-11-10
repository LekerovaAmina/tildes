"""Создаёт учётку администратора по умолчанию, если её ещё нет.

    python manage.py ensure_admin                      # admin@admin.com / admin123
    python manage.py ensure_admin --reset-password     # вернуть пароль, если его поменяли

Email и пароль можно задать в backend/.env: DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD.
Только для разработки: при DJANGO_DEBUG=0 с паролем по умолчанию команда откажется работать.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from learning.models import User

DEFAULT_EMAIL = 'admin@admin.com'
DEFAULT_PASSWORD = 'admin123'


class Command(BaseCommand):
    help = 'Создаёт администратора по умолчанию (admin@admin.com / admin123), если его нет.'

    def add_arguments(self, parser):
        parser.add_argument('--reset-password', action='store_true', help='Сбросить пароль существующего админа')

    def handle(self, *args, **opts):
        email = os.environ.get('DEFAULT_ADMIN_EMAIL', DEFAULT_EMAIL).strip().lower()
        password = os.environ.get('DEFAULT_ADMIN_PASSWORD', DEFAULT_PASSWORD)

        if not settings.DEBUG and password == DEFAULT_PASSWORD:
            raise CommandError(
                'Пароль admin123 годится только для разработки. Задайте DEFAULT_ADMIN_PASSWORD в .env '
                'или создайте админа командой createsuperuser.'
            )

        user = User.objects.filter(email=email).first()
        if user is None:
            User.objects.create_superuser(email, password, display_name='Администратор')
            self.stdout.write(self.style.SUCCESS(f'Создан администратор {email}'))
            return

        changed = []
        if user.role != User.Role.ADMIN or not user.is_superuser or not user.is_active:
            user.role, user.is_superuser, user.is_active = User.Role.ADMIN, True, True
            changed.append('права админа')
        if opts['reset_password']:
            user.set_password(password)
            changed.append('пароль')
        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Администратор {email}: обновлены {", ".join(changed)}'))
        else:
            self.stdout.write(f'Администратор {email} уже есть')
