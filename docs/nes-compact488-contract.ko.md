# NES488 — compact raw 실제 연결과 전달 보류 판정

[검증 JSON](../analysis/compact488-verification.json) · [PR137](progress/pr-137.md) · [현재 순서](nes-output487-plan.json). 실제 하드웨어 기준은 **MMC485 대기13.55fps/첫 레벨 플레이 포함8.22fps** 그대로다. 이 후보를 설치본으로 선택하지 않았고 새 ZIP도 만들지 않았다.

## 연결한 경계

실제 linked ARM의 SEAL 생산 → 기존 압축 DATA/E1 → candidate WRAM → 실제65816 canonical 복원 → 기존 독립 의미/coverage 검사 → 기존 raw2048B DMA → VBlank 최종 표시 ACK를 연결했다. BEGIN/SEAL 버전은 **4882**로 함께 변경해2271과 섞이면 거부한다. 입력 압축·tile plan·공유 SPI 속도·4credit·독립 CRC·STOP·최종 ACK 뒤 resident commit/EA·메뉴 복귀 구현은 유지한다.

raw_count1/2는 tile→plane pair→사용 행 순서로 low6plane만 보낸다. count2는2048→384B다. 색상0..63에64를 더하는 기존 변환에 따라 사용 행의 plane6은1, plane7은0이고 나머지 행은0이다. count3..7은 기존2048B로 보수적으로 fallback하며 raw0은 바꾸지 않는다. compact section5의 정확한 길이는1370+192×count다. 길이·버전·count·기존 mode/enable 검사를 생략하지 않는다.

ARM은 BG 계획/동기 staging callback이 끝난 뒤 더 읽지 않는8KiB bg_keys의4096번 바이트부터 최대384B를 빌린다. 기존 OBJ 검사 scratch0..447과 겹치지 않는다. canonical patch.chr는 보존한다. 실제71개에서 이 임시 영역 밖 쓰기가 없고, 다음 계획을 포함한 canonical 상태·계획이 기준과 일치했다. 실제 소비 완료와 저장 credit은 계속 별개다.

65816은 비활성 bank에서249B table tail을 뒤로 옮기고, compact prefix를 보존한 채 나머지 raw 공간만 zero DMA로 지운다. **지금 보유한 SEAL의 예약 zero byte40000E**를 고정 DMA source로 쓴다. WRAM→WRAM DMA를 가정하지 않는다. tile을 역순으로 확장해 아직 읽지 않은 compact bytes를 덮지 않고, prefix 안의 미사용 행만 명시적으로 지운다. 중간 복사 buffer·새 retained cache·별도 frame RAM은 없다. 4tile/256B 복원마다 service하며, 기존 의미/coverage 검사와 한 덩어리 raw2048B DMA 전에 canonical3418B를 복원한다.

## 실제 비용

| 항목 | 487/기존 경로 → 488 후보 | 판정 |
|---|---|---|
| 고정71개 ordinary/SEAL E1 | 364761→237174B | **127587B/34.98% 절감**, raw2 프레임당1797B |
| ARM serializer 명령 | 13767406→6392237 | **53.57% 절감**, pack 계산 포함; 전체 ARM 시간 아님 |
| 실제 M4 window CRC/credit/barrier,6표본 | 2238692→1551186명령 | 즉시 retire endpoint; IRQ/대기/물리 cycle 아님 |
| ARM | text202809/data10040/BSS18572, firmware212852B | 485 대비Flash+92B,487 대비+80B; **140B 잔여** |
| ARM RAM/stack | 새 global0B, 기존 BG scratch384B; SEAL static304B | 이전과 같은304B; RUN31848B/full stack·IRQ 증명 미완료 |
| SNES body | 3712→4233B | 기존3936B 배치 용량을297B 초과해 **program4→8KiB** |
| SNES RAM | 새 persistent/framebuffer/staging-tail0B | 기존 DP·비활성 bank 재사용; 시험의 관측 stack11→11B |
| Lite whole FIT | 15254→15287LE,14049→14081comb,8392FF 동일 | +33LE/+32comb; **121LE 잔여** |
| FPGA memory | 256608→289376bits,47→51M9K | program ROM+32768bits/+4M9K; **5M9K 잔여** |
| 관련 setup/hold | +0.133/+0.132→**−0.101/+0.151ns** | setup 실패. 전체 CDC/IO 승인도 아님 |

1797B는2.625Mbps 선로에서5.4766ms다. BEGIN·tile/plan·source·polling을 제외한 ordinary/SEAL E1 절감이며, 실제494개 플레이 프레임의 전송량이나 FPS에 그대로 적용하지 않는다. 로컬 rebuild의 firmware는 genhdr가 현재 시각으로 만드는 header version magic4B만 다르고 나머지 모든 firmware byte와 payload CRC가 동일함을 확인했다. 공개 JSON에 두 해시를 구분했다.

## 표시 시간은 거의 줄지 않았다

실제65816과4credit/2.625Mbps 전송 모델로 같은12개 입력905..916을 연속 실행했다. 매번 앞 프레임의 최종 ACK 뒤 다음 BEGIN을 허용하며 전체 픽셀·canonical WRAM·raw VRAM·DMA·ACK를 비교했다.

