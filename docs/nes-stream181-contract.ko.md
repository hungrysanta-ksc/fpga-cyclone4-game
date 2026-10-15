# NES1815 — 긴 반복 전송과 상수 메모리 분할

## 결과와 작업 의미

앞선1814는 같은 word가 길게 반복돼도240B마다 새 요청/ACK를 만들었다. 새1815는 **최대4096B 반복 구간을 payload2B 한 요청으로 보내고, SNES가64B마다 STOP/입력을 확인하며 복원**한다. 반복 구간과 일반 데이터를 나누는 C 송신기도 추가했다. 이전 frame 복사본이나 새 frame buffer는 필요하지 않다.

같은 합성7frame의 요청은275→219회, request bytes37,575→31,073B로 줄었다. 복원한50,217 logical DATA bytes는 이전과 모두 같다. raw 지속 부분 갱신은 앞선 구현을 그대로 사용한다.

| 같은 장면의 MCU→SNES 구간 | 기존1814→1815 최소SPI byte | 최소 모델시간 |
|---|---:|---:|
| normal gen12/15/16 |4782→3690|15.270→11.798ms|
| raw7 gen13/14 |8389→6970|26.694→22.154ms|
| raw1 gen17 |8003→6829|25.518→21.700ms|
| raw7 gen18 |8073→6899|25.731→21.914ms|

SPI2.625MHz, packet당 최소 status/ACK35B 및3transaction×8µs를 적용했다. **CPU의 두 번 계획 검사와 실제 송신 시 재탐색, SNES 복원/비교, 추가poll, FPGA→MCU는 제외한 하한 모델**이다. 실게임 압축률이나 실제FPS가 아니며, raw는 이 한 방향만으로도16.7ms를 넘는다. 요청 감소는 이 fixture 결과다. 다른 데이터에서는 요청 수가 늘더라도 총 모델 전송 비용이 줄 때만 분할할 수 있다.

이 작업은 진단 출력 추가가 아니라60fps에 필요한 실제 wire/요청 감소 구현이다. 전체section 송신과 단일 수집lease가 남아 있으므로 작은 codec 변경만 반복하며60fps를 달성했다고 판단하지 않는다. 다음에는 남은 큰 비용과 동시 처리 가능성을 함께 다룬다.

## 전송·취소 계약

- DATA2의 literal payload1..240, DATA4의 반복4..240 규격은 유지한다.
- 새 DATA5는 physical payload2B/header12=2, header14의 확장 길이242..4096 짝수다. section/offset/sequence/serial/generation은 기존과 같다. SEAL24 버전은1815다. FPGA→MCU 후보1813과 다른 경계다.
- 기존 header 물리길이·BUILD 소유권·token·section·정확한 다음offset·덧셈carry·section별 끝 검사를 모두 **복원 쓰기 전에** 수행한다. 4096은 새 작업의 명시적 한도이며 section별 한도를 늘리는 값이 아니다.
- DATA4/5 모두 매64B와 마지막 조각에서 service를 호출한다. service는 X/Y와 WRAM 포인터를 바꾸지 않는다. STOP이면E4/FAULT로 끝나며 성공ACK·SEAL·화면공개로 진행하지 않는다. 일부 candidate에 쓴 bytes는 표시하지 않고 기존 화면을 유지한다.
- 공유 mailbox packet은 복원 종료/ACK까지 기존 소유권으로 고정한다. 새 프레임 버퍼/별도상태RAM/새CPU interrupt는 추가하지 않는다. 입력/오디오 클록을 정지시키거나 source frame을 생략하지 않는다.
- 1814 client와 혼용하지 않는다. 구판은DATA5 또는 새SEAL을 거절하며, 새판은1814SEAL을 최종 화면으로 공개하지 않는다. 이번 시험의 version 오류는 새SEAL에서 version field를 바꾸어 검사했다; 별도구판 조합 실행시험은 하지 않았다.

## C 분할과 자원

각 유효 span은1..4096B이다. 송신기는64B 이상 반복 후보와 최대240B literal을 찾고, 기존240B chunk의 DATA2/4 비용과 새 계획 비용을 각각 계산한다. 새 계획이 **엄격히 더 작을 때만** 사용한다. 같거나 불리하면 기존 chunk를 사용한다. 전역최적 압축이라고 주장하지 않는다.

