#!/usr/bin/env python3
"""
쇼츠 생성 스크립트
- 다운로드된 영상을 쇼츠 포맷(9:16, 1080x1920)으로 변환
- 자막, 텍스트 오버레이 추가
- 최대 60초로 자르기
"""

import os
import json
import subprocess
import argparse
import glob
from datetime import datetime

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), '..', 'downloads')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'channels.json')


def get_video_info(filepath):
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        filepath
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None


def convert_to_shorts(input_path, output_path, title="", max_duration=60, start_time=0):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    info = get_video_info(input_path)
    if not info:
        print(f"  ✗ 영상 정보 읽기 실패: {input_path}")
        return False

    # 영상 스트림 정보
    video_stream = None
    for s in info.get('streams', []):
        if s.get('codec_type') == 'video':
            video_stream = s
            break

    if not video_stream:
        print(f"  ✗ 비디오 스트림 없음")
        return False

    orig_w = int(video_stream.get('width', 1080))
    orig_h = int(video_stream.get('height', 1920))
    orig_ratio = orig_w / orig_h

    target_w, target_h = 1080, 1920
    target_ratio = target_w / target_h  # 9:16 = 0.5625

    # 필터 체인 구성
    if abs(orig_ratio - target_ratio) < 0.01:
        # 이미 9:16 비율
        vf = f"scale={target_w}:{target_h}"
    elif orig_ratio > target_ratio:
        # 가로가 더 넓음 (16:9 등) → 세로 맞추고 좌우 블러 배경
        vf = (
            f"split[orig][blur];"
            f"[blur]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},boxblur=20:20[bg];"
            f"[orig]scale=-1:{target_h}[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
    else:
        # 세로가 더 길거나 이미 세로형
        vf = f"scale={target_w}:-2,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"

    # 텍스트 오버레이 (제목이 있을 때)
    if title:
        safe_title = title[:40].replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")
        vf += (
            f",drawtext=text='{safe_title}'"
            f":fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h-80"
            f":shadowcolor=black:shadowx=2:shadowy=2"
        )

    cmd = [
        'ffmpeg',
        '-y',
        '-ss', str(start_time),
        '-i', input_path,
        '-t', str(max_duration),
        '-vf', vf,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        '-r', '30',
        output_path
    ]

    print(f"  🎬 변환: {os.path.basename(input_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ✓ 완료 ({size_mb:.1f}MB) → {os.path.basename(output_path)}")
        return True
    else:
        print(f"  ✗ 실패: {result.stderr[-300:]}")
        return False


def find_downloaded_videos():
    videos = []
    for ext in ['*.mp4', '*.webm', '*.mkv']:
        videos.extend(glob.glob(os.path.join(DOWNLOADS_DIR, '**', ext), recursive=True))
    return sorted(videos)


def load_video_title(video_path):
    info_path = video_path.rsplit('.', 1)[0] + '.info.json'
    if os.path.exists(info_path):
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('title', '')
        except:
            pass
    return os.path.basename(video_path).rsplit('.', 1)[0]


def main():
    parser = argparse.ArgumentParser(description='쇼츠 변환')
    parser.add_argument('--channel', help='특정 채널 폴더만 처리')
    parser.add_argument('--max-duration', type=int, default=60, help='최대 길이(초)')
    parser.add_argument('--start', type=int, default=0, help='시작 시간(초)')
    parser.add_argument('--no-title', action='store_true', help='제목 오버레이 제거')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    videos = find_downloaded_videos()

    if args.channel:
        videos = [v for v in videos if args.channel.lower() in v.lower()]

    if not videos:
        print("❌ 다운로드된 영상이 없습니다.")
        print(f"   먼저 download_videos.py를 실행하세요.")
        return

    print("=" * 60)
    print(f"쇼츠 변환 시작: {len(videos)}개 영상")
    print("=" * 60)

    success = 0
    fail = 0

    for video_path in videos:
        # 채널 폴더명 추출
        rel_path = os.path.relpath(video_path, DOWNLOADS_DIR)
        parts = rel_path.split(os.sep)
        channel_folder = parts[0] if len(parts) > 1 else 'unknown'

        # 출력 경로
        video_id = os.path.basename(video_path).rsplit('.', 1)[0]
        output_path = os.path.join(OUTPUT_DIR, channel_folder, f"shorts_{video_id}.mp4")

        if os.path.exists(output_path):
            print(f"  ⏭ 이미 존재: {os.path.basename(output_path)}")
            success += 1
            continue

        title = "" if args.no_title else load_video_title(video_path)

        ok = convert_to_shorts(
            video_path,
            output_path,
            title=title,
            max_duration=args.max_duration,
            start_time=args.start
        )

        if ok:
            success += 1
        else:
            fail += 1

    print(f"\n✅ 완료: 성공 {success}개 / 실패 {fail}개")
    print(f"   출력 위치: {OUTPUT_DIR}")

    # 출력 파일 목록
    out_files = glob.glob(os.path.join(OUTPUT_DIR, '**', '*.mp4'), recursive=True)
    print(f"   총 쇼츠 파일: {len(out_files)}개")


if __name__ == '__main__':
    main()
