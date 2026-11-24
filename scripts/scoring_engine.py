#!/usr/bin/env python3
"""
영상 바이럴 점수 계산 엔진

점수 구성 (레퍼런스 채널 실제 분석 기반):
  - 바이럴 속도 (40%): views / 경과일  → 지금 뜨는 영상
  - 참여율     (25%): (likes+comments) / views × 100
  - 최신성     (15%): 14일 이내 보너스
  - 제목 패턴  (20%): 히트 패턴 키워드 매칭

필터:
  - 조회수 10,000 이상
  - 좋아요율 0.5% 이상
  - 길이 60초 이하
  - 90일 이내 업로드
"""

from datetime import datetime
import math
import re

# ── 임계값 ────────────────────────────────────────────────────
MIN_VIEWS      = 10_000
MIN_LIKE_RATIO = 0.005
MAX_DURATION   = 60
MAX_AGE_DAYS   = 90
VIRAL_WINDOW   = 14

# ── 레퍼런스 채널 실제 분석으로 도출한 히트 제목 패턴 ──────────
# (키워드, 가중치 0~1)
TITLE_PATTERNS = {
    "비주얼_충격": (
        ["예쁜", "비주얼", "직캠", "비율", "완벽", "미모", "얼굴",
         "pretty", "beautiful", "fancam", "세로캠", "4k", "화보", "top tier"],
        0.90,
    ),
    "황당_반전": (
        ["반전", "황당", "갑자기", "말실수", "어떻게", "충격", "실화",
         "대박", "wtf", "unexpected", "shocking", "crazy", "헐"],
        0.85,
    ),
    "감동_눈물": (
        ["눈물", "감동", "오열", "은퇴", "마지막", "farewell",
         "emotional", "감격", "울었", "울컥"],
        0.80,
    ),
    "해외_시각": (
        ["해외반응", "외국인", "reaction", "foreigner", "overseas",
         "foreign", "해외", "외국"],
        0.85,
    ),
    "궁금증_유발": (
        ["이유", "때문에", "왜", "다른", "진짜", "못하는", "why",
         "reason", "차이", "비밀", "알고보니", "사실"],
        0.75,
    ),
    "재미_웃음": (
        ["웃긴", "funny", "웃음", "빵터짐", "개웃김", "유머",
         "예능", "망가짐", "당황"],
        0.70,
    ),
    "핫_트렌드": (
        ["핫", "hot", "화제", "난리", "인기", "trending",
         "viral", "요즘"],
        0.65,
    ),
    "실력_감탄": (
        # KIOFJUDY 채널 패턴: "음색으로 극락 감", "보법이 다른", "올라운더"
        ["극락", "레전드", "미쳤", "대단", "올라운더", "실력", "음색",
         "보법", "춤선", "퍼포먼스", "무대", "legendary", "insane",
         "vocals", "dance", "stage", "goat", "best"],
        0.72,
    ),
}


# ── 날짜 유틸 ──────────────────────────────────────────────────
def parse_date(upload_date_str):
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


# ── 개별 점수 함수 ─────────────────────────────────────────────
def viral_speed(views, days_old):
    return views / max(days_old, 1)


def engagement_rate(views, likes, comments):
    if not views:
        return 0
    return ((likes or 0) + (comments or 0)) / views * 100


def recency_score(days_old):
    if days_old <= VIRAL_WINDOW:
        return 1.0
    if days_old >= MAX_AGE_DAYS:
        return 0.0
    return 1.0 - (days_old - VIRAL_WINDOW) / (MAX_AGE_DAYS - VIRAL_WINDOW)


def normalize_log(value, scale=1_000_000):
    if value <= 0:
        return 0
    return min(math.log10(value + 1) / math.log10(scale + 1), 1.0)


def title_pattern_score(title: str) -> tuple[float, list[str]]:
    """
    제목이 히트 패턴에 얼마나 매칭되는지 점수 반환 (0~1)
    matched_categories도 함께 반환
    """
    if not title:
        return 0.0, []

    title_lower = title.lower()
    matched = []
    max_weight = 0.0

    for category, (keywords, weight) in TITLE_PATTERNS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                matched.append(category)
                max_weight = max(max_weight, weight)
                break

    # 복수 카테고리 매칭 보너스
    bonus = min(len(set(matched)) * 0.05, 0.15)
    score = min(max_weight + bonus, 1.0)

    return score, list(set(matched))


