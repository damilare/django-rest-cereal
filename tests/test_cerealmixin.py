import unittest
import json

from django.db import models
from django.conf import settings
from rest_framework.test import APIClient, APIRequestFactory, APITestCase, \
    force_authenticate
from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer

from cereal.mixins import CerealMixin, CerealException
from cereal.serializers import LazySerializer


class RecursiveParseFieldsTest(unittest.TestCase):
    '''
    Test the recursive field parsing method (parse_fields_to_nested_tree)
    '''

    def test_parse_fields_to_nested_tree_empty_case(self):
        result = CerealMixin.parse_fields_to_nested_tree('')
        assert len(result.normal_fields) == 0 and \
               len(result.nested_fields) == 0 and \
               len(result.options) == 0, \
               'Empty string input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_multiple_empty_commas(self):
        result = CerealMixin.parse_fields_to_nested_tree(',,,')
        assert len(result.normal_fields) == 0 and \
               len(result.nested_fields) == 0 and \
               len(result.options) == 0, \
               'Empty string with commas input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_single_field(self):
        fields_string = 'job'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 1 and \
               len(result.nested_fields) == 0 and \
               len(result.options) == 0, \
               'Single field string input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_default_option(self):
        fields_string = ':default'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 0 and \
               len(result.nested_fields) == 0 and \
               len(result.options) == 1, \
               'Single option field string input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_multiple_fields(self):
        fields_string = 'jobs,job,document,user'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 0 and \
               len(result.nested_fields) == 0 and \
               len(result.options) == 1, \
               'Single option field string input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_overlapping_fields(self):
        fields_string = 'job,job'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 2 and \
               len(result.nested_fields) == 0 and \
               len(result.options) == 0, \
               'Overlapping fields string input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_multiple_fields(self):
        fields_string = 'jobs,job,document,user,:default'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 4 and \
               len(result.nested_fields) == 0 and \
               len(result.options) == 1, \
               'Single option multiple fields field string input ' \
               'returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_basic_nested(self):
        fields_string = 'job(user)'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 0 and \
               len(result.nested_fields) == 1 and \
               len(result.options) == 0, \
               'Basic nested field string input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_basic_nested_with_normal_fields(self):
        fields_string = 'time,job(user,document),address'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 2 and \
               len(result.nested_fields) == 1 and \
               len(result.nested_fields['job'].normal_fields) == 2 and \
               len(result.options) == 0, \
               'Basic nested field string input returned {0}'.format(result)

    def test_parse_fields_to_nested_tree_very_nested(self):
        fields_string = 'a(b(c(d),e(f)),g(h(i)))'
        result = CerealMixin.parse_fields_to_nested_tree(
            fields_string
        )
        assert len(result.normal_fields) == 0 and \
               len(result.nested_fields) == 1 and \
               len(result.options) == 0, \
               'Very nested field string input returned {0}'.format(result)
        assert len(result.nested_fields['a'].nested_fields) == 2, \
            'Very nested field string first nest level had error: {0}'\
            .format(result.nested_fields['a'])
        assert len(result.nested_fields['a'].nested_fields['b'].nested_fields['e'].normal_fields) == 1, \
            'Very nested field string nest level 3 had error: {0}'\
            .format(result.nested_fields['a'].nested_fields['b'].nested_fields['e'])
        assert len(result.nested_fields['a'].nested_fields['g'].nested_fields['h'].normal_fields) == 1, \
            'Very nested field string nest level 3 had error: {0}'\
            .format(result.nested_fields['a'].nested_fields['g'].nested_fields['h'])

    def test_parse_fields_to_nested_tree_multiple_open_brackets_inarow(self):
        fields_string = 'job((value))'
        try:
            result = CerealMixin.parse_fields_to_nested_tree(
                fields_string
            )
            assert False, 'Expected error - too many open brackets. No error.'
        except CerealException:
            pass

    def test_parse_fields_to_nested_tree_too_many_close_brackets(self):
        fields_string = 'job(value))'
        try:
            result = CerealMixin.parse_fields_to_nested_tree(
                fields_string
            )
            assert False, 'Expected error - too many close brackets. No error.'
        except CerealException:
            pass

    def test_parse_fields_to_nested_tree_too_few_close_brackets(self):
        fields_string = 'job(value'
        try:
            result = CerealMixin.parse_fields_to_nested_tree(
                fields_string
            )
            assert False, 'Expected error - too few close brackets. No error.'
        except CerealException:
            pass


class NestedTestModel(models.Model):
    val = models.IntegerField()
    nest = models.ForeignKey('cerebro.NestedTestModel', null=True, blank=True)

    class Meta:
        app_label = 'cerebro'


