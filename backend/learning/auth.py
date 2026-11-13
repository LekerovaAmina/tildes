"""Авторизация по email и паролю — таблица users + токены DRF (таблица authtoken_token).

POST /api/auth/register/  {email, password, name?}  → {token, user}
POST /api/auth/login/     {email, password}         → {token, user}
POST /api/auth/logout/    (Authorization: Token …)   → токен удаляется
GET  /api/auth/me/        (Authorization: Token …)   → {user}

Если при регистрации передан X-Device-Id и у устройства уже есть прогресс, анонимный
пользователь устройства превращается в аккаунт — баллы и прогресс сохраняются.
"""

from django.contrib.auth import authenticate, password_validation
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from . import services
from .models import User


class AuthThrottle(AnonRateThrottle):
    """Ограничение попыток входа/регистрации с одного IP (REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth'])."""
    scope = 'auth'


def user_data(user):
    return {
        'id': user.id,
        'email': user.email,
        'name': user.display_name,
        'role': user.role,
        'points': user.points,
        'level': user.current_level.code if user.current_level_id else None,
        # Сотрудник (admin / editor) — фронтенд отправляет его в админку
        'is_staff': user.is_staff,
        'date_joined': user.date_joined,
    }


def token_response(user, code=status.HTTP_200_OK):
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': user_data(user)}, status=code)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)
    name = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if email.endswith('@' + User.DEVICE_EMAIL_DOMAIN):
            raise serializers.ValidationError('Этот email нельзя использовать.')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email

    def validate(self, attrs):
        probe = User(email=attrs['email'], display_name=attrs.get('name', ''))
        try:
            password_validation.validate_password(attrs['password'], probe)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)


# --- Схемы ответов (используются только в документации OpenAPI / Swagger) ---

class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    name = serializers.CharField(allow_blank=True)
    role = serializers.ChoiceField(choices=['student', 'editor', 'admin'])
    points = serializers.IntegerField()
    level = serializers.CharField(allow_null=True, help_text='Код текущего уровня, например b2')
    is_staff = serializers.BooleanField(help_text='Сотрудник (admin / editor) — фронтенд ведёт его в админку')
    date_joined = serializers.DateTimeField()


class TokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField(help_text='Передавайте в заголовке Authorization: Token <token>')
    user = UserSerializer()


class LoginResponseSerializer(TokenResponseSerializer):
    redirect = serializers.CharField(required=False, help_text='Только для сотрудников: /django-admin/')


class MeResponseSerializer(serializers.Serializer):
    user = UserSerializer()


class OkSerializer(serializers.Serializer):
    ok = serializers.BooleanField()


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


VALIDATION_ERROR = OpenApiResponse(
    OpenApiTypes.OBJECT,
    description='Ошибка в полях: {"<поле>": ["сообщение", ...]}',
    examples=[OpenApiExample('Короткий пароль', value={'password': ['Введённый пароль слишком короткий.']})],
)
THROTTLED = OpenApiResponse(DetailSerializer, description='Слишком много попыток с этого IP (AUTH_THROTTLE_RATE)')
NOT_AUTHENTICATED = OpenApiResponse(DetailSerializer, description='Нет заголовка Authorization или токен недействителен')


@extend_schema(
    tags=['auth'],
    summary='Регистрация',
    description='Создаёт пользователя и возвращает токен. Если передан X-Device-Id, анонимный '
                'пользователь устройства становится аккаунтом — баллы и прогресс сохраняются.',
    auth=[],
    parameters=[OpenApiParameter('X-Device-Id', str, OpenApiParameter.HEADER, required=False,
                                 description='Идентификатор устройства анонимного пользователя')],
    request=RegisterSerializer,
    responses={201: TokenResponseSerializer, 400: VALIDATION_ERROR, 429: THROTTLED},
)
@api_view(['POST'])
@authentication_classes([])
@throttle_classes([AuthThrottle])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    data = s.validated_data

    with transaction.atomic():
        user = None
        device_id = request.headers.get('X-Device-Id', '').strip()[:64]
        if device_id:
            # Анонимный пользователь устройства становится аккаунтом — прогресс не теряется
            user = User.objects.select_for_update().filter(email=services.device_email(device_id)).first()
        if user is not None:
            user.email = data['email']
            if data.get('name'):
                user.display_name = data['name']
        else:
            user = User(email=data['email'], display_name=data.get('name', ''))
        user.set_password(data['password'])
        user.save()

    return token_response(user, status.HTTP_201_CREATED)


@extend_schema(
    tags=['auth'],
    summary='Вход по email и паролю',
    auth=[],
    request=LoginSerializer,
    responses={
        200: LoginResponseSerializer,
        400: VALIDATION_ERROR,
        401: OpenApiResponse(DetailSerializer, description='Неверный email или пароль',
                             examples=[OpenApiExample('Неверный пароль', value={'detail': 'Неверный email или пароль.'})]),
        429: THROTTLED,
    },
)
@api_view(['POST'])
@authentication_classes([])
@throttle_classes([AuthThrottle])
def login(request):
    s = LoginSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = authenticate(request, email=s.validated_data['email'].strip().lower(), password=s.validated_data['password'])
    if user is None:
        # Явно 401: при authentication_classes([]) DRF превращает AuthenticationFailed в 403,
        # потому что ему нечего поставить в обязательный для 401 заголовок WWW-Authenticate.
        return Response({'detail': 'Неверный email или пароль.'},
                        status=status.HTTP_401_UNAUTHORIZED, headers={'WWW-Authenticate': 'Token'})
    update_last_login(None, user)
    response = token_response(user)
    if user.is_staff:
        # Админка Django работает на сессии: открываем её сразу, чтобы не вводить пароль второй раз
        django_login(request._request, user)
        response.data['redirect'] = '/django-admin/'
    return response


@extend_schema(
    tags=['auth'],
    summary='Выход',
    description='Удаляет токен пользователя (и сессию Django-админки, если была).',
    request=None,
    responses={200: OkSerializer, 401: NOT_AUTHENTICATED},
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    django_logout(request._request)  # закрываем и сессию админки, если была
    return Response({'ok': True})


@extend_schema(
    tags=['auth'],
    summary='Текущий пользователь',
    responses={200: MeResponseSerializer, 401: NOT_AUTHENTICATED},
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({'user': user_data(request.user)})
