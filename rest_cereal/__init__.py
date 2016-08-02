import itertools

# This gross block of code is to allow you to use the
# parse_fields_to_nested_tree methods without installing rest_framework/django
import importlib
rest_framework_loader = importlib.find_loader("rest_framework")
django_installed = rest_framework_loader is not None
if django_installed:
    from rest_framework.exceptions import APIException
else:
    class APIException(Exception):
        pass


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
    cereal_fields = CerealFields()

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
    return parse_fields_to_nested_tree_rec(iter(flat_fields))

