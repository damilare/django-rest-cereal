# Django Rest Cereal

Inspired by:
http://www.pivotaltracker.com/help/api#Response_Controlling_Parameters

## Overview
Django Rest Cereal allows requests to control the data returned in a response in Django Rest Framework.

Some reasons you may want to use Cereal:

* You want to give consumers of your API more flexibility.
* Your models have many fields and you want to reduce the number of views/serializers used to access the same model.
* You want to reuse serializers or do circular nesting of serializers.
* You want dynamic filtering (per-request) within a nested serializer (see MethodSerializer).

## Requirements
* Python (2.7, 3.2, 3.3, 3.4, 3.5)
* Django (1.7, 1.8, 1.9)
* Django Rest Framework (3.2.x)

## Example

### Compare with vanilla DRF
https://github.com/networklocum/django-rest-cereal/tree/master/examples

### Backwards compatibility
TODO

## To test:

If you don't have mysql installed, you need it:

```
$ apt-get install libmysqlclient-dev
$ apt-get install mysql-server
```

Make the virtualenv and install the requirements:

```
$ mkvirtualenv cereal
$ workon cereal
$ cd tests
$ pip install -r test_requirements.txt
$ python manage.py test
```

The cereal tests require a functioning django project because it is difficult to make unit tests (for this serializer functionality) without requests going through the whole django rest framework stack of views/serializers. The serializers and mixins are also very sensitive to changes in the ways django rest framework's views and serializer work. 'cerealtesting' is the testing django project - it will create a mysql database locally (using the testrunner).

The way the tests work right now is to install the cereal package, not by importing the files with a relative import. That means to change the serializers / mixins for tests, point the test_requirements to a different branch or work on the cereal files in your virtualenv (which are set up to be tracked by git).

## Improvements needed:
* Rate-limiting (easy to make requests that require a lot of processing)
* Field access limitations (this is what serializers are for in the first place, but it needs to be re-thought, as right now all fields on the model are accessible)
* Testing edge cases
* Schema option (allow consumers to ask what fields are accessible on any serializer)
