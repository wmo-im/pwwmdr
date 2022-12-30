from lxml import etree
import os
from pywmdr.kpi import WMDRKeyPerformanceIndicators
import pywmdr.util as util
import glob
import json
import re
import jsonschema
import traceback
import click

def parseAndEvaluate(filename,output=None,selected_kpi : int=None,skip_schema_eval=False):
    exml = etree.parse(filename)
    try:
        kpi = WMDRKeyPerformanceIndicators(exml)
    except Exception:
        print("warning: invalid wmdr document:")
        traceback.print_exc()
        return None
    if selected_kpi is not None:
        result = kpi.evaluate(selected_kpi)
    else:
        result = kpi.evaluate(0,skip_schema_eval)
    if output is not None:
        f = open(output,"w")
        json.dump(result,f,indent=2)
        f.close()
    return result

def parseAndEvaluateFiles(file_pattern,output_dir=None,selected_kpi : int=None,skip_schema_eval=False,return_results=False):
    files = glob.glob(file_pattern)
    if not len(files):
        print("Error: no files matched the pattern")
        return
    results = []
    for file in files:
        try:
            result = parseAndEvaluate(file,selected_kpi=selected_kpi,skip_schema_eval=skip_schema_eval)
        except Exception:
            print("Error: kpi evaluation failed:")
            traceback.print_exc()
            continue
        if(return_results):
            results.append(result)
        if output_dir is not None:
            filename = "%s/%s_eval.json" % (output_dir, file.split("/")[-1])
            f = open(filename,"w")
            json.dump(result,f,indent=2)
            f.close()
    if return_results:
        return results
    else:
        return

def getPercentiles(values : list,perc = [5,10,25,50,75,95]):
    values_ = [0 if x is None else x for x in values]
    values_.sort()
    count = len(values_)
    percentiles = {}
    for p in perc:
        percentiles[p] = None
    for p in percentiles:
        p_index = int(int(p) / 100 * count)
        percentiles[p] = {
            "count": p_index,
            "value": values_[p_index]
        }
    return percentiles

def getKPIStats(results):
    totals = [x["total"] for x in results]
    scores = [x["score"] for x in results]
    percentages = [0 if x["percentage"] is None else x["percentage"] for x in results]
    percentiles = getPercentiles(percentages)
    count = len(results)
    average_score = sum(scores) / count
    average_percentage = sum(percentages) / count
    return {
        "name": results[0]["name"] if len(results) else None,
        "count": count,
        "totals": totals,
        "scores": scores,
        "percentages": percentages,
        "percentiles": percentiles,
        "average_score": average_score,
        "average_percentage": average_percentage
    }


def getMetrics(results):
    identifier = []
    organisation = []
    country = []
    region = []
    totals = []
    scores = []
    comments = []
    percentages = []
    grades = []
    kpis = {}
    count = len(results)
    if count == 0:
        print("Error: no results to evaluate")
        return
    for result in results:
        if "summary" in result:
            summary = result["summary"]
            totals.append(summary["total"])
            scores.append(summary["score"])
            # comments.append(summary["comments"])
            percentages.append(summary["percentage"])
            grades.append(summary["grade"])
            identifier.append(summary["identifier"])
            organisation.append(summary["organisation"])
            country.append(summary["country"])
            region.append(summary["region"])
        for kpi in [key for key in result if re.search("^kpi_",key) is not None]:
            if kpi not in kpis:
                kpis[kpi] = [
                    result[kpi]
                ]
            else:
                kpis[kpi].append(result[kpi])
    if len(totals):
        grade_counts = {"A":None,"B":None,"C":None,"D":None,"E":None,"F":None,"U":None}
        for id in grade_counts:
            grade_count = len([x for x in grades if x == id])
            grade_counts[id] = {
                "count": grade_count,
                "percentage": grade_count / count * 100
            }
        percentiles = getPercentiles(percentages)
        average_percentage = sum(percentages) / count
        average_score = sum(scores) / count
    kpi_stats = {}
    for kpi in kpis:
        kpi_stats[kpi] = getKPIStats(kpis[kpi])
    if len(totals):
        return {
            "identifier": identifier,
            "organisation": organisation,
            "country": country,
            "region": region,
            "count": count,
            "totals": totals,
            "scores": scores,
            # "comments": comments,
            "percentages": percentages,
            "grades": grades,
            "grade_counts": grade_counts,
            "percentiles": percentiles,
            "average_percentage": average_percentage,
            "average_score": average_score,
            "kpi": kpi_stats
        }
    else:
        return {
            "count": count,
            "kpi": kpi_stats 
        }

def readResults(file_pattern):
    results = []
    files = glob.glob(file_pattern)
    for file in files:
        f = open(file)
        content = json.load(f)
        isValid = util.validate_kpi_evaluation_result(content)
        if isValid:
            results.append(content)
        f.close()
    print("readResults found %i files." % len(results))
    return results

def readEvaluationsAndGetMetrics(file_pattern):
    results = readResults(file_pattern)
    return getMetrics(results)

@click.group()
def kpi():
    """key performance indicators"""
    pass

@click.command()
@click.pass_context
@click.argument('action',
            type=click.Choice(["evaluate","metrics"]))
@click.argument('path',
              type=str)
@click.option('--output_dir', '-o', type=click.Path(),
              help='Save the results onto this location')
@click.option('--compute_metrics', '-m', type=click.Path(), default="https://oscar.wmo.int:443/oai/provider",
              help='Compute metrics and save the results onto this file')
@click.option('--kpi', '-k', type=int, help='Compute selected kpi only')
@click.option('--skip_schema_eval', '-s', is_flag=True,show_default=True,default=False, help='skip evaluation of schema (kpi 1-01)')
def metrics(self,action,path,output_dir,compute_metrics,kpi,skip_schema_eval):
    if action == "evaluate":
        if compute_metrics:
            results = parseAndEvaluateFiles(path,output_dir=output_dir,selected_kpi=kpi,skip_schema_eval=skip_schema_eval,return_results=True)
            if results is not None:
                metric_results = getMetrics(results)
                f = open(compute_metrics,"w")
                json.dump(metric_results,f,indent=2)
                f.close()
        else:
            parseAndEvaluateFiles(path,output_dir=output_dir,selected_kpi=kpi,skip_schema_eval=skip_schema_eval)
    elif action == "metrics":
            metric_results = readEvaluationsAndGetMetrics(path)
            if compute_metrics:
                f = open(compute_metrics,"w")
                json.dump(metric_results,f,indent=2)
                f.close()
            else:
                print(json.dumps(metric_results,indent=2))
    else:
        print("Bad action. choices: evaluate, metrics")
        exit(1)

kpi.add_command(metrics)
