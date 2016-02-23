# This would normally be split into:
# - models.py
# - serializers.py
# - views.py
# - urls.py
# but this makes vanilla vs cereal easier to compare.

###
# Example requests
###
import requests
import json

# 1.
# I want some basic details about a player.
response = requests.get(
    url='http://localhost/player/21/'
)

# 2.
# I want some deeper details about a player
response = requests.get(
    url='http://localhost/player/21/',
)


# 3.
# I want to search for players with some properties
# (the captains of 1st place teams).

response = requests.get(
    url='http://localhost/player/',
    query_params='is_captain=true&team_rank=1'
)

# 4.
# I want some details about a team and their summer activity
response = requests.get(
    url='http://localhost/team/21/'
)

# 5.
# I want basic details about a league

response = requests.get(
    url='http://localhost/league/21/'
)

# 6.
# I want deep details about a league - parent league winter info

league = json.loads(requests.get(
    url='http://localhost/league/21/'
))
parent_league = league['parent_league']['id']
parent_league = json.loads(requests.get(
    url='http://localhost/league/' + str(parent_league) + '/'
))

teams = {}
for team in parent_league['teams']:
    teams_and_their_winter_leagues[team['id']] = json.loads(requests.get(
        url='http://localhost/' + team['id'] + '/'
    ))
    teams_and_their_winter_leagues[team['id']]['players_joined_in_october'] = \
        json.loads(requests.get(
            url='http://localhost/team/{0}/players-joined-in/?month=10'.format(
                team['id'])
        ))




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
from rest_framework.serializers import ModelSerializer, MethodSerializer
from rest_framework.exceptions import APIException


class BadRequest(APIException):
    status_code = 400
    default_detail = 'Bad request.'


class FlatPlayerSerializer(ModelSerializer):

    class Meta:
        model = Player
        fields = (
            'id', 'field1', 'field2', 'field3'
        )


class FullPlayerSerializer(ModelSerializer):

    class Meta:
        model = Player
        fields = (
            'id', 'field1', 'field2', 'field3', 'field4', 'field5', 'field6',
            'field7', 'field8', 'field9',
        )


class FlatTeamSerializer(ModelSerializer):

    class Meta:
        model = Team
        fields = (
            'id', 'field1', 'field2', 'field3'
        )


class FlatLeagueSerializer(ModelSerializer):

    class Meta:
        model = League
        fields = (
            'id', 'field1', 'field2', 'field3'
        )


class LeagueSerializer(ModelSerializer):

    players = FlatPlayerSerializer(many=True)
    teams = FlatTeamSerializer(many=True)
    subleagues = FlatLeagueSerializer(many=True)
    parent_league = FlatLeagueSerializer()

    class Meta:
        model = League
        fields = (
            'field1', 'field2', 'field3', 'field4', 'field5', 'field6',
            'field7', 'field8', 'field9', 'players', 'teams', 'subleagues',
            'parent_league'
        )


class TeamSerializer(ModelSerializer):
    players = FlatPlayerSerializer(many=True)
    captain = FullPlayerSerializer()
    rivals = FlatTeamSerializer()
    leagues = LeagueSerializer(many=True)
    summer_leagues = LeagueSerializer(many=True)
    winter_leagues = LeagueSerializer(many=True)

    class Meta:
        model = Team
        fields = (
            'id', 'field1', 'field2', 'field3', 'field4', 'field5', 'field6',
            'field7', 'field8', 'field9', 'players', 'captain', 'rivals',
            'leagues', 'summer_leagues', 'winter_leagues'
        )


# This has to be defined after the other serializers because it uses them.
# This can cause problems in the future when those models' serializers need
# something like this serializer. Also, this will return much more data than any
# one request needs.
class PlayerSerializer(ModelSerializer):

    teams = TeamSerializer(many=True, source='team_set')
    leagues = LeagueSerializer(many=True, source='league_set')

    class Meta:
        model = Player
        fields = (
            'field1', 'field2', 'field3', 'field4', 'field5', 'field6',
            'field7', 'field8', 'field9', 'teams', 'leagues'
        )

# Padding to make the files the same size
























###
# views.py
###
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView, APIView
from rest_framework.filters import DjangoFilterBackend


class PlayersSearchListView(ListAPIView, ModelViewSet):
    model = Player
    serializer_class = PlayerSerializer
    queryset = Player.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('field1', 'field2', 'field3', 'field4', 'field5')

    def get_queryset(self, *args, **kwargs):
        queryset = super(PlayersSearchListView, self).get_queryset(
            *args, **kwargs
        )
        # Do some really specific filtering here based on the request.

        # Then.
        return queryset


class TeamViewSet(ModelViewSet):
    model = Team
    serializer_class = TeamSerializer
    queryset = Team.objects.all()


class LeagueViewSet(ModelViewSet):
    model = League
    serializer_class = LeagueSerializer
    queryset = League.objects.all()


class PlayersJoinedInMonthView(APIView):

    def get(self, request, **kwargs):
        month = request.query_params.get('month', None)
        if month is None:
            raise BadRequest('month is required in query params to access '
                             'get_players_joined_in_month attribute')
        try:
            month = int(month)
        except (ValueError, AttributeError):
            raise BadRequest(
                'month={0} must be an integer'.format(month)
            )

        if not 1 <= month <= 12:
            raise BadRequest(
                'month={0} must be between 1-12'.format(month)
            )

        #################finish this part
        return league.players.filter(field1=month)


###
# URLs
###
from django.conf.urls import patterns, url

urlpatterns = patterns(
    url(
        r'^player/(?P<pk>\d+)/?$',
        PlayerViewSet.as_view({'get': 'retrieve'}),
        name='player_detail'
    ),
    url(
        r'^player/search/?$',
        PlayersSearchListView.as_view({'get': 'list'}),
        name='player_search'
    ),
    url(
        r'^team/(?P<pk>\d+)/?$',
        TeamViewSet.as_view({'get': 'retrieve'}),
        name='team_detail'
    ),
    url(
        r'^team/(?P<pk>\d+)/players-joined-in-month?$',
        PlayersJoinedInMonthView.as_view({'get': 'retrieve'}),
        name='players_joined_in_month'
    ),
    url(
        r'^league/(?P<pk>\d+)/?$',
        LeagueViewSet.as_view({'get': 'retrieve'}),
        name='league_detail'
    ),
)
