# NES181 ROM 응답 로컬 캡처의 보드 결합·배선 결과

**실제 보드 결합과 배치·배선은 성공했다. 혼잡은 줄었지만 전체 실제 타이밍은 여전히 실패하여 실기 패키지는 만들지 않았다.** 선택 근거는 `replyjoin181/test03 + map02 + scope01 + route01`이다. [검증 데이터](../analysis/replyjoin181-verification.json), [이전 공식 문서 조사](nes-routing181-design.ko.md).

## 작업 의미와 변경 범위

실기 화면 출력을 위한 FPGA 전달 구조 개선이다. memory 클럭의 ROM 데이터가 CPU·PPU 캐시/우회 경로와 영상 FIFO까지 직접 퍼지던 연결을 NES 클럭의8비트 `reply_data`에서 받는다. 이후 소비자 연결은 NES 클럭 내부에 남는다. Altera 공식 지침에 따라 혼잡과 제어 신호의 지역성을 개선한 것이며, seed·클럭 완화·전역 false-path 변경은 없다.

기존 CDC181의69개 보드 입력 중 `nes_rom_physical.sv`, `cdc181.sdc`만 바뀌었다. 이전 reader 후보와 동일한 LF 바이트를 사용한다. 보드핀, PSRAM READ16/HOLD/RELEASE, request/ACK/ready/주소, CHECK, CPU·PPU 서비스, 영상 fill과 중재기는 그대로다. 기존 ARM/SNES는 재빌드하지 않았다. 외부 세이브 SRAM·GBC·164복원본·180배포본도 변경하지 않았다.

## 응답 계약과 결합 시험

`reply_data`는 매 NES edge에 held byte를 샘플링하지만, **ACK 두 번째 동기화 단계에 따른 기존 `rom_response`가 유효할 때만** 사용한다. 유효하지 않을 때의 데이터 값은 기존과 같다고 보장하지 않는다. ACK와 데이터가 함께 memory edge에서 시작된 뒤 첫 ACK 샘플과 다음 ACK 단계 사이에 데이터가 안정되어야 한다. 실제 데이터 지연은 별도로 검사한다. 응답이 난 다음에야 데이터 FF를 갱신하면 늦으므로 해당 대조군은 실패해야 한다.

이번 테스트는 실제 `nes_rom_early` → `nes_native_arbiter165` → `nes_rom_physical`과 실제 `nes_native_fill165` FIFO를 연결했다. CPU/PPU 주소·sample·prefetch와 vblank 허용 슬롯/조회표는 모델이다. 전체 NES CPU/PPU 코어나 SMB3 replay를 새로 돌렸다는 뜻은 아니다.

주소에 따라 값이 달라지는70ns PSRAM 핀 모델, NES45.454ns/메모리5.952381ns, 메모리 위상16개(0..5.625ns)를 사용했다. 기존 reader, 새 reader, 새 reader에9.904ns 데이터 전파 지연을 더한 경우의 **관측 transcript가 모두 동일**했다.

각 버전에서16위상을 합친 결과:

- 유효 ROM 응답1,776회: core928, fill768, 취소되어 폐기된80회.
- CPU/PPU 소비912회, 응답과 다음 요청이 같은 edge인16회, core 우선권16회.
- fill 취소·drain·리셋 없는 재사용80회, core/fill 요청 중 공통 리셋160회.
- 위상당48byte/3tile 전송 완료, FIFO 데이터·태그 확인. fill 응답 시 최대 arbiter `age=4`로 기존7edge 한도 유지.
- 응답 이후에 캡처하는 잘못된 대조군은 qualified byte 불일치로 실패.

이전 reader 단독의 clock-stop/핀 비교는 재사용한다. 이번 결합 시험만으로 전체 STOP 명령/MCU/SNES 복귀, 임의 모든 PPU 스케줄, 메타안정성 또는60fps를 승인하지 않는다. 실제 RUN/STOP 활성 제어는 아래 다음 작업에서 별도로 다룬다.

## 합성 경계와 예외 범위

실제 합성 DB에서8개의 `data_hold[i] → reply_data[i]`가 각각 대응하고, 각 held bit의 NES 대상은 수신 FF 하나뿐임을 확인했다. 그 뒤의 timed 데이터 소비자는 모두 NES 클럭이다. 이전 분석의1,257개 memory→NES endpoint/clock 조합이8개 경계로 줄었다. 이 숫자는 물리 배선 개수나 직접 fan-out 개수가 아니다.

새8개 경계에만 `set_max_delay 11.904ns`와 hold-only 예외를 적용했다. 별도 물리 data-delay 기준은9.904ns다. Quartus Standard의 max-delay에는 clock 경로도 반영되므로 설정 slack만으로 데이터 안정 시간을 판정하지 않는다. full false-path를 적용하지 않으며 기존128 payload·17 first-stage 제약은 유지한다.

