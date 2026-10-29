# NROM geometry 캡처 연결 진단

426에서는 자체 NROM의 실제 보드 RTL NES 코어가 픽셀을 만들고 수동 SNES 버스 입력에 반응했지만, 65816 소비·표시 완료는 검증하지 않았다. 427은 그 코어의 geometry를 D0/D1/D2로 읽어 기존 227 수신기에 전달하는 경로를 시험했다.

core01은 첫 블록을 기다리다 120 ms simulated watchdog에 실패했다. core02는 실제 BEGIN을 생략한 시드의 ROM epoch를 1로 바꾸고 105 ms까지 관찰했지만 같은 결과였다. core03/04의 거부 순간 관찰에서 fetch·compact·raster는 유효하고 patch는 오류 08(8번째 raw 행 초과)이었다. 화면이 켜진 상태의 mask는 0x0A였다. 실제 raster181은 mask 0x18 또는 0x1E만 일반 행으로 인정하고, 다른 mask의 모든 행을 raw로 처리한다. 따라서 0x0A 테스트 ROM에서 첫 블록이 없어지는 현상을 설명한다. 이는 일반 NROM 지원이 아니라 현재 지원 조건의 제약이며 오류를 무시하거나 독립 검사를 완화하지 않았다.

별도의 428 자체 ROM은 mask 0x1E와 숨긴 스프라이트를 사용한다. Mesen NES에서 색상과 명시적으로 주입한 4016 입력 반응은 통과했다. 동일 ROM의 실제 보드 RTL은 완전한 프레임에서 224행·28그룹·팔레트 1개를 유효하게 캡처하고 SPI 첫 블록 252바이트를 발행했다. D1 CRC16 0x8867 및 D2 token 0→1을 확인했다. 기존 227 수신 C는 같은 블록을 103개 레코드로 오류 없이 해석했다. PSRAM과 loader 검증 상태는 시드이고 SNES 버스는 수동 제어다. 전체 geometry·실제 ARM 실행·65816 표시, 실제 컨트롤러 및 실기는 별도로 확인해야 한다. 427의 실패 로그는 probes/nes-nrom427에 보존한다.

428 ROM SHA-256 `61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c`; 첫 블록 SHA-256 `f65cec869007209b22109e5764d0611eedcc50ff2c64bf6aad747d86fdad5c49`. 227 loader/FatFS host의 9개 사례도 통과했으나 SPI·PSRAM 및 GPIO는 모델이다. Lite 전체 합성은 변경하지 않았고 RTL 시뮬레이션 84개 초기 경고도 그대로 남는다.
