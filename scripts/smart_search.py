#!/usr/bin/env python3
"""
레퍼런스 채널 패턴 기반 스마트 탐색

실제 채널 분석 결과 반영:
  - KIOFJUDY:   KISS OF LIFE 전문, 비주얼/황당/해외반응
  - 연예덕후:   연예인 일상 클립, 반응 모음
  - Iso_iso:    사건·이슈 재편집, 반전 사연
  - 숏뽕닷컴:  K팝 해외반응, 블랙핑크·추성훈 등 대중적 인물
  - hifunny:    아이돌 비주얼·웃긴 순간 (에스파·아이브·르세라핌 등)
"""

import json
import subprocess
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from scoring_engine import rank_videos, print_ranking, compute_score

ANALYSIS_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'channel_analysis.json')
LOGS_DIR      = os.path.join(os.path.dirname(__file__), '..', 'logs')

# ── 레퍼런스 채널 분석으로 확인된 아이돌/인물 ──────────────────
CONFIRMED_IDOLS = [
    # 직접 확인된 그룹/인물
    "Kiss of Life", "KISS OF LIFE", "키스오브라이프",
    "aespa", "에스파", "카리나", "윈터", "닝닝", "지젤",
    "IVE", "아이브", "안유진", "장원영", "리즈", "레이",
    "LE SSERAFIM", "르세라핌", "카즈하", "채원", "은채",
    "BLACKPINK", "블랙핑크", "지수", "제니", "로제", "리사",
    "TWICE", "트와이스", "사나", "나연", "지효",
    "NMIXX", "엔믹스", "오해원", "설윤",
    "NewJeans", "뉴진스", "민지", "하니", "다니엘",
    "BTS", "방탄소년단",
    "Stray Kids", "스트레이키즈",
    "SEVENTEEN", "세븐틴",
    "ENHYPEN", "엔하이픈",
    "NCT", "엔시티",
    # 연예인 (실제 채널에서 확인)
    "추성훈", "김채연", "리센느",
]

# ── 히트 패턴별 검색 쿼리 템플릿 ──────────────────────────────
# 실제 채널의 인기 영상 패턴 그대로 반영
QUERY_TEMPLATES = [
    # 비주얼 충격 (hifunny 1.6M뷰 패턴)
    "{idol} pretty fancam shorts",
    "{idol} 직캠 세로캠 shorts",
    "{idol} 비주얼 충격 shorts",
    "아이돌 비주얼 top tier shorts",

    # 황당/반전 (KIOFJUDY 3.4M뷰 패턴)
    "{idol} 황당 반응 shorts",
    "{idol} unexpected reaction shorts",
    "아이돌 반전 모음 shorts",
    "아이돌 말실수 황당 shorts",

    # 해외 시각 (숏뽕닷컴 899K 패턴)
    "{idol} 해외반응 shorts",
    "{idol} foreigner reaction shorts",
    "K팝 해외반응 모음 shorts",
    "kpop reaction compilation shorts",

    # 궁금증 유발 (숏뽕닷컴 "못하는 이유" 패턴)
    "아이돌 {action} 이유 shorts",
    "{idol} 다른 이유 shorts",
    "아이돌 왜 shorts",

    # 감동/눈물 (숏뽕닷컴 추성훈 230K 패턴)
    "아이돌 감동 눈물 shorts",
    "연예인 감동 순간 shorts",

    # 재미 (hifunny 채널 전체 패턴)
    "{idol} funny moment shorts",
    "{idol} 웃긴 순간 shorts",
    "아이돌 예능 웃긴 shorts",

    # 직접 채널 패턴 복제
    "키스오브라이프 쇼츠",
    "에스파 쇼츠",
    "아이브 쇼츠",
    "르세라핌 쇼츠",
    "블랙핑크 쇼츠",
    "트와이스 쇼츠",
]

# 쿼리에 넣을 아이돌 (상위 인기 그룹만)
FILL_IDOLS = [
    "KISS OF LIFE", "aespa", "IVE", "LE SSERAFIM",
    "BLACKPINK", "TWICE", "NewJeans", "NMIXX",
]

FILL_ACTIONS = ["못하는", "포기", "다른", "진짜"]

EXCLUDE_KEYWORDS = ["광고", "sponsored", "advertisement", "라이브 방송", "live stream"]


