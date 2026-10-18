# NES247 P1: mask8 통합 수신 경계의 ROM 기각

2026-10-18, PR128. **mask8 진단 소비기의 본문4,398B가 현재4KiB 구성의 본문3936B 한도를462B 초과했다.** 현재 구성을 유지하는 후보로 기각했으며 에뮬레이터 기능·오류 주입·시간 검증은 실행하지 않았다. 이는 SNES 실행 불가나 mask8 전체의 불가능 증명이 아니다. P2 후보는 여전히 미선정이다.

[진단 빌더](../tools/nes_maskboundary247.py) · [크기·주소·해시 근거](../analysis/maskboundary247-verification.json) · [앞선 공동 비용 모델](nes-mapjoint247-contract.ko.md).

## 통합한 범위와 검증 수준

SELECT `maskboundary-build01`. 기존3903B 배치 정렬 소비기를 바탕으로 다음을 하나의 assembly 이미지에 연결했다. 아래 동작은 소스 및 조립 결과의 설계 범위이고 실행 통과를 뜻하지 않는다.

- 진단 버전2471: op9/section2의 mask8 기록과 op10/section2의 manifest. 기존 map DATA/RLE는 거부한다. 이 번호는 제품 프로토콜에 할당하지 않았다.
- 패킷당 payload≤240B, mask8 식별자2, nonzero mask, frame 전체 granule 순서, word 길이·주소 경계를 검사한다. 기록은 inactive WRAM에 쓰고 기존 append 경로로 DMA 목록을 만든다.
- manifest는 offset0/240 및 크기240/16을 강제하고256B received와 직접 비교한다. 첫 manifest 이후 map 쓰기를 막고 완료 cursor256을 SEAL 조건으로 둔다. expected256B 복제는 없다.
- 미초기화 목적 은행은 received256B 전체가FF여야 한다. 초기화한 은행도 manifest 정확 일치는 유지한다. 초기화 상태는 기존 upload 성공과 표시 retirement 뒤 기록하고, STOP을 감지하면 두 은행을 무효화한다.
- 기존 토큰/serial/epoch, pattern·CGRAM·raw 유효성, raw prefix, OAM, HDMA, serviced wait, 최종 표시 ACK 경로를 유지한다. 기존 불변 mailbox의 transport integrity 전제는 그대로이며 이번에 CRC/CDC나 실물 ACK를 검증하지 않았다.

부분 쓰기 실패는 기존 terminal failure/common reset 경로로 처리하는 설계다. 원상 복구나 실패 뒤 다음 BEGIN을 허용하는 설계가 아니다. 새 ARM sender·입력 parser·FPGA source 구현은 없다.

## 크기와 private WRAM

여기서 ROM은 **SMB3 게임 ROM이 아니라 FPGA 내부의 SNES 수신 프로그램**이다. SMB3를 개조하거나 SNES 게임으로 패치하는 작업이 아니다. NES 코어 실행 결과에서 전달한 화면 데이터를 이 프로그램이 처리하며, 부팅 때 SNES WRAM으로 복사해 실행한다. [실제 bus](../src/nes/diagnostic/nes_sink_bus165.sv)는 `PROGRAM_BYTES=4096`을 기본값으로 내부 M9K ROM을 만든다. SNES 일반 게임 ROM 용량 한도가 아니다.

이 값은 변경 가능하다. [194 기록](nes-bulk194-contract.ko.md)에는8KiB bus/소비기의 기능 시험이 있고, [195](nes-bulk195-contract.ko.md)에서4KiB로 복귀했다. 따라서 “4KiB를 넘으면 불가능”을 다음 판단의 전제로 쓰지 않는다. 8KiB 확대는 과거 산술로 M9K 약4개 증가였으며 현재 전체 설계의 합성·배치 결과는 아니다. 기존 ROM MIF만 교체하는227 배포 경로는4KiB에 묶여 있지만 새 전체 설계에서 그 경계를 재검토할 수 있다.

