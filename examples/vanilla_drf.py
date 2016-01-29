# This would normally be split into:
# - models.py
# - serializers.py
# - views.py
# - urls.py
# but this makes vanilla vs cereal easier to compare.

###
# models.py
###
from django.db import models


class Player(models.Model):
    field1 = models.IntegerField()
    field2 = models.IntegerField()
    field3 = models.IntegerField()
    field4 = models.IntegerField()
    field5 = models.IntegerField()
    field6 = models.IntegerField()
    field7 = models.IntegerField()
    field8 = models.IntegerField()
    field9 = models.IntegerField()

    friends = models.ManyToManyField('self', related_name='reverse_friends')


class Team(models.Model):
    field1 = models.IntegerField()
    field2 = models.IntegerField()
    field3 = models.IntegerField()
    field4 = models.IntegerField()
    field5 = models.IntegerField()
    field6 = models.IntegerField()
    field7 = models.IntegerField()
    field8 = models.IntegerField()
    field9 = models.IntegerField()

    players = models.ManyToManyField(Player)
    captain = models.ForeignKey(Player, related_name='captain_of')
    rivals = models.ManyToManyField('self', related_name='rivals_of')
    leagues = models.ManyToManyField('League')


class League(models.Model):
    field1 = models.IntegerField()
    field2 = models.IntegerField()
    field3 = models.IntegerField()
    field4 = models.IntegerField()
    field5 = models.IntegerField()
    field6 = models.IntegerField()
    field7 = models.IntegerField()
    field8 = models.IntegerField()
    field9 = models.IntegerField()

    players = models.ManyToManyField(Player)
    teams = models.ManyToManyField(Team)
    parent_league = models.ManyToManyField('self', related_name='subleagues')


###
# serializers.py
###
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import APIException