class NestLevel2TestSerializer(ModelSerializer):
    class Meta:
        model = NestedTestModel
        fields = ('val',)


class NestLevel1TestSerializer(ModelSerializer):
    nest = NestLevel2TestSerializer()

    class Meta:
        model = NestedTestModel
        fields = ('val', 'nest')


class BaseTestSerializer(CerealMixin, ModelSerializer):
    nest = NestLevel1TestSerializer()

    class Meta:
        model = NestedTestModel
        fields = ('val', 'nest')


class NestedTestView(ModelViewSet):
    model = NestedTestModel
    serializer_class = BaseTestSerializer
    queryset = NestedTestModel.objects.all()


class CerealMixinTest(unittest.TestCase):
    '''
    Tests for the CerealMixin initialization and responses to requests
    (depends on the parse_field_to_nested_tree method)
    '''

    request_factory = APIRequestFactory()

    api_key = settings.APIKEYS["internal"]
    request_data = {
        'api_key': api_key
    }

    def setUp(self):
        self.client = APIClient()
        self.model1 = NestedTestModel.objects.create(val=1)
        self.model2 = NestedTestModel.objects.create(nest=self.model1, val=2)
        self.model3 = NestedTestModel.objects.create(nest=self.model2, val=3)
        self.url = '/nest/{0}'.format(self.model1.id)

    def _get_response(self, fields_string):
        if fields_string:
            self.request_data['fields'] = fields_string
        elif self.request_data.get('fields'):
            del self.request_data['fields']
        request = self.request_factory.get(self.url, self.request_data)
        api_view = NestedTestView.as_view({'get': 'retrieve'})
        response = api_view(request, pk=self.model3.id)
        response.render()
        return response

    def test_no_request_serializer(self):
        serializer = BaseTestSerializer(self.model3)
        assert serializer.data['val'] == 3
        assert serializer.data['nest']['val'] == 2

    def test_basic_request(self):
        fields_string = ''
        response = self._get_response(fields_string)
        self.assertEqual(
            response.content,
            '{"val":3,"nest":{"val":2,"nest":{"val":1}}}'
        )

    def test_assign_serializer_fields_single_normal_field(self):
        fields_string = 'val'
        response = self._get_response(fields_string)
        self.assertEqual(
            response.content,
            '{"val":3}'
        )

    def test_assign_serializer_fields_single_nested_field(self):
        fields_string = 'nest(val)'
        response = self._get_response(fields_string)
        self.assertEqual(
            response.content,
            '{"nest":{"val":2}}'
        )

    def test_assign_serializer_fields_double_nested_initially_not_in_fields(self):
        fields_string = 'val,nest(nest(val),val)'
        response = self._get_response(fields_string)
        expected_response = json.loads(
            '{"nest":{"nest":{"val":1},"val":2},"val":3}'
        )
        self.assertEqual(
            json.dumps(json.loads(response.content)),
            json.dumps(expected_response)
        )

    def test_assign_serializer_fields_double_nested_random_options(self):
        fields_string = 'val,nest(:random,nest(:random,val),val),:random'
        response = self._get_response(fields_string)
        expected_response = json.loads(
            '{"nest":{"nest":{"val":1},"val":2},"val":3}'
        )
        self.assertEqual(
            json.dumps(json.loads(response.content)),
            json.dumps(expected_response)
        )

    def test_assign_serializer_fields_default_includes(self):
        fields_string = ':default'
        response = self._get_response(fields_string)
        self.assertEqual(
            response.content,
            '{"val":3,"nest":{"val":2,"nest":{"val":1}}}'
        )

    def test_assign_serializer_fields_nested_default_includes(self):
        fields_string = ':default,nest(:default,nest(:default))'
        response = self._get_response(fields_string)
        self.assertEqual(
            response.content,
            '{"val":3,"nest":{"val":2,"nest":{"val":1}}}'
        )

    def test_assign_serializer_fields_error_field(self):
        fields_string = 'error'
        response = self._get_response(fields_string)
        expected_response1 = json.loads(
            '{"reason": "Field error isn\'t defined in serializer.", '
            '"code": 400}'
        )
        expected_response2 = json.loads(
            '{"detail": "Field error isn\'t defined in serializer."}'
        )
        self.assertIn(
            json.dumps(json.loads(response.content)),
            [json.dumps(expected_response1), json.dumps(expected_response2)]
        )

    def test_assign_serializer_fields_error_nested_field(self):
        fields_string = 'nest(error(val))'
        response = self._get_response(fields_string)
        expected_response1 = json.loads(
            '{"reason": "Field error isn\'t defined in serializer.", '
            '"code": 400}'
        )
        expected_response2 = json.loads(
            '{"detail": "Field error isn\'t defined in serializer."}'
        )
        self.assertIn(
            json.dumps(json.loads(response.content)),
            [json.dumps(expected_response1), json.dumps(expected_response2)]
        )

    def test_defaults_arent_modified(self):
        fields_string = 'val'
        response = self._get_response(fields_string)
        fields_string = ':default'
        response = self._get_response(fields_string)
        self.assertEqual(
            response.content,
            '{"val":3,"nest":{"val":2,"nest":{"val":1}}}'
        )


