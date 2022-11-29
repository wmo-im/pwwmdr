import pytz
from datetime import datetime
from pandas import DataFrame

def getTimezoneOffsetSeconds(tz_string):
    timezone = pytz.timezone(tz_string)
    offset = timezone.utcoffset(datetime.utcnow()) # ,is_dst = False)
    return offset.total_seconds()

def getTimezoneDstSeconds(tz_string):
    timezone = pytz.timezone(tz_string)
    offset = timezone.dst(datetime.utcnow()) # ,is_dst = False)
    return offset.total_seconds()

def secondsToDateString(total_seconds):
    sign = lambda x: "-" if x < 0 else ( "+" if x > 0 else "±")
    hours, remainder = divmod(abs(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return 'UTC%s%02d:%02d' % (sign(total_seconds), int(hours), int(minutes))

def timezone_to_offset(tz_string):
    timezone = pytz.timezone(tz_string)
    offset = timezone.utcoffset(datetime.utcnow()) # ,is_dst = False)
    total_seconds = offset.total_seconds()
    sign = lambda x: "-" if x < 0 else ( "+" if x > 0 else "±")
    hours, remainder = divmod(abs(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%s%02d:%02d' % (sign(total_seconds), int(hours), int(minutes))

def makeTimezoneCodelist():
    codes = []
    unique_names = {}
    for tz in pytz.all_timezones:
        current_offset = getTimezoneOffsetSeconds(tz)
        current_dst = getTimezoneDstSeconds(tz)
        main_offset = current_offset - current_dst
        notation = str(int(main_offset / 3600)) if main_offset / 3600 % 1 == 0 else str(main_offset / 3600)
        codes.append({"tz_name": tz, "current_offset": current_offset, "current_dst": current_dst, "main_offset": main_offset, "name_w_dst": secondsToDateString(current_offset), "name": secondsToDateString(main_offset), "notation": notation})
    return DataFrame(codes).sort_values("main_offset")

def makeCodelist(as_dataframe=True):
    tz_codelist = makeTimezoneCodelist()
    unique_names = list(set(tz_codelist["name"]))
    codelist = []
    for name in unique_names:
        subset = tz_codelist[tz_codelist["name"]==name]
        description = "Timezone with a UTC offset of %s hours. Locations in this timezone include %s" % (name, ", ".join(subset["tz_name"]))
        codelist.append({
            "notation": list(subset["notation"])[0],
            "name": name,
            "description": description,
            "offset":  list(subset["main_offset"])[0]
        })
    if as_dataframe:
        codelist = DataFrame(codelist).sort_values("offset")
        del codelist["offset"]
        return codelist
    else:
        return codelist

if __name__ == "__main__":
    # codelist = makeTimezoneCodelist()
    # f = open("results/timezones.csv","w")
    # f.write(codelist.to_csv(index=False))
    # f.close()

    final_codelist = makeCodelist()
    # f = open("results/wmdr_timezones.csv","w")
    # f.write(final_codelist.to_csv(index=False))
    # f.close()
    print(final_codelist.to_csv(index=False))