같은 새 합성 DB에 새 제약 적용 전/후를 비교했다. 고유 clock 교차 검사 조합4,320→4,312 중 **예상한8개 hold만 제거**됐다. setup, recovery/removal 및 같은 PLL 경로는 추가 제거가 없다. 기존 CDC coverage486행·17개 first-stage→second-stage 단일 연결도 재검사했다.

## 실제 배치·배선 결과

| 항목 | 이전 CDC181 | 새 로컬 캡처 결합 |
|---|---:|---:|
| 전체 FIT | 성공 | 성공 |
| LE / LAB / M9K |15,072 /963 /38 |15,048 /963 /38 |
| 배선 평균 total/H/V |68.8 /67.8 /70.2% |61.4 /61.7 /60.9% |
| 배선 peak total/H/V |86.2 /87.2 /91.2% |79.5 /84.4 /75.8% |
| 실제 관련 클럭 최악 setup |−3.379ns |−1.408ns, 실패 |
| 실제 hold 최악 |+0.146ns |+0.147ns |
| 같은 PLL 간 setup 최악 |−0.740ns |−1.408ns, 악화 |
| 같은 클럭 내부 setup 최악 |기존 memory 경로−3.379ns |−0.088ns, 실패 |

전체 최악 값과 혼잡은 개선됐으나 같은 PLL 간 경로는 악화됐다. 이를 타이밍 통과 또는 일관된 모든 경로 개선으로 표현하지 않는다. LAB는 여전히963/963이다. 새 구조가 배선 부담을 줄였다는 증거는 있지만 실기 설치에 필요한 여유는 없다.

3corners의 새 캡처24행은 최대 데이터 지연3.130ns로9.904ns 기준을 만족했다. 기존 CDC486행도 통과했다. 조건부 PSRAM70ns 여유+3.527ns, SNES 응답 envelope79.110ns/270ns, SPI162.820ns/190.476ns, native payload의 음수 reset 경로0이다. 별도 동기화/수명주기 reset 표본24개는 남아 있으며, 전체 IO/CDC/MTBF signoff는 아니다. PCB·전기적 가정은 기존 조건부 모델을 유지한다.

실제 FIT 원본421파일을 고정하고 STA는 복사본에서 실행했다. 원본은 해시가 유지됐으며 복사본의 도구 캐시 변경만 허용했다. 추가 seed/FIT 반복·ASM·RBF·실기 ZIP은 실행하지 않았다.

## 남은 병목과 다음 작업

최악 경로는 memory 클럭의 `loader.release_reset[1]`에서 host 클럭의 `sink.endpoint.ack_work[42]`로 간다. 실제 data delay7.177ns, setup−1.408ns다. `run_enable = !active_reset && !fault && phase[RUN]`, boot의 `!check_failed`, top의 `run_enable && !core_reset`이 sink `active`와 endpoint `enable`을 거쳐 ACK 쓰기 조건에 연결된다. **동일 PLL의 관련 클럭이므로 비동기 예외로 자르지 않는다.**

다음은 host 영역에서 활성 상태/ACK 갱신을 처리하는 구조를 설계한다. 먼저 아래 계약을 고정한다.

1. RUN 시작 시 host가 준비된 뒤에만 패킷·ACK를 받아들인다. 단순1클럭 지연 추가를 기존과 동등하다고 주장하지 않는다.
2. STOP/reset/error 시 외부 SNES 버스 출력은 즉시 비활성화하고, 진행 중 패킷·ACK는 폐기한다. host 상태의 늦은 해제가 이전 세대 ACK를 되살리면 안 된다.
3. 실제 SPI endpoint와 SNES bus를 함께 연결해 START/STOP/오류/ACK publish 충돌과 재시작을 짧게 검증한다. 현재 request/packet/최종 ACK 소유권을 보존한다.
4. 같은 클럭 내부 CHECK 제어−0.088ns도 남아 있다. 먼저 큰 host 활성 제어 구조를 반영한 후 전체 보고서에서 다시 평가한다. 예전 loader 미세 수정·seed 반복으로 돌아가지 않는다.

전체 실제 timing/조건부 IO와 paired ARM 적합성을 통과한 뒤 SMB3 숫자1 타일→A 실기로 간다. 화면 지속과60fps, raw 전송 약53ms 모델·최대7vblank+final의 개선은 여전히 남아 있다. 이번 배선 개선을 프레임 속도 개선으로 계산하지 않는다.

보존된 실패: test01은 예약어를 변수명으로 써서 compile 실패, test02는 기준 설계에서도 clear 펄스가 sampling edge를 지나지 않아 fixture 실패였다. test03에서 수정했다. map01은 CRLF 후보 해시 검사 실패 뒤 불완전 준비 상태로 MAP가 잘못 실행됐고 FIT는 하지 않았다. map02는 LF 해시가 일치하는 준비본이며 모든 후속 단계는 종료 코드를 확인해 진행했다. 실패 자료를 삭제하거나 선택 결과로 바꾸지 않았다.
