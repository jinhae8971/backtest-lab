# Changelog

All notable changes to **backtest-lab** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- MA Golden Alignment 전략 구현 (MA5 > MA20 > MA60 + RSI14 필터)
- Elliott Wave 3파 진입 전략 (trendline-detector 통합)
- 전략별 Sharpe Ratio / MDD / Win Rate HTML 리포트
- GitHub Pages 자동 배포
- Telegram 주간 요약 발송

---

## [0.0.0] — 2026-04-18

### Added
- 프로젝트 초기화
- README with Quick Start + Emergency Rollback SOP
- CHANGELOG.md (Keep a Changelog 표준)
- .gitignore (Python 표준)
- requirements.txt (의존성 정의)
- 프로젝트 스켈레톤 (src/ directory structure)

### Context
- 목적: TrendSpider "AI Strategy Lab" 기능의 무료 대체
- 기존 운영 시스템(global-market-orchestrator 등 10개 레포)와 **완전 독립**
- Rollback 전략: archive 처리만으로 격리 가능

### Baseline (작업 시작 시점 기존 시스템 상태)
기존 10개 운영 레포 commit SHA (2026-04-18 기준):

| Repo | SHA |
|------|-----|
| global-market-orchestrator | 4417984e |
| crypto-research-agent | 1a59604a |
| kospi-research-agent | 53dbfaca |
| sp500-research-agent | beaa678f |
| nasdaq-research-agent | 8402b032 |
| dow30-research-agent | f18bfc72 |
| github-actions-dashboard | 47b12d54 |
| kospi-strategy | 2e87972d |
| crypto-monitor | f7594646 |

이 상태는 backtest-lab 작업과 무관하게 보존됨.
