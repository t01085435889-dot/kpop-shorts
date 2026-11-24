#!/bin/bash
# ============================================================
# K팝 쇼츠 자동 생성 파이프라인
# 사용법: ./pipeline.sh [옵션]
#
# 옵션:
#   --analyze-only    채널 분석만 실행
#   --download-only   다운로드만 실행
#   --convert-only    변환만 실행
#   --channel NAME    특정 채널만 처리
#   --count N         채널당 다운로드 수 (기본: 5)
#   --duration N      쇼츠 최대 길이(초) (기본: 60)
#   --no-title        제목 오버레이 없이 변환
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/pipeline_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "$1" | tee -a "$LOG_FILE"; }
info()    { log "${BLUE}[INFO]${NC} $1"; }
success() { log "${GREEN}[✓]${NC} $1"; }
warn()    { log "${YELLOW}[!]${NC} $1"; }
error()   { log "${RED}[✗]${NC} $1"; }

# 기본값
ANALYZE=true
DOWNLOAD=true
CONVERT=true
CHANNEL_FILTER=""
COUNT=5
DURATION=60
NO_TITLE=""

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --analyze-only)
            DOWNLOAD=false; CONVERT=false; shift ;;
        --download-only)
            ANALYZE=false; CONVERT=false; shift ;;
        --convert-only)
            ANALYZE=false; DOWNLOAD=false; shift ;;
        --channel)
            CHANNEL_FILTER="$2"; shift 2 ;;
        --count)
            COUNT="$2"; shift 2 ;;
        --duration)
            DURATION="$2"; shift 2 ;;
        --no-title)
            NO_TITLE="--no-title"; shift ;;
        *)
            warn "알 수 없는 옵션: $1"; shift ;;
    esac
done

# ── 의존성 확인 ──────────────────────────────────────────────
check_deps() {
    info "의존성 확인 중..."
    local missing=()

    command -v python3 >/dev/null 2>&1 || missing+=("python3")
    command -v yt-dlp  >/dev/null 2>&1 || missing+=("yt-dlp")
    command -v ffmpeg  >/dev/null 2>&1 || missing+=("ffmpeg")
    command -v ffprobe >/dev/null 2>&1 || missing+=("ffprobe")

    if [ ${#missing[@]} -gt 0 ]; then
        error "다음 패키지가 필요합니다: ${missing[*]}"
        error "설치 방법:"
        echo ""
        echo "  # yt-dlp"
        echo "  pip install yt-dlp"
        echo "  # 또는"
        echo "  sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp"
        echo "  sudo chmod a+rx /usr/local/bin/yt-dlp"
        echo ""
        echo "  # ffmpeg"
        echo "  sudo apt-get install -y ffmpeg"
        echo ""
        exit 1
    fi

    success "의존성 확인 완료"
    python3 --version
    yt-dlp --version | head -1
    ffmpeg -version | head -1
}

# ── STEP 1: 채널 분석 ────────────────────────────────────────
run_analyze() {
    info "STEP 1/3: 레퍼런스 채널 분석"
    echo "────────────────────────────────────────────────────────"

    python3 "$SCRIPT_DIR/scripts/analyze_channels.py" 2>&1 | tee -a "$LOG_FILE"

    if [ $? -eq 0 ]; then
        success "채널 분석 완료"
    else
        warn "채널 분석 중 일부 오류 발생 (계속 진행)"
    fi
}

# ── STEP 2: 영상 다운로드 ─────────────────────────────────────
run_download() {
    info "STEP 2/3: 영상 다운로드 (채널당 ${COUNT}개)"
    echo "────────────────────────────────────────────────────────"

    local extra_args=""
    [ -n "$CHANNEL_FILTER" ] && extra_args="--channel '$CHANNEL_FILTER'"

    # 분석 결과가 있으면 사용
    if [ -f "$SCRIPT_DIR/logs/channel_analysis.json" ]; then
        python3 "$SCRIPT_DIR/scripts/download_videos.py" \
            --count "$COUNT" \
            --use-analysis \
            $( [ -n "$CHANNEL_FILTER" ] && echo "--channel '$CHANNEL_FILTER'" ) \
            2>&1 | tee -a "$LOG_FILE"
    else
        python3 "$SCRIPT_DIR/scripts/download_videos.py" \
            --count "$COUNT" \
            $( [ -n "$CHANNEL_FILTER" ] && echo "--channel '$CHANNEL_FILTER'" ) \
            2>&1 | tee -a "$LOG_FILE"
    fi

    if [ $? -eq 0 ]; then
        success "다운로드 완료"
    else
        warn "다운로드 중 일부 오류 발생 (계속 진행)"
    fi
}

# ── STEP 3: 쇼츠 변환 ────────────────────────────────────────
run_convert() {
    info "STEP 3/3: 쇼츠 변환 (최대 ${DURATION}초)"
    echo "────────────────────────────────────────────────────────"

    python3 "$SCRIPT_DIR/scripts/create_shorts.py" \
        --max-duration "$DURATION" \
        $( [ -n "$CHANNEL_FILTER" ] && echo "--channel '$CHANNEL_FILTER'" ) \
        $NO_TITLE \
        2>&1 | tee -a "$LOG_FILE"

    if [ $? -eq 0 ]; then
        success "변환 완료"
    else
        error "변환 실패"
        exit 1
    fi
}

# ── 결과 요약 ─────────────────────────────────────────────────
show_summary() {
    echo ""
    echo "════════════════════════════════════════════════════════"
    success "파이프라인 완료!"
    echo "════════════════════════════════════════════════════════"

    local out_count
    out_count=$(find "$SCRIPT_DIR/output" -name "*.mp4" 2>/dev/null | wc -l)
    local dl_count
    dl_count=$(find "$SCRIPT_DIR/downloads" -name "*.mp4" 2>/dev/null | wc -l)

    echo ""
    echo "  📥 다운로드된 영상: ${dl_count}개"
    echo "  🎬 생성된 쇼츠:    ${out_count}개"
    echo "  📁 출력 위치:      $SCRIPT_DIR/output/"
    echo "  📋 로그:           $LOG_FILE"
    echo ""

    if [ "$out_count" -gt 0 ]; then
        echo "  생성된 쇼츠 목록:"
        find "$SCRIPT_DIR/output" -name "*.mp4" | head -20 | while read f; do
            size=$(du -sh "$f" 2>/dev/null | cut -f1)
            echo "    [$size] $(basename "$f")"
        done
    fi
    echo ""
}

# ── 메인 ──────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  K팝 쇼츠 자동 생성 파이프라인"
echo "  시작: $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════"
echo ""

check_deps

$ANALYZE  && run_analyze
$DOWNLOAD && run_download
$CONVERT  && run_convert

show_summary
