from lxml import etree
import os
from pywmdr.kpi import WMDRKeyPerformanceIndicators
import glob
import json
import re

def parseAndEvaluate(filename,output=None,selected_kpi : int=None):
    exml = etree.parse(filename)
    try:
        kpi = WMDRKeyPerformanceIndicators(exml)
    except Exception as e:
        print("warning: invalid wmdr document: %s" % str(e))
        return None
    if selected_kpi is not None:
        result = kpi.evaluate(selected_kpi)
    else:
        result = kpi.evaluate()
    if output is not None:
        f = open(output,"w")
        json.dump(result,f,indent=2)
        f.close()
    return result

def parseAndEvaluateFiles(file_pattern,output_dir=None,selected_kpi : int=None):
    files = glob.glob(file_pattern)
    if not len(files):
        print("Error: no files matched the pattern")
        return
    results = []
    for file in files:
        try:
            result = parseAndEvaluate(file,selected_kpi=selected_kpi)
        except Exception as e:
            print("Error: kpi evaluation failed: %s" % str(e))
            continue
        results.append(result)
        if output_dir is not None:
            filename = "%s/%s_eval.json" % (output_dir, file.split("/")[-1])
            f = open(filename,"w")
            json.dump(result,f,indent=2)
            f.close()
    return results

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
        results.append(json.load(f))
        f.close()
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Bulk evaluate WMDR KPIs. Compute metrics')
    parser.add_argument('path', type=str, help='path where to read wmdr files')
    parser.add_argument('-o','--output_dir',type=str,help="optional. Save the results onto this location")
    parser.add_argument('-m','--metrics',type=str,help="optional. Compute metrics and save the results onto this file")
    parser.add_argument('-k','--kpi',type=int,help="optional. Compute selected kpi only")
    
    args = parser.parse_args()
    print("kpi type:%s" % str(type(args.kpi)))
    results = parseAndEvaluateFiles(args.path,output_dir=args.output_dir,selected_kpi=args.kpi)
    if args.metrics and results is not None:
        metrics = getMetrics(results)
        f = open(args.metrics,"w")
        json.dump(metrics,f,indent=2)
        f.close()
