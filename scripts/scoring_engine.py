#!/usr/bin/env python3
"""
영상 바이럴 점수 계산 엔진 (여자 아이돌 / 남성 시청자 타겟)

점수 구성:
  - 바이럴 속도 (40%): views / 경과일
  - 참여율     (25%): (likes+comments) / views × 100
  - 최신성     (15%): 14일 이내 보너스
  - 제목 패턴  (20%): 타겟 패턴 키워드 매칭

필터:
  - 조회수 10,000 이상
  - 좋아요율 0.5% 이상
  - 길이 60초 이하
  - 90일 이내 업로드
"""

from datetime import datetime, timedelta
import math

# ── 임계값 ────────────────────────────────────────────────────
MIN_VIEWS      = 10_000
MIN_LIKE_RATIO = 0.005
MAX_DURATION   = 60
MAX_AGE_DAYS   = 90
VIRAL_WINDOW   = 14

# ── 타겟 여자 아이돌 그룹 / 멤버 ──────────────────────────────
FEMALE_IDOLS = [
    # 그룹명
    "aespa", "에스파", "IVE", "아이브", "LE SSERAFIM", "르세라핌",
    "BLACKPINK", "블랙핑크", "TWICE", "트와이스", "NewJeans", "뉴진스",
    "KISS OF LIFE", "키스오브라이프", "Red Velvet", "레드벨벳",
    "ITZY", "있지", "NMIXX", "엔믹스", "Kep1er", "케플러",
    "tripleS", "트리플에스", "ILLIT", "아일릿", "BABYMONSTER",
    "fromis_9", "프로미스나인", "SECRET NUMBER",
    # 인기 멤버
    "카리나", "karina", "윈터", "winter", "닝닝", "지젤",
    "안유진", "장원영", "wonyoung", "리즈", "가을", "이서",
    "카즈하", "kazuha", "채원", "허윤진", "사쿠라",
    "지수", "jisoo", "제니", "jennie", "로제", "rose", "리사", "lisa",
    "사나", "sana", "나연", "nayeon", "쯔위", "tzuyu", "지효",
    "민지", "하니", "hani", "다니엘", "혜인", "혜린",
    "벨", "나티", "줄리", "소아",
    "아이린", "슬기", "조이", "웬디",
    "미야오", "miyao", "ella",
]

# ── 히트 패턴 (남성 시청자 선호 기준) ─────────────────────────
TITLE_PATTERNS = {
    "직캠_퍼포먼스": (
        # 가장 높은 가중치 - 직캠은 남성 팬 핵심 콘텐츠
        ["직캠", "fancam", "세로캠", "4k", "4K", "직캠모음",
         "무대", "stage", "퍼포먼스", "performance", "choreography",
         "직촬", "직찍", "현장"],
        0.95,
    ),
    "비주얼_비율": (
        # hifunny 1.6M 패턴 - 외모/몸매 강조
        ["비율", "비주얼", "예쁜", "pretty", "beautiful", "얼굴",
         "미모", "미녀", "완벽", "화보", "top tier", "레전드 비주얼",
         "몸매", "뒤태", "각선미", "허리"],
        0.92,
    ),
    "댄스_섹시": (
        # 댄스 + 매력적인 순간
        ["댄스", "dance", "춤", "안무", "choreography",
         "섹시", "sexy", "매력", "끈적", "치명적", "치명",
         "걸크러쉬", "girl crush", "파워풀", "강렬"],
        0.90,
    ),
    "귀엽_발랄": (
        ["귀여운", "cute", "귀염", "깜찍", "사랑스러운",
         "lovely", "adorable", "웃음", "미소", "리액션",
         "당황", "부끄러운", "수줍"],
        0.75,
    ),
    "황당_반전": (
        # KIOFJUDY 3.4M 패턴
        ["반전", "황당", "충격", "실화", "대박", "헐",
         "unexpected", "shocking", "wtf", "crazy", "말실수",
         "갑자기", "어떻게"],
        0.85,
    ),
    "궁금증_유발": (
        # 숏뽕닷컴 "못하는 이유" 패턴
        ["이유", "때문에", "왜", "다른", "진짜", "못하는",
         "why", "reason", "차이", "비밀", "알고보니", "사실",
         "포기 못하는", "남다른"],
        0.80,
    ),
    "실력_감탄": (
        # KIOFJUDY "음색으로 극락 감" 패턴
        ["극락", "레전드", "미쳤", "대단", "올라운더", "실력",
         "음색", "보법", "춤선", "legendary", "insane", "goat",
         "vocals", "best", "역대급"],
        0.78,
    ),
    "해외_시각": (
        # 해외팬 반응 - 외국 시각으로 K팝 보기
        ["해외반응", "외국인", "reaction", "foreigner", "overseas",
         "foreign", "외국", "해외"],
        0.82,
    ),
}


