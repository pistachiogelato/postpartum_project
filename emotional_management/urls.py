from django.urls import path
from django.views.decorators.http import require_http_methods
from . import views
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async

app_name = 'emotional_management'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('update-mood/', views.update_mood, name='update_mood'),
    
    path('api/submit-family-keyword/', views.submit_family_keyword, name='submit-family-keyword'),
    path('api/family-art-daily/', views.get_family_art_daily, name='family-art-daily'),
    path('api/retry-generation/', views.retry_generation, name='retry_generation'),
    
    path('api/tasks/generate/', views.generate_tasks, name='generate_tasks'),
    path('api/tasks/update-status/', views.update_task_status, name='update_task_status'),
    path('api/tasks/today/', views.get_today_tasks, name='get_today_tasks'),

    path('api/daily-quiz/', views.generate_daily_quiz, name='daily_quiz'),
    path('api/answer-quiz/', views.answer_quiz, name='answer_quiz'),
    path('api/quiz-result/<int:quiz_id>/', views.get_quiz_result, name='quiz_result'),
    
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('settings/', views.settings_view, name='settings'),
    path('api/update-settings/', views.update_settings, name='update_settings'),

    
    
]
