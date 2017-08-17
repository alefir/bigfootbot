import pydle
import subprocess
import sys
import exceptions
from bs4 import BeautifulSoup
import urllib
import ban
import admin
import tell
import chan

# Set our name and version.
name = "Python3Bot"
version = "0.1-dev"
cmd = "!"

def error(error, fatal = False):
	""" Prints error to stdout, flusing the output, and exiting if it's a fatal error. """
	if not fatal:
		print("ERROR: {}".format(error), flush = True)
	else:
		print("FATAL ERROR: {}".format(error), flush = True)
		sys.exit(1)

def warning(warning):
	""" Prints warning to stdout, flusing the output. """
	print("WARNING: {}".format(warning), flush = True)

def debug(debug):
	""" Prints debug to stdout, flushing the output. """
	print("DEBUG: {}".format(debug), flush = True)

def is_yes(s):
	""" Returns whether the string means True or False """
	s = s.lower()
	
	if s == "true" or s == "yes" or s == "y":
		return True
	else:
		return False

class Bot(pydle.Client):
	""" The main bot class. Handles events, and the raw IRC connection."""

	def quit(self, message=None):
		""" Quits network. """
		# I'm gonna implement something here.
		# But for now just return the super call.
		debug("Quitting. Reason: {}".format(message))
		# Save and clean up handlers
		self.Bans.save_bans()
		self.Admins.save_admins()
		self.Tells.save_tells()
		self.Channels.save_chans()
		return super().quit(message)

	def on_connect(self):
		""" Join configured channels on connect """
		
		# Call the superclass.
		super().on_connect()
		# Set modes on self
		self.rawmsg("MODE", self.config.nick, self.config.usermode)
		# Initialize handlers
		self.Bans = ban.BanManager("bans.dat", self)
		self.Admins = admin.AdminManager("admins.dat", self)
		self.Tells = tell.TellManager("tells.dat", self)
		self.Channels = chan.ChannelManager("channels.dat", self)

	def is_admin(self, target, account):
		for each in self.Admins.admins:
			if target == each.target and account == each.nick:
				return True
		if account == self.config.owner:
			return True
		# This is reached when no admin privliges we're detected.
		return False



	@pydle.coroutine
	def __handle_internal(self, target, source, message):
		""" Handles commands for internal plugin(s). """
		message = message.strip(' ')

		# Test for links
		link = message.find("http://")
		prot_len = 7
		found = False
		link_end = len(message)
		link_url = -1
		if link == -1:
			link = message.find("https://")
			prot_len = 8

		if link != -1:
			if link != 0:
				if message[link-1] == ' ':
					found = True
			else:
				found = True
			if found:
				for i in range(link, len(message)):
					if message[i] == '/' and link_url == -1 and i > prot_len+1:
						link_url = i
					elif message[i] == ' ':
						link_end = i
						if link_url == -1:
							link_url = i
						break
				if link_url == -1:
					link_url = link_end
				try:
					soup = BeautifulSoup(urllib.request.urlopen(message[link:link_end]), "html5lib")
					self.__respond(target, source, " [ {} ]".format(soup.title.string, message[link+prot_len:link_url]))
				except:
					self.__respond(target, source, "{}".format(sys.exec_info()[0]))

		if message == cmd+"version":
			# Handler for !version.
			self.notice(target, "{}: {}, Version: {}. {}".format(source, name, version, target))

		if message == cmd+"quit":
			# Handler for !quit.
			# Check for admin privs.
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				self.quit("Recieved a quit command.")
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message == cmd+"wiki":
			self.__respond(target, source, "Alefir I command you to add the wikipedia lib")
		
		if message.startswith(cmd+"remove"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=2)
				pmsg = ""
				if len(args) == 2:
					pmsg = "Removed by {}".format(source)
				elif len(args) == 3 and args[2] != "":
					pmsg = "Removed by {} (".format(source) + args[2] + ")"
				else:
					self.notice(target, "{}: Invalid command invocation.".format(source))
					return
				
				if args[1] == self.config.nick:
					self.notice(target, "{}: I refuse to remove myself.".format(source))
					return
				
				self.rawmsg("REMOVE", target, args[1], pmsg)
				self.notice(target, "{}: Removed {}.".format(source, args[1]))
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message.startswith(cmd+"ban"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=3)
				remove = False
				reason = ""
				#self.message(target, "Ban command invoked")
				if len(args) == 2:
					#self.message(target, "Banning without removing")
					ban_number = self.Bans.add_ban(target, args[1])
					self.__respond(target, source, "{}: Ban added on {} (Channel: {}) as ban number {}.".format(source, args[1], target, ban_number))
				elif len(args) > 2:
					#self.message(target, "Banning with 2nd argument")
					if len(args) == 3:
						reason = "Banned by {}".format(source)
					elif len(args) == 4:
						reason = "Banned by {} ({})".format(source, args[3])
					else:
						self.__respond(target, source, "{}: Invalid command invocation.".format(source))
						return

					#self.message(target, "Remove reason {}".format(reason))
					ban_number = self.Bans.add_ban(target, args[1])
					self.rawmsg("REMOVE", target, args[2], reason)
					self.__respond(target, source, "{}: Ban added on {} (Channel: {}) as ban number {}.".format(source, args[1], target, ban_number))
				else:
					self.__respond(target, source, "{}: Invalid command invocation.".format(source))
					return
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message.startswith(cmd+"rmban"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					try:
						num = int(float(args[1]))
					except ValueError:
						self.__respond(target, source, "{}: Invalid number.".format(source))
						return
					status = self.Bans.remove_ban(num)
					if status != 0:
						self.__respond(target, source, "{}: Ban number out of range.".format(source))
					else:
						self.__respond(target, source, "{}: Ban lifted.".format(source))
				else:
					self.__respond(target, source, "{}: Invalid command invocation.".format(source))
					return
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

		if message == cmd+"lsban":
			self.notice(source, "Bot ban list:")
			for i in range(0, len(self.Bans.bans)):
				self.notice(source, "{}. Channel: {} | Hostmask: {}".format(i, self.Bans.bans[i].target, self.Bans.bans[i].mask))
			self.notice(source, "End of bot ban list.")

		if message.startswith(cmd+"quiet"): # syntax !quiet <hostmask>
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=2)
				if len(args) == 2:
					self.rawmsg("MODE", target, '+q', args[1])
				else:
					
					return
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message.startswith(cmd+"unquiet"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					self.rawmsg("MODE", target, '-q', args[1])
				else:
					self.__respond(target, source, "{}: Invalid command invocation.".format(source))
					return
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

		if message.startswith(cmd+"op"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					self.rawmsg("MODE", target, '+o', args[1])
				else:
					self.rawmsg("MODE", target, '+o', source)
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message.startswith(cmd+"deop"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					if args[1] == self.config.nick:
						self.__respond(target, source, "{}: I refuse to deop myself.".format(source))
						return
					
					self.rawmsg("MODE", target, '-o', args[1])
				else:
					self.rawmsg("MODE", target, '-o', source)
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

		if message.startswith(cmd+"voice"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					self.rawmsg("MODE", target, '+v', args[1])
				else:
					self.rawmsg("MODE", target, '+v', source)
					return
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message.startswith(cmd+"devoice"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					self.rawmsg("MODE", target, '-v', args[1])
				else:
					self.rawmsg("MODE", target, '-v', source)
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message.startswith(cmd+"exempt"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					self.rawmsg("MODE", target, '+e', args[1])
				else:
					self.rawmsg("MODE", target, '+e', "*!*@" + host['hostname'])
					return
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))
		
		if message.startswith(cmd+"unexempt"):
			host = yield self.whois(source)
			if self.is_admin(target, host['account']):
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					self.rawmsg("MODE", target, '-e', args[1])
				else:
					self.rawmsg("MODE", target, '-e', "*!*@" + host['hostname'])
			else:
				self.__respond(target, source, "{}: You need admin privs to execute that command.".format(source))

		if message.startswith(cmd+"admin"):
			host = yield self.whois(source)
			if host['account'] == self.config.owner:
				args = message.split(' ', maxsplit=1)
				adminnum = self.Admins.add_admin(target, args[1])
				self.__respond(target, source, "{}: Admin \"{}\" added on channel {} as number {}.".format(source, args[1], target, adminnum))
			else:
				self.__respond(target, source, "{}: You need to be the bot owner to run that command.".format(source))

		if message.startswith(cmd+"rmadmin"):
			host = yield self.whois(source)
			if host['account'] == self.config.owner:
				args = message.split(' ', maxsplit=1)
				if len(args) == 2:
					try:
						num = int(float(args[1]))
					except ValueError:
						self.__respond(target, source, "{}: Invalid number.".format(source))
						return
					retval = self.Admins.remove_admin(num)
					if retval == 0:
						self.__respond(target, source, "{}: Admin removed.".format(source))
					else:
						self.__respond(target, source, "{}: Admin number out of range.".format(source))
				else:
					self.__respond(target, source, "{}: Invalid command invocation".format(source))
			else:
				self.__respond(target, source, "{}: You need to be the bot owner to run that command.".format(source))

		if message == cmd+"lsadmin":
			self.notice(source, "Bot admin list:")
			for i in range(0, len(self.Admins.admins)):
				self.notice(source, "{}. Channel: {} | Account: {}".format(i, self.Admins.admins[i].target, self.Admins.admins[i].nick))
			self.notice(source, "End of bot admin list.")

		if message.startswith(cmd+"tell"):
			args = message.split(' ', maxsplit=2)
			if len(args) == 3:
				tell_num = self.Tells.add_tell(target, args[1], source, args[2])
				self.__respond(target, source, "{}: I'll pass that on when {} is around. The tell ID is {}.".format(source, args[1], tell_num))
			else:
				self.__respond(target, source, "{}: Invalid command invocation.".format(source))
			return

		if message == cmd+"lstell":
			self.notice(source, "Bot tell list:")
			for i in range(0, len(self.Tells.tells)):
				if self.Tells.tells[i].harbinger == source:
					self.notice(source, "{}. Channel: {} | To: {} | From: {} | Message: {}".format(i, self.Tells.tells[i].target, self.Tells.tells[i].nick, self.Tells.tells[i].harbinger, self.Tells.tells[i].message))
				else:
					self.notice(source, "{}. Channel: {} | To: {} | From: {}".format(i, self.Tells.tells[i].target, self.Tells.tells[i].nick, self.Tells.tells[i].harbinger))
			self.notice(source, "End of bot tell list.")

		if message.startswith(cmd+"rmtell"):
			args = message.split(' ', maxsplit=1)
			if len(args) == 2:
				try:
					num = int(float(args[1]))
				except BaseException as e:
					self.__respond(target, source, "{}: Invalid number.".format(source))
					return
				# Num is a number
				if num > len(self.Tells.tells)-1:
					self.__respond(target, source, "{}: Number out of range.".format(source))
					return
				else:
					tell = self.Tells.tells[num]
					if source == tell.harbinger:
						self.Tells.remove_tell(num, activate=False)
						self.__respond(target, source, "{}: Tell removed.".format(source))
						return
					else: # The person requesting to remove the tell didn't make it in the first place
						host = yield self.whois(source)
						if self.is_admin(target, host['account']):
							self.Tells.remove_tell(num, activate=False)
							self.__respond(target, source, "{}: Tell forcibly removed.".format(source))
							return
						else:
							self.__respond(target, source, "{}: You are not authorized to remove someone else's tell.".format(source))
							return
			else:
				self.__respond(target, source, "{}: Invalid command invocation.".format(source))

		if message.startswith(cmd+"join"):
			host = yield self.whois(source)
			if self.config.owner == host['account']:
				args = message.split(' ')
				if len(args) == 2:
					self.Channels.join_chan(args[1])
					self.__respond(target, source, "{}: Channel joined.".format(source))
				else:
					self.__respond(target, source, "{}: Invalid command invocation.".format(source))
			else:
				self.__respond(target, source, "{}: You need to be the bot owner to execute this command.".format(source))

		if message.startswith(cmd+"part"):
			host = yield self.whois(source)
			args = message.split(' ')
			if len(args) == 2:
				try:
					num = int(float(args[1]))
				except ValueError:
					self.__respond(target, source, "{}: Invalid number.".format(source))
					return
				if num > len(self.Channels.channels)-1:
					self.__respond(target, source, "{}: Number out of range.".format(source))
					return
				try:
					if self.is_admin(self.Channels.channels[num].name, host['account']):
						self.Channels.part_chan(num, source)
						self.__respond(target, source, "{}: Channel removed.".format(source))
				except BaseException as e:
					print(str(e), type(e))
			else:
				self.__respond(target, source, "{}: Invalid command invocation.".format(source))

		if message == cmd+"lschans":
			self.notice(source, "Bot channel list:")
			i = 0
			for each in self.Channels.channels:
				self.notice(source, "{}. {}".format(i, each.name))
				i += 1
			self.notice(source, "End of bot channel list.")

		if message == cmd+"help":
			# Please leave this here.
			helptext = "" \
			"Command list:\n" \
			" <name>   | <arguments>                       | <description>\n" \
			"!version  |                                   | Displays the version information of the bot.\n" \
			"!quit     |                                   | Kills the bot (Requires admin privs)\n" \
			"!next     |                                   | NEXT!\n" \
			"!remove   | <nick> [reason]                   | Removes <nick> from channel with optional [reason].\n" \
			"!ban      | <mask> [<nick> [reason]]          | Bans the mask <mask> and can remove <nick> with [reason] if <nick> specified.\n" \
			"!rmban    | <number>                          | Lifts ban specified by <number>.\n" \
			"!lsban    |                                   | Lists the banlist for the bot. Can be quite a flood at times.\n" \
			"!unban    | <mask>                            | Unbans the specified <mask>.\n" \
			"!quiet    | <mask>                            | Sets quiet on <mask>.\n" \
			"!unquiet  | <mask>                            | Removes quiet on <mask>.\n" \
			"!op       | [nick]                            | Ops [nick]. If not specified, ops you.\n" \
			"!deop     | [nick]                            | Deops [nick]. If not specified, deops you.\n" \
			"!voice    | [nick]                            | Gives voice to [nick]. If not specified, voices you.\n" \
			"!devoice  | [nick]                            | Takes voice from [nick. If not specified, devoices you.\n" \
			"!exempt   | [hostmask]                        | Sets ban exempt status on [hostmask]. If not specified, uses your hostmask.\n" \
			"!unexempt | [hostmask]                        | Removes ban exempt status from [hostmask]. If not specified, uses your hostmask.\n" \
			"!admin    | <account>                         | Adds <account> as an admin on the channel. (Requires owner privs)\n" \
			"!rmadmin  | <number>                          | Removes admin specified by <number>. (Requires owner privs)\n" \
			"!lsadmin  |                                   | Lists all admins.\n" \
			"!tell     | <nick> <message>                  | Tells me to pass <message> onto <nick> next time they type a message.\n" \
			"!rmtell   | <number>                          | Removes a number by tell ID, an admin can remove the tells of someone else.\n" \
			"!lstell   |                                   | Lists all tells, the message is displayed only on your tells.\n" \
			"!help     |                                   | Sends this help message.\n" \
			"End of help."

			self.notice(source, helptext)

		if len(self.Tells.tells) > 0:
			for i in range(len(self.Tells.tells)):
				if self.Tells.tells[i].nick == source:
					self.Tells.remove_tell(i)

	def __respond(self, target, source, message):
		""" Responds to a command. """
		if self.is_channel(target):
			self.notice(target, message)
		else:
			self.notice(source, message)

	def on_message(self, target, source, message):
		""" Debugging function to print messages to stdout """
		# Call the superclass.
		super().on_message(target, source, message)

		# Handle internal command(s).
		self.__handle_internal(target, source, message)

		# Trigger plugins.
		for each in self.plugin.plugin_commands:
			value = each.split(":")
			if message.startswith("!{}".format(value[0])):
				module_obj = self.plugin.plugins[value[2]]
				function_obj = getattr(module_obj, value[1])
				warning("Plugin returned: {}".format(function_obj()))

		# Print message.
		debug("Target: {}, Source: {}, Message: {}".format(target, source, message))

	def on_kick(self, channel, target, by, reason=None):
		""" Called when a person is kicked from the channel """
		# Call the superclass.
		super().on_kick(channel, target, by, reason)

		# Rejoin the channel
		if target == self.config.nick:
			self.join(channel)

	def on_part(self, channel, user, message=None):
		""" Called when a person parts from the channel """
		# Call the superclass.
		super().on_kick(channel, user, message)

		# Rejoin the channel if on list
		on_list = False

		for each in self.Channels.channels:
			if each.name == channel:
				on_list = True

		if user == self.config.nick and on_list:
			self.join(channel)

	def on_raw(self, data):
		""" Debugging function to print all raw data to stdout """
		# Call the superclass.
		super().on_raw(data)

		# Convert data to a string.
		data = str(data)

		# Strip newlines from the data.
		data = data.strip('\n')

		# And output it.
		if data.find("PING") == -1 and data.find("PRIVMSG") == -1:
			debug(data)

	def on_unknown(self, message):
		""" Unknown command. """
		warning("Recieved an unknown command: {}".format(message))

	def on_data_error(self, exception):
		""" Handle's socket errors. """
		error("Caught a socket exception. {} {}".format(type(exception), str(exception)), fatal = True)
