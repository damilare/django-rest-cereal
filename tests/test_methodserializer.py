import unittest
import json

from rest_framework.test import APIClient, APIRequestFactory, APITestCase, \
    force_authenticate
from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer

from cereal.mixins import CerealMixin
from cereal.serializers import MethodSerializerMixin
from cerealtesting.models import NestedTestModel


class XMethodSerializer(MethodSerializerMixin, ModelSerializer):

    class Meta:
        model = NestedTestModel
        fields = ('val', 'nest')


class YMethodSerializer(CerealMixin, MethodSerializerMixin, ModelSerializer):
    added_xs = XMethodSerializer(method_name='get_nestedtestmodel')

    class Meta:
        model = NestedTestModel
        fields = ('val', 'added_xs')

    def get_nestedtestmodel(self, obj):
        # Test method that uses a combination of the value of the object hit
        # by the request and a query param in the request to determine what
        # results to serialize by the XMethodSerializer

        # Return x's where their value is the sum of the object's value and the
        # query param x_adder.
        assert self.context.get('request', None), \
            "context (of the request) not saved in serializer"
        target_xs_adder = self.context['request'].query_params.get('added_xs',
                                                                   None)
        if target_xs_adder is None:
            return []

        target_xs = obj.val + int(target_xs_adder)
        x_results = NestedTestModel.objects.filter(val=int(target_xs))
        return x_results


    # This doesn't work right now because views don't pass the args/kwargs of a
    # serializer when they initialize them.
    # def get_x(self, obj):
    #     # Return the smallest x >= max(min_x, obj.val) where min_x is in
    #     # request query_params
    #     assert self.context.get('request', None), \
    #         "context (of the request) not saved in serializer"
    #     min_x = self.context['request'].QUERY_PARAMS.get('x_min', None)
    #     if min_x is None:
    #         return []
    #
    #     min_x = max(int(min_x), obj.val)
    #
    #     x_results = NestedTestModel.objects.filter(
    #         val__gte=min_x
    #     ).order_by('val')
    #     if x_results:
    #         return x_results[0]
    #     else:
    #         return None


class YViewSet(ModelViewSet):
    model = NestedTestModel
    serializer_class = YMethodSerializer
    queryset = NestedTestModel.objects.all()


class MethodSerializerMixinTest(unittest.TestCase):
    request_factory = APIRequestFactory()

    def setUp(self):
        self.client = APIClient()

    def setUp(self):
        NestedTestModel.objects.create(val=1)
        self.test_models1 = \
            [NestedTestModel.objects.create(val=i) for i in range(2, 5)]
        self.test_models2 = \
            [NestedTestModel.objects.create(val=i) for i in range(2, 5)]

    def _get_response(self, request_data, pk):
        request = self.request_factory.get('/{0}'.format(pk), request_data)
        api_view = YViewSet.as_view({'get': 'retrieve'})
        response = api_view(request, pk=pk)
        response.render()
        return response

    def test_request_basic(self):
        request_data = {'added_xs': 1, 'fields': 'added_xs(val)'}
        response = self._get_response(request_data, self.test_models1[0].id)
        results = json.loads(response.content)
        for result in results['added_xs']:
            self.assertEqual(result['val'], 3)

    def test_request_basic_2(self):
        request_data = {'added_xs': 2, 'fields': 'added_xs(val)'}
        response = self._get_response(request_data, self.test_models1[0].id)
        results = json.loads(response.content)
        for result in results['added_xs']:
            self.assertEqual(result['val'], 4)
