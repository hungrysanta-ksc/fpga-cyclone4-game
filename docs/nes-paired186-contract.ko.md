# NES186 전체 펌웨어와 ROM-only 실기 준비

[구현 계약](nes-copy186-contract.ko.md) · [실기 안내](nes-game186-ready.ko.md) · [전체 검증](../analysis/paired186-verification.json).

PR116 같은 branch에서185 실기 결과에 이어186 시험판을 준비했다. 새 후보는 COPY6의 고정256바이트 묶음이며 프로토콜1861이다. 기존185 입력 유지와 사운드를 보존한다. 실기60fps 승인은 아니다.

- private `probes/nes-copy186`: build01/test01/evidence/coupled03/coupled04,1659파일 동결. 전체 C101검사 및 실제 C/65816 픽셀/잘못된 요청/STOP 검사 통과. 64정렬·옛64길이 거부 추가 확인.
- private `probes/nes-paired186`: arm01/check01/report01/evidence/asm01/rom01/romcheck01/release01.
- 전체 펌웨어202064바이트, 정적 RAM26592/RUN37120/IRQ508/잔여1204바이트. 로그4003/4096.185와 RAM·스택 여유 동일.
- 기존184 FPGA RTL·배치·배선 관련73파일 보존. 생성MIF 교체 후 CDB/ASM/CPF만 실행. 새 FIT/STA/불변RTL replay 없음. 실제 큐 전송 길이와CRC/버스 회로는 그대로다.
- post-fit4개 netlist의4096바이트 ROM이 새 compact 이미지와 일치.32768바이트 테스트 ROM의 앞4032+마지막64바이트 투영과 동일. 물리 readback이나 RBF ROM 비트 직접 추출은 아니다.
- 이전 setup+.315/hold+.116 및 조건부IO/CDC 검증을 같은 배치에 재사용. full 전기/MTBF signoff로 확대 해석하지 않는다.

ZIP `NES186-SMB3-COPY-GROUP.zip` SHA256:
`1c8c4e01c75fc44551e3a975c7f1a87f024dbb309a54d826ee6d29aab7c401ee`

펌웨어 `0a2241d4f3e3dd412da1a04674ed417954410200fae11f5c08dccb5f92c8891d`, FPGA `97eb2b58f5e5cb0ec56275ec0839961b6c21a661ea58951ca4a64fdfff231627`. 두 파일을 함께 설치한다.185/184와 섞지 않는다. 이전185·복원164·GBC·세이브SRAM 보존, ROM/바이너리는 Git에 넣지 않는다.

동일 합성7화면의 요청498→259, 보관SMB3 map64요청/1214B→17요청/558B는 이번 구현의 직접 확인 결과다. 실제 장면별 FPS는 다음 실기에서 판단한다. COPY 한 번의 무service 구간은 최대256바이트로 늘었으며, 이를64바이트 repeat service와 혼동하지 않는다. copy 이후 기존 poll/service·STOP 경로와 bounded 총작업량을 유지한다. 입력 service와SPC/upload 코드는 바이트 동일하다.

다음은 숫자1타일+A 첫레벨에서185 대비 끊김·소리·조작·실제 메뉴 복귀와186 두TXT를 확인한다. 초기 로딩·60초 제한을 유지한다. 같은185/044·별도pad-only·불변FIT 시험 불필요. 이번 결과를 보고 receive/build/seal의 잔여 비용, CHR 중복, capture/수신/표시 겹침을 목표16.7ms 기준으로 진행한다. body3776/3776, MMC4/5·state·mute·frameskip·장기 플레이 요구를 계속 고려한다.