# ── 날짜 유틸 ──────────────────────────────────────────────────
def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s), "%Y%m%d")
    except ValueError:
        return None

def days_since_upload(s):
    dt = parse_date(s)
    if not dt:
        return 999
    return max((datetime.now() - dt).days, 1)


# ── 개별 점수 ─────────────────────────────────────────────────
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

def title_pattern_score(title: str) -> tuple:
    if not title:
        return 0.0, []
    t = title.lower()
    matched, max_w = [], 0.0
    for cat, (keywords, weight) in TITLE_PATTERNS.items():
        for kw in keywords:
            if kw.lower() in t:
                matched.append(cat)
                max_w = max(max_w, weight)
                break
    # 여자 아이돌 언급 보너스
    idol_bonus = 0.0
    for idol in FEMALE_IDOLS:
        if idol.lower() in t:
            idol_bonus = 0.08
            break
    bonus = min(len(set(matched)) * 0.05, 0.15) + idol_bonus
    return min(max_w + bonus, 1.0), list(set(matched))


# ── 메인 점수 ─────────────────────────────────────────────────
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
def is_eligible(video: dict) -> tuple:
    views      = video.get('view_count', 0) or 0
    likes      = video.get('like_count', 0) or 0
    duration   = video.get('duration', 0) or 0
    upload     = video.get('upload_date', '')
    days_old   = days_since_upload(upload)
    like_ratio = likes / max(views, 1)

    if views < MIN_VIEWS:
        return False, f"조회수 부족 ({views:,})"
    if duration > MAX_DURATION:
        return False, f"길이 초과 ({duration}초)"
    if days_old > MAX_AGE_DAYS:
        return False, f"오래된 영상 ({days_old}일)"
    if like_ratio < MIN_LIKE_RATIO:
        return False, f"좋아요율 낮음 ({like_ratio*100:.2f}%)"
    return True, ""


def rank_videos(videos: list, top_n: int = 10) -> tuple:
    scored, filtered_out = [], []
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
    print(f"\n{'순위':<4} {'점수':<6} {'바이럴속도':>10} {'참여율':>7} {'제목패턴':>8} {'조회수':>10}  매칭패턴 / 제목")
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
    def daysago(n):
        return (datetime.now() - timedelta(days=n)).strftime("%Y%m%d")

    tests = [
        {'id':'a','title':'에스파 카리나 직캠 4K 세로캠 치명적인 댄스','view_count':850_000,'like_count':62_000,'comment_count':4_200,'duration':45,'upload_date':daysago(4)},
        {'id':'b','title':'청바지 완판시키려는 에스파 카리나 뒤태 #shorts','view_count':302_000,'like_count':18_000,'comment_count':1_200,'duration':38,'upload_date':daysago(2)},
        {'id':'c','title':'아이브 원영턴과 다른 마라맛 안유진 턴 #shorts','view_count':363_000,'like_count':21_000,'comment_count':1_800,'duration':38,'upload_date':daysago(3)},
        {'id':'d','title':'What happens when your daughter is too pretty? Miyao Ella','view_count':1_600_000,'like_count':80_000,'comment_count':5_000,'duration':35,'upload_date':daysago(5)},
        {'id':'e','title':'브랜드들이 블핑 포기 못하는 이유','view_count':899_000,'like_count':42_000,'comment_count':3_200,'duration':50,'upload_date':daysago(12)},
        {'id':'f','title':'르세라핌 카즈하 무대 직캠 legendary dance','view_count':520_000,'like_count':35_000,'comment_count':2_800,'duration':55,'upload_date':daysago(7)},
        {'id':'g','title':'뉴진스 하니 귀여운 리액션 모음','view_count':180_000,'like_count':14_000,'comment_count':900,'duration':42,'upload_date':daysago(1)},
    ]
    ranked, filtered = rank_videos(tests, top_n=10)
    print_ranking(ranked)
    print(f"\n필터 탈락: {len(filtered)}개")
