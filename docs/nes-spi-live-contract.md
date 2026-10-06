# 055 SPI 적재 후 실제 코어 회귀

054의 디지털 SPI 명령과053의 실제 코어 실행을 연결하는 시험이다. 제품 RTL 변경은 없으며, 96KiB `banks32`와80KiB `fine_x` 진단을 각각 처음부터 적재한다. 실제 STM32·SD/메뉴 호출은 다음 경계다.

## 입력과 검증

- 해시가 고정된 private053 `live` 소스 export와 같은 PRG/CHR 입력이 필요하다. 모든 원본 소스 해시를 검사한 뒤 새 출력 폴더에 복사한다. upstream HDL이나 ROM을 공개 저장소에 추가하지 않는다.
- 핀 메모리는 미초기화 상태에서 시작한다. 시험 입력 배열은 SPI 송신 바이트와 비교 기준으로만 사용한다. PSRAM 내용은 `WE`와 byte lane을 통한 쓰기만 반영한다.
- BEGIN → 모든 DATA → END → START 순서로 전달한다. 매 바이트 완료 count,16KiB마다 직렬 STATUS, 전체 핀 메모리 내용, END/RUN 분리를 확인한다.
- `ready`는 다음 DATA 수신 가능 여부다. 마지막 바이트 이후 END 전에는 count가 전체 길이이고 `ready=0, loaded=0, run=0`이 정상이다. END 후 `loaded=1`, START 후 `run=1`을 각각 확인한다. 완료 count와 수신 가능 상태를 같은 의미로 해석하지 않는다.
- SPI는 반주기60ns의 가속 디지털 자극이다. 054의250kHz C callback 파형시험을 대체하거나 실제 MCU 처리량을 측정하는 시험이 아니다. 매 바이트 STATUS를 보내는 C 전송기와 달리 이 시험은 각 DATA 후 내부 완료 count를 확인한다.
- NES/memory/host 클록은 적재 중에도 계속 진행한다. 적재 watchdog1초와 RUN 이후 실행 watchdog150ms를 분리한다. 기존 ROM 응답 지연·PPU/CPU 마감·프레임/전송 무결성 검사는 그대로다. 출력 수집은 RUN 이후60ms에 허용한다.
- 시험의 `chr_32k` 입력으로 SPI BEGIN의 길이와 코어 CHR 마스크를 함께 선택한다. SPI BEGIN만으로 실제 보드의 코어 마스크를 설정하는 경로는 아직 없다. 보드 연결에서는 승인된 ROM 형상을 한곳에 고정해 로더와 코어가 같은 값을 사용하게 해야 한다. 이 별도 입력을 숨긴 채 SPI만으로 모든 코어 설정이 끝났다고 주장하지 않는다.
- 진단별4프레임에서 패킷을 디코드한 픽셀을 실제 PPU 픽셀과 비교하고,053의 픽셀·패킷 내용·전체 S/E/F/D 이벤트를 비교한다. release tick과 이벤트 시각은 **모든 프레임/이벤트가 같은 상수 차이**인 경우만 허용하고 차이를 기록한다.

## 실행

```powershell
./tools/run_nes_spi_live.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Baseline $PRIVATE_053_LIVE -Out $FRESH_ASCII_OUTPUT
```

기존 사용자 지침의 Starter FLOAT wrapper만 재사용한다. 입력 경로는 절대 경로, 출력은 존재하지 않는 ASCII 경로를 지정한다. wrapper는 개인 작업 폴더에서 실행되고 라이선스·서버 로그는 공개하지 않는다.

원시 증거 감사는 다음과 같다. 새 시뮬레이션이 아니며 private 원본 없이는 실행할 수 없다.

```powershell
python -B tools/verify_nes_spi_live.py --evidence $PRIVATE_055_LIVE --baseline $PRIVATE_053_LIVE --fit $PRIVATE_054_RESOURCE
```

모든 합성 모듈이054 공동 fit 입력과 동일한 경우에만 그 자원 결과를 재사용한다. 새 fit나 물리 STA 통과로 기록하지 않는다. 실제 보드 클록·핀, PSRAM 무결성 검사기, SNES 소비자와 프레임 마감·복구는 이 시험의 범위 밖이다.

비교기 자체의 대조 시험은 `nes_spi_live_compare_checks.py --baseline $PRIVATE_053_LIVE --out $FRESH_OUTPUT`이다. 복사한 자료에 전체+7클록을 적용하면 통과하고, 개별 이벤트1클록 또는 픽셀1개를 바꾸면 실패해야 한다. 합성한 감사 입력이며 새 RTL/SPI 실행으로 계산하지 않는다. 원본053 자료는 수정하지 않는다.
