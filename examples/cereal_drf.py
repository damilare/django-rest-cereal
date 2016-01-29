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

from cereal.mixins import CerealMixin
from cereal.serializers import LazySerializer, MethodSerializerMixin


class BadRequest(APIException):
    status_code = 400
    default_detail = 'Bad request.'


class PlayerCircularMethodSerializer(CerealMixin, MethodSerializerMixin,
                                     ModelSerializer):
    teams = LazySerializer('TeamCircularSerializer', many=True)
    leagues = LazySerializer('LeagueCircularMethodSerializer', many=True)

    class Meta:
        model = Player
        circular = True
        fields = (
            'field1', 'field2', 'field3', 'field4', 'field5', 'field6',
            'field7', 'field8', 'field9', 'teams', 'leagues'
        )


class TeamCircularSerializer(CerealMixin, ModelSerializer):
    players = LazySerializer('PlayerCircularMethodSerializer', many=True)
    captain = LazySerializer('PlayerCircularMethodSerializer')
    rivals = LazySerializer('TeamCircularSerializer')
    leagues = LazySerializer('TeamCircularMethodSerializer', many=True)
    summer_leagues = LazySerializer('LeagueCircularMethodSerializer',
                                    method_name='get_summer_leagues')
    players_joined_in_month = LazySerializer(
        'PlayerCircularMethodSerializer',
        method_name='get_players_joined_in_month'
    )

    class Meta:
        model = Team
        circular = True
        fields = (
            'field1', 'field2', 'field3', 'field4', 'field5', 'field6',
            'field7', 'field8', 'field9', 'players', 'captain', 'rivals',
            'leagues', 'summer_leagues', 'winter_leagues',
            'players_joined_in_month'
        )

    # This is what is returned by the summer_leagues field on this serializer.
    # Counter-intuitively, you need to make the League Serializer returned in
    # this method inherit from the MethodSerializerMixin. This is because the
    # MethodSerializerMixin does magic in the serializer's to_representation()
    # method, which accesses its parent serializer's get_x method.
    #
    # With vanilla DRF, you have to return json data (serializer.data) to get
    # this kind of functionality. This returns a list of ModelSerializer objects
    # that you can select fields from per-request (using CerealMixin).
    def get_summer_leagues(self, player):
        return player.league_set.filter(field1=1)

    def get_winter_leagues(self, player):
        return player.league_set.filter(field1=2)

    # The MethodSerializerMixin gives the serializer access the the request
    # context. This kind of functionality is not possible at the serializer
    # level in vanilla DRF - a new view/endpoint would be required.
    def get_players_joined_in_month(self, league):
        request = self.context['request']
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

        return league.players.filter(field1=month)


class LeagueCircularMethodSerializer(CerealMixin, MethodSerializerMixin,
                                     ModelSerializer):
    players = LazySerializer('PlayerCircularMethodSerializer', many=True)
    teams = LazySerializer('TeamCircularSerializer', many=True)
    subleagues = LazySerializer('LeagueCircularMethodSerializer', many=True)
    parent_league = LazySerializer('LeagueCircularMethodSerializer')

    class Meta:
        model = League
        circular = True
        fields = (
            'field1', 'field2', 'field3', 'field4', 'field5', 'field6',
            'field7', 'field8', 'field9', 'players', 'teams', 'subleagues',
            'parent_league'
        )

# *** Any serializer that has a LazySerializer inside must be put here. ***
# *** The serializers referenced in the LazySerializer must be accessible in
# the namespace passed in to the convert_serializers method. ***
#
# This is required for LazySerializers to resolve properly. It's necessary
# because of circular nesting - the serializers being referenced haven't been
# initialized yet.
LazySerializer.convert_serializers(
    globals(),
    [
        PlayerCircularMethodSerializer,
        TeamCircularSerializer,
        LeagueCircularMethodSerializer
    ]
)


###
# views.py
###
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView
from rest_framework.filters import DjangoFilterBackend


class PlayerViewSet(ModelViewSet):
    model = Player
    serializer_class = PlayerCircularMethodSerializer
    queryset = Player.objects.all()


# This is an example of what you shouldn't put as a method field in a
# serializer. Fields on serializers should be things that will be reused in
# different views. Views used for searches typically should be their own
# endpoint.
# If the fields aren't re-used often, you should consider whether your data
# access logic would be better placed in a View.
class PlayersSearchListView(ListAPIView):
    model = Player
    serializer_class = PlayerCircularMethodSerializer
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
    serializer_class = TeamCircularSerializer
    queryset = Team.objects.all()


class LeagueViewSet(ModelViewSet):
    model = League
    serializer_class = LeagueCircularMethodSerializer
    queryset = League.objects.all()


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
        r'^league/(?P<pk>\d+)/?$',
        LeagueViewSet.as_view({'get': 'retrieve'}),
        name='league_detail'
    ),
)

###
# Example requests
###
import requests

# 1.
# I want some basic details about a player
response = requests.get(
    url='http://localhost/player/21/',
    query_params='fields=id,field1,field2'
)

# 2.
# I want some deeper details about a player
captain_fields = 'id,field3'
team_fields = 'id,field1,captain({captain_fields})'.format(**locals)
league_fields = 'id,field2'

# equivalent to '(id,field1,teams(id,field1,captain(id,field3)),leagues(...
fields = 'id,field1,teams({team_fields}),leagues({league_fields})'.format(
    **locals)

response = requests.get(
    url='http://localhost/player/21/',
    query_params='fields=' + fields
)


# 3.
# I want to search for players with some properties
# (the captains of 1st place teams).

response = requests.get(
    url='http://localhost/player/21/',
    query_params='fields=id,field1,team(id,field2)&is_captain=true'
                 '&team_rank=1'
)

# 4.
# I want some details about a team and their summer activity
response = requests.get(
    url='http://localhost/team/21/',
    query_params='fields=id,field1,players_joined_in_month(id),'
                 'summer_leagues(id,field1)'
                 '&month=6'
)

# 5.
# I want basic details about a league

response = requests.get(
    url='http://localhost/league/21/',
    query_params='fields=id,field1'
)

# 6.
# I want deep details about a league - parent league winter info

parent_fields = 'id,teams(winter_leagues(id),players_joined_in_month(id)'
response = requests.get(
    url='http://localhost/league/21/',
    query_params='fields=id,field1,parent_league({parent_fields})'
                 '&month=10'.format(**locals)
)
