from django.db import models

from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer

from cereal.mixins import CerealMixin
from cereal.serializers import LazySerializer, MethodSerializer


class NestedTestModel(models.Model):
    val = models.IntegerField()
    nest = models.ForeignKey('self', null=True, blank=True, default=None,
                             related_name='parent')
