# 불변 CHR32KiB 상주와 packet 저장 경계 — 025

2026-10-05. 후보 NES-R2-CHR-RESIDENCY-025, 구현 NES-P2-RDY-014, 계획 NES-PLAN-20261005-R1.

021 banks32의 전체 불변 CHR32KiB를 SNES VRAM에 시작 때 적재하고, 프레임마다16KiB 참조 영역을
전환하는 소비자를 구현했다. 새 SNES Mesen5실행으로 정상3조건·오류2조건을 검증했다.
NES/RTL/Questa/Quartus는 재실행하지 않았다. 기존024의199개 해시와 상태6파일을 먼저 확인/보존했다.

## 표본과 구현

source frames6..9는 각각 physical tiles1536..1791,0..255,512..767,1024..1279를 사용한다.
프레임마다256개/4096B이며 관측4묶음은 서로 겹치지 않는다. 반복주기 이후 cache hit 주장은 하지 않는다.
SNES tile index의1024개 한계를 넘는 physical index를 그대로 map에 쓰지 않는다.
현재 frame의990개 cell 모두 같은16KiB window 안에 있는지 검사하고 index를 window 안의0..1023으로 바꾼다.
window 순서는1,0,0,1이며 BG1 CHR base register210b에4,2,2,4를 commit한다.
한 cell 안 tile 변경 또는 한 frame에 두 window가 함께 필요한 경우는 거부한다.
024 cell내 bank 보정은 별도 구현으로 보존되며 이번 경로에 결합되지 않았다.

미래 frame의 사용 타일만 골라 적재하지 않고, 사용되지 않은 부분까지 원본 불변32KiB 전체를 적재한다.
이 선택은 입력 ROM 크기에 따른 고정 정책이다. source frame 전체를 관측한 뒤 만드는 오프라인 packet과
ROM 공급 조건은 그대로이며 live producer의 완료/도착 기한을 입증하지 않는다.

## SNES 실행 결과

| 항목 | 결과 |
| --- | ---: |
| banks32 top/bottom | 각4연속 frames, 화소 차이0 |
| 별도 fine-X1 회귀 | 4연속 frames, 화소 차이0 |
| 정상 실제 화소 비교 | 734,208 |
| 두 banks32 관측의 전체240줄 union | 245,760화소 일치 |
| packet / 진단ROM stride | 2,008B / 2,048B |
| PPU DMA/frame | 1,988B |
| startup CHR DMA | 32,768B |
| 최대 정상 검사·DMA·commit | 19,732 master clocks |
| 관측 최소 정상 VBlank 여유 | 10,166 master clocks |
| 022 소비자 대비 | 최대 +114clocks, packet/DMA 증분0 |
| 소프트웨어 부정 검사 | 23종 통과 |

정상 frame은 연속이며 모든 frame DMA/CHRbase/scroll/map commit은 VBlank 안에서 완료했다.
startup에서만 forced blank를 사용한다. fine-X 회귀는16KiB 원본을32KiB atlas로0-padding한다.
선택 window를 반전하는 실제 오류 주입은42,456/42,404/42,456/42,404화소 불일치를 검출했다.
두 번째 packet window를2로 변조하면 E2로 모든 DMA와 CHRbase/scroll/map 변경 전에 거부하고 이전 frame1을 유지한다.
정상 frame을 생략하는 정책이 아니다. raw trace를 재파싱하고 입력 fetch로 packet을 재구성해 검사했다.

## 공간과 전송 한계

SNES VRAM byte 크기 기준 map 두 세트8KiB + CHR32KiB =40KiB, 미배정24KiB.
map word0000..0fff, CHR word2000..5fff를 사용한다. word1000..1fff와6000..7fff가 비어 있다.
023 OBJ의 word4000은 이번 CHR 영역과 겹친다. OBJ 재배치와 통합 재생은 미검증이다.
025는 sprite/bank patch를 함께 지원하는 완성 renderer가 아니며32KiB보다 큰 ROM의 해결책도 아니다.

새 CHR4096B를 매 frame VBlank에 전송하는 대안은 map/palette1988B와 합쳐6084B다.
DMA payload만 8clocks/B 기준48,672clocks로239줄 모드의 raw blank30,008clocks를 넘는다.
이는 현재 전체 map+신규타일 전송 방식의 산술 하한이다. 실패 실행을 새로 했다는 뜻이나 모든 renderer의 불가능 증명이 아니다.
32KiB startup 비용을 정상 frame 전송 비용에서 제외한 조건을 명시한다.

기존 실제 packet 파일 길이로 다음 저장 하한을 계산했다. slot2개는 비교 시나리오이며 queue 깊이 채택이 아니다.

| 표본 | packet B | 2KiB 초과 B | 2slot 밀집 B | 1KiB 단위 2slot B | 2의 거듭제곱 2slot B |
| --- | ---: | ---: | ---: | ---: | ---: |
|022 fine-X|2008|0|4016|4096|4096|
|023 sprite|2052|4|4104|6144|8192|
|024 split|2328|280|4656|6144|8192|
|025 residency|2008|0|4016|4096|4096|

기존 표본을 모두 수용하는 데이터 슬롯은 1KiB 단위라면3KiB씩2개=6KiB, 단순2의 거듭제곱 주소 배치는4KiB씩2개=8KiB다.
1024×8 payload로 M9K를 배치한다는 가정 아래 데이터만6개/8개라는 산술값이며 실제 합성 수치가 아니다.
018의 잔여44M9K에서 이것만 빼는 것으로 통합 가능성을 판단할 수 없다.
packet metadata/길이/소유권/CDC, producer scratch, 최대 backlog, audio 및 clock drift 비용은 별도다.
동시 sprite+split+largeCHR packet은 아직 없으므로2328B를 제품 최대값으로 확정하지 않는다.

## 다음 단계와 제한

다음은 producer release tick을 실제 packet 완료·전달 지연 및 queue/pacing에 연결하는 모델과 인터페이스다.
동시 renderer 표현/VRAM 소유권과 memory/CDC 비용을 정한 뒤018 구성에 넣어 합성/배치를 측정한다.
R2는 계속 진행 중이다. 동시240줄 출력, 최종 색 정책, DMC, SMB3, 전체board fit/STA, 실기 및 HDL 반입 hold가 남았다.
두 개의 독립239줄 실험을 합친 비교는 crop 승인이 아니다. GBC C44/0.9.0과 기존 구현을 보존한다.

[계약](../docs/nes-chr-residency-contract.md), [검증 JSON](chr-residency-verification.json),
[해시 목록](chr-residency-artifacts.json), [현재 계획](../cores/nes/PROPOSAL.ko.md).
