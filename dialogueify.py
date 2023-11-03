"""
A small python CLI utility created for cutting down on non-dialogue sections of video utilising a subtitle file. 
Utilises substripper
"""


#Built-in modules
import argparse
import subprocess
import os
import tempfile
from datetime import timedelta
import sys
import re
import traceback

#Custom modules
from exceptions import *
from substripper import *

# Global variables
temp_files = []
final_time = 0.0




# Main
def main(args):
    # ANSI escape sequence formatting
    os.system("")
    
    input_video = args.input_video
    subtitle_file = args.subtitle_file
    output_file = args.output_file
    audio_only = args.audio_only
    
    if audio_only:
        extension = "mp3"
    else:
        extension = "mp4"
    
    output_file= resolve_nameconflict(f"{output_file}.{extension}")
    
    with tempfile.TemporaryDirectory() as temp_files_folder:
        global temp_files
        temp_files.insert(0, temp_files_folder)
        
        try:
            print("Finding gaps...")
            gaps = analyze_subtitle_file(subtitle_file)
            
            print("Creating clips..." + "\n" * 4, end="") # Newlines for space
            create_clips(input_video, gaps, temp_files_folder, audio_only)
            
            print("Stitching video...")
            concatenate_clips(output_file, audio_only)
        except KeyboardInterrupt as k:
            halt("Program keyboard interrupted, halting...", k)
        except Exception as e:
            halt(f"An unexpected error occurred: {e}", e)
    halt(delete = True)




# Active Functions
def analyze_subtitle_file(subtitle_file):
    gaps = []
    
    subtitles = sub_parse(subtitle_file)

    grouped_subtitles = []

    if subtitles:
        grouped_subtitles.append(subtitles[0])

    for i in range(1, len(subtitles)):
        prev_subtitle = grouped_subtitles[-1]
        current_subtitle = subtitles[i]

        # Check for significant gap or non-overlapping subtitles
        if current_subtitle["start_time"] - prev_subtitle["end_time"] > timedelta(seconds=3):
            grouped_subtitles.append(current_subtitle)
        else:
            # Extend the previous subtitle
            prev_subtitle["end_time"] = current_subtitle["end_time"]

    for subtitle in grouped_subtitles:
        gaps.append((subtitle["start_time"], subtitle["end_time"]))
    
    return gaps

def create_clips(input_video, gaps, temp_files_folder, audio_only=False):
    global temp_files
    
    for i, (start_time, end_time) in enumerate(gaps):
        start_time_str = str(start_time.total_seconds() - 1)
        duration_str = str((end_time - start_time).total_seconds() + 2)
        
        if audio_only:
            temp_output_file = os.path.join(temp_files_folder, f"temp_trimmed_{i}.mp3")
        else:
            temp_output_file = os.path.join(temp_files_folder, f"temp_trimmed_{i}.mp4")
        
        clear_lines(4)
        create_progress_bar(i + 1, len(gaps), length=50)  # i+1 so that progress bar ends at 100%, not 99%
        run_ffmpeg_command(["ffmpeg", "-ss", start_time_str, "-i", input_video, "-t", duration_str, temp_output_file])
        
        temp_files.append(temp_output_file)

def concatenate_clips(output_file, audio_only=False):
    global temp_files

    
    concat_txt = os.path.normpath(os.path.join(tempfile.gettempdir(), "concat.txt"))
    temp_files.insert(0, concat_txt)
    
    with open(concat_txt, "w") as txtfile:
        for file in temp_files[2::]:
            txtfile.write(f"file '{file}'\n")

    run_ffmpeg_command(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c:a", "copy", output_file])




# Active helpers
def run_ffmpeg_command(command):
    try:
        total_time = 0
        total_match = None
        outputted = False

        print("Running FFmpeg command: " + " ".join(command))
        create_progress_bar(0.0, 0.0) ## Intitialize progress_bar
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        command_str = " ".join(command)  # Convert the command list to a string
        
        try:
            total_time = float(command[command.index("-t") + 1])
            global final_time
            final_time += total_time
        except ValueError:
            total_time = final_time
        
        for line in process.stderr:
            time_match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
            if time_match:
                current_time = (
                    int(time_match.group(1)) * 3600 +
                    int(time_match.group(2)) * 60 +
                    int(time_match.group(3)) * 1 +
                    float(time_match.group(4)) / 100
                )

                if total_time:
                    print("\033[1A", end="")
                    create_progress_bar(current_time, total_time)
                    print("\033[K", end="")
        for line in process.stdout:
            print(line.strip())

        process.communicate()  # Wait for the process to finish
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        print("\033[32mFFmpeg command completed.\033[K\033[0m")
    except subprocess.CalledProcessError as e:
        halt(f"\033[31mError running FFmpeg command: {e}\033[0m", e)

def cleanup(errored=False):
    global temp_files

    for path in temp_files:
        if os.path.isfile(path):
            os.remove(path)
    for path in temp_files:
        if os.path.exists(path):
            try:
                os.rmdir(path)
            except OSError:
                for x, y, files in os.walk(path):
                    for file in files:
                        os.remove(os.path.join(path,file))
                    os.rmdir(path)

    if errored:
        print("\033[31mTemporary files deleted due to error.\033[0m")
    else:
        print(f"Temporary files cleaned up.")

def halt(message="Halting script...", exception=None, delete=None):
    global temp_files
    print(message)
    
    errored = bool(exception)
    
    if errored:
        exit_code = 1
        if not isinstance(exception, KeyboardInterrupt):
            traceback.print_exc()
            print()

        while temp_files and (delete == None):
            delete_temp_files = input(f"Do you want to delete temporary files kept at {temp_files[0]}? (y/n): ")
            if delete_temp_files.lower() == "y":
                delete = True
            elif delete_temp_files.lower() == "n":
                delete = False
    else:
        exit_code = 0
        
    if delete:
        cleanup(errored)
        
    print("\033[32mScript completed.\033[0m")
    exit(exit_code)

def resolve_nameconflict(path):
    while True:
        if not os.path.isfile(path):
            return path
        elif os.path.isfile(path):
            choice = input(f"\033[36mThe file '{path}' already exists.\033[K\033[0m Do you want to overwrite it? ([y]es [n]o [r]ename): ")
            if choice.lower() == "y":
                return path
            elif choice.lower() == "n":
                halt("Stopping because of name conflict...")
            elif choice.lower() == "r":
                return resolve_nameconflict(input("Enter a new filename: "))




# Utilities
def clear_lines(lines):
    for i in range(lines):
        print("\033[1A\033[K", end="")

def create_progress_bar(current_progress, total_progress, length = 25):
    try:
        progress = current_progress / total_progress
    except ZeroDivisionError:
        progress = 0.0
    num_blocks = int(progress * length)
    progress_bar = "[" + "▓" * num_blocks + "░" * (length-num_blocks) + "]"
    print(f"{progress_bar} {int(progress * 100)}% ({round(current_progress,2)} / {round(total_progress,2)})")



if __name__ == "__main__":
    # Arguments
    parser = argparse.ArgumentParser(description="Dialogueify: Shorten video through subtitles.")
    parser.add_argument("input_video", help="Path to the input video file")
    parser.add_argument("subtitle_file", help="Path to the subtitle file")
    parser.add_argument("output_file", help="Path to the output file")
    parser.add_argument("-ao", "--audio_only", action="store_true", help="Produce audio-only output")
    args = parser.parse_args()
    
    main(args)
