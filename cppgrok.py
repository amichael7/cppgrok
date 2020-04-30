#!/usr/bin/env python3

'''
I'm not exactly sure what I'm looking for with this project,
It could be good, it could be a dud.
'''

import os
import re
from pprint import pprint
from enum import Enum
import networkx as nx
import matplotlib.pyplot as plt

ROOT = '../webrtc/'
FTYPE_REPORTING_THRESHOLD = 0.01	# file type must be over 5%
DEBUG = os.getenv('DEBUG')

class CppComment:
	class Type(Enum):
		INLINE=1
		MULTILINE=2
		SINGLE_LINE=3

	def __init__(self,cmt_type,line,ref,cmt):
		self.type = cmt_type
		self.line = line
		self.ref = ref
		self.comment = cmt


class CppSrc:
	def __init__(self,src):
		self.src = src
		self.comments = []

	def decomment(self):
		'''
		Decomment src and store comments in the object

		Comment Rules:
			- for each comment find the next nearest line of code
				- if comment share a code reference, combine them with a newline
			- if comment is at the top ignore it
			- if comment is on a code line get the code on the line
				- but, if it is attached to an ending brace, get the line prior to the beginning brace
		'''
		src = self.src.split('\n')
		idx = 0
		line_n = 1
		while idx < len(src):
			ln = src[idx]

			if '/*' in ln and '*/' in ln:
				start,end = ln.find('/*'),ln.find('*/')+2
				src[idx] = ln[:start]+ln[end:]
				ref = ln.strip()
				line = line_n
				cmt = ln[start+2:end-2].strip()
				comment = CppComment(CppComment.Type.INLINE,line,ref,cmt)
				self.comments.append(comment)

			elif '//' in ln:
				ref, cmt = tuple(map(str.strip, ln.split('//',maxsplit=1)))
				line = None					
				# assign ref
				if len(ref) == 0:
					# single line cmt referring to code line below
					while idx < len(src):
						ln = src[idx].strip()
						if ln[:2] not in ['//','/*'] and len(ln)>0:
							ref = None if idx==0 else ln
							line = line_n
							break
						elif ln[:2] == '//':
							tmp = ln.split('//',maxsplit=1)[1].strip()
							cmt += ' '+tmp if len(tmp)>0 else '\n'
						del src[idx]
						line_n += 1
				elif ref[-1] == '}':
					# if ref is to a closing bracket: backtrack to match the bracket
					src[idx] = ref
					i = 0
					bracket_level = 0
					while idx-i > 0:
						search_ln = src[idx-i]
						if '}' in search_ln:	bracket_level += 1
						if '{' in search_ln:	bracket_level -= 1
						if bracket_level == 0:
							ref = search_ln+(' ... '+ref if i>0 else '')
							line = line_n-i
							break
						i += 1
				comment = CppComment(CppComment.Type.MULTILINE,line,ref,cmt)
				self.comments.append(comment)

			elif '/*' in ln:
				ref, cmt = tuple(map(str.strip, ln.split('/*',maxsplit=1)))
				line = None
				del src[idx]
				line_n += 1
				while  idx < len(src):
					ln = src[idx]
					if '*/' in ln:
						tmp = tuple(map(str.strip, ln.split('*/',maxsplit=1)))
						cmt += tmp[0].replace('/*','')
						if len(tmp[1]) == 0:
							del src[idx]
							line_n += 1
						else:
							src[idx] = tmp[1]
						break
					else:
						ln = ln.replace('/*','').strip()
						if len(ln) > 0:
							if ln[0] == '*':
								ln = ln[1:].strip()
							cmt += ' '+ln if len(ln)>0 else '\n'
						del src[idx]
						line_n += 1

				# set ref as either line before or line after
				if idx == 0 or idx == len(src)-1:
					ref = None
					line = idx
				else:
					# set ref to line before if it ends with bracket
					ln = src[idx-1].strip()
					if len(ln) != 0 and ln[-1] == '{':
						ref = ln + ' ... }'
						line = line_n-1
					elif idx < len(src)-1:
						ref = src[idx+1].strip()
						line = line_n+1
				comment = CppComment(CppComment.Type.SINGLE_LINE,line,ref,cmt)
				self.comments.append(comment)
			idx+=1
			line_n+=1
		# decomment the source
		self.src = '\n'.join(src)


	def dependencies(self):
		if hasattr(self, 'deps'):
			return self.deps
		includes = []
		for ln in self.src.split('\n'):
			if '#include' in ln:
				includes.append(ln.split('#include ')[-1].replace('\"',''))
		if DEBUG:
			if len(includes)>0:
				print('[INCLUDES]:')
				for i in includes:
					print('  ',i)
		self.deps = includes
		return self.deps
		

	def parse(self):
		self.decomment()
		self.dependencies()
		


class DependencyGraph:
	def __init__(self, files):
		# the nodes are file path strings
		self.G = nx.DiGraph()
		self.G.add_nodes_from(files)


	def add_dependency(self,caller,dependency):
		# `caller` depends on `dependency`
		'''
		TODO: color nodes that aren't part of main code base
		'''
		c,d = caller, dependency
		if c not in self.G.nodes:
			self.G.add_node(c)
		if dependency not in self.G.nodes:
			self.G.add_node(d)
		self.G.add_edge(c,d)

	def show(self, file):
		def _get_deps(node,subgraph):
			subgraph.add_node(node)
			for child in self.G.successors(node):
				subgraph.add_edge(node,child)
				_get_deps(child,subgraph)
				

		subgraph = nx.DiGraph()
		_get_deps(file,subgraph)
		nx.draw(subgraph,with_labels=True)
		plt.show()


def get_extension(fname):
	fname = list(filter(None,fname.split('\\')[-1].split('.')))
	return fname[-1] if len(fname)>1 else None

class DirStructure:
	def __init__(self, path):
		def dir_walk(path):
			files, folders = [],[]
			# r=root, d=dirs, f=files
			for r,d,f in os.walk(path):
				for file in f:
					files.append(os.path.join(r, file).replace(ROOT,''))
				for folder in d:
					folders.append(os.path.join(r, folder).replace(ROOT,''))
			return files,folders

		self.files, self.folders = dir_walk(path)



	def summarize(self):
		extensions = {}
		for f in self.files:
			ext = get_extension(f)
			if ext is None: continue
			if ext in extensions:
				extensions[ext] += 1
			else:
				extensions[ext] = 1

		n_code_files = sum(extensions.values())
		extensions = {k: v for k, v in sorted(extensions.items(), key=lambda x: x[1],reverse=True) if v > FTYPE_REPORTING_THRESHOLD*n_code_files}
		print(extensions)


		dep_graph = DependencyGraph(self.files)
		for f in self.files:
			ext = get_extension(f)
			if DEBUG: print('\n[filename]:',f)
			
			if ext in ['cc','cpp','h']:
				with open(os.path.join(ROOT,f)) as file:
					file = file.read()
				cpp = CppSrc(file)
				cpp.parse()
				for dep in cpp.dependencies():
					if f[0]=='<' and '>' in f: 		continue
					if dep[0]=='<' and '>' in dep: 	continue
					dep_graph.add_dependency(f,dep)

		dep_graph.show('examples/peerconnection/client/linux/main.cc')






	# reverse search includes

	# search comments




def main():
	structure = DirStructure(ROOT)
	structure.summarize()

if __name__ == '__main__':
	main()