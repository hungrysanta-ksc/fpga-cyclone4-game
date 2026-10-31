# sd2snes Cyclone IV 멀티 코어 확장

**목표는 sd2snes의 Cyclone IV FPGA에 여러 게임기 코어를 추가하고, 기존 SNES 기능과 함께 선택·실행할 수 있는 환경을 만드는 것입니다.** 개발·검증은 이 저장소, 사용자 배포는 [sd2snesHST](https://github.com/hungrysanta-ksc/sd2snesHST)에서 관리합니다.

현재 확인된 개발 대상은 **FXPAK Pro / Mk.III · EP4CE15F17C8 · STM32F401RCT6**입니다. 모든 sd2snes 보드에 대한 호환성 주장은 아닙니다.

## 현재 진행 상황

기준일: 2026-10-31. **추가·공개 완료된 코어는 GB/GBC이며, NES는 개발 중입니다.**

| 코어 | 상태 | 확인된 범위 | 다음 목표 |
|---|---|---|---|
| [GB/GBC](cores/gbc/README.md) | **추가 성공·공개 완료** | G13C44 / sd2snesHST 0.9.0, 실기·저장·RTC 등은 호환성 문서 범위 | 검증된 구현·세이브 보존, 회귀 유지 |
| [NES](cores/nes/README.md) | **개발 중** | 실제 SMB3 전체 평균 MMC516 **10.99fps**, MMC509 12.82fps(다른 동선). 실행·메뉴 복귀 정상 | OBJ 타일 공급이 몰리는 구간의 표시 지연 확인 → 지속 60fps |
| [PC Engine](cores/pce/README.md) | 조사 대기 | 구현·실기 성공 없음 | NES 이후 범위·자원 검토 |

MMC516은 이전보다 게임을 더 진행한 60.07초 동안 660회를 표시했습니다. 45~50초 구간에서는 30회(약 6fps)였고 OBJ 타일 계획·공급과 출력 대기가 함께 늘었습니다. 같은 장면에서 MMC509와 비교하는 것이 다음 단계입니다. [실기 분석](docs/nes-hardware517-results.ko.md)

[전체 경로 감사499](docs/nes-audit499.ko.md) 뒤 수집기의 행 복구와 압축 입력·출력 공급을 개선했습니다. 다음은 표시당 약 43ms인 출력 실행과 남은 입력 전송량을 줄이는 작업입니다. MMC509를 현재 실기 기준으로, MMC502를 복구 기준으로 보존합니다.

## 여기서 시작하세요

| 필요한 정보 | 진입점 |
|---|---|
| 현재 완료·미완료·측정값 | [프로젝트 현황](docs/PROJECT-STATUS.ko.md) |
| 다른 PC·새 작업에서 이어가기 | [재개 안내](docs/development/RESUME.ko.md) |
| NES 선택 소스·산출물·남은 작업 | [현재 NES 인계](cores/nes/HANDOFF.ko.md) |
| PR별 진척과 결정 | [PR 기록 폴더](docs/progress/README.md) |
| GBC 빌드·제품 사용 | [GBC 안내](cores/gbc/README.md) · [빌드](docs/BUILD-C44.ko.md) · [사용 가이드](docs/USER-GUIDE.ko.md) |
| 구현·검증·라이선스 문서 | [문서 안내](docs/README.md) · [기여 규칙](CONTRIBUTING.md) · [PR 양식](.github/PULL_REQUEST_TEMPLATE.md) |

## 기록 방식

README는 의미 있는 진척 변화나 정정이 필요할 때만 갱신하며, 목표·현재 상태·진입 링크만 유지합니다. PR별 목표·작업내용·성과·후속작업은 `docs/progress/pr-NNN.md`에 기록하며, 세부 계약과 검증 결과는 해당 기록에서 연결합니다. PR 요약을 이 파일 앞에 계속 덧붙이지 않습니다.

예전 README·인계·등록부는 [원문 이력](docs/progress/archive/README.md)에 보존했습니다. 이력 안의 ‘현재’, ‘FIRST’, ‘NEXT’는 당시 상태이며 새 작업 지시가 아닙니다.

다른 PC에서도 현재 상황과 다음 판단은 저장소만 읽고 파악할 수 있습니다. 다만 **현재 NES509 전체 재빌드는 아직 별도 로컬 원본·도구에 의존**합니다. [재현 범위와 필요한 자료](cores/nes/REPRODUCING.ko.md)를 먼저 확인하고, 누락 입력을 모델이나 임의 파일로 대체하지 않습니다.

상용 ROM·BIOS·사용자 세이브·영상·라이선스 파일은 Git에 넣지 않습니다. [소스 출처](docs/DEPENDENCY-REGISTER.ko.md) · [공개 정책](docs/REPOSITORY-POLICY.ko.md) · [라이선스](LICENSE.md)
