import random
import itertools
from rest_framework.exceptions import APIException
from rest_cereal.serializers import MethodSerializerMixin


class CerealException(APIException):
    status_code = 400


class CerealFields:
    def __init__(self):
        # List of strings (of field names).
        self.normal_fields = []

        # Nested_fields is a dict of: 'nested_field_name': CerealFields
        self.nested_fields = {}

        # A set of (string) options for the serializer. Options can be used
        # to modify field selection or CerealMixin behaviour. For example,
        # passing the option :schema could return all the fields available
        # to be accessed on a serializer instead of returning the serializer
        # data (:schema is not implemented).
        self.options = set()

    def __str__(self):
        return 'CerealFields(normal_fields: ' + str(self.normal_fields) + \
               ', ' + 'nested_fields: ' + str(self.nested_fields) + ', ' + \
               'options: ' + str(self.options) + ')'

    def flat_string(self):
        flat_nested_fields = ['{}({})'.format(name, f.flat_string())
                              for name, f in self.nested_fields.items()]
        return ','.join(itertools.chain(flat_nested_fields, self.normal_fields))


def parse_fields_to_nested_tree_rec(field_iter, field=None,
                                    close_bracket=False):
    '''Produces the return CerealFields struct (see above) for the field_iter
    list of strings. Recursively calls itself on nested fields to the nested
    fields' CerealFields until the field_iter is exhausted.

    :param field_iter: the iterator for the list of fields
    :param field: the current field being examined (and added to the list
    of fields for the serializer currently being worked on)
    :param close_bracket: whether a bracket must be closed in this recursive
    step
    :return: CerealFields object

    '''
    cereal_fields = CerealMixin.CerealFields()

    # base case (when the function is called initially)
    if field is None:
        try:
            field = next(field_iter)
        except StopIteration:
            return cereal_fields

    # go through each field in the field_iter
    while True:
        # it's an 'option', remove the colon when adding to the options list
        if field and field[0] == ':':
            if ')' in field:
                last_option = field[1:-1]
                cereal_fields.options.add(last_option)
                return cereal_fields
            else:
                cereal_fields.options.add(field[1:])
        elif '(' in field:
            # Only split the first occurrence of '(' in case of multiple
            # immediate nests and pass the rest to the nested field.
            # Ex: 'field1(field2(field3' ->
            # serializer['field1'] contains recursive_fn('field2(field3')
            nested = field.split('(', 1)
            if not nested[0]:
                raise CerealException(
                    "Fields parameter bad format: nested field without "
                    "nested field name."
                )

            cereal_fields.nested_fields[nested[0]] = \
                CerealMixin.\
                parse_fields_to_nested_tree_rec(
                    field_iter, nested[1], True
                )
        elif field == ')':
            if not close_bracket:
                raise CerealException(
                    "Fields parameter bad format: close bracket without "
                    "a corresponding open bracket in advance."
                )
            last_field = field[:-1]
            if last_field:
                cereal_fields.normal_fields.append(last_field)
            return cereal_fields
        elif field:
            # skip empty fields Ex: ',,'
            cereal_fields.normal_fields.append(field)

        try:
            next_field = next(field_iter)
        except StopIteration:
            # the end of the list has been reached
            if close_bracket:
                raise CerealException(
                    "Open bracket not closed in fields parameter."
                )
            else:
                return cereal_fields
        field = next_field


def parse_fields_to_nested_tree(flat_field_string):
    '''Produces the tree of serializer fields and options for the
    flat_field_string.

    :param flat_field_string: string used to control the serializer used.
    Extracted from the url parameter, 'fields'.
    Example:
    'id,name,label(name),comments(text,attachments(url),id)'

    :return: CerealFields object

    '''

    # Closing brackets are treated as separate list items
    # to reduce complexity (by not having to consider what to do with
    # several braces on a single pass (which have to bubble up the
    # recursive stack. Low impact on performance - causes O(#fields) more
    # iterations in the while(True) loop of the recursive function.
    flat_fields = flat_field_string.replace(')', ',)')
    flat_fields = flat_fields.split(',')
    return CerealMixin.parse_fields_to_nested_tree_rec(iter(flat_fields))


