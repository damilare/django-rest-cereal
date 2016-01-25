from django.db import models

from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer


class NestedTestModel(models.Model):
    field1 = models.IntegerField()
    field2 = models.IntegerField()
    field3 = models.IntegerField()
    field4 = models.IntegerField()
    field5 = models.IntegerField()
    field6 = models.IntegerField()
    field7 = models.IntegerField()
    field8 = models.IntegerField()
    field9 = models.IntegerField()
    
    nest1 = models.ForeignKey('self', null=True, blank=True, default=None,
                             related_name='parent1')
