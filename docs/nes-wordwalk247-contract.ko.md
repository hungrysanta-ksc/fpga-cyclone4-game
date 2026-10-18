# NES247 P1: 빈 word 건너뛰기와 남은 직렬 처리시간

2026-10-18, PR128. **전체 bit 순회53.08..53.84ms를 빈16bit word 건너뛰기로5.41..7.90ms까지 줄였고, 같은71 frame의 화면·DMA 목록이 일치했다.** 그러나 post-SEAL 작업을 그대로 남기는 직렬 시나리오는 전송+스캔만으로도 frame 예산을 초과한다. P2 선정이나 제품 적용은 없다.

SELECT `walk-model01/build01/test01/analysis01/budget01`. [이전 전체순회 기각](nes-scan247-contract.ko.md)은 그대로 보존한다. 이번은 같은 구조의 opcode 조정이 아니라, 빈 묶음에서는 bit 방문을 생략하고 set bit에서만 run/address를 계산하도록 순회를 교체한 진단이다.

## 실제 분포로 먼저 비교한 두 구조

[작업량 모델](../analysis/sparsewalk247-verification.json) · [71행](../analysis/sparsewalk247-frames.csv) · [분석기](../tools/analyze_nes_sparsewalk247.py).

같은 plan/packet에서 BG1024, OBJ128, map256, rawCHR128개의 received 단위를 독립 복원했다. 원래 실제 스캐너의71개 DMA 목록과도 일치시켰다. 모든 수치는 warm69 기준이다.

|항목|최소..최대|
|---|---:|
|실제 set 단위|16..73|
|값이 있는 bitmap byte|8..25 /192|
|값이 있는16bit word|7..17 /96|
|nonzero word를0까지 shift하는 횟수|55..192|
|수신 범위 목록 수|16..58|
|범위 삽입 비교|12..67|
|삽입 시 이동하는8B descriptor|0..21|

범위 삽입은 이 관측 순서에서는 싸다. 하지만 section별 미병합 목록을 뒤에서 삽입하는 안은 허용된 역순 단위 입력에서 최대572,672개 descriptor 이동, **4,581,376B 쓰기와 같은 양의 읽기**가 필요하다. 이것은 모든 정렬 알고리즘의 하한이 아니며, 해당 단순 삽입안의 한계다. merge·bucket·다른 순서 보장이나 상한이 있는 별도 설계가 필요하다.

word 순회는 매 frame96word를 읽고 빈 word를 건너뛴다. nonzero word만 마지막 set bit까지 shift하며 set bit에서만 주소/합치기를 처리한다. 최악의 full-density는 여전히1536shift와1536set 처리다. 방문 수 비율을 기존53ms에 곱해 실행시간을 예측하지 않았다.

## 조립한 구조와 크기

[진단 builder](../tools/nes_wordwalk247.py)는 기존 수신 시 명령 생성 제거·SEAL 이후 호출을 재사용하고 스캐너를 교체한다. received bitmap192B, 기존 DP 임시 영역과12KiB 명령 저장소를 사용하며 persistent 상태 추가는0B다. 네 section 표48B를 포함한 scanner는273B다.

|구조|body /3936B|남은 byte|
|---|---:|---:|
|기존232|3910|26|
|기각된 전체 bit 순회|3930|6|
|이번 word 순회|3920|16|

source/destination의 bank base와 section 내 run 시작/끝을 분리했다. bitmap word마다 service를 호출한 뒤 word를 읽고, Y에는 현재 section 내 byte offset을 둔다. service를 넘어 Y 상태를 보존한다고 가정하지 않는다. word 끝에서는 다음 word의 byte offset으로 바로 이동한다. 주소는 출력할 때 base+run 시작으로 만든다. BG bank B의16bit destination wrap도 이 모듈러 덧셈에 포함된다.

gap≤96B/descriptor≤4096B, received/valid 검사, SEAL coverage, no-raw invalidation, uploader4192, final displayACK/retire는 기존 경계다. gap DMA가 validity를 올리지 않는다. bitmap 전체가 SEAL 뒤 안정되어 있다는 기존 소유권에 의존하며, 이 결과로 수신 도중 DMA나 target 재사용을 허용하지 않는다.

## 실제65816 재생과 시간

[검증 요약](../analysis/wordwalk247-verification.json) · [71행 실행표](../analysis/wordwalk247-frames.csv) · [독립 분석](../tools/analyze_nes_wordwalk247.py).

기존 [재생기](../tools/test_nes_scan247.py)를 새 진단 ROM에 사용했다. 기존 metadata/used pattern/map/raw 비교와 별도의 plan/packet→descriptor oracle을 유지했다. 실제 Mesen master clock 기준이며 물리 SNES FPS가 아니다.

