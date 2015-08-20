import os
import unicodecsv
import json
from lxml import etree
import re
import urllib
import sys
from rdf_from_csvw import CSVWtoRDF
from rdflib import Graph

#Template for the CSVW to use
#Property URL is incorrect
template = {
	"@id": None,
	"@context": ["http://www.w3.org/ns/csvw",
        {"@language": "en",
        "dcterms":"http://purl.org/dc/terms/",
        "xsd": "http://www.w3.org/2001/XMLSchema#"
        }],
    "delimiter": ",",    
    "@type": ["Table"],
    "tableSchema":{
    	"columns": [
    		{"name": "o-tmf",
    			"title": "o-tmf",
    			"dcterms:description": "Creator of original file",
    			"dataType": "xsd:string",
    			"required": "true",
    			"propertyUrl": "null"
    		},
    		{"name": "creationtool",
    			"title": "creationtool",
    			"dcterms:description": "Tool used to create file",
    			"dataType": "xsd:string",
    			"required": "true",
    			"propertyUrl": "null"
    		},
    		{"name": "creationtoolversion",
    			"title": "creationtoolversion",
    			"dcterms:description": "Version of the creation tool",
    			"dataType": "xsd:string",
    			"required": "true",
    			"propertyUrl": "null"
    		},
    		{"name": "segtype",
    			"title": "segtype",
    			"dcterms:description": "Type of the segment",
    			"dataType": "xsd:string",
    			"required": "true",
    			"propertyUrl": "null"
    		},
    		{"name": "datatype",
    			"title": "datatype",
    			"dcterms:description": "Type of the data",
    			"dataType": "xsd:string",
    			"required": "true",
    			"propertyUrl": "null"
    		},
    		{"name": "adminlang",
    			"title": "adminlang",
    			"dcterms:description": "Administrative language ",
    			"dataType": "xsd:string",
    			"required": "true",
    			"propertyUrl": "null"
    		},
    		{"name": "srclang",
    			"title": "srclang",
    			"dcterms:description": "Source language",
    			"dataType": "xsd:string",
    			"required": "true",
    			"propertyUrl": "null"
    		},
	    	{"name": "prop",
	    		"title": "prop",
	    		"dcterms:description": "Document type",
	    		"dataType": "xsd:string",
	    		"required": "true",
	    		"propertyUrl": "null"
	    		},
	    	{"name": "tuv",
	    		"title": "tuv",
	    		"dcterms:description": "Language of the segment",
	    		"dataType": "xsd:string",
	    		"required": "true",
	    		"propertyUrl": "null"
	    		},
	    	{"name": "seg",
	    		"title": "seg",
	    		"dcterms:description": "Sentences in various languages",
	    		"dataType": "xsd:string",
	    		"required": "true",
	    		"propertyUrl": "null"
	    		},				
	],
	"primaryKey":["seg", "prop"]
    }
}

#Convert an input TMX file to a CSV file, and a corresponding CSVW file
def TMXToCSVW(input, output = None):
	csvName = output
	csvwName = output
	fileName = os.path.splitext(input)[0] #file name without extension

	#if output is empty, use the same input name with a different extension
	if output == None:
		csvName = "{0}.csv".format(fileName)
		csvwName = "{0}.csv.csvw".format(fileName)

	#parse the document using LXML
	doc = etree.parse(input).getroot()
 
	tus = doc.findall("tu")
	
	csv_header = ("header.o-tmf", "header.creationtool", "header.creationtoolversion", "header.segtype", 
		"header.datatype", "header.adminlang", "header.srclang", "prop.type", "prop.value", 
		"lang", "seg")

	with open(csvName, "w") as f:
		writer = unicodecsv.writer(f, encoding="utf-8")
		writer.writerow(csv_header)
		
		otmf = doc.xpath("//header/@o-tmf")[0]
		creationtool = doc.xpath("//header/@creationtool")[0]
		creationtoolversion = doc.xpath("//header/@creationtoolversion")[0]
		segtype = doc.xpath("//header/@segtype")[0]
		datatype = doc.xpath("//header/@datatype")[0]
		adminlang = doc.xpath("//header/@adminlang")[0]
		srclang = doc.xpath("//header/@srclang")[0]
		
		for tu in doc.xpath("//tu"):
			propType = tu.xpath("./prop/@type")[0]
			propVal = tu.xpath("./prop")[0].text
			
			for tuv in tu.xpath("./tuv"):
				lang = tuv.xpath("./@lang")[0]
				seg = tuv.xpath("./seg")[0].text

				row = otmf, creationtool, creationtoolversion, segtype, datatype, \
					adminlang, srclang, propType, propVal, lang, seg

				writer.writerow(row)

	csvw = template
	head,tail = os.path.split(fileName)
	
	csvw["@id"] = "http://mt.peep.ie/download/{0}.csv".format(tail)			
	csvw["@url"] = "http://mt.peep.ie/download/{0}.csv".format(tail)
	csvw["tableSchema"]["aboutUrl"] = "http://mt.peep.ie/download/{0}.csv/row.{{_row}}".format(tail)


	with open(csvwName, "w") as f:
		json.dump(csvw, f, indent = 2)		

	return (csvName, csvwName)

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print "Usage: python dgt_converter_lxml.py <path to directory containing tmx files>"
		exit(2)

	g = Graph()
	rdfConverter = CSVWtoRDF(g)
	curDir = os.path.dirname(os.path.abspath(__file__))
	root = os.path.join( curDir , sys.argv[1] )
	for subdir, dirs, files in os.walk(root):
		for name in files:
			ext = ""
			try: 
				ext = name.split(".")[1]
			except IndexError:
				pass
			if ext == "tmx":
				print "Converting " + name
				relFilePath = os.path.join(subdir, name)
				filePath = os.path.join(root, relFilePath)
				(csvName, csvwName) = TMXToCSVW(filePath)
				rdfConverter.loadCSVW(csvName)
				rdfConverter.writeToFile("{0}.rdf".format(csvName))