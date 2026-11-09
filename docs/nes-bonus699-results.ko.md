# 699: sprite 주소 수락 경계 수정

**sprite ALE의 읽기 요청에 기존 mapper write preview를 연결했다. 실제 T65가 대상 ROM 명령을 실행하는 24조건은 수정 전 동일 오류2, 수정 후 정상 CHR 소비로 바뀌었다.** mapper의 뱅크 확정 시점·실제 sample 마감·독립 물리주소 검사는 그대로다. 선택 보드는 `699 board01`, ARM·65816은 선택694 그대로이며 새 설치본·수정 후 실기 결과는 아직 없다.

[자동 검증](../analysis/bonus699-verification.json) · [원본 보존](../analysis/bonus699-archive.json) · [698 재현](nes-bonus698-results.ko.md) · [수정 생성기](../tools/prepare_nes_bonus699.py)

## 수정 범위

`rtl/ppu.sv`에서 sprite의 pattern ALE이며 PPUDATA 겹침이 없는 경우를 내보낸다. `rtl/nes.v`는 이때만 현재 논리주소를 기존 preview mapper에 넣고, 그 물리주소로 early ROM 요청을 시작한다. 실제 read/sample에서는 기존 `chr_linaddr`를 다시 사용한다. 정상 mapper의 register·A12 IRQ 입력·clock·PSRAM reader·cache tag·deadline checker에는 변경이 없다. 다른 보드 입력80개, ARM·65816·STOP/ACK/menu 구현도 바이트 그대로다.

실제 CPU에서는 `$8001` 쓰기 주소/값이 mapper commit보다 **9 NES master clocks 먼저** 안정된다. 698의 실패는 그 정보를 쓰지 않고 옛 bank 주소를 먼저 수락한 결과였다. 새 경로는 step48에 `$21FBE7`을 요청하고 step55의 소비 전에 확보한다. 이미 수락된 요청을 덮어쓰거나 늦은 응답을 정상으로 취급하지 않는다.

## 재현과 보호 조건

| 시험 | 기존694/696 | 수정699 |
|---|---|---|
| 실제 T65·대상 ROM 명령, 4 commit 위치 × 2 OAM Y 조건 × 3 메모리 위상 | 24/24 실기와 동일한 오류2 | 24/24 정상 바이트 소비; 옛 주소 요청0 |
| CPU 쓰기 폭을 반영한 기존8조건 × 3위상 | 15조건 오류 | 24/24 정상 |
| 실제 native arbiter·연속 fill 요청, 유효/dummy sprite·3위상 | 별도 대상 | 24/24 정상, 허용 VBlank fill 24건의 응답/identity 일치 |
| 요청 전·진행 중·응답 경계에서 STOP | 별도 대상 | 24/24 즉시 request/response/valid/OE 차단 |
| 실제 SPI/ACK/queue 경계 | 기준과 대조 | 4개 SPI 위상/속도 각각46검사 통과 |
| 두 슬롯 plan·세대 wrap·stale 완료·정지 클록 취소 | 기존 보호 조건 | 두 위상 통과 |
| packed65816 program bus·STOP status | 선택694 ROM | 23위상·5,125읽기 통과 |

실제 CPU 시험은 원본 ROM의 `$FB29…$FB34` 명령과 `$F794=$7E`를 실행한다. private reset vector와 RAM 초기화 stub으로 그 코드에 도달하며, CPU 출력이나 mapper commit을 강제로 만들지 않는다. CHR·대상 명령/테이블은 원본이다. PPU 위치와 OAM은 제어한 경계 fixture이므로 전체851초 게임 재생이라고 하지 않는다. 유효 sprite 시험은 in-range도 켜고, 소비 주소가 **기존 committed mapper 주소와 `$21FBE7`에 모두 일치**하는지 검사했다.

실제 arbiter 시험은 CPU 캐시 적중·기존 VBlank 허가로 fill을 수락하고, line192의 sprite 경계에서는 연속 요청이 있어도 수락하지 않음을 검사했다. source 생산기·전체 ARM packet 경로까지 하나의 RTL 실행에 포함한 시험은 아니다. 기존 plan 소유권/취소는 별도 실제 RTL 시험으로 연결했다.

**기존 단일 클록 강제 쓰기24조건을 전부 정상으로 바꾸지는 않았다.** 옛 요청이 이미 수락된 뒤 처음 나타나는 쓰기9조건은 계속 동일 오류2를 낸다. 이 경우는 실제 T65의9클록 선행 안정 구간이 없으며, 마감 검사를 보존한 의도적 음성 대조군이다. 나머지15조건은 정상이다. 원래 실패12개 중3개만 정상으로 바뀌었다는 결과와, 실제 CPU24조건 모두 정상이라는 결과를 혼동하지 않는다.

