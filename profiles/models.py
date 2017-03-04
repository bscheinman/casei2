from __future__ import unicode_literals

from cix.fields import UUIDField
from datetime import datetime
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User)
    join_date = models.DateTimeField(auto_now_add=True)
    verification_id = UUIDField(auto=True)
    is_verified = models.BooleanField(default=False)

    def __unicode__(self):
        return self.user.username


admin.site.register(UserProfile)


# Automatically create a profile for each user that is created
@receiver(post_save, sender=User, weak=False)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
