#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import users
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import db

class Message(db.Model):
	text = db.TextProperty()
	views = db.IntegerProperty()
	created = db.DateTimeProperty(auto_now_add=True)

class MainHandler(webapp.RequestHandler):
	def get(self):
		# get the appropriate message
		# (for now, just get the first message in the list)
		message = Message.all().order('-created').get()
		if message:
			if not message.views:
				message.views = 0
			message.views = message.views + 1
			message.put()

			template_values = {'message':message.text, 'views':message.views}

		else:
			self.redirect('/add')
			return
	
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))

class AddHandler(webapp.RequestHandler):
	def get(self):
		template_values = {}
		path = os.path.join(os.path.dirname(__file__), 'add.html')
		self.response.out.write(template.render(path, template_values))

	def post(self):
		message = self.request.get('message')
		if message:
			new_message = Message()
			new_message.text = message
			new_message.put()
			self.redirect('/')
		else:
			self.redirect('/add')

def main():
	application = webapp.WSGIApplication([('/', MainHandler), ('/add', AddHandler)],
										 debug=True)
	util.run_wsgi_app(application)


if __name__ == '__main__':
	main()
