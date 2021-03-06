# -*- coding: iso-8859-1 -*-

#Copyright (C) Fiz Vazquez vud1@sindominio.net

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

import logging
import os
from lxml import etree
import dateutil.parser
from dateutil.tz import * # for tzutc()

from pytrainer.lib.date import Date
from pytrainer.lib.gpx import Gpx
from pytrainer.lib.graphdata import GraphData
from pytrainer.lib.unitsconversor import *

class Activity:
	'''
	Class that knows everything about a particular activity

	All values are stored in the class (and DB) in metric and are converted as needed

	tracks			- (list) tracklist from gpx
	tracklist		- (list of dict) trackpoint data from gpx
	laps			- (list of dict) lap list
	tree			- (ElementTree) parsed xml of gpx file
	us_system		- (bool) True: imperial measurement False: metric measurement
	distance_unit	- (string) unit to use for distance
	speed_unit		- (string) unit to use for speed
	distance_data	- (dict of graphdata classes) contains the graph data with x axis distance
	time_data		- (dict of graphdata classes) contains the graph data with x axis time
	height_unit		- (string) unit to use for height
	pace_unit		- (string) unit to use for pace
	gpx_file		- (string) gpx file name
	gpx				- (Gpx class) actual gpx instance
	sport_name		- (string) sport name
	sport_id		- (string) id for sport in sports table
	title			- (string) title of activity
	date			- (string) date of activity
	time			- (int) activity duration in seconds
	time_tuple		- (tuple) activity duration as hours, min, secs tuple
	beats			- (int) average heartrate for activity
	maxbeats 		- (int) maximum heartrate for activity
	comments		- (string) activity comments
	calories		- (int) calories of activity
	id_record		- (string) id for activity in records table
	date_time_local	- (string) date and time of activity in local timezone
	date_time_utc	- (string) date and time of activity in UTC timezone
	date_time		- (datetime) date and time of activity in local timezone
	starttime		- (string)
	distance 		- (float) activity distance
	average			- (float) average speed of activity
	upositive 		- (float) height climbed during activity
	unegative		- (float) height decended during activity
	maxspeed 		- (float) maximum speed obtained during activity
	maxpace 		- (float) maxium pace obtained during activity
	pace			- (float) average pace for activity
	has_data		- (bool) true if instance has data populated
	x_axis			- (string) distance or time, determines what will be graphed on x axis
	x_limits		- (tuple of float) start, end limits of x axis (as determined by matplotlib)
	y1_limits		- (tuple of float) start, end limits of y1 axis (as determined by matplotlib)
	y2_limits		- (tuple of float) start, end limits of y2 axis (as determined by matplotlib)
	x_limits_u		- (tuple of float) start, end limits of x axis (as requested by user)
	y1_limits_u		- (tuple of float) start, end limits of y1 axis (as requested by user)
	y2_limits_u		- (tuple of float) start, end limits of y2 axis (as requested by user)
	show_laps		- (bool) display laps on graphs
	lap_distance	- (graphdata)
	lap_time		- (graphdata)
	pace_limit		- (int) maximum pace that is valid for this activity
	'''
	def __init__(self, pytrainer_main = None, id = None):
		logging.debug(">>")
		self.id = id
		#It is an error to try to initialise with no id
		if self.id is None:
			return
		#It is an error to try to initialise with no reference to pytrainer_main
		if pytrainer_main is None:
			print("Error - must initialise with a reference to the main pytrainer class")
			return
		self.pytrainer_main = pytrainer_main
		self.tracks = None
		self.tracklist = None
		self.laps = None
		self.tree = None
		self.has_data = False
		self.distance_data = {}
		self.time_data = {}
		self.time_pause = 0
		self.pace_limit = None
		self.starttime = None
		self.gpx_distance = None
		#self.upositive = 0
		#self.unegative = 0
		if self.pytrainer_main.profile.getValue("pytraining","prf_us_system") == "True":
			self.us_system = True
		else:
			self.us_system = False
		self._set_units()
		self.gpx_file = "%s/%s.gpx" % (self.pytrainer_main.profile.gpxdir, id)
		#It is OK to not have a GPX file for an activity - this just limits us to information in the DB
		if not os.path.isfile(self.gpx_file):
			self.gpx_file = None
			logging.debug("No GPX file found for record id: %s" % id)
		if self.gpx_file is not None:
			self._init_from_gpx_file()
		self._init_from_db()
		self._init_graph_data()
		self._generate_per_lap_graphs()
		self.x_axis = "distance"
		self.x_limits = (None, None)
		self.y1_limits = (None, None)
		self.y2_limits = (None, None)
		self.x_limits_u = (None, None)
		self.y1_limits_u = (None, None)
		self.y2_limits_u = (None, None)
		self.y1_grid = False
		self.y2_grid = False
		self.x_grid = False
		self.show_laps = False
		logging.debug("<<")

	def __str__(self):
		return '''
        tracks (%s)
		tracklist (%s)
		laps (%s)
		tree (%s)
		us_system (%s)
		distance_unit (%s)
		speed_unit (%s)
		distance_data (%s)
		time_data (%s)
		height_unit (%s)
		pace_unit (%s)
		gpx_file (%s)
		gpx (%s)
		sport_name (%s)
		sport_id (%s)
		title (%s)
		date (%s)
		time (%s)
		time_tuple (%s)
		beats (%s)
		maxbeats (%s)
		comments (%s)
		calories (%s)
		id_record (%s)
		date_time_local (%s)
		date_time_utc (%s)
		date_time (%s)
		starttime (%s)
		distance (%s)
		average (%s)
		upositive (%s)
		unegative (%s)
		maxspeed (%s)
		maxpace (%s)
		pace (%s)
		has_data (%s)
		x_axis (%s)
		x_limits (%s)
		y1_limits (%s)
		y2_limits (%s)
		x_limits_u (%s)
		y1_limits_u (%s)
		y2_limits_u (%s)
		show_laps (%s)
		lap_distance (%s)
		lap_time (%s)
		pace_limit (%s)
        ''' % ('self.tracks', self.tracklist, self.laps, self.tree, self.us_system,
			self.distance_unit, self.speed_unit, self.distance_data, self.time_data,
			self.height_unit, self.pace_unit, self.gpx_file, self.gpx, self.sport_name,
			self.sport_id, self.title, self.date, self.time, self.time_tuple, self.beats,
			self.maxbeats, self.comments, self.calories, self.id_record, self.date_time_local,
			self.date_time_utc, self.date_time, self.starttime, self.distance, self.average,
			self.upositive, self.unegative, self.maxspeed, self.maxpace, self.pace, self.has_data,
			self.x_axis, self.x_limits, self.y1_limits, self.y2_limits, self.x_limits_u, self.y1_limits_u,
			self.y2_limits_u, self.show_laps, self.lap_distance, self.lap_time, self.pace_limit)

	def _set_units(self):
		if self.us_system:
			self.distance_unit = _("miles")
			self.speed_unit = _("miles/h")
			self.pace_unit = _("min/mile")
			self.height_unit = _("feet")
		else:
			self.distance_unit = _("km")
			self.speed_unit = _("km/h")
			self.pace_unit = _("min/km")
			self.height_unit = _("m")
		self.units = { 'distance': self.distance_unit, 'average': self.speed_unit, 'upositive': self.height_unit, 'unegative': self.height_unit, 'maxspeed': self.speed_unit, 'pace': self.pace_unit, 'maxpace': self.pace_unit }

	def _init_from_gpx_file(self):
		'''
		Get activity information from the GPX file
		'''
		logging.debug(">>")
		#Parse GPX file
		#print "Activity initing GPX.. ",
		self.gpx = Gpx(filename = self.gpx_file) #TODO change GPX code to do less....
		self.tree = self.gpx.tree
		self.tracks = self.gpx.getTrackList() #TODO fix - this should removed and replaced with self.tracklist functionality
		self.tracklist = self.gpx.trkpoints
		self.gpx_distance = self.gpx.total_dist
		logging.info("GPX Distance: %s | distance (trkpts): %s | duration: %s | duration (trkpts): %s" % (self.gpx_distance, self.gpx.total_dist_trkpts, self.gpx.total_time, self.gpx.total_time_trkpts))
		time_diff = self.gpx.total_time_trkpts - self.gpx.total_time
		acceptable_lapse = 4 # number of seconds that duration calculated using lap and trkpts data can differ
		if time_diff > acceptable_lapse:
			self.time_pause = time_diff
			logging.debug("Identified non active time: %s s" % self.time_pause)
		logging.debug("<<")

	def _init_from_db(self):
		'''
		Get activity information from the DB
		'''
		logging.debug(">>")
		#Get base information
		cols = ("sports.name","id_sports", "date","distance","time","beats","comments",
						"average","calories","id_record","title","upositive","unegative",
						"maxspeed","maxpace","pace","maxbeats","date_time_utc","date_time_local", "sports.max_pace")
		# outer join on sport id to workaround bug where sport reference is null on records from GPX import
		db_result = self.pytrainer_main.ddbb.select("records left outer join sports on records.sport=sports.id_sports",
					", ".join(cols),
					"id_record=\"%s\" " %self.id)
		if len(db_result) == 1:
			row = db_result[0]
			self.sport_name = row[cols.index('sports.name')]
			if self.sport_name == None:
				self.sport_name = ""
			self.sport_id = row[cols.index('id_sports')]
			self.pace_limit = row[cols.index('sports.max_pace')]
			if self.pace_limit == 0 or self.pace_limit == "":
				self.pace_limit = None
			self.title = row[cols.index('title')]
			if self.title is None:
				self.title = ""
			self.date = row[cols.index('date')]
			self.time = self._int(row[cols.index('time')])
			self.time_tuple = Date().second2time(self.time)
			self.beats = self._int(row[cols.index('beats')])
			self.comments = row[cols.index('comments')]
			if self.comments is None:
				self.comments = ""
			self.calories = self._int(row[cols.index('calories')])
			self.id_record = row[cols.index('id_record')]
			self.maxbeats = self._int(row[cols.index('maxbeats')])
			#Sort time....
			# ... use local time if available otherwise use date_time_utc and create a local datetime...
			self.date_time_local = row[cols.index('date_time_local')]
			self.date_time_utc = row[cols.index('date_time_utc')]
			if self.date_time_local is not None: #Have a local time stored in DB
				self.date_time = dateutil.parser.parse(self.date_time_local)
				self.starttime = self.date_time.strftime("%X")
			else: #No local time in DB
				tmpDateTime = dateutil.parser.parse(self.date_time_utc)
				self.date_time = tmpDateTime.astimezone(tzlocal()) #datetime with localtime offset (using value from OS)
				self.starttime = self.date_time.strftime("%X")
			#Sort data that changes for the US etc
			#if self.us_system:
			#	self.distance = km2miles(self._float(row[cols.index('distance')]))
			#	self.average = km2miles(self._float(row[cols.index('average')]))
			#	self.upositive = m2feet(self._float(row[cols.index('upositive')]))
			#	self.unegative = m2feet(self._float(row[cols.index('unegative')]))
			#	self.maxspeed = km2miles(self._float(row[cols.index('maxspeed')]))
			#	self.maxpace = pacekm2miles(self._float(row[cols.index('maxpace')]))
			#	self.pace = pacekm2miles(self._float(row[cols.index('pace')]))
			#else:
			self.distance = self._float(row[cols.index('distance')])
			if not self.distance:
				self.distance = self.gpx_distance
			self.average = self._float(row[cols.index('average')])
			self.upositive = self._float(row[cols.index('upositive')])
			self.unegative = self._float(row[cols.index('unegative')])
			self.maxspeed = self._float(row[cols.index('maxspeed')])
			self.maxpace = self._float(row[cols.index('maxpace')])
			self.pace = self._float(row[cols.index('pace')])
			self.has_data = True
		else:
			raise Exception( "Error - multiple results from DB for id: %s" % self.id )
		#Get lap information
		laps = self.pytrainer_main.ddbb.select_dict("laps",
					("id_lap", "record", "elapsed_time", "distance", "start_lat", "start_lon", "end_lat", "end_lon", "calories", "lap_number", "intensity", "avg_hr", "max_hr", "max_speed", "laptrigger", "comments"),
					"record=\"%s\"" % self.id)
		if laps is None or laps == [] or len(laps) < 1:  #No laps found
			logging.debug("No laps in DB for record %d" % self.id)
			if self.gpx_file is not None:
				laps = self._get_laps_from_gpx()
		self.laps = laps
		logging.debug("<<")

	def _generate_per_lap_graphs(self):
		'''Build lap based graphs...'''
		logging.debug(">>")
		if self.laps is None:
			logging.debug("No laps to generate graphs from")
			logging.debug("<<")
			return
		#Lap columns
		self.lap_distance = GraphData()
		self.lap_distance.set_color('#CCFF00', '#CCFF00')
		self.lap_distance.graphType = "vspan"
		self.lap_time = GraphData()
		self.lap_time.set_color('#CCFF00', '#CCFF00')
		self.lap_time.graphType = "vspan"
		#Pace
		title=_("Pace by Lap")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Pace'), self.pace_unit)
		self.distance_data['pace_lap'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['pace_lap'].set_color('#99CCFF', '#99CCFF')
		self.distance_data['pace_lap'].graphType = "bar"
		xlabel=_("Time (seconds)")
		self.time_data['pace_lap'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.time_data['pace_lap'].set_color('#99CCFF', '#99CCFF')
		self.time_data['pace_lap'].graphType = "bar"
		#Speed
		title=_("Speed by Lap")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Speed'), self.speed_unit)
		self.distance_data['speed_lap'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['speed_lap'].set_color('#336633', '#336633')
		self.distance_data['speed_lap'].graphType = "bar"
		xlabel=_("Time (seconds)")
		self.time_data['speed_lap'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.time_data['speed_lap'].set_color('#336633', '#336633')
		self.time_data['speed_lap'].graphType = "bar"
		for lap in self.laps:
			time = float( lap['elapsed_time'].decode('utf-8') ) # time in sql is a unicode string
			dist = lap['distance']/1000 #distance in km
			try:
				pace = time/(60*dist) #min/km
			except ZeroDivisionError:
				pace = 0.0
			try:
				avg_speed = dist/(time/3600) # km/hr
			except:
				avg_speed = 0.0
			if self.pace_limit is not None and pace > self.pace_limit:
				logging.debug("Pace (%s) exceeds limit (%s). Setting to 0" % (str(pace), str(self.pace_limit)))
				pace = 0.0
			logging.debug("Time: %f, Dist: %f, Pace: %f, Speed: %f" % (time, dist, pace, avg_speed) )
			self.lap_time.addBars(x=time, y=10)
			if self.us_system:
				self.lap_distance.addBars(x=km2miles(dist), y=10)
				self.distance_data['pace_lap'].addBars(x=km2miles(dist), y=pacekm2miles(pace))
				self.time_data['pace_lap'].addBars(x=time, y=pacekm2miles(pace))
				self.distance_data['speed_lap'].addBars(x=km2miles(dist), y=km2miles(avg_speed))
				self.time_data['speed_lap'].addBars(x=time, y=km2miles(avg_speed))
			else:
				self.lap_distance.addBars(x=dist, y=10)
				self.distance_data['pace_lap'].addBars(x=dist, y=pace)
				self.time_data['pace_lap'].addBars(x=time, y=pace)
				self.distance_data['speed_lap'].addBars(x=dist, y=avg_speed)
				self.time_data['speed_lap'].addBars(x=time, y=avg_speed)
		logging.debug("<<")

	def _get_laps_from_gpx(self):
		logging.debug(">>")
		laps = []
		gpxLaps = self.gpx.getLaps()
		for lap in gpxLaps:
			lap_number = gpxLaps.index(lap)
			tmp_lap = {}
			tmp_lap['record'] = self.id
			tmp_lap['lap_number'] = lap_number
			tmp_lap['elapsed_time'] = lap[0]
			tmp_lap['distance'] = lap[4]
			tmp_lap['start_lat'] = lap[5]
			tmp_lap['start_lon'] = lap[6]
			tmp_lap['end_lat'] = lap[1]
			tmp_lap['end_lon'] = lap[2]
			tmp_lap['calories'] = lap[3]
			laps.append(tmp_lap)
		if laps is not None:
			for lap in laps:
				lap_keys = ", ".join(map(str, lap.keys()))
				lap_values = lap.values()
				self.pytrainer_main.record.insertLaps(lap_keys,lap.values())
		logging.debug("<<")
		return laps

	def _init_graph_data(self):
		logging.debug(">>")
		if self.tracklist is None:
			logging.debug("No tracklist in activity")
			logging.debug("<<")
			return
		#Profile
		title=_("Elevation")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Elevation'), self.height_unit)
		self.distance_data['elevation'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['elevation'].set_color('#ff0000', '#ff0000')
		self.distance_data['elevation'].show_on_y1 = True #Make graph show elevation by default
		xlabel=_("Time (seconds)")
		self.time_data['elevation'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
		self.time_data['elevation'].set_color('#ff0000', '#ff0000')
		self.time_data['elevation'].show_on_y1 = True #Make graph show elevation by default
		#Corrected Elevation...
		title=_("Corrected Elevation")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Corrected Elevation'), self.height_unit)
		self.distance_data['cor_elevation'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['cor_elevation'].set_color('#993333', '#993333')
		xlabel=_("Time (seconds)")
		self.time_data['cor_elevation'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
		self.time_data['cor_elevation'].set_color('#993333', '#993333')
		#Speed
		title=_("Speed")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Speed'), self.speed_unit)
		self.distance_data['speed'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['speed'].set_color('#000000', '#000000')
		xlabel=_("Time (seconds)")
		self.time_data['speed'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
		self.time_data['speed'].set_color('#000000', '#000000')
		#Pace
		title=_("Pace")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Pace'), self.pace_unit)
		self.distance_data['pace'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['pace'].set_color('#0000ff', '#0000ff')
		xlabel=_("Time (seconds)")
		self.time_data['pace'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
		self.time_data['pace'].set_color('#0000ff', '#0000ff')
		#Heartrate
		title=_("Heart Rate")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Heart Rate'), _('bpm'))
		self.distance_data['hr'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['hr'].set_color('#00ff00', '#00ff00')
		xlabel=_("Time (seconds)")
		self.time_data['hr'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
		self.time_data['hr'].set_color('#00ff00', '#00ff00')
		#Heartrate as %
		maxhr = self.pytrainer_main.profile.getMaxHR()
		title=_("Heart Rate (% of max)")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Heart Rate'), _('%'))
		self.distance_data['hr_p'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['hr_p'].set_color('#00ff00', '#00ff00')
		xlabel=_("Time (seconds)")
		self.time_data['hr_p'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
		self.time_data['hr_p'].set_color('#00ff00', '#00ff00')
		#Cadence
		title=_("Cadence")
		xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
		ylabel="%s (%s)" % (_('Cadence'), _('rpm'))
		self.distance_data['cadence'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
		self.distance_data['cadence'].set_color('#cc00ff', '#cc00ff')
		xlabel=_("Time (seconds)")
		self.time_data['cadence'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
		self.time_data['cadence'].set_color('#cc00ff', '#cc00ff')
		for track in self.tracklist:
			try:
				pace = 60/track['velocity']
				if self.pace_limit is not None and pace > self.pace_limit:
					logging.debug("Pace (%s) exceeds limit (%s). Setting to 0" % (str(pace), str(self.pace_limit)))
					pace = 0  #TODO this should be None when we move to newgraph...
			except Exception as e:
				#print type(e), e
				pace = 0
			try:
				hr_p = float(track['hr'])/maxhr*100
			except:
				hr_p = 0
			if self.us_system:
				self.distance_data['elevation'].addPoints(x=km2miles(track['elapsed_distance']), y=m2feet(track['ele']))
				self.distance_data['cor_elevation'].addPoints(x=km2miles(track['elapsed_distance']), y=m2feet(track['correctedElevation']))
				self.distance_data['speed'].addPoints(x=km2miles(track['elapsed_distance']), y=km2miles(track['velocity']))
				self.distance_data['pace'].addPoints(x=km2miles(track['elapsed_distance']), y=pacekm2miles(pace))
				self.distance_data['hr'].addPoints(x=km2miles(track['elapsed_distance']), y=track['hr'])
				self.distance_data['hr_p'].addPoints(x=km2miles(track['elapsed_distance']), y=hr_p)
				self.distance_data['cadence'].addPoints(x=km2miles(track['elapsed_distance']), y=track['cadence'])
				self.time_data['elevation'].addPoints(x=track['time_elapsed'], y=m2feet(track['ele']))
				self.time_data['cor_elevation'].addPoints(x=track['time_elapsed'], y=m2feet(track['correctedElevation']))
				self.time_data['speed'].addPoints(x=track['time_elapsed'], y=km2miles(track['velocity']))
				self.time_data['pace'].addPoints(x=track['time_elapsed'], y=pacekm2miles(pace))
			else:
				self.distance_data['elevation'].addPoints(x=track['elapsed_distance'], y=track['ele'])
				self.distance_data['cor_elevation'].addPoints(x=track['elapsed_distance'], y=track['correctedElevation'])
				self.distance_data['speed'].addPoints(x=track['elapsed_distance'], y=track['velocity'])
				self.distance_data['pace'].addPoints(x=track['elapsed_distance'], y=pace)
				self.distance_data['hr'].addPoints(x=track['elapsed_distance'], y=track['hr'])
				self.distance_data['hr_p'].addPoints(x=track['elapsed_distance'], y=hr_p)
				self.distance_data['cadence'].addPoints(x=track['elapsed_distance'], y=track['cadence'])
				self.time_data['elevation'].addPoints(x=track['time_elapsed'], y=track['ele'])
				self.time_data['cor_elevation'].addPoints(x=track['time_elapsed'], y=track['correctedElevation'])
				self.time_data['speed'].addPoints(x=track['time_elapsed'], y=track['velocity'])
				self.time_data['pace'].addPoints(x=track['time_elapsed'], y=pace)
			self.time_data['hr'].addPoints(x=track['time_elapsed'], y=track['hr'])
			self.time_data['hr_p'].addPoints(x=track['time_elapsed'], y=hr_p)
			self.time_data['cadence'].addPoints(x=track['time_elapsed'], y=track['cadence'])
		#Remove data with no values
		for item in self.distance_data.keys():
			if len(self.distance_data[item]) == 0:
				logging.debug( "No values for %s. Removing...." % item )
				del self.distance_data[item]
		for item in self.time_data.keys():
			if len(self.time_data[item]) == 0:
				logging.debug( "No values for %s. Removing...." % item )
				del self.time_data[item]
		logging.debug("<<")
		#Add Heartrate zones graphs
		if 'hr' in self.distance_data:
			zones = self.pytrainer_main.profile.getZones()		
			title=_("Heart Rate zone")
			xlabel="%s (%s)" % (_('Distance'), self.distance_unit)
			ylabel="%s (%s)" % (_('Heart Rate'), _('bpm'))
			self.distance_data['hr_z'] = GraphData(title=title, xlabel=xlabel, ylabel=ylabel)
			self.distance_data['hr_z'].graphType = "hspan"
			self.distance_data['hr_z'].set_color(None, None)
			xlabel=_("Time (seconds)")
			self.time_data['hr_z'] = GraphData(title=title,xlabel=xlabel, ylabel=ylabel)
			self.time_data['hr_z'].set_color(None, None)
			for zone in zones:
				self.distance_data['hr_z'].addPoints(x=zone[0], y=zone[1], label=zone[3], color=zone[2])
				self.time_data['hr_z'].addPoints(x=zone[0], y=zone[1], label=zone[3], color=zone[2])

	def _float(self, value):
		try:
			result = float(value)
		except:
			result = 0.0
		return result

	def _int(self, value):
		try:
			result = int(value)
		except:
			result = 0
		return result

	def get_value_f(self, param, format=None, with_units=False):
		''' Function to return a value formated as a string
			- takes into account US/metric
			- also appends units if required
		'''
		value = self.get_value(param)
		if not value:
			#Return blank string if value is None or 0
			return ""
		if format is not None:
			result = format % value
		else:
			result = str(value)
		if with_units:
			if param in self.units:
				result += self.units[param]
		#print "activity: 509", result
		return result

	def get_value(self, param):
		''' Function to get the value of various params in this activity instance
			Automatically returns values converted to imperial if needed
		'''
		if param == 'distance':
			if self.us_system:
				return km2miles(self.distance)
			else:
				return self.distance
		elif param == 'average':
			if self.us_system:
				return km2miles(self.average)
			else:
				return self.average
		elif param == 'upositive':
			if self.us_system:
				return m2feet(self.upositive)
			else:
				return self.upositive
		elif param == 'unegative':
			if self.us_system:
				return m2feet(self.unegative)
			else:
				return self.unegative
		elif param == 'maxspeed':
			if self.us_system:
				return km2miles(self.maxspeed)
			else:
				return self.maxspeed
		elif param == 'maxpace':
			if self.us_system:
				return self.pace_from_float(pacekm2miles(self.maxpace))
			else:
				return self.pace_from_float(self.maxpace)
		elif param == 'pace':
			if self.us_system:
				return self.pace_from_float(pacekm2miles(self.pace))
			else:
				return self.pace_from_float(self.pace)
		elif param == 'calories':
			return self.calories
		elif param == 'time':
			if not self.time:
				return ""
			_hour,_min,_sec=self.pytrainer_main.date.second2time(self.time)
			if _hour == 0:
				return "%02d:%02d" % (_min, _sec)
			else:
				return "%0d:%02d:%02d" % (_hour, _min, _sec)
		else:
			print "Unable to provide value for unknown parameter (%s) for activity" % param
			return None

	def set_value(self, param, value):
		''' Function to set the value of various params in this activity instance
			Automatically converts from imperial if using them
		'''
		_value = _float(value)
		if param == 'distance':
			if self.us_system:
				self.distance = miles2mk(_value)
			else:
				self.distance = _value
		elif param == 'average':
			if self.us_system:
				self.average = miles2mk(_value)
			else:
				self.average = _value
		elif param == 'upositive':
			if self.us_system:
				self.upositive = feet2m(_value)
			else:
				self.upositive = _value
		elif param == 'unegative':
			if self.us_system:
				self.unegative = feet2m(_value)
			else:
				self.unegative = _value
		elif param == 'maxspeed':
			if self.us_system:
				self.maxspeed = miles2mk(_value)
			else:
				self.maxspeed = _value
		elif param == 'maxpace':
			if self.us_system:
				_maxpace = pacemiles2mk(_value)
			else:
				_maxpace = _value
			self.maxpace = self.pace_to_float(_maxpace)
		elif param == 'pace':
			if self.us_system:
				_pace = pacemiles2mk(_value)
			else:
				_pace = _value
			self.pace = self.pace_to_float(_pace)
		else:
			print "Unable to set value (%s) for unknown parameter (%s) for activity" % (str(value), param)


	def pace_to_float(self, value):
		'''Take a mm:ss or mm.ss and return float'''
		value = value.replace(':', '.')
		try:
			value = float(value)
		except ValueError:
			value = None
		return value

	def pace_from_float(self, value):
		'''Helper to generate mm:ss from float representation mm.ss (or mm,ss?)'''
		#Check that value supplied is a float
		if not value:
			return ""
		try:
			_value = "%0.2f" % float(value)
		except ValueError:
			_value = str(value)
		return _value.replace('.',':')

