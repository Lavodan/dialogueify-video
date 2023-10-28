import argparse
import subprocess
import os
import tempfile
from datetime import timedelta
import sys
import re
import traceback

# Global variables
cleanup_needed = False
temp_trimmed_files = []
final_time = 0.0

def clear_lines(lines):
    for i in range(lines):
        print("\033[1A\033[K", end="")

def create_progress_bar(current_progress, total_progress, length = 25):
    try:
        progress = current_progress / total_progress
    except ZeroDivisionError:
        progress = 0
    num_blocks = int(progress * length)
    progress_bar = "[" + "▓" * num_blocks + "░" * (length-num_blocks) + "]"
    print(f"{progress_bar} {int(progress * 100)}% ({round(current_progress,2)} / {round(total_progress,2)})")

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
                    

            if not total_time:
                pass
        for line in process.stdout:
            print(line.strip())

        process.communicate()  # Wait for the process to finish
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        print("\033[32mFFmpeg command completed.\033[K\033[0m")
    except subprocess.CalledProcessError as e:
        print(f"\033[31mError running FFmpeg command: {e}\033[0m")
        traceback.print_exc()
        print()
        cleanup_on_error()
        exit(1)


def analyze_subtitle_file(subtitle_file):
    gaps = []
    with open(subtitle_file, "r", encoding="utf-8") as srt_file:
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
            start_time = parse_timecode(start_time.strip())
            end_time = parse_timecode(end_time.strip())
            current_subtitle = {"start_time": start_time, "end_time": end_time, "lines": []}
        elif current_subtitle:
            current_subtitle["lines"].append(line)

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
            prev_subtitle["lines"].extend(current_subtitle["lines"])
            prev_subtitle["end_time"] = current_subtitle["end_time"]

    for subtitle in grouped_subtitles:
        gaps.append((subtitle["start_time"], subtitle["end_time"]))

    
    return gaps


def parse_timecode(timecode):
    timecode_parts = timecode.split(":")
    hours = int(timecode_parts[0])
    minutes = int(timecode_parts[1])
    seconds, milliseconds = map(int, timecode_parts[2].replace(",", ".").split("."))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)


def create_clips(input_video, gaps, temp_trimmed_folder, audio_only=False):
    global temp_trimmed_files
    
    for i, (start_time, end_time) in enumerate(gaps):
        start_time_str = str(start_time.total_seconds() - 1)
        duration_str = str((end_time - start_time).total_seconds() + 2)
        
        if audio_only:
            temp_output_file = os.path.join(temp_trimmed_folder, f"temp_trimmed_{i}.mp3")
            
        else:
            temp_output_file = os.path.join(temp_trimmed_folder, f"temp_trimmed_{i}.mp4")
        
        clear_lines(4)
        create_progress_bar(i+1, len(gaps), length = 50) #i+1 so that pgoress bar ends at 100%, not 99%
        run_ffmpeg_command(["ffmpeg", "-ss", start_time_str, "-i", input_video, "-t", duration_str, temp_output_file])
        
        temp_trimmed_files.append(temp_output_file)
        
    return temp_trimmed_files


def concatenate_trimmed_files(temp_trimmed_files, output_file, audio_only=False):
    concat_txt = os.path.normpath(os.path.join(tempfile.gettempdir(), "concat.txt"))
    with open(concat_txt, "w") as txtfile:
        for file in temp_trimmed_files:
            txtfile.write(f"file '{file}'\n")

    run_ffmpeg_command(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c:a", "copy", output_file])


def ask_user_for_filename(output_file):
    while True:
        if not os.path.isfile(output_file):
            return output_file
        elif os.path.isfile(output_file):
            choice = input(f"\033[36mThe file '{output_file}' already exists.\033[K\033[0m Do you want to overwrite it? ([y]es [n]o [r]ename): ")
            if choice.lower() == "y":
                return output_file
            elif choice.lower() == "n":
                exit(0)
            elif choice.lower() == "r":
                return ask_user_for_filename(input("Enter a new filename: "))


def cleanup_on_error():
    global cleanup_needed
    cleanup_needed = True


def cleanup():
    global temp_trimmed_files
    global cleanup_needed

    for file in temp_trimmed_files:
        if os.path.exists(file):
            os.remove(file)

    if cleanup_needed:
        print("\033[31mTemporary files deleted due to error.\033[0m")
    else:
        print(f"Temporary files cleaned up.")

    cleanup_needed = False


def main(args):
    input_video = args.input_video
    subtitle_file = args.subtitle_file
    output_file = args.output_file
    audio_only = args.audio_only
    
    
    
    if audio_only:
        extension = "mp3"
    else:
        extension = "mp4"
        
    output_file= ask_user_for_filename(f"{output_file}.{extension}")
    
    with tempfile.TemporaryDirectory() as temp_trimmed_folder:
        temp_trimmed_files = []
        try:
            print("Finding gaps...")
            gaps = analyze_subtitle_file(subtitle_file)
            print("Creating clips..." + "\n" * 4, end="") # Newlines for space
            temp_trimmed_files = create_clips(input_video, gaps, temp_trimmed_folder, audio_only)
            print("Stitching video...")
            concatenate_trimmed_files(temp_trimmed_files, output_file, audio_only)
        except KeyboardInterrupt:
            print("\n\033[31mScript interrupted by user.\033[0m")
            cleanup_on_error()
            cleanup()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            traceback.print_exc()
            print()
            while True:
                delete_temp_files = input("\033[31mAn error occurred\033[0m. Do you want to delete temporary files? (y/n): ")
                if delete_temp_files.lower() == "y":
                    cleanup_on_error()
                    cleanup()
                    break
                elif delete_temp_files.lower() == "n":
                    print(f"Files kept at {temp_trimmed_folder}")
                    break

    print("\033[32mScript completed.\033[0m")


if __name__ == "__main__":
    # ANSI escape sequence formatting
    os.system("")

    # Arguments
    parser = argparse.ArgumentParser(description="Dialogueify: Shorten video through subtitles.")
    parser.add_argument("input_video", help="Path to the input video file")
    parser.add_argument("subtitle_file", help="Path to the subtitle file")
    parser.add_argument("output_file", help="Path to the output file")
    parser.add_argument("-ao", "--audio_only", action="store_true", help="Produce audio-only output")
    args = parser.parse_args()

    main(args)
