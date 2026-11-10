from django.urls import path

from . import auth, panel_api, views

# API админ-панели (/admin на фронтенде) — только для admin / editor, см. learning/panel_api.py
panel_urls = [
    path('panel/dashboard/', panel_api.dashboard),
    path('panel/search/', panel_api.search),
    path('panel/levels/', panel_api.levels),
    path('panel/levels/<str:code>/', panel_api.level_update),
    path('panel/levels/<str:code>/modules/', panel_api.level_modules),
    path('panel/levels/<str:code>/modules/reorder/', panel_api.modules_reorder),
    path('panel/modules/<int:pk>/', panel_api.module_update),
    path('panel/modules/<int:module_id>/lessons/', panel_api.lesson_create),
    path('panel/lessons/<int:pk>/', panel_api.lesson),
    path('panel/lessons/<int:pk>/publish/', panel_api.lesson_publish),
    path('panel/lessons/<int:pk>/blocks/', panel_api.blocks_add),
    path('panel/lessons/<int:pk>/blocks/reorder/', panel_api.blocks_reorder),
    path('panel/lessons/<int:pk>/blocks/<str:block>/', panel_api.blocks_delete),
    path('panel/lessons/<int:pk>/words/', panel_api.words),
    path('panel/lessons/<int:pk>/words/bulk/', panel_api.words_bulk),
    path('panel/lessons/<int:pk>/words/import/', panel_api.words_import),
    path('panel/words/<int:pk>/', panel_api.word),
    path('panel/lessons/<int:pk>/grammar/', panel_api.grammar),
    path('panel/lessons/<int:pk>/text-quiz/', panel_api.text_quiz),
    path('panel/media/', panel_api.media_upload),
]

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
] + panel_urls
