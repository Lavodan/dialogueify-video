# Dialogueify Video
A small CLI python utility created for cutting down on non-dialogue sections of video utilising a subtitle file.

## Prerequisites
- Python 3+
- ffmpeg version n5.1+ (will probably work with older versions too, not tested)
- Twice the amount of disk space as the output (this is because the program uses the system's tmp folder to store the clips with dialogue)
- Terminal which supports ANSI/VT100 escape sequences

## Usage
1. Open command prompt, powershell, or other terminal software
2. Open the .py file with python along with the needed arguments: `py dialogueify.py <video.mp4> <subtitles.srt> <Output Filename> [-ao]`

### Arguments and flags
- `<video.mp4>` - Path to video file - Format: forward slashes, example: `c:/users/dummy/desktop/video.mp4`
- `<subtitles.srt>` - Path to the subtitle file - Format: forward slashes, example: `c:/users/dummy/desktop/subs.srt`
- `<Output filename>` - Name of output file - The file will be given an extension based on the flags. The default is .mp4, example: `./dielogueified_video.mp4`
- `[-ao]` - Audio Only - Generates a .mp3 file instead of the default .mp4, much faster than the default

## Implementation
The program first analyzes the video based on the timing of the subtitles.
By defaut, the minimum length of each clip is (clip length + 1 second).
By default, clips will be grouped together and kept in one piece if there is a 3 second or smaller delay inbetween two subtitles, this is in place to keep together continuity with subtitles which are close together.
After each clip/group is analyzed, a temporary clip is saved in the system's temporary storage
After the whole length of the video is analyzed, the clips are stiched together, and output to the given filename

## Mission
This script was inspired by [this language learning video](https://www.youtube.com/watch?v=eliB_y0fmSk), and specifically for the French version of Spider Man: Into The Spiderverse, which was reduced from an original runtime of 1:56:xx to a new runtime of 1:17:xx.
Cutting down on non-dialogue parts of videos allows language learners to focus on speech nstead of having to see all of a video/movie.

## Roadmap
- More customization
  - More formats, ideally detected automatically both for subtitles and for video
  - Customizable timing for padding and grouping
    - Account for padding being bigger than grouping
- Allow pairing of audio files with subtitles
- Long term: create a swiss army knife of utilities and include this one in it
- More input validation of arguments and proper handling of improper input
- Descriptive error messages with error handling (improper suttiles format, insufficient space...)
