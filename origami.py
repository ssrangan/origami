#-------------------------------------------------------------------------------
# Name:			origami.py
# Purpose:		Fuseki command line
# Author:		Larry Roberts
# Created:		September 4, 2015
#-------------------------------------------------------------------------------

from SPARQLWrapper import SPARQLWrapper, JSON
import json
import time
import csv
import sys
import argparse

sparqlq = SPARQLWrapper("http://localhost:3030/ds/query")
sparqlq.setReturnFormat(JSON)


parser = argparse.ArgumentParser()
parser.add_argument("application", type=int, help="Application number 1 - 8 (0 for list).")
parser.add_argument("start", help="Starting term")
parser.add_argument("--size", type=int, help="Size of Results (default=25).", default=25)
parser.add_argument("--hops", type=int, help="Number of hops.", default=1)
parser.add_argument("--file", help="File name to save results to.")
parser.add_argument("--filter", help="Node filters separated by commas.")
parser.add_argument("--predicates", help="Predicates separated by commas.")
parser.add_argument("--end", help="Ending term - required for applications 6, 7 and 8.")
parser.add_argument("--verbose", help="increase output verbosity",action="store_true")
args = parser.parse_args()
node1 = "<urn:sm/"+args.start+">"
node2 = ""
limitString = " limit {0}".format(args.size)
hops = args.hops

def getQueryStr(queryValue):
	global hops
	global node2
	queryStr = ""
	graphName = "<tg:hg-miner-paths>";
	if (queryValue == "4") and (hops < 2):
		hops = 2
	if (queryValue == "14") and (hops < 2):
		hops = 2
	if (queryValue == "10") and (hops > 2):
		hops = 2
	if (queryValue == "11") and (hops > 2):
		hops = 2
		
	if (queryValue == "10") or (queryValue == "11"):
		node2 = "?x"+str(hops)

	filter = ""
	if args.filter:
		arrayOfLines = args.filter.split(',')
		for nodeF in arrayOfLines:
			if len(nodeF) > 2:
				for j in range (0,hops-1):
					filter = filter + " filter (?x"+str(j+1)+" != <urn:sm/"+nodeF+">) "
				if (queryValue == "10") or (queryValue == "11"):
					filter = filter + " filter ("+node2+" != <urn:sm/"+nodeF+">) "
	
	filterP = ""
	if args.predicates:
		arrayOfLines = args.predicates.split(',')
		for nodeP in arrayOfLines:
			if len(nodeP) > 2:
				for j in range (1,hops+1):
					filterP = filterP + " filter ("
					andOn = 0;
					for i in range(0,len(arrayOfLines)):
						if (len(nodeP) > 2):
							if (andOn == 0):
								andOn = 1
							else:
								filterP = filterP + "|| "
						filterP = filterP + "?p"+str(j)+" = <urn:sm/"+nodeP+"> "
					filterP = filterP + ") "
	
	queryStr = "select ?p1 ?x1";
	if (hops > 1 ):
		for i in range(2,hops):
			queryStr += " ?p"+str(i)+" ?x"+str(i)
			
	if (queryValue == "10") or (queryValue == "11"):
		if (hops > 1 ):
			queryStr += " ?p"+str(hops)+" "+node2
	else:
		queryStr += " ?p"+str(hops)
		
	if (queryValue == "11"):
		queryStr += " ?avgScore where { "+node1+" ?p1 ?x1 . "
	else:
		queryStr += " ?avgScore where { graph "+graphName+" { "+node1+" ?p1 ?x1}. "
		
	if (hops > 1 ):
		for i in range(2,hops):
			if (queryValue == "11"):
				queryStr += " ?x"+str(i-1)+" ?p"+str(i)+" ?x"+str(i)+" . "
			else:
				queryStr += "graph "+graphName+" { ?x"+str(i-1)+" ?p"+str(i)+" ?x"+str(i)+"}. "
				
	if ((queryValue != "10") and (queryValue != "11")) or (hops > 1 ): 
		if (queryValue == "11"):
			queryStr += " ?x"+str(hops-1)+" ?p"+str(hops)+" "+node2+" . "
		else:
			queryStr += "graph "+graphName+" { ?x"+str(hops-1)+" ?p"+str(hops)+" "+node2+"}. "
	
	if (queryValue != "14"):
		for i in range (1,hops+1):
			if (i==1):
				queryStr += "graph <tg:sp-cnt> {"+node1+" ?p"+str(i)+" ?sp_cnt"+str(i)+"}. "
			else:
				queryStr += "graph <tg:sp-cnt> {?x"+str(i-1)+" ?p"+str(i)+" ?sp_cnt"+str(i)+"}. "
			if (i==hops):
				queryStr += "graph <tg:po-cnt> {?p"+str(i)+" "+node2+" ?po_cnt"+str(i)+"}. "
			else:
				queryStr += "graph <tg:po-cnt> {?p"+str(i)+" ?x"+str(i)+" ?po_cnt"+str(i)+"}. "
			queryStr += "BIND(((1/?sp_cnt"+str(i)+")*(1/?po_cnt"+str(i)+")) AS ?score"+str(i)+") . "
		queryStr = queryStr +"BIND((?score1"
		if (hops > 1 ):
			for i in range(2,hops+1):
				queryStr += "+?score"+str(i)
		queryStr = queryStr +")/"+str(hops)+" AS ?avgScore) . "
	else:
		# is query 14
		for i in range(1,hops+1):
			queryStr += "graph <tg:predweight>  {?p"+str(i)+" <urn:sm/weight>  ?score"+str(i)+"}. "
		queryStr = queryStr +"BIND((?score1"
		if (hops > 1 ):
			for i in range(2,hops+1):
				queryStr += "+?score"+str(i)
		queryStr = queryStr +") AS ?avgScore) . "
	
	if (hops > 1 ):
		queryStr = queryStr +" filter ("
		for i in range(1,hops):
			queryStr = queryStr +"("+node1+" != ?x"+str(i)+" ) && "
		for i in range(1,hops):
			for j in range (i+1,hops):
				queryStr = queryStr +"(?x"+str(i)+" != ?x"+str(j)+" ) && "
			if (i < hops-1):
				queryStr = queryStr +"(?x"+str(i)+" != "+node2+" ) && "
			else:
				queryStr = queryStr +"(?x"+str(i)+" != "+node2+" ) "
		queryStr = queryStr +") "

	queryStr = queryStr + filter
	queryStr = queryStr + filterP
	
	queryStr = queryStr +" } order by desc(?avgScore) "+limitString

	return queryStr;

