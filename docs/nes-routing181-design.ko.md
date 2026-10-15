# NES181 배선 혼잡 조사와 수신 경계 재설계

사용자의 요청에 따라 `fpga 배선잡는 노하우` 및 routing congestion, register duplication, Quartus Standard 설계 최적화를 검색했다. 조언의 적용 기준은 **Cyclone IV / Quartus Standard25.1의 실제 배선 결과**다. Pro/Hyperflex 전용 기능을 현재 장치의 기능으로 가져오지 않는다. 검색 결과의 경험담보다 아래 Altera 공식 자료와 실제 소스·보고서를 우선했다.

이번에는 연구 결과를 **ROM 응답의 수신 클록 로컬 캡처 RTL 후보**에 반영했다. reader 단독 시험은 통과했지만 보드 통합·새 합성·FIT·실기 승인은 아직 없다. 기존 배치 성공 결과는 cdc181/map02이고 실제 타이밍은 계속 실패 상태다. [검증 데이터](../analysis/routing181-verification.json).

## 공식 지침과 현재 설계의 대응

| 근거 | 현재 자료에 적용한 판단 |
|---|---|
| [Standard 3.3.1.5.2 Routing Usage](https://docs.altera.com/r/docs/683230/18.1/quartus-prime-standard-edition-user-guide-design-optimization/routing-usage?contentId=YonD0LH~waCChQu9z6oeew) | 평균 배선 사용률과 국소 최대치를 함께 평가한다. 평균65% 초과·국소90% 이상은 문서의 어려움 예상 범위이지 합격/불합격의 절대 기준은 아니다. 이번 평균68.8%, 수직 최대91.2%는 구조적 배선 부담을 줄일 근거다. |
| [Standard 3.4.3.4 임계 경로 양끝의 주변 연결 조사](https://docs.altera.com/r/docs/683230/18.1/quartus-prime-standard-edition-user-guide-design-optimization/tips-for-analyzing-paths-from/to-the-source-and-destination-of-critical-path?contentId=aIZPHF6h1yKSW10lnRhZig) | 최악 한 경로만 고치지 않고 source에서 나가는/들어오는 경로와 destination에서 나가는/들어오는 경로를 함께 조회했다. 새 스크립트로 기존 routed DB 복사본에서306개 경로 행을 수집했다. 새 FIT는 하지 않았다. |
| [Altera Manual Register Duplication](https://www.intel.com/content/www/us/en/docs/programmable/683641/22-3/manual-register-duplication.html) | 복제는 자원을 늘리고, fan-out 수만 제한해도 목적지가 가까워진다는 보장은 없다. 여기서는 원리만 참고한다. LAB963/963인 설계에 전역 maxfan/복제 옵션을 무조건 적용하지 않는다. 같은 생산 데이터를 소비자 클록에서 받는 경계를 우선한다. |
| [Standard Logic Lock 주의사항](https://docs.altera.com/r/docs/683230/18.1/quartus-prime-standard-edition-user-guide-design-optimization/logic-lock-standard-assignments?contentId=xWpmgoVfDvUfDdT_F_TvRw) | 위치 고정이 항상 개선을 주지 않으며 도구의 자유도를 제한한다. 이번 최악 source/destination은 이미 가깝다. 고정 좌표·좁은 Logic Lock부터 적용하지 않는다. |
| [Cyclone IV Memory Blocks, 3–7](https://cdrdv2-public.intel.com/653974/cyclone4-handbook.pdf) | M9K는 입력이 동기식인 메모리다. OAM을 RAM 선언으로 바꾸기만 해서는 기존 비동기 읽기를 보존할 수 없다. CPU 주소 변경·PPU CE·행 복사·동일 주소 충돌의 소비 시점을 먼저 설계한다. 외부 세이브 SRAM은 사용하지 않는다. |

온라인 Standard 안내의 버전 표기는18.1이며 실행기는25.1이다. 문서의 원리와 설치판에서 실제 실행된 명령을 구분한다. 일부 과거 Intel PDF 주소는404/403으로 열리지 않아 검색 색인과 접근 가능한 공식 HTML을 구분해 사용했다. Pro 자동 register-tree/report-spread/Hyper-Retiming 기능을 실행했다고 주장하지 않는다.

## 현재 실패는 단순히 두 레지스터가 멀어서가 아니다

현재 cdc181/map02는15,072LE,963/963LAB,38/56M9K다. 평균 interconnect는 total/H/V=68.8/67.8/70.2%, peak는86.2/87.2/91.2%다. 이는 전체/방향별 집계이며 특정 좌표의 혼잡 지도를 측정한 것은 아니다.

`control.shift[0]`은 `FF_X22_Y27_N9`, `control.offset[9]`는 `FF_X21_Y26_N29`다. 좌표상 가까운데 배선은 X6..23/Y17..28을 거쳐 돌아간다. 데이터 지연9.254ns 중8.526ns(92%)가26개 routing element에서 생겼고 LUT 단계는0이다. 좌표 거리는 칩 실제 길이(mm)가 아니며 이 우회만으로 특정 회로가 원인이라고 단정하지 않는다.

주변 조회에서 shift의 다른 setup 경로44개는 통과했고, offset의 다른 입력10개와 출력5개도 통과했다. source의 직접 fan-out은15이며 queried timing 경로45개와 다른 수다. 따라서 높은 fan-out 숫자만 보고 shift를 복제하거나 계산식을 고치는 것을 우선하지 않는다. 평균 혼잡·남은 클록 교차 보정·공유 제어 연결을 함께 다룬다.

다른 실패 `boot.check_failed → sink.endpoint.ack_work[31]`는 같은 PLL의 memory→host 경로이며 −0.740ns,4 LUT·배선71%다. ACK 레지스터로 들어오는 enable 경로다. host 쪽에 활성 상태를 등록하는 변경을 검토할 때 **STOP/오류 시 즉시 버스 비활성화, 패킷 취소, 이전 ACK 무효화**를 함께 보존해야 한다. 같은 PLL이므로 비동기 예외로 덮지 않는다.

새 주변 보고서는 root가 다른 raw reset/수명주기 연결도 포함하므로 −8.389ns 같은 값이 나온다. 이는 해당 CDC 계약이 미완료인 별도 범위다. 이를 기존 실제 관련 클록의 −3.379ns와 섞어 개선/악화라고 비교하지 않는다. setup/hold만 수집한 한 corner의 상위50개씩이며 전체 경로나 리셋 안전성 증명이 아니다.

최대 non-global fan-out703의 보고 이름은 APU 내부 `EnvNoi|env_count~0`다. 합성된 공유 노드 이름만으로 오디오 오류 원인이나 제거 대상으로 판단하지 않는다. 즉시 복제를 선택하지 않았으며 fan-in과 소비자별 물리 위치를 확인할 경우에만 별도 후보로 삼는다.

## 반영한 구조: ROM 응답을 수신 클록에서 한 번 받는다

기존 `nes_rom_physical.sv`는 memory 클록의 `data_hold`를 그대로 `rom_data`에 연결한다. arbiter도 이를 그대로 core/fill로 배포하고, ROM service는 응답 시 cache 저장뿐 아니라 CPU/PPU 데이터 bypass에도 쓴다. 그래서8비트가 실제 CDC timing cone에서는1,257개의 source/destination·clock 조합으로 퍼진다. 물리 wire가1,257개라는 뜻은 아니다.

새 `nes_reply181.py` 후보는 NES 클록의8비트 `reply_data` 레지스터를 추가한다. 이 레지스터는 매 클록 held byte를 샘플링하고 **기존 `rom_response`가 참일 때만** 소비자에게 유효하다. ACK의 두 번째 동기화 FF와 데이터 레지스터가 같은 NES edge에서 갱신된다. 응답 이후에 데이터를 받으면 한 클록 늦으므로 그렇게 구현하지 않는다.

설계 의도는 memory→NES의 넓은 조합 fan-out을 명시적인8비트 캡처 경계에서 끝내고 그 뒤를 NES 클록 내부 배선으로 바꾸는 것이다. 단순한 숫자 maxfan 변경이나 응답을 한 클록 늦추는 pipeline과 구분한다. **8비트 경계로 합성됐는지, fan-out·혼잡·slack이 실제로 좋아졌는지는 아직 측정하지 않았다.**

- `rom_ready`, `rom_response`, 주소, request/ACK, PSRAM 핀과 READ16·HOLD·RELEASE 시점, CHECK 경로는 변경하지 않는다.
- 유효하지 않은 때의 `rom_data`는 기존과 달라질 수 있다. CPU/PPU/fill이 반드시 응답으로 한정해서 소비하는지 실제 결합 시험이 필요하다.
- capture 이전 데이터 안정 시간을 별도 max-delay로 검증해야 한다. 비동기 첫 샘플을 항상 신뢰하는 것이 아니며 ACK stage2로 자격을 부여한다. RESET/STOP과 새 요청이 겹칠 때 이전 byte가 새 태그로 게시되지 않아야 한다.
- 현재 후보의 디지털 시험 지연은9.904ns다. 이후 routed 경계도 이보다 짧게 확인한다. 전역 false-path나 MTBF 검증 대체로 사용하지 않는다.

reader 기존 상태·핀·응답 시점 비교는 READ_CYCLES1/2/3과16의16개 위상(0..5.625ns,0.375ns 간격)을 합쳐19경우다. exact와9.904ns 지연 각각48,241관측,456읽기,714중단/리셋,클록정지 리셋19경우가 통과했다. 응답에 보이는 추가 클록은0이다.136.362ns로 늦춘 데이터와 응답이 난 다음에야 캡처하는 대조군은 유효 데이터 불일치로 실패했다.

PSRAM 입력은 고정 두 byte와 주소 lane 변화 모델이다. 실제70ns IO, arbitrary bytes 전체 상태공간, metastability, arbiter7edge 한도, CPU/PPU 전체 게임 소비는 새 후보로 아직 승인하지 않았다. 기존 물리 reader 증거를 새 캡처 경계의 실제 배선 승인으로 대체하지 않는다. 초기 줄바꿈 준비 오류, 지연 wire 선언 순서 및 timeunit 누락 실패도 보존하며 test04만 선택한다.

## 자원 구조와 다음 작업 순서

1. **reply02/test04를 실제 arbiter→ROM service→CPU/PPU/fill에 결합**한다. 같은 ACK edge, 동시 다음 요청, fill abort/drain, STOP/reset, 주소 태그와7edge 한도를 검증한다. 새 capture 경계의 제한된 CDC 제약을 만들고 이전 예외의 적용 개수를 다시 감사한다. 기존1,257개 조합 경로를 무조건 제외하는 방향으로 가지 않는다.
2. 관련 PLL의 RUN/STOP 활성 상태와 ACK 쓰기 enable을 소비자 근처에서 처리하도록 설계한다. 비활성화·버스 충돌 보호를 늦추지 않는다. 실측된 혼잡과 control fan-in/out을 보고 필요한 부분만 복제/등록한다. 검증되지 않은1클록 지연을 삽입하지 않는다.
3. 배선 여유가 계속 부족하면 **OAM의 저장·읽기 포트 구조**를 다음 큰 대상으로 삼는다. 현재 OAMEval은4,315LE/1,942register이며M9K는0이다. 칩에 남은M9K18개는 가능성의 근거이지 그대로 옮길 수 있다는 보장이 아니다. 사전 읽기·CPU 즉시 주소·행복사·native snapshot·save-state 동시 접근의 시간표를 먼저 만든다. 이전 onehot-read/row-writer/enable-OFF의 실패 시도는 반복하지 않는다.
4. 새 구조가 경계 기능을 통과한 뒤 정당화된 한 번의 FIT로 전체 실제 setup/hold와 배선 평균·국소 최대·자원·IO/reset을 비교한다. 의미 있는 배선 감소 없이 실패 경로만 이동하면 성공으로 처리하지 않는다. 기존 AREA/MAXIMUM router 설정을 새 해법처럼 반복하지 않는다. LAB가 이미 가득 찬 상태에서 sparse packing·전역 복제를 무작정 켜지 않는다.
5. 전체 timing/조건부 IO 통과 뒤 기존 paired ARM/client를 재사용해 SMB3 숫자1→A 실기로 간다. 화면 동결 해결과60fps는 별도 목표다. 이 후보가 SPI payload/여러 vblank 전송 병목까지 해결한 것은 아니다.

보드핀·클록속도·세이브 SRAM·GBC·164복원본·180배포본은 보존한다. 현재 추가된 것은 연구에 근거한 캡처 후보와 경계 검증이며, 새 실기 설치 파일은 없다.
