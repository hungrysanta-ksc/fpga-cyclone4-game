# NES203 CHR 중복 수신 제거

PR117 같은 branch의 보드 연결 후보다. 배포186, GBC164, 세이브 SRAM은 유지한다. 전체 ARM 링크까지 확인했지만 actual loader epoch/board mux/192 source 연결과 FIT가 남아 있어 **설치 가능한 짝펌웨어가 아니다.** 새 실기 ZIP은 없다.

## 작업 의미

202는 MCU에서 SNES로 보내던 BG/OBJ 픽셀 업로드를 직접 타일 계획으로 바꿨지만, FPGA가 CHR를 읽어 MCU에 보내는 old fill은 남겨 두었다.203은 exporter와 receiver를 함께2031 형식으로 바꿔 이 중복을 제거한다. exporter에는 fill/CHR byte 포트와 상태가 없고, 실제 수집기 결합 시험에서도 fill 인스턴스 및 query 중재 mux를 제거했다.

MCU에는 타일 픽셀 대신 필요한 물리 tag와 BG/OBJ 용도만 보관한다.512개 타일의16B 픽셀, 총8192B가 사라진다. 단순히 데이터 검사를 생략하는 방식이 아니다. geometry 전체를 검사해 참조되는 tag/kind 목록을 직접 만들고, 실제 픽셀의 유효성은201 표시 lease와192 immutable CHR-ROM epoch 계약으로 분리한다. **이 후자의 actual board 배선이 아직 남아 있으므로 지금 배포하면 안 된다.**

이 변경은60fps를 위한 불필요한 원본 읽기·전송·저장 제거다.60fps 실측 달성으로 해석하지 않는다. 현재 고유 표시 간격 측정은 없고 `collected_runs=[]`다. 이전199의 합성17.944ms도 전체16.67ms 예산을 넘는다.

## 새 입력 계약

- BEGIN version2031만 받는다. 이전1813와 혼용하면 거부한다. D0/D1/D2/D3의 CRC·token·PREPARED/COMMIT은 유지한다.
- map/object/low-plane exception에서13bit 물리 tag와2bit 용도 bitmap을 만든다. 기존 geometry 순서·개수·비트 범위 및 raw slot 연속성 검사를 유지한다.
- control7/index4는 이제 **META_END**다. 이 시점까지 논리 record 수가 일치하고 byte count가0이며 모든 geometry가 완료되어야 한다.512개 이내의 고유 요구를 오름차순 tag/kind 목록으로 만들고 개수가 일치해야 raw scratch 전환을 허용한다.
- META_END 이전의 kind6 CHR byte는 허용하지 않는다. 이후에는 기존 packed color6 raw 경로만 사용한다. 누락된 geometry, 이른 raw, 중복 META_END, generation/byte count 오류는 tentative frame을 실패시킨다.
- END→호스트 PREPARED→exporter COMMIT만 receiver 자료를 공개한다. 최종 SNES 표시 ACK→200/201 retire→receiver consumed 순서는202와 같다. source 오류·불확실한 완료에서 자동 재시도하지 않는다.
-191 planner의 주소 존재/용도 검사는 `tile.data` 포인터 대신 metadata 항목을 조회한다. 계획·slot·low-plane/OBJ mask·raw 알고리즘은 그대로다. 픽셀을 가정하거나0으로 대체하지 않는다.

`nes_metadata203.py`는 선택202 후보를 기반으로 paired exporter/C를 생성하고 source pins를 남긴다. 이전 픽셀 converter API는 후보에서 명시적 실패로 막으며 전체 링크에서 실제 호출은 없다. RUN은191 planner만 사용한다. 참고186 converter는 시험에서 별도 타입으로 유지해 pixel oracle로만 쓴다. 기존 공개186/202 소스와 완료된 archive는 수정하지 않는다.

## 검증

선택 `test04/capture02/arm01/check01/evidence01`.

`test04`: 실제203 exporter RTL이 만든96bit record를 저장하고, 그대로 실제 C receiver/RUN/planner/service/sink/window에 재생했다. RTL query memory와 ACK, C 하드웨어 SPI·타일 생성·최종 표시 ACK는 fixture다. **동시 board/C/65816 cosimulation이나 게임CPU 실행은 아니다.**

