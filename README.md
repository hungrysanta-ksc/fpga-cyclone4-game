# FPGA Core Development — sd2snesHST

NES179 조사: 실제 SMB3 기준 실행에서 숫자1→A→첫 레벨에 도달했다. 레벨100프레임의 행중 렌더링 중단·재개를 확인하고 배포178 raster의 거부/회복16경우와 합성 타일 누락/회복5경우를 검증했다. 실기 전체 오류·유일 원인·수정 완료는 미확정이며 배포178 유지, 새 ZIP 없음이다. [조사·다음 작업](docs/nes-level179-investigation.ko.md). 아래는 과거 기록이다.

NES178 실기: 월드맵 진입과 게임 오버 뒤 영상 회복을 확인했지만 첫 레벨에서는 영상이 정지했다. 표시 완료69회·마지막59.65초로 영구 정지보다 장면별 수집/표현 제약을 우선 조사한다. 레벨의 최초 거부 이유는 로그에 없어 아직 미확정이며, 지속 영상·60fps는 미완료다. [실기 분석](docs/nes-game178-hardware01.ko.md). 아래는 과거 기록이다.

NES178 실기 시험판 준비 완료: START 이후 mask18 거부를 수정한 FPGA·MCU·SNES 조합이 패킷 경계·전체 ARM·단일 FIT·조건부 IO 검사를 통과했다. 실제 게임 전환 후 영상 지속 여부는 사용자 실기로 확인하며 초기 끊김·60fps는 아직 미완료다. [실기 안내](docs/nes-game178-ready.ko.md). 아래는 과거 기록이다.

NES178: 목표 SMB3 일본판의 START 전환 후 mask18을 기존 수집기가 계속 거부하는 문제를 재현했다. 왼쪽8픽셀 클리핑을 보존하는 FPGA·MCU·SNES 후보와 경계/픽셀 검증을 완료했다. 전체 ARM 링크·FIT·실기 전이라 배포177 유지·새 ZIP 없음이며, 초기 끊김과60fps는 아직 미완료다. [검증·남은 작업](docs/nes-clip178-contract.ko.md). 아래는 과거 기록이다.

NES177 실기: START 화면 전환 때 영상만 정지한다는 사용자 관찰을 확인했다. 로그는27회 표시 완료·마지막12.48초 뒤 추가 BEGIN 없음, ABORT0이다. 종료 직전16클록에서 exporter IDLE/owned0/rawgeometry0/active1/fillbusy0/arbiterfault0이며 전송 적체 증거는 없다. 정상 수집 중간에도 가능한 표본이므로 반복 거부·결합 실패는 아직 구분하지 못했다. 연속 영상·60fps 미달성이며 새 패키지는 없다. [실기 결과·다음 작업](docs/nes-game177-hardware01.ko.md). 아래는 과거 기록이다.

NES177 실기 시험판 준비: 기존 history 하위22비트로 마지막 COMMIT 뒤 수집·소유권·전송·중재기 경계를 구분한다. 해제14위치 검증, 실제 클록 setup +0.055ns/hold +0.152ns, 조건부 IO, ARM 여유1040B, 최대TXT3925B 검사를 통과했다. 화면 정지 해결·60fps는 아직 미완료다. 무관한 로더 수정 없이 한 번의 FIT로 패키지를 만들었다. [검증·다음 작업](docs/nes-boundary177-contract.ko.md). 아래는 과거 기록이다.

NES176 회고 반영: 실제 SMB3 모델360프레임에서 즉시 해제349개·10프레임 보유35개 정상 후보와 기존 픽셀 일치를 확인했다. 두 장면의 전체5,493바이트 중 차이20바이트를 확인해 앞단 변경 전송의 근거를 마련했다. 공유 메모리 오류 연결6경우도 검증했지만 실기 정지 원인은 확정하지 않았다. 배포174 유지·새 ZIP 없음·60fps 미달성이며, 무관한 로더 미세FIT 반복을 멈춘다. [결과·수정 계획](docs/nes-video-review176.ko.md). 아래는 과거 기록이다.

NES175 READY·카운터 후보의 기능/SPI 검증은 통과했다. READY 경로 제거와 쓰기 대기 경로 +1.573ns 개선에도 전체 setup은 각각−0.048/−0.218ns로 실패해 두 후보 모두 미채택이며 새 ZIP은 없다. 배포174를 유지한다. [결과·다음 조건](docs/nes-ready175-contract.ko.md).

NES175는 느린 소비 후5회 전달·거부3회 후 회복을 연결 시험으로 확인했다. 실기 정지는 아직 미해결이며, 관측 후보 A4(-0.178ns)·A5(-1.114ns)는 타이밍 실패로 미채택이다. 새 ZIP 없이 검증된174를 보존한다. [검증 결과·다음 조건](docs/nes-lifecycle175-contract.ko.md).

