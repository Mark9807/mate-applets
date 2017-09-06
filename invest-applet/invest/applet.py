import os, time
from os.path import *
import mate_invest.defs

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import MatePanelApplet

GObject.threads_init()
from gettext import gettext as _

import mate_invest, mate_invest.about, mate_invest.chart, mate_invest.preferences
from mate_invest.quotes import QuoteUpdater
from mate_invest.widgets import *

Gtk.Window.set_default_icon_from_file(join(mate_invest.ART_DATA_DIR, "invest_neutral.svg"))

class InvestApplet(MatePanelApplet.Applet):
	def __init__(self, applet):
		self.applet = applet

		# name, stock_id, label, accellerator, tooltip, callback
		menu_actions = [("About", Gtk.STOCK_ABOUT, _("About"), None, None, self.on_about),
				("Help", Gtk.STOCK_HELP, _("Help"), None, None, self.on_help),
				("Prefs", Gtk.STOCK_PREFERENCES, _("Preferences"), None, None, self.on_preferences),
				("Refresh", Gtk.STOCK_REFRESH, _("Refresh"), None, None, self.on_refresh)
				]
		actiongroup = Gtk.ActionGroup.new("InvestAppletActions")
		actiongroup.set_translation_domain(mate_invest.defs.GETTEXT_PACKAGE)
		actiongroup.add_actions(menu_actions, None)
		self.applet.setup_menu_from_file (join(mate_invest.defs.PKGDATADIR, "Invest_Applet.xml"), actiongroup)

		evbox = Gtk.HBox()
		self.applet_icon = Gtk.Image()
		self.set_applet_icon(0)
		self.applet_icon.show()
		evbox.add(self.applet_icon)
		self.applet.add(evbox)
		self.applet.connect("button-press-event", self.button_clicked)
		self.applet.show_all()
		self.new_ilw()

	def new_ilw(self):
		self.quotes_updater = QuoteUpdater(self.set_applet_icon,
						   self.set_applet_tooltip)
                self.investwidget = Gtk.ScrolledWindow()
                self.investwidget.set_policy(Gtk.PolicyType.NEVER,
                                             Gtk.PolicyType.AUTOMATIC)
                #this helps get the initial height right
                self.investwidget.set_propagate_natural_height(True)
                raw_invest_widget = InvestWidget(self.quotes_updater)

                #the window containing the list of quotes can't be
                #resized by the user so show all quotes possible up to a
                #maximum window size
		window = self.applet.get_window()
		screen = window.get_screen()
                monitor = screen.get_monitor_geometry(
                        screen.get_monitor_at_window (window))
                self.investwidget.set_max_content_height(monitor.height-60)
                
                self.investwidget.add(raw_invest_widget)
		self.ilw = InvestmentsListWindow(self.applet, self.investwidget)

	def reload_ilw(self):
		self.ilw.destroy()
		self.new_ilw()

	def button_clicked(self, widget,event):
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
			# Three cases...
			if len (mate_invest.STOCKS) == 0:
				# a) We aren't configured yet
				mate_invest.preferences.show_preferences(self, _("<b>You have not entered any stock information yet</b>"))
				self.reload_ilw()
			elif not self.quotes_updater.quotes_valid:
				# b) We can't get the data (e.g. offline)
				alert = Gtk.MessageDialog(buttons=Gtk.ButtonsType.CLOSE)
				alert.set_markup(_("<b>No stock quotes are currently available</b>"))
				alert.format_secondary_text(_("The server could not be contacted. The computer is either offline or the servers are down. Try again later."))
				alert.run()
				alert.destroy()
			else:
				# c) Everything is normal: pop-up the window
				self.ilw.toggle_show()
	
	def on_about(self, action):
		mate_invest.about.show_about()
	
	def on_help(self, action):
		mate_invest.help.show_help()

	def on_preferences(self, action):
		mate_invest.preferences.show_preferences(self)
		self.reload_ilw()
	
	def on_refresh(self, action):
		self.quotes_updater.refresh()

	def set_applet_icon(self, change):
		if change == 1:
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(join(mate_invest.ART_DATA_DIR, "invest-22_up.png"), -1,-1)
		elif change == 0:
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(join(mate_invest.ART_DATA_DIR, "invest-22_neutral.png"), -1,-1)
		else:
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(join(mate_invest.ART_DATA_DIR, "invest-22_down.png"), -1,-1)
		self.applet_icon.set_from_pixbuf(pixbuf)
	
	def set_applet_tooltip(self, text):
		self.applet_icon.set_tooltip_text(text)

class InvestmentsListWindow(Gtk.Window):
	def __init__(self, applet, list):
		Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
		self.set_type_hint(Gdk.WindowTypeHint.DOCK)
		self.stick()
		self.set_resizable(False)
		self.set_border_width(6)
		
		self.applet = applet # this is the widget we want to align with
		self.alignment = self.applet.get_orient ()
		
		self.add(list)
		list.show_all()

		# boolean variable that identifies if the window is visible
		# show/hide is triggered by left-clicking on the applet
		self.hidden = True

	def toggle_show(self):
		if self.hidden == True:
                        #we have the problem that the width and height are not
                        #correctly known until the window has finished being
                        #shown (which is done asynchrously). So start by
                        #showing window.
			self.show_all()
                        #then get the window vaguely in the right place
			self.update_position()
                        #and finally, once the window dimensions are fully known,
                        #move it to the right place
                        GObject.idle_add(self.update_position)
			self.hidden = False
		elif self.hidden == False:
			self.hide()
			self.hidden = True

	def update_position (self):
		"""
		Calculates the position and moves the window to it.
		"""
		self.realize()

		# Get our own dimensions & position
		#(wx, wy) = self.get_origin()

		window = self.applet.get_window()
		screen = window.get_screen()
                self.set_screen(screen) #in case of multiple screens
                monitor = screen.get_monitor_geometry (screen.get_monitor_at_window (window))
                (ret, ax, ay) = window.get_origin()
                (ignored, ignored, aw, ah) = window.get_geometry()

		(ww, wh) = self.get_size()

		if self.alignment == MatePanelApplet.AppletOrient.LEFT:
			x = ax - ww
			y = ay

			if (y + wh > monitor.y + monitor.height):
				y = monitor.y + monitor.height - wh

			if (y < 0):
				y = 0

			if (y + wh > monitor.height / 2):
				gravity = Gdk.Gravity.SOUTH_WEST
			else:
				gravity = Gdk.Gravity.NORTH_WEST

		elif self.alignment == MatePanelApplet.AppletOrient.RIGHT:
			x = ax + aw
			y = ay

			if (y + wh > monitor.y + monitor.height):
				y = monitor.y + monitor.height - wh

			if (y < 0):
				y = 0

			if (y + wh > monitor.height / 2):
				gravity = Gdk.Gravity.SOUTH_EAST
			else:
				gravity = Gdk.Gravity.NORTH_EAST

		elif self.alignment == MatePanelApplet.AppletOrient.DOWN:
			x = ax
			y = ay + ah

			if (x + ww > monitor.x + monitor.width):
				x = monitor.x + monitor.width - ww

			if (x < 0):
				x = 0

			gravity = Gdk.Gravity.NORTH_WEST
		elif self.alignment == MatePanelApplet.AppletOrient.UP:
			x = ax
			y = ay - wh

			if (x + ww > monitor.x + monitor.width):
				x = monitor.x + monitor.width - ww

			if (x < 0):
				x = 0

			gravity = Gdk.Gravity.SOUTH_WEST

		self.set_gravity(gravity)
		self.move(x, y)
