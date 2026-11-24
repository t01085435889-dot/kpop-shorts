#!/usr/bin/env python3
"""
영상 바이럴 점수 계산 엔진 (여자 아이돌 / 남성 시청자 타겟)
포커스: 의외의 글래머 · 반전 볼륨감 · 베이글 아이돌
"""

from datetime import datetime, timedelta
import math

MIN_VIEWS      = 10_000
MIN_LIKE_RATIO = 0.005
MAX_DURATION   = 60
MAX_AGE_DAYS   = 90
VIRAL_WINDOW   = 14

# ── 타겟 아이돌 (제공 목록 전체 반영) ──────────────────────────
FEMALE_IDOLS = [
    # === 한국 아이돌 그룹 ===
    "aespa", "에스파",
    "IVE", "아이브",
    "LE SSERAFIM", "르세라핌",
    "BLACKPINK", "블랙핑크",
    "TWICE", "트와이스",
    "NewJeans", "뉴진스",
    "KISS OF LIFE", "키스오브라이프",
    "Red Velvet", "레드벨벳",
    "ITZY", "있지",
    "NMIXX", "엔믹스",
    "BABYMONSTER",
    "tripleS", "트리플에스",
    "ILLIT", "아일릿",
    "Kep1er", "케플러",
    "MAMAMOO", "마마무",
    "오마이걸", "OH MY GIRL",
    "브브걸", "BB Girls",
    "에이핑크", "Apink",
    "소녀시대", "Girls Generation",
    "SNSD",
    "있지", "ITZY",
    "비비지", "VIVIZ",
    "우주소녀", "WJSN",
    "프로미스나인", "fromis_9",
    "스테이씨", "STAYC",
    "시그니처", "cignature",
    "QWER",
    "하츠투하츠",
    "미야오", "Miyao",
    "이즈나", "IZNA",
    "키키", "Kiki",
    "SECRET NUMBER",
    "구구단", "gugudan",
    "다이아", "DIA",
    "아이즈원", "IZ*ONE",

    # === 한국 멤버 (에스파) ===
    "카리나", "karina", "닝닝", "윈터", "winter", "지젤",

    # === 한국 멤버 (아이브) ===
    "장원영", "wonyoung", "안유진", "리즈", "가을", "이서", "레이",

    # === 한국 멤버 (르세라핌) ===
    "카즈하", "kazuha", "허윤진", "김채원", "채원", "사쿠라", "eunchae",

    # === 한국 멤버 (블랙핑크) ===
    "제니", "jennie", "지수", "jisoo", "로제", "rose", "리사", "lisa",

    # === 한국 멤버 (트와이스) ===
    "사나", "sana", "나연", "nayeon", "쯔위", "tzuyu", "지효", "모모", "momo",
    "다현", "정연", "채영", "미나",

    # === 한국 멤버 (뉴진스) ===
    "하니", "hani", "민지", "다니엘", "혜인", "혜린",

    # === 한국 멤버 (키스오브라이프) ===
    "벨", "나띠", "쥴리", "하늘",

    # === 한국 멤버 (레드벨벳) ===
    "아이린", "슬기", "조이", "웬디", "예리",

    # === 한국 멤버 (있지) ===
    "유나", "채령", "예지", "류진", "리아",

    # === 한국 멤버 (엔믹스) ===
    "설윤", "지우", "배이", "릴리", "해원", "규진",

    # === 한국 멤버 (마마무) ===
    "화사", "솔라", "문별", "휠인",

    # === 한국 멤버 (오마이걸) ===
    "아린", "유아", "미미",

    # === 한국 멤버 (브브걸) ===
    "유정", "민영",

    # === 한국 멤버 (에이핑크) ===
    "손나은", "오하영", "김남주",

    # === 한국 멤버 (소녀시대) ===
    "서현", "유리",

    # === 한국 멤버 (우주소녀) ===
    "보나", "수빈", "설아", "다영",

    # === 한국 멤버 (비비지) ===
    "은하", "신비", "엄지",

    # === 한국 멤버 (프로미스나인) ===
    "채영", "백지헌", "이나경", "송하영",

    # === 한국 멤버 (케플러) ===
    "샤오팅", "휴닝바히에",

    # === 한국 멤버 (스테이씨) ===
    "아이사", "재이",

    # === 한국 멤버 (QWER) ===
    "마젠타", "쵸단", "히나", "시연",

    # === 한국 솔로 / 출신 ===
    "권은비", "전소미", "청하", "선미", "화사", "유주",
    "이채연", "미주", "강미나", "김세정", "정채연",
    "강혜원", "김민주", "혼다 히토미",

    # === 베이비몬스터 ===
    "아사", "라미", "로라", "파리타", "치키타",

    # === 아일릿 ===
    "민주", "윤아", "모카",

    # === 미야오 ===
    "miyao", "ella", "미야오",

    # === 일본 아이돌 그룹 ===
    "노기자카46", "Nogizaka46",
    "사쿠라자카46", "Sakurazaka46",
    "히나타자카46", "Hinatazaka46",
    "AKB48", "NMB48", "HKT48", "SKE48", "NGT48", "STU48",
    "FRUITS ZIPPER",
    "모닝구무스메", "Morning Musume",

    # === 일본 아이돌 멤버 ===
    "야마시타 미즈키", "타나카 미쿠",
    "와다 미유", "죠니시 레이", "요코노 스미레",
    "아오야마 히카루",
]

