from django.db import models


class NestedTestModel(models.Model):
    val = models.IntegerField()
    nest = models.ForeignKey('self', null=True, blank=True, default=None,
                             related_name='parent')
