# NES206 로컬 취소 경계와 전체 보드 타이밍 통과

## 작업 의미

205의 중복 타일 저장 제거를 유지하면서 새 직접 전송 경로의 raw reset/fault 데이터 우회를 없앤다. 관련 클록 타이밍은 통과했지만 ROM epoch reset 해제 검증이 남아 있어 설치 가능한 FPGA/ARM 짝은 아니다. 기존186/GBC164/세이브 SRAM을 유지한다. 실기60fps 측정이나 새 ARM/ASM/ZIP은 없다.

## 변경과 수명 계약

`nes_board206.py`는 고정된205 source에서 네 모듈을206 이름으로 생성한다. 원래165/193/201/204 모듈은 수정하지 않는다. 이전 geometry/ACK mailbox165는 전체 보드에서 계속 사용하므로 QSF에165와206을 함께 둔다.

- direct206: host/NES base reset과 취소 release를 따로 만든다. endpoint·SNES control·NES source와 버스 출력 허용은 해당 영역의 상태만 사용한다. sticky hf/nf는 base reset에서만 지운다. SPI의 source_fault는 startup hold를 포함하지 않는 host hf를 사용해 부팅 직후 오류로 오인하지 않는다.
- batch206/bulk206: 공통 reset과 내부 sticky fault는 각 영역의 cancel release 입력에서 끝난다. host와 NES 데이터 조건에 raw cancel을 다시 AND하지 않는다. 취소 release가 자신의 원인인 fault 레지스터를 지우지 않도록 base reset과 분리한다.
- mailbox206: raw reset은 reset release 플롭에만 연결한다. src_ready/dst_valid는 로컬 release 및 peer-up 상태로 결정한다. 독립 endpoint reset은 여전히 지원하지 않으며 common reset/held payload/ACK 수명은 유지한다.
- loader: count_complete가 별도의 우선순위 mux를 만들지 않고 기존 loaded_bytes의 count_update/count_clear 조건을 공유한다. terminal 비교값/동작 edge/START·END·STOP·fault 우선순위를 바꾸지 않는다. 타이밍 제약·clock·seed 변경은 없다.

205의 부분 byte stream→193 계열 unpublished RAM 계약은 그대로다. 마지막 byte 전에는 mailbox를 공개하지 않고, 부분 오류가 나면 소유권을 버린다. frame SEAL/display ACK/retire와 chunk consume은 서로 다른 단계다.

## 기능 검사

SELECT source03/test01/cancel01/mapfit01/timing01/io02. test01은 source02를 실행했다. source03은 QSF에 기존165 mailbox 정의를 보존한 수정뿐이며 모든RTL은 source02와 byte 동일함을 확인한다.

- 실제 SPI2.625MHz/192 READ16/206 bulk/194 consume 경로3장면×3프레임1968B exact186.205와381183/384357/740051사이클 및290/316/508 core read가 같다.
- 실제205 stream+206 bulk에서 부분 오류/전송 대기·복구22검사 통과.
- cancel01: 부분7byte/완성16byte 상태, reset/STOP/source_fault, NES/host/양쪽 clock 정지 조합18검사. 실제 잘못된 타일 index와 CRC로 두 내부 sticky fault를 만들고 재개1검사까지 총21검사 통과. 취소 후 예전 RAM/plan/descriptor가 다시 공개되지 않는다.
- loader: 전체16상태/명령·우선순위294912개, 실제 BEGIN/쓰기 phase 중8종 action1056개, 모든19bit old count524288개 비교 통과. 잘못된 terminal 값 후보는 검사가 거부한다. 전체 ROM 업로드/게임 구동 시험은 아니다.

CPU request/PSRAM/계획/lease/최종 ACK는 fixture다. 실제 NES CPU+ARM+65816 동시 결합, 실기 입력·사운드·FPS 증거로 세지 않는다.

## 전체 배치와 타이밍

