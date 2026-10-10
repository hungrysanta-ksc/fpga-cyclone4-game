# NES 현재 인계 — 146 결과 수집 완료, 실제 SMB3 실행으로 전환

[146 실기 결과](../../analysis/SCREEN146-HARDWARE-RESULT.ko.md)

## 다음 작업의 우선순위

사용자가 빠른 A/B 혼합의 추가 판정을 생략하고 실제 Super Mario Bros. 3 (J)의 이동·스크롤·프레임 끊김을 확인하도록 지시했다. 146은 적재·대조·RUN·STOP·표시 존재·실제 메뉴 복귀 PASS, 빠른 전체 화면 정합성 INCONCLUSIVE다. CRT의 빠른 교대 관찰만으로 오류라 단정하지 않는다. 146 영상/로그 재수집이나 같은044 복원 시험을 요구하지 않는다.

기존 MMC3를 재사용하되 목표 ROM의 PRG256KiB/CHR128KiB에 맞춰 주소·캐시·적재·대조 범위를 확장해야 한다. 현재 작은 진단 ROM과 배경 전용 화면 경로만으로 게임이 지원되는 것은 아니다. 기존 146 결과는 PR90에 기록하고, 실제 게임 구현·검증은 별도 브랜치와 새 PR로 분리한다.

다음 출구는 (1) 실제 목표 ROM 코어의 첫 유효 게임 화면, (2) 384KiB MCU 적재·대조와게임용 SNES 출력·패드 연결, (3) 변경된 경계의 최소 검증·배치 후 유한 실기 패키지다. 마리오 이동·스크롤을 주 검증 장면으로 삼되, 원래 게임의 느려짐과 구현 오류를 구분한다. 전체 게임·오디오·다른 맵퍼 호환성은 아직 미완료다. 화면 전달을 위해 코어 시간을 몰래 느리게 하거나 deadline 오류를 숨기지 않는다.

## 보존할 기준

## 구현과 검증 범위

실제65816/PPU/DMA 모형 정상·혼합·늦음 각30패킷/60,240바이트와395개RGB 통과. 정상 전송18,390~18,406 master clocks,첫225→238줄/이후240→253줄로 같은 블랭크 안에서 켠다. 늦음은13번째 블랭크 판독값0을 주입해 다음 블랭크 대기를 확인한 분기 시험이며 물리 지연 증거는 아니다. 해당 분기를 우회한 테스트전용ROM은 완전30패킷 실행 후대기 조건에서 거부됐다. 길이/헤더오류2/7도 차단했다.

MCU는145에서 이름146만 변경,호스트21사례·ARM186792/NMI15store0call3DSB2ISB·소스일치 통과. 같은142/145 RTL·배치·QSF·SDC·타이밍 보고서를 유지하고 ROM/MIF24576바이트 및ASM만 갱신했다. 실제65536주소대응 통과. 전체코어/새MAPFITSTA는 반복하지 않았다. 기존144NES ROM/CRC·전량 대조·보호·RUN중SD쓰기금지·STOP/base/menu는 그대로다.

선택client01/normal02/mixed01/late01/negative02/bad_length01/bad_header01/host01/arm01/armcheck01/rom01/asm01/bus01/reference01/release01. 첫normal01의225줄검사 실패와negative01의테스트ROM누락은 별도 보존하며 실제RTL/펌웨어 실패로 분류하지 않는다. frozen1464701파일 manifest b533b53f59b667181acd8c243b013fce5dc29a7284df978bae3d4bcd6a42f967. completed freezer나기존archive를 다시 실행·수정하지 않는다.

## 공통 보존

보드는 FXPAK Pro Mk.III Rev.D/2022-05-02, STM32F401RCT6, EP4CE15F17C8N, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 기존 FLOAT wrapper1seat를 재사용하고 새 유료 라이선스/부품/PC연결을 다시 요구하지 않는다. GBC152·원래NES334·모든 과거 public pin 유지. 전체IO/MTBF, ACK16ns 실패, E1/E2·8µs·양 클록 정지CE9µs·source-lock4·124격리 유지. 공개에는ROM/바이너리/사용자영상/라이선스/개인경로 금지. PR한국어4절과 사용자머지 원칙.
새 PR은 사용자가 머지한다. 다음 작업 전에 실제 PR/master와 인계 상태를 갱신한다.
