#!/usr/bin/env python3
"""
레퍼런스 채널 직접 다운로드
- 5개 채널에서 최신 영상 N개씩 다운로드
- 조회수 필터 적용
"""

import json
import subprocess
import os
import sys
import argparse

CHANNELS = [
    {"name": "KIOFJUDY",    "url": "https://www.youtube.com/@KIOFJUDY/shorts"},
    {"name": "연예덕후",     "url": "https://www.youtube.com/@yydukhu/shorts"},
    {"name": "Iso_iso",     "url": "https://www.youtube.com/@Iso_iso/shorts"},
    {"name": "숏뽕닷컴",    "url": "https://www.youtube.com/@shortppong/shorts"},
    {"name": "hifunny",     "url": "https://www.youtube.com/@hifunny/shorts"},
]

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), '..', 'downloads', 'channels')
MIN_VIEWS = 50_000


def get_channel_videos(channel_url: str, max_count: int = 20) -> list:
    cmd = [
        'python3', '-m', 'yt_dlp',
        '--flat-playlist',
        '--dump-single-json',
        '--no-warnings',
        '--playlist-end', str(max_count),
        channel_url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    videos = []
    for e in (data.get('entries') or []):
        if not e:
            continue
        vid_id = e.get('id', '')
        view_count = e.get('view_count', 0) or 0
        if view_count < MIN_VIEWS:
            continue
        videos.append({
            'id':          vid_id,
            'title':       e.get('title', ''),
            'url':         f"https://www.youtube.com/shorts/{vid_id}",
            'view_count':  view_count,
            'upload_date': e.get('upload_date', ''),
            'duration':    e.get('duration', 0) or 0,
        })
    return videos


def already_downloaded(video_id: str, output_dir: str) -> bool:
    for f in os.listdir(output_dir):
        if video_id in f and f.endswith('.mp4'):
            return True
    return False


def download_video(video: dict, output_dir: str) -> bool:
    url = video['url']
    views = video.get('view_count', 0)
    output_template = os.path.join(output_dir, f"views{views}_%(id)s.%(ext)s")

    cmd = [
        'python3', '-m', 'yt_dlp',
        '-f', 'bestvideo[ext=mp4][height<=1920]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '-o', output_template,
        '--no-playlist',
        '--no-warnings',
        '--progress',
        '--socket-timeout', '30',
        url
    ]
    result = subprocess.run(cmd, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=5, help='채널당 다운로드 수 (기본: 5)')
    parser.add_argument('--fetch', type=int, default=30, help='채널당 조회할 영상 수 (기본: 30)')
    args = parser.parse_args()

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    total_ok = 0
    total_fail = 0

    for ch in CHANNELS:
        name = ch['name']
        url  = ch['url']
        ch_dir = os.path.join(DOWNLOADS_DIR, name)
        os.makedirs(ch_dir, exist_ok=True)

        print(f"\n{'='*50}")
        print(f"채널: {name}")
        print(f"{'='*50}")

        videos = get_channel_videos(url, max_count=args.fetch)
        # 조회수 내림차순
        videos.sort(key=lambda x: x['view_count'], reverse=True)
        to_dl = videos[:args.count]

        if not to_dl:
            print(f"  → 영상 없음 (조회수 {MIN_VIEWS:,} 이상)")
            continue

        print(f"  조회수 상위 {len(to_dl)}개 선별:")
        for v in to_dl:
            print(f"    [{v['view_count']:>10,}뷰] {v['title'][:50]}")

        print()
        for i, v in enumerate(to_dl, 1):
            vid_id = v['id']
            title  = v['title'][:45]
            views  = v['view_count']

            print(f"  [{i}/{len(to_dl)}] {views:,}뷰 | {title}")

            if already_downloaded(vid_id, ch_dir):
                print(f"    ⏭ 이미 존재")
                total_ok += 1
                continue

            ok = download_video(v, ch_dir)
            if ok:
                print(f"    ✓ 완료")
                total_ok += 1
            else:
                print(f"    ✗ 실패")
                total_fail += 1

    print(f"\n{'='*50}")
    print(f"완료: 성공 {total_ok}개 / 실패 {total_fail}개")
    print(f"저장 위치: {DOWNLOADS_DIR}")


if __name__ == '__main__':
    main()
