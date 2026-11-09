# sd2snes Cyclone IV 멀티 코어 확장

**목표는 sd2snes의 Cyclone IV FPGA에 여러 게임기 코어를 추가하고, 기존 SNES 기능과 함께 선택·실행할 수 있는 환경을 만드는 것입니다.** 개발·검증은 이 저장소, 사용자 배포는 [sd2snesHST](https://github.com/hungrysanta-ksc/sd2snesHST)에서 관리합니다.

현재 확인된 개발 대상은 **FXPAK Pro / Mk.III · EP4CE15F17C8 · STM32F401RCT6**입니다. 모든 sd2snes 보드에 대한 호환성 주장은 아닙니다.

## 현재 진행 상황

2026-11-09 기준 **추가·공개 완료된 코어는 GB/GBC이며, NES는 개발 중입니다.**

| 코어 | 상태 | 확인된 범위 | 다음 목표 |
|---|---|---|---|
| [GB/GBC](cores/gbc/README.md) | **추가 성공·공개 완료** | G13C44 / sd2snesHST 0.9.0, 실기·저장·RTC 등은 호환성 문서 범위 | 검증된 구현·세이브 보존, 회귀 유지 |
| [NES](cores/nes/README.md) | **개발 중** | MMC690 성공 실행20.71fps·5–55초19.80fps, 2회 중1회 부팅 실패·둘 다 메뉴 복귀 | 스테이지 진입 중 스프라이트 ROM 읽기 오류 수정·60fps |
| [PC Engine](cores/pce/README.md) | 조사 대기 | 구현·실기 성공 없음 | NES 이후 범위·자원 검토 |

PR155 병합 후 개발 기준은 MMC690이며, 다음 수치는 보존 대조군 MMC666의 기록이다. 실기에서 60.32초에 1,221화면(20.24fps)을 표시하고 메뉴로 복귀했다. 5–40초 19.63fps, 40–55초 19.33fps, 5–55초 19.54fps다. MMC662보다 초반은 소폭 상승하고 후반은 하락했으나 map·OBJ 작업량이 크게 달라 구현만의 개선·회귀를 확정하지 않는다. [실기 비교](docs/nes-hardware667-results.ko.md)

첫·마지막 5초를 제외한 완료 표시는 977회다. 출력·최종 ACK가 표시당 26.84ms로 가장 크며, 같은 작업량의 재생에서 발행·수락·DMA·VBlank 대기를 분리해 검증한다. [현재 NES 작업](cores/nes/HANDOFF.ko.md)

최신 MMC690은 성공 실행의5–55초 평균이19.80fps로 MMC666보다1.33% 높았다. 후반은19.33→19.40fps로 거의 같고 작업량도 달라 구현만의 가속률은 미확정이다. 첫 실행의 첫 표시 전5초 timeout은 성능 집계에서 제외했다. [두 실기 분석](docs/nes-hardware691-results.ko.md)

장시간판 MMC705에서 **스페이드 보너스 진입·클리어와 사용자 종료·메뉴 복귀를 확인했다.** 다만 별도 실행의 초기 배경 CHR 읽기 오류, 기존 첫 표시 준비 timeout, 여러 장면에서 반복되는 타일 깨짐이 남아 안정성 검증을 우선한다. 이번 MMC704의5–55초는19.04fps이며 이전과 작업량이 달라 수정 자체의 가속·회귀는 확정하지 않았다. [최신 실기·미해결 경계](docs/nes-hardware706-results.ko.md)

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
