# 🧪 backtest-lab

Backtrader 기반의 전략 백테스트 랩.
TrendSpider의 "AI Strategy Lab" 기능을 무료로 대체하는 프로젝트.

## 🎯 목적

- 코드 기반 전략을 **50년 히스토리 데이터**로 백테스트
- 결과를 HTML/JSON 리포트로 출력 → `global-market-orchestrator` 생태계와 호환
- GitHub Actions로 **주간 자동 재백테스트** 실행
- Claude API로 AI Coding Assistant 기능 대체 (자연어 → Backtrader 코드)

## 📦 기술 스택

- **Backtrader** — 무료 오픈소스 백테스팅 엔진
- **yfinance / FinanceDataReader** — 무료 시장 데이터
- **pandas, numpy** — 데이터 처리
- **Claude API** (optional) — 전략 설명 해석 / 결과 리뷰

## 🚀 Quick Start

```bash
git clone https://github.com/jinhae8971/backtest-lab.git
cd backtest-lab
pip install -r requirements.txt

# 예제 전략 실행 (MA Golden Alignment)
python -m src.run --strategy ma_golden --ticker SPY --years 10
```

## 📂 프로젝트 구조

```
backtest-lab/
├── src/
│   ├── strategies/      # Backtrader 전략 모음
│   ├── data/            # 데이터 로더 (yfinance/FDR)
│   ├── reports/         # HTML/JSON 리포트 생성기
│   └── run.py           # CLI 진입점
├── configs/             # YAML 기반 전략 설정
├── docs/reports/        # GitHub Pages로 배포되는 결과물
├── tests/
├── .github/workflows/
│   └── weekly_backtest.yml
├── CHANGELOG.md         # 변경 이력
├── README.md
└── requirements.txt
```

## 🔄 Emergency Rollback

### 이전 버전으로 즉시 복원
```bash
git log --oneline              # commit 이력 확인
git checkout <commit_sha>      # 특정 시점으로 이동
```

### 이 레포가 문제될 경우
이 레포는 **독립 실행**되므로, archive 처리만으로 안전하게 격리 가능:
```
Settings → Danger Zone → Archive this repository
```
**기존 10개 운영 레포(global-market-orchestrator, research-agents 등)에는
어떤 영향도 미치지 않습니다.**

## 📝 변경 이력

[CHANGELOG.md](./CHANGELOG.md) 참조

## 🔗 관련 프로젝트

- [global-market-orchestrator](https://github.com/jinhae8971/global-market-orchestrator) — 5개 시장 통합 브리프
- [chart-analyzer](https://github.com/jinhae8971/chart-analyzer) — 차트 이미지 분석
- [trendline-detector](https://github.com/jinhae8971/trendline-detector) — 트렌드라인 자동 검출

## 📜 License

Personal use — jinhae8971
