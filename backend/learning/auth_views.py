"""Регистрация и вход по email и паролю. Токен отдаётся фронтенду, он шлёт его в Authorization: Token <key>."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User


def user_data(user):
    return {
        'id': user.id,
        'email': user.email,
        'name': user.display_name,
        'role': user.role,
        'level': user.current_level.code if user.current_level else None,
        'is_staff': user.is_staff,
    }


def token_response(user, code=status.HTTP_200_OK):
    token, _ = Token.objects.get_or_create(user=user)
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    return Response({'token': token.key, 'user': user_data(user)}, status=code)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128)
    name = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if email.endswith('@' + User.DEVICE_EMAIL_DOMAIN):
            raise serializers.ValidationError('Этот email нельзя использовать')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Пользователь с таким email уже зарегистрирован')
        return email

    def validate(self, attrs):
        try:
            validate_password(attrs['password'], User(email=attrs['email'], display_name=attrs.get('name', '')))
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


@api_view(['POST'])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    user = User.objects.create_user(d['email'], d['password'], display_name=d.get('name', '').strip())
    return token_response(user, status.HTTP_201_CREATED)


@api_view(['POST'])
def login(request):
    s = LoginSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = authenticate(request, email=s.validated_data['email'].strip().lower(), password=s.validated_data['password'])
    if user is None:
        return Response({'detail': 'Неверный email или пароль'}, status=status.HTTP_400_BAD_REQUEST)
    return token_response(user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(user_data(request.user))
