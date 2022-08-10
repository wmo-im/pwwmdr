import requests
from lxml import etree
import json
import os
import shutil


def getMetadataFormats(output,endpoint="https://oscar.wmo.int:443/oai/provider"):
    response = requests.get(endpoint, params = { "verb": "ListMetadataFormats"})
    response.text
    f = open(output,"w")
    f.write(response.text)
    f.close()
    tree = etree.parse(output)
    return tree.getroot()


# %%
def getRecord(identifier,output_dir,metadata_prefix = "wmdr",endpoint="https://oscar.wmo.int:443/oai/provider"):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    record_file = "%s/%s.xml" % (output_dir,identifier)
    response = requests.get(endpoint,params={"verb":"GetRecord","metadataPrefix":metadata_prefix,"identifier":identifier})
    f = open(record_file,"w")
    f.write(response.text)
    f.close()
    tree = etree.parse(record_file)
    root = tree.getroot()
    el = root.find("{http://www.openarchives.org/OAI/2.0/}GetRecord/{http://www.openarchives.org/OAI/2.0/}record/{http://www.openarchives.org/OAI/2.0/}metadata/{http://def.wmo.int/wmdr/2017}WIGOSMetadataRecord")
    if el is None:
        print("Warning: WIGOSMetadataRecord tag not found in document")
        return None
    el.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = "http://def.wmo.int/wmdr/2017 http://schemas.wmo.int/wmdr/1.0RC9/wmdr.xsd"
    et = etree.ElementTree(el)
    filename = "%s/%s.xml" % (output_dir, identifier)
    et.write(filename, pretty_print=True)
    return el

# %%

def getIdentifiersFirstPage(output,endpoint="https://oscar.wmo.int:443/oai/provider",metadata_prefix="wmdr",set_spec=None):
    response = requests.get(endpoint, params = { "verb": "ListIdentifiers", "metadataPrefix": metadata_prefix, "set": set_spec})
    f = open(output,"w")
    f.write(response.text)
    f.close()
    tree = etree.parse(output)
    root = tree.getroot()
    list_identifiers = root.find("{http://www.openarchives.org/OAI/2.0/}ListIdentifiers")
    identifiers = []
    for header in list_identifiers.iter("{http://www.openarchives.org/OAI/2.0/}header"):
        identifiers.append({
            "identifier": header.find("{http://www.openarchives.org/OAI/2.0/}identifier").text,
            "datestamp" : header.find("{http://www.openarchives.org/OAI/2.0/}datestamp").text,
            "setSpec" : header.find("{http://www.openarchives.org/OAI/2.0/}setSpec").text if header.find("{http://www.openarchives.org/OAI/2.0/}setSpec") is not None else None
        })
    # [x.find("{http://www.openarchives.org/OAI/2.0/}identifier").text for x in identifiers if "status" not in x.attrib]
    resumptionToken = list_identifiers.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken")
    return identifiers, resumptionToken.text, int(resumptionToken.attrib["completeListSize"]), int(resumptionToken.attrib["cursor"])

def resumeGetIdentifiers(resumption_token,output,endpoint="https://oscar.wmo.int:443/oai/provider"):
    response = requests.get(endpoint,params={"verb":"ListIdentifiers","resumptionToken":resumption_token})
    f = open(output,"w")
    f.write(response.text)
    f.close()
    tree = etree.parse(output)
    root = tree.getroot()
    list_identifiers = root.find("{http://www.openarchives.org/OAI/2.0/}ListIdentifiers")
    identifiers = []
    for header in list_identifiers.iter("{http://www.openarchives.org/OAI/2.0/}header"):
        identifiers.append({
            "identifier": header.find("{http://www.openarchives.org/OAI/2.0/}identifier").text,
            "datestamp" : header.find("{http://www.openarchives.org/OAI/2.0/}datestamp").text,
            "setSpec" : header.find("{http://www.openarchives.org/OAI/2.0/}setSpec").text if header.find("{http://www.openarchives.org/OAI/2.0/}setSpec") is not None else None
        })
    resumption_token = list_identifiers.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken")
    return identifiers, int(resumption_token.attrib["cursor"]), resumption_token.text

def getIdentifiers(output,output_all,output_dir=None,endpoint="https://oscar.wmo.int:443/oai/provider",max_pages=500,metadata_prefix="wmdr",set_spec=None):
    identifiers, resumption_token, completeListSize, cursor = getIdentifiersFirstPage(output=output,endpoint=endpoint,metadata_prefix=metadata_prefix,set_spec=set_spec)
    page = 0
    if output_dir is not None:
        new_file = "%s/identifiers_%i.xml" % (output_dir,page)
        shutil.copyfile(output,new_file)
    while cursor < completeListSize and page < max_pages and resumption_token is not None:
        page = page + 1
        more_identifiers, cursor, resumption_token = resumeGetIdentifiers(resumption_token,output=output,endpoint=endpoint)
        identifiers.extend(more_identifiers)
        print("cursor: %i, page: %i, completeListSize: %i" % (cursor, page, completeListSize))
        if output_dir is not None:
            new_file = "%s/identifiers_%i.xml" % (output_dir,page)
            shutil.copyfile(output,new_file)
    f = open(output_all,"w")
    json.dump(identifiers,f,indent=2)
    f.close()
    return identifiers

def getRecordsFromIdentifiers(identifiers,output_dir,metadata_prefix="wmdr",endpoint="https://oscar.wmo.int:443/oai/provider"):
    for identifier in identifiers:
        getRecord(identifier["identifier"],output_dir=output_dir,metadata_prefix=metadata_prefix,endpoint=endpoint)

