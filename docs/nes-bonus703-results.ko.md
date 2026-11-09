# 703: MMC701 CPU 오류 재현과 연속 스프라이트 읽기 수정

선택 후보는 **703B / board02**다. 실기 MMC701과 같은 CPU 오류 문맥을 재현했고, CPU·CHR 연속 읽기 및 중간 STOP 각각 36조건과 전체 Quartus Lite FIT·기존 제약 STA를 통과했다. 새 실기 설치본은 아직 없으며 스페이드 진입의 실제 해결 여부와 MMC700의 일회성 타일 깨짐은 실기 확인이 남는다.

[검증 데이터](../analysis/bonus703-verification.json) · [원시 근거 목록](../analysis/bonus703-archive.json) · [이전 실기 분석](nes-hardware702-results.ko.md)

## 재현과 원인

사용자 SMB3(J) ROM의 원본 PRG 명령·CHR 데이터와 실제 T65/MMC3/native arbiter/PSRAM reader를 실행했다. ROM SHA256은 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`다. PPU 위치·OAM을 경계 상태로 배치하고 비공개 시뮬레이션 메모리의 reset stub으로 진입했으며 원본 ROM 파일은 변경하지 않았다. 263초 전체 플레이 재현은 아니다.

mapper commit 정렬 6개 × sprite Y 상태 2개 × 메모리 위상 3개(0/3.5/5.5ns)를 비교했다. 이전 시험의 step59 종료를 step111/dot276까지 늘려 두 스프라이트의 CHR low/high 네 바이트와 중간 CPU 읽기를 검사했다. NT 주소가 실제 상태와 같도록 PPU vram=0x0300도 반영했다.

699는 36조건 중 18조건에서 실패했다. 그중 6조건에서 MMC701의 CPU deadline1 문맥 `440107f66803fb34`와 PPU 상태 `60425c008c03bc01`가 **각각 64비트 전체 일치**했다. 나머지 12조건은 CHR high deadline2였다.

원인은 sprite ALE 뒤 mapper 쓰기가 확정되기 전, 비소비 read에서 잠시 옛 bank 주소로 돌아가 불필요한 PSRAM 읽기가 수락되는 경계다. 뒤따르는 CHR high와 CPU 읽기가 밀렸다. 대표 실패 조건의 NES 클록별 일정은 다음과 같다.

| 요청 / 응답 | 699 | 703B |
|---|---:|---:|
| CHR low 0x21FBE7 | 48 / 53 | 44 / 49 |
| 불필요한 옛 주소 0x208FE7 | 53 / 58 | 없음 |
| CHR high 0x21FBEF | 58 / 63 | 52 / 57 |
| CPU 0x03FB34 | 63 / 68 | 57 / 62 |
| CPU 소비 마감 | 66, 오류 | 66, 4클록 여유 |

## 수정 범위

699의 고정 입력 중 `rtl/ppu.sv`, `rtl/nes.v` 두 파일만 변경했다.

1. ALE 이후 비소비 sprite read에서도 기존 mapper write preview를 유지한다. 실제 `ce` 소비에서는 확정된 mapper 주소로 독립 검사한다.
2. low 소비 중 준비 가능한 high plane을 기존 idle-only hint로 공급한다.
3. 다음 sprite의 Y·tile·attribute가 확정된 dummy NT 구간에서 low plane hint를 공급한다. X는 패턴 주소에 영향을 주지 않는다.

CPU/PPU의 실제 요청 우선권, mapper commit·A12 IRQ, reader 응답 지연, 소비 마감, STOP·CRC·identity·최종 ACK는 그대로다. 새 RAM·큐·캐시·상태 레지스터를 추가하지 않았고 ARM·65816 바이너리, SDC·pin·seed도 변경하지 않았다.

중간 후보 A는 preview 유지와 high hint만 적용했다. vram=0의 작은 시험은 통과했지만 실제 NT 주소와 다음 sprite를 포함하자 12/36조건에서 다음 low plane이 실패했다. 전체 setup도 −0.021ns였으므로 기각했다. A의 소스·로그·FIT/STA를 보존했다. B는 다음 low hint를 포함한 기능 수정이며 seed나 제약 변경으로 통과시킨 후보가 아니다.

## 검증 결과와 범위

| 검사 | 결과 |
|---|---|
| CPU·두 sprite 연속 읽기 | 36/36 통과, CHR 144바이트 소비 검사 |
| CPU 원본 PRG / CHR 원본 데이터·확정 주소 | 실제 소비마다 독립 비교 통과 |
| 읽기 중 STOP | 36/36 통과, 즉시와 16 NES edge 뒤 요청·응답·valid·OE 차단 확인 |
| 실제 native arbiter fill | 36조건에서 VBlank fill 응답 identity·data 검사 통과 |
| SPI·수락·ACK·STOP | 4속도/위상 × 46검사 통과 |
| 두 plan 슬롯 | 세대 wrap·stale identity·취소 2위상 통과 |
| 실제 packed ROM bus | 23위상·5125읽기 통과 |
| ARM·65816 표시 일정 | 두 시작 위상, 각 53화면이 699와 클록 단위 동일 |

host/queue/plan 검사와 표시 재생은 A에서 실행한 뒤 B의 관련 입력 해시가 전부 같음을 확인해 연결했다. 변경된 NES/PPU 연속 읽기·STOP은 B에서 다시 실행했다. 메뉴/base는 변경 없는 ARM·65816 및 기존 700 전달 검증에 연결했으며 새 실물 시험은 아니다.

| 표시 재생 | 위상 1 | 위상 2 |
|---|---:|---:|
| 밀집 표시 간격 평균 | 49.879668ms | 49.866743ms |
| 마지막 ACK (master clocks) | 67,513,300 | 67,870,990 |
| 699 대비 간격·ACK 변화 | 0 | 0 |
| 952 표시 간격 / 957 최종 대기 | 3 VBlank / 0회 | 3 VBlank / 0회 |

951의 246번 공개선도 유지한다. 이 일정은 실제 링크 ARM·65816과 기존 SPI·IRQ·ROM 달력의 재생이다. 수정 NES·PSRAM RTL 전체와 동시에 실행한 종단 시뮬레이션은 아니며 새 실기 FPS 향상 근거로 사용하지 않는다.

## 전체 보드 비용

| Quartus Lite 전체 보드 | 699 | 703A (기각) | 703B (선택) |
|---|---:|---:|---:|
| LE / 15,408 | 15,349 | 15,323 | 15,348 |
| LAB / 963 | 963 | 962 | 963 |
| M9K / 56 | 56 | 56 | 56 |
| FF | 8,377 | 8,385 | 8,377 |
| RAM bits | 305,264 | 305,264 | 305,264 |
| setup (ns) | +0.536 | −0.021 | +0.137 |
| hold (ns) | +0.152 | — | +0.157 |
| recovery (ns) | +1.332 | — | +1.412 |
| removal (ns) | +0.481 | — | +0.482 |

B는 전체 FIT 및 기존 제약 STA를 통과했다. reader·word CDC·ROM 출력 관련 추가 보고서도 양수다. LE 여유 60개, LAB/M9K 여유 0이다. ARM Flash·RAM·65816 ROM 증가는 없다. **setup 여유는 699보다 0.399ns 줄었다.** 전체 외부 IO signoff는 여전히 미완료이며 모든 STA 수치가 개선됐다는 뜻은 아니다.

## 재현 자료와 다음 순서

- `tools/prepare_nes_bonus703.py`: 해시 고정 699 입력에서 선택 B 보드 생성, 두 RTL 파일의 수정만 허용. 중간 A의 실제 소스는 근거 묶음에 별도 보존.
- `tools/probe_nes_bonus703.py`: 실제 T65·원본 ROM·연속 CHR/CPU·STOP 시험 생성.
- `tools/analyze_nes_bonus703.py`: 행렬·경계 검사·보드 비용·두 위상 일정 대조와 근거 보존.
- 선택 보드: `%LOCALAPPDATA%/Temp/nes-bonus703-board02`.
- 선택 분석: `WORKSPACE/probes/nes-bonus703/analysis02`; 346개 파일의 SHA256 재검증 완료. 상용 ROM 원시 바이트·라이선스는 제외했다.
- 원본 비교: `nes-bonus703-old02..04`, 기각 A: `new02..04`, 선택 B: `b02..04`, STOP: `bstop02..04`. 초기 진단 01 자료도 로컬에서 보존한다.

다음은 선택 B와 검증된 ARM·65816을 새 이름의 60초판/장시간판으로 묶어 전달 검증하는 단계다. RESTORE는 제외하고 스페이드 진입, 장시간 플레이, 종료 조합·STOP·메뉴 복귀를 실제 보드에서 확인한다. MMC700의 일회성 타일 깨짐은 별도 미해결 항목으로 남기며, 이번 수정으로 해결됐다고 판단하지 않는다. 안정성 확인 전에는 출력 속도 최적화를 재개하지 않는다.
