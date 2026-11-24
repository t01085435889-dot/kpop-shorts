#!/usr/bin/env python3
"""
스마트 다운로드 스크립트
- smart_search 결과 기반으로 선별된 영상만 다운로드
- 점수 순 정렬, 중복 방지, 실패 재시도
"""

import json
import subprocess
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.dirname(__file__))
from smart_search import run_smart_search, save_results

SEARCH_RESULTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'smart_search_results.json')
DOWNLOADS_DIR       = os.path.join(os.path.dirname(__file__), '..', 'downloads', 'smart')
LOGS_DIR            = os.path.join(os.path.dirname(__file__), '..', 'logs')


def already_downloaded(video_id: str) -> bool:
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        for f in files:
            if video_id in f and f.endswith('.mp4'):
                return True
    return False


def download_video(video: dict, output_dir: str, retry: int = 2) -> bool:
    url      = video.get('url') or video.get('webpage_url', '')
    video_id = video.get('id', '') or video.get('url', '').split('=')[-1]
    score    = video.get('score', 0)
    title    = (video.get('title', '') or '')[:50]

    if not url:
        print(f"  ✗ URL 없음")
        return False

    # 파일명: 점수_조회수_id.mp4
    views = video.get('views') or video.get('view_count', 0)
    prefix = f"score{score:.3f}_views{views}"
    output_template = os.path.join(output_dir, f"{prefix}_%(id)s.%(ext)s")

    cmd = [
        'yt-dlp',
        '-f', 'bestvideo[ext=mp4][height<=1920]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '-o', output_template,
        '--no-playlist',
        '--write-info-json',
        '--no-warnings',
        '--progress',
        '--socket-timeout', '30',
        url
    ]

    for attempt in range(1, retry + 2):
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            return True
        if attempt <= retry:
            print(f"  재시도 {attempt}/{retry}...")
            time.sleep(2)

    return False


def main():
    parser = argparse.ArgumentParser(description='스마트 다운로드')
    parser.add_argument('--top', type=int, default=10, help='다운로드할 영상 수 (기본: 10)')
    parser.add_argument('--use-cached', action='store_true', help='이전 탐색 결과 재사용')
    parser.add_argument('--keywords', nargs='+', help='추가 검색 키워드')
    parser.add_argument('--min-score', type=float, default=0.1, help='최소 점수 (기본: 0.1)')
    args = parser.parse_args()

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

    # 탐색 결과 로드 또는 새로 실행
    if args.use_cached and os.path.exists(SEARCH_RESULTS_PATH):
        print(f"캐시된 탐색 결과 사용: {SEARCH_RESULTS_PATH}")
        with open(SEARCH_RESULTS_PATH, 'r', encoding='utf-8') as f:
            candidates = json.load(f)
    else:
        print("=" * 60)
        print("STEP 1: 스마트 탐색")
        print("=" * 60)
        candidates = run_smart_search(
            max_per_query=15,
            top_n=args.top * 2,  # 여유분 탐색
            extra_keywords=args.keywords,
            verbose=True
        )
        save_results(candidates)

    # 최소 점수 필터
    candidates = [v for v in candidates if v.get('score', 0) >= args.min_score]

    # 다운로드 대상 선별
    to_download = candidates[:args.top]

    print("\n" + "=" * 60)
    print(f"STEP 2: 다운로드 ({len(to_download)}개)")
    print("=" * 60)

    if not to_download:
        print("❌ 다운로드할 영상이 없습니다.")
        return

    print(f"\n선별된 영상 목록:")
    for i, v in enumerate(to_download, 1):
        title = (v.get('title', '') or '')[:45]
        score = v.get('score', 0)
        views = v.get('views') or v.get('view_count', 0)
        speed = v.get('viral_speed', 0)
        eng   = v.get('engagement', 0)
        print(f"  {i:2}. [점수 {score:.3f}] [{views:>10,}뷰] [일당{speed:>8,.0f}] [{eng:.1f}%참여] {title}")

    print()

    success = 0
    fail    = 0
    skipped = 0

    for i, video in enumerate(to_download, 1):
        video_id = video.get('id', '') or ''
        title    = (video.get('title', '') or '')[:50]
        score    = video.get('score', 0)
        views    = video.get('views') or video.get('view_count', 0)

        print(f"\n[{i}/{len(to_download)}] 점수 {score:.3f} | {views:,}뷰")
        print(f"  제목: {title}")

        if video_id and already_downloaded(video_id):
            print(f"  ⏭ 이미 다운로드됨 (ID: {video_id})")
            skipped += 1
            success += 1
            continue

        ok = download_video(video, DOWNLOADS_DIR)
        if ok:
            success += 1
            print(f"  ✓ 다운로드 완료")
        else:
            fail += 1
            print(f"  ✗ 다운로드 실패")

    print("\n" + "=" * 60)
    print(f"✅ 완료: 성공 {success}개 (스킵 {skipped}개) / 실패 {fail}개")
    print(f"   저장 위치: {DOWNLOADS_DIR}")

    # 결과 파일 목록
    mp4_files = []
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        for f in files:
            if f.endswith('.mp4'):
                mp4_files.append(os.path.join(root, f))

    print(f"   총 파일 수: {len(mp4_files)}개")


if __name__ == '__main__':
    main()