class CerealMixin(object):
    '''Inspired by:
    http://www.pivotaltracker.com/help/api#Response_Controlling_Parameters
    '''

    # If the ':default' option is not included in the
    # field list of a serializer, the serializer's default list of fields
    # will be cleared and replaced by the list of fields defined by the
    # response-controlling parameters.
    REQUIRE_DEFAULT_OPTION = True

    def get_default_field_names(self, declared_fields, model_info):
        return set(
            super(CerealMixin, self
                  ).get_default_field_names(declared_fields, model_info)
        )

    def get_field_names(self, declared_fields, info):
        '''Other options can be applied here before the response-controlling
        parameters start changing serializers (options can also be
        used elsewhere).
        :return:
        '''

        cereal_fields = getattr(self, 'cereal_fields', None)
        is_circular = getattr(getattr(self, 'Meta', None), 'circular', False)
        if is_circular and not cereal_fields:
            raise CerealException(
                "'fields' query parameter must be defined in this "
                "request due to circular serializers."
            )

        if not cereal_fields or (self.REQUIRE_DEFAULT_OPTION and
                              'default' in cereal_fields.options):
            return super(CerealMixin, self).get_field_names(
                declared_fields, info
            )

        has_cereal_fields = len(cereal_fields.normal_fields) > 0 or \
                            len(cereal_fields.nested_fields) > 0
        if is_circular and not has_cereal_fields:
            raise CerealException(
                "Circular Serializer for model {0} had no fields defined in "
                "the request."
                .format(str(self.Meta.model))
            )

        # Remove all the fields not defined in normal_fields.
        # This allows custom fields defined in the Serializer class to be used
        # by the response-controlling parameters, since only basic model fields
        # can be manually added by the information in the parameters.
        # (Ex: MethodFields, etc.)
        original_fields = getattr(self.Meta, 'fields', [])
        original_exclude = getattr(self.Meta, 'exclude', [])
        default_fields = self.get_default_field_names(declared_fields, info)
        for field_name in cereal_fields.normal_fields:
            if field_name not in original_fields and \
                field_name not in default_fields:
                raise CerealException(
                    "Field {0} isn't defined in serializer."
                    .format(field_name)
                )

        new_fields = cereal_fields.normal_fields + \
                     list(cereal_fields.nested_fields.keys())
        setattr(self.Meta, 'exclude', [])
        setattr(self.Meta, 'fields', new_fields)

        # Make a new list of declared fields so that we don't get the error:
        # "The field '{field_name}' was declared on serializer
        # {serializer_class}, but has not been included in the
        # 'fields' option."
        new_declared_fields = {field_name: declared_fields[field_name]
                               for field_name in declared_fields
                               if field_name in new_fields}

        field_names = super(CerealMixin, self).get_field_names(
            new_declared_fields, info
        )
        # Set the fields back to how they are explicitly defined in the
        # serializer class Meta.
        setattr(self.Meta, 'exclude', original_exclude)
        setattr(self.Meta, 'fields', original_fields)
        return field_names

    def get_fields(self, *args, **kwargs):
        '''The get_fields method selects from the fields defined in its
        _declared_fields attribute. Permanently add the mixin to the nested
        serializers who were selected on this request's use of the serializer.
        '''

        # Meta doesn't exist on SerializerMethodField serializers
        meta = getattr(self, 'Meta', None)

        is_circular = getattr(meta, 'circular', False)
        depth = getattr(meta, 'depth', None)
        if not self.cereal_fields and is_circular and depth != 0:
            # protect against circular serializers recursing infinitely
            return {}

        if not self.cereal_fields or (self.REQUIRE_DEFAULT_OPTION and
                                   'default' in self.cereal_fields.options):
            return super(CerealMixin, self).get_fields(
                *args, **kwargs
            )

        nested_cereal_fields = self.cereal_fields.nested_fields
        # Save the original fields in original fields and build a new
        # self._declared_fields using the 'normal' declared fields that should
        # stay and the 'nested' declared fields that must be initialized
        # inheriting the CerealMixin
        original_fields = self._declared_fields
        self._declared_fields = {field_name: original_fields[field_name]
                                 for field_name in original_fields
                                 if field_name in
                                 self.cereal_fields.normal_fields}
        for nested_field_key in nested_cereal_fields:
            if nested_field_key not in original_fields:
                self._declared_fields = original_fields
                raise CerealException(
                        "Field {0} isn't defined in serializer."
                        .format(nested_field_key)
                    )
            original_field = original_fields[nested_field_key]
            if getattr(original_field, 'many', False):
                # deal with ListSerializers - they wrap the nested child
                # serializer that we want to use
                list_field = original_field
                original_field = list_field.child
                many = True
            else:
                many = False
            field_class = original_field.__class__
            if not issubclass(field_class, CerealMixin):
                new_field_class = type(
                    'CerealTemp' + field_class.__name__,
                    (CerealMixin, field_class),
                    {}
                )
            else:
                # This is required for circular nesting. We need different
                # temporary classes to represent the same class when circular
                # nesting occurs so the class.Meta can be different.
                new_field_class = type(
                    'CerealTemp' + field_class.__name__,
                    (field_class,),
                    {}
                )

            # Create a new object with the new list of base classes (including
            # CerealMixin).
            # The source of the field mustn't be redundant.
            source = getattr(meta, 'source', None)
            if source == nested_field_key:
                source = None
            new_field = new_field_class(
                source=source,
                cereal_fields=nested_cereal_fields[nested_field_key],
                method_name=getattr(original_field, 'method_name', None),
                many=many
            )
            self._declared_fields[nested_field_key] = new_field

        fields = super(CerealMixin, self).get_fields(
            *args, **kwargs
        )
        # Reset the fields of the serializer, or they will be picked up in
        # error on future requests which don't specify fields.
        if self.cereal_fields:
            self._declared_fields = original_fields

        return fields

    def __init__(self, *args, **kwargs):
        '''Assigns a serializer's fields and options recursively (because
        serializer fields can be nested with other serializer objects).

        :param cereal_fields: CerealFields object

        '''

        has_request = kwargs.get('context') and kwargs['context'].get('request')

        if has_request:
            # the base-level serializer
            fields_parameter = kwargs['context']['request'].query_params.get(
                'fields', None
            )

            if fields_parameter:
                # The cereal_fields parameter is passed down recursively, so it
                # must be computed once by the top-level serializer.
                cereal_fields = \
                    self.parse_fields_to_nested_tree(fields_parameter)

                # We don't want weird behavior resulting from serializers being
                # prevented from nesting further because of this Meta depth
                # attribute.
                if getattr(self, 'Meta', None):
                    self.Meta.depth = 10
            else:
                # Allow for requests without fields defined
                cereal_fields = None
        else:
            # We don't want weird behavior resulting from serializers being
            # prevented from nesting further because of this Meta depth
            # attribute.
            if getattr(self, 'Meta', None):
                self.Meta.depth = 10

            cereal_fields = kwargs.pop(
                'cereal_fields', getattr(self, 'cereal_fields', None)
            )

        self.cereal_fields = cereal_fields

        # This would ideally be in the MethodSerializerMixin class, but DRF
        # Field doesn't allow for unused kwargs, and serializers with the
        # CerealMixin don't always inherit the MethodSerializerMixin mixin.
        # The __bases__[0] is necessary because a MethodSerializerMixin will be
        # hiding behind a temporary class created by this serializer's parent.
        bases = self.__class__.__bases__
        parent_bases = self.__class__.__bases__[0].__bases__
        if MethodSerializerMixin not in bases and \
                        MethodSerializerMixin not in parent_bases:
            kwargs.pop('method_name', None)

        super(CerealMixin, self).__init__(
            *args, **kwargs
        )

        # Don't allow requests without fields to hit endpoints with
        # circular serializers
        is_circular = getattr(getattr(self, 'Meta', None), 'circular', False)
        if is_circular and has_request and not fields_parameter:
            raise CerealException(
                "'fields' query parameter must be defined in this "
                "request due to circular serializers."
            )

    def save_object(self, obj, **kwargs):
        raise CerealException(
            "Saving hasn't been tested with the CerealMixin. "
            "Use at your own peril."
        )

    def save(self, *args, **kwargs):
        raise CerealException(
            "Saving hasn't been tested with the CerealMixin. "
            "Use at your own peril."
        )
