# NES247 P1: unused tile 간격의 수명과 실제 DMA 실행 경계

2026-10-18, PR128. [의미 raster·재배치 검토](nes-relocation247-contract.ko.md) 후속이다. **SEAL coverage 뒤라면 초기화되지 않은 unused tile 간격을 복사해도 현재 화면을 보존한다. 다만 DMA가 validity를 올려서는 안 된다.** 같은 쓰기 집합의 pattern 명령 비용을 최소화해도 word-map 조합의 frame955는 기존4192 charge를6 초과한다. 별도 실제65816 계측은 charge가 master clock의 직접 환산값이 아님을 확인했다. 새 구현·예산 변경·P2 후보 선정은 아직 없다.

[gap 검증](../analysis/gap247-verification.json) · [71행 gap 비용](../analysis/gap247-frames.csv) · [실행 계측](../analysis/dma247-verification.json) · [71행 실행 경계](../analysis/dma247-frames.csv). SELECT private `gap01/dma01/dma-analysis01`; 이전 observer03/analysis06/schedule04/relocation01 보존.

## 더 넓은 안전 조건

현재 frame에서 SEAL이 참조하는 pattern 집합을 U, 해당 target bank에서 실제 쓰기로 초기화된 집합을 V라 한다. 기존 coverage는 **U ⊆ V**를 DMA 전에 검사한다. 그러므로 V에 없는 tile은 U에도 없다. 따로 unused bitmap을 만들거나 gap마다 새 SEAL 검사를 추가할 필요는 없다.

이 결론의 조건은 다음과 같다.

1. 기존 실제 쓰기와 SEAL 검증이 끝난 뒤, 같은 target bank의 shadow에서 같은 target VRAM으로만 DMA한다. 활성 bank, 다른 section,4096B 경계를 넘지 않는다.
2. DMA gap 복사는 `mark212`를 호출하지 않으며 received/valid 비트를 올리지 않는다. 초기 WRAM 값은 임의 값이어도 되고0으로 가정하지 않는다.
3. 나중에 그 tile을 처음 참조한다면 실제 쓰기가 먼저 V에 추가해야 한다. 그렇지 않으면 기존 coverage가 거부한다. 현재 초기화됐다는 사실과 현재 physical key의 내용이 맞다는 사실은 다르며, 후자는 기존 host resident/dirty 및 final display commit 규칙을 계속 요구한다.
4. STOP/common reset 뒤에는 기존 양 bank 무효화와 새 admission이 적용돼야 한다. 과거 gap 복사나 늦은 ACK로 새 epoch의 유효성을 복구할 수 없다. 이번 검증은 이 규칙을 보존하는 조건부 모델이지 새 STOP/CDC 구현 검증이 아니다.

### 같은71 frame의 결과

독립적인 세 초기 WRAM/VRAM 패턴으로 replay했다. 임의 byte를 복사하는 위치는 unused로 제한하고, SEAL이 참조하는 **130,592B를 각각 비교하여 총391,776B 비교 PASS**했다. 각 frame의 활성 bank 불변, DMA 후 validity 불변도 검사했다.

- 총33개 gap/1472B. schedule04의 initialized-only 조건은11개/592B였다.
- 처음에는 invalid였던 `(bank,slot)`30개 중10개는 이후 실제 쓰기 후 사용됐다. 나머지20개는 관측 구간 끝까지 미기록·미사용이며 장기 성공으로 세지 않는다.
- 실제906에서 gap에 들어갔다가930에서 사용된 slot의 첫 실제 쓰기를 제거하면 coverage가 실패했다.
- missing write, 미래 사용, 다른 bank, reset, 잘못된 validity 승격에 관한5개 작은 정책 반례도 확인했다. 실제 ROM fault injection5건이라는 뜻은 아니다.

## 같은 쓰기 집합에서는 더 묶는 것만으로 충분하지 않다

주소순 pattern에 gap≤96B, 같은 kind, 총길이≤4096B를 적용했다. 별도로 모든 길이의 gap을 허용하는 동적 계획법으로 descriptor 분할 최소값을 구했다. **warm69 모두 현재 greedy 결과와 이 독립 최소값이 같았다.** 이것은 동일한 pattern 쓰기 집합과 `length+96` 비용식의 최소값이며, map/raw 배치 변경·쓰기 생략·다른 비용식까지 불가능하다는 증명은 아니다.

|frame|16B map+unused gap charge|word map+unused gap charge|4192 대비 word 여유|
|---|---:|---:|---:|
|952|4208|4180|12|
|954|4176|4120|72|
|955|4240|4198|−6|
|963|4240|4178|14|
|968|4176|4134|58|

16B map은952/955/963, word map은955가 남는다. gap 변경은 VRAM 명령 범위만 바꾸므로 이전 의미 raster+rowshift의 wire 모델은 그대로다:16B map 최대5141/5321B(ready4/ready1), word map4601/4741B 및 ARM 추가448B. 이 여유를 ARM CPU·FPGA mapper 여유로 옮겨 계산하지 않는다.

## 기존 실제65816의 CPU 경계를 새로 계측

[계측 도구](../tools/measure_nes_dma247.py)는 봉인된232 ROM과 기존231 C host를 그대로 사용했다. Lua instruction callback만 추가하여 `upload_loop212`, `wait169`, `final212`, `final_upload212_return`의 master clock을 읽었다. 새 ROM을 만들거나 메모리를 주입하지 않았다. 파일 mailbox로 기다린 전체 SEAL 시간은 CPU 처리 시간으로 사용하지 않는다.