전체 MAP/FIT 한 번,15179LE/8360FF/959LAB/47M9K.205 대비3LE/2LAB 감소,23FF 증가. 여유229LE/4LAB/9M9K이며 mapper 확장 예산이 충분하다는 뜻은 아니다. 로컬 release를 추가한 비용을 포함한다.

동일DB3corner 관련클록 최저 setup **+0.293ns**, 더 엄격한 기존 implementation 제약 **+0.193ns**, hold **+0.121ns**. 이전 loaded_bytes→count_complete는−0.739→+0.641ns. 현재 최저 nominal은 load_end→phase[0]이다. 기존 loader state* 이름 미일치 경고는 남아 있고 이를 수정하거나 예외로 덮지 않았다. 이 수치는 관련 클록 setup/hold 통과이며 모든 비동기/IO signoff를 뜻하지 않는다.

3corner cross-clock 목록4968행, 첫 단계45개의 대응 단일 fanout 확인.205에서 기본corner8455행이었던 새 취소/기타 데이터 경로 분류는206에서0행이다. 남은 새 데이터 경로는 control/Gray 첫 단계와 held→received payload로 분류된다. 경로행 수 감소를독립 버그 수나 속도 증가량으로 해석하지 않는다. 새 timing exception은 추가하지 않았다.

held payload 최대6.598ns, Gray 최대6.693ns. mailbox는 request를2단 동기화한 뒤 capture 상태를 거쳐 받으며 ACK 반환 전 held가 유지된다. 이 측정만으로 reset/메타안정성/전체 protocol 승인을 대체하지 않는다. 특히 source_epoch205의 epoch_meta/epoch_sync/previous **96레지스터에288개 negative recovery 경로행(3corner)**이 남는다. memory-domain cold reset을 직접 해제하는 기존 연결을 NES 로컬 release로 끝내야 한다. 단순히 false_path를 추가해서 없애지 않는다.

같은 DB의 측정 전용 IO 복사본에서 기존 조건부 계산 통과: PSRAM70ns/PCB 왕복4ns 가정 여유+3.221ns, SNES read envelope86.231ns<270ns, SPI reply166.008ns<190.476ns. 기존 native payload reset 검사도 통과했다. 해당 측정의1000ns overlay slack은 합격 기준이 아니며 실제 PCB/전기·MTBF signoff는 아니다. 생산 board.sdc/cdc181.sdc는 byte 동일하다.

source01은 하위rtl 디렉터리 생성 누락으로 준비 실패, source02는 독립 시험에 성공했지만 QSF에서 기존165 mailbox도 필요함을 확인해 source03을 선택했다. io01은 inherited CDC 예외가 records_req를 숨겨 측정기에서 실패했다. io02는 측정용 nominal view에서 해당 예외 파일을 제외해 raw 지연을 추출했으며 실제 제약은 변경하지 않았다. 처음 sandbox 내 FLOAT 시작은 시뮬레이션에 진입하지 못했고 승인된 래퍼의 host 실행으로 test01을 수행했다. 원본 증거/기존21개 archive를 보존한다.

## 다음 작업

통과한206 구조를 유지하고 loader나 seed를 다시 미세 조정하지 않는다. ROM epoch96개 레지스터의 cold-reset 로컬 release를 수정하고, 정지 clock 중 무효화·Gray 안정화 후 admission·새 epoch 수명을 최소 검사로 확인한다. reset release/held-data bounds를 정확히 기록한 뒤 실제 board→C→SNES 짝을 검증한다. 준비가 끝나면 SMB3 숫자1+A→RIGHT+B 유지/A press-release 연속스크롤에서16.67ms 목표를 측정한다. 같은 boot/codec 시험 반복이나 오프닝 FPS 대체는 하지 않는다. MMC4/5·CHR-RAM·delta와 AV60fps→장기play/오류·reset로그→입력 유지 순서를 유지한다.
