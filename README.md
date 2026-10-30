# sd2snes Cyclone IV 멀티 코어 확장

**목표는 sd2snes의 Cyclone IV FPGA에 여러 게임기 코어를 추가하고, 기존 SNES 기능과 함께 선택·실행할 수 있는 환경을 만드는 것입니다.** 개발·검증은 이 저장소, 사용자 배포는 [sd2snesHST](https://github.com/hungrysanta-ksc/sd2snesHST)에서 관리합니다.

현재 확인된 개발 대상은 **FXPAK Pro / Mk.III · EP4CE15F17C8 · STM32F401RCT6**입니다. 모든 sd2snes 보드에 대한 호환성 주장은 아닙니다.

## 현재 진행 상황

기준일: 2026-10-30. **추가·공개 완료된 코어는 GB/GBC이며, NES는 개발 중입니다.**

| 코어 | 상태 | 확인된 범위 | 다음 목표 |
|---|---|---|---|
| [GB/GBC](cores/gbc/README.md) | **추가 성공·공개 완료** | G13C44 / sd2snesHST 0.9.0, 실기·저장·RTC 등은 호환성 문서 범위 | 검증된 구현·세이브 보존, 회귀 유지 |
| [NES](cores/nes/README.md) | **개발 중** | MMC489 실제 SMB3 **첫 레벨 플레이 포함 평균9.60fps**,실행·메뉴 복귀 정상; NROM476은별도23.84fps | 조회·실제 소비 대기와 입력 공급 비용 개선으로 지속60fps |
| [PC Engine](cores/pce/README.md) | 조사 대기 | 구현·실기 성공 없음 | NES 이후 범위·자원 검토 |

MMC489는60.08초 동안577회 최종 표시로 **평균9.60fps**를 기록했고 실행·메뉴 복귀가 정상이었습니다. 첫 레벨의 체감 개선은 작았으며, 이 값은 타이틀·맵도 포함해 레벨 전용 FPS가 아닙니다. 이전485 플레이 포함8.22fps/대기13.55fps와 장면·입력이 달라 인과적 개선율은 미입증입니다. **60fps는 아직 미완료입니다.** [실기 비용·다음 순서](docs/nes-hardware490-results.ko.md) · [측정 근거](analysis/hardware490-mmc489.json) · [상세 현황](docs/PROJECT-STATUS.ko.md)

MMC492는 ROM 적재·검증 뒤 표시 준비5초 시간초과로 실행에 실패했고 메뉴 복귀는 정상이었습니다. 프레임 처리가 시작되지 않아 FPS는 산출하지 않습니다. [MMC493 분리 검증본](docs/nes-mmc493-trial.ko.md)은 정상489 FPGA·표시 프로그램을 그대로 쓰고 ARM 조회 변경만 유지합니다. **493 부팅·성능은 아직 미확인**이며 위9.60fps 기준을 유지합니다. [실패 분석·다음 관문](docs/nes-boot493-contract.ko.md).

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

다른 PC에서도 현재 상황과 다음 판단은 저장소만 읽고 파악할 수 있습니다. 다만 **NES474 전체 재빌드는 아직 별도 로컬 원본·도구에 의존**합니다. [재현 범위와 필요한 자료](cores/nes/REPRODUCING.ko.md)를 먼저 확인하고, 누락 입력을 모델이나 임의 파일로 대체하지 않습니다.

상용 ROM·BIOS·사용자 세이브·영상·라이선스 파일은 Git에 넣지 않습니다. [소스 출처](docs/DEPENDENCY-REGISTER.ko.md) · [공개 정책](docs/REPOSITORY-POLICY.ko.md) · [라이선스](LICENSE.md)