NES174 실기:12회 표시 완료·마지막generation23/RUN3.81초 이후 영상만 정지했다. 사운드·조작은 정상으로 보인다는 보고이며 로그상60초 종료·메뉴 준비는 정상이다. 변환·전송/표시 확인 평균167.5ms, 연속 화면·60fps 미달성. 다음은 새 후보의 허용·해제·전달 경계다. [실기 분석](docs/nes-game174-hardware01.ko.md). 아래 시험판 준비 기록은 당시 상태로 보존한다.

NES174 실기 시험판 준비 완료: 실제 클록 setup +0.246ns / hold +0.156ns와 기존 외부 인터페이스 조건을 통과했다. 타일 간 비트평면 수정·묶음 전송을 새 FPGA/MCU에 함께 적용한다. 화면 정지 해결·60fps는 실기에서 확인할 차례다. [현재174 설치·시험 안내](docs/nes-game174-ready.ko.md).

NES174 로더의 명령 허용 상태를 분리해 전체 실제 클록 setup을 -0.807ns에서 -0.098ns로 개선했다. 기능·실제 SPI 연결은 통과했으나 타이밍은 여전히 실패다. 후속 속성 변경(-1.344ns)은 미채택이며 새 실기 ZIP은 없다. [타이밍 변경과 검증](docs/nes-legality174-contract.ko.md).

NES174에 타일 묶음 전송을 추가했다. SMB3 모델 장면의 패턴 요청18회→3회, 전체 요청45회→30회이며 실제 SNES 수신·229,376픽셀과 ARM 여유1040바이트를 확인했다. 실기 속도·60fps는 미확인이다. FPGA 타이밍-0.807ns와 전체 테이블 전송 비용이 남아 새 ZIP은 없다. [묶음 전송 검증과 다음 작업](docs/nes-batch174-contract.ko.md).

NES174 후보는 SMB3의 서로 다른 타일 비트평면을 보존하도록 수정했다. 모델frame24 수집과 frame24·25의114,688픽셀 비교, SPI·C 및 ARM 여유1024바이트 검증을 통과했다. FPGA 배치는 성공했지만 memory setup-0.807ns로 미채택이며 새 실기 ZIP은 없다. 실제 정지 해결·60fps는 미확인이고 반복 전송 비용도 남았다. [174 검증과 미완료 작업](docs/nes-cross174-contract.ko.md).

NES173 실기: RUN 시작 후5.79초까지 표시 ACK16회 뒤 추가 완료가 멈췄다. 변환/패턴 전송910ms와 테이블·SEAL/ACK2340ms, 합계 회당 약203ms로 초기 처리량도60fps 목표에 크게 못 미친다. 정상60초 종료·STOP/메뉴 준비 확인. 정지 원인 미확정, 같은173 재시험 없이 타일 간 plane 표현과 반복 전송/왕복 개선으로 진행한다. [173 실기 결과](docs/nes-game173-hardware01.ko.md).

NES173 실기 시간 측정판을 준비했다. 172 FPGA 전체 바이트·표시 프로그램을 유지하고 MCU에 수신 대기·변환/전송·표시 ACK 누적 시간과 마지막 표시 완료 시각을 추가했다. 화면 정지와 약60fps 연속 표시 목표는 아직 미달성이다. [173 실기 안내](docs/nes-game173-ready.ko.md) · [측정 범위](docs/nes-profile173-contract.ko.md).

NES172 실기에서 표시 준비와 14회 표시 완료 응답을 통과했지만 이후 화면이 멈췄다. 버튼·스테이지 음악은 계속 반응했고 정상 약60초 한도로 메뉴에 복귀했다. BEGIN/END/COMMIT 각14, ABORT0, 마지막 generation27이다.170의 수집 시간 초과와 달리 다음 BEGIN이 수신되지 않은 경계이며, 초반도 끊겼으며 약60fps 연속 표시 목표는 미달성이다. [172 실기 결과](docs/nes-game172-hardware01.ko.md).

현재164 실기: **검정 구간 제거 통과·사운드 정상으로 보임, 심한 갱신 지연으로 정상 플레이 미달성**. 다음은 영상 전송량·갱신 지연 개선이며, DOWN 유지는 이번 미시험입니다. [164 실기 결과](analysis/GAME164-HARDWARE-RESULT.ko.md).

이전151 실기: **SMB3 제목·캐릭터 표시와 메뉴 복귀 성공, PPU 읽기 오류로 조기 종료**. 정상 플레이·전체 버튼 입력은 미완료입니다. [151 실기 결과](analysis/GAME151-HARDWARE-RESULT.ko.md).

