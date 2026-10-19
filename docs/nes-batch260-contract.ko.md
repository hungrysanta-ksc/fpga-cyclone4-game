# NES260 — 여러 map 범위의 한 패킷 소유권과 전체 비용

PR130의 같은 브랜치에서259 다음 후보를 구현했다. ARM이 정확한 map 범위를 묶고, FPGA가 한 queue head 아래에서 범위마다 staging→DMA→receipt를 반복한 뒤 마지막에만 packet credit을 돌려준다. production227/GBC164/saveSRAM은 그대로다. 아래 시간은 실제 ARM 명령 실행과 RTL에 SNES 서비스/CPI를 배정한 일정이며 물리60fps가 아니다.

## 실제 구현과 수명

`nes_output260.c`는 기존259 ABI를 유지해 같은 Cortex-M4/SPI 시험 경계를 사용한다. 259의 범위별op12 전송을op14 묶음으로 바꿨다. 총256B 이하이며16B 공통 header,4B 시작 token,1B 범위 수, 범위마다2B byte offset+1B byte length+값을 담는다. offset/length는 짝수, length2..64B, 끝은4096B 이하이고 최소 범위만 넣을 때47개까지 들어간다. 전체 packet의 SPI command/CRC는3B다. header의14..15는0이며10..11은 이 형식에서 사용하지 않는다. 마지막 범위가 packet 끝과 정확히 일치해야 한다.

ARM은 기존 계획의 연속 map records를 packet 경계에 맞춰 쌓는다. 기존 packed-map packet 경계를 넘어서도 묶을 수 있지만 일반 명령 전에 반드시 flush한다. tile-end barrier 이후 연속 token을 예약하며 token FFFFFFFF는 발급하지 않는다. 기존 wire buffer를 재사용하고 batch 길이4B만 추가했다. `send`의 credit 대기는 별도 status buffer를 사용하므로 아직 보내지 않은 batch를 덮어쓰지 않는다. 네 packet credit과16bit sent/retired counter의 순환 규칙은 유지한다.

FPGA는 공통 header와 token 범위를 먼저 검사하고 각 descriptor를 동기식 queue RAM에서 읽는다. 각 범위는 기존 aperture에 seal하고 실제 bus read가 모두 끝난 token consume 후 receipt를 기다린다. 마지막이 아니면 **MAP owner와 동일 packet head를 유지**하고 다음 descriptor로 간다. 마지막 receipt 후에만 qretire/sequence를 한 번 진행하며 한 cycle의 retire 간격 뒤 다음 head를 읽는다. 일반 ACK와 typed retire가 동시에 head를 해제할 수 없다. 기존op12도 회귀 비교용으로 남겨 두었으므로 이번 MAP에는 두 형식의 분기 비용이 포함된다.

잘못된 뒤쪽 descriptor는 앞 범위의 receipt가 이미 완료된 다음 발견될 수 있다. 부분 성공을 표시 완료로 취급하지 않는다. fault/STOP은 queue·staging·외부 가시성을 무효화하고 새로운 identity에서 다시 시작한다. 이미 할당된 token과 serial history는 되돌리지 않는다. ARM이 예약했지만 FPGA가 아직 할당하지 않은 미래 token은 취소 뒤 새 identity에서 쓸 수 있다. 이것은 완성된 화면/기존 유효성의 rollback을 입증한 것이 아니며 실제 core validity/lease의 공통 STOP 연결은 남은 통합 경계다.

## 검증 범위

실제 Cortex-M4 바이너리를 Unicorn에서 실행한71개의 기존2472 계획에서2,069범위를124batch로 보냈다. 독립 검사기는 batch를 원래 범위로 펼쳐 byte offset/값과 일반 명령을 비교하고71개의 H2 인증서도 기존255와 대조한다. packet을 유지한1,945회 poll이 포함되며4credit 사용을 확인했다. 이 endpoint의 한 poll당 한 범위 진행은 기능 검사 정책이다. 처리 시간은 아래 실제 SPI/RTL 연결 실행에서 따로 산정한다.

ARM 오류12종은 CRC/counter/단계·세대/잘못된 계획/HDMA 의미/token 끝값/serial을 포함하며 최초 오류 뒤 추가 SPI와 SEAL이 없다. cold 계획의 counter65530→41,47packets로16bit 순환과 최대4credit을 확인했다.

