# NES220 RUN 상태·READY 전환 조건 정리

## 작업 의미

216 정상 대기 수정과211~212 변경 범위 출력을 실기에 보내기 위한 FPGA 타이밍 정리다.60fps 처리량 개선 자체가 아니며 전체 타이밍과 현재212 ROM 짝 검증 전에 설치판을 만들지 않는다.

## 변경과 전제

봉인된219 source02의90개 파일 중 로더1파일만 변경한다. SPI snapshot의 capture/shift 시점과 내용, 현재 에지의 응답 오류 차단, 외부 PSRAM reset gate는 그대로다.

- `run_enable`에서 `!active_reset`을 제거한다. phase 레지스터가 비동기 reset에서 IDLE로 초기화되고 local release 동안 IDLE을 유지하므로, 정상 도달 상태에서 RUN은 active_reset이 아님을 뜻한다. sticky fault 차단은 유지한다. 임의로 reset과 RUN 상태를 동시에 강제한 손상까지 동등하다고 주장하지 않는다. 비동기 reset의 물리적 전파 지연이0이라는 주장도 아니다.
- READY 전환의 세 출발 상태별 조건을 직접 표현한다. RECEIVE에서 END를 승인하면 commands_blocked가0이므로 그 뒤의 중복 accepted/receive_bad 조건을 전개할 수 있다. 다른 명령과 STOP, count_complete, fault 조건은 같은 에지에 적용한다. READY 대기와 RUN→STOP도 원래 의미를 유지한다. 새 상태·지연·타임아웃·RAM은 없다.

## 검증

실제219/220 로더를294912상태/1056쓰기 시퀀스/524288count/131072이전 오류코드에서 비교한다. READY를 RUN으로 잘못 노출하는 후보와 END+STOP을 잘못 승인하는 후보를 negative로 사용한다.

별도로16상태×64명령×2blocked의2048경우에서 비동기 reset을 인가한다. 메모리 클록이 멈춘 assert/release 구간 및 이후4에지에서18432회 상태를 검사한다. reset 중 IDLE과 RUN 비노출, 기존 출력과 일치가 필요하다. 실제 SPI+새 로더+boot+reader219거래/14016MISO비트/100READ/7ACK/19손상/72취소/2겹침도 확인한다. 전체 게임/실기/물리적 glitch 검증은 아니다.

변경 없는SPI219 상태 전이·216 wait·217 epoch는 기존 증거를 재사용하고 재실행했다고 표시하지 않는다. 전체3corner nominal/strict setup·hold, reset96reg, held/Gray/CDC 및 조건부 I/O를 기존 기준으로 평가한다. clocks/SDC/pins/GBC164/저장SRAM/완료archive는 보존한다.

## 두 번째 후보

첫 후보에서 상태 snapshot은+0.286ns, READY 전환은+1.030ns로 통과했지만 전체 nominal−0.234ns/strict−0.485ns/hold+0.135ns였다. FIT15206LE/8352FF/960LAB/47M9K. 남은 최악은 response_address[2]→control.fault,7LUT/6.372ns/배선69%이며 공유 always10 노드의12fanout에서fault까지1.668ns 배선이 있었다. 조건부 I/O 등은 통과했지만 배포 후보는 아니었다.

source02는 첫 후보에 SPI1파일 변경을 더한다. sticky fault를 별도 동등식으로 기록하고, 응답 주소 상하위 비교를 CHECK 상태별 허용식과 분리한다. 새 레지스터나 에지 지연은 없다. fault가 이미 설정됐을 때 유지하고, 오류 코드의 우선순위와 checked_data 허용식, load_chr32 및 명령 pulse/카운터 처리는 그대로다. 원래 SPI 상태와1056768에지/1024후속조건/327680주소경계를 비교하고, 하위·상위 fault 검사를 제거한 negative를 확인한다. 새 로더+SPI의 실제219거래도 검증한다. source01의 로더 증거는 해시가 같은 source02에 재사용한다.

시험 구성 이력: test01은 비교용 SPI 모듈 연결 누락으로 wire 실행 전 실패했다. test02의 정상 로더/reset/wire는 통과했지만 STOP negative가 예상한 DIFF보다 먼저 one-hot assertion에서 검출돼 수집기가 거부했다. test03은 소스 동일성을 확인하여 test02 정상 로그를 재사용하고 두 negative를 다시 실행한다. 제품 RTL 수정으로 고친 실패가 아니며 각 원본 로그를 보존한다.

## 최종 결과 — source02 실기 시험으로 진행

두 번째 후보의 전체3corner nominal setup+0.298ns/strict setup+0.121ns/hold+0.142ns가 모두 통과했다. FIT15156LE/8352FF/957LAB/47M9K,252LE/6LAB/9M9K 여유다. source01보다50LE/3LAB 적으며 새 FF나RAM은 없다. 기존 대상 snapshot+0.594ns/READY+1.614ns, 응답→오류 상태+0.121ns다. 첫 후보와 실패 보고서도 보존한다. clock/SDC/seed는 바꾸지 않았다.

CDC3984행/45첫단계 단일fanout/새 미분류data0,held6.630ns/Gray6.948ns와96reg/576reset 최소40.341ns/1.553ns가 통과했다. 조건부PSRAM+2.924ns/SNES83.559ns/SPI168.997ns와native payload reset도 통과했다. 전기적 전체signoff·MTBF·실기 성능을 증명한 것은 아니다.219 봉인5670파일을 확인했다.

ARM220은215에서 식별자3파일만 변경한다.207536바이트/static27868/RUN32096/IRQ508/여유4952바이트. 실제215 실행 루프·입력·소리·60초 제한·로그 schema와 플랫폼 코드 검사를 유지했다. 새 FPGA에는 검증된 배선을 다시 FIT하지 않고 현재212 SNES ROM4096바이트만CDB/ASM/CPF로 결합했다. 실제 EDA3출력의ROM4096바이트가 모두 일치한다.

보드 검증은 `analysis/status220-verification.json`, 최종 ARM/FPGA/ROM/ZIP 및 설치 가능 여부는 `analysis/release220-verification.json`을 참조한다. 선택 source02/test03/spi02/mapfit02/timing02/io02/paths02/evidence03/arm01/check01/asm01/romcheck01/release01. 실기에서216 정상 대기 수정이 스테이지 선택과첫레벨 조기 종료를 해결했는지 확인하는 단계다.60fps는 아직 미확인이다. 다음에는 동일215/044를 반복하지 말고 [NES220 안내](nes-game220-ready.ko.md)에 따라 숫자1+A→첫레벨 스크롤/세TXT/소리·조작·메뉴 복귀를 확인한다.
