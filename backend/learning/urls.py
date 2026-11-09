from django.urls import path

from . import auth, views

urlpatterns = [
    path('auth/register/', auth.register),
    path('auth/login/', auth.login),
    path('auth/logout/', auth.logout),
    path('auth/me/', auth.me),
    path('levels/', views.levels),
    path('levels/<str:code>/modules/', views.level_modules),
    path('levels/<str:code>/content/', views.level_content),
    path('modules/<int:pk>/', views.module_detail),
    path('modules/<int:pk>/quiz/', views.quiz_submit),
    path('cards/review/', views.cards_review),
    path('cards/answer/', views.cards_answer),
    path('cards/complete/', views.cards_complete),
    path('topics/read/', views.topic_read),
    path('progress/', views.progress),
    path('progress/reset/', views.progress_reset),
    path('leaderboard/', views.leaderboard),
]
