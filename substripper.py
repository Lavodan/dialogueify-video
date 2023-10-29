"""
Small utility for pulling out a list of start and end times without anything else from multiple subttile formats
Made for dialogueify
"""

# Built-in modules
import os
import re
import json
from datetime import timedelta

#Custom modules
from exceptions import *

#Global variables
parsers = {}




# Main function
def sub_parse(file):
    global parsers
    
    extension = file[len(file)-file[::-1].find(".")::] #Pull the extension from the file name
    try:
        return parsers[extension](file)
    except KeyError:
        raise UnsupportedSubFormat




# Parsers
def parse_srt(file):
    with open(file, "r", encoding="utf-8") as srt_file:
        lines = srt_file.readlines()

    subtitles = []
    current_subtitle = None

    for line in lines:
        line = line.strip()
        if not line:
            if current_subtitle:
                subtitles.append(current_subtitle)
                current_subtitle = None
                
        elif "-->" in line:
            if current_subtitle:
                subtitles.append(current_subtitle)
                
            start_time, end_time = line.split("-->")
            
            start_time = parse_hhmmssms(start_time.strip())
            end_time = parse_hhmmssms(end_time.strip())
            current_subtitle = {"start_time": start_time, "end_time": end_time}
            
    return subtitles
    
def parse_json(file):
    with open(file, "r", encoding="utf-8") as json_file:
        events = json.load(json_file)["events"]
    
    subtitles = []
    
    for sub in events:
        start_time = timedelta(milliseconds = sub["tStartMs"])
        end_time = start_time + timedelta(milliseconds = sub["dDurationMs"])
        subtitles.append({"start_time" : start_time, "end_time" : end_time})
        
    return subtitles

def parse_vtt(file):
    raise UnsupportedSubFormat



# Utilities
def parse_hhmmssms(timecode):
    timecode_parts = timecode.split(":")
    seconds, milliseconds = map(int, timecode_parts[2].replace(",", ".").split("."))
    return timedelta(hours=int(timecode_parts[0]), minutes=int(timecode_parts[1]), seconds=seconds, milliseconds=milliseconds)

if True:
    parsers = {
        "srt" : parse_srt,
        "json3" : parse_json, #Format used by youtube's subtitles
        "json" : parse_json,
        "vtt" : parse_vtt
    }