from django.urls import path
from . import views 
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('', views.register_view, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('main/', views.main_view,name='main'),
    path('leaderboard/',views.leaderboard_view,name='leaderboard'),
    path('education/', views.education_view, name='education'),
    path('task/',views.task_view, name='task'),
    path('chat/', views.gemini_chat_view, name='gemini_chat'),
]
