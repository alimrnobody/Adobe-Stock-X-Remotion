#!/usr/bin/env python3
import re
import os
import sys
import json
import time
import subprocess
import textwrap
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_FILE = SCRIPT_DIR / "Prompts" / "Prompts.txt"
SRC_DIR = SCRIPT_DIR / "src"
OUT_DIR = SCRIPT_DIR / "Output Folder"
ROOT_TSX = SRC_DIR / "Root.tsx"
LOG_FILE = SCRIPT_DIR / "render_prompts.log"

OUT_DIR.mkdir(parents=True, exist_ok=True)

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line)
    except Exception:
        print(line.encode('ascii', 'ignore').decode('ascii'))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def parse_prompts():
    content = PROMPTS_FILE.read_text(encoding="utf-8")
    blocks = re.split(r'\n\s*\n', content.strip())
    
    parsed = []
    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        if not lines:
            continue
        
        full_text = " ".join(lines)
        
        # Match prompt line like "1. **Corporate Blue Network** — Remotion..." or "1. Corporate Blue Network..."
        title_match = re.search(r'^\s*(\d+)\.\s*(?:\*\*)?(.+?)(?:\*\*)?\s*(?:—|-|:)\s*(.+)$', full_text)
        if not title_match:
            # Fallback title match
            title_match = re.search(r'^\s*(\d+)\.\s*(.+)$', lines[0])
            if not title_match:
                continue
            prompt_id = int(title_match.group(1))
            title = title_match.group(2)
            desc = " ".join(lines[1:]) if len(lines) > 1 else ""
        else:
            prompt_id = int(title_match.group(1))
            title = title_match.group(2).strip()
            desc = title_match.group(3).strip()
            
        # Clean markdown bold/formatting from title
        clean_title = re.sub(r'[\*\_\-]', '', title).strip()
        words = re.sub(r'[^a-zA-Z0-9 ]', ' ', clean_title).split()
        comp_name = "".join(w.capitalize() for w in words)
        if not comp_name:
            comp_name = f"AnimPrompt{prompt_id}"
            
        kebab_name = re.sub(r'(?<!^)(?=[A-Z])', '-', comp_name).lower() + ".mp4"
        
        # FPS (default 60)
        fps_m = re.search(r'(\d+)fps', desc)
        fps = int(fps_m.group(1)) if fps_m else 60
        
        # Frames (e.g., 480 frames, 600 frames, 720 frames)
        frames_m = re.search(r'(\d+)\s*frames', desc)
        frames = int(frames_m.group(1)) if frames_m else 480
        
        # Dots count (default 80)
        dots_m = re.search(r'(\d+)\s+dots', desc, re.IGNORECASE)
        dots_count = int(dots_m.group(1)) if dots_m else 80
        
        # Dot size px (default 4)
        dot_size_m = re.search(r'size\s*(\d+)px', desc, re.IGNORECASE)
        dot_size = int(dot_size_m.group(1)) if dot_size_m else 4
        
        # Connection distance px (default 220)
        conn_m = re.search(r'connection\s+distance\s*(\d+)px', desc, re.IGNORECASE)
        conn_dist = int(conn_m.group(1)) if conn_m else 220
        
        # Dot color
        dot_color_m = re.search(r'Dot\s+color\s*(#[0-9a-fA-F]{6})', desc, re.IGNORECASE)
        dot_color = dot_color_m.group(1) if dot_color_m else "#48cae4"
        
        # Line color
        line_color_m = re.search(r'line\s+color\s*(#[0-9a-fA-F]{6})', desc, re.IGNORECASE)
        line_color = line_color_m.group(1) if line_color_m else "#0096c7"
        
        # Base color
        base_color_m = re.search(r'Base\s*(#[0-9a-fA-F]{6})', desc, re.IGNORECASE)
        base_color = base_color_m.group(1) if base_color_m else "#03111f"
        
        has_glow = "glow" in desc.lower()
        has_vignette = "vignette" in desc.lower()
        
        parsed.append({
            "id": prompt_id,
            "title": clean_title,
            "comp_name": comp_name,
            "kebab_name": kebab_name,
            "fps": fps,
            "frames": frames,
            "dots_count": dots_count,
            "dot_size": dot_size,
            "conn_dist": conn_dist,
            "dot_color": dot_color,
            "line_color": line_color,
            "base_color": base_color,
            "has_glow": has_glow,
            "has_vignette": has_vignette,
            "desc": desc
        })
    return parsed