- 9연속 장면에서 BG/OBJ/low-plane 예외/raw1·7행/normal 복귀와 generation wrap을 확인했다.100개 출력 타일 및 전체 video metadata가 원래186 converter와 일치한다.
- 512개 고유 tag 허용/513개 거부를 포함한9개 수신 경계,6개 기존 RUN 오류 경로가 통과했다. receiver는 실패 상태의 raw 포인터를 공개하지 않는다.
- exporter11장면 COMMIT, 조회 실패·lease 무효·호스트 거부3경로, backpressure3136cycle을 확인했다. old CHR record는0개다. fixture 호출 수4152회는202의 비압축 fixture와 직접 속도 비교하지 않는다.
- host ABI의 receiver9880B, tile4B를 확인했다. 원래 같은 ABI receiver보다8192B 작다.

`capture02`: 선택된 실제 수집기201→203 exporter→표시 lease/200 SPI/201 batch/193 bulk를 연결했다. 이전 fill과 mux가 없고 geometry는 수집기에 직접 질의한다.3회 export, packed raw512값, 이전 표시 중 다음224행 캡처 및33개 geometry 조회, reader drain까지 retire 보류, 거부 후 복구와 epoch 변경 실패를 확인한다. bulk의 데이터는 zero tile3개이며 **실제 BG/OBJ source192·전체 보드 mux 증거는 아니다.**

`arm01/check01`: 실제 전체 ARM 후보 링크203648B, SHA256 `5b65b786b4e491ed3f0283833c8c3d31b2b1b64bca3cff8288c2fa9341c0491f`.

| 항목 |202 선택|203 선택|
|---|---:|---:|
|static RAM|26872B|26872B|
|RUN foreground 상한|36976B|28784B|
|IRQ reserve|508B|508B|
|남은 여유|1068B|9260B|
|최소 기준|1024B|1024B|

8192B는 RUN용 caller-owned workspace 감소다. static RAM이나 세이브 SRAM을 늘리지 않았다.116개 도달 함수/간접 callback과 기존13개 library/platform body를 검사했다. 실제 high-water, 전체 메뉴/GBC call graph, 새 FPGA FIT/IO/CDC 승인과 같지 않다.

실패 기록: test01 생성 C의 줄바꿈/Windows printf 형식, test02 printf 형식, capture01 SystemVerilog wire 선언 오류를 보존했다. test03은 정상 중간 결과이나 결과JSON의 host receiver 크기 상수가 잘못되어 선택하지 않았다. test04는 실행 출력에서 크기를 읽고 exporter 오류 경로도 포함한다. 완료된 기록은 고치지 않는다.

## 다음 작업

1. actual loader content epoch/ROM ready/write →201 capture/표시 lease →192 source를 실제 보드에 연결한다. **exported captured_generation/epoch**를 사용하고 다음 수집기의 generation을 쓰지 않는다. CHR-RAM은 immutable처럼 허용하지 않는다.
2.203 exporter를 실제 board top에서 old fill/arbiter와 교체하고 source192가 코어 우선 물리 reader를 소유하게 한다. host SPI/descriptor/consume mux와 SNES ROM195를 연결한다. 남은 old fill을 성능판에 두지 않는다.
3. 실제 BG/OBJ를 포함하는 최소 board→C RUN→SNES 결합, 변경된 전체 ARM/FPGA FIT·IO·메모리 예산을 확인한 뒤 짝패키지를 만든다. 동일 boot/독립 codec/seed FIT를 반복하지 않는다.
4. SMB3 숫자1+A→첫 레벨 확인→RIGHT+B 유지/A press-release 연속스크롤에서 전체16.67ms와 고유 표시 간격을 측정한다. 프레임마다 SD 로그를 쓰지 않는다.

persistent delta는 base generation/bank/slot/content epoch/row-alt-mask/CHR-RAM write를 함께 다뤄야 한다. 확보한8KB는 전체 화면 버퍼나 MMC4/5 지원 승인으로 간주하지 않는다. AV약60fps→장기 플레이·오류/reset 로그→입력 유지 품질 순서를 유지한다.
