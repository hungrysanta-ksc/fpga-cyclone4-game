# NROM461: 실제 ARM 검사와 FPGA CHECK·STOP 결합

460에서 전체 readback에 사용한 실제 418 firmware의 ARM `nes_rom_verify`와 SPI framing 기계어를 Unicorn에서 실행하고, GPIO 전송 함수만 transaction RPC로 연결해 실제 457 전체 board RTL의 SPI·loader·reader와 기능 PSRAM 모델을 구동했다. 457 FIT/live의 QSF 입력 66개와 시험 보드가 일치한다. 16KiB PRG·8KiB CHR 및 loader READY/count는 시드이며 실제 FatFS·ROM 적재·ARM GPIO와 IRQ는 이 실행에 포함되지 않는다.

16바이트를 실제 FPGA CHECK READ·STATUS·ACK로 비교한 뒤 두 오류를 각각 주입했다. source 실패에서는 ARM이 오류 4를 기록하고 STOP을 보내 loader count를 0으로 만들었고, 16번째 데이터 불일치에서는 오류 6을 기록하고 같은 STOP·상태 확인에 성공했다. 두 경우 START 전송은 0회이고 FPGA RUN 비활성·verified 해제·SNES 버스 해제를 확인했다. Questa 각각 0 errors, 기존 포트/초기화 경고 84개다. 전체 393,216바이트 ARM readback은 460의 모델 장치 시험이며, 이 제한 RTL 시험과 하나의 전체 업로드로 합치지 않는다.

첫 `joint01`은 테스트 드라이버에 결과 해석 함수가 없어 FPGA 실행 뒤 중단됐다. `joint05`는 Windows가 RPC 응답 파일을 일시적으로 잠가 드라이버가 중단됐다. 두 실패를 보존했고 파일이 열릴 때까지 제한 시간 내 재시도한 수정 후 `joint06`/`joint07`이 통과했고 최종 보존한 벤치 바이트로 다시 실행한 `joint08` 데이터 불일치와 `joint09` 소스 실패도 통과했다. `analysis/nrom461-joint.json`은 실제 SPI 요청의 START 부재와 66개 입력 해시를 독립 검사한다. 원시 자료는 `probes/nes-nrom461`이다.

실제 MCU·FPGA 재구성·SD/base/menu 복구, 장시간 캡처 및 60fps는 검증되지 않았다. 457의 raw reset/CDC와 미제약 IO도 남는다.
