#!/usr/bin/env python3
"""
레퍼런스 채널 분석 스크립트
- 채널의 인기 쇼츠 메타데이터 수집
- 제목 패턴, 조회수, 태그 분석
"""

import json
import subprocess
import sys
import os
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'channels.json')
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')


def run_ytdlp(args):
    cmd = ['yt-dlp'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr


def analyze_channel(channel):
    name = channel['name']
    url = channel['url']
    print(f"\n[분석 중] {name} ({url})")

    stdout, stderr = run_ytdlp([
        '--flat-playlist',
        '--dump-single-json',
        '--playlist-end', '20',
        '--no-warnings',
        url
    ])

    if not stdout.strip():
        print(f"  ⚠ 데이터 없음: {stderr[:200]}")
        return None

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        print(f"  ⚠ JSON 파싱 실패")
        return None

    entries = data.get('entries', [])
    if not entries:
        print(f"  ⚠ 영상 없음")
        return None

    videos = []
    for e in entries:
        if not e:
            continue
        videos.append({
            'id': e.get('id', ''),
            'title': e.get('title', ''),
            'url': f"https://www.youtube.com/shorts/{e.get('id', '')}",
            'duration': e.get('duration', 0),
            'view_count': e.get('view_count', 0),
            'like_count': e.get('like_count', 0),
            'upload_date': e.get('upload_date', ''),
        })

    # 조회수 순 정렬
    videos.sort(key=lambda x: x.get('view_count', 0), reverse=True)

    result = {
        'channel': name,
        'category': channel['category'],
        'total_analyzed': len(videos),
        'top_videos': videos[:10],
        'title_patterns': extract_title_patterns(videos),
        'analyzed_at': datetime.now().isoformat()
    }

    print(f"  ✓ {len(videos)}개 영상 분석 완료")
    for v in videos[:3]:
        print(f"    - [{v.get('view_count', 0):,}뷰] {v['title'][:50]}")

    return result


def extract_title_patterns(videos):
    titles = [v['title'] for v in videos if v.get('title')]

    # 자주 쓰이는 키워드 추출
    keywords = {}
    for title in titles:
        words = title.replace('|', ' ').replace('#', ' ').split()
        for word in words:
            word = word.strip('[](){}')
            if len(word) >= 2:
                keywords[word] = keywords.get(word, 0) + 1

    top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        'top_keywords': [{'word': k, 'count': v} for k, v in top_keywords],
        'avg_title_length': sum(len(t) for t in titles) // max(len(titles), 1),
        'sample_titles': titles[:5]
    }


def main():
    os.makedirs(LOGS_DIR, exist_ok=True)

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    channels = config['reference_channels']
    all_results = []

    print("=" * 60)
    print("레퍼런스 채널 분석 시작")
    print("=" * 60)

    for channel in channels:
        result = analyze_channel(channel)
        if result:
            all_results.append(result)

    output_path = os.path.join(LOGS_DIR, 'channel_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 분석 완료 → {output_path}")
    print(f"   총 {len(all_results)}/{len(channels)} 채널 분석됨")

    # 전체 인기 키워드 요약
    all_keywords = {}
    for r in all_results:
        for kw in r.get('title_patterns', {}).get('top_keywords', []):
            w = kw['word']
            all_keywords[w] = all_keywords.get(w, 0) + kw['count']

    top = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:15]
    print("\n📊 전체 인기 키워드:")
    for word, count in top:
        print(f"   {word}: {count}회")

    return all_results


if __name__ == '__main__':
    main()
