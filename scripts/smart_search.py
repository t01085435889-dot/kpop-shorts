#!/usr/bin/env python3
"""
여자 아이돌 스마트 탐색 (의외의 글래머 · 반전 볼륨감 포커스)

검색 전략:
  1. 반전·글래머 (핵심: 의외의 볼륨감, 베이글)
  2. 직캠·세로캠 (고조회수 보장)
  3. 비율·피지컬 (핫바디, S라인)
  4. 댄스·퍼포먼스 하이라이트
  5. 멤버 단독 (제공 목록 기반)
  6. 해외반응
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

# ── 타겟 그룹 (전체 목록) ─────────────────────────────────────
TARGET_GROUPS = [
    # 4~5세대 (높은 조회수)
    "aespa", "에스파",
    "IVE", "아이브",
    "LE SSERAFIM", "르세라핌",
    "BLACKPINK", "블랙핑크",
    "TWICE", "트와이스",
    "NewJeans", "뉴진스",
    "KISS OF LIFE", "키스오브라이프",
    "ITZY", "있지",
    "NMIXX", "엔믹스",
    "BABYMONSTER",
    "ILLIT", "아일릿",
    "tripleS",
    "Kep1er", "케플러",
    # 3세대 (레전드급 반전 글래머)
    "Red Velvet", "레드벨벳",
    "MAMAMOO", "마마무",
    "오마이걸",
    "VIVIZ", "비비지",
    "우주소녀",
    "fromis_9", "프로미스나인",
    "STAYC", "스테이씨",
    # 반전 글래머 특화 그룹
    "브브걸",
    "에이핑크",
    "소녀시대",
    "QWER",
    "cignature", "시그니처",
    # 5세대 신인
    "IZNA", "이즈나",
    "Miyao", "미야오",
]

EN_GROUPS = [
    "aespa", "IVE", "LE SSERAFIM", "BLACKPINK", "TWICE", "NewJeans",
    "KISS OF LIFE", "Red Velvet", "NMIXX", "ILLIT", "BABYMONSTER",
    "MAMAMOO", "ITZY", "VIVIZ", "fromis_9", "STAYC", "Kep1er",
]

# ── 핵심 멤버 (의외의 글래머 목록 기반) ──────────────────────
HOT_MEMBERS_KR = [
    # 에스파
    "카리나", "닝닝",
    # 아이브
    "장원영", "안유진", "리즈",
    # 르세라핌
    "카즈하", "허윤진",
    # 블랙핑크
    "제니", "지수", "리사", "로제",
    # 트와이스
    "사나", "쯔위", "모모", "지효",
    # 키스오브라이프
    "나띠", "쥴리", "벨",
    # 레드벨벳
    "조이", "슬기", "아이린", "예리",
    # 있지
    "유나", "채령",
    # 마마무
    "화사", "솔라",
    # 오마이걸
    "아린", "유아",
    # 브브걸
    "유정", "민영",
    # 에이핑크
    "손나은", "오하영", "김남주",
    # 소녀시대
    "서현", "유리",
    # 우주소녀
    "보나", "설아",
    # 비비지
    "은하", "신비", "엄지",
    # 솔로
    "화사", "권은비", "전소미", "청하", "선미",
    # 뉴진스
    "하니",
]

HOT_MEMBERS_EN = [
    "karina", "wonyoung", "kazuha", "jennie", "lisa", "jisoo",
    "sana", "tzuyu", "momo", "nayeon", "hani",
]

EXCLUDE_KEYWORDS = [
    "광고", "sponsored", "라이브 방송", "live stream",
    "먹방", "브이로그", "vlog", "게임", "광고영상",
]


def build_search_queries(extra_keywords: list = None) -> list:
    queries = []

    # ── 카테고리 1: 반전·글래머 (최우선) ──────────────────────
    for member in HOT_MEMBERS_KR[:15]:
        queries.append(f"{member} 반전 볼륨감 shorts")
        queries.append(f"{member} 글래머 비율 shorts")
    queries += [
        "여자아이돌 의외의 글래머 shorts",
        "아이돌 반전 볼륨감 shorts",
        "여자아이돌 베이글녀 shorts",
        "아이돌 숨겨진 볼륨 shorts",
        "여자아이돌 반전매력 볼륨감 shorts",
        "kpop idol unexpected glamour shorts",
        "kpop female idol hidden volume shorts",
        "아이돌 의외의 비율 shorts",
        "여자아이돌 글래머 반전 shorts",
        "화사 볼륨감 shorts",
        "권은비 볼륨 shorts",
        "나띠 비율 shorts",
        "유나 있지 비율 shorts",
        "손나은 반전 shorts",
        "아린 오마이걸 반전 shorts",
        "서현 반전 글래머 shorts",
        "브브걸 볼륨감 shorts",
    ]

    # ── 카테고리 2: 직캠·세로캠 ───────────────────────────────
    for group in TARGET_GROUPS[:12]:
        queries.append(f"{group} 직캠 shorts")
    for group in EN_GROUPS[:8]:
        queries.append(f"{group} fancam shorts")
        queries.append(f"{group} 4K fancam vertical shorts")
    queries += [
        "여자아이돌 직캠 모음 shorts",
        "kpop female idol fancam compilation shorts",
        "아이돌 세로캠 4K shorts",
    ]

    # ── 카테고리 3: 비율·핫바디 ──────────────────────────────
    for group in TARGET_GROUPS[:10]:
        queries.append(f"{group} 비율 shorts")
    for member in HOT_MEMBERS_KR[:12]:
        queries.append(f"{member} 비율 shorts")
    queries += [
        "여자아이돌 비율 레전드 shorts",
        "아이돌 핫바디 shorts",
        "여자아이돌 S라인 비율 shorts",
        "아이돌 몸매 반전 shorts",
        "kpop idol body ratio shorts",
        "female idol figure shorts",
        "여자아이돌 각선미 shorts",
        "아이돌 허리 비율 shorts",
    ]

    # ── 카테고리 4: 댄스·퍼포먼스 ───────────────────────────
    for group in EN_GROUPS[:8]:
        queries.append(f"{group} dance performance shorts")
    queries += [
        "여자아이돌 댄스 치명적 shorts",
        "kpop girl group sexy dance shorts",
        "아이돌 안무 명장면 shorts",
        "여자아이돌 걸크러쉬 무대 shorts",
        "kpop female idol powerful stage shorts",
        "여자아이돌 섹시댄스 shorts",
    ]

    # ── 카테고리 5: 멤버 단독 (제공 목록 전체) ──────────────
    for member in HOT_MEMBERS_KR:
        queries.append(f"{member} shorts")
    for member in HOT_MEMBERS_EN:
        queries.append(f"{member} shorts")

    # ── 카테고리 6: 해외반응 ─────────────────────────────────
    for group in EN_GROUPS[:6]:
        queries.append(f"{group} foreigner reaction shorts")
    queries += [
        "kpop female idol reaction shorts",
        "여자아이돌 해외반응 shorts",
        "non kpop fan reacts female idol shorts",
    ]

    # ── 추가 키워드 ──────────────────────────────────────────
    if extra_keywords:
        for kw in extra_keywords:
            queries.insert(0, f"{kw} shorts")

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
        cats = ["반전글래머", "직캠·세로캠", "비율·핫바디", "댄스·퍼포먼스", "멤버단독", "해외반응"]
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
    print("여자 아이돌 쇼츠 스마트 탐색 (반전 글래머 포커스)")
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