**71 commit,3077 ACK,478 VRAM DMA/133,600B PASS.** 기존 metadata8570B/used pattern/map/raw 비교와 표시 중 PPU 쓰기의 VBlank 검사도 유지했다. 기존 결과와 마찬가지로 전체71 중64개가 단일 VBlank였다. 새 gap 스케줄의 실제 실행 결과는 아니다.

|계측 범위|대기를 포함하지 않은 표본|master clock 범위|
|---|---:|---:|
|list loop 진입→다음 진입|403명령|1346..13490, payload 포함|
|위 값에서 payload×8을 뺀 잔여|403명령|1218..1586|
|warm `final212`→최종 루틴 return 직전|64frame|9284..9442|

payload×8 차감은 진단용 정규화다. 잔여에는 CPU 설정뿐 아니라 DMA 시작 정렬·메모리 refresh 등의 영향이 섞일 수 있으므로 순수 setup cycle이라고 부르지 않는다. wait169를 거친 명령75개와 final5개는 위 표본에서 제외했으며, 추정 대기 시간을 빼서 끼워 넣지 않았다. cold final2개도 warm 표에서 제외했다(각14236/14386clock, CGRAM 포함1568charge). final 측정은 OAM/표시 설정 등을 포함하지만 그 뒤의 RTS/ACK/host retire까지 포함하지 않는다.

표시 ACK의 scanline은232..257이었다. 이 실행은 VBlank 검사를 통과했지만 각 새 스케줄의 허용 시간 상한을 도출한 것은 아니다. 현재96/960 charge를 단순히8배 한768/7680과 위 잔여/실행값이 일치하지 않는다. 따라서 **4192 charge는 기존 분할 정책이며 독립적인 master-clock 상한이 아니다.** 반대로 이 불일치만으로 기존 화면 실행이 VBlank를 넘었다고 주장하지도 않는다.

관측 최대값은 최악 실행시간 증명이 아니다. 코드·주소·DMA 시작 위상, pad/service, raw/mode/HDMA 경로와 실제 사용 가능한 VBlank 시간을 함께 묶어야 한다. 아직4192를 완화하거나 “6만 줄이면60Hz”라고 승인할 근거는 없다.

## 교체 범위와 코드·시간 미완료

기존 received bitmap의 pattern144B에 이미 해당 frame의 실제 쓰기가 있다. post-SEAL scanner는 이를 주소순으로 읽어 최대1152slot을 방문하고 기존8B descriptor 형식으로 만들 수 있다. **gap 수명 증명 자체는 추가 validity 상태0B**지만 scanner의 임시 변수·코드·실행시간이0이라는 뜻은 아니다.

구체적인 경계는 `coverage212` 성공 뒤, 첫 `wait169` 전이다. pattern 수신 시의 명령 생성 경로를 대체하고 metadata 명령을 보존한 채 pattern 명령을 추가하는 방식을 검토한다. 계획 생성·bulk token·payload consume 순서는 바꾸지 않는다. SEAL 전 sorted DMA를 시작하지 않는다. 최대1536개 기존 command storage와 메모리 범위를 지키고, scan 중 STOP/pad service의 지연 상한도 필요하다.

현재 body는3910/3936B로26B만 남는다. 실제 label 범위의 shared append는132B, list loop는112B지만 append는 metadata에도 필요하므로132B를 전부 회수할 수 없다. uploader와 최종 표시 소유권을 유지하면서 scanner를 단순 추가할 수 있다는 승인은 없다. 새 code byte 수와 worst-case cycle은 **UNKNOWN**이다. word-map receiver/SEAL coverage의 교체 비용도 기존232로 대체할 수 없다.

## 다음 결정

gap 논리와 같은 pattern 집합의 charge 최소값 조사는 종료한다. 더 많은 seed/opcode/gap 순열은 다음 작업이 아니다. 다음은 기존 실행 경계에서 **가용 VBlank master-clock 예산과 CPU/DMA 최악 경로를 연결하고**, bitmap scanner와 shared command 생성의 교체 코드 크기·서비스 지연을 산정하는 일이다. 현4192 정책은 유지한다.

동시에 의미 raster+rowshift source가240의490LE/40LAB 부족과 mapper 여유를 해결할 수 있는지, 새 입력을 포함한 ARM RUN/IRQ가 들어가는지 결합해야 한다. 한 후보의 면적·메모리·시간 여유가 함께 뒷받침될 때만 P2로 보낸다. 생산227, 미배치240, 기각241/246, GBC164/save SRAM과 과거 실패 근거는 유지한다.

## 재현

```text
python tools/analyze_nes_gap247.py --prior <analysis06/result.json> --schedule <schedule04/result.json> --observer <observer03> --out <new-private-directory>
python tools/measure_nes_dma247.py --out <new-private-directory> --rom <private-SMB3-J-ROM>
python tools/analyze_nes_dma247.py --measurement <dma01> --out <new-private-directory>
```

gap01/dma01/dma-analysis01은 첫 실행 PASS다. Windows 기존 MinGW/Mesen 실행 제한에 따라 승인된 외부 실행으로 실제 재생만 수행했다. raw logs/CSV/Lua와 재현 source hash는 private에 보존하며 ROM·게임 graphics·실행 파일은 공개하지 않는다. 새 FPGA FIT/STA/ARM build/물리 실기는 실행하지 않았다.