boot96B+footer64B를 제외한 본문 한도는3936B다. 조립기가 branch relaxation 후 다음 크기를 냈다. 초과 이미지를 보존하는8192B 진단 컨테이너는 기존 빌더의 동작이며 FPGA ROM 확대나 설치 승인이 아니다.

|구간|기존 order-build01|통합 maskboundary-build01|차이|
|---|---:|---:|---:|
|초기화·poll 전|415|415|0|
|mailbox·dispatch·BEGIN·SEAL·retire|1482|1594|112|
|entry·기존 mark|402|410|8|
|DMA 목록 append|125|125|0|
|coverage|210|250|40|
|mask8 수신|0|248|248|
|manifest 수신|0|81|81|
|기존 주소 표|18|18|0|
|upload·HDMA·wait·검증|1158|1158|0|
|service·마지막 표|93|99|6|
|**합**|**3903**|**4398**|**495**|

이는 label 사이 byte 구간의 합이며 독립 최적화 절감량이나 CPU 시간 분해가 아니다. 기존 여유33B에 새 경계495B가 들어가지 않는다. 기능을 빼거나 branch/opcode를 반복 조정해462B를 줄였다고 가정하지 않는다.

|private WRAM|용도|
|---|---|
|7E1280..1325|pattern144B+CGRAM4B+raw18B received|
|7E1340..13e5,7E13e6..148b|각 은행의 같은166B valid|
|7E148c..148d|은행별 map 초기화 byte|
|7E148e..148f|다음 granule 최소 index|
|7E1490..1491|manifest 완료 cursor|
|7E1500..15ff|word received256B|

상태 allocation은 기존594B에서760B로 **166B 증가**한다. 앞선 모델의 논리161B에 manifest/order4B와 초기화 byte 정렬1B를 더한 값이다. 주소 범위는 서로 겹치지 않고7E2000 코드 및7E4000 command 영역과 분리된다. 실제 stack 최대 깊이 또는 runtime 주소 접근 증명은 아니다. save SRAM을 사용하지 않는다.

## 남은 판정과 다음 단계

이번 결과로 새 map decode+coverage가 앞선 낙관 시간1.47114ms에 들어가는지는 알 수 없다. 과거 Python213maps/34반례를 새65816 성공으로 세지 않는다. ROM gate에서 기각했으므로71-frame 재생, 새 ARM, FIT, firmware ZIP, 실기 시험으로 진행하지 않았다.

다음 P1은 **소비기 코드의 저장·부팅 경계를 포함해 전체 배치**를 비교한다. 우선 현재4KiB 유지와8KiB 확대 또는 기존 외부 저장/WRAM 적재 경로의 재사용을 실제 ROM 주소·부트·메모리 소유권·전체 M9K/LE/LAB 비용으로 비교한다. 후자의 사용 가능성과 비용은 아직 미검증이며 새 임의 경로를 구현하지 않는다. 기존 mailbox/검증/표시 경계의 중복 제거도 실제 byte 근거가 있을 때만 비교한다. 공유 decoder나 ROM 확대는 미선정이다. 단독 mask opcode,4398B 미세축소,3971/3950B 재조정 반복으로 돌아가지 않는다.

동시에 frame952의 pattern 순서 비용과955의 최소4198>4192 표시 비용을 해결할 근거가 필요하다. source449B/rowshift의 whole-board LE/LAB·mapper, 새 입력 ARM RUN/IRQ, firstfault·CDC/IO·final display 소유권도 열려 있다. 이전 wire 절감 모델만으로 후보를 선택하지 않는다. 생산227·기능 기준240 미배치·기각241/246·GBC164·모든 과거 근거를 보존한다.

## 재현

```text
python tools/nes_maskboundary247.py --out <new-private-build-directory>
```

`result.json`이 새 경계의 판정·주소를 담는 권위 결과다. 상속 빌더가 먼저 쓴 `build.json`의232 metadata 설명은 새 결과로 대체된다. 본문·label·source snapshot은 private 결과에 보존하며 공개 파일에는 게임 ROM·그래픽·추적 자료를 넣지 않는다.
