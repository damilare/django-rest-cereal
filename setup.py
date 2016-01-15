from setuptools import setup

setup(
    name='cereal',
    version='1.0',
    description='cereal',
    packages=['cereal'],
    install_requires=[
      'django',
      'djangorestframework==3.2.4'
    ]
)

