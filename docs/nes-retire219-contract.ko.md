# NES219 응답 차단과 카운터 데이터 선택

## 작업 의미

216 정상 대기 처리와211~212 변경 범위 출력을 실기에서 검증할 수 있도록,218에서 남은 전체 FPGA 타이밍 실패를 정리한다. SPI 속도·게임 프레임 제한·오류 검사·클록·SDC·핀은 변경하지 않는다. 국소 경로 개선이나 기능 검증은 전체 타이밍 통과 또는60fps 증명이 아니다.

## 변경

봉인된218 source02의90개 소스 중 첫 후보는 SPI와로더2파일, 두 번째 후보는 CHECK 연결까지3파일을 변경한다.

- SPI 명령 출력의 응답 주소 비교를 하위9비트/상위10비트의 명령별 허용 신호로 나눈다. 중간 허용 신호에 keep을 사용해 합성 시 모든 출력이 공통 error_response 배선을 경유하도록 합쳐지는 것을 줄이는 후보다. 실제 효과는 FIT로 판단한다. 두 부분 모두 현재 에지의 응답 주소와 고정 READ tag를 비교하고, 응답 유효·busy·enable·fault·SS 조건을 같은 에지에 적용한다. counter retirement와 오류 상태 계산은 그대로다.
- 로더의 `count_update` 허용식은 그대로 두고 데이터 입력의 초기화/증가 선택을 단순화한다. 갱신이 허용된 경우 reset이 아니고 one-hot RELEASE이며 STOP이 없으면 증가이고, 나머지는 초기화다. 기존 phase one-hot 불변식이 전제이며 임의의 multi-hot 레지스터 손상까지 동등하다는 주장은 하지 않는다. unused state encoding도 단일 비트인 경우 비교한다. 데이터 선택에 사용하던 긴 count_clear 경로를 없애며 카운터 갱신 시점·값은 유지한다.

## 기능 검증 범위

로더:294912상태/1056실제 쓰기 시퀀스/524288count/131072이전 오류코드 조건, 잘못된 상태·STOP 처리 negative. phase one-hot/terminal 불변식과 출력 핀·WRITE/HOLD drain을 기존 실제 회로와 비교한다.

SPI:1056768상태 에지/1024후속 시퀀스에 더해,256개 live 조건 ×64개 승인 pulse mask ×19개 단일 주소 비트 오류와 일치 조건 =327680경계를 비교한다. 상·하위 주소 검사를 각각 제거한 negative가 검출되어야 한다. 새 로더+SPI+boot+reader 조합에서 실제2.625MHz SPI/SS-high2us219거래/14016MISO비트/100READ/7ACK/19손상/72취소/2중첩을 확인한다. 실기 게임 시험은 아니다.

변경 없는216 wait와217 epoch는 소스 해시와 기존 증거를 재사용하며 재실행했다고 표시하지 않는다. GBC164·저장SRAM·완료archive는 보존한다.

## 배포 조건

전체3corner nominal/strict setup·hold,96 epoch register reset, CDC 첫단계/held/Gray, 조건부 PSRAM/SNES/SPI I/O 검증 후에만 새 ARM 식별자·현재212 SNES ROM을 결합한 ASM/ZIP으로 진행한다. 전체 전기적 signoff나 MTBF 계산을 대체하지 않는다. 최종 결과는 `analysis/retire219-verification.json` 및 `probes/nes-retire219/progress.json`을 참조한다. 동일215/044 반복 또는 추가 영상은 수정판 전에는 요청하지 않는다.

## 두 번째 후보의 CHECK 연결

첫 후보의 최악 경로는 `control.fault → boot.check_failed`였다. `nes_spi_boot`에서 CHECK enable을 다시 `!spi_fault`로 마스킹하는 배선이 포함된다. 실제 SPI 상태 회로는 reset에서 fault=0/enable=0이고, fault가 새로 설정되는 에지에는 enable도0으로 기록한다. fault가 이미1이면 enable=0을 유지한다. 따라서 도달 가능한 상태에서 fault→!enable이 유지된다.

