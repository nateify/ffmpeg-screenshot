#!/usr/bin/env python3

import argparse
import math
import re
import sys
from pathlib import Path

import ffmpeg
from tqdm import tqdm

parser = argparse.ArgumentParser(description="Generate screenshots from a video file using ffmpeg")
parser.add_argument("in_file", type=str, help="Input file")
parser.add_argument("--print-chapters", action="store_true", help="Print input file chapters and exit")
parser.add_argument("--interval", "--int", type=int, default=20, help="Screenshot interval in seconds")
parser.add_argument("-o", "--outpath", type=str, help="Output directory")

start_group = parser.add_mutually_exclusive_group(required=False)
end_group = parser.add_mutually_exclusive_group(required=False)
start_group.add_argument("--start-time", "--s", type=str, default="0", help="Start timestamp")
start_group.add_argument("--start-chapter-number", type=int, help="Start chapter number (1-based)")
start_group.add_argument("--start-chapter-name", type=str, help="Start chapter name")
end_group.add_argument("--end-time", "--e", type=str, help="End timestamp")
end_group.add_argument("--end-chapter-number", type=int, help="End chapter number (1-based)")
end_group.add_argument("--end-chapter-name", type=str, help="End chapter name")

parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-s", "--simulate", action="store_true")


def parse_time(time_str):
    """Parse time string (hh:mm:ss or seconds) into seconds."""
    if re.match(r"^([0-9]{2}:){2}[0-9]{2}$", time_str):
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    return int(time_str)


def get_chapter_time(chapters, chapter_num=None, chapter_name=None, key="start_time"):
    """Retrieve time from chapters by number or name."""
    if chapter_num:
        return float(chapters[chapter_num - 1][key])
    if chapter_name:
        for chapter in chapters:
            if chapter["tags"]["title"] == chapter_name:
                return float(chapter[key])
    return None


def ensure_directory(path):
    path.mkdir(parents=True, exist_ok=True)


def generate_screenshots(args):
    try:
        in_file = Path(args.in_file)
        probe = ffmpeg.probe(in_file, show_chapters=None, hide_banner=None)

        chapters = probe.get("chapters", [])
        duration = float(probe["format"]["duration"])

        if args.print_chapters:
            for idx, chapter in enumerate(chapters, 1):
                print(f"Chapter {idx}: {chapter['start_time']} {chapter['tags'].get('title', '')}")
            sys.exit(0)

        out_path = Path(args.outpath) if args.outpath else in_file.parent / "screenshots"
        ensure_directory(out_path)

        # Calculate start and end times
        start_time = get_chapter_time(chapters, args.start_chapter_number, args.start_chapter_name) or parse_time(
            args.start_time
        )

        if args.end_chapter_number or args.end_chapter_name:
            end_time = get_chapter_time(chapters, args.end_chapter_number, args.end_chapter_name, "end_time")
        elif args.end_time:
            end_time = parse_time(args.end_time)
        else:
            end_time = duration

        # Calculate the number of screenshots
        time_range = end_time - start_time
        max_count = math.ceil(time_range / args.interval)

        if True in (args.verbose, args.simulate):
            print(f"Input file: {in_file.resolve()}")
            print(f"Output directory: {out_path.resolve()}")
            print(f"Start time: {start_time} seconds")
            print(f"End time: {end_time} seconds")
            print(f"Interval: {args.interval} seconds")
            print(f"Total screenshots: {max_count}")

        for count, timestamp in enumerate(
            tqdm(
                range(math.ceil(start_time), math.floor(end_time), args.interval),
                total=max_count,
                desc="Generating Screenshots",
            ),
            1,
        ):
            if args.simulate:
                continue

            out_file = f"{in_file.stem}_{str(count).zfill(len(str(max_count)))}.png"
            out_fullpath = out_path / out_file

            (
                ffmpeg.input(str(in_file), guess_layout_max=0, ss=timestamp, hide_banner=None)
                .filter("setsar", 1)
                .output(
                    str(out_fullpath),
                    vcodec="png",
                    compression_level=1,
                    an=None,
                    pix_fmt="rgb24",
                    vframes=1,
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

    except ffmpeg.Error as e:
        print(f"ffmpeg error: {e.stderr.decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    args_namespace = parser.parse_args()
    generate_screenshots(args_namespace)
