from django.db import models


class NestedTestModel(models.Model):
    val = models.IntegerField()
    nest = models.ForeignKey('self', null=True, blank=True, default=None,
                             related_name='parent')


class TwoNestedTestModel(models.Model):
    val = models.IntegerField()
    nest1 = models.ForeignKey(NestedTestModel, null=True, blank=True,
                              default=None, related_name='twonestedparent1')
    nest2 = models.ForeignKey(NestedTestModel, null=True, blank=True,
                              default=None, related_name='twonestedparent2')


class ManyNestedTestModel(models.Model):
    val = models.IntegerField()
    nests = models.ManyToManyField(NestedTestModel)

