from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import User, Family
#from .models import Profile
from .forms import RegisterForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import google.generativeai as genai
import os
from datetime import date
from django.views.decorators.csrf import csrf_exempt


genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# views.py




User = get_user_model()

class CustomLoginView(LoginView):
    template_name = 'emotional_management/login.html'

    def get_success_url(self):
        return reverse('main')  # 登录成功后重定向到 main 页面

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            family_name = form.cleaned_data['family_name']

            family, _ = Family.objects.get_or_create(name=family_name)
            user = User.objects.create_user(username=username, password=password, role=role)
            user.family = family
            user.save()

            login(request, user)  # 自动登录新用户
            return redirect('main')  # 重定向到主页面
    else:
        form = RegisterForm()
    return render(request, 'emotional_management/register.html', {'form': form})

@login_required
def main_view(request):
    user = request.user
    family = user.family

    if family:
        generate_daily_tasks(family)  # 确保生成当天任务
        return render(request, 'emotional_management/main.html', {
            'family_name': family.name,
            'tasks': family.daily_tasks,
        })
    else:
        return redirect('register')
    '''
    # 检查用户是否登录
    if request.user.is_authenticated:
        family_name = getattr(request.user, 'profile', None)
        return render(request, 'emotional_management/main.html', {'family_name': family_name})
    else:
        return redirect('register')
    '''


def leaderboard_view(request):
    return render(request, 'emotional_management/leaderboard.html')

def education_view(request):
    return render(request, 'emotional_management/education.html')

def task_view(request):
    return render(request, 'emotional_management/task.html')

def generate_daily_tasks(family):
    # 如果今天还未生成任务，调用 gemini 生成器生成任务
    if family.daily_tasks_date != date.today():
        model = genai.GenerativeModel("gemini-1.5-flash")
        tasks = [
            model.generate_content("Provide a task to support postpartum care and baby care."),
            model.generate_content("Suggest a task for boosting the mood of a new mom."),
            model.generate_content("Give a task that family members can perform to help the new mom.")
        ]
        family.daily_tasks = [task.text for task in tasks]
        family.daily_tasks_date = date.today()
        family.save()

@csrf_exempt  # 用于允许 POST 请求测试
def gemini_chat_view(request):
    if request.method == 'POST':
        user_message = request.POST.get('message')
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Respond supportively to the following message about postpartum depression: {user_message}")
        gemini_reply = response.text if response else "抱歉，目前无法处理您的请求。"
        return JsonResponse({'reply': gemini_reply})
'''
def gemini_chat_view(request):
    if request.method == 'POST':
        user_message = request.POST.get('message')
        # 调用 gemini API 获取回复
        model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content("Write a story about a magic backpack.")
print(response.text)
        gemini_reply = "这是 gemini 的回复"  # 模拟回复，实际应调用 API
        return JsonResponse({'reply': gemini_reply})
'''