새 RTL 시험은 공유/분리 staging 각각35경우다. 정상 흐름은13range receipts·2ordinary ACK·3final ACK·bank0→1→0·48DMA bytes를 비교한다. receipt 지연 중 head/credit 유지, 네 credit을 일반/묶음으로 채운 후 순서대로 해제, 다섯째 거절, 잘못된 count/정렬/길이/끝/CRC/identity, stale·duplicate/partial consume, token overflow, 앞 범위 완료 뒤 잘못된 tail, 조기 final ACK를 검사한다. 256B/47범위 packet도 끝까지 소비한다. 취소는 첫/다음 범위 복사, descriptor 읽기, 부분 DMA, receipt 대기, 마지막 consume, 다음 packet까지 대기한 지점에서 수행하고 새 identity로 복구한다. 대기 중 도착한 tile은 batch의 세 범위를 끊지 않고 이후 token4로 처리한다. 기존258의 정상+16guards도 양 구성에서 별도로 재실행한다.

새 output RTL에는 실제 queue/SPI/일반 ACK/typed parser/tile206/공유 aperture/CDC/token/최종 논리 ACK를 연결했다. cold905,heavy952/954/955/962/963/968/970, 느린tile 공급, CPI2, queue 순환을 검사한다. metadata8570B와 tile bytes를 기존 계획과 비교한다. source257 transport도 같은 SPI 핀에 붙여954/963/970과954 CPI2/느린tile을 검사한다. 원래 source255 payload의 진단용243B 분할, 별도 CRC 응답, 무료 query 생산이라는259의 제한은 그대로다.

현재 SNES 서비스는 bus200ns active+200ns release, setup500master-clock=23.28us, COPY/fill560ns/B의 모델이다. receipt는8NEScycle 응답 endpoint다. **이번 batch 전체 흐름을 실제65816/core H2 검증기로 실행한 결과는 아니다.** 이전257/258의 실제65816 한 범위 증거를 이 전체 실행에 확대하지 않는다. tile192/ROM arbiter는 아직 없으며 FETCH_WAIT4→64는 민감도만 나타낸다. 실제 ARM N5 decoder/planner/RUN/IRQ/STM32 driver도 포함하지 않는다.

## 시간 비교

| frame | 259 입력+출력 조건부 ms | 260 출력 ARM 완료 ms | 260 입력+출력 조건부 ms |
|---|---:|---:|---:|
| 952 | 14.647289 | 7.600518 | 12.129473 |
| 954 | 17.302155 | 7.221506 | 13.476551 |
| 955 | 15.844036 | 7.814111 | 12.093156 |
| 962 | 16.575308 | 8.285964 | 13.381010 |
| 963 | 17.099933 | 7.203787 | 12.269878 |
| 968 | 14.239821 | 6.857399 | 11.584081 |
| 970 | 18.039275 | 7.261684 | 13.538093 |

기존 입력 RTL 시간을 합산한 기본 조건의heavy7 최대는13.538093ms다. 이것은 서로 다른 실행의 조건부 합계이며 실제 공용 버스 실행은 다음 표로 분리한다.

| 같은 핀 source+output 진단 | ARM 완료 모델 ms | 16.667ms 대비 잔여 ms |
|---|---:|---:|
| 954 CPI1 | 14.381105 | 2.285562 |
| 963 CPI1 | 12.931113 | 3.735553 |
| 970 CPI1 | 14.447141 | 2.219526 |
| 954 CPI2 | 16.549534 | 0.117133 |
| 954 tile64cycle/B | 14.916772 | 1.749895 |

954의 같은 핀 결과는18.206709→14.381105ms,963은17.761168→12.931113ms다. CPI2의954는잔여0.117133ms뿐이어서 아직 빠진 planner/실제driver/표시를 감당한다고 결론낼 수 없다. CPI2에서는 실제 진행이 달라 F8 조회가27→21회가 되므로 CPI1의 시간을 단순히 두 배로 계산하지 않았다. 느린tile은 실제 ROM 경쟁 측정이 아닌 공급 지연 민감도다.

cold905 출력 ARM 완료는35.618402ms다. 초기 전체 갱신을 정상 스크롤60fps와 구분한다. 954 출력 단독 CPI2는8.126518ms,느린tile은7.757280ms다. counter65530→11의17packet 실행도 통과했다.

954의 절약3.825604ms는 SPI1,020B 감소에3.108568ms, ARM55,989명령 감소에0.666536ms(CPI1), RPC50회 감소에0.050500ms가 대응한다. map wire는1189→337B로852B 줄고 F8 조회7회/168B가 추가로 줄었다. map 범위45개, 값154B 및 전체48DMA/714B는 그대로여서 DMA setup을 줄인 결과로 계산하지 않는다.