# ── 히트 패턴 (의외의 글래머 / 남성 시청자 타겟) ───────────────
TITLE_PATTERNS = {
    "직캠_퍼포먼스": (
        ["직캠", "fancam", "세로캠", "4k", "4K", "직캠모음",
         "무대", "stage", "퍼포먼스", "performance", "choreography",
         "직촬", "직찍", "현장"],
        0.95,
    ),
    "반전_글래머": (
        # 핵심 포커스: 의외의 글래머 · 반전 볼륨감
        ["반전", "의외", "글래머", "볼륨", "베이글", "베이글녀",
         "숨겨진", "반전매력", "숨막히는", "충격", "대박 비율",
         "unexpected", "hidden", "glamour", "volume"],
        0.98,
    ),
    "비율_피지컬": (
        # 비율 · 몸매 · 핫바디
        ["비율", "비주얼", "피지컬", "핫바디", "몸매", "뒤태",
         "각선미", "허리", "힙", "엉덩이", "S라인", "개미허리",
         "탄탄", "근육", "복근", "허벅지",
         "pretty", "beautiful", "top tier", "body", "figure"],
        0.95,
    ),
    "댄스_섹시": (
        ["댄스", "dance", "춤", "안무", "choreography",
         "섹시", "sexy", "매력", "끈적", "치명적", "치명",
         "걸크러쉬", "girl crush", "파워풀", "강렬"],
        0.90,
    ),
    "황당_반전": (
        ["황당", "충격", "실화", "대박", "헐",
         "shocking", "wtf", "crazy", "말실수",
         "갑자기", "어떻게"],
        0.85,
    ),
    "궁금증_유발": (
        ["이유", "때문에", "왜", "다른", "진짜", "못하는",
         "why", "reason", "차이", "비밀", "알고보니", "사실",
         "포기 못하는", "남다른"],
        0.80,
    ),
    "실력_감탄": (
        ["극락", "레전드", "미쳤", "대단", "올라운더", "실력",
         "음색", "보법", "춤선", "legendary", "insane", "goat",
         "vocals", "best", "역대급"],
        0.78,
    ),
    "해외_시각": (
        ["해외반응", "외국인", "reaction", "foreigner", "overseas",
         "foreign", "외국", "해외"],
        0.82,
    ),
    "귀엽_발랄": (
        ["귀여운", "cute", "귀염", "깜찍", "사랑스러운",
         "lovely", "adorable", "웃음", "미소", "리액션",
         "당황", "부끄러운", "수줍"],
        0.72,
    ),
}


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
    idol_bonus = 0.0
    for idol in FEMALE_IDOLS:
        if idol.lower() in t:
            idol_bonus = 0.10  # 아이돌 이름 보너스 상향
            break
    bonus = min(len(set(matched)) * 0.05, 0.15) + idol_bonus
    return min(max_w + bonus, 1.0), list(set(matched))


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
        {'id':'b','title':'청바지 완판시키려는 에스파 카리나 뒤태 반전 볼륨감 #shorts','view_count':302_000,'like_count':18_000,'comment_count':1_200,'duration':38,'upload_date':daysago(2)},
        {'id':'c','title':'아이브 원영턴과 다른 마라맛 안유진 턴 #shorts','view_count':363_000,'like_count':21_000,'comment_count':1_800,'duration':38,'upload_date':daysago(3)},
        {'id':'d','title':'화사 의외의 글래머 반전 볼륨감 베이글','view_count':1_600_000,'like_count':80_000,'comment_count':5_000,'duration':35,'upload_date':daysago(5)},
        {'id':'e','title':'브랜드들이 블핑 포기 못하는 이유','view_count':899_000,'like_count':42_000,'comment_count':3_200,'duration':50,'upload_date':daysago(12)},
        {'id':'f','title':'르세라핌 카즈하 무대 직캠 legendary dance','view_count':520_000,'like_count':35_000,'comment_count':2_800,'duration':55,'upload_date':daysago(7)},
        {'id':'g','title':'키스오브라이프 나띠 핫바디 비율 반전 shorts','view_count':180_000,'like_count':14_000,'comment_count':900,'duration':42,'upload_date':daysago(1)},
    ]
    ranked, filtered = rank_videos(tests, top_n=10)
    print_ranking(ranked)
    print(f"\n필터 탈락: {len(filtered)}개")