def getRecordsFirstPage(output,endpoint="https://oscar.wmo.int:443/oai/provider",metadata_prefix="wmdr",set_spec=None,output_dir=None):
    params={"verb":"ListRecords","metadataPrefix":metadata_prefix}
    if set_spec is not None:
        params["set"] = set_spec
    response = requests.get(endpoint,params=params)
    f = open(output,"w")
    f.write(response.text)
    f.close()
    tree = etree.parse(output)
    root = tree.getroot()
    root.tag
    list_records = root.find("{http://www.openarchives.org/OAI/2.0/}ListRecords")
    records = []
    for record in list_records.iter("{http://www.openarchives.org/OAI/2.0/}record"):
        identifier = record.find("{http://www.openarchives.org/OAI/2.0/}header/{http://www.openarchives.org/OAI/2.0/}identifier").text
        metadata = record.find("{http://www.openarchives.org/OAI/2.0/}metadata/{http://def.wmo.int/wmdr/2017}WIGOSMetadataRecord")
        records.append({
            "identifier": identifier,
            "metadata" : metadata
        })
        if output_dir is not None and metadata is not None:
            record_filename = "%s/%s.xml" % (output_dir,identifier)
            et = etree.ElementTree(metadata)
            et.write(record_filename, pretty_print=True)
    resumptionToken = list_records.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken")
    if resumptionToken is not None:
        resumption_token = resumptionToken.text
        completeListSize = int(resumptionToken.attrib["completeListSize"])
        cursor = int(resumptionToken.attrib["cursor"])
        return records, resumption_token, completeListSize, cursor
    else:
        return records, None, None, None

def getRecordsNextPage(output,resumption_token,endpoint="https://oscar.wmo.int:443/oai/provider",output_dir=None):
    response = requests.get(endpoint,params={"verb":"ListRecords","resumptionToken":resumption_token})
    f = open(output,"w")
    f.write(response.text)
    f.close()
    tree = etree.parse(output)
    root = tree.getroot()
    root.tag
    list_records = root.find("{http://www.openarchives.org/OAI/2.0/}ListRecords")
    cursor = int(list_records.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken").attrib["cursor"])
    filename ="%s/records_%i.xml" % (output_dir,cursor)
    if output_dir is not None:
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        shutil.copyfile(output,filename)
    records = []
    for record in list_records.iter("{http://www.openarchives.org/OAI/2.0/}record"):
        identifier = record.find("{http://www.openarchives.org/OAI/2.0/}header/{http://www.openarchives.org/OAI/2.0/}identifier").text
        metadata = record.find("{http://www.openarchives.org/OAI/2.0/}metadata/{http://def.wmo.int/wmdr/2017}WIGOSMetadataRecord")
        records.append({
            "identifier": identifier,
            "metadata" : metadata
        })
        if output_dir is not None and metadata is not None:
            record_filename = "%s/%s.xml" % (output_dir,identifier)
            et = etree.ElementTree(metadata)
            et.write(record_filename, pretty_print=True)
    new_token = list_records.find("{http://www.openarchives.org/OAI/2.0/}resumptionToken").text
    return records, cursor, new_token

def getRecords(output,output_dir,endpoint="https://oscar.wmo.int:443/oai/provider",max_pages=500,metadata_prefix="wmdr",set_spec=None):
    records, resumption_token, completeListSize, cursor = getRecordsFirstPage(output,endpoint=endpoint,metadata_prefix=metadata_prefix,set_spec=set_spec,output_dir=output_dir)
    page = 0
    if resumption_token is None:
        return records
    while cursor < completeListSize and page < max_pages:
        page = page + 1
        more_records, cursor, resumption_token = getRecordsNextPage(output,resumption_token,endpoint=endpoint,output_dir=output_dir)
        print("cursor: %i, page: %i, completeListSize: %i" % (cursor, page, completeListSize))
        records.extend(more_records)
    return records
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Bulk download WMDR records from OAI web service')
    parser.add_argument('action', type=str, help='action to perform',choices=["identifiers","records","record"])
    parser.add_argument('output', type=str, help='directory where to save results')
    parser.add_argument('-s','--set_spec',type=str,help="optional. Retrieve only records with the specified setSpec attribute")
    parser.add_argument('-e','--endpoint',type=str,default="https://oscar.wmo.int:443/oai/provider",help="optional. OAI web service endpoint")
    parser.add_argument('-i','--identifier',type=str,help="Record identifier. Valid only for action=record")
    
    args = parser.parse_args()
    if not os.path.isdir(args.output):
        print("Error: specified output directory not found")
        exit(1)
    if args.action == "identifiers":
        filename = "%s/identifiers.xml" % args.output
        filename_json = "%s/identifiers.json" % args.output
        if args.set_spec is not None:
            getIdentifiers(filename,filename_json,args.output,endpoint=args.endpoint,set_spec=args.set_spec)
        else:
            getIdentifiers(filename,filename_json,args.output,endpoint=args.endpoint)
    elif args.action == "records":
        filename = "%s/records.xml" % args.output
        if args.set_spec is not None:
            records = getRecords(filename,args.output,endpoint=args.endpoint,set_spec=args.set_spec)
        else:
            records = getIdentifiers(filename,args.output,endpoint=args.endpoint)
    elif args.action == "record":
        if args.identifier is None:
            print("ERROR: missing -i, --identifier")
            exit(1)
        getRecord(args.identifier,output_dir=args.output, endpoint=args.endpoint)
    else:
        print("ERROR: invalid action")
        exit(1)