ARM 명령수는 실행 관측값이지만 CPI1/2와84MHz는 가정이다. 마지막 RTL final ACK 이후 상태 수신·CRC·함수 반환까지 ARM 완료 일정에 포함한다. 10us 초기 준비와 전송당10ns+1000ns도 포함하고 DONE의100us 정착 대기는 제외한다. source/output 같은 핀 실행에는 입력이 이미 들어 있으므로 예전 입력 시간을 다시 더하지 않는다. 기존 전체 display sample을 그대로 더하면 map DMA를 중복 계산하므로 최종 PPU/VBlank의 남은 항목을 따로 연결해야 한다.

## 회로·메모리 비용과 판정

| 동일 공유 출력 경계 / Lite MAP | 259 | 260 | 변화 |
|---|---:|---:|---:|
| LE | 3282 | 3509 | +227 |
| comb | 2072 | 2339 | +267 |
| FF | 1667 | 1703 | +36 |
| RAM bits | 41216 | 41216 | 0 |

추가 batch descriptor 검사·cursor·범위 제어를 포함한 결과이며 개별 증가 원인을 임의의 gate 수로 분해하지 않는다. 새 RTL9개 hash와 통과한954 실행을 MAP에 고정했다. MAP report에서state와owner 모두One-Hot FSM으로 추출됐다. Quartus Lite25.1std.0 Build1129만 사용했고 Standard 평가판은 재시도하지 않았다. whole FIT/STA는 실행하지 않았다. source/core/collector/display lease/upstream tile192/ROM arbiter는 이 출력 MAP 밖이다. 이227LE를 whole240의490LE/40LAB 부족에 단순 가산하거나 다른 standalone MAP 절약으로 상쇄하지 않는다.

ARM 출력 text2120→2244B(+124),bss308→312B(+4),71계획 관측 stack120→144B(+24)다. caller의8570B metadata/입력 계획 및 RUN/IRQ stack은 별도다. source 진단까지 링크하면2652text/312bss/관측 stack328B다. 전체 ELF와 raw size/result를 보존한다.

**batch는 시간 이득을 확인한 후보이나 회로 여유까지 확보한 후보는 아니다.** 기존 단일범위 parser 등 실제로 대체할 제어를 식별하고 source/core와 출력 receipt/표시의 공통 경계를 연결해야 한다. 다음 판단은 남은 full ARM·실제 SNES·tile ROM 경쟁·최종 표시 비용과 전체 회로 예산을 함께 닫는 것이다. 이 조건을 갖추기 전에는 P2/실기60fps/설치 패키지를 승인하지 않는다. 개별 counter/opcode/seed 조정이나 반복 FIT는 다음 목표가 아니다.

## 재현·보존

선택 경로는 `nes-batch260-plan.json`에 고정한다. `probe_nes_arm260.py`, `guard_nes_arm260.py`는259와 같은 ARM GNU13.3/Unicorn2.1.4/pyelftools0.33를 사용한다. `gate_nes_batch260.py --batch`는 새70경우, 옵션 없는 실행은 기존34경우다. `probe_nes_output260.py`와 `probe_nes_bus260.py`는 승인된 FLOAT wrapper 안에서 절대 job 경로로 실행한다. `gate_nes_batch260.py --map-test <rtl01> --shared 1`은 Lite 한 번의 MAP이다. `analyze_nes_batch260.py`는 raw logs·RTL·ARM loaded image·입력·기존 비교자료를 다시 검사해 payload 없는 CSV/JSON을 만든다.

첫batch01의guard36은 시험에서end_tiles를 DMA보다 먼저 기다린 deadlock이었다. 공급 종료와 DMA를 병행하게 수정했고 RTL은 바꾸지 않았다. 실패 로그는 보존한다. 새 경로의 최종 결과만 선택하며 ROM/map/tile payload·ELF·raw logs는 비공개 `probes/nes-batch260`에 둔다. 공개 소스·분석과 이전 증거를 hash로 고정한다.

최종 선택은arm01/arm-guards01/batch02/legacy01/map01,출력11회와공유SPI5회,analysis02이다. 851개증거hash와16개연결실행을검사했다.

analysis01도검증은통과했으나공개CSV의Windows CRLF가diff --check에걸렸다. 출력줄바꿈을LF로고정하고analysis02에서동일851증거·16실행을다시검사했다. 논리/성능값은동일하며원본도보존했다.