source02는 이 조건부 불변식의 실제 RTL 전이 검사와 연결 시험을 통과해야만 `boot.check_enable`을 control의 enable에 직접 연결한다. `read_reset || spi_fault`, 외부 RUN/loaded/load_ready의 fault 차단, loader의 WRITE/HOLD drain은 그대로다. 임의로 fault=1/enable=1을 동시에 주입한 비도달 상태까지 동등하다고 주장하지 않는다. 실제219거래 fixture는 원래 raw enable 연결을 쓰므로 그 연결에서 불변식을 추가 검증한다. 전체 보드의 모든 입력을 함께 시뮬레이션한 것으로 표현하지 않는다.

## 최종 결과와 다음 작업

기능 검증은 모두 통과했다. CHECK 불변식은1211304조건부 전이에서 유지되며, 오류 시 enable 해제를 제거한 negative가 검출된다. 전체 보드3corner nominal/strict setup은 두 후보 모두 실패했다. source02는 다음 분석을 이어갈 기능 후보이지 배포 승인 또는 전체 타이밍 개선판이 아니다.

| 후보 | LE / FF / LAB / M9K | nominal / strict setup | hold | 판정 |
|---|---|---|---|---|
| source01 응답 분할+카운터 |15152 /8352 /956 /47|−0.323 /−0.323ns|+0.138ns|미채택|
| source02 CHECK 중복 게이트 제거 |15131 /8352 /955 /47|−0.611 /−0.611ns|+0.154ns|미채택|

source02는277LE/8LAB/9M9K 여유다. 카운터 대상은+0.312ns, 응답→명령 출력은 nominal+0.329ns지만 엄격 응답→오류 상태 경로에는−0.153ns가 남는다. source01의 fault→check_failed 경로는 source02에서 사라졌지만 다른 경로가 악화되었다. 이 때문에 후보를 누적하면 자동으로 타이밍이 좋아진다고 판단하지 않는다.

최악 경로는 diagnostic_release.release_reset[1]→boot.run_enable→control.snapshot[42],6.493ns/3LUT/배선4.880ns(75%)다. 이는 같은168MHz 도메인의 상태 데이터 경로이며 비동기 reset 예외로 지울 수 없다. run_enable 두 배선1.917ns/1.835ns가 크다. 별도로 load_valid→loader.phase[4]는−0.392ns/6.267ns/6LUT/65%배선이다. `paths04/snapshot219-implementation-0-status.rpt`와`-receive.rpt`, `paths03/fault219-implementation-0-response.rpt`를 함께 확인한다.

다음 작업은 상태 snapshot의 첫 바이트 capture/이후 shift 조건과 boot 상태 마스킹의 공유 범위, RECEIVE 자격 조건을 함께 정리하는 것이다. 원래 에지의 flags·reset·fault 우선순위와 현재 응답 주소 오류 차단을 보존한다. 단순 seed/CE 속성 변경이나 같은 후보 재FIT, 이미 개선된 epoch 수식 재작성으로 돌아가지 않는다. 상태 응답을 한 클록 늦추거나 status snapshot 시점을 바꾸는 것도 동등한 변경으로 취급하지 않는다.

source02의 CDC4392행/45첫단계 단일 fanout/새 미분류 data0, held6.587ns/Gray6.737ns,96register/576reset 경로 최소39.721/1.740ns는 통과했다. 조건부 PSRAM 여유+0.943ns, SNES86.854ns/SPI167.754ns envelope와 native payload reset도 통과했다. 이는 전체 전기적 signoff나 MTBF 증명이 아니다.218 archive5057파일 불변을 검증했다.

새 ARM/ASM/ZIP 및 실기 시험은 없다. 선택 source02/counter01/spi01/enable02/mapfit02/timing02/io02/paths03+04/evidence03. 기능용 source01 증거는 두 후보의 SPI·로더가 byte-identical임을 검증하여 재사용한다.216 wait/217 epoch도 재실행하지 않았다. 원본 실패 후보·원시 보고서를 모두 보존한다.
