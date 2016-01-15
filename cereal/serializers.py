import collections


class LazySerializer(object):
    '''
    This serializer is used for circular referencing of serializers.

    Before, if you wanted to access items in a circular fashion with serializers
    (ie. to do a.b OR b.a OR a.b.a), you would do something like:

    class SerializerA_from_B_point_of_view(...):
        ...
    class SerializerB_from_A_point_of_view(...):
        ...
    class A:
        b = B_from_A_point_of_view(...)
    class B:
        a = A_from_B_point_of_view(...)

    But for Serializers using response-controlling parameters (CerealMixin),
    it's more convenient for there to exist only two serializers for this case.
    This is because if you want to change one model or one model's serializers,
    you have to change each serializer. This isn't allowed in DRF because of
    infinite circular nesting:

    class A:
        b = B()
    class B:
        a = A()

    print A() -> prints infinitely (would also produce infinite serialized data)

    The CerealMixin solves this infinite serializing problem by requiring you
    to specify exacly which fields to include in the request. You can't specify
    infinitely nested fields in a request (you can specify a lot of nesting,
    but we can put limits on the requests).

    IMPORTANT
    * You have to call the convert_serializers method at the bottom of your
    serializers file which pieces together all the lazy circular referencing.
    '''

    class DoesNotExistException(BaseException):
        pass

    def __init__(self, serializer_class, *args, **kwargs):
        self.serializer_class = serializer_class
        self.args = args
        self.kwargs = kwargs
        return None

    @staticmethod
    def convert_serializers(global_namespace, serializer_class_list):
        '''
        Call this method at the end of your serializer file with the global
        namespace and the classes that have LazySerializers in them. Ex:

        LazySerializer.convert_serializers(
            globals(), [LJobDaySerializer, LJobSerializer]
        )

        This converts the lazyserializer's class to the field of each
        LazySerializer found within the inherited classes of
        inherited_serializer_class_list.
        :param global_namespace:
        :param serializer_class_list:
        :return:
        '''

        circular_fields = \
            {serializer_class: {} for serializer_class in serializer_class_list}

        # First, remove the field from each class' 'field' attribute
        # so that when circular fields are instantiated in other serializers,
        # they don't cause errors, 'Can't instantiate LazySerializer field'.
        for serializer_class in serializer_class_list:
            for field_name in serializer_class.Meta.fields:
                field = getattr(serializer_class, field_name, None)
                if isinstance(field, LazySerializer):
                    field = getattr(serializer_class, field_name)
                    circular_fields[serializer_class][field_name] = field
            # remove the LazySerializer fields
            serializer_class.Meta.fields = \
                tuple(fld for fld in serializer_class.Meta.fields
                      if fld not in circular_fields[serializer_class].keys())

        # Next, turn the LazyFields into real fields and add the field back to
        # the class' 'field' attribute (because the class no longer has
        # error-causing LazySerializer fields).
        for serializer_class, fields in circular_fields.iteritems():
            _declared_fields = getattr(serializer_class, '_declared_fields', {})
            for field_name, field in fields.iteritems():
                field_class = global_namespace.get(
                    field.serializer_class, None
                )
                if field_class is None:
                    # You could implement handling namespaced paths here, but
                    # it's painful with little reward.
                    raise LazySerializer.DoesNotExistException(
                        '{0} does not exist in global_namespace, so the '
                        'field could not be instantiated. Use the actual class '
                        'name and not a namespaced path to it (ex: Foo, not '
                        'bar.Foo)'
                        .format(field.serializer_class)
                    )
                _declared_fields[field_name] = field_class(*field.args,
                                                           **field.kwargs)
                field_args = field.args
                field_kwargs = field.kwargs
                field = field_class(*field_args, **field_kwargs)
                field.args = field_args
                field.kwargs = field_kwargs
                setattr(serializer_class, field_name, field)

            # put the LazerSerializer fields back
            serializer_class.Meta.fields = \
                tuple(list(serializer_class.Meta.fields) + fields.keys())


class MethodSerializerMixin(object):
    """
    Serializers can inherit this Serializer if you want to define the single
    object or iterable of the object to be serialized based on the context
    (often using the request or view).

    This is similar to DRF's SerializerMethodField, but allows the get_*
    method to have access to the context, and can also act as a ModelSerializer
    (important for CerealMixin) instead of just returning data.

    Example usages:
    class X(Model):
        ...
    class Y(Model):
        ...
    class Z(Model):
        x = ForeignKey(X)
        ys = ManyToMany(Y)

    class XMethodSerializer(MethodSerializerMixin, ModelSerializer):
        ...
    class YMethodSerializer(MethodSerializerMixin, ModelSerializer):
        ...

    class ZSerializer(ModelSerializer):
        x = XMethodSerializer('get_x')
        ys = YMethodSerializer('get_y')

        def get_x(self, obj):
            return obj.a + self.context['request'].data['b'] +
                self.context['view'].c

        def get_y(self, obj):
            return obj.y_set.filter(
                foo=self.context['request'].data['foo']
            )

    """

    def __init__(self, *args, **kwargs):
        self.method_name = kwargs.pop('method_name', None)
        if self.method_name is None:
            self.method_name = 'get_' + self.Meta.model.__name__.lower()
        super(MethodSerializerMixin, self).__init__(*args, **kwargs)

    def get_attribute(self, instance, *args, **kwargs):
        function_ = getattr(self.parent, self.method_name)
        value = function_(instance)
        # We don't want the setattr call below to write to db.
        # This can happen if there is a RelatedField at getattr(obj, field_name)
        # so make sure there are no collisions of fields to write to
        # on the model.
        original_source_attr = self.source_attrs[0]
        while getattr(instance, self.source_attrs[0], None) is not None:
            self.source_attrs[0] += '_temp'

        setattr(instance, self.source_attrs[0], value)
        result = super(MethodSerializerMixin, self).get_attribute(
            instance, *args, **kwargs
        )

        self.source_attrs[0] = original_source_attr

        return result

    def to_representation(self, instance_s, *args, **kwargs):
        if isinstance(instance_s, collections.Iterable):
            return [super(MethodSerializerMixin, self).to_representation(item)
                    for item in instance_s]
        else:
            return super(MethodSerializerMixin, self).to_representation(
                instance_s
            )
