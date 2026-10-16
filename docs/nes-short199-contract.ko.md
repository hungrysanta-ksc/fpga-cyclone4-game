# NES199 무손실 공통 타일 명령

PR117 후보를 이어가는 변경이다. 배포186/세이브 SRAM/GBC164는 변경하지 않았다. 이전 프레임 캐시가 아니라, 같은 타일 계획에서 반복되는 기본값을 짧게 표현하는 구현이다.

## 접근 결정과 작업 의미

198은 계획 송신을 묶었지만 일반 BG512개의 계획payload8192B만 SPI2.625MHz에서24.966ms였다. 기존191 planner는 매 프레임 슬롯을 다시 배정하고, bg_keys를 OBJ 검사와 raw patch scratch로 덮어쓴다.195 sink는 연속 bg_next/obj_next를 요구한다. 따라서 tag가 같다는 이유로 계획을 생략하면 연속staging 및 destination 소유권 계약이 깨진다. 별도 이전계획 배열을 추가하면 ARM 메모리 예산도 다시 검증해야 한다.

199는 원본/출력 타일 수·순서·generation·slot·내용을 유지하고, 가장 흔한 identity row 계획을 줄인다. 프레임 건너뛰기나 게임 처리 생략이 아니다. 일반 BG는16→7B, OBJ는16→8B, zero/END는16→3B다. 행 변환과 cross-tile 예외는 기존16..32B 형식 그대로 보낸다. 새 지속cache나 payload RAM은 추가하지 않았으며 실제FIT 자원 증감은 미측정이다.

## Wire와 decoder

E8 상태 version은3으로 바꾼다. E9 framing은198의 lengthLE16/plans/payloadCRC16/framingCRC8/A5 그대로다. payload 최소3B이며 홀수길이도 허용한다. 전체CRC/정확한길이/credit/common cancel은 유지한다.

| 첫byte | 길이 | 나머지 필드와 복원값 |
|---|---:|---|
| 80 | 7 | generationLE16, slotLE16, tagLE16. BG/maskFF/각plane행0..7/alt없음 |
| 81 | 8 | 위 필드와 mask8. OBJ/각plane행0..7/alt없음 |
| 82 | 3 | generationLE16. BG zero, 나머지필드0 |
| 83 | 3 | generationLE16. END, 나머지필드0 |
| 00..03 | 16..32 | 기존196 full form, version1 및 alt tags 포함 |

marker의 reserved bits, tag/slot 상위bits, BG slot0, OBJ slot128 이상·mask0, lease generation 불일치, 잘린 명령, 남은bytes, END 뒤 다른계획은 거부한다. 길이가 짧다는 이유로 신뢰하지 않는다. 한 묶음에 short/full 혼합 가능하다.

새 encoder는 기존196 입력 검사를 통과한 뒤에만 줄인다.16개 row가 모두 identity이고 alt가 없을 때만 짧은BG/OBJ로 보낸다. 임의row/alt는 full form으로 돌아간다. palette는 원래 계획필드가 아니며 이번 변화로 생략한 것이 아니다.

decoder는 short 시작에서 mask/rows/alt/slot/tag를 명시적으로 초기화해 이전full 계획의 필드가 남지 않게 한다.198의 두bank1024×8RAM, 마지막계획decode 후mailbox 반환, tile_done까지held fields를 유지한다. C199도248B buffer/240B payload/15계획 한도와 in-place DMA 계약, 대기 중195 op7소비, guard, terminal/no-retry를 유지한다. 한frame/commonreset session 제약은 아직 남는다. final displayACK가 없는 상태를 재사용 가능한 이전frame으로 승인하지 않는다.

## 검증과 성능 해석

SELECT `probes/nes-short199/test01`, `faults01`, `c01`, `evidence01`.

- 실제SPI→199RAM→192qualified70ns READ16→193aperture에서8합성장면97계획1840출력B가 변경 없는186 reference와 동일하다. 일반행·변형행·cross-tile·OBJ mask·raw0/1/7행을 포함한다. 모든199 run은 실제설정과 같은2.625MHz/4×2us wait 모델이다.
- 512개 일반BG+END의 계획payload는8208→3587B다. 묶음 수35/출력8192B/4chunk는 동일하다. 동일source/pin 모델의 경과시간이198의32.096399ms에서199의17.944424ms로 감소했다. 이는 이 합성workload의 전송경로 비교다. 실제스크롤 감소율이나 게임FPS가 아니다.
- 해당시험은 raw SNES bus consumer이며 실제C scheduler/실제65816 finalSEAL을 함께 실행한cosimulation은 아니다. fullwait/sourcewait는0이므로 포화 검증도 아니다.17.94ms 자체가16.67ms보다 길고 게임 준비·최종표시까지 더해지므로60fps 달성으로 판단할 수 없다.
- SPI/decoder37검사: 기존23경계와 short4종 최대필드 복원,10잘못된short 검사를 포함한다.2bank/512B 최대full묶음/STOP/credit/CRC/중간fault 검증을 유지했다.
- 실제C199+195sink24검사, 별도codec283검사 통과.8장면+512pressure의43송신frames는 독립Python 압축기로 생성한RTL 입력과 byte-exact다. SPI/SNES ACK는mock이다. 기존198 DMA in-place744정상/248오류 증거는 변경 없이 재사용한다.
- 이전198까지14개 archive의 hash를 확인한다. 전체ARM/FIT/STA/IO/새FW/ZIP/실기결과는 없다. 전체RAM과callback stack 승인은 별도다.

## 다음 작업

추가로 작은codec만 고치는 반복 대신 **여러frame의 실제수명 연결**을 다음 우선순위로 한다. frame lease/content epoch, END 재무장, fresh token, producer/board mux/C runtime/최종SNES ACK·STOP을 결합해야 실제 첫레벨에서 전송량과시간을 잴 수 있다. 프레임마다NES전체reset을 사용하면 안 된다.

현재코드에서전송을생략하는cache는 미구현이다. 이후delta를 추가할 때에는 실제표시완료의 base generation, WRAM/VRAM bank, slot ownership, row/alt/mask, physical tag와content epoch/CHR-RAM write를 함께 검증해야 한다. 실패·STOP·raw전환에서 불확실한캐시는 폐기하고 bounded rebuild한다. hash충돌이나 tag만으로동일내용이라고가정하지 않는다. 신규cache의메모리비용을 전체ARM/FIT예산에 포함한다.

최소결합 검증과 전체ARM/FIT/IO 뒤에는 짝패키지로 실제첫레벨스크롤을 측정한다. 숫자1+A→레벨확인→RIGHT+B유지/Apress-release반복. collected_runs는 아직 비어 있고, 정지/오프닝/합성/ACK수로 대체하지 않는다. 약60fps+사운드→장기play/오류·reset로그→입력유지 품질 순서를 유지한다.
