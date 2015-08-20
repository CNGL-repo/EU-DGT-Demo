from rdflib import Graph, Literal, URIRef, Namespace, XSD, RDF, RDFS, BNode
import csv
import urllib
import re
from operator import itemgetter
import sys


MAX_LINES_TO_PROCESS = -1

CSVW = Namespace("http://www.w3.org/ns/csvw#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DC = Namespace("http://purl.org/dc/terms/")


class CSVWtoRDF:
    '''
    Provides operation to add triples extracted from CSV files using an implementation of a subset of the
    CSV on the Web standard to a provided Graph.

    Assumptions on the input files:
     * CSVW meta file is provided as JSON-LD serialisation
     * if not specified otherwise, loadCSW() looks for the CSVW meta file for '/path/to/input.csv' at
        '/path/to/input.csv.csvw'
     * the CSVW meta description RDF graph contains exactly one resource where the a suffix of the IRI is identical
        to the filename of the provided CSV input and this resource is the 'root' of the CSVW mapping description
        (otherwise, provide the resource name explicitly using the mappingResouceIRI parameter of the constructor)
    * only the CSVW datatype definitins 'anyURI', 'string' and 'double' are supported at the moment

    creators: Brian Walshe (Trinity College Dublin, KDEG)
              Markus Ackermann (University Leipzig, AKSW)
    '''
    def __init__(self, rdfGraph):
        self.graph = rdfGraph
      


    def loadCSVW(self, csvFilename, csvwFilename=None, mappingResourceIRI=None):

        if csvwFilename == None:
            csvwFilename = csvFilename + ".csvw"

        self.graph.parse(csvwFilename, format='json-ld')
        self.graph.serialize(open("metadata.rdf", "w"), "xml")
       

        #for prefix, expansion in csvwLD.namespaces():
        #    self.graph.bind(prefix, expansion, override=False)


        #if mappingResourceIRI == None:
        #    mappingResource = self._findMappingResource(csvwLD, csvFilename)
        #else:
        #    mappingResource = URIRef(str(mappingResourceIRI))

        #if next(csvwLD.predicate_objects(mappingResource), 'NA') == 'NA':
        #    raise RuntimeError("mapping description %s does not exist"%mappingResource)

        #def anyObject(subject=None, property=None):
        #    #print "(%s, %s)"%(subject, object)
        #    return next(csvwLD.objects(subject, property) )

        tableNode = self.graph.value(predicate=RDF.type, object=CSVW.Table)

        delim =  self.graph.value(tableNode, CSVW.delimiter)
        print "delimiter = %s"%delim
        csvFile = open(csvFilename, "r")
        csvData = csv.reader(csvFile, delimiter=str(delim))

        schemaRes = self.graph.value(tableNode, CSVW.tableSchema)
       
        

        #tableNode = URIRef("%s#table" % csvFilename)
        #self.graph.add((tableNode, RDF.type, CSVW.Table))

        dcatNode = BNode()
        self.graph.add((dcatNode, RDF.type, DCAT.Distribution))
        self.graph.add((dcatNode, DCAT.downloadURL, URIRef(csvFilename)))

        self.graph.add((tableNode, DCAT.distribution, dcatNode))

        mappedColumnsNames = []
        datatypeForColumn = dict()
        propertyForColumn = dict()
        columnList =  self.graph.value(schemaRes, CSVW.column)
        
        while columnList != None and self.graph.value(columnList, RDF.first)!=None:
            column = self.graph.value(columnList, RDF.first)
            columnName = self.graph.value(column, CSVW.name)
            print "doing colunm %s"%columnName
            propertyRes = self.graph.value(column, CSVW.propertyUrl)
            self.graph.add((propertyRes, RDF.type, RDF.Property))
            if self.graph.value(column, CSVW.title) != None:
               self.graph.add((propertyRes, RDFS.label, self.graph.value(column, CSVW.title)))

            if self.graph.value(column, DC.description) != None:
               self.graph.add((propertyRes, DC.description, self.graph.value(column, DC.description)))
            mappedColumnsNames += columnName
            datatypeForColumn[str(columnName)] = str(self.graph.value(column, CSVW.datatype))
            propertyForColumn[str(columnName)] = propertyRes
            columnList = self.graph.value(columnList, RDF.rest)

        print propertyForColumn.keys()

        urlTemplate = self.graph.value(schemaRes, CSVW.aboutUrl)
        groups = re.match("^(.*?)\{([A-Za-z0-9\-_]+)\}(.*)$", urlTemplate)
        pre = groups.group(1)
        post = groups.group(3)
        nameCol = groups.group(2)
        

        csvHeader = csvData.next()
        cellname2Index = self._cellToIndexMapping(csvHeader)
        idIndex=-1
        if nameCol!="_row":
            idIndex = csvHeader.index(nameCol)

        linesRead = 0
        for line in csvData:
            linesRead += 1
            id_fragment=str(linesRead)
            if idIndex!=-1:
                id_fragment = urllib.quote_plus(line[idIndex])
            subject = URIRef("%s%s%s" % (pre, id_fragment, post))

            self.graph.add((tableNode, CSVW.row, subject))
            self.graph.add((subject, RDF.type, CSVW.Row))
            for cellname, i in cellname2Index.items():
                if cellname not in propertyForColumn.keys(): 
                   #print "no hit for (%s)"%cellname
                   continue
                predicate = propertyForColumn[cellname]
                obj = self.makeObject(datatypeForColumn[cellname], line[i])
                self.graph.add((subject, predicate, obj))
            if(MAX_LINES_TO_PROCESS > 0 and linesRead >= MAX_LINES_TO_PROCESS): break



    #def _findMappingResource(self, csvwLD, csvFileName):
    #        def mappingResFilter(subject):
    #            return isinstance(subject, URIRef) and str(subject).endswith(csvFileName)#

#            mappingCandidates = set(filter(mappingResFilter, map(itemgetter(0), csvwLD)))

#            if not mappingCandidates:
#                raise RuntimeError("unable to find mapping description")
#            else:
#                if len(mappingCandidates) > 1:
#                   raise RuntimeError("more than one mapping descrption candidate")

#            return next(iter(mappingCandidates))

    def _cellToIndexMapping(self, csvHeader):
        return dict(zip([x.strip() for x in csvHeader], range(0, len(csvHeader))))
#
#    def _sanitizeSID(self, sid):
#        return sid.replace('_', '-')

    def makeObject(self, datatypeStr, val):
        if datatypeStr == "anyURI":
            return URIRef(val)
        else:
            return Literal(val, datatype=datatypeStr)

    def printN3(self):
        print(self.graph.serialize(format='n3'))

    def writeToFile(self, fileName, format="xml"):
        self.graph.serialize(open(fileName, "w"), format)


if __name__ == "__main__":
    g = Graph()

    converter = CSVWtoRDF(g)
    converter.loadCSVW(sys.argv[1])
   
    converter.writeToFile("%s.rdf"%sys.argv[1])
