from rest_cereal import (
    CerealException, CerealFields, parse_fields_to_nested_tree
)
from rest_cereal.serializers import MethodSerializerMixin


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
