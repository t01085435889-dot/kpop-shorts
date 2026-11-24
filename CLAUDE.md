# K팝 쇼츠 자동 생성 프로젝트

## 작업해줘

사용자가 "작업해줘"라고 하면 아래 명령어를 즉시 실행한다:

```bash
cd ~/kpop-shorts && ./pipeline.sh --channel-mode --count 5
```

완료 후 output/ 폴더에 생성된 쇼츠 파일 목록을 보여준다.

## 타겟 콘텐츠

- 여자 아이돌 방송 순간포착 클립 (음악방송, 예능, 라이브방송)
- 상체 포커스 / 의외의 볼륨감 / 반전 글래머 순간
- 남성 시청자 타겟, 조회수 높은 쇼츠 선별

## 주요 명령어

| 작업 | 명령어 |
|------|--------|
| 채널 직접 다운 (채널당 5개) | `./pipeline.sh --channel-mode --count 5` |
| 채널 직접 다운 (채널당 10개) | `./pipeline.sh --channel-mode --count 10` |
| 스마트 검색 모드 | `./pipeline.sh --smart --count 10` |
| 특정 키워드 | `./pipeline.sh --smart --count 10 --keywords 화사 볼륨` |
| 다운로드만 | `./pipeline.sh --smart --download-only --count 10` |
| 변환만 | `./pipeline.sh --convert-only` |

## 파일 구조

- `scripts/smart_search.py` — 유튜브 검색 & 선별
- `scripts/scoring_engine.py` — 바이럴 점수 계산
- `scripts/smart_download.py` — 다운로드
- `scripts/create_shorts.py` — 쇼츠 변환
- `downloads/smart/` — 다운로드된 원본
- `output/` — 완성된 쇼츠
