#!/usr/bin/python

# Generate a Freemind mindmap from filesystem path

import os

sourceDir = os.path.normpath("src_html");
webRoot = "http://127.0.0.1:8000/src_html"
outputMM = open("Content.mm","w") 

def map_start():
	outputMM.write("<map version=\"1.0.0\">")
	
def map_end():
	outputMM.write("</map>")

def node_start(nodeText, nodeLink, folded):
	outputMM.write("<node ID=\"" + os.urandom(8).hex() + \
		"\" TEXT=\"" + nodeText + "\" FOLDED=\"" + str(folded).lower() + "\" LINK=\"" + nodeLink + "\">");

def node_end():
	outputMM.write("</node>\n") 

def traverse_directory(dirpath):
          
   for direntry in sorted(os.listdir(dirpath)):
       
       #global node replace
       direntry = direntry.replace("&", "&amp;");

       curdirentrypath = dirpath + "/" + direntry;
       webLink = curdirentrypath.replace(sourceDir, webRoot);
       
       #weblink replace
       webLink = webLink.replace(" ", "%20");
       webLink = webLink.replace("#", "%23");
                                                                                      
       node_start(direntry, webLink, True); 
       
       if os.path.isdir(curdirentrypath):
          traverse_directory(curdirentrypath);
          node_end();
       else:
       	  node_end();

def main():
   
   map_start();
   
   node_start("Content", webRoot, False);
   
   traverse_directory(sourceDir);
   
   node_end();
   
   map_end();
   
   outputMM.close();

if __name__=='__main__':

    main()
