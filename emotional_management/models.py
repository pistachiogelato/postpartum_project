from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import ValidationError
from django.utils import timezone
#from django.contrib.postgres.fields import JSONField  

# 定义用户模型
class User(AbstractUser):
    family = models.ForeignKey('Family', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    role = models.CharField(max_length=50, choices=[('mom', 'Mom'), ('husband', 'Husband'), ('elder', 'Elder'), ('friend', 'Friend')])

# 定义家庭模型
class Family(models.Model):
    name = models.CharField(max_length=100, unique=True)
    daily_tasks = models.JSONField(default=list)  # 存储每天任务的字段
    daily_tasks_date = models.DateField(auto_now_add=True)

    def clean(self):
        if self.members.count() > 0:
            raise ValidationError('家庭不能在创建时已有成员。')

    def add_member(self, user):
        user.family = self
        user.save()

# 创建用户并关联家庭的函数
def create_user_and_family(username, password, family_name, role):
    family, created = Family.objects.get_or_create(name=family_name)
    user = User.objects.create_user(username=username, password=password, role=role)
    user.family = family
    user.save()
    return user