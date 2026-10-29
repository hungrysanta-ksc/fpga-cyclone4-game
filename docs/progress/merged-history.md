# PR 전체 이력 색인

Git의 실제 merge commit과 확인한 GitHub PR 메타데이터를 기준으로 정리했다. 최근129–136는 개별 네 항목 기록에서 읽는다. 과거 PR의 테스트 결과를 새 후보에 승계하지 않는다.

PR29는 다른 작업 브랜치로 병합됐으며 이 clone에 해당 merge 객체가 없어 master 도달을 단정하지 않는다. PR31은 확인 시점에 병합되지 않았다. PR135는948a2e9로 master에 병합됐고 PR136은 초안으로 열려 있다. 상태는2026-10-29 스냅샷이며 현재 remote를 다시 확인한다.

| PR | 상태 | 제목 | 근거/상세 |
|---|---|---|---|
| [#136](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/136) | 열림·초안 | NES484: 실제 ARM 계획 절감과 공급 병목 분리 | [정리](pr-136.md) |
| [#135](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/135) | 병합 | NES476–483: 수신 개선·MMC3 실기 성공과 성능 기준선 | [정리](pr-135.md) |
| [#134](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/134) | 병합 | 실기 NROM 20% 개선과 멀티 코어 현황·인계 정리 | [정리](pr-134.md) |
| [#133](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/133) | 병합 | NES: 제한 NROM 실기 진입과 loader 경계 검증 | [정리](pr-133.md) |
| [#132](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/132) | 병합 | NES: PR132 회고와 실기 진입·60프레임 후속 계획 | [정리](pr-132.md) |
| [#131](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/131) | 병합 | NES299–364 회고: 실제 개선과 지속 캡처·실기 검증 계획 | [정리](pr-131.md) |
| [#130](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/130) | 병합 | NES256–298: PR130 통합 검증 회고·개선 효과와 후속 구조 재검토 | [정리](pr-130.md) |
| [#129](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/129) | 병합 | NES248–255: 회로·시간 검증 회고와 머지 후 전체 경로 판정 계획 | [정리](pr-129.md) |
| [#128](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/128) | 병합 | NES247: 60프레임 목표의 ROM 확대·수신 시간·전체 경로 검증 | `64640645e3e3` |
| [#127](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127) | 병합 | NES231–246: 증분 전송 검증·공유 인코더 기각과 60fps 목표 재설정 | `b6958f24fbe2` |
| [#126](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/126) | 병합 | Merge pull request #126 from hungrysanta-ksc/codex/nes-scroll-workload-229 | `a86ba0504eae` |
| [#125](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/125) | 병합 | NES227: OAM 반복 전송 감소 및 실기 스크롤 결과 | `459bc6661fc9` |
| [#124](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/124) | 병합 | NES226: 일반 배경 계산 생략으로 스크롤 처리 비용 감소 | `f48017ad7912` |
| [#123](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/123) | 병합 | NES225: 원형 맵 배치와 실기 스크롤 성능 한계 기록 | `db37aa3f8ad2` |
| [#122](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/122) | 병합 | NES223: geometry 전송량 축소 및 실기 60초·스크롤 개선 확인 | `6c4bd8412a9e` |
| [#121](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/121) | 병합 | NES221·222: 슬롯 검색 개선과 실기 시작 절차 보강 | `93351eb37d77` |
| [#120](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/120) | 병합 | NES211–220: 변경 범위 출력과 정상 대기 수정, 실기 60초 통과 | `b8de96e93f47` |
| [#119](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/119) | 병합 | NES210: 스크롤 전송·재사용 측정과 타일 검색 개선 | `e0a924793dfc` |
| [#118](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/118) | 병합 | NES209 회고: 60fps 가능성·전송 예산과 스크롤 재사용 계획 | `c263d6385622` |
| [#117](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/117) | 병합 | NES188–209: 직접 타일 DMA 구현과 실기 결과 | `ef75c54f1be9` |
| [#116](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/116) | 병합 | NES185–187: 타일맵 재사용·입력 유지와 60fps 구조 재검토 | `7439179b45f7` |
| [#115](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/115) | 병합 | NES184: 연속 전송 큐 실기 결과와 패드 유지 오류 수정 후보 | `fef83c723df7` |
| [#114](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/114) | 병합 | NES182–183: 전송 개선과 실기 결과, 연속 전송 후속 계획 | `91b0bf79cb8c` |
| [#113](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/113) | 병합 | NES 부분 행 영상과 묶음 전송·지속 갱신 구현 | `3453c053c4f3` |
| [#112](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/112) | 병합 | NES 첫 레벨 영상 정지: 최소 진단 구현 및 실기 수집 오류08/82 확인 | `6ce5f2a7a585` |
| [#111](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/111) | 병합 | NES 화면 전환 클리핑 수정 시험판과 공통 영상 호환성 계획 | `3669027133d4` |
| [#110](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/110) | 병합 | NES 연속 영상 경로 개선과 176 회고·장면 검증 | `86e0195a22c7` |
| [#109](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/109) | 병합 | NES 새 영상 경로 연결과 첫 화면 실기 결과 기록 | `9c4e152b3d0b` |
| [#108](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/108) | 병합 | NES 영상 전송 회로 연결과 실제 내부 클록 타이밍 통과 | `607312230ff1` |
| [#107](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/107) | 병합 | NES 타일 출력과 세이브 보호·SNES 수신 응답 구현 | `019a92efeba6` |
| [#106](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/106) | 병합 | NES164 검정 구간 제거와 실기 갱신 지연 결과 | `a467be7e1e2d` |
| [#105](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/105) | 병합 | NES163 본체 사운드 초기화 연결과 실기 사운드·플레이 성공 | `6f0457d167a1` |
| [#104](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/104) | 병합 | NES162 사운드 경로 연결과 실기 결과: 플레이 통과·무음 수정 대기 | `23e41b59a227` |
| [#103](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/103) | 병합 | NES161 첫 레벨 플레이 통과와 방향키 유지 입력 문제 기록 | `a5da39ef5020` |
| [#102](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/102) | 병합 | NES160 렌더링 재개 예측 보강과 첫 레벨 실기 오류·표시 지연 기록 | `3100e5c78286` |
| [#101](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/101) | 병합 | NES159: 매퍼 쓰기 중 ROM 읽기 차단 및 월드맵 진입·이동 실기 확인 | `7f93ac599a95` |
| [#100](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/100) | 병합 | NES MMC3 선행 주소 예측과 158 실기 읽기 지연 분석 | `3ef0a0714fd8` |
| [#99](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/99) | 병합 | NES157: 정지 직전 이력 수집과 실기 CHR 주소 전환 확인 | `289674a14407` |
| [#98](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/98) | 병합 | NES156: 음원 차단·버튼 이력과 Select 성공·Start 정지 실기 결과 | `5b82510cedb4` |
| [#97](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/97) | 병합 | NES155: 배경 선행 읽기 적용 및 Select 입력 후 정지 실기 결과 | `e5bbdf545bae` |
| [#96](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/96) | 병합 | NES154: PPU 상태 회수 실기 성공과 배경 읽기 기한 오류 기록 | `4639d4b4e5ac` |
| [#95](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/95) | 병합 | NES153: PPU 오류 로그·메뉴 복귀 수정 및 실기 확인 | `95fa5e360610` |
| [#94](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/94) | 병합 | NES152: 입력 갱신 개선 및 실기 정지·오류 수신 결함 기록 | `b01e7cf5926b` |
| [#93](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/93) | 병합 | NES151: 게임 화면 갱신 수정 및 PPU 오류 실기 결과 | `9b26d7b6a837` |
| [#92](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/92) | 병합 | NES150: 실제 게임 화면·패드 연결 및 첫 실기 결과 기록 | `74f94640f7ee` |
| [#91](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/91) | 병합 | Merge pull request #91 from hungrysanta-ksc/codex/nes-game-147 | `9f97bb7ae4c6` |
| [#90](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/90) | 병합 | NES146: 연속 표시·메뉴 복귀 실기 결과와 게임 전환 계획 | `c38bad708988` |
| [#89](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/89) | 병합 | NES143~145: 실기 문자·고정 화면·메뉴 복귀 검증 | `b7923d1194d7` |
| [#88](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/88) | 병합 | NES142: 화면 진행 관측 구현과 실기 전송72회·영상 실패 확인 | `47460aa81ed2` |
| [#87](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/87) | 병합 | NES 141: ROM 실행·메뉴 복귀 수정과 실기 영상 실패 확인 | `112fd8b13307` |
| [#86](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/86) | 병합 | NES 140: ROM 응답 수정 후보와 실기 재실패 결과 | `6de714461240` |
| [#85](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/85) | 병합 | NES 139: 최초 ROM 오류 기록과 조기 복귀 실기 패키지 | `dd1464ac8449` |
| [#84](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/84) | 병합 | NES 화면 시험 패키지 및 실기 ROM 응답 오류 확인 | `bb5fd6860da0` |
| [#83](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/83) | 병합 | NES 실기 RUN 통과 반영 및 실제 영상 소비자 연결 | `4cbba8005a92` |
| [#82](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/82) | 병합 | NES 136: 최초 최소 RUN 실기 패키지와 STOP·메뉴 복원 연결 | `7de6ef0e1cad` |
| [#81](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/81) | 병합 | NES 135: 최소 RUN 회로의 명령 처리와 같은 클록 타이밍 개선 | `a8b4450a6f81` |
| [#80](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/80) | 병합 | NES: 최소 RUN 물리 결선과 CPU 진행 관측 구현 | `2fc0e0e9591c` |
| [#79](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/79) | 병합 | NES 133: 실제 코어 결선의 RUN 시작·종료와 CHR 변경 검증 | `91fa3f055182` |
| [#78](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/78) | 병합 | NES 132: 현재 배치의 클록 간 전달과 reset 경로 재검증 | `4df157e5fbc8` |
| [#77](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/77) | 병합 | Merge pull request #77 from hungrysanta-ksc/codex/nes-loader-counter-131 | `1d2257d03983` |
| [#76](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/76) | 병합 | NES: 로더 상태 enable 제거와 남은 카운터 타이밍 정리 | `77454989e171` |
| [#75](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/75) | 병합 | NES 129: reader 소유권 분리와 타이밍 후보 검증 | `5ab3754a99b8` |
| [#74](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/74) | 병합 | NES 128: 명령·로더 타이밍 개선과 남은 reader reset 경로 정리 | `533a01875cba` |
| [#73](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/73) | 병합 | NES 로더·검증 후 RUN·클록 감시 통합과 168MHz 타이밍 병목 확인 | `dfd1454db4e0` |
| [#72](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/72) | 병합 | NES 126: 영상 제어 동기화 배치 설정과 타이밍 검증 | `cd6325e7f298` |
| [#71](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/71) | 병합 | NES 125: 메모리·영상 데이터의 클록 간 전달 시간 검증 | `5cd4d28f71fd` |
| [#70](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/70) | 병합 | NES 도메인별 리셋 해제 배선 구현과 코어 검증 | `85e98c9243ea` |
| [#69](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/69) | 병합 | NES 실제 PLL·PSRAM 핀 배치와 교차 클록 타이밍 문제 정리 | `befb91f2746f` |
| [#68](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/68) | 병합 | NES 보호 메모리 읽기의 기한 실패 분석 및 168MHz 후보 검증 | `878c8ce71a9b` |
| [#67](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/67) | 병합 | NES: 70ns 메모리에서 전체 프레임과 클록 위상 검증 | `79daf3f539c1` |
| [#66](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/66) | 병합 | NES 전체80KiB 실기 통과 기록과 정상속도70ns 코어 읽기 검증 | `ac3baaaf1016` |
| [#65](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/65) | 병합 | NES 짧은 복구 실기 통과 기록과 전체80KiB 통합 시험 준비 | `459358e31d29` |
| [#64](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/64) | 병합 | Merge pull request #64 from hungrysanta-ksc/codex/nes-base-recovery-116 | `6135317d774b` |
| [#63](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/63) | 병합 | NES113: 무로그 진입 실패의 SD 인계 수정과 짧은 실기 진단 | `043c4381d50d` |
| [#62](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/62) | 병합 | NES 112: 실기 단계 로그와 적재·비교 진행 기록 추가 | `d28e1726a8c4` |
| [#61](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/61) | 병합 | NES 111: 80KiB 실기 패키지 제공과 실기 우선 개발 원칙 반영 | `9a6d9733c601` |
| [#60](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/60) | 병합 | NES 110: 제한 실기 시험 범위와 미확인 조건 정리 | `b49f9e2c8ea5` |
| [#59](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/59) | 병합 | Merge pull request #59 from hungrysanta-ksc/codex/nes-css-integration-109 | `eeed238d9e30` |
| [#58](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/58) | 병합 | NES 108: 진단 전용 CSS/NMI 고장 종료 구현 | `33b19045929e` |
| [#57](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/57) | 병합 | NES 107: 보드 자료 적용 범위와 공통 클록 고장 경로 확인 | `e3b0f4853698` |
| [#56](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/56) | 병합 | NES 106: 외부 지연 한계와 제한 실기 관측 조건 정리 | `3578defda4d5` |
| [#55](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/55) | 병합 | NES 105: 진단 파일 조합 검증과 작업 의미 기록 | `4558aedab3fe` |
| [#54](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/54) | 병합 | NES 104: 타이머·IRQ 통합 및 진단 중 출력 재진입 수정 | `93feb9f3262c` |
| [#53](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/53) | 병합 | NES 103: 공유 오류의 출력 전 SPI 차단과 UART 대기 억제 | `3dab89e66eff` |
| [#52](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/52) | 병합 | NES 102: 오류 정지 시 SPI와 GPIO 차단 구현 | `03f2ac3815e0` |
| [#51](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/51) | 병합 | NES 101: SPI 전송 완료 순서 수정과 종료 경계 검증 | `bedfad5bf53d` |
| [#50](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/50) | 병합 | NES 100: 실제 SRAM·SPI 연결과 오류 후 칩 선택 차단 | `6977f6c8fdd3` |
| [#49](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/49) | 병합 | NES 099: RTC 무한 대기 방지와 메뉴·저장 오류 전달 검증 | `13118bdb15df` |
| [#48](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/48) | 병합 | Merge pull request #48 from hungrysanta-ksc/codex/nes-menu-boundary-098 | `4ea53133ff22` |
| [#47](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/47) | 병합 | Merge pull request #47 from hungrysanta-ksc/codex/nes-config-images-097 | `1f57b10dd977` |
| [#46](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/46) | 병합 | NES: 실제 SD·구성·READY 코드 통합 검증과 다음 단계 인계 | `a005137040bf` |
| [#45](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/45) | 병합 | NES 095: CF86 전체 SPI 전송과 고장 취소 검증 | `7d669b1d6d91` |
| [#44](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/44) | 병합 | NES 094: CF86 MCU 세션의 고장 유지와 재접근 차단 | `e2a11912f179` |
| [#43](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/43) | 병합 | NES 093: CF86 비동기 차단 지연 분석과 고장 처리 계약 정리 | `b13a37973099` |
| [#42](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/42) | 병합 | NES 091–092: 클록 관측 실기 성공과 복원 확인, SMB3 첫 목표 기록 | `02ccce30618a` |
| [#41](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/41) | 병합 | NES 090: 클록 관측·TXT 저장 전체 세션과 ARM 펌웨어 통합 | `3f83e0f10416` |
| [#40](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/40) | 병합 | NES 089: CF87 구성과 클록 관측 왕복의 처리 제한 검증 | `6077d65b26ac` |
| [#39](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/39) | 병합 | NES 088: MCU 클록 수집 코드와 CF87 응답 검증 | `fef3935525cc` |
| [#38](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/38) | 병합 | NES 087: 메모리 비활성 기준 클록 관측 회로와 배선 검증 | `72ed581bd6c3` |
| [#37](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/37) | 병합 | NES 086: 비동기 reset 경계 수정과 새 배치·CDC 검증 | `4017a50d7164` |
| [#36](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/36) | 병합 | NES085: 단일 클록 정지 시 PSRAM 차단과 재시작 보호 검증 | `2995577f3728` |
| [#35](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/35) | 병합 | NES 084 실기 저장·재읽기·화면 및 정상 복원 통과 기록 | `bf29565e94fd` |
| [#34](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/34) | 병합 | NES 저장 진단: 쓰기 전 FAT 공간 탐색과 화면 여백 수정 | `5ad37abe1de6` |
| [#33](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/33) | 병합 | NES 보고서 초기화부터 저장·재읽기까지 단일 실행 검증 | `413c4fd11a39` |
| [#32](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/32) | 병합 | NES 보고서 전용 SD 초기화와 FatFS 연결 검증 재제출 | `648d399865e6` |
| [#31](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/31) | 미병합·닫힘 | NES 보고서 전용 SD 초기화와 FatFS 연결 검증 | 원문 메타데이터 |
| [#30](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/30) | 병합 | NES 080 검증 내용을 master에 반영 | `2a8c8140e5f4` |
| [#29](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/29) | 다른 브랜치 병합 | NES mini·부트 ROM 초기화와 최종 화면의 오류 보호 | `6dac56d12530` |
| [#28](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/28) | 병합 | Merge pull request #28 from hungrysanta-ksc/codex/nes-report-checkpoints-079 | `1efd312dbb07` |
| [#27](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/27) | 병합 | NES SD 보고서 저장 경로 통합 검증과 실기 관측 계획 정리 | `249f37fbe029` |
| [#26](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/26) | 병합 | NES071: CF68 FPGA·069 ARM 파일 쌍과 복원 검증 | `dbb4a3b17165` |
| [#25](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/25) | 병합 | NES070: CF68 전체 적재·읽기 비교와 종료 경로 검증 | `1245e0dff52c` |
| [#24](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/24) | 병합 | NES069: CF68 MCU 승인·초기 준비 대기와 오류 복구 보호 검증 | `8528e15eb511` |
| [#23](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/23) | 병합 | NES068: PSRAM 초기 대기·읽기 활성 유지와 외부 타이밍 예산 검증 | `4651eada3c26` |
| [#22](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/22) | 병합 | NES067: 진단 PSRAM 준비·유지 구간 검증과 다음 작업 인계 | `4d8868f2e324` |
| [#21](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/21) | 병합 | FXPAK 실물 부품 식별과 NES 진단 메모리 타이밍 검토 | `ea6d576a6df1` |
| [#20](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/20) | 병합 | NES 실기 진단 파일 쌍과 SD 백업·복원 사전 점검 검증 | `ffb920513a33` |
| [#19](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/19) | 병합 | NES065: 메뉴 복귀·늦은 로그의 대기 종료와 오류 보호 연결 | `40374438ebdd` |
| [#18](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/18) | 병합 | NES064: 진단 하위 대기 종료·오류 보호와 진행 표시 연결 | `28e58e240d99` |
| [#17](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/17) | 병합 | NES063: 전체 적재·읽기 비교·종료 경로의 보드 핀 모형 검증 | `76bfe89dddba` |
| [#16](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/16) | 병합 | NES062: connect candidate-aware SD verification to manual menu routes | `b8e22a3c1df1` |
| [#15](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/15) | 병합 | NES061: connect load-only diagnostic to physical board pins and clocks | `39e831aaf045` |
| [#14](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/14) | 병합 | NES060: bind SD readback verification and safe recovery | `99f6a1cb59ca` |
| [#13](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/13) | 병합 | NES059: SPI ROM readback verification and guarded core startup | `6e6e3b8f6955` |
| [#12](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/12) | 병합 | Merge pull request #12 from hungrysanta-ksc/codex/nes-readback-port-058 | `fad834e704cc` |
| [#11](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/11) | 병합 | NES 057: 승인된 ROM 크기와 코어 주소 범위 연결 | `02e5583514fc` |
| [#10](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/10) | 병합 | NES 056: STM32 SD 적재·GPIO 소유권·실패 복구 연결 | `533c7a699e1a` |
| [#9](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/9) | 병합 | NES 055: 전체 SPI 적재 후 실제 코어 8프레임 검증 | `8e50f0af8137` |
| [#8](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/8) | 병합 | NES 054: SPI ROM 적재 경계와 MCU 파형 검증 | `1ec6bef133ca` |
| [#7](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/7) | 병합 | NES 053까지 누적 개발 기록과 기종별 마일스톤 관리 정리 | `b1ef45ff57d2` |
| [#6](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/6) | 병합 | GBC 이식 회고와 NES 구현 착수 인계 | `161b97c90f4f` |
| [#5](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/5) | 병합 | 0.9.0 최종 라이선스·대응 소스·배포 검증 정리 | `ed9a0f9cac39` |
| [#4](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/4) | 병합 | 리드미 수정 | `803f9d82564c` |
| [#3](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/3) | 병합 | sd2snesHST 저장소와 0.9.0 릴리스 초안 연결 | `5e4d631344e1` |
| [#2](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/2) | 병합 | C44 소스 공개와 sd2snesHST 0.9.0 배포·멀티코어 개발 준비 | `92b4c5a05dc0` |
| [#1](https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/1) | 병합 | Document G13 STA, 200-frame backlog, and SRAM reset risk | `eb98df5391c6` |

전체 SHA/날짜/출처는 [JSON 색인](pull-requests.json)에 있다. 네트워크가 없어도 full clone의 `git show <merge SHA>`로 당시 변경과 결과 문서를 읽을 수 있다. 초기/누적 설명 원문은 [archive](archive/README.md), 현재 작업은 [프로젝트 현황](../PROJECT-STATUS.ko.md)을 따른다.