def main():
	global node2

	if args.application == 6 or args.application == 7 or args.application == 8:
		if args.end:
			node2 = "<urn:sm/"+args.end+">"
		else:
			print "Ending term required for applications 6, 7 and 8"
			quit()

	if args.application == 0:
		print ("1 = Specific Reasoning on Graph")
		print ("2 = Reasoning on Whole Graph")
		print ("3 = Pattern Similarity - Whole Graph")
		print ("4 = Browse Selected Triples")
		print ("5 = Browse All Triples")
		print ("6 = Paths")
		print ("7 = Context Terms")
		print ("8 = Paths by Predicate Weight")
		
	elif args.application == 1:
		if args.verbose:
			print("Application 1 Specific Reasoning on Graph")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = "select ?similar (count(?s) as ?count) where {"
		queryStr = queryStr +"graph <tg:hg-miner-paths> {?s ?p1 "+node1+" } . "
		queryStr = queryStr +"graph <tg:hg-miner-paths> {?s ?p2 ?similar } . "
		queryStr = queryStr +" filter ("+node1+" != ?similar)"
		queryStr = queryStr +"} group by ?similar order by desc(?count) "+limitString
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				if (len(result)> 1):
					print(result["similar"]["value"]),
					print(', '+str(result["count"]["value"]))
					
	elif args.application == 2:
		if args.verbose:
			print("Application 2 Reasoning on Whole Graph")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = "select ?similar (count(?s) as ?count) where {"
		queryStr = queryStr +" ?s ?p1 "+node1+" . "
		queryStr = queryStr +" ?s ?p2 ?similar . "
		queryStr = queryStr +" filter ("+node1+" != ?similar)"
		queryStr = queryStr +"} group by ?similar order by desc(?count) "+limitString
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				if (len(result)> 1):
					print(result["similar"]["value"]),
					print(', '+str(result["count"]["value"]))
					
	elif args.application == 3:
		if args.verbose:
			print("Application 3 Pattern Similarity - Whole Graph")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = "select ?similar (count(?p) as ?count) where {"
		queryStr = queryStr +" "+node1+" ?p ?o   . "
		queryStr = queryStr +" ?similar ?p ?o  . "
		queryStr = queryStr +" filter ("+node1+" != ?similar)"
		queryStr = queryStr +"} group by ?similar order by desc(?count) "+limitString
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				if (len(result)> 1):
					print(result["similar"]["value"]),
					print(', '+str(result["count"]["value"]))
		
	elif args.application == 4:
		if args.verbose:
			print("Application 4 Browse Selected Triples")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = getQueryStr("10")
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				lineCt = 0
				for key in result.keys():
					if lineCt > 0:
						print ',',
					print key+":"+result[key]["value"],
					lineCt += 1
				print ""
		
	elif args.application == 5:
		if args.verbose:
			print("Application 5 Browse All Triples")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = getQueryStr("11")
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				lineCt = 0
				for key in result.keys():
					if lineCt > 0:
						print ',',
					print key+":"+result[key]["value"],
					lineCt += 1
				print ""
		
	elif args.application == 6:
		if args.verbose:
			print("Application 6 Paths")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = getQueryStr("4")
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				lineCt = 0
				for key in result.keys():
					if lineCt > 0:
						print ',',
					print key+":"+result[key]["value"],
					lineCt += 1
				print ""
		
	elif args.application == 7:
		if args.verbose:
			print("Application 7 Context Terms")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = "select ?incontext ?cnt where {{"
		queryStr = queryStr +"select ?incontext (count(*) as ?cnt) {{"
		queryStr = queryStr +"select distinct ?incontext ("+node1+" as ?term) {{"
		queryStr = queryStr +"select (?hop1 as ?incontext) {graph <tg:hg-miner-paths>{"+node1+" ?p1 ?hop1.}}}"
		queryStr = queryStr +" union { "
		queryStr = queryStr +"select (?hop2 as ?incontext) {graph <tg:hg-miner-paths>{"+node1+" ?p1 ?hop1. "
		queryStr = queryStr +"?hop1 ?p2 ?hop2 . }}}}}"
		queryStr = queryStr +" union { "
		queryStr = queryStr +"select distinct ?incontext ("+node2+" as ?term) {{ "
		queryStr = queryStr +"select (?hop1 as ?incontext) {graph <tg:hg-miner-paths>{"+node2+" ?p1 ?hop1.}}}"
		queryStr = queryStr +" union { "
		queryStr = queryStr +"select (?hop2 as ?incontext) {graph <tg:hg-miner-paths>{"+node2+" ?p1 ?hop1. "
		queryStr = queryStr +"?hop1 ?p2 ?hop2 . }}}}}} "
		queryStr = queryStr +"group by ?incontext} filter (?cnt=2) } "+limitString
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				if (len(result)> 1):
					print(result["incontext"]["value"])
			
	elif args.application == 8:
		if args.verbose:
			print("Application 8 Paths by Predicate Weight")
			print("Search Term = "+args.start)
			print("size = {0} ".format(args.size))
		queryStr = getQueryStr("14")
		if args.verbose:
			print(queryStr)
		sparqlq.setQuery(queryStr)
		ret = sparqlq.queryAndConvert()
		if args.file:
			qfile = open(args.file,'w')
			json.dump(ret,qfile)
			qfile.close()
		else:
			for result in ret["results"]["bindings"]:
				lineCt = 0
				for key in result.keys():
					if lineCt > 0:
						print ',',
					print key+":"+result[key]["value"],
					lineCt += 1
				print ""
	
if __name__ == '__main__':
    main()