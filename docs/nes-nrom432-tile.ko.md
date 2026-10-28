# 실제 227 타일 RTL과 ROM 경쟁

430에서 실제 227 planner가 생성한 두 타일 계획을 419 보드에 포함된 source_tile192·tile205·cache·물리 ROM reader RTL에 직접 제출했다. ROM pin은 같은 428 자체 ROM의 CHR 데이터를 사용하는 모델이다. NES core 요청과 제한된 ROM 허용 구간, 출력 backpressure를 포함했다. 두 타일 32바이트, CHR 읽기 16회, core 경쟁 응답 2회, 출력 대기 11회를 확인했고 0 errors/0 warnings였다. RTL 출력 scoreboard의 32바이트는 431의 65816 소비 시험에서 사용한 두 modeled 타일 파일과 같다.

이 시험은 plan을 RTL 포트에 직접 제출하며 SPI plan 전송·실제 NES 코어·65816을 동시에 실행하지 않는다. 표시 경로 전체나 60fps 시간의 증거가 아니다. 01은 실제 보드의 tile205 모듈을 컴파일 목록에 누락해 실패했고 02·03은 통과했다. raw 결과는 probes/nes-nrom432/tile03, ROM/plan 해시는 결과 JSON에 기록했다.
