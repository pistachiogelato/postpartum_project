from django.contrib import admin
from .models import DailyQuiz, QuizAnswer

@admin.register(DailyQuiz)
class DailyQuizAdmin(admin.ModelAdmin):
    list_display = ['question', 'date', 'created_at']
    list_filter = ['date']
    search_fields = ['question']

@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'is_correct', 'created_at']
    list_filter = ['is_correct', 'created_at']
    search_fields = ['user__username']

# Register your models here.
