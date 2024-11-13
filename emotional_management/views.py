from functools import partial
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import models
from .models import UserProfile, UserPreference,FamilyArtDaily, Task, DailyQuiz, QuizAnswer
import json
from datetime import datetime, timedelta
from requests.exceptions import Timeout  
import google.generativeai as genai
import os
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from django.core.exceptions import ValidationError
import asyncio
from asgiref.sync import sync_to_async
import logging
from django.utils import timezone
import random
from django.core.cache import cache
from django.conf import settings
import base64
import io
from PIL import Image
import requests
from .utils import validate_image_url
import traceback
from django.views.decorators.http import require_http_methods


# DEFAULT tasks based on role
DEFAULT_ADMIN_TASKS = [
    "Ensure 8 hours of rest today",
    "Drink 8 glasses of water",
    "Engage in 15 minutes of light exercise",
    "Have a heart-to-heart with family"
]

DEFAULT_FAMILY_TASKS = [
    "Prepare a nutritious meal for the postpartum woman",
    "Ensure the postpartum woman takes nutritional supplements on time",
    "Help care for the baby for 2 hours to allow the postpartum woman to rest",
    "Accompany the postpartum woman on a 15-minute walk"
]


TASK_GENERATION_CACHE = {}  # Store task generation status per user

# proxy
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("[Warning] GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Add timeout wrapper function (after imports, before views)
def with_timeout(func, timeout_seconds):
    """
    Wrapper function to add timeout to synchronous functions
    Args:
        func: Function to execute
        timeout_seconds: Maximum execution time in seconds
    Returns:
        Function result or raises TimeoutError
    """
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(func)
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        raise TimeoutError("Operation timed out")
    finally:
        executor.shutdown(wait=False)
        
def index(request):
    return render(request, 'emotional_management/index.html')

def login_view(request):
    return render(request, 'emotional_management/login.html')

def register_view(request):
    return render(request, 'emotional_management/register.html')

def logout_view(request):
    """Logout view"""
    auth_logout(request)
    return redirect('emotional_management:login')

@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nickname = data.get('nickname')
            family_name = data.get('family_name')

            #test
            print("Received login attempt:")
            print(f"Nickname: {nickname}")
            print(f"Family name: {family_name}")

            try:
                user_profile = UserProfile.objects.get(
                    nickname=nickname,
                    family_name=family_name
                )

                #test
                print(f"Found user profile: {user_profile}")

                login(request, user_profile.user)
                return JsonResponse({
                    "status": "success",
                    "message": "Login successful"
                })
            except UserProfile.DoesNotExist:
                #test
                print("UserProfile not found")

                return JsonResponse({
                    "status": "error",
                    "message": "Invalid nickname or family name"
                }, status=400)
                
        except Exception as e:
            #test
            print(f"Login error: {str(e)}")

            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def api_register(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nickname = data.get('nickname')
            family_name = data.get('familyName')
            role = data.get('role', 'family')
            
            if not nickname or not family_name:
                return JsonResponse({
                    "status": "error",
                    "message": "Nickname and family name are required"
                }, status=400)
            
            # Check if any user exists with this family name
            existing_family_members = UserProfile.objects.filter(family_name=family_name)
            
            # If this is the first member of the family, they must be admin
            if not existing_family_members.exists() and role != 'admin':
                return JsonResponse({
                    "status": "error",
                    "message": "First family member must be an administrator"
                }, status=400)
            
            # If family exists, check if it already has an admin
            if existing_family_members.exists() and role == 'admin':
                if existing_family_members.filter(role='admin').exists():
                    return JsonResponse({
                        "status": "error",
                        "message": "This family already has an administrator"
                    }, status=400)
            
            if User.objects.filter(username=nickname).exists():
                return JsonResponse({
                    "status": "error",
                    "message": "This nickname is already taken"
                }, status=400)
            
            # Create user
            user = User.objects.create(username=nickname)
            
            # Create profile
            UserProfile.objects.create(
                user=user,
                nickname=nickname,
                family_name=family_name,
                age_range=data.get('age_range'),
                role=role,
                fertility_status=data.get('fertility', 'no_planning')
            )
            
            # Create preferences
            preferences = data.get('preferences', [])
            UserPreference.objects.create(
                user=user,
                emotional_support='emotional_support' in preferences,
                health_wellness='health_wellness' in preferences,
                family_activities='family_activities' in preferences
            )
            
            login(request, user)
            return JsonResponse({
                "status": "success",
                "message": "Registration successful"
            })
            
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def dashboard(request):
    """
    Initial dashboard view that renders the template with loading state
    """
    try:
        print("[Debug] Starting dashboard view")
        user_profile = request.user.userprofile
        
        # Get admin's mood for all family members
        admin_profile = UserProfile.objects.filter(
            family_name=user_profile.family_name,
            role='admin'
        ).first()
        
        context = {
            'user_profile': user_profile,
            'admin_mood': admin_profile.mood if admin_profile else 50,  # Default mood if no admin
            'tasks': [],  # Initially empty
            'is_loading': True,  # Show loading state
            'show_to_be_continued': False,
        }
        
        return render(request, 'emotional_management/dashboard.html', context)
        
    except Exception as e:
        print(f"[Debug] Error in dashboard: {str(e)}")
        return redirect('emotional_management:login')

@login_required
@require_http_methods(["GET"])
def get_today_tasks(request):
    """
    Synchronous view for getting/generating today's tasks
    """
    try:
        print("[Debug] Starting get_today_tasks")
        user_profile = request.user.userprofile
        today = timezone.now().date()
        
        # Check for existing tasks
        tasks = Task.objects.filter(
            user=request.user,
            created_at__date=today
        )
        
        if not tasks.exists():
            print("[Debug] No existing tasks, generating new ones")
            # Create default tasks first
            default_tasks = DEFAULT_FAMILY_TASKS if user_profile.role != 'admin' else DEFAULT_ADMIN_TASKS
            for task_desc in default_tasks:
                Task.objects.create(
                    user=request.user,
                    description=task_desc,
                    task_type='daily'
                )
            
            # Get updated tasks
            tasks = Task.objects.filter(
                user=request.user,
                created_at__date=today
            )
        
        # Convert tasks to list of dicts
        task_list = list(tasks.values('id', 'description', 'completed', 'task_type'))
        
        return JsonResponse({
            'status': 'success',
            'tasks': task_list
        })
        
    except Exception as e:
        print(f"[Debug] Error in get_today_tasks: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@csrf_exempt
def update_mood(request):
    """
    Update admin's mood value
    Only admin can update mood, others can only view
    Expects POST request with mood value
    Returns updated mood value
    """
    print("[Debug] Mood update request received")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mood_value = data.get('mood')
            user_profile = request.user.userprofile
            
            # Verify user is admin
            if user_profile.role != 'admin':
                print("[Debug] Non-admin user attempted to update mood")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Only administrators can update mood'
                }, status=403)
            
            # Update mood
            user_profile.mood = mood_value
            user_profile.save()
            
            print(f"[Debug] Admin mood updated to: {mood_value}")
            
            return JsonResponse({
                'status': 'success',
                'mood': mood_value
            })
            
        except Exception as e:
            print(f"[Debug] Mood update error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
            
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


@login_required
@csrf_exempt
def submit_family_keyword(request):
    """
    Handle keyword submission and trigger image generation
    Returns:
        JsonResponse with status and updated keywords information
    """
    if request.method == 'POST':
        try:
            # Parse request data
            data = json.loads(request.body)
            keyword = data.get('keyword', '').strip()
            
            if not keyword:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid keyword'
                }, status=400)

            # Get user's family info
            family_name = request.user.userprofile.family_name
            today = timezone.now().date()
            
            print(f"[Debug] Processing keyword '{keyword}' for family '{family_name}'")
            
            # Get or create today's entry
            art_entry, created = FamilyArtDaily.objects.get_or_create(
                family_name=family_name,
                date=today,
                defaults={'keywords': []}
            )
            
            print(f"[Debug] Current keywords: {art_entry.keywords}")
            
            # Try to add keyword
            if art_entry.add_keyword(keyword):
                try:
                    art_entry.full_clean()  # Validate model
                    art_entry.save()
                    
                    print(f"[Debug] Successfully added keyword. Updated keywords: {art_entry.keywords}")
                    
                    remaining_slots = 3 - len(art_entry.keywords)
                    return JsonResponse({
                        'status': 'success',
                        'keywords': art_entry.keywords,
                        'remaining_slots': remaining_slots,
                        'message': 'Keyword added successfully'
                    })
                except ValidationError as e:
                    print(f"[Debug] Validation error: {str(e)}")
                    return JsonResponse({
                        'status': 'error',
                        'message': str(e)
                    }, status=400)
            else:
                print("[Debug] Failed to add keyword - limit reached or duplicate")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Could not add keyword (limit reached or duplicate)'
                }, status=400)
                
        except Exception as e:
            print(f"[Debug] Error in submit_family_keyword: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@login_required
def get_family_art_daily(request):
    """Get today's family art and keywords"""
    try:
        family_name = request.user.userprofile.family_name
        today = timezone.now().date()
        
        print(f"[Debug] Getting art for family: {family_name}, date: {today}")
        
        art_entry = FamilyArtDaily.objects.filter(
            family_name=family_name,
            date=today
        ).first()
        
        if art_entry:
            print(f"[Debug] Found art entry: keywords={art_entry.keywords}, image_url={art_entry.image_url}")
            
            # Check if we need to generate image
            if len(art_entry.keywords) == 3 and not art_entry.image_url:
                try:
                    print("[Debug] Attempting to generate image with Gemini")
                    # Initialize Gemini with updated model
                    genai.configure(api_key=GEMINI_API_KEY)
                    # Use gemini-1.5-flash instead of gemini-1.5-flash-vision
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # Create prompt from keywords
                    prompt = f"""Please create a family-friendly image that incorporates these three concepts: 
                    {', '.join(art_entry.keywords)}. 
                    The image should be:
                    - Heartwarming and positive
                    - Suitable for a family wellness app
                    - Simple and clear in composition
                    - Using soft, pleasant colors
                    Please provide the image in a format suitable for web display."""
                    
                    print(f"[Debug] Sending prompt to Gemini with model gemini-1.5-flash")
                    # Generate image with safety settings
                    safety_settings = {
                        "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
                        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
                        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
                        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
                    }
                    
                    response = model.generate_content(
                        prompt,
                        safety_settings=safety_settings
                    )
                    
                    if response.candidates:
                        image_url = response.candidates[0].content.parts[0].text
                        # Validate image URL
                        if image_url and image_url.startswith(('http://', 'https://')):
                            art_entry.image_url = image_url
                            art_entry.save()
                            print(f"[Debug] Image generated successfully: {art_entry.image_url}")
                        else:
                            print("[Debug] Invalid image URL received from Gemini")
                            raise Exception("Invalid image URL format")
                    else:
                        print("[Debug] No image generated from Gemini")
                        raise Exception("No image generated")
                except Exception as e:
                    print(f"[Debug] Error generating image: {str(e)}")
                    # Update response to indicate generation failed
                    return JsonResponse({
                        'status': 'success',
                        'data': {
                            'keywords': art_entry.keywords,
                            'image_url': None,
                            'remaining_slots': 0,
                            'generation_status': 'failed',
                            'error_message': str(e)
                        }
                    })

        response_data = {
            'status': 'success',
            'data': {
                'keywords': art_entry.keywords if art_entry else [],
                'image_url': art_entry.image_url if art_entry else None,
                'remaining_slots': 3 - len(art_entry.keywords) if art_entry else 3,
                'generation_status': 'complete' if (art_entry and art_entry.image_url) else 'pending'
            }
        }
        
        print(f"[Debug] Sending response: {response_data}")
        return JsonResponse(response_data)

    except Exception as e:
        print(f"[Debug] Error in get_family_art_daily: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# Add task generation state tracking
TASK_GENERATION_CACHE = {}  # Store task generation status per user

def generate_ai_tasks(user_role, fertility_status):
    """
    Generate personalized tasks using Gemini AI
    Returns list of task descriptions or None if generation fails
    """
    try:
        # Construct prompt based on user role and status
        prompt = f"""Generate 4 personalized daily tasks for a {user_role} in a family with a {fertility_status} woman.
        Tasks should be:
        1. Specific and actionable
        2. Focused on family well-being
        3. Appropriate for the role
        4. Considerate of the woman's current status
        Return only the tasks, one per line."""
        
        # Generate response from Gemini
        response = model.generate_content(prompt)
        
        if response and response.text:
            # Split response into individual tasks and clean them
            tasks = [task.strip() for task in response.text.split('\n') if task.strip()]
            return tasks[:4]  # Ensure we only return up to 4 tasks
            
        return None
        
    except Exception as e:
        print(f"[Debug] Error in AI task generation: {str(e)}")
        return None

@login_required
async def generate_tasks(request):
    """Generate daily tasks for user"""
    print("[Debug] Starting generate_tasks function")
    try:
        user = request.user
        user_profile = user.userprofile
        today = timezone.now().date()
        
        print(f"[Debug] Generating tasks for user: {user.username}, role: {user_profile.role}")
        
        # Check if tasks already exist for today
        existing_tasks = Task.objects.filter(
            user=user,
            created_at__date=today
        )
        
        if existing_tasks.exists():
            print(f"[Debug] Found {existing_tasks.count()} existing tasks for today")
            return JsonResponse({
                'status': 'success',
                'tasks': [{
                    'id': task.id,
                    'description': task.description,
                    'completed': task.completed,
                    'task_type': task.task_type
                } for task in existing_tasks]
            })

        print("[Debug] No existing tasks found, attempting AI generation")
        # Try to generate AI tasks
        ai_tasks = await generate_ai_tasks(
            user_profile.role,
            user_profile.fertility_status
        )

        print(f"[Debug] AI task generation result: {ai_tasks}")

        tasks_to_create = []
        if ai_tasks:
            print("[Debug] Using AI generated tasks")
            tasks_to_create = ai_tasks
        else:
            print("[Debug] Falling back to default tasks")
            tasks_to_create = (DEFAULT_FAMILY_TASKS 
                             if user_profile.role != 'admin' 
                             else DEFAULT_ADMIN_TASKS)

        # Create tasks in database
        created_tasks = []
        print(f"[Debug] Creating {len(tasks_to_create)} tasks in database")
        for task_desc in tasks_to_create:
            task = Task.objects.create(
                user=user,
                description=task_desc,
                task_type='family' if user_profile.role != 'admin' else 'daily'
            )
            created_tasks.append({
                'id': task.id,
                'description': task.description,
                'completed': task.completed,
                'task_type': task.task_type
            })
            print(f"[Debug] Created task: {task.id} - {task.description}")

        return JsonResponse({
            'status': 'success',
            'tasks': created_tasks
        })

    except Exception as e:
        print(f"[Debug] Task generation error: {str(e)}")
        print(f"[Debug] Error type: {type(e).__name__}")
        print(f"[Debug] Error traceback: {traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    
@csrf_exempt
@login_required
def update_task_status(request):
    """Update task completion status"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            completed = data.get('completed', False)
            
            # Get task and verify ownership
            task = Task.objects.get(id=task_id, user=request.user)
            task.completed = completed
            task.save()
            
            print(f"[Debug] Updated task {task_id} completion status to: {completed}")
            
            return JsonResponse({
                'status': 'success',
                'task_id': task_id,
                'completed': completed
            })
            
        except Task.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Task not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@login_required
@require_http_methods(["GET"])
def get_today_tasks(request):
    """
    Synchronous view for getting/generating today's tasks.
    First attempts to generate tasks using Gemini AI, falls back to default tasks if AI generation fails.
    """
    try:
        print("[Debug] Starting get_today_tasks")
        user_profile = request.user.userprofile
        today = timezone.now().date()
        
        # Check for existing tasks first
        tasks = Task.objects.filter(
            user=request.user,
            created_at__date=today
        )
        
        if not tasks.exists():
            print("[Debug] No existing tasks found, attempting AI generation")
            
            # First try to generate AI tasks with age range
            ai_tasks = generate_ai_tasks(
                user_profile.role,
                user_profile.fertility_status,
                user_profile.age_range  # Add age_range parameter
            )
            
            if ai_tasks:
                print("[Debug] Successfully generated AI tasks:", ai_tasks)
                # Create AI generated tasks
                for task_desc in ai_tasks:
                    Task.objects.create(
                        user=request.user,
                        description=task_desc,
                        task_type='ai_generated'
                    )
            else:
                print("[Debug] AI generation failed, falling back to default tasks")
                # Fall back to default tasks if AI generation fails
                default_tasks = DEFAULT_FAMILY_TASKS if user_profile.role != 'admin' else DEFAULT_ADMIN_TASKS
                for task_desc in default_tasks:
                    Task.objects.create(
                        user=request.user,
                        description=task_desc,
                        task_type='daily'
                    )
            
            # Get the newly created tasks
            tasks = Task.objects.filter(
                user=request.user,
                created_at__date=today
            )
        
        # Convert tasks to list of dicts
        task_list = list(tasks.values('id', 'description', 'completed', 'task_type'))
        print(f"[Debug] Returning {len(task_list)} tasks")
        
        return JsonResponse({
            'status': 'success',
            'tasks': task_list
        })
        
    except Exception as e:
        print(f"[Debug] Error in get_today_tasks: {str(e)}")
        print(f"[Debug] Error type: {type(e).__name__}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def generate_ai_tasks(role, fertility_status, age_range):
    """
    Generate personalized tasks using Gemini AI based on user role and age
    Args:
        role (str): User role (admin/family)
        fertility_status (str): Admin's fertility status
        age_range (str): User's age range
    Returns:
        list: Generated tasks or None if generation fails
    """
    try:
        print(f"[Debug] Starting AI task generation for role: {role}, status: {fertility_status}, age: {age_range}")
        
        # Validate input parameters
        if not all([role, fertility_status, age_range]):
            print("[Debug] Invalid input parameters")
            return None
            
        # Different prompts for admin and family members
        if role == 'admin':
            prompt = f"""Create 4 daily self-care tasks for a {age_range} woman who is {fertility_status}.
            Requirements:
            - Focus on physical and mental well-being
            - Make tasks specific and actionable for self-care
            - Consider both {fertility_status} status and {age_range} age group
            - Balance rest and activity
            - Return each task on a new line
            - Do not include any numbers, bullets, or prefixes
            - Keep each task concise and clear"""
        else:
            prompt = f"""Create 4 daily tasks for a {age_range} family member supporting a {fertility_status} woman.
            Requirements:
            - Focus on supporting the woman's well-being
            - Make tasks specific and actionable
            - Consider both her {fertility_status} status and your {age_range} age group
            - Balance practical help and emotional support
            - Return each task on a new line
            - Do not include any numbers, bullets, or prefixes
            - Keep each task concise and clear"""

        print(f"[Debug] Using prompt:\n{prompt}")
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Check Gemini API configuration
        if not GEMINI_API_KEY:
            print("[Debug] GEMINI_API_KEY not found")
            return None
            
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        try:
            print("[Debug] Calling Gemini API...")
            response = model.generate_content(prompt)
            print(f"[Debug] Raw Gemini response: {response}")
            
            if response and response.text:
                # Clean and process tasks
                tasks = [
                    task.strip().lstrip('1234567890.-*• ') # Remove any potential prefixes
                    for task in response.text.split('\n')
                    if task.strip() and not task.startswith('Requirements:')
                ]
                print(f"[Debug] Generated {len(tasks)} tasks: {tasks}")
                
                # Validate tasks
                if len(tasks) < 1:
                    print("[Debug] No valid tasks generated")
                    return None
                    
                return tasks[:4]  # Ensure we only return up to 4 tasks
            else:
                print("[Debug] Empty response from Gemini")
                return None
                
        except Exception as api_error:
            print(f"[Debug] Gemini API error: {str(api_error)}")
            print(f"[Debug] Error type: {type(api_error).__name__}")
            return None
            
    except Exception as e:
        print(f"[Debug] Error in AI task generation: {str(e)}")
        print(f"[Debug] Error type: {type(e).__name__}")
        print(f"[Debug] Error traceback: {traceback.format_exc()}")
        return None

@login_required
def generate_daily_quiz(request):
    """
    Generate or retrieve daily quiz using Gemini API
    Returns quiz data in consistent format
    """
    print("[Debug] Daily quiz request received")
    if request.method == 'GET':
        try:
            user = request.user
            today = datetime.now().date()
            
            # Try to get existing quiz for today
            quiz = DailyQuiz.objects.filter(date=today).first()
            
            if not quiz:
                print("[Debug] No existing quiz found, generating new one")
                try:
                    # Get admin's profile for quiz generation context
                    admin_profile = UserProfile.objects.filter(role='admin').first()
                    if not admin_profile:
                        print("[Debug] Admin profile not found")
                        raise Exception("Admin profile not found")

                    # Create prompt for quiz generation
                    prompt = f"""
                    Generate a multiple-choice question about maternal health and well-being.
                    Consider the following context:
                    - Age range: {admin_profile.age_range}
                    - Fertility status: {admin_profile.fertility_status}

                    The question should be educational and focused on health knowledge.
                    Format the response EXACTLY as a JSON object with the following structure:
                    {{
                        "question": "Your question here?",
                        "options": ["option1", "option2", "option3", "option4"],
                        "correct_answer": 0,
                        "explanation": "Detailed explanation of why this answer is correct and what we can learn from it"
                    }}
                    
                    Make sure to include a detailed explanation that helps users understand the correct answer.
                    """

                    # Generate quiz using Gemini API
                    print("[Debug] Calling Gemini API for quiz generation")
                    response = model.generate_content(prompt)
                    
                    if not response or not response.text:
                        print("[Debug] Gemini API call failed - no response")
                        raise Exception("Failed to generate quiz content")

                    print("[Debug] Raw Gemini API response:", response.text)
                    
                    # Parse the response
                    try:
                        quiz_data = json.loads(response.text)
                        print("[Debug] Parsed quiz data:", quiz_data)
                        
                        # Validate required fields
                        required_fields = ['question', 'options', 'correct_answer', 'explanation']
                        missing_fields = [field for field in required_fields if field not in quiz_data]
                        if missing_fields:
                            print(f"[Debug] Missing required fields: {missing_fields}")
                            raise Exception(f"Missing required fields: {missing_fields}")
                        
                        # Create new quiz in database
                        quiz = DailyQuiz.objects.create(
                            question=quiz_data['question'],
                            options=quiz_data['options'],
                            correct_answer=quiz_data['correct_answer'],
                            explanation=quiz_data.get('explanation'),
                            date=today
                        )
                        print(f"[Debug] Created new quiz with explanation: {quiz.explanation}")
                        
                    except json.JSONDecodeError as e:
                        print("[Debug] Failed to parse Gemini API response:", e)
                        print("[Debug] Raw response content:", response.text)
                        raise Exception("Invalid quiz format received from API")

                except Exception as e:
                    print(f"[Debug] Quiz generation error: {str(e)}")
                    raise
            else:
                print(f"[Debug] Found existing quiz with explanation: {quiz.explanation}")

            # Check if user has already answered
            has_answered = QuizAnswer.objects.filter(
                user=user,
                quiz=quiz,
                created_at__date=today
            ).exists()
            
            print(f"[Debug] User has answered: {has_answered}")
            print(f"[Debug] Sending quiz - ID: {quiz.id}, Question: {quiz.question}, "
                  f"Options: {quiz.options}, Correct Answer: {quiz.correct_answer}, "
                  f"Explanation: {quiz.explanation}")
            
            return JsonResponse({
                'status': 'success',
                'quiz': {
                    'id': quiz.id,
                    'question': quiz.question,
                    'options': quiz.options,
                    'answered': has_answered,
                    'explanation': quiz.explanation
                }
            })
            
        except Exception as e:
            print(f"[Debug] Quiz error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    })

@login_required
def answer_quiz(request):
    """
    Handle user's quiz answer submission
    Returns whether the answer was correct and provides explanation
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quiz_id = data.get('quiz_id')
            user_answer = int(data.get('answer', 0))
            
            # Get the quiz
            quiz = DailyQuiz.objects.get(id=quiz_id)
            
            # Add detailed debug logging
            print(f"[Debug] Quiz answer details:")
            print(f"- User submitted answer index: {user_answer}")
            print(f"- Quiz correct answer index: {quiz.correct_answer}")
            print(f"- All options: {quiz.options}")
            
            # Check if answer is correct
            is_correct = (user_answer == quiz.correct_answer)
            
            # Get or create user's answer
            quiz_answer, created = QuizAnswer.objects.get_or_create(
                user=request.user,
                quiz=quiz,
                defaults={
                    'answer': user_answer,
                    'is_correct': is_correct
                }
            )
            
            # If answer already exists, update it with new submission
            if not created:
                quiz_answer.answer = user_answer
                quiz_answer.is_correct = is_correct
                quiz_answer.save()
            
            # Award points if correct
            points_earned = 10 if is_correct else 0
            if is_correct:
                try:
                    user_profile = request.user.userprofile
                    user_profile.points = (user_profile.points or 0) + points_earned
                    user_profile.save()
                except Exception as e:
                    print(f"[Debug] Error awarding points: {str(e)}")
            
            return JsonResponse({
                'status': 'success',
                'is_correct': is_correct,
                'correct_answer': quiz.options[quiz.correct_answer],
                'explanation': quiz.explanation or "No explanation available",
                'points_earned': points_earned
            })
            
        except DailyQuiz.DoesNotExist:
            print("[Debug] Quiz not found")
            return JsonResponse({
                'status': 'error',
                'message': 'Quiz not found'
            })
        except (ValueError, TypeError) as e:
            print(f"[Debug] Invalid answer format: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid answer format'
            })
        except Exception as e:
            print(f"[Debug] Error processing answer: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    })

def generate_random_color():
    # random color for leaderboard
    return "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
logger = logging.getLogger(__name__)

@login_required
def leaderboard(request):
    """
    Family Task Completion Statistics with overall progress visualization
    Displays a circular progress chart and member-specific statistics
    """
    try:
        family_name = request.user.userprofile.family_name
        
        # Get all family members
        family_members = UserProfile.objects.filter(family_name=family_name)
        members_progress = []
        
        # Initialize counters for family total
        total_family_tasks = 0
        total_completed_tasks = 0
        
        # Calculate progress for each member and family total
        for member in family_members:
            today = timezone.now().date()
            member_tasks = Task.objects.filter(
                user=member.user,
                created_at__date=today
            )
            
            member_total = member_tasks.count()
            member_completed = member_tasks.filter(completed=True).count()
            
            # Add to family totals
            total_family_tasks += member_total
            total_completed_tasks += member_completed
            
            # Calculate member completion rate
            completion_rate = (member_completed / member_total * 100) if member_total > 0 else 0

            # Generate a random color for each member
            member_color = generate_random_color()

            members_progress.append({
                'nickname': member.nickname,
                'role': member.role,
                'completion_rate': round(completion_rate, 1),
                'completed': member_completed,
                'total': member_total,
                'color': member_color,  
            })
        
        # Ensure we have valid numbers to prevent division by zero
        total_family_tasks = max(total_family_tasks, 1)  # Ensure at least 1 task for division
        family_completion_rate = (total_completed_tasks / total_family_tasks * 100)
        
        context = {
            'members_progress': members_progress,
            'family_name': family_name,
            'completion_rate': round(family_completion_rate, 1),
            'total_tasks': total_family_tasks,
            'completed_tasks': total_completed_tasks
        }
        
        return render(request, 'emotional_management/leaderboard.html', context)
    except Exception as e:
        print(f"[Debug] Leaderboard error: {str(e)}")
        return redirect('emotional_management:dashboard')

    
@login_required
def settings_view(request):
    """User settings view"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        user_preferences = UserPreference.objects.get(user=request.user)
        
        context = {
            'user_profile': user_profile,
            'user_preferences': user_preferences
        }
        
        return render(request, 'emotional_management/settings.html', context)
    except (UserProfile.DoesNotExist, UserPreference.DoesNotExist):
        return redirect('emotional_management:dashboard')

@login_required
@csrf_exempt
def update_settings(request):
    """Handle settings update"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_profile = UserProfile.objects.get(user=request.user)
            user_preferences = UserPreference.objects.get(user=request.user)
            
            # Update profile
            user_profile.nickname = data.get('nickname', user_profile.nickname)
            user_profile.fertility_status = data.get('fertility_status', user_profile.fertility_status)
            user_profile.save()
            
            # Update preferences
            user_preferences.emotional_support = data.get('emotional_support', user_preferences.emotional_support)
            user_preferences.health_wellness = data.get('health_wellness', user_preferences.health_wellness)
            user_preferences.family_activities = data.get('family_activities', user_preferences.family_activities)
            user_preferences.save()
            
            return JsonResponse({
                "status": "success",
                "message": "Settings updated successfully"
            })
            
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def get_quiz_result(request, quiz_id):
    """
    Get the result of a previously answered quiz
    Returns the answer details and explanation
    """
    try:
        quiz = DailyQuiz.objects.get(id=quiz_id)
        answer = QuizAnswer.objects.get(user=request.user, quiz=quiz)
        
        return JsonResponse({
            'status': 'success',
            'is_correct': answer.is_correct,
            'correct_answer': quiz.options[quiz.correct_answer],
            'explanation': quiz.explanation or "Keep learning and try again tomorrow!",
            'points_earned': 10 if answer.is_correct else 0
        })
    except (DailyQuiz.DoesNotExist, QuizAnswer.DoesNotExist):
        return JsonResponse({
            'status': 'error',
            'message': 'Quiz result not found'
        })

@login_required
@csrf_exempt
def retry_generation(request):
    """Handle retry requests for image generation"""
    try:
        # Get user's family info
        family_name = request.user.userprofile.family_name
        today = timezone.now().date()
        
        print(f"[Debug] Starting retry generation for family: {family_name}")
        
        # Get current art entry
        art_entry = FamilyArtDaily.objects.filter(
            family_name=family_name,
            date=today
        ).first()
        
        if not art_entry:
            print("[Debug] No art entry found")
            return JsonResponse({
                'status': 'error',
                'message': 'No art entry found'
            }, status=404)
            
        if len(art_entry.keywords) != 3:
            print("[Debug] Incomplete keywords")
            return JsonResponse({
                'status': 'error',
                'message': 'Please submit all three keywords first'
            }, status=400)

        try:
            # Initialize Gemini
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-pro')  # Using pro model
            
            # Create detailed prompt
            keywords_str = ', '.join(art_entry.keywords)
            prompt = f"""Create a family-friendly image incorporating these concepts: {keywords_str}.
            Requirements:
            - Style: Simple, cheerful design
            - Colors: Soft, pastel palette
            - Content: Family-appropriate
            - Format: Web-optimized image
            
            Please provide a direct image URL."""
            
            print(f"[Debug] Sending prompt to Gemini: {prompt}")
            
            # Generate content
            response = model.generate_content(prompt)
            
            if response.candidates:
                generated_content = response.candidates[0].content.parts[0].text.strip()
                print(f"[Debug] Received response from Gemini: {generated_content}")
                
                # Try to extract URL from the response
                import re
                urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', generated_content)
                
                if urls:
                    image_url = urls[0]
                    # Validate URL is accessible and is an image
                    try:
                        # Try to fetch and validate the image
                        img_response = requests.get(image_url, timeout=10)
                        if img_response.status_code == 200:
                            # Try to open the image to validate it's really an image
                            Image.open(io.BytesIO(img_response.content))
                            
                            # If we get here, it's a valid image
                            art_entry.image_url = image_url
                            art_entry.save()
                            
                            print(f"[Debug] Valid image URL saved: {image_url}")
                            return JsonResponse({
                                'status': 'success',
                                'data': {
                                    'image_url': image_url,
                                    'description': generated_content,
                                    'keywords': art_entry.keywords
                                }
                            })
                        else:
                            raise Exception("Failed to fetch image from URL")
                    except Exception as e:
                        print(f"[Debug] Error validating image: {str(e)}")
                else:
                    # Use fallback image service
                    fallback_url = f"https://picsum.photos/800/600?random={timezone.now().timestamp()}"
                    art_entry.image_url = fallback_url
                    art_entry.save()
                    
                    print(f"[Debug] Using fallback image URL: {fallback_url}")
                    return JsonResponse({
                        'status': 'success',
                        'data': {
                            'image_url': fallback_url,
                            'description': generated_content,
                            'keywords': art_entry.keywords
                        }
                    })
            else:
                raise Exception("No content generated by Gemini")
                
        except Exception as e:
            print(f"[Debug] Error in image generation: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f"Image generation failed: {str(e)}"
            }, status=500)
            
    except Exception as e:
        print(f"[Debug] System error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def get_image_url(keywords):
    """
    Generate a reliable image URL based on keywords
    Args:
        keywords (list): List of keywords for image generation
    Returns:
        str: Valid image URL
    """
    try:
        # List of reliable image services with their base URLs
        image_services = [
            "https://source.unsplash.com/800x600/?{}",
            "https://api.pexels.com/v1/search?query={}&per_page=1",
            "https://picsum.photos/800/600?query={}"
        ]
        
        # Join keywords for the query
        query = '+'.join(keywords)
        
        # Try each service until we get a valid URL
        for service_url in image_services:
            try:
                url = service_url.format(query)
                # Validate URL is accessible
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    return url
            except:
                continue
                
        # Fallback to random image if all services fail
        return f"https://picsum.photos/800/600?random={timezone.now().timestamp()}"
        
    except Exception as e:
        print(f"[Debug] Error in get_image_url: {str(e)}")
        # Return a safe fallback URL
        return "https://picsum.photos/800/600"