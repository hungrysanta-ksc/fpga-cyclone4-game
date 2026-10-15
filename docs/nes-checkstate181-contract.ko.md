# NES181 — CHECK 상태 갱신 분리와 첫 실기 패키지

부분 행 영상181의 전체 보드가 기능 검사·배치·타이밍·조건부 IO 기준을 통과해 **NES181-SMB3-ROW-VIDEO.zip**을 만들었다. 첫 레벨 화면 복구와 실제60fps는 실기 확인 전이다. [설치·시험 안내](nes-game181-ready.ko.md).

## 변경 계약

이전 OAMPORTS 후보의69개 입력 중 `nes_rom_spi.sv`만 변경했다. OAM32bit RAM, packed1813 ingress,1815 SNES ROM, 클럭·핀·SDC·CPU/PPU 속도는 동일하다.

CHECK 상태 갱신이 `checked_data`의 쓰기 허용 조건 아래 중첩돼 있던 구조를 분리했다. `check_enable/busy/done/verified`의 다음 값을 병렬로 계산하고 같은 edge의 live 오류로 승인 여부를 결정한다. 오류 종류와 우선순위는 hard9→응답7→SS겹침1→명령 오류 순서다.

- C0 원시 자격→C1 원인→C2 명령 판정→C3 승인→C4 카운터 반영을 유지한다. 새 파이프라인 지연을 추가하지 않았다.
- 응답 주소는 그 응답이 발생한 edge에서 요청 tag와 비교한다. 이전 edge의 주소가 유효했다고 가정하지 않는다.
- live 오류는 해당 edge의 RUN·READ·STOP 펄스와 카운터 승인을 차단한다. 이미C3에 승인된 카운터 효과의C4 기록과 비동기reset 취소 계약도 그대로다.
- 정상 응답과 잘못된 명령이 겹치면 응답 데이터는 저장하되 오류를 기록하고 상태는 해제한다. 원래 코드의 순서를 보존한다.
- CHECK_END는 verified를 설정하고 enable을 해제하지만 done을 별도로 지우지 않는다. 응답과 명령이 같은 edge에 겹치는 조건도 기존과 같다.
- SPI ID0x74·2.625MHz·최소2µs SS high·트랜잭션별 coherent snapshot은 그대로다.

## 검증

|항목|결과|
|---|---|
|같은edge 상태 대조|1,048,576개 조합 +1,024개8edge 시퀀스, 총1,056,768edge 일치|
|실제 SPI/boot/READ16 연결|219프레임/14,016응답비트/1,126,009관찰edge;100읽기·7ACK·19주소손상·72취소·2오류겹침 통과|
|오류 회로 검출|오류 시verified 유지, 명령 오류가 정상 응답 저장을 막음, CHECK_END가done을 지움:3종 모두 mismatch 검출|
|전체 FIT|13,281LE /923LAB /42M9K /6,504FF|
|전체 nominal setup /hold|**+0.373ns /+0.153ns**|
|강화 개발 예산 setup|**+0.221ns**|
|관련PLL 최저setup|+1.284ns|
|기존 CHECK 대상 경로|최저+0.673ns; 이전−0.240ns|
|OAM 검사|3corner/2,220경로의setup·hold 통과|
|기존 CDC /reply|486행 /24행 통과|
|조건부 IO|PSRAM70ns여유+4.508ns;SNES70.026/270ns;SPI161.472/190.476ns|
|native payload 음수recovery/removal|0개|
|전체 ARM 재사용|200,412B/static26,564B/foreground36,968B/IRQ508B/여유1,384B|
|이번 실제 로그 formatter|최대필드·16버튼·16사건에서3,921/4,096B|
|배포 묶음|ARM1,413입력·보드69입력 해시 확인, SNES1815 재생성 동일, ASM/CPF·압축복호화·ZIP manifest 통과|

