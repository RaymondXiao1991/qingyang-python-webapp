#!/usr/bin/python
# coding: utf-8

__author__ = 'Raymond Xiao'

from transwarp.web import get, view
from models import User, Blog, Comment

@view('test_users.html')
@get('/')
def test_users():
	users = User.find_all()
	return dict(users=users)