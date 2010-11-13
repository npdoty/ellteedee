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
import logging
import math

class Message(db.Model):
	text = db.TextProperty()
	views = db.IntegerProperty()
	created = db.DateTimeProperty(auto_now_add=True)
	blurred = db.IntegerProperty()
	
	white_list = ['\n']
	
	def toHtml(self):
		html = '<span class="blurred">' + self.text[:self.blurred] + '</span>'
		html += '<span class="original">' + self.text[self.blurred:] + '</span>'
		
		return html.replace('\n', '<br/>')
	
	def blur(self, number, should_put):
		# currently ignoring the number parameter, but ideally should blur that number of characters
		if not self.blurred:
			self.blurred = 0
		
		if self.text[self.blurred] not in self.white_list:
			self.text = self.text[:self.blurred] + '?' + self.text[self.blurred+1:] # strings are immutable, who knew?
		self.blurred = self.blurred + 1
		
		if should_put:
			self.put()
	
	def percent_blurred(self):
		return self.blurred * 1.0 / len(self.text)

class MainHandler(webapp.RequestHandler):
	def get(self, key=None):
		# get the appropriate message
		if key:
			try:
				m_key = db.Key.from_path('Message', int(key)) # maybe it's a numeric key?
			except ValueError:
				m_key = db.Key.from_path('Message', key) # or maybe it's a string key
			message = Message.get(m_key)
		else:
			message = Message.all().order('-created').get()
		
		if message:
			if not message.views:
				message.views = 0
			message.views = message.views + 1
			
			# blur some of the message
			message.blur(1, True)

			template_values = {'message': message.toHtml(), 'views':message.views, 'key': str(message.key().id_or_name()), 'color': int(math.floor((1.0 - message.percent_blurred()) * 255))}

		else:
			if key:
				logging.warning('Tried to load key %s that does not exist.', key)
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
		key_name = self.request.get('key')
		if message:
			if key_name:
				new_message = Message(key_name=key_name)
			else:
				new_message = Message()
			new_message.text = message	# um, XSS
			new_message.put()
			self.redirect('/')
		else:
			self.redirect('/add')

def main():
	application = webapp.WSGIApplication([('/', MainHandler), ('/add', AddHandler), ('/k/(.+)', MainHandler)],
										 debug=True)
	util.run_wsgi_app(application)


if __name__ == '__main__':
	main()
