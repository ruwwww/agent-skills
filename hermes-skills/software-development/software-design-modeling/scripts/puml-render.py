#!/usr/bin/env python3
"""
PlantUML Headless Renderer via Kroki API
Converts .puml files into PNG or SVG without local Graphviz or Java dependencies.
"""
import os
import sys
import urllib.error
import urllib.request


def render_puml(input_file: str, output_format: str = "png", output_file: str = None):
    if not os.path.exists(input_file):
        print(f"Error: input file '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    if not output_file:
        base, _ = os.path.splitext(input_file)
        output_file = f"{base}.{output_format}"

    url = f"https://kroki.io/plantuml/{output_format}"
    req = urllib.request.Request(
        url,
        data=content.encode("utf-8"),
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            with open(output_file, "wb") as out:
                out.write(data)
            print(f"Successfully rendered: {output_file} ({len(data)} bytes)")
            return output_file
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        print(f"Kroki HTTP Error ({e.code}): {err_msg}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Render failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: puml-render.py <file.puml> [format: png|svg] [output_file]")
        sys.exit(1)

    src = sys.argv[1]
    fmt = sys.argv[2] if len(sys.argv) > 2 else "png"
    dest = sys.argv[3] if len(sys.argv) > 3 else None
    render_puml(src, fmt, dest)
