import subprocess
import os
import tempfile
from datetime import timedelta

def run_ffmpeg_command(command):
    try:
        print(f"Running FFmpeg command: {' '.join(command)}")
        subprocess.run(command, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error running FFmpeg command: {e}")
        delete_temp_files = input("An error occurred. Do you want to delete temporary files? (y/n): ")
        if delete_temp_files.lower() == 'y':
            cleanup(temp_subtitle_file, temp_trimmed_files)
        exit(1)

def extract_subtitles(input_video, subtitle_file, temp_subtitle_file):
    run_ffmpeg_command(["ffmpeg", "-i", input_video, temp_subtitle_file])

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
    seconds, milliseconds = map(int, timecode_parts[2].replace(',', '.').split('.'))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

def trim_video(input_video, gaps, temp_trimmed_folder, audio_only=False):
    temp_trimmed_files = []
    for i, (start_time, end_time) in enumerate(gaps):
        start_time_str = str(start_time.total_seconds() - 1)
        duration_str = str((end_time - start_time).total_seconds() + 2)
        if audio_only:
            temp_output_file = os.path.join(temp_trimmed_folder, f"temp_trimmed_{i}.mp3")
        else:
            temp_output_file = os.path.join(temp_trimmed_folder, f"temp_trimmed_{i}.mp4")
        run_ffmpeg_command(["ffmpeg", "-ss", start_time_str, "-i", input_video, "-t", duration_str, temp_output_file])
        temp_trimmed_files.append(temp_output_file)
    return temp_trimmed_files

def concatenate_trimmed_files(temp_trimmed_files, output_file, audio_only=False):
    concat_txt = os.path.normpath(os.path.join(tempfile.gettempdir(), "concat.txt"))
    with open(concat_txt, "w") as txtfile:
        for file in temp_trimmed_files:
            txtfile.write(f"file '{file}'\n")
    
    if audio_only:
        output_file = f'{output_file}.mp3'
    else:
        output_file = f'{output_file}.mp4'
    
    run_ffmpeg_command(["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c:a", "copy", output_file])

def cleanup(temp_subtitle_file, temp_trimmed_files):
    os.remove(temp_subtitle_file)
    for file in temp_trimmed_files:
        os.remove(file)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python dialogueify.py <input_video> <subtitle_file> <output_file> [-ao]")
        exit(1)

    input_video = sys.argv[1]
    subtitle_file = sys.argv[2]
    output_file = sys.argv[3]

    audio_only = "-ao" in sys.argv

    temp_subtitle_file = "temp.ass"
    
    with tempfile.TemporaryDirectory() as temp_trimmed_folder:
        temp_trimmed_files = []
        try:
            extract_subtitles(input_video, subtitle_file, temp_subtitle_file)
            gaps = analyze_subtitle_file(subtitle_file)
            temp_trimmed_files = trim_video(input_video, gaps, temp_trimmed_folder, audio_only)
            concatenate_trimmed_files(temp_trimmed_files, output_file, audio_only)
        except KeyboardInterrupt:
            print("Script interrupted by user.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            delete_temp_files = input("An error occurred. Do you want to delete temporary files? (y/n): ")
            if delete_temp_files.lower() == 'y':
                cleanup(temp_subtitle_file, temp_trimmed_files)
        finally:
            cleanup(temp_subtitle_file, temp_trimmed_files)

    print("Script completed.")
