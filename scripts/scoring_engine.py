#!/usr/bin/env python3
"""
영상 바이럴 점수 계산 엔진

점수 구성:
  - 바이럴 속도 (50%): views ÷ 업로드 경과일  → 현재 뜨는 영상
  - 참여율     (30%): (likes + comments) ÷ views × 100
  - 최신성     (20%): 14일 이내 업로드 가중치

필터 기준:
  - 조회수 최소 10,000회 이상
  - 좋아요율 0.5% 이상
  - 길이 60초 이하 (Shorts)
  - 업로드 후 90일 이내
"""

from datetime import datetime, timedelta
import math


# ── 임계값 (config로 뺄 수 있음) ──────────────────────────────
MIN_VIEWS        = 10_000   # 최소 조회수
MIN_LIKE_RATIO   = 0.005   # 최소 좋아요율 0.5%
MAX_DURATION     = 60      # 최대 영상 길이(초)
MAX_AGE_DAYS     = 90      # 최대 업로드 경과일
VIRAL_WINDOW     = 14      # 최신성 기준일 (14일 이내 = 보너스)


def parse_date(upload_date_str):
    """yt-dlp 날짜 형식(YYYYMMDD) → datetime"""
    if not upload_date_str:
        return None
    try:
        return datetime.strptime(str(upload_date_str), "%Y%m%d")
    except ValueError:
        return None


def days_since_upload(upload_date_str):
    dt = parse_date(upload_date_str)
    if not dt:
        return 999
    return max((datetime.now() - dt).days, 1)


def viral_speed(views, days_old):
    """일당 조회수 (바이럴 속도)"""
    return views / max(days_old, 1)


def engagement_rate(views, likes, comments):
    """참여율 (%)"""
    if not views:
        return 0
    return ((likes or 0) + (comments or 0)) / views * 100


def recency_score(days_old):
    """최신성 점수 0~1 (14일 이내 = 1, 90일 이후 = 0)"""
    if days_old <= VIRAL_WINDOW:
        return 1.0
    if days_old >= MAX_AGE_DAYS:
        return 0.0
    return 1.0 - (days_old - VIRAL_WINDOW) / (MAX_AGE_DAYS - VIRAL_WINDOW)


def normalize_log(value, scale=1_000_000):
    """로그 스케일 정규화 (0~1)"""
    if value <= 0:
        return 0
    return min(math.log10(value + 1) / math.log10(scale + 1), 1.0)


def compute_score(video: dict) -> dict:
    """
    영상 메타데이터 dict → 점수 dict 반환

    입력 필드: id, title, view_count, like_count, comment_count,
               duration, upload_date, webpage_url
    """
    views    = video.get('view_count', 0) or 0
    likes    = video.get('like_count', 0) or 0
    comments = video.get('comment_count', 0) or 0
    duration = video.get('duration', 0) or 0
    upload   = video.get('upload_date', '')

    days_old  = days_since_upload(upload)
    v_speed   = viral_speed(views, days_old)
    eng_rate  = engagement_rate(views, likes, comments)
    rec_score = recency_score(days_old)
    like_ratio = likes / max(views, 1)

    # 정규화
    viral_norm = normalize_log(v_speed, scale=500_000)   # 일당 50만뷰 = 최고
    eng_norm   = min(eng_rate / 10.0, 1.0)               # 10% = 최고

    # 가중 합산
    total = (
        viral_norm * 0.50 +
        eng_norm   * 0.30 +
        rec_score  * 0.20
    )

    return {
        'score':        round(total, 4),
        'viral_speed':  round(v_speed),
        'engagement':   round(eng_rate, 2),
        'recency':      round(rec_score, 2),
        'days_old':     days_old,
        'like_ratio':   round(like_ratio * 100, 2),
        'views':        views,
        'likes':        likes,
        'comments':     comments,
        'duration':     duration,
    }


def is_eligible(video: dict) -> tuple[bool, str]:
    """
    필터 통과 여부 → (bool, 탈락사유)
    """
    views    = video.get('view_count', 0) or 0
    likes    = video.get('like_count', 0) or 0
    duration = video.get('duration', 0) or 0
    upload   = video.get('upload_date', '')
    days_old = days_since_upload(upload)
    like_ratio = likes / max(views, 1)

    if views < MIN_VIEWS:
        return False, f"조회수 부족 ({views:,} < {MIN_VIEWS:,})"
    if duration > MAX_DURATION:
        return False, f"길이 초과 ({duration}초 > {MAX_DURATION}초)"
    if days_old > MAX_AGE_DAYS:
        return False, f"오래된 영상 ({days_old}일 경과)"
    if like_ratio < MIN_LIKE_RATIO:
        return False, f"좋아요율 낮음 ({like_ratio*100:.2f}% < {MIN_LIKE_RATIO*100:.1f}%)"

    return True, ""


def rank_videos(videos: list[dict], top_n: int = 10) -> list[dict]:
    """
    영상 목록 → 점수 계산 → 필터 → 상위 N개 반환
    """
    scored = []
    filtered_out = []

    for v in videos:
        ok, reason = is_eligible(v)
        if not ok:
            filtered_out.append({'title': v.get('title', '')[:40], 'reason': reason})
            continue

        s = compute_score(v)
        scored.append({**v, **s})

    scored.sort(key=lambda x: x['score'], reverse=True)

    return scored[:top_n], filtered_out


def print_ranking(ranked: list[dict], show_n: int = 10):
    print(f"\n{'순위':<4} {'점수':<6} {'바이럴속도':>10} {'참여율':>7} {'최신성':>6} {'조회수':>10}  제목")
    print("─" * 90)
    for i, v in enumerate(ranked[:show_n], 1):
        title = (v.get('title') or '')[:35]
        print(
            f"{i:<4} {v['score']:<6.3f} "
            f"{v['viral_speed']:>10,.0f} "
            f"{v['engagement']:>6.1f}% "
            f"{v['recency']:>6.2f} "
            f"{v['views']:>10,}  "
            f"{title}"
        )


if __name__ == '__main__':
    # 간단 테스트
    test_videos = [
        {'id': 'a', 'title': '인기 영상 A', 'view_count': 500000, 'like_count': 15000,
         'comment_count': 800, 'duration': 45, 'upload_date': '20241110'},
        {'id': 'b', 'title': '오래된 영상 B', 'view_count': 2000000, 'like_count': 50000,
         'comment_count': 2000, 'duration': 55, 'upload_date': '20240101'},
        {'id': 'c', 'title': '최신 바이럴 C', 'view_count': 300000, 'like_count': 20000,
         'comment_count': 1500, 'duration': 30, 'upload_date': '20241115'},
        {'id': 'd', 'title': '조회수 낮음 D', 'view_count': 5000, 'like_count': 100,
         'comment_count': 10, 'duration': 60, 'upload_date': '20241112'},
    ]
    ranked, filtered = rank_videos(test_videos)
    print_ranking(ranked)
    print(f"\n필터 탈락: {len(filtered)}개")
    for f in filtered:
        print(f"  - {f['title']}: {f['reason']}")
