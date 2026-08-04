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
        
        title_match = re.match(r'^(\d+)\.\s*(.+)$', lines[0])
        if not title_match:
            continue
        
        prompt_id = int(title_match.group(1))
        title = title_match.group(2)
        desc = lines[1] if len(lines) > 1 else ""
        
        words = re.sub(r'[^a-zA-Z0-9 ]', ' ', title).split()
        comp_name = "".join(w.capitalize() for w in words)
        
        kebab_name = re.sub(r'(?<!^)(?=[A-Z])', '-', comp_name).lower() + ".mp4"
        
        fps_m = re.search(r'(\d+)fps', desc)
        fps = int(fps_m.group(1)) if fps_m else 60
        
        frames_m = re.search(r'(\d+)\s*frames', desc)
        frames = int(frames_m.group(1)) if frames_m else 240
        
        blur_m = re.search(r'blur\s*(\d+)px', desc)
        blur = int(blur_m.group(1)) if blur_m else 220
        
        blobs_m = re.search(r'(\d+)\s+(?:blurred\s+)?blobs', desc, re.IGNORECASE)
        blobs_count = int(blobs_m.group(1)) if blobs_m else 5
        
        colors_part = desc
        base_color = "#0a0a14"
        if "on base" in desc:
            parts = desc.split("on base")
            colors_part = parts[0]
            base_m = re.search(r'#([0-9a-fA-F]{6})', parts[1])
            if base_m:
                base_color = "#" + base_m.group(1)
        
        hex_colors = re.findall(r'#([0-9a-fA-F]{6})', colors_part)
        if base_color[1:] in hex_colors and len(hex_colors) > 1:
            hex_colors.remove(base_color[1:])
        hex_colors = ["#" + c for c in hex_colors]
        if not hex_colors:
            hex_colors = ["#ff9a5a", "#ff6b6b", "#ffd280", "#c8467a", "#ffb37a"]
            
        has_vignette = "vignette" in desc.lower()
        has_grain = "grain" in desc.lower()
        has_breathe = "breathe" in desc.lower() or "scale" in desc.lower()
        
        parsed.append({
            "id": prompt_id,
            "title": title,
            "comp_name": comp_name,
            "kebab_name": kebab_name,
            "fps": fps,
            "frames": frames,
            "blur": blur,
            "blobs_count": blobs_count,
            "colors": hex_colors,
            "base_color": base_color,
            "has_vignette": has_vignette,
            "has_grain": has_grain,
            "has_breathe": has_breathe,
            "desc": desc
        })
    return parsed

def generate_tsx(item):
    comp_name = item["comp_name"]
    blobs_count = item["blobs_count"]
    colors = item["colors"]
    base_color = item["base_color"]
    blur = item["blur"]
    has_vignette = item["has_vignette"]
    has_grain = item["has_grain"]
    has_breathe = item["has_breathe"]
    
    blob_configs = []
    num_colors = len(colors)
    for i in range(blobs_count):
        color = colors[i % num_colors]
        cx = 1920 + ((i - (blobs_count - 1) / 2.0) * 380)
        cy = 1080 + (((i % 3) - 1) * 280)
        size = 850 + (i * 120) % 500
        rx = 320 + (i * 110) % 380
        ry = 260 + (i * 85) % 320
        freq1 = 1.0 + (i % 3) * 0.5
        freq2 = 1.2 + (i % 2) * 0.4
        phase = round(i * (6.28318 / max(blobs_count, 1)), 3)
        blob_configs.append({
            "color": color,
            "cx": cx,
            "cy": cy,
            "size": size,
            "rx": rx,
            "ry": ry,
            "phase": phase,
            "freq1": freq1,
            "freq2": freq2,
            "opacity": round(0.78 + (i % 3) * 0.08, 2)
        })

    blob_js = json.dumps(blob_configs, indent=2)

    code = f"""import React from 'react';
import {{ useCurrentFrame, useVideoConfig, interpolate }} from 'remotion';

const BASE_COLOR = '{base_color}';
const BLUR_PX = {blur};
const BLOBS = {blob_js};

export const {comp_name}: React.FC = () => {{
  const frame = useCurrentFrame();
  const {{ durationInFrames, width, height }} = useVideoConfig();

  // Seamless 360-degree loop progress (0 to 2*PI)
  const loopProgress = (frame / durationInFrames) * Math.PI * 2;

  // Smooth fade-in (first 50 frames) and fade-out (last 50 frames)
  const fadeIn = interpolate(frame, [0, 50], [0, 1], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
  const fadeOut = interpolate(frame, [durationInFrames - 50, durationInFrames], [1, 0], {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }});
  const opacity = fadeIn * fadeOut;

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
      {{/* Gradient Blobs Layer */}}
      <div
        style={{{{
          position: 'absolute',
          inset: -250,
          filter: `blur(${{BLUR_PX}}px)`,
          transform: 'scale(1.15)',
        }}}}
      >
        {{BLOBS.map((blob, idx) => {{
          // Sin/Cos seamless drifting paths
          const offsetX = Math.sin(loopProgress * blob.freq1 + blob.phase) * blob.rx;
          const offsetY = Math.cos(loopProgress * blob.freq2 + blob.phase) * blob.ry;
          
          {"const scale = 1 + 0.1 * Math.sin(loopProgress * 2 + blob.phase);" if has_breathe else "const scale = 1;"}

          return (
            <div
              key={{idx}}
              style={{{{
                position: 'absolute',
                left: blob.cx + offsetX - blob.size / 2,
                top: blob.cy + offsetY - blob.size / 2,
                width: blob.size,
                height: blob.size,
                borderRadius: '50%',
                backgroundColor: blob.color,
                opacity: blob.opacity,
                transform: `scale(${{scale}})`,
                mixBlendMode: idx % 2 === 0 ? 'screen' : 'normal',
              }}}}
            />
          );
        }})}}
      </div>

      {f'''{{/* Film Grain Overlay */}}
      <svg
        style={{{{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          opacity: 0.06,
          pointerEvents: 'none',
          mixBlendMode: 'overlay',
        }}}}
      >
        <filter id="grain-{comp_name}">
          <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain-{comp_name})" />
      </svg>''' if has_grain else ''}

      {f'''{{/* Soft Vignette Overlay */}}
      <div
        style={{{{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.65) 100%)',
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

    log(f"Rendering [{item['id']}/50] {comp_name} -> {out_file.name} ({item['frames']} frames @ {item['fps']}fps)...")
    env = {**os.environ, "CI": "true"}

    for gl in ["angle", "swiftshader"]:
        cmd = [
            "npx.cmd" if sys.platform.startswith("win") else "npx",
            "remotion", "render",
            "src/index.ts",
            comp_name,
            str(out_file),
            f"--gl={gl}",
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

def main():
    items = parse_prompts()
    log(f"=== Starting Clean Process for {len(items)} Prompts ===")
    
    for item in items:
        file_path = SRC_DIR / f"{item['comp_name']}.tsx"
        code = generate_tsx(item)
        file_path.write_text(code, encoding="utf-8")
    log("Generated 50 TSX component files in src/")

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

if __name__ == "__main__":
    main()
