#!/usr/bin/env python3
"""
여자 아이돌 / 남성 시청자 타겟 스마트 탐색

검색 전략:
  1. 직캠·세로캠 (가장 높은 조회수 보장)
  2. 비주얼·비율 충격 (hifunny 1.6M 패턴)
  3. 댄스·퍼포먼스 하이라이트
  4. 황당·반전·매력 순간 포착
  5. 해외팬 반응
"""

import json
import subprocess
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from scoring_engine import rank_videos, print_ranking, FEMALE_IDOLS

ANALYSIS_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'channel_analysis.json')
LOGS_DIR      = os.path.join(os.path.dirname(__file__), '..', 'logs')

# ── 타겟 그룹 (조회수 검증된 그룹만) ─────────────────────────
TARGET_GROUPS = [
    "aespa",        "에스파",
    "IVE",          "아이브",
    "LE SSERAFIM",  "르세라핌",
    "BLACKPINK",    "블랙핑크",
    "TWICE",        "트와이스",
    "NewJeans",     "뉴진스",
    "KISS OF LIFE", "키스오브라이프",
    "Red Velvet",   "레드벨벳",
    "NMIXX",        "엔믹스",
    "ILLIT",        "아일릿",
    "BABYMONSTER",
    "tripleS",
    "Kep1er",
]

# 영어 그룹명만 (해외 검색용)
EN_GROUPS = [
    "aespa", "IVE", "LE SSERAFIM", "BLACKPINK",
    "TWICE", "NewJeans", "KISS OF LIFE", "Red Velvet",
    "NMIXX", "ILLIT", "BABYMONSTER",
]

# 인기 멤버 (단독 검색용)
HOT_MEMBERS = [
    "카리나", "karina",
    "안유진", "장원영", "wonyoung",
    "카즈하", "kazuha",
    "제니", "jennie", "리사", "lisa",
    "사나", "sana", "쯔위", "tzuyu",
    "하니", "hani",
    "벨",
]

EXCLUDE_KEYWORDS = ["광고", "sponsored", "라이브 방송", "live stream", "먹방", "브이로그", "vlog"]


def build_search_queries(extra_keywords: list = None) -> list:
    queries = []

    # ── 카테고리 1: 직캠·세로캠 (최우선) ────────────────────────
    for group in TARGET_GROUPS[:10]:
        queries.append(f"{group} 직캠 shorts")
        queries.append(f"{group} fancam shorts")
    for group in EN_GROUPS[:6]:
        queries.append(f"{group} 4K fancam vertical shorts")
    queries += [
        "여자아이돌 직캠 모음 shorts",
        "kpop female idol fancam compilation shorts",
        "아이돌 세로캠 4K shorts",
    ]

    # ── 카테고리 2: 비주얼·비율 (hifunny 패턴) ─────────────────
    for group in TARGET_GROUPS[:8]:
        queries.append(f"{group} 비주얼 shorts")
    for member in HOT_MEMBERS[:8]:
        queries.append(f"{member} 비율 shorts")
    queries += [
        "여자아이돌 비율 레전드 shorts",
        "kpop idol pretty moments shorts",
        "아이돌 미모 충격 shorts",
        "female idol visual compilation shorts",
    ]

    # ── 카테고리 3: 댄스·퍼포먼스 ──────────────────────────────
    for group in EN_GROUPS[:6]:
        queries.append(f"{group} dance performance shorts")
    queries += [
        "여자아이돌 댄스 치명적 shorts",
        "kpop girl group sexy dance shorts",
        "아이돌 안무 명장면 shorts",
        "여자아이돌 걸크러쉬 무대 shorts",
        "kpop female idol powerful stage shorts",
    ]

    # ── 카테고리 4: 매력 순간 포착 (반전·황당) ─────────────────
    for group in TARGET_GROUPS[:6]:
        queries.append(f"{group} 황당 반응 shorts")
    queries += [
        "아이돌 반전 매력 shorts",
        "kpop idol unexpected charming moment shorts",
        "여자아이돌 치명적 순간 shorts",
        "아이돌 귀여운 반응 모음 shorts",
        "kpop idol cute reaction compilation shorts",
    ]

    # ── 카테고리 5: 해외반응 ────────────────────────────────────
    for group in EN_GROUPS[:5]:
        queries.append(f"{group} foreigner reaction shorts")
    queries += [
        "kpop female idol reaction shorts",
        "여자아이돌 해외반응 shorts",
        "non kpop fan reacts female idol shorts",
    ]

    # ── 카테고리 6: 멤버 단독 ───────────────────────────────────
    for member in HOT_MEMBERS[:10]:
        queries.append(f"{member} shorts")

    # ── 추가 키워드 ─────────────────────────────────────────────
    if extra_keywords:
        for kw in extra_keywords:
            queries.insert(0, f"{kw} shorts")

    # 중복 제거
    seen, unique = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique


def search_youtube(query: str, max_results: int = 20) -> list:
    cmd = [
        'python3', '-m', 'yt_dlp',
        '--flat-playlist',
        '--dump-single-json',
        '--no-warnings',
        f"ytsearch{max_results}:{query} #shorts"
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
    queries = build_search_queries(extra_keywords)

    if verbose:
        print(f"\n검색 쿼리 {len(queries)}개")
        cats = ["직캠·세로캠", "비주얼·비율", "댄스·퍼포먼스", "매력순간", "해외반응", "멤버단독"]
        print(f"  카테고리: {' / '.join(cats)}")
        print("  예시:")
        for q in queries[:6]:
            print(f"    · {q}")
        print(f"    ... 외 {len(queries)-6}개\n")

    all_videos = {}

    for i, query in enumerate(queries, 1):
        if verbose:
            print(f"[{i:>3}/{len(queries)}] {query}")

        videos = search_youtube(query, max_results=max_per_query)
        new = 0
        for v in videos:
            if v['id'] and v['id'] not in all_videos:
                all_videos[v['id']] = v
                new += 1

        if verbose and new > 0:
            print(f"       → {new}개 신규 (누적 {len(all_videos)}개)")

    all_list = list(all_videos.values())
    if verbose:
        print(f"\n총 수집: {len(all_list)}개")

    ranked, filtered = rank_videos(all_list, top_n=top_n)

    if verbose:
        print(f"필터 탈락: {len(filtered)}개 | 최종 선별: {len(ranked)}개")
        print_ranking(ranked)

        # 패턴 분포
        dist = {}
        for v in ranked:
            for p in v.get('matched_patterns', []):
                dist[p] = dist.get(p, 0) + 1
        if dist:
            print("\n선별 영상 패턴 분포:")
            for p, c in sorted(dist.items(), key=lambda x: -x[1]):
                bar = "█" * c
                print(f"  {p:<20} {bar} {c}개")

    return ranked


def save_results(ranked: list, path: str = None) -> str:
    if not path:
        path = os.path.join(LOGS_DIR, 'smart_search_results.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    output = [{
        'rank':             i + 1,
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
    } for i, v in enumerate(ranked)]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 결과 저장 → {path}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--per-query', type=int, default=15)
    parser.add_argument('--keywords', nargs='+')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    print("=" * 60)
    print("여자 아이돌 쇼츠 스마트 탐색")
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
