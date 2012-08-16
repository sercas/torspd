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

import time
import math
import random
import itertools
import networkx
from entropy import *

# ------------------------------------------------------------------------------

CLIENT_NODE = "ME"

# ------------------------------------------------------------------------------

class Graph:
  
        def __init__ (self, length, k_paths):
                self.G = networkx.Graph()
                self.inittime = time.time()
                self.pos = []
                self.max_len = length + 1
                self.k_paths = k_paths
                
        # ----------------------------------------------------------------------

        def set_length(self, length):
                self.max_len = length + 1
                
        # ----------------------------------------------------------------------

        def update_first_edge(self, nodej, latency, eventtime):
                 self.update_edge(CLIENT_NODE, nodej, latency, eventtime)

        # ----------------------------------------------------------------------

        def update_edge(self, nodei, nodej, latency, eventtime):
                if (nodei, nodej) not in self.G.edges():
                      self.G.add_edge(nodei, nodej, weight=latency,
                                                    lasttime=eventtime)
                      return

                prevtime = self.G[nodei][nodej]['lasttime']
                alpha    = (prevtime - self.inittime) / (eventtime - self.inittime)
                curlat   = self.G[nodei][nodej]['weight']
                self.G[nodei][nodej]['weight'] = alpha * curlat + (1 - alpha) * latency
                self.G[nodei][nodej]['lasttime'] = eventtime

	# ----------------------------------------------------------------------

        def get_paths_length_n(self, s, t, curpath, sol):
                if len(sol) == self.k_paths:
                      return

                newpathlen = len(curpath) + 1
                if newpathlen > self.max_len:
                      return

                adjnodes = self.G[curpath[-1]].keys()
                adjnodes = [el for el in adjnodes if el not in curpath]
                random.shuffle(adjnodes)
    
                for node in adjnodes:
                      newpath = curpath + [node]
                      if node == t and newpathlen < self.max_len:
                            return

                      if (node == t) and (newpathlen == self.max_len):
                            sol.append(newpath)
                            return

                      self.get_paths_length_n(s, t, newpath, sol)

        def calc_path_weight(self, path):
                weight = 0.0
                for i in xrange(len(path)-1):
                    nodei = path[i]
                    nodej = path[i+1]
                    weight = weight + self.G[nodei][nodej]['weight']
                return weight

        def get_ordered_shortest_paths(self, s, t):
                curpath  = [s]
                paths    = []
                solution = []
                self.get_paths_length_n(s, t, curpath, paths)

                for path in paths:
                      weight = self.calc_path_weight(path)
                      solution.append((weight, path))

                solution.sort(key=lambda i: i[0])
                return solution

	# ----------------------------------------------------------------------

	def get_rnd_short_path(self):
		l = []
		while not l:
		      t = random.sample(self.G.nodes(), 1)[0]
		      while t == CLIENT_NODE:
				t = random.sample(self.G.nodes(), 1)[0]
                      s = CLIENT_NODE
                      l = self.get_ordered_shortest_paths(s, t)

                return l[0]

	# ----------------------------------------------------------------------

        def get_all_paths_length_n(self, GA, s, t, curpath, sol):
                newpathlen = len(curpath) + 1
                gmax_len = self.max_len - 1 # Analytical graph
                if newpathlen > gmax_len:
                      return

                adjnodes = GA[curpath[-1]].keys()

                adjnodes = [el for el in adjnodes if el not in curpath]
                for node in adjnodes:
                      newpath = curpath + [node]
                      if node == t and newpathlen < gmax_len:
                            return

                      if (node == t) and (newpathlen == gmax_len):
                            sol.append(newpath)
                            return

                      self.get_all_paths_length_n(GA, s, t, newpath, sol)


        def get_entropy(self):
                GA = self.G.copy()
                GA.remove_node(CLIENT_NODE)
                tmp_nodes = GA.nodes()

                pairs = itertools.permutations(tmp_nodes, 2)
                paths_length_n = []
                for pair in pairs:
                      s,t = pair
                      curpath  = [s]
                      paths    = []

                      self.get_all_paths_length_n(GA, s, t, curpath, paths)
                      if paths:
                              for path in paths:
                                    paths_length_n.append(path)

                prob_nodes = []
                for node in tmp_nodes:
                      present = 0
                      for path in paths_length_n:
                           if (node in path[1:-1]):
                               present = present + 1

                      if present > 0:
                            prob = float(present)/float(len(paths_length_n))
                            prob_nodes.append(prob)
                final_prob = []
                sum_probs = sum(prob_nodes)
                
                for prob in prob_nodes:
                      final_prob.append(prob/sum_probs)
                      
                return calc_ent(final_prob, 89)

	# ----------------------------------------------------------------------

	def get_all_paths_st_length_lambda(self, GA, vlambda, s, t, curpath, result_paths):
                newpathlen = len(curpath) + 1
                if newpathlen > vlambda:
                      return

                adjnodes = GA[curpath[-1]].keys()
                adjnodes = [el for el in adjnodes if el not in curpath]

                for node in adjnodes:
                      if node == t and newpathlen < vlambda:
                            continue

                      if (node == t) and (newpathlen == vlambda):
                            newpath = curpath + [node]  
                            result_paths.append(newpath)
                            break

                      newpath = curpath + [node]
                      self.get_all_paths_st_length_lambda(GA, vlambda, s, t, newpath, result_paths)

	def get_all_paths_length_lambda(self, GA, vlambda):
	        pairs = itertools.permutations(GA.nodes(), 2)
	        paths_length_lambda = []
	        for pair in pairs:
                      s,t             = pair
                      curpath         = [s] 
                      result_st_paths = []  

                      self.get_all_paths_st_length_lambda(GA, vlambda, s, t, curpath, result_st_paths)
                      for path in result_st_paths:
                             paths_length_lambda.append(path)

                paths_length_lambda.sort()
                return paths_length_lambda

        def get_anon_degree(self, vlambda, nnodes):
                GA = self.G.copy()
                GA.remove_node(CLIENT_NODE)
                tmp_nodes = GA.nodes()
                
                paths_len_lambda = self.get_all_paths_length_lambda(GA, vlambda)
                prob_nodes = []
                for node in tmp_nodes:
                      present = 0
                      for path in paths_len_lambda:
                            if node in path[1:-1]:
                                  present = present + 1
                      if present > 0:
                            prob = float(present)/float(len(paths_len_lambda))
                            prob_nodes.append(prob)
                psum = float(sum(prob_nodes))
                final_probs = [el/psum for el in prob_nodes]
                return calc_ent(final_probs, nnodes), len(GA.edges())

# -----------------------------------------------------------------------------