| 동일 조건 비교 | 기존 | 488 | 차이 |
|---|---:|---:|---:|
| 시작 masterclock3000000,12개 최종 ACK까지 | 823.806394ms | 823.797082ms | **0.009312ms**, 실질 개선 없음 |
| 시작을4ms 늦춘 별도 비교 | 819.806398ms | 819.797086ms | **0.009312ms**, 같은 결론 |

복원은3.83..3.96ms다. VRAM DMA가 끝나고 마지막 palette/OAM 표시를 준비한 시각도 대략−15..+18µs 범위로 거의 같았다. 단순히 마지막 ACK polling만 남은 문제가 아니라, 절약한 선로 시간 일부를 복원이 사용하고 뒤의 VBlank/DMA 일정에서 이득이 흡수된다. **wire 절감5.48ms에서 복원 비용만 빼서 전체 가속을 주장하지 않는다.** 시험의 최장 decoder service 간격은1.658ms였고 중간 STOP 뒤 이전 표시 identity/픽셀 보존을 확인했다. STOP 지연 개선을 주장하지 않는다.

이 시간 모델은 실제 ARM 계산·IRQ·source 준비·ROM 경쟁과 공통 시계가 아니다. 별도로 actual M4 계산/CRC 비용을 계측했고, actual C→source/ROM/SPI RTL→실제65816→STOP/base 공동 실행도 통과했지만 **그 첫 boot 프레임은 raw0**이다. raw 복원·DMA의12프레임 검증과 합쳐 하나의 완전한 물리 시간 증명으로 표시하지 않는다. 새 실기 메뉴 복귀/FPS는 미측정이다.

## 검증과 보존

- 실제 M471개 canonical 상태/계획 일치·expired scratch 밖 쓰기 없음. raw0..7 sender8벡터와 실제65816 두 bank16벡터로 compact1/2와 canonical fallback3..7을 확인했다. 이 경계 벡터는 합성 입력이며 유효한 전체 게임/HDMA 의미 시험은 아니다.
- 실제 M4 window CRC16/CRC8·credit·barrier6표본, 기존 delayed ACK/잘못된 CRC·generation·token/STOP/불확실 E1 등12소유권 사례 통과.
- 실제6581612프레임 전체239행 RGB·canonical/VRAM·VBlank 최종 ACK 통과. 이전 버전/count8/count0/잘못된 길이/mode5종은 두 번째 표시를 거부했다. 복원 중/raw DMA 뒤/최종 표시 전 STOP3종은 이전 identity/픽셀을 보존했다.
- 같은 board02/source closure의 actual C/RTL/65816 첫 표시·34ACK·STOP/base, 확장 ROM8196읽기/23위상 통과. 한 Starter FLOAT 좌석으로 순차 실행했다. 실물 IO 증명은 아니다.
- whole FIT의 ROM MIF8192B가 선택 program과 byte 동일함을 확인했다. 관련 setup 실패를 false-path나 seed 재시도로 숨기지 않았다.
- 느린 CPU scatter·중간 복사 후보, bank register/주소 모드 오류를 잡은 canonical 반례,4KiB 초과/branch 범위 실패, 초기 fixture 경로/로딩 오류와 이후 통과를 모두 별도 로컬 산출물로 보존했다. 더 빠른 과거 direct-VRAM prototype의 시간과 현재 canonical 후보의 비용을 합치지 않는다.

## 다음 순서

1. setup 최악 경로 `loader_boot|boot|check_failed`→`loader|byte_hold[7]`의 reset/control fanout을 추적한다. CRC 실패와 같은 클록의 바이트·STOP·복구를 보존하는 실제 제어 변경을 먼저 기능 검증한다. 타이밍 예외 추가/같은 seed·FIT 반복으로 통과시키지 않는다.
2. raw 복원과 VRAM DMA를 함께 줄일 구조를 비교한다. strided low-plane DMA와 암묵 plane 관리 같은 후보는1↔2행·bank 재사용·clear 도중 STOP·최종 ACK까지 증명하고, 같은 시작 시각의 최종 표시 시간 개선을 먼저 요구한다. 5KiB 등 실제 code에 맞는 ROM 배치도 비용 후보이며 절감이 보장된 것은 아니다.
3. 선택 구조가 정해진 뒤 **한 번의 같은-source whole Lite FIT/관련 timing**으로 비용을 확정한다. 시간·timing을 둘 다 통과해야 새 번호·marker·로그·원복을 갖춘 전달본을 만든다. 현485/482/476/164/467·GBC/save는 보존한다.

## 재개·재현

공개 레시피는 `tools/nes_compact488.py`, `prepare_nes_compact488_board.py`이며 관련 `audit/test/analyze_nes_compact488*`가 실제 실행 검증을 수행한다. 로컬 선택은 `probes/nes-compact488`의 candidate05/ARM06(계산 시험 ARM04와 payload 동일)/audit06/window01/sender02/armguards02/client14이며 board02·snes22/25/26·unit02·live03·bootbus03 원시 실행은 ASCII 임시 경로에 있다. 절대 경로·ROM/바이너리·raw 로그는 Git에 넣지 않는다.

재빌드는 기존487 ARM 및482 board의 동결된 전체 로컬 원본,905..975 입력/reference, 정당한 동일 SMB3 원본과 도구가 필요하다. `cores/nes/REPRODUCING.ko.md`의 재현 부채는 해소되지 않았다. ARM build wrapper와 FLOAT job에는 절대 경로를 사용한다. 다른 PC에서는 저장소의 판정·순서를 읽되 없는 자료를 임의 fixture로 대체하지 않는다.
