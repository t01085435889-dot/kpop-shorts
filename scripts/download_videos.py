#!/usr/bin/env python3
"""
영상 다운로드 스크립트
- 채널 분석 결과를 바탕으로 인기 쇼츠 다운로드
- yt-dlp 사용
"""

import json
import subprocess
import sys
import os
import argparse

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'channels.json')
ANALYSIS_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'channel_analysis.json')
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), '..', 'downloads')


def download_video(video_url, output_dir, filename_prefix=""):
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, f"{filename_prefix}%(id)s.%(ext)s")

    cmd = [
        'yt-dlp',
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '-o', output_template,
        '--no-playlist',
        '--write-info-json',
        '--no-warnings',
        '--progress',
        video_url
    ]

    print(f"  ⬇ 다운로드: {video_url}")
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"  ✓ 완료")
        return True
    else:
        print(f"  ✗ 실패")
        return False


def download_from_channel(channel_url, channel_name, max_count=5):
    output_dir = os.path.join(DOWNLOADS_DIR, channel_name.replace(' ', '_'))
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, '%(id)s.%(ext)s')

    cmd = [
        'yt-dlp',
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '-o', output_template,
        '--playlist-end', str(max_count),
        '--write-info-json',
        '--no-warnings',
        '--progress',
        channel_url
    ]

    print(f"\n[다운로드] {channel_name}")
    print(f"  URL: {channel_url}")
    result = subprocess.run(cmd, text=True)

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='쇼츠 다운로드')
    parser.add_argument('--channel', help='특정 채널만 다운로드 (채널명)')
    parser.add_argument('--count', type=int, default=5, help='채널당 다운로드 수 (기본: 5)')
    parser.add_argument('--use-analysis', action='store_true', help='분석 결과 기반 다운로드')
    args = parser.parse_args()

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    channels = config['reference_channels']
    max_count = args.count

    print("=" * 60)
    print(f"영상 다운로드 시작 (채널당 {max_count}개)")
    print("=" * 60)

    if args.use_analysis and os.path.exists(ANALYSIS_PATH):
        # 분석 결과 기반: 조회수 높은 영상 다운로드
        with open(ANALYSIS_PATH, 'r', encoding='utf-8') as f:
            analysis = json.load(f)

        for ch_data in analysis:
            ch_name = ch_data['channel']
            if args.channel and args.channel not in ch_name:
                continue

            top_videos = ch_data.get('top_videos', [])[:max_count]
            output_dir = os.path.join(DOWNLOADS_DIR, ch_name.replace(' ', '_'))

            print(f"\n[{ch_name}] 인기 영상 {len(top_videos)}개 다운로드")
            for v in top_videos:
                download_video(v['url'], output_dir, prefix=f"{v.get('view_count', 0)}_")
    else:
        # 채널 URL 직접 다운로드
        for ch in channels:
            if args.channel and args.channel not in ch['name']:
                continue
            download_from_channel(ch['url'], ch['name'], max_count)

    print("\n✅ 다운로드 완료")
    print(f"   저장 위치: {DOWNLOADS_DIR}")

    # 다운로드된 파일 목록
    total_files = 0
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        mp4_files = [f for f in files if f.endswith('.mp4')]
        total_files += len(mp4_files)

    print(f"   총 {total_files}개 영상 다운로드됨")


if __name__ == '__main__':
    main()