전체 FIT는 한 번 실행했다. 원본 FIT DB는 보존하고 별도 사본에서 STA·ASM을 실행했다. CHECK 대상 최악 경로는 여전히6logic levels지만 데이터 지연이6.111→5.204ns로 줄었으며, 전체 최악 경로는START→loader.loaded_bytes로 바뀌었다. LUT 수 감소나 clock 완화로 통과했다고 주장하지 않는다. M9K14개·LAB40개가 남는다.

모든 상태 조합 시험은 주입 가능한 비정상 내부 상태도 포함한 RTL 등가 검사이며 formal 증명은 아니다. 실제 SPI 시험은 loader READY·카운터를 시드한 제한된70ns 메모리 모델로, 전체 ROM 쓰기·SMB3 부팅 시험이 아니다. 미연결 출력 경고는 hierarchy로 직접 비교한 시험bench 출력에 한정된다.

기존 OAM의 제조사 RAM 모델·실제CPU/PPU/MMC3 자체ROM 렌더링 비교와 paired ARM/C→실제65816 검증은 바이트 확인으로 재사용했다. 새 게임 검증으로 세지 않는다. OAM 기준에도 있던8개 unknown색, 이상적인 메모리, 일반 extra/state 포트의 현재보드 pruning 한계는 유지한다. 조건부IO는70ns 부품·디지털 버스 모델과 배선 여유 가정이며 전체asyncreset/CDC/MTBF/전기적IO 승인이 아니다. postfit SDF·실기 테스트도 아니다.

첫 시험 실행은 샌드박스의 임시 디렉터리가 프로세스 간 유지되지 않아 소스를 찾지 못했다. 고정 절대경로의test02가 실제 통과본이다. report01은GCC 실행의Windows DLL 오류623으로 중단됐고 동일 코드의host report02가 통과했다. 실패 기록을 지우거나 제품 오류로 해석하지 않았다.

## 패키지와 다음 판단

선택: checkstate181 map01/test02/route01/check01/report02/asm01/release01. 기존 paired181 arm02/check03와 SNES1815를 사용한다.

- ZIP SHA-256: `274489a0106c2a82457e8a157883f60e545f0691737ad1a1452139b0b9e27f71`
- firmware: `cf16e9c124a20ab0e25e9f0d0646d8dfd33f706300b8df600318e3020bcc5d1c`
- FPGA: `6cb2235de30a12f8dbae084beb56c3d1f58efb14ed7039ef6a298b39504c5d50`

다음은 **SMB3 숫자1타일→A 실기 시험**이다. 첫 레벨 영상 지속·음성·메뉴 복귀와 두TXT를 받는다. 가능한 경우20~30초 영상으로 끊김도 본다. 실패 시 수집거부→BEGIN/ABORT/COMMIT→SNES ACK 순서로 기존 로그와 관찰을 연결한다. 화면만 멈추고 소리·조작이 계속되는 경우 게임 전체실패로 단정하지 않는다.

성공 시 무변경FIT·장시간 모델 부팅·180/044 복원 반복 대신 실제 표시 간격과 전송비용을 개선한다. raw7 egress 최소22.154ms 모델과 단일capturelease는 아직60fps를 막을 수 있는 별도 병목이다.60fps를 core 감속·frameskip으로 대체하지 않는다. AV품질→장기플레이/오류·리셋로그→입력유지 순서를 유지한다. MMC4/5·강제save/load·mute의 추가 배선/자원 검토는 별도 계획으로 남는다.

**작업 의미:** 첫 레벨 복구용 부분 행 영상 경로를 FPGA에 넣고 안전한 명령 처리 속도를 확보해, 오랫동안 미뤄졌던 통합 실기 시험이 가능한 상태로 만든 작업이다. ROM CHECK 변경 자체가 표시 FPS를 올리는 것은 아니며, 앞선 영상·압축·OAM 구현을 실제 보드에서 시험할 수 있게 한다.180 패키지/GBC164/세이브 SRAM/완료archive는 보존했다.
