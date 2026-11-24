#!/usr/bin/env python3
"""
레퍼런스 채널 키워드 기반 유사 영상 탐색

흐름:
  1. 채널 분석 결과에서 인기 키워드/아이돌명 추출
  2. yt-dlp ytsearch로 유사 쇼츠 검색
  3. scoring_engine으로 점수 계산
  4. 상위 영상 목록 반환
"""

import json
import subprocess
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from scoring_engine import rank_videos, print_ranking, compute_score, is_eligible

ANALYSIS_PATH  = os.path.join(os.path.dirname(__file__), '..', 'logs', 'channel_analysis.json')
LOGS_DIR       = os.path.join(os.path.dirname(__file__), '..', 'logs')
CONFIG_PATH    = os.path.join(os.path.dirname(__file__), '..', 'config', 'channels.json')

# 기본 검색어 (분석 결과가 없을 때 폴백)
DEFAULT_KEYWORDS = [
    "아이돌 쇼츠",
    "K팝 직캠 shorts",
    "아이돌 웃긴 순간",
    "K팝 해외반응 shorts",
    "연예인 쇼츠",
    "아이돌 funny moment",
]

# 필터 패턴 (제목에 이게 있으면 제외)
EXCLUDE_KEYWORDS = [
    "광고", "sponsored", "advertisement",
    "라이브", "live stream",
]

# 아이돌 그룹 / 키워드 (채널 분석에서 추가 보완)
IDOL_GROUPS = [
    "KISS OF LIFE", "키오브라이프",
    "aespa", "에스파",
    "NewJeans", "뉴진스",
    "IVE", "아이브",
    "LE SSERAFIM", "르세라핌",
    "BLACKPINK", "블랙핑크",
    "TWICE", "트와이스",
    "BTS", "방탄소년단",
    "SEVENTEEN", "세븐틴",
    "Stray Kids", "스트레이키즈",
    "NCT", "엔시티",
    "EXO", "엑소",
    "ENHYPEN", "엔하이픈",
    "TXT", "투모로우바이투게더",
    "ITZY", "있지",
    "Red Velvet", "레드벨벳",
]


def load_analysis_keywords(top_n=15) -> list[str]:
    """채널 분석 결과에서 인기 키워드 추출"""
    if not os.path.exists(ANALYSIS_PATH):
        return []

    with open(ANALYSIS_PATH, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    keyword_counts = {}
    for ch in analysis:
        for kw in ch.get('title_patterns', {}).get('top_keywords', []):
            word = kw['word']
            count = kw['count']
            # 아이돌 그룹명과 매칭되는 키워드 가중치 2배
            if any(idol.lower() in word.lower() for idol in IDOL_GROUPS):
                count *= 2
            keyword_counts[word] = keyword_counts.get(word, 0) + count

    top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    return [k for k, _ in top_keywords[:top_n]]


def build_search_queries(extra_keywords: list[str] = None) -> list[str]:
    """검색 쿼리 목록 생성"""
    analysis_keywords = load_analysis_keywords()

    queries = []

    # 1. 분석 키워드 + "shorts" 조합
    for kw in analysis_keywords[:8]:
        if len(kw) >= 2:
            queries.append(f"{kw} shorts")

    # 2. 아이돌 그룹 + 액션 조합
    action_words = ["직캠", "funny", "reaction", "무대", "댄스", "fancam"]
    for group in IDOL_GROUPS[:6]:
        for action in action_words[:2]:
            queries.append(f"{group} {action} shorts")

    # 3. 기본 검색어
    queries.extend(DEFAULT_KEYWORDS)

    # 4. 추가 키워드
    if extra_keywords:
        queries.extend(extra_keywords)

    # 중복 제거
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique


def search_youtube(query: str, max_results: int = 20) -> list[dict]:
    """yt-dlp로 유튜브 쇼츠 검색 → 메타데이터 목록"""
    search_url = f"ytsearch{max_results}:{query} #shorts"

    cmd = [
        'yt-dlp',
        '--flat-playlist',
        '--dump-single-json',
        '--no-warnings',
        search_url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
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

        title = e.get('title', '')

        # 제외 키워드 체크
        if any(ex.lower() in title.lower() for ex in EXCLUDE_KEYWORDS):
            continue

        videos.append({
            'id':            e.get('id', ''),
            'title':         title,
            'url':           e.get('url') or f"https://www.youtube.com/watch?v={e.get('id', '')}",
            'webpage_url':   e.get('webpage_url') or f"https://www.youtube.com/shorts/{e.get('id', '')}",
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
                     extra_keywords: list = None, verbose: bool = True) -> list[dict]:
    """
    전체 스마트 탐색 실행
    → 쿼리별 검색 → 점수 계산 → 중복 제거 → 상위 N개
    """
    queries = build_search_queries(extra_keywords)

    if verbose:
        print(f"\n검색 쿼리 {len(queries)}개:")
        for q in queries[:10]:
            print(f"  · {q}")
        if len(queries) > 10:
            print(f"  ... 외 {len(queries)-10}개")

    all_videos = {}  # id → video (중복 제거)

    for i, query in enumerate(queries, 1):
        if verbose:
            print(f"\n[{i}/{len(queries)}] 검색: {query}")

        videos = search_youtube(query, max_results=max_per_query)
        new = 0
        for v in videos:
            vid_id = v['id']
            if vid_id and vid_id not in all_videos:
                all_videos[vid_id] = v
                new += 1

        if verbose:
            print(f"  → {len(videos)}개 발견, {new}개 신규")

    all_list = list(all_videos.values())

    if verbose:
        print(f"\n총 수집: {len(all_list)}개 (중복 제거 후)")

    ranked, filtered = rank_videos(all_list, top_n=top_n)

    if verbose:
        print(f"필터 탈락: {len(filtered)}개")
        print(f"최종 선별: {len(ranked)}개\n")
        print_ranking(ranked)

    return ranked


def save_results(ranked: list[dict], path: str = None):
    if not path:
        path = os.path.join(LOGS_DIR, 'smart_search_results.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)

    output = []
    for v in ranked:
        output.append({
            'rank':         ranked.index(v) + 1,
            'score':        v.get('score'),
            'title':        v.get('title'),
            'url':          v.get('webpage_url') or v.get('url'),
            'views':        v.get('views') or v.get('view_count'),
            'viral_speed':  v.get('viral_speed'),
            'engagement':   v.get('engagement'),
            'days_old':     v.get('days_old'),
            'channel':      v.get('channel'),
            'search_query': v.get('search_query'),
        })

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 탐색 결과 저장 → {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description='스마트 쇼츠 탐색')
    parser.add_argument('--top', type=int, default=20, help='최종 선별 수 (기본: 20)')
    parser.add_argument('--per-query', type=int, default=15, help='쿼리당 검색 수')
    parser.add_argument('--keywords', nargs='+', help='추가 검색 키워드')
    parser.add_argument('--quiet', action='store_true', help='간략 출력')
    args = parser.parse_args()

    print("=" * 60)
    print("스마트 쇼츠 탐색 시작")
    print("=" * 60)

    ranked = run_smart_search(
        max_per_query=args.per_query,
        top_n=args.top,
        extra_keywords=args.keywords,
        verbose=not args.quiet
    )

    save_results(ranked)
    return ranked


if __name__ == '__main__':
    main()