- 71 commit/3077 ACK, **71개 전체 명령 목록 exact PASS**.
- DMA418회/135,072B, 각 frame 명령·bytes·charge는 이전 전체순회와 동일하다.
- 미초기화 읽기880건/880주소는 모두 허용된 invalid-unused gap이다. 경고를 지우거나 초기화로 숨기지 않았다.
- 66/71 single VBlank. cold2개와 warm952/955/963은 여전히 다중 VBlank다.

|시간·서비스|실측|
|---|---:|
|warm69 scanner master clocks|116,142..169,624|
|21,477,270Hz 환산|5.40767..7.89784ms|
|cold2 scanner|16.98875 /17.51079ms|
|service 호출|96/frame|
|전체71의 최대 service 진입 간격|12,068clock =0.56190ms|

warm scanner 자체는69개 모두16.67ms 안에 들어왔다. 이는 전체 frame 완료나 최악 실행시간의 증명이 아니다. 관측 service 간격도 STOP 지연 상한이 아니다. 새 STOP fault injection과 모든 서비스 경로 검증은 아직 없다. 코드 여유16B 또한 제품 확장 여유로 승인하지 않는다.

## 전송과 함께 놓으면 남는 제약

[직렬 시나리오 요약](../analysis/walkbudget247-verification.json) · [같은 frame 비교표](../analysis/walkbudget247-frames.csv) · [분석기](../tools/analyze_nes_walkbudget247.py).

ready4의2.625MHz 모델 전송시간에 **동일 frame의 실측 post-SEAL 스캔**을 더했다. 단일 frame transaction에서 둘이 직렬이며 새로운 cross-frame overlap은 없다는 조건부 비교다. 실제 통합 실행도, 모든 pipeline의 불가능 증명도 아니다. source 준비/ARM/gap/packet 처리/coverage/VBlank 대기/DMA/final ACK 비용은 아직 빠져 있다.

|retained-consumer 시나리오|warm 최대 전송+스캔|16.67ms 초과|
|---|---:|---:|
|full codec + 기존16B 출력 모델|24.09322ms|24/69|
|의미449B raster + rowshift + batched16|23.48370ms|21/69|
|위 안의 sparse raw 병렬 이동 낙관 모델|21.30465ms|8/69|

마지막 안에는 새 병렬 제어·변환 비용도 아직 없다. word-map decoder는 구현하지 않았고, 다른 지도 수신 방식에도 이 측정값을 그대로 적용하지 않았다. 단일 부품의 개선은 확인했지만, 이 직렬 조합 중 전체 near60Hz 여유를 확보한 것은 없다.

## 판정과 다음 작업

word 순회는 기능·코드 크기·관측 warm 시간 측면에서 유효한 **진단 결과**로 보존한다. 제품 후보로 선정하지 않는다. post-SEAL5.4..7.9ms를 고정 비용으로 남겨 놓고 wire만 줄이는 접근은 위 직렬 시나리오에서 충분하지 않다. service 빈도나 opcode를 미세 조정하는 반복으로 돌아가지 않는다.

다음 P1은 명령 생성의 위치와 전체 transaction 일정을 함께 비교한다. 수신 시 범위 처리 또는 생산자 순서/descriptor 전달을 이용한다면 삽입 이동량의 상한·추가 wire/ARM 상태·코드 크기를 먼저 제시한다. 수신과 준비를 겹치려면 실제 mailbox/target/base/lease가 언제 잠기는지 밝히고, 계산의 이름만 바꿔 수신 시간에서 빼지 않는다. post-SEAL critical path와 warm3개의 VBlank burst를 함께 줄이는 근거가 필요하다.

449B 의미 raster+rowshift source의 전체LE/LAB/M9K/mapper 여유, 새 입력 ARM RUN/IRQ, 최종 display 소유권·STOP·CDC/IO/STA는 여전히 OPEN이다. 한 후보의 시간·자원 여유가 함께 성립한 뒤에만 P2로 간다. 생산227, 미배치240, 기각241/246, GBC164, save SRAM과 기존 봉인 근거는 보존했다.

## 재현

```text
python tools/analyze_nes_sparsewalk247.py --prior <analysis06/result.json> --observer <observer03> --scan <scan-test01> --out <new-model>
python tools/nes_wordwalk247.py --out <new-build>
python tools/test_nes_scan247.py --client <new-build> --out <new-test> --rom <private-SMB3-J-ROM>
python tools/analyze_nes_wordwalk247.py --build <new-build> --test <new-test> --prior <analysis06/result.json> --observer <observer03> --model <new-model/result.json> --previous <scan-analysis01/result.json> --out <new-analysis>
python tools/analyze_nes_walkbudget247.py --walk <new-analysis/result.json> --prior <analysis06/result.json> --relocation analysis/relocation247-frames.csv --out <new-budget>
```

ROM·게임 파생 자료·raw 로그·계측·생성 코드/바이너리는 private에 보존한다. 공개 파일은 분석 도구와 수치·문서뿐이며, 공개 clone만으로 private 재생이 가능하다고 주장하지 않는다.
