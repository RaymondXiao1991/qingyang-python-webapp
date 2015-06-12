#!/usr/bin/python
# coding: utf-8

__author__ = 'Raymond Xiao'

# 创建一个Web App的启动文件wsgiapp.py，负责初始化数据库、初始化Web框架，然后加载urls.py，最后启动Web服务：

import logging; logging.basicConfig(level=logging.INFO)

import os, re, sys

#sys.path.append("www")
#sys.path.append("www/transwarp")
from transwarp import db
from transwarp.web import WSGIApplication, Jinja2TemplateEngine

from config import configs

# 初始化数据库：
db.create_engine(**configs.db)

# 创建一个WSGIApplication:
wsgi = WSGIApplication(os.path.dirname(os.path.abspath(__file__)))
# 初始化jinja2模板引擎:
template_engine = Jinja2TemplateEngine(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
wsgi.template_engine = template_engine

# 加载带有@get/@post的URL处理函数:
from transwarp import urls
wsgi.add_module(urls)

# 在9000端口上启动本地测试服务器:
if __name__ == '__main__':
	wsgi.run(9000)
