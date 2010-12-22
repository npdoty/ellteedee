#!/usr/bin/env python
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import users
import os
from google.appengine.ext.webapp import template
from google.appengine.ext import db
import logging
import math
import random
import re

class Message(db.Model):
	text = db.TextProperty()
	views = db.IntegerProperty()
	created = db.DateTimeProperty(auto_now_add=True)
	blurred = db.IntegerProperty()
	blur_type = db.StringProperty(default='random') # ['start', 'random', ] 
	home_page = db.BooleanProperty(default=False)
	has_characters = db.BooleanProperty(default=True)	# still has non-blurred letters
	
	blur_char = '_' # '_' is considered a blurred character
	white_list = ['\n', blur_char]
	
	def toHtml(self):
		def enclose_blurred(match):
			return '</span><span class="blurred">' + match.group(0) + '</span><span class="original">'
		html = re.sub('_+', enclose_blurred, self.text)
		html = '<span class="original">' + html + '</span>'
		
		return html.replace('\n', '<br/>')
	
	def blur(self, number, should_put):
		# currently ignoring the number parameter, but ideally should blur that number of characters
		if not self.blurred:
			self.blurred = 0	# can't just set this to 0, need to count the number of white list characters that the message starts with
		
		if self.white_list_count() == len(self.text):	# is this message already completely blurred?
			self.has_characters = False
			self.home_page = False
			self.put()
			return
		
		if self.blur_type and self.blur_type == 'random':
			index = random.randint(0,len(self.text)-1)
			replaced = False
			while not replaced:
				replaced = self.blur_character(index)
				index = index + 1
				if index >= len(self.text):
					index = 0
		else:
		    self.blur_character(self.blurred)
			
		self.blurred = self.blurred + 1
		
		if self.white_list_count() == len(self.text):
			self.has_characters = False
			self.home_page = False
		
		if should_put:
			self.put()
	
	def white_list_count(self):
		count = 0
		for c in self.white_list:
			count += self.text.count(c)
		return count
	
	def blur_character(self, index):
		if self.text[index] not in self.white_list:
			self.text = self.text[:index] + self.blur_char + self.text[index+1:] # strings are immutable, who knew?
			logging.info('Blurred character %d', index)
			return True
		else:
			return False
	
	def percent_blurred(self):
		return self.blurred * 1.0 / len(self.text)	# doesn't account for messages that start with blurred characters

class MainHandler(webapp.RequestHandler):
	def get(self, key=None):
		# get the appropriate message
		if key:
			try:
				m_key = db.Key.from_path('Message', int(key)) # maybe it's a numeric key?
			except ValueError:
				m_key = db.Key.from_path('Message', key) # or maybe it's a string key
			message = Message.get(m_key)
		elif Message.all().filter('home_page =', True).count(limit=1):
			message = Message.all().order('created').filter('home_page =', True).get()
		elif Message.all().filter('has_characters =', True).count(limit=1):
			message = Message.all().order('created').filter('has_characters =', True).get()
			message.home_page = True
		else:
			message = None
		
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
