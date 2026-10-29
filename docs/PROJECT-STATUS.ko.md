# 프로젝트 현황

목표는 **sd2snes Cyclone IV 멀티 코어 확장**이다. 현재 PC에서 NES 개발을 계속하며 PR135에서476 실기/시험 대표성을 확인했다. 현재 판단과 다음 순서는 [NES 인계](../cores/nes/HANDOFF.ko.md), PR별 경과는 [progress](progress/README.md)를 따른다.

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44 / sd2snesHST0.9.0, [기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | 제한 NROM476 약24fps, 실제 게임/30·60fps 미완료 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은 FXPAK Pro/Mk.III, EP4CE15F17C8, STM32F401RCT6, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 다른 보드/전체 IO 승인을 뜻하지 않는다.

## 최신 실기

조합은 **ARM476-02 / byte 동일 FPGA471-04 / 자체 이동 scene02**다. raw3TXT와 사용자 정상 메뉴 복귀 보고를 확인했다. 새 영상은 없다.

| 측정 | 474 1회 | 474 2회 | 476 1회 |
|---|---:|---:|---:|
| 관측 / 완료 표시 | 60.07초/1417 | 60.07초/1417 | 60.07초/1432 |
| 평균 표시율 | 23.59fps | 23.59fps | **23.84fps** |
| 정상 구간 | 약24fps | 약24fps | 약24fps |
| 수신 포함 | 18.40ms | 20.67ms | 15.65ms |
| 계획 포함 | 6.09ms | 6.07ms | 6.09ms |
| SEAL·소비·최종ACK 포함 | 17.29ms | 14.91ms | 19.58ms |

같은 장면의 평균은1.06% 증가했지만 정상 cadence 개선은 미입증이다. 수신 감소 대부분을 후반 대기가 상쇄했다. CPU replay39% 감소를 FPS 개선율로 쓰지 않는다. phase/op/quiet는 중첩되므로 합산하지 않는다.

CRC/driver/입력abort0,384KiB 적재/readback·START·STOP·base·메뉴 정상. commit1433/표시1432/EA1432, deadline 마지막 프레임의4packet이 취소됐다. 이는4frame 누락 수치가 아니다. 신뢰 불가 screen_frames나 SPC결과169를 표시 수/오류로 쓰지 않는다.

[실기477와 시험 대표성](nes-receive477-hardware.ko.md) · [측정 JSON](../analysis/receive477-hardware.json) · [476 선택 소스](../analysis/receive476-verification.json) · [설치 명세](../analysis/receive476-package.json) · [이전475](nes-nrom475-hardware.ko.md)

## 시험의 범위와 다음 관문

단순 문양은 core→수신·검사→ARM 계획→FPGA/65816 DMA·표시→최종ACK·복구의 회귀에 유효하다. 그러나 OBJ0, warm mapdirty0, BG27/28group 재사용의 쉬운 장면이다. NES 내부 실행 속도·실제 게임 표시율/정상 동작을 대표하지 않는다.

**이 문양60fps를 실제 게임 진입의 선행 조건으로 삼지 않는다.** 게임 대표 BG/OBJ·split/bank 입력과 현재 ARM을 비교하고, 실제 MMC3/SMB3의 loader·WRAM/IRQ·source/lease/ROM 경쟁·전체 보드 비용을 다음에 고정한다. 현재 NROM 전용 검사만 풀어 SMB3를 실행하지 않는다. 478에서 기존 MMC3 복원 진단 FIT15266/15408LE·관련 setup+0.187ns/hold+0.146ns를 확인했다. 이후MMC480 게임 실기는 ROM hash/전체384KiB 적재·검증·START와 STOP·base/메뉴 복귀가 정상이었지만 SNES 표시 프로그램 시작5초 timeout으로 실패했다. 비용 계측 전 종료해 게임 FPS는 미측정이다.481 진단 후보의 기능 검사는 통과했으나 전체 Lite 관련 setup−0.228ns로 전달하지 않았다. [현재 실패 분석·작업 순서](nes-mmc481-startup.ko.md). 기능 모델의57344픽셀/최종ACK 통과를 실물 부팅 성공으로 승격하지 않는다.

## 비용과 미완료

| 항목 | 현재 값/판정 |
|---|---|
| FPGA | 14740LE/13672comb/8063FF/185824bits,471 bitstream 재사용 |
| Timing | nominal 관련 setup+0.081ns/hold+0.143ns; 강화 예산−0.036ns·raw reset/CDC/미제약IO 미완료 |
| ARM | text202597/data10040/bss18552B, Flash 파일 후미352B |
| RAM/stack | RUN31848B·산술 잔여4984B는 중첩/IRQ 전 값, full stack proof 없음 |
| 해당 문양 평균 격차 | 30fps까지8.615ms,60Hz까지25.282ms |
| 실제 게임/매퍼 | SMB3/MMC3 새 조합·MMC4/5·게임별60fps 미완료 |
| 지속성 | capture 누락/반복·p95·공통 경계 시각 미측정 |

원본 누적 문서는 [archive](progress/archive/README.md)에 보존했다. 다른 PC의 자료 의존성은 [재개 안내](development/RESUME.ko.md)에 있으며 현재 PC 이전은 우선 작업이 아니다. README는 의미 있는 변화/정정 때만 갱신하고 PR은 목표·작업내용·성과·후속작업을 유지한다.
