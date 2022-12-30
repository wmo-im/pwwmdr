import requests
from lxml import etree
import json
import os
import shutil
import click

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
    if list_records is None:
        print("Element ListRecords not found")
        return None, None, None
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

def getRecords(output,output_dir,endpoint="https://oscar.wmo.int:443/oai/provider",max_pages=500,metadata_prefix="wmdr",set_spec=None,return_records=False):
    records, resumption_token, completeListSize, cursor = getRecordsFirstPage(output,endpoint=endpoint,metadata_prefix=metadata_prefix,set_spec=set_spec,output_dir=output_dir)
    page = 0
    if resumption_token is None:
        return records
    while cursor < completeListSize and page < max_pages:
        page = page + 1
        more_records, cursor, resumption_token = getRecordsNextPage(output,resumption_token,endpoint=endpoint,output_dir=output_dir)
        if cursor is None:
            break
        print("cursor: %i, page: %i, completeListSize: %i" % (cursor, page, completeListSize))
        if return_records:
            records.extend(more_records)
    if return_records:
        return records
    else:
        return

@click.group()
def kpi():
    """key performance indicators"""
    pass

@click.command()
@click.pass_context
@click.argument('action',
            type=click.Choice(["identifiers","records","record"]))
@click.argument('output',
              type=str)
@click.option('--set_spec', '-s', type=str,
              help='Retrieve only records with the specified setSpec attribute')
@click.option('--endpoint', '-e', type=str, default="https://oscar.wmo.int:443/oai/provider",
              help='OAI web service endpoint')
@click.option('--identifier', '-i', type=str, help='Record identifier. Valid only for action=record')
@click.option('--metadata_prefix', '-p', default="wmdr", help='Metadata prefix. Defaults to wmdr')
def harvest(self,action,output,set_spec,endpoint,identifier,metadata_prefix):
    """
    Bulk download WMDR records from OAI web service

    ACTION is the action to perform. Options are 
    
      - identifiers: request record identifiers. 
    
      - records: request records. 
    
      - record: request record by identifier"
    
    OUTPUT is the directory where to save results
    """
    if not os.path.isdir(output):
        print("Error: specified output directory not found")
        exit(1)
    if action == "identifiers":
        filename = "%s/identifiers.xml" % output
        filename_json = "%s/identifiers.json" % output
        if set_spec is not None:
            getIdentifiers(filename,filename_json,output,endpoint=endpoint,set_spec=set_spec,metadata_prefix=metadata_prefix)
        else:
            getIdentifiers(filename,filename_json,output,endpoint=endpoint)
    elif action == "records":
        filename = "%s/records.xml" % output
        if set_spec is not None:
            getRecords(filename,output,endpoint=endpoint,set_spec=set_spec,metadata_prefix=metadata_prefix)
        else:
            getRecords(filename,output,endpoint=endpoint,metadata_prefix=metadata_prefix)
    elif action == "record":
        if identifier is None:
            print("ERROR: missing -i, --identifier")
            exit(1)
        getRecord(identifier,output_dir=output, endpoint=endpoint,metadata_prefix=metadata_prefix)
    else:
        print("ERROR: invalid action")
        exit(1)

kpi.add_command(harvest)
