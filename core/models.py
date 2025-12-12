from django.contrib.auth.models import User
from django.db import models
from django.utils import  timezone

class TimeStampedModel(models.Model):
    """Abstract base model with created and updated timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class AuditableModel(TimeStampedModel):
    """Abstract model with user who created and last modified"""
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL,null=True,blank=True,related_name='%(class)s_created_by')
    updated_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL,null=True,blank=True,related_name='%(class)s_created_by')

    class Meta:
        abstract = True