def build_search_queries() -> list:
    queries = []

    # 아이돌 × 쿼리 템플릿 조합
    for template in QUERY_TEMPLATES:
        if "{idol}" in template and "{action}" not in template:
            for idol in FILL_IDOLS[:5]:
                queries.append(template.format(idol=idol))
        elif "{action}" in template:
            for idol in FILL_IDOLS[:3]:
                for action in FILL_ACTIONS[:2]:
                    queries.append(template.format(idol=idol, action=action))
        else:
            queries.append(template)

    # 채널 분석 결과 키워드 추가
    if os.path.exists(ANALYSIS_PATH):
        try:
            with open(ANALYSIS_PATH, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            for ch in analysis:
                for kw in ch.get('title_patterns', {}).get('top_keywords', [])[:5]:
                    word = kw['word']
                    if len(word) >= 2:
                        queries.append(f"{word} shorts")
        except Exception:
            pass

    # 중복 제거 + 순서 유지
    seen, unique = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique


def search_youtube(query: str, max_results: int = 20) -> list:
    search_url = f"ytsearch{max_results}:{query} #shorts"

    cmd = [
        'python3', '-m', 'yt_dlp',
        '--flat-playlist',
        '--dump-single-json',
        '--no-warnings',
        search_url
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

    entries = data.get('entries', []) or []
    videos = []

    for e in entries:
        if not e:
            continue
        title = e.get('title', '') or ''
        if any(ex.lower() in title.lower() for ex in EXCLUDE_KEYWORDS):
            continue

        vid_id = e.get('id', '')
        videos.append({
            'id':            vid_id,
            'title':         title,
            'url':           f"https://www.youtube.com/shorts/{vid_id}",
            'webpage_url':   e.get('webpage_url') or f"https://www.youtube.com/shorts/{vid_id}",
            'duration':      e.get('duration', 0),
            'view_count':    e.get('view_count', 0),
            'like_count':    e.get('like_count', 0),
            'comment_count': e.get('comment_count', 0),
            'upload_date':   e.get('upload_date', ''),
            'channel':       e.get('channel', ''),
            'search_query':  query,
        })

    return videos


def run_smart_search(max_per_query: int = 15, top_n: int = 20,
                     extra_keywords: list = None, verbose: bool = True) -> list:
    queries = build_search_queries()

    if extra_keywords:
        for kw in extra_keywords:
            queries.insert(0, f"{kw} shorts")

    if verbose:
        print(f"\n검색 쿼리 {len(queries)}개 준비")
        print("  카테고리별 쿼리 예시:")
        for q in queries[:8]:
            print(f"    · {q}")
        print(f"    ... 외 {max(0, len(queries)-8)}개")

    all_videos = {}

    for i, query in enumerate(queries, 1):
        if verbose:
            print(f"\n[{i}/{len(queries)}] {query}")

        videos = search_youtube(query, max_results=max_per_query)
        new = sum(1 for v in videos if v['id'] and v['id'] not in all_videos)
        for v in videos:
            if v['id'] and v['id'] not in all_videos:
                all_videos[v['id']] = v

        if verbose:
            print(f"  → {len(videos)}개 발견 / {new}개 신규 (누적 {len(all_videos)}개)")

    all_list = list(all_videos.values())

    if verbose:
        print(f"\n총 수집: {len(all_list)}개")

    ranked, filtered = rank_videos(all_list, top_n=top_n)

    if verbose:
        print(f"필터 탈락: {len(filtered)}개 | 최종 선별: {len(ranked)}개")
        print_ranking(ranked)

        # 패턴 분포 출력
        pattern_dist = {}
        for v in ranked:
            for p in v.get('matched_patterns', []):
                pattern_dist[p] = pattern_dist.get(p, 0) + 1
        if pattern_dist:
            print("\n선별 영상 패턴 분포:")
            for pat, cnt in sorted(pattern_dist.items(), key=lambda x: -x[1]):
                print(f"  {pat}: {cnt}개")

    return ranked


def save_results(ranked: list, path: str = None) -> str:
    if not path:
        path = os.path.join(LOGS_DIR, 'smart_search_results.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)

    output = []
    for v in ranked:
        output.append({
            'rank':             ranked.index(v) + 1,
            'score':            v.get('score'),
            'title':            v.get('title'),
            'url':              v.get('webpage_url') or v.get('url'),
            'views':            v.get('views') or v.get('view_count'),
            'viral_speed':      v.get('viral_speed'),
            'engagement':       v.get('engagement'),
            'title_score':      v.get('title_score'),
            'matched_patterns': v.get('matched_patterns'),
            'days_old':         v.get('days_old'),
            'channel':          v.get('channel'),
            'search_query':     v.get('search_query'),
        })

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 결과 저장 → {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description='스마트 쇼츠 탐색')
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--per-query', type=int, default=15)
    parser.add_argument('--keywords', nargs='+')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    print("=" * 60)
    print("스마트 탐색 (레퍼런스 채널 패턴 적용)")
    print("=" * 60)

    ranked = run_smart_search(
        max_per_query=args.per_query,
        top_n=args.top,
        extra_keywords=args.keywords,
        verbose=not args.quiet,
    )
    save_results(ranked)


if __name__ == '__main__':
    main()