**sd2snesHST의 개발 저장소**입니다. FXPAK Pro의 코어 구현, 재현 빌드, 검증 근거와 이식 경험을 관리합니다.
제품 이름의 **HST는 HungrySanTa = 제작팀 이름**을 뜻합니다.

일반 사용자 안내는 [sd2snesHST](https://github.com/hungrysanta-ksc/sd2snesHST)에서 제공합니다. **sd2snesHST 0.9.0 = 검증된 GBC C44**를 [공개했습니다](https://github.com/hungrysanta-ksc/sd2snesHST/releases/tag/v0.9.0). 다음 작업은 NES 코어 이식이며, [GBC 회고](docs/development/GBC-PORTING-LESSONS.ko.md)와 [NES 인계 계획](cores/nes/HANDOFF.ko.md)에서 시작합니다.

## 어디서 시작하나요?

| 목적 | 문서 |
| --- | --- |
| 사용자 배포와 개발의 역할·버전 관리 | [두 저장소 운영 계획](docs/distribution/REPOSITORIES.ko.md) |
| 0.9.0 준비·발행 순서 | [0.9.0 공개 계획](docs/distribution/0.9.0-PLAN.ko.md) |
| 배포 저장소 첫 화면 초안 | [sd2snesHST](distribution/sd2snesHST/README.md) |
| 코어 현황·NES/PCE 후속 작업 | [코어 로드맵](cores/README.md) |
| 새 코어 조사 시작 | [코어 제안서](cores/CORE-PROPOSAL.ko.md) · [이식 절차](docs/PORTING-PLAYBOOK.ko.md) |
| 공통 구현과 코어 경계 | [개발 구조](docs/development/ARCHITECTURE.ko.md) |
| 모든 현재 문서와 과거 기록 | [문서 안내](docs/README.md) |

## 개발 기준선

| 구성 | 현재 상태 | 소스·재현 |
| --- | --- | --- |
| GB/GBC | C44 실기 확인, 0.9.0 공개 완료 | [GBC 개발 안내](cores/gbc/README.md) |
| NES | 164 첫 레벨·사운드·메뉴 복귀 확인; 화면 끊김으로 정상 플레이 미달성 | [NES 개발 안내](cores/nes/README.md) |
| PC Engine | 조사 대기; HuCard 범위를 우선 검토 | [PCE 조사 범위](cores/pce/README.md) |

현재 구현 대상은 **FXPAK Pro / Mk.III, STM32 + EP4CE15F17C8**입니다. 제품 이름이 바뀌어도 보드 지원 범위가 넓어지는 것은 아닙니다. NES/PCE의 동작 가능성·일정은 아직 확정하지 않았습니다.

이 보드·MCU·FPGA 대상은 [등록부](cores/registry.json)와 [NES 실기 준비 가이드의 하드웨어 기준](docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md#확정된-개발-대상과-추가-확인-항목)에 고정합니다. 기존에 적힌 제품 정보를 반복해서 질문하지 않습니다. PSRAM IS66WVE4M16EBLL-70BLI 두 개와 MCU STM32F401RCT6도 사진으로 확인했습니다. 추가 확인은 실제 배선 지연·외부 타이밍 등 아직 확인되지 않은 항목으로 한정합니다.

검증된 GBC 입력 경로 `src/fpga`, `src/firmware-overlay`, `src/renderer`는 유지합니다. 코어별 안내·등록부로 구분하고, 실제 공통 코드 추출은 두 번째 코어의 요구가 확인된 뒤 별도 검증으로 진행합니다.

주요 진전마다 [코어별 기록·커밋·PR 절차](docs/development/MILESTONE-WORKFLOW.ko.md)에 따라 정리합니다. NES의 [공개 재현 시험](cores/nes/REPRODUCING.ko.md)과 전체 코어/실기 검증 범위는 구분합니다.

## 기록과 배포 원칙

- 구현 변경·upstream 출처·가설·실패 결과·재현 가능한 검증은 이 저장소에서 관리합니다.
- 사용자용 저장소에는 제품 안내와 릴리스만 정리합니다. 코드를 두 저장소에서 따로 수정하지 않습니다.
- 제품 버전, 코어 후보, 개발 커밋, 바이너리 해시, 세이브/상태 형식을 연결합니다.
- 상용 ROM·BIOS·개인 세이브·덤프·비밀 정보는 공개하지 않습니다.
- [라이선스](LICENSE.md) · [대응 소스 묶음](docs/SOURCE-BUNDLE.ko.md)
- [기여 규칙](CONTRIBUTING.md), [소스 고지](docs/DEPENDENCY-REGISTER.ko.md), [공개 정책](docs/REPOSITORY-POLICY.ko.md)을 따릅니다.
