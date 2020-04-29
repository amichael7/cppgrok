#!/usr/bin/env python3

'''
I'm not exactly sure what I'm looking for with this project,
It could be good, it could be a dud.
'''

import os
import re
from pprint import pprint

PATH = 'WebRTC'
FTYPE_REPORTING_THRESHOLD = 0.01	# file type must be over 5%

class DirStructure:
	def __init__(self, path):
		def dir_walk(path):
			files, folders = [],[]
			# r=root, d=dirs, f=files
			for r,d,f in os.walk(path):
				for file in f:
					files.append(os.path.join(r, file))
				for folder in d:
					folders.append(os.path.join(r, folder))
			return files,folders

		self.files, self.folders = dir_walk(path) 

	def summarize(self):
		def get_extension(file):
			fname = list(filter(None,f.split('\\')[-1].split('.')))
			return fname[-1] if len(fname)>1 else None

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

		for f in self.files:
			ext = get_extension(f)
			print('[filename]:',f)
			with open(f) as file:
				file = file.read()
				if ext == 'cc':		self.parse_cpp(file);break
				if ext == 'h':		self.parse_h(file)



	def parse_cpp(self,file):
		comments = []
		if '/*' in file:
			cmts = re.findall(r'(/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)|(//.*)', file)
			for cmt in cmts:
				remove_comment_markers = lambda s: s.replace('/','').replace('*','').replace('\n','')
				cmt = [remove_comment_markers(c) for c in cmt]
				cmt = ''.join([c.strip() for c in list(filter(None,cmt)) if c!=' '])
				cmt = ' '.join(cmt.split())	# clean up whitepace
				comments.append(cmt)

		# for each comment find the next nearest line of code
			# if comment share a code reference, combine them with a newline
		# if comment is at the top ignore it
		# if comment is on a code line get the code on the line
			# But, if it is attached to an ending brace, get the line prior to the beginning brace
		for c in comments:
			print(c)

		includes = []
		for ln in file.split('\n'):
			if '#include' in ln:
				includes.append(ln.split('#include ')[-1].replace('\"',''))

		for i in includes:
			print(i)

	def parse_h(self,file):
		print(file)




	# reverse search includes

	# search comments




def main():
	structure = DirStructure(PATH)
	structure.summarize()

if __name__ == '__main__':
	main()