# NES185 전체 펌웨어와 실기 시험 패키지

PR116의 타일맵 재사용 후보를 전체 펌웨어에 통합했다. 구현 계약은 [MAP185](nes-map185-contract.ko.md), 설치·실기 절차는 [NES185 안내](nes-game185-ready.ko.md), 기계 판독 결과는 [검증 JSON](../analysis/paired185-verification.json)에 있다. 이 단계는60fps를 위한 전송량 감소 구현을 실기에 연결하는 작업이며, 실기 성능 통과 판정은 아니다.

## 선택 결과

- private `probes/nes-paired185`: arm01/check02/report02, evidence/asm01 및 rom01, romcheck01, release02.
- 펌웨어202,068바이트. 정적 RAM26,592, RUN 전경 호출 경로37,120, IRQ508, 잔여1,204바이트. 기존184의1,232바이트에서28바이트 감소했다. 보수적 정적 분석이며 실기 stack high-water 측정은 아니다.
- 실제 로그 formatter의 최대 폭4,003/4,096바이트. 새 진단 필드 없이185 파일명만 변경했다. `sink_window_schema=184`는 그대로다.
- 검증된184 FPGA의 RTL·제약·배치·배선·타이밍 관련73파일 보존.4096바이트 프로그램 ROM의 생성 MIF를 갱신한 뒤 CDB/ASM/CPF 실행. 새 MAP/FIT/STA 없음.
- 별도 복사본의 post-fit EDA ROM atom4개 netlist에서 각4096바이트가185 compact 이미지와 일치.32768바이트 Mesen ROM은 앞4032바이트와 마지막64바이트 header/vector를 compact4096으로 투영한다. RBF 비트 직접 추출/실물 readback은 아니다.
- 기존184 setup+.315ns/hold+.116ns와 조건부 IO/CDC 검증을 같은 배치에 재사용한다. full 전기/CDC MTBF signoff로 확대 해석하지 않는다.

## 짝과 보존

`NES185-SMB3-MAP-INHERIT.zip` SHA256:
`b4f060f4b0edc96571e363f6648d44aa85510d235e06a6f18230d2d651f25075`

펌웨어 `9a256f0ca3dffb09114ae72bca77722d0e4fc67d677f177f1dc1669451cbf6dd`, FPGA `13c4d4965cd1b1246e76856b35a5cade34f387324bab53b68bc54139c764433f`. SEAL1851이므로184 MCU/FPGA 파일과 섞지 않는다. ingress1813과4패킷 큐는 유지한다.

map185 build04와 full ARM 입력을 해시로 연결했다. 앞서 끝난 C37검사/30차등계획, 실제C·65816 화면 비교·6개 잘못된 헤더·STOP, FPGA 큐 replay, 실제 auto-poll186정상 표본은 그대로 재사용했다. 반복 실행 대신 전체 linked callback을 `nes_native_video185_build`로 연결해 RUN/IRQ를 다시 계산했다. GBC164·기존184·복원164 바이트와 다른 게임 세이브 SRAM을 보존한다. ROM과 배포 바이너리는 Git에 넣지 않는다.

`build01` 임시 드라이브 매핑과 `check01/report01` sandbox DLL623 실패는 호스트 재실행으로 해결했다. `release01`은 검증기의4096/32768 ROM 동일성 가정이 틀려 실패했고, 실제 기존 생성기의 compact 투영 규칙으로 고친 `release02`만 선택했다. 실패 로그와 완료archive는 수정하지 않는다.

## 다음 판단

실기에서 SMB3 숫자1타일+A 진입 후 오프닝/첫 레벨 끊김, 사운드, 가능하면 입력 유지, 약60초 메뉴 복귀와 두TXT를 받는다. 보관된 SMB3 map3952→1214바이트는 map 요청만의 수치다. 작은 COPY 패킷 증가와 CPU 처리 비용 때문에 전체 FPS 개선을 단정하지 않는다.

실기 결과를 받아 receive/build/seal 시간과 표시 완료를 비교한 뒤 연속 복사 묶음·CHR 차등·capture/전송/표시 겹침 중 실제 병목을 개선한다. 목표16.7ms와 MMC4/5·state·mute·frameskip 확장을 유지한다. SNES body3776/3776으로 여유가 없으므로 기능을 추가할 때 크기·호출 계약을 다시 검토한다. 같은184/044·불변 FIT·별도pad-only 시험은 하지 않는다. AV60fps 이후 장기 플레이/오류·reset 로그, 입력 품질을 마무리한다.
