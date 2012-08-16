#!/usr/bin/python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
"""
   Copyright (c) 2012 Sergio Castillo-Pérez

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
# ------------------------------------------------------------------------------

import sys
import TorCtl
import TorUtil
import PathSupport
import socket
import struct
import GeoIP
import random
import time
import networkx

from circuits    import *
from TorUtil     import *
from PathSupport import *
from graph       import *

# ------------------------------------------------------------------------------

VERSION        = "0.1.0"
max_circuits   = 200
k_paths	       = 300
circ_nrouters  = 3
country_filter = 'US'
ip_policy      = '255.255.255.255'
port_policy    = 80

# ------------------------------------------------------------------------------

class Stream:
	def __init__(self, id, circ_id, ctime):
		self.strm_id  = id
		self.circ_id  = circ_id
		self.new_time = ctime

	def set_circ(self, circ_id):
		self.circ_id = circ_id

	def set_close_time(self, ctime):
		self.close_time = ctime
	
	def get_total_time(self):
		return self.close_time - self.new_time

# -----------------------------------------------------------------------------

class Circuit:
	def __init__(self, id, launch_time):
		self.circ_id     = id
		self.launch_time = launch_time
		self.built_time  = None
		self.lstreams    = []
		self.last_extended_at = 0
		self.path        = []
                
	def set_built_time(self, ctime):
		self.built_time = ctime

	def set_last_extended_at(self, last_time):
                self.last_extended_at = last_time

	def set_path(self, path):
                self.path = path

	def get_path(self, path):
                return self.path

	def get_last_extended_at(self):
                return self.last_extended_at

	def is_built(self):
		return self.built_time != None

	def del_strm(self, strm_id):
		self.lstreams.remove(strm_id)

	def add_strm(self, strm_id):
		self.lstreams.append(strm_id)

	def get_built_time(self):
		return self.built_time - self.launch_time

# ------------------------------------------------------------------------------
# General Event Handler
# See https://gitweb.torproject.org/torspec.git/blob_plain/master:/control-spec.txt
# ------------------------------------------------------------------------------
class EventHandler(TorCtl.EventHandler):

	def __init__(self, c, lencircuit):
		TorCtl.EventHandler.__init__(self)
		self.c        = c
		self.dcircuit = {}
		self.dstream  = {}
		self.circ_idx = -1
		self.lencirc  = lencircuit
		self.G        = Graph(lencircuit, k_paths)

	# ----------------------------------------------------------------------

	def set_lencirc(self, lencircuit):
	        self.lencirc = lencircuit
	        self.G.set_length(lencircuit)
	        
	# ----------------------------------------------------------------------

	def avail_circs(self):
		lcircs = []

		for circ_obj in self.dcircuit.values():
			if circ_obj.is_built():
				lcircs.append(circ_obj.circ_id)
		return lcircs

	# ----------------------------------------------------------------------

	def attchstrm(self, strmid):

		# Use a Round Robin strategy for selecting the circuit
		lcircs = self.avail_circs()
		self.circ_idx = (self.circ_idx + 1) % len(lcircs)
		circid = lcircs[self.circ_idx]

		print "\t\tAttaching STREAM (id: %s) -> CIRCUIT (id: %i)" % (strmid, circid)

		try:
			self.c.attach_stream(strmid, circid)
			cur_circ = self.dcircuit[circid]
			cur_circ.add_strm(strmid)
			return circid

		except TorCtl.ErrorReply, e:
			print "\t\tError Attaching STREAM %s: %s" %\
				(strmid, e.args)
			return False
	
	# ----------------------------------------------------------------------

	def get_graph(self):
	        return self.G
        
	# ----------------------------------------------------------------------
	# Stream Event handler
	# ----------------------------------------------------------------------
	def stream_status_event(self, event):

		if event.status in ['NEW', 'NEWRESOLVE'] and event.purpose and \
		   event.purpose.find("DIR_") == 0:
			return

		if event.status == "NEW":

			lcircs = self.avail_circs()
			if not lcircs:
				return

			circid = self.attchstrm(event.strm_id)
			if circid:
				new_strm = Stream(event.strm_id, circid, event.arrived_at)
				self.dstream[event.strm_id] = new_strm

		if event.status == "CLOSED":

			if self.dstream.has_key(event.strm_id):
				cur_strm    = self.dstream[event.strm_id]
				cur_strm.set_close_time(event.arrived_at)
				cur_circ_id = cur_strm.circ_id
				cur_circ    = self.dcircuit[cur_circ_id]
				cur_circ.del_strm(event.strm_id)

				print "\t\tTotal STREAM %d (circ: %d) time: %.8f" % \
				      (event.strm_id, event.circ_id, cur_strm.get_total_time())
				
				self.dstream.pop(event.strm_id)
				return

		if event.status in ['FAILED', 'DETACHED']:

			if self.dstream.has_key(event.strm_id):
				cur_strm    = self.dstream[event.strm_id]
				cur_circ_id = cur_strm.circ_id
				cur_circ    = self.dcircuit[cur_circ_id]
				cur_circ.del_strm(event.strm_id)
				self.dstream.pop(event.strm_id)

				return

	# ----------------------------------------------------------------------
	# Circuit Event Handler
	# ----------------------------------------------------------------------
	def circ_status_event(self, event):

                if event.status == "EXTENDED":
                        if self.dcircuit.has_key(event.circ_id):
                                cur_circ = self.dcircuit[event.circ_id]

                                if len(event.path) == 1:
                                      latency = event.arrived_at - cur_circ.launch_time
                                      self.G.update_first_edge(event.path[0], latency, event.arrived_at)
                                      cur_circ.set_last_extended_at(event.arrived_at)
                                      return

				latency = event.arrived_at - cur_circ.get_last_extended_at()
				cur_circ.set_last_extended_at(event.arrived_at)
				nodei, nodej = event.path[-2:]
				self.G.update_edge(nodei, nodej, latency, event.arrived_at)
				

		if event.status == "LAUNCHED":
			if len(self.avail_circs()) + 1 > max_circuits:
				self.c.close_circuit(event.circ_id)
				return 

			print "\tBuilding new CIRCUIT (%i)" % event.circ_id
			new_circ = Circuit(event.circ_id, event.arrived_at)
			self.dcircuit[event.circ_id] = new_circ

		if event.status == "FAILED" or event.status == "CLOSED":
			if self.dcircuit.has_key(event.circ_id):
				print "\tFailed/closed CIRCUIT (%i): %s " %\
					(event.circ_id, event.reason)
					
				# Reattach pending streams from the current circuit
				cur_circ = self.dcircuit[event.circ_id]
				if cur_circ.lstreams:
					for strm in cur_circ.lstreams:
						self.attchstrm(strm)

				self.dcircuit.pop(event.circ_id)


		if event.status == "BUILT":
			if self.dcircuit.has_key(event.circ_id):
				if len(self.avail_circs()) + 1 > max_circuits:
				        try:
  					        self.c.close_circuit(event.circ_id)
                                        except:
                                                pass
					self.dcircuit.pop(event.circ_id)
					return

				if len(event.path) != circ_nrouters:
					self.c.close_circuit(event.circ_id)
					self.dcircuit.pop(event.circ_id)
					return
				
				# Update construction times and path
				cur_circ = self.dcircuit[event.circ_id]
				cur_circ.set_built_time(event.arrived_at)
				cur_circ.set_path(event.path)
				built_time = cur_circ.get_built_time()

				print "\tBuilt CIRCUIT (id: %i - %.2fs): %s" %\
				      (event.circ_id, built_time, str(event.path))
                                      
# ------------------------------------------------------------------------------

def built_or_launch_circs(c):
	circ_stat = c.get_info('circuit-status')['circuit-status'].split('\n')
	lcirc = filter(lambda x:x !='', circ_stat)
	lcirc = filter(lambda x:(x.split(' ')[1] == 'BUILT') or \
				(x.split(' ')[1] == 'LAUNCHED') , lcirc)
	return lcirc

# ------------------------------------------------------------------------------

if __name__ == '__main__':

	TorUtil.loglevel = "ERROR"

	print "TorSpeed v.", VERSION 
	print "[-] Connecting to TOR port control..."
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((TorUtil.control_host,TorUtil.control_port))
	c = Connection(s)
	#c.debug(file("control.log", "w"))

	print "[-] Launching thread..."
	c.launch_thread()

	print "[-] Authenticating to TOR port control..."
	c.authenticate(TorUtil.control_pass)

	print "[-] Retrieving router node list...",
	rlist = c.read_routers(c.get_network_status())
	print "(%i nodes) " % len(rlist)

	# Filter routers based on its country and exit policy ------------------
	print "[-] Filtering nodes...",
	nfilter = filter_nodes(rlist)
	# nfilter.by_country(country_filter)
	# nfilter.by_exit_policy(ip_policy, port_policy)

	rlist = nfilter.get_nodes()
	print "(%i nodes) " % len(rlist)

        # Close any previous built circuit -------------------------------------
	print '[-] Closing all previous built circuits...'
	circ_stat = c.get_info('circuit-status')['circuit-status'].split('\n')
	for el in circ_stat:
		if el == '':
			continue
		circ_id = int(el.split(' ')[0])
		c.close_circuit(circ_id)

	# Set the event handler ------------------------------------------------
	event_handler = EventHandler(c, circ_nrouters)
	c.set_event_handler(event_handler)
	c.set_events([TorCtl.EVENT_TYPE.STREAM, TorCtl.EVENT_TYPE.CIRC], True)

	# Create circuits according to a selection strategy --------------------
	print "[-] Creating until %i circuits (%s routers)...\n" %\
	      (max_circuits, country_filter)

	circ_gen = circ_generator(rlist)

	while True:
		npending_circs = max_circuits - len(built_or_launch_circs(c))
		print npending_circs, len(built_or_launch_circs(c))

		for i in xrange(npending_circs):
			new_circ = circ_gen.rand_nodes(circ_nrouters)
			#new_circ = circ_gen.rand_prio_bw(circ_nrouters)
			#new_circ = circ_gen.rand_prio_uptime(circ_nrouters)
			#new_circ = circ_gen.rand_prio_bw_uptime(circ_nrouters)
			try:
			      c.extend_circuit(0, new_circ)
			except:
			      continue
		time.sleep(2)

		if npending_circs == 0:
			print "Ready for incomming connections"

# ------------------------------------------------------------------------------
