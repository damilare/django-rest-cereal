
Inspired by:
http://www.pivotaltracker.com/help/api#Response_Controlling_Parameters


To test:
```
$ mkvirtualenv cereal
$ workon cereal
$ cd tests
$ pip install -r test_requirements.txt
$ python manage.py test
```

The cereal tests require a functioning django project because it is difficult to make unit tests (for this serializer functionality) without requests going through the whole django rest framework stack of views/serializers. The serializers and mixins are also very sensitive to changes in the ways django rest framework's views and serializer work. 'cerealtesting' is the testing django project - it will create a mysql database locally (using the testrunner).