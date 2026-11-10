"""Record a fresh, isolated Bonsai GUI session on Linux/X11."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "data/bonsai-authoring"
    if output.exists():
        parser.error("Archive data/bonsai-authoring before recording another run")
    if not os.environ.get("DISPLAY"):
        parser.error("An X11 DISPLAY is required")
    output.mkdir(parents=True)
    env = {
        **os.environ,
        "BLENDER_USER_RESOURCES": str(args.profile.resolve()),
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }
    recorder = None
    with (output / "blender.log").open("w") as log:
        blender = subprocess.Popen(
            [str(args.blender.resolve()), "-noaudio", "--window-geometry",
             "20", "20", "1440", "1000", "--python", str(root / "scripts/bonsai_author.py")],
            env=env, stdout=log, stderr=subprocess.STDOUT,
        )
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            probe = subprocess.run(
                ["xdotool", "search", "--all", "--onlyvisible", "--pid",
                 str(blender.pid), "--class", "Blender"],
                capture_output=True, text=True, check=False,
            )
            windows = [line for line in probe.stdout.splitlines() if line.isdigit()]
            if windows:
                window = windows[-1]
                break
            if blender.poll() is not None:
                raise RuntimeError("Blender exited; inspect data/bonsai-authoring/blender.log")
            time.sleep(0.2)
        else:
            raise TimeoutError("Blender window did not appear")
        # --all is essential: --pid and --class otherwise use OR matching.
        owner = subprocess.check_output(["xdotool", "getwindowpid", window], text=True)
        if str(blender.pid) not in owner.splitlines():
            raise RuntimeError("Refusing to record a window belonging to another process")
        print(f"Recording isolated Blender process {blender.pid}", flush=True)
        recorder = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-f", "x11grab", "-window_id", window,
             "-framerate", "15", "-i", env["DISPLAY"], "-c:v", "libvpx-vp9",
             "-deadline", "realtime", "-cpu-used", "8", "-b:v", "1M",
             str(output / "bonsai-authoring.webm")], stdin=subprocess.PIPE,
        )
        deadline = time.monotonic() + 120
        last_step = 0
        while time.monotonic() < deadline:
            if blender.poll() is not None or recorder.poll() is not None:
                raise RuntimeError("Blender or recorder exited before the authoring run finished")
            path = output / "session.json"
            if path.exists():
                try:
                    session = json.loads(path.read_text())
                except json.JSONDecodeError:
                    time.sleep(0.1)
                    continue
                if session.get("error"):
                    raise RuntimeError(session["error"])
                if len(session["steps"]) > last_step:
                    last_step = len(session["steps"])
                    print(session["steps"][-1]["label"], flush=True)
                if session["complete"]:
                    subprocess.run(
                        ["ffmpeg", "-loglevel", "error", "-f", "x11grab",
                         "-window_id", window, "-i", env["DISPLAY"], "-frames:v", "1",
                         str(output / "bonsai-saved.png")], check=True,
                    )
                    break
            time.sleep(0.5)
        else:
            raise TimeoutError("Authoring did not complete")
    finally:
        try:
            if recorder is not None:
                recorder.communicate(b"q", timeout=20)
        finally:
            blender.terminate()
            try:
                blender.wait(timeout=10)
            except subprocess.TimeoutExpired:
                blender.kill()
                blender.wait()
    if recorder.returncode:
        raise RuntimeError("Recording failed")
    print(f"Saved authoring evidence to {output}")


if __name__ == "__main__":
    main()
