# NES091: 클록 실기 패키지와 첫 게임 목표

## 작업 목표

PR41 병합과 master `3f83e0f104160d0347810a0226264bd0527f3a9b` 도달을 확인했다.090에서 남긴 실제 GPIO/SPI/RESET 전환 경계를 점검하고, 고정090 펌웨어와 정상044 복원본을 묶은 report-only 실기 패키지를 만든다. 사용자 지정 첫 ROM을 기록한다.

## 작업 내용

091는090의 실제 STM32 설정 함수·매크로를 레지스터 모델에 연결해 구성/관측/mini 복귀94검사와 전환 누락 대조3개를 통과했다. 생산 펌웨어는090 그대로이며 정상044 복원본을 포함한 클록 관측 trial/source ZIP을 완성했다. 다음은 사용자 HW090 TXT/화면 회수다. SMB3(J), mapper4·PRG256KiB/CHR128KiB를 첫 게임 목표로 등록했다.

PB3/4/5의 GPIO↔AF5 전환·SPI CR1 복원, PB8 DATA0 출력→MCU_RDY 입력, PB9 구성 클록·PA1 PROG·PA4 CS·PA15 DONE·PB7 INIT 상태를 검사했다. 실제 spi_init/fpga helper body와 핀/방향/속도/전송 매크로를 고정090 소스에서 가져왔다. 매 성공 세션에서 mini 두 번+CF87 구성의 상승/하강각6543555에지를 검사한다. 출력817944바이트×8비트+CF87 추가3클록이다.

## 작업 결과

**전환의 코드·레지스터 모델 검증과 첫 실기 관측 패키지 목표를 달성했다.** 실기 기준 클록 가용성과 SMB3 실행은 미완료다. 최종 pins04의94검사 및 AF복원/SPI복원/DATA0입력 제거3대조가 통과했다. 출력·RESET 소유권을 검사하지만 실제 전압/파형·절대 주파수 승인이나 SRAM bit-level SPI replay는 아니다. SRAM 완료의 CS HIGH는 원본 FPGA_DESELECT 계약에 따른 모델이다.

첫 include 순서 컴파일 오류, 초기 속도값3 모델, 최종 원본속도2 교정 및 인과01/02 로그를 보존했다. 생산 소스는 그대로이고 기존090 ARM 링크/전체SD 세션·084 실기 저장/복원/menu/GBC 근거를 재사용했다. 새 ARM/RTL/ASM/fit/STA/Questa를 실행하지 않았다.

| 산출물 | 길이 | SHA-256 |
| --- | ---: | --- |
| TRIAL ZIP | 190417 | 99bfc70a2fd468945d163d4388db4f5d65d1f440d98fd6a3c6684faf285c24e2 |
| SOURCE ZIP | 8632240 | cb489b75660a50081f2e5fd24c8d9a38608d33b7d076b70d0a1507a61c84e695 |
| 시험090 firmware |196248|00f757fcd1ca0da08ce0e5564358e06b482071e6119d8827e6c81748fcfddebe|
| 정상044 복원 firmware |169056|1c3b40a3459d24114cb4d91ee9d861d1a08025a670ef25317ef489092203693b|

ZIP 전체 멤버를 다시 읽고 대응 소스·라이선스를 동봉했다. SD 자동 설치는 하지 않았다. [실행 안내](../docs/CLOCKREPORT090-RUN.ko.md)에 복사할 한 파일, 자동 진단,90초 관측 종료, 결과표·정상 복원·HW090TXT/영상 수거를 명시했다. 이 패키지는 SMB3 게임 코어가 아니다.

[첫 게임 계획](../docs/development/NES-GAME-COMPATIBILITY.ko.md): 사용자 파일393232바이트, SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`, mapper4·PRG256KiB/CHR128KiB·iNES1.0을 직접 확인했다. battery bit는 헤더 값으로만 기록하고 임의 수정/정확한 dump·칩 리비전 인증을 하지 않았다. 현재80/96KiB loader의384KiB 확장과 mapper/IRQ/화면/입력/소리가 남아 있다. SMB3를 우선하고 이후 mapper 확장마다 회귀를 유지한다. 원본 ROM은 수정·Git게시·패키지포함하지 않았다.

다음은 새 클록 TXT/화면을 분석해 RESET-held reference availability를 판단하는 것이다. 그 뒤 CF86 외부PSRAM·async/common-cause·최신MCU/전체SPI를 진행한다. 기존084저장/복원 질문과 부품/LED/분해/PCUSB 요청을 반복하지 않는다. 넓은 준비도4/7/1, report_trial_ready=true, nes_installable=false다. 동결717파일 manifest `1ef0c061a1a38dbbec210ad5ee8b4e1f54a7c7ed936b22f53ccaf5f131913040`. 완료 finalizer 재실행/044–091 archive 수정 금지.