# ── 메인 점수 계산 ─────────────────────────────────────────────
def compute_score(video: dict) -> dict:
    views    = video.get('view_count', 0) or 0
    likes    = video.get('like_count', 0) or 0
    comments = video.get('comment_count', 0) or 0
    duration = video.get('duration', 0) or 0
    upload   = video.get('upload_date', '')
    title    = video.get('title', '') or ''

    days_old   = days_since_upload(upload)
    v_speed    = viral_speed(views, days_old)
    eng_rate   = engagement_rate(views, likes, comments)
    rec_score  = recency_score(days_old)
    like_ratio = likes / max(views, 1)
    t_score, matched_cats = title_pattern_score(title)

    viral_norm = normalize_log(v_speed, scale=500_000)
    eng_norm   = min(eng_rate / 10.0, 1.0)

    total = (
        viral_norm * 0.40 +
        eng_norm   * 0.25 +
        rec_score  * 0.15 +
        t_score    * 0.20
    )

    return {
        'score':            round(total, 4),
        'viral_speed':      round(v_speed),
        'engagement':       round(eng_rate, 2),
        'recency':          round(rec_score, 2),
        'title_score':      round(t_score, 2),
        'matched_patterns': matched_cats,
        'days_old':         days_old,
        'like_ratio':       round(like_ratio * 100, 2),
        'views':            views,
        'likes':            likes,
        'comments':         comments,
        'duration':         duration,
    }


# ── 필터 ──────────────────────────────────────────────────────
def is_eligible(video: dict) -> tuple[bool, str]:
    views      = video.get('view_count', 0) or 0
    likes      = video.get('like_count', 0) or 0
    duration   = video.get('duration', 0) or 0
    upload     = video.get('upload_date', '')
    days_old   = days_since_upload(upload)
    like_ratio = likes / max(views, 1)

    if views < MIN_VIEWS:
        return False, f"조회수 부족 ({views:,} < {MIN_VIEWS:,})"
    if duration > MAX_DURATION:
        return False, f"길이 초과 ({duration}초)"
    if days_old > MAX_AGE_DAYS:
        return False, f"오래된 영상 ({days_old}일)"
    if like_ratio < MIN_LIKE_RATIO:
        return False, f"좋아요율 낮음 ({like_ratio*100:.2f}%)"

    return True, ""


def rank_videos(videos: list, top_n: int = 10) -> tuple:
    scored = []
    filtered_out = []

    for v in videos:
        ok, reason = is_eligible(v)
        if not ok:
            filtered_out.append({'title': (v.get('title') or '')[:40], 'reason': reason})
            continue
        s = compute_score(v)
        scored.append({**v, **s})

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_n], filtered_out


def print_ranking(ranked: list, show_n: int = 10):
    header = f"{'순위':<4} {'점수':<6} {'바이럴속도':>10} {'참여율':>7} {'제목패턴':>8} {'조회수':>10}  매칭패턴 / 제목"
    print(f"\n{header}")
    print("─" * 110)
    for i, v in enumerate(ranked[:show_n], 1):
        title    = (v.get('title') or '')[:30]
        patterns = ','.join(v.get('matched_patterns', [])) or '-'
        print(
            f"{i:<4} {v['score']:<6.3f} "
            f"{v['viral_speed']:>10,.0f} "
            f"{v['engagement']:>6.1f}% "
            f"{v['title_score']:>8.2f} "
            f"{v['views']:>10,}  "
            f"[{patterns}] {title}"
        )


if __name__ == '__main__':
    today = datetime.now().strftime("%Y%m%d")
    # 날짜를 오늘 기준으로 세팅
    from datetime import timedelta
    def daysago(n):
        return (datetime.now() - timedelta(days=n)).strftime("%Y%m%d")

    test_videos = [
        {'id':'a','title':'What happens when your daughter is too pretty? Miyao Ella #shorts',
         'view_count':1_600_000,'like_count':80_000,'comment_count':5_000,'duration':35,'upload_date':daysago(5)},
        {'id':'b','title':'브랜드들이 블핑 포기 못하는 이유',
         'view_count':899_000,'like_count':42_000,'comment_count':3_200,'duration':50,'upload_date':daysago(12)},
        {'id':'c','title':'[키스오브라이프] 음색으로 극락 감',
         'view_count':1_600_000,'like_count':71_000,'comment_count':4_100,'duration':42,'upload_date':daysago(20)},
        {'id':'d','title':'아이브 원영턴과 다른 마라맛 안유진 턴 #shorts',
         'view_count':363_000,'like_count':21_000,'comment_count':1_800,'duration':38,'upload_date':daysago(3)},
        {'id':'e','title':'남자들은 안울수 없다는 추성훈 은퇴경기',
         'view_count':168_000,'like_count':12_000,'comment_count':2_300,'duration':58,'upload_date':daysago(8)},
        {'id':'f','title':'에스파 로켓펀처 카리나 퇴근 후 현실모습은? #shorts',
         'view_count':28_000,'like_count':1_400,'comment_count':190,'duration':45,'upload_date':daysago(2)},
        {'id':'g','title':'일반 아이돌 직캠',
         'view_count':50_000,'like_count':800,'comment_count':50,'duration':55,'upload_date':daysago(15)},
    ]

    ranked, filtered = rank_videos(test_videos)
    print_ranking(ranked)
    print(f"\n필터 탈락: {len(filtered)}개")
    for f in filtered:
        print(f"  - {f['title']}: {f['reason']}")
