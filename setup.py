from setuptools import setup

setup(
    name='djangorestcereal',
    version='1.0',
    description='Response-controlling parameters for Django Rest Framework.',
    packages=['rest_cereal'],
    install_requires=[
      'django',
      'djangorestframework==3.2.4'
    ]
)

