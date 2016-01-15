from rest_framework.exceptions import APIException


class CerealException(APIException):
    status_code = 400


class CerealMixin(object):
    '''
    Inspired by:
    http://www.pivotaltracker.com/help/api#Response_Controlling_Parameters
    '''

    # If the ':default' option is not included in the
    # field list of a serializer, the serializer's default list of fields
    # will be cleared and replaced by the list of fields defined by the
    # response-controlling parameters.
    REQUIRE_DEFAULT_OPTION = True

    class CerealFields:
        def __init__(self):
            # list of strings (of field names)
            # let the serializers deal with duplicate fields
            self.normal_fields = []
            # nested_fields is a dict of: 'nested_field_name': CerealFields
            self.nested_fields = {}
            # a set of string options for the serializer
            self.options = set()

        def __str__(self):
            return 'CerealFields(normal_fields: ' + str(self.normal_fields) + \
                   ', ' + 'nested_fields: ' + str(self.nested_fields) + ', ' + \
                   'options: ' + str(self.options) + ')'

    @staticmethod
    def parse_fields_to_nested_tree_rec(field_iter, field=None,
                                        close_bracket=False):
        '''
        Produces the return CerealFields struct (see above) for the field_iter
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
                field = field_iter.next()
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
                next_field = field_iter.next()
            except StopIteration:
                # the end of the list has been reached
                if close_bracket:
                    raise CerealException(
                        "Open bracket not closed in fields parameter."
                    )
                else:
                    return cereal_fields
            field = next_field

    @staticmethod
    def parse_fields_to_nested_tree(flat_field_string):
        '''
        Produces the tree of serializer fields and options for the
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
        return CerealMixin\
            .parse_fields_to_nested_tree_rec(iter(flat_fields))

    def get_default_field_names(self, declared_fields, model_info):
        return set(
            super(CerealMixin, self
                  ).get_default_field_names(declared_fields, model_info)
        )

    def get_field_names(self, declared_fields, info):
        '''
        Other options can be applied here before the response-controlling
        parameters start changing serializers (options can also be
        used elsewhere).
        :return:
        '''

        cereal_fields = getattr(self.Meta, 'cereal_fields', None)
        is_circular = getattr(self.Meta, 'circular', False)
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
                     cereal_fields.nested_fields.keys()
        setattr(self.Meta, 'exclude', [])
        setattr(self.Meta, 'fields', new_fields)

        # Make a new list of declared fields so that we don't get the error:
        # "The field '{field_name}' was declared on serializer
        # {serializer_class}, but has not been included in the
        # 'fields' option."
        new_declared_fields = {field_name: declared_fields[field_name]
                               for field_name in declared_fields
                               if field_name in new_fields}

        field_names = \
            super(CerealMixin, self).get_field_names(
                new_declared_fields, info
            )
        # Set the fields back to how they are explicitly defined in the
        # serializer class Meta.
        setattr(self.Meta, 'exclude', original_exclude)
        setattr(self.Meta, 'fields', original_fields)
        return field_names

    def get_fields(self, *args, **kwargs):
        # The get_fields method selects from the fields defined in its
        # _declared_fields attribute. Permanently add the mixin to the nested
        # serializers who were selected on this request's use of the serializer.

        meta_cereal_fields = getattr(self.Meta, 'cereal_fields', None)
        is_circular = getattr(self.Meta, 'circular', False)
        depth = getattr(self.Meta, 'depth', None)
        if not meta_cereal_fields and is_circular and \
                (depth is None or depth > 0):
            # protect against circular serializers recursing infinitely
            return {}
        elif not meta_cereal_fields or (self.REQUIRE_DEFAULT_OPTION and
                                   'default' in meta_cereal_fields.options):
            return super(CerealMixin, self).get_fields(
                *args, **kwargs
            )

        nested_cereal_fields = meta_cereal_fields.nested_fields
        # Save the original fields in original fields and build a new
        # self._declared_fields using the 'normal' declared fields that should
        # stay and the 'nested' declared fields that must be initialized
        # inheriting the CerealMixin
        original_fields = self._declared_fields
        self._declared_fields = {field_name: original_fields[field_name]
                                 for field_name in original_fields
                                 if field_name in
                                 meta_cereal_fields.normal_fields}
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
            source = getattr(original_field.Meta, 'source', None)
            if source == nested_field_key:
                source = None
            new_field = new_field_class(
                source=source,
                cereal_fields=nested_cereal_fields[nested_field_key],
                depth=depth + 1
            )
            if many:
                list_field.child = new_field
                new_field = list_field
            self._declared_fields[nested_field_key] = new_field

        fields = super(CerealMixin, self).get_fields(
            *args, **kwargs
        )
        # Erase the cereal_fields on meta and reset the fields of the
        # serializer, or they will be picked up in error on future requests
        # which don't specify fields.
        setattr(self.Meta, 'cereal_fields', None)
        setattr(self.Meta, 'depth', None)
        if meta_cereal_fields:
            self._declared_fields = original_fields


        # Ok, so this str(fields) is here because it seems to trigger the fields to have to actually do all the
        # setup in order right now, and without it we get an intermittent problem where the the dictionaries
        # get looped over in some non-deterministic way (Warning: working theory only!). This causes
        # repeated instance of the same serializer [ e.g. fields=job(locum(id),partapplication(locum(name)) ]
        # to return an empty output `{}` for the second instance.
        #
        # Our level of confidence around this fix is fairly low, but it's all we've got right now.

        str(fields)

        return fields

    def __init__(self, *args, **kwargs):
        '''

        Assigns a serializer's fields and options recursively (because
        serializer fields can be nested with other serializer objects).

        :param cereal_fields: CerealFields object

        '''

        depth = kwargs.pop('depth', None)
        has_request = kwargs.get('context') and kwargs['context'].get('request')
        if depth is None:
            depth = getattr(self.Meta, 'depth', None)
            # self.Meta.depth may be None and depth=None may be passed into
            # kwargs.
            if depth is None and has_request:
                depth = 0
            elif depth == 0:
                # this case happens in circular nesting, causes errors
                depth = 1
        setattr(self.Meta, 'depth', depth)

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
            else:
                # Allow for requests without fields defined
                cereal_fields = None
        elif depth is None:
            # If there's no request and no depth, it means the class is being
            # initially instantiated.

            # If there is no fields parameter, but there are LazySerializer
            # fields defined in the Serializer, those LazySerializer fields
            # have been converted into normal serializers and can
            # potentially be infinitely nested when returning data.
            # Django rest framework appears to prevent this kind of
            # infinite nesting. If this needs to be actioned, we would do it
            # here.
            cereal_fields = getattr(self.Meta, 'cereal_fields', None)
        else:
            cereal_fields = kwargs.pop(
                'cereal_fields',
                getattr(self.Meta, 'cereal_fields', None)
            )
            if cereal_fields is None:
                # This can happen with circular nested serializers that don't
                # use a nest in fields. This nested serializer is constructed
                # with a deepcopy on the parent serializer's
                # self._declared_fields, but this nested serializer will
                # not be used.
                self.Meta.fields = {}
        setattr(self.Meta, 'cereal_fields', cereal_fields)

        super(CerealMixin, self).__init__(
            *args, **kwargs
        )

        # Don't allow requests without fields to hit endpoints with
        # circular serializers
        is_circular = getattr(self.Meta, 'circular', False)
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