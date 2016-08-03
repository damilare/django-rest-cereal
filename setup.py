from setuptools import setup

setup(
    name='djangorestcereal',
    version='1.0',
    description='Response-controlling parameters for Django Rest Framework.',
    packages=['rest_cereal'],
    install_requires=[
      'django==1.9.8',
      'djangorestframework==3.2.4'
    ]
)