## 전체 보드 비용

Quartus Lite25.1, EP4CE15F17C8, 기존 SDC·pin·seed1을 그대로 사용한 전체 compile 한 번의 결과다. 단독 MAP 절감으로 전체 FIT를 대신하지 않았다.

| 항목 | 선택694/696 | 699 |
|---|---:|---:|
| LE | 15,295 | 15,349 /15,408 (+54, 여유59) |
| LAB | 963 | 963 /963 |
| M9K | 56 | 56 /56 |
| registers | 8,377 | 8,377 |
| RAM bits | 305,264 | 305,264 |
| 최악 setup | +0.104ns | +0.536ns |
| 최악 hold | +0.137ns | +0.152ns |
| 최악 recovery | +1.460ns | +1.332ns |
| 최악 removal | +0.488ns | +0.481ns |

전체 FIT·기존 제약 STA는 통과했다. recovery/removal 여유는 각각0.128/0.007ns 줄었으므로 모든 slack이 좋아졌다고 하지 않는다. reader·word·ROM 제어 출력의 별도3-corner 검사도 양수이며 ROM_OE 최악 setup은+1.289ns다. 기존 unconstrained input54/output56·57 및 path 수는 같다. 외부 IO 전체 sign-off 완료는 아니다.

ARM Flash212,940B/여유52B, 추가 ARM RAM0B, 추가65816 ROM0B다. LAB·M9K 여유는 없다. 범위 밖 회로 최적화나 seed 탐색은 하지 않았다.

## 두 시작 위상 표시 일정

수정 보드의 실제 ACK/SPI interface 검증을 바인딩하고 선택694 ARM·65816으로 각53화면을 다시 실행했다. map·OBJ·SPI 작업량과 ARM 명령 수, 각 화면 표시 간격·마지막 ACK는 기준694와 클록 단위로 일치했다.

| 항목 | 위상1 | 위상2 |
|---|---:|---:|
| 밀집 표시 평균 | 49.879668ms | 49.866743ms |
| 기준694 대비 변화 | 0 | 0 |
| 952 표시 간격 | 3 VBlank | 3 VBlank |
| 957 최종 대기 | 0회 | 0회 |
| 마지막 ACK master clock | 67,513,300 | 67,870,990 |

이 재생은 실제 링크 M4/native65816에 SPI·IRQ 비용과 **기존 ROM 달력 모델**을 연결한다. 수정 NES/PSRAM RTL이 동시에 실행되는 전체 공동 시뮬레이션은 아니다. 새 ROM 수락 경계의 안전성은 위 실제 T65/arbiter 시험, 표시/ACK 일정의 무회귀는 별도 재생으로 검증했다. 이번 수정을 FPS 향상으로 계산하지 않는다. 선택694의 기존 위상1 장시간판 오버헤드도 사라졌다고 하지 않는다.

STOP/base/menu의 생산 코드와 선택 바이너리는 동일하며694의 native 종료·ARM 복귀 근거를 해시로 연결했다. 이번 보드에서 실제 메뉴 복귀를 새로 시험한 것은 아니다.

## 재개 순서

1. 699 보드와 검증된 정상60초/장시간 ARM·65816으로 새 번호의 전달본을 준비한다. 699는 현재 장시간65816 ROM 구성의 FIT이며, 정상판에 다른 packed ROM을 넣으면 그 구성을 별도로 결합 검증한다. 프로그래머·로그명·설치명과 board hash를 함께 갱신하고 RESTORE를 제외한다.
2. 스페이드 안내→회전 게임 진입, 스테이지 이동, L+R+Start+Select 종료와 메뉴 복귀를 실기에서 확인한다. 기존 첫 레벨5–40/40–55초 대조와 장시간 로그를 분리한다. 실기에서 동일 오류가 사라지기 전 안정성 문제를 닫지 않는다.
3. 안정성 확인 뒤692의951 마지막 tile ACK→SEAL 병목 개선을 재개한다. 이번+54LE와 LAB/M9K 여유0을 다음 후보 예산에 반영한다.

재현에는 사용자 ROM SHA256 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`가 필요하다. private699 근거 ZIP은 선택 보드 입력·정확한 patch·시험벤치·원시 결과·전체 FIT/STA·표시 재생과 실패한 harness 시도를 포함하며 각 파일을 재해시한다. ROM bytes·라이선스·서버 로그는 Git에 넣지 않는다. 두 위상 재생의 외부 fixture 의존성은694 재현 안내를 함께 따른다.
