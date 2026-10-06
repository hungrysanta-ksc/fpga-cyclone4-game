# CHR bank 변경 타일 보정 — 024

2026-10-05. NES-R2-BANK-PATCH-024 / 구현 NES-P2-RDY-014 / 계획 NES-PLAN-20261005-R1.

021의 split 표본에서 한 8×8 cell 안에 서로 다른 bank의 pattern이 섞이는 문제를 구현했다.
NES에서 관측한 각 행의 low/high plane 바이트를 그대로 묶어 SNES 2bpp 보정 타일을 만든다.
실제 SNES Mesen 정상 3조건과 오류 주입 2조건을 새로 실행했다. NES/RTL/Questa/Quartus는 재실행하지 않았다.

## 표현과 소유권

source frames6..9의 line63 MMC3 R0/R1 변경으로 cell row7, column13..32의 20개 cell이 바뀐다.
각 프레임 20개 ×16B=320B를 보정한다. 오른쪽 숨은 33번째 열도 포함한다.
plane별 실제 읽기값을 사용하므로 첫 fetch의 tile 번호로 행 전체를 추정하지 않는다.
990cell/15,840plane event를 검증한 뒤 원래 타일 전체와 일치하는 cell은 원래 index를 유지한다.
나머지를 현재 프레임의 cell 순서로 slot256..275에 배정한다. 다음 프레임을 참조하지 않는다.

slot256..287을 보정 전용으로 예약한다. 현재 프레임 일반 tile이 이 범위를 사용하면 명시적으로 거부한다.
모든 보정은 현재 프레임에 다시 공급하며, 덮어쓴 atlas 타일을 일반 타일로 재사용하지 않는다.
이 표본에서는 일반 BG가 원래 이 영역을 사용하지 않는다. 임의 게임의 빈 공간 보장은 아니다.
32개 초과는 거부하며, 최대32개 실측 성능을 주장하지 않는다. 이번 실제 표본은20개다.

## 실제 결과

| 항목 | 결과 |
| --- | ---: |
| split top/bottom | 각4연속 frames, 차이0 |
| 별도 fine-X1/no-split 회귀 | 4연속 frames, 차이0 |
| 정상 실제 화소 비교 | 734,208 |
| 두 split viewport의 source240줄 union | 245,760화소 일치 |
| split packet / ROM stride | 2,328B / 4,096B |
| split PPU DMA/frame | 2,308B |
| 최대 검사·DMA·commit | 22,788 master clocks |
| 관측 최소 VBlank 여유 | 7,130 master clocks |
| 022 대비 추가량 | packet/DMA +320B, 최대 소비자 +3,170clocks |
| startup CHR | 16,384B |
| 소프트웨어 부정 검사 | 23종 통과 |

4DMA는 main map1920B, 오른쪽 열60B, palette8B, 보정CHR320B다.
보정CHR은 VRAM word2800부터 연속 기록한다. 모든 DMA/commit은 관측 VBlank 안에서 끝났다.
다음 frame의 map을 고른 뒤 정상 frame을 연속 표시하고, 정상 재생 중 forced blank를 반복하지 않았다.

보정CHR을 모두0으로 만든 실제 오류 주입은 888/902/888/902화소 불일치를 검출했다.
차이는 해당 cell row의56..63행에만 발생했다.
두 번째 packet count를33으로 바꾸면 E2로 해당 frame의 DMA/scroll/map commit 전에 거부했다.
이 오류 때만 이전 frame1을 유지하며, 정상 frame 생략 정책이 아니다.
검증기는 실제 raw trace를 다시 파싱하고 packet도 원본 NES fetch에서 재구성했다.
누락/중복 plane, 예약 슬롯 충돌, 32개 용량 초과, 잘못된 header/map/palette/길이,
미지원 sprite/vertical/coarse/midframe PPU/mutable CHR 조건을 검사했다.

## 범위와 다음 단계

완성 packet을 ROM에 미리 넣고 불변 BG CHR16KiB를 startup에 적재한 오프라인 소비자 실험이다.
현재 프레임 전체 fetch가 있어야 표현을 결정한다. release tick은 metadata이며 producer 완료,
외부 메모리 지연, queue/CDC/pacing 기한은 검증하지 않았다. FPGA 구현이나 FIFO 깊이 확정도 아니다.
host guard는 생성한 4packet header에 특화되어 있다. 임의 live packet의 범용 parser가 아니다.
023 sprite와024 bank split은 별도 경로/표본이다. 둘을 동시에 표현하는 packet은 아직 없다.
두 개의 독립239줄 관측으로240줄을 비교했으며 동시240줄 출력이나 crop 승인으로 해석하지 않는다.
4색의 RGB555 기호 대응만 검증했고 최종 NES 색 정책을 확정하지 않았다.

다음은021 banks32의 큰 CHR residency와 packet 저장 경계다. 이후 실제 producer/queue/CDC/pacing을
018 자원 표에 연결한다. R2는 계속 진행 중이며 DMC, 전체 board fit/STA, SMB3, 실기 및 HDL 반입 hold는 남아 있다.
GBC C44/0.9.0, 기존 소스와 upstream을 보존한다.

[재현 계약](../docs/nes-bank-patch-contract.md), [검증 JSON](bank-patch-verification.json),
[해시 목록](bank-patch-artifacts.json), [계획](../cores/nes/PROPOSAL.ko.md).
