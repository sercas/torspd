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

import math
import random
import bisect
import GeoIP
import socket
import struct

from entropy import *

# ------------------------------------------------------------------------------

class rand_weight:
        def __init__ (self, lnodes):
                self.lnodes  = lnodes
                self.lweight = []
                self.compute()

        def compute(self):
                self.lnodes.sort(lambda x, y: cmp(x[1], y[1]))

                self.lweight = []
                total = sum([el[1] for el in self.lnodes])
                acum  = 0.0
                for (it, weight) in self.lnodes:
                        acum += weight
                        self.lweight.append(acum/total)

        def get_one(self, remove = False):
                if self.lnodes == []:
                      return None

                rnd  = random.random()
                idx  = bisect.bisect(self.lweight, rnd)
                item = self.lnodes[idx][0]
                
                if remove:
                        self.lnodes = filter(lambda x:x[0] != item, self.lnodes)
                        self.compute()

                return item
                
        def get_n(self, n, repeat = False):
                lres = []
                lold_items = self.lnodes
                
                for i in xrange(n):
                        lres.append(self.get_one(not repeat))
                return lres

                self.lnodes = lold_items
                self.compute()


# ------------------------------------------------------------------------------

class filter_nodes:

        def __init__ (self, lnodes):
                self.lnodes = lnodes        

        def by_country(self, country_filter):
                gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
                filtered_nodes = []

                for node in self.lnodes:
                        str_ip = socket.inet_ntoa(struct.pack('>I', node.ip))
                        node_country = gi.country_code_by_addr(str_ip)
                        if node_country == country_filter:
                                filtered_nodes.append(node)
                self.lnodes = filtered_nodes

        def by_bw(self, min_bw, max_bw):
                filtered_nodes = []
                for node in lnodes:
                        if node.bw >= min_bw and node.bw <= max_bw:
                                filtered_nodes.append(node)
                self.lnodes = filtered_nodes

        def by_uptime(self, min_upt, max_upt):
                filtered_nodes = []
                for node in lnodes:
                        if node.uptime >= min_upt and node.uptime <= max_upt:
                                filtered_nodes.append(node)
                self.lnodes = filtered_nodes

        def by_exit_policy(self, ip, port):
                filtered_nodes = []
                for node in self.lnodes:
                        if node.will_exit_to(ip, port):
                                filtered_nodes.append(node)
                self.lnodes = filtered_nodes

        def by_os(self, os):
                self.lnodes = filter(lambda el:el.os == os, self.lnodes)

        def get_nodes(self):
                return self.lnodes

# ------------------------------------------------------------------------------

class circ_generator:

        def __init__ (self, lnodes):
                self.lnodes = lnodes

        def rand_nodes(self, nnodes):
                random.shuffle(self.lnodes)
                tmp_nodes = self.lnodes[0:nnodes]
                return [el.idhex for el in tmp_nodes]

        def rand_prio_bw(self, nnodes):
                tmp_nodes = [(el.idhex, el.desc_bw) for el in self.lnodes]
                ritems = rand_weight(tmp_nodes)
                return ritems.get_n(nnodes)

        def get_entropy_bw(self):
                bw_nodes = [el.desc_bw for el in self.lnodes]
                total_bw = float(sum(bw_nodes))
                prob_nodes = [el/total_bw for el in bw_nodes]
		return calc_ent(prob_nodes, len(self.lnodes))

        def rand_prio_uptime(self, nnodes):
                tmp_nodes = [(el.idhex, el.uptime) for el in self.lnodes]
                ritems = rand_weight(tmp_nodes)
                return ritems.get_n(nnodes)

        def rand_prio_bw_uptime(self, nnodes):
                tmp_nodes = [(el.idhex, el.bw * el.uptime) for el in self.lnodes]
                ritems = rand_weight(tmp_nodes)
                return ritems.get_n(nnodes)


# ------------------------------------------------------------------------------
