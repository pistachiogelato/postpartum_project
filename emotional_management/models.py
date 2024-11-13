from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from django.utils import timezone

class UserProfile(models.Model):
    """Extended user profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mood = models.IntegerField(default=50)
    nickname = models.CharField(max_length=50)
    age_range = models.CharField(  
        max_length=20,
        choices=[
            ('under18', 'Under 18'),
            ('18-24', '18-24'),
            ('25-44', '25-44'),
            ('above45', '45 and above'),
        ],
        default= '25-44'  
    )
    family_name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Administrator'),
            ('partner', 'Partner'),
            ('family', 'Family Member'),
            ('friend', 'Friend'),
        ],
        default = 'admin'
    )
    fertility_status = models.CharField(
        max_length=40,
        choices=[
        ('pregnant', 'Pregnant'),
        ('postpartum', 'Postpartum'),
        ('planning', 'Planning'),
        ('no_planning', 'No Planning'),
         ],
        default='no_planning'
    )
    points = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def clean(self):
            # 检查同一个家庭是否已经有管理员
            if self.role == 'admin':
                existing_admin = UserProfile.objects.filter(
                    family_name=self.family_name, 
                    role='admin'
                ).exclude(id=self.id).exists()
                
                if existing_admin:
                    raise ValidationError({
                        'role': 'This family already has an administrator.'
                    })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nickname} ({self.role})"

class UserPreference(models.Model):
    """User preferences model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    emotional_support = models.BooleanField(default=False)
    health_wellness = models.BooleanField(default=False)
    family_activities = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"

class Task(models.Model):
    """Daily tasks for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    task_type = models.CharField(
        max_length=50,
        choices=[
            ('daily', 'Daily Task'),
            ('wellness', 'Wellness Task'),
            ('family', 'Family Task'),
            ('health', 'Health Task'),
            ('ai_generated', 'AI Generated Task'),
        ],
        default='daily'
    )
    
    class Meta:
        ordering = ['-created_at']

    @classmethod
    def get_today_tasks(cls, user):
        """Get tasks for today with timezone awareness"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timezone.timedelta(days=1)
        return cls.objects.filter(
            user=user,
            created_at__gte=today_start,
            created_at__lt=today_end
        ).order_by('created_at')
    
    @classmethod
    def has_today_tasks(cls, user):
        """Check if user has tasks for today"""
        return cls.get_today_tasks(user).exists()


class FamilyArtDaily(models.Model):
    """Daily family art keywords and generated image"""
    family_name = models.CharField(max_length=100)
    # Change default to a callable function
    keywords = models.JSONField(default=list)  
    image_url = models.URLField(null=True, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['family_name', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.family_name}'s art ({self.date})"

    def clean(self):
        """Validate the model data"""
        super().clean()
        # Ensure keywords is a list
        if not isinstance(self.keywords, list):
            self.keywords = []
        # Ensure maximum 3 keywords
        if len(self.keywords) > 3:
            raise ValidationError("Maximum 3 keywords allowed")

    def add_keyword(self, keyword):
        """
        Add keyword if less than 3 keywords exist
        Args:
            keyword (str): Keyword to add
        Returns:
            bool: True if keyword was added, False otherwise
        """
        # Validate input
        if not keyword or not isinstance(keyword, str):
            return False
            
        # Clean keyword
        keyword = keyword.strip()
        if not keyword:
            return False
            
        # Check length limit
        if len(self.keywords) >= 3:
            return False
            
        # Check for duplicates
        if keyword in self.keywords:
            return False
            
        # Add keyword
        if not isinstance(self.keywords, list):
            self.keywords = []
        self.keywords.append(keyword)
        return True
class DailyQuiz(models.Model):
    """
    Daily quiz model to store questions generated by Gemini
    Includes question, options, correct answer and explanation
    """
    question = models.CharField(max_length=500)
    options = models.JSONField()  # Stores the list of options
    correct_answer = models.IntegerField()  # Index of correct option (zero-based)
    explanation = models.TextField()
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['date']

    def __str__(self):
        return f"Quiz for {self.date}: {self.question[:50]}..."

    def clean(self):
        """Validate the model data"""
        super().clean()
        # Ensure correct_answer is within valid range (zero-based index)
        if not isinstance(self.options, list):
            raise ValidationError("Options must be a list")
        if self.correct_answer < 0 or self.correct_answer >= len(self.options):
            raise ValidationError("Correct answer index out of range")

class QuizAnswer(models.Model):
    """Store user answers to daily quizzes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(DailyQuiz, on_delete=models.CASCADE)
    answer = models.IntegerField()
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'quiz']  # Each user can answer each quiz only once

    def __str__(self):
        return f"{self.user.username}'s answer to quiz {self.quiz.id}"
    
    def clean(self):
        """Validate the answer is within valid range"""
        super().clean()
        if self.quiz and (self.answer < 0 or self.answer >= len(self.quiz.options)):
            raise ValidationError("Answer index out of range")
        
        # Set is_correct based on answer
        if self.quiz:
            self.is_correct = (self.answer == self.quiz.correct_answer)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    