class CircularTestSerializer1(CerealMixin,
                              ModelSerializer):
    nest = LazySerializer('CircularTestSerializer2')

    class Meta:
        model = NestedTestModel
        fields = ('val', 'nest')
        circular = True


class CircularTestSerializer2(CerealMixin,
                              ModelSerializer):
    nest = LazySerializer('CircularTestSerializer1')

    class Meta:
        model = NestedTestModel
        fields = ('val', 'nest')
        circular = True


class CircularTestView1(ModelViewSet):
    model = NestedTestModel
    serializer_class = CircularTestSerializer1
    queryset = NestedTestModel.objects.all()


class CircularTestView2(ModelViewSet):
    model = NestedTestModel
    serializer_class = CircularTestSerializer2
    queryset = NestedTestModel.objects.all()


LazySerializer.convert_serializers(
    globals(), [CircularTestSerializer1, CircularTestSerializer2]
)


class CircularSerializersTest(unittest.TestCase):
    '''
    Test circular referencing of serializers and the LazySerializer.
    '''

    request_factory = APIRequestFactory()
    client = APIClient()
    api_key = settings.APIKEYS["internal"]
    request_data = {
        'api_key': api_key
    }
    url = '/nest/{0}/'
    encoding = 'utf-8'

    def setUp(self):
        self.model1 = NestedTestModel.objects.create(val=4)
        self.model2 = NestedTestModel.objects.create(nest=self.model1, val=5)
        self.model1.nest = self.model2
        self.model1.save()

    def _get_response_from_view1(self, fields_string):
        if fields_string is not None:
            self.request_data['fields'] = fields_string
        else:
            del self.request_data['fields']
        request = self.request_factory.get(
            self.url.format(self.model1.id), self.request_data
        )

        api_view1 = CircularTestView1.as_view({'get': 'retrieve'})
        response = api_view1(request, pk=self.model1.id)
        response.render()
        return response

    def _get_response_from_view2(self, fields_string):
        if fields_string:
            self.request_data['fields'] = fields_string
        else:
            del self.request_data['fields']
        request = self.request_factory.get(
            self.url.format(self.model2.id), self.request_data
        )
        api_view2 = CircularTestView2.as_view({'get': 'retrieve'})
        response = api_view2(request, pk=self.model2.id)
        response.render()
        return response

    def test_circular_no_nesting(self):
        fields_string = 'val'
        response = self._get_response_from_view1(fields_string)
        expected_response = json.loads('{"val":4}')
        self.assertEqual(
            json.dumps(json.loads(response.content)),
            json.dumps(expected_response)
        )

    def test_circular_nesting_first_defined_view(self):
        fields_string = 'nest(val)'
        response = self._get_response_from_view1(fields_string)
        expected_response = json.loads('{"nest":{"val":5}}')
        self.assertEqual(
            json.dumps(json.loads(response.content)),
            json.dumps(expected_response)
        )

    def test_circular_nesting_second_defined_view(self):
        fields_string = 'nest(val)'
        response = self._get_response_from_view2(fields_string)
        expected_response = json.loads('{"nest":{"val":4}}')
        self.assertEqual(
            json.dumps(json.loads(response.content)),
            json.dumps(expected_response)
        )

    def test_circular_double_nesting(self):
        fields_string = 'val,nest(val,nest(val))'
        response = self._get_response_from_view1(fields_string)
        expected_response = json.loads(
            '{"val":4,"nest":{"val":5,"nest":{"val":4}}}'
        )
        self.assertEqual(
            json.dumps(json.loads(response.content)),
            json.dumps(expected_response)
        )

    def test_infinite_circular_nesting_error(self):
        fields_string = ''
        response = self._get_response_from_view1(fields_string)
        expected_response = json.loads(
            '{"detail": "\'fields\' query parameter must be defined in this '
            'request due to circular serializers."}'
        )
        self.assertEqual(
            json.dumps(json.loads(response.content)),
            json.dumps(expected_response)
        )