비용은1/8byte 단위로 `8×payload+471`이다. 471은 header16+최소응답35 및24µs×2.625MHz를 포함한다. lookup table이나 plan 배열을 만들지 않고 실제 immutable source를 다시 읽는다. span이 반환될 때까지 원본수명/COMMITTED receiver lease를 유지해야 한다. callback pointer나 원본을 이후frame용 cache로 보관하지 않는다. raw padding은 기존static zero240B의 첫word만 참조해 긴0반복을 만들고, 홀수끝은 별도literal로 보낸다.

정적 frame RAM/구조체와save SRAM은 변경하지 않았다. 그러나 **stack 증가0은 아니다.** ARM object `packet_wire320B`, `span72B`, `seal144B`, `pattern32B`이다. 기존seal136+packet312=448B에서 새seal144+span72+packet_wire320=536B로 해당국소경로+88B, pattern 경로+80B다. 전체link/IRQ 여유 승인이 아니다. 전체stack 분석 시 callback 간선의 옛 `packet` 이름을 새 `packet_wire`에 연결하고 span 경로를 포함해야 한다. 이전ingress1813 poll의+40B와도 실제 call graph로 함께 계산한다.

SNES 본문3643/3776B, program4096B로 남은본문133B다. rawsteady assembler의명시적분기완화를 재사용했다. 새FIT/전체ARM/실기/ZIP은 없다.

## 검증

SELECT test01/normal·steady, test02(19경우), check01. test01 전체suite는 뒤large_steady의 긴 held-file replay가 emulator50초 한도에 걸렸으므로 PASS로 취급하지 않는다. 앞서 완료한두case의 실제C/ROM 동일성, producer/consumer 성공과 기준영상을 별도확인했다. 큰DMA는test02/max의7chunk에서 확인하며 같은 긴후반시퀀스를 반복하지 않았다. 제품시간제한을 변경하지 않았다.

- 실제 C→held mailbox→실제65816/WRAM/DMA/PPU/ACK **21경우/1651ACK/42완료장면/2,569,728픽셀** 통과. DATA2/4/5의모든복원bytes를ACK시점실제WRAM에서비교했다. ACK/PPU쓰기는주입하지않는다.
- normal/steady/raw-first/max, raw비교·최종STOP과긴복원중STOP, 잘못된version/표/행수/긴길이0·240·홀수·4098·physical길이·section·offset·token, DATA4의242금지, section끝초과를검사했다.
- long_full은4096B를실제WRAM에성공복원한뒤의도적으로이어지는기존offset패킷을거절한다. 최대길이**staging**시험이며해당데이터를새화면으로공개했다는시험은아니다. 이전화면유지도확인했다.
- 실제memory callback에서긴반복의STOP검사사이쓰기가최대64B임을확인했다. 실기 wall-clock STOP 응답시간으로환산하지않는다.
- nativeC 별도20,491경우/98,303 mock exchange: 길이1..4096×5pattern, byte일치, 관측된wire비용≤기존방식, 잘못된ACK/IO실패시첫·중간·마지막에서즉시종료와재시도금지. 여기ACK는mock이며위실제SNES검사와구분한다.

[검증 데이터](../analysis/stream181-verification.json) · [raw 지속 갱신](nes-rawsteady181-contract.ko.md)

## 다음 작업

남은section/CHR전송, raw의큰payload, 수집/export단일lease와hostRUN/STOP 경계를공동으로다룬다. target-bank delta는기준세대·정확한원본동일성·저장위치·포트·취소수명이확정되어야한다. 추가ARM16KiB plan이나raw가덮는BGkey영구cache, hash만으로같다는판정을쓰지않는다. SPI클록·timeout을근거없이올리지않는다.

변경된최소경계검사뒤paired전체ARM/IRQ와통합FIT/IO를통과시켜SMB3숫자1+A실기로간다. 마지막전체FIT−1.408ns는여전히미채택이며이codec으로해결된것이아니다. raw복구확인과실제60fps목표를분리해기록하되, 불필요한합성시험확대로실기를미루지않는다. 배포180/GBC164/saveSRAM/이전완료archive는보존한다.