def generate_plexus_tsx(item):
    comp_name = item["comp_name"]
    dots_count = item["dots_count"]
    dot_size = item["dot_size"]
    conn_dist = item["conn_dist"]
    dot_color = item["dot_color"]
    line_color = item["line_color"]
    base_color = item["base_color"]
    has_glow = item["has_glow"]
    has_vignette = item["has_vignette"]
    
    # Pre-compute deterministic node initial positions and sin/cos drift parameters at module level
    nodes = []
    for i in range(dots_count):
        # Even distribution across 3840x2160 screen with margin
        seed = int(re.sub(r'\D', '', str(hash(f"{comp_name}_{i}")))[-4:])
        base_x = 200 + ((i % 12) * 310) + ((seed % 150) - 75)
        base_y = 150 + ((i // 12) * 230) + (((seed // 10) % 150) - 75)
        
        rx = 80 + (seed % 140)
        ry = 70 + ((seed // 3) % 130)
        freq1 = 1.0 + ((i % 5) * 0.25)
        freq2 = 0.8 + ((i % 4) * 0.3)
        phase = round((i * 6.28318) / max(dots_count, 1), 3)
        
        nodes.append({
            "x": base_x,
            "y": base_y,
            "rx": rx,
            "ry": ry,
            "freq1": freq1,
            "freq2": freq2,
            "phase": phase
        })
        
    nodes_js = json.dumps(nodes, indent=2)

    code = f"""import React from 'react';
import {{ useCurrentFrame, useVideoConfig, interpolate }} from 'remotion';

const BASE_COLOR = '{base_color}';
const DOT_COLOR = '{dot_color}';
const LINE_COLOR = '{line_color}';
const DOT_SIZE = {dot_size};
const MAX_CONN_DIST = {conn_dist};
const NODES = {nodes_js};

export const {comp_name}: React.FC = () => {{
  const frame = useCurrentFrame();
  const {{ durationInFrames }} = useVideoConfig();

  // Seamless 360-degree loop progress (0 to 2*PI)
  const loopProgress = (frame / durationInFrames) * Math.PI * 2;

  // Smooth fade-in (first 50 frames) and fade-out (last 50 frames)
  const fadeIn = interpolate(frame, [0, 50], [0, 1], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
  const fadeOut = interpolate(frame, [durationInFrames - 50, durationInFrames], [1, 0], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
  const opacity = fadeIn * fadeOut;

  // Calculate current node positions for this frame
  const currentPositions = NODES.map((node) => ({{
    x: node.x + Math.sin(loopProgress * node.freq1 + node.phase) * node.rx,
    y: node.y + Math.cos(loopProgress * node.freq2 + node.phase) * node.ry,
  }}));

  // Compute connecting lines between close nodes
  const lines: {{ x1: number; y1: number; x2: number; y2: number; lineOpacity: number }}[] = [];
  const len = currentPositions.length;

  for (let i = 0; i < len; i++) {{
    for (let j = i + 1; j < len; j++) {{
      const dx = currentPositions[i].x - currentPositions[j].x;
      const dy = currentPositions[i].y - currentPositions[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < MAX_CONN_DIST) {{
        const lineOpacity = (1 - dist / MAX_CONN_DIST) * 0.75;
        lines.push({{
          x1: currentPositions[i].x,
          y1: currentPositions[i].y,
          x2: currentPositions[j].x,
          y2: currentPositions[j].y,
          lineOpacity,
        }});
      }}
    }}
  }}

  return (
    <div
      style={{{{
        width: '100%',
        height: '100%',
        backgroundColor: BASE_COLOR,
        position: 'relative',
        overflow: 'hidden',
        opacity,
      }}}}
    >
      <svg
        style={{{{
          width: '100%',
          height: '100%',
          position: 'absolute',
          inset: 0,
        }}}}
        viewBox="0 0 3840 2160"
      >
        {f'''<defs>
          <filter id="glow-{comp_name}" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>''' if has_glow else ''}

        <g {f'filter="url(#glow-{comp_name})"' if has_glow else ''}>
          {{/* Plexus Connecting Lines */}}
          {{lines.map((line, idx) => (
            <line
              key={{idx}}
              x1={{line.x1}}
              y1={{line.y1}}
              x2={{line.x2}}
              y2={{line.y2}}
              stroke={{LINE_COLOR}}
              strokeWidth={{1.5}}
              strokeOpacity={{line.lineOpacity}}
            />
          ))}}

          {{/* Plexus Dots / Nodes */}}
          {{currentPositions.map((pos, idx) => (
            <circle
              key={{idx}}
              cx={{pos.x}}
              cy={{pos.y}}
              r={{DOT_SIZE}}
              fill={{DOT_COLOR}}
            />
          ))}}
        </g>
      </svg>

      {f'''{{/* Soft Vignette Overlay */}}
      <div
        style={{{{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at center, transparent 35%, rgba(0,0,0,0.7) 100%)',
          pointerEvents: 'none',
        }}}}
      />''' if has_vignette else ''}
    </div>
  );
}};
"""
    return code

def patch_root_tsx_clean(items):
    imports_list = ["import React from 'react';", "import { Composition } from 'remotion';"]
    comp_list = []

    for item in items:
        comp_name = item["comp_name"]
        imports_list.append(f"import {{ {comp_name} }} from './{comp_name}';")
        comp_list.append(f"""      <Composition
        id="{comp_name}"
        component={{{comp_name}}}
        durationInFrames={{{item['frames']}}}
        fps={{{item['fps']}}}
        width={{3840}}
        height={{2160}}
      />""")

    content = "\n".join(imports_list) + "\n\nexport const RemotionRoot: React.FC = () => {\n  return (\n    <>\n" + "\n".join(comp_list) + "\n    </>\n  );\n};\n"
    ROOT_TSX.write_text(content, encoding="utf-8")
    log(f"Cleanly updated Root.tsx with {len(items)} compositions.")

def render_item(item):
    comp_name = item["comp_name"]
    out_file = OUT_DIR / item["kebab_name"]
    if out_file.exists() and out_file.stat().st_size > 100000:
        log(f"SKIPPING {comp_name} — already rendered at {out_file.name}")
        return True

    log(f"Rendering [{item['id']}/100] {comp_name} -> {out_file.name} ({item['frames']} frames @ {item['fps']}fps)...")
    env = {**os.environ, "CI": "true"}

    for gl in ["angle", "swiftshader"]:
        cmd = [
            "npx.cmd" if sys.platform.startswith("win") else "npx",
            "remotion", "render",
            "src/index.ts",
            comp_name,
            str(out_file),
            "--codec=h264",
            "--video-bitrate=40M",
            "--pixel-format=yuv420p",
            "--color-space=bt709",
            f"--gl={gl}",
            "--muted",
            "--concurrency=8"
        ]
        res = subprocess.run(cmd, cwd=str(SCRIPT_DIR), env=env, capture_output=True, text=True)
        if res.returncode == 0 and out_file.exists() and out_file.stat().st_size > 0:
            size_mb = out_file.stat().st_size / (1024 * 1024)
            log(f"[OK] DONE {comp_name} ({size_mb:.1f} MB) via {gl}")
            return True
        else:
            log(f"WARN: Backend {gl} failed for {comp_name}: {res.stderr.strip()[:200]}")

    log(f"ERROR: Failed to render {comp_name}")
    return False

def blank_prompts_file():
    try:
        PROMPTS_FILE.write_text("\n", encoding="utf-8")
        log("Successfully blanked Prompts/Prompts.txt after completing all renders!")
    except Exception as e:
        log(f"Error blanking Prompts.txt: {e}")

def main():
    items = parse_prompts()
    log(f"=== Starting Batch Process for {len(items)} Prompts ===")
    
    for item in items:
        file_path = SRC_DIR / f"{item['comp_name']}.tsx"
        code = generate_plexus_tsx(item)
        file_path.write_text(code, encoding="utf-8")
    log(f"Generated {len(items)} TSX component files in src/")

    patch_root_tsx_clean(items)

    succeeded = 0
    failed = 0
    for item in items:
        ok = render_item(item)
        if ok:
            succeeded += 1
        else:
            failed += 1

    log(f"=== FINISHED ALL RENDERS: {succeeded} succeeded, {failed} failed out of {len(items)} ===")
    
    if succeeded == len(items):
        blank_prompts_file()

if __name__ == "__main__":
    main()
