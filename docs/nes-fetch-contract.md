# NES fetch 관측 및 최소 RTL 컴파일 계약

2026-10-05. SPDX-License-Identifier: MIT. 후보 NES-P2-FETCH-005.

## 입력과 분리

`tools/build_nes_fetch.py`는 MIT 자체 6502 프로그램과 CHR를 생성한다. NROM 32KB PRG,
8KB CHR, horizontal mirroring이며 save·상용 데이터가 없다. `run_nes_fetch.py`는
현재 generator로 만든 바이트와 입력 ROM이 완전히 같은지 검사한다. 일반 게임 실행기가 아니다.
원래 probe/diagnostic/sim 초안은 수정하지 않았고 기존 checkerboard generator는
`tests/nes-functional/build_smoke.py`에 독립 재현용으로 보존했다.

실험 파일은 새 ASCII 경로에 생성한다. Questa의 work SQLite와 Lua io는 이 환경에서
한글 경로 문제가 있었으므로 실행 출력은 ASCII 임시 경로, 최종 보존은 ignored
`analysis/local-fetch-verified/`를 사용했다. 모든 명령은 기존 독립 checkout에서 실행한다.
아래 변수는 설치된 실행 파일과 고정 upstream을 가리킨다. 새 도구 설치를 전제하지 않는다.

```powershell
# $PY: Python, $MESEN: 격리된 기존 Mesen.exe
# $UPSTREAM: 고정 NES_MiSTer checkout, $QUESTA: 기존 win64 도구 폴더
# $DOTNET: Mesen에 쓰는 기존 .NET 런타임 폴더
$env:DOTNET_ROOT = $DOTNET
$env:DOTNET_ROOT_X64 = $DOTNET
& $PY -B -X utf8 tools/build_nes_fetch.py --out "$env:TEMP/nes-fetch-rom-repro"
& $PY -B -X utf8 tools/run_nes_fetch.py --mesen $MESEN --probe "$env:TEMP/nes-fetch-rom-repro" --out "$env:TEMP/nes-fetch-run-repro"
& $PY -B -X utf8 tools/test_nes_fetch.py --probe "$env:TEMP/nes-fetch-rom-repro" --capture "$env:TEMP/nes-fetch-run-repro" --out "$env:TEMP/nes-fetch-negative-repro"

& $PY -B -X utf8 tests/nes-functional/build_smoke.py --out "$env:TEMP/nes-smoke-repro"
& $PY -B -X utf8 tools/nes_functional.py --upstream $UPSTREAM --out "$env:TEMP/nes-rtl-repro" --questa-bin $QUESTA --diagnostic "$env:TEMP/nes-smoke-repro" --testbench tests/nes-functional/nrom_tb.sv
```

모든 out 경로는 새 경로여야 한다. 마지막 명령은 현재 세션에서는 실행 라이선스 오류로
끝난다. 컴파일만 검사하려면 diagnostic/testbench 옵션을 생략한다. 출력 메시지의
`PASS minimal compilation`을 RTL 실행 성공으로 해석하면 안 된다.

## Mesen 관측 계약

격리된 Mesen CE 2.2.1의 파일 해시는 verification의 `mesen.tools`에 있다. 로컬 소스
기준은 `20ba206cef5ba207c21203176d02cb9f43dda9fb`와 기존 emucap 변경이며 새로
설치/패치하지 않았다. 설정은 VideoFilter=None, brightness/contrast/hue/saturation=0,
Lua IO 허용이다. 네 개 RGB 값은 고정 소스 `UI/Config/NesConfig.cs`의 기본 NES
팔레트 항목을 사용했다. 영상에 맞춰 색·위치·프레임 offset을 탐색하지 않았다.

Lua는 `nesPpuMemory` read 0..1FFF, CPU write $2000, endFrame을 관측한다.
read callback은 `convertAddress`로 물리 CHR ROM 주소를 기록한다. 반환 값이 없으므로
메모리를 대체하지 않는다. $2007 read를 하지 않는 자체 ROM이라 렌더링 fetch 분류가
가능하며, 이 분류기를 일반 게임에 그대로 적용하지 않는다.

`trace.tsv` 열은 kind, frame, scanline, dot, ppu.masterClock, CPU cycles, bus address,
value, physical address, memType, BG table 순서다. `frames.tsv`에는 frame, line, dot,
PPU counter, CPU cycles, table, ROM counter, width, height, CHR ROM enum이 들어간다.
read는 warmup 프레임 5부터 보존하고 최종 비교는 프레임 6..13이다. trace 182,207행은
9프레임 CHR read 182,196개와 CPU control write 11개를 포함한다.

각 프레임의 BG read slot 전체(241줄 × 34타일 × 2plane)를 검사한다. 이 중 실제 화소에
사용되는 구간은 pre-render 및 앞 scanline의 dot 325/327/333/335와 visible scanline의
dot 5..239다. 오른쪽 pipeline·사용되지 않는 pre-render 읽기를 working set에서 제외한다.
화면 기준은 좌표 → nametable tile → CHR bitplane → 고정 RGB 순서로 별도 계산한다.

frame counter 연속성, NTSC odd-frame skip 주기, table 교대, ROM counter 증가,
물리 주소/값, slot 누락, 화소 전체를 함께 검사한다. 오류 주입은 캡처 사본에만 적용하며
에뮬레이터의 실제 오류가 발생했다는 주장이 아니다. 원본 결과는 보존한다.

`ppu.masterClock`은 oscillator counter이며 top-level `masterClock`은 NES CPU cycles다.
PPU read와 CPU write callback이 counter 증가의 서로 다른 쪽에서 불리므로 raw 차에
한 dot의 위상 차가 포함된다. `first_*_lead_master_clocks`는 그 raw 관측 차이며 정확한
CPU φ2→PPU bus 시각을 뜻하지 않는다. sprite 두 plane의 동시 callback도 Mesen 근사다.

## RTL 경계와 증거

`nes_functional.py`는 고정 upstream의 최소 의존성만 ASCII 출력 폴더에 복사하고
선언 순서/타입만 변환한다. `simulation-only.diff`, source 입력/출력 해시, vcom/vlog/vsim
raw log를 보존한다. 생성된 cart adapter는 NROM·CPU RAM·CIRAM과 이상적인 메모리만
다루며 MMC3, 외부 메모리 latency, 보드 IO, full-fit/STA를 구현하지 않는다.

로컬 `rtl-02/03`의 컴파일 실패, `rtl-04`의 변환 예외로 생긴 부분 출력, `rtl-05`의
컴파일/최적화 성공 및 라이선스 실패를 유지한다. 처음 한글 경로 시도는
`analysis/local-functional-01`에 있다. upstream HDL·변환 diff·raw log·ROM·RGB·메모리 자료는
allowlist에 넣지 않는다. 공개 가능한 자체 소스·문서·요약과 해시만 명시적으로 허용한다.
컴파일에 사용된 의존성의 개별 라이선스 보류와 미연결 포트 경고도 그대로 남긴